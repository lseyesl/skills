import math
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from assembly_diagnostics import pixels,axes,sweep,fit_pivot

class AssemblyDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.r=Path(self.tmp.name)
        Image.new('RGBA',(40,40),(0,0,0,0)).save(self.r/'a.png')
    def test_pixels_ignore_invisible_rgb_but_detect_shift(self):
        a=Image.new('RGBA',(40,40),(200,0,0,0));a.putpixel((10,10),(255,0,0,255));a.save(self.r/'a.png')
        b=Image.new('RGBA',(40,40),(0,200,0,0));b.putpixel((11,10),(255,0,0,255));b.save(self.r/'b.png')
        r=pixels(self.r/'a.png',self.r/'b.png',self.r)
        self.assertEqual(r['changed_pixels'],2);self.assertEqual(r['alpha_support_iou'],0)
        a.save(self.r/'b.png');self.assertEqual(pixels(self.r/'a.png',self.r/'b.png',self.r)['changed_pixels'],0)
    def manifests(self):
        Image.new('RGBA',(10,10),'red').save(self.r/'part.png')
        d={'schema_version':'1.0','coordinate_system':'image-pixels-y-down','source_size':[40,40],
           'nodes':[{'id':'body','pivot_global':[10,10]},{'id':'arm','parent':'body','pivot_global':[15,15]}],
           'parts':[{'id':'a','node':'body','file':'part.png','crop_origin':[10,10],'pixel_size':[10,10]},
                    {'id':'b','node':'arm','file':'part.png','crop_origin':[15,10],'pixel_size':[10,10]}]}
        (self.r/'ref.json').write_text(json.dumps(d));return d
    def test_axes_find_wrong_pivot_in_rotated_parent(self):
        d=self.manifests();d['nodes'][1]['pivot_global']=[18,19];(self.r/'candidate.json').write_text(json.dumps(d))
        r=axes(self.r/'ref.json',self.r/'candidate.json',self.r,{'angles':{'body':90}})
        arm=next(n for n in r['nodes'] if n['node']=='arm')
        self.assertAlmostEqual(arm['pivot_error_pixels'],5);self.assertFalse(arm['within_pivot_tolerance'])
    def test_sweep_reports_disconnected_anchors_and_overlap(self):
        self.manifests();config={'node':'arm','range':[-10,10],'step':10,'parts':['a','b'],'anchors':[[15,15],[15,15]]}
        r=sweep(self.r/'ref.json',config,self.r)
        self.assertEqual(len(r['samples']),3);self.assertTrue(all(s['anchor_distance_pixels']<1e-8 for s in r['samples']))
        config['anchors'][1]=[20,15];r=sweep(self.r/'ref.json',config,self.r)
        self.assertTrue(all(abs(s['anchor_distance_pixels']-5)<1e-8 for s in r['samples']))
        config['range']=[0,0];config['base_pose']={'translations':{'arm':[20,0]}}
        self.assertEqual(sweep(self.r/'ref.json',config,self.r)['zero_overlap_angles'],[0])
    def test_invalid_sampling_is_rejected(self):
        self.manifests()
        with self.assertRaisesRegex(ValueError,'invalid sweep'):sweep(self.r/'ref.json',{'node':'arm','range':[0,30],'step':0},self.r)

    def test_fit_axis_from_independent_landmarks(self):
        observations=[]
        for angle,x in [(30,[20,10]),(-45,[18,16]),(80,[10,25])]:
            c=math.cos(math.radians(angle));sn=math.sin(math.radians(angle))
            q=[10+c*(x[0]-10)-sn*(x[1]-12),12+sn*(x[0]-10)+c*(x[1]-12)]
            observations.append({'angle':angle,'before':x,'after':q})
        report=fit_pivot({'source_size':[40,40],'observations':observations},self.r)
        self.assertAlmostEqual(report['suggested_pivot'][0],10);self.assertAlmostEqual(report['suggested_pivot'][1],12)
        self.assertLess(report['rms_residual_pixels'],1e-10)
        observations[0]['after'][0]+=5
        self.assertGreater(fit_pivot({'source_size':[40,40],'observations':observations},self.r)['rms_residual_pixels'],1)
    def test_pivot_fit_rejects_zero_rotation(self):
        with self.assertRaisesRegex(ValueError,'degenerate'):
            fit_pivot({'source_size':[40,40],'observations':[{'angle':0,'before':[1,1],'after':[1,1]}]*2},self.r)

    def test_sweep_preserves_faint_alpha_support(self):
        d=self.manifests();d['parts'][1]['crop_origin']=[10,10]
        (self.r/'ref.json').write_text(json.dumps(d))
        Image.new('RGBA',(10,10),(255,0,0,1)).save(self.r/'part.png')
        result=sweep(self.r/'ref.json',{'node':'arm','range':[0,0],'parts':['a','b']},self.r)
        self.assertEqual(result['samples'][0]['joint_roi_overlap_pixels'],100)

if __name__=='__main__':unittest.main()

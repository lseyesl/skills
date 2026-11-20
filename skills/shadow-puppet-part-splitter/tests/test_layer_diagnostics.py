import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from layer_diagnostics import layers

class LayerDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.r=Path(self.tmp.name)
        Image.new('RGBA',(5,5),'red').save(self.r/'part.png')
        self.data={'schema_version':'1.0','coordinate_system':'image-pixels-y-down','source_size':[20,20],
          'nodes':[{'id':'body','pivot_global':[5,5]},{'id':'arm','parent':'body','pivot_global':[5,5]}],
          'parts':[{'id':k,'file':'part.png','pixel_size':[5,5],'crop_origin':[5,5],'node':'arm' if k=='front' else 'body','z_index':i} for i,k in enumerate(['back','front'])]}
        self.config={'occlusion_rules':[{'front':'front','back':'back'}]}
    def run_check(self):
        path=self.r/'manifest.json';path.write_text(json.dumps(self.data));return layers(path,self.config,self.r)
    def test_valid_order_and_actual_ids(self):
        result=self.run_check();self.assertEqual(result['status'],'pass-sampled')
        with Image.open(self.r/'frame-000000-ids.png') as im:self.assertEqual(list(im.getpixel((6,6))),result['id_colors']['front'])
    def test_wrong_order_marks_overlap(self):
        self.data['parts'][0]['z_index']=2
        result=self.run_check();self.assertEqual(result['status'],'fail');self.assertEqual(result['frames'][0]['violation_pixels'],25)
    def test_equal_z_uses_actual_array_order(self):
        self.data['parts'][0]['z_index']=1;self.data['parts'].reverse()
        self.assertEqual(self.run_check()['status'],'fail')
    def test_no_overlap_is_warning_not_visible_failure(self):
        self.data['parts'][0]['z_index']=2;self.data['parts'][0]['crop_origin']=[0,0]
        result=self.run_check();self.assertEqual(result['status'],'warning');self.assertEqual(result['frames'][0]['violation_pixels'],0)
    def test_opaque_third_party_hides_pair_but_translucent_does_not(self):
        self.data['parts'][0]['z_index']=2
        cover=dict(self.data['parts'][0],id='cover',z_index=3,file='cover.png');self.data['parts'].append(cover)
        Image.new('RGBA',(5,5),'blue').save(self.r/'cover.png');self.assertEqual(self.run_check()['status'],'warning')
        Image.new('RGBA',(5,5),(0,0,255,128)).save(self.r/'cover.png');self.assertEqual(self.run_check()['status'],'fail')
    def test_rules_do_not_cycle_across_disjoint_time_intervals(self):
        self.config['occlusion_rules']=[{'front':'front','back':'back','frames':[1,2]},{'front':'back','back':'front','frames':[3,4]}]
        self.config['frames']=[{'frame':1},{'frame':3}]
        result=self.run_check();self.assertEqual(result['occlusion_cycles'],[]);self.assertEqual(result['frames'][1]['violation_pixels'],25)
    def test_active_cycle_detected_without_pixel_overlap(self):
        self.config['occlusion_rules'].append({'front':'back','back':'front'})
        self.data['parts'][0]['crop_origin']=[0,0]
        result=self.run_check();self.assertTrue(result['occlusion_cycles']);self.assertEqual(result['status'],'fail')
    def test_region_limits_pixel_violations(self):
        self.data['parts'][0]['z_index']=2;self.config['occlusion_rules'][0]['region']=[5,5,8,8]
        self.assertEqual(self.run_check()['frames'][0]['violation_pixels'],9)
    def test_parent_intent_is_checked_separately(self):
        self.config['expected_parents']={'arm':None};self.assertEqual(self.run_check()['parent_errors'][0]['actual'],'body')
    def test_unknown_part_rejected(self):
        self.config['occlusion_rules'][0]['front']='unknown'
        with self.assertRaisesRegex(ValueError,'unknown draw part'):self.run_check()
    def test_uncovered_rules_are_reported(self):
        self.config['occlusion_rules'][0]['frames']=[10,20]
        result=self.run_check();self.assertEqual(result['unsampled_rules'],[0]);self.assertEqual(result['status'],'warning')

    def test_malformed_frame_sample_rejected_cleanly(self):
        self.config['frames']=[0]
        with self.assertRaisesRegex(ValueError,'frame sample must be an object'):self.run_check()

if __name__=='__main__':unittest.main()

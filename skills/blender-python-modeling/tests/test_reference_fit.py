"""Host tests for true constraints, semantic metrics and transaction boundaries."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
import cv2,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from reference_fit.config import validate,candidate,changed,dependencies,check_runtime
from reference_fit.geometry import loft,path_samples,part_seed
from reference_fit.evaluation import align,boundary_distance,color_delta,reference_masks,read
from reference_fit.refiner import decide,defects,optimize,converged
CASE=ROOT/'examples/clay-girl-fit/character.json'
def metrics(value=.7):
 return {'global':{'iou':value,'boundary_distance':.02},'components':{'arm_L':{'status':'measured','iou':value,'confidence':.9,'reference_bbox':[0,0,10,30],'model_bbox':[0,0,7,30]},'hair':{'status':'measured','iou':.9}},'landmarks':{'mean':.01,'max':.02}}
class ConfigTests(unittest.TestCase):
 def setUp(self):self.c=json.loads(CASE.read_text())
 def test_example(self):self.assertIs(validate(self.c),self.c)
 def test_invalid_inputs(self):
  for field,value in [('schema_version',2),('unexpected',1)]:
   c=copy.deepcopy(self.c);c[field]=value
   with self.subTest(field=field),self.assertRaises(ValueError):validate(c)
 def test_numeric(self):
  for value in [-1,True,float('nan'),float('inf'),'1']:
   c=copy.deepcopy(self.c);c['shape']['head']['width_scale']=value
   with self.subTest(value=value),self.assertRaises(ValueError):validate(c)
 def test_profiles(self):
  self.c['shape']['head']['sections'].reverse()
  with self.assertRaises(ValueError):validate(self.c)
 def test_degenerate_path(self):
  self.c['shape']['arm_L']['path'][1]=self.c['shape']['arm_L']['path'][0]
  with self.assertRaises(ValueError):validate(self.c)
 def test_unknown_material(self):
  self.c['shape']['head']['material']='missing'
  with self.assertRaises(ValueError):validate(self.c)
 def test_units(self):
  self.c['reference']['units']='meters'
  with self.assertRaises(ValueError):validate(self.c)
 def test_seed(self):
  self.c['materials']['skin']['seed']=1.2
  with self.assertRaises(ValueError):validate(self.c)
 def test_bounds(self):
  self.c['validation']['parameters'][0]['max']=-1
  with self.assertRaises(ValueError):validate(self.c)
 def test_locality_and_lock(self):
  d=candidate(self.c,'arm_L.radius_scale',.15);self.assertEqual(changed(self.c,d),['arm_L'])
  self.assertEqual(d['shape']['hair'],self.c['shape']['hair'])
  self.c['shape']['arm_L']['state']='approved'
  with self.assertRaises(ValueError):candidate(self.c,'arm_L.radius_scale',.1)
 def test_clamp(self):self.assertEqual(candidate(self.c,'head.cheek_fullness',100)['shape']['head']['cheek_fullness'],1)
 def test_dependencies(self):
  affected=dependencies(self.c,['head']);self.assertIn('eye_L',affected);self.assertNotIn('arm_L',affected)
 def test_loft(self):
  p=self.c['shape']['head'];v,f=loft(p,20,32);self.assertEqual(len(v),672);self.assertEqual(len(f),642);self.assertTrue(np.isfinite(v).all())
  d=copy.deepcopy(p);d['cheek_fullness']=.9;vv,_=loft(d,20,32);self.assertGreater(max(p[0] for p in vv),max(p[0] for p in v))
 def test_sweep(self):
  p=path_samples([[0,0,0],[0,0,1]],[.1,.2],4);self.assertEqual(p[0],[0,0,0,.1]);self.assertEqual(p[-1],[0,0,1,.2]);self.assertAlmostEqual(p[2][-1],.15)
 def test_seed_stability(self):
  self.assertEqual(part_seed(1,'arm'),part_seed(1,'arm'));self.assertNotEqual(part_seed(1,'arm'),part_seed(1,'leg'))
class MetricTests(unittest.TestCase):
 def setUp(self):self.a=np.zeros((80,60),np.uint8);self.a[10:70,20:40]=255
 def test_identity(self):
  _,m=align(self.a,self.a);self.assertEqual(m['iou_after'],1);self.assertEqual(boundary_distance(self.a,self.a,60),0)
 def test_global_similarity(self):
  b=np.zeros_like(self.a);b[5:35,8:18]=255;matrix,m=align(self.a,b,'bbox_similarity')
  self.assertEqual(matrix[0,0],2);self.assertEqual(matrix[1,1],2);self.assertGreater(m['iou_after'],.94);self.assertFalse(m['part_warps'])
 def test_no_alignment(self):
  _,m=align(self.a,np.roll(self.a,10,axis=1));self.assertLess(m['iou_after'],.5)
 def test_empty(self):
  with self.assertRaises(ValueError):align(self.a,np.zeros_like(self.a))
  self.assertIsNone(boundary_distance(self.a,np.zeros_like(self.a),60))
 def test_forbidden_warp(self):
  with self.assertRaises(ValueError):align(self.a,self.a,'elastic')
 def test_lab(self):
  a=np.full((80,60,3),120,np.uint8);b=a.copy();self.assertEqual(color_delta(a,b,self.a,self.a)['delta_e76'],0)
  b[:,:,2]=230;self.assertGreater(color_delta(a,b,self.a,self.a)['delta_e76'],10)
 def test_untrusted_annotations(self):
  im=np.zeros((80,60,4),np.uint8);im[:,:,3]=self.a;spec={'components':{'head':{'confidence':.2}}}
  _,parts,e=reference_masks(im,spec,'.');self.assertFalse(parts);self.assertEqual(e['head']['status'],'not_evaluable')
  spec['components']['head']['confidence']=.9
  with self.assertRaises(ValueError):reference_masks(im,spec,'.')
 def test_missing_reference(self):
  with self.assertRaises(FileNotFoundError):read('/nonexistent-reference-fit.png')
 def test_bad_segmentation(self):
  with self.assertRaises(ValueError):reference_masks(np.zeros((80,60,4),np.uint8),{'components':{'head':{'confidence':.9}}},'.')
class RefinementTests(unittest.TestCase):
 def setUp(self):self.c=json.loads(CASE.read_text());self.m=metrics()
 def test_gain(self):self.assertTrue(decide(self.m,metrics(.72),self.c,'arm_L')['accepted'])
 def test_global_regression(self):
  a=metrics(.73);a['global']['iou']=.65;self.assertIn('global_regression',decide(self.m,a,self.c,'arm_L')['reasons'])
 def test_other_part_regression(self):
  a=metrics(.73);a['components']['hair']['iou']=.8;self.assertIn('component_regression:hair',decide(self.m,a,self.c,'arm_L')['reasons'])
 def test_structure(self):self.assertIn('structure_failure',decide(self.m,metrics(.8),self.c,'arm_L',False)['reasons'])
 def test_landmark(self):
  a=metrics(.8);a['landmarks']['max']=.08;self.assertIn('landmark_regression:max',decide(self.m,a,self.c,'arm_L')['reasons'])
 def test_no_gain(self):self.assertFalse(decide(self.m,self.m,self.c,'arm_L')['accepted'])
 def test_plan(self):
  d=next(d for d in defects(self.m,self.c) if d['component']=='arm_L');self.assertTrue(d['evidence']['measured']);self.assertFalse(d['requires_full_regeneration']);self.assertIn('visible_region_too_narrow',d['issues'])
 def test_unmeasured_blocks_complete(self):
  m=metrics(.99);m['components']['torso']={'status':'not_evaluable'};self.assertFalse(converged(m,self.c))
 def test_limit(self):
  self.c['validation']['max_iterations']=0
  with tempfile.TemporaryDirectory() as d:
   r=optimize(self.c,self.m,Path(d)/'original.blend',d,lambda *a:self.fail());self.assertEqual(r['stop_reason'],'iteration_limit');self.assertEqual(r['accepted_iterations'],0)
 def test_failed_render(self):
  self.c['validation']['max_iterations']=1
  def fail(*a):raise RuntimeError('Render failed')
  with tempfile.TemporaryDirectory() as d:
   original=Path(d)/'original.blend';original.write_text('untouched');r=optimize(self.c,self.m,original,d,fail)
   self.assertEqual(Path(r['scene']),original.resolve());self.assertEqual(original.read_text(),'untouched');self.assertEqual(len(r['history']),2)
 def test_reject_and_rollback(self):
  self.c['validation']['max_iterations']=1
  with tempfile.TemporaryDirectory() as d:
   original=Path(d)/'original.blend';r=optimize(self.c,self.m,original,d,lambda *a:(metrics(.6),True));self.assertEqual(r['accepted_iterations'],0);self.assertEqual(Path(r['scene']),original.resolve())
 def test_best_candidate_snapshot(self):
  self.c['validation']['max_iterations']=1
  def run(c,source,affected,folder):folder.mkdir();return metrics(.8 if folder.name=='plus' else .75),True
  with tempfile.TemporaryDirectory() as d:
   r=optimize(self.c,self.m,Path(d)/'original.blend',d,run);self.assertEqual(r['accepted_iterations'],1);self.assertIn('plus',r['scene']);self.assertEqual(sum(p.get('selected',False) for p in r['history']),1)
 def test_locked_dependency(self):
  self.c['shape']['eye_L']['state']='locked';self.c['validation']['max_iterations']=1;m=metrics();m['components']['head']={'status':'measured','iou':.5,'reference_bbox':[0,0,10,10],'model_bbox':[0,0,8,10]}
  with tempfile.TemporaryDirectory() as d:
   r=optimize(self.c,m,Path(d)/'original.blend',d,lambda *a:self.fail());self.assertEqual(r['accepted_iterations'],0);self.assertTrue(all('locked_dependency' in v['reasons'] for v in r['history']))
class FailureAndEvidenceTests(unittest.TestCase):
 def test_runtime_capability_boundary(self):
  check_runtime((4,5,12));check_runtime((5,0,0))
  for version in [(3,6,0),(6,0,0)]:
   with self.assertRaises(RuntimeError):check_runtime(version)
 def test_missing_required_section(self):
  c=json.loads(CASE.read_text());del c['materials']
  with self.assertRaises(ValueError):validate(c)
 def test_invalid_surface_and_light_parameters(self):
  for section,key,value in [('materials','medium',-.1),('render','exposure',float('nan'))]:
   c=json.loads(CASE.read_text())
   if section=='materials':c[section]['skin'][key]=value
   else:c[section][key]=value
   with self.assertRaises(ValueError):validate(c)
 def test_missing_or_mismatched_annotations(self):
  from reference_fit.evaluation import annotations
  image=np.zeros((30,30,4),np.uint8)
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'annotations.json'
   with self.assertRaises(FileNotFoundError):annotations(p,image)
   p.write_text(json.dumps({'schema_version':1,'image_size':[31,30],'components':{'head':{}}}))
   with self.assertRaises(ValueError):annotations(p,image)
 def test_explicit_mask_missing(self):
  image=np.zeros((80,60,4),np.uint8);image[10:70,20:40,3]=255
  a={'components':{'head':{'confidence':.9,'mask':'missing-mask.png'}}}
  with tempfile.TemporaryDirectory() as d,self.assertRaises(FileNotFoundError):reference_masks(image,a,d)
 def test_observed_color_sampling(self):
  from reference_fit.evaluation import sampled_colors
  image=np.full((20,20,3),(12,34,56),np.uint8);mask=np.ones((20,20),np.uint8)*255
  self.assertEqual(sampled_colors(image,{'head':mask})['head']['hex'],'#38220C')
 def test_immutable_stop_no_actions(self):
  c=json.loads(CASE.read_text());c['shape']['arm_L']['state']='locked'
  with tempfile.TemporaryDirectory() as d:
   r=optimize(c,metrics(),Path(d)/'accepted.blend',d,lambda *a:self.fail())
   self.assertEqual(r['stop_reason'],'no_actionable_unlocked_parameters')
 def test_profile_has_no_artificial_zero_slope_bands(self):
  from reference_fit.geometry import sample
  rows=[[0,1],[1,2],[2,3]];eps=.001
  left=(sample(rows,1)[0]-sample(rows,1-eps)[0])/eps;right=(sample(rows,1+eps)[0]-sample(rows,1)[0])/eps
  self.assertAlmostEqual(left,1,places=4);self.assertAlmostEqual(right,1,places=4)

class ProcessFailureTests(unittest.TestCase):
 def test_subprocess_render_failure_retains_log(self):
  from reference_fit.process import run_logged
  with tempfile.TemporaryDirectory() as d:
   log=Path(d)/'blender.log'
   with self.assertRaisesRegex(RuntimeError,'failed 7'):run_logged([sys.executable,'-c','print("render failure evidence");raise SystemExit(7)'],log,5)
   self.assertIn('render failure evidence',log.read_text())
 def test_subprocess_timeout(self):
  from reference_fit.process import run_logged
  with tempfile.TemporaryDirectory() as d,self.assertRaisesRegex(RuntimeError,'timed out'):
   run_logged([sys.executable,'-c','import time;time.sleep(2)'],Path(d)/'log',.05)
 def test_missing_blender_executable(self):
  from reference_fit.process import run_logged
  with tempfile.TemporaryDirectory() as d,self.assertRaises(FileNotFoundError):run_logged(['/nonexistent/blender-fit-test'],Path(d)/'log',1)
 def test_unknown_parameter_not_silently_ignored(self):
  c=json.loads(CASE.read_text());c['shape']['head']['cheek_fullnes']=.7
  with self.assertRaises(ValueError):validate(c)

if __name__=='__main__':unittest.main()

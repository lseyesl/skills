"""Real Blender regression: ownership, determinism, local rebuilding and rig guards."""
from pathlib import Path
import argparse,sys,json,copy,traceback
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from reference_fit.config import load,candidate
from reference_fit.blender_builder import build,fingerprints,OWNER
from reference_fit.blender_validation import workspace,structure,rig_probe
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=args.output.resolve()
if out.exists():raise FileExistsError(out)
out.mkdir(parents=True);c,base=load(ROOT/'examples/clay-girl-fit/character.json');checks={}
def test(name,fn):
 try:checks[name]={'ok':True,'result':fn()}
 except Exception as exc:checks[name]={'ok':False,'error':str(exc),'traceback':traceback.format_exc(limit=4)}
def require(v,message):
 if not v:raise AssertionError(message)
scene=bpy.data.scenes.new('Disposable fit integration');bpy.context.window.scene=scene
foreign=bpy.data.objects.new('Unowned preserved sentinel',None);scene.collection.objects.link(foreign);foreign.location=(4,5,6)
workspace(scene,c,base);scene,_=build(c,scene);initial=fingerprints(scene,c['character_id'])
def ownership():
 require(tuple(foreign.location)==(4,5,6),'Unowned object changed')
 refs=[o for o in scene.objects if o.get('fit_reference_view')]
 require(len(refs)==2 and all(o.data.packed_file and o.empty_image_depth=='FRONT' for o in refs),'Reference prerequisites missing')
 for ob in refs:
  up=ob.rotation_euler.to_matrix()@__import__('mathutils').Vector((0,1,0))
  require(abs(up.z-1)<1e-5,'Side/front reference not upright')
  cal=json.loads(ob['fit_calibration'])
  require(abs(ob.empty_display_size-max(cal['image_size'])/cal['pixels_per_unit'])<1e-5,'Reference Image Empty largest-dimension calibration wrong')
 count=len(bpy.data.objects);workspace(scene,c,base);require(len(bpy.data.objects)==count,'Reference refresh duplicates objects')
 return {'references':len(refs),'owned_meshes':len(initial)}
test('source_preservation_and_packed_references',ownership)
def deterministic():
 before={k:len(getattr(bpy.data,k)) for k in ['objects','meshes','materials']}
 for i in range(2):
  build(c,scene);require(fingerprints(scene,c['character_id'])==initial,'Seed/names/materials drift: '+str([k for k,v in fingerprints(scene,c['character_id']).items() if initial.get(k)!=v]))
 after={k:len(getattr(bpy.data,k)) for k in before};require(before==after,'Datablock leak')
 return after
test('repeatable_build_no_datablock_growth',deterministic)
def local():
 d=candidate(c,'arm_L.radius_scale',.15);before=fingerprints(scene,c['character_id']);build(d,scene,['arm_L']);after=fingerprints(scene,c['character_id'])
 moved=[k for k in before if before[k]!=after[k]]
 require(moved and all('::arm_L::' in k for k in moved),'Unrelated/locked component drift')
 require(before.keys()==after.keys(),'Stable IDs changed');return moved
test('actual_local_edit_preserves_locked_materials_and_geometry',local)
def locks():
 try:build(c,scene,['hair'])
 except ValueError:return True
 raise AssertionError('Locked part rebuilt')
test('locked_component_rebuild_rejected',locks)
def project():
 d=candidate(c,'head.cheek_fullness',.25);before=fingerprints(scene,c['character_id']);_,affected=build(d,scene,['head']);after=fingerprints(scene,c['character_id'])
 require('eye_L' in affected and before['clay_girl_fit::eye_L::patch']!=after['clay_girl_fit::eye_L::patch'],'Face not reprojected')
 require(before['clay_girl_fit::hair::cap']==after['clay_girl_fit::hair::cap'],'Locked hair changed');return affected
test('head_shape_reprojects_face_preserves_hair',project)
def topology():
 qa=structure(scene,c);require(qa['ok'],qa['errors']);return {'meshes_checked':len(qa['meshes'])}
test('evaluated_topology_normals_depth_and_connections',topology)
def depth():
 d=copy.deepcopy(c);d['shape']['head']['depth_scale']=.5;build(d,scene,['head']);qa=structure(scene,d)
 require(any('insufficient depth' in e for e in qa['errors']),'Paper head accepted');build(c,scene,['head']);return True
test('flattened_head_rejected',depth)
def weights():
 qa=rig_probe(scene,c);require(qa['ok'],qa);return qa
test('actual_four_limb_weight_and_bend_probe',weights)
def shared():
 d=copy.deepcopy(c);d['materials']['skin']['color']='#F0BC87'
 try:build(d,scene,['arm_L'])
 except ValueError:return True
 raise AssertionError('Local edit mutated a shared material')
test('shared_material_change_rejected_in_local_edit',shared)
def disconnected_socket():
 d=copy.deepcopy(c);d['shape']['arm_L']['path'][0][0]=-.5
 qa=structure(scene,d);require(any('Disconnected limb socket' in e for e in qa['errors']),'Disconnected shoulder passed broad-phase only')
 return True
test('actual_socket_surface_check',disconnected_socket)
def render_transaction():
 from reference_fit.blender_validation import setup,render_channels
 from validate_clay_scene import check_outputs
 d=copy.deepcopy(c);d['reference']['image_size']=[128,134];d['reference']['center_px']=[v/4 for v in c['reference']['center_px']];d['reference']['pixels_per_unit']/=4;d['render']['samples']=2
 setup(scene,d);before=fingerprints(scene,c['character_id']);render_channels(scene,d,out/'passes',quick=True)
 require(before==fingerprints(scene,c['character_id']),'Render pass mutated/restyled model')
 require(scene.view_settings.view_transform==d['render']['view_transform'] and scene.cycles.samples==2,'Render settings not restored')
 images=check_outputs(sorted((out/'passes').glob('*.png')));require(len(images)==5 and all(i['ok'] for i in images),'Missing/corrupt actual channels')
 return {'decoded_channels':len(images),'model_materials_restored':True}
test('actual_render_channels_restore_original_materials',render_transaction)
def material_layers():
 mats={m.get('fit_material_id'):m for m in bpy.data.materials if m.get('fit_material_id')}
 for key,settings in c['materials'].items():
  m=mats[c['character_id']+'::'+key];p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
  require(abs(p.inputs['Roughness'].default_value-settings['roughness'])<1e-6,'Material roughness drift')
  require(sum(n.type=='BUMP' for n in m.node_tree.nodes)==2,'Missing medium/micro bands')
 return {'region_materials':len(mats),'micro_and_medium_separate':True}
test('per_region_three_band_surface_shader',material_layers)
result={'blender':bpy.app.version_string,'checks':checks,'ok':all(v['ok'] for v in checks.values())}
(out/'integration.json').write_text(json.dumps(result,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(out/'scene.blend'))
print(json.dumps(result,indent=2))
if not result['ok']:raise SystemExit(1)

"""Blender integration of scoped gates and production template; synthetic review only."""
import bpy
import importlib.util
import json
import sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from stage_guard import file_input,require_stage
from blockout_gate import require_blockout_review,review_signature
out=Path(sys.argv[sys.argv.index('--')+1]);out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
spec=importlib.util.spec_from_file_location('project_template',ROOT/'assets/blender_task_template.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.TASK_ID='pipeline-test';m.BUILD_MODE='original';m.REFERENCE_HELPER_DIR=ROOT/'scripts';m.MODELING_PLAN=out/'plan.json';m.MODELING_SCOPE=['body']
m.BUILD_RECEIPT=out/'build.json';m.BLOCKOUT_RECEIPT=out/'blockout.json';m.BLOCKOUT_REVIEW=out/'review.json';m.REFINEMENT_RECEIPT=out/'refine.json'
plan={'schema_version':1,'task_id':m.TASK_ID,'intended_use':'synthetic static assembly','modules':[
 {'id':'body','method':'box','reason':'continuous low-resolution control cage','world_dimensions':[3,1,1],'dimension_tolerance':0.00001,'objects':['CoarseBody'],'depends_on':[],'checks':[{'id':'shape','kind':'visual','criterion':'inspect proportion and silhouette'}]},
 {'id':'accessory','method':'primitives','reason':'independent part','objects':['Accessory'],'depends_on':[],'checks':[{'id':'shape','kind':'visual','criterion':'inspect shape'}]}]}
m.MODELING_PLAN.write_text(json.dumps(plan))
m.REFERENCE_PREPARATION=out/'reference-preparation.json'
m.REFERENCE_PREPARATION.write_text(json.dumps({'schema_version':1,'task_id':m.TASK_ID,'purpose':'synthetic original geometry','route':'no_reference','reason':'Original test cube, no input images','source_images':[],'construction_images':[]}))
bpy.ops.mesh.primitive_cube_add(size=0.2,location=(-3,0,0));protected=bpy.context.object;protected.name='Protected'
checks={}
def rejects(name,fn):
    try:fn()
    except (RuntimeError,ValueError,NotImplementedError,FileNotFoundError):checks[name]=True
    else:raise AssertionError('Did not block: '+name)
m.EXECUTION_STAGE='blockout';rejects('placeholder_creates_no_model',m.main)
assert bpy.data.objects.get('Protected') is protected and bpy.data.objects.get('CoarseBody') is None
checks['placeholder_failure_recorded']=json.loads(m.BUILD_RECEIPT.read_text())['status']=='failed'
def build(plan,scope):
    m.remove_previous_generated_data(scope,'blockout')
    bpy.ops.mesh.primitive_cube_add();obj=bpy.context.object;obj.name='CoarseBody';obj.scale=(1.5,0.5,0.5)
    m.mark_owned(obj,'body','blockout');m.mark_owned(obj.data,'body','blockout');return [obj]
m.build_blockout=build;m.main();body=bpy.data.objects['CoarseBody'];checks['cube_box_route_builds']=len(body.data.vertices)==8
checks['measured_dimensions']=m.validate_blockout([body],plan,['body'])['measurements']['body']['world_dimensions']==[3,1,1]
wrong=json.loads(json.dumps(plan));wrong['modules'][0]['world_dimensions']=[9,1,1]
rejects('dimension_failure_blocks',lambda:m.validate_blockout([body],wrong,['body']))
coarse=m._state([plan['modules'][0]])
def refine(objects,plan,scope):
    result=objects[0].copy();result.data=objects[0].data.copy();result.name='DetailedBody';bpy.context.collection.objects.link(result)
    m.mark_owned(result,'body','refine');m.mark_owned(result.data,'body','refine')
    modifier=result.modifiers.new('Subdivision','SUBSURF');modifier.levels=1;return [result]
m.refine_geometry=refine;m.EXECUTION_STAGE='refine'
rejects('no_review_blocks_refinement',m.main);assert bpy.data.objects.get('DetailedBody') is None
# Real diagnostic artifact; review below is explicitly a protocol fixture, not artistic approval.
bpy.ops.object.camera_add(location=(5,-7,5));camera=bpy.context.object;camera.rotation_euler=(Vector((0,0,0))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=6
scene=bpy.context.scene;scene.camera=camera;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=4;scene.cycles.use_denoising=False
scene.render.resolution_x=400;scene.render.resolution_y=300;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('World');scene.world.use_nodes=True
bpy.ops.object.light_add(type='AREA',location=(1,-3,5));bpy.context.object.data.energy=500;bpy.context.object.data.size=4
scene.render.filepath=str(out/'blockout.png');bpy.ops.render.render(write_still=True)
review={'schema_version':1,'task_id':m.TASK_ID,'status':'passed','reviewer':'synthetic-integration-only','modules':{'body':{'unresolved_issues':[],'checks':{'shape':{'status':'passed','finding':'Synthetic gate calibration, not reference-fidelity approval','view':'diagnostic perspective','evidence':[{'path':'blockout.png','sha256':file_input(out/'blockout.png')['sha256']}]}}}}}
review['inspection_signature']=review_signature(m._load_plan,['body'],m._state,lambda:m._dependencies(m._load_plan()))
m.BLOCKOUT_REVIEW.write_text(json.dumps(review));m.EXECUTION_STAGE='review';m.main()
# Other independent objects do not invalidate the coarse geometry gate.
protected.location.x-=1;bpy.context.view_layer.update();m.EXECUTION_STAGE='refine';result=m.main()
checks['review_allows_derived_refinement']=result['objects']==['DetailedBody'] and not result['ready_to_claim_complete']
checks['coarse_preserved']=coarse==m._state([plan['modules'][0]])
require_stage(m.REFINEMENT_RECEIPT,'refine',m.refinement_inputs)
# Detail-only changes are outside the source gate; source edits invalidate it.
bpy.data.objects['DetailedBody'].data.vertices[0].co.x+=0.1;bpy.context.view_layer.update()
require_blockout_review(m.BLOCKOUT_RECEIPT,m._load_plan,['body'],m.BLOCKOUT_REVIEW,m._state,lambda:m._dependencies(m._load_plan()))
checks['detail_only_edit_preserves_source_gate']=True
body.data.vertices[0].co.x+=0.2;bpy.context.view_layer.update()
rejects('source_geometry_edit_invalidates',lambda:require_stage(m.REFINEMENT_RECEIPT,'refine',m.refinement_inputs))
rejects('stale_gate_blocks_callback',m.main)
# Restore source then demonstrate actual existing-asset reuse, without calling builder again.
body.data.vertices[0].co.x-=0.2;bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(out/'reuse-source.blend'))
plan['modules'][0].update(method='reuse',reason='existing control mesh already fits this limited task',source_snapshot='reuse-source.blend');m.MODELING_PLAN.write_text(json.dumps(plan))
review['inspection_signature']=review_signature(m._load_plan,['body'],m._state,lambda:m._dependencies(m._load_plan()))
m.BLOCKOUT_REVIEW.write_text(json.dumps(review))
m.EXECUTION_STAGE='review';m.main();checks['existing_asset_reused_without_rebuild']=bpy.data.objects.get('CoarseBody') is body
# A failed scoped build cannot delete independent task-owned geometry through the helper.
m.mark_owned(protected,'accessory','blockout');m.remove_previous_generated_data(['body'],'refine')
checks['scoped_cleanup_preserves_other_module']=bpy.data.objects.get(protected.name) is protected
shared=dict(plan['modules'][1],id='shared-region',objects=['CoarseBody'])
plan['modules'].append(shared);m.MODELING_PLAN.write_text(json.dumps(plan))
rejects('shared_semantic_mesh_not_deleted',lambda:m.remove_previous_generated_data(['body'],'blockout'))
assert bpy.data.objects.get('CoarseBody') is body
# A final consumer cap cannot reject a sound higher-resolution construction source.
# The exact same geometry must still be rejected as a budgeted delivery.
from blockout_gate import resource_limits
from production_checks import require_asset_geometry
budget_plan={'resource_budget':{'required':True,'max_triangles':1,'reason':'synthetic delivery cap'}}
source_report=m._geometry_check([body],'refine',budget_plan)
checks['source_above_delivery_cap_allowed']=source_report['passed'] and source_report['evaluated_triangles']>1 and source_report['budget_passed'] is None
rejects('same_source_rejected_as_delivery',lambda:require_asset_geometry([body],stage='delivery',**resource_limits(budget_plan,'delivery')))
budget_plan['resource_budget']['working_max_triangles']=1
rejects('explicit_working_resource_cap_enforced',lambda:m._geometry_check([body],'refine',budget_plan))
from reference_fit.blender_validation import structure
from reference_fit.blender_builder import OWNER as FIT_OWNER
body[FIT_OWNER]='budget-test'
fit_config={'character_id':'budget-test','shape':{},'validation':{'max_triangles':1}}
fit_source=structure(bpy.context.scene,fit_config)
checks['fitter_source_not_rejected_by_delivery_cap']=fit_source['ok'] and fit_source['delivery_budget_passed'] is False and fit_source['geometry_audit']['budget_passed'] is None
fit_config['validation']['working_max_triangles']=1
checks['fitter_explicit_working_cap_rejects']=not structure(bpy.context.scene,fit_config)['ok']
report={'passed':all(checks.values()),'blender':bpy.app.version_string,'checks':checks,'scope':'synthetic blockout/review/refinement/freshness mechanics only; no visual-quality or Agent-effect certification'}
(out/'pipeline-report.json').write_text(json.dumps(report,indent=2));print('BLOCKOUT_PIPELINE_OK',json.dumps(report))
if not report['passed']:raise SystemExit(1)

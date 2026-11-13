"""Project template: implement builders; default placeholders never create a model.
Keep reviewed coarse sources immutable while refining copies. No automatic save/export.
"""
from __future__ import annotations
import json
import math
from pathlib import Path
import sys
import bpy

TASK_ID='replace-me'
OWNER_KEY='codex_task_id'
MODULE_KEY='codex_module_id'
PHASE_KEY='codex_build_phase'
BUILD_MODE=None  # reference, original, waived
SCENE_MODE='create'  # create: owned empty scene; edit: explicitly named existing scene
SCENE_NAME=None  # defaults to MODEL_<TASK_ID> only for create
WAIVER_REASON=''
EXECUTION_STAGE=None  # blockout, review, refine
REFERENCE_HELPER_DIR=None  # installed Skill scripts directory, required for gates
MODELING_PLAN=None  # project modeling-plan.json
MODELING_SCOPE=[]  # explicit module IDs, one receipt per scope
REFERENCE_CONFIG=None
REFERENCE_PREPARATION=None  # explicit route decision, required even for no-reference originals
CALIBRATION_REVIEW=None
BLOCKOUT_REVIEW=None  # inspected evidence JSON, not pre-filled at build time
BLOCKOUT_RECEIPT=None
BUILD_RECEIPT=None
REFINEMENT_RECEIPT=None
BUILD_OUTPUTS=[]
REFINEMENT_OUTPUTS=[]
BLOCKOUT_PARAMETERS={}
REFINEMENT_PARAMETERS={}
BLOCKOUT_INPUT_FILES=[]  # defaults to this recipe; use separate coarse recipe files for narrower invalidation


def build_blockout(plan,scope):
    raise NotImplementedError('Implement a purpose-selected low-resolution builder; see the separate cube example')
build_blockout.placeholder=True  # Remove this marker when replacing the function implementation.


def refine_geometry(objects,plan,scope):
    raise NotImplementedError('Implement refinement of derived copies; preserve reviewed coarse sources')
refine_geometry.placeholder=True  # Remove this marker when replacing the function implementation.


def mark_owned(data,module_id,phase):
    data[OWNER_KEY]=TASK_ID;data[MODULE_KEY]=module_id;data[PHASE_KEY]=phase;return data


def remove_previous_generated_data(module_ids,phase):
    """Project builders may call this after prerequisites, only for their own scope."""
    if phase not in {'blockout','refine'} or not module_ids:raise ValueError('Explicit phase/module scope required')
    outside={name for module in _load_plan()['modules'] if module['id'] not in module_ids for name in module['objects']}
    candidates=[obj for obj in bpy.context.scene.objects if obj.get(OWNER_KEY)==TASK_ID and obj.get(MODULE_KEY) in module_ids and obj.get(PHASE_KEY)==phase]
    if any(obj.name in outside for obj in candidates):raise RuntimeError('Scoped deletion would remove a shared module object; edit the region or derive a copy')
    if any(any(scene is not bpy.context.scene for scene in obj.users_scene) for obj in candidates):raise RuntimeError('Scoped deletion would affect another scene')
    for obj in candidates:bpy.data.objects.remove(obj,do_unlink=True)
    for mesh in list(bpy.data.meshes):
        if mesh.users==0 and mesh.get(OWNER_KEY)==TASK_ID and mesh.get(MODULE_KEY) in module_ids and mesh.get(PHASE_KEY)==phase:bpy.data.meshes.remove(mesh)


def _objects(modules):
    result=[]
    for module in modules:
        for name in module['objects']:
            obj=bpy.context.scene.objects.get(name)
            if obj is None:raise RuntimeError('Missing bound blockout object: '+name)
            if obj not in result:result.append(obj)
    return result


def _geometry_check(objects,phase,plan):
    from production_checks import require_asset_geometry
    from blockout_gate import resource_limits
    # Include unaffected same-phase modules so local work cannot spend the whole
    # asset allowance once per object/module. Reviewed coarse controls stay excluded.
    rest=[o for o in bpy.context.scene.objects if o.get(OWNER_KEY)==TASK_ID and
          o.get(PHASE_KEY)==phase and o.type in {'MESH','CURVE'} and o not in objects]
    return require_asset_geometry(list(objects)+rest,stage=phase,**resource_limits(plan,phase))


def validate_blockout(objects,plan,scope):
    """Finite geometry and optional world-size constraints; visual inspection stays separate."""
    expected=_objects([m for m in plan['modules'] if m['id'] in scope])
    if not expected or set(objects)!=set(expected):raise RuntimeError('Builder objects do not match scoped module bindings')
    measurements={}
    graph=bpy.context.evaluated_depsgraph_get()
    for module in plan['modules']:
        if module['id'] not in scope:continue
        points=[]
        for obj in _objects([module]):
            if obj.type not in {'MESH','CURVE'}:raise RuntimeError('Default template state supports mesh/curve proxies; implement an equivalent adapter for other representations')
            evaluated=obj.evaluated_get(graph);mesh=evaluated.to_mesh()
            try:points.extend(evaluated.matrix_world@v.co for v in mesh.vertices)
            finally:evaluated.to_mesh_clear()
        if not points or any(not all(math.isfinite(value) for value in point) for point in points):raise RuntimeError('Empty/nonfinite blockout geometry')
        dimensions=[max(point[i] for point in points)-min(point[i] for point in points) for i in range(3)]
        if 'world_dimensions' in module and any(abs(actual-target)>module['dimension_tolerance'] for actual,target in zip(dimensions,module['world_dimensions'])):raise RuntimeError('Blockout dimensions outside declared tolerance: '+module['id'])
        measurements[module['id']]={'world_dimensions':dimensions}
    return {'geometry':_geometry_check(objects,'blockout',plan),'measurements':measurements,'objects':[o.name for o in objects],'stage':'blockout-built','ready_to_refine':False,'ready_to_claim_complete':False}


def validate_result(objects):
    if not objects:raise RuntimeError('No refinement output')
    return {'geometry':_geometry_check(objects,'refine',_load_plan()),'objects':[o.name for o in objects],'stage':'refinement-produced','ready_to_claim_complete':False}


def _state(modules):
    from reference_workspace import model_signature
    bpy.context.view_layer.update()
    return {'geometry':model_signature(_objects(modules)),'frame':bpy.context.scene.frame_current}


def _dependencies(plan):
    from stage_guard import file_input
    result={'reference_preparation':_preparation(),'parameters':BLOCKOUT_PARAMETERS,'recipes':[file_input(p) for p in (BLOCKOUT_INPUT_FILES or [__file__])],
            'helpers':[file_input(Path(REFERENCE_HELPER_DIR)/name) for name in ('blockout_gate.py','stage_guard.py','reference_workspace.py','production_workspace.py','reference_preparation.py','production_checks.py')]}
    for module in plan['modules']:
        if module['id'] in _dependency_scope(plan) and module['method']=='reuse':
            result.setdefault('reuse_sources',[]).append(file_input(Path(MODELING_PLAN).resolve().parent/module['source_snapshot']))
    if BUILD_MODE=='reference':
        from reference_workspace import workspace_signature,require_reference_review
        require_reference_review(bpy.context.scene,TASK_ID,CALIBRATION_REVIEW)
        path=Path(REFERENCE_CONFIG).resolve();config=json.loads(path.read_text())
        result.update(workspace=workspace_signature(bpy.context.scene,TASK_ID),config=file_input(path),calibration=file_input(CALIBRATION_REVIEW),
                      images=[file_input(path.parent/item['image']) for item in config['views'].values()])
        if config.get('multiview_review'):result['design']=file_input(path.parent/config['multiview_review'])
    return result


def _dependency_scope(plan):
    from blockout_gate import select_modules
    return {m['id'] for m in select_modules(plan,MODELING_SCOPE)}


def _prepare_reference():
    _preparation()
    if BUILD_MODE=='reference':
        from reference_workspace import setup_references,require_reference_review
        path=Path(REFERENCE_CONFIG).resolve()
        setup_references(bpy.context.scene,TASK_ID,json.loads(path.read_text()),path.parent)
        require_reference_review(bpy.context.scene,TASK_ID,CALIBRATION_REVIEW)


def build_task(plan):
    if getattr(build_blockout,'placeholder',False):raise NotImplementedError('Replace build_blockout before any scene mutation')
    _activate_scene(create=True)
    _prepare_reference()
    objects=build_blockout(plan,MODELING_SCOPE);bpy.context.view_layer.update()
    return validate_blockout(objects,plan,MODELING_SCOPE)


def refine_task(plan):
    if getattr(refine_geometry,'placeholder',False):raise NotImplementedError('Replace refine_geometry before mutation')
    from blockout_gate import require_blockout_review,select_modules
    require_blockout_review(BLOCKOUT_RECEIPT,plan,MODELING_SCOPE,BLOCKOUT_REVIEW,_state,lambda:_dependencies(plan))
    modules=select_modules(plan,MODELING_SCOPE);before=_state(modules)
    objects=refine_geometry(_objects([m for m in plan['modules'] if m['id'] in MODELING_SCOPE]),plan,MODELING_SCOPE)
    bpy.context.view_layer.update()
    if before!=_state(modules):raise RuntimeError('Reviewed blockout source changed during refinement; use derived copies and renew affected evidence')
    if any(obj in _objects(modules) for obj in objects):raise RuntimeError('Refinement outputs must be derived copies, not reviewed source objects')
    return validate_result(objects)


def _load_plan():
    from blockout_gate import validate_plan
    plan=validate_plan(json.loads(Path(MODELING_PLAN).read_text()))
    if plan['task_id']!=TASK_ID:raise RuntimeError('Plan task identity mismatch')
    return plan


def _preparation():
    from reference_preparation import require_preparation
    images=[]
    if REFERENCE_CONFIG:
        path=Path(REFERENCE_CONFIG).resolve()
        images=[path.parent/item['image'] for item in json.loads(path.read_text())['views'].values()]
    return require_preparation(REFERENCE_PREPARATION,TASK_ID,mode=BUILD_MODE,construction_images=images)


def _activate_scene(create=False):
    from production_workspace import task_scene
    name=SCENE_NAME or ('MODEL_'+TASK_ID if SCENE_MODE=='create' else None)
    if not name:raise ValueError('Edit mode requires SCENE_NAME')
    existing=bpy.data.scenes.get(name)
    if not create and existing is None:raise RuntimeError('Build/reuse the project scene before review/refinement')
    return task_scene(TASK_ID,mode=SCENE_MODE,name=name,existing=existing)


def build_inputs():
    from stage_guard import file_input
    from blockout_gate import select_modules
    plan=_load_plan()
    result={'task_id':TASK_ID,'mode':BUILD_MODE,'reference_preparation':_preparation(),'scene_mode':SCENE_MODE,'scene_name':SCENE_NAME,'waiver':WAIVER_REASON,'plan_context':{k:v for k,v in plan.items() if k!='modules'},
            'modules':select_modules(plan,MODELING_SCOPE),'recipe':file_input(__file__),
            'recipes':[file_input(p) for p in (BLOCKOUT_INPUT_FILES or [__file__])],'parameters':BLOCKOUT_PARAMETERS,
            'geometry_checker':file_input(Path(REFERENCE_HELPER_DIR)/'production_checks.py')}
    if BUILD_MODE=='reference':
        path=Path(REFERENCE_CONFIG).resolve();config=json.loads(path.read_text())
        result.update(config=file_input(path),calibration=file_input(CALIBRATION_REVIEW),
                      images=[file_input(path.parent/item['image']) for item in config['views'].values()])
        if config.get('multiview_review'):result['design']=file_input(path.parent/config['multiview_review'])
    return result


def refinement_inputs():
    from stage_guard import file_input
    from blockout_gate import require_blockout_review
    plan=_load_plan()
    predecessor=require_blockout_review(BLOCKOUT_RECEIPT,plan,MODELING_SCOPE,BLOCKOUT_REVIEW,_state,lambda:_dependencies(plan))
    return {'task_id':TASK_ID,'predecessor_run':predecessor['run_id'],'review_receipt':file_input(BLOCKOUT_RECEIPT),
            'coarse_inputs':build_inputs(),'recipe':file_input(__file__),'parameters':REFINEMENT_PARAMETERS}


def main():
    if TASK_ID=='replace-me' or BUILD_MODE not in {'reference','original','waived'}:raise RuntimeError('Set task identity and explicit reference mode')
    if BUILD_MODE=='waived' and not WAIVER_REASON.strip():raise RuntimeError('Record the actual user reference waiver')
    if not REFERENCE_HELPER_DIR or not MODELING_PLAN:raise RuntimeError('Set installed helper directory and modeling plan')
    if BUILD_MODE=='reference' and not all([REFERENCE_CONFIG,CALIBRATION_REVIEW]):raise RuntimeError('Reference setup and calibration are required')
    sys.path.insert(0,str(Path(REFERENCE_HELPER_DIR).resolve()))
    from blockout_gate import record_blockout_review
    from stage_guard import run_stage
    if EXECUTION_STAGE=='blockout':
        if not BUILD_RECEIPT:raise RuntimeError('Build receipt required')
        result=run_stage(BUILD_RECEIPT,'blockout-build',build_inputs,BUILD_OUTPUTS,
                         lambda:build_task(_load_plan()),lambda result:bool(result['objects']))
    elif EXECUTION_STAGE=='review':
        if not BLOCKOUT_RECEIPT or not BLOCKOUT_REVIEW:raise RuntimeError('Inspection evidence and review receipt required')
        _activate_scene()
        result=record_blockout_review(BLOCKOUT_RECEIPT,_load_plan,MODELING_SCOPE,BLOCKOUT_REVIEW,_state,lambda:_dependencies(_load_plan()))
        result.update(ready_to_refine=True,ready_to_claim_complete=False)
    elif EXECUTION_STAGE=='refine':
        if not REFINEMENT_RECEIPT or not BLOCKOUT_RECEIPT or not BLOCKOUT_REVIEW:raise RuntimeError('Refinement and prerequisite review paths required')
        _activate_scene()
        result=run_stage(REFINEMENT_RECEIPT,'refine',refinement_inputs,REFINEMENT_OUTPUTS,
                         lambda:refine_task(_load_plan()),lambda result:bool(result['objects']))
    else:raise RuntimeError('Choose blockout, review or refine explicitly')
    print(json.dumps(result,ensure_ascii=False));return result

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',choices=['blockout','review','refine'],default=EXECUTION_STAGE)
    arguments=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    EXECUTION_STAGE=arguments.stage
    main()

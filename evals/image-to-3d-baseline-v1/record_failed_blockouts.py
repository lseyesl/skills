"""Record inspected coarse failures, prove refine gate rejects, export diagnostics only."""
import argparse,importlib.util,json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'skills/blender-python-modeling/scripts'))
from blockout_gate import record_blockout_review,require_blockout_review
from reference_workspace import model_signature
from stage_guard import file_input

def main():
    p=argparse.ArgumentParser();p.add_argument('--case',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=a.output.resolve()
    bpy.ops.wm.open_mainfile(filepath=str(out/'coarse.blend'));scene=bpy.context.scene
    plan=json.loads((out/'modeling-plan.json').read_text());objects=[o for o in bpy.data.collections['CoarseSource'].objects if o.type in {'MESH','CURVE'}]
    state=lambda modules:{'geometry':model_signature(objects),'frame':scene.frame_current}
    recipe=Path(__file__).parent/'build_props.py';deps={'recipe':file_input(recipe),'reference':file_input(Path(__file__).parent/'inputs'/a.case/'reference.jpg')}
    finding={'mug':'Inspected blockout.png: lower handle endpoint at x=.398,z=.225 lies outside the tapered cup wall (~x=.322); tube radius .052 leaves a visible gap. The lathe also leaves a small axial hole through the intended bottom. Required connection/cavity-bottom checks fail.',
             'wheel':'Inspected blockout.png: ten branches are present but radial spoke roots start at r=.20 whereas the center cap ends at r=.155, leaving a disconnected radial gap. The photo has continuous cast-metal joins. Required assembly continuity fails.'}[a.case]
    review=json.loads((out/'review-draft.json').read_text());review.update(status='failed',reviewer='current-session-Agent-self-review')
    review['modules'][a.case]={'unresolved_issues':[finding],'checks':{'shape':{'status':'failed','finding':finding,'view':'three-quarter','evidence':[{'path':'blockout.png','sha256':file_input(out/'blockout.png')['sha256']}]}}}
    (out/'blockout-review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
    rejected={}
    for name,fn in [('record',record_blockout_review),('refine-prerequisite',require_blockout_review)]:
        try:fn(out/'blockout-receipt.json',plan,[a.case],out/'blockout-review.json',state,deps)
        except (ValueError,RuntimeError) as e:rejected[name]=str(e)
        else:raise RuntimeError('Failed blockout accepted')
    (out/'gate-result.json').write_text(json.dumps({'refinement_executed':False,'rejected':rejected,'finding':finding},ensure_ascii=False,indent=2)+'\n')
    spec=importlib.util.spec_from_file_location('case_recipe',recipe);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.CASE=a.case
    for view in ['front','side','back','three-quarter']:module.render(scene,out/(view+'.png'),view)
    module.render(scene,out/'clay.png','three-quarter',True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'diagnostic-asset.blend'))
    for ob in bpy.context.view_layer.objects:ob.select_set(False)
    for ob in bpy.data.collections['CoarseSource'].objects:ob.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.export_scene.gltf(filepath=str(out/'diagnostic-asset.glb'),export_format='GLB',use_selection=True,export_animations=True)

if __name__=='__main__':main()

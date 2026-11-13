"""Diagnostic salvage of a failed first run; does not change the frozen Skill.
Retains the first failure, disables unavailable denoising only for diagnostic renders.
No armature or artistic geometry is added to improve a baseline score.
"""
import argparse,json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'skills/blender-python-modeling/scripts'))
import reference_fit.blender_validation as validation

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(a.input.resolve()/'scene.blend'));scene=bpy.context.scene
    config=json.loads((a.input/'config.json').read_text())
    # The original explicitly turns denoising back on for clay. Preserve and log
    # a diagnostic-only execution adapter instead of editing Skill source.
    source=Path(validation.__file__).read_text()
    needle="scene.cycles.use_denoising=channel=='clay'"
    if source.count(needle)!=1:raise RuntimeError('Unexpected original denoise implementation')
    namespace=dict(validation.__dict__)
    exec(compile(source.replace(needle,'scene.cycles.use_denoising=False'),str(Path(__file__).resolve())+'::diagnostic-adapter','exec'),namespace)
    scene.cycles.use_denoising=False
    namespace['render_channels'](scene,config,out)
    for ob in bpy.context.view_layer.objects:ob.select_set(False)
    meshes=[ob for ob in scene.objects if ob.type=='MESH' and ob.get('reference_fit_owner')==config['character_id']]
    for ob in meshes:ob.select_set(True)
    bpy.context.view_layer.objects.active=meshes[0]
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'asset.blend'))
    bpy.ops.export_scene.gltf(filepath=str(out/'asset.glb'),export_format='GLB',use_selection=True)
    (out/'salvage.json').write_text(json.dumps({'status':'diagnostic-only','original_attempt':'../character','original_failure':'OpenImageDenoise unavailable','adapter':'disable beauty and clay denoising only; original source unchanged','not_a_successful_original_run':True,'armatures':[ob.name for ob in scene.objects if ob.type=='ARMATURE']},indent=2)+'\n')

if __name__=='__main__':main()

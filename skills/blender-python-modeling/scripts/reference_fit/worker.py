"""Blender-only worker launched by the host CLI in a disposable process."""
from pathlib import Path
import sys,argparse,json,re
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from reference_fit.config import load,digest,check_runtime
from reference_fit.blender_builder import build,fingerprints,OWNER
from reference_fit.blender_validation import workspace,setup,render_channels,structure,rig_probe


def main():
    check_runtime(bpy.app.version)
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True)
    p.add_argument('--source');p.add_argument('--only',default='');p.add_argument('--legacy',action='store_true');p.add_argument('--quick',action='store_true');p.add_argument('--rig-test',action='store_true');p.add_argument('--render-only',action='store_true')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);c,base=load(args.config);folder=Path(args.output).resolve()
    if (folder/'scene.blend').exists():raise FileExistsError('Refuse overwrite: '+str(folder))
    folder.mkdir(parents=True,exist_ok=True);owner=c['character_id'];before={};unchanged=[]
    if args.source:
        bpy.ops.wm.open_mainfile(filepath=str(Path(args.source).resolve()))
        scene=bpy.context.scene
        if not args.legacy and scene.get(OWNER)!=owner:raise RuntimeError('Source is not a scene owned by this fitter/character')
        if args.render_only:
            saved=json.loads(scene['fit_config'])
            if digest(saved['shape'])!=digest(c['shape']) or digest(saved['materials'])!=digest(c['materials']):
                raise ValueError('Render-only source does not match requested shape/material config')
        if args.legacy:
            rules=c['reference']['legacy_labels']
            for ob in list(scene.objects):
                if ob.type in ['LIGHT','CAMERA']:ob.hide_render=True
                if ob.type=='MESH':
                    label=next((r['component'] for r in rules if re.search(r['pattern'],ob.name)),None)
                    if label is None:ob.hide_render=True;continue
                    ob[OWNER]=owner;ob['fit_component']=label;ob['fit_stable_id']=ob.name
            workspace(scene,c,base)
        elif not args.render_only:
            before=fingerprints(scene,owner)
            scene,affected=build(c,scene,only=args.only.split(',') if args.only else None)
            after=fingerprints(scene,owner)
            unchanged=[k for k in before if k in after and not any('::'+part+'::' in k for part in affected)]
            if any(before[k]!=after[k] for k in unchanged):raise RuntimeError('Unrelated/locked geometry or material changed')
    else:
        # Create a separate scene; leave factory/user scene datablocks intact.
        scene=bpy.data.scenes.new('Fit_'+owner);bpy.context.window.scene=scene
        workspace(scene,c,base) # mandatory reference workspace precedes geometry
        bpy.ops.wm.save_as_mainfile(filepath=str(folder/'reference-workspace.blend'))
        scene,affected=build(c,scene)
    if args.source and not args.legacy:workspace(scene,c,base)
    setup(scene,c)
    # Label groups may aggregate face parts/ears into the visible head region.
    for ob in scene.objects:
        if ob.get(OWNER)==owner and ob.type=='MESH':
            ob['fit_label']=c['shape'].get(ob['fit_component'],{}).get('label',ob['fit_component'])
    qa=structure(scene,c) if not args.legacy else {'ok':True,'scope':'Original v5 preserved, topology not re-certified by new builder','errors':[]}
    if args.rig_test and not args.legacy:
        qa['rig_probe']=rig_probe(scene,c)
        if not qa['rig_probe']['ok']:qa['errors'].append('Rig probe failed');qa['ok']=False
    qa['unchanged_object_count']=len(unchanged);qa['config_hash']=digest(c)
    (folder/'structure.json').write_text(json.dumps(qa,indent=2))
    (folder/'config.json').write_text(json.dumps(c,indent=2))
    (folder/'fingerprints.json').write_text(json.dumps(fingerprints(scene,owner),indent=2))
    # Saved file contains original materials and fixed setup, not temporary mask shaders.
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'scene.blend'))
    render_channels(scene,c,folder,quick=args.quick)
    (folder/'worker-result.json').write_text(json.dumps({'ok':qa['ok'],'structure':'structure.json','scene':'scene.blend'}))
    print('REFERENCE_FIT_WORKER_DONE',str(folder),flush=True)

if __name__=='__main__':main()

#!/usr/bin/env python3
"""Host entry: reference analysis -> owned model -> measured local refinement."""
from pathlib import Path
import argparse,json,subprocess,sys,shutil,hashlib
from reference_fit.config import load,validate
from reference_fit.evaluation import evaluate,read,annotations,reference_masks,sampled_colors
from reference_fit.refiner import optimize,defects
from reference_fit.process import run_logged

SCRIPT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['analyze','build','baseline','render','evaluate','optimize'])
    parser.add_argument('--config',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--blender',default='/Applications/Blender.app/Contents/MacOS/Blender')
    parser.add_argument('--source',type=Path);parser.add_argument('--iterations',type=int);parser.add_argument('--rig-test',action='store_true');parser.add_argument('--timeout',type=int,default=600)
    args=parser.parse_args();c,base=load(args.config)
    # Resolve only data paths, preserving the caller's independent character source.
    for key in ['image','annotation']:
        p=(base/c['reference'][key]).resolve()
        if not p.is_file():raise FileNotFoundError(p)
        c['reference'][key]=str(p)
    for item in c['reference'].get('views',{}).values():item['image']=str((base/item['image']).resolve())
    if args.iterations is not None:c['validation']['max_iterations']=args.iterations;validate(c)
    out=args.output.resolve()
    if args.command not in ['evaluate'] and out.exists() and any(out.iterdir()):raise FileExistsError('Choose empty output directory: '+str(out))
    out.mkdir(parents=True,exist_ok=True)
    source_hash=hashlib.sha256(args.source.read_bytes()).hexdigest() if args.source else None
    def measure(folder):
        m=evaluate(c['reference']['image'],c['reference']['annotation'],folder,folder/'evaluation',c['validation'].get('alignment','none'))
        (folder/'refinement_plan.json').write_text(json.dumps(defects(m,c),indent=2));return m
    def worker(config,folder,source=None,only=None,legacy=False,quick=False,render_only=False):
        folder.mkdir(parents=True,exist_ok=True);cfg=folder/'input-config.json';cfg.write_text(json.dumps(config,indent=2))
        cmd=[args.blender,'--background','--factory-startup','-t','4','--python-exit-code','1','--python',str(SCRIPT/'reference_fit/worker.py'),'--','--config',str(cfg),'--output',str(folder)]
        if source:cmd+=['--source',str(source)]
        if only:cmd+=['--only',','.join(only)]
        if legacy:cmd+=['--legacy']
        if quick:cmd+=['--quick']
        if render_only:cmd+=['--render-only']
        if args.rig_test:cmd+=['--rig-test']
        run_logged(cmd,folder/'blender.log',args.timeout)
        if not (folder/'worker-result.json').is_file():raise RuntimeError('Blender produced no completion record')
        return json.loads((folder/'structure.json').read_text())
    if args.command=='analyze':
        import cv2
        image=read(c['reference']['image']);a=annotations(c['reference']['annotation'],image)
        fg,parts,evidence=reference_masks(image,a,Path(c['reference']['annotation']).parent)
        cv2.imwrite(str(out/'silhouette.png'),fg)
        for name,mask in parts.items():cv2.imwrite(str(out/(name+'.png')),mask)
        (out/'analysis.json').write_text(json.dumps({'components':evidence,'assumptions':c.get('assumptions',[])},indent=2))
        (out/'sampled-colors.json').write_text(json.dumps(sampled_colors(image,parts),indent=2))
    elif args.command=='evaluate':measure(out)
    elif args.command in ['build','baseline','render']:
        if args.command in ['baseline','render'] and not args.source:raise ValueError('This command needs --source existing blend')
        qa=worker(c,out,args.source,legacy=args.command=='baseline',render_only=args.command=='render')
        if not qa['ok']:raise RuntimeError('Initial structural checks failed; see '+str(out/'structure.json'))
        measure(out)
    else:
        initial=out/'initial';qa=worker(c,initial,args.source,render_only=bool(args.source))
        if not qa['ok']:raise RuntimeError('Initial structural checks failed; refinement not started: '+str(initial/'structure.json'))
        m=measure(initial)
        def run(proposed,source,affected,folder):
            qa=worker(proposed,folder,source,affected,quick=True)
            return measure(folder),qa['ok']
        result=optimize(c,m,initial/'scene.blend',out/'iterations',run)
        final=out/'final';qa=worker(result['config'],final,Path(result['scene']),quick=False,render_only=True)
        if not qa['ok']:raise RuntimeError('Final structural checks failed: '+str(final/'structure.json'))
        measure(final)
        (out/'result.json').write_text(json.dumps({'final_scene':str(final/'scene.blend'),'optimization':'iterations/optimization.json','stop_reason':result['stop_reason'],'accepted_iterations':result['accepted_iterations']},indent=2))
    if args.source:
        if hashlib.sha256(args.source.read_bytes()).hexdigest()!=source_hash:raise RuntimeError('Source file changed unexpectedly')
        (out/'source-preservation.json').write_text(json.dumps({'source':str(args.source.resolve()),'sha256':source_hash,'unchanged':True},indent=2))
    print(json.dumps({'ok':True,'command':args.command,'output':str(out)}))

if __name__=='__main__':main()

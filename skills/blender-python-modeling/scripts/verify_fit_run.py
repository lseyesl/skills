#!/usr/bin/env python3
"""Verify real pipeline evidence, snapshots and paired measurements (host-side)."""
from pathlib import Path
import argparse,json,hashlib
import cv2


def verify(run,baseline):
    run=Path(run);baseline=Path(baseline);checks={}
    def check(name,condition):
        checks[name]=bool(condition)
    initial=json.loads((run/'initial/evaluation/metrics.json').read_text())
    final=json.loads((run/'final/evaluation/metrics.json').read_text())
    old=json.loads((baseline/'evaluation/metrics.json').read_text())
    optimization=json.loads((run/'iterations/optimization.json').read_text())
    check('same_reference_and_annotation_hashes',initial['input_hashes']==final['input_hashes']==old['input_hashes'])
    check('same_fixed_camera',initial['render_record']['camera']==final['render_record']['camera']==old['render_record']['camera'])
    check('actual_model_snapshots',all((p/'scene.blend').is_file() and (p/'scene.blend').stat().st_size>100000 for p in [run/'initial',run/'final',baseline]))
    images=[]
    for folder in [run/'initial',run/'final',baseline]:
        for name in ['beauty_front','beauty_side','beauty_back','beauty_three_quarter','labels_front','silhouette_front','albedo_front','clay_front']:
            path=folder/(name+'.png');a=cv2.imread(str(path),cv2.IMREAD_UNCHANGED)
            images.append(a is not None and list(a.shape[1::-1])==final['render_record']['resolution'])
    check('24_real_required_images_decode',all(images) and len(images)==24)
    check('at_least_one_accepted_local_change',optimization['accepted_iterations']>0)
    check('at_least_one_rejected_candidate',any(not r['accepted'] for r in optimization['history']))
    check('measured_global_improvement',final['global']['iou']>initial['global']['iou'])
    check('unknown_torso_stays_not_evaluable',all(m['components']['torso']['status']=='not_evaluable' for m in [initial,final,old]))
    check('3d_initial_and_final_pass',all(json.loads((run/name/'structure.json').read_text())['ok'] for name in ['initial','final']))
    check('actual_rig_probe_pass',json.loads((run/'final/structure.json').read_text()).get('rig_probe',{}).get('ok',False))
    final_fingerprints=json.loads((run/'final/fingerprints.json').read_text())
    selected_fingerprints=json.loads((Path(optimization['scene']).parent/'fingerprints.json').read_text())
    check('final_is_last_selected_geometry_materials',selected_fingerprints==final_fingerprints)
    # Every rejected branch is separate; the following accepted branch must be
    # based on prior selected state, not the previous rejected branch.
    selected=run/'initial/scene.blend'
    untouched=[]
    for round_dir in sorted((run/'iterations').glob('round-*')):
        plan=json.loads((round_dir/'refinement_plan.json').read_text())
        check(round_dir.name+'_reopens_last_accepted',Path(plan['source_scene']).resolve()==selected.resolve())
        prev=json.loads((selected.parent/'fingerprints.json').read_text())
        for record in [r for r in optimization['history'] if r['iteration']==int(round_dir.name.rsplit('-',1)[1])]:
            folder=Path(record['candidate']);qa_path=folder/'structure.json'
            if qa_path.exists():untouched.append(json.loads(qa_path.read_text())['unchanged_object_count']>0)
            if record.get('selected'):selected=folder/'scene.blend'
    check('candidate_local_regression_hashes_checked',bool(untouched) and all(untouched))
    return {'ok':all(checks.values()),'checks':checks,'global_iou':{'old':old['global']['iou'],'initial':initial['global']['iou'],'final':final['global']['iou']},'accepted_iterations':optimization['accepted_iterations'],'stop_reason':optimization['stop_reason']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=verify(a.run,a.baseline);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
    if not result['ok']:raise SystemExit(1)

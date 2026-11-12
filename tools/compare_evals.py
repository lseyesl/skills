"""Conservative paired task-run comparison; never an automatic release approval."""
import argparse
import json
import math
from run_evals import read


def compare(base,head,min_pairs=10):
    if min_pairs < 2: raise ValueError('At least two pairs required')
    for run in (base,head):
        if run.get('kind')!='tasks' or not run.get('evidence_validated'): raise ValueError('Use validated task reports')
    if base['suite_sha256']!=head['suite_sha256']: raise ValueError('Suite/rubric changed; not comparable')
    for field in ('model','environment','budget','rubric_version'):
        if base['metadata'][field]!=head['metadata'][field]: raise ValueError('Confounded comparison: '+field)
    def records(run):
        result={}
        for r in run['records']:
            key=(r['task_id'],r['repeat'])
            if key in result: raise ValueError('Duplicate pair')
            result[key]=r
        return result
    a,b=records(base),records(head)
    if set(a)!=set(b) or base.get('missing_tasks') or head.get('missing_tasks'):
        return {'verdict':'insufficient-evidence','reason':'missing task/repeat pairs'}
    if any(r['status'] not in {'passed','failed'} for r in [*a.values(),*b.values()]):
        return {'verdict':'insufficient-evidence','reason':'unverified/skipped runs'}
    gains=[];losses=[];severe=[];check_regressions=[]
    for key in a:
        old_checks=a[key].get('checks', {}); new_checks=b[key].get('checks', {})
        if set(old_checks)!=set(new_checks): raise ValueError('Check contract changed inside task records')
        check_regressions.extend({'task_id':key[0], 'repeat':key[1], 'check':c} for c in old_checks if old_checks[c]['status']=='passed' and new_checks[c]['status']=='failed')
        if b[key]['severe_error'] and not a[key]['severe_error']: severe.append(key)
        if a[key]['status']=='passed' and b[key]['status']=='failed':losses.append(key)
        if a[key]['status']=='failed' and b[key]['status']=='passed':gains.append(key)
    n=len(a);delta=(len(gains)-len(losses))/n if n else 0
    # Hoeffding bound for bounded paired differences [-1,1]; intentionally conservative.
    # Repeated runs for one task are correlated: bound across task means, not raw repeats.
    task_ids={key[0] for key in a}
    task_deltas=[]
    for task_id in task_ids:
        keys=[k for k in a if k[0]==task_id]
        task_deltas.append(sum(int(b[k]['status']=='passed')-int(a[k]['status']=='passed') for k in keys)/len(keys))
    delta=sum(task_deltas)/len(task_deltas) if task_deltas else 0
    radius=math.sqrt(2*math.log(40)/len(task_deltas)) if task_deltas else 1
    if severe: verdict='negative'
    elif check_regressions and not gains: verdict='negative'
    elif (losses or check_regressions) and gains: verdict='conditional-tradeoff'
    elif len(task_deltas)<min_pairs or radius>=abs(delta): verdict='insufficient-evidence'
    elif delta>0: verdict='positive'
    else: verdict='negative'
    costs={field:sum(b[k][field]-a[k][field] for k in a)/n if n else None for field in ('elapsed_seconds','context_tokens','human_interventions')}
    return {'verdict':verdict,'pairs':n,'distinct_tasks':len(task_deltas),'gains':gains,'regressions':losses,'check_regressions':check_regressions,'new_severe_errors':severe,
            'success_delta':delta,'conservative_95_interval':[max(-1,delta-radius),min(1,delta+radius)],
            'mean_cost_delta':costs,'scope':'success-rate target only; cost-target optimization requires its own declared analysis; no automatic approval'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('base');p.add_argument('head');p.add_argument('--output',required=True)
    a=p.parse_args();report=compare(read(a.base),read(a.head))
    from pathlib import Path
    Path(a.output).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(report['verdict'])

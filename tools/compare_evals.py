"""Conservative paired task-run comparison; never an automatic release approval."""
import argparse
import json
import math
import hashlib
from run_evals import read


def compare(base,head,min_pairs=10,policy=None):
    if min_pairs < 2: raise ValueError('At least two pairs required')
    for run in (base,head):
        if run.get('kind')!='tasks' or not run.get('evidence_validated'): raise ValueError('Use validated task reports')
    if base['suite_sha256']!=head['suite_sha256']: raise ValueError('Suite/rubric changed; not comparable')
    for field in ('model','environment','budget','rubric_version'):
        if base['metadata'][field]!=head['metadata'][field]: raise ValueError('Confounded comparison: '+field)
    if policy is not None:
        if not base['metadata'].get('source_sha256') or base['metadata'].get('source_sha256') != head['metadata'].get('source_sha256'):
            return {'verdict':'insufficient-evidence','reason':'Missing/different initial asset fingerprints'}
        validate_policy(policy)
        expected_policy = hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest()
        if any(r['metadata'].get('comparison_policy_sha256') != expected_policy for r in (base, head)):
            return {'verdict':'insufficient-evidence','reason':'Policy was not bound to both runs before execution'}
    if any('unobserved' in r['metadata']['model'] for r in (base,head)):
        return {'verdict':'insufficient-evidence','reason':'Actual model identity was not observed'}
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
    candidate_verdict = verdict
    policy_result = evaluate_policy(policy, a, b, radius, verdict)
    verdict = policy_result['verdict']
    return {'verdict':verdict,'success_rate_suggestion':candidate_verdict,'policy_result':policy_result,'pairs':n,'distinct_tasks':len(task_deltas),'gains':gains,'regressions':losses,'check_regressions':check_regressions,'new_severe_errors':severe,
            'success_delta':delta,'conservative_95_interval':[max(-1,delta-radius),min(1,delta+radius)],
            'mean_cost_delta':costs,'scope':'Declared objective and constraints only; statistical assumptions and release review still apply'}

COSTS = ('elapsed_seconds', 'context_tokens', 'human_interventions')


def validate_policy(policy):
    if not isinstance(policy, dict) or policy.get('schema_version') != 1:
        raise ValueError('Policy requires schema_version=1')
    minimum = policy.get('minimum_distinct_tasks', 10)
    if type(minimum) is not int or minimum < 2: raise ValueError('minimum_distinct_tasks must be at least two')
    objective = policy.get('objective', {})
    if objective.get('metric') not in ('success_rate', *COSTS): raise ValueError('Unknown objective metric')
    improvement = objective.get('min_improvement')
    if type(improvement) not in (int, float) or not math.isfinite(improvement) or improvement < 0:
        raise ValueError('Objective needs nonnegative min_improvement')
    for name in ('max_mean_increase', 'max_per_run'):
        limits = policy.get(name)
        if not isinstance(limits, dict) or set(limits) != set(COSTS):
            raise ValueError('Explicit limits required for all costs: ' + name)
        if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in limits.values()):
            raise ValueError('Cost limits must be finite and nonnegative')
    checks = policy.get('protected_checks')
    if not isinstance(checks, list) or any(not isinstance(c, str) or not c for c in checks):
        raise ValueError('protected_checks must be a list of check IDs')
    return policy


def evaluate_policy(policy, base, head, radius, suggestion):
    if policy is None:
        return {'verdict': suggestion if suggestion in {'negative', 'conditional-tradeoff'} else 'insufficient-evidence',
                'reason': 'No predeclared objective/cost limits; cannot certify a positive change'}
    validate_policy(policy)
    policy_hash = hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest()
    violations = []
    for metric in COSTS:
        if any(r[metric] > policy['max_per_run'][metric] for r in head.values()): violations.append('per-run:' + metric)
        mean_increase = sum(head[k][metric] - base[k][metric] for k in base)/max(1,len(base))
        if mean_increase > policy['max_mean_increase'][metric]: violations.append('mean-increase:' + metric)
    for key in base:
        for ident in policy['protected_checks']:
            before = base[key].get('checks', {}).get(ident, {}).get('status')
            after = head[key].get('checks', {}).get(ident, {}).get('status')
            if before is None or after is None or before not in {'passed','failed'} or after not in {'passed','failed'}:
                return {'verdict':'insufficient-evidence','reason':'Missing/unverified protected check: ' + ident,'policy_sha256':policy_hash}
            if before == 'passed' and after != 'passed': violations.append('protected-check:' + ident)
    if violations:
        return {'verdict':'negative','violations':sorted(set(violations)),'policy_sha256':policy_hash}
    if suggestion == 'negative': return {'verdict':'negative','reason':'Observed task/check regression','policy_sha256':policy_hash}
    if suggestion == 'conditional-tradeoff': return {'verdict':suggestion,'policy_sha256':policy_hash}
    metric = policy['objective']['metric']
    deltas = []
    for task in {k[0] for k in base}:
        keys = [k for k in base if k[0] == task]
        if metric == 'success_rate':
            values = [int(head[k]['status']=='passed')-int(base[k]['status']=='passed') for k in keys]
        else: values = [base[k][metric]-head[k][metric] for k in keys]
        deltas.append(sum(values)/len(values))
    gain = sum(deltas)/max(1,len(deltas))
    scale = 1 if metric == 'success_rate' else policy['max_per_run'][metric]
    if metric != 'success_rate' and any(r[metric] > scale for r in base.values()):
        return {'verdict':'insufficient-evidence','reason':'Baseline exceeds declared metric bound','policy_sha256':policy_hash}
    lower = gain-radius*scale
    enough = len(deltas) >= policy.get('minimum_distinct_tasks',10)
    verdict = 'positive' if enough and lower > policy['objective']['min_improvement'] else 'insufficient-evidence'
    return {'verdict':verdict,'objective_gain':gain,'conservative_lower_bound':lower,'policy_sha256':policy_hash}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('base');p.add_argument('head');p.add_argument('--output',required=True);p.add_argument('--policy',help='Predeclared objective and limits JSON')
    a=p.parse_args();report=compare(read(a.base),read(a.head),policy=read(a.policy) if a.policy else None)
    from pathlib import Path
    Path(a.output).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(report['verdict'])

"""Run deterministic retrieval evals or validate evidence from independent task runs.
Task records are produced by an external Agent/operator, never synthesized here.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from knowledge import load_catalog, search

STATUSES = {'passed','failed','skipped','unknown'}


def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_suite(suite):
    if suite.get('schema_version') != 1 or not isinstance(suite.get('tasks'), list) or not suite['tasks']:
        raise ValueError('Invalid task suite')
    ids=set()
    for task in suite['tasks']:
        if not isinstance(task.get('id'),str) or task['id'] in ids: raise ValueError('Duplicate/missing task ID')
        ids.add(task['id'])
        if not task.get('prompt') or task.get('split') not in {'dev','test'}: raise ValueError('Missing prompt/split')
        checks=task.get('checks',[])
        if not checks or len({c['id'] for c in checks}) != len(checks): raise ValueError('Empty/duplicate checks')
        for check in checks:
            if check.get('kind') not in {'structure','behavior','visual'} or type(check.get('required')) is not bool or not check.get('criterion'):
                raise ValueError('Invalid check contract')
    return suite


def validate_run(suite, run, evidence_root):
    validate_suite(suite)
    tasks={t['id']:t for t in suite['tasks']}
    if run.get('schema_version') != 1 or not isinstance(run.get('records'),list) or not run['records']:
        raise ValueError('Invalid/empty run')
    metadata=run.get('metadata',{})
    for field in ('revision','model','environment','budget','rubric_version'):
        if not metadata.get(field): raise ValueError('Missing run metadata: '+field)
    root=Path(evidence_root).resolve(); seen=set()
    for record in run['records']:
        task=tasks.get(record.get('task_id')); repeat=record.get('repeat')
        if task is None or type(repeat) is not int or repeat < 1: raise ValueError('Unknown task/invalid repeat')
        key=(task['id'],repeat)
        if key in seen: raise ValueError('Duplicate task/repeat')
        seen.add(key)
        if record.get('status') not in STATUSES or type(record.get('severe_error')) is not bool: raise ValueError('Invalid status/severity')
        for field in ('elapsed_seconds','context_tokens','human_interventions'):
            v=record.get(field)
            if type(v) not in (int,float) or not math.isfinite(v) or v<0: raise ValueError('Invalid measured cost: '+field)
        expected={c['id']:c for c in task['checks']}; actual=record.get('checks')
        if not isinstance(actual,dict) or set(actual)!=set(expected): raise ValueError('Checks must exactly match task contract')
        required=[]
        for ident, check in actual.items():
            if check.get('status') not in STATUSES: raise ValueError('Invalid check status')
            if check['status'] in {'skipped','unknown'} and not check.get('reason'): raise ValueError('Missing unverified reason')
            if expected[ident]['required']: required.append(check['status'])
            if check['status']=='passed':
                evidence=check.get('evidence',[])
                if not evidence: raise ValueError('Passed check needs evidence')
                for ref in evidence:
                    p=(root/ref['path']).resolve()
                    if not p.is_relative_to(root) or not p.is_file() or digest(p)!=ref['sha256']:
                        raise ValueError('Missing/escaping/stale evidence')
                if expected[ident]['kind']=='visual' and not check.get('reviewer'):
                    raise ValueError('Visual check needs identified reviewer')
        if record['status']=='passed' and (any(s!='passed' for s in required) or record['severe_error']):
            raise ValueError('False pass: required checks incomplete or severe error')
        if ('failed' in required or record['severe_error']) and record['status']!='failed':
            raise ValueError('Failed required check/severe error must fail the task')
    return run


def retrieval(root, split='test'):
    data=read(root/'evals/retrieval/queries.json'); entries=load_catalog(root/'skills'); results=[]
    for case in data['queries']:
        if case['split']!=split: continue
        found=search(entries,case['query'],case.get('task'),case.get('subject'),case.get('facts'),5)
        ids=[e['id'] for e in found]; expected=case['expected']
        if not set(expected)<=entries.keys(): raise ValueError('Unknown expected knowledge ID')
        passed=bool(set(expected)&set(ids)) if expected else not ids
        passed=passed and not bool(set(case.get('forbidden',[]))&set(ids))
        results.append({'id':case['id'],'passed':passed,'expected':expected,'returned':ids})
    if not results: raise ValueError('No retrieval cases for split')
    answerable=[r for r in results if r['expected']]
    rejected=[r for r in results if not r['expected']]
    metrics={'hit_at_1':sum(bool(r['returned']) and r['returned'][0] in r['expected'] for r in answerable)/len(answerable) if answerable else None,
             'hit_at_5':sum(bool(set(r['expected']) & set(r['returned'])) for r in answerable)/len(answerable) if answerable else None,
             'correct_rejection_rate':sum(not r['returned'] for r in rejected)/len(rejected) if rejected else None}
    return {'kind':'retrieval','split':split,'passed':all(r['passed'] for r in results),'metrics':metrics,'cases':results}


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='action',required=True)
    r=sub.add_parser('retrieval');r.add_argument('--split',choices=['dev','test'],default='test');r.add_argument('--output',type=Path,required=True)
    t=sub.add_parser('tasks');t.add_argument('--suite',type=Path,required=True);t.add_argument('--records',type=Path,required=True);t.add_argument('--evidence-root',type=Path,required=True);t.add_argument('--output',type=Path,required=True)
    args=p.parse_args();root=Path(__file__).resolve().parents[1]
    if args.action=='retrieval': report=retrieval(root,args.split)
    else:
        suite=read(args.suite);run=validate_run(suite,read(args.records),args.evidence_root)
        report={**run,'kind':'tasks','suite_sha256':digest(args.suite),'evidence_validated':True,
                'missing_tasks':sorted({t['id'] for t in suite['tasks']}-{r['task_id'] for r in run['records']})}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(args.output),'kind':report['kind']},ensure_ascii=False))
    if report['kind']=='retrieval' and not report['passed']: raise SystemExit(1)
if __name__=='__main__': main()

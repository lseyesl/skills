"""Scoped blockout review gates built on stage_guard; never an image-quality judge."""
import json
import math
from pathlib import Path
from stage_guard import file_input,fingerprint,run_stage,require_stage

METHODS={'primitives','box','surface','curve','sculpt','reuse'}
CHECK_KINDS={'structural','visual','functional'}


def validate_plan(plan):
    plan=plan() if callable(plan) else plan
    if plan.get('schema_version')!=1 or not isinstance(plan.get('task_id'),str) or not plan['task_id'].strip():raise ValueError('Plan needs schema_version=1 and task_id')
    modules=plan.get('modules')
    if not isinstance(modules,list) or not modules:raise ValueError('Plan requires modules')
    ids=set()
    for module in modules:
        ident=module.get('id')
        if not isinstance(ident,str) or not ident.strip() or ident in ids:raise ValueError('Missing/duplicate module ID')
        ids.add(ident)
        if module.get('method') not in METHODS or not isinstance(module.get('reason'),str) or not module['reason'].strip():raise ValueError('Explicit method and reason required: '+ident)
        names=module.get('objects')
        if not isinstance(names,list) or not names or any(not isinstance(n,str) or not n.strip() for n in names) or len(set(names))!=len(names):raise ValueError('Explicit unique object bindings required: '+ident)
        dependencies=module.get('depends_on',[])
        if not isinstance(dependencies,list) or any(not isinstance(n,str) for n in dependencies):raise ValueError('Invalid module dependencies')
        checks=module.get('checks')
        if not isinstance(checks,list) or not checks:raise ValueError('Explicit acceptance checks required: '+ident)
        check_ids=set()
        for check in checks:
            if not isinstance(check.get('id'),str) or not check['id'].strip() or check['id'] in check_ids:raise ValueError('Missing/duplicate check ID')
            check_ids.add(check['id'])
            if check.get('kind') not in CHECK_KINDS or not isinstance(check.get('criterion'),str) or not check['criterion'].strip():raise ValueError('Check kind and criterion required')
        if not any(c['kind']=='visual' for c in checks):raise ValueError('A blockout needs actual visual inspection: '+ident)
        if 'world_dimensions' in module:
            dimensions=module['world_dimensions'];tolerance=module.get('dimension_tolerance')
            if not isinstance(dimensions,list) or len(dimensions)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in dimensions):raise ValueError('Invalid expected world dimensions')
            if type(tolerance) not in (int,float) or not math.isfinite(tolerance) or tolerance<0:raise ValueError('Explicit nonnegative dimension tolerance required')
        if module['method']=='reuse' and not module.get('source_snapshot'):raise ValueError('Reuse requires a preserved source snapshot')
    for module in modules:
        if set(module.get('depends_on',[]))-ids or module['id'] in module.get('depends_on',[]):raise ValueError('Unknown/self module dependency')
    return plan


def select_modules(plan,scope):
    plan=validate_plan(plan)
    if not isinstance(scope,(list,tuple)) or not scope or len(set(scope))!=len(scope):raise ValueError('Explicit unique scope required')
    modules={m['id']:m for m in plan['modules']}
    if set(scope)-modules.keys():raise ValueError('Unknown scope')
    selected=set(scope);pending=list(scope)
    while pending:
        for dep in modules[pending.pop()].get('depends_on',[]):
            if dep not in selected:selected.add(dep);pending.append(dep)
    return [modules[key] for key in sorted(selected)]


def _review_inputs(plan,scope,review,state,dependencies):
    plan=validate_plan(plan)
    modules=select_modules(plan,scope)
    current=state(modules)
    if not isinstance(current,dict) or not current:raise ValueError('Actual nonempty blockout state required')
    return {'task_id':plan['task_id'],'plan_context':{k:v for k,v in plan.items() if k!='modules'},'scope':sorted(scope),'modules':modules,'state':current,
            'review':file_input(review),'gate':file_input(__file__),
            'dependencies':dependencies() if callable(dependencies) else dependencies or {}}


def review_signature(plan,scope,state,dependencies=None):
    plan=validate_plan(plan)
    modules=select_modules(plan,scope)
    return fingerprint({'task_id':plan['task_id'],'plan_context':{k:v for k,v in plan.items() if k!='modules'},'scope':sorted(scope),'modules':modules,
                        'state':state(modules),'gate':file_input(__file__),'dependencies':dependencies() if callable(dependencies) else dependencies or {}})


def _check_review(plan,scope,review,expected_signature):
    plan=validate_plan(plan)
    review=Path(review).resolve();data=json.loads(review.read_text())
    if data.get('schema_version')!=1 or data.get('task_id')!=plan['task_id'] or data.get('status')!='passed':raise ValueError('Review identity/status did not pass')
    if not isinstance(data.get('reviewer'),str) or not data['reviewer'].strip():raise ValueError('Identified reviewer required')
    if set(data.get('modules',{}))!=set(scope):raise ValueError('Review scope must match requested modules exactly')
    if data.get('inspection_signature')!=expected_signature:raise RuntimeError('Review was not made for the current blockout/plan/context; inspect again before recording')
    artifacts=[];modules={m['id']:m for m in plan['modules']}
    for ident in scope:
        result=data['modules'][ident]
        if result.get('unresolved_issues')!=[]:raise ValueError('Unresolved/undeclared issues: '+ident)
        expected={c['id']:c for c in modules[ident]['checks']};actual=result.get('checks',{})
        if set(actual)!=set(expected):raise ValueError('Missing/extra required checks: '+ident)
        for key,check in actual.items():
            if check.get('status')!='passed' or not isinstance(check.get('finding'),str) or not check['finding'].strip():raise ValueError('Unreviewed/failed check: '+key)
            if expected[key]['kind']=='visual' and not check.get('view'):raise ValueError('Visual check needs view identification')
            evidence=check.get('evidence')
            if not isinstance(evidence,list) or not evidence:raise ValueError('Actual evidence required: '+key)
            for ref in evidence:
                path=(review.parent/ref['path']).resolve()
                if not path.is_relative_to(review.parent):raise ValueError('Evidence must stay within review artifact root')
                artifact=file_input(path)
                if artifact['sha256']!=ref.get('sha256'):raise RuntimeError('Evidence changed: '+str(path))
                artifacts.append(artifact)
    return {'passed':True,'scope':sorted(scope),'evidence':artifacts,'scope_note':'Recorded checks and freshness only; no automatic visual/fidelity approval'}


def make_review_draft(plan,scope,state,dependencies=None):
    plan=validate_plan(plan);select_modules(plan,scope)
    modules={m['id']:m for m in plan['modules']}
    return {'schema_version':1,'task_id':plan['task_id'],'status':'pending','reviewer':None,
            'inspection_signature':review_signature(plan,scope,state,dependencies),
            'modules':{ident:{'unresolved_issues':['Not inspected yet'],'checks':{
                c['id']:{'status':'unknown','finding':'','evidence':[],**({'view':''} if c['kind']=='visual' else {})}
                for c in modules[ident]['checks']}} for ident in scope}}


def record_blockout_review(receipt,plan,scope,review,state,dependencies=None):
    inputs=lambda:_review_inputs(plan,scope,review,state,dependencies)
    # Evidence hashes participate in inputs so image replacement also invalidates prior approval.
    def complete_inputs():
        result=inputs();signature=fingerprint({k:v for k,v in result.items() if k!='review'});result['inspection']=_check_review(plan,scope,review,signature);return result
    return run_stage(receipt,'blockout-review',complete_inputs,[],lambda:_check_review(plan,scope,review,review_signature(plan,scope,state,dependencies)),lambda result:result['passed'] is True)


def require_blockout_review(receipt,plan,scope,review,state,dependencies=None):
    def inputs():
        result=_review_inputs(plan,scope,review,state,dependencies);signature=fingerprint({k:v for k,v in result.items() if k!='review'});result['inspection']=_check_review(plan,scope,review,signature);return result
    return require_stage(receipt,'blockout-review',inputs)

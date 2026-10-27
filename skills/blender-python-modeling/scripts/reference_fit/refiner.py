"""Bounded coordinate search with immutable candidates and evidence-based rollback."""
import copy,json
from pathlib import Path
from .config import candidate,changed,dependencies
from .evaluation import compare


def defects(metrics,c):
    out=[];target=c['validation']['component_iou_target']
    for name,p in metrics['components'].items():
        state=c['shape'].get(name,{}).get('state','not_evaluable')
        paths=[v for v in c['validation'].get('parameters',[]) if v['path'].split('.')[0]==name]
        if p.get('status')=='not_evaluable':out.append({'component':name,'status':'not_evaluable','reason':p.get('reason'),'parameter_candidates':[]});continue
        if state in ['locked','approved']:out.append({'component':name,'status':state,'iou':p.get('iou'),'parameter_candidates':[]});continue
        if p['iou']<target:
            a=p['reference_bbox'];b=p['model_bbox'];issues=[]
            if b:
                if b[2]<a[2]*.94:issues.append('visible_region_too_narrow')
                if b[2]>a[2]*1.06:issues.append('visible_region_too_wide')
                if b[3]<a[3]*.94:issues.append('visible_region_too_short')
                if b[3]>a[3]*1.06:issues.append('visible_region_too_tall')
            out.append({'component':name,'status':'needs_refinement','issues':issues or ['boundary_mismatch'],'priority':c['shape'].get(name,{}).get('priority',1),'iou':p['iou'],'evidence':{'source':'visible part masks and calibrated front render','measured':True,'confidence':p.get('confidence')},'parameter_candidates':paths,'requires_full_regeneration':False})
    return sorted(out,key=lambda p:(p.get('priority',99),p.get('iou',1)))


def decide(before,after,c,component,structure_ok=True):
    d=compare(before,after);v=c['validation'];reasons=[]
    if not structure_ok:reasons.append('structure_failure')
    if d['global_iou'] < -v['regression_tolerance']:reasons.append('global_regression')
    # Protect every other measured region, not just labels declared locked.
    for name,delta in d['components'].items():
        if name!=component and delta < -v['regression_tolerance']:reasons.append('component_regression:'+name)
    for metric in ['mean','max']:
        a=before['landmarks'].get(metric);b=after['landmarks'].get(metric)
        if a is not None and b is not None and b-a>v['regression_tolerance']:reasons.append('landmark_regression:'+metric)
    gain=d['components'].get(component,0)
    if gain<v['min_improvement']:reasons.append('no_significant_local_improvement')
    return {'accepted':not reasons,'reasons':reasons,'delta':d,'target_gain':gain}


def converged(metrics,c):
    v=c['validation'];measured=[p['iou'] for p in metrics['components'].values() if 'iou' in p]
    landmarks=metrics['landmarks']['mean']
    # Missing semantic evidence cannot be silently turned into a successful gate.
    unavailable=[p for p in metrics['components'].values() if p.get('status')=='not_evaluable']
    return bool(measured) and not unavailable and metrics['global']['iou']>=v['global_iou_target'] and min(measured)>=v['component_iou_target'] and (landmarks is not None and landmarks<=v.get('landmark_target',.02))


def optimize(c,initial_metrics,initial_scene,out,run):
    """run(config, source_scene, affected_ids, candidate_dir) -> metrics, structure_ok."""
    folder=Path(out);folder.mkdir(parents=True,exist_ok=True);current=copy.deepcopy(c);metrics=initial_metrics;scene=Path(initial_scene)
    history=[];stop='iteration_limit';attempted=set();accepted=0
    (folder/'initial-config.json').write_text(json.dumps(c,indent=2))
    # Each round evaluates at most two bounded candidates for one component/parameter.
    for iteration in range(c['validation']['max_iterations']):
        if converged(metrics,current):stop='thresholds_met';break
        plan=defects(metrics,current)
        options=[(d,p) for d in plan if d['status']=='needs_refinement' for p in d['parameter_candidates'] if (d['component'],p['path'],current['shape'][d['component']][p['path'].split('.')[1]]) not in attempted]
        if not options:stop='no_actionable_unlocked_parameters';break
        defect,param=options[0];component=defect['component'];path=param['path'];key=path.split('.')[1]
        attempted.add((component,path,current['shape'][component][key]));round_dir=folder/f'round-{iteration:02d}';round_dir.mkdir()
        (round_dir/'refinement_plan.json').write_text(json.dumps({'defect':defect,'selected_parameter':param,'source_scene':str(scene)},indent=2))
        best=None
        for sign in [-1,1]:
            proposed=candidate(current,path,sign*param['step']);target=round_dir/('minus' if sign<0 else 'plus')
            affected=dependencies(proposed,changed(current,proposed))
            if any(proposed['shape'][k].get('state') in ['locked','approved'] for k in affected):
                history.append({'iteration':iteration,'candidate':str(target),'accepted':False,'reasons':['locked_dependency']});continue
            try:
                m,ok=run(proposed,scene,sorted(affected),target)
                choice=decide(metrics,m,current,component,ok)
            except (RuntimeError,ValueError,OSError) as exc:
                history.append({'iteration':iteration,'candidate':str(target),'accepted':False,'reasons':['candidate_failed'],'error':str(exc)});continue
            record={'iteration':iteration,'component':component,'parameter':path,'before':current['shape'][component][key],'after':proposed['shape'][component][key],'candidate':str(target),**choice,'selected':False}
            history.append(record)
            if choice['accepted'] and (best is None or choice['target_gain']>best[0]):best=(choice['target_gain'],proposed,m,target,record)
        if best:
            _,current,metrics,target,record=best;scene=target/'scene.blend';record['selected']=True;accepted+=1
        # Rollback is retaining the last accepted immutable scene/config. Rejected
        # mesh edits never touch the accepted file; next candidate reopens it.
        (round_dir/'accepted-state.json').write_text(json.dumps({'scene':str(scene),'config':current,'accepted_iterations':accepted},indent=2))
    result={'stop_reason':stop,'accepted_iterations':accepted,'history':history,'scene':str(scene.resolve()),'config':current,'metrics':metrics,'scope':'Front-view bounded parameter search; 3D checks are separate. No learned semantic reconstruction.'}
    (folder/'optimization.json').write_text(json.dumps(result,indent=2));(folder/'final-config.json').write_text(json.dumps(current,indent=2));return result

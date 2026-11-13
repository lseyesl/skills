"""Freeze actual self-review observations and generate an evidence-bound provisional score.
Not a live Agent runner and not the formal task-run interchange schema.
"""
import datetime,hashlib,html,json,shutil,subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
RAW=ROOT/'.tmp/image3d-baseline-20261113'
OUT=HERE/'results'
def read(p):return json.loads(p.read_text())
def write(p,data):p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    if OUT.exists():raise FileExistsError('Choose a new baseline; never overwrite scored runs')
    protocol=read(HERE/'protocol.json');freeze=read(HERE/'freeze.json')
    for path,digest in freeze['sha256'].items():
        if sha(HERE/path)!=digest:raise RuntimeError('Frozen input/standard changed: '+path)
    calibration=read(RAW/'calibration/calibration.json')
    if not calibration['passed'] or calibration['checker_sha256']!=sha(HERE/'check_assets.py'):raise RuntimeError('Missing/stale calibration')
    OUT.mkdir()
    # These levels are judgments made after viewing the actual fixed-view images.
    # Every reasoning string records a concrete discrepancy, not intended code behavior.
    visual={
      'mug':{'silhouette':(.5,'Tapered cup, D handle and tall spoon recognizable. Handle floats at lower attachment; photo has a continuous join. Faceted rim and cup profile remain coarse.'),'proportions':(.75,'Cup taper roughly follows photo; spoon axis/bowl outline and handle curvature differ. Perspective was not solved, so this is qualitative, not measured reconstruction accuracy.'),'signature_features':(.5,'Open lip, handle hole and separate spoon exist. Handle join and axial bottom fail; rolled lip and bowl concavity are not close enough for final.'),'materials':(.5,'White ceramic colour block present; bright/noisy lighting, coarse curvature and highlight response differ from photo.'),'shading':(.5,'No winding errors measured, but 16-sided silhouette and strong highlights expose faceting.')},
      'wheel':{'silhouette':(.5,'Round tire and radial wheel identifiable, but 20-sided tire outline and no sidewall lettering/tread differ strongly.'),'proportions':(.5,'Normalized radii follow broad tire/rim ratio; cast spoke widths/shape and recessed hub do not match. Depth inferred, camera not solved.'),'signature_features':(.25,'Ten branches and five lugs exist, but spoke roots are disconnected, hub detail/logo missing, tire tread/lettering absent, and cast opening profiles wrong.'),'materials':(.5,'Rubber/alloy separation exists; tire and cast-metal highlight response differ.'),'shading':(.25,'Strong faceting and rounded rod-like branches do not reproduce the broad smoothly cast spokes.')},
      'character':{'silhouette':(.75,'Girl, two buns, dress, separated limbs and shoes recognizable. Head contour, hands, feet and dress hem differ; back/depth only partly observed.'),'proportions':(.75,'Front head/body placement reasonably close. Head/skull profile, facial placement, hand/thumb shape and shoe thickness have visible discrepancies.'),'signature_features':(.5,'Happy face and two buns present. Braided irregular hair, ceramic/clay relief, dress texture/hem and explicit hand/thumb details remain substantially simplified.'),'materials':(.5,'Broad skin/green/red/dark colour blocks match; surface relief and hand-made material response missing or weak.'),'shading':(.75,'Closed finite meshes and consistent winding measured; close-up form is smooth but noisy and reference-specific surface relief is absent.')} }
    groups={'fidelity':['silhouette','proportions','signature_features','materials'],'technical':['geometry','shading','material_portability','source_editability'],'purpose':['purpose_function','export_roundtrip'],'process':['reference_preparation','blockout_gate','completion_evidence']}
    records=[]
    for case in protocol['cases']:
        ident=case['id'];folder=RAW/(ident+'-salvage' if ident=='character' else ident);dest=OUT/ident;dest.mkdir()
        tech=read(folder/'technical.json');checks=tech['checks'];fmt=read(folder/'format.json')
        for name in ['technical.json','format.json']:shutil.copyfile(folder/name,dest/name)
        if ident=='character':
            image_files={'front':'beauty_front.png','side':'beauty_side.png','back':'beauty_back.png','three-quarter':'beauty_three_quarter.png','clay':'clay_front.png'}
            shutil.copyfile(RAW/'character/structure.json',dest/'original-structure.json');shutil.copyfile(folder/'salvage.json',dest/'salvage.json')
            shutil.copyfile(RAW/'character-run.log',dest/'original-failure.log')
        else:
            image_files={k:k+'.png' for k in ['front','side','back','three-quarter','clay']}
            for name in ['blockout-review.json','blockout-receipt.json','gate-result.json','modeling-plan.json']:shutil.copyfile(folder/name,dest/name)
        for key,filename in image_files.items():shutil.copyfile(folder/filename,dest/(key+'.png'))
        levels={key:{'level':value,'reason':reason} for key,(value,reason) in visual[ident].items()}
        geometry=all(checks[k] for k in ['source_nonempty_finite','no_degenerate_triangles','triangle_budget'])
        levels.update(geometry={'level':int(geometry),'reason':f"Source evaluated triangles={tech['source']['triangles']}, budget={case['triangle_budget']}; nonfinite={tech['source']['nonfinite_vertices']}, degenerate={tech['source']['degenerate_triangles']}. All geometry criteria required for these 8 points."},
          material_portability={'level':.5 if ident=='character' else 1,'reason':'Base PBR materials embedded and Khronos format passed; procedural surface detail not baked/preserved.' if ident=='character' else 'Base untextured PBR materials embedded; Khronos format validation passed. Extra Cube is penalized under export scope.'},
          source_editability={'level':1,'reason':'Source .blend reopens with separately editable semantic parts; this does not certify a usable armature.'},
          purpose_function={'level':0,'reason':{'mug':'Independent ray test misses center floor; lower handle center-to-wall distance .07429 exceeds tube radius .052.','wheel':'Coarse review failed assembly continuity; no refinement/rotation clip executed. Sampled angle remains zero. A stationary center is not evidence of successful rotation.','character':'No persistent armature, skin or exported clip; four disposable skinning probes are not production binding.'}[ident]},
          export_roundtrip={'level':0,'reason':f"Unexpected Cube exported. Bounds max error={tech['world_bounds_max_error']:.6f}; source triangles={tech['source']['triangles']}, imported={tech['reimport']['triangles']}. Not asset-only or equivalent geometry."},
          reference_preparation={'level':.5 if ident=='character' else .25,'reason':'Existing fitter uses pixel/profile config and packed guides; side reference inconsistent. Actual reference-visible viewport calibration not performed.' if ident=='character' else 'Public source, license and interpretation retained, but perspective camera/calibration and reference-visible viewport check missing.'},
          blockout_gate={'level':0 if ident=='character' else 1,'reason':'Existing fitter creates detailed geometry directly; no prior signed coarse inspection in this run.' if ident=='character' else 'Actual coarse image inspected, failure recorded with current signature/evidence, gate rejects refinement, coarse source preserved. These process points do not pass the asset.'},
          completion_evidence={'level':1,'reason':'Per-module unresolved differences and failed final gate retained; no modules falsely labeled matched or assets claimed final.'})
        for key,level in levels.items():level['weight']=protocol['score_items'][key]['weight'];level['points']=level['level']*level['weight']
        subtotals={group:sum(levels[k]['points'] for k in keys) for group,keys in groups.items()}
        signatures=case['required_modules'];objects=list(tech['source']['objects'])
        modules=[]
        for index,title in enumerate(signatures):
            modules.append({'id':'module-'+str(index+1),'name':title,'evidence':'observed','source_views':['front'] if ident=='character' else ['perspective-photo'],'priority':'primary' if index<2 else 'secondary','required':True,'expected_instances':1,'implemented_instances':1,'signature_features':[title],'matched_signature_features':[],'feature_reviews':[],'review_invalidated':'','status':'blockout','implementation_objects':objects,'user_approved_simplification':False,'simplification_reason':'','notes':levels['signature_features']['reason']+' Aggregate assembly entry, not a declaration that each signature is matched.'})
        # Correct count is recorded separately when one assembly contains repetition.
        if ident=='wheel':modules[1]['expected_instances']=10;modules[1]['implemented_instances']=10;modules[2]['expected_instances']=5;modules[2]['implemented_instances']=5
        ledger={'schema_version':1,'task_id':ident,'target_stage':'final','modules':modules,'final_review':{'status':'failed','structural_report':'technical.json','contact_sheet':'../report.html','perspective_view':'three-quarter.png','unresolved_issues':[levels['purpose_function']['reason'],levels['export_roundtrip']['reason'],levels['signature_features']['reason']]}}
        write(dest/'module-ledger.json',ledger)
        validation=__import__('sys');validation.path.insert(0,str(ROOT/'skills/blender-python-modeling/scripts'))
        from validate_module_ledger import validate_ledger
        final=validate_ledger(ledger);write(dest/'final-gate.json',final)
        if final['ok']:raise RuntimeError('Known failed candidate passed final ledger')
        record={'task_id':ident,'status':'failed','actual_stage':'failed-blockout' if ident!='character' else 'static-character-diagnostic-after-render-failure','visual_reviewer':'current-session-Agent-self-review','review_confidence':'provisional; uncalibrated self-assessment','score':sum(subtotals.values()),'subtotals':subtotals,'items':levels,'hard_gate_passed':False,'source_triangles':tech['source']['triangles'],'glb_triangles':tech['reimport']['triangles'],'format_status':fmt['status'],'context_tokens':None,'total_task_elapsed_seconds':None,'human_interventions':0,'runtime_rescues':int(ident=='character'),'quality_retries':0,'execution_process_costs':[read(p) for p in sorted(RAW.glob(ident+'-*-execution.json'))],'evidence':{p.name:sha(p) for p in dest.iterdir() if p.is_file()},'asset_paths':{'blend':str((folder/('asset.blend' if ident=='character' else 'diagnostic-asset.blend')).relative_to(ROOT)),'glb':str((folder/('asset.glb' if ident=='character' else 'diagnostic-asset.glb')).relative_to(ROOT))}}
        write(dest/'score.json',record);records.append(record)
    report={'schema_version':1,'id':protocol['id'],'status':'provisional-artifact-baseline','revision':protocol['source_revision'],'protocol_sha256':sha(HERE/'protocol.json'),'freeze_sha256':sha(HERE/'freeze.json'),'blender':'4.3.2','model_identity':None,'token_usage':None,'task_count':3,'passed':0,'failed':3,'interpretation':'0/3 observed deliverables pass; not an estimated general Agent success rate','technical_calibration':calibration,'records':records,'limitations':protocol['comparison_limits'],'skill_source_modified':False,'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    write(OUT/'baseline.json',report)
    rows=''.join(f"<tr><td>{r['task_id']}</td><td>{r['subtotals']['fidelity']}/40</td><td>{r['subtotals']['technical']}/20</td><td>{r['subtotals']['purpose']}/25</td><td>{r['subtotals']['process']}/15</td><td>{r['score']}/100</td><td>未通过</td></tr>" for r in records)
    sections=''
    for r in records:
        ident=r['task_id'];src='../inputs/character/front.png' if ident=='character' else '../inputs/'+ident+'/reference.jpg'
        sections+=f'<section><h2>{ident} — {r["score"]}/100，未通过</h2><div class="images"><figure><img src="{src}"><figcaption>输入参考</figcaption></figure><figure><img src="{ident}/three-quarter.png"><figcaption>实际候选／诊断模型</figcaption></figure><figure><img src="{ident}/front.png"><figcaption>正面检查</figcaption></figure><figure><img src="{ident}/side.png"><figcaption>侧面检查</figcaption></figure><figure><img src="{ident}/back.png"><figcaption>背面检查</figcaption></figure><figure><img src="{ident}/clay.png"><figcaption>灰模检查</figcaption></figure></div><p>{html.escape(r["items"]["purpose_function"]["reason"])}</p><p>{html.escape(r["items"]["export_roundtrip"]["reason"])}</p><details><summary>逐项评分与证据</summary><ul>'+''.join(f'<li>{k}: {v["points"]}/{v["weight"]} — {html.escape(v["reason"])}</li>' for k,v in r['items'].items())+'</ul></details></section>'
    (OUT/'report.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>图片到可用3D 首轮基准</title><style>body{font:16px/1.65 system-ui;max-width:1250px;margin:35px auto;padding:0 20px;color:#233}table{border-collapse:collapse;width:100%}td,th{padding:10px;border-bottom:1px solid #ccc;text-align:left}.images{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}figure{margin:0}img{width:100%;height:320px;object-fit:contain;background:#b4bdc5}figcaption{color:#455}section{padding:22px 0;border-bottom:1px solid #ccc}</style><h1>图片 → 可用 3D：首轮探索基准</h1><p>2026-11-13 · Skill b7a0844 · Blender 4.3.2 · 当前会话自评，非隔离／盲测，分数待独立复核。80分与全部用途硬门槛同时通过才合格。</p><p><strong>观察结果 0/3 通过。</strong>前两项在粗模验收失败后停止细化；角色原始渲染失败，图像来自禁用降噪后的诊断补救。可打开或格式合法不代表可用。</p><table><tr><th>任务</th><th>还原</th><th>技术</th><th>用途/导出</th><th>流程</th><th>总分</th><th>结果</th></tr>'+rows+'</table>'+sections+'<p>未测目标引擎／实际游戏性能；未知绝对尺寸；角色为已见回归样本。缺陷可能来自执行配方、环境或Skill覆盖，不能据此推断全部能力。</p></html>',encoding='utf-8')
    print(json.dumps({'scores':{r['task_id']:r['score'] for r in records},'passed':0,'failed':3},ensure_ascii=False))

if __name__=='__main__':main()

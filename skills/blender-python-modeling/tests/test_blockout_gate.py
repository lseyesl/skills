import copy,json
from pathlib import Path
import sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from blockout_gate import validate_plan,record_blockout_review,require_blockout_review,review_signature,make_review_draft
from stage_guard import file_input

class BlockoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.review=self.root/'review.json';self.receipt=self.root/'gate.json';self.image=self.root/'front.png';self.image.write_bytes(b'synthetic-test-evidence-not-art-approval')
        self.plan={'schema_version':1,'task_id':'test','intended_use':'static','modules':[self.module('body'),self.module('wheel')]}
        self.states={'body':'geometry-v1','wheel':'wheel-v1'}
        self.state=lambda modules:{m['id']:self.states[m['id']] for m in modules}
        self.data={'schema_version':1,'task_id':'test','status':'passed','reviewer':'unit-test-only','modules':{'body':{'unresolved_issues':[],'checks':{'silhouette':{'status':'passed','finding':'Synthetic protocol fixture; not a visual judgment','view':'front','evidence':[{'path':'front.png','sha256':file_input(self.image)['sha256']}]}}}}}
        self.sign();self.save()
    def sign(self,dependencies=None):self.data['inspection_signature']=review_signature(self.plan,['body'],self.state,dependencies)
    def module(self,ident):return {'id':ident,'method':'box','reason':'continuous low-resolution surface','objects':[ident],'depends_on':[],'checks':[{'id':'silhouette','kind':'visual','criterion':'check actual silhouette'}]}
    def save(self):self.review.write_text(json.dumps(self.data))
    def record(self):return record_blockout_review(self.receipt,self.plan,['body'],self.review,self.state)
    def require(self):return require_blockout_review(self.receipt,self.plan,['body'],self.review,self.state)
    def test_planned_profile_requires_profile_review(self):
        self.plan['modules'][0]['checks'][0]['view']='right'
        draft=make_review_draft(self.plan,['body'],self.state)
        self.assertEqual(draft['modules']['body']['checks']['silhouette']['view'],'right')
        self.sign();self.save()
        with self.assertRaisesRegex(ValueError,'planned view'):
            self.record()
        self.data['modules']['body']['checks']['silhouette']['view']='right'
        self.save();self.record();self.require()

    def test_front_pass_cannot_clear_missing_or_failed_side_overlap(self):
        module = self.plan['modules'][0]
        module['control_views'] = ['front', 'right']
        module['checks'][0].update(view='front', silhouette=True)
        with self.assertRaisesRegex(ValueError, 'right'):
            validate_plan(self.plan)
        criterion = 'The sash knot and hanging end remain visible beyond the sleeve.'
        module['checks'].append({'id': 'knot', 'kind': 'visual', 'view': 'right', 'criterion': criterion})
        with self.assertRaisesRegex(ValueError, 'Missing silhouette check for: right'):
            validate_plan(self.plan)
        module['checks'].append(dict(id='profile', kind='visual', view='right', silhouette=True,
                                     criterion='Trace the chin and heel in profile'))
        draft = make_review_draft(self.plan, ['body'], self.state)
        self.assertEqual(draft['modules']['body']['checks']['knot']['criterion'], criterion)
        self.sign()
        checks = self.data['modules']['body']['checks']
        checks['silhouette']['evidence'][0]['role'] = 'silhouette_overlay'
        checks['profile'] = dict(checks['silhouette'], view='right', finding='The heel aligns in profile')
        checks['knot'] = dict(checks['silhouette'], view='right', status='failed', finding='Sleeve hides knot')
        self.save()
        with self.assertRaisesRegex(ValueError, 'knot'):
            self.record()
        with self.assertRaises((ValueError, RuntimeError)):
            self.require()

    def test_shoe_baseline_and_count_do_not_cover_local_shape(self):
        module = self.plan['modules'][0]
        module['reference_parts'] = {'footwear': ['front', 'right']}
        module['checks'][0].update(view='front', criterion='Both shoes touch ground')
        module['checks'].append(dict(id='count', kind='visual', view='right', criterion='Count shoes'))
        with self.assertRaisesRegex(ValueError, 'footwear/front, footwear/right'):
            validate_plan(self.plan)
        module['checks'].append(dict(id='toe', kind='visual', view='front', local_shape='footwear',
                                     criterion='Inspect toe width and instep opening'))
        with self.assertRaisesRegex(ValueError, 'footwear/right'):
            validate_plan(self.plan)
        module['checks'].append(dict(id='heel', kind='visual', view='right', local_shape='footwear',
                                     criterion='Compare heel height and sole thickness'))
        validate_plan(self.plan)

    def test_profile_cannot_reuse_front_criterion_or_finding(self):
        module = self.plan['modules'][0]
        module['reference_parts'] = {'fans': ['front', 'right']}
        front = module['checks'][0]
        front.update(local_shape='fans', view='front', criterion='Fan folds are visible')
        side = dict(front, id='side', view='right')
        module['checks'].append(side)
        with self.assertRaisesRegex(ValueError, 'Repeated criterion'):
            validate_plan(self.plan)
        side['criterion'] = 'Near fan exposes radial folds while the bun hides the far fan'
        checks = self.data['modules']['body']['checks']
        checks['silhouette']['evidence'][0]['role'] = 'local_comparison'
        checks['side'] = dict(checks['silhouette'], view='right')
        self.sign(); self.save()
        with self.assertRaisesRegex(ValueError, 'Repeated finding'):
            self.record()
        checks['side']['finding'] = 'Near fan folds extend past bun edge in profile'
        self.save(); self.record(); self.require()

    def test_silhouette_requires_overlay_evidence(self):
        self.plan['modules'][0]['checks'][0].update(view='front', silhouette=True)
        self.sign(); self.save()
        with self.assertRaisesRegex(ValueError, 'contour overlay'):
            self.record()
        self.data['modules']['body']['checks']['silhouette']['evidence'][0]['role'] = 'silhouette_overlay'
        self.save(); self.record(); self.require()

    def test_local_shape_requires_comparison_evidence(self):
        module = self.plan['modules'][0]
        module['reference_parts'] = {'footwear': ['front']}
        module['checks'][0].update(view='front', local_shape='footwear', criterion='Inspect toe width')
        self.sign()
        self.save()
        with self.assertRaisesRegex(ValueError, 'crop comparison'):
            self.record()
        self.data['modules']['body']['checks']['silhouette']['evidence'][0]['role'] = 'local_comparison'
        self.save()
        self.record()
        self.require()

    def test_draft_is_not_an_approval(self):
        self.data=make_review_draft(self.plan,['body'],self.state);self.save()
        with self.assertRaises(ValueError):self.record()
        self.assertEqual(json.loads(self.receipt.read_text())['status'],'failed')

    def test_continuous_mesh_can_serve_multiple_semantic_modules(self):
        self.plan['modules'][1]['objects']=['body']
        validate_plan(self.plan)

    def test_requires_actual_prior_review(self):
        with self.assertRaises(FileNotFoundError):self.require()
        self.record();self.require()
    def test_method_choices_are_valid(self):
        for method in ('primitives','box','surface','curve','sculpt'):
            self.plan['modules'][0]['method']=method;self.assertIs(validate_plan(self.plan),self.plan)
        self.plan['modules'][0].update(method='reuse',source_snapshot='source.blend');validate_plan(self.plan)
    def test_failed_review_invalidates_old_success(self):
        self.record();self.data['modules']['body']['checks']['silhouette']['status']='unknown';self.save()
        with self.assertRaises(ValueError):self.record()
        self.assertEqual(json.loads(self.receipt.read_text())['status'],'failed')
    def test_old_review_cannot_be_replayed_after_geometry_change(self):
        self.record();self.states['body']='changed'
        with self.assertRaises(RuntimeError):self.record()
        self.assertEqual(json.loads(self.receipt.read_text())['status'],'failed')

    def test_geometry_and_method_changes_block(self):
        self.record();self.states['body']='geometry-v2'
        with self.assertRaises(RuntimeError):self.require()
        self.states['body']='geometry-v1';self.plan['modules'][0]['method']='primitives'
        with self.assertRaises(RuntimeError):self.require()
    def test_global_use_change_blocks(self):
        self.record();self.plan['intended_use']='animated'
        with self.assertRaises(RuntimeError):self.require()
    def test_unrelated_module_does_not_invalidate(self):
        self.record();self.states['wheel']='changed';self.plan['modules'][1]['reason']='updated independent wheel'
        self.require()
    def test_explicit_dependency_invalidates(self):
        self.plan['modules'][0]['depends_on']=['wheel'];self.sign();self.save();self.record();self.states['wheel']='changed'
        with self.assertRaises(RuntimeError):self.require()
    def test_changed_or_missing_artifact_blocks(self):
        self.record();self.image.write_bytes(b'changed')
        with self.assertRaises(RuntimeError):self.require()
        self.image.unlink()
        with self.assertRaises(RuntimeError):self.require()
    def test_scope_cannot_expand_to_unreviewed_modules(self):
        self.record()
        with self.assertRaises(ValueError):require_blockout_review(self.receipt,self.plan,['body','wheel'],self.review,self.state)
    def test_reuse_and_unknown_method_constraints(self):
        self.plan['modules'][0]['method']='reuse'
        with self.assertRaises(ValueError):validate_plan(self.plan)
        self.plan['modules'][0]['method']='subdivide-until-done'
        with self.assertRaises(ValueError):validate_plan(self.plan)
    def test_no_count_only_acceptance(self):
        self.plan['modules'][0]['checks']=[{'id':'exists','kind':'structural','criterion':'object exists'}]
        with self.assertRaises(ValueError):validate_plan(self.plan)
    def test_reference_inputs_changes_block(self):
        context={'reference':'v1'}
        self.sign(lambda:context);self.save()
        record_blockout_review(self.receipt,self.plan,['body'],self.review,self.state,lambda:context)
        context['reference']='v2'
        with self.assertRaises(RuntimeError):require_blockout_review(self.receipt,self.plan,['body'],self.review,self.state,lambda:context)

if __name__=='__main__':unittest.main()

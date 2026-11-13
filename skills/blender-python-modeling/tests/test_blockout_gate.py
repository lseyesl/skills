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

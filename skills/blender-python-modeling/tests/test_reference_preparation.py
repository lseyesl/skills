"""Synthetic declaration/freshness controls, not visual image-fidelity certification."""
import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from reference_preparation import require_preparation,require_source_fidelity

class ReferencePreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        for name in ['source.png','front.png','side.png','prompt.txt']:
            (self.root/name).write_bytes(('synthetic-'+name).encode())
        self.generation={'tool':'builtin-image-generation','reference_images':[self.ref('source.png')],'prompt':self.ref('prompt.txt'),'outputs':[self.ref('front.png'),self.ref('side.png')]}
        self.save('generation.json',self.generation)
        self.fidelity={'schema_version':1,'status':'passed','scope':'synthetic declared observed identity only','reviewer':'unit-fixture-not-visual-review',
            'source_images':[self.ref('source.png')],'generated_images':[self.ref('front.png'),self.ref('side.png')],'unresolved_issues':[],
            'invariants':[{'id':'spoke-count','critical':True,'evidence_type':'observed','status':'passed','source_region':'source front','generated_region':'generated front','finding':'Synthetic fixture, not image assessment','evidence':[self.ref('front.png')]}]}
        self.save('fidelity.json',self.fidelity)
        self.decision={'schema_version':1,'task_id':'test','purpose':'synthetic reference creation','route':'generated','reason':'Perspective source needs construction guides',
            'facts':{'projection':'perspective','needs_hidden_shape':True,'needs_pose_normalization':False},'selected_skill':'concept-multiview-sheet',
            'source_images':[self.ref('source.png')],'construction_images':[self.ref('front.png'),self.ref('side.png')],
            'generation_record':self.ref('generation.json'),'source_fidelity_review':self.ref('fidelity.json')}
    def save(self,name,data):self.root.joinpath(name).write_text(json.dumps(data))
    def ref(self,name):return {'path':name,'sha256':hashlib.sha256((self.root/name).read_bytes()).hexdigest()}
    def require(self,mode='reference',**kwargs):
        self.save('decision.json',self.decision)
        return require_preparation(self.root/'decision.json','test',mode=mode,**kwargs)
    def test_missing_route_blocks(self):
        with self.assertRaises(ValueError):require_preparation(None,'test',mode='reference')
    def test_explicit_no_reference_original(self):
        self.decision.update(route='no_reference',source_images=[],construction_images=[])
        self.assertTrue(self.require(mode='original')['accepted_construction'])
    def test_photo_cannot_be_called_original(self):
        with self.assertRaises(ValueError):self.require(mode='original')
        self.decision['route']='no_reference'
        with self.assertRaises(ValueError):self.require(mode='original')
    def test_generated_declared_route_and_hashes(self):
        self.assertEqual(self.require(construction_images=[self.root/'front.png',self.root/'side.png'])['route'],'generated')
    def test_single_view_bypass_rejected_for_perspective(self):
        self.decision['route']='single_view_sufficient'
        with self.assertRaises(RuntimeError):self.require()
    def test_declared_skill_without_generation_is_insufficient(self):
        self.decision.pop('generation_record')
        with self.assertRaises(ValueError):self.require()
    def test_consistency_without_source_fidelity_is_insufficient(self):
        self.decision.pop('source_fidelity_review')
        with self.assertRaises(ValueError):self.require()
    def test_source_fidelity_unknown_or_failed_blocks(self):
        for status in ['unknown','failed']:
            self.fidelity['invariants'][0]['status']=status;self.save('fidelity.json',self.fidelity);self.decision['source_fidelity_review']=self.ref('fidelity.json')
            with self.subTest(status=status),self.assertRaises(RuntimeError):self.require()
    def test_unresolved_source_issue_blocks(self):
        self.fidelity['unresolved_issues']=['Extra spoke'];self.save('fidelity.json',self.fidelity);self.decision['source_fidelity_review']=self.ref('fidelity.json')
        with self.assertRaises(RuntimeError):self.require()
    def test_hidden_inference_cannot_be_source_truth(self):
        self.fidelity['invariants'][0]['evidence_type']='inferred';self.save('fidelity.json',self.fidelity);self.decision['source_fidelity_review']=self.ref('fidelity.json')
        with self.assertRaises(ValueError):self.require()
    def test_source_change_invalidates(self):
        self.require();(self.root/'source.png').write_bytes(b'changed')
        with self.assertRaises(RuntimeError):self.require()
    def test_generated_change_invalidates(self):
        self.require();(self.root/'front.png').write_bytes(b'changed')
        with self.assertRaises(RuntimeError):self.require()
    def test_different_guide_not_approved(self):
        with self.assertRaises(RuntimeError):self.require(construction_images=[self.root/'source.png'])
    def test_existing_reviewed_guides_do_not_force_generation(self):
        self.save('existing.json',{'status':'passed','finding':'Synthetic reviewed guides','construction_images':self.decision['construction_images']})
        self.decision.update(route='existing_reviewed',existing_review=self.ref('existing.json'))
        self.assertEqual(self.require()['route'],'existing_reviewed')
    def test_valid_single_view_has_reviewed_sufficient_scope(self):
        self.decision.update(route='single_view_sufficient',facts={'projection':'orthographic','needs_hidden_shape':False,'needs_pose_normalization':False},construction_images=[self.ref('front.png')])
        self.save('existing.json',{'status':'passed','finding':'Flat outline with explicit user depth; synthetic','construction_images':self.decision['construction_images']});self.decision['existing_review']=self.ref('existing.json')
        self.assertEqual(self.require()['route'],'single_view_sufficient')
    def test_diagnostic_cannot_be_promoted(self):
        self.decision['route']='diagnostic_only'
        with self.assertRaises(RuntimeError):self.require()
        self.assertFalse(self.require(allow_diagnostic=True)['accepted_construction'])
    def test_waiver_not_invented(self):
        self.decision.update(route='user_waived',construction_images=[])
        with self.assertRaises(ValueError):self.require(mode='waived')
        self.decision['user_waiver']='Synthetic existing explicit instruction, not an actual user approval'
        self.assertEqual(self.require(mode='waived')['route'],'user_waived')

if __name__=='__main__':unittest.main()

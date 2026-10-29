import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from reference_review import CHECKS, file_hash, require_design_review
from stage_guard import file_input, require_stage, run_stage


class DesignReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for view in ['front', 'right', 'top']:
            (self.root / (view + '.png')).write_bytes(('synthetic-' + view).encode())
        self.config = {'multiview_review': 'review.json', 'views': {
            v: {'image': v + '.png'} for v in ['front', 'right']}}
        self.review = {'schema_version': 1, 'purpose': 'synthetic reusable character',
            'pose': 'fixed four-foot stand, head and torso aligned', 'readiness': 'passed',
            'checks': {k: {'status': 'passed', 'finding': 'Synthetic evidence fixture for ' + k} for k in CHECKS},
            'allowed_regions': ['head', 'body'], 'blocked_regions': [], 'conflicts': [],
            'views': {v: {'image': v + '.png', 'sha256': file_hash(self.root / (v + '.png')),
                'role': 'controlling' if v != 'top' else 'supplemental',
                'controls': ['head', 'body'], 'finding': 'Synthetic fixture, not image approval'}
                for v in ['front', 'right', 'top']}, 'review_artifacts': ['front.png']}

    def run_review(self):
        (self.root / 'review.json').write_text(json.dumps(self.review))
        return require_design_review(self.config, self.root)

    def test_full_review_accepts_same_source_and_scope(self):
        self.assertEqual(self.run_review()['build_regions'], ['head', 'body'])

    def test_multiple_guides_need_review(self):
        self.config.pop('multiview_review')
        with self.assertRaises(ValueError): self.run_review()

    def test_single_ordinary_reference_does_not_need_multiview_receipt(self):
        self.assertIsNone(require_design_review({'views': {'front': {}}}, self.root))

    def test_partial_can_continue_independent_body(self):
        self.review.update(readiness='partial', allowed_regions=['body'], blocked_regions=['head'])
        self.review['checks']['proportions']['status'] = 'partial'
        self.review['conflicts'] = [{'severity': 'critical', 'status': 'unresolved',
                                    'regions': ['head'], 'finding': 'Nose heights conflict'}]
        self.config['build_regions'] = ['body']
        self.assertEqual(self.run_review()['build_regions'], ['body'])
        self.config['build_regions'] = ['head.muzzle']
        with self.assertRaises(RuntimeError): self.run_review()

    def test_parent_scope_cannot_bypass_blocked_child(self):
        self.review.update(readiness='partial', allowed_regions=['head.skull'], blocked_regions=['head.muzzle'])
        self.config['build_regions'] = ['head']
        with self.assertRaises(RuntimeError): self.run_review()

    def test_allowed_parent_cannot_hide_blocked_child(self):
        self.review.update(readiness='partial', blocked_regions=['head.muzzle'])
        self.config['build_regions'] = ['body']
        with self.assertRaises(ValueError): self.run_review()

    def test_critical_parent_conflict_requires_parent_block(self):
        self.review.update(readiness='partial', allowed_regions=['head.skull'], blocked_regions=['head.muzzle'])
        self.review['conflicts']=[{'severity':'critical','status':'unresolved','regions':['head'], 'finding':'Head pose is inconsistent'}]
        self.config['build_regions']=['head.skull']
        with self.assertRaises(ValueError): self.run_review()

    def test_partial_requires_explicit_build_scope(self):
        self.review['readiness'] = 'partial'
        with self.assertRaises(ValueError): self.run_review()

    def test_critical_conflict_cannot_claim_pass(self):
        self.review['conflicts'] = [{'severity': 'critical', 'status': 'unresolved',
                                    'regions': ['head'], 'finding': 'Different neutral head directions'}]
        with self.assertRaises(ValueError): self.run_review()

    def test_resolved_conflict_needs_reason(self):
        self.review['conflicts'] = [{'severity': 'critical', 'status': 'resolved', 'finding': 'Wrong side label'}]
        with self.assertRaises(ValueError): self.run_review()
        self.review['conflicts'][0]['resolution'] = 'Verified projection and symmetric anatomy; use +X right view'
        self.run_review()

    def test_global_projection_failure_blocks_even_body(self):
        self.review['checks']['projection']['status'] = 'blocked'
        with self.assertRaises(RuntimeError): self.run_review()

    def test_changed_source_invalidates_review(self):
        (self.root / 'right.png').write_bytes(b'new design')
        with self.assertRaises(RuntimeError): self.run_review()

    def test_rejected_or_unreviewed_view_cannot_be_guide(self):
        for role in ['supplemental', 'rejected']:
            self.review['views']['right']['role'] = role
            with self.assertRaises(RuntimeError): self.run_review()

    def test_missing_evidence_or_finding_rejects(self):
        old = copy.deepcopy(self.review)
        self.review['review_artifacts'] = ['missing.png']
        with self.assertRaises(RuntimeError): self.run_review()
        self.review = old
        self.review['checks']['pose']['finding'] = ''
        with self.assertRaises(ValueError): self.run_review()

    def test_scope_must_be_constrained_by_configured_guide(self):
        self.review['allowed_regions'].append('tail')
        with self.assertRaises(RuntimeError): self.run_review()


class StageGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.state = self.root / 'build-state.json'
        self.output = self.root / 'model.blend'
        self.inputs = {'recipe': 'v1', 'source': 'hash'}

    def build(self):
        self.output.write_bytes(b'generated model')
        return {'ok': True}

    def test_success_requires_explicit_check_and_fresh_artifact(self):
        run_stage(self.state, 'build', self.inputs, [self.output], self.build, lambda r: r['ok'])
        receipt = require_stage(self.state, 'build', self.inputs)
        self.assertGreaterEqual(receipt['elapsed_seconds'], 0)
        self.output.write_bytes(b'changed')
        with self.assertRaises(RuntimeError): require_stage(self.state, 'build', self.inputs)

    def test_failed_attempt_invalidates_prior_success_and_stops_caller(self):
        run_stage(self.state, 'build', self.inputs, [self.output], self.build, lambda r: True)
        continued = []
        def fail(): raise RuntimeError('geometry failed')
        with self.assertRaises(RuntimeError):
            run_stage(self.state, 'build', self.inputs, [self.output], fail, lambda r: True)
            continued.append('render')
        self.assertEqual(continued, [])
        self.assertEqual(json.loads(self.state.read_text())['status'], 'failed')
        with self.assertRaises(RuntimeError): require_stage(self.state, 'build', self.inputs)

    def test_false_validation_or_missing_output_never_passes(self):
        for check in [lambda r: False, lambda r: None]:
            with self.assertRaises(RuntimeError): run_stage(self.state, 'build', {}, [], self.build, check)
        with self.assertRaises(RuntimeError):
            run_stage(self.state, 'build', {}, [self.root/'missing'], lambda: None, lambda r: True)

    def test_changed_inputs_or_wrong_attempt_rejected(self):
        run_stage(self.state, 'build', self.inputs, [self.output], self.build, lambda r: True)
        with self.assertRaises(RuntimeError): require_stage(self.state, 'build', {'recipe': 'v2'})
        with self.assertRaises(RuntimeError): require_stage(self.state, 'build', self.inputs, run_id='old-attempt')

    def test_input_failure_invalidates_old_success(self):
        run_stage(self.state, 'build', {}, [], lambda: None, lambda r: True)
        def missing_input(): return file_input(self.root/'missing-reference')
        with self.assertRaises(RuntimeError):
            run_stage(self.state, 'build', missing_input, [], self.build, lambda r: True)
        self.assertEqual(json.loads(self.state.read_text())['status'], 'failed')

    def test_interrupted_running_receipt_not_usable(self):
        self.state.write_text(json.dumps({'stage':'build','status':'running'}))
        with self.assertRaises(RuntimeError): require_stage(self.state, 'build', self.inputs)

    def test_file_dependencies_compare_content(self):
        self.output.write_bytes(b'one')
        before=file_input(self.output)
        self.output.write_bytes(b'two')
        self.assertNotEqual(before, file_input(self.output))


if __name__ == '__main__': unittest.main()

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('validate_contract', Path(__file__).resolve().parents[1] / 'scripts/validate_contract.py')
validator = importlib.util.module_from_spec(spec); spec.loader.exec_module(validator)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.contract = dict(schema_version=1, repository_id='test', project_id='p',
                             visual_profile='shadow_puppet', implementation_profile='godot',
                             route_id='flat-components', asset_unit='component-png', hidden_region_policy='concept-covered',
                             upstream=[dict(self.proof('content/definition.json', {'status': 'locked', 'version': 'v1'}), version='v1', status='locked')])

    def tearDown(self):
        self.temp.cleanup()

    def proof(self, name, data):
        path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
        return {'path': name, 'sha256': validator.assets.file_sha(path)}

    def gate_contract(self, gate='gate-4'):
        master = [{'shot_id': f'S{i:03}', 'frames': 24} for i in range(1, 7)]
        selected = master[:3] if gate == 'gate-4' else master
        self.contract['backend'] = {'entrypoint': 'scripts/build.py', 'validation_evidence': self.proof('audit/backend.json', {'pass': True})}
        self.proof('scripts/build.py', {'fixture': 'not executed'})
        asset_path = 'projects/p/a.png'; asset_ref = self.proof(asset_path, 'synthetic asset')
        asset = dict(asset_id='a', project_id='p', version='v1', path=asset_path,
                     sha256=asset_ref['sha256'], size=(self.root/asset_path).stat().st_size, status='locked',
                     uri=f"hf://buckets/owner/test/test/objects/{asset_ref['sha256']}.png")
        receipt = {k: asset[k] for k in ('asset_id', 'project_id', 'version', 'sha256')}
        receipt.update(repository_id='test', approved_by='fixture', approved_at='2026-11-05')
        ref = self.proof('content/receipt.json', receipt)
        asset.update(approval_receipt=ref['path'], approval_receipt_sha256=ref['sha256'])
        self.contract['assets_manifest'] = self.proof('assets.lock.json', dict(repository_id='test', bucket='owner/test', assets=[asset]))
        review = dict(gate=gate, review_scope='sample' if gate == 'gate-4' else 'full-film',
                      master_timeline=master, timeline=selected, fps=24, total_frames=sum(s['frames'] for s in selected),
                      director_review_status='pass', director_taste_review_status='pass')
        if gate == 'gate-5':
            review['locale'] = 'zh-CN'
        review['master_evidence'] = self.proof('content/master.json', {'status': 'locked', 'timeline': master, 'fps': 24})
        review['output_evidence'] = self.proof('output/sample.bin', 'synthetic preview')
        approval = {k: review[k] for k in ('gate', 'review_scope', 'timeline', 'fps', 'total_frames')}
        if gate == 'gate-5':
            approval['locale'] = review['locale']
        approval.update(repository_id='test', project_id='p', master_sha256=review['master_evidence']['sha256'],
                        output_sha256=review['output_evidence']['sha256'], approved_by='fixture', approved_at='2026-11-05')
        review['approval_evidence'] = self.proof('content/gate-receipt.json', approval)
        self.contract['review'] = review
        return self.contract

    def test_handoff_checks_hashes_without_granting_approval(self):
        self.assertFalse(validator.validate_contract(self.root, self.contract)['approval_granted'])
        (self.root / 'content/definition.json').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'changed'): validator.validate_contract(self.root, self.contract)

    def test_hidden_policy_requires_explicit_approval_and_static_pose_cannot_be_components(self):
        self.contract['hidden_region_policy'] = 'inferred-repair'
        with self.assertRaises(ValueError): validator.validate_contract(self.root, self.contract)
        policy = {key: self.contract[key] for key in ('repository_id', 'project_id', 'route_id', 'hidden_region_policy')}
        policy.update(upstream_sha256=[ref['sha256'] for ref in self.contract['upstream']], approved_by='fixture', approved_at='2026-11-05')
        self.contract['policy_approval'] = self.proof('content/policy.json', policy)
        validator.validate_contract(self.root, self.contract)
        self.contract['route_id'] = 'static-pose'
        with self.assertRaisesRegex(ValueError, 'asset_unit'): validator.validate_contract(self.root, self.contract)

    def test_locked_upstream_cannot_be_declared_over_a_draft_artifact(self):
        self.contract['upstream'][0].update(self.proof('content/definition.json', {'status': 'needs-sync', 'version': 'v1'}))
        with self.assertRaisesRegex(ValueError, 'declarations'): validator.validate_contract(self.root, self.contract)

    def test_sample_and_full_film_are_distinct_and_receipts_are_bound(self):
        contract = self.gate_contract()
        validator.validate_contract(self.root, contract)
        contract['review']['review_scope'] = 'full-film'
        with self.assertRaisesRegex(ValueError, 'scope'): validator.validate_contract(self.root, contract)
        contract = self.gate_contract('gate-5')
        validator.validate_contract(self.root, contract)
        contract['review']['timeline'] = contract['review']['timeline'][:3]
        with self.assertRaisesRegex(ValueError, 'all shots'): validator.validate_contract(self.root, contract)

    def test_gate5_receipt_cannot_be_reused_for_another_locale(self):
        contract = self.gate_contract('gate-5')
        contract['review']['locale'] = 'en-US'
        with self.assertRaisesRegex(ValueError, 'different scope/output'): validator.validate_contract(self.root, contract)

    def test_stale_receipt_does_not_approve_changed_output_or_duration(self):
        contract = self.gate_contract()
        contract['review']['output_evidence'] = self.proof('output/revised.bin', 'changed preview')
        with self.assertRaisesRegex(ValueError, 'different scope/output'): validator.validate_contract(self.root, contract)
        contract = self.gate_contract()
        contract['review']['timeline'] = copy.deepcopy(contract['review']['timeline'])
        contract['review']['timeline'][0]['frames'] = 25
        with self.assertRaisesRegex(ValueError, 'duration'): validator.validate_contract(self.root, contract)

    def test_preflight_requires_locked_installed_skill_and_external_capability(self):
        with self.assertRaises((ValueError, OSError)): validator.validate_contract(self.root, self.contract, True)
        runtime = validator.load_module('test_runtime', validator.PIPELINE / 'runtime.py')
        folder = self.root / '.agents/skills/shadow-puppet-part-splitter'; folder.mkdir(parents=True)
        (folder / 'SKILL.md').write_text('synthetic installed Skill')
        sha = runtime.tree(folder)
        runtime.write(self.root / 'skills.lock.json', {'skills': [{'name': folder.name, 'directory': 'skills/' + folder.name, 'requires': [], 'tree_sha256': sha, 'source_state': 'committed'}]})
        runtime.write(self.root / '.agents/skills-receipts.json', {folder.name: sha})
        with self.assertRaisesRegex(ValueError, 'Missing capability'): validator.validate_contract(self.root, self.contract, True)
        from importlib.metadata import version
        self.contract['capabilities'] = {'Pillow': {'kind': 'python-package', 'distribution': 'Pillow', 'version': version('Pillow')}}
        validator.validate_contract(self.root, self.contract, True)
        (folder / 'SKILL.md').write_text('locally edited')
        with self.assertRaisesRegex(ValueError, 'modified'): validator.validate_contract(self.root, self.contract, True)


if __name__ == '__main__':
    unittest.main()

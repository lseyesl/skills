"""Offline regression tests; real temporary Git repositories exercise locking."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import runtime as r
import skill_dependencies as dep


class PipelineTests(unittest.TestCase):
    def setUp(self):
        parent = Path(os.environ.get('SKILLS_TEST_TMP', Path(__file__).resolve().parents[3] / '.tmp/tests'))
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.root = Path(self.temp.name).resolve()
        (self.root / '.tmp').mkdir()
        r.write(self.root / 'assets.config.json', {'enabled': True, 'repository_id': 'test', 'bucket': 'owner/bucket'})

    def tearDown(self):
        self.temp.cleanup()

    def args(self, action, **kw):
        return argparse.Namespace(project=str(self.root), action=action, source=None, **kw)

    def lock(self, data=b'good', path='projects/p/a.png', status='unreviewed'):
        sha = hashlib.sha256(data).hexdigest()
        return {'repository_id': 'test', 'bucket': 'owner/bucket', 'assets': [{'path': path, 'sha256': sha, 'size': len(data), 'status': status, 'uri': 'hf://buckets/owner/bucket/test/objects/' + sha + '.png'}]}

    def materialize(self, lock, data=b'good'):
        p = r.safe(self.root, lock['assets'][0]['path'])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def git(self, root, *args):
        return subprocess.check_output(['git', '-C', str(root), *args], encoding='utf-8').strip()

    def commit(self, source):
        self.git(source, 'add', '--', 'skills', 'skills.json')
        self.git(source, '-c', 'user.name=Skill Tests', '-c', 'user.email=tests@example.invalid', 'commit', '--quiet', '-m', 'fixture')
        return self.git(source, 'rev-parse', 'HEAD')

    def setup_skills(self, requires=None):
        source = self.root / 'source-skills'
        source.mkdir()
        self.git(source, 'init', '--quiet')
        self.git(source, 'config', 'core.autocrlf', 'false')
        catalog = {
            'base': {'directory': 'skills/base', 'requires': [], 'optional': []},
            'example': {'directory': 'skills/example', 'requires': requires or [], 'optional': ['base']},
        }
        for name in catalog:
            p = source / 'skills' / name / 'SKILL.md'
            p.parent.mkdir(parents=True)
            p.write_bytes(f'---\nname: {name}\ndescription: fixture\n---\nOriginal\n'.encode())
        r.write(source / 'skills.json', {'schema_version': 1, 'skills': catalog})
        self.commit(source)
        args = self.args('update', skill=['example'], allow_working_tree=False, install_dir=None)
        args.source = str(source)
        r.skills(args)
        return source, args

    def install(self, args):
        args.action = 'install'
        r.skills(args)
        return self.root / '.agents/skills/example/SKILL.md'

    def test_path_escape(self):
        with self.assertRaises(ValueError):
            r.safe(self.root, '../outside')

    def test_runpy_project_wrapper_resolves_sibling_module(self):
        entry = Path(r.__file__).resolve()
        script = 'import runpy,sys;sys.argv=[sys.argv[1],"--help"];runpy.run_path(sys.argv[0],run_name="__main__")'
        proc = subprocess.run([sys.executable, '-c', script, str(entry)], cwd=self.root, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('assets', proc.stdout)

    def test_repository_without_hf_policy_is_blocked(self):
        (self.root / 'assets.config.json').unlink()
        with self.assertRaises(ValueError):
            r.assets(self.args('index'))

    def test_cross_project_lock_is_blocked(self):
        lock = self.lock(); lock['repository_id'] = 'other'
        r.write(self.root / 'assets.lock.json', lock)
        with self.assertRaises(ValueError):
            r.assets(self.args('pull'))

    def test_corrupt_local_asset(self):
        lock = self.lock(); p = self.materialize(lock, b'evil')
        with self.assertRaises(ValueError):
            r.asset_verify(self.root, lock)
        with patch.object(r, 'run') as run:
            with self.assertRaises(ValueError):
                r.asset_transfer(self.root, lock, 'pull')
            run.assert_not_called()
        self.assertEqual(p.read_bytes(), b'evil')

    def test_corrupt_download_does_not_install(self):
        lock = self.lock()
        def fake(*args): Path(args[4]).write_bytes(b'evil')
        with patch.object(r, 'run', side_effect=fake):
            with self.assertRaises(ValueError):
                r.asset_transfer(self.root, lock, 'pull')
        self.assertFalse(r.safe(self.root, lock['assets'][0]['path']).exists())

    def test_verified_download_install(self):
        lock = self.lock()
        def fake(*args): Path(args[4]).write_bytes(b'good')
        with patch.object(r, 'run', side_effect=fake):
            r.asset_transfer(self.root, lock, 'pull')
        self.assertEqual(r.asset_verify(self.root, lock), 1)

    def test_failed_upload_preserves_active_lock(self):
        active = {'repository_id': 'test', 'bucket': 'owner/bucket', 'assets': []}
        r.write(self.root / 'assets.lock.json', active)
        lock = self.lock(); self.materialize(lock)
        r.write(self.root / 'assets.pending.json', lock)
        with patch.object(r, 'asset_transfer', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):
                r.assets(self.args('push'))
        self.assertEqual(r.read(self.root / 'assets.lock.json'), active)

    def test_approved_change_requires_new_path(self):
        lock = self.lock(status='approved'); self.materialize(lock, b'new')
        r.write(self.root / 'assets.lock.json', lock)
        with self.assertRaises(ValueError):
            r.assets(self.args('index', bucket='owner/bucket', repository_id='test'))

    def test_duplicate_paths(self):
        lock = self.lock(); self.materialize(lock)
        lock['assets'].append(lock['assets'][0].copy())
        with self.assertRaises(ValueError):
            r.asset_verify(self.root, lock)

    def test_unchanged_locked_asset_preserves_identity_and_receipts_through_push(self):
        lock = self.lock(status='locked'); self.materialize(lock)
        lock['approval_policy'] = {'receipt_root': 'content/approvals'}
        record = lock['assets'][0]
        record.update(asset_id='hero', project_id='p', version='v1',
                      approved_by='reviewer', approved_at='2026-11-01',
                      approval_receipt='content/approvals/hero-v1.json',
                      extension={'reviewed_sha256': record['sha256']})
        r.write(self.root / 'assets.lock.json', lock)
        r.assets(self.args('index', bucket='owner/bucket', repository_id='test'))
        pending = r.read(self.root / 'assets.pending.json')
        self.assertEqual(pending['assets'], lock['assets'])
        self.assertEqual(pending['approval_policy'], lock['approval_policy'])
        self.assertEqual(r.read(self.root / 'assets.lock.json'), lock)
        with patch.object(r, 'asset_transfer') as transfer:
            r.assets(self.args('push'))
            transfer.assert_called_once_with(self.root, pending, 'push')
        self.assertEqual(r.read(self.root / 'assets.lock.json'), pending)

    def test_index_rejects_previous_manifest_from_other_namespace(self):
        lock = self.lock(); self.materialize(lock); lock['repository_id'] = 'other'
        r.write(self.root / 'assets.lock.json', lock)
        r.write(self.root / 'assets.pending.json', {'existing': 'candidate'})
        with self.assertRaisesRegex(ValueError, 'namespace'):
            r.assets(self.args('index', bucket='owner/bucket', repository_id='test'))
        self.assertEqual(r.read(self.root / 'assets.pending.json'), {'existing': 'candidate'})

    def test_missing_locked_asset_does_not_erase_formal_or_pending_lock(self):
        lock = self.lock(status='locked')
        r.write(self.root / 'assets.lock.json', lock)
        pending = {'previous': 'candidate'}
        r.write(self.root / 'assets.pending.json', pending)
        with self.assertRaisesRegex(ValueError, 'missing'):
            r.assets(self.args('index', bucket='owner/bucket', repository_id='test'))
        self.assertEqual(r.read(self.root / 'assets.lock.json'), lock)
        self.assertEqual(r.read(self.root / 'assets.pending.json'), pending)

    def test_filter_changes_cannot_remove_existing_records(self):
        lock = self.lock(); self.materialize(lock); lock['excluded_roots'] = ['projects']
        r.write(self.root / 'assets.lock.json', lock)
        r.assets(self.args('index', bucket='owner/bucket', repository_id='test'))
        self.assertEqual(r.read(self.root / 'assets.pending.json')['assets'], lock['assets'])

    def test_forget_is_explicit_and_does_not_delete_remote_or_local_bytes(self):
        lock = self.lock(status='locked'); p = self.materialize(lock)
        r.write(self.root / 'assets.lock.json', lock)
        args = self.args('forget', path=[lock['assets'][0]['path']], allow_locked=False)
        with self.assertRaises(ValueError): r.assets(args)
        args.allow_locked = True
        with patch.object(r, 'run') as run:
            r.assets(args)
            self.assertEqual(r.read(self.root / 'assets.lock.json'), lock)
            r.assets(self.args('push'))
            run.assert_not_called()
        self.assertEqual(p.read_bytes(), b'good')
        self.assertEqual(r.read(self.root / 'assets.lock.json')['assets'], [])

    def test_pending_lock_cannot_silently_drop_records(self):
        lock = self.lock(); r.write(self.root / 'assets.lock.json', lock)
        r.write(self.root / 'assets.pending.json', {**lock, 'assets': []})
        with patch.object(r, 'asset_transfer') as transfer:
            with self.assertRaisesRegex(ValueError, 'explicit forget'): r.assets(self.args('push'))
            transfer.assert_not_called()

    def test_required_dependencies_are_automatically_locked_and_installed(self):
        source, args = self.setup_skills(['base'])
        lock = r.read(self.root / 'skills.lock.json')
        self.assertEqual([s['name'] for s in lock['skills']], ['base', 'example'])
        self.install(args)
        self.assertTrue((self.root / '.agents/skills/base/SKILL.md').exists())

    def test_optional_dependencies_are_not_automatically_installed(self):
        source, args = self.setup_skills()
        self.install(args)
        self.assertFalse((self.root / '.agents/skills/base').exists())

    def test_missing_required_dependency_and_cycles_are_rejected(self):
        for catalog in [{'x': {'requires': ['missing']}}, {'x': {'requires': ['y']}, 'y': {'requires': ['x']}}]:
            with self.assertRaises(ValueError): dep.resolve(['x'], catalog)

    def test_tampered_lock_omitting_dependency_is_rejected(self):
        source, args = self.setup_skills(['base'])
        lock = r.read(self.root / 'skills.lock.json'); lock['skills'] = [lock['skills'][-1]]
        r.write(self.root / 'skills.lock.json', lock)
        with self.assertRaisesRegex(ValueError, 'Unknown required'): self.install(args)

    def test_clean_lf_and_crlf_checkouts_produce_identical_locks_and_installation(self):
        source, args = self.setup_skills()
        locked = r.read(self.root / 'skills.lock.json')
        clone = self.root / 'crlf-source'
        subprocess.run(['git', 'clone', '--config', 'core.autocrlf=true', '--quiet', '--local', str(source), str(clone)], check=True, capture_output=True)
        self.assertFalse(self.git(clone, 'status', '--porcelain'))
        self.assertIn(b'\r\n', (clone / 'skills/example/SKILL.md').read_bytes())
        args.source = str(clone); r.skills(args)
        self.assertEqual(r.read(self.root / 'skills.lock.json'), locked)
        dest = self.install(args)
        self.assertNotIn(b'\r\n', dest.read_bytes())

    def test_old_pinned_commit_installs_without_changing_source_head(self):
        source, args = self.setup_skills()
        expected = (source / 'skills/example/SKILL.md').read_bytes()
        (source / 'skills/example/SKILL.md').write_bytes(b'new version\n')
        head = self.commit(source)
        self.assertEqual(self.install(args).read_bytes(), expected)
        self.assertEqual(self.git(source, 'rev-parse', 'HEAD'), head)

    def test_committed_install_ignores_mutable_source_files(self):
        source, args = self.setup_skills()
        expected = (source / 'skills/example/SKILL.md').read_bytes()
        (source / 'skills/example/SKILL.md').write_bytes(b'work in progress\n')
        self.assertEqual(self.install(args).read_bytes(), expected)

    def test_non_ascii_paths_and_binary_skill_assets_are_preserved(self):
        source, args = self.setup_skills()
        binary = source / 'skills/example/assets/action.blend'
        binary.parent.mkdir(); binary.write_bytes(b'\x00BLENDER\r\n\xff\x00')
        note = source / 'skills/example/参考.md'
        note.write_bytes('中文参考\n'.encode('utf-8'))
        self.commit(source); r.skills(args)
        with patch.object(r, 'run', side_effect=AssertionError('No HF or external tool call')):
            self.install(args)
        installed = self.root / '.agents/skills/example'
        self.assertEqual((installed / 'assets/action.blend').read_bytes(), binary.read_bytes())
        self.assertEqual((installed / '参考.md').read_bytes(), note.read_bytes())

    def test_dirty_update_requires_explicit_opt_in(self):
        source, args = self.setup_skills()
        before = (self.root / 'skills.lock.json').read_bytes()
        (source / 'skills/example/SKILL.md').write_bytes(b'development\n')
        with self.assertRaisesRegex(ValueError, 'allow-working-tree'): r.skills(args)
        self.assertEqual((self.root / 'skills.lock.json').read_bytes(), before)
        args.allow_working_tree = True; r.skills(args)
        self.assertEqual(r.read(self.root / 'skills.lock.json')['skills'][0]['source_state'], 'working-tree')

    def test_staged_tampering_does_not_replace_existing_install(self):
        source, args = self.setup_skills()
        dest = self.install(args); before = dest.read_bytes()
        receipt = (self.root / '.agents/skills-receipts.json').read_bytes()
        original = r.stage_skill
        def tamper(*a):
            original(*a); (a[2] / 'SKILL.md').write_bytes(b'changed after validation\n')
        with patch.object(r, 'stage_skill', side_effect=tamper):
            with self.assertRaisesRegex(ValueError, 'Staged Skill differs'): r.skills(args)
        self.assertEqual(dest.read_bytes(), before)
        self.assertEqual((self.root / '.agents/skills-receipts.json').read_bytes(), receipt)

    def test_development_source_race_does_not_install(self):
        source, args = self.setup_skills()
        (source / 'skills/example/SKILL.md').write_bytes(b'development\n')
        args.allow_working_tree = True; r.skills(args); args.action = 'install'
        original = r.shutil.copytree
        def mutate(src, dest, **kw):
            (Path(src) / 'SKILL.md').write_bytes(b'changed during copying\n')
            return original(src, dest, **kw)
        with patch.object(r.shutil, 'copytree', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'Staged Skill differs'): r.skills(args)
        self.assertFalse((self.root / '.agents/skills/example').exists())

    def test_skill_local_edit_is_preserved(self):
        source, args = self.setup_skills(); dest = self.install(args)
        dest.write_bytes(b'user edit')
        with self.assertRaisesRegex(ValueError, 'Locally modified'): r.skills(args)
        self.assertEqual(dest.read_bytes(), b'user edit')

    def test_skill_repeated_install_and_source_free_check(self):
        source, args = self.setup_skills()
        self.install(args); self.install(args)
        args.action = 'check'; args.source = None
        with patch.object(r, 'git_bytes', side_effect=AssertionError('check must be offline')):
            r.skills(args)

    def test_failed_stage_keeps_previous_install(self):
        source, args = self.setup_skills(); dest = self.install(args); before = dest.read_bytes()
        with patch.object(r, 'stage_skill', side_effect=OSError('disk full')):
            with self.assertRaises(OSError): r.skills(args)
        self.assertEqual(dest.read_bytes(), before)

    def test_activation_failure_rolls_back_every_replaced_skill(self):
        source, args = self.setup_skills(['base']); dest = self.install(args)
        receipt = (self.root / '.agents/skills-receipts.json').read_bytes(); before = dest.read_bytes()
        original = r.os.replace
        def fail(src, dst):
            if Path(src).parent.name == 'incoming' and Path(src).name == 'example':
                raise OSError('activation failed')
            return original(src, dst)
        with patch.object(r.os, 'replace', side_effect=fail):
            with self.assertRaises(OSError): r.skills(args)
        self.assertEqual(dest.read_bytes(), before)
        self.assertEqual((self.root / '.agents/skills-receipts.json').read_bytes(), receipt)

    def test_legacy_lock_still_installs_exact_worktree_bytes(self):
        source, args = self.setup_skills()
        lock = r.read(self.root / 'skills.lock.json')
        r.write(self.root / 'skills.lock.json', {'skills': [{k: v for k, v in lock['skills'][0].items() if k not in {'content_format', 'requires'}}]})
        dest = self.install(args)
        self.assertEqual(dest.read_bytes(), (source / 'skills/example/SKILL.md').read_bytes())

    def test_claude_project_target_uses_separate_receipt(self):
        source, args = self.setup_skills(); args.install_dir = '.claude/skills'; r.skills(args)
        args.action = 'install'; r.skills(args)
        self.assertTrue((self.root / '.claude/skills/example/SKILL.md').exists())
        self.assertTrue((self.root / '.claude/skills-receipts.json').exists())


if __name__ == '__main__':
    unittest.main()

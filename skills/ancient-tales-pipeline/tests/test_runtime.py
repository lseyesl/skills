import argparse
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import runtime as r

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root = Path(self.temp.name).resolve()
        (self.root / '.tmp').mkdir()
        r.write(self.root/'assets.config.json',{'enabled':True,'repository_id':'test','bucket':'owner/bucket'})
    def tearDown(self):
        self.temp.cleanup()
    def lock(self, data=b'good', path='projects/p/a.png'):
        source = self.root / 'source'
        source.write_bytes(data)
        sha = r.digest(source)
        return {'repository_id':'test','bucket':'owner/bucket','assets':[{'path':path,'sha256':sha,'size':len(data),'uri':'hf://buckets/owner/bucket/test/objects/'+sha+'.png'}]}
    def test_path_escape(self):
        with self.assertRaises(ValueError): r.safe(self.root,'../outside')
    def test_repository_without_hf_policy_is_blocked(self):
        (self.root/'assets.config.json').unlink()
        with self.assertRaises(ValueError):r.assets(argparse.Namespace(project=str(self.root),action='index'))
    def test_cross_project_lock_is_blocked(self):
        lock=self.lock();lock['repository_id']='other'
        r.write(self.root/'assets.lock.json',lock)
        with self.assertRaises(ValueError):r.assets(argparse.Namespace(project=str(self.root),action='pull'))
    def test_corrupt_local_asset(self):
        lock=self.lock()
        p=r.safe(self.root,lock['assets'][0]['path']);p.parent.mkdir(parents=True);p.write_bytes(b'evil')
        with self.assertRaises(ValueError):r.asset_verify(self.root,lock)
        with patch.object(r,'run') as run:
            with self.assertRaises(ValueError):r.asset_transfer(self.root,lock,'pull')
            run.assert_not_called()
        self.assertEqual(p.read_bytes(),b'evil')
    def test_corrupt_download_does_not_install(self):
        lock=self.lock()
        def fake(*args):Path(args[4]).write_bytes(b'evil')
        with patch.object(r,'run',side_effect=fake):
            with self.assertRaises(ValueError):r.asset_transfer(self.root,lock,'pull')
        self.assertFalse(r.safe(self.root,lock['assets'][0]['path']).exists())
    def test_verified_download_install(self):
        lock=self.lock()
        def fake(*args):Path(args[4]).write_bytes(b'good')
        with patch.object(r,'run',side_effect=fake):r.asset_transfer(self.root,lock,'pull')
        self.assertEqual(r.asset_verify(self.root,lock),1)
    def test_failed_upload_preserves_active_lock(self):
        r.write(self.root/'assets.lock.json',{'assets':[]})
        lock=self.lock();p=r.safe(self.root,lock['assets'][0]['path']);p.parent.mkdir(parents=True);p.write_bytes(b'good')
        r.write(self.root/'assets.pending.json',lock)
        with patch.object(r,'asset_transfer',side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):r.assets(argparse.Namespace(project=str(self.root),action='push'))
        self.assertEqual(r.read(self.root/'assets.lock.json'),{'assets':[]})
    def test_approved_change_requires_new_path(self):
        lock=self.lock();lock['assets'][0]['status']='approved'
        p=r.safe(self.root,lock['assets'][0]['path']);p.parent.mkdir(parents=True);p.write_bytes(b'new')
        r.write(self.root/'assets.lock.json',lock)
        with self.assertRaises(ValueError):r.assets(argparse.Namespace(project=str(self.root),action='index',bucket='owner/bucket',repository_id='test'))
    def test_duplicate_paths(self):
        lock=self.lock();p=r.safe(self.root,lock['assets'][0]['path']);p.parent.mkdir(parents=True);p.write_bytes(b'good')
        lock['assets'].append(lock['assets'][0].copy())
        with self.assertRaises(ValueError):r.asset_verify(self.root,lock)
    def setup_skills(self):
        source=self.root/'source-skills';(source/'.git').mkdir(parents=True)
        skill=source/'skills/example';skill.mkdir(parents=True);(skill/'SKILL.md').write_text('original')
        r.write(self.root/'skills.lock.json',{'skills':[{'name':'example','directory':'skills/example'}]})
        args=argparse.Namespace(project=str(self.root),source=str(source),action='update')
        def fake(cmd,**kw):return 'a'*40 if 'rev-parse' in cmd else '?? skills/example'
        with patch.object(r.subprocess,'check_output',side_effect=fake):r.skills(args)
        return source,args,fake
    def test_skill_source_change_does_not_install(self):
        source,args,fake=self.setup_skills();(source/'skills/example/SKILL.md').write_text('changed')
        args.action='install'
        with patch.object(r.subprocess,'check_output',side_effect=fake):
            with self.assertRaises(ValueError):r.skills(args)
        self.assertFalse((self.root/'.agents/skills/example').exists())
    def test_skill_local_edit_is_preserved(self):
        source,args,fake=self.setup_skills();args.action='install'
        with patch.object(r.subprocess,'check_output',side_effect=fake),patch.object(r.subprocess,'run'):r.skills(args)
        dest=self.root/'.agents/skills/example/SKILL.md';dest.write_text('user edit')
        with patch.object(r.subprocess,'check_output',side_effect=fake):
            with self.assertRaises(ValueError):r.skills(args)
        self.assertEqual(dest.read_text(),'user edit')
    def test_skill_repeated_install_and_check(self):
        source,args,fake=self.setup_skills()
        with patch.object(r.subprocess,'check_output',side_effect=fake),patch.object(r.subprocess,'run'):
            for action in ['install','install','check']:
                args.action=action;r.skills(args)
    def test_failed_skill_copy_keeps_previous_install(self):
        source,args,fake=self.setup_skills();args.action='install'
        with patch.object(r.subprocess,'check_output',side_effect=fake),patch.object(r.subprocess,'run'):r.skills(args)
        dest=self.root/'.agents/skills/example/SKILL.md'
        with patch.object(r.subprocess,'check_output',side_effect=fake),patch.object(r.subprocess,'run'),patch.object(r.shutil,'copytree',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):r.skills(args)
        self.assertEqual(dest.read_text(),'original')

if __name__=='__main__':unittest.main()

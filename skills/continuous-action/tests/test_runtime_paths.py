import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('runtime_paths', Path(__file__).resolve().parents[1] / 'scripts/runtime_paths.py')
paths = importlib.util.module_from_spec(spec); spec.loader.exec_module(paths)


class RuntimePathsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def test_source_and_both_installed_layouts_write_into_consuming_project(self):
        for prefix in ('', '.agents', '.claude'):
            with self.subTest(prefix=prefix):
                skill = self.root / prefix / 'skills/continuous-action'; skill.mkdir(parents=True)
                (skill / 'catalog.json').write_text('protected')
                output = paths.prepare_output(skill)
                self.assertEqual(output.parent, self.root / '.tmp/continuous-action')
                self.assertEqual((skill / 'catalog.json').read_text(), 'protected')

    def test_explicit_project_and_output_override_layout(self):
        skill = self.root / 'library/skills/continuous-action'; skill.mkdir(parents=True)
        project = self.root / 'project'
        self.assertEqual(paths.prepare_output(skill, project).parent, project / '.tmp/continuous-action')
        output = self.root / 'deliverables/action-v1'
        self.assertEqual(paths.prepare_output(skill, project, output), output)
        (output / 'frame.png').write_bytes(b'existing')
        with self.assertRaisesRegex(ValueError, 'empty'): paths.prepare_output(skill, project, output)
        self.assertEqual((output / 'frame.png').read_bytes(), b'existing')

    def test_global_install_uses_calling_project_instead_of_global_config_root(self):
        skill = self.root / '.codex/skills/continuous-action'
        self.assertEqual(paths.project_root(skill, cwd=self.root / 'consumer'), self.root / 'consumer')

    def test_rejects_resource_and_install_container_output(self):
        skill = self.root / '.agents/skills/continuous-action'; skill.mkdir(parents=True)
        for output in (skill / 'assets/run', self.root / '.agents/.tmp/run', skill.parent):
            with self.subTest(output=output), self.assertRaisesRegex(ValueError, 'overlaps'):
                paths.prepare_output(skill, output=output)

    def test_rejects_symlink_into_resources_when_supported(self):
        skill = self.root / '.agents/skills/continuous-action'; skill.mkdir(parents=True)
        link = self.root / 'alias'
        try:
            link.symlink_to(skill, target_is_directory=True)
        except OSError as exc:
            self.skipTest('Symlinks unavailable on this host: ' + str(exc))
        with self.assertRaisesRegex(ValueError, 'overlaps'):
            paths.prepare_output(skill, output=link / 'run')


if __name__ == '__main__':
    unittest.main()

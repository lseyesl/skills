import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('library_check', ROOT / 'tools/check.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class LibraryChecks(unittest.TestCase):
    def setUp(self):
        parent = Path(os.environ.get('SKILLS_TEST_TMP', ROOT / '.tmp/tests'))
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.root = Path(self.temp.name)
        folder = self.root / 'skills/example'
        folder.mkdir(parents=True)
        (folder / 'SKILL.md').write_text('---\nname: example\ndescription: test\n---\nBody\n', encoding='utf-8')
        (self.root / 'index.md').write_text('[Example](skills/example/SKILL.md)\n', encoding='utf-8')
        self.registry = {'schema_version': 1, 'skills': {'example': {'directory': 'skills/example', 'requires': [], 'optional': []}}}
        self.save()

    def save(self):
        (self.root / 'skills.json').write_text(json.dumps(self.registry), encoding='utf-8')

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_library(self):
        self.assertEqual(check.validate_library(self.root)['skills'], 1)

    def test_missing_dependency_fails(self):
        self.registry['skills']['example']['requires'] = ['absent']; self.save()
        with self.assertRaises(ValueError): check.validate_library(self.root)

    def test_entry_missing_from_manifest_fails(self):
        self.registry['skills'].clear(); self.save()
        with self.assertRaises(ValueError): check.validate_library(self.root)

    def test_invalid_frontmatter_fails(self):
        (self.root / 'skills/example/SKILL.md').write_text('---\nname: wrong\n---\n', encoding='utf-8')
        with self.assertRaises(ValueError): check.validate_library(self.root)

    def test_broken_link_fails(self):
        with (self.root / 'skills/example/SKILL.md').open('a', encoding='utf-8') as f: f.write('[Missing](references/missing.md)\n')
        with self.assertRaises(ValueError): check.validate_library(self.root)

    def test_historical_docs_are_not_active_inputs(self):
        p = self.root / 'skills/example/history/retired.md'; p.parent.mkdir(); p.write_text('[old](missing.md)', encoding='utf-8')
        self.assertEqual(check.validate_library(self.root)['skills'], 1)

    def test_active_link_to_history_fails(self):
        self.test_historical_docs_are_not_active_inputs()
        with (self.root / 'skills/example/SKILL.md').open('a', encoding='utf-8') as f: f.write('[old](history/retired.md)\n')
        with self.assertRaises(ValueError): check.validate_library(self.root)

    def test_required_cycle_fails(self):
        self.registry['skills']['example']['requires'] = ['other']
        self.registry['skills']['other'] = {'directory': 'skills/other', 'requires': ['example']}
        self.save()
        with self.assertRaises(ValueError): check.validate_library(self.root)

    def production_fixture(self):
        folder = self.root / 'skills/ancient-tales-production'
        (folder / 'references').mkdir(parents=True)
        (folder / 'SKILL.md').write_text('---\nname: ancient-tales-production\ndescription: production\n---\n', encoding='utf-8')
        with (self.root / 'index.md').open('a', encoding='utf-8') as f: f.write('[Production](skills/ancient-tales-production/SKILL.md)\n')
        self.registry['skills']['ancient-tales-production'] = {'directory': 'skills/ancient-tales-production', 'requires': []}
        self.save()
        return folder

    def test_active_production_cannot_route_to_retired_backend(self):
        folder = self.production_fixture()
        (folder / 'references/route.md').write_text('[backend](https://github.com/example/repo/blob/main/docs/backend/legacy-vault/old.md)', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'retired backend'): check.validate_library(self.root)

    def test_retired_output_path_is_rejected_even_inside_code_examples(self):
        folder = self.production_fixture()
        (folder / 'references/output.md').write_text('Output: `projects/中国神话视频/项目/<主题>/`', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'retired Vault output'): check.validate_library(self.root)

    def test_production_library_route_cannot_escape_installed_version(self):
        folder = self.production_fixture()
        (folder / 'references/route.md').write_text('[tool](https://github.com/lseyesl/skills/blob/main/skills/example/SKILL.md)', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'locked relative'): check.validate_library(self.root)

    def test_optional_cycle_is_allowed(self):
        other = self.root / 'skills/other'; other.mkdir()
        (other / 'SKILL.md').write_text('---\nname: other\ndescription: test\n---\n', encoding='utf-8')
        with (self.root / 'index.md').open('a', encoding='utf-8') as f: f.write('[Other](skills/other/SKILL.md)\n')
        self.registry['skills']['example']['optional'] = ['other']
        self.registry['skills']['other'] = {'directory': 'skills/other', 'requires': [], 'optional': ['example']}
        self.save()
        self.assertEqual(check.validate_library(self.root)['skills'], 2)


if __name__ == '__main__':
    unittest.main()

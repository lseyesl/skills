#!/usr/bin/env python3
"""Shared local/CI entrypoint. Blender stays opt-in; no HF/API calls."""
import argparse
from pathlib import Path
import os
import re
import subprocess
import sys
from urllib.parse import unquote

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/ancient-tales-pipeline/scripts'))
import skill_dependencies as dependencies
import json


def validate_library(root):
    root = Path(root).resolve()
    catalog = dependencies.validate_registry(json.loads((root / 'skills.json').read_text(encoding='utf-8')))
    actual = {p.parent.name for p in (root / 'skills').glob('*/SKILL.md')}
    if actual != set(catalog):
        raise ValueError('skills.json differs from actual Skill entries')
    index = (root / 'index.md').read_text(encoding='utf-8')
    documents = [root / p for p in ('README.md', 'index.md', 'AGENTS.md') if (root / p).is_file()]
    for name, item in catalog.items():
        if item['directory'] + '/SKILL.md' not in index:
            raise ValueError('Skill missing from index: ' + name)
        folder = root / item['directory']
        text = (folder / 'SKILL.md').read_text(encoding='utf-8-sig')
        match = re.match(r'^---\r?\n(.*?)\r?\n---(?:\r?\n|$)', text, re.S)
        metadata = yaml.safe_load(match.group(1)) if match else None
        if not isinstance(metadata, dict) or metadata.get('name') != name or not isinstance(metadata.get('description'), str) or not metadata['description'].strip():
            raise ValueError('Invalid Skill frontmatter: ' + name)
        interface = folder / 'agents/openai.yaml'
        if interface.exists() and not isinstance(yaml.safe_load(interface.read_text(encoding='utf-8')), dict):
            raise ValueError('Invalid agent metadata: ' + name)
        documents += [p for p in folder.rglob('*.md') if not any(part in {'history', 'evals', 'examples', '.tmp', '__pycache__'} for part in p.relative_to(folder).parts)]
    links = 0
    for p in documents:
        text = p.read_text(encoding='utf-8-sig')
        if p.is_relative_to(root / 'skills/ancient-tales-production/references') and 'projects/中国神话视频/' in text:
            raise ValueError('Active production reference uses a retired Vault output path: ' + str(p))
        for target in re.findall(r'\]\(([^)\n]+)\)', text):
            if '://' in target or target.startswith(('#', '<')):
                if p.is_relative_to(root / 'skills/ancient-tales-production') and re.match(r'https?://github\.com/lseyesl/skills/(blob|tree)/', target):
                    raise ValueError('Use a locked relative Skill/tool link, not a remote library route: ' + str(p))
                if p.is_relative_to(root / 'skills/ancient-tales-production') and ('/legacy-vault/' in target or '/docs/archive/' in target):
                    raise ValueError('Active production reference routes into retired backend docs: ' + str(p))
                continue
            rel = unquote(target.split('#')[0])
            if '<' in rel or not rel:
                continue
            dest = (p.parent / rel).resolve()
            if not dest.exists():
                raise ValueError(f'Broken relative link: {p.relative_to(root)} -> {rel}')
            if dest.is_relative_to(root) and 'history' in dest.relative_to(root).parts:
                raise ValueError('Active document routes into history: ' + str(p))
            links += 1
    return {'skills': len(catalog), 'documents': len(documents), 'relative_links': links}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', choices=['lightweight', 'metadata', 'blender'], default='lightweight')
    parser.add_argument('--blender', help='Explicit Blender executable for optional real-engine tests')
    args = parser.parse_args()
    print('LIBRARY_CHECK_OK', validate_library(ROOT), flush=True)
    if args.group == 'metadata':
        return
    temp = ROOT / '.tmp/tests'
    temp.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1', 'SKILLS_TEST_TMP': str(temp), 'TMPDIR': str(temp), 'TMP': str(temp), 'TEMP': str(temp)}
    if args.group == 'blender':
        if not args.blender:
            parser.error('--group blender requires --blender; Blender is never installed automatically')
        subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'skills/shadow-puppet-part-splitter/tests/blender_smoke.py'), '--blender', args.blender], cwd=ROOT, env=env, check=True)
        return
    suites = [
        'skills/ancient-tales-pipeline/tests/test_runtime.py',
        'tests/test_library_checks.py',
        'skills/epub-xhtml-to-markdown/tests/test_converter.py',
        'skills/shadow-puppet-part-splitter/tests/test_puppet.py',
        'skills/shadow-puppet-part-splitter/tests/test_toolbox.py',
        'skills/blender-python-modeling/tests/test_reference_review.py',
        'skills/blender-python-modeling/scripts/test_module_ledger.py',
    ]
    for suite in suites:
        print('RUN', suite, flush=True)
        subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / suite)], cwd=ROOT, env=env, check=True)
    print('LIGHTWEIGHT_CHECKS_OK', len(suites), 'suites', flush=True)


if __name__ == '__main__':
    main()

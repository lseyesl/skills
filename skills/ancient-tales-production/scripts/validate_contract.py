"""Offline handoff validation/preflight; never grants approval or runs a backend."""
import argparse
import importlib.util
import json
import os
import re
from pathlib import Path
from types import SimpleNamespace

SKILL = Path(__file__).resolve().parents[1]
PIPELINE = SKILL.parent / 'ancient-tales-pipeline' / 'scripts'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


assets = load_module('handoff_asset_contract', PIPELINE / 'asset_contract.py')


def routes():
    return json.loads((SKILL / 'references/routes.json').read_text(encoding='utf-8'))['routes']


def evidence(root, ref):
    if not isinstance(ref, dict):
        raise ValueError('Evidence needs path and sha256')
    path = assets.relative_file(root, assets.text_field(ref, 'path'))
    if not path.is_file() or assets.file_sha(path) != ref.get('sha256'):
        raise ValueError('Missing/changed evidence: ' + str(path))
    return path


def validate_review(review):
    if not isinstance(review, dict):
        raise ValueError('Review must be an object')
    gate, scope = review.get('gate'), review.get('review_scope')
    if gate not in {'gate-4', 'gate-5'} or scope != ('sample' if gate == 'gate-4' else 'full-film'):
        raise ValueError('Gate/review_scope mismatch')
    if gate == 'gate-5':
        assets.text_field(review, 'locale')
    master, actual = review.get('master_timeline'), review.get('timeline')
    def timeline(rows):
        if not isinstance(rows, list) or not rows:
            raise ValueError('Timeline must contain shots')
        result = {}
        for row in rows:
            shot = assets.text_field(row, 'shot_id')
            if shot in result or type(row.get('frames')) is not int or row['frames'] < 1:
                raise ValueError('Duplicate shot or invalid frames')
            result[shot] = row['frames']
        return result
    expected, rendered = timeline(master), timeline(actual)
    if type(review.get('fps')) is not int or review['fps'] < 1:
        raise ValueError('Invalid fps')
    if scope == 'sample' and not 3 <= len(rendered) <= 5:
        raise ValueError('Gate 4 requires 3-5 sample shots')
    if scope == 'full-film' and list(rendered) != list(expected):
        raise ValueError('Full-film review must cover all shots in master order')
    if any(shot not in expected or frames != expected[shot] for shot, frames in rendered.items()):
        raise ValueError('Shot identity/duration differs from locked master')
    if type(review.get('total_frames')) is not int or review['total_frames'] != sum(rendered.values()):
        raise ValueError('Review total_frames differs from timeline')
    for field in ('director_review_status', 'director_taste_review_status'):
        if review.get(field) != 'pass':
            raise ValueError('Review is not passed: ' + field)


def preflight(root, route, contract):
    runtime = load_module('handoff_runtime', PIPELINE / 'runtime.py')
    runtime.skills(SimpleNamespace(project=str(root), action='check', source=None))
    lock = runtime.read(root / 'skills.lock.json')
    locked = {entry['name'] for entry in lock['skills']}
    if not set(route['skills']).issubset(locked):
        raise ValueError('Selected route Skills are not installed and locked')
    capabilities = contract.get('capabilities', {})
    if not isinstance(capabilities, dict):
        raise ValueError('Capabilities must be an object')
    for name in route['external']:
        capability = capabilities.get(name, {})
        if not isinstance(capability, dict):
            raise ValueError('Capability must be an object: ' + name)
        kind = capability.get('kind')
        expected_kind = {'Pillow': 'python-package', 'sprite-gen': 'skill', 'image generation': 'service-evidence'}.get(name, 'executable')
        if kind != expected_kind:
            raise ValueError('Missing capability or incorrect provider kind: ' + name)
        if name == 'Pillow' and capability.get('distribution') != 'Pillow':
            raise ValueError('Incorrect distribution for Pillow capability')
        if kind in {'executable', 'skill'}:
            path = Path(assets.text_field(capability, 'path')).expanduser()
            path = path if path.is_absolute() else assets.relative_file(root, path.as_posix())
            if not path.is_file() or (kind == 'executable' and not os.access(path, os.X_OK)) or (kind == 'skill' and path.name != 'SKILL.md'):
                raise ValueError('Unavailable capability: ' + name)
            declared_version = assets.text_field(capability, 'version')
            if name == 'Blender >=4.5':
                match = re.search(r'(\d+)\.(\d+)', declared_version)
                if not match or tuple(map(int, match.groups())) < (4, 5):
                    raise ValueError('Declared Blender version must be >=4.5')
        elif kind == 'python-package':
            from importlib.metadata import version, PackageNotFoundError
            try:
                found = version(assets.text_field(capability, 'distribution'))
            except PackageNotFoundError as exc:
                raise ValueError('Unavailable Python capability: ' + name) from exc
            if found != capability.get('version'):
                raise ValueError('Python capability version mismatch: ' + name)
        elif kind == 'service-evidence':
            proof = json.loads(evidence(root, capability.get('evidence')).read_text(encoding='utf-8'))
            if not isinstance(proof, dict) or proof.get('capability') != name or proof.get('available') is not True:
                raise ValueError('Unavailable service capability: ' + name)
            assets.text_field(proof, 'checked_at')
            assets.text_field(proof, 'version')
        else:
            raise ValueError('Missing capability: ' + name)


def validate_contract(root, contract, check_environment=False):
    root = Path(root).resolve()
    if not isinstance(contract, dict) or contract.get('schema_version') != 1:
        raise ValueError('Handoff contract requires schema_version=1')
    for key in ('repository_id', 'project_id', 'visual_profile', 'implementation_profile'):
        assets.text_field(contract, key)
    route = routes().get(contract.get('route_id'))
    if route is None or contract.get('asset_unit') != route['asset_unit']:
        raise ValueError('Unknown route or incompatible asset_unit')
    if 'hidden_region_policies' in route:
        if contract.get('hidden_region_policy') not in route['hidden_region_policies']:
            raise ValueError('Missing/invalid hidden_region_policy')

    upstream = contract.get('upstream')
    if not isinstance(upstream, list) or not upstream:
        raise ValueError('Formal handoff requires locked upstream references')
    for ref in upstream:
        if not isinstance(ref, dict):
            raise ValueError('Upstream reference must be an object')
        if ref.get('status') != 'locked':
            raise ValueError('Upstream is not locked')
        assets.text_field(ref, 'version')
        path = evidence(root, ref)
        if path.suffix == '.json':
            artifact = json.loads(path.read_text(encoding='utf-8-sig'))
            if not isinstance(artifact, dict) or artifact.get('status') != 'locked' or artifact.get('version') != ref['version']:
                raise ValueError('Upstream declarations differ from artifact')
    if contract.get('hidden_region_policy') == 'inferred-repair':
        policy_path = evidence(root, contract.get('policy_approval'))
        policy = json.loads(policy_path.read_text(encoding='utf-8-sig'))
        expected = {key: contract[key] for key in ('repository_id', 'project_id', 'route_id', 'hidden_region_policy')}
        expected['upstream_sha256'] = [ref['sha256'] for ref in upstream]
        if not isinstance(policy, dict) or any(policy.get(key) != value for key, value in expected.items()):
            raise ValueError('Policy approval does not bind this handoff')
        assets.validate_attribution(policy)
    if route['backend_required'] or 'review' in contract:
        backend = contract.get('backend', {})
        entry = assets.relative_file(root, assets.text_field(backend, 'entrypoint'))
        if not entry.is_file() or any(part in {'.agents', '.claude', 'skills'} for part in Path(backend['entrypoint']).parts):
            raise ValueError('Backend must be a project entrypoint, not a Skill')
        evidence(root, backend.get('validation_evidence'))
    if 'assets_manifest' in contract:
        manifest_path = evidence(root, contract['assets_manifest'])
        manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
        if not isinstance(manifest, dict) or manifest.get('repository_id') != contract['repository_id']:
            raise ValueError('Handoff asset repository mismatch')
        assets.validate_manifest(manifest, root=root, strict=True, expected_project=contract['project_id'])
        if not manifest['assets']:
            raise ValueError('Formal handoff requires nonempty assets')
        if any(asset['status'] != 'locked' for asset in manifest['assets']):
            raise ValueError('Formal backend handoff requires locked assets')
        for asset in manifest['assets']:
            path = assets.relative_file(root, asset['path'])
            if not path.is_file() or path.stat().st_size != asset['size'] or assets.file_sha(path) != asset['sha256']:
                raise ValueError('Missing/corrupt handoff asset: ' + asset['path'])
    if 'review' in contract:
        if 'assets_manifest' not in contract:
            raise ValueError('Gate review requires an assets_manifest')
        validate_review(contract['review'])
        review = contract['review']
        master_path = evidence(root, review.get('master_evidence'))
        master = json.loads(master_path.read_text(encoding='utf-8-sig'))
        if not isinstance(master, dict) or master.get('status') != 'locked' or master.get('timeline') != review['master_timeline'] or master.get('fps') != review['fps']:
            raise ValueError('Review declarations differ from locked master evidence')
        evidence(root, review.get('output_evidence'))
        approval_path = evidence(root, review.get('approval_evidence'))
        approval = json.loads(approval_path.read_text(encoding='utf-8-sig'))
        expected = {key: review[key] for key in ('gate', 'review_scope', 'timeline', 'fps', 'total_frames')}
        if review['gate'] == 'gate-5':
            expected['locale'] = review['locale']
        expected.update(repository_id=contract['repository_id'], project_id=contract['project_id'],
                        master_sha256=review['master_evidence']['sha256'], output_sha256=review['output_evidence']['sha256'])
        if not isinstance(approval, dict) or any(approval.get(key) != value for key, value in expected.items()):
            raise ValueError('Gate approval evidence is bound to different scope/output')
        assets.validate_attribution(approval)
    if check_environment:
        preflight(root, route, contract)
    scope = 'gate-review' if 'review' in contract else 'assets' if 'assets_manifest' in contract else 'inputs'
    return {'route': contract['route_id'], 'validation': 'pass', 'validation_scope': scope,
            'environment_checked': check_environment, 'approval_granted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    try:
        contract = json.loads(args.contract.read_text(encoding='utf-8-sig'))
        print(json.dumps(validate_contract(args.project, contract, args.preflight)))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, 'CONTRACT_INVALID: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()

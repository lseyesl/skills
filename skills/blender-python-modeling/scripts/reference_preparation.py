"""Fail-closed reference route and source-fidelity declarations, not image understanding.
Source fidelity, generated-view consistency and Blender calibration are separate gates.
"""
import hashlib
import json
from pathlib import Path

ROUTES = {'generated', 'existing_reviewed', 'single_view_sufficient', 'no_reference', 'user_waived', 'diagnostic_only'}


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _file(ref, base):
    if not isinstance(ref, dict) or not _text(ref.get('path')):
        raise ValueError('Explicit artifact path and sha256 required')
    path = (Path(base) / ref['path']).resolve()
    if not path.is_file() or not path.stat().st_size:
        raise RuntimeError('Missing/empty reference evidence: ' + str(path))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if ref.get('sha256') != digest:
        raise RuntimeError('Reference evidence changed: ' + str(path))
    return str(path), digest


def _files(items, base, *, nonempty=True):
    if not isinstance(items, list) or (nonempty and not items):
        raise ValueError('Explicit reference artifact list required')
    records = [_file(item, base) for item in items]
    if len(set(records)) != len(records):
        raise ValueError('Duplicate reference artifact')
    return set(records)


def require_source_fidelity(path, expected_sources, expected_guides):
    path = Path(path).resolve()
    review = json.loads(path.read_text())
    if review.get('schema_version') != 1 or review.get('status') != 'passed':
        raise RuntimeError('Source fidelity has not passed; view consistency alone cannot authorize reconstruction')
    if not _text(review.get('reviewer')) or not _text(review.get('scope')):
        raise ValueError('Identified source reviewer and explicit scope required')
    if review.get('unresolved_issues') != []:
        raise RuntimeError('Unresolved source-fidelity issues remain')
    sources = _files(review.get('source_images'), path.parent)
    generated = _files(review.get('generated_images'), path.parent)
    if sources != expected_sources or not expected_guides <= generated:
        raise RuntimeError('Source fidelity does not bind the actual source/guide images')
    checks = review.get('invariants')
    if not isinstance(checks, list) or not checks:
        raise ValueError('Observed source invariants required')
    ids = set(); critical = 0
    for item in checks:
        if not _text(item.get('id')) or item['id'] in ids:
            raise ValueError('Unique source invariant IDs required')
        ids.add(item['id'])
        if item.get('evidence_type') != 'observed':
            raise ValueError('Do not certify inferred/hidden geometry as source fidelity')
        if type(item.get('critical')) is not bool:
            raise ValueError('Explicit criticality required')
        critical += item['critical']
        if item.get('status') != 'passed':
            raise RuntimeError('Unmatched source invariant: ' + item['id'])
        if not all(_text(item.get(k)) for k in ('source_region', 'generated_region', 'finding')):
            raise ValueError('Actual source/candidate regional comparison required')
        _files(item.get('evidence'), path.parent)
    if not critical:
        raise ValueError('At least one critical observed identity/structure invariant required')
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'scope': review['scope'], 'pixel_agreement_automatically_verified': False}


def require_preparation(path, task_id, *, mode, construction_images=(), allow_diagnostic=False):
    if path is None:
        raise ValueError('Record reference preparation route before construction; do not silently skip concept-multiview-sheet')
    path = Path(path).resolve(); decision = json.loads(path.read_text())
    if decision.get('schema_version') != 1 or decision.get('task_id') != task_id:
        raise ValueError('Reference decision identity/schema mismatch')
    if not all(_text(decision.get(k)) for k in ('purpose', 'reason')):
        raise ValueError('State intended use and route rationale')
    route = decision.get('route')
    if route not in ROUTES or mode not in {'reference', 'original', 'waived'}:
        raise ValueError('Explicit supported route/mode required')
    sources = _files(decision.get('source_images'), path.parent, nonempty=route != 'no_reference')
    guides = _files(decision.get('construction_images'), path.parent, nonempty=route not in {'no_reference', 'user_waived', 'diagnostic_only'})
    actual = {str(Path(p).resolve()) for p in construction_images}
    if actual and actual != {p for p, digest in guides}:
        raise RuntimeError('Decision does not match the actual construction guides')
    if route == 'no_reference':
        if mode != 'original' or sources or guides or actual:
            raise ValueError('A visual-reference task cannot be reclassified as original/no-reference')
    elif route == 'user_waived':
        if mode != 'waived' or not _text(decision.get('user_waiver')):
            raise ValueError('Actual existing user waiver required; Agent preference is not a waiver')
    elif route == 'diagnostic_only':
        if not allow_diagnostic:
            raise RuntimeError('Diagnostic-only references cannot authorize accepted construction')
    else:
        if mode != 'reference':
            raise ValueError('Visual reconstruction route requires reference mode')
        facts = decision.get('facts', {})
        if facts.get('projection') not in {'perspective', 'orthographic', 'unknown'} or any(
                type(facts.get(k)) is not bool for k in ('needs_hidden_shape', 'needs_pose_normalization')):
            raise ValueError('Record source projection, hidden-shape and pose-normalization facts')
        if route == 'single_view_sufficient' and (
                facts['needs_hidden_shape'] or facts['needs_pose_normalization'] or facts['projection'] != 'orthographic'):
            raise RuntimeError('Single-view bypass contradicts the declared task facts')
        if route in {'existing_reviewed', 'single_view_sufficient'}:
            review_path, digest = _file(decision.get('existing_review'), path.parent)
            existing = json.loads(Path(review_path).read_text())
            if existing.get('status') != 'passed' or not _text(existing.get('finding')):
                raise RuntimeError('Existing guide suitability has not been inspected')
            if _files(existing.get('construction_images'), Path(review_path).parent) != guides:
                raise RuntimeError('Existing-view review is stale or for different guides')
        if route == 'generated':
            if facts['needs_hidden_shape'] and len(guides) < 2:
                raise RuntimeError('Hidden-shape reconstruction needs separate reviewed construction views')
            if decision.get('selected_skill') != 'concept-multiview-sheet':
                raise ValueError('Generated reference route must record the selected Skill')
            generation_path, digest = _file(decision.get('generation_record'), path.parent)
            generation = json.loads(Path(generation_path).read_text())
            if generation.get('tool') != 'builtin-image-generation':
                raise ValueError('Record actual generation tool evidence, not just a planned Skill name')
            if _files(generation.get('reference_images'), Path(generation_path).parent) != sources:
                raise RuntimeError('Generation did not declare the actual source images as inputs')
            _file(generation.get('prompt'), Path(generation_path).parent)
            if not guides <= _files(generation.get('outputs'), Path(generation_path).parent):
                raise RuntimeError('Construction guides are not declared generation outputs')
            fidelity_path, digest = _file(decision.get('source_fidelity_review'), path.parent)
            require_source_fidelity(fidelity_path, sources, guides)
    return {'route': route, 'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'accepted_construction': route != 'diagnostic_only',
            'scope': 'route and evidence freshness only; actual image fidelity and decision facts require inspection'}

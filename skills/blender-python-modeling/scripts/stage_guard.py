"""Fresh, fail-closed receipts for project build/verify/render entry points.

Callbacks are ordinary project code. A passed receipt certifies callback checks
and artifact freshness only; it never confers visual or fidelity approval.
"""
from pathlib import Path
import hashlib
import json
import os
import time
import uuid


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def file_input(path):
    path = Path(path).resolve()
    if not path.is_file() or not path.stat().st_size:
        raise RuntimeError('Missing or empty stage artifact: ' + str(path))
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def _write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        tmp.write_text(json.dumps(value, indent=2, allow_nan=False))
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def run_stage(path, name, inputs, outputs, work, validate):
    """Invalidate old success before work, then pass only after explicit validation.

    outputs may be empty for a live-scene build; include current scene signatures
    in the next stage's inputs. For saved builds, supply the saved .blend path.
    """
    state = {'stage': name, 'run_id': uuid.uuid4().hex, 'status': 'running',
             'input_signature': None, 'artifacts': [],
             'scope': 'Stage execution and declared validation only'}
    _write(path, state)
    start = time.perf_counter()
    try:
        # A missing source or invalid input must invalidate old success too.
        state['input_signature'] = fingerprint(inputs() if callable(inputs) else inputs)
        _write(path, state)
        result = work()
        if validate(result) is not True:
            raise RuntimeError('Stage validator did not explicitly pass: ' + name)
        state['artifacts'] = [file_input(p) for p in outputs]
    except BaseException as exc:
        state.update(status='failed', error=str(exc), elapsed_seconds=time.perf_counter() - start)
        _write(path, state)
        raise
    state.update(status='passed', elapsed_seconds=time.perf_counter() - start)
    _write(path, state)
    return result


def require_stage(path, name, inputs, *, run_id=None):
    state = json.loads(Path(path).read_text())
    if state.get('stage') != name or state.get('status') != 'passed':
        raise RuntimeError('Predecessor stage has not passed: ' + name)
    if state.get('input_signature') != fingerprint(inputs() if callable(inputs) else inputs):
        raise RuntimeError('Predecessor inputs changed: ' + name)
    if run_id is not None and state.get('run_id') != run_id:
        raise RuntimeError('Receipt belongs to a different stage attempt')
    if not state.get('run_id'):
        raise RuntimeError('Missing stage attempt identity')
    for artifact in state.get('artifacts', []):
        if file_input(artifact['path']) != artifact:
            raise RuntimeError('Predecessor artifact changed: ' + artifact['path'])
    return state

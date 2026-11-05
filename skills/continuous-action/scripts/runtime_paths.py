"""Resolve read-only Skill resources separately from writable task outputs."""
from pathlib import Path
import tempfile


def project_root(skill_dir, explicit=None, cwd=None):
    if explicit is not None:
        return Path(explicit).expanduser().resolve()
    skill_dir = Path(skill_dir).resolve()
    if skill_dir.parent.name == 'skills':
        container = skill_dir.parent.parent
        if container.name in {'.agents', '.claude'} and container.parent != Path.home():
            return container.parent
        if container.name.startswith('.'):
            return Path(cwd or Path.cwd()).resolve()
        return container
    return Path(cwd or Path.cwd()).resolve()


def prepare_output(skill_dir, project=None, output=None, prefix='run-'):
    skill_dir = Path(skill_dir).resolve()
    root = project_root(skill_dir, project)
    destination = Path(output).expanduser().resolve() if output is not None else root / '.tmp/continuous-action'
    protected = [skill_dir]
    if skill_dir.parent.name == 'skills' and skill_dir.parent.parent.name in {'.agents', '.claude', '.codex'}:
        protected.append(skill_dir.parent.parent)
    for source in protected:
        if destination == source or source in destination.parents or destination in source.parents:
            raise ValueError('Output overlaps Skill resources or installation container')
    if output is None:
        destination.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix=prefix, dir=destination))
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError('Output directory must be empty: ' + str(destination))
    destination.mkdir(parents=True, exist_ok=True)
    return destination

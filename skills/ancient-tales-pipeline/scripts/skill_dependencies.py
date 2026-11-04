"""Validate the library registry and resolve required local Skill dependencies."""
import re

NAME = re.compile(r'^[a-z0-9][a-z0-9-]{0,63}$')


def validate_registry(data):
    if data.get('schema_version') != 1 or not isinstance(data.get('skills'), dict):
        raise ValueError('skills.json must contain schema_version=1 and a skills object')
    catalog = data['skills']
    for name, item in catalog.items():
        if not NAME.fullmatch(name) or item.get('directory') != 'skills/' + name:
            raise ValueError('Invalid Skill name/directory: ' + name)
        for field in ('requires', 'optional'):
            names = item.get(field, [])
            if not isinstance(names, list) or any(not isinstance(n, str) or n not in catalog for n in names):
                raise ValueError(f'Unknown {field} dependency in {name}')
            if len(set(names)) != len(names) or name in names:
                raise ValueError(f'Duplicate/self {field} dependency in {name}')
        if not isinstance(item.get('external', []), list):
            raise ValueError('external must be a list: ' + name)
        for requirement in item.get('external', []):
            if not isinstance(requirement, dict) or not requirement.get('name') or requirement.get('kind') not in {'tool', 'skill', 'python-package'} or not requirement.get('when'):
                raise ValueError('External dependency needs name, kind and when: ' + name)
    resolve(list(catalog), catalog)
    return catalog


def resolve(roots, catalog):
    order, visiting, done = [], set(), set()
    def visit(name):
        if name not in catalog:
            raise ValueError('Unknown required Skill: ' + name)
        if name in visiting:
            raise ValueError('Required Skill dependency cycle: ' + name)
        if name in done:
            return
        visiting.add(name)
        for dependency in catalog[name].get('requires', []):
            visit(dependency)
        visiting.remove(name)
        done.add(name)
        order.append(name)
    for name in roots:
        visit(name)
    return order


def validate_lock(entries):
    catalog = {}
    for item in entries:
        name = item['name']
        if not NAME.fullmatch(name) or name in catalog or item['directory'] != 'skills/' + name:
            raise ValueError('Invalid/duplicate locked Skill: ' + name)
        catalog[name] = item
    resolve(list(catalog), catalog)
    return catalog

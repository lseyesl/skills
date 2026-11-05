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


def validate_routes(data, catalog, owner='ancient-tales-production'):
    if data.get('schema_version') != 1 or not isinstance(data.get('routes'), dict) or not data['routes']:
        raise ValueError('routes.json requires schema_version=1 and nonempty routes')
    available = {owner, *catalog[owner].get('requires', []), *catalog[owner].get('optional', [])}
    for route_id, route in data['routes'].items():
        if not NAME.fullmatch(route_id) or not isinstance(route, dict):
            raise ValueError('Invalid route')
        providers = route.get('skills')
        if not isinstance(providers, list) or any(not isinstance(s, str) for s in providers) or len(set(providers)) != len(providers) or any(s not in available for s in providers):
            raise ValueError('Route Skill is not declared by owner: ' + route_id)
        external = {r['name'] for s in resolve([owner, *providers], catalog) for r in catalog[s].get('external', [])}
        needed = route.get('external')
        if not isinstance(needed, list) or any(name not in external for name in needed):
            raise ValueError('Undeclared route external capability: ' + route_id)
        if not isinstance(route.get('asset_unit'), str) or not route['asset_unit'] or type(route.get('backend_required')) is not bool:
            raise ValueError('Route needs asset_unit and backend_required: ' + route_id)
        policies = route.get('hidden_region_policies', [])
        if not isinstance(policies, list) or any(p not in {'concept-covered', 'inferred-repair'} for p in policies):
            raise ValueError('Invalid hidden-region route policy')
    return len(data['routes'])

"""Read-only Blender weight diagnostics and pure rolling measurement helpers.
Does not certify deformation, concentricity, visual quality, or engine export.
"""
import argparse
import json
import math


def weight_issues(rows, limit, tolerance=1e-4):
    if type(limit) is not int or limit < 1 or not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError('Invalid weight limits')
    issues = {'unweighted': [], 'sum_outside_tolerance': [], 'excess_influences': [], 'invalid_weights': []}
    for index, weights in enumerate(rows):
        if any(not math.isfinite(w) or w < 0 or w > 1 for w in weights):
            issues['invalid_weights'].append(index); continue
        active = [w for w in weights if w > 0]
        if not active: issues['unweighted'].append(index)
        if abs(sum(active)-1) > tolerance: issues['sum_outside_tolerance'].append(index)
        if len(active) > limit: issues['excess_influences'].append(index)
    return issues


def rolling_error(distance, radius, angle, tolerance):
    if not all(math.isfinite(v) for v in (distance, radius, angle, tolerance)) or radius <= 0 or tolerance < 0:
        raise ValueError('Invalid rolling measurement')
    error = abs(distance-radius*angle)
    return {'error': error, 'passed': error <= tolerance, 'scope': 'signed path arc length versus unwrapped radians only'}


def inspect_weights(obj, limit, tolerance=1e-4):
    if obj.type != 'MESH': raise ValueError('Target must be a mesh')
    rigs = [m.object for m in obj.modifiers if m.type == 'ARMATURE' and m.object]
    if len(rigs) != 1: raise ValueError('Expected one explicit target armature; inspect layered rigs separately')
    deform = {b.name for b in rigs[0].data.bones if b.use_deform}
    groups = {g.index: g.name for g in obj.vertex_groups}
    rows = [[g.weight for g in v.groups if groups[g.group] in deform] for v in obj.data.vertices]
    return {'object': obj.name, 'armature': rigs[0].name, 'vertices': len(rows),
            'issues': weight_issues(rows, limit, tolerance),
            'non_deform_groups': sorted(set(groups.values())-deform),
            'scope': 'weight numbers only; inspect topology, bone axes and actual poses separately'}


def main():
    import bpy
    import sys
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--object', required=True); parser.add_argument('--limit', type=int, required=True)
    parser.add_argument('--tolerance', type=float, default=1e-4)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    obj=bpy.data.objects.get(args.object)
    if obj is None: parser.error('Unknown object')
    print(json.dumps(inspect_weights(obj,args.limit,args.tolerance),ensure_ascii=False,indent=2))
if __name__=='__main__': main()

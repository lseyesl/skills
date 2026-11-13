"""Read-only, world-space content measurements. A metric never proves visual fidelity."""
import math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def _number(value, *, positive=False):
    if type(value) not in (int,float) or not math.isfinite(value) or (value<=0 if positive else value<0):
        raise ValueError('Finite positive/nonnegative measurement required')
    return value


def world_tree(obj):
    if obj.type not in {'MESH','CURVE'}:raise ValueError('Evaluable mesh/curve target required')
    graph=bpy.context.evaluated_depsgraph_get();ev=obj.evaluated_get(graph);mesh=ev.to_mesh()
    try:
        mesh.calc_loop_triangles()
        vertices=[ev.matrix_world@v.co for v in mesh.vertices]
        if not vertices or any(not all(math.isfinite(x) for x in p) for p in vertices):raise ValueError('Empty/nonfinite target')
        return BVHTree.FromPolygons(vertices,[list(t.vertices) for t in mesh.loop_triangles],all_triangles=True)
    finally:ev.to_mesh_clear()


def endpoint_proximity(target, endpoints, radii, tolerance):
    _number(tolerance)
    if not endpoints or len(endpoints)!=len(radii):raise ValueError('Explicit world endpoints and reach radii required')
    tree=world_tree(target);samples=[]
    for point,radius in zip(endpoints,radii):
        _number(radius,positive=True)
        if len(point)!=3 or not all(math.isfinite(x) for x in point):raise ValueError('Finite 3D endpoint required')
        hit,normal,face,distance=tree.find_nearest(Vector(point))
        samples.append({'endpoint':list(point),'reach':radius,'distance':distance,'passed':hit is not None and distance<=radius+tolerance})
    return {'passed':all(s['passed'] for s in samples),'samples':samples,'tolerance':tolerance,
            'scope':'distance to evaluated world surface only; proximity is not welding, load-bearing continuity or manifoldness'}


def axial_floor(target, origins, direction, *, minimum, maximum, distance, epsilon):
    for v in (minimum,maximum,distance,epsilon):_number(v,positive=True)
    if minimum>maximum or epsilon>=minimum or len(origins)<3:raise ValueError('At least three declared rays and coherent axial-thickness limits required')
    axis=Vector(direction)
    if len(axis)!=3 or not all(math.isfinite(x) for x in axis) or axis.length==0:raise ValueError('Finite nonzero direction required')
    axis.normalize();tree=world_tree(target);samples=[]
    for origin in origins:
        if len(origin)!=3 or not all(math.isfinite(x) for x in origin):raise ValueError('Finite ray origin required')
        first=tree.ray_cast(Vector(origin),axis,distance)[0];second=None
        if first is not None:second=tree.ray_cast(first+axis*epsilon,axis,distance)[0]
        thickness=(second-first).length if second is not None else None
        samples.append({'origin':list(origin),'first':list(first) if first is not None else None,
            'second':list(second) if second is not None else None,'axial_thickness':thickness,
            'passed':thickness is not None and minimum<=thickness<=maximum})
    return {'passed':all(s['passed'] for s in samples),'samples':samples,
            'scope':'two surface hits along declared interior-to-exterior rays; not minimum wall thickness or a watertightness proof'}


def connected_regions(obj, regions, paths):
    """Base-mesh vertex-region paths. Call after explicit welding/bridging, not on intersecting proxies."""
    if obj.type!='MESH' or not paths:raise ValueError('Mesh and explicit required region paths needed')
    count=len(obj.data.vertices);neighbors=[set() for _ in range(count)]
    for edge in obj.data.edges:
        a,b=edge.vertices;neighbors[a].add(b);neighbors[b].add(a)
    for name,indices in regions.items():
        if not indices or any(type(i) is not int or not 0<=i<count for i in indices):raise ValueError('Invalid seed region: '+name)
    results=[]
    for a,b in paths:
        if a not in regions or b not in regions:raise ValueError('Unknown connectivity region')
        seen=set(regions[a]);pending=list(seen);targets=set(regions[b])
        while pending:
            for i in neighbors[pending.pop()]-seen:seen.add(i);pending.append(i)
        results.append({'from':a,'to':b,'passed':bool(seen&targets)})
    return {'passed':all(p['passed'] for p in results),'paths':results,
            'scope':'base-mesh edge paths between explicit seeds; does not prove adequate cross-section, material strength or evaluated Boolean connectivity'}

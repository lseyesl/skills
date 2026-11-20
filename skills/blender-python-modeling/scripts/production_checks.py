"""Read-only production diagnostics. Facts/preflight never certify visual quality."""
import argparse
import json
import math


def correspondence_status(source_count,target_count,source_ids=None,target_ids=None):
    if source_count!=target_count:return 'incompatible-count'
    if source_ids is None or target_ids is None:return 'unknown-order'
    if len(source_ids)!=source_count or len(target_ids)!=target_count or len(set(source_ids))!=source_count or len(set(target_ids))!=target_count:
        return 'invalid-identity'
    return 'compatible' if list(source_ids)==list(target_ids) else 'incompatible-order'


def padding_pixels(measured_uv_gap,resolution):
    if not math.isfinite(measured_uv_gap) or measured_uv_gap<0 or type(resolution) is not int or resolution<=0:raise ValueError('Invalid measured gap/resolution')
    return measured_uv_gap*resolution


def optimization_result(before,after,metric,minimum_gain,protected):
    if metric not in before or metric not in after or not isinstance(protected,dict) or not protected:
        raise ValueError('Measured metric and explicit nonempty protected checks are required')
    values=(before[metric],after[metric],minimum_gain)
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in values):raise ValueError('Nonnegative measured values required')
    if any(v is False for v in protected.values()):return {'status':'negative','reason':'protected capability regressed'}
    if any(v is not True for v in protected.values()):return {'status':'unknown','reason':'unverified protected capability'}
    gain=before[metric]-after[metric]
    return {'status':'positive' if gain>=minimum_gain and gain>0 else 'not-demonstrated','gain':gain,'scope':'one measured lower-is-better metric and declared checks only'}


def triangle_budget(value):
    if value is not None and (type(value) is not int or value <= 0):
        raise ValueError('Triangle budget must be a positive integer or explicit None')
    return value


def _measure_mesh(mesh, matrix, require_closed, min_face_area, min_triangle_area, seam_weld_distance=None):
    import bmesh
    mesh.calc_loop_triangles()
    points=[matrix @ v.co for v in mesh.vertices]
    examples=[];bad_triangles=0
    for t in mesh.loop_triangles:
        a,b,c=(points[i] for i in t.vertices)
        area=(b-a).cross(c-a).length * .5
        if not math.isfinite(area) or area <= min_triangle_area:
            bad_triangles+=1
            if len(examples)<8:examples.append({'triangle':t.index,'polygon':t.polygon_index,
                'vertices':list(t.vertices),'area':area if math.isfinite(area) else None})
    bm=bmesh.new()
    try:
        bm.from_mesh(mesh)
        result={'vertices':len(mesh.vertices),'triangles':len(mesh.loop_triangles),
            'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),
            'inconsistent_winding_edges':sum(e.is_manifold and not e.is_contiguous for e in bm.edges),
            'loose_vertices':sum(not v.link_edges for v in bm.verts),'degenerate_faces':sum(f.calc_area()<=min_face_area for f in bm.faces),
            'degenerate_triangles':bad_triangles,'triangle_examples':examples,
            'nonfinite_vertices':sum(not all(math.isfinite(x) for x in p) for p in points),
            'require_closed':require_closed,'min_face_area':min_face_area,'face_area_space':'mesh-local',
            'min_triangle_area':min_triangle_area,'triangle_area_space':'world'}
        issues=[]
        if not result['vertices'] or not result['triangles']:issues.append('empty_geometry')
        for k in ('loose_vertices','degenerate_faces','degenerate_triangles','nonfinite_vertices','inconsistent_winding_edges'):
            if result[k]:issues.append(k)
        closure_edges=result['nonmanifold_edges']
        if seam_weld_distance is not None:
            welded=bm.copy()
            try:
                for v in welded.verts:v.co=matrix @ v.co
                bmesh.ops.remove_doubles(welded,verts=list(welded.verts),dist=seam_weld_distance)
                closure_edges=sum(not e.is_manifold for e in welded.edges)
                result['position_welded_topology']={'distance_world':seam_weld_distance,
                    'nonmanifold_edges':closure_edges,'scope':'temporary position-welded geometric closure only; raw attribute seams retained above'}
            finally:welded.free()
        if require_closed and closure_edges:issues.append('nonmanifold_edges')
        result['structural_issues']=issues
        return result
    finally:bm.free()


def inspect_mesh(obj,require_closed=False,min_face_area=0.0,*,min_triangle_area=5e-13,seam_weld_distance=None):
    """Read source topology and evaluated triangulation without applying modifiers.
    World-space triangle area includes object transforms; base topology is diagnostic,
    so a legal open control cage with a closing modifier is not rejected as a solid.
    """
    import bpy
    if obj.type not in {'MESH','CURVE'}:
        raise ValueError('Mesh/curve geometry target required')
    if type(require_closed) is not bool:raise ValueError('Explicit boolean closure requirement required')
    for value in (min_face_area,min_triangle_area):
        if type(value) not in (int,float) or not math.isfinite(value) or value<0:
            raise ValueError('Finite nonnegative area tolerances required')
    if seam_weld_distance is not None and (type(seam_weld_distance) not in (int,float) or not math.isfinite(seam_weld_distance) or seam_weld_distance<=0):raise ValueError('Explicit finite positive world seam tolerance required')
    bpy.context.view_layer.update()
    source=_measure_mesh(obj.data,obj.matrix_world,False,min_face_area,min_triangle_area) if obj.type=='MESH' else None
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    try:
        result=_measure_mesh(mesh,evaluated.matrix_world,require_closed,min_face_area,min_triangle_area,seam_weld_distance)
        result.update(object=obj.name,evaluated_vertices=result.pop('vertices'),evaluated_triangles=result.pop('triangles'),
            source_geometry=source,uv_layers=[layer.name for layer in mesh.uv_layers],
            shape_keys=list(obj.data.shape_keys.key_blocks.keys()) if getattr(obj.data,'shape_keys',None) else [],
            scope='source topology facts and evaluated world-space triangulation; not thickness/intersection/fidelity acceptance')
        return result
    finally:evaluated.to_mesh_clear()


def inspect_asset(objects,*,stage,max_triangles=None,require_closed=False,min_triangle_area=5e-13,seam_weld_distance=None):
    """Aggregate budget over the explicit asset whitelist, not a per-object allowance."""
    triangle_budget(max_triangles)
    if stage not in {'blockout','refine','delivery','reimport'}:
        raise ValueError('Explicit geometry inspection stage required')
    if not objects or len(set(objects))!=len(objects):
        raise ValueError('Explicit nonempty unique geometry whitelist required')
    measured={o.name:inspect_mesh(o,require_closed,min_triangle_area=min_triangle_area,seam_weld_distance=seam_weld_distance) for o in objects}
    total=sum(r['evaluated_triangles'] for r in measured.values())
    issues=[name+':'+issue for name,r in measured.items() for issue in r['structural_issues']]
    budget_ok=None if max_triangles is None else total<=max_triangles
    if budget_ok is False:issues.append('triangle_budget')
    return {'stage':stage,'objects':measured,'evaluated_triangles':total,'max_triangles':max_triangles,
        'budget_passed':budget_ok,'budget_scope':'aggregate evaluated triangles over explicit whitelist',
        'issues':issues,'passed':not issues,'ready_to_claim_complete':False,
        'scope':'geometry and declared budget only; no reference/visual/consumer certification'}


class GeometryRejected(RuntimeError):
    def __init__(self,report):
        self.report=report
        super().__init__('Geometry prerequisite failed: '+json.dumps(report,ensure_ascii=False,allow_nan=False))


def require_asset_geometry(objects,**kwargs):
    report=inspect_asset(objects,**kwargs)
    if not report['passed']:raise GeometryRejected(report)
    return report


def inspect_cloth(obj,colliders):
    cloth=[m for m in obj.modifiers if m.type=='CLOTH']
    if len(cloth)!=1:raise ValueError('Expected one Cloth modifier; inspect complex stacks separately')
    settings=cloth[0].collision_settings
    enabled=bool(settings.use_collision) and cloth[0].show_viewport;collection=getattr(settings,'collection',None)
    objects=set(collection.all_objects) if collection else None
    items=[]
    for collider in colliders:
        collision=any(m.type=='COLLISION' and m.show_viewport for m in collider.modifiers)
        included=objects is None or collider in objects
        items.append({'object':collider.name,'mesh':collider.type=='MESH','collision_modifier':collision,'in_collision_collection':included,
                      'configured':enabled and collider.type=='MESH' and collision and included})
    return {'object':obj.name,'object_collision_enabled':enabled,'self_collision':bool(settings.use_self_collision),
            'collision_distance':settings.distance_min,'colliders':items,
            'configuration_ready':enabled and bool(items) and all(i['configured'] for i in items),
            'scope':'configuration only; initial intersection, actual contact, cache and rendered animation remain unverified'}


def inspect_joint(obj):
    keys=obj.data.shape_keys if obj.type=='MESH' else None
    return {'object':obj.name,'modifiers':[{'name':m.name,'type':m.type,'preserve_volume':getattr(m,'use_deform_preserve_volume',None)} for m in obj.modifiers],
            'shape_keys':[{'name':k.name,'value':k.value,'relative_key':k.relative_key.name if k.relative_key else None} for k in keys.key_blocks] if keys else [],
            'scope':'configuration inventory, not bone-axis/weight/pose/deformation acceptance'}


def main():
    import bpy,sys
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--object',required=True);p.add_argument('--mode',choices=['mesh','cloth','joint'],default='mesh');p.add_argument('--require-closed',action='store_true');p.add_argument('--min-face-area',type=float,default=0.0);p.add_argument('--collider',action='append',default=[]);p.add_argument('--min-triangle-area',type=float,default=5e-13)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    obj=bpy.data.objects.get(a.object)
    if obj is None:p.error('Unknown target object')
    if a.mode=='mesh':result=inspect_mesh(obj,a.require_closed,a.min_face_area,min_triangle_area=a.min_triangle_area)
    elif a.mode=='joint':result=inspect_joint(obj)
    else:
        colliders=[bpy.data.objects.get(name) for name in a.collider]
        if any(c is None for c in colliders):p.error('Unknown collider')
        result=inspect_cloth(obj,colliders)
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
if __name__=='__main__':main()

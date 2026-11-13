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


def inspect_mesh(obj,require_closed=False,min_face_area=0.0):
    import bpy,bmesh
    if obj.type!='MESH' or not math.isfinite(min_face_area) or min_face_area<0:raise ValueError('Mesh target and nonnegative area tolerance required')
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles();bm=bmesh.new()
        try:
            bm.from_mesh(mesh)
            report={'object':obj.name,'evaluated_vertices':len(mesh.vertices),'evaluated_triangles':len(mesh.loop_triangles),
                    'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),
                    'loose_vertices':sum(not v.link_edges for v in bm.verts),'degenerate_faces':sum(f.calc_area()<=min_face_area for f in bm.faces),
                    'nonfinite_vertices':sum(not all(math.isfinite(x) for x in v.co) for v in mesh.vertices),
                    'uv_layers':[layer.name for layer in mesh.uv_layers],
                    'shape_keys':list(obj.data.shape_keys.key_blocks.keys()) if obj.data.shape_keys else [],
                    'require_closed':require_closed,'scope':'evaluated local-space mesh facts, not thickness/intersection/deformation/fidelity acceptance'}
            report['structural_issues']=[]
            for key in ('loose_vertices','degenerate_faces','nonfinite_vertices'):
                if report[key]:report['structural_issues'].append(key)
            if require_closed and report['nonmanifold_edges']:report['structural_issues'].append('nonmanifold_edges')
            return report
        finally:bm.free()
    finally:evaluated.to_mesh_clear()


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
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--object',required=True);p.add_argument('--mode',choices=['mesh','cloth','joint'],default='mesh');p.add_argument('--require-closed',action='store_true');p.add_argument('--min-face-area',type=float,default=0.0);p.add_argument('--collider',action='append',default=[])
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    obj=bpy.data.objects.get(a.object)
    if obj is None:p.error('Unknown target object')
    if a.mode=='mesh':result=inspect_mesh(obj,a.require_closed,a.min_face_area)
    elif a.mode=='joint':result=inspect_joint(obj)
    else:
        colliders=[bpy.data.objects.get(name) for name in a.collider]
        if any(c is None for c in colliders):p.error('Unknown collider')
        result=inspect_cloth(obj,colliders)
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
if __name__=='__main__':main()

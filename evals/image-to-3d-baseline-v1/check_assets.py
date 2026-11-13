"""Independent-of-recipe technical measurements. No golden geometry or visual scoring.
Runs in fresh Blender processes; reopens the source and actual GLB, then samples motion.
"""
import argparse,json,math,struct,sys
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def snapshot(objects):
    graph=bpy.context.evaluated_depsgraph_get();points=[];triangles=0;bad=0;degenerate=0;nonmanifold=0;winding=0;info={}
    for ob in objects:
        if ob.type not in {'MESH','CURVE'}:continue
        ev=ob.evaluated_get(graph);mesh=ev.to_mesh()
        try:
            mesh.calc_loop_triangles();triangles+=len(mesh.loop_triangles)
            world=[ev.matrix_world@v.co for v in mesh.vertices];points.extend(world)
            bad+=sum(not all(math.isfinite(x) for x in point) for point in world)
            degenerate+=sum((world[t.vertices[1]]-world[t.vertices[0]]).cross(world[t.vertices[2]]-world[t.vertices[0]]).length<1e-12 for t in mesh.loop_triangles)
            bm=bmesh.new();bm.from_mesh(mesh);nonmanifold+=sum(not e.is_manifold for e in bm.edges);winding+=sum(e.is_manifold and not e.is_contiguous for e in bm.edges);bm.free()
            info[ob.name]={'vertices':len(mesh.vertices),'triangles':len(mesh.loop_triangles),'uv_layers':len(mesh.uv_layers),'materials':[m.name for m in mesh.materials if m]}
        finally:ev.to_mesh_clear()
    return {'mesh_count':len(info),'triangles':triangles,'nonfinite_vertices':bad,'degenerate_triangles':degenerate,'nonmanifold_edges':nonmanifold,'inconsistent_winding_edges':winding,'bounds':[[min(p[i] for p in points) for i in range(3)],[max(p[i] for p in points) for i in range(3)]] if points else None,'objects':info}

def glb_json(path):
    data=path.read_bytes();magic,version,total=struct.unpack_from('<4sII',data)
    if magic!=b'glTF' or version!=2 or total!=len(data):raise RuntimeError('Invalid GLB framing')
    size,kind=struct.unpack_from('<I4s',data,12)
    if kind!=b'JSON':raise RuntimeError('Missing first JSON chunk')
    return json.loads(data[20:20+size])

def main():
    p=argparse.ArgumentParser();p.add_argument('--case',required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--glb',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);report={'case':a.case,'blender':bpy.app.version_string,'scope':'Blender exporter/importer technical check, not Khronos validation or target-engine certification'}
    bpy.ops.wm.open_mainfile(filepath=str(a.source.resolve()));scene=bpy.context.scene;scene.frame_set(1)
    objects=[o for o in scene.objects if (o.get('baseline_case')==a.case and not o.hide_render and not any(c.hide_render for c in o.users_collection)) or (a.case=='character' and o.get('reference_fit_owner')=='clay_girl_fit' and o.type=='MESH')]
    report['source']=snapshot(objects)
    report['source_armatures']=[o.name for o in scene.objects if o.type=='ARMATURE']
    report['source_actions']=[action.name for action in bpy.data.actions]
    report['materials']=[{'name':m.name,'has_nodes':m.use_nodes,'node_types':sorted({n.type for n in m.node_tree.nodes}) if m.node_tree else []} for m in {m for o in objects if hasattr(o.data,'materials') for m in o.data.materials if m}]
    if a.case=='mug':
        cup=next(o for o in objects if o.get('semantic_module')=='cup')
        handle=next(o for o in objects if o.get('semantic_module')=='handle')
        tree=BVHTree.FromObject(cup,bpy.context.evaluated_depsgraph_get())
        endpoints=[handle.matrix_world@Vector(p.co[:3]) for p in (handle.data.splines[0].points[0],handle.data.splines[0].points[-1])]
        distances=[tree.find_nearest(cup.matrix_world.inverted()@p)[3] for p in endpoints]
        floor=tree.ray_cast(Vector((0,0,.9)),Vector((0,0,-1)))[0]
        offaxis=tree.ray_cast(Vector((.1,0,.9)),Vector((0,0,-1)))[0]
        report['cup_function']={'handle_endpoint_surface_distances':distances,'handle_tube_radius':handle.data.bevel_depth,'both_ends_reach_cup':all(d<=handle.data.bevel_depth+1e-4 for d in distances),'center_floor_ray_hit':list(floor) if floor is not None else None,'offaxis_floor_ray_hit':list(offaxis) if offaxis is not None else None}
    if a.case=='wheel':
        root=bpy.data.objects.get('WheelPivot.001') or bpy.data.objects.get('WheelPivot');samples=[]
        for frame in [1,9,17,25,33]:
            scene.frame_set(frame);geometry=snapshot(objects);center=[(geometry['bounds'][0][i]+geometry['bounds'][1][i])/2 for i in range(3)]
            samples.append({'frame':frame,'root_world':list(root.matrix_world.translation),'angle_y':root.rotation_euler.y,'bbox_center':center})
        report['rotation_samples']=samples
        report['rotation_center_max_drift']=max((Vector(s['bbox_center'])-Vector(samples[0]['bbox_center'])).length for s in samples)
    doc=glb_json(a.glb);report['glb']={'bytes':a.glb.stat().st_size,'mesh_count':len(doc.get('meshes',[])),'materials':len(doc.get('materials',[])),'skins':len(doc.get('skins',[])),'animations':[x.get('name','') for x in doc.get('animations',[])],'extensions_required':doc.get('extensionsRequired',[]),'external_resources':[x['uri'] for key in ('buffers','images') for x in doc.get(key,[]) if 'uri' in x and not x['uri'].startswith('data:')]}
    new=bpy.data.scenes.new('IsolatedImport');bpy.context.window.scene=new
    bpy.ops.import_scene.gltf(filepath=str(a.glb.resolve()))
    new.frame_set(1);report['reimport']=snapshot(list(new.objects))
    source=report['source'];target=report['reimport']
    report['world_bounds_max_error']=max(abs(source['bounds'][i][j]-target['bounds'][i][j]) for i in range(2) for j in range(3)) if source['bounds'] and target['bounds'] else None
    report['checks']={'source_nonempty_finite':bool(source['mesh_count']) and source['nonfinite_vertices']==0,'no_degenerate_triangles':source['degenerate_triangles']==0,'winding_consistent':source['inconsistent_winding_edges']==0,'triangle_budget':source['triangles']<={'mug':25000,'wheel':40000,'character':80000}[a.case],'reimport_nonempty':bool(target['mesh_count']),'bounds_preserved':report['world_bounds_max_error'] is not None and report['world_bounds_max_error']<1e-4,'triangles_preserved':source['triangles']==target['triangles'],'embedded_resources':report['glb']['external_resources']==[]}
    if a.case=='character':report['checks'].update(persistent_armature=bool(report['source_armatures']),exported_skin=report['glb']['skins']>0,exported_animation=bool(report['glb']['animations']))
    if a.case=='mug':report['checks'].update(handle_connected=report['cup_function']['both_ends_reach_cup'],center_floor_exists=report['cup_function']['center_floor_ray_hit'] is not None)
    if a.case=='wheel':report['checks'].update(rotation_center=report['rotation_center_max_drift']<1e-4,full_rotation=max(s['angle_y'] for s in report['rotation_samples'])>6.28,exported_animation=bool(report['glb']['animations']))
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()

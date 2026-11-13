"""Worker for asset_delivery.py. Only runs in a disposable Blender process."""
import hashlib,json,math,struct,sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree
sys.path.insert(0,str(Path(__file__).resolve().parent))


def sample(scene,spec=None,stage='reimport'):
    bpy.context.view_layer.update();graph=bpy.context.evaluated_depsgraph_get();result={}
    # Blender's glTF importer creates bone display meshes. These are not GLB
    # asset geometry; exclude only meshes actually referenced as custom shapes.
    custom_shapes={p.custom_shape for rig in scene.objects if rig.type=='ARMATURE' for p in rig.pose.bones if p.custom_shape}
    objects=[o for o in scene.objects if o.type in {'MESH','CURVE'} and o not in custom_shapes]
    from production_checks import require_asset_geometry
    spec=spec or {}
    audit=require_asset_geometry(objects,stage=stage,max_triangles=spec.get('max_triangles'),
        min_triangle_area=spec.get('min_triangle_area',5e-13),require_closed=spec.get('require_closed',False),
        seam_weld_distance=spec.get('tolerance') if stage=='reimport' and spec.get('require_closed') else None)
    for obj in objects:
        ev=obj.evaluated_get(graph);mesh=ev.to_mesh()
        try:
            mesh.calc_loop_triangles();points=[tuple(ev.matrix_world@v.co) for v in mesh.vertices]
            if not points or any(not all(math.isfinite(x) for x in p) for p in points):raise ValueError('Empty/nonfinite geometry')
            result[obj.name]={'triangles':len(mesh.loop_triangles),'points':points,
                'geometry':audit['objects'][obj.name],
                'materials':sorted(m.name for m in mesh.materials if m),
                'bounds':[[min(p[i] for p in points) for i in range(3)],[max(p[i] for p in points) for i in range(3)]]}
        finally:ev.to_mesh_clear()
    return result


def distance(a,b):
    tree=KDTree(len(b))
    for i,p in enumerate(b):tree.insert(Vector(p),i)
    tree.balance()
    return max(tree.find(Vector(p))[2] for p in a)


def compact(samples):
    return {frame:{name:{k:v for k,v in item.items() if k!='points'} for name,item in records.items()} for frame,records in samples.items()}


def material_state():
    fields=['Base Color','Metallic','Roughness','Alpha']
    result={}
    for mat in bpy.data.materials:
        if not mat.use_nodes:continue
        shader=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
        if shader:
            result[mat.name]={key:list(shader.inputs[key].default_value) if key=='Base Color' else shader.inputs[key].default_value for key in fields}
    return result


def run(package,contract,output):
    spec=json.loads(contract.read_text());checks={};record={'status':'failed','blender':bpy.app.version_string,'contract':spec,'checks':checks,
        'scope':'isolated constant-PBR GLB geometry/skin/clip sampling; no visual/target-engine certification'}
    try:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        with bpy.data.libraries.load(str(package)) as (src,dst):dst.scenes=[spec['scene']]
        scene=dst.scenes[0];bpy.context.window.scene=scene
        if set(o.name for o in scene.objects)!=set(spec['expected_objects']):raise ValueError('Package object whitelist mismatch')
        for obj in scene.objects:
            if 'delivery_name' in obj:obj.name=obj['delivery_name']
        meshes=set(spec['expected_meshes'])
        before={}
        for frame in spec['frames']:scene.frame_set(frame if spec['mode']!='static' else spec['source_frame']);before[str(frame)]=sample(scene,spec,stage='delivery')
        source_materials=material_state()
        bones={b.name:b.parent.name if b.parent else None for o in scene.objects if o.type=='ARMATURE' for b in o.data.bones}
        scene.frame_set(spec['frames'][0] if spec['mode']!='static' else spec['source_frame'])
        operator=bpy.ops.export_scene.gltf;allowed=set(operator.get_rna_type().properties.keys())
        if 'use_active_scene' not in allowed:raise RuntimeError('Runtime cannot explicitly constrain the export scene')
        for obj in scene.objects:obj.select_set(True)
        bpy.context.view_layer.objects.active=next(iter(scene.objects))
        options={'filepath':str(output),'export_format':'GLB','use_selection':True,'use_active_scene':True,
                 'export_apply':False,'export_animations':spec['mode']!='static','export_yup':True}
        if 'export_frame_range' in allowed:options['export_frame_range']=True
        result=operator(**options)
        if 'FINISHED' not in result:raise RuntimeError('Exporter did not finish')
        raw=output.read_bytes();length,kind=struct.unpack_from('<I4s',raw,12)
        if kind!=b'JSON':raise ValueError('Missing GLB JSON')
        doc=json.loads(raw[20:20+length]);clips=[a.get('name') for a in doc.get('animations',[])]
        checks['raw_mesh_whitelist']={n.get('name') for n in doc.get('nodes',[]) if 'mesh' in n}==meshes
        checks['no_external_resources']=not any('uri' in r and not r['uri'].startswith('data:') for k in ('images','buffers') for r in doc.get(k,[]))
        if spec['mode']!='static':checks['clip_present']=spec['clip'] in clips
        if spec['mode']=='rigged':checks['skin_present']=bool(doc.get('skins'))
        # Clear only the disposable worker. Import cannot see original or factory objects.
        bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene
        scene.render.fps=spec['fps'];scene.render.fps_base=spec['fps_base']
        bpy.ops.import_scene.gltf(filepath=str(output))
        after={}
        for frame in spec['frames']:scene.frame_set(frame);after[str(frame)]=sample(scene,spec)
        for frame in before:
            checks['meshes@'+frame]=set(before[frame])==set(after[frame])==meshes
            for name in meshes & before[frame].keys() & after[frame].keys():
                a=before[frame][name];b=after[frame][name]
                error=max(distance(a['points'],b['points']),distance(b['points'],a['points']))
                checks[name+'@'+frame+'/surface_vertices']=error<=spec['tolerance']
                checks[name+'@'+frame+'/triangles']=a['triangles']==b['triangles']
                checks[name+'@'+frame+'/material_slots']=a['materials']==b['materials']
        imported_materials=material_state()
        for name,values in source_materials.items():
            actual=imported_materials.get(name,{})
            checks['material/'+name]=actual.keys()==values.keys() and all(
                max(abs(a-b) for a,b in zip(value,actual[key]))<1e-5 if isinstance(value,list) else abs(value-actual[key])<1e-5
                for key,value in values.items())
        if spec['mode']=='rigged':
            imported_bones={b.name:b.parent.name if b.parent else None for o in scene.objects if o.type=='ARMATURE' for b in o.data.bones}
            checks['bone_hierarchy']=bones==imported_bones
        record.update(source=compact(before),imported=compact(after),animation_names=clips,skin_count=len(doc.get('skins',[])),
                      bytes=output.stat().st_size,sha256=hashlib.sha256(raw).hexdigest(),effective_options=options)
        record['status']='passed' if all(checks.values()) else 'failed'
    except Exception as exc:
        if hasattr(exc,'report'):record['geometry_failure']=exc.report
        record['error']=str(exc)
        raise
    finally:
        Path(str(output)+'.report.json').write_text(json.dumps(record,indent=2)+'\n')
    if record['status']!='passed':raise RuntimeError('Roundtrip checks failed')
    return record


if __name__=='__main__':run(*map(Path,sys.argv[sys.argv.index('--')+1:]))

"""Isolated GLB delivery: evaluated static copies or explicitly prepared native animation.

Supported material scope is constant Principled PBR. Bake textured/procedural assets
and use validate_glb_roundtrip for their richer material/UV contract.
"""
import json
from pathlib import Path
import subprocess
import tempfile
import bpy


def export_glb(objects, output, *, mode='static', frames=(1,), clip=None,
               tolerance=1e-5, timeout=180):
    output = Path(output).resolve()
    report = Path(str(output) + '.report.json')
    if output.suffix.lower() != '.glb' or output.exists() or report.exists():
        raise ValueError('Choose a new .glb and report path')
    if mode not in {'static','animated','rigged'} or not objects or len(set(objects)) != len(objects):
        raise ValueError('Explicit unique objects and supported delivery mode required')
    if not isinstance(tolerance,(int,float)) or not 0 < tolerance < float('inf'):
        raise ValueError('Explicit finite positive spatial tolerance required')
    source = bpy.context.scene
    if any(source.objects.get(o.name) is not o for o in objects):
        raise ValueError('All delivery objects must belong to the active source scene')
    if bpy.context.mode != 'OBJECT':
        raise RuntimeError('Enter Object Mode before preparing delivery')
    if not frames or any(type(f) is not int for f in frames) or len(set(frames)) != len(frames):
        raise ValueError('Unique integer sample frames required')
    if mode != 'static' and (len(frames) < 2 or not isinstance(clip,str) or not clip.strip()):
        raise ValueError('Animation requires explicit clip and at least two sampled frames')
    if mode != 'static' and (min(frames)!=source.frame_start or max(frames)!=source.frame_end):
        raise ValueError('Sample both boundaries of the declared source clip range; do not silently truncate animation')
    bpy.context.view_layer.update()
    meshes = [o for o in objects if o.type in {'MESH','CURVE'}]
    if not meshes: raise ValueError('No delivery geometry')
    for obj in objects:
        if obj.type not in {'MESH','CURVE','EMPTY','ARMATURE'}:
            raise ValueError('Exclude cameras/lights/reference helpers from delivery')
        if obj.type=='EMPTY' and obj.empty_display_type=='IMAGE':
            raise ValueError('Exclude reference Image Empties from model delivery')
        if mode != 'static':
            if obj.parent and obj.parent not in objects: raise ValueError('Include the parent dependency explicitly')
            if obj.constraints: raise ValueError('Bake constraints into a prepared export copy first')
            if obj.type == 'CURVE': raise ValueError('Convert animated curves in a prepared copy first')
            if any(m.type != 'ARMATURE' and m.show_viewport for m in obj.modifiers):
                raise ValueError('Prepare non-armature modifiers on an export copy, preserving skin/shape keys')
            if obj.type == 'MESH' and obj.data.shape_keys:
                raise ValueError('Shape-key delivery requires the dedicated character export audit')
        if hasattr(obj.data,'materials'):
            for mat in obj.data.materials:
                if mat is None or not mat.use_nodes: raise ValueError('Explicit constant PBR materials required')
                outputs=[n for n in mat.node_tree.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output]
                shaders=[n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED']
                if len(outputs)!=1 or len(shaders)!=1 or not outputs[0].inputs['Surface'].is_linked or outputs[0].inputs['Surface'].links[0].from_node != shaders[0] or any(s.is_linked for s in shaders[0].inputs):
                    raise ValueError('Bake unsupported material graphs; constant-PBR exporter must not silently discard them')
    if mode == 'rigged':
        from domain_checks import inspect_weights
        rigs=[o for o in objects if o.type=='ARMATURE']
        if len(rigs)!=1: raise ValueError('This adapter requires one explicit export armature')
        for obj in meshes:
            weights=inspect_weights(obj,4)
            if weights['armature']!=rigs[0].name or any(weights['issues'].values()):
                raise ValueError('Repair deform weights/influence limits before export')
    output.parent.mkdir(parents=True,exist_ok=True)
    prepared=bpy.data.scenes.new('DeliveryPackage');prepared.frame_start=min(frames);prepared.frame_end=max(frames)
    prepared.render.fps=source.render.fps;prepared.render.fps_base=source.render.fps_base
    copies=[];data=[];expected=[]
    try:
        if mode=='static':
            graph=bpy.context.evaluated_depsgraph_get()
            for obj in meshes:
                evaluated=obj.evaluated_get(graph)
                mesh=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=graph);data.append(mesh)
                copy=bpy.data.objects.new('DELIVERY_'+obj.name,mesh);copies.append(copy)
                copy['delivery_name']=obj.name;copy.matrix_world=obj.matrix_world.copy()
                prepared.collection.objects.link(copy);expected.append(obj.name)
        else:
            for obj in objects: prepared.collection.objects.link(obj)
            expected=[o.name for o in meshes]
        with tempfile.TemporaryDirectory(prefix='blender-delivery-') as temp:
            temp=Path(temp);package=temp/'package.blend';contract=temp/'contract.json'
            bpy.data.libraries.write(str(package),{prepared},path_remap='ABSOLUTE')
            contract.write_text(json.dumps({'scene':prepared.name,'mode':mode,'frames':list(frames),'clip':clip,
                'expected_meshes':expected,'expected_objects':[o.name for o in prepared.objects],
                'tolerance':tolerance,'source_scene':source.name,'source_frame':source.frame_current,
                'fps':source.render.fps,'fps_base':source.render.fps_base},indent=2))
            command=[bpy.app.binary_path,'--background','--factory-startup','--disable-autoexec','-t','2','--python-exit-code','1',
                '--python',str(Path(__file__).with_name('isolated_delivery.py')),'--',str(package),str(contract),str(output)]
            try:
                result=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
            except subprocess.TimeoutExpired as exc:
                text=lambda value:value.decode(errors='replace') if isinstance(value,bytes) else value or ''
                Path(str(output)+'.log').write_text(text(exc.stdout)+text(exc.stderr))
                report.write_text(json.dumps({'status':'failed','error':'delivery timeout','timeout_seconds':timeout},indent=2)+'\n')
                raise RuntimeError('Delivery timed out; failed report and log retained') from exc
            Path(str(output)+'.log').write_text(result.stdout+result.stderr)
            if not report.is_file(): raise RuntimeError('Delivery worker failed; inspect '+str(output)+'.log')
            record=json.loads(report.read_text())
            if result.returncode or record['status']!='passed': raise RuntimeError('Delivery checks failed: '+str(report))
            return record
    finally:
        bpy.data.scenes.remove(prepared)
        for obj in copies: bpy.data.objects.remove(obj,do_unlink=True)
        for mesh in data:
            if mesh.users==0: bpy.data.meshes.remove(mesh)

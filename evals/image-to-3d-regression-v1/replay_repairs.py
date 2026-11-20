"""Explicit local defect replay on preserved baseline outputs, not a new Agent benchmark.
Only uses case-specific diagnoses already established by the baseline.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'skills/blender-python-modeling/scripts'))
from production_workspace import task_scene,role_collection,apply_render_preflight
from construction_checks import endpoint_proximity,axial_floor,connected_regions
from asset_delivery import export_glb

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def copy_case(path,case):
    bpy.ops.wm.open_mainfile(filepath=str(path));source=bpy.context.scene
    original=[o for o in source.objects if o.get('baseline_case')==case]
    scene=task_scene(case+'-repair');collection=role_collection(scene,'Asset');copies=[]
    root=bpy.data.objects.new(case+'-repair-root',None);collection.objects.link(root)
    if case=='wheel':root.location=(0,0,1)
    bpy.context.view_layer.update()
    for obj in original:
        copy=obj.copy();copy.data=obj.data.copy();matrix=obj.matrix_world.copy();copy.parent=root;copy.matrix_world=matrix
        collection.objects.link(copy);copy['repair_source']=obj.name;copies.append(copy)
    # A new task studio copies explicit comparison settings, not factory objects.
    scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.device='CPU';scene.render.resolution_x=512;scene.render.resolution_y=512;scene.render.resolution_percentage=100
    scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True;scene.view_settings.view_transform='Standard'
    scene.world=source.world.copy()
    studio=role_collection(scene,'Studio')
    for obj in source.objects:
        if obj.type in {'CAMERA','LIGHT'}:
            copy=obj.copy();copy.data=obj.data.copy();studio.objects.link(copy)
            if obj is source.camera:scene.camera=copy
    write(OUTPUT/(case+'-preflight.json'),apply_render_preflight(scene))
    return scene,root,copies

def render(scene,path):
    scene.frame_set(1);scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)

def replay_mug(source):
    scene,root,objects=copy_case(source,'mug')
    cup=next(o for o in objects if o.get('semantic_module')=='cup');handle=next(o for o in objects if o.get('semantic_module')=='handle')
    def contact():return endpoint_proximity(cup,[tuple(handle.matrix_world@Vector(p.co[:3])) for p in (handle.data.splines[0].points[0],handle.data.splines[0].points[-1])],[.052,.052],.001)
    def bottom():return axial_floor(cup,[(0,0,.9),(.1,0,.9),(-.1,0,.9)],(0,0,-1),minimum=.02,maximum=.04,distance=2,epsilon=1e-5)
    bpy.context.view_layer.update();before={'handle':contact(),'bottom':bottom()}
    points=handle.data.splines[0].points
    for i,p in enumerate(points):p.co.x-=.09*(i/(len(points)-1))**2
    # This known recipe erroneously connected the two .015-radius bottom rings.
    bm=bmesh.new();bm.from_mesh(cup.data)
    tunnel=[f for f in bm.faces if all(math.hypot(v.co.x,v.co.y)<.016 for v in f.verts) and max(v.co.z for v in f.verts)-min(v.co.z for v in f.verts)>.02]
    if not tunnel:raise RuntimeError('Known baseline axial tunnel not found; refuse a blind cap')
    bmesh.ops.delete(bm,geom=tunnel,context='FACES_ONLY')
    loose=[e for e in bm.edges if not e.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='EDGES')
    boundaries=[e for e in bm.edges if e.is_boundary and all(math.hypot(v.co.x,v.co.y)<.016 for v in e.verts)]
    if len(boundaries)!=32:raise RuntimeError('Unexpected baseline cap boundaries')
    bmesh.ops.holes_fill(bm,edges=boundaries,sides=0);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(cup.data);bm.free();cup.data.update()
    bpy.context.view_layer.update();after={'handle':contact(),'bottom':bottom()}
    render(scene,OUTPUT/'mug-repaired.png');bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT/'mug-repaired.blend'))
    delivery=export_glb(objects,OUTPUT/'mug-repaired.glb')
    return {'before':before,'after':after,'delivery_status':delivery['status'],
            'limitations':['Handle surface reach fixed, but continuous welded ceramic joint is not certified','Coarse silhouette/material mismatch remains; no new final score or completion claim']}

def replay_wheel(source):
    scene,root,objects=copy_case(source,'wheel');bpy.context.view_layer.update()
    spokes=[o for o in objects if o.get('semantic_module')=='spokes']
    for obj in spokes:
        for index in (0,1,6,7):obj.data.vertices[index].co.x*=.7;obj.data.vertices[index].co.z*=.7
        obj.data.update()
    bpy.context.view_layer.update();graph=bpy.context.evaluated_depsgraph_get()
    # Freeze only the derived copies' existing bevel before Boolean union.
    for obj in spokes:
        data=bpy.data.meshes.new_from_object(obj.evaluated_get(graph),preserve_all_data_layers=True,depsgraph=graph)
        obj.modifiers.clear();obj.data=data
    hub=next(o for o in objects if o.get('semantic_module')=='hub');rim=next(o for o in objects if o.get('semantic_module')=='rim')
    for obj in [rim,*spokes]:
        boolean=hub.modifiers.new('DerivedCastUnion','BOOLEAN');boolean.operation='UNION';boolean.solver='EXACT';boolean.object=obj
        bpy.context.view_layer.objects.active=hub;bpy.ops.object.modifier_apply(modifier=boolean.name)
        objects.remove(obj);bpy.data.objects.remove(obj,do_unlink=True)
    # Exact Boolean left a few zero-area tessellation faces in this fixture.
    # Clean only the prepared copy, then fix triangulation before measuring it.
    bm=bmesh.new();bm.from_mesh(hub.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7)
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    zero=[f for f in bm.faces if f.calc_area()<1e-12]
    if zero:bmesh.ops.delete(bm,geom=zero,context='FACES')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(hub.data);bm.free();hub.data.update()
    vertices=hub.data.vertices
    regions={'hub':[v.index for v in vertices if math.hypot(v.co.x,v.co.z)<.16],
             'rim':[v.index for v in vertices if math.hypot(v.co.x,v.co.z)>.68]};paths=[]
    for i in range(5):
        for sign in [-1,1]:
            a=i*math.tau/5+math.pi/2+sign*math.radians(7.5);target=Vector((.42*math.cos(a),-.195,.42*math.sin(a)))
            name=str(i)+'_'+str(sign);regions[name]=[min(vertices,key=lambda v:(v.co-target).length).index];paths += [('hub',name),(name,'rim')]
    continuity=connected_regions(hub,regions,paths)
    for frame,angle in [(1,0),(9,math.pi/2),(17,math.pi),(25,math.pi*1.5),(33,math.tau)]:root.rotation_euler.y=angle;root.keyframe_insert('rotation_euler',frame=frame)
    root.animation_data.action.name='RepairedWheelSpin'
    for curve in root.animation_data.action.fcurves:
        for key in curve.keyframe_points:key.interpolation='LINEAR'
    scene.frame_start=1;scene.frame_end=33;scene.frame_set(1)
    bpy.context.view_layer.update()
    centers=[]
    tire=next(o for o in objects if o.get('semantic_module')=='tire')
    for frame in (1,9,17,25,33):
        scene.frame_set(frame);bpy.context.view_layer.update();points=[tire.matrix_world@v.co for v in tire.data.vertices]
        centers.append([(min(v[i] for v in points)+max(v[i] for v in points))/2 for i in range(3)])
    pivot_error=max((Vector(center)-Vector((0,0,1))).length for center in centers)
    if pivot_error>1e-5:raise RuntimeError('Derived wheel pivot/assembly transform drift')
    render(scene,OUTPUT/'wheel-repaired.png');bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT/'wheel-repaired.blend'))
    delivery=export_glb([root,*objects],OUTPUT/'wheel-repaired.glb',mode='animated',frames=(1,9,17,25,33),clip='RepairedWheelSpin')
    return {'continuity':continuity,'pivot_max_error':pivot_error,'delivery_status':delivery['status'],
            'limitations':['Known coarse branch geometry locally joined, not a new reference-faithful wheel reconstruction','Tread, sidewall lettering, cast profiles, mechanical strength and vehicle assembly remain unverified']}

def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);global OUTPUT;OUTPUT=a.output.resolve()
    if OUTPUT.exists():raise FileExistsError('Preserve prior attempts; use a new output directory')
    source={case:a.baseline.resolve()/case/'diagnostic-asset.blend' for case in ['mug','wheel']}
    hashes={case:digest(path) for case,path in source.items()};OUTPUT.mkdir(parents=True)
    write(OUTPUT/'protocol.json',{'scope':'local known-defect technical regression; no Agent score comparison','source_hashes':hashes,'recipe_sha256':digest(Path(__file__)),'max_attempts':1,'visual_score_recomputed':False,
        'tools':{p.name:digest(p) for p in (ROOT/'skills/blender-python-modeling/scripts').glob('*.py') if p.name in ['asset_delivery.py','isolated_delivery.py','construction_checks.py','production_workspace.py']}})
    results={'mug':replay_mug(source['mug']),'wheel':replay_wheel(source['wheel'])}
    results['baseline_unchanged']=all(digest(path)==hashes[case] for case,path in source.items())
    results['passed']=results['baseline_unchanged'] and all(v['passed'] for v in results['mug']['after'].values()) and results['wheel']['continuity']['passed'] and results['mug']['delivery_status']==results['wheel']['delivery_status']=='passed'
    write(OUTPUT/'regression.json',results)
    if not results['passed']:raise RuntimeError('Known-defect regression failed')
    print('KNOWN_DEFECT_REPLAY_OK')

if __name__=='__main__':main()

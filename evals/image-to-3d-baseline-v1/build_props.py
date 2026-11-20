"""Case recipes for a visible-rubric exploratory baseline, not a generic reconstructor.
Two real perspective photos are interpreted manually. Hidden geometry is inferred.
Run in disposable Blender scenes, preserving the factory scene and coarse sources.
"""
import argparse, json, math, sys
from pathlib import Path
import bpy, bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'skills/blender-python-modeling/scripts'))
from reference_workspace import model_signature
from stage_guard import file_input
from blockout_gate import make_review_draft,record_blockout_review,require_blockout_review

def write(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

def material(name,color,metal=0,rough=.35):
    mat=bpy.data.materials.new(name);mat.diffuse_color=(*color,1);mat.use_nodes=True
    node=mat.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value=(*color,1);node.inputs['Metallic'].default_value=metal;node.inputs['Roughness'].default_value=rough
    return mat

def mesh_object(name,verts,faces,mat,parent,collection):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    ob=bpy.data.objects.new(name,mesh);collection.objects.link(ob);ob.parent=parent
    ob['baseline_case']=CASE;ob['semantic_module']=name.split('_',1)[0]
    if mat:mesh.materials.append(mat)
    for p in mesh.polygons:p.use_smooth=True
    return ob

def lathe(name,profile,mat,parent,collection,n,axis='Z'):
    verts=[];faces=[]
    for r,h in profile:
        for j in range(n):
            a=j*math.tau/n
            verts.append((r*math.cos(a),r*math.sin(a),h) if axis=='Z' else (r*math.cos(a),h,r*math.sin(a)))
    for k in range(len(profile)):
        for j in range(n):
            faces.append((k*n+j,k*n+(j+1)%n,((k+1)%len(profile))*n+(j+1)%n,((k+1)%len(profile))*n+j))
    return mesh_object(name,verts,faces,mat,parent,collection)

def tube(name,points,radius,mat,parent,collection,res=3):
    curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.resolution_u=res;curve.bevel_depth=radius;curve.bevel_resolution=res;curve.use_fill_caps=True
    spline=curve.splines.new('POLY');spline.points.add(len(points)-1)
    for p,co in zip(spline.points,points):p.co=(*co,1)
    ob=bpy.data.objects.new(name,curve);collection.objects.link(ob);ob.parent=parent;ob['baseline_case']=CASE;ob['semantic_module']=name.split('_',1)[0];curve.materials.append(mat)
    return ob

def new_root(name,collection,loc=(0,0,0)):
    ob=bpy.data.objects.new(name,None);collection.objects.link(ob);ob.location=loc;return ob

def mug(collection,fine):
    root=new_root('MugRoot',collection);n=64 if fine else 16
    white=material('GlazedCeramic',(0.8,.83,.85),rough=.23)
    # Observed base / rim width approximately .58; absolute dimensions unknown.
    profile=[(.255,.04),(.26,.01),(.28,.015),(.29,.05),(.455,.94),(.47,.985),(.465,1),(.445,1.005),(.43,.985),(.425,.95),(.263,.08),(.25,.065),(.015,.065),(.015,.04)]
    lathe('cup_body',profile,white,root,collection,n)
    steps=48 if fine else 10
    tube('handle_D',[(.398+.35*math.sin(math.pi*i/steps),0,.55+.325*math.cos(math.pi*i/steps)) for i in range(steps+1)],.052,white,root,collection,4 if fine else 1)
    spoon=new_root('SpoonRoot',collection)
    tube('spoon_stem',[(.51,.045,.28),(.565,.05,.58),(.63,.055,.92),(.66,.06,1.07)],.025,white,spoon,collection,4 if fine else 1)
    # Thin, dished elliptical ceramic bowl facing approximately -Y.
    verts=[];faces=[];rings=[(.005,0),(.35,.006),(.7,.022),(1,.05),(1,.065),(.7,.037),(.35,.021),(.005,.015)]
    for radius,depth in rings:
        for j in range(n):
            a=j*math.tau/n;verts.append((.68+.105*radius*math.cos(a),.055-depth,1.16+.21*radius*math.sin(a)))
    for k in range(len(rings)):
        for j in range(n):faces.append((k*n+j,k*n+(j+1)%n,((k+1)%len(rings))*n+(j+1)%n,((k+1)%len(rings))*n+j))
    mesh_object('spoon_bowl',verts,faces,white,spoon,collection)
    return [root,spoon]

def spoke(name,a,b,mat,parent,collection):
    centers=[(.20,a),(.42,(a+b)/2),(.69,b)];verts=[]
    for y in [-.195,-.095]:
        for r,t in centers:
            width=.052 if r<.3 else .038
            for sign in [-1,1]:verts.append((r*math.cos(t)-sign*width*math.sin(t),y,r*math.sin(t)+sign*width*math.cos(t)))
    faces=[(0,2,3,1),(2,4,5,3),(6,7,9,8),(8,9,11,10),(0,1,7,6),(4,10,11,5),(0,6,8,2),(2,8,10,4),(1,3,9,7),(3,5,11,9)]
    ob=mesh_object(name,verts,faces,mat,parent,collection);bevel=ob.modifiers.new('EditableEdgeFillet','BEVEL');bevel.width=.025;bevel.segments=3
    return ob

def wheel(collection,fine):
    root=new_root('WheelPivot',collection,(0,0,1));n=96 if fine else 20
    black=material('Rubber',(.025,.027,.03),rough=.82);metal=material('Alloy',(.52,.54,.57),.8,.24);dark=material('ValveRubber',(.012,.012,.012),rough=.8)
    lathe('tire_shell',[(.74,-.17),(.80,-.205),(.94,-.18),(1,-.105),(1,.105),(.94,.18),(.8,.205),(.74,.17)],black,root,collection,n,'Y')
    lathe('rim_lip',[(.65,-.19),(.71,-.22),(.735,-.19),(.735,.17),(.69,.17),(.69,-.15)],metal,root,collection,n,'Y')
    lathe('hub_cap',[(.012,-.23),(.135,-.23),(.155,-.19),(.155,-.1),(.012,-.1)],metal,root,collection,n,'Y')
    for k in range(5):
        angle=k*math.tau/5+math.pi/2
        for sign in [-1,1]:spoke('spokes_'+str(k)+'_'+str(sign),angle,angle+sign*math.radians(15),metal,root,collection)
        ob=lathe('lugs_'+str(k),[(.005,-.255),(.034,-.255),(.034,-.18),(.005,-.18)],metal,root,collection,6,'Y');ob.location=(.21*math.cos(angle),0,.21*math.sin(angle))
    valve=lathe('valve_stem',[(.005,-.28),(.019,-.28),(.019,-.17),(.005,-.17)],dark,root,collection,12,'Y');valve.location=(.63*math.cos(.6),0,.63*math.sin(.6))
    if fine:
        # Geometry ribs are a known approximation to the photographed grooved tread.
        for j in range(64):
            a=j*math.tau/64
            tube('tread_'+str(j),[(1.001*math.cos(a),-.09,1.001*math.sin(a)),(1.001*math.cos(a+.015),.09,1.001*math.sin(a+.015))],.007,black,root,collection,1)
    if fine:
        root.rotation_mode='XYZ'
        for frame,angle in [(1,0),(9,math.pi/2),(17,math.pi),(25,3*math.pi/2),(33,math.tau)]:
            root.rotation_euler.y=angle;root.keyframe_insert('rotation_euler',frame=frame)
        for curve in root.animation_data.action.fcurves:
            for key in curve.keyframe_points:key.interpolation='LINEAR'
    return [root]

def studio(scene):
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8;scene.cycles.use_denoising=False
    scene.render.resolution_x=512;scene.render.resolution_y=512;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
    scene.world=bpy.data.worlds.new(CASE+'World');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
    for i,(loc,energy,size) in enumerate([((-3,-4,5),400,4),((3,-2,3),250,3),((0,3,4),350,3)]):
        data=bpy.data.lights.new('Area'+str(i),'AREA');data.energy=energy;data.shape='DISK';data.size=size
        ob=bpy.data.objects.new(data.name,data);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,0,.7))-ob.location).to_track_quat('-Z','Y').to_euler()
    data=bpy.data.cameras.new('ReviewCamera');data.type='ORTHO';data.ortho_scale=2.8 if CASE=='wheel' else 1.9
    camera=bpy.data.objects.new(data.name,data);scene.collection.objects.link(camera);scene.camera=camera
    scene.view_settings.view_transform='Standard'

def render(scene,path,view='three-quarter',clay=False):
    center=Vector((0,0,1 if CASE=='wheel' else .68))
    offsets={'front':(0,-5,0),'side':(5,0,0),'back':(0,5,0),'three-quarter':(2.2,-5,1.8)}
    scene.camera.location=center+Vector(offsets[view]);scene.camera.rotation_euler=(center-scene.camera.location).to_track_quat('-Z','Y').to_euler()
    old=scene.view_layers[0].material_override
    try:
        if clay:scene.view_layers[0].material_override=material('ReviewClay',(.5,.5,.5),rough=.7)
        scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    finally:scene.view_layers[0].material_override=old

def main():
    p=argparse.ArgumentParser();p.add_argument('--case',choices=['mug','wheel'],required=True);p.add_argument('--stage',choices=['blockout','review','refine'],required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);global CASE;CASE=args.case;out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    source=Path(__file__).parent/'inputs'/CASE/'reference.jpg'
    if args.stage=='blockout':
        scene=bpy.data.scenes.new(CASE);bpy.context.window.scene=scene
        collection=bpy.data.collections.new('CoarseSource');scene.collection.children.link(collection)
        (mug if CASE=='mug' else wheel)(collection,False);studio(scene)
        guide=bpy.data.objects.new('PerspectivePhoto_NotOrthographicCalibration',None);guide.empty_display_type='IMAGE';guide.data=bpy.data.images.load(str(source));guide.data.pack();guide.hide_render=True;guide['reference_role']='Perspective appearance only; dimensions inferred';scene.collection.objects.link(guide)
        plan={'schema_version':1,'task_id':CASE,'intended_use':'static prop' if CASE=='mug' else 'detached rotating wheel','modules':[{'id':CASE,'method':'surface' if CASE=='mug' else 'primitives','reason':'Low-resolution revolution profiles and curves preserve cavity and radial structures; hidden depth inferred from mechanics','objects':[o.name for o in collection.objects if o.type in {'MESH','CURVE'}],'checks':[{'id':'shape','kind':'visual','criterion':'Coarse profile, negative space and count support refinement; not final likeness'}]}]}
        write(out/'modeling-plan.json',plan);render(scene,out/'blockout.png');bpy.ops.wm.save_as_mainfile(filepath=str(out/'coarse.blend'))
    else:
        bpy.ops.wm.open_mainfile(filepath=str(out/'coarse.blend'));scene=bpy.context.scene;plan=json.loads((out/'modeling-plan.json').read_text())
        collection=bpy.data.collections['CoarseSource'];objects=[o for o in collection.objects if o.type in {'MESH','CURVE'}]
        state=lambda modules:{'geometry':model_signature(objects),'frame':scene.frame_current}
        deps={'recipe':file_input(__file__),'reference':file_input(source)}
        if args.stage=='review':
            draft=make_review_draft(plan,[CASE],state,deps);write(out/'review-draft.json',draft)
            return
        require_blockout_review(out/'blockout-receipt.json',plan,[CASE],out/'blockout-review.json',state,deps)
        before=state(None)
        collection.hide_render=True
        collection=bpy.data.collections.new('Asset');scene.collection.children.link(collection);roots=(mug if CASE=='mug' else wheel)(collection,True)
        scene.frame_set(1)
        if before!=state(None):raise RuntimeError('Coarse source changed')
        for view in ['front','side','back','three-quarter']:render(scene,out/(view+'.png'),view)
        render(scene,out/'clay.png','three-quarter',True)
        scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(out/'asset.blend'))
        for ob in bpy.context.view_layer.objects:ob.select_set(False)
        for ob in collection.objects:ob.select_set(True)
        bpy.context.view_layer.objects.active=roots[0]
        bpy.ops.export_scene.gltf(filepath=str(out/'asset.glb'),export_format='GLB',use_selection=True,export_animations=True)
        write(out/'build-result.json',{'stage':'candidate','coarse_preserved':before==state(None),'objects':[o.name for o in collection.objects],'absolute_scale_known':False,'reference_workspace_calibration':'not verified; perspective photo only','ready_to_claim_complete':False})

if __name__=='__main__':main()

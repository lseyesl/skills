"""Synthetic repair experiments: actual wheel geometry and two-bone finger segment.
Not a human hand/anatomical or full vehicle production acceptance test.
"""
import bpy
import json
import math
from mathutils import Matrix, Vector
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from domain_checks import inspect_weights
out=Path(sys.argv[sys.argv.index('--')+1]);out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add(size=0.2,location=(-2,0,0));protected=bpy.context.object;protected.name='protected-existing-object'
original=(protected.matrix_world.copy(),[v.co.copy() for v in protected.data.vertices])
bpy.ops.mesh.primitive_torus_add(major_radius=0.8,minor_radius=0.18,major_segments=32,minor_segments=12)
wheel=bpy.context.object;wheel.name='test-wheel'
wheel.data.transform(Matrix.Translation((0.25,0,0)))
def center(obj):return obj.matrix_world @ (sum((v.co for v in obj.data.vertices),Vector())/len(obj.data.vertices))
def orbit(obj):
    result=[]
    for i in range(9):
        obj.rotation_euler.z=math.tau*i/8;bpy.context.view_layer.update();result.append(center(obj).copy())
    obj.rotation_euler.z=0;bpy.context.view_layer.update();return result
before=orbit(wheel);before_geometry=[wheel.matrix_world@v.co for v in wheel.data.vertices]
# Build a tubular segment with explicit deform groups and a known missing weight.
verts=[];faces=[];rings=9;segments=12
for ring in range(rings):
    y=3*ring/(rings-1)
    for i in range(segments):
        angle=math.tau*i/segments;verts.append((0.15*math.cos(angle),y,0.15*math.sin(angle)))
for ring in range(rings-1):
    for i in range(segments):
        a=ring*segments+i;b=ring*segments+(i+1)%segments;faces.append((a,b,b+segments,a+segments))
mesh=bpy.data.meshes.new('finger-segment');mesh.from_pydata(verts,[],faces)
finger=bpy.data.objects.new('finger-segment',mesh);bpy.context.collection.objects.link(finger);finger.location.x=2
arm=bpy.data.armatures.new('finger-rig');rig=bpy.data.objects.new('finger-rig',arm);bpy.context.collection.objects.link(rig);rig.location.x=2
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
a=arm.edit_bones.new('proximal');a.head=(0,0,0);a.tail=(0,1.5,0)
b=arm.edit_bones.new('distal');b.head=a.tail;b.tail=(0,3,0);b.parent=a;b.use_connect=True
bpy.ops.object.mode_set(mode='OBJECT')
mod=finger.modifiers.new('deform','ARMATURE');mod.object=rig
proximal=finger.vertex_groups.new(name='proximal');distal=finger.vertex_groups.new(name='distal')
for i,v in enumerate(verts):
    w=max(0,min(1,(v[1]-1.1)/0.8))
    if w<1:proximal.add([i],1-w,'REPLACE')
    if w>0:distal.add([i],w,'REPLACE')
bad_index=len(verts)-1;distal.remove([bad_index])
initial=inspect_weights(finger,4);assert initial['issues']['unweighted']==[bad_index]
bpy.ops.wm.save_as_mainfile(filepath=str(out/'source-with-defects.blend'))
# Repair origin without moving rest geometry, and restore only the confirmed missing weight.
local_center=sum((v.co for v in wheel.data.vertices),Vector())/len(wheel.data.vertices)
wheel.data.transform(Matrix.Translation(-local_center));wheel.matrix_world=wheel.matrix_world@Matrix.Translation(local_center)
bpy.context.view_layer.update();after_geometry=[wheel.matrix_world@v.co for v in wheel.data.vertices]
assert max((a-b).length for a,b in zip(before_geometry,after_geometry))<1e-6
fixed=orbit(wheel);before_excursion=max((v-before[0]).length for v in before);after_excursion=max((v-fixed[0]).length for v in fixed)
assert before_excursion>0.49 and after_excursion<1e-6
distal.add([bad_index],1,'REPLACE');assert not any(inspect_weights(finger,4)['issues'].values())
def evaluated():
    bpy.context.view_layer.update();obj=finger.evaluated_get(bpy.context.evaluated_depsgraph_get());return [obj.matrix_world@v.co for v in obj.data.vertices]
rest=evaluated();rig.pose.bones['distal'].rotation_mode='XYZ';rig.pose.bones['distal'].rotation_euler.z=math.pi/3
posed=evaluated();assert max((a-b).length for a,b in zip(rest[:segments],posed[:segments]))<1e-6
assert max((a-b).length for a,b in zip(rest[-segments:],posed[-segments:]))>0.5
assert protected.matrix_world==original[0] and all(v.co==c for v,c in zip(protected.data.vertices,original[1]))
bpy.ops.wm.save_as_mainfile(filepath=str(out/'repaired.blend'))
# Diagnostic view, not a production beauty render.
bpy.ops.object.camera_add(location=(6,-7,7));camera=bpy.context.object
camera.rotation_euler=(Vector((1,1,0))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=6
scene=bpy.context.scene;scene.camera=camera;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=12;scene.cycles.use_denoising=False
scene.render.resolution_x=640;scene.render.resolution_y=480;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('test-world');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(0.2,0.2,0.2,1)
bpy.ops.object.light_add(type='AREA',location=(2,-3,6));bpy.context.object.data.energy=800;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=5
scene.render.filepath=str(out/'diagnostic.png');bpy.ops.render.render(write_still=True)
report={'passed':True,'blender':bpy.app.version_string,'wheel':{'before_center_excursion':before_excursion,'after_center_excursion':after_excursion,'rest_geometry_preserved':True},'finger':{'vertices':len(verts),'initial_unweighted':initial['issues']['unweighted'],'repaired_weight_checks':True,'proximal_surface_preserved':True,'distal_surface_moved':True},'unrelated_object_preserved':True,'scope':'synthetic diagnosis/repair experiment; not full hand/vehicle or locomotion acceptance'}
(out/'repair-report.json').write_text(json.dumps(report,indent=2));print('REPAIR_ACCEPTANCE_OK',json.dumps(report))

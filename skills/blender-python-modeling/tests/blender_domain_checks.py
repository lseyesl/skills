"""Isolated synthetic fixtures calibrate diagnostics, not production visual quality."""
import bpy
import json
import math
from pathlib import Path
import sys
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from domain_checks import inspect_weights, rolling_error
out=Path(sys.argv[sys.argv.index('--')+1]);out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
mesh=bpy.data.meshes.new('fixture_mesh')
mesh.from_pydata([(0,0,0),(1,0,0),(1,1,0),(0,1,0)],[],[(0,1,2,3)])
obj=bpy.data.objects.new('fixture_hand_patch',mesh);bpy.context.collection.objects.link(obj)
arm=bpy.data.armatures.new('fixture_armature');rig=bpy.data.objects.new('fixture_rig',arm);bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT');bone=arm.edit_bones.new('joint');bone.head=(0,0,0);bone.tail=(0,1,0);bpy.ops.object.mode_set(mode='OBJECT')
group=obj.vertex_groups.new(name='joint');group.add([0,1,2,3],1,'REPLACE')
mod=obj.modifiers.new('armature','ARMATURE');mod.object=rig;obj.parent=rig
bpy.context.scene.frame_end=12
assert not any(inspect_weights(obj,4)['issues'].values())
group.remove([0]);assert inspect_weights(obj,4)['issues']['unweighted']==[0]
group.add([0],1,'REPLACE')
rig.pose.bones['joint'].rotation_mode='XYZ'
rig.pose.bones['joint'].rotation_euler.z=0;rig.keyframe_insert(data_path='pose.bones["joint"].rotation_euler',frame=1)
rig.pose.bones['joint'].rotation_euler.z=0.4;rig.keyframe_insert(data_path='pose.bones["joint"].rotation_euler',frame=12)
bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
rest=[(obj.matrix_world@v.co).copy() for v in obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
bpy.context.scene.frame_set(12);bpy.context.view_layer.update()
posed=[(obj.matrix_world@v.co).copy() for v in obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
assert any((a-b).length>0.01 for a,b in zip(rest,posed))
# Correct pivot versus displaced pivot: geometry-center orbit distinguishes eccentricity.
from mathutils import Matrix
center=Vector((0,0,0));offset=Vector((0.2,0,0));rot=Matrix.Rotation(math.pi,3,'Z')
assert (rot@center-center).length<1e-6
assert (rot@offset-offset).length>0.3
assert rolling_error(2*math.pi,1,2*math.pi,1e-6)['passed']
assert not rolling_error(2*math.pi,1,math.pi,1e-6)['passed']
bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'synthetic-binding.blend'))
bpy.ops.export_scene.gltf(filepath=str(out/'synthetic-binding.glb'),export_format='GLB',export_animations=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(out/'synthetic-binding.glb'))
loaded=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert loaded
assert any(m.type=='ARMATURE' and m.object for o in loaded for m in o.modifiers)
assert len(bpy.data.actions)>0
bpy.context.scene.frame_set(12);bpy.context.view_layer.update()
roundtrip=[(o.matrix_world@v.co).copy() for o in loaded for v in o.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
assert all(min((v-w).length for w in roundtrip)<1e-4 for v in posed), 'Animated evaluated geometry changed after GLB reload'
report={'passed':True,'blender':bpy.app.version_string,'scope':'synthetic weight/pose/pivot/rolling/export smoke only','production_visual_acceptance':'not-run','baseline_4_5':bpy.app.version>=(4,5,0)}
(out/'domain-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('DOMAIN_FIXTURES_OK',report)

"""Synthetic production workflow integration, not production-asset visual approval."""
import bpy
import json
import math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from production_checks import inspect_mesh,inspect_cloth,inspect_joint,correspondence_status
out=Path(sys.argv[sys.argv.index('--')+1]);out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
checks={}
def activate(obj):
    if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj

def evaluated(obj):
    bpy.context.view_layer.update();value=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [v.co.copy() for v in value.data.vertices]

bpy.ops.mesh.primitive_plane_add();plane=bpy.context.object;plane.name='TransferSource'
checks['open_sheet_legal']=not inspect_mesh(plane)['structural_issues']
checks['open_solid_rejected']='nonmanifold_edges' in inspect_mesh(plane,True)['structural_issues']
bpy.ops.mesh.primitive_cube_add(location=(5,0,0));cube=bpy.context.object
checks['closed_cube_legal']=not inspect_mesh(cube,True)['structural_issues']
# Transfer nearest-surface data to a differently positioned duplicate; no topology assumption.
left=plane.vertex_groups.new(name='Left');right=plane.vertex_groups.new(name='Right')
for v in plane.data.vertices:(left if v.co.x<0 else right).add([v.index],1,'REPLACE')
target=plane.copy();target.data=plane.data.copy();bpy.context.collection.objects.link(target);target.name='TransferTarget';target.location.z=0.1
for group in target.vertex_groups:group.remove(list(range(len(target.data.vertices))))
transfer=target.modifiers.new('Transfer','DATA_TRANSFER');transfer.object=plane;transfer.use_vert_data=True;transfer.data_types_verts={'VGROUP_WEIGHTS'};transfer.vert_mapping='NEAREST';transfer.layers_vgroup_select_src='ALL';transfer.layers_vgroup_select_dst='NAME'
activate(target);bpy.ops.object.modifier_apply(modifier=transfer.name)
checks['spatial_weight_transfer']=all(any(g.group==(target.vertex_groups['Left'].index if v.co.x<0 else target.vertex_groups['Right'].index) and abs(g.weight-1)<1e-6 for g in v.groups) for v in target.data.vertices)
checks['same_count_is_not_identity']=correspondence_status(4,4)=='unknown-order'
checks['reordered_identity_rejected']=correspondence_status(4,4,[0,1,2,3],[3,2,1,0])=='incompatible-order'
# Native local corrective shape driven by a real bone rotation.
arm=bpy.data.armatures.new('JointRig');rig=bpy.data.objects.new('JointRig',arm);bpy.context.collection.objects.link(rig)
activate(rig);bpy.ops.object.mode_set(mode='EDIT');bone=arm.edit_bones.new('Joint');bone.head=(0,0,0);bone.tail=(0,1,0);bpy.ops.object.mode_set(mode='OBJECT')
activate(target);basis=target.shape_key_add(name='Basis');key=target.shape_key_add(name='JointFix');key.data[0].co.z+=0.2
basis_before=[v.co.copy() for v in basis.data]
driver=key.driver_add('value').driver;driver.type='SCRIPTED';var=driver.variables.new();var.name='angle';var.type='TRANSFORMS';var.targets[0].id=rig;var.targets[0].bone_target='Joint';var.targets[0].transform_type='ROT_Z';var.targets[0].transform_space='LOCAL_SPACE'
driver.expression='max(0,min(1,angle/1.5707963267948966))'
rig.pose.bones['Joint'].rotation_mode='XYZ';rig.pose.bones['Joint'].rotation_euler.z=math.pi/4
posed=evaluated(target)
checks['corrective_driver']=abs(key.value-0.5)<1e-5 and abs(posed[0].z-basis.data[0].co.z-0.1)<1e-5
checks['corrective_locality']=all((posed[i]-basis.data[i].co).length<1e-6 for i in range(1,len(posed)))
driver.expression='max(0,min(1,-angle/1.5707963267948966))';rig.update_tag();target.data.update();bpy.context.view_layer.update()
checks['wrong_sign_detected']=abs(key.value-0.5)>0.1
driver.expression='max(0,min(1,angle/1.5707963267948966))';rig.update_tag();bpy.context.view_layer.update()
checks['basis_preserved']=all((v.co-old).length<1e-7 for v,old in zip(basis.data,basis_before))
# Flat tangent normal bake: verifies target UV/image/context/data-space, not cage projection.
bpy.ops.mesh.primitive_plane_add(location=(8,0,0));baked=bpy.context.object;baked.name='ExportSample'
mat=bpy.data.materials.new('BakeMaterial');mat.use_nodes=True;baked.data.materials.append(mat)
image=bpy.data.images.new('NormalData',width=32,height=32);image.colorspace_settings.name='Non-Color'
tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image;mat.node_tree.nodes.active=tex
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=4;scene.cycles.use_denoising=False
scene.render.bake.use_selected_to_active=False;activate(baked);bpy.ops.object.bake(type='NORMAL')
index=(16*32+16)*4;pixel=list(image.pixels[index:index+4])
checks['flat_normal_bake']=abs(pixel[0]-0.5)<0.03 and abs(pixel[1]-0.5)<0.03 and pixel[2]>0.97
image.filepath_raw=str(out/'normal.png');image.file_format='PNG';image.save()
normal=mat.node_tree.nodes.new('ShaderNodeNormalMap');mat.node_tree.links.new(tex.outputs['Color'],normal.inputs['Color']);bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');mat.node_tree.links.new(normal.outputs['Normal'],bsdf.inputs['Normal'])
bpy.ops.export_scene.gltf(filepath=str(out/'production-sample.glb'),export_format='GLB',use_selection=True,export_tangents=True)
# Short flat cloth contact and preflight defect/alternative controls.
mesh=bpy.data.meshes.new('SheetGrid');size=7
vertices=[(-0.5+x/(size-1),-0.5+y/(size-1),0.4) for y in range(size) for x in range(size)]
faces=[(y*size+x,y*size+x+1,(y+1)*size+x+1,(y+1)*size+x) for y in range(size-1) for x in range(size-1)]
mesh.from_pydata(vertices,[],faces);sheet=bpy.data.objects.new('ClothSheet',mesh);bpy.context.collection.objects.link(sheet)
cloth=sheet.modifiers.new('Cloth','CLOTH');cloth.settings.quality=5;cloth.collision_settings.use_collision=True;cloth.collision_settings.use_self_collision=False;cloth.collision_settings.distance_min=0.01
bpy.ops.mesh.primitive_plane_add(size=4);collider=bpy.context.object;collider.name='Collider'
checks['missing_collision_detected']=not inspect_cloth(sheet,[collider])['configuration_ready']
collider.modifiers.new('Collision','COLLISION');collider.collision.thickness_outer=0.01
checks['cloth_preflight']=inspect_cloth(sheet,[collider])['configuration_ready']
collider.modifiers['Collision'].show_viewport=False
checks['disabled_collider_detected']=not inspect_cloth(sheet,[collider])['configuration_ready']
collider.modifiers['Collision'].show_viewport=True
checks['distant_sheet_no_self_collision_legal']=not inspect_cloth(sheet,[collider])['self_collision']
scene.frame_start=1;scene.frame_end=20;scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'synthetic-source.blend'))
mins=[]
for frame in range(1,21):
    scene.frame_set(frame);bpy.context.view_layer.update();mins.append(min(v.z for v in evaluated(sheet)))
checks['short_contact_finite']=all(math.isfinite(v) for v in mins)
checks['short_contact_no_large_penetration']=min(mins)>-0.02
checks['short_contact_reaches_surface']=mins[-1]<0.2
report={'passed':all(checks.values()),'blender':bpy.app.version_string,'checks':checks,'flat_normal_center':pixel,'cloth_min_z_per_frame':mins,'scope':'synthetic mesh/transfer/local-corrective/flat-bake/20-frame-cloth technical checks; no full hand, high-low cage bake, garment or target-viewer certification'}
(out/'production-report.json').write_text(json.dumps(report,indent=2));print('PRODUCTION_CHECKS',json.dumps(report))
if not report['passed']:raise SystemExit(1)

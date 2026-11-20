"""Real-engine scene, delivery, content and persistent-rig regressions.
Synthetic controls prove these operations; they do not certify a production character.
"""
import json,math,subprocess,sys,uuid
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from production_workspace import task_scene,role_collection,probe_render
from asset_delivery import export_glb
from construction_checks import endpoint_proximity,axial_floor,connected_regions
from character_rig import build_rig,rig_inventory

output_root=Path(sys.argv[sys.argv.index('--')+1]).resolve();output_root.mkdir(parents=True,exist_ok=True)
out=output_root/('run-'+uuid.uuid4().hex[:12]);out.mkdir()
checks={}
def check(name,value):
    assert value,name
    checks[name]=True
def rejects(name,fn):
    try:fn()
    except (ValueError,RuntimeError):checks[name]=True
    else:raise AssertionError('Not rejected: '+name)
def mat(name):
    m=bpy.data.materials.new(name);m.use_nodes=True;return m
def mesh(name,vertices,faces):
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update()
    ob=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(ob);ob.data.materials.append(mat(name+'_PBR'));return ob

# Factory Cube stays selected in the old scene, but cannot reach task creation or export.
factory=bpy.context.scene;cube=bpy.data.objects['Cube'];old_coords=[tuple(v.co) for v in cube.data.vertices]
scene=task_scene('delivery-test')
check('creation_scene_empty',len(scene.objects)==0)
check('creation_collections',len(scene.collection.children)==4)
check('scene_reused',task_scene('delivery-test') is scene)
rejects('unowned_scene_not_cleared',lambda:task_scene('other',name=factory.name))
check('edit_explicit_scene_preserved',task_scene('delivery-test',mode='edit',existing=factory) is factory and bpy.data.objects.get('Cube') is cube)
task_scene('delivery-test')
bpy.ops.mesh.primitive_cube_add(size=1);body=bpy.context.object;body.name='DeliveryBody';body.data.materials.append(mat('BodyPBR'))
bevel=body.modifiers.new('KeepEditableBevel','BEVEL');bevel.width=.1;bevel.segments=3
source_vertices=[tuple(v.co) for v in body.data.vertices]
record=export_glb([body],out/'static.glb')
check('static_isolated_roundtrip',record['status']=='passed')
guide=bpy.data.objects.new('ReferenceGuide',None);scene.collection.objects.link(guide);guide.empty_display_type='IMAGE'
rejects('reference_image_not_delivered_as_model',lambda:export_glb([body,guide],out/'bad-reference.glb'))
check('evaluated_bevel_preserved',record['source']['1']['DeliveryBody']['triangles']>12)
check('source_modifier_and_mesh_preserved',len(body.modifiers)==1 and source_vertices==[tuple(v.co) for v in body.data.vertices])
check('other_scene_cube_preserved',cube.select_get(view_layer=factory.view_layers[0]) and old_coords==[tuple(v.co) for v in cube.data.vertices])
check('temporary_package_removed',not any(s.name.startswith('DeliveryPackage') for s in bpy.data.scenes))
rejects('no_overwrite',lambda:export_glb([body],out/'static.glb'))
body.data.materials[0].node_tree.nodes.new('ShaderNodeTexNoise')
shader=body.data.materials[0].node_tree.nodes.get('Principled BSDF');noise=body.data.materials[0].node_tree.nodes.get('Noise Texture')
body.data.materials[0].node_tree.links.new(noise.outputs['Fac'],shader.inputs['Roughness'])
rejects('procedural_material_not_silently_dropped',lambda:export_glb([body],out/'bad-material.glb'))
body.data.materials[0].node_tree.nodes.remove(noise)
scene.render.engine='CYCLES';scene.cycles.use_denoising=True
probe=probe_render(scene);(out/'render-preflight.json').write_text(json.dumps(probe,indent=2))
check('actual_render_preflight',probe['probe_passed'])
check('preflight_preserves_source_render',scene.cycles.use_denoising)
def unrelated_error(scene):raise RuntimeError('Disk full')
rejects('unrelated_render_error_not_hidden',lambda:probe_render(scene,render_probe=unrelated_error))
calls=[]
def unsupported(scene):
    calls.append(scene.cycles.use_denoising)
    if scene.cycles.use_denoising:raise RuntimeError('Failed to denoise: OpenImageDenoise unavailable')
fallback=probe_render(scene,render_probe=unsupported)
check('only_unavailable_denoise_falls_back',calls==[True,False] and fallback['fallback_reason'] and not fallback['use_denoising'])

# World-space surface distances work under nonidentity transforms.
check('endpoint_contact_positive',endpoint_proximity(body,[(.5,0,0)],[.05],.001)['passed'])
check('endpoint_gap_negative',not endpoint_proximity(body,[(.8,0,0)],[.05],.001)['passed'])
body.location.x=2;body.scale=(2,1,1);bpy.context.view_layer.update()
check('endpoint_world_transform',endpoint_proximity(body,[(3,0,0)],[.05],.001)['passed'])
# Open-at-top box cup with actual bottom; then remove its floor as a negative control.
v=[(-.5,-.5,0),(.5,-.5,0),(.5,.5,0),(-.5,.5,0),(-.5,-.5,.1),(.5,-.5,.1),(.5,.5,.1),(-.5,.5,.1)]
floor=mesh('Floor',v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
args=dict(origins=[(0,0,1),(.2,0,1),(-.2,0,1)],direction=(0,0,-1),minimum=.09,maximum=.11,distance=2,epsilon=1e-5)
check('floor_thickness_positive',axial_floor(floor,**args)['passed'])
floor.location.x=5;bpy.context.view_layer.update()
check('missing_floor_negative',not axial_floor(floor,**args)['passed'])
disconnected=mesh('Disconnected',[(0,0,0),(1,0,0),(0,1,0),(2,0,0),(3,0,0),(2,1,0)],[(0,1,2),(3,4,5)])
check('disconnected_region_negative',not connected_regions(disconnected,{'hub':[0],'spoke':[3]},[('hub','spoke')])['passed'])
check('connected_region_positive',connected_regions(disconnected,{'hub':[0],'spoke':[2]},[('hub','spoke')])['passed'])

spin_scene=task_scene('spin-test');spin_scene.frame_start=1;spin_scene.frame_end=33;spin_scene.render.fps=30
root=bpy.data.objects.new('SpinRoot',None);spin_scene.collection.objects.link(root)
spoke=mesh('RotatingSpoke',[(0,0,0),(1,0,0),(1,.1,0)],[(0,1,2)]);spoke.parent=root
for frame,angle in [(1,0),(9,math.pi/2),(17,math.pi),(25,3*math.pi/2),(33,math.tau)]:
    root.rotation_euler.y=angle;root.keyframe_insert('rotation_euler',frame=frame)
root.animation_data.action.name='WheelSpin'
for c in root.animation_data.action.fcurves:
    for key in c.keyframe_points:key.interpolation='LINEAR'
spin_scene.frame_set(1)
record=export_glb([root,spoke],out/'spin.glb',mode='animated',frames=(1,9,17,25,33),clip='WheelSpin')
check('rotation_clip_and_sampled_surface_survive',record['status']=='passed' and record['source']['1']!=record['source']['9'])
rejects('sample_range_cannot_truncate_clip',lambda:export_glb([root,spoke],out/'truncated.glb',mode='animated',frames=(1,9),clip='WheelSpin'))
rejects('missing_required_clip_not_approved',lambda:export_glb([root,spoke],out/'missing-clip.glb',mode='animated',frames=(1,33),clip='NotPresent'))
check('failed_export_report_preserved',json.loads(Path(str(out/'missing-clip.glb')+'.report.json').read_text())['status']=='failed')

rig_scene=task_scene('rig-test');rig_scene.frame_start=1;rig_scene.frame_end=17
verts=[];faces=[]
for z in [0,.5,1,1.5,2]:
    for i in range(8):verts.append((.1*math.cos(i*math.tau/8),.1*math.sin(i*math.tau/8),z))
for ring in range(4):
    for i in range(8):a=ring*8+i;b=ring*8+(i+1)%8;faces.append((a,b,b+8,a+8))
limb=mesh('SkinnedLimb',verts,faces)
rejects('static_mesh_not_mistaken_for_rig',lambda:export_glb([limb],out/'missing-rig.glb',mode='rigged',frames=(1,17),clip='FK_Check'))
bones=[{'name':'upper','head':[0,0,0],'tail':[0,0,1]},{'name':'lower','parent':'upper','head':[0,0,1],'tail':[0,0,2]}]
rows=[]
for co in verts:
    w=max(0,min(1,(co[2]-.5)));rows.append({'upper':1-w,'lower':w})
bad_rows=[dict(row) for row in rows];bad_rows[0]={}
rejects('unweighted_binding_rejected_before_mutation',lambda:build_rig(rig_scene,'BadRig',bones,{limb:bad_rows}))
check('bad_binding_creates_no_rig',bpy.data.objects.get('BadRig') is None)
rig=build_rig(rig_scene,'PersistentRig',bones,{limb:rows})
check('persistent_rig_weights',rig_inventory([limb],rig)['weights_valid'])
rejects('existing_rig_not_replaced',lambda:build_rig(rig_scene,'Replacement',bones,{limb:rows}))
bone=rig.pose.bones['lower'];bone.rotation_mode='XYZ'
for frame,angle in [(1,0),(9,.45),(17,0)]:bone.rotation_euler.x=angle;bone.keyframe_insert('rotation_euler',frame=frame)
rig.animation_data.action.name='FK_Check';rig_scene.frame_set(1)
record=export_glb([rig,limb],out/'rig.glb',mode='rigged',frames=(1,9,17),clip='FK_Check')
check('persistent_skin_clip_and_actual_vertices_survive',record['status']=='passed' and record['skin_count']==1 and record['source']['1']!=record['source']['9'])
check('source_armature_still_editable',bpy.data.objects.get(rig.name) is rig and len(limb.modifiers)==1)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'source.blend'))
expression="import bpy; assert bpy.context.scene.name == 'MODEL_rig-test'; assert bpy.context.scene.objects.get('PersistentRig'); assert bpy.context.scene.objects.get('Cube') is None"
result=subprocess.run([bpy.app.binary_path,'--background',str(out/'source.blend'),'--disable-autoexec','--python-exit-code','1','--python-expr',expression],capture_output=True,text=True,timeout=90)
check('saved_file_opens_in_model_scene',result.returncode==0)
report={'passed':all(checks.values()),'checks':checks,'blender':bpy.app.version_string,'artifacts':out.name,'scope':'synthetic regressions; not full character, wheel or image-fidelity certification'}
(out/'delivery-report.json').write_text(json.dumps(report,indent=2));(output_root/'delivery-report.json').write_text(json.dumps(report,indent=2));print('ASSET_DELIVERY_OK',json.dumps(report))

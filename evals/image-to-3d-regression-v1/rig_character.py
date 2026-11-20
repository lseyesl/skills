"""Seen-character derivative experiment with explicit joints/weights and budget.
Not an unseen image reconstructor or a final character quality certification.
Source appearance uses procedural clay; the diagnostic derivative explicitly uses
constant colours rather than silently claiming its materials were baked.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'skills/blender-python-modeling/scripts'))
from production_workspace import task_scene,role_collection,apply_render_preflight
from character_rig import build_rig,rig_inventory
from asset_delivery import export_glb
from production_checks import inspect_mesh

def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def clamp(x):return max(0,min(1,x))

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=a.output.resolve()
    if out.exists():raise FileExistsError('Keep prior attempts in separate folders')
    out.mkdir(parents=True);source_hash=digest(a.source);config=json.loads(a.config.read_text());owner=config['character_id']
    write(out/'protocol.json',{'scope':'known character derivative, technical binding/export regression only','source_sha256':source_hash,'config_sha256':digest(a.config),'recipe_sha256':digest(Path(__file__)),'triangle_budget':80000,
        'material_change':'explicit diagnostic constant-PBR approximation; original procedural material not certified equivalent','visual_rescore':False,'maximum_candidate_builds':1})
    bpy.ops.wm.open_mainfile(filepath=str(a.source.resolve()));original=bpy.context.scene;source_meshes=[o for o in original.objects if o.type=='MESH' and o.get('reference_fit_owner')==owner]
    graph=bpy.context.evaluated_depsgraph_get();copies=[];scene=task_scene('girl-rig-derivative');assets=role_collection(scene,'Asset')
    # Read source evaluated geometry in its own depsgraph before linking derived meshes.
    bpy.context.window.scene=original;graph=bpy.context.evaluated_depsgraph_get()
    for obj in source_meshes:
        data=bpy.data.meshes.new_from_object(obj.evaluated_get(graph),preserve_all_data_layers=True,depsgraph=graph)
        copy=bpy.data.objects.new('Rigged_'+obj.name,data);copy.matrix_world=obj.matrix_world.copy();copy['fit_component']=obj['fit_component'];copy['source_name']=obj.name;assets.objects.link(copy);copies.append(copy)
    bpy.context.window.scene=scene;before=sum(inspect_mesh(o)['evaluated_triangles'] for o in copies)
    # Explicit one-pass budget experiment, not a general decimation prescription.
    for obj in copies:
        mod=obj.modifiers.new('ReviewedDerivativeBudget','DECIMATE');mod.ratio=.46
        bpy.context.view_layer.objects.active=obj;bpy.ops.object.modifier_apply(modifier=mod.name)
        bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.triangulate(bm,faces=list(bm.faces))
        zero=[f for f in bm.faces if f.calc_area()<1e-14]
        if zero:bmesh.ops.delete(bm,geom=zero,context='FACES')
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
        original_material=obj.data.materials[0]
        # The clay shader's Base Color is linked. Its socket default is white,
        # so use the explicit case palette, never the unlinked fallback value.
        colour=original_material.get('reference_fit_base_color')
        if not isinstance(colour,str) or len(colour)!=7:raise RuntimeError('Explicit source palette missing; do not guess a baked colour')
        srgb=[int(colour[i:i+2],16)/255 for i in (1,3,5)]
        linear=[c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in srgb]+[1]
        name='Diagnostic_'+original_material.name;material=bpy.data.materials.get(name)
        if material is None:
            material=bpy.data.materials.new(name);material.use_nodes=True;node=material.node_tree.nodes.get('Principled BSDF')
            node.inputs['Base Color'].default_value=linear;node.inputs['Roughness'].default_value=.82
        obj.data.materials.clear();obj.data.materials.append(material)
    stats={o.name:inspect_mesh(o,require_closed=True,min_face_area=1e-14) for o in copies};after=sum(v['evaluated_triangles'] for v in stats.values())
    if after>80000 or any(v['structural_issues'] for v in stats.values()):raise RuntimeError('Prepared mesh structural/budget check failed')
    bones=[{'name':'root','head':[0,0,.01],'tail':[0,0,.28]},
           {'name':'spine','head':[0,0,.28],'tail':[0,0,.55],'parent':'root'},
           {'name':'head','head':[0,0,.55],'tail':[0,0,.82],'parent':'spine'}]
    joint_map={}
    for limb in ['arm_L','arm_R','leg_L','leg_R']:
        path=config['shape'][limb]['path'];start=path[1] if limb.startswith('arm') else path[0];middle=path[2] if limb.startswith('arm') else path[len(path)//2];end=path[-1]
        bones.extend([{'name':limb+'_upper','head':start,'tail':middle,'parent':'spine' if limb.startswith('arm') else 'root'},
                      {'name':limb+'_lower','head':middle,'tail':end,'parent':limb+'_upper'}]);joint_map[limb]=(Vector(start),Vector(middle),Vector(end))
    bindings={}
    for obj in copies:
        part=obj['fit_component'];rows=[]
        if part in joint_map and obj['source_name'].endswith('::limb'):
            start,middle,end=joint_map[part];axis=end-start;joint=(middle-start).dot(axis)/axis.length_squared
            for v in obj.data.vertices:
                t=(obj.matrix_world@v.co-start).dot(axis)/axis.length_squared;w=clamp((t-joint+.12)/.24)
                rows.append({part+'_upper':1-w,part+'_lower':w})
        else:
            if part.startswith('arm_'):bone=part+'_lower'
            elif part.startswith('shoe_'):bone='leg_'+part[-1]+'_lower'
            elif part in joint_map:bone=part+'_lower'
            elif part in ['neck','torso','dress']:bone='spine'
            else:bone='head'
            rows=[{bone:1} for _ in obj.data.vertices]
        bindings[obj]=rows
    rig=build_rig(scene,'GirlExportRig',bones,bindings)
    write(out/'joint-plan.json',{'bones':bones,'weight_strategy':'explicit per-component regions; limb band blend around inferred elbow/knee; rigid head/accessories; no finger or cloth animation','coordinate_source':'seen fixture neutral-pose path controls; not measured hidden anatomy'})
    inventory=rig_inventory(copies,rig);write(out/'rig-inventory.json',inventory)
    frames=[1,9,17,25,33];targets={9:('arm_L_upper',2,.35),17:('arm_L_lower',0,.7),25:('leg_L_lower',0,.5)}
    for frame in frames:
        for bone in rig.pose.bones:bone.rotation_mode='XYZ';bone.rotation_euler=(0,0,0)
        if frame in targets:
            key,axis,angle=targets[frame];rig.pose.bones[key].rotation_euler[axis]=angle
        for bone in rig.pose.bones:bone.keyframe_insert('rotation_euler',frame=frame)
    rig.animation_data.action.name='BasicJointChecks';scene.frame_start=1;scene.frame_end=33;scene.render.fps=24
    studio=role_collection(scene,'Studio');scene.world=original.world.copy();scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.device='CPU';scene.render.resolution_x=512;scene.render.resolution_y=536;scene.render.resolution_percentage=100;scene.render.film_transparent=True;scene.render.image_settings.color_mode='RGBA';scene.view_settings.view_transform='Standard'
    for obj in original.objects:
        if obj.type in {'CAMERA','LIGHT'} and obj.get('fit_studio')==owner:
            copy=obj.copy();copy.data=obj.data.copy();studio.objects.link(copy)
            if obj.get('fit_view')=='front':scene.camera=copy
    write(out/'render-preflight.json',apply_render_preflight(scene))
    for frame in frames[:-1]:scene.frame_set(frame);scene.render.filepath=str(out/('pose-'+str(frame)+'.png'));bpy.ops.render.render(write_still=True)
    scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(out/'rigged-derivative.blend'))
    delivery=export_glb([rig,*copies],out/'rigged-derivative.glb',mode='rigged',frames=tuple(frames),clip='BasicJointChecks',timeout=600)
    report={'technical_passed':inventory['weights_valid'] and delivery['status']=='passed' and source_hash==digest(a.source),'triangles_before':before,'triangles_after':after,'bones':len(bones),'skin_count':delivery['skin_count'],'clip':delivery['animation_names'],'source_unchanged':source_hash==digest(a.source),'final_asset_passed':False,
        'limitations':['Seen case and hand-specified joints; no unseen reconstruction evidence','Diagnostic colour-material simplification is not approved final reference fidelity','Decimation visual review and shoulder/knee topology remain subject to actual pose inspection','No finger, gait, cloth, IK, retargeting, multiple-clip or target-engine certification']}
    write(out/'regression.json',report)
    if not report['technical_passed']:raise RuntimeError('Character derivative technical checks failed')

if __name__=='__main__':main()

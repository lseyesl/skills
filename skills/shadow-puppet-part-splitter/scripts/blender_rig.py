#!/usr/bin/env python3
"""Import v1 2D parts as a rigid 2.5D FK rig; run with Blender --python.

Creates a task-owned scene, preserves existing scenes, packs textures, tests
evaluated rigid transforms and limits. Visual seam acceptance remains manual.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

import bpy
from mathutils import Matrix, Vector


def require(ok, message):
    if not ok:
        raise ValueError(message)


def finite(v):
    return isinstance(v, (int,float)) and not isinstance(v,bool) and math.isfinite(v)


def pair(v):
    return isinstance(v,list) and len(v)==2 and all(finite(x) for x in v)


def inside(root, name):
    require(isinstance(name,str) and name and not Path(name).is_absolute(), "invalid asset path")
    path=(root/name).resolve()
    require(path.is_relative_to(root) and path.is_file(),f"missing/outside asset: {name}")
    return path


def inputs(manifest, plan):
    data=json.loads(manifest.read_text(encoding="utf-8"))
    motion=json.loads(plan.read_text(encoding="utf-8"))
    require(data.get("schema_version")=="1.0" and data.get("coordinate_system")=="image-pixels-y-down", "unsupported manifest")
    require(pair(data.get("source_size")) and all(isinstance(x,int) and x>0 for x in data["source_size"]),"invalid source_size")
    require(isinstance(data.get("nodes"),list) and data["nodes"],"missing nodes")
    require(isinstance(data.get("parts"),list) and data["parts"],"missing parts")
    nodes={}
    for n in data["nodes"]:
        key=n.get("id")
        require(isinstance(key,str) and re.fullmatch(r"[A-Za-z0-9_-]{1,48}",key) and key not in nodes,"invalid/duplicate node id")
        require(pair(n.get("pivot_global")) and pair(n.get("rotation_range")),f"invalid node {key}")
        require(n["rotation_range"][0]<=0<=n["rotation_range"][1],"range must include rest")
        nodes[key]=n
    for key,n in nodes.items():
        chain=set(); p=key
        while p is not None:
            require(isinstance(p,str) and p in nodes and p not in chain,"missing parent or parent cycle")
            chain.add(p); p=nodes[p].get("parent")
    seen=set(); zseen=set()
    for p in data["parts"]:
        key=p.get("id")
        require(isinstance(key,str) and key and key not in seen,"invalid/duplicate part id")
        seen.add(key)
        require(isinstance(p.get("node"),str) and p["node"] in nodes,"unknown part node")
        for field in ("crop_origin","pixel_size","pivot_local"):
            require(pair(p.get(field)),f"invalid {field}")
        require(all(isinstance(v,int) for v in p["crop_origin"]+p["pixel_size"]) and min(p["pixel_size"])>0,"noninteger crop/size")
        require(all(abs(nodes[p["node"]]["pivot_global"][i]-p["crop_origin"][i]-p["pivot_local"][i])<1e-6 for i in range(2)),"pivot mismatch")
        require(isinstance(p.get("z_index"),int) and not isinstance(p["z_index"],bool) and p["z_index"] not in zseen,"invalid/duplicate z_index")
        zseen.add(p["z_index"])
        inside(manifest.parent,p.get("file"))
    require(motion.get("schema_version")=="1.0" and motion.get("angle_convention")=="relative-clockwise","unsupported motion plan")
    targets=motion.get("target_ranges")
    require(isinstance(targets,dict) and set(targets)==set(nodes),"target_ranges must cover all nodes")
    for key,bounds in targets.items():
        require(pair(bounds) and bounds[0]<=0<=bounds[1],f"invalid target range {key}")
        require(bounds[0]<=nodes[key]["rotation_range"][0]<=nodes[key]["rotation_range"][1]<=bounds[1],"accepted range must be within target range")
    require(isinstance(motion.get("poses"),list) and motion["poses"],"missing poses")
    seen=set()
    for p in motion["poses"]:
        key=p.get("id")
        require(isinstance(key,str) and re.fullmatch(r"[A-Za-z0-9_+-]{1,80}",key) and key not in seen,"invalid/duplicate pose id")
        seen.add(key)
        require(isinstance(p.get("angles"),dict),"invalid pose angles")
        for node,angle in p["angles"].items():
            require(node in nodes and finite(angle) and targets[node][0]<=angle<=targets[node][1],"pose outside target ranges")
    return data,motion,nodes


def build(data,motion,nodes,manifest,out,trial):
    identity="SPP_"+hashlib.sha256(str(out).encode()).hexdigest()[:8]
    require(identity not in bpy.data.scenes,"task scene exists; use a fresh process or a different output directory")
    scene=bpy.data.scenes.new(identity)
    scene["owner"]=identity
    bpy.context.window.scene=scene
    collection=bpy.data.collections.new(identity+"_parts"); scene.collection.children.link(collection)
    w,h=data["source_size"]; scale=0.01
    def point(p,z=0): return Vector(((p[0]-w/2)*scale,(h/2-p[1])*scale,z))
    armdata=bpy.data.armatures.new(identity+"_bones")
    rig=bpy.data.objects.new(identity+"_rig",armdata); collection.objects.link(rig)
    rig["owner"]=identity; rig["mode"]="trial_not_accepted" if trial else "accepted_ranges"
    rig["target_ranges_json"]=json.dumps(motion["target_ranges"])
    rig["manifest_path"]=str(manifest)
    rig.show_in_front=True; armdata.display_type="STICK"
    bpy.context.view_layer.objects.active=rig; rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    try:
        for key,n in nodes.items():
            b=armdata.edit_bones.new(key); b.head=point(n["pivot_global"])
            children=[child for child in nodes.values() if child.get("parent")==key]
            candidates=[point(child["pivot_global"]) for child in children if (point(child["pivot_global"])-b.head).length>0.01]
            b.tail=min(candidates,key=lambda p:(p-b.head).length) if candidates else b.head+Vector((0,0.22,0))
            b.align_roll(Vector((0,0,1)))
        for key,n in nodes.items():
            if n.get("parent") is not None:
                armdata.edit_bones[key].parent=armdata.edit_bones[n["parent"]]
                armdata.edit_bones[key].use_connect=False
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")
    ranges=motion["target_ranges"] if trial else {key:n["rotation_range"] for key,n in nodes.items()}
    for key,bounds in ranges.items():
        pb=rig.pose.bones[key]; pb.rotation_mode="XYZ"
        pb.lock_location=(True,True,True); pb.lock_scale=(True,True,True); pb.lock_rotation=(True,True,False)
        pb["screen_clockwise_min"]=bounds[0]; pb["screen_clockwise_max"]=bounds[1]
        pb["target_range_json"]=json.dumps(motion["target_ranges"][key])
        c=pb.constraints.new("LIMIT_ROTATION"); c.name="Planar FK limits"
        c.owner_space="LOCAL"; c.use_limit_x=True; c.use_limit_y=True; c.use_limit_z=True
        c.min_x=c.max_x=c.min_y=c.max_y=0
        c.min_z=math.radians(-bounds[1]); c.max_z=math.radians(-bounds[0])
        if "use_transform_limit" in c.bl_rna.properties:
            c.use_transform_limit=True
    meshes={}
    for p in data["parts"]:
        ox,oy=p["crop_origin"]; pw,ph=p["pixel_size"]; depth=p["z_index"]*0.005
        verts=[point((ox,oy)),point((ox+pw,oy)),point((ox+pw,oy+ph)),point((ox,oy+ph))]
        mesh=bpy.data.meshes.new(identity+"_"+p["id"]); mesh.from_pydata(verts,[],[(0,3,2,1)]); mesh.update()
        obj=bpy.data.objects.new(mesh.name,mesh); collection.objects.link(obj); obj["owner"]=identity; obj["part_id"]=p["id"]
        # EEVEE blended transparency sorts objects by origin: geometry-only z
        # offsets leave coincident origins and can put hidden wrist tabs on top.
        obj.location.z=depth
        uv=mesh.uv_layers.new(name="SourceUV")
        coords=((0,1),(1,1),(1,0),(0,0))
        for loop in mesh.loops: uv.data[loop.index].uv=coords[loop.vertex_index]
        group=obj.vertex_groups.new(name=p["node"]); group.add(list(range(4)),1,"REPLACE")
        modifier=obj.modifiers.new("Rigid single-bone binding","ARMATURE"); modifier.object=rig
        image=bpy.data.images.load(str(inside(manifest.parent,p["file"])),check_existing=False)
        require(list(image.size)==p["pixel_size"],f"PNG dimensions mismatch: {p['id']}")
        require(image.channels==4,f"PNG missing alpha: {p['id']}")
        image.alpha_mode="STRAIGHT"; image.pack()
        material=bpy.data.materials.new(mesh.name+"_alpha"); material.use_nodes=True
        methods={v.identifier for v in material.bl_rna.properties["surface_render_method"].enum_items} if "surface_render_method" in material.bl_rna.properties else set()
        if "BLENDED" in methods: material.surface_render_method="BLENDED"
        elif hasattr(material,"blend_method"): material.blend_method="BLEND"
        else: raise RuntimeError("Required alpha blending capability unavailable")
        nt=material.node_tree; nt.nodes.clear()
        tex=nt.nodes.new("ShaderNodeTexImage"); tex.image=image
        emission=nt.nodes.new("ShaderNodeEmission"); transparent=nt.nodes.new("ShaderNodeBsdfTransparent")
        mix=nt.nodes.new("ShaderNodeMixShader"); output=nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(tex.outputs["Color"],emission.inputs["Color"])
        nt.links.new(tex.outputs["Alpha"],mix.inputs[0]); nt.links.new(transparent.outputs[0],mix.inputs[1]); nt.links.new(emission.outputs[0],mix.inputs[2]); nt.links.new(mix.outputs[0],output.inputs["Surface"])
        obj.data.materials.append(material); meshes[p["id"]]=obj
    camera_data=bpy.data.cameras.new(identity+"_ortho"); camera_data.type="ORTHO"; camera_data.ortho_scale=h*scale
    camera=bpy.data.objects.new(camera_data.name,camera_data); collection.objects.link(camera); camera.location=(0,0,30); scene.camera=camera
    scene.render.resolution_x=w//2; scene.render.resolution_y=h//2; scene.render.resolution_percentage=100
    frame=camera_data.view_frame(scene=scene)
    camera_data.ortho_scale*=h*scale/(max(v.y for v in frame)-min(v.y for v in frame))
    scene.render.film_transparent=True; scene.render.image_settings.file_format="PNG"; scene.render.image_settings.color_mode="RGBA"
    scene.view_settings.view_transform="Standard"; scene.view_settings.look="None"; scene.view_settings.exposure=0; scene.view_settings.gamma=1
    scene.render.engine="BLENDER_EEVEE_NEXT"
    if hasattr(scene,"eevee") and hasattr(scene.eevee,"taa_render_samples"): scene.eevee.taa_render_samples=32
    scene.render.fps=24
    return scene,rig,meshes,point,ranges


def verify(data,motion,nodes,scene,rig,meshes,point,ranges,out,render):
    report={"blender_version":bpy.app.version_string,"rigid_weights_valid":True,"poses":[],"visual_qa":"requires_render_review"}
    for p in data["parts"]:
        obj=meshes[p["id"]]
        require(abs(obj.location.z-p["z_index"]*0.005)<1e-7,"transparent object sort depth mismatch")
        for v in obj.data.vertices:
            require(len(v.groups)==1 and obj.vertex_groups[v.groups[0].group].name==p["node"] and abs(v.groups[0].weight-1)<1e-6,"nonrigid vertex weight")
    cases=list(motion["poses"])
    # Extra invalid requests exercise clamping even when all targets are accepted.
    for key,bounds in ranges.items():
        if bounds[0]!=bounds[1]:
            cases.extend([{"id":f"limit_{key}_lo","angles":{key:bounds[0]-25}},
                          {"id":f"limit_{key}_hi","angles":{key:bounds[1]+25}}])
    for i,case in enumerate(cases):
        scene.frame_set(i+1)
        requested=case["angles"]
        for key,pb in rig.pose.bones.items():
            pb.rotation_euler=(0,0,math.radians(-requested.get(key,0)))
        bpy.context.view_layer.update()
        evaluated={k:max(ranges[k][0],min(ranges[k][1],requested.get(k,0))) for k in nodes}
        matrices={None:Matrix.Identity(4)}
        for key in nodes:
            chain=[]; cursor=key
            while cursor not in matrices:
                chain.append(cursor); cursor=nodes[cursor].get("parent")
            for cursor in reversed(chain):
                pivot=point(nodes[cursor]["pivot_global"])
                matrices[cursor]=matrices[nodes[cursor].get("parent")] @ Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(-evaluated[cursor]),4,"Z") @ Matrix.Translation(-pivot)
        depsgraph=bpy.context.evaluated_depsgraph_get(); max_error=0; max_length_error=0
        for p in data["parts"]:
            obj=meshes[p["id"]]; ev=obj.evaluated_get(depsgraph)
            verts=ev.data.vertices
            for v in obj.data.vertices:
                expected=matrices[p["node"]] @ v.co
                max_error=max(max_error,(verts[v.index].co-expected).length)
            for a,b in ((0,1),(1,2),(2,3),(3,0)):
                max_length_error=max(max_length_error,abs((verts[a].co-verts[b].co).length-(obj.data.vertices[a].co-obj.data.vertices[b].co).length))
        require(max_error<1e-4,f"evaluated transform mismatch at {case['id']}: {max_error}")
        require(max_length_error<1e-4,f"rigid part stretched at {case['id']}")
        limited={key:{"requested":angle,"evaluated":evaluated[key]} for key,angle in requested.items() if abs(angle-evaluated[key])>1e-6}
        report["poses"].append({"id":case["id"],"requested":requested,"evaluated":evaluated,"limited":limited,"max_vertex_error_world":max_error,"max_edge_length_error_world":max_length_error})
        if render and i<len(motion["poses"]):
            scene.render.filepath=str(out/"preview"/(case["id"]+".png")); bpy.ops.render.render(write_still=True,scene=scene.name)
    for pb in rig.pose.bones: pb.rotation_euler=(0,0,0)
    scene.frame_set(1); scene.frame_end=len(motion["poses"]); bpy.context.view_layer.update()
    rig["pose_plan_json"]=json.dumps(motion)
    # Store selectable reference poses as keyed FK controls, preserving constraints.
    for i,case in enumerate(motion["poses"]):
        for key,pb in rig.pose.bones.items():
            angle=case["angles"].get(key,0)
            angle=max(ranges[key][0],min(ranges[key][1],angle))
            pb.rotation_euler=(0,0,math.radians(-angle)); pb.keyframe_insert(data_path="rotation_euler",frame=i*12+1)
        scene.timeline_markers.new(case["id"],frame=i*12+1)
    scene.frame_end=(len(motion["poses"])-1)*12+1; scene.frame_set(1); bpy.context.view_layer.update()
    report.update({"nodes":len(nodes),"parts":len(meshes),"effective_ranges":ranges,"transform_and_limit_tests":"passed",
                   "max_vertex_error_world":max(p["max_vertex_error_world"] for p in report["poses"]),
                   "packed_texture_count":sum(1 for obj in meshes.values() for mat in obj.data.materials for n in mat.node_tree.nodes if n.type=="TEX_IMAGE" and n.image.packed_file is not None)})
    return report


def main():
    args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest",type=Path,required=True); parser.add_argument("--motion-plan",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True); parser.add_argument("--trial",action="store_true"); parser.add_argument("--render",action="store_true")
    cfg=parser.parse_args(args); manifest=cfg.manifest.resolve(); out=cfg.out.resolve()
    require(not (out/"rig.blend").exists(),"rig.blend already exists; choose a new review directory")
    data,motion,nodes=inputs(manifest,cfg.motion_plan.resolve())
    out.mkdir(parents=True,exist_ok=True); (out/"preview").mkdir(exist_ok=True)
    scene,rig,meshes,point,ranges=build(data,motion,nodes,manifest,out,cfg.trial)
    report=verify(data,motion,nodes,scene,rig,meshes,point,ranges,out,cfg.render)
    report["mode"]="trial_not_accepted" if cfg.trial else "accepted_ranges"
    report["unmet_targets"]={key:{"target":motion["target_ranges"][key],"accepted":n["rotation_range"]} for key,n in nodes.items() if motion["target_ranges"][key]!=n["rotation_range"]}
    report["scene_name"]=scene.name; report["rig_name"]=rig.name
    # Save an immediately inspectable camera/pose view for interactive editing.
    bpy.context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode="POSE")
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=="VIEW_3D":
                area.spaces.active.region_3d.view_perspective="CAMERA"
                area.spaces.active.shading.type="MATERIAL"
    bpy.ops.wm.save_as_mainfile(filepath=str(out/"rig.blend"))
    (out/"rig-test-results.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({key:value for key,value in report.items() if key!="poses"},ensure_ascii=False))


if __name__=="__main__":
    main()

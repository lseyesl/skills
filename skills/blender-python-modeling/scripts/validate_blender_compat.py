"""Smoke-test Blender APIs used by the blender-python-modeling skill.

Run only in a disposable Blender session, preferably:
blender --background --factory-startup --python validate_blender_compat.py

The script creates temporary datablocks, removes them, prints one JSON report,
and exits non-zero if a required recipe fails.
"""

from __future__ import annotations

import json
import sys
import tempfile
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

import bmesh
import bpy
from mathutils import Vector


PREFIX = "__BLENDER_SKILL_COMPAT__"
REPORT: dict[str, Any] = {
    "blender": ".".join(map(str, bpy.app.version)),
    "python": sys.version.split()[0],
    "required": {},
    "capabilities": {},
}


def record(name: str, fn: Callable[[], Any]) -> Any:
    try:
        result = fn()
        REPORT["required"][name] = {"ok": True, "result": result}
        return result
    except Exception as exc:  # pragma: no cover - executed inside Blender
        REPORT["required"][name] = {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(limit=5),
        }
        return None


def remove_temporary_data() -> None:
    for obj in list(bpy.data.objects):
        if obj.name.startswith(PREFIX):
            bpy.data.objects.remove(obj, do_unlink=True)
    for collection in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.node_groups,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.armatures,
        bpy.data.actions,
        bpy.data.worlds,
        bpy.data.images,
        bpy.data.scenes,
    ):
        for datablock in list(collection):
            if datablock.name.startswith(PREFIX) and datablock.users == 0:
                collection.remove(datablock)


def test_bmesh_and_modifiers() -> dict[str, Any]:
    mesh = bpy.data.meshes.new(f"{PREFIX}Mesh")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.bevel(
        bm,
        geom=list(bm.edges),
        offset=0.05,
        segments=2,
        affect="EDGES",
    )
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate(verbose=False)
    mesh.update()

    obj = bpy.data.objects.new(f"{PREFIX}Object", mesh)
    bpy.context.scene.collection.objects.link(obj)

    mirror = obj.modifiers.new(f"{PREFIX}Mirror", "MIRROR")
    mirror.use_axis = (True, False, False)
    mirror.use_clip = True

    solidify = obj.modifiers.new(f"{PREFIX}Solidify", "SOLIDIFY")
    solidify.thickness = 0.05

    bevel = obj.modifiers.new(f"{PREFIX}Bevel", "BEVEL")
    bevel.width = 0.02
    bevel.segments = 2

    subsurf = obj.modifiers.new(f"{PREFIX}Subdivision", "SUBSURF")
    subsurf.levels = 1
    subsurf.render_levels = 2

    boolean = obj.modifiers.new(f"{PREFIX}Boolean", "BOOLEAN")
    boolean.operation = "DIFFERENCE"
    boolean.solver = "EXACT"

    for polygon in mesh.polygons:
        polygon.use_smooth = True

    return {
        "vertices": len(mesh.vertices),
        "polygons": len(mesh.polygons),
        "modifiers": [modifier.type for modifier in obj.modifiers],
    }


def test_curve() -> dict[str, Any]:
    curve = bpy.data.curves.new(f"{PREFIX}Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 8
    curve.bevel_depth = 0.02
    curve.bevel_resolution = 2
    curve.use_fill_caps = True
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(2)
    for point, co in zip(
        spline.bezier_points,
        ((-1.0, 0.0, 0.0), (0.0, 0.5, 0.5), (1.0, 0.0, 0.0)),
        strict=True,
    ):
        point.co = co
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(f"{PREFIX}CurveObject", curve)
    bpy.context.scene.collection.objects.link(obj)
    return {"splines": len(curve.splines), "points": len(spline.bezier_points)}


def test_uv_data() -> dict[str, Any]:
    obj = bpy.data.objects.get(f"{PREFIX}Object")
    if obj is None or obj.type != "MESH":
        raise RuntimeError("BMesh compatibility object is unavailable")

    uv_layer = obj.data.uv_layers.new(name=f"{PREFIX}UVMap")
    obj.data.uv_layers.active = uv_layer
    uv_layer.active_render = True
    for loop_uv in uv_layer.data:
        loop_uv.uv = (0.25, 0.75)
    obj.data.update()

    if len(uv_layer.data) != len(obj.data.loops):
        raise RuntimeError("UV loop count does not match mesh loop count")
    return {
        "layer": uv_layer.name,
        "loops": len(uv_layer.data),
        "active_render": uv_layer.active_render,
        "unwrap_parameters": sorted(
            bpy.ops.uv.unwrap.get_rna_type().properties.keys()
        ),
        "pack_parameters": sorted(
            bpy.ops.uv.pack_islands.get_rna_type().properties.keys()
        ),
    }


def test_glb_roundtrip() -> dict[str, Any]:
    mesh = bpy.data.meshes.new(f"{PREFIX}ExportMesh")
    mesh.from_pydata(
        [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)],
        [],
        [(0, 1, 2)],
    )
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for loop_uv, coordinate in zip(
        uv_layer.data,
        ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)),
        strict=True,
    ):
        loop_uv.uv = coordinate

    obj = bpy.data.objects.new(f"{PREFIX}ExportObject", mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    with tempfile.TemporaryDirectory(prefix="blender-skill-export-") as directory:
        output_path = Path(directory) / "roundtrip.glb"
        export_result = bpy.ops.export_scene.gltf(
            filepath=str(output_path),
            export_format="GLB",
            use_selection=True,
            export_apply=False,
            export_materials="NONE",
            export_animations=False,
            check_existing=True,
        )
        if "FINISHED" not in export_result or not output_path.is_file():
            raise RuntimeError(f"GLB export failed: {export_result}")
        byte_size = output_path.stat().st_size
        if byte_size <= 0:
            raise RuntimeError("GLB export produced an empty file")

        bpy.data.objects.remove(obj, do_unlink=True)
        before = set(bpy.data.objects)
        import_result = bpy.ops.import_scene.gltf(filepath=str(output_path))
        imported = [item for item in bpy.data.objects if item not in before]
        if "FINISHED" not in import_result or not imported:
            raise RuntimeError(f"GLB import failed: {import_result}")

        imported_meshes = [item for item in imported if item.type == "MESH"]
        if not imported_meshes or len(imported_meshes[0].data.polygons) != 1:
            raise RuntimeError("GLB round-trip changed the test mesh topology")
        return {
            "bytes": byte_size,
            "imported_objects": [item.name for item in imported],
            "polygons": len(imported_meshes[0].data.polygons),
        }


def test_character_data() -> dict[str, Any]:
    armature_data = bpy.data.armatures.new(f"{PREFIX}ArmatureData")
    armature = bpy.data.objects.new(f"{PREFIX}Armature", armature_data)
    bpy.context.scene.collection.objects.link(armature)
    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")
    try:
        bone = armature_data.edit_bones.new("root")
        bone.head = (0.0, 0.0, 0.0)
        bone.tail = (0.0, 0.0, 1.0)
        bone.use_deform = True
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")

    mesh = bpy.data.meshes.new(f"{PREFIX}CharacterMesh")
    mesh.from_pydata(
        [(-0.5, 0.0, 0.0), (0.5, 0.0, 0.0), (0.0, 0.0, 1.0)],
        [],
        [(0, 1, 2)],
    )
    mesh.update()
    character = bpy.data.objects.new(f"{PREFIX}Character", mesh)
    bpy.context.scene.collection.objects.link(character)
    group = character.vertex_groups.new(name="root")
    group.add([vertex.index for vertex in mesh.vertices], 1.0, "REPLACE")
    modifier = character.modifiers.new(f"{PREFIX}ArmatureModifier", "ARMATURE")
    modifier.object = armature

    influence_counts = [len(vertex.groups) for vertex in mesh.vertices]
    weight_sums = [sum(item.weight for item in vertex.groups) for vertex in mesh.vertices]
    if any(count != 1 for count in influence_counts):
        raise RuntimeError(f"unexpected influence counts: {influence_counts}")
    if any(abs(total - 1.0) > 1e-6 for total in weight_sums):
        raise RuntimeError(f"unnormalized test weights: {weight_sums}")
    return {
        "bones": len(armature.data.bones),
        "influence_counts": influence_counts,
        "weight_sums": weight_sums,
        "modifier": modifier.type,
    }


def test_asset_metadata() -> dict[str, Any]:
    obj = bpy.data.objects.get(f"{PREFIX}Object")
    if obj is None:
        raise RuntimeError("compatibility object is unavailable")
    if not hasattr(obj, "asset_mark"):
        raise RuntimeError("Object.asset_mark is unavailable")
    obj.asset_mark()
    try:
        obj.asset_data.description = "Compatibility smoke-test asset"
        obj.asset_data.tags.new("compatibility")
        return {
            "description": obj.asset_data.description,
            "tags": [tag.name for tag in obj.asset_data.tags],
        }
    finally:
        obj.asset_clear()


def test_compositor_nodes() -> dict[str, Any]:
    scene = bpy.data.scenes.new(f"{PREFIX}CompositorScene")
    scene.use_nodes = True
    tree = scene.node_tree
    nodes = tree.nodes
    nodes.clear()
    render_layers = nodes.new("CompositorNodeRLayers")
    denoise = nodes.new("CompositorNodeDenoise")
    cryptomatte = nodes.new("CompositorNodeCryptomatteV2")
    file_output = nodes.new("CompositorNodeOutputFile")
    composite = nodes.new("CompositorNodeComposite")
    tree.links.new(render_layers.outputs["Image"], denoise.inputs["Image"])
    tree.links.new(denoise.outputs["Image"], composite.inputs["Image"])

    view_layer = scene.view_layers[0]
    view_layer.use_pass_normal = True
    view_layer.use_pass_cryptomatte_object = True
    return {
        "nodes": [node.bl_idname for node in nodes],
        "normal_pass": view_layer.use_pass_normal,
        "cryptomatte_object_pass": view_layer.use_pass_cryptomatte_object,
        "file_output_slots": [slot.path for slot in file_output.file_slots],
        "cryptomatte": cryptomatte.bl_idname,
    }


def test_physics_setup() -> dict[str, Any]:
    mesh = bpy.data.meshes.new(f"{PREFIX}PhysicsMesh")
    mesh.from_pydata(
        [
            (-0.5, -0.5, 0.0),
            (0.5, -0.5, 0.0),
            (0.5, 0.5, 0.0),
            (-0.5, 0.5, 0.0),
        ],
        [],
        [(0, 1, 2, 3)],
    )
    mesh.update()
    obj = bpy.data.objects.new(f"{PREFIX}PhysicsObject", mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    rigid_result = bpy.ops.rigidbody.object_add()
    if "FINISHED" not in rigid_result or obj.rigid_body is None:
        raise RuntimeError(f"rigid-body setup failed: {rigid_result}")
    obj.rigid_body.collision_shape = "BOX"

    cloth = obj.modifiers.new(f"{PREFIX}Cloth", "CLOTH")
    if cloth.point_cache is None:
        raise RuntimeError("cloth modifier did not expose a point cache")
    return {
        "rigid_body": obj.rigid_body.type,
        "collision_shape": obj.rigid_body.collision_shape,
        "cloth_modifier": cloth.type,
        "cache_frame_range": [cloth.point_cache.frame_start, cloth.point_cache.frame_end],
    }


def socket_by_identifier(node: bpy.types.Node, *identifiers: str) -> bpy.types.NodeSocket:
    wanted = set(identifiers)
    for socket in node.inputs:
        if socket.identifier in wanted:
            return socket
    available = [socket.identifier for socket in node.inputs]
    raise KeyError(f"No socket {sorted(wanted)} on {node.bl_idname}; available={available}")


def test_material_nodes() -> dict[str, Any]:
    material = bpy.data.materials.new(f"{PREFIX}Material")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    principled = next(node for node in nodes if node.type == "BSDF_PRINCIPLED")
    created = [
        nodes.new("ShaderNodeTexNoise"),
        nodes.new("ShaderNodeValToRGB"),
        nodes.new("ShaderNodeTexImage"),
        nodes.new("ShaderNodeNormalMap"),
    ]
    socket_by_identifier(principled, "Base Color").default_value = (0.12, 0.24, 0.8, 1.0)
    socket_by_identifier(principled, "Metallic").default_value = 0.25
    socket_by_identifier(principled, "Roughness").default_value = 0.4
    return {
        "principled_bl_idname": principled.bl_idname,
        "input_identifiers": [socket.identifier for socket in principled.inputs],
        "recipe_nodes": [node.bl_idname for node in created],
    }


def test_geometry_nodes() -> dict[str, Any]:
    group = bpy.data.node_groups.new(f"{PREFIX}GeometryNodes", "GeometryNodeTree")
    group.interface.new_socket(
        name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry"
    )
    group.interface.new_socket(
        name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry"
    )
    input_node = group.nodes.new("NodeGroupInput")
    output_node = group.nodes.new("NodeGroupOutput")
    geometry_output = next(socket for socket in input_node.outputs if socket.type == "GEOMETRY")
    geometry_input = next(socket for socket in output_node.inputs if socket.type == "GEOMETRY")
    group.links.new(geometry_output, geometry_input)
    recipe_nodes = [
        group.nodes.new("GeometryNodeMeshCube"),
        group.nodes.new("GeometryNodeSetPosition"),
        group.nodes.new("GeometryNodeJoinGeometry"),
        group.nodes.new("GeometryNodeCurvePrimitiveLine"),
        group.nodes.new("GeometryNodeCurveToMesh"),
        group.nodes.new("GeometryNodeInstanceOnPoints"),
    ]

    mesh_obj = bpy.data.objects.get(f"{PREFIX}Object")
    modifier = mesh_obj.modifiers.new(f"{PREFIX}GeometryNodesModifier", "NODES")
    modifier.node_group = group
    return {
        "interface_api": "NodeTree.interface.new_socket",
        "nodes": [node.bl_idname for node in group.nodes],
        "recipe_nodes": [node.bl_idname for node in recipe_nodes],
    }


def test_camera_light_animation() -> dict[str, Any]:
    camera_data = bpy.data.cameras.new(f"{PREFIX}CameraData")
    camera = bpy.data.objects.new(f"{PREFIX}Camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = (4.0, -4.0, 3.0)
    camera.rotation_euler = (Vector((0.0, 0.0, 0.0)) - camera.location).to_track_quat(
        "-Z", "Y"
    ).to_euler()
    camera_data.lens = 50.0

    light_data = bpy.data.lights.new(f"{PREFIX}KeyData", "AREA")
    light_data.energy = 500.0
    light_data.shape = "DISK"
    light_data.size = 3.0
    light = bpy.data.objects.new(f"{PREFIX}Key", light_data)
    bpy.context.scene.collection.objects.link(light)

    target = bpy.data.objects.new(f"{PREFIX}Target", None)
    bpy.context.scene.collection.objects.link(target)
    constraint = camera.constraints.new("TRACK_TO")
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"

    driver_curve = light_data.driver_add("energy")
    driver = driver_curve.driver
    driver.type = "SCRIPTED"
    variable = driver.variables.new()
    variable.name = "camera_x"
    variable.type = "TRANSFORMS"
    variable.targets[0].id = camera
    variable.targets[0].transform_type = "LOC_X"
    variable.targets[0].transform_space = "WORLD_SPACE"
    driver.expression = "max(0.0, camera_x * 100.0)"

    camera.location.x = 4.0
    camera.keyframe_insert(data_path="location", frame=1)
    camera.location.x = 5.0
    camera.keyframe_insert(data_path="location", frame=24)
    action = camera.animation_data.action
    if action is None:
        raise RuntimeError("keyframe_insert did not create an action")
    return {
        "camera_lens": camera_data.lens,
        "light_type": light_data.type,
        "action": action.name,
        "constraint": constraint.type,
        "driver_variables": len(driver.variables),
    }


def test_world_nodes() -> dict[str, Any]:
    world = bpy.data.worlds.new(f"{PREFIX}World")
    world.use_nodes = True
    background = next(node for node in world.node_tree.nodes if node.type == "BACKGROUND")
    socket_by_identifier(background, "Color").default_value = (0.03, 0.03, 0.03, 1.0)
    socket_by_identifier(background, "Strength").default_value = 0.3
    return {
        "background": background.bl_idname,
        "input_identifiers": [socket.identifier for socket in background.inputs],
    }


def list_enum_identifiers(owner: Any, property_name: str) -> list[str]:
    prop = owner.bl_rna.properties[property_name]
    return [item.identifier for item in prop.enum_items]


def inspect_capabilities() -> None:
    scene = bpy.context.scene
    group = bpy.data.node_groups.get(f"{PREFIX}GeometryNodes")
    REPORT["capabilities"] = {
        "render_engine_current": scene.render.engine,
        "image_file_formats": list_enum_identifiers(
            scene.render.image_settings, "file_format"
        ),
        "mesh_remove_doubles_operator": hasattr(bpy.ops.mesh, "remove_doubles"),
        "mesh_merge_by_distance_operator": hasattr(
            bpy.ops.mesh, "merge_by_distance"
        ),
        "pose_apply_to_basis_operator": hasattr(bpy.ops.pose, "apply_to_basis"),
        "scene_eevee_property": hasattr(scene, "eevee"),
        "node_tree_interface_api": bool(group and hasattr(group, "interface")),
        "export_operator_parameters": {
            path: operator_parameters(path)
            for path in (
                "export_scene.gltf",
                "export_scene.fbx",
                "wm.obj_export",
                "wm.stl_export",
            )
        },
        "weight_operator_parameters": {
            path: operator_parameters(path)
            for path in (
                "object.vertex_group_clean",
                "object.vertex_group_normalize_all",
                "object.vertex_group_limit_total",
            )
        },
        "physics_operator_parameters": {
            "rigidbody.object_add": operator_parameters("rigidbody.object_add"),
        },
    }


def operator_parameters(path: str) -> list[str] | None:
    namespace, name = path.split(".", 1)
    operator = getattr(getattr(bpy.ops, namespace), name)
    try:
        return sorted(operator.get_rna_type().properties.keys())
    except KeyError:
        return None


def main() -> None:
    remove_temporary_data()
    try:
        record("bmesh_and_modifiers", test_bmesh_and_modifiers)
        record("uv_data", test_uv_data)
        record("glb_roundtrip", test_glb_roundtrip)
        record("character_data", test_character_data)
        record("asset_metadata", test_asset_metadata)
        record("compositor_nodes", test_compositor_nodes)
        record("physics_setup", test_physics_setup)
        record("curve", test_curve)
        record("material_nodes", test_material_nodes)
        record("geometry_nodes", test_geometry_nodes)
        record("camera_light_animation", test_camera_light_animation)
        record("world_nodes", test_world_nodes)
        inspect_capabilities()
    finally:
        remove_temporary_data()

    failures = [name for name, value in REPORT["required"].items() if not value["ok"]]
    REPORT["ok"] = not failures
    REPORT["failures"] = failures
    print(json.dumps(REPORT, ensure_ascii=False, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

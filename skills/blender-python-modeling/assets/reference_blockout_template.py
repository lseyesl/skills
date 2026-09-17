"""Create a normalized Blender blockout from reference-analysis JSON.

Copy this file into the target project, then set TASK_ID and ANALYSIS_PATH.
The template creates only task-owned data and does not save or export a file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import bmesh
import bpy
from mathutils import Matrix, Vector


TASK_ID = "replace-me"
ANALYSIS_PATH = Path("/absolute/path/reference-analysis.json")
OWNER_KEY = "codex_task_id"
COLLECTION_NAME = f"GEN_{TASK_ID}"


def mark_owned(datablock: Any) -> Any:
    datablock[OWNER_KEY] = TASK_ID
    return datablock


def generated_collection() -> bpy.types.Collection:
    collection = bpy.data.collections.get(COLLECTION_NAME)
    if collection is None:
        collection = bpy.data.collections.new(COLLECTION_NAME)
        bpy.context.scene.collection.children.link(collection)
    return collection


def remove_previous_generated_data() -> None:
    for obj in list(bpy.data.objects):
        if obj.get(OWNER_KEY) == TASK_ID:
            bpy.data.objects.remove(obj, do_unlink=True)
    for datablocks in (bpy.data.meshes, bpy.data.cameras):
        for datablock in list(datablocks):
            if datablock.get(OWNER_KEY) == TASK_ID and datablock.users == 0:
                datablocks.remove(datablock)


def load_dimensions() -> tuple[Vector, dict[str, Any]]:
    analysis = json.loads(ANALYSIS_PATH.read_text(encoding="utf-8"))
    fused = analysis.get("multi_view_dimensions", {})
    if not fused.get("available"):
        raise RuntimeError(
            "Reference analysis has no fused dimensions; provide at least two "
            "orthographic-like front/side/top views or define a manual envelope"
        )
    values = fused["dimensions"]
    dimensions = Vector((values["width"], values["depth"], values["height"]))
    if min(dimensions) <= 0:
        raise ValueError(f"Invalid fused dimensions: {tuple(dimensions)}")
    return dimensions, analysis


def create_envelope(dimensions: Vector) -> bpy.types.Object:
    mesh = mark_owned(bpy.data.meshes.new(f"MESH_{TASK_ID}_reference_envelope"))
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.transform(
        bm,
        matrix=Matrix.Diagonal((*dimensions, 1.0)),
        verts=bm.verts,
    )
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate(verbose=True)
    mesh.update()
    obj = mark_owned(bpy.data.objects.new(f"GEO_{TASK_ID}_reference_envelope", mesh))
    generated_collection().objects.link(obj)
    obj.display_type = "WIRE"
    obj.show_in_front = True
    return obj


def create_camera(name: str, location: Vector, scale: float) -> bpy.types.Object:
    camera_data = mark_owned(bpy.data.cameras.new(f"CAMDATA_{TASK_ID}_{name}"))
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = scale
    camera_data.clip_start = 0.001
    camera_data.clip_end = max(100.0, location.length * 10.0)
    camera = mark_owned(bpy.data.objects.new(f"CAM_{TASK_ID}_{name}", camera_data))
    generated_collection().objects.link(camera)
    camera.location = location
    camera.rotation_euler = (Vector((0.0, 0.0, 0.0)) - location).to_track_quat(
        "-Z", "Y"
    ).to_euler()
    return camera


def create_reference_cameras(dimensions: Vector) -> list[bpy.types.Object]:
    width, depth, height = dimensions
    distance = max(dimensions) * 3.0 + 1.0
    margin = 1.25
    return [
        create_camera("front", Vector((0.0, -distance, 0.0)), max(width, height) * margin),
        create_camera("side", Vector((distance, 0.0, 0.0)), max(depth, height) * margin),
        create_camera("top", Vector((0.0, 0.0, distance)), max(width, depth) * margin),
    ]


def main() -> None:
    if TASK_ID == "replace-me":
        raise RuntimeError("Set TASK_ID before running this template")
    if not ANALYSIS_PATH.is_file():
        raise FileNotFoundError(ANALYSIS_PATH)

    remove_previous_generated_data()
    dimensions, analysis = load_dimensions()
    envelope = create_envelope(dimensions)
    cameras = create_reference_cameras(dimensions)
    bpy.context.view_layer.update()
    print(
        json.dumps(
            {
                "task_id": TASK_ID,
                "scale_mode": analysis.get("scale_policy", {}).get("mode", "unknown"),
                "dimensions": [round(value, 6) for value in dimensions],
                "envelope": envelope.name,
                "cameras": [camera.name for camera in cameras],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

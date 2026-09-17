"""Template for deterministic, task-scoped Blender scene generation.

Copy this file into the target project's scripts/blender/ directory and replace
the TASK_ID and build function. It deliberately does not save or export files.
"""

from __future__ import annotations

import json
from typing import Any

import bmesh
import bpy
from mathutils import Matrix


TASK_ID = "replace-me"
COLLECTION_NAME = f"GEN_{TASK_ID}"
OWNER_KEY = "codex_task_id"


def generated_collection() -> bpy.types.Collection:
    collection = bpy.data.collections.get(COLLECTION_NAME)
    if collection is None:
        collection = bpy.data.collections.new(COLLECTION_NAME)
        bpy.context.scene.collection.children.link(collection)
    return collection


def remove_previous_generated_data() -> None:
    """Delete only objects and orphaned meshes explicitly owned by this task."""
    for obj in list(bpy.data.objects):
        if obj.get(OWNER_KEY) == TASK_ID:
            bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        if mesh.get(OWNER_KEY) == TASK_ID and mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def mark_owned(data: Any) -> Any:
    data[OWNER_KEY] = TASK_ID
    return data


def build_geometry() -> list[bpy.types.Object]:
    """Replace this sample cube with the task's actual model."""
    collection = generated_collection()
    mesh = mark_owned(bpy.data.meshes.new(f"MESH_{TASK_ID}_body"))

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.transform(
        bm,
        matrix=Matrix.Diagonal((1.0, 1.0, 1.0, 1.0)),
        verts=bm.verts,
    )
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate(verbose=True)
    mesh.update()

    obj = mark_owned(bpy.data.objects.new(f"GEO_{TASK_ID}_body", mesh))
    collection.objects.link(obj)
    return [obj]


def validate_result(objects: list[bpy.types.Object]) -> dict[str, Any]:
    if not objects:
        raise RuntimeError("The build created no objects")

    result = {
        "task_id": TASK_ID,
        "objects": [],
        "warnings": [],
    }
    for obj in objects:
        item = {
            "name": obj.name,
            "type": obj.type,
            "dimensions": [round(value, 6) for value in obj.dimensions],
        }
        if obj.type == "MESH":
            item["vertices"] = len(obj.data.vertices)
            item["polygons"] = len(obj.data.polygons)
        result["objects"].append(item)
    return result


def main() -> None:
    if TASK_ID == "replace-me":
        raise RuntimeError("Set TASK_ID before running this template")

    remove_previous_generated_data()
    objects = build_geometry()
    bpy.context.view_layer.update()
    print(json.dumps(validate_result(objects), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

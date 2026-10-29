"""Template for deterministic, task-scoped Blender scene generation.

Copy this file into the target project's scripts/blender/ directory and replace
the TASK_ID and build function. It deliberately does not save or export files.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import bmesh
import bpy
from mathutils import Matrix


TASK_ID = "replace-me"
COLLECTION_NAME = f"GEN_{TASK_ID}"
OWNER_KEY = "codex_task_id"
BUILD_MODE = None  # Set explicitly: 'reference', 'original', or 'waived'.
WAIVER_REASON = ""  # For 'waived', record the user's actual instruction.
REFERENCE_HELPER_DIR = None  # Absolute path to this skill's scripts/ directory.
REFERENCE_CONFIG = None  # Project-local reference-setup.json; see reference-workspace-tool.md.
CALIBRATION_REVIEW = None  # Inspected reference-visible orthographic captures.
COMPARISON_REVIEW = None  # Optional until blockout exists; required for a final claim.
INFERRED_DEPTH = None  # Sample builder only: explicitly chosen depth if no side evidence.


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


def geometry_transform() -> Matrix:
    """Resolve reference-derived sample inputs before replacing prior geometry."""
    transform = Matrix.Identity(4)
    if BUILD_MODE == 'reference':
        # Example of consuming actual imported image coordinates. Replace these
        # semantic anchors/profiles for the subject; do not keep arbitrary sizes.
        from reference_workspace import reference_landmark
        point = lambda name: reference_landmark(bpy.context.scene, TASK_ID, 'front', name)
        center = point('body_center')
        width = (point('body_right') - point('body_left')).length
        height = (point('body_top') - point('body_bottom')).length
        if INFERRED_DEPTH is None or INFERRED_DEPTH <= 0 or min(width, height) <= 0:
            raise RuntimeError('Supply valid anchor-derived dimensions and an explicitly inferred depth')
        transform = Matrix.Translation(center) @ Matrix.Diagonal((width, INFERRED_DEPTH, height, 1))
    return transform


def build_geometry(transform: Matrix) -> list[bpy.types.Object]:
    """Replace this sample cube with the task's actual model."""
    collection = generated_collection()
    mesh = mark_owned(bpy.data.meshes.new(f"MESH_{TASK_ID}_body"))
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.transform(
        bm,
        matrix=transform,
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
    if BUILD_MODE not in {'reference', 'original', 'waived'}:
        raise RuntimeError('Choose BUILD_MODE explicitly; reference-driven tasks cannot silently skip setup')
    if BUILD_MODE == 'waived' and not WAIVER_REASON.strip():
        raise RuntimeError('Record the user instruction waiving reference setup')
    if BUILD_MODE == 'reference':
        if not all([REFERENCE_HELPER_DIR, REFERENCE_CONFIG, CALIBRATION_REVIEW]):
            raise RuntimeError('Prepare/calibrate the workspace and inspect reference-visible views first')
        sys.path.insert(0, str(Path(REFERENCE_HELPER_DIR).resolve()))
        from reference_workspace import setup_references, require_reference_review
        config_path = Path(REFERENCE_CONFIG).resolve()
        setup_references(bpy.context.scene, TASK_ID, json.loads(config_path.read_text()), config_path.parent)
        require_reference_review(bpy.context.scene, TASK_ID, CALIBRATION_REVIEW)

    # Resolve required anchors/dimensions before deleting prior geometry too.
    transform = geometry_transform()
    remove_previous_generated_data()
    objects = build_geometry(transform)
    bpy.context.view_layer.update()
    result = validate_result(objects)
    if BUILD_MODE == 'reference':
        result['reference_stage'] = 'blockout_pending_comparison'
        if COMPARISON_REVIEW:
            require_reference_review(bpy.context.scene, TASK_ID, COMPARISON_REVIEW,
                                     phase='comparison', objects=objects)
            result['reference_stage'] = 'compared_against_imported_guides'
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

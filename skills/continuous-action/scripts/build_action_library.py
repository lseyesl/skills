"""Build assets/A.blend from FBX sources listed in assets/A.catalog.json.

Run: blender -b -t 2 --python scripts/build_action_library.py
"""
import json
import math
from pathlib import Path

import bpy


SKILL_DIR = Path(__file__).resolve().parents[1]
ROOT = SKILL_DIR.parents[1]
SOURCE_DIR = ROOT / ".tmp" / "fbx"
ASSET_DIR = SKILL_DIR / "assets"
CATALOG_PATH = ASSET_DIR / "A.catalog.json"


def main():
    specification = json.loads(CATALOG_PATH.read_text())
    clip_specs = specification.get("clips")
    base_id = specification.get("base_clip")
    if not isinstance(clip_specs, dict) or not clip_specs or base_id not in clip_specs:
        raise ValueError("A.catalog.json needs clips and a base_clip key present in clips")
    clip_order = [base_id, *(clip_id for clip_id in clip_specs if clip_id != base_id)]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 16
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.world = bpy.data.worlds.new("ReferenceWorld")
    scene.world.color = (0.8, 0.8, 0.8)
    catalog = {**specification, "library": "A.blend", "rig": "ActionRig", "meshes": [], "clips": {}}
    rig = None
    canonical_bones = None

    for clip_id in clip_order:
        clip_spec = clip_specs[clip_id]
        filename = clip_spec["source_fbx"]
        if Path(filename).name != filename:
            raise ValueError(f"source_fbx must be a filename: {filename}")
        path = SOURCE_DIR / filename
        if not path.is_file():
            raise FileNotFoundError(path)
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=str(path))
        imported = set(bpy.data.objects) - before
        armatures = [obj for obj in imported if obj.type == "ARMATURE"]
        if len(armatures) != 1:
            raise RuntimeError(f"{filename}: expected one armature, got {len(armatures)}")
        source_rig = armatures[0]
        action = source_rig.animation_data.action
        if action is None:
            raise RuntimeError(f"{filename}: no action")
        bone_names = {bone.name for bone in source_rig.data.bones}
        if canonical_bones is None:
            canonical_bones = bone_names
        elif bone_names != canonical_bones:
            raise RuntimeError(f"{filename}: bone names do not match base clip {base_id}")

        collection = bpy.data.collections.new(f"Source_{clip_id}")
        scene.collection.children.link(collection)
        for obj in imported:
            for old in list(obj.users_collection):
                old.objects.unlink(obj)
            collection.objects.link(obj)

        action.name = f"A_{clip_id}"
        action.use_fake_user = True
        if clip_id == base_id:
            rig = source_rig
            rig.name = "ActionRig"
            meshes = [obj for obj in imported if obj.type == "MESH"]
            if not meshes:
                raise RuntimeError(f"base clip {base_id} has no renderable character mesh")
            meshes.sort(key=lambda obj: (obj.name != "Beta_Surface", -len(obj.data.vertices), obj.name))
            for index, mesh in enumerate(meshes):
                mesh.name = "ActionCharacter" if index == 0 else f"ActionCharacter_{index}"
                catalog["meshes"].append(mesh.name)
            for image in bpy.data.images:
                if image.source == "FILE" and image.filepath:
                    try:
                        image.pack()
                    except RuntimeError:
                        pass
        else:
            collection.hide_render = True
            collection.hide_viewport = True
        start, end = (int(round(value)) for value in action.frame_range)
        if "phase_markers" in clip_spec and clip_spec.get("phase_frame_range") != [start, end]:
            raise RuntimeError(
                f"{clip_id}: action frame range changed to {start}–{end}; "
                "review and update phase markers in A.catalog.json before rebuilding"
            )
        catalog["clips"][clip_id] = {**clip_spec,
            "action": action.name,
            "source_fbx": filename,
            "frame_start": start,
            "frame_end": end,
            "source_has_mesh": any(obj.type == "MESH" for obj in imported),
            "loop_hint": bool(clip_spec.get("loop_hint", False)),
        }

    rig.animation_data.action = bpy.data.actions[catalog["clips"][base_id]["action"]]
    rig.animation_data.action_slot = rig.animation_data.action.slots[0]
    scene.frame_set(catalog["clips"][base_id]["frame_start"])
    rig.display_type = "WIRE"
    rig.show_in_front = False

    camera_data = bpy.data.cameras.new("ReferenceCamera")
    camera = bpy.data.objects.new("ReferenceCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = (0.0, -4.0, 1.0)
    camera.rotation_euler = (math.pi / 2, 0.0, 0.0)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 2.8

    light_data = bpy.data.lights.new("ReferenceKeyLight", "AREA")
    light = bpy.data.objects.new("ReferenceKeyLight", light_data)
    scene.collection.objects.link(light)
    light.location = (1.0, -2.0, 2.5)
    light_data.energy = 500
    light_data.shape = "DISK"
    light_data.size = 4

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    blend = ASSET_DIR / "A.blend"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
    print("ACTION_LIBRARY", json.dumps(catalog))


if __name__ == "__main__":
    main()

"""Integration tests in a disposable Blender process; optionally render both engines."""
from pathlib import Path
import argparse
import copy
import json
import sys
import traceback

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_demo import build_demo
from clay_common import (OWNER_KEY, ROLE_KEY, curves_for, linear_rgba, merge_config, owned,
                         save_new, scope, write_json)
from create_clay_material import create_palette
from setup_clay_animation import setup_animation
from setup_clay_lighting import setup_lighting
from setup_render import render, setup_render
from validate_clay_scene import check_outputs, compare_shots, validate_scene


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Choose an empty test output directory")
    output.mkdir(parents=True, exist_ok=True)
    report = {"blender": bpy.app.version_string, "python": sys.version.split()[0],
              "checks": {}, "renders": [], "render_requested": args.render}

    def test(name, fn):
        try:
            result = fn()
            report["checks"][name] = {"ok": True, "result": result}
        except Exception as exc:
            report["checks"][name] = {"ok": False, "error": str(exc),
                                      "traceback": traceback.format_exc(limit=5)}

    def require(condition, message):
        if not condition:
            raise AssertionError(message)

    def rejects(fn, exception=Exception):
        try:
            fn()
        except exception:
            return True
        raise AssertionError("Invalid operation was not rejected")

    preserved = {o.name: tuple(v for row in o.matrix_world for v in row) for o in bpy.data.objects}
    source_world = bpy.context.scene.world
    config = merge_config({"render": {"engine": "CYCLES", "device": "CPU", "width": 480,
                                      "height": 270, "samples": 8},
                           "animation": {"hold_frames": 2}})
    scene = bpy.data.scenes.new("Clay Integration A")
    bpy.context.window.scene = scene
    state = {}

    def demo_test():
        state["objects"] = build_demo(scene, config, "test")
        qa = validate_scene(scene, config, "test", state["objects"])
        require(qa["structural_ok"], qa["errors"])
        write_json(output / "scene-quality.json", qa)
        return {"objects": len(state["objects"]), "materials": len(qa["materials"])}
    test("demo_structural_quality", demo_test)

    def counts():
        return {key: len(getattr(bpy.data, key)) for key in
                ("objects", "meshes", "materials", "lights", "cameras", "worlds", "actions", "collections")}

    def idempotence_test():
        before = counts()
        for _ in range(3):
            build_demo(scene, config, "test")
        require(counts() == before, f"Datablock growth: {before} -> {counts()}")
        return counts()
    test("three_reruns_no_datablock_growth", idempotence_test)

    def preservation_test():
        require(all(bpy.data.objects.get(name) and
                    tuple(v for row in bpy.data.objects[name].matrix_world for v in row) == matrix
                    for name, matrix in preserved.items()), "Unrelated source objects changed")
        require(source_world.name in bpy.data.worlds, "Source world removed")
        return list(preserved)
    test("unrelated_data_preserved", preservation_test)

    def color_test():
        require(abs(linear_rgba("#808080")[0] - 0.2158605) < 1e-6, "sRGB conversion incorrect")
        require(linear_rgba([0.2, 0.3, 0.4])[0] == 0.2, "Linear numeric color changed")
        return True
    test("color_space_conversion", color_test)

    def config_test():
        invalid = [[], False, 0, "", {"unknown": 1}, {"render": {"sample": 8}}, {"render": {"samples": 0}},
                   {"scale": 0}, {"palette": {}}, {"palette": {"x": "#GG0000"}},
                   {"material": {"roughness": float("nan")}}, {"camera": {"dof": "yes"}},
                   {"animation": {"hold_frames": 1.5}}, {"render": {"width": True}},
                   {"render": {"frame_start": 10, "frame_end": 5}}]
        for value in invalid:
            rejects(lambda v=value: merge_config(v), ValueError)
        return {"rejected": len(invalid)}
    test("invalid_profiles_rejected", config_test)

    def shader_test():
        palette = create_palette(scene, config, "test")
        for m in palette.values():
            types = {n.type for n in m.node_tree.nodes}
            require({"BSDF_PRINCIPLED", "BUMP", "TEX_NOISE", "VALTORGB", "OUTPUT_MATERIAL"} <= types,
                    "Missing clay shader nodes")
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            require(bsdf.inputs["Base Color"].is_linked and bsdf.inputs["Normal"].is_linked,
                    "Shader inputs disconnected")
        return {"palette": list(palette)}
    test("shader_nodes_and_links", shader_test)

    def timing_test():
        root = state["objects"][0]
        old_action = root.animation_data.action
        setup_animation(root, scene, config, "test")
        require(root.animation_data.action == old_action, "Rerun copied action unnecessarily")
        curves = curves_for(root)
        require(len(curves) == 6, "Unexpected action-slot curve count")
        for fc in curves:
            require(abs(fc.evaluate(1) - fc.evaluate(2)) < 1e-6, "Two-frame hold not respected")
            require(abs(fc.evaluate(1) - fc.evaluate(25)) < 1e-6, "Loop endpoint mismatch")
        z = next(fc for fc in curves if fc.data_path == "location" and fc.array_index == 2)
        require(abs(z.evaluate(3) - z.evaluate(1)) > 1e-4, "Hold freezes all animation")
        return {"curves": len(curves), "poses_per_second": scene.render.fps / 2}
    test("24fps_two_frame_hold_and_loop", timing_test)

    def smooth_test():
        root = state["objects"][0]
        smooth = copy.deepcopy(config)
        smooth["animation"]["hold_frames"] = 1
        setup_animation(root, scene, smooth, "test")
        z = next(fc for fc in curves_for(root) if fc.data_path == "location" and fc.array_index == 2)
        require(abs(z.evaluate(1) - z.evaluate(2)) > 1e-4, "Smooth animation remains stepped")
        setup_animation(root, scene, config, "test")
        return True
    test("smooth_timing_restored", smooth_test)

    def shared_action_test():
        a = bpy.data.objects.new("Authored Motion A", None)
        b = bpy.data.objects.new("Authored Motion B", None)
        scene.collection.objects.link(a)
        scene.collection.objects.link(b)
        a.location.z = 0
        a.keyframe_insert("location", frame=1)
        a.location.z = 1
        a.keyframe_insert("location", frame=25)
        original = a.animation_data.action
        b.animation_data_create()
        b.animation_data.action = original
        if hasattr(a.animation_data, "action_slot"):
            b.animation_data.action_slot = a.animation_data.action_slot
        values = [fc.evaluate(2) for fc in curves_for(b)]
        setup_animation(a, scene, config, "test")
        require(a.animation_data.action != original and b.animation_data.action == original,
                "Shared source action not preserved")
        require(values == [fc.evaluate(2) for fc in curves_for(b)], "Other user's curves changed")
        require(original.use_fake_user, "Source action not retained")
        copied = a.animation_data.action
        setup_animation(a, scene, config, "test")
        require(a.animation_data.action == copied, "Owned copy not idempotent")
        return {"source": original.name, "copy": copied.name}
    test("shared_authored_action_copy", shared_action_test)

    def conflicts_test():
        root = state["objects"][0]
        constraint = root.constraints.new("LIMIT_LOCATION")
        try:
            rejects(lambda: setup_animation(root, scene, config, "test"), RuntimeError)
        finally:
            root.constraints.remove(constraint)
        name = f"Clay::{scope(scene, 'collision')}::material-x"
        m = bpy.data.materials.new(name)
        rejects(lambda: owned(bpy.data.materials, scope(scene, "collision"), "material-x", bpy.data.materials.new), RuntimeError)
        require(m.get(OWNER_KEY) is None, "Unowned material adopted")
        return True
    test("constraints_and_unowned_collisions_rejected", conflicts_test)

    def modifier_failure_test():
        root = state["objects"][0]
        action = root.animation_data.action
        curves = curves_for(root)
        for modifier in list(curves[-1].modifiers):
            if modifier.name in ("SoftClayCycle", "SoftClayHold"):
                curves[-1].modifiers.remove(modifier)
        artist = curves[-1].modifiers.new("CYCLES")
        artist.name = "ArtistCycle"
        before = [[(p.co[:], p.interpolation) for p in fc.keyframe_points] for fc in curves]
        modifiers = [[(m.name, m.type) for m in fc.modifiers] for fc in curves]
        rejects(lambda: setup_animation(root, scene, config, "test"), RuntimeError)
        require(root.animation_data.action == action, "Failed operation replaced action")
        require(before == [[(p.co[:], p.interpolation) for p in fc.keyframe_points] for fc in curves],
                "Failed operation modified keys")
        require(modifiers == [[(m.name, m.type) for m in fc.modifiers] for fc in curves],
                "Failed operation modified timing modifiers")
        curves[-1].modifiers.remove(artist)
        setup_animation(root, scene, config, "test")
        return True
    test("modifier_conflict_preserves_motion", modifier_failure_test)

    def shared_demo_test():
        other = bpy.data.scenes.new("Shared Demo Guard")
        obj = state["objects"][2]
        other.collection.objects.link(obj)
        before = counts()
        original = [tuple(v.co) for v in obj.data.vertices]
        changed = copy.deepcopy(config)
        changed["scale"] = 3
        rejects(lambda: build_demo(scene, changed, "test"), RuntimeError)
        require(counts() == before and original == [tuple(v.co) for v in obj.data.vertices],
                "Failed rebuild changed shared data")
        other.collection.objects.unlink(obj)
        return True
    test("shared_demo_object_preserved", shared_demo_test)

    def negative_qa_test():
        mesh_obj = state["objects"][2]
        before = mesh_obj.scale.copy()
        mesh_obj.scale.x = 0
        bpy.context.view_layer.update()
        qa = validate_scene(scene, config, "test", state["objects"])
        require(not qa["structural_ok"] and any("Zero scale" in e for e in qa["errors"]), "Bad scale passed")
        mesh_obj.scale = before
        root = state["objects"][0]
        fc = next(fc for fc in curves_for(root) if fc.data_path == "location" and fc.array_index == 2)
        endpoint = fc.keyframe_points[-1]
        old = endpoint.co.y
        endpoint.co.y = 0.5
        fc.update()
        root.animation_data.action.update_tag()
        qa = validate_scene(scene, config, "test", state["objects"])
        require(not qa["structural_ok"] and any("Loop endpoint mismatch" in e for e in qa["errors"]), "Bad loop passed")
        # FCurve.update may relocate keyframe storage: reacquire the RNA point.
        fc.keyframe_points[-1].co.y = old
        fc.update()
        root.animation_data.action.update_tag()
        return True
    test("bad_scale_and_loop_fail_quality", negative_qa_test)

    def proportions_test():
        obj = state["objects"][2]
        bpy.context.view_layer.update()
        expected = {obj.name: {"dimensions": list(obj.dimensions), "tolerance": 0.001}}
        qa = validate_scene(scene, config, "test", state["objects"], expectations=expected)
        require(qa["structural_ok"], qa["errors"])
        expected[obj.name]["dimensions"][2] *= 2
        qa = validate_scene(scene, config, "test", state["objects"], expectations=expected)
        require(any("Dimension/proportion" in e for e in qa["errors"]), "Bad dimensions passed")
        return True
    test("project_dimension_manifest", proportions_test)

    def rig_test():
        # Context-sensitive Edit Mode is isolated and only used for the new test rig.
        arm = bpy.data.armatures.new("Test Deform Rig Data")
        rig = bpy.data.objects.new("Test Deform Rig", arm)
        scene.collection.objects.link(rig)
        previous = bpy.context.view_layer.objects.active
        selected = list(bpy.context.selected_objects)
        for obj in selected:
            obj.select_set(False)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode="EDIT")
        try:
            bone = arm.edit_bones.new("deform")
            bone.head, bone.tail = (0, 0, 0), (0, 0, 1)
        finally:
            bpy.ops.object.mode_set(mode="OBJECT")
            rig.select_set(False)
            for obj in selected:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = previous
        source = state["objects"][2]
        obj = source.copy()
        obj.data = source.data.copy()
        obj.name = "Test Deform Mesh"
        # A copied test asset needs a distinct role, not duplicate demo ownership.
        obj[ROLE_KEY] = "test-rig-mesh"
        scene.collection.objects.link(obj)
        group = obj.vertex_groups.new(name="deform")
        indices = [v.index for v in obj.data.vertices]
        group.add(indices, 1, "REPLACE")
        modifier = obj.modifiers.new("Test Skin", "ARMATURE")
        modifier.object = rig
        bpy.context.view_layer.update()
        qa = validate_scene(scene, config, "test", [obj, rig])
        require(qa["structural_ok"], qa["errors"])
        group.remove([indices[0]])
        qa = validate_scene(scene, config, "test", [obj, rig])
        require(any("deform weights" in e for e in qa["errors"]), "Unweighted vertex passed")
        group.add(indices, 1, "REPLACE")
        for f, angle in ((1, 0), (13, 0.25), (25, 0)):
            rig.pose.bones["deform"].rotation_mode = "XYZ"
            rig.pose.bones["deform"].rotation_euler.y = angle
            rig.pose.bones["deform"].keyframe_insert("rotation_euler", frame=f)
        setup_animation(rig, scene, config, "test")
        qa = validate_scene(scene, config, "test", [obj, rig])
        require(qa["structural_ok"], qa["errors"])
        obj.hide_render = True
        return {"vertices": len(indices), "bone_loop": qa["animation"]}
    test("armature_weights_and_pose_loop", rig_test)

    def material_negative_test():
        material = state["objects"][2].data.materials[0]
        bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Roughness"].default_value = 0.7  # Still matte, but drifts from profile.
        qa = validate_scene(scene, config, "test", state["objects"])
        require(any("Actual shader parameter mismatch" in e for e in qa["errors"]), "Shader drift passed")
        bsdf.inputs["Roughness"].default_value = config["material"]["roughness"]
        return True
    test("actual_shader_drift_detected", material_negative_test)

    def separate_project_test():
        other = bpy.data.scenes.new("Independent Clay Project")
        bpy.context.window.scene = other
        changed = merge_config({"scale": 2, "palette": {"red": "#BB8877", "white": "#EEE0CE"},
                               "render": {"engine": "EEVEE", "width": 270, "height": 480, "samples": 8},
                               "camera": {"position": [7.5, -10.5, 6.5], "lens": 45},
                               "animation": {"hold_frames": 1}})
        objects = build_demo(other, changed, "test")
        qa = validate_scene(other, changed, "test", objects)
        require(qa["structural_ok"], qa["errors"])
        first_key = next(o for o in scene.objects if o.get(ROLE_KEY) == "key")
        second_key = next(o for o in other.objects if o.get(ROLE_KEY) == "key")
        require(abs(second_key.data.energy / first_key.data.energy - 4) < 1e-6, "Power scaling not quadratic")
        require(scene.world != other.world and scene.camera != other.camera, "Shared cross-scene rig")
        require(not compare_shots([scene, other])["ok"], "Different shot profiles passed comparison")
        write_json(output / "independent-quality.json", qa)
        state["other"], state["other_config"] = other, changed
        bpy.context.window.scene = scene
        return {"scene": other.name, "portrait": [270, 480], "scale": 2}
    test("independent_scene_palette_scale_and_portrait", separate_project_test)

    def shot_test():
        other = state["other"]
        setup_render(other, config)
        require(compare_shots([scene, other])["ok"], "Matching profiles rejected")
        other.view_settings.exposure = 0.5
        require(not compare_shots([scene, other])["ok"], "Actual exposure drift undetected")
        setup_render(other, state["other_config"])
        return True
    test("shot_profiles_and_actual_exposure", shot_test)

    def fps_test():
        changed = copy.deepcopy(config)
        changed["render"]["fps"] = 12
        setup_render(scene, changed)
        require(scene.render.fps == 12, "12fps not configurable")
        require(scene.frame_end == 24, "Changing FPS unexpectedly retimed keys")
        setup_render(scene, config)
        return True
    test("native_12fps_configuration", fps_test)

    def saves_test():
        path = output / "test-scene.blend"
        save_new(path)
        rejects(lambda: save_new(path), FileExistsError)
        require(path.is_file() and path.stat().st_size > 0, "Blend not saved")
        return {"blend": str(path)}
    test("save_and_overwrite_guard", saves_test)

    def output_negative_test():
        path = output / "broken.png"
        path.write_text("not an image")
        require(not check_outputs([path])[0]["ok"], "Corrupt image passed")
        path.unlink()
        return True
    test("corrupt_image_rejected", output_negative_test)

    if args.render:
        def cycles_test():
            bpy.context.window.scene = scene
            setup_render(scene, config, output / "cycles.png")
            files = render(scene, "still")
            images = check_outputs(files)
            require(all(i["ok"] and i["size"] == [480, 270] for i in images), "Cycles output invalid")
            rejects(lambda: render(scene, "still"), FileExistsError)
            report["renders"].extend(images)
            return images
        test("cycles_cpu_landscape_render", cycles_test)

        def eevee_test():
            other, changed = state["other"], state["other_config"]
            bpy.context.window.scene = other
            setup_render(other, changed, output / "eevee-portrait.png")
            files = render(other, "still")
            images = check_outputs(files)
            require(all(i["ok"] and i["size"] == [270, 480] for i in images), "EEVEE output invalid")
            report["renders"].extend(images)
            bpy.context.window.scene = scene
            return images
        test("eevee_portrait_render", eevee_test)

        def sequence_test():
            small = merge_config({"render": {"engine": "CYCLES", "device": "CPU", "width": 160,
                                              "height": 90, "samples": 4},
                                   "animation": {"hold_frames": 2}})
            setup_render(scene, small, output / "frame-")
            files = render(scene, "animation")
            require(len(files) == 24, "Sequence frame count wrong")
            images = check_outputs(files)
            require(all(i["ok"] and i["size"] == [160, 90] for i in images), "Sequence contains invalid images")
            one = bpy.data.images.load(files[0], check_existing=False)
            two = bpy.data.images.load(files[1], check_existing=False)
            # Render noise can differ per frame even with held geometry.
            require(scene.frame_end == 24 and state["objects"][0].get("soft_clay_hold_frames") == 2,
                    "Sequence hold configuration lost")
            bpy.data.images.remove(one)
            bpy.data.images.remove(two)
            report["renders"].extend(images)
            setup_render(scene, config)
            return {"frame_count": len(files), "prefix": str(output / "frame-")}
        test("24_frame_png_sequence", sequence_test)

        def video_test():
            small = merge_config({"render": {"engine": "CYCLES", "device": "CPU", "width": 160,
                                              "height": 90, "samples": 2, "format": "FFMPEG"},
                                   "animation": {"hold_frames": 2}})
            setup_render(scene, small, output / "clip-")
            files = render(scene, "animation")
            require(len(files) == 1 and files[0].endswith(".mp4"), "Native video not emitted")
            setup_render(scene, config)
            return {"files": files, "note": "Container playback/decoder validation is a separate gate"}
        test("native_h264_video", video_test)

    report["ok"] = all(item["ok"] for item in report["checks"].values())
    write_json(output / "test-report.json", report)
    print(json.dumps(report, sort_keys=True))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

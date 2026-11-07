"""Prepare the P1 review from accepted P0 snapshots and apply a sourced preview finish."""

import argparse
import json
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
from render_feature_review import execute
from stage_guard import file_input


APPEARANCE_URL = ("https://raw.githubusercontent.com/elithril/blender-kiln/"
                  "e9a421467dd95d0de71d45b3d331f8efa4b80f26/site/public/assets/img/ref-Lantern_01.webp")
TEXTURE_SCALE = 20.0
FINISHES = {
    "iron": ((0.078, 0.061, 0.043, 1), (0.30, 0.59), (0.32, 0.86)),
    "rim": ((0.18, 0.127, 0.069, 1), (0.23, 0.49), (0.46, 0.94)),
    "wire": ((0.12, 0.087, 0.047, 1), (0.27, 0.53), (0.43, 0.90)),
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def shader_for(material):
    return next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")


def finish(material, role, maps):
    tree = material.node_tree
    nodes, links = tree.nodes, tree.links
    shader = shader_for(material)
    tone, roughness, metallic = FINISHES[role]
    coord = nodes.new("ShaderNodeTexCoord")
    scale = nodes.new("ShaderNodeVectorMath")
    scale.operation = "SCALE"
    scale.inputs["Scale"].default_value = TEXTURE_SCALE
    links.new(coord.outputs["Object"], scale.inputs[0])
    textures = {}
    for name, details in maps.items():
        texture = nodes.new("ShaderNodeTexImage")
        texture.label = name
        texture.image = bpy.data.images.load(details["path"], check_existing=True)
        texture.image.colorspace_settings.name = "sRGB" if name == "base_color" else "Non-Color"
        texture.projection = "BOX"
        texture.projection_blend = 0.25
        links.new(scale.outputs["Vector"], texture.inputs["Vector"])
        textures[name] = texture.outputs["Color"]

    color = nodes.new("ShaderNodeMixRGB")
    color.inputs[0].default_value = 0.20
    color.inputs[1].default_value = tone
    links.new(textures["base_color"], color.inputs[2])
    links.new(color.outputs["Color"], shader.inputs["Base Color"])
    for name, limits, socket in (("roughness", roughness, "Roughness"), ("metallic", metallic, "Metallic")):
        value = nodes.new("ShaderNodeMapRange")
        value.inputs["To Min"].default_value, value.inputs["To Max"].default_value = limits
        links.new(textures[name], value.inputs["Value"])
        links.new(value.outputs["Result"], shader.inputs[socket])
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.16
    bump.inputs["Distance"].default_value = 0.00025
    links.new(textures["height"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])


def prepare_materials(scene, source, photo):
    collection = scene.collection.children["iron-lantern-p0::model"]
    regions = {}
    for obj in collection.objects:
        for slot in obj.material_slots:
            regions.setdefault(slot.material.name, set()).add(obj["lantern_module"])
    report = []
    for role in FINISHES:
        material = bpy.data.materials[f"iron-lantern-p0::{role}"]
        finish(material, role, source["maps"])
        report.append({"material": material.name, "modules": sorted(regions[material.name]),
                       "source": source, "appearance_reference": photo,
                       "tint_linear": FINISHES[role][0], "roughness_range": FINISHES[role][1],
                       "metallic_range": FINISHES[role][2], "texture_repeat_m": 1 / TEXTURE_SCALE,
                       "wear": "Scanned patch distribution with more exposed metal and lower roughness on rims and wire."})
    glass = bpy.data.materials["iron-lantern-p0::glass"]
    shader = shader_for(glass)
    shader.inputs["Base Color"].default_value = (0.11, 0.17, 0.18, 1)
    shader.inputs["Roughness"].default_value = 0.25
    report.append({"material": glass.name, "modules": sorted(regions[glass.name]), "appearance_reference": photo,
                   "source": "Procedural tinted glass preview on the existing solid globe geometry."})
    return report


def main(p0, out, selected):
    p0, out = p0.resolve(), out.resolve()
    plan_path = HERE / "p1-review.json"
    plan = read(plan_path)
    verification_path = p0 / "verification.json"
    verification = read(verification_path)
    snapshots = {tag: str(p0 / f"{tag}.blend") for tag in ("before", "after")}
    if verification["status"] != "passed" or any(
        file_input(path)["sha256"] != verification["snapshot_sha256"][tag] for tag, path in snapshots.items()
    ):
        raise RuntimeError("P1 requires the accepted P0 snapshots from verification.json")

    frame_path = p0 / "reference-frame.json"
    frame = read(frame_path)
    ppu = frame["pixels_per_unit"]
    x_origin, y_origin = frame["origin_px"]
    features = []
    for item in plan["features"]:
        feature = dict(item)
        left, top, right, bottom = feature.pop("box_px")
        if right-left != bottom-top:
            raise ValueError("The matched orthographic crop must be square")
        feature["reference"] = {"image": str(p0 / "reference-front.png"), "view": "front",
                                "box_px": [left, top, right, bottom]}
        feature["camera"] = {"target": [((left + right) / 2 - x_origin) / ppu, 0,
                                        (y_origin - (top + bottom) / 2) / ppu],
                             "direction": [0, -1, 0], "span": (right-left) / ppu}
        features.append(feature)

    out.mkdir(parents=True, exist_ok=True)
    source = plan["source"]
    for role, entry in source["maps"].items():
        local = file_input(out / "textures" / source["id"] / f"{role}.jpg")
        if local["sha256"] != entry["sha256"]:
            raise RuntimeError(f"P1 material map changed: {role}")
        entry.update(local, url=source["map_url_prefix"] + entry["suffix"] + "_1k.jpg",
                     color_space="sRGB" if role == "base_color" else "Non-Color")
    photo = {**file_input(out / "appearance-reference.webp"), "url": APPEARANCE_URL,
             "asset_url": "https://polyhaven.com/a/Lantern_01", "license": "CC0-1.0",
             "scope": "Supplemental appearance reference. The crop for geometric comparison uses the calibrated orthographic view."}
    config_path = out / "review-config.json"
    config = {"schema_version": 1, "snapshots": snapshots, "ledger": str(p0 / "module-ledger.json"),
              "resolution": 384, "samples": 24, "studio": {"center": frame["target"], "scale": 0.17},
              "features": features, "material_recipe": {"scan": source, "reference": photo}}
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    material_inputs = [__file__, frame_path, verification_path, photo["path"],
                       *(entry["path"] for entry in source["maps"].values())]
    execute(config_path, out, selected=selected, material_inputs=material_inputs,
            setup_materials=lambda scene: prepare_materials(scene, source, photo))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("p0", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--feature", action="append", default=[])
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    main(args.p0, args.out, args.feature)

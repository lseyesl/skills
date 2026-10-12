"""Create owned matte clay materials. Does not assign/replace object slots."""
from pathlib import Path
import json
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clay_common import cli, emit, linear_rgba, owned, parse, scope, socket


def create_material(name, color, config, owner):
    m = owned(bpy.data.materials, owner, "material-" + name, bpy.data.materials.new)
    m.use_nodes = True
    nodes, links = m.node_tree.nodes, m.node_tree.links
    nodes.clear()  # Only our owned procedural tree, never an arbitrary user's tree.
    base = linear_rgba(color)
    p = config["material"]
    m.diffuse_color = base
    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (650, 60)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (350, 60)
    socket(bsdf, "Roughness").default_value = p["roughness"]
    socket(bsdf, "Metallic").default_value = 0.0
    socket(bsdf, "Specular IOR Level", "Specular").default_value = p["specular"]
    socket(bsdf, "IOR").default_value = 1.45
    tex = nodes.new("ShaderNodeTexCoord")
    tex.location = (-800, 0)
    color_noise = nodes.new("ShaderNodeTexNoise")
    color_noise.location = (-560, 160)
    color_noise.label = "Broad subtle color variation"
    socket(color_noise, "Scale").default_value = p["color_scale"] / config["scale"]
    socket(color_noise, "Detail").default_value = 2.0
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-260, 170)
    for element, sign in zip(ramp.color_ramp.elements, (-1, 1)):
        element.color = tuple(min(1, max(0, c * (1 + sign * p["color_variation"])))
                              for c in base[:3]) + (1,)
    micro = nodes.new("ShaderNodeTexNoise")
    micro.location = (-560, -150)
    micro.label = "Micro relief, no geometry displacement"
    socket(micro, "Scale").default_value = p["micro_scale"] / config["scale"]
    socket(micro, "Detail").default_value = 2.0
    bump = nodes.new("ShaderNodeBump")
    bump.location = (50, -100)
    socket(bump, "Strength").default_value = p["bump_strength"]
    socket(bump, "Distance").default_value = p["bump_distance"] * config["scale"]
    for noise in (color_noise, micro):
        links.new(socket(tex, "Object", output=True), socket(noise, "Vector"))
    links.new(socket(color_noise, "Fac", output=True), socket(ramp, "Fac"))
    links.new(socket(ramp, "Color", output=True), socket(bsdf, "Base Color"))
    links.new(socket(micro, "Fac", output=True), socket(bump, "Height"))
    links.new(socket(bump, "Normal", output=True), socket(bsdf, "Normal"))
    links.new(socket(bsdf, "BSDF", output=True), socket(out, "Surface"))
    m["soft_clay_parameters"] = json.dumps({"color": base, **p, "scale": config["scale"]}, sort_keys=True)
    return m


def create_palette(scene, config, owner="soft-clay"):
    owner = scope(scene, owner)
    return {name: create_material(name, color, config, owner)
            for name, color in config["palette"].items()}


def main():
    args, config, scene = parse(cli(__doc__))
    palette = create_palette(scene, config, args.owner)
    emit("materials", materials={k: m.name for k, m in palette.items()})


if __name__ == "__main__":
    main()

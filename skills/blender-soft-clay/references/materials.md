# Clay shader and palette

`scripts/create_clay_material.py` creates the same procedural node topology for each named color. It does not assign slots; the project recipe chooses authorized objects and slots explicitly.

| Parameter | Default | Interpretation |
|---|---:|---|
| roughness | 0.82 | Matte dielectric response; useful range 0.7–0.95 |
| specular | 0.22 | Low, nonzero dielectric highlight (Specular IOR Level / legacy Specular) |
| color_variation | 0.035 | Multiplicative dark/light endpoints around scene-linear base RGB |
| color_scale | 3 | Broad noise frequency per reference unit |
| micro_scale | 110 | Fine bump frequency per reference unit |
| bump_strength | 0.12 | Restrained normal perturbation |
| bump_distance | 0.003 | Relative Blender-unit bump distance, multiplied by scene scale |

Metallic stays zero, IOR is 1.45, and no true displacement or subsurface scattering is required. Large area lights create the soft response. Roughness alone does not remove highlights; source area, specular level and exposure interact.

## Node topology

```text
Texture Coordinate.Object → broad Noise.Fac → ColorRamp → Principled.Base Color
Texture Coordinate.Object → fine Noise.Fac → Bump.Height → Principled.Normal
Principled.BSDF → Material Output.Surface
```

Noise scales are divided by `scale`; bump distance is multiplied by `scale`. This preserves the approximate look when geometry coordinates and light/camera layout are scaled by the same factor. Geometry should be constructed at intended local dimensions with identity object scale when safe. Arbitrary unapplied per-object scaling stretches object-coordinate noise; a style pass must not apply rig transforms to solve that.

Object-space coordinates follow rigid object transforms but can swim across deformed surfaces. For a production skinned character, use a stable UV/rest-position shader or bake the procedural textures. The bundled tool is a rigid-asset and preview baseline, not a guarantee of deformation-stable texturing. Use the [existing UV/baking workflow](../../blender-python-modeling/references/uv-and-texture-baking.md) when needed.

## Colors and assignment

Hex colors are treated as sRGB and converted to scene-linear RGB for node values. Numeric RGB(A) lists are already scene-linear in [0,1]; alpha must be 1. Replacing the `palette` configuration replaces the entire color mapping, making user-defined color names sufficient for any project. Removed colors are not automatically deleted from Blender: they may still be used by existing assets.

```python
palette = create_palette(scene, profile, owner="shot-style")
material = palette[chosen_palette_key]
# Append a new slot or replace a specific authorized slot; do not clear arbitrary slots.
obj.data.materials.append(material)
```

Use one palette and node recipe across shots. Judge shades under the actual view transform and output lighting, not the solid viewport. If coarse noise makes the clay look like stone or bump sparkles during animation, reduce variation/strength/frequency and rerender at final resolution. Bump should enrich the surface without altering silhouette.

## Ownership and compatibility

Owned materials are reused by tag on reruns, their nodes rebuilt deterministically. Editing a tagged material updates all its users intentionally; duplicate it with a different owner for a different look. Tools never adopt a similarly named unowned material. Node sockets are retrieved by runtime identifiers; missing required sockets produce a version-specific error. Shader graphs are compatible with both EEVEE and Cycles on the tested build; procedural export to other engines may require baking.

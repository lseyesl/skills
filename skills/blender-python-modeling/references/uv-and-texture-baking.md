# UV and Texture Baking

UVs are part of the output contract, not a cosmetic final step. Decide the target texture resolution, material boundaries, required UV sets, and whether procedural materials must be baked before final topology changes.

## Choose the projection

| Asset | Preferred starting point |
|---|---|
| Character or organic hero asset | intentional seams plus Angle Based unwrap |
| Hard-surface asset | seams along panel breaks plus Conformal unwrap |
| Fast background prop | Smart UV Project, followed by packing inspection |
| Planar label, screen, or decal | planar or project-from-view mapping |
| Game lighting | a second non-overlapping lightmap UV set |
| Large environment | tiled UVs or UDIM only when the target supports them |

Hide seams on less visible edges, material transitions, sharp corners, or existing construction breaks. Do not add seams to every hard edge automatically: shading splits and UV splits serve different purposes. Finish topology before final packing; topology edits can invalidate island layout and baked maps.

## Multi-view projection check

适用于多个参考视角给同一表面供色，以及已有模型出现重复眉眼、双唇线或接缝残影。烘焙前在部位台账列出容易重复或消失的标记。脸部通常包括左右眉眼、鼻翼和唇线。以下步骤也适用于跨投影接缝的徽记、文字和服装图案。

1. 锁定镜头与姿态，保存正面、过渡角（通常为斜前方）和纯侧面的局部基线。对同一机位比较无纹理灰模、无光照基础色和最终材质。灰模也有双边时检查重复网格、眼片和贴花；基础色出现双线时，单独显示各投影层与遮罩，定位重复来源。仅在动态画面出现时另外检查时间采样。
2. 在各可信视图上标出眼角、鼻梁、嘴角等锚点，核对相机配准、可见性和网格深度。每个高对比标记在最终 UV 上只落一次；可逐个特征选主视图，或将多图先对齐到同一组表面锚点。其余视图补肤色与低频明暗，在无遮挡、无轮廓线的区域羽化。隔开皮肤、头发、耳朵及衣物的取色范围。
3. 同镜头逐个复查数量、位置和清晰度。例如正面每只眼只有一道眼形；斜前方眼角不分叉；侧面近眼与鼻梁的间距、嘴角位置和唇线可读性接近该方向的参考。远眼可被鼻梁遮住。观察发际、面颊和耳前是否染色，旋转检查视角间的过渡。侧面眼位前移或唇线消失时，重开对应项，校正眼窝深度、表面锚点或局部 UV，再烘焙。仅在参考无法约束该部位时调用多视图技能补特写。
4. 按[正式交付证据](fidelity-and-completion.md#final-evidence-file)保存各方向的逐项结论及特写。完整模型的轮廓分数不能替代五官位置和唇线检查。

## Create and identify UV layers

Use the data API for layer ownership and operators only for unwrap/packing:

```python
mesh = obj.data
uv = mesh.uv_layers.get("UVMap") or mesh.uv_layers.new(name="UVMap")
mesh.uv_layers.active = uv
uv.active_render = True
```

Use stable semantic names such as `UVMap`, `Lightmap`, or a target-required name. Never rely on `mesh.uv_layers[0]` when editing an existing file. For export, verify which layer is active for rendering and whether the destination supports multiple sets.

Mark seams through mesh data when possible:

```python
for edge in mesh.edges:
    edge.use_seam = edge.index in seam_edge_indices
mesh.update()
```

When seam selection depends on topology, derive it from explicit rules such as material boundary, marked sharp edge, dihedral angle, or named vertex group. Record the rule; do not preserve a fragile list of indices across topology rebuilds.

## Context-safe unwrap and packing

UV operators require a mesh object in Edit Mode with faces selected. Isolate the operation and restore mode/selection afterwards:

```python
def unwrap_object(obj, method="ANGLE_BASED", margin=0.02):
    if obj.type != "MESH":
        raise TypeError(f"expected MESH, got {obj.type}")

    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    obj.data.uv_layers.get("UVMap") or obj.data.uv_layers.new(name="UVMap")

    bpy.ops.object.mode_set(mode="EDIT")
    try:
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.unwrap(method=method, margin=margin)
        bpy.ops.uv.average_islands_scale()
        bpy.ops.uv.pack_islands(margin=margin)
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")
```

Treat the keywords as runtime API. Inspect `bpy.ops.uv.unwrap.get_rna_type().properties` and `bpy.ops.uv.pack_islands.get_rna_type().properties` before using newer options. Blender 5.x Geometry Nodes UV features such as newer Minimum Stretch or custom pack-region behavior are not part of the Blender 4.x baseline.

For scripted production work, make the margin policy explicit. Pixel padding is approximately `margin_uv * texture_resolution`; mipmapped game textures usually need more padding than a still render. Packing a 1K and 4K target with the same pixel padding requires different normalized margins.

## Texel density and multiple UV sets

Texel density must be compared in evaluated world scale, not raw object coordinates. Apply scale only if the downstream format requires it; otherwise include object scale in the density calculation. For each island, compare UV area with corresponding world-space surface area and normalize islands toward the approved pixels-per-unit target.

- Preserve intentionally higher density for faces carrying labels or close-up detail only when documented.
- Allow mirrored/stacked islands for symmetric reusable detail only when unique baking, lightmaps, or the target engine do not require unique UVs.
- Lightmap UVs must stay inside the 0–1 tile, have no overlaps, and use target-appropriate padding.
- UDIM tiles require explicit tile numbering, saved images, and confirmation that the exporter/consumer supports them. Do not assume GLB preserves an arbitrary UDIM workflow.

## Bake procedural materials

Use baking when the destination cannot reproduce Blender's node tree. Keep the editable procedural material and bake to a separate task-owned material or delivery copy.

1. Confirm final transforms, normals, triangulation policy, UV layer, cage/high-poly source, and low-poly target.
2. Create each target image at the approved resolution and colour space.
3. Add an Image Texture node for that image to every target material and make that node active; it need not be connected while baking.
4. Use Cycles for the bake unless the running Blender build documents another supported path.
5. Select source objects first and the low-poly target last for selected-to-active baking. Validate cage extrusion or ray distance on a small test.
6. Bake one map at a time and save it immediately to an absolute project path.

Colour handling:

- Base Color and Emission are colour data, normally saved as sRGB delivery textures.
- Roughness, Metallic, AO, masks, Height, and Normal are non-colour data.
- Confirm tangent-space normal orientation expected by the consumer; engines may differ on the green/Y channel convention.
- Do not bake lighting into Base Color unless the deliverable explicitly requests it.

`bpy.ops.object.bake` is context-sensitive. Before calling it, set the render engine, bake type, active target object, selected source objects, active UV layer, active image node, and image save path. Read the running operator properties instead of copying Blender 5.x-only parameters.

## UV and bake validation

Before delivery, verify:

- every textured mesh has the expected named UV layers and active render layer;
- all loop UV coordinates are finite;
- islands are in the allowed tile range;
- no unintended overlap, flips, extreme stretching, or microscopic islands exist;
- padding is sufficient at the final texture resolution and mip level;
- baked images exist on disk, have the expected dimensions and colour space, and are linked by the delivery material;
- tangent normals render correctly after triangulation and export;
- a checker texture and final baked material have both been visually inspected.

Do not treat a successful operator return as proof of a usable UV layout. Capture a UV/checker preview and inspect seams, distortion, density, and padding.

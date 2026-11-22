<a id="uv-and-texture-baking"></a>

# UV 接缝与贴图烘焙

在定稿拓扑前，明确交付所需的贴图分辨率、材质边界、UV 集，以及程序化材质是否需要烘焙。

按参考图新建整模时，先完成[白模审查并保存快照](fidelity-and-completion.md#clay-review-before-production-texturing)，再正式绘制贴图、生成图集、投影和烘焙。可以提前规划 UV 或做局部材质试验。

<a id="choose-the-projection"></a>

## 投影方式

| 资产 | 建议方法 |
|---|---|
| 角色或重点展示的有机模型 | 手动指定接缝，使用基于角度的展开（Angle Based） |
| 硬表面模型 | 沿面板交界设置接缝，使用保角展开（Conformal） |
| 快速制作的背景道具 | 使用 Smart UV Project，检查 UV 岛的排列 |
| 平面标签、屏幕或贴花 | 使用平面投影或从视图投影 |
| 游戏光照 | 使用第二套互不重叠的光照贴图 UV |
| 大型环境 | 目标平台支持时才使用平铺 UV 或 UDIM |

将接缝放在不显眼的边、材质交界、锐角或已有结构分界处。硬边用于控制着色，UV 接缝用于展开，无需将每条硬边都设为接缝。拓扑定稿后再排列 UV 岛；后续改动拓扑可能使布局和已烘焙的贴图失效。

<a id="multi-view-projection-check"></a>

## 多视图投影检查

适用于多个参考视角给同一表面供色，以及已有模型出现重复眉眼、双唇线或接缝残影。烘焙前在部位台账列出容易重复或消失的标记。脸部通常包括左右眉眼、鼻翼和唇线。以下步骤也适用于跨投影接缝的徽记、文字和服装图案。

1. 锁定镜头与姿态，保存正面、过渡角（通常为斜前方）和纯侧面的局部基线。对同一机位比较无纹理灰模、无光照基础色和最终材质。灰模也有双边时检查重复网格、眼片和贴花；基础色出现双线时，单独显示各投影层与遮罩，定位重复来源。仅在动态画面出现时另外检查时间采样。
2. 在各可信视图上标出眼角、鼻梁、嘴角等锚点，核对相机配准、可见性和网格深度。每个高对比标记在最终 UV 上只落一次；可逐个特征选主视图，或将多图先对齐到同一组表面锚点。其余视图补肤色与低频明暗，在无遮挡、无轮廓线的区域羽化。隔开皮肤、头发、耳朵及衣物的取色范围。
3. 同镜头逐个复查数量、位置和清晰度。例如正面每只眼只有一道眼形；斜前方眼角不分叉；侧面近眼与鼻梁的间距、嘴角位置和唇线可读性接近该方向的参考。远眼可被鼻梁遮住。观察发际、面颊和耳前是否染色，旋转检查视角间的过渡。侧面眼位前移或唇线消失时，重开对应项，校正眼窝深度、表面锚点或局部 UV，再烘焙。仅在参考无法约束该部位时调用多视图技能补特写。
4. 按[正式交付证据](fidelity-and-completion.md#final-evidence-file)保存各方向的逐项结论及特写。完整模型的轮廓分数不能替代五官位置和唇线检查。

<a id="create-and-identify-uv-layers"></a>

## 创建和识别 UV 层

通过数据 API 管理网格上的 UV 层，仅在展开和排列时使用操作器。

```python
mesh = obj.data
uv = mesh.uv_layers.get("UVMap") or mesh.uv_layers.new(name="UVMap")
mesh.uv_layers.active = uv
uv.active_render = True
```

使用语义明确且稳定的名称，如 `UVMap`、`Lightmap` 或目标平台指定的名称。编辑现有文件时不要假定 `mesh.uv_layers[0]` 就是所需层。导出前核实当前渲染使用的 UV 层，以及目标平台是否支持多套 UV。

尽量直接通过网格数据标记接缝。

```python
for edge in mesh.edges:
    edge.use_seam = edge.index in seam_edge_indices
mesh.update()
```

如果接缝取决于拓扑，应按材质边界、已标记的锐边、二面角或命名顶点组等明确规则选择，并记录规则。重建拓扑后应重新计算，避免沿用旧边索引。

<a id="context-safe-unwrap-and-packing"></a>

## 展开与排列

UV 操作器需要活动对象为网格，处于编辑模式且已选中面。隔离本次操作，结束后恢复原模式和选择状态。

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

参数以运行版本为准。使用新选项前，检查 `bpy.ops.uv.unwrap.get_rna_type().properties` 和 `bpy.ops.uv.pack_islands.get_rna_type().properties`。Blender 5.x 几何节点中较新的最小拉伸和自定义排列区域功能不属于 4.x 基线。

在制作脚本中明确留边规则。像素间距约为 `margin_uv * texture_resolution`。使用多级渐远纹理的游戏通常需要比静帧渲染更宽的留边。要在 1K 和 4K 贴图中保留同样的像素间距，需要不同的归一化边距。

<a id="texel-density-and-multiple-uv-sets"></a>

## 纹素密度与多套 UV

比较纹素密度时，使用求值后的世界空间尺寸。仅在下游格式要求时应用缩放，否则应将对象缩放计入密度。逐岛比较 UV 面积与对应表面的世界空间面积，调整至已确认的单位长度像素数。

- 仅在有明确记录时，为标签或近景细节保留更高的纹素密度。
- 对于可复用的对称细节，只有在烘焙、光照贴图和目标引擎都允许 UV 共用时，才能镜像或叠放 UV 岛。
- 光照贴图的 UV 必须位于 0–1 范围内，互不重叠，并按目标平台要求留边。
- 明确 UDIM 各图块的编号，保存对应图像，确认导出器及下游软件都支持。逐项验证 GLB 能保留哪些 UDIM 数据。

<a id="bake-procedural-materials"></a>

## 程序化材质烘焙

当目标软件无法复现 Blender 的节点树时，保留可编辑的程序化材质，并将结果烘焙到本任务独立使用的材质或交付副本。

1. 确认最终变换、法线、三角化规则、UV 层、投射笼、高模源及低模目标。
2. 按已确认的分辨率和色彩空间创建各目标图像。
3. 在每个目标材质中为该图像添加 Image Texture 节点，并设为活动节点。烘焙时可以不接入节点树。
4. 使用 Cycles 烘焙，除非当前 Blender 构建的文档明确支持其他方式。
5. 从选中对象烘焙到活动对象时，先选源对象，最后选低模目标。先做小样，检查投射笼外扩量或射线距离。
6. 每次烘焙一张贴图，完成后立即保存至项目中的绝对路径。

色彩空间

- 基础色（Base Color）与自发光（Emission）属于颜色数据，通常以 sRGB 贴图交付。
- 粗糙度、金属度、环境光遮蔽（AO）、遮罩、高度和法线属于非颜色数据。
- 确认下游软件对切线空间法线的约定。不同引擎对绿色（Y）通道的方向可能有不同要求。
- 仅在交付要求明确指定时，才把光照烘焙进基础色。

`bpy.ops.object.bake` 依赖当前上下文。调用前设置渲染引擎、烘焙类型、活动目标对象、选中的源对象、活动 UV 层、活动图像节点和保存路径。读取实际运行版本的操作器属性，避免引用 5.x 独有参数。

<a id="uv-and-bake-validation"></a>

## UV 与烘焙验收

交付前逐项核验。

- 每个带贴图的网格都有约定名称的 UV 层，并正确指定渲染使用的活动层。
- 所有面角的 UV 坐标均为有限数值。
- 所有 UV 岛都位于允许的图块范围内。
- 没有意外的重叠、翻转、严重拉伸或过小的 UV 岛。
- 最终分辨率及目标渐远纹理级别下仍有足够的留边。
- 烘焙图像已写入磁盘，尺寸及色彩空间正确，交付材质已链接这些图像。
- 三角化和导出后，切线空间法线渲染正确。
- 已目视检查棋盘格测试贴图和最终烘焙材质。

保存 UV 布局和棋盘格预览，检查接缝、变形、密度和留边。操作器成功返回只是执行结果，布局仍须目视核验。

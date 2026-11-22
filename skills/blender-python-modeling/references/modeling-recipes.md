<a id="modeling-recipes"></a>

# 建模方法

<a id="choose-the-representation-first"></a>

## 先选几何表示方式

| 形状或要求 | 首选的建造方式 |
|---|---|
| 机械的、建筑的、尺寸驱动的 | primitives/BMesh 加上实时修改器 |
| 管道、电缆、轨道、轮廓、路径 | 带有倒角的曲线或曲线转网格 |
| 重复的部分 | 链接的网格、集合实例、数组或几何节点 |
| 地形和图案化表面 | 几何节点或位移网格 |
| Soft/organic 轮廓 | 低分辨率基础网格加上细分；仅在需要时进行雕刻 |
| 密封打印部件 | 显式流形网格，经过清理的布尔值，测量得到的厚度 |

在详细设定之前，先确定主要比例。当需要对主要部分进行不同的旋转、材质、导出行为或替换时，要分别命名这些部分。使用一种真实世界的单位制，并将用户可编辑的参数放在脚本的顶部。

对于具有硬化表面的例子，请参见 [铁灯领航员](../examples/iron-lantern-p0/README.md)。它将对准的基准点映射到旋转的轮廓和扫描的管体，然后针对相同的视图、孔径射线和网格座进行局部校正。

<a id="low-resolution-construction-and-refinement"></a>

## 低分辨率建模与精修

使用 [遮挡工作流程](procedures/modeling/blockout-and-refinement.md) 和 [接受度](acceptance/blockout.md) 进行复杂的创建。每个模块都会选择一种方法，而不是对整个复杂资产一次性选择一种方法：

| 表示 | 良好的开端 | 下一个决定 |
|---|---|---|
| 基本组件 | 探索主要部件和独立的机械零件 | 在需要的地方分别进行细化或重构连续曲面 |
| 盒模型建模 | 一个连续的壳体可以通过一个小笼子和挤出工艺来控制。 | 添加有意义的边缘 flow/support，然后评估细分 |
| 表面贴片 | 具有重要边界控制的面板和外壳 | 建立连续性、厚度和可控的细分 |
| Curves/sweeps | 管道、导轨、轮廓 | 选择path/profile采样与下游表示 |
| 低分辨率sculpt/base网格 | 有机体积探索 | 优化形态；如果 delivery/deformation 需要的话，进行拓扑重组 |
| 现有合适的资源 | 本地编辑或兼容的可复用几何结构 | 保留一个快照，并直接检查受影响的范围 |

在比例和结构确定之前，不要进行密集的细分。编辑模式下的“细分”、“细分曲面”和“多分辨率”有不同的用途。相反，一组相交的原始几何图形并不自动构成最终的皮肤或附件。要确保连续性，要仔细区分各个部分以及移动的连接点。连续的角色可以将多个语义模块映射到一个网格上；不要仅仅为了满足记录而拆分皮肤。

<a id="direct-mesh-construction"></a>

## 直接构建网格

使用 `mesh.from_pydata`进行已知拓扑结构和BMesh的程序化编辑：

```python
mesh = bpy.data.meshes.new("MESH_task_panel")
mesh.from_pydata(
    [(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)],
    [],
    [(0, 1, 2, 3)],
)
mesh.validate(verbose=True)
mesh.update()
obj = bpy.data.objects.new("GEO_task_panel", mesh)
collection.objects.link(obj)
```

```python
mesh = bpy.data.meshes.new("MESH_task_body")
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=2.0)
bmesh.ops.bevel(
    bm,
    geom=list(bm.edges),
    offset=0.08,
    segments=3,
    affect="EDGES",
)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(mesh)
bm.free()
mesh.validate(verbose=True)
mesh.update()
```

请使用 `bpy_api_lookup` 检查不确定的 BMesh 参数，或者使用 Blender 的 Python API 查看运行版本；这些参数不是 RNA 操作符，可能需要直接查阅文档。

<a id="curves-for-linear-forms"></a>

## 用曲线制作线状结构

使用曲线来定义电线、管道、把手、修剪线、道路和轮廓扫描。在仅使用网格的操作或导出需要转换之前，保持这些元素的程序化特性。

```python
curve = bpy.data.curves.new("CURVE_task_rail", "CURVE")
curve.dimensions = "3D"
curve.resolution_u = 12
curve.bevel_depth = 0.015
curve.bevel_resolution = 3
curve.use_fill_caps = True
spline = curve.splines.new("BEZIER")
points = [(-1, 0, 0), (0, 0.4, 0.5), (1, 0, 0)]
spline.bezier_points.add(len(points) - 1)
for point, co in zip(spline.bezier_points, points, strict=True):
    point.co = co
    point.handle_left_type = "AUTO"
    point.handle_right_type = "AUTO"
```

使用 `AUTO`来创建平滑的有机路径，`ALIGNED`来实现可控的切线，而`VECTOR`则用于处理角部。从输出目标中选择倒角分辨率，而不是最大化它。

<a id="hard-surface-modifier-stacks"></a>

## 硬表面修改器堆栈

常见的非破坏性排序为：

1. 用于对称性的镜像；
2. 用于重复的数组；
3. 布尔逻辑用于主要的cuts/unions；
4. 在表面需要厚度时，使其更加坚固；
5. 为制造边缘进行倒角处理；
6. 仅在形式需要连续平滑时进行细分。

顺序也是设计的一部分。通常，布尔运算在前、倒角运算在后的方式会比倒角运算在前、布尔运算在后的方式产生更干净的加工边缘。镜像运算在前、布尔运算在后的方式会使切割器影响到两侧；当存在不对称时，反转这种顺序可能会很有用。

```python
mirror = obj.modifiers.new("MOD_task_mirror", "MIRROR")
mirror.use_axis = (True, False, False)
mirror.use_clip = True

boolean = obj.modifiers.new("MOD_task_cut", "BOOLEAN")
boolean.operation = "DIFFERENCE"
boolean.solver = "EXACT"
boolean.object = cutter

bevel = obj.modifiers.new("MOD_task_bevel", "BEVEL")
bevel.width = 0.01
bevel.segments = 3

for polygon in obj.data.polygons:
    polygon.use_smooth = True
```

将切割器保存在一个任务拥有的集合中，并仅在视觉验证之后才显示它们。不要仅仅为了整理视口而应用修改器。仅在下一个操作或输出需要评估几何形状时才应用或烘焙修改器。

<a id="organic-and-sculptable-forms"></a>

## 有机形体与可雕刻模型

对于脚本生成的有机对象：

1. 创建一個低分辨率、分布均勻的基礎模型；
2. 建立对称性和轮廓；
3. 在保守的预览级别下添加细分或多分辨率功能；
4. 请保持眼睛、牙齿、配饰和刚性部件分开；
5. 仅在程序化基础和缩放被接受后，才手动进行雕塑操作。

避免将详细的雕塑笔触作为默认设置进行脚本化处理：这些笔触与上下文相关，难以复制，且难以验证。对于程序化有机变异，应使用可控位移或结合显式随机种子的 Geometry Nodes 来实现。

<a id="topology-and-cleanup"></a>

## 拓扑与清理

对于已评估的 BMesh：

```python
bm = bmesh.new()
bm.from_mesh(mesh)
bm.normal_update()
loose_verts = [v for v in bm.verts if not v.link_edges]
boundary_or_nonmanifold = [e for e in bm.edges if not e.is_manifold]
degenerate_faces = [f for f in bm.faces if f.calc_area() <= 1e-12]
bm.free()
```

根据目标要求，对非流形边缘进行解释：这些边缘在封闭的打印实体中是不合法的，但在开放的板材上却是预期存在的。距离合并和孔洞填充是修正操作，并非自动默认设置；它们可能会破坏故意设计的接缝和开口。

使用直接网格编辑或BMesh操作来进行清理。如果无法避免使用某个操作符，则优先选择API查找后的`bpy.ops.mesh.merge_by_distance`方式；不要依赖跨版本的旧`remove_doubles`别名。

<a id="repetition-and-instances"></a>

## 重复结构与实例

- 在许多对象共享一个可编辑的网格时，使用链接的副本。
- 使用数组来实现属于一个对象的线性或径向重复。
- 使用集合实例来处理重复装配。
- 使用 Geometry Nodes 实现基于属性的散射效果以及大规模计数处理。

在后续的网格操作或导出需要真实的几何形状之前，保持实例的未实现状态。记录预期的实例数量和评估后的三角形数量，以防止重新运行时场景复杂度无意识地增加。

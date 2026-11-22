<a id="materials-and-node-recipes"></a>

# 材质与节点

<a id="stable-node-access"></a>

## 稳定访问节点

通过 `node.type` 查找节点，而不是翻译显示名称。通过运行时标识符查找套接字，当期望的套接字不存在时，使用可用的标识符进行查找会失败：

```python
def socket_by_identifier(node, *identifiers):
    wanted = set(identifiers)
    for socket in node.inputs:
        if socket.identifier in wanted:
            return socket
    available = [socket.identifier for socket in node.inputs]
    raise KeyError(f"missing {sorted(wanted)}; available={available}")

material.use_nodes = True
principled = next(
    node for node in material.node_tree.nodes
    if node.type == "BSDF_PRINCIPLED"
)
socket_by_identifier(principled, "Base Color").default_value = (0.2, 0.4, 0.8, 1)
socket_by_identifier(principled, "Metallic").default_value = 0.0
socket_by_identifier(principled, "Roughness").default_value = 0.35
```

已验证的 Blender 4.5 基础标识符包括 `Base Color`、 `Metallic`、 `Roughness`、 `IOR`、 `Alpha`、 `Normal`、 `Transmission Weight`、 `Emission Color` 和 `Emission Strength`。请不要假设其他版本使用相同的确切标识符；请先调用 `describe_node_type`。

<a id="material-choices"></a>

## 材质选择

| 表面 | 基本原则的出发点 |
|---|---|
| 哑光塑料 | 金属感 0，粗糙度 0.35–0.6 |
| 绘制的金属 | 金属效果为 0，粗糙度设为 0.2–0.5；仅在去除金属效果的地方进行曝光处理。 |
| 裸机 | 金属感 1，粗糙度 0.08–0.45 |
| 透明玻璃 | 传输权重 1，IOR约为 1.45，粗糙度较低 |
| 磨砂玻璃 | 传输权重 1，IOR约为 1.45，粗糙度 0.2–0.6 |
| 橡胶 | 金属感 0，粗糙度 0.65–0.9，颜色较深但非零的基础颜色 |
| 发射符号 | 发射颜色加上物理上合理的发射强度；在渲染中进行验证 |

将这些视为起始范围，而非通用常数。缩放、光照、曝光度和渲染引擎会改变外观。

<a id="texture-based-pbr"></a>

## 使用贴图的 PBR 材质

使用此地图路线：

- 基础颜色：sRGB图像 → 基于Principled的基础颜色；
- Roughness/Metallic：非彩色图像 → 对应的标量输入；
- 普通：非彩色图像 → 普通贴图节点 → 原理性普通贴图；
- 高度：对于非彩色图像，可以使用“Bump”效果来产生廉价的外观效果，或者在使用Cycles时，可以使用“Displacement”效果来实现真正的位移效果。

使用 `check_existing=True` 加载每张图片一次。如果可能的话，在分配之前确认已安装的色彩空间标识符。如果采用非标准的 OCIO 配置，请务必进行确认。

对于 GLB 格式，建议使用与 Principled 兼容的节点和传统的图像映射。复杂的程序化树结构在忠实传递之前，通常需要先进行烘焙处理。

<a id="procedural-materials"></a>

## 程序化材质

对于以参考为导向的色彩搭配，在投影之前定义语义区域：面部cap/blaze/brows、耳朵正面、轮廓、背面、喉部、胸部、腹部、爪子top/sole以及附属物根部、末端，或者相应的部件。使用源视图来约束这些区域；明确解决可见性和法线方向的歧义。仅通过表面法线来混合正面、侧面图像遮罩，可以绘制出耳朵的背面或中断底面的色彩场。早期检查背面、顶部、底部，不仅仅是美观的相机视角。

用于变形角色，固定程序化坐标、区域将属性分配给其余网格，或者使用UV来使颜色和纹理与皮肤相吻合。在目标需要的情况下，将不支持的过程区域烘焙为UV纹理；保留可编辑的源数据。将遮罩投影与几何恢复分开，不要将源光照作为材料设计的替代品。在实际材料变形与关节测试之间进行对比。有关无效性和外部纹理依赖性的比较，请参见[staged-execution.md](staged-execution.md).

常见的与 Blender 4.x 兼容的模板：

- 噪声纹理 → 颜色渐变 → 石头的基底颜色、颜料变化、云朵的颜色；
- Noise/Voronoi → 凹凸 → 法线，用于精细的曲面浮雕效果；
- 波浪纹理加上噪声失真，用于模拟木质纹理；
- Geometry/Object坐标 → 映射 → 可控制的纹理比例；
- 用于角度依赖的涂层效果的层权重或菲涅尔效应。

在连接不熟悉的节点之前，请使用 `describe_node_type`。节点布局可能会随着节点属性（如数据类型）的变化而变化，而像 Mix 这样的共享节点则具有与版本相关的布局。

<a id="geometry-nodes-baseline"></a>

## 几何节点兼容基线

经过测试的基础版本 Blender 4.5 包含 Mesh Cube、设置位置、连接几何、曲线线、曲线到网格以及点上的实例等功能。使用 Blender 4.x 界面 API 创建组插座：

```python
group = bpy.data.node_groups.new("GN_task_scatter", "GeometryNodeTree")
group.interface.new_socket(
    name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry"
)
group.interface.new_socket(
    name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry"
)
group_in = group.nodes.new("NodeGroupInput")
group_out = group.nodes.new("NodeGroupOutput")
geometry_out = next(s for s in group_in.outputs if s.type == "GEOMETRY")
geometry_in = next(s for s in group_out.inputs if s.type == "GEOMETRY")
group.links.new(geometry_out, geometry_in)
modifier = obj.modifiers.new("GN_task", "NODES")
modifier.node_group = group
```

有用的模式：

- 分散：在面上分布点 → 在点上实例化；随机化旋转和缩放，后期实现。
- 变形：Position/Normal加上噪声 → 向量计算 → 设置位置偏移。
- Cable/profile：曲线线或输入曲线 → 使用曲线圆轮廓将曲线转换为网格。
- 条件分支：分离几何结构 → 处理分支 → 合并几何结构。

请不要从标签中推断节点标识符。Blender 5.x 中，每个元素、包、骨骼信息、射线检测、新的 UV/volume-grid 节点以及字体套接字都不属于 4.x 版本的基础功能。

<a id="node-tree-quality"></a>

## 节点树质量

- 为节点赋予稳定的名称和可阅读的标签，但应通过存储的引用或`bl_idname`/`type`方式来获取它们。
- 将节点从左到右排列，并保持一致的间距，以便人类能够查看图表。
- 在复杂的图表中，使用帧节点来划分逻辑部分。
- 仅展示用户需要调整的参数；实现细节请保留内部。
- 在重新运行时，复用任务拥有的材料和节点组，而不是创建 `.001`副本。
- 验证节点的拓扑结构和rendered/viewport结果。

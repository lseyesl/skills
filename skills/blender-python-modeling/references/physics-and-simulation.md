<a id="physics-and-simulation"></a>

# 物理与模拟

将模拟视为一个独立的、显式缓存的阶段。在烘焙之前，记录 Blender 版本、FPS、帧范围、单位比例、求解器设置、种子、缓存路径以及依赖几何图形。视图窗口播放并不能实现可复制的渲染效果。

<a id="shared-simulation-rules"></a>

## 模拟通则

- 在真实世界的规模下进行操作，因为求解器是预期这样的场景的；无论是微小的还是巨大的场景，都可能变得不稳定。
- 仅在对源对象安全且被求解器要求时应用缩放。保留一个可编辑的副本。
- 从简单的碰撞几何形状开始，初始时没有交点。
- 在共享或含义模糊的位置之外，使用稳定的对象名称和任务拥有的缓存目录。
- 在暴露的位置设置确定性种子。某些求解器或硬件路径仍可能存在变化；请报告这一限制。
- 在较低resolution/substeps处预览，然后在最终烘焙前冻结设置。
- 未经明确许可，切勿在任务所有权范围之外覆盖或释放现有缓存。

<a id="rigid-bodies"></a>

## 刚体

在常见的 Blender 应用程序编程接口中，刚体的创建是由操作符驱动的，因此需要明确选择并激活对象：

```python
bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.rigidbody.object_add()
obj.rigid_body.type = "ACTIVE"
obj.rigid_body.collision_shape = "CONVEX_HULL"
obj.rigid_body.mass = 1.0
```

在可能的情况下使用 primitive/convex碰撞形状；`MESH`模型较为昂贵，且对于移动凹体来说可能不稳定。需要验证质量比、边缘、子步骤、求解器迭代次数、禁用功能、约束条件以及高速隧穿功能。确认Rigid Body World集合中仅包含预期的参与者。

<a id="cloth-and-soft-bodies"></a>

## 布料与软体

布料质量取决于网格的规模和拓扑结构。在可能的情况下使用均匀的四边形；将模拟和渲染分开处理，并通过明确的顶点组来定义固定点。验证弯曲、自碰撞、碰撞厚度、摩擦以及极端姿态的处理方式。

软体需要明确的goal/spring其意图和拓扑结构适合变形处理。对于这两种系统，在确定最终缓存之前，先测试短帧范围。初始交叉点通常会导致爆炸性的结果；在提高求解器质量之前，先对几何结构进行诊断。

<a id="fluids-smoke-and-fire"></a>

## 流体、烟雾与火焰

Mantaflow需要一个包含流动和效应器的领域，在整个模拟期间保持不变。需要记录领域类型、分辨率、自适应设置、时间尺度、缓存类型、缓存目录、流动行为、效应器厚度以及诸如mesh/noise/particles.这样的辅助数据。

- 在行为测试中使用低分辨率，而不是作为最终表面质量的证据。
- 请保持缓存目录在每个 task/version/settings 哈希值下都是唯一的。
- 按照运行中的 Blender API 要求的顺序，为依赖项进行“烘焙”。
- 请验证整个动画的域边界；移动的源点可能会离开域。
- 在适用的情况下，将液体网格、气体噪声和 spray/foam/bubble 缓存视为独立的输出。

流体操作符和缓存模式对版本敏感。在正在运行的 Blender 中检查 RNA 和 modifier/domain 属性；在没有一次性测试的情况下，不要将 Blender 5.x 的烘焙调用复制到 4.x 的管道中。

<a id="force-fields-and-particles"></a>

## 力场与粒子

确认字段类型、衰减、强度、噪声、受影响的系统和收集可见性。传统的粒子系统和 Geometry Nodes 模拟在数据和导出行为上有所不同，请慎重选择。不要承诺程序化粒子或模拟区域能够持续存在。GLB/FBX—仅在需要时，对交付副本进行烧录或转换。

<a id="baking-and-invalidation"></a>

## 烘焙与缓存失效

在烘焙之前，请哈希或记录可能导致缓存失效的设置和上游输入：拓扑、变换、帧范围、FPS、求解器质量、碰撞对象、顶点组以及源动画。尽可能将这些元数据与缓存一起存储。

烘焙之后：

- 样本起始、中间、结束以及具有挑战性的接触帧；
- 验证缓存文件在重新打开后仍然存在且可读取。`.blend`;
- 确保在烘焙后没有任何依赖关系发生变化；
- 渲染代表性帧，因为视区和最终subdivision/materials可能会暴露出交叉点；
- 仅当用户需要时，才生成转换文件或网格序列以供导出。

在出现反复的不稳定现象后停止，并报告最小的故障frame/settings，而不是默默升级解决方案或覆盖缓存。

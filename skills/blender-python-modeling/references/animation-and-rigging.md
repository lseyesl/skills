<a id="animation-and-rigging-recipes"></a>

# 动画与骨骼绑定

<a id="direct-keyframes"></a>

制作或修复动画时，可按[节奏与帧间距](../../animation-principles/references/motion-review.md#timing)及[运动弧线](../../animation-principles/references/motion-review.md#paths)定位异常帧，再检查对应控制器、关键帧与 F-Curve。

有接触约束和柔性附属件的镜头可按[关键姿势与逐帧推进](../../animation-principles/references/motion-review.md#pose-workflow)先排主体动作，再处理自由部件。蒙皮或缩放导致轮廓跳变时，按[跨帧体积检查](../../animation-principles/references/motion-review.md#volume)核对相邻姿势。

运镜或切镜影响动作辨读时，按[空间层次与转场](../../animation-principles/references/shot-review.md#space)对照固定机位与交付镜头。

## 直接插入关键帧

对于对象变换和标量属性，直接插入关键帧比使用用户界面操作更为稳定：

```python
obj.location = (0.0, 0.0, 0.0)
obj.keyframe_insert(data_path="location", frame=1)
obj.location = (2.0, 0.0, 0.0)
obj.keyframe_insert(data_path="location", frame=48)
```

在动画化旋转之前，明确设置旋转模式。当需要对艺术家面向的通道进行无约束的3D运动，以及进行可预测的单一轴编辑时，使用四元数旋转。

关键帧材质输入、形状键值、光能量、相机镜头、约束影响以及所属数据块上的自定义属性。验证起始帧、中间帧、结束帧、接触帧和循环边界帧。

<a id="interpolation-and-motion-design"></a>

## 插值与运动设计

- 贝兹曲线：自然加速且可编辑的缓动效果；
- 线性：恒定速率的机械运动；
- 常量：stepped/blocking动画；
- Cycles修饰符：重复运动而不复制关键帧。

Blender的分层Action API在4.x和5.x版本后期发生了变化。简单说明。`keyframe_insert`已在 Blender 4.5.12 上验证；适用于直接F-Curve/action-layer请操作并检查正在运行的 Action 模式，而不是复制 5.x 版本的示例。

<a id="constraints-before-baked-keyframes"></a>

## 先用约束，再烘焙关键帧

对于应保持可编辑性的关系，使用约束：

- 复制 Location/Rotation/Transforms以用于以下内容；
- 用于相机和注视对象的跟踪或阻尼跟踪；
- 适用于可切换父级关系的子节点；
- 限制 Location/Rotation/Scale 机械边界；
- 肢体链的IK功能；
- 遵循路径进行运动。

直接创建约束：

```python
constraint = camera.constraints.new("TRACK_TO")
constraint.target = target
constraint.track_axis = "TRACK_NEGATIVE_Z"
constraint.up_axis = "UP_Y"
```

在不确定时，通过 `bpy_api_lookup` 确认枚举标识符。在链接已经相互影响的对象之前，检查依赖循环。

<a id="drivers"></a>

## 驱动器

该软件适用于确定性的关系，而非任意的脚本编写：

```python
fcurve = driven.driver_add("scale", 2)
driver = fcurve.driver
driver.type = "SCRIPTED"
variable = driver.variables.new()
variable.name = "control_x"
variable.type = "TRANSFORMS"
variable.targets[0].id = controller
variable.targets[0].transform_type = "LOC_X"
variable.targets[0].transform_space = "WORLD_SPACE"
driver.expression = "max(0.1, 1.0 + control_x)"
```

保持表达式的简洁性，使用驱动变量，而不是通过`bpy`来连接表达式。为控件赋予明确的名称，并说明其取值范围。

<a id="armature-construction"></a>

## 创建骨架

“Armature”编辑骨骼需要“编辑模式”，因此将这一与上下文相关的阶段分离出来：

1. 通过 `bpy.data` 创建骨架数据和对象；
2. 将其激活并选中；
3. 进入编辑模式并选择create/connect骨骼；
4. 返回到对象模式，采用 `finally` 风格的清理路径；
5. 在姿势模式下添加姿势约束，或者直接作用于`pose.bones`上；
6. 在权重绘制之前，先验证姿态、骨骼滚动、父链以及变形情况。

不要在未检查骨骼修饰符、形状键、顶点组以及动画的情况下，对装有骨骼的网格应用对象变换或破坏性修饰符。通过命名和骨骼集合将变形骨骼与control/mechanism骨骼分开。

<a id="ik-and-mechanical-rigs"></a>

## 反向动力学与机械绑定

对于肢体IK链，需要配置IK目标、极点目标、链长、极点角度以及影响参数。测试直线、弯曲以及极端姿势的翻转情况。对于机械结构，优先使用明确的约束和局部轴；任意的欧拉关键帧会导致对齐误差的累积。

<a id="baking-and-export"></a>

## 烘焙与导出

仅在对齐边界处或当simulation/constraint评估必须明确指定时，才进行烘焙。保留可编辑的源action/rig.。对于GLB/FBX，需验证帧范围、采样率、根运动、object/bone轴、NLA包含情况，以及是否必须保持修改器或形状键未应用状态。

关于变形权重、影响范围、形状键、剪辑所有权、根运动以及角色特定的导出检查，请阅读 [character-delivery.md](character-delivery.md) 部分。

物理和模拟缓存对上下文和版本非常敏感。将其视为具有明确缓存目录和帧范围的独立阶段；在烘焙之前验证运行中的API，切勿隐式覆盖现有的缓存。

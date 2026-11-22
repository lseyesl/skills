<a id="clay-animation-and-timing"></a>

# 黏土动画与节奏

<a id="playback-rate-versus-pose-rate"></a>

## 播放帧率与姿势更新频率

| 交付 | 播放配置 | 运动处理 |
|---|---|---|
| 平滑处理 24帧每秒 | `fps=24`, `fps_base=1` | `hold_frames=1`、贝塞尔曲线还是线性 |
| 12poses/sec以 24 帧每秒的频率 | `fps=24`, `fps_base=1` | `hold_frames=2`，关闭运动模糊 |
| 原生 12帧每秒 | `fps=12`, `fps_base=1` | Retimed keys/range 保留秒数，然后 `hold_frames=1` |

更改场景的FPS会改变现有按键的持续时间。为了保留按键相对于帧原点的时间，请使用`new_frame = origin + (old_frame-origin) * new_fps/old_fps`，包括Bezier手柄。在重新计时后检查联系人，并仅在明确的采样边界处进行四舍五入。辅助工具不会自动重新计时按键或更改播放FPS。

<a id="keyframe-and-hold-helper"></a>

## 关键帧与姿势停留辅助工具

使用 `keyframe_insert` 创建关键帧，遵循 [一般动画工作流程](../../../../blender-python-modeling/references/animation-and-rigging.md) 的步骤。 `setup_clay_animation.py` 接受明确的对象名称和已激活的 Action。它：

1. 拒绝linked/override对象、场景间共享的对象、NLA轨迹、驱动程序和对象、姿态约束条件；
2. 通过假用户复制一个 non-owned/shared操作，并保留源数据；
3. 读取该对象在分层动作中分配的位置的曲线，或传统的F曲线；
4. 设置所需的插值功能和自动夹紧贝兹控制点；
5. 仅替换了名为`SoftClayCycle` / `SoftClayHold`的修改器；
6. 添加了重复循环 and/or，使采样与 `scene.frame_start` 保持一致。

采样保留了可编辑的基础关键点；保持操作会重复计算每个间隔的评估姿态。恒定插值会一直保持到下一个关键点，这是另一个艺术性选择。保持操作不会使模拟、其他动作、形状关键帧数据块进行量化。shader/light动画或未选中的父对象。提供并审查项目工作流程中所有相关的动画数据块。该辅助工具直接支持对象和不受约束的姿势骨骼曲线。shape-key/material数据需要专门的时序处理。

现有的未命名艺术作品Cycles/Stepped修改器会导致显性的冲突错误。Blender要求先使用Cycles，因此循环设置会拒绝在编辑之前使用任何其他艺术性修改器，而不是重新排序它们。在循环功能禁用的情况下，其他艺术性修改器仍然存在，需要进行评估检查。该工具会更改分配通道的所有通道，因此如果只有部分通道需要保留，请使用专用的“动作”选项，而不是混合的生产控制“动作”。

<a id="rigging-and-topology"></a>

## 绑定与拓扑

使用 [字符传输](../../../../blender-python-modeling/references/character-delivery.md) 进行其余的变换，使用 deform/control 进行骨骼分离，使用标准化权重和根运动。对于玩具或机械形状，建议使用 parent/bone 进行固定，而对于可弯曲的肢体，则使用皮肤化技术。将关节放置在功能性的枢轴点上，保留边缘循环，并避免 bevel/decimation 破坏关节运动。在最终着色之前，检查最大弯曲度和相反的姿态。

对于受限的生产设备，使用项目验证过的烘焙工作流程，将计算出的姿势烘焙到**新的**动作中，并采用预期的采样率。保留原始的Action、设备以及约束条件；使用渲染副本进行无约束的播放。时间辅助工具并不旨在禁用约束条件或重新编写NLA/driver关系。

<a id="loop-contract"></a>

## 循环要求

定义周期`P`明确指定。用于输出帧`start…start+P−1`，在重复端点处键入`start+P`超出输出范围。需匹配翻译、方向，并修改几何形状，进行审核。velocity/acceleration在接缝处。欧拉值应避免意外的±2π不连续性；四元数通道需要符号一致性，并且需要评估姿态。

对于保留的循环，`P`必须能被`hold_frames`整除。不要将第一帧和相同的终点作为可见帧导出，因为这会导致暂停。验证器会比较在起始点和结束点+1处计算得到的transforms/meshvertices/bone矩阵，并检查每条曲线的保留情况；它不会证明接缝速度或连贯接触运动的匹配。

<a id="contact-and-continuity-review"></a>

## 接触与连贯性审查

检查每一个接触过渡，大多数compressed/extended在设定姿势和接缝时，要标记出支撑脚或接触面；检查滑动、穿透、浮动部件、肢体翻转以及附件碰撞情况。在简单的刚性工作中，为避免意外的网格变形，可以动画处理一个空的父对象。使用变形测试，而不是假设低多边形网格可以容忍任何姿势。

渲染包含 first/last/seam-neighbor帧的接触图，然后在实际播放时以完整的 FPS 进行播放。保持缩放、材质、光照强度和摄像机的稳定，除非这些参数的改变是故意的。该演示测试了一个 bob/tilt循环，而不是行走骨架或碰撞求解器。 `continuous-action`是一个可选的独立 library/reference工作流程，而不是这里的依赖项。

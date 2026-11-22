<a id="soft-clay-style"></a>

# 柔和低多边形黏土风格

生成可编辑、可复制的场景，并附上经过视觉审核的渲染证据。这是一个基于一般 Blender 建模的艺术指导层，并非角色生成器或物理模拟器。

所有 `scripts/...` 路径都以共享的 `blender-styles/` 目录为根。风格示例与历史结果保存在本风格目录中。应用配置前先阅读[共享工作流程](../../references/workflow-and-review.md)。

<a id="workflow"></a>

## 工作流程

1. 检查项目和当前场景。解决资源缩放、所属目标的问题。静态、动画交付、宽高比、渲染引擎、播放帧率以及姿态节奏。保留无关数据和来源。`.blend`文件。对于实时的MCP工作，请使用[blender-python-modeling](../../../blender-python-modeling/SKILL.md)用于检查、执行save/export相关规范、其结构设计和参考分析程序仍然具有权威性。
2. 编写项目本地化的 Python 脚本和 JSON 样式配置文件。仅加载下方所需的引用内容。使用 [examples/preview.json](examples/preview.json) 或 [examples/portrait.json](examples/portrait.json) 作为 `scripts/clay_common.py::DEFAULTS` 的部分替代方案。在多个镜头中保持一个相同的 palette/material/color-management 配置文件。除非有特别要求，否则不要将示例角色或场景布局复制到生产项目中。
3. 构建经济实惠、圆润的轮廓和模块化资产。保留骨骼拓扑结构和未应用的变形堆栈。选择光滑的有机表面和平坦的宽平面面；相对于每个部件，保持倒角较小。在添加材质之前，检查表面的方向、厚度、连接和轮廓。柔和度并不允许删除参考纹理、凹槽、杯状或压痕；在完整渲染之前，根据[本地功能审核](../../../blender-python-modeling/references/local-feature-review.md)标准检查一个经过评估的局部样本。
4. 从项目配方中的绝对 `scripts/` 目录导入捆绑的工具。调用 `create_palette`、 `setup_lighting`、 `setup_render`，对于明确的动画目标，则调用 `setup_animation`。材料生成不会替代现有的材料槽位。照明会替换活动的世界，并且默认情况下会替换相机参考，同时保留之前的datablocks；使用 `with_camera=False` 来保留镜头相机。现有的灯光仍然处于活动状态，需要进行审查。
5. 评估起始帧、第contact/extreme帧、中间帧、最后帧以及循环边界帧。将播放帧率配置与姿势保持分开。对于24帧的循环，将第1帧和第25帧设置为相同的姿势，并渲染第1至24帧。在24帧每秒的速度下，进行两帧的保持操作，可以获得12个姿势updates/second，而不会降低播放速度。对于受约束的骨架、NLA和驱动程序，需要在时间辅助工具之前进行明确的评估和处理。
6. 运行 `validate_scene` / `validate_clay_scene.py`。使用所选引擎渲染代表性图像；检查哑光效果、微浮雕、轮廓、构图、阴影、变形和接触效果。自动检查并不能确保比例符合设计要求、运动无碰撞，或拍摄效果的一致性。这些视觉指标需要明确标注。
7. 保存为派生输出路径，在适当的情况下渲染可重启的图像序列，并提供脚本、配置文件、`.blend`、渲染结果、质量保证报告、Blender版本及限制信息。在批量运行中使用`--python-exit-code 1`，以便Python失败时能够直接反馈到shell界面。仅仅因为结构性的质量保证通过，就声称视觉场景已经完成是不合适的。

<a id="load-references-progressively"></a>

## 按需查阅参考

| 工作 | 阅读 |
|---|---|
| 网格预算、轮廓、倒角、模块化或可变形资源 | [建模](references/modeling.md) |
| 调色板、过程性着色器、噪声比例、材质分配 | [材料](references/materials.md) |
| 场景比例、大灯光效、接触阴影、camera/DOF | [照明](references/lighting.md) |
| 关键帧、绑定、定格动画、12/24fps、循环接缝 | [动画](references/animation.md) |
| Renderer/device/OCIO兼容性，sequences/video/batch | [渲染](references/rendering.md) |
| 可执行性检查、手动门控和多次拍摄的接受标准 | [质量检查](references/quality-check.md) |
| 最少的命令和适用于现有项目 | [使用](references/usage.md) |
| 已执行的证据与未经验证的界限 | [测试结果](references/test-results.md) |

<a id="resource-ownership-and-scope"></a>

## 资源归属与范围

- 工具会为生成的数据块添加`soft_clay_owner = <owner>::<scene.name>`和`soft_clay_role`标签。在重新运行时，保持所有者和场景名称的稳定性。通过标签来查找资源；拒绝未指定所有者的名称冲突以及linked/override编辑。独立场景会获得独立的rigs/materials.。
- 切勿在造型过程中清除用户的场景、重新划分绑定角色的网格、更换所有材质槽、应用骨骼变换，或强制使用 GPU 后端。仅通过演示即可重新生成所拥有的测试网格。
- 该动画辅助工具复制non-owned/shared动作，保留源数据，并仅对对象指定的槽进行操作。它不进行重新目标定位、自动调整骨骼或解决接触问题。重新运行仅替换其命名的时序修饰符。
- CLI设置脚本会改变当前进程，但不会自动保存。使用项目配方或 `setup_render.py --save` 来持久保存所有阶段。避免为依赖的设置阶段创建未保存的 Blender 进程。
- `continuous-action`仅在其动作库工作流程被请求时提供运动参考；该技能不依赖于`A.blend`或图像生成。`concept-multiview-sheet`提供的是推断出的设计视图，而非实际测量的几何信息。

<a id="minimal-smoke-test"></a>

## 最小运行测试

从仓库根目录开始，将 `blender` 替换为主机的可执行文件：

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python skills/blender-styles/scripts/build_demo.py -- \
  --config skills/blender-styles/styles/soft-clay/examples/preview.json \
  --output .tmp/clay-smoke --render still
```

这将创建一个新的抽象测试场景、一个已保存的`.blend`、一个预览，以及`quality.json`。它会保留原始的启动场景。默认的工具没有项目路径；输出位置来自调用者。

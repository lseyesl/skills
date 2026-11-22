<a id="executed-tests-and-known-limits"></a>

# 已执行的测试与已知局限

这是历史性的软黏土基准，最初是在统一的`blender-styles`目录迁移之前执行的。以下的复制命令使用当前路径；日期、结果和工件位置保留了其原始来源。与迁移相关的检查在[迁移验证](../../../references/migration-validation.md)中有单独的记录。

<a id="baseline-and-reproduction"></a>

## 基线与复现

执行于 **2026-10-12**, macOS 平台, **Blender 4.5.12 LTS** (版本 `84afd5f785f7`), 附带了 Python 3.11.11。无需更改任何第三方 Python 依赖项或 GPU 设置。所提供的软件包使用 CPU 进行渲染, 并采用安装的 EEVEE 图形后端。

```bash
blender --background --factory-startup -t 2 --python-exit-code 1 \
  --python skills/blender-styles/scripts/test_soft_clay.py -- \
  --output .tmp/clay-tests --render
```

使用空输出目录。如果主机沙箱阻止了 Blender 的图形初始化，请执行主机正常的审批流程；不要更改全局 GPU 设置来绕过此问题。此主机在 Metal 启动崩溃后需要在沙箱外进行审批，之后才能运行 Python。

<a id="results"></a>

## 结果

**25/25集成检查通过。**可复现的机器摘要为[evals/test-summary.json](../evals/test-summary.json). 完整的本地报告和生成的伪影已保存在仓库中被忽略`.tmp/blender-soft-clay/verified/`目录；生成的`.blend`/images/video并非按照要求打包为技能资源。

| 验证 | 证据 |
|---|---|
| 一般场景 | 多部分抽象模型，封闭ground/block/cone/pebble5种程序化黏土颜色，3个区域灯光，摄像机bob/tilt循环 |
| 重复执行 | 3次重放，对象、网格、材质、相机、灯光、世界、动作和收藏的计数完全相同 |
| 保留 | 启动 objects/world 保留；未指定所有权的名称冲突被拒绝；在重建前，共享的演示对象被拒绝。 |
| 着色器 | 所需的着色器 nodes/links，sRGB转换，实际 roughness/specular 轮廓漂移检测 |
| 时机 | 24帧每秒，采用两帧保持（12个姿势 updates/sec），六个物体曲线，平滑的时序恢复，匹配循环终点 |
| 原始动画 | 共享源操作已保留，独立副本已创建，副本被重新使用；艺术性时间冲突在编辑前失败 |
| 绑定 | 新的单骨测试平台，42个标准化加权顶点，未加权顶点的负例，姿态循环端点 |
| 几何质量检查 | 零级和循环不匹配被拒绝；项目维度的预期pass/fail如预期般 |
| 独立项目 | 分离场景，2倍缩放，自定义双色调色板，肖像相机，二次方灯光强度缩放，独立世界环境、相机 |
| 拍摄一致性 | 匹配配置文件成功；但配置文件与实际曝光值存在偏差 |
| 无效的配置 | 15malformed/unknown/out-of-range/type-invalid驳回的覆盖 |
| Cycles | CPU 布局 PNG，480×270，8个样本，解码后的有限像素 |
| EEVEE | 独立的肖像PNG格式，尺寸为270×480，包含8个样本，解码后的像素数量有限。 |
| 图像序列 | 24解码后的PNG帧，尺寸为160×90，包含4个样本，帧数范围为1至24。 |
| 视频 | 原生 H.264/MPEG-4，160×90，24帧每秒，24帧，1.000秒；通过ffprobe元数据及完整的ffmpeg解码 |
| 输出保护 | 现有的 `.blend`/仍被拒绝覆盖；损坏的图像也被拒绝 |

独立的材质、照明（`--keep-camera`）、动画（`--objects`）、渲染设置以及质量检查命令行工具也在保存的场景上执行了。在开发过程中，还进行了背景演示的创建；集成套件运行相同的构建功能，并验证最终默认值。

<a id="visual-review"></a>

## 视觉审查

检查了最终的 Cycles 文件，以及 EEVEE 肖像和覆盖第 1、7、13、19、23 和 24 帧的接触图。预览显示颜色柔和，高光部分较为宽泛，形状圆润，轮廓清晰。bob/tilt循环。所有前景边界都适合最终的相机位置。这个抽象循环故意将整个模型抬高；它并没有展示行走脚的锁定机制。

EEVEE的低采样肖像在接触细节上较弱，且距离较远。地面、后台靠近顶部的边缘部分；这是测试预览，而非最终的小模型拍摄。最终拍摄的布局、背景、阴影细节以及景深都需要根据项目进行进一步的优化。Sequence/video这些结果都是经过刻意设计得非常小、样本验证程度较低的；它们都不被视作生产级分辨率。完整解码和pose/endpoint检查通过；正式编辑仍需要实时播放和联系审核。

<a id="known-limits"></a>

## 已知局限

- 仅执行了此 Blender 版本。其他4.x/5.x这些构建具有运行时保护机制，但需要自己进行维护。suite/render审核。GPU Cycles和自定义OCIO并非测试目标。
- 着色器坐标属于对象空间。变形角色可能需要UV/rest-position纹理或烘焙以避免出现“游泳”现象。程序性材质可能需要进行烘焙以用于外部引擎导出。
- 这是一个 style/tool 层，不是自动调整结构、重新定位、运动库打包、物理黏土或碰撞模拟。生产限制、NLA 和驱动因素要求在时间设置之前进行评估。
- 循环相等性和标准化权重是结构上的检查，并不能证明良好的变形、接触或无缝速度。该检查器仅进行这些检查。`visual_approved=false`故意的。
- 镜头对比用于验证存储的样式参数和实际效果color-management/FPS; 它并不比较所有实际的情况shader/light编辑或渲染的感知相似性。
- EXR、GPU配置、受限的骨架、复杂的模拟以及大型制作流程都得到了记录。capabilities/workflows但是它们并不属于这个渲染基准的一部分。

<a id="existing-skill-boundaries"></a>

## 与现有技能的分工

`blender-python-modeling`提供了通用建模、参考分析、装备、导出以及实时MCP规范。这种风格使用黏土palette/shader、可缩放的工作室装备、时间调整适配器、渲染预设，以及专注于质量控制的工具，这些工具现在都存放在统一的`blender-styles/scripts/`目录中。这些工具不导入来自其他技能的Python代码，因此统一的可执行工具目录保持独立。文档链接提供了更深入的工作流程指导。

`continuous-action` 仍然对它基于`A.blend` keyframe/image-reference 工作流程 `concept-multiview-sheet` 的 2D 设计视图负责。 也不是一种运行时间依赖；这些技能中的任何资产都不会被复制到此视图 。

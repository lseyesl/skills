<a id="executable-and-visual-acceptance"></a>

# 脚本验证与视觉验收

使用 `scripts/validate_clay_scene.py`进行结构检查和 JSON 验证。除了临时帧的评估（在退出时恢复）和临时加载的图像（在移除时删除）之外，它是只读的。提供与设置相同的 JSON 配置文件。默认情况下，它会检查已拥有的对象；对于明确的现有资产，请使用 `--objects`。

所请求的场景必须处于活动状态，因为评估几何图形时会使用其依赖关系图。在项目配置中，请在调用 `validate_scene` 之前设置正确的场景；如果场景不匹配，系统会拒绝评估，而不是使用其他场景的图进行评估。

```bash
blender --background /absolute/output/demo.blend --python-exit-code 1 \
  --python skills/blender-styles/scripts/validate_clay_scene.py -- \
  --config /absolute/project/style.json --frames 1 7 13 19 24 25 \
  --images '/absolute/output/frame-*.png' --report /absolute/output/quality.json
```

<a id="automated-gates"></a>

## 自动检查

| 区域 | 可执行检查 | 进一步接受 |
|---|---|---|
| 几何结构 | 有限变换、非零比例、base/evaluated面预算、degenerate/loose几何结构；可选的流形和项目维度要求 | 比较轮廓与部件比例，与已批准的设计在多个视图下进行对比 |
| 材料 | 分配的材料槽位，单个原则性roughness/metallic限制，存储参数协议，实际情况roughness/specular以及所需的链接 | 实际渲染的调色板、高光、纹理比例以及时间稳定性 |
| 照明 | 主动式区域灯光，shadows/size诊断，环境存在性 | 柔和阴影方向，可识别接触，无blown-out/floating形态 |
| 相机 | 活动链接摄像机，在帧和片段范围内采样并评估边界框 | 设计framing/DOF和空间shadows/motion |
| 绑定 | 存在骨架目标，变形组权重present/normalized | 静止姿势，极端弯曲，关节体积，控制和变形行为 |
| 动画 | 有限评估数据，循环终点（transforms/vertices/bones），保持采样和周期的可除性 | 完整播放、接触过渡、穿透、接缝速度和肢体身份 |
| 拍摄 | `--shots`与存储的palette/material/light配置文件以及实际的OCIO/exposure/gamma/FPS进行了比较 | 渲染出的颜色、轮廓比例、光线方向以及编辑的连续性 |
| 产出 | 现有的可解码图像、有限的像素、轮廓尺寸的一致性 | 预期帧数 count/order，视频 decoder/playback |

默认情况下，`require_manifold`是关闭的，因为可渲染的开放表面可能是有意为之。对于需要防水几何形状的封闭资源，可以启用该功能。面预算指的是**面**，而不是三角形，并且不包括需要单独进行资源级检查的生成的实例。即使一个高复杂度的网格的基础网格较为稀疏，该网格仍然会被视为失败。

背景网格如果故意位于摄像机之外，可以被标记为 `soft_clay_background=True`；这样可以绕过裁剪检查，但无法进行 拓扑、材质 验证。边界框的裁剪是保守的，可能会报告故意裁剪的前景区域的裁剪情况：将这种特定于拍摄的异常情况记录在审查中，而不是将其他对象隐藏起来进行质量评估。

在强制使用真实比例时，传递`--expectations /absolute/project/asset-dimensions.json`：如`{"actual object name": {"dimensions": [1.0, 0.8, 1.5], "tolerance": 0.01}}`这样的映射。尺寸和绝对容差以Blender单位表示，并在当前帧进行计算。同时保留ratio/design在项目清单中的证据。通用shader/rig无法推断出哪些比例是正确的。对于基于参考驱动的项目，可以重用现有的[模块：账本与诚信工作流程](../../../../blender-python-modeling/references/fidelity-and-completion.md)。

<a id="manual-review-record"></a>

## 人工审查记录

分别记录每个可见的特征：例如，叶片上表面的倾斜度、实体的厚度、附着的叶柄、连续的中脉、分支的叶脉；花瓣的凹陷、肿胀的边缘以及指状凹陷。在实际的柔和照明下评估修改结果。仅显示宽阔中心凹陷的作物无法提供具有可识别次级叶脉的参考。结构、局部起伏的幅度以及完整的图像外观是独立的证据。遵循[local-feature-review.md](../../../../blender-python-modeling/references/local-feature-review.md)。

存储带有输出帧名称的评论笔记，以及 pass/fail：

1. 几何形状：经过批准的剪影、部件比例、圆润的边缘以及可控的棱角。
2. 材质：无光泽的响应，连贯的色调，没有类似石头的斑点或闪烁的凸起。
3. 光线：易于阅读的接触阴影，可控的高光效果，以及稳定的照明效果。
4. 动画:接触和极姿势,全速回放，相邻的接合框，无意外deformation/intersections.
5. 多镜头编辑：稳定的资源比例、调色板、曝光度以及有意为之相机、灯光差异。

`structural_ok`表示自动检查已通过。`visual_approved`仍然为假：agent/user必须分别检查图像、播放和记录证据。仅通过端点相等性并不能保证流程的流畅性。仅通过权重归一化也不能保证设备的性能良好。通用检查器无法实现碰撞求解、推断目标轮廓，也无法从少量样本中验证所有帧的合规性。

保留失败的报告，并修复顽固的问题配方。使用 [测试结果](test-results.md) 提供测试结果和已知限制，并提供实际的 Blender 版本和渲染器证据，而不是推测的兼容性声明。

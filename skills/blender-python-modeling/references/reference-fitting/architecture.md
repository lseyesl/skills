<a id="reference-fitting-audit-and-design"></a>

# 参考拟合的审查与设计

阶段0已在Blender 4.5.12 LTS上经过审核。优化规格：用户自行提供`blender_clay_skill_optimization.md`v1.0：该版本为现有技能增加了一个可执行的流程，同时保留了所有现有的脚本接口。

| 现有模块 | 已经提供 | 决策 |
|---|---|---|
| `analyze_reference_images.py` | Alpha/background前景比例、剪影比例、轮廓、确定性调色板 | 复用前景提取和IoU算法；添加语义注释层，而不是使用另一个前景检测器。 |
| `validate_module_ledger.py` | 存在与声称阶段的记账 | 保留；图像指标是额外的证据，不得覆盖账本标签 |
| `blender-styles/scripts/clay_common.py` | 严格的共享配置、所有权、sRGB转换 | 复用颜色、着色器配置和插槽辅助工具；将角色配置分开保存 |
| `create_clay_material.py`, `setup_render.py` | 现有的 palette/shader 和 引擎、颜色 管理设置 | 从可选的手工制作中复用surface/validation适配器；不要更改旧的默认设置 |
| `validate_clay_scene.py`, `test_soft_clay.py` | 基础scene/output质量保证，现有集成缺陷 | 保留并配合新的拟合测试运行 |
| 原版女孩`rebuild/`食谱 | 导入的参考工作区，头部表面投影，连续的肢体，三种可互换的表情 | 保留原始文件；将构建概念概括为独立的配置驱动构建器。新的示例包括参考的“笑脸”示例；旧的三种表达式工作流程仍然可用。 |
| 原始 `compare_reference.py` | 相同摄像头的叠加和完整轮廓调试 IoU | 保留；将其用于优化的角色替换为组件遮罩、地标、Lab值和边界误差 |

新的数据流：

```text
character.json + 明确的信任 masks/polygons + 源 RGBA
   - > 配置。 validate +reference_masks
   -> Blender 工作线程：在创建几何图形之前先打包参考工作区
   -> 组件构建器 -> 每材料三波段黏土
   ->修复了相机、渲染 -> 美丽 / 轮廓 / 标签 / 反照率 / 黏土
   -> 一种全局相似性对齐（或没有）
   可见组件IoU + 边界 + 实际网格地标 + 描述性Lab
   ->缺陷->有界单组件参数候选值
   ->重新打开上次已接受的场景 ->重建受影响的依赖项集
   -> 与哈希无关的内容 geometry/transforms/materials -> 结构保护
   ->评估->保留候选方案或回退到不可更改的已接受快照
```

模块边界：

- `scripts/reference_fit/config.py`：与 Blender 无关的验证、规范哈希、change/dependency检测。
- `geometry.py`：可测试的单调截面和可变半径路径采样。
- `blender_builder.py`：稳定的 owner/component/object ID；头部、limbs/hands、dress/straps、鞋子、定向发型、投影式面部贴图。本地更新仅会移除被拥有的受影响对象。在本地形状更改过程中，材料树会被重用。
- `blender_validation.py`：实际的图像填充处理，修复了渲染环境，在`finally`中恢复了临时通道材质，进行了topology/depth/connection检查，并进行了一次性双骨弯曲测试。
- `evaluation.py`：共享前景复用，明确的语义注释，一个记录的全局变换，masks/overlays/heatmaps/metrics.
- `refiner.py`：与证据相关的缺陷、有界坐标搜索、lock/dependency保护、不可更改的快照以及拒绝原因。
- `worker.py`：独立的 Blender 执行；`fit_character.py`：主机编排、超时处理、保留日志以及命令行界面。
- `blender-styles/scripts/handmade_surface.py`：可选的、按地区确定的低频变形，局部性的中等凹陷和中等着色浮雕效果，同时限制高频的凸起；使用已建立的着色器接口。

角色尺寸、特定来源的遮罩、轮廓点、材质值、头发流动引导线和候选边界都存在于`examples/clay-girl-fit/`中，绝不在通用算法中体现。几何单位以角色高度为单位进行标准化；绝对物理尺寸是未知的。侧视图是由不可靠的人工智能生成的证据，而非经过校准的摄影结果。

冻结的原始基线：运行`baseline --source <original.blend>`进入一个新的目录。源混合文件被读取，仅在一次性过程中进行标记，并且不会保存。新环境应用相同的设置。相机、灯光、颜色管理基线和新模型。在运行报告中保留其配置、Blender版本、渲染记录以及源文件哈希值。在不同环境下的基线渲染必须与原始历史数据分开标注。

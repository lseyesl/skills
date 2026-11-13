# 基础形体、方法选择与逐步细化

适用：新建复杂模型、较大形体调整，或需要确认已有资产是否适合继续细化。局部修复可复用已有形体，只检查受影响范围。前置参考标定仍按主 Skill 执行；无视觉参考的原创任务不强制生成多视图。

## 先选结构，再选工具

从用途、参考与交付拆解主要体积、独立部件、连接、开口、厚度、对称与运动关系。把每个模块的方法与理由写入 [建模计划](../../../assets/modeling-plan-template.json)，在任务分析记录中保存其路径。module id 可对应既有台账 ID，不要求一个模块对应一个 Blender object。

| 方法 | 适用条件 | 基础形体之后 |
|---|---|---|
| primitives | 整体设计尚需探索，多体积/装配关系明确 | 校验比例和连接，再分别细化、重建表面或雕刻 |
| box | 连续表面适合少量顶点、挤出和边环控制 | 编辑低模控制网格，再以细分曲面观察求值结果 |
| surface | 面板、外壳、局部曲面需要直接控制边界 | 处理厚度、支撑线、连接和必要细分 |
| curve | 管线、栏杆、线性轮廓与扫掠 | 调整截面、路径与采样；输出需要时才转换 |
| sculpt | 需要自由形体/有机体积探索 | 先主次形体，后局部细节；动画目标再决定是否重拓扑 |
| reuse | 现有基础网格/资产足够合适 | 保存源快照，直接检查相关范围；不为走流程重建 |

从 Cube 开始可以是合法低模搭建，不等于先加高细分。Subdivision Surface、编辑模式 Subdivide、Multires 和雕刻不是同一操作。细分增加采样/平滑，不自动生成正确解剖、机械结构或关节拓扑。没有统一细分等级或面数门槛。

## 分阶段执行

1. **计划**：选择方法、对象绑定、理由与依赖；明确连续/分离/装配关系。人物皮肤接头、独立衣服与机械部件不能统一融合或统一保持相交体。
2. **blockout**：仅建立能验证主要比例、轮廓、截面、厚度、负空间和连接的低成本表示。基础体越多不意味着越完整。
3. **review**：按 [基础形体验收](../../acceptance/blockout.md) 检查，保存实际测量与必要视图，并填写 [review 模板](../../../assets/blockout-review-template.json)。构建代码不能预填检查通过。
4. **refine**：通过新鲜的作用域回执后，细化派生副本，保留粗模或等价冻结控制状态。根据用途选择细分/雕刻/布尔/曲线等路线，不要求所有模型经过同一操作。
5. **后续验收**：可变形模型检查拓扑和姿势；实时/打印/静态按交付要求检查，细节和材质不掩盖基础形体错误。原有模块台账和 final 完成门槛仍然有效。

方法选择或关键形体失败时回到相应模块，不全场景推倒重来。review 可以由实际检查结果的 Agent 或人工记录，不自动增加用户批准步骤；重要设计歧义才按已有规则向用户确认。

## 脚本与证据

正式入口为 [blender_task_template.py](../../../assets/blender_task_template.py)，默认构建/细化函数未实现会报错，不会生成 Cube 冒充结果。示例 [blockout_cube_example.py](../../../assets/examples/blockout_cube_example.py) 只演示参考标定后的粗模，不能设置为 final。

复用 [blockout_gate.py](../../../scripts/blockout_gate.py) 和 [stage_guard](../../../scripts/stage_guard.py)。blockout/review/refine 是不同调用；通过命令行 `--stage` 或运行时设置切换，不通过编辑同一配方文件切换，否则配方哈希改变会使回执失效。脚本默认不保存/导出，项目需实现明确的快照和输出。

每个作用域使用独立回执；depends_on 表示会影响当前检查的其他模块。变化后只重查选中模块及明确依赖。默认状态读取实际粗模求值网格、变换和帧；项目还需声明参考、外部缓存、连接控制、姿态和其他影响检查的输入。复杂上下文不可能仅靠一个网格哈希自动发现。

典型调用：在相同的项目 .blend 与计划下执行 `blender project.blend --python scripts/blender/build_asset.py -- --stage blockout`，检查后 `--stage review`，再 `--stage refine`。无头技术测试允许此调用；正常制作仍遵循主 Skill 的工具约定。

来源：[Blender Subdivision Surface](https://docs.blender.org/manual/en/4.5/modeling/modifiers/generate/subdivision_surface.html)、[Blender Studio 基础体身体](https://studio.blender.org/training/stylized-character-workflow/5d7f7cf055ccaf1a4a78102d/)、[基础网格复用](https://studio.blender.org/training/realistic-human-research/use-of-base-meshes/)。新流程保持 experimental，技术测试不认证艺术品质。

生成检查草稿可调用 `make_review_draft(plan, scope, state_provider, dependencies)`；该函数只填写当前 inspection_signature 和 unknown 检查，不宣称检查通过。保留草稿对应状态，实际检查后再填写结果。旧文件的 signature 不匹配时必须重新检查，不得直接改 signature 复用旧通过结论。

修改正式模板中的构建/细化函数时同时移除对应的 placeholder 标记。多个语义模块允许绑定同一个连续网格；默认状态会保守检查整个共享对象，局部清理不能删除其他模块仍使用的对象。

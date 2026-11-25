---
name: blender-python-modeling
description: "通过可复现的 Python（`bpy`）脚本和本地 `mcp-for-blender` 服务创建、检查或修改 Blender 模型与场景。适用于参考图分析、建模、UV、贴图烘焙、材质、几何节点、场景搭建、绑定、动画、物理、灯光、渲染合成、`.blend` 文件编辑和资产导出。配方以 Blender 4.5 LTS 为测试基线，版本相关接口需在实际运行的 4.x 或 5.x 版本中核验。其他数字内容制作软件、Blender 本体安装及纯二维生图需求另选相应流程。"
---

<a id="blender-python-modeling"></a>

# 使用 Python 在 Blender 中建模

检查任务场景，运行保存到文件的脚本，然后核验场景结构和外观。实时工作使用 Blender MCP；允许后台运行的独立文件任务可通过 Blender CLI 在任务专属副本上运行同一脚本。

<a id="decision-workflow"></a>

## 任务判断

先判断任务属于创建、检查、修复、优化、动画还是导出。阅读 [任务分析](references/task-analysis.md)，根据 [场景诊断](references/scene-diagnosis.md) 检查现有场景，再参照 [流程选择](references/procedure-selection.md) 和 [知识索引](knowledge.json) 决定执行路径。可移植脚本 `scripts/knowledge_catalog.py` 可搜索同级已安装技能的清单。缺少事实时先检查现场。

在项目的 `task-analysis.json` 或等效记录里写明事实、假设、方法、需保留的数据、基线和验收标准。共用输入只保存一份，各阶段引用相同的源哈希和证据。修复前先重现问题，再用相同镜头、比例和照明拍摄修改前后的局部。优化前先测基线，明确收益与允许的退化范围。局部动画编辑或已有兼容绑定可复用已有资产与参考。新建整模按下文准备参考。

保留原图可见设计，根据对象、材质及姿态的常规结构补全遮挡部位。用户指定的例外只适用于其声明范围。完整着装角色在粗模清单中逐侧登记袖内与裙内的肢体支撑链，隐藏外衣检查肩到手、髋到脚的实际连接；源模型和交付文件均需保留已验收结构。按[衣下肢体检查](references/acceptance/blockout.md#covered-limbs)执行。见 [隐藏结构的解读](references/reference-image-analysis.md#complete-hidden-structure)。

创建参考模型前先完成 [参考准备](references/reference-preparation.md)。单图新建整模时，从粗模开始前就要备齐并审阅多视图；复用合适的已审视图，用原图实际调用 `concept-multiview-sheet` 补足缺失方向。单视图准备适用于限定范围的局部编辑。无参考、用户豁免或仅诊断均须如实登记；缺少必要准备时保留未通过状态。

选择有代表性的局部试验，使用已有的分阶段校验流程执行，独立验收并回归检查其他能力。失败时回查与结果相矛盾的诊断。专项流程包括 [手部建模](references/procedures/characters/hand-construction.md)、[手部形变](references/procedures/characters/hand-deformation.md)、[车轮建模](references/procedures/vehicles/wheel-construction.md)、[车轮运动](references/procedures/vehicles/wheel-motion.md) 和 [骨骼绑定与蒙皮](references/procedures/characters/rigging-and-skinning.md)。新建人形角色手部默认以 [v10 右手蓝本](assets/hands/Hand-R-v10.blend) 参考结构和动作，再按角色设计调整比例、造型与材质。逐指建模的角色应在粗模阶段分别检查双手及摆姿后的手指体积，静态角色也适用。这些流程的适用范围仍需实际任务和视觉证据验证。

<a id="blockout-before-refinement"></a>

## 粗模验收后再精修

生成的参考图要分别通过原图忠实度和跨视图一致性审阅。使用多视图技能的可见特征台账和原图核对记录。建模前保留原图、提示词、生成图的哈希和局部对照。复用旧参数时仍须检查本次的参考图。

复杂创建或主要形体修改遵循 [粗模与精修](references/procedures/modeling/blockout-and-refinement.md)：分解资产，记录各模块的方法和理由，建立低分辨率形体，检查后按部位细化。可选盒式建模、基本体组合、曲面、曲线、雕刻或复用资产。检查实际形体后再决定能否细化。

精修前取得与当前粗模、计划和依赖相符的 [粗模验收](references/acceptance/blockout.md) 证据。局部任务复用合适的粗模，保留审阅过的源资产或等效的冻结状态。已有拟合流程可用自己的快照和审阅记录完成等效检查。

先按 [参考解读](references/reference-image-analysis.md#interpret-the-reference-before-tracing-or-choosing-geometry) 区分真实边界、遮挡与反射，说明重复结构的依据。在建模计划中区分交付指标与可选的运行资源限制。先建成忠实于原图的源模型，审阅并冻结后，按 [实时优化](references/procedures/delivery/realtime-optimization.md) 处理派生交付副本。还原过程中保留可见结构和重要曲率。粗模分辨率、增加面数或施工遮罩吻合度都不能决定最终还原度。在关键阶段执行 [源几何与回读检查](references/verification.md#source-evaluated-triangles-and-reimport-are-distinct-layers)，独立检查原图忠实度。分别报告源模型的质量和优化副本的质量与成本；外观明显退化时保护项未通过。

<a id="core-contract"></a>

## 执行约定

- 将可复用的代码保存在 `.py` 文件。已有项目沿用其脚本布局，新项目使用 `scripts/blender/<task-name>.py`。
- 使用已配置的 `ahujasid/mcp-for-blender` 提供的 `mcp__blender__*` 工具。其他实现的同名工具不保证兼容。
- 修改前调用 `get_addon_status` 和 `get_scene_info`。每次 MCP 调用都将用户最新的 Blender 请求原文传给 `user_prompt`。
- 新建模型使用 [制作工作区](references/production-workspace.md)，在任务专属空场景中移除或避开默认立方体、相机和灯光，按需创建参考与摄影棚。编辑已有场景时保留用户数据。生成对象需有稳定的归属标记，仅替换目标模块，不得因重复运行而覆盖用户的 `.blend`。
- 优先使用 `bpy.data`、`bmesh` 和直接属性赋值。只有数据 API 缺少合适方法时才使用 `bpy.ops`，并显式设置模式、活动对象、选择、区域及上下文覆盖。
- 在运行时核对 Blender 版本、RNA 属性、枚举标识、节点插口和操作器签名。不确定或受版本影响时查询 `bpy_api_lookup` 或 `describe_node_type`。
- Blender 4.5.12 LTS 是已测试基线。使用依赖版本的功能前查阅 [版本兼容性](references/compatibility.md)，并核实当前 4.x 或 5.x 环境。
- 宿主侧参考图工具使用本技能的 uv 项目（`uv run --project <skill-dir> ...`）。不要向 Blender 自带或用户全局 Python 安装 OpenCV、NumPy。
- 先生成设计图再建模时，主动用 `concept-multiview-sheet` 补控制视图并审查姿态、投影。需要完整图集时使用五或六视图。单张照片新建整模应在粗模前补方向；简单编辑或用户明确豁免时可跳过。生成的隐藏面标记为推定。存在问题的图集仅供预览，事后模型渲染不能补证建模前的审阅。
- 第一张建模参考图生成前确定角色用途和绑定／静止姿势。可复用角色或用途未指定时，默认采用解剖结构适合的中立姿态，如人体 A/T 姿势、四足站姿，四肢分开、连接处清晰。坐姿或动作图保留为外观及表演参考，另生成并审查中立姿态的多视图。明确要求固定姿势或静态雕塑时保留该姿势。见 [角色交付](references/character-delivery.md#reference-and-rest-pose-before-modeling)；仍须实际检查绑定条件。
- 建模前在 Blender 中搭建参考工作区。各图分别以沿对应轴摆放的图像空物体导入，校准比例和原点，设置透明度、前置显示和按轴可见性。在正面和侧面核查真实叠图；图像分析 JSON 或导入数量不足以证明校准。见 [参考图分析](references/reference-image-analysis.md)。
- 导入多张施工视图前检查项目的 `multiview_review`，其中包含源哈希、姿态、比例、投影、结构、外观、轴向，以及 `passed`、`partial` 或 `blocked` 状态。整套 `passed` 后才导入冻结的干净控制图，部分通过时退回多视图流程。工作区工具检查范围和源文件版本，视觉一致性需要审图。见 [建模前审阅](../concept-multiview-sheet/references/pre-model-review.md)。
- 根据参考图局部改形时（包括独立 Blender 脚本），先确定要修改的轮廓和相邻接触点。修改前在 `required_landmarks` 声明控制视角与锚点，为本次修改重新设置参考并使用映射坐标驱动形变。交付前在同一叠图核对目标与相邻接触。缺方向时先补参考，生成的遮挡面标为推定。
- 通用构建器使用 [可执行参考工作区](references/reference-workspace-tool.md)，通过特征点映射取得坐标或截面，在重建及交付前检查场景状态和审阅记录。模板须显式声明有参考、原创无参考或用户豁免。现有拟合器可继续使用等效的校准像素映射和对照流程。仅导入或打包图片不能证明参考参与了建模。
- AI 参考图可能出错。依据可靠原图、解剖或机械结构及一致的视图解释伪影，并记录解决办法。重大歧义无法按证据消解时向用户确认，其他部位继续制作。保留身份特征，避免复刻不可能的结构。
- 参考驱动任务先读 [还原度与完成条件](references/fidelity-and-completion.md)，精模前建立部位台账，分别跟踪语义模块和识别特征，不按 Blender 对象数推算完成度。
- 分开验收 `blockout`、`feature-complete` 和 `final`。轮廓相似、主视图美观、物体多或存在占位体都不足以认定最终还原完成。
- 分别报告匹配、简化、粗模和缺失的模块数。台账覆盖率表示记录数量；认定 `matched` 还需要指定视角的对比证据。
- 每个实质阶段都要验证预期对象、数据和实际视觉结果。
- 修改已有生成资产时，以最新可编辑版本为基线，在派生副本上执行 [固定镜头返修对比](references/local-feature-review.md#iterate-an-existing-asset)。
- 多视图共同向同一表面供色时，烘焙前在台账的 `projected_features` 登记高对比特征。修复已有模型上的重复标记时也要补录。按 [多视图投射检查](references/uv-and-texture-baking.md#multi-view-projection-check) 检查烘焙或重影修复。
- 批量渲染前通过 [局部形体与细节审阅](references/local-feature-review.md)，在实际求值的网格和预期照明下检查表面朝向、厚度、连接与标志性浮雕。已有快照时，保留参考裁图与固定镜头的白模／材质对照。先验收一个代表性重复部件，确认实际渲染中能读出对应细节。
- 即使用户只给图，也应在整模参考通过审阅后、建立 Blender 工作区前确认造型和表面线索，在参考准备中记录 [风格选择与试样](references/fidelity-and-completion.md#style-sample)。按用户指定或图中可辨的风格查阅 [风格索引](../blender-styles/SKILL.md)，仅加载选定风格和必要参考；仍须核查比例、几何和交付质量。

<a id="workflow"></a>

## 工作流程

1. **确定交付与总计划。** 新建整模先在任务记录中列出用途、风格目标、参考来源、交付物及阶段里程碑。待审参考和待定风格注明状态，第 3 步再落实风格。 明确场景或模型改动、实际尺度、格式、输出路径、参考图和现有 `.blend` 的保留要求。角色在生成参考前确定静态、复用或绑定用途及静止姿态；同时需要固定展示姿势时另行保留。可推定普通美术细节，影响结果的尺寸和破坏性改动须有依据。
2. **分析参考。** 阅读 [参考图分析](references/reference-image-analysis.md) 和 [还原度与完成条件](references/fidelity-and-completion.md)。提取归一化剪影和各视角比例，登记可见模块、重复数量、刻意的不对称及识别特征。逐区确认可靠证据、AI 伪影和跨视图冲突，记录推定依据。重大选择仍无法判断时再询问用户。缺乏尺度锚点时采用归一化尺度，实际尺寸标为未知。
3. **确认整模风格。** 参考驱动的新建整模在所需视图通过审阅后，依据用户目标和原图确认主风格，在参考准备记录中填写 `style_selection`。用户已指定的风格从准备参考时就沿用；此处核对并记录依据。索引未收录时填写 `unlisted` 和理由。进入 Blender 完成参考校准后，再按[风格样件流程](references/fidelity-and-completion.md#style-sample)制作代表部位的小样。
4. **检查 Blender。** MCP 工具缺失时按 [上游安装步骤](references/mcp-workflow.md#missing-mcp-install-the-upstream-integration-then-verify) 为实际客户端配置服务端和插件，核验连接后继续原阶段。依次调用 `get_addon_status`、`get_scene_info`，必要时用 `get_object_info` 查具体对象。连接失败按 [MCP工作流程](references/mcp-workflow.md) 有限重试，先检查进程，必要时用正常界面启动 Blender（可最小化），重试后才请求用户手动启动。不要用 `--background` 或 `-b` 恢复 MCP。若用户只需要脚本，可交付脚本并标明未执行。
5. **初始化工作区。** 新建时激活任务专属空场景，按 Asset、Coarse、References、Studio 区分对象，移除默认启动对象。编辑时明确已有场景并检查，保留原有数据。确定归属、单位、轴向、范围，保存重开后核对活动场景。见 [制作工作区](references/production-workspace.md)。
6. **建立参考工作区。** 将各视图导入专属集合，作为朝向对应正交轴的图像空物体。透明度可从 0.35–0.5 起调，设置前置显示和按面／轴可见性。校准中线、地面、原点、比例和特征点后锁定选择与变换。可靠性不足的视图只作补充。实际查看可见参考的正面和侧面截图，并保留打包的图像及校准、解读记录。仅在无视觉参考或用户明确豁免时跳过；无法运行 Blender 时如实标记未执行。
7. **编制施工计划。** 新建整模在参考审阅与校准完成后、创建第一块角色或资产网格前，按[两阶段规划](references/task-analysis.md#construction-plan)写出模块先后和每步通过条件。 按模块记录表示方法、选型依据、关联对象、连接、依赖及检查项。参考驱动任务在粗模前根据已审视图生成[逐视角清单](references/acceptance/blockout.md#reference-checklist)，先逐图盘点可辨部件，再把台账逐项对应到计划的模块、控制视角和可判断对错的局部形状条件。小部件登记同尺度特写，逐项核对轮廓、开口、厚度与相邻部件的连接或遮挡。逐视角写清参考中应露出的形状与遮挡范围。每个控制视角先审整身双色剪影叠图，再审局部对照图，分别记录该镜头实际可见的边界和偏差；发现偏差就修正几何并复拍受影响的视图，再进入精修。角色按[发型、双手与鞋的专项核对](references/acceptance/blockout.md#hair-hands-footwear)记录粗发束或表面纹理的制作依据、两只手的尺寸与指形、脚袜鞋的共用截面。参考中有交领时，按[交领开口与叠穿](references/acceptance/blockout.md#crossed-collar)逐件建立开口和连续领缘；内外衣均为交领时先单显各层，再合穿复核胸前遮挡与侧面领宽。有配色目标时提前圈选材质样区，在材质试渲染时比较。完成诊断并按下表选择流程后，再设计层级、建模方法、修改器／节点、材质、灯光和输出约束。写明本轮目标阶段，不因实现困难擅自降低标准。
8. **编写脚本。** 可从 [任务模板](assets/blender_task_template.py) 开始，拆分 `build_*`、`update_*`、`validate_*` 和按需使用的 `export_*`。按 [Python建模](references/python-modeling.md) 使用可靠的 `bpy` 写法，依据校准的特征点和轮廓确定坐标与比例。
9. **按施工计划分阶段执行。** 按模块依赖和模块内的步骤施工，在当前组装状态验收本步，再进行依赖该结果的工作。 参考角色进入精模前，在已组装粗模上完成 [剪影对比](references/acceptance/blockout.md#参考角色的粗模剪影)。每个适用控制视角分别检查整身、脸型、颈部和躯干，保存叠图与粗模快照。构建、视觉审阅和精修分开运行，修改前将精修绑定到当前范围的审阅。按对象增加 [连接与空腔检查](references/procedures/modeling/containers-and-connections.md)。失败时诊断、局部修复、重新审阅，保留尝试并使旧证据失效。实际渲染预检后锁定比较设置。用简短的 `execute_blender_code` 引导代码加载脚本；大型任务按构建、绑定、验证、渲染分阶段检查前序版本和 MCP 原始错误。见 [分阶段执行](references/staged-execution.md) 和 [MCP工作流程](references/mcp-workflow.md)。
10. **对照参考迭代。** 按 [固定镜头精修](references/fidelity-and-completion.md#fixed-camera-refinement-loop) 先审 组装后的整模，再选局部修改；扩大到相邻区域，最后整体精修。保留参考可见的视口截图，检查图像叠加、头部比例和肢体厚度。五官与发型使用 [固定镜头特征对比](references/fidelity-and-completion.md#fixed-camera-feature-comparison)，候选修改后再复拍。分析工具只作辅助。粗模、贴图前白模和最终导出都要在原图对应姿势和镜头下直接核查可见特征。生成正视图可辅助施工，原图可见特征仍须对照上传原图。新建整模在正式绘制、投射或烘焙贴图前先完成并冻结 [已审白模](references/fidelity-and-completion.md#clay-review-before-production-texturing)；早期风格试验限于局部。贴图后用相同镜头比较白模和材质渲染。按证据处理 AI 伪影；重大歧义需用户判断。根据实查更新模块状态和脚本。
   角色组装后复核用途。需要摆姿或动画时，在绑定前完成 [动作分析与测试计划](references/procedures/characters/rigging-and-skinning.md#动作分析与逐项复测)。逐个动作记录控制器或直接操纵的 FK 骨，在可编辑绑定中实际操作，返修后及最终回归时同时核验控制行为与网格形变。静态交付在建模计划中登记范围。
11. **执行完成验收。** 回读导出文件后，对实际交付件执行 [正式验收命令](references/fidelity-and-completion.md#final-evidence-file)，依据本版报告决定是否通过。用 `scripts/validate_module_ledger.py` 核查逐项比较和最终证据，查看多视图总览及透视图。验证器检查证据声明，视觉判断仍须审图。禁止仅凭模块存在就批量标记为 `matched`。用户纠正会使受影响的匹配项及最终审阅失效。把可见缺陷列为剩余差异前先执行 [可见缺陷修复](references/fidelity-and-completion.md#visible-defect-repair)。缺原图哈希会阻断认证，视觉修复仍应继续；缺少视角或细节时调用 `concept-multiview-sheet` 补图，从失败视角检查修改后的网格。局部停滞时记下证据并保留最佳已审版，继续其余部位。最终整模审阅确认无可执行的改进后，才可交付带差异说明的最佳版本；粗模与特征完成阶段保留其真实阶段名称。
12. **保存与导出。** 只写入指定或可明确推导的路径；导出限制在任务场景与对象白名单内，不依赖其他场景的选择。MCP 的 `export_scene` 能执行所需设置时方可使用，否则在支持的材质与动画范围内调用 [隔离交付适配器](references/production-workspace.md)。保留可编辑源，隔离回读后复查几何、蒙皮和动作片段。静态贴图 GLB 执行 [静态审计](references/export-and-packaging.md#static-textured-glb-audit)，交付前完成 [资产可用性验收](references/acceptance/usable-asset.md) 和 [验证](references/verification.md)。

<a id="production-repair-routes"></a>

## 常见修复流程

扫描或生成网格的修复见 [网格修复](references/procedures/modeling/generated-mesh-recovery.md) 和 [数据传递](references/procedures/modeling/data-transfer-repair.md)。基础绑定诊断后可使用 [关节校正](references/procedures/characters/joint-correctives.md)。表面与模拟问题分别查 [法线烘焙修复](references/procedures/surfacing/normal-bake-repair.md) 或 [布料接触修复](references/procedures/simulation/cloth-collision-repair.md)；交付阶段可查 [glTF验证](references/procedures/delivery/gltf-validation.md) 和 [实时优化](references/procedures/delivery/realtime-optimization.md)。

每条流程都说明输入、适用条件、诊断与独立验收。资料来源和适用边界见 [制作资料来源](references/sources/production-sources.md)。按需阅读，避免静默安装可选插件；实际任务和视觉证据确定适用范围前，这些流程保持实验状态。

<a id="loading-a-persistent-script-through-mcp"></a>

## 通过 MCP 加载已保存的脚本

重复拟合角色或参考时使用 [参考拟合流程](references/reference-fitting/workflow.md) 和 `scripts/fit_character.py`。使用已审语义遮罩、锚点、固定渲染通道、模块指标、可配置构建器、有界候选、锁定、快照与回退。扩展前阅读 [架构审计](references/reference-fitting/architecture.md)，对象专属坐标放入 JSON，复用已有几何和风格工具。二维阈值或临时肢体测试不足以证明最终三维和动画验收通过。

只通过 `execute_blender_code` 发送以下引导代码，安全替换为实际绝对路径：

```python
from pathlib import Path

script_path = Path("/absolute/project/scripts/blender/build_asset.py")
scope = {"__name__": "__main__", "__file__": str(script_path)}
exec(compile(script_path.read_text(encoding="utf-8"), str(script_path), "exec"), scope)
```

如果 Blender 无法读取项目路径，将同一脚本拆成若干自包含的小段执行。每段重新导入模块，用稳定名称或归属标记取回对象，不依赖跨调用保留的 Python 全局变量。

<a id="content-routing"></a>

## 按任务查阅资料

只读取当前请求需要的参考：

| 任务 | 参考资料 |
|---|---|
| 折纸、软黏土、手捏橡皮泥或混合风格 | [blender-styles](../blender-styles/SKILL.md)，然后查阅选定的 `styles/<id>/STYLE.md` |
| AI 渲染图、照片、线稿或多视图输入 | [references/reference-image-analysis.md](references/reference-image-analysis.md) 和 [references/fidelity-and-completion.md](references/fidelity-and-completion.md) |
| 网格、曲线、硬表面、重复或有机形体 | [references/modeling-recipes.md](references/modeling-recipes.md) |
| UV 展开、纹素密度、光照贴图 UV、UDIM 或烘焙 | [references/uv-and-texture-baking.md](references/uv-and-texture-baking.md) |
| PBR、程序材质或几何节点 | [references/materials-and-nodes.md](references/materials-and-nodes.md) |
| 重拓扑、面数、LOD、碰撞网格或引擎命名 | [references/game-assets.md](references/game-assets.md) |
| 相机、棚拍灯光、世界环境和渲染设置 | [references/scene-lighting-rendering.md](references/scene-lighting-rendering.md) |
| 渲染通道、Cryptomatte、降噪、合成或多层 EXR | [references/compositing-and-passes.md](references/compositing-and-passes.md) |
| 关键帧、约束、驱动器、骨架 | [references/animation-and-rigging.md](references/animation-and-rigging.md) |
| 蒙皮权重、形变绑定、形态键、根运动或角色导出 | [references/character-delivery.md](references/character-delivery.md) |
| 刚体、布料、流体、软体、力场或缓存 | [references/physics-and-simulation.md](references/physics-and-simulation.md) |
| 资产浏览器、复用资产、链接或追加库及库覆盖 | [references/asset-libraries.md](references/asset-libraries.md) |
| 静帧、动画、游戏资产、3D 打印或目标选择 | [references/output-targets.md](references/output-targets.md) |
| 保存、GLB/glTF、FBX、OBJ、STL、打包或回读 | [references/export-and-packaging.md](references/export-and-packaging.md) |
| Blender 版本或 API 差异 | [references/compatibility.md](references/compatibility.md) |

以下通用资料也适用：

- 工具顺序、本地 MCP 工具名、连接失败及分步执行，见 [MCP工作流程](references/mcp-workflow.md)。
- 幂等性、上下文安全、变换、命名与性能，见 [Python建模](references/python-modeling.md)。
- 结构、几何、视觉、渲染、保存和导出检查，见 [验收验证](references/verification.md)。

<a id="completion-report"></a>

## 完成报告

报告选用的知识条目 ID、诊断依据、基线与回归结果、脚本路径、场景修改、已运行的验证，以及 `.blend`、渲染图和导出文件路径。参考建模还须给出参考集合、校准与对比证据、目标阶段、必需模块数及匹配、简化、粗模、缺失数量和用户允许的每项简化。台账覆盖率不能解释为图像相似度或实测还原精度。说明已排除的 AI 伪影、推定修正，以及影响尺度、拓扑、材质或还原度的假设和未决事项。区分实机验证与仅写脚本；只有 `ready_to_claim_complete: true` 且参考对比和渲染审阅通过后，才能称为完成。

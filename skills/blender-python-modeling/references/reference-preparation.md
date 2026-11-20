# 建模前先决定参考路线，避免静默跳过已有 Skill

适用：图片驱动的新建模型，以及决定是否需要 concept-multiview-sheet。新建先读本流程；已有合适资产的局部修复不强制重新生成视图。

## 选择路线

| route | 使用条件 | 不允许的替代 |
|---|---|---|
| generated | 透视/遮挡、隐藏结构或姿态影响本次构建，需要生成规范视图 | 只导入照片、凭经验写坐标、拿模型渲染倒充前置参考 |
| existing_reviewed | 已有适合本次范围、实际审查过的视图或校准资料 | 有几个图片文件就认定可用；参数配方代替视图证据 |
| single_view_sufficient | 合适正交单视图足以约束当前范围，无待补隐藏体积/姿态 | 对复杂透视产品图一律说“单图足够” |
| no_reference | 真正无视觉源的原创任务 | 用户提供图片却选择 original 绕行 |
| user_waived | 会话已有明确用户豁免并记录实际指令 | Agent 自己决定省时间或替用户批准 |
| diagnostic_only | 为定位参考矛盾做明确诊断实验 | 把诊断模型、旧粗模或静态 fitter 当完整交付 |

concept-multiview-sheet 在安装依赖中是 optional，不代表选中生成路线后可以省略。已有合适来源无需重新生成；需要生成时必须读取并实际执行该 Skill，默认用内置图像工具提供原图作为参考。不可用时说明阻塞并继续独立工作，不偷偷切回经验建模或另一收费服务。

## 必须留下决策和证据

项目从 [路线模板](../assets/reference-preparation-template.json) 建立记录。source_images 是实际原图；construction_images 是实际导入的独立视图。记录投影、是否需要隐藏结构/姿态补全、用途和理由，不能按想走的路线反过来编造事实。

generated 路线还需要：

1. generation_record 文件引用：tool 为 builtin-image-generation，reference_images 为原图列表，prompt 为实际提示词文件，outputs 为输出列表。每项使用 path/sha256。记录来自实际调用，不是在模型做完后补计划。
2. source_fidelity_review 文件引用：实际原图/生成图哈希、审阅者、observed 关键约束、原/候选区域、finding 和证据；未过关键项不能构建。
3. 多视图一致性记录：按已有 multiview_review 校验姿态、投影、尺度和允许范围。源图忠实不意味着跨视图一致，反之也一样。
4. Blender 实际导入和标定。生成图片与 JSON 校验不能代替这一阶段。

相对路径按记录文件所在目录解析；模板不是通过证明。图片/提示词/审查变化后旧哈希不能继续通过。existing_reviewed 和 single_view_sufficient 使用 existing_review 引用，其 JSON 包含 status=passed、实际 finding 及带哈希的 construction_images；不能把自己写的“可信”当作照片被校准的证明。纯原创显式使用 no_reference 和两个空图片列表。

## 执行入口

[reference_preparation.py](../scripts/reference_preparation.py) 是标准库检查器。模板 REFERENCE_PREPARATION 必须指向决策文件；即使 BUILD_MODE=original 也需显式声明 no_reference。它在场景/几何构建前验证路线、文件和哈希，并参与下游签名。它不会看图，事实与忠实度仍需实际审阅。

fitter 新建 build / 无 source 的 optimize 必须传 --reference-preparation。已有 source 的局部优化/render 不强制重生成图。实验仍需显式 diagnostic_only 决策并传 --diagnostic-only，不能升级为正式建模通过。

    from reference_preparation import require_preparation
    decision = require_preparation(
        project / "reference-preparation.json", task_id, mode="reference",
        construction_images=[project/"references/front.png", project/"references/right.png"])

源图检查通过仅证明声明和证据新鲜，还必须验证一致性、标定和视觉结果。不允许任意直接 bpy 脚本绕过后宣称完整执行 Skill。评测应独立检查路由、实际生成记录、源图审查和标定；缺失是前置失败，不能只扣少量过程分后继续算可用交付。

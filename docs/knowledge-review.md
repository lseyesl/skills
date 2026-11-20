# 知识验证、审阅与失效

知识默认 experimental。维护者负责来源、接口与版本范围，专业审阅者负责技术准确性和适用边界；不得因目录整理、脚本成功或评分器给出通过就自动升级。未指定专业审阅者的内容保持 experimental，无须建立额外 Skill。

validated 条目需要 validated_for 明确平台/版本/用途，evidence 指向本 Skill 内 JSON 回执。回执绑定当前条目语义、正文、requires/verification 闭包，以及声明的评分任务和工具文件。须有明确 reviewer、非空且全部通过的 checks、passed verdict 和与 validated_for 相等的 scope。tool_dependencies 声明必须覆盖的本 Skill 脚本。

草稿生成：`python tools/knowledge_audit.py --id blender.hand-deformation --suite evals/task-suite.json --tool scripts/domain_checks.py --output .tmp/hand-receipt-draft.json`。输出只含指纹与 unknown 状态，不构成通过或审阅。真实执行并独立复核后，将回执保存到 Skill 内证据目录，再更新条目状态。证据应记录来源链接、版本和校准依据；没有完整支持范围不得升级。

`python tools/knowledge_audit.py` 检查所有 validated 条目。正文、前置知识、验收规则、语义边界、工具或评分任务变化会导致 stale。检索此时降为 experimental 并显示 validation_state；仓库 CI 会拒绝过期的 validated 声明。路径存在和哈希一致只证明证据新鲜度，不能鉴定审阅内容是否正确，也不能自动发现未声明依赖。

修改后使用 impacts 定位受影响流程，复测并重新审阅后才能更新回执。保留旧报告用于追溯，不篡改旧通过结果。历史材料不进入活动检索；迁移报告仅作为证据来源。

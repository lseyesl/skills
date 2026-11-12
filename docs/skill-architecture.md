# Skill 与知识组织

Skill 是稳定的能力入口。先查 index.md 和现有能力；对象、症状、风格、导出目标优先归入已有 Skill 的知识或处理方案。仅在工具环境、输入输出和工作流程具有独立边界时新增 Skill，并记录已有入口不能承载的原因。

skills.json 只管理安装依赖；catalog/taxonomy.json 为每个 Skill 指定唯一主分组；各 Skill 的 knowledge.json 保存知识选择信息，正文保留在原文件。index.md 是人工入口。制作项目 routes.json 继续只管制作路由，不承担全库检索。

知识 ID 稳定，不随文件移动改变。kind 为 overview/knowledge/procedure/acceptance/style；tasks 使用查询工具的受控集合；subjects 为领域标签。aliases 收录中英文症状与术语。applies_when/exclude_when 是必须人工核对的条件，conditions 是可用现场事实作硬过滤的键值条件。required_facts 缺失时返回待检查项，不能把搜索命中当成执行许可。

requires 指知识前置依赖，verification 指验收入口；跨 Skill 必需引用必须属于 skills.json 的 requires 闭包，不能因 optional 可见而假设已经安装。资源路径只能指向本 Skill 内活动文件。可选协作仍按对应 SKILL.md 判断，未安装时说明缺口。执行资源不能依赖源码根目录的 tools/ 或 docs/。

状态默认 experimental。validated 必须附 validated_for（版本、用途、环境）与 evidence（本 Skill 内的报告路径）；文件存在仅证明证据可定位，不证明报告正确。deprecated 不参与搜索；改名应保留旧 ID 的迁移说明。修改知识后，通过 requires/verification 反向关系查找受影响流程及评测，更新证据；不继承旧的通过结论。

新增内容时更新 knowledge.json、相应评测、索引；新增 Skill 还需更新 skills.json 和 taxonomy。保持原目录与安装锁协议；修改源码后由消费项目显式升级，不改受管副本。

查询：`python tools/knowledge.py search "握拳塌陷" --task repair --subject hand`。锁定安装后使用 `python <skill-dir>/scripts/knowledge_catalog.py search "握拳塌陷" --task repair`，默认只搜索同级已安装 Skill。按 ID 获取：`python tools/knowledge.py retrieve blender.hand-deformation`。空结果表示没有匹配证据，继续诊断或说明知识缺口，不能套用不相关方案。

影响分析：`python tools/knowledge.py impacts blender.acceptance.hand-poses` 返回该条目及通过前置/验收引用受影响的流程。按结果复测相关任务；无显式引用的外部调用仍需人工检查。

knowledge.json 可声明 query_exclusions，按词项组合显式排除其他领域及能力边界外的查询；这里只做可解释规则，不保证理解任意否定或复杂意图。空值事实保持未知；条件值类型必须一致。得分相同时优先具体 procedure，再显示通用知识与入口。新增反例应记录原始失败，并在修复后归入回归集，不再称盲测。

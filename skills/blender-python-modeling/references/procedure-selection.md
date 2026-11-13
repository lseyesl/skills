# 方案选择与执行

用 [知识索引](../knowledge.json) 或本 Skill scripts/knowledge_catalog.py 按任务、对象与症状查询；检索结果是候选，不是操作授权。读取正文，核对 applies_when/exclude_when 和 required_facts；有冲突排除，无证据先诊断。无对应方法时明确缺口，先做可回滚局部实验，禁止声称已验证通用方法。

手部新建用 hand-construction；已有手形变异常用 hand-deformation；车轮新建用 wheel-construction；偏心、摆动、滚动关系用 wheel-motion；绑定/权重/骨骼导出用 rigging-and-skinning。风格选择继续使用 blender-styles，不能用风格规范替代结构方案。

在任务记录中写选中 ID、依据、改动范围、替代方案与停止条件。先在代表性局部验证，再推广；修改后按独立验收入口测试。失败先归因到检索、适用性、诊断、执行或验收，不无限调参数。新证据否定假设时回到诊断；达到事先声明的实验预算后报告具体未决项，不降低完成标准。

复用 stage_guard、模块台账、参考拟合和现有持久脚本；不为一个局部修改再建执行框架。保存修改前后证据，更新受影响签名，旧通过回执不能继续代表新结果。

更多问题：生成/扫描网格用 [网格恢复](procedures/modeling/generated-mesh-recovery.md)，重拓扑后数据用 [迁移](procedures/modeling/data-transfer-repair.md)，基础绑定正确后的局部失真用 [关节修正](procedures/characters/joint-correctives.md)，烘焙接缝用 [法线诊断](procedures/surfacing/normal-bake-repair.md)，布料异常用 [接触诊断](procedures/simulation/cloth-collision-repair.md)，GLB 交付/优化用 [格式验证](procedures/delivery/gltf-validation.md) 与 [优化回归](procedures/delivery/realtime-optimization.md)。

复杂模型从 [低分辨率搭建与细化](procedures/modeling/blockout-and-refinement.md) 进入。Cube 盒式建模、基础体组合、面片/曲线/雕刻或已有资产复用按模块判断；进入细化前使用 [基础形体验收](acceptance/blockout.md)。

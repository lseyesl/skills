---
name: ancient-tales-production
description: 中国神话视频的调研、策划、编剧、导演、美术、音频、本地化和交付流程；用于真实制作项目，不用于个人课程或 Wiki 摄取。
---

# 神话制作流程

本技能提供专业流程与验收依据，不是自动调度器。制片／总控负责阶段推进，导演负责镜头决策与专业复审；通用 Skill 制作资产，项目后端装配和渲染。选择能力、处理规则冲突或跨阶段交接时，先读[技能协作与交付契约](references/技能协作与交付契约.md)。独立建模、拆件或图片任务可直接使用对应 Skill，不因使用能力工具而自动进入影片五 Gate。

## 当前权威边界

- 当前项目仓库拥有内容、提示词、生产总控、交接和批准记录；Obsidian 仅提供来源与知识查询，禁止向 Vault 写制作状态。
- 从项目 README、migration.json、content/制作/生产总控及最新 HANDOFF 读取当前事实。无总控的草案保持草案，不补造批准。
- 下列 references 是现行专业规范；退役原文单独保存在 history/，仅供明确的历史审计，不参与活动路由。
- 文本、规则、清单和代码进入项目 Git；媒体和工程二进制进入 HF。资产身份为 repository_id + project_id + bucket URI + SHA-256 + version，不能用 Git commit 证明二进制存在。
- 读取 sources.lock.json 核对来源；事实、研究解释和创作推演分层。不得改写来源层。
- 不改变既有项目 ID、风格或批准事实；同故事不同风格独立制作，不跨项目借用正式资产。
- 沿用五个 Gate 和 locked 上游依赖，不因迁移、导入或测试成功自动晋升。
- FFmpeg 编码和滤镜线程最多 max(1, floor(逻辑 CPU / 2))，并以低优先级运行。

## 按阶段读取

| 任务 | 专业参考 |
|---|---|
| 阶段与交接 | [全流程总控](references/工作流-全流程总控.md) |
| 事实与选题 | [神话调研](references/工作流-神话调研.md)、[策划](references/工作流-策划与制片.md) |
| 剧本与分镜 | [编剧](references/工作流-编剧.md)、[导演](references/工作流-导演.md) |
| 视觉与资产 | [美术](references/工作流-美术设计与资产.md)，再按已绑定视觉 profile 读取相应参考 |
| 音频与语言 | [音频](references/工作流-音频交付与导入.md)、[本地化](references/工作流-多语言本地化.md) |
| 终片 | [成片 QA](references/工作流-成片合成与质量检查.md) |

后端执行以当前项目 docs/backend 和实际脚本为准；不存在的历史脚本不能直接调用。需要技能锁定安装或 HF 资产管理时调用 [ancient-tales-pipeline](../ancient-tales-pipeline/SKILL.md)；安装依赖不表示自动运行它，其字节校验不替代专业审阅或批准。

Skill 库与 Obsidian 的源码及资源均完整保留在各自 Git 中；本技能的 HF 条款仅适用于独立制作仓库。原有 project.json 与 runtime manifest 必须与迁入的历史内容一并核对，发生冲突先审计，不以旧草案覆盖较新的工程事实。

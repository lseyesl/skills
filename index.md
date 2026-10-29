# 技能索引

本文件集中维护本仓库现有技能，供用户和 Agent 查找。根据任务选择入口后，读取对应 `SKILL.md`，以其中的适用边界、执行流程与依赖要求为准。

## Blender 与视觉资产

| 技能 | 适用场景与边界 |
|---|---|
| [blender-python-modeling](skills/blender-python-modeling/SKILL.md) | Blender 建模、参考图校准、材质、场景、绑定、动画、渲染和导出；不用于仅需二维图片的任务。 |
| [blender-styles](skills/blender-styles/SKILL.md) | 选择和应用柔和低多边形黏土、稚拙手捏橡皮泥等 Blender 风格；通用建模配合 blender-python-modeling。具体风格与验证状态见技能内索引。 |
| [concept-multiview-sheet](skills/concept-multiview-sheet/SKILL.md) | 从单视图概念图推演五视图或六视图设计稿及技术线稿；隐藏视图属于设计推测，不代表实测几何或真实拓扑。 |
| [continuous-action](skills/continuous-action/SKILL.md) | 基于内置 Blender 动作库生成连贯角色动作图或精灵序列；可用动作以运行时读取的动作目录为准。 |
| [shadow-puppet-image](skills/shadow-puppet-image/SKILL.md) | 生成或修正皮影角色图片，约束头颈、腰身、腿脚等平面分件与搭接，允许明亮现代配色；交付静态参考，不替代拆件与活动验证。 |
| [shadow-puppet-part-splitter](skills/shadow-puppet-part-splitter/SKILL.md) | 将皮影、剪纸或平面角色参考图拆成独立二维组件，按需进行刚性绑定、隐藏区域补全和活动验证；不用于三维重建或普通矩形裁图。 |

## 文档转换

| 技能 | 适用场景与边界 |
|---|---|
| [epub-xhtml-to-markdown](skills/epub-xhtml-to-markdown/SKILL.md) | 直接读取流式 EPUB 的 XHTML，按章转换 Markdown 并生成 Obsidian 嵌入总装笔记；此类 EPUB 优先使用，不适用于扫描书或需视觉重建的固定版式。 |
| [pdf-epub-to-markdown](skills/pdf-epub-to-markdown/SKILL.md) | 使用 marker-pdf 将 PDF、EPUB、Office 文档、HTML 或图片转换为面向 Obsidian 的 Markdown；具体支持与依赖见技能说明。 |

## Obsidian 知识库

| 技能 | 适用场景与边界 |
|---|---|
| [query-obsidian](skills/query-obsidian/SKILL.md) | 检索用户已有 Obsidian / ai-wiki 知识库并基于笔记回答；普通查询保持只读。 |
| [distill-to-obsidian](skills/distill-to-obsidian/SKILL.md) | 将正在阅读的代码、文章、文档或讨论蒸馏为可复用知识并整合进 Obsidian；不用于临时摘要或逐字归档。 |

## 索引维护

- 新增、移除、重命名技能或改变适用范围时，同步更新本文件。
- 每个 `skills/<skill-name>/SKILL.md` 应在本索引中有一个入口。
- 本索引只保存简要路由信息，详细流程和依赖保留在各技能内。
- 未找到匹配项时，继续搜索 `skills/` 目录，避免遗漏尚未同步到索引的技能。

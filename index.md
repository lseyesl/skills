# 技能索引

按任务选择入口，再读取对应 `SKILL.md` 的执行流程与依赖。整片神话视频制作从制作流程进入；独立图片、拆件、建模、文档或知识任务直接选择通用能力。项目基础设施按需使用。

## 制作流程

| 技能 | 适用场景与交付 |
|---|---|
| [ancient-tales-production](skills/ancient-tales-production/SKILL.md) | 神话视频从调研、策划、编剧、导演到素材、音频、本地化与成片交付。定义专业分工、五个 Gate 和交付契约，提供交接校验与能力环境检查；按项目配置调用通用 Skill 和后端。 |

导演负责镜头决策与专业复审，制片／总控负责阶段推进，项目后端负责装配与渲染。调用关系与边界见[技能协作与交付契约](skills/ancient-tales-production/references/技能协作与交付契约.md)；制作状态与批准记录由具体项目拥有。

## 通用视觉能力

### 皮影动画

| 技能 | 适用场景与交付 |
|---|---|
| [shadow-puppet-animation](skills/shadow-puppet-animation/SKILL.md) | 基于双参考的皮影镜头制作与审阅：角色、服装、场景道具、可动性、接触与运动逻辑、表演、镜头叙事和品质对照；复用概念图／拆件技能，不替代后端或影片批准。 |

### 概念设计与二维资产

| 技能 | 适用场景与交付 |
|---|---|
| [concept-multiview-sheet](skills/concept-multiview-sheet/SKILL.md) | 从单视图概念图推演五视图或六视图设计稿及技术线稿；隐藏视图属于设计推测，不代表实测几何或真实拓扑。 |
| [shadow-puppet-image](skills/shadow-puppet-image/SKILL.md) | 生成或修正皮影角色概念图，约束平面分件、搭接与遮挡；交付静态参考，不替代独立组件制作、绑定或活动验证。 |
| [shadow-puppet-part-splitter](skills/shadow-puppet-part-splitter/SKILL.md) | 将皮影、剪纸或平面角色图制作成独立二维组件，按需绑定、补全与试动；单图可经本地边界/关节标注编译出独立 PNG、组装数据与差分；已有素材可直接使用确定性处理工具。制作项目须遵循约定的资产单位与隐藏区策略。 |

### 三维建模与风格

| 技能 | 适用场景与交付 |
|---|---|
| [blender-python-modeling](skills/blender-python-modeling/SKILL.md) | Blender 建模、参考校准、材质、场景、绑定、动画、渲染和导出；交付可复现脚本、场景与验证证据，不用于仅需二维图片的任务。 |
| [blender-styles](skills/blender-styles/SKILL.md) | 选择柔和低多边形黏土、稚拙手捏橡皮泥等 Blender 风格，提供造型、材质、灯光与节奏规则；通用建模依赖 blender-python-modeling，风格验证状态见技能内索引。 |

### 动作参考与序列生成

| 技能 | 适用场景与交付 |
|---|---|
| [continuous-action](skills/continuous-action/SKILL.md) | 基于内置 Blender 动作库生成连贯角色动作图或精灵序列，交付参考帧、生成帧、映射与连续性检查。可用动作以运行时目录为准；不静默替换缺失动作。 |

这些能力可独立使用，也可按制作契约协作。工具技术通过只作为验收证据，不直接推进影片 Gate 或批准资产。

## 文档与知识

### 文档转换

| 技能 | 适用场景与交付 |
|---|---|
| [epub-xhtml-to-markdown](skills/epub-xhtml-to-markdown/SKILL.md) | 直接读取流式 EPUB 的 XHTML，按章转换 Markdown 并生成 Obsidian 嵌入总装笔记；普通流式 EPUB 优先使用，不适用于扫描书或需视觉重建的固定版式。 |
| [pdf-epub-to-markdown](skills/pdf-epub-to-markdown/SKILL.md) | 使用 marker-pdf 将 PDF、EPUB、Office 文档、HTML 或图片转换为面向 Obsidian 的 Markdown；支持范围与环境要求见技能说明。 |

### 知识检索与沉淀

| 技能 | 适用场景与交付 |
|---|---|
| [query-obsidian](skills/query-obsidian/SKILL.md) | 检索已有 Obsidian / ai-wiki 知识库，基于笔记回答并提供来源；普通查询保持只读。 |
| [distill-to-obsidian](skills/distill-to-obsidian/SKILL.md) | 将代码、文章、文档或讨论蒸馏为可复用知识并整合进 Obsidian；不用于临时摘要或逐字归档。 |

## 项目基础设施

| 技能 | 适用场景与交付 |
|---|---|
| [ancient-tales-pipeline](skills/ancient-tales-pipeline/SKILL.md) | 锁定、安装与检查共享 Skill；在明确启用的制作项目中索引、上传、恢复 HF 资产，校验身份、文件完整性和批准回执。不承担创作、阶段调度或资产批准。 |

技能库与 Obsidian 的源码、参考图片和动作库由各自 Git 管理；HF 资产操作仅适用于明确配置的独立制作项目。

## 依赖、安装与验证

必需本库依赖、可选协作 Skill 与外部工具统一声明在 [skills.json](skills.json)。安装器只自动补齐必需项，不自动安装可选能力或外部工具。安装方式、固定版本消费与旧锁升级见 [README](README.md)。

仓库校验入口为 `python tools/check.py`；制作项目的交接与环境检查见[交接校验与环境检查](skills/ancient-tales-production/references/交接校验与环境检查.md)。

## 索引维护

- 新增、移除、重命名技能或改变适用范围时，同步更新本文件及依赖声明。
- 每个 `skills/<skill-name>/SKILL.md` 在对应用途分类中保留一个主入口。
- 本索引只保存选择入口所需的信息，详细流程、工具接口和契约保留在对应技能中。
- 未找到匹配项时，继续搜索 `skills/`，检查是否存在尚未同步的技能。

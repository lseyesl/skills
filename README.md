# lseyesl_skills

个人 Claude Skills 技能合集。

本仓库收录各类可复用的 Skills，用于在 Claude（或兼容 Agent）环境中通过 `skill` 巇令加载，辅助完成特定任务。

## 目录结构

```
.
└── skills/
    └── <skill-name>/
        └── SKILL.md
```

每个 Skill 位于 `skills/` 下一个独立目录中，至少包含一个 `SKILL.md` 描述文件。

## Blender 制作与风格

| Skill | 作用 |
|---|---|
| [blender-python-modeling](skills/blender-python-modeling/SKILL.md) | 通用建模、参考图导入校准、对照验证、绑定和交付流程 |
| [blender-styles](skills/blender-styles/SKILL.md) | 统一风格入口，按索引加载柔和黏土、稚拙手捏橡皮泥及组合规则，共用材质、灯光和渲染工具 |

风格细节位于 `blender-styles/styles/<style-id>/STYLE.md`，不再分别注册 Skill。当前有 `soft-clay` 和 `handmade-plasticine`；手捏橡皮泥仍待实际小样视觉校准。

## 二维角色资产

| Skill | 作用 |
|---|---|
| [shadow-puppet-part-splitter](skills/shadow-puppet-part-splitter/SKILL.md) | 按目标动作拆分皮影组件，在 Blender 刚性绑定试动，补全隐藏结构并验收活动范围 |

## 使用方式

1. 将本仓库克隆到 Claude 可识别的 skills 目录（例如 `~/.claude/skills/`）。
2. 在对话中通过 `skill` 工具加载对应技能，或在需要时由 Agent 自动根据描述触发。

## 新增 Skill

在 `skills/` 下创建新的子目录，并在其中放置 `SKILL.md` 文件即可。建议遵循现有 Skill 的命名与组织方式。

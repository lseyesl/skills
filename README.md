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

## 使用方式

1. 将本仓库克隆到 Claude 可识别的 skills 目录（例如 `~/.claude/skills/`）。
2. 在对话中通过 `skill` 工具加载对应技能，或在需要时由 Agent 自动根据描述触发。

## 新增 Skill

在 `skills/` 下创建新的子目录，并在其中放置 `SKILL.md` 文件即可。建议遵循现有 Skill 的命名与组织方式。

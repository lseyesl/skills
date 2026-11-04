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

## 技能索引

查看 [index.md](index.md)，按用途查找全部现有技能、适用场景与 `SKILL.md` 入口。完整清单统一在该文件维护。

Agent 的仓库工作约定见 [AGENTS.md](AGENTS.md)。

## 使用方式

1. 将本仓库克隆到 Claude 可识别的 skills 目录（例如 `~/.claude/skills/`）。
2. 在对话中通过 `skill` 工具加载对应技能，或在需要时由 Agent 自动根据描述触发。

## 新增 Skill

在 `skills/` 下创建新的子目录，并在其中放置 `SKILL.md` 文件，同时更新 [技能索引](index.md)。建议遵循现有 Skill 的命名与组织方式。

## 权威源与同步

本仓库是自维护 Skill 的唯一源码。按项目 skills.lock.json 安装到项目受管目录，不独立编辑安装副本。

运行 `python skills/ancient-tales-pipeline/scripts/runtime.py --help` 查看同步与 HF 命令。Skill 源码与依赖媒体完整保留在本仓库 Git 中，不上传 HF；Obsidian 仓库也不使用 HF。working-tree 锁明确依赖本地尚未提交源码；提交后运行 update/install。官方和第三方 Skill 保持上游维护，仅在项目依赖说明记录实际来源版本。

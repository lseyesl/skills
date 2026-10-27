# 风格目录迁移

## 新入口与路径

现在只有一个风格 Skill 入口：`blender-styles`。通用 `blender-python-modeling` 保持独立。

| 原位置 | 新位置 |
|---|---|
| `blender-soft-clay/SKILL.md` | `blender-styles/styles/soft-clay/STYLE.md` |
| `blender-handmade-plasticine/SKILL.md` | `blender-styles/styles/handmade-plasticine/STYLE.md` |
| `blender-soft-clay/scripts/` | `blender-styles/scripts/` |
| `blender-soft-clay/references/`、`examples/`、`evals/` | `blender-styles/styles/soft-clay/` 下的同名目录 |
| `blender-handmade-plasticine/references/`、`assets/` | `blender-styles/styles/handmade-plasticine/` 下的同名目录 |

旧风格名称仍可作为用户指定风格的别名，在统一索引中路由；旧独立 Skill 目录和各自的 agent 入口已撤下，没有旧路径执行垫片。外部项目配方需修改导入目录，例如从 `/absolute/skills/blender-soft-clay/scripts` 改为 `/absolute/skills/blender-styles/scripts`。本项目的活动配方已同步；历史报告、归档与 `.blend` 中旧记录保留原始来源，不作为当前执行命令。

## 兼容性与证据

- 共用 Python 文件保留名称、接口、导入关系、默认 owner 和 `soft_clay_*` 数据标签，迁移本身不改变已有场景数据的归属。
- 柔和黏土的历史测试仍注明原执行日期、版本与输出路径。新路径上的迁移复核单独记录，不能把旧日期的成功报告改写为本次运行。
- 手捏橡皮泥仍是待实际小样视觉校准的规范。合并目录、共享工具测试通过，均不改变这个状态。
- `.tmp/` 下的历史运行产物不随风格内容迁移；风格包包含参考、规范、配置和历史摘要，不包含所有生成媒体。

需要在其他安装环境使用时，安装统一目录并让宿主刷新 Skill 列表；不要同时保留旧副本作为额外入口。通用建模文档通过相邻目录链接，迁移时一并维护它们。

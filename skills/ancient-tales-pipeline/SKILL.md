---
name: ancient-tales-pipeline
description: 为 ancient-tales 项目解析并锁定共享 Skill 依赖，安全安装固定版本，以及上传、恢复、校验 HF 制作资产；不执行故事创作或自动批准资源。
---

# 项目依赖与资产

本技能提供可执行的版本与存储操作，不编排制作阶段。调用方交付明确的项目根、操作及命名空间，返回锁文件／回执或完整性结果；故事、镜头、素材方法和批准由调用方制作项目的契约决定。独立使用技能安装功能无需安装 production。

权威源为 `lseyesl/skills`。本机位置用 `--source` 或 `ANCIENT_TALES_SKILLS_SOURCE` 指定，禁止独立修改受管安装副本。外部工具与可选协作关系见源库 `skills.json`；仅必需的本库 Skill 自动加入依赖闭包。

## Skill 锁定与安装

入口是本技能 `scripts/runtime.py`；已有项目可通过自己的 `tools/manage.py` 转发。首次安装示例：

```powershell
python <skill-dir>/scripts/runtime.py skills update --project <project> --source <skills-repo> --skill ancient-tales-production
python <skill-dir>/scripts/runtime.py skills install --project <project> --source <skills-repo>
python <skill-dir>/scripts/runtime.py skills check --project <project>
```

- `update` 只更新锁；`install` 检查本地冲突、暂存全部技能并核对暂存内容后才激活。失败保持旧安装。
- 正式锁读取指定 commit 的 Git blob 字节，不受检出换行或公共源码当前 HEAD 影响。旧锁可显式 update 升级到 schema 2。
- `check` 验证安装、哈希和必需依赖完整性，不要求源库或网络。
- 默认安装到项目 `.agents/skills/`。首次 update 可用 `--install-dir .claude/skills` 选择另一项目目录；不改客户端全局配置。
- 只有显式 `--allow-working-tree` 才锁定未提交开发内容。此类锁标为 `working-tree`，只能依赖完全匹配的本地快照。
- Skill 库的图片、动作库和其他媒体完整保留在自身 Git；Obsidian 也仅使用自身 Git。二者禁止纳入 HF 同步。

## 制作资产

仅在制作仓库存在启用的 `assets.config.json` 时使用，配置与清单的仓库及 bucket 身份必须一致：

```powershell
python <skill-dir>/scripts/runtime.py assets pull --project <project>
python <skill-dir>/scripts/runtime.py assets verify --project <project>
python <skill-dir>/scripts/runtime.py assets index --project <project> --repository-id <repository-id> --bucket <owner/bucket>
python <skill-dir>/scripts/runtime.py assets push --project <project>
python <skill-dir>/scripts/runtime.py git-check --project <project>
```

- `index` 生成 pending；原索引文件缺失时先恢复，不能用重新扫描删除其记录。过滤规则改变也不自动移除原条目。
- 字节未变的已有条目原样保留，包括业务版本、项目身份、批准回执与扩展字段；扫描不重新批准或重命名版本。清单级扩展元数据也保留。
- 需要移除引用时显式 `assets forget --path <relative-path>`；批准或锁定记录另需 `--allow-locked`。forget 只生成待变更清单；push 后才晋升，远端对象和本地文件都不删除。
- push 上传并回读验证后才替换正式锁；移除记录必须有明确 forget 标记。远端对象按内容哈希寻址，新发现条目默认以哈希初始化版本；已有业务版本不重写，approved/locked 文件改变必须新建路径。
- pull 先验证全部远端内容，再安装缺失项，不覆盖本地改动。正式构建先 verify，缺失或损坏立即停止。
- 凭据沿用用户现有 `hf auth`，不得打印 token 或写入仓库；这些命令不表示获得视觉批准。
- `verify` 检查本地路径、大小与 SHA-256；它不验证项目身份语义、生产状态枚举、批准回执或 Gate。调用方须另行核对这些契约，不能将 `ASSETS_VERIFY_OK` 当作制作批准。

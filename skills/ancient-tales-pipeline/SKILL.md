---
name: ancient-tales-pipeline
description: 为 ancient-tales 项目锁定和同步共享 Skill，上传、恢复并校验 Hugging Face bucket 媒体资产；不执行故事创作或自动批准资产。
---

# 项目依赖与资产

权威 Skill 源为 lseyesl/skills。本机位置通过 --source 或 ANCIENT_TALES_SKILLS_SOURCE 指定，不把机器路径当作来源身份。

使用本技能 scripts/runtime.py。项目提供 tools/manage.py 同入口。

```powershell
python scripts/runtime.py skills update --project <project> --source <skills-repo>
python scripts/runtime.py skills install --project <project> --source <skills-repo>
python scripts/runtime.py skills check --project <project> --source <skills-repo>
python scripts/runtime.py assets index --project <project> --repository-id <repository-id>
python scripts/runtime.py assets push --project <project>
python scripts/runtime.py assets pull --project <project>
python scripts/runtime.py assets verify --project <project>
python scripts/runtime.py git-check --project <project>
```

- update 只更新锁，不激活安装；install 检查全部来源及本地冲突后安装。不要手改运行副本。
- locks 保存完整来源 commit 和文件树 SHA-256；working-tree 表示尚未提交的精确本地快照，不能宣称可以只靠 Git 恢复。提交源库后显式 update/install 使之成为 committed。
- Skill 源库包含的媒体依赖完整保留在 Skill Git 中，克隆后直接安装；禁止把 Skill 库或 Obsidian 纳入 HF 资产同步。
- assets index 生成 pending；push 上传后回读校验成功才晋升 assets.lock.json。
- 所有 HF 对象按仓库隔离并以 SHA-256 命名。approved/locked 文件变化必须新建版本路径。
- pull 先验证全部远端文件，再安装缺失文件；不覆盖本地改动。不使用远端删除传播。
- 正式构建前 assets verify；缺失、损坏或身份不符立即停止。缓存不作为长期备份。
- hf-cli 使用用户现有认证，不打印 token、不将凭据写入仓库。

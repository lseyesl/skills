# lseyesl Skills

可复用的 Agent Skill 源码库。每个入口位于 `skills/<name>/SKILL.md`；用途见 [技能索引](index.md)，必需、可选及外部依赖统一声明在 [skills.json](skills.json)。

本库的源码、参考图片、动作库及其他依赖完整保存于 Git，不上传 HF。Obsidian 同样仅使用自己的 Git；HF 工具只适用于明确启用的独立制作仓库。

## 制作流程与通用能力

`ancient-tales-production` 定义专业流程、Gate 和交接，`ancient-tales-pipeline` 提供技能安装及资产索引／传输工具。制作任务从项目配置选择通用 Skill 与后端；独立建模、拆件或图片任务可直接调用对应 Skill。具体调用与返回字段见[技能协作与交付契约](skills/ancient-tales-production/references/技能协作与交付契约.md)。

导演负责镜头决策和专业复审，制片／总控负责阶段推进，项目后端负责装配与渲染。当前提供工作流规范与能力工具，没有自动导演调度器或自动生产契约校验器；文件哈希通过不代表制作批准。

## 安装到项目

需要 Python 3.10+ 和 Git。先把本库克隆到独立的源码目录，而不是把整个仓库嵌套进某个客户端的单个 Skill 目录：

```powershell
git clone https://github.com/lseyesl/skills.git D:/code/skills
python D:/code/skills/skills/ancient-tales-pipeline/scripts/runtime.py skills update --project D:/work/my-project --source D:/code/skills --skill blender-styles
python D:/code/skills/skills/ancient-tales-pipeline/scripts/runtime.py skills install --project D:/work/my-project --source D:/code/skills
python D:/code/skills/skills/ancient-tales-pipeline/scripts/runtime.py skills check --project D:/work/my-project
```

macOS/Linux 使用相应路径和 `python3`。`--skill` 可重复；更新现有锁时可省略，沿用 `requested_skills`。上例自动补齐必需的 `blender-python-modeling`，可选协作 Skill 和外部工具不会自动安装或调用。

默认写入项目 `.agents/skills/<name>/`，保留兄弟 Skill 的相对布局。要使用项目的 `.claude/skills/`，在首次 `update` 增加 `--install-dir .claude/skills`。这两个目录是安装目标；具体客户端的发现方式以该客户端为准。也可以直接打开源码的 `SKILL.md` 按任务加载。

把 `skills.lock.json` 提交到消费项目；将 `.agents/` 或 `.claude/skills/` 及对应 `skills-receipts.json` 加入该项目忽略规则。已有非受管或被手改的安装副本会阻止覆盖。工具不修改客户端全局配置。

## 锁定、升级与旧锁迁移

- `update` 从库的依赖声明解析闭包，只更新项目锁；`install` 才激活依赖。
- 正式锁使用完整 commit 和 Git blob 内容哈希。安装直接提取该 commit，源库 HEAD 可以更新到别的版本，不需要为消费项目切换公共源码目录。LF/CRLF 检出不影响正式锁。
- `check` 仅检查本地安装与锁，不需要源库、网络或 HF 凭据。
- 修改只在源码库进行，验证并提交后，再在消费项目显式 `update`、`install`、`check`。
- 未提交开发快照需要 `update --allow-working-tree`，锁会标为 `working-tree`；此类锁只能从完全匹配的本地工作区恢复，不能声称可从远端 Git 恢复。
- 老锁仍按原工作区字节校验；运行一次新版 `update` 升级到 schema 2，再安装即可获得跨平台、固定 commit 和依赖闭包支持。工具不会自动改写其他项目的锁。

## HF 资产工具

仅当制作项目已配置 `assets.config.json` 时，才使用 [ancient-tales-pipeline](skills/ancient-tales-pipeline/SKILL.md)。`assets index` 发现原索引文件缺失会报错；先 `pull` 恢复，不把本地缺失解释为删除。

需要移除引用时显式使用 `assets forget --path <relative-path>`，已批准记录另加 `--allow-locked`。随后 `push` 验证并晋升待提交清单；远端对象和本地文件均不自动删除。不得在本 Skill 库或 Obsidian 上启用 HF 同步。

## 检查与测试

```powershell
python -m pip install -r requirements-ci.txt
python tools/check.py
```

默认入口检查全部 Skill 的元数据、索引、依赖图和活动文档相对链接，然后分进程运行同步工具、EPUB、皮影图像工具与建模审阅等轻量测试，不生成生产资产或连接 HF。CI 在 Windows/Linux、Python 3.10/3.13 上运行同一入口。

图像拟合测试另有 NumPy/OpenCV 环境，可使用对应 Skill 的 `pyproject.toml`；Blender 实机检查独立运行：

```powershell
python tools/check.py --group blender --blender G:/SteamLibrary/steamapps/common/Blender/blender.exe
```

该检查使用隔离临时场景，技术测试通过不等于视觉批准。历史制作规范位于 `ancient-tales-production/history/`，不参与活动路由。

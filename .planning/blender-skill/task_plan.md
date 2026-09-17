# Blender Skill 任务计划

## 目标

在当前本地 skills 仓库中新增一个可自动触发的 Blender skill，参考用户指定的三个 Blender/Claude 项目，适配已安装的 `mcp-for-blender`，并把 Python 脚本作为创建和修改模型的首选方式。

## 阶段

- [complete] 1. 调研参考仓库与本地 skill 结构
- [complete] 2. 设计 skill 的触发边界、工作流和配套资源
- [complete] 3. 创建 skill 文件并补充必要参考/脚本
- [complete] 4. 验证结构、内容和辅助脚本
- [complete] 5. 汇总交付
- [complete] 6. 审计 Blender 4.x/5.x API 差异并筛选具体制作配方
- [complete] 7. 增加领域参考内容与可执行兼容性验证脚本
- [complete] 8. 在 Blender 4.5.12 实测配方并修复不兼容项
- [complete] 9. 复验 skill 结构、路由和交付内容
- [complete] 10. 设计 AI 参考图分析的能力边界、schema 和多视图一致性策略
- [complete] 11. 实现参考图分析脚本与 skill 路由说明
- [complete] 12. 用 skill-local uv 环境运行合成参考图测试，验证轮廓、比例、方向和矛盾检测
- [complete] 13. 复验 Blender skill 与新增分析流程
- [complete] 14. 设计剩余领域缺口的渐进披露结构与边界
- [complete] 15. 增加游戏资产、角色交付、资产复用、合成与物理模拟参考
- [complete] 16. 扩展 Blender 4.5.12 兼容性烟测并修复不兼容内容
- [complete] 17. 复验全部路由、文档、脚本与离线依赖
- [complete] 18. 设计 concept-multiview-sheet 的触发边界、输出契约与 ImageGen 工作流
- [complete] 19. 初始化并实现新 Skill、参考文档和 Blender 衔接路由
- [complete] 20. 验证新 Skill 的结构、内链和典型行为边界
- [complete] 21. 将 concept-multiview-sheet 升级为对称五视图/非对称六视图输出并复验

## 约束与决策

- skill 位于当前仓库 `skills/` 下，作为本地、可版本控制的 skill。
- MCP 使用已安装的 `ahujasid/mcp-for-blender`；不重复安装或修改 MCP。
- 建模和场景修改优先生成可复用、幂等、可审计的 Blender Python 脚本。
- 外部网页内容只记录到 `findings.md`，不写入本计划。
- 兼容性以本机 Blender 4.5.12 LTS 为已验证基线；未实测的 4.x/5.x 版本不得笼统宣称兼容。
- 参考项目中的 Blender 5.x 示例只提炼设计思路，所有进入本 skill 的 API 模式必须经 4.5.12 实测或运行时探测保护。
- 参考图分析只输出归一化比例、轮廓特征、视角线索和不确定性；没有尺度锚点时不得宣称恢复真实尺寸。
- AI 多视图必须先做一致性检查；矛盾视图不得被静默平均成一个“确定”模型。
- OpenCV/NumPy 由 skill 内 `pyproject.toml` 与 `uv.lock` 管理；宿主工具统一经 `uv run --project <skill-dir>` 执行，`.venv/` 必须被忽略。
- 单视图补全三视图属于生成式设计推断，独立为 `concept-multiview-sheet`；不得把隐藏结构描述为从原图测得。
- `concept-multiview-sheet` 默认使用内置 ImageGen；只有用户明确选择 CLI/API 路径时才采用需要 API key 的回退模式。

## 错误记录

| 错误 | 尝试次数 | 处理 |
|---|---:|---|
| 单个 `apply_patch` 同时删除并新增同一路径失败 | 1 | 拆为先删除、后新增两个补丁 |
| 官方验证器缺少 PyYAML | 1 | 使用 `uv --with pyyaml` 的临时依赖环境 |
| `uv` 默认缓存目录被沙箱拒绝 | 1 | 将 `UV_CACHE_DIR` 指向 `/private/tmp` |
| 沙箱内无法访问 PyPI | 1 | 经用户批准后联网获取临时验证依赖 |
| 本机 Ruby/Psych 不支持 `safe_load_file` | 1 | 改用兼容的 `safe_load(File.read(...))` |
| Blender MCP add-on 当前未运行，`get_addon_status` 无法连接 | 1 | 记录为实时集成未验证；改用 Blender 4.5.12 factory-startup 后台实测全部配方 API |
| 临时 PyYAML 缓存被清理，官方验证器再次尝试联网失败 | 1 | 使用此前获批的临时依赖联网规则重跑，不写入项目依赖 |
| 临时下载 OpenCV/NumPy 的权限未获批准 | 1 | 不重试、不安装全局依赖；搜索本机已有环境，并保留可复现合成测试命令 |
| 本机未找到现成 OpenCV Python 环境 | 1 | 完成语法/静态检查；行为测试标记为依赖可用后执行，不虚报通过 |
| 最终 uv 回归测试再次访问默认缓存目录被沙箱拒绝 | 1 | 设置 `UV_CACHE_DIR=/private/tmp/blender-skill-uv-cache` 后离线复跑通过 |
| 同一补丁对新 Skill 的 `SKILL.md` 同时执行删除和新增被拒绝 | 1 | 改为直接更新初始化器生成的文件，并用独立补丁新增 references |
| 行为边界静态检查要求入口显式出现大写 Evidence 标签，入口只有小写表述 | 1 | 在 Boundaries 中明确加入 `Observed`、`Inferred`、`Unknown` 三个标签 |

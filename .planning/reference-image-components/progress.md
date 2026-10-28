# 进度

## 2026-10-28
- 阅读用户指定的皮影拆件 Skill 与 planning-with-files-zh。
- 检查项目 .planning，未找到同义任务目录，采用 reference-image-components。
- 查看 git diff --stat，发现已有 .gitignore 改动并保留。
- 完成拆件方法分析与七步执行计划。
- 交付范围：计划；图像分析与生产未执行，需以实际参考图为输入。
- 未运行图像测试：本轮没有参考图或生成资产。

## 2026-10-28 用户授权创建与测试
- 在 skills/shadow-puppet-part-splitter 创建 SKILL.md、UI 元数据、数据与修补参考、Pillow 工具、12 项单元测试、4 个行为验收用例。
- 更新项目 README 的技能索引。
- 系统 Python 缺少 Pillow，创建 .tmp/puppet-test-venv 并安装 Pillow、PyYAML。
- 首轮 11 项测试通过；修复 getdata 弃用提示，补充自定义路径资产覆盖保护后复跑 12 项全部通过。
- Skill quick_validate 通过，合成 manifest CLI check 通过，git diff --check 通过。
- 输出 output/shadow-puppet-part-splitter-smoke：合成源图、独立部件、补全区 mask、manifest、原姿态及角度预览、对照图与 qa_report.md。
- 使用图片查看工具检查角度对照图，连接与透明孔洞保持。
- 未执行真实图像分割/生成补全测试、独立模型行为评估或特定引擎导入验收；报告已说明。

## 2026-10-28 生成人物并测试
- 用户要求生成真实皮影人物图片并运行新 Skill；这里的“真实”按传统皮影实物质感处理，来源仍是 AI 生成，不宣称实物摄影或历史藏品。
- 已调用内置 imagegen 生成右向侧身、长袍、近侧手臂外伸的传统皮影人物，要求透明背景及镂空。
- 测试资产目录固定为 output/shadow-puppet-character-test，不覆盖上一轮几何 smoke test。
- 已生成原图和去臂躯干 donor，保存完整提示词与来源。目视制定遮罩并用确定性脚本导出原图像素，输出 5 部件和 4 个推测 mask。
- 经两次独立层审查修正误留袖边与误划裙摆；原始可见层回组在浅底合成后完全一致，补片回组 RGB 平均绝对误差 0.005669/255，0 个源透明像素被填住。
- 输出并查看拆件、关节、推测高亮、并排回组、23 姿态对照及肘部局部图。
- 肘 -15/-30 和含负肘角的组合出现宽袖三角开口，记录为视觉失败。最终 manifest 肘范围为 0..30，stress manifest 保留原范围；已测试非法负角输入被拒绝。
- 12 项单元测试复跑通过，Skill quick_validate 通过，实图 manifest check 通过。
- QA 报告保存到 output/shadow-puppet-character-test/qa_report.md。交付限定范围预览资产，不声称对称 ±30° 全范围无缝或引擎导入已验证。

## 2026-10-28 Blender 工作流改版
- 用户确认按动作优先、Blender 绑定试动、暴露补全闭环修改。
- 更新 Skill、UI 元数据、manifest 参考、新增 blender-workflow.md、motion_plan 与 Blender 行为验收用例。
- 新增 scripts/blender_rig.py，支持正式验收范围和试验目标范围两种模式，单骨刚性绑定、局部限位、纹理打包、姿态渲染与数值验证。
- MCP 未连接，改用独立后台 Blender 4.5.12 LTS，保存至 output/shadow-puppet-blender-test。没有操作用户实时场景。
- 改进骨尾朝子关节，显式对齐局部 Z。目视发现透明排序错误后改为对象位置承担深度，最终输出 accepted-v3 与 trial-v3。
- 每种模式 17 个求值检查通过：9 姿态与 8 越界输入。最大顶点误差 2.568e-6 世界单位；单骨权重和刚性边长保持通过。
- 正式 v3 重开检查通过：5 部件、5 骨骼、5 打包纹理、Pose Mode、轴向和未归属任务的默认 Scene/Cube 保留。
- 目视查看 v3 原姿态、骨架及正式/试验动作对照；腕部铆钉遮挡修正。负肘角宽袖开缝仍是未满足动作目标，正式范围0..30，试验范围-30..30保留。
- 模块账本：5 匹配、1 受限、0 缺失，feature-complete 结构检查通过但最终门禁 false。
- 12 项旧工具测试及 Skill 结构校验通过。QA 保存到 output/shadow-puppet-blender-test/qa_report.md。

## 通用工具固化完成（2026-10-28）
- 完成共享数据/变换核心与统一命令入口，静态素材/局部骨架/完整已有角色/独立序列均可按需使用。
- 完成遮罩裁剪、已知点配准、保护区合成、回组与预览、连接/边界测量、Blender IO 与重开、媒体与显式清单打包（可选 manifest 可迁移引用检查）。
- 编排器记录耗时、哈希缓存、成功续跑、部分产物和依赖失败；损坏 manifest 或步骤配置不会取消独立步骤。
- 24 项单元测试、真实 Blender 冒烟与猪八戒样本回归、实际媒体编码、示例首次/缓存运行、Skill 结构与 diff 检查通过。
- 修改保存在工作区；没有在本轮提交或推送。保留已有其他任务文件与修改。

# 发现

- 仓库相关技能：blender-python-modeling（通用 bpy/MCP 工作流）、continuous-action（A.blend 驱动的 2D 动作参考）、concept-multiview-sheet（单图推断多视图）。
- 通用技能已有材质、灯光、动画、兼容与验证文档；新技能应只增加黏土风参数与执行工具，不复制通用建模/绑定/参考图分析体系。
- 已有 Blender skill 提倡稳定所有权、避免清空场景、使用数据 API、RNA/节点插槽运行时检查。测试基线声明为 4.5.12，不能直接宣称所有版本验证。
- Blender 可执行文件位于 /Applications/Blender.app/Contents/MacOS/Blender，另有 /usr/local/bin/blender。
- 初始已有修改：.gitignore；未跟踪 .planning/continuous-action-fbx、.planning/fox-blender-model、assets、scripts。均非本任务。
- 本机两个 Blender 路径均为 4.5.12 LTS。没有第二个版本可实测，其他版本仅声明能力探测，不能宣称执行通过。
- 通用脚本包含所有权模板、兼容烟测和参考图分析；没有通用黏土 shader、灯光或渲染配置模块可直接导入。采用独立实现最小工具，引用已有通用参考。
- 核心风格：粗糙度 0.82、低介电高光、有限色噪声、微小 bump；不使用 Subsurface 伪造柔光，不使用 soft-body 物理。

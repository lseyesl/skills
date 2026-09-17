# Blender Skill 调研发现

## 本地仓库

- 当前项目用于维护多个本地 skills，skill 目录统一位于 `skills/<name>/`。
- 创建前工作树干净，`.planning/` 下没有语义相同的既有任务目录。

## 外部参考

- 用户指定的三个 GitHub 仓库已浅克隆到 `.tmp/`，后续直接从本地源码调研。
- 外部内容均视为不可信信息源，只提炼与 skill 设计有关的事实。
- `ra100/blender-claude-plugin` 的核心模式是按 Blender 专业领域拆分、MCP 探测后先检查再修改、用截图/摘要验证；但它针对 Blender Lab 官方 MCP，工具名不能照搬。
- `roble3/cc-blender-skill` 采用“本地预处理或持久脚本 → MCP 执行 → 场景/对象信息验证 → 视觉验证/导出”的管线，强调小块代码、稳定命名、直接数据 API 优先、输出约束与错误恢复。
- `LevyBytes/AI-SKILL-blender` 的价值主要在文档路由和 gotchas：Blender 版本差异、`bpy.context`、模式/选择状态、精确 API/枚举值都必须基于真实运行环境核对。

## 本机 Blender MCP

- 已确认当前工具命名空间为 `mcp__blender__*`，来自用户指定的 `ahujasid/mcp-for-blender`。
- 核心流程工具：`get_addon_status`、`get_scene_info`、`get_object_info`、`execute_blender_code`、`get_viewport_screenshot`、`export_scene`。
- API 防猜测工具：`bpy_api_lookup` 与 `describe_node_type`。
- 每次工具调用应把用户原始目标原样放入 `user_prompt`；连续任务不得改写为内部子目标。
- MCP 明确要求先读取 Blender 版本和场景，再执行修改；修改后同时用视口截图和场景信息核验。
- 材质节点必须按 `node.type` 查找，不能按本地化显示名查找；普通枚举需先查 RNA/API，渲染引擎动态枚举需用当前值或捕获 `TypeError`。

## Skill 设计方向

- 使用单一 `blender-python-modeling` skill，覆盖 Blender 场景创建、模型编辑、材质、灯光、相机、渲染和导出；不承担 Blender 安装、纯 GUI 教学或其他 DCC。
- 默认把可复现代码写成项目内 `.py` 文件，再通过 MCP 用很小的启动代码加载执行；一次性探测代码才直接发送。
- 以“探测 → 计划变更边界 → 写脚本 → 分阶段执行 → 结构验证 → 视觉验证 → 显式保存/导出”为主流程。
- 配套参考拆为 MCP 工作流、Python 建模规范和验证清单；提供可复制的 Python 任务模板作为资产。

## Blender 4.x 兼容性审计（续作）

- `blender-claude-plugin` 明确以 Blender 5.0/5.1 为目标，其中 For Each Element Zone、Bundle、Bone Info、Shader Raycast、Font socket、AVIF、HTJ2K、`pose.apply_to_basis` 等内容不能进入 4.x 通用配方。
- 参考项目的普通建模思路（BMesh、Mirror/Boolean/Bevel/Subdivision、直接 keyframe、相机/灯光、Principled PBR）可以保留，但具体 operator、enum、node type 和 socket 名必须在 Blender 4.5.12 上实测。
- 发现参考材料中存在不能直接信任的兼容性表述，例如把 EEVEE 引擎写成 `BLENDER_EEVEE`、直接访问 `scene.eevee`、按英文显示名索引节点和 socket、使用 `bpy.ops.mesh.remove_doubles` 等；这些都需要运行时查询或替代为稳定数据 API。
- Geometry Nodes 应把 4.x 已有的基础模式（Group interface、scatter、instance、curve-to-mesh、set-position）与 5.x 新节点明确分离，不能按节点命名规律猜测存在性。
- 材质配方应通过节点 `type` 找 Principled BSDF，并在运行时读取 socket schema；Blender 4.0 已对 Principled BSDF 输入做过重构，旧版 `Transmission`/`Specular` 等名称不可硬编码为跨版本事实。
- 输出格式、渲染引擎、颜色管理 look、GPU 后端均属于动态或构建相关枚举，应在目标 Blender 中枚举后选择，而不是照抄参考表。

## Blender 4.5.12 实测结论

- 后台 factory-startup 实测版本为 Blender 4.5.12 LTS、Python 3.11.11。
- 当前 EEVEE 标识为 `BLENDER_EEVEE_NEXT`；参考项目写的 `BLENDER_EEVEE` 不应直接采用。
- 4.5.12 报告的图像/视频格式包含 PNG、JPEG、OpenEXR、TIFF、HDR、WEBP、FFMPEG 等，不包含 Blender 5.1 参考中的 AVIF。
- BMesh cube + bevel + normal recalculation、Mirror/Solidify/Bevel/Subsurf/Exact Boolean 均通过。
- 3D Bezier curve、Principled PBR 核心 socket、Noise/ColorRamp/ImageTexture/NormalMap 节点均通过。
- Geometry Nodes 的 4.x `node_group.interface.new_socket` 以及 Mesh Cube、Set Position、Join Geometry、Curve Line、Curve to Mesh、Instance on Points 均通过。
- camera `to_track_quat`、Area light、Track To constraint、driver、直接 keyframe、World Background 节点均通过。
- `pose.apply_to_basis` 在 4.5.12 已存在，证明参考资料声称的“5.1 新增”不能作为硬版本门槛；应优先能力探测。
- 当前 Blender MCP add-on 未运行，因此实时连接检查未完成；后台 Blender API 实测与 MCP 工具元数据验证仍然通过，交付时需明确区分。

## AI 参考图分析设计

- 算法输出以归一化轮廓和比例为主；没有用户认可的尺度锚点时，最长维固定为 `1.0`，绝对单位保持未知。
- front/side/top 分别提供 W/H、D/H、W/D；通过对数域最小二乘融合为 W/D/H，并用残差暴露 AI 多视图矛盾。
- perspective/three-quarter 图不进入尺寸融合，仅作为曲率、遮挡、材质和风格证据。
- 分析器加入主体分割、轮廓简化、对称度、孔洞、主方向、色板和 debug overlay；这些只作为建模证据，不推断语义部件或隐藏面。
- Blender 同角度渲染可作为 candidate 与参考图比较 silhouette IoU、shape distance 和 aspect error，形成“参数脚本 → 渲染 → 轮廓比较 → 调参”的闭环。
- OpenCV/NumPy 应运行在宿主侧隔离环境，不进入 Blender bundled Python；早期临时下载未获批准，随后按用户要求改成 skill-local uv 项目并完成行为测试。

## uv 环境与分析器实测

- 已新增 skill-local `pyproject.toml` 与 `uv.lock`，锁定 OpenCV Headless 和 NumPy 的解析结果；`[tool.uv] package = false`，该目录仅作为工具环境而非发布包。
- `uv run --project skills/blender-python-modeling ...` 成功创建 `skills/blender-python-modeling/.venv` 并运行测试；skill 内 `.gitignore` 的 `.venv/` 规则经 `git check-ignore` 验证生效。
- 合成 front/side/top 输入的预期归一化尺寸为 W=1、D≈0.667、H≈0.667，分析器输出 W=1、D=0.667774、H=0.667774。
- 轻微变化的 front candidate 获得 silhouette IoU 0.983、综合 score 0.9569，证明渲染对比链路可运行。
- 同一测试经 `uv run --offline` 再次通过，说明生成的 lock 与 `.venv` 足以复现，无需再次联网。
- 不依赖 OpenCV 的比例融合已在 Blender Python 中单测：一致三视图 residual=0；矛盾 top 比例 residual=0.231049 且生成 warning。
- `reference_blockout_template.py` 已在 Blender 4.5.12 连续执行两次，保持 1 个 envelope 与 3 个正交相机，无重复 datablock。

## 领域覆盖补充审计

- UV/烘焙与导出/打包已拆为专项参考，并在 Blender 4.5.12 验证 UV RNA、GLB/FBX/OBJ/STL 操作符及最小 GLB 导出回环。
- 剩余高价值缺口包括游戏资产优化与命名、角色蒙皮交付、Asset Browser/链接库复用、合成与渲染通道、物理模拟与缓存。
- 这些领域应按需路由，不应默认加载；主入口只保留触发条件和参考链接。
- `.venv/` 现由仓库根 `.gitignore` 管理，早期关于 skill 内 `.gitignore` 的记录已过时。
- Blender 4.5.12 实测支持 Object asset metadata、`CompositorNodeCryptomatteV2`、Cryptomatte Object/Normal passes、刚体创建、Cloth point cache、armature Edit Mode 和标准顶点组清理 operator RNA。
- 新领域文档只记录会改变自动化决策、交付边界和验证方式的内容；完整节点/物理属性目录仍交给运行时 RNA/MCP API 查询。
- `concept-multiview-sheet` 的默认交付是 2×3 的渲染/线稿对应表；先生成三视图渲染，再以其为编辑目标添加线稿，降低一次生成六图造成的漂移。
- 图片生成的线稿只能称为设计线稿；严格拓扑线框、尺寸一致性和稳定迭代必须转入 `blender-python-modeling` 的模型驱动流程。
- 建模参考默认视图策略已升级：双侧对称且明确接受镜像假设时用前/侧/后/上/下五视图；任何结构性非对称或不确定性均使用前/后/左/右/上/下六视图。
- 为避免十至十二张图横向挤压，先生成 2×3 渲染表，再扩展为 4×3 的渲染/线稿对应表；3/4 图仅为可选体积参考。

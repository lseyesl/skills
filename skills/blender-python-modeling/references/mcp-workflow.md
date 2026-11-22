<a id="local-blender-mcp-workflow"></a>

# 本地 Blender MCP 工作流程

此技能针对已安装的 `ahujasid/mcp-for-blender`工具命名空间。工具的可用性取决于运行时环境；仅使用当前会话中实际暴露的工具。

对于与后台执行兼容的孤立文件任务，请使用持久任务脚本`blender --background <task-copy.blend> --python-exit-code 1 --python <script.py>`请验证保存的工件和渲染的证据。对于需要使用用户当前场景或视口的操作，请使用实时MCP工作流程。

<a id="missing-mcp-install-the-upstream-integration-then-verify"></a>

## MCP 缺失时安装上游集成并验证

请使用官方提供的[ahujasid/mcp-for-blender 仓库](https://github.com/ahujasid/mcp-for-blender)。当前软件包为`mcp-for-blender`（以前称为`blender-mcp`）；较旧的正常工作安装无需为了此任务而重新命名。在添加另一份副本之前，请先检查已安装的client/server/add-on。安装分为两部分：AI客户端中的stdio MCP服务器，以及Blender内部的匹配插件。仅安装其中一部分是无法建立连接的。

当此任务需要安装时，请遵循上游设置流程，而不是仅依赖代码进行工作。现有的官方 `uv`：

```bash
uvx mcp-for-blender setup
```

该工具会发现客户端，提供配置选项，安装并启用插件，并备份和保留原有客户端配置。检查实际检测到的目标，只配置任务涉及的客户端。若缺少 uv，先按操作系统对应的[uv 官方安装说明](https://docs.astral.sh/uv/getting-started/installation/)安装。运行下载的 shell 安装脚本前先检查其内容。

手动设置 Codex：

```bash
codex mcp add blender -- uvx mcp-for-blender
uvx mcp-for-blender install-addon
```

对于使用 JSON MCP 配置的客户，请将此条目合并到现有设置中，而不是替换它们：

```json
{"mcpServers":{"blender":{"command":"uvx","args":["mcp-for-blender"]}}}
```

在 Blender 的偏好设置 → 插件中启用 **Interface: MCP for Blender**，然后以普通用户界面模式启动 Blender。默认情况下，插件会自动启动其套接字服务器；检查 3D 视窗侧栏中的 **MCP for Blender** 选项卡，如果需要，请使用 **启动 MCP 服务器**。匹配 host/port（默认 localhost:9876）；除非明确请求了远程访问，否则保持本地连接。MCP 客户端可能需要完全重启才能发现新注册的工具。不要在同一个桥接设备上启动多个竞争 客户端、服务端 实例。

在受限或受管理的工作空间中，使用任务本地环境以及支持的 `install-addon --addons-dir /absolute/path/scripts/addons` 覆盖功能，而不是覆盖无法访问的全局设置。Blender 必须实际使用该脚本目录 (`BLENDER_USER_SCRIPTS`) 和可编写的任务配置 (`BLENDER_USER_CONFIG`)；在任意目录中复制的文件并非启用的附加组件。当客户端命令的路径与系统路径不同时，应使用绝对路径指向安装好的可执行文件。将 版本、提交 用于任务安装记录。在只读或动态管理的客户端中，新的设置可能不会出现在活动对话中：请报告这一差异。使用官方 MCP SDK 和实际的上游 stdio 服务器的任务所属客户端可以立即验证和执行相同的工具；这并不表示对话中的工具注册表被重新加载了。

安装完成后，调用实际的上游程序`get_addon_status`那么`get_scene_info`，保留用户的原话指令`user_prompt`即使 isError=false，仍要拒绝返回的错误文本。请确认。server/add-on协议兼容性和实际的 Blender 版本，然后执行一个只读的小型探测，并在返回到保存的建模阶段之前检查一个视口图像。当前的上游版本 2.2.9 将视觉检查作为`look`; 较旧的工具集可能会暴露`get_viewport_screenshot`. 发现工具names/signatures无需发明别名。保留脚本和证据，然后继续原任务；仅安装成功并不能代表任务完成。

如果在状态检查过程中，源代码检查构建报告出现`No module named blender_mcp.config`问题，请不要仅通过场景访问来确认连接。在2026-11-13的上游检查中，该模块被遗漏了；安装官方PyPI 2.2.9版本解决了实际问题。对于常规安装，建议使用已发布的版本，并记录所使用的版本。

对于升级，请使用所选服务器版本的配套插件，disable/re-enable或者重启 Blender，然后重新执行握手过程。切勿在包含未保存用户工作的 Blender 中重启，以进行桥接问题的排查。安装后的连接失败遵循以下有限恢复机制；无头 CLI 不是 MCP 自动启动的恢复方法。

<a id="required-order"></a>

## 执行顺序

1. `mcp__blender__get_addon_status` — 确认附加组件的连接、server/add-on兼容性以及`blender_version`。
2. `mcp__blender__get_scene_info` — 在進行任何變更之前，先對現場狀況進行清點。
3. `mcp__blender__get_object_info` — 检查每个将被编辑或用作参考的现有对象。
4. `mcp__blender__bpy_api_lookup`或`mcp__blender__describe_node_type`——解决不确定的API签名、枚举类型、节点属性以及套接字布局问题。
5. `mcp__blender__execute_blender_code` — 运行一个小型探针、一个持续性的脚本启动程序，或者一个受限制的生成阶段。
6. `mcp__blender__get_scene_info`加上目标`get_object_info`——确认结构结果。
7. `mcp__blender__get_viewport_screenshot` — 检查可见结果；修复后重复操作。
8. `mcp__blender__export_scene` — 在请求时导出 GLB/FBX，然后验证返回的路径、字节大小以及导出的对象。

在每次调用工具时，将用户最新的 Blender 请求精确复制到 `user_prompt` 中。除非用户更改请求，否则在多调用操作中保持相同的文本不变。

<a id="execute-persistent-scripts"></a>

## 执行已保存的脚本

建议使用已检入或已保存的 Python 源文件。`execute_blender_code`通常只应接收一个加载器：

```python
from pathlib import Path

p = Path(r"/absolute/path/to/script.py")
ns = {"__name__": "__main__", "__file__": str(p)}
exec(compile(p.read_text(encoding="utf-8"), str(p), "exec"), ns)
```

请使用绝对路径并正确引用它。该脚本包含了所有实质性的逻辑，因此即使在 Blender 重新启动后，结果仍然可以重现。

<a id="stage-large-builds"></a>

## 分阶段构建大型场景

构建、验证和渲染分散在不同的工具调用中时，使用[分阶段执行](staged-execution.md)和 `scripts/stage_guard.py`。新尝试开始前应使旧成功记录失效。同时检查返回文本和 `isError`。若文本中有 `Error executing code`、异常堆栈或通信错误，即使传输层标志为 false，仍须停止依赖该阶段的渲染。要求提供本轮前序阶段的记录和产物哈希。失败后不能沿用旧 `.blend` 或场景中的成功标记。

将昂贵或易出故障的工作分解为有界阶段，例如：

1. 生成的集合和基础几何结构；
2. 修改器和拓扑清理；
3. UVs、材质和纹理；
4. 场景组装、灯光和摄像机；
5. 动画或模拟设置；
6. 渲染和导出。

每个阶段都应该是幂等的，并且通过稳定的名称或任务所有者属性来检索现有数据。不要假设之前在 MCP 中调用的变量仍然存在。返回一个简短的、机器可读的摘要，包含名称、计数、尺寸以及警告信息，而不是打印巨大的顶点数组。

<a id="connection-and-execution-failures"></a>

## 连接与执行故障

- **Blender无法访问：** 在要求用户手动启动 Blender 之前，请遵循以下恢复步骤。仅暴露的 MCP工具可以证明桥梁是可用的，但不能证明 Blender 或其附加服务正在运行。
- **Add-on/server不匹配：** 传递 `get_addon_status`返回的更新指令；不要猜测安装路径。
- **超时问题：**将工作分解为更小的阶段，降低预览分辨率，或将重複性較高的操作移入持久性脚本中。不要重新发送相同的大型调用。
- **上下文或投票失败：** 检查模式、活动对象、选择、区域和区域范围。优先使用直接的数据接口或有限的 `bpy.context.temp_override`。
- **API或枚举错误：** 查询`bpy_api_lookup`; 请不要通过试错法来尝试多种猜测的拼写方式。
- **错误Node/socket：** 在重写节点代码之前，请先使用指定的属性覆盖来查询`describe_node_type`。

<a id="recover-an-unreachable-blender"></a>

### 恢复与 Blender 的连接

1. 检查实际的 Blender 应用程序进程。在 macOS 上，`pgrep -fl Blender` 可以提供帮助，但缩略图扩展或 `mcp-for-blender` 桥接进程并不算数。如果沙箱进程检查被拒绝，请请求执行批准；不要将拒绝视为 Blender 已关闭的证据。
2. 如果 Blender 不存在，且任务需要实时会话，请启动已安装的应用程序。在 macOS 上，如果路径存在，请使用 `open -a /Applications/Blender.app`；否则，先找到已安装的应用程序。遵循环境的批准要求。以普通用户界面模式启动 Blender；在使用 MCP 时，其窗口可能会保持后台运行或最小化状态。不要使用 `blender --background` 或 `blender -b` 无头模式进行 MCP 连接恢复：此附加组件的自动启动回调会跳过该模式，而视口工具需要用户界面上下文。不要将 Blender 作为连接恢复的一部分进行安装或重新配置。
3. 允许启动完成后再重试 `get_addon_status`最多三次，每次间隔大约五秒。如果插件已启用且配置了自动启动功能，则无需手动点击启动按钮。在已知插件重新加载后立即重置连接也可以支持这种有限次的重试。一旦状态成功，请调用 `get_scene_info`以继续任务。
4. 如果 Blender 已经运行，或者重试失败，请检查 MCP 插件是否启用，其服务是否启动，配置的 host/port 是否正确，以及是否有其他 Blender 实例占用该端口。在可行的情况下，检查版本兼容性。保留任何现有的自动启动设置。不要为了重试连接而启动重复的实例、结束进程、重启 运行中的 Blender，或update/reinstall 插件；这些操作可能会影响当前的工作或配置，需要适当的任务范围管理。
5. 如果恢复仍然失败，请报告所观察到的错误以及具体的剩余检查项。请用户启用、开始该附加组件仅在无法使用现有授权工具时才会使用。仅用代码编写的可交付成果在适当且明确标注的情况下仍可以被完成。在没有成功的MCP响应的情况下，切勿声称连接成功。

<a id="optional-asset-services"></a>

## 可选资产服务

MCP可能会使用Poly Haven、Poly Pizza、Sketchfab、Hyper3D或Hunyuan3D工具。这些是可选的建模来源，并非默认建模方式。只有在特定需求时，才应使用这些工具。external/generated这些资产或它们显著改善了所请求的结果。保留licence/attribution在调用付费或按量计费生成服务之前，需先获取元数据并获得用户批准。

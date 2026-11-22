<a id="export-and-asset-packaging"></a>

# 导出与资产打包

导出是一个可复现的构建阶段。保留可编辑的源场景，并在需要进行转换、修改器、三角测量、烘焙动画或纹理重新链接时，准备一个由任务拥有的交付副本，以避免造成破坏。

<a id="define-the-delivery-contract"></a>

## 明确交付要求

在导出之前，请录制：

- 目标应用程序和格式；
- 绝对输出路径和覆盖权限；
- 选定的对象或集合；
- 单位比例、forward/up轴、原点和旋转中心约定；
- 修改器、实例、曲线、几何节点和三角化策略；
- 材料，纹理embedding/copyingUV集、顶点颜色、法线和切线；
- 骨架、形状键、动画片段、FPS以及帧范围要求；
- 多边形、材质、纹理、骨骼、影响、LOD以及碰撞预算。

请不要仅从文件名中推断引擎的约定。Unity、Unreal、WebGLTF、切片工具和与CAD相关的工具在轴、比例、动画、材质和命名方面都有不同的期望。

<a id="choose-the-format"></a>

## 选择格式

| 格式 | 用于 | 重要限制 |
|---|---|---|
| GLB/glTF | 网络，实时PBR，便携静态、动画资源 | 受限材料模型；无法烘焙不支持的过程节点 |
| FBX | DCC/game-engine 交换，尤其是装备和片段 | 轴、叶骨、NLA/action和缩放设置需要进行目标测试 |
| OBJ | 简单的静态网格交换 | 有限层级、动画、材质行为 |
| STL | 3D打印几何结构 | 没有可靠的单元元数据、材质、层次结构、UVs或动画 |
| `.blend` | 可编辑的 Blender 源代码或可重复使用的资产 | 下游的 Blender 版本和外部文件路径非常重要。 |

使用 `mcp__blender__export_scene` 来显示 GLB/FBX 中的所有必要选项。否则，需要通过 MCP 运行一个持久的 `bpy` 导出功能。在记录有效设置之前，不要中途切换机制。

<a id="discover-operators-and-parameters"></a>

## 查询操作器及参数

操作符名称和关键词集合因 Blender 版本及启用的扩展而有所不同。Blender 4.5.12 支持 `bpy.ops.export_scene.gltf`、`bpy.ops.export_scene.fbx`、`bpy.ops.wm.obj_export` 和 `bpy.ops.wm.stl_export`；使用 `export_mesh.stl` 或 `export_scene.obj` 的较旧示例可能不适用。

明确解析和过滤：

```python
def resolve_operator(path):
    namespace, name = path.split(".", 1)
    operator = getattr(getattr(bpy.ops, namespace), name)
    try:
        operator.get_rna_type()
    except KeyError as exc:
        raise RuntimeError(f"export operator unavailable: bpy.ops.{path}") from exc
    return operator


def call_supported(operator, **requested):
    allowed = set(operator.get_rna_type().properties.keys())
    unknown = sorted(set(requested) - allowed)
    if unknown:
        raise RuntimeError(f"unsupported export options: {unknown}; allowed={sorted(allowed)}")
    return operator(**requested)
```

在不受支持的选项上尝试操作比默默放弃一个会改变缩放、材质或动画输出的设置要更安全。如果有可用的MCP `bpy_api_lookup`，请优先使用它。

<a id="stable-selection-and-export-examples"></a>

## 稳定选择对象与导出示例

在有限的选择导出之前，进入对象模式，并限制活动场景和特定任务所属对象。仅取消当前视图层的选择并不能清除其他场景中的选择。优先使用[独立传输适配器](production-workspace.md)在其支持的范围内；对于其他适配器，仍需显式设置当前场景的属性和独立的白名单检查。在实际情况允许时，恢复用户的选择。

与 Blender 4.5 兼容的最低 GLB 调用：

```python
call_supported(
    resolve_operator("export_scene.gltf"),
    filepath=str(output_path),
    export_format="GLB",
    use_selection=True,
    use_active_scene=True,
    export_apply=False,
    export_texcoords=True,
    export_normals=True,
    export_tangents=True,
    export_materials="EXPORT",
    export_animations=True,
    export_yup=True,
    check_existing=True,
)
```

仅当网格具有有效的 UV 映射且目标需要切线空间法线时，才启用切线。选择`export_apply`仅在测试了骨架、形状键、实例和几何节点之后进行。

请不要将这种简单的调用作为完整的交付流程。静态资源应该冻结评估后的副本，以便bevel/subdivision/curve结果被保留。配备特定功能的资产需要预先准备好的副本，以保留皮肤和形状关键点的对应关系；对所有修改器的统一应用并非修复措施。源文件和导入的评估表面必须在声明的样本帧数上保持一致。`asset_delivery.py`实现孤立的恒定 PBRstatic/object-animation/linear-skin在某些情况下，软件拒绝处理不支持的图表、约束和形状键；纹理更丰富且角色更丰富的案例仍会进行专门的审核。

典型的 FBX 设置包括 `use_selection=True`、 `axis_forward="-Z"`、 `axis_up="Y"`、 `apply_unit_scale=True`、 `use_mesh_modifiers=True`，以及明确的 animation/NLA 选项。这些是常见的起始值，并非通用的引擎预设。OBJ 使用 `wm.obj_export` 与 `export_selected_objects`；STL 使用 `wm.stl_export` 与 `export_selected_objects`，并可选地使用 `use_scene_unit`。在传递这些设置之前，请先检查运行时的 RNA 参数。

<a id="prepare-delivery-geometry"></a>

## 准备交付用几何

请保持对象的完整性。在需要的时候，将其作为一个独立的任务所属的导出集合进行处理。

- 仅当目标无法处理 曲线、文本 时，才进行转换；
- 仅在需要时才创建实例，并记录生成的三角形数量；
- 请仔细评估 Geometry Nodes 和修饰器的作用；
- 在已知阶段进行三角化，以确保烘焙后的切线法线和导出的拓扑结构一致；
- 仅在目标合同要求时应用转换；
- 移除隐藏的辅助工具、切割器、摄像机、灯光以及仅用于预览的数据，除非有特别请求；
- 验证法线、材质槽、UV层、顶点颜色、起点和边界。

对于游戏资源，在合同中包含特定目标的LOD和碰撞规则。从已批准的来源生成LOD，保留轮廓和UV/material兼容性，并验证每个计算出的三角形数量。碰撞网格应简单，在需要的地方是封闭的，名称应正确对应目标，并且除非目标另有要求，否则不应包含在渲染几何体中。

<a id="textures-and-external-files"></a>

## 贴图与外部文件

请选择一种包装模式并报告它：

- GLB：在请求时，将支持的图片嵌入到二进制文件中；
- glTF分离：保持`.gltf`、`.bin`以及纹理路径的完整性，使其具有可移植性；
- FBX：仅当消费者支持所选模式时，才复制或嵌入纹理；
- `.blend`：将路径设置为相对路径，或者显式打包资源，而不会意外地修改用户的源文件。

检查 `bpy.data.images`中缺失的文件、generated/dirty图像、打包状态、色彩空间、尺寸以及重复的逻辑纹理。在导出之前保存生成或烘焙的图像。不要假设 `bpy.ops.file.pack_all()`会保存脏图像或使不支持的过程性材料可移植。

在有用时，在复杂资产旁边生成一个小交付清单：源 Blender 版本、格式、有效的导出选项、轴向、单位、对象名称、计算出的三角形数量、材质、纹理、动画、LOD、碰撞以及已知的限制。

对于游戏级命名、纹理后缀、打包通道约定、LOD、碰撞以及评估预算，请应用[game-assets.md](game-assets.md)。对于变形骨架、皮肤影响、形状键以及根运动，请应用[character-delivery.md](character-delivery.md)。

<a id="save-blend-safely"></a>

## 安全保存 `.blend`

切勿覆盖用户的源文件，除非有明确的请求。解决绝对路径问题，验证父目录，并使用适合任务的“另存为”或“保存副本”功能。保存后，请确认。`bpy.data.filepath`仅当操作旨在更改实时文档路径时，并验证输出文件的大小不为零。

使用 `bpy.data.libraries.write`编写的仅包含任务的依赖包，并不能作为正常用户可打开场景的充分证据。即使其资产数据块存在，该场景仍可能以 empty/default激活状态重新打开。在隔离的进程中，选择目标 scene/camera并保存一个正常的 `.blend`文件，然后在不进行 `--scene`覆盖的情况下重新打开该文件。确认默认的激活场景、模型、打包 references/materials和绑定实际上是可用的；在验证器中选择场景时，不得掩盖错误的打开状态。在整个过程中，保留用户的原始实时场景和源文件。

<a id="round-trip-validation"></a>

## 导出回读验证

文件存在只是第一个检查步骤。需要在一次性空白场景或实际消费者环境中对高风险导出内容进行验证：

1. 记录源对象层次结构、变换、边界、计算出的三角形数量、材质、UV层、armature/bone计数、形状键、动画范围和纹理路径；
2. 导出到新的绝对路径；
3. 确认导出结果、文件扩展名以及非零字节大小；
4. 导入到隔离的场景中或在目标 查看器、引擎 中打开；
5. 比较比例、轴、层次结构、旋转点、阴影、UV、纹理、动画、LOD和碰撞；
6. 截取屏幕截图或渲染结果，并报告偏差情况。

切勿将数据直接返回到用户的工作场景。导入操作符的名称与版本相关，就像导出操作符一样；在运行时确定它们的具体功能。

<a id="static-textured-glb-audit"></a>

### 静态带贴图 GLB 检查

使用 [可执行的审计](../scripts/validate_glb_roundtrip.py)对确切的二进制文件进行传输，以准备好的导出集合为基准。该脚本会在一次性进程中打开源文件，清点其评估过的网格，重置到空的 Blender 场景，然后导入 GLB 文件。

```bash
blender --background --factory-startup --disable-autoexec --python-exit-code 1 \
  --python scripts/validate_glb_roundtrip.py -- prepared.blend COLLECTION final.glb --report roundtrip.json
```

在 Blender 到 glTF 的转换过程中，有一些静态审计检查，包括网格边界、三角形数量、材质分配以及原始 GLB 位置等检查。`(x, y, z) -> (x, z, -y)`，每米一个 Blender 单元。它验证了一个 0–1 的 UV 设置、退化的 UV 三角形，以及未改变的world-position/UV成对。采样重叠是按网格在 384×384 网格上测量的。使用`--allow-uv-overlap`仅适用于在网格中记录的堆栈或镜像。在不同网格之间重复使用纹理与这一政策无关。

支持的材质路径包括原则性常量、直接图像输入以及分离路径。metallic/roughness图像通道。审计功能会对比导入的图像像素、尺寸和色彩空间，并记录每个嵌入图像的哈希值。在审计之前，将不兼容的过程图转换为支持的映射。原始轴检查使用密集的浮点位置访问器。此方案适用于使用这些访问器和精确三角形计数的静态纹理道具。在使用不同的顶点编码或故意简化的预算之前，需对审计功能进行适配。

该 [灯笼重播](../examples/iron-lantern-p0/README.md#p2-isolated-glb-round-trip) 使用与项目特定的开启和座椅探测相同的审计方法对导入的网格进行处理。它仅发布经过验证的候选字节，并在导入后审查渲染结果的同时生成报告。

<a id="export-acceptance-checks"></a>

## 导出验收

- 仅导出了预定对象。
- 世界空间的范围、单位、轴、原点和旋转中心与合同约定一致。
- 评估后的几何形状和三角形数量都在预算范围内。
- 法线、切线、UV集、材质分配以及阿尔法模式都保持不变。
- 纹理可以在另一台机器或目标包中进行处理。
- 在适用的情况下，骨架层次结构、骨骼轴、皮肤权重、形状键和剪辑会保留下来。
- 在任务专属的导出阶段之外，源场景仍然可以编辑且保持不变。
- 已报告导出路径、字节大小、有效设置、Blender版本以及下游测试结果。

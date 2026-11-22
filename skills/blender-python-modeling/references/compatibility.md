<a id="blender-version-compatibility"></a>

# Blender 版本兼容性

<a id="support-statement"></a>

## 支持范围

- **执行环境：** Blender 4.5.12 LTS，Python 3.11.11，运行于macOS系统。
- **其他 Blender 4.x 版本：** 支持功能检测和 API 查询，但并未声称已完全测试。
- **Blender 5.x：** 不要假设来自 5.x 版本参考文档中的示例保持不变。请检测该特性，并在相应的 Blender 版本中验证结果。

在更改配方或安装不同的 Blender 版本后，请在一个一次性会话中运行捆绑的烟雾测试：

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background --factory-startup \
  --python scripts/validate_blender_compat.py
```

调整主机项目的可执行文件和脚本路径。测试会创建临时数据块，验证该技能使用的API，删除这些临时数据块，打印JSON结果，并在需要失败的情况下以非零状态码退出。

<a id="prefer-capabilities-over-version-numbers"></a>

## 按实际功能判断兼容性

回迁版本和长期支持版本使得简单的版本假设变得不可靠。例如，Blender 4.5.12已经暴露了`bpy.ops.pose.apply_to_basis`，尽管一些针对Blender 5.1的材料将其描述为5.1版本中的新功能。

使用以下顺序：

1. 通过 MCP查询 `bpy_api_lookup` 或 `describe_node_type`。
2. 检查 RNA 或使用 `hasattr` 进行 properties/operators.
3. 创建一個隨機的人节点、修改器在一个 scratch 数据块中，以证明其类型存在。
4. 仅在使用 `bpy.app.version`时，确保其行为在已记录的边界处发生了真正的改变。

切勿捕获每一个异常并默默继续运行。缺少必要的功能应该会生成一个明确的错误，明确指出Blender的版本和缺失的API。

<a id="blender-4512-verified-facts"></a>

## 已在 Blender 4.5.12 验证的行为

捆绑的烟雾测试用于验证：

- BMesh立方体创建和面法线重新计算；
- 网格UV层创建、循环UV分配、活动渲染UV以及UVunwrap/packRNA发现；
- 镜像、固化、倒角、细分曲面和精确布尔修改器；
- 3D贝塞尔曲线，包含倒角与填充功能；
- 基于节点类型和核心 PBR 套接字标识符的实用 BSDF 发现方法；
- 噪声、颜色渐变、图像纹理和法线贴图着色器节点；
- 通过 `node_group.interface.new_socket` 访问 Geometry Nodes 组界面；
- 网格立方体、设置位置、连接几何、曲线线、曲线到网格以及基于点的实例节点；
- 使用 `to_track_quat`进行相机定位、区域灯光以及对象关键帧。
- 导出 RNA 发现功能，适用于 glTF/GLB、FBX、OBJ 和 STL 格式；
- 一个真正的单三角形 GLBexport/import使用 UV 数据的往返处理。
- 骨架编辑模式构建、标准化变形权重以及使用“骨架”修改器；
- 对象资产标记、描述、标签和清除；
- 渲染层、去噪、Cryptomatte、文件输出以及复合节点，还包括所需的视图层处理；
- 刚体创建、碰撞形状分配、Cloth修改器创建以及点缓存访问。

观察到的运行时间包括：

- EEVEE引擎：`BLENDER_EEVEE_NEXT`；
- 图像格式：PNG、JPEG、OpenEXR、TIFF、HDR、WEBP、FFMPEG，以及RNA报告的其它格式；
- 测试版本中未包含 AVIF；
- `scene.eevee`、`mesh.remove_doubles`、`mesh.merge_by_distance`和`pose.apply_to_basis`都存在，但仅有存在并不能使其成为首选的跨版本接口。
- 导出操作符包括`export_scene.gltf`、`export_scene.fbx`、`wm.obj_export`和`wm.stl_export`；在运行时才能发现它们的属性，而不是从其他版本的 Blender 中复制设置。

<a id="known-5x-only-or-unsafe-to-assume-features"></a>

## 5.x 专有功能及须现场确认的功能

在与 Blender 4.x 兼容的脚本中，除非运行时查找证明其可用，否则不要使用以下内容：

- 对于 Blender 5.x 中引入的“每个元素”区域和“捆绑”节点；
- Blender 5.1 骨骼信息、着色器射线投射、字体插槽、更新的体积网格和UV节点；
- AVIF输出和HTJ2K OpenEXR编解码器；
- Blender 5.1将合成器功能中的“Strip Info”和“Mask”功能转换为SDF节点；
- Blender 5.x特有的分层操作辅助工具，或已移除的旧版转换运算符；
- 节点插槽名称来源于截图或英文用户界面标签。

<a id="dynamic-values"></a>

## 动态值

请将这些视为运行时数据：

- `scene.render.engine`标识符；
- image/video格式和编解码器枚举；
- 渲染设备后端，例如 CUDA、OptiX、HIP、Metal 或 oneAPI；
- 色彩管理视图的变换和外观；
- 节点类型可用性、插槽标识符以及插槽顺序；
- 操作符参数和修改器枚举项。

首先阅读 RNA/API 元数据。对于动态渲染引擎枚举，保留有效的当前值，或在 `try/except TypeError` 中指定所需的引擎，并从异常中报告接受的标识符。

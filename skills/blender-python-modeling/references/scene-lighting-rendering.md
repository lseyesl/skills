<a id="scene-lighting-and-rendering-recipes"></a>

# 场景、布光与渲染

<a id="camera-composition"></a>

## 相机构图

创建一个具有明确目标的相机，包括镜头、距离和裁剪范围。无需使用视口操作器即可进行瞄准：

```python
from mathutils import Vector

camera.location = (4.0, -4.0, 3.0)
target = Vector((0.0, 0.0, 1.0))
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.lens = 50.0
camera.data.clip_start = 0.01
camera.data.clip_end = 1000.0
scene.camera = camera
```

对于图表、立面图、图标以及尺寸中性的产品视图，使用正交投影。对于自然比例提示，则使用透视投影。对于产品，起始尺寸约为50–85毫米；对于室内设计，使用更宽的镜头，并仔细检查边缘的变形问题。

来自被评估的边界的帧，而非猜测的距离。为阴影、运动和宽高比的变化留出空间。

<a id="three-point-studio-lighting"></a>

## 三点式摄影棚布光

一个实用的基准线：

- 关键词：大范围的光源，距离被摄物体30-60度，是最强的光源；
- 填充物：在相反的一侧，体积更大且强度更弱；
- rim:behind/above分离轮廓；
- 世界：低强度中性环境，不能替代人工照明。

大型光源会产生较柔和的阴影。根据被摄物的大小来调整光源的大小。以能量比例作为参考，然后判断渲染出的图像效果；相同的瓦特值在不同场景规模和曝光条件下会有不同的表现。

对于白天场景，使用太阳作为方向，使用高动态范围图像或天空作为环境。对于风格化的作品，先构建价值结构，然后再添加色彩对比。

<a id="world-nodes"></a>

## 世界环境节点

按类型检索世界节点：

```python
world = scene.world or bpy.data.worlds.new("WORLD_task")
scene.world = world
world.use_nodes = True
background = next(node for node in world.node_tree.nodes if node.type == "BACKGROUND")
socket_by_identifier(background, "Color").default_value = (0.03, 0.03, 0.03, 1.0)
socket_by_identifier(background, "Strength").default_value = 0.3
```

使用材料参考中的`socket_by_identifier`辅助工具。在在其他 Blender 版本上索引世界套接字之前，使用`describe_node_type`检查该节点。

<a id="render-engine-selection"></a>

## 渲染引擎选择

渲染引擎标识符是动态变化的。Blender 4.5.12版本的报告为`BLENDER_EEVEE_NEXT`；请不要复制来自较旧版本或面向Blender 5的示例中的`BLENDER_EEVEE`内容。

保留当前有效的引擎，除非交付物需要其他引擎。在切换时，在`try/except TypeError`内进行分配，报告已接受的值，并验证结果：

```python
try:
    scene.render.engine = desired_engine
except TypeError as exc:
    raise RuntimeError(
        f"Render engine {desired_engine!r} is unavailable in {bpy.app.version_string}: {exc}"
    ) from exc
```

使用 EEVEE 进行快速迭代、风格化处理，并拥有许多实时预览效果。当需要精确的间接照明、折射效果、对焦痕敏感的玻璃材质或最终的光影真实感时，请使用 Cycles。不要通过硬编码的枚举值来配置 GPU 后端；检查可用的设备，并保留用户的设备选择，除非任务明确要求改变这些设置。

<a id="output-settings"></a>

## 输出设置

明确设置分辨率、帧范围、FPS、输出路径和格式。在赋值之前，从RNA枚举有效的文件格式：

```python
settings = scene.render.image_settings
valid = {
    item.identifier
    for item in settings.bl_rna.properties["file_format"].enum_items
}
if requested_format not in valid:
    raise ValueError(f"unsupported format {requested_format}; valid={sorted(valid)}")
settings.file_format = requested_format
```

Blender 4.5.12 不报告 AVIF 格式，而 Blender 5.1 可能会报告。测试的基础格式包括 PNG、JPEG、OpenEXR、TIFF、HDR、WEBP 和 FFMPEG。

对于静态图片，使用 PNG 进行无损传输，使用 OpenEXR 进行compositing/high动态范围。对于动画来说，如果渲染过程昂贵或需要重新启动，建议使用图像序列，然后单独对视频进行编码。

<a id="colour-management"></a>

## 色彩管理

不要硬编码颜色管理的样式。在正在运行的 OCIO 配置中列出有效的视图变换和样式。除非用户要求更改样式，否则保留当前的设置。在通过任意方式放大每个光源来进行补偿之前，先调整曝光。

<a id="render-validation"></a>

## 渲染验证

在最终渲染之前：

- 确认当前使用的相机和屏幕比例；
- 检查near/far裁剪和主题边界；
- 以较低的分辨率渲染低采样预览；
- 在选定的渲染引擎中检查材质，而不仅仅是实体视窗模式；
- 检查高光、阴影细节、噪声、透明度、位移以及颜色变换；
- 在需要进行滤波、去噪、掩模处理或后处理时，应用 [compositing-and-passes.md](compositing-and-passes.md) 并验证最终的 Composite/File 输出结果，而不仅仅是原始的渲染结果。
- 确认输出路径不会覆盖无关文件。

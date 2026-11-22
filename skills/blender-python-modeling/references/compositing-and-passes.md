<a id="compositing-and-render-passes"></a>

# 合成与渲染通道

仅在对交付成果进行去噪、分级、遮罩、输出、去眩光、关键帧处理或其他后处理操作时，才构建合成图。对于高价值的交付成果，应保持原始渲染数据；在单个扁平化图像中进行破坏性处理会限制后续修正。

<a id="plan-passes-before-rendering"></a>

## 渲染前规划通道

从实际的复合或下游工作流程中选择通道：

- 结合用于美妆形象的；
- 去噪Normal/Albedo用于 Cycles 去噪；
- Z或Mist用于深度效果，已验证相机裁剪和数值范围；
- 仅在使用时设置正常、位置、向量、UV或对象索引；
- Diffuse/Glossy/Transmission/Emission 用于重新照明或调色的组件；
- 用于坚固面部的Cryptomatte Object/Material/Asset。

每个渲染步骤都会增加内存占用、文件大小以及渲染时间。不要出于防御目的而启用所有渲染步骤。

<a id="script-a-stable-compositor-tree"></a>

## 用脚本构建稳定的合成节点树

使用精确节点`bl_idname`在运行时获取值和检索套接字identifier/name在确认节点架构之后：

```python
scene.use_nodes = True
tree = scene.node_tree
nodes = tree.nodes
links = tree.links

render_layers = nodes.new("CompositorNodeRLayers")
denoise = nodes.new("CompositorNodeDenoise")
composite = nodes.new("CompositorNodeComposite")

links.new(render_layers.outputs["Image"], denoise.inputs["Image"])
links.new(denoise.outputs["Image"], composite.inputs["Image"])
```

该示例未包含去噪Normal/Albedo链接，因为这些功能在启用之前需要先确认其套接字。Blender节点的套接字和合成器的执行方式在版本更新中有所变化；请使用`describe_node_type`进行查询，或者检查所创建的节点，而不是盲目依赖Blender 5.x版本的套接字。

为任务所属节点赋予稳定的名称和框架。在编辑现有的合成器时，保留无所有权的节点，并将其连接到所需分支，而不是清除整个树结构。

<a id="file-outputs-and-colour"></a>

## 文件输出与色彩

- 对于文件输出节点，请使用绝对基路径和确定性的槽名称。
- 选择 PNG/TIFF 用于显示相关图像，而使用 OpenEXR 进行 scene-linear/high-dynamic-range 或多通道传输。
- 在需要保持文件同步的情况下，建议使用多层 OpenEXR；同时，需要说明压缩方式和位深。
- 请勿重复应用显示变换。明确输出是场景线性还是视图变换，或者是否适用于色彩管理应用。
- 对于动画，使用带有帧编号的序列；不要仅依赖视频容器作为唯一的主渲染工具。

<a id="cryptomatte-and-masks"></a>

## Cryptomatte 与遮罩

在创建 Cryptomatte 节点之前，启用匹配的视图层 Cryptomatte 通道。在需要下游选择时，保留足够的 EXR 中的清单数据。对重叠的透明、运动模糊、实例化以及 头发、体积 元素进行掩模验证；可见的对象并不保证具有有用的遮罩效果。

仅在使用 ID 掩码时，如果其整数分配和抗锯齿限制是可以接受的，才应使用 ID 掩码。不要默默地用对象索引替代 Cryptomatte。

<a id="denoising-and-grading"></a>

## 降噪与调色

- 使用兼容的引导处理对美丽路径进行去噪，并检查精细纹理、头发、反射、透明度以及运动效果。
- 去噪后的等级，除非所选工作流程另有要求。
- 保持曝光和白平衡设置与场景色彩管理的一致性。
- 仅出于明确的艺术意图才使用夹具或眩光效果；它们可能会隐藏萤火虫效果或破坏高光信息。

<a id="composite-validation"></a>

## 合成验证

- 使用實際的引擎和視圖層渲染一個代表性的帧。
- 确认所需的插槽已填充，文件输出已写入，并且paths/extensions匹配设置。
- 检查原始合并后的结果，每个必需的步骤，哑光边缘，去噪后的输出以及最终的复合体。
- 对于动画，需要选取运动量较大且透明的帧并进行验证。Vector/Z/Mist时间行为。
- 确认 无界面、后台 渲染生成的文件与交互式会话生成的文件一致。

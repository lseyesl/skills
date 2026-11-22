<a id="soft-low-poly-modeling"></a>

# 柔和低多边形建模

<a id="art-direction-contract"></a>

## 美术风格要求

在计数面数之前，请根据批准的设计测量轮廓和部件比例。低多边形描述的是经济型几何结构，并非自动实现平坦着色。一个具有100-1000个基面的圆形可读形状，对于小型道具来说是一个有用的起点；配置的QA预算默认为每个网格有5000个**基面和评估面**。需要明确设置项目预算；细分和倒角会计入评估的复杂性。

使用少数几个大型、易于识别的造型，并设计成具有适度不对称性的结构。避免过于尖锐的棱角和不必要的密集细节。在微缩场景中，次要细节在输出分辨率下仍应清晰可见，且不应与轮廓相冲突。在资源清单中保留 头部、身体、肢体长度、道具厚度和位置等规范。统一的全局比例应保持比例协调；改变某个部分的尺寸时，需要从多个角度进行复核。

<a id="geometry-recipe"></a>

## 几何制作方法

1. 用立方体、低分段UV球体、icospheres、圆锥或曲线来划分区域。使用`bmesh`或数据API按照指定的尺寸构建顶点。
2. 起始倒角宽度为最小相关尺寸的3-8%，分为2-3个分段，并限制角度。小于像素大小的倒角通常没有实际效果。在狭窄的轮廓中检查overlap/clamping，不要自动对所有的变形边缘进行倒角处理。
3. 在圆形有机体上使用光滑多边形，在宽阔的平面板上使用平面多边形。按多边形进行混合。`use_smooth`检查最终得到的倒角堆叠上的法线。当有意需要时，平面阴影的ICOSphere可以保留面。
4. 重新计算新构建的拥有权网格的法线。验证零面积面、断开的顶点以及 negative/zero 变换。不要盲目修复或对现有资产应用修改器。
5. 检查正交正面、侧面、背面以及拍摄相机。在添加纹理细节之前，先完善轮廓。

```python
# An explicitly authorized mesh, not all objects in the scene.
for face in mesh.polygons:
    face.use_smooth = face.index in organic_face_indices
bevel = obj.modifiers.new("asset_bevel", "BEVEL")
bevel.width, bevel.segments = intended_width, 2
bevel.limit_method = "ANGLE"
```

请不要依赖旧的 `mesh.use_auto_smooth` API。通过角度进行平滑处理、自定义法线以及加权法线在不同 Blender 版本中有所不同；请检查其功能并在渲染中验证它们。捆绑的示例使用了可移植的多边形平滑处理和倒角处理，而无需使用这些 API。

<a id="deforming-and-modular-assets"></a>

## 可变形资产与模块化资产

- 在弯曲关节处保持循环，拥有足够的纵向段以实现变形，并且保持整洁的四边形流动结构是有帮助的。刚性低多边形部件可以使用 object/bone 父子关系来替代皮肤化处理。
- 在设置参数之前，先简化一下。Decimate/remesh在绑定之后，可能会使权重、形状键、UV以及依赖顶点索引的效果失效。切勿使用通用的简化方式来破坏性地简化已绑定的网格。
- 保持基础网格、骨骼、配件部件和材质槽的模块化设计。对于相同的刚性道具，优先使用实例；在每次修改实例网格之前，将数据进行单用户处理。
- 存储真实尺寸或标准化比例及其不确定性。在绑定之前，冻结枢轴和静止变换；不要对已经设置了变换的模型应用变换来“固定”程序化纹理比例。
- 使用现有技能库工作流程，在资源浏览器中标记已批准的资源。无需遵循特定的角色、故事或场景命名规范。

用于构建、绑定、导出和再利用 [一般建模规则](../../../../blender-python-modeling/references/python-modeling.md)、 [建模配方](../../../../blender-python-modeling/references/modeling-recipes.md)、 [字符传输](../../../../blender-python-modeling/references/character-delivery.md) 和 [资源库](../../../../blender-python-modeling/references/asset-libraries.md)。此参考文档提供了样式选择，而不是第二个建模框架。

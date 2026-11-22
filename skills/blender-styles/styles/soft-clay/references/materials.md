<a id="clay-shader-and-palette"></a>

# 黏土着色与配色

`scripts/create_clay_material.py`为每种命名颜色创建相同的程序节点拓扑结构。它不会分配插槽；项目配方会明确选择授权对象和插槽。

| 参数 | 默认设置 | 解释/解读 |
|---|---:|---|
| 粗糙度 | 0.82 | 哑光介电响应；适用范围 0.7–0.95 |
| 镜面反射 | 0.22 | 低非零介电亮点（镜面反射指数/传统镜面反射） |
| color_variation | 0.035 | 在场景线性基础RGB上进行的乘法dark/light端点运算 |
| color_scale | 3 | 每参考单位的宽噪声频率 |
| micro_scale | 110 | 每个参考单元的精细凹凸频率 |
| bump_strength | 0.12 | 受限法向扰动 |
| bump_distance | 0.003 | 相对混合单元凹凸距离，乘以场景比例 |

金属效果为0，反射率为1.45，不需要真正的位移或次表面散射效果。大面积的灯光能够产生柔和的响应效果。仅使用粗糙度并不能消除高光效果；光源区域、镜面程度和曝光度是相互影响的。

<a id="node-topology"></a>

## 节点连接结构

```text
纹理坐标对象 → 宽噪声函数 → 颜色渐变 → 基础颜色
纹理坐标对象 → 细噪声函数 → 凹凸高度 → 基于原理的法线
Principled.BSDF → 材质输出.表面
```

噪声比例被除以`scale`; 凹凸距离乘以`scale`. 这保留了几何坐标时的大致外观灯光、相机布局按照相同的比例进行缩放。在确保安全的情况下，几何图形应以预期的局部尺寸构建，并且对象的比例应保持不变。任意未应用的对象缩放会加剧对象坐标的噪声；因此，在样式处理过程中不得应用骨骼变换来解决这个问题。

物体空间坐标会随刚性变换移动，但网格变形时，纹理可能在表面滑动。对需要蒙皮的生产角色，使用基于稳定 UV 或静止位置的着色器，或先烘焙程序化纹理。随附工具提供刚性资产和预览基线；角色变形时仍须核验贴图的稳定性。见[UV 与贴图烘焙](../../../../blender-python-modeling/references/uv-and-texture-baking.md)。

<a id="colors-and-assignment"></a>

## 颜色与分配

Hex颜色被视为sRGB颜色，并转换为场景线性RGB值。数值RGB(A)列表在[0,1]范围内已经是场景线性值；alpha值必须为1。替换`palette`配置会替换整个颜色映射，使得用户定义的颜色名称适用于任何项目。被移除的颜色不会自动从Blender中删除：它们仍可被现有资源使用。

```python
palette = create_palette(scene, profile, owner="shot-style")
material = palette[chosen_palette_key]
# Append a new slot or replace a specific authorized slot; do not clear arbitrary slots.
obj.data.materials.append(material)
```

在多个镜头中使用相同的调色板和节点配方。根据实际的视图变换来评判色调，并输出照明效果，而不是纯视觉效果。如果粗糙的噪声使得陶土看起来像石头，或者在动画过程中产生凹凸效果，请降低variation/strength/frequency值，并在最终分辨率下重新渲染。凹凸效果应该能够丰富表面，而不改变轮廓。

<a id="ownership-and-compatibility"></a>

## 归属与兼容性

拥有的材质在重新运行时通过标签进行复用，其节点会确定性地重建。编辑带有标签的材质会有意地更新其所有用户；可以通过不同的所有者来复制该材质，以实现不同的效果。工具永远不会采用同名但未被拥有的材质。节点接口是通过运行时标识符来检索的；缺少必要的接口会导致版本特定的错误。着色器图在测试版本中既与 EEVEE 兼容，也与 Cycles 兼容；对于其他引擎的过程导出可能需要进行烘焙处理。

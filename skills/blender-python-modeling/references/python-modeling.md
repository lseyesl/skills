<a id="blender-python-modeling-rules"></a>

# Blender Python 建模规范

<a id="script-shape"></a>

## 脚本结构

使用稳定的任务标识符，并确保生成的数据明确属于该任务。将脚本拆分为多个函数，并以简洁的方式结束。`main()`:

```python
def main():
    remove_previous_generated_data()
    build_geometry()
    build_materials()
    assemble_scene()
    validate_result()

if __name__ == "__main__":
    main()
```

重新运行脚本应该会得到相同的结果。使用自定义的“owner”属性来标记对象，并仅删除匹配的生成对象。不要在用户的场景中将`bpy.ops.object.select_all(...); bpy.ops.object.delete()`用作重置逻辑。

为了创建，首先使用与任务相关的空白场景。[production_workspace](production-workspace.md);avoid/cull在建模之前，该新任务场景中的启动对象。不要复制工厂对象。Cube/Camera/Light进入该模式。编辑模式明确针对现有场景，并不会清除该场景。保留粗粒度快照、辅助工具和导出几何图形，它们分别存储在不同的角色集合中；只有被声明的输出对象才会进入导出流程。

<a id="data-api-before-operators"></a>

## 优先使用数据 API

建议：

- `bpy.data.meshes.new`、`bmesh`、`mesh.from_pydata`和`foreach_set`用于几何图形；
- `bpy.data.objects.new`和明确的集合链接；
- 直接变换、约束、修改器属性、关键帧以及节点树编辑；
- 评估了测量所需的依赖关系图数据。

仅在使用 Blender 时，当没有合理的数据 API 替代方案时，才使用 `bpy.ops`。在调用操作符之前，请确保设置正确的模式、活动对象、选择和上下文覆盖。在实际情况允许的情况下，恢复任何面向用户的 mode/selection 状态。

对于与后台兼容的脚本，应避免使用仅限视窗的操作和UI区域的假设。

<a id="version-and-api-safety"></a>

## 版本与 API 兼容

- 请阅读来自 `get_addon_status` 的 Blender 实际版本说明；不要针对猜测的发布版本。
- 在使用不确定的运算符参数、RNA属性、枚举或版本敏感的API之前，请先执行`bpy_api_lookup`查询。
- 切勿在未经 RNA 确认的情况下硬编码枚举标识符。`scene.render.engine` 是动态枚举的一个例外：保留有效的当前值，或者在 `try/except TypeError` 内分配所需的值，并处理报告的有效标识符。
- 在索引不熟悉的套接字之前，或者在套接字布局依赖于节点属性时，先执行 `describe_node_type` 查询。
- 仅将功能检测（`hasattr`，RNA检查）用作兼容性边界，而不是用来掩盖真正的错误。

<a id="nodes-and-materials"></a>

## 节点与材质

Blender节点的显示名称可以进行本地化处理。按类型查找节点：

```python
principled = next(
    node for node in material.node_tree.nodes
    if node.type == "BSDF_PRINCIPLED"
)
```

不要依赖 `nodes["Principled BSDF"]`。使用 `material.use_nodes = True`，可以在着色器输入上设置渲染外观；仅使用 `material.diffuse_color` 只能实现视口显示颜色。

为生成的材质赋予任务级名称。重复利用并更新已拥有的材质，而不是每次运行都添加重复项。除非请求明确要求替换，否则保留现有的用户创建的材质槽。

<a id="geometry-scale-and-transforms"></a>

## 几何、尺度与变换

- 采用统一的单位制，通常为米，同时保留 `scene.unit_settings.system = 'METRIC'` 的占位符，无需随意改变已有的场景单位制。
- 以预期的规模构建几何图形。当实际尺寸未提供时，需说明假设条件。
- 建议使用显式矩阵或直接顶点坐标，而不是一系列与上下文相关的变换算子。
- 决定 scale/rotation是否应在过程编辑、骨骼或形状键处理中保持未应用状态。仅在下游交付物需要时才应用变换。
- 对于目标输出，使用足够的曲线和倒角分辨率，但保持预览几何体的经济性。
- 在交付物需要水密几何结构时，重新计算法线、验证网格，并检查非流形边界。

<a id="performance-and-maintainability"></a>

## 性能与维护

- 在可能的情况下，使用 `foreach_set`、 `mesh.from_pydata`、NumPy，或者采用 `bmesh` 操作，而不是逐个元素的 `bpy.ops` 循环。
- 在舞台上缓存常用的场景、集合、视图层以及节点引用。
- 在完成后移除临时拥有的数据块，避免在不同版本中重复积累。
- 显式生成种子随机值，并将重要参数存储在脚本的顶部附近。
- 生成简洁的摘要，包括对象数量、多边形数量、边界、材质名称以及经过的时间。避免打印完整的网格或节点图。

<a id="existing-scene-edits"></a>

## 编辑现有场景

在编辑之前，先对相关的对象名称、类型、变换、父子关系、修改器、材质和集合进行快照记录。只触碰用户请求中的对象。当更改可能导致装备、形状键、模拟、链接数据、库覆盖或现有动画失效时，先检查这些关系并保留它们，除非明确要求进行替换。

# 数据约定 v1.0

`parts_plan.json` 是图像制作前的计划，至少包含源图尺寸、动作需求及候选部件数组；候选项记录 id、中文名、角色归属、拟定控制节点、可见程度、边界/遮罩位置、关节候选、遮挡关系、置信度、补全原因。看不清的坐标为 null 并说明原因，不捏造精确值。计划不能直接当作已完成的 manifest。

## 可执行 manifest

```json
{
  "schema_version": "1.0",
  "coordinate_system": "image-pixels-y-down",
  "source_size": [256, 256],
  "nodes": [
    {"id": "torso", "parent": null, "pivot_global": [100, 100], "rotation_range": [-10, 10]},
    {"id": "forearm_l", "parent": "torso", "pivot_global": [120, 120], "rotation_range": [-30, 30]}
  ],
  "parts": [
    {
      "id": "forearm_l_front",
      "label": "角色左前臂前片",
      "character_id": "character_1",
      "node": "forearm_l",
      "file": "parts/forearm_l_front.png",
      "crop_origin": [110, 110],
      "pixel_size": [40, 70],
      "pivot_local": [10, 10],
      "z_index": 4,
      "inferred": true,
      "inferred_region_mask": "masks/forearm_l_front_inferred.png",
      "notes": "肘根增加隐藏接片，结构为推测"
    }
  ]
}
```

以上只是字段示例，不对应真实图片。路径只能指向交付目录内的实际文件。PNG 必须 RGBA、非空并含透明像素。补全 mask 为灰度 L PNG，尺寸与部件一致，至少有一个非零像素，且不标记完全透明区域。

所有节点锚点是**参考姿态的全局坐标**。无旋转时，PNG 左上角就是 `crop_origin`，`pivot_local = nodes[node].pivot_global - crop_origin`，允许锚点在裁剪边界之外。父节点的静止锚点差即子节点静止位移，无需另行存储重复数据。一个节点可控制多个绘制片，片的 z_index 为全局绘制顺序，要求唯一，避免依赖数组顺序。

在屏幕坐标下，正角度顺时针。工具对每个节点计算：

`T(node) = T(parent) × Translate(pivot_global) × Rotate(angle_delta) × Translate(-pivot_global)`。

根父矩阵为单位矩阵。绘制片参考位置 `crop_origin + local_pixel` 经其节点矩阵变换。参考姿态已烘焙在 PNG 中，因此所有 angle_delta 为 0；不要把原图肢段倾斜角再次当作旋转输入。

此版不含缩放、导出前旋转、重采样坐标或镜像；输出 2x 必须同步变换所有坐标、尺寸及 source_size。运动图用双线性采样，边缘可能出现抗锯齿差异；零角度回组使用整数像素位置，无需重采样。

`rotation_range` 必须含 0，是允许输入的角度范围，尚未视觉验证时须在 QA 中注明“暂定”。元数据合法不代表范围已通过视觉验收。全画布裁剪、半透明皮革叠加效果及运动遮挡切换须另行审查。

动画任务另用 `motion_plan.json` 的 `target_ranges` 保存目标范围和代表姿态，见 [Blender 工作流](blender-workflow.md)。验收失败后缩小 manifest 范围时保留原动作目标及失败证据；Blender 正式绑定与试验绑定分别采用这两种范围。

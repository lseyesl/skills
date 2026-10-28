# 动作优先的 2.5D 骨骼流程

## motion_plan.json

```json
{
  "schema_version": "1.0",
  "angle_convention": "relative-clockwise",
  "target_ranges": {"body": [0,0], "forearm_near": [-30,30]},
  "poses": [
    {"id": "rest", "angles": {}},
    {"id": "elbow_negative", "angles": {"forearm_near": -30}},
    {"id": "elbow_middle", "angles": {"forearm_near": 15}},
    {"id": "elbow_positive", "angles": {"forearm_near": 30}}
  ]
}
```

示例只说明字段，实际 target_ranges 要覆盖全部节点。所有范围包含 0。pose ID 使用文件名安全字符；每个角度落在目标范围内。目标动作是设计意图，不等于已验收能力。计划阶段可记录未知值，执行脚本前须解决到具体数值。

## 导入与刚性绑定

`scripts/blender_rig.py` 读取现有 v1 manifest、独立 PNG 和 motion plan，创建专属新场景。它不分割图片、不自动补全、不保证接缝质量。所有物体和骨架受任务标识管理，现有场景不清空。

- 将原图 (x,y) 映射为世界 `(x-W/2, H/2-y, layer_depth)`，按统一尺度缩小；相机沿 +Z 看向 XY 平面。
- 保留裁剪原点和 PNG UV，正交画幅对应源图尺寸，较高 z_index 更靠近相机。
- 使用 EEVEE 混合透明时，将深度写到对象位置，让对象原点也按 z_index 排列；仅挪动顶点、所有对象原点重合会导致透明排序错误。必须目视核对腕部、领口等隐藏接片，矩阵测试通过仍可能出现错层。
- 骨骼静止头位置取 pivot_global，父骨影响子骨整体位置。有子关节时尾端指向最近子关节，否则用短控制骨；各骨局部 Z 显式对齐平面法线，屏幕顺时针偏移对应骨 local Z 的负角度。
- 每个片所有顶点赋给唯一骨骼，权重 1；骨架修改器保持刚性。不运行自动权重。
- 锁定骨骼平移、缩放和局部 X/Y 旋转，局部 Z 加 Limit Rotation。范围必须从图像坐标角转换符号：`blender_min=-screen_max`、`blender_max=-screen_min`。
- 纹理使用真实 alpha 和无灯光颜色输出，保持皮影图样；检查透明孔洞、层叠与色彩管理。透明渲染的边缘采样可能与 Pillow 不同，不能仅靠像素差断言结构错误。

运行示例（参数在 `--` 之后，相对路径以当前工作目录为基准）：

```bash
blender --background --factory-startup --python scripts/blender_rig.py -- \
  --manifest /path/to/assets/manifest.json \
  --motion-plan /path/to/assets/motion_plan.json \
  --out /path/to/review/accepted --render
```

正式模式采用 manifest 的当前允许范围：越界的目标姿态会被限位，报告同时保留请求角度、实际使用角度与未满足目标，不能把限位后的静止姿态说成完成了目标动作。

设计试验时加 `--trial`，用 target_ranges 创建骨骼限位，保存明确标记为 trial 的场景与报告。在独立输出目录渲染同组姿态，观察真正的暴露。**不要以试验模式替换已验收交付文件。** 先将源 PNG 和 manifest 校验通过，再导入；脚本还会检查它实际依赖的坐标、层级、路径、图片尺寸和目标动作数据。

脚本打包使用的纹理，保存 rig.blend、rig-test-results.json，`--render` 额外输出逐姿态预览。可在 Blender 的 Pose Mode 选择骨骼手动调整。位置/旋转锁是编辑便利限制，受约束轴的数值和最终求值均需检查。

## 试动—补全闭环

1. 用初步可见片与少量连接片跑 reference、目标端点、中间点及组合；保存尚未补全的失败图。
2. 在图上标记露缝区域、造成它的两片、遮挡方向。必要时用宽画布区分裁剪与断裂。
3. 依据接缝扫掠范围确定隐藏延伸，而非统一固定像素长度；补全区单独标为 inferred。
4. 修改源 mask/PNG 或增加绘制片，保留同一控制骨和坐标约定，重新导入并跑完全相同的 motion plan。
5. 同时审查原姿态纹样/镂空、动作接缝和透明叠层。新增背片遮住镂空也是失败。
6. 保存目标范围、通过范围、失败姿态和理由。范围缩小只能形成有明确限制的交付，不能消除原目标未满足的事实。

## 验收分层

- 自动验证：节点/骨骼对应、单骨权重、纹理存在、父子变换、顶点预期位置、片长不变、深度不变、越界旋转确实限位、保存文件存在。
- 目视验证：原姿态、宽袖整条接缝、补片暴露、花纹/镂空遮挡、组合穿插、画幅边界。
- 骨架验证通过与目标动作视觉通过分别报告。刚性绑定不会自动修复宽袖缺口；若需 IK，用骨骼 IK 限制并另测翻转，不把 FK Limit Rotation 当作 IK 求解限制。

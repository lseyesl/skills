# 新建空场景、环境预检与隔离交付

适用：新建图片模型、独立资产交付、渲染前环境确认和默认对象污染排查。现有项目的局部编辑不清场景。

## 新建与编辑分开

新建模型必须新开任务场景，删除/避免其中的默认 Cube、Camera、Light 后再创作。优先使用 `bpy.data.scenes.new` 创建真正的空场景，不复制启动场景；因此没有默认对象需要遗留。之后按任务需要重新建立参考、模型、相机与灯光。不要为了清理默认对象，跨场景删除用户资产。

使用 [production_workspace.py](../scripts/production_workspace.py)：

```python
from production_workspace import task_scene, role_collection
scene = task_scene(task_id, mode="create")
assets = role_collection(scene, "Asset")
coarse = role_collection(scene, "Coarse")
# References、Studio 用于任务参考图和明确创建的灯光/相机。
```

同一 task_id 复用已拥有场景；同名未拥有场景会拒绝清理。重复运行只替换已声明模块，不在场景内全选删除。编辑模式必须传入已核对的 `existing` 场景，不创建或清空其他场景。模板用 SCENE_MODE/SCENE_NAME 区分；场景名称是寻址信息，所有权仍需验证。

保存后在新进程直接打开 `.blend`，不替它选择场景来掩盖错误默认状态。核对实际活动场景、可见模型、参考资源和骨架。渲染辅助可以保存在源文件中，但不进入模型 GLB 的对象白名单。

## 真正运行一次渲染预检

在最终固定相机/光照下建立比较基线前，调用 `apply_render_preflight(scene)`。它用单独小场景实际运行 16px CPU 探针；仅遇到明确的降噪器不可用错误才关闭降噪并重试。磁盘、引擎等其他错误传播，不以“兼容模式”隐藏。保存返回记录；fallback 后的图片不能沿用旧外观验收签名。

该探针只覆盖 CPU 和小图，不证明 GPU、最终分辨率、显存、模拟缓存或完整渲染可靠。实际生产设置不同需另做代表性局部渲染。参考拟合器已接入此检查，beauty/clay 使用同一实测结果；ID/轮廓 pass 继续禁用降噪。

## 导出独立于全局选择状态

使用 [asset_delivery.py](../scripts/asset_delivery.py) 的 `export_glb`：

```python
report = export_glb(objects, new_glb_path, mode="static", tolerance=1e-5)
# object-level rotation or prepared linear skinning:
report = export_glb(objects, new_glb_path, mode="animated",
                    frames=(1, 9, 17, 25, 33), clip="WheelSpin", tolerance=1e-5)
report = export_glb(objects, new_glb_path, mode="rigged",
                    frames=(1, 9, 17), clip="FK_Check", tolerance=1e-5)
```

容差是任务单位下的示例值，必须按尺寸和用途声明。输出与报告路径必须新建。工具把明确对象打包，在独立 Blender 进程选择目标场景，显式限制 active scene/selection，并隔离重载核对：网格节点白名单、三角面、双向顶点云距离、基础 PBR 参数；动画模式再检查声明 clip，rigged 再检查 skin 和骨层级。保留 `.report.json`、有效设置、哈希和日志。失败报告不能作为发布批准。

动画模式先把 source scene.frame_start/frame_end 设为本次单 clip 的声明范围，采样必须包含两个端点；不能因只选了中间采样帧而静默截短动作。重载按源 FPS/fps_base 对齐时间，不套用默认 24 FPS。

**适用边界必须核对：**

- static 烘焙当前帧的求值 mesh/curve，保留源修改器，输出为世界坐标静态副本；不保留实例、动画或原层级。
- animated/rigged 要求显式列出父级和骨架依赖。非 Armature 修改器、约束和形态键应先在受管导出副本按目标准备，并使用相应专门验收；本适配器拒绝默默丢弃它们。原骨架、形态键与动作不应因导出被破坏。
- 当前适配器只接受常量 Principled PBR；程序材质/纹理需先烘焙，并走已有 [纹理 GLB audit](export-and-packaging.md#static-textured-glb-audit)。它不能把复杂材质自动降成纯色后宣布一致。
- 骨骼辅助显示网格仅在实际被 imported pose bone 引用为 custom_shape 时排除；GLB 原始网格白名单仍需通过。不能把任意隐藏模型都忽略。
- 多动作、非线性蒙皮、IK/驱动、形态键和目标引擎特性需对应适配与目标检查。逐帧采样表面相同不证明解剖合理或整段播放正确。

完整交付仍要运行 Khronos 格式检查、固定视图视觉检查和用途验收。不要把“进程成功”或“格式 0 错误”升级为完整模型可用。

<a id="apply-imported-references-to-geometry"></a>

# 将导入的参考图用于构建几何

在 Blender 中使用 `scripts/reference_workspace.py`进行通用参考驱动的过程构建。它提供图像引导设置、实时状态检查、像素到世界地标映射以及证据检查。它不解释像素、检测语义地标、生成截图或自动判断视觉一致性。

现有的字符拟合工具已经校准好了。pixel/profile构建与渲染的对比。它可能会保留该路径；不要替换其解剖结构构建器，也不要声称无头工人制作了经过人类审核的视口叠加层。该通用模板以前没有相应的前提条件；现在需要明确的`reference`,`original`或用户授权的`waived`模式。

<a id="1-prepare-the-workspace-before-a-geometry-build"></a>

## 1. 建模前准备参考工作区

导入多张建模参考前，先完成[建模前多视图审查](../../concept-multiview-sheet/references/pre-model-review.md)。在配置中加入 `"multiview_review": "multiview-review.json"`。仅接收就绪状态为 `passed` 的整套控制图；`partial` 留在多视图审阅中。`setup_references` 在**更改任何参考图之前**检查源文件哈希、视图用途及范围。补充或已否决的视图不能直接成为建模依据；被阻塞的父部位或子部位也不能纳入。该记录声明实际审图结果，脚本不会自动判断像素或解剖结构，建模脚本必须遵守所列部位范围。普通单张参考无需额外填写多视图记录。

对于范围有限的局部修复，可以在设置配置中设置例如`"required_landmarks": {"right": ["chin_tip", "under_chin", "neck_front"]}`。选择实际编辑所需的锚点和视图。设置会在导入引导线之前进行验证，并启动一个新的使用记录。从那些映射的点出发进行修复。与邻近的颌部和领部一起检查覆盖层。一个before/after渲染可以记录差异；比较工件必须显示独立的引导线。单独的修复调用与模板相同的设置、校准和最终比较检查，或者提供等效的证据。没有这个字段的旧配置仍然保留其现有的检查。

保留一个项目本地 `reference-setup.json` 文件，其中包含独立的图像路径和经过审核的像素锚点。仅示例形状；将其坐标替换为实际分析结果：

```json
{
  "views": {
    "front": {
      "image": "front.png",
      "pixels_per_unit": 170,
      "origin_px": [50, 180],
      "origin_world": [0, 0, 0],
      "opacity": 0.4,
      "landmarks": {
        "body_center": [50, 95],
        "body_left": [10, 95],
        "body_right": [90, 95],
        "body_top": [50, 10],
        "body_bottom": [50, 180]
      }
    }
  }
}
```

像素从图像的左上角开始，X轴向右，Y轴向下。`origin_world`表示与`origin_px`相对应的图像像素；`pixels_per_unit`表示统一的缩放比例。由于没有实际的尺寸，选择标准化单位，并将深度和隐藏的几何图形标记为推断出的数值。仅有一个前视地标就能提供一个平面上的点，而不是三维深度。在条件可靠时添加侧面、顶部约束。

Blender视图基础：从前方看是-Y方向，从后方看是+Y方向，从右侧看是+X方向，从左侧看是-X方向，从上方看是+Z方向，从下方看是+Z方向。
-Z. 相反的视图具有相应的平面反转。如果现有项目使用不同的轴，则应采用有文档支持的方法进行调整，而不是简单地镜像。

从持续运行的设置脚本开始，当前激活的是所请求的场景：

```python
import json, sys
from pathlib import Path
import bpy

sys.path.insert(0, "/absolute/skill/blender-python-modeling/scripts")
from reference_workspace import setup_references, workspace_signature

p = Path("/absolute/project/reference-setup.json")
setup_references(bpy.context.scene, "my-task", json.loads(p.read_text()), p.parent)
signature = workspace_signature(bpy.context.scene, "my-task")
```

这只会创建由任务拥有的图像填充对象，这些对象经过对齐和校准，深度方向为正面，默认不透明度为0.4。front-side/orthographic-axis可见性，transform/selection锁定，打包的图像。它重复使用已拥有的资源。guides/images并且拒绝未经处理的碰撞。它不会随意将引导线向摄像机方向移动以获得前序绘制顺序。

<a id="2-inspect-calibration-then-open-the-build-gate"></a>

## 2. 检查校准结果，确认可以建模

捕获实际的正视图，同时保留参考图，检查图像的方向。地面、原点调整比例和锚点，并将捕获内容保存到项目中。录制`calibration-review.json`仅在检查后：

```json
{
  "workspace_signature": "实际场景返回的签名",
  "phase": "calibration",
  "status": "passed",
  "views": {
    "front": {
      "artifact": "review/front-reference.png",
      "finding": "记录实际观察到的轴向、比例和特征点"
    }
  }
}
```

记录每个配置的引导视图。保留unreliable/contradictory将面板从控制设置中分离出来，并将其作为补充设计证据保存。一个视角原始图并不因为文件名是front.png. 通过现有的证据政策解决材料上的歧义；不要要求艺术模型使用伪造的测量数据。

该模板在**移除先前生成的几何图形**之前会进行此检查。如果缺少引导线、front/alpha/visibility设置错误、sources/transforms已更改、缺少捕获数据或工作区签名失效，则会导致构建过程中断。此检查用于验证状态并提供证据；但它不能证明屏幕截图中的内容。

<a id="3-use-the-imported-guides-coordinates-in-the-builder"></a>

## 3. 在建模脚本中使用导入参考的坐标

设置模板的 helper/config/review路径和 `BUILD_MODE = "reference"`。使用映射来指定实际的模型输入，例如：

```python
from reference_workspace import reference_landmark
center = reference_landmark(scene, task, "front", "body_center")
left = reference_landmark(scene, task, "front", "body_left")
right = reference_landmark(scene, task, "front", "body_right")
width = (right - left).length
# Use center/width in mesh placement and dimensions, not just in a log.
```

该辅助工具通过实时图像空变换来映射，并记录场景中使用的锚点。对于曲线轮廓，会选取经过审核的轮廓锚点，构建相应的表面；该样本立方体仅用于坐标演示。运行时使用的记录可以追溯其来源，但不能仅凭艺术相似性或证据来判断调用者是否真实使用了返回的值。参数必须能够追溯到这些值，并且必须比较最终得到的形状。

<a id="4-compare-the-model-before-final-delivery"></a>

## 4. 交付前对比模型

构建块排除，检查参考可见的轴覆盖，并修复差异。使用相位 `comparison`、当前工作区签名、每视图 capture/findings、 `model_signature(objects)` 和 `appearance_signature(scene, objects, extra=...)` 保存 `comparison-review.json` 实际 model/presentation.。这两个功能都由 `reference_workspace` 导出。如果使用了外部视觉依赖项，请将其存储在 `appearance_extra` 下，并将相同的值传递给外观签名。有关范围，请参阅 [staged-execution.md](staged-execution.md)。在声称最终参考引导结果之前，请运行 `require_reference_review(scene, task, path, phase="comparison", objects=objects)`。没有进行此审查的模板会报告 `blockout_pending_comparison`，而不是完成。

更改模型geometry/transforms/evaluated修改器使得比较无效；material/texture/attribute,灯光、世界环境, 相机和渲染更改会使其外观证据失效，即使几何形状相同。没有外观特征的旧比较记录需要检查和更新，而不是自动通过。移动、隐藏或替换引导线会使校准失效。仅新的地标读数并不能使视觉检查重新通过。提供比较伪影feature/finalledger审查证据；有效的账本并不能替代这个Blender实时状态检查。图像仍然作为视口引导线存在，与最终的美化渲染是分开的。

在场景中保留预模型审查文本，以便对便携式打包文件进行检查。新的 setup/build 需要包含源文件和审查工件；现有的打包场景可以在没有这些文件的情况下进行检查。如果可用的设计收据发生更改，则校准无效。旧的保存的工作空间仍然可以读取，但新的多指导设置需要范围设计审查。

若构建和渲染分开调用，在任务模板启用 `BUILD_RECEIPT`，提供辅助脚本路径、实际阶段输入及已保存的输出。本次尝试失败或中断后，不能沿用旧的成功记录。按[分阶段执行](staged-execution.md)校验实际产物，不能只看传输层的错误标志。

<a id="executable-checks"></a>

## 可执行检查

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python skills/blender-python-modeling/tests/blender_reference_workspace.py
```

该合成测试检查了六轴映射、Front/alpha设置、稳定所有权、删除前的模板门、实际锚点衍生尺寸、missing/stale证据以及编辑后的比较无效性。合成捕获收据测试的是机制本身，并非真实的模型叠加或艺术性审批。

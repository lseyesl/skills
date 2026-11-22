<a id="minimal-usage-and-cross-project-application"></a>

# 基本用法与跨项目复用

<a id="standalone-smoke-scene"></a>

## 独立测试场景

来自此仓库根目录：

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python skills/blender-styles/scripts/build_demo.py -- \
  --config skills/blender-styles/styles/soft-clay/examples/preview.json \
  --output .tmp/clay-example --render still
```

该示例包含了一个抽象的多部分内容。bob/tilt模型、大型地面、圆形块体、锥形cone、鹅卵石、五种黏土颜色、区域灯光、摄像机以及输出范围之外的重复循环端点。它创建一个新的场景，并保留其他scenes/data完好无损。该几何形状是一个验证装置，并非必需的项目风格或命名规范。

使用 `examples/portrait.json`进行肖像 EEVEE 预览。 `build_demo.py --render animation` 会输出序列（如果配置文件设置为 `format="FFMPEG"`，则输出原生视频）。在实验之间切换输出目录； `--overwrite` 明确选择替换模式。

<a id="existing-project-recipe"></a>

## 现有项目的配置方法

这些工具可以导入函数以及 CLI 脚本。使用一个持久的项目脚本来处理依赖的设置步骤，这样在 Blender 进程之间就不会丢失未保存的更改：

```python
from pathlib import Path
import json
import sys
import bpy

# Supply the installed Skill's scripts location; no project-specific path is in the Skill.
tool_dir = Path("/absolute/installed/blender-styles/scripts")
sys.path.insert(0, str(tool_dir))
from clay_common import merge_config, save_new
from create_clay_material import create_palette
from setup_clay_lighting import setup_lighting
from setup_render import setup_render
from validate_clay_scene import validate_scene

scene = bpy.context.scene
profile = merge_config(json.loads(Path("/absolute/project/style.json").read_text()))
palette = create_palette(scene, profile, owner="project-style")
targets = [scene.objects[name] for name in authorized_mesh_names]
for obj in targets:
    # Choose a specific authorized slot; clone shared mesh data first if needed.
    obj.data.materials[authorized_slot_for(obj)] = palette[palette_key_for(obj)]
setup_lighting(scene, profile, owner="project-style", with_camera=False)
setup_render(scene, profile, output="/absolute/output/frame-")
report = validate_scene(scene, profile, owner="project-style", objects=targets)
if not report["structural_ok"]:
    raise RuntimeError(report["errors"])
save_new("/absolute/output/styled.blend")
```

`authorized_mesh_names`、slot/color 映射和几何信息是项目输入。不要通过无差别地应用样式来实施它们。现有的材质槽和共享网格数据是调用者的责任。`merge_config` 在编辑之前会验证完整的合并后的轮廓。

用于动画调用`setup_animation(obj, scene, profile, owner)`在插入键位后，明确选择无约束的目标。适用于由作者创建的绑定结构constraints/NLA使用带有计算出的烘焙运动的渲染副本；仅为满足这个辅助需求，不要移除生产 rig 控制。

<a id="individual-cli-stages"></a>

## 各阶段的命令行用法

所有阶段都可以在 Blender 的 `--`之后接受 `--config`、`--scene`、`--owner`。它们只改变内存中的数据，除非需要保存：

```bash
blender --background /absolute/project/source.blend --python-exit-code 1 \
  --python skills/blender-styles/scripts/create_clay_material.py -- \
  --config /absolute/project/style.json --owner project-style
```

此工具用于检查材质的创建，但不保存这些创建结果。要组合 CLI 阶段，可以像上述那样运行一个包装脚本，或者使用有序的 Blender 操作。`--python`**不使用脚本 CLI 参数的调用**，然后通过最后一个保存stage/project配方。各阶段`--`在 Blender 中，所有脚本都会共享参数，因此不要以这种方式组合不同的解析器。

`setup_render.py --save /absolute/output/styled.blend` 保存一个已配置的副本。`setup_render.py --output /absolute/output/preview.png --render still` 显式进行渲染。`setup_clay_lighting.py --keep-camera` 保留活动摄像机的位置。`setup_clay_animation.py --objects NAME ...` 从不猜测动画目标。

<a id="local-repeatable-test-suite"></a>

## 可在本地重复运行的测试

```bash
blender --background --factory-startup -t 2 --python-exit-code 1 \
  --python skills/blender-styles/scripts/test_soft_clay.py -- \
  --output .tmp/clay-tests --render
```

移除 `--render`以进行快速结构测试。该套件会创建一次性新场景，测试两种渲染器、 portrait/landscape覆盖、重新运行、保留所有权、计时、不良输入以及负面质量保证情况。它使用 CPU Cycles，保持硬件偏好不变，并生成机器可阅读的报告。仅在一个一次性进程中运行，而不是在生产中的开放场景中运行。请参阅录制的 [测试结果](test-results.md)，了解实际执行的内容。

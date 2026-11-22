<a id="render-configuration-and-batch-delivery"></a>

# 渲染配置与批量交付

这些工具仅需要 Blender 的 Python 语言和标准库。配置采用 JSON 格式的部分覆盖方式；未知键和无效值会在设置之前导致失败。使用 `scale`、 `palette`、 `material`、 `lighting`、 `camera`、 `render`、 `animation`、 `quality`。完整的键集和默认值存储在 `scripts/clay_common.py` 中； `palette` 会替换其映射，而其他部分则会合并。

<a id="engine-and-hardware"></a>

## 引擎与硬件

`render.engine`： `KEEP`保留了一个有效的 EEVEE/Cycles引擎； `EEVEE`会尝试使用运行时支持的 `BLENDER_EEVEE_NEXT`，然后 `BLENDER_EEVEE`； `CYCLES`会请求 Cycles。如果缺少引擎或所需的样本 API，则会生成诊断信息，而不是静默的渲染器回退。 `samples`控制 Cycles 的样本，或者支持的 EEVEE 渲染样本属性。

`render.device`：`KEEP`保留了Cycles的设备选择。`CPU`明确选择了CPU，以便进行可重复的测试。`GPU`需要已经配置并启用的GPU；该脚本不会选择Metal/CUDA/OptiX/HIP或更改全局设备设置。EEVEE的图形后端由Blender/platform控制，而不是`render.device`。仅使用CPU的Cycles路径仍然可用；EEVEE的后台渲染可能需要一个正常工作的图形环境。

运行时兼容性保护涵盖了引擎的分配，format/codec/OCIO枚举类型、着色器插口标识符、分层与传统动作的对比、运动模糊以及采样属性。所执行的基线版本为 Blender 4.5.12 LTS。其他4.x/5.x这些版本**并未经过测试**；请自行运行。`scripts/test_soft_clay.py`在那次构建和检查中errors/RNA在扩展适配器之前。检测到的功能并不具备视觉验证功能。

<a id="aspect-ratio-frame-range-and-color"></a>

## 宽高比、帧范围与色彩

- Landscape: e.g., `width=1920`, `height=1080`; Portrait: `width=1080`, `height=1920`.
- `percentage` 会调整最终的像素尺寸；像素的比例关系保持不变，仍为正方形。
- 设置 `fps`、 `fps_base`、 `frame_start`、 `frame_end`；渲染步长为 1，因此在播放时姿态保持仍然可见。
- `view_transform="AgX"`、`look="KEEP"`、`exposure=0`、`gamma=1`是起始值。在需要保证拍摄均匀性的生产配置中，要显式保留与运行时相关的参数；`KEEP`则保留了一个可能在不同项目中有所不同但依然有效的选择。
- `transparent`使用RGBA格式进行PNG/EXR.处理。H.264格式没有alpha通道；该工具会拒绝透明的FFMPEG输出。
- 禁用停格动画中的运动模糊。在验证已安装的 API 并渲染后，可以使动画更加流畅。

<a id="stills-image-sequences-and-video"></a>

## 静帧、图像序列与视频

`PNG`是默认的无损显示输出（8位）。`OPEN_EXR`是16位场景线性合成输出。`FFMPEG`使用Blender的原生编码器配置MPEG-4/H.264，不包含音频；选择`--render animation`。这些是经过设计的支持预设，并非完整的格式列表。

对于昂贵的动画，建议使用PNG/EXR序列：孤立的帧是可恢复的，并且可以在审核中进行比较。使用Blender的VSE或可用的编码器对已批准的序列进行编码；确保帧数、顺序、实际FPS、尺寸、编解码器和播放时长都符合要求。直接使用FFPEG进行渲染可以方便地制作短预览，但不是一种可恢复的序列编码器。

```bash
# Existing configured .blend; commands shown from repository root.
blender --background /absolute/output/demo.blend --python-exit-code 1 \
  --python skills/blender-styles/scripts/setup_render.py -- \
  --config /absolute/project/style.json --output /absolute/output/frame- \
  --render animation
```

图像序列前缀会生成编号的文件，例如 `frame-0001.png`。仍然会输出所需的文件名加上扩展名。Blender可能会在视频文件名中添加帧范围后缀；将生成的 `files` 列表作为实际结果使用。每个渲染都会优先处理现有的输出，除非明确指定了 `--overwrite`。

对于已保存的配置好的场景，原生批量渲染同样适用：

```bash
blender --background /absolute/output/demo.blend -o /absolute/output/frame- -F PNG -s 1 -e 24 -a
```

Blender的CLI参数会按顺序执行；将渲染操作放在最后。避免使用已存在的输出前缀；原生功能。`-a`不使用此技能的覆盖保护机制。当该保护机制或配置验证很重要时，请使用脚本化路径。

<a id="evidence"></a>

## 证据

记录引擎、设备策略、Blender版本、配置文件、分辨率、FPS以及帧数范围。解码渲染后的图像，检查有限的像素数和预期的dimensions/count.。一个有效的图像或MP4文件并不能证明正确的构图或运动效果；需要检查代表性的帧数，并播放视频。渲染器的差异、自定义OCIO、DOF噪声以及较低的采样数量可能会改变视觉效果；需要在最终的渲染器中进行测试。

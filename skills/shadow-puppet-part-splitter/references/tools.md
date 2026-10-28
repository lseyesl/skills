# 通用工具：直接使用

以下命令从本 Skill 目录执行，`python` 指已安装 `scripts/requirements.txt` 的 Python 3.10+ 环境。图片处理需要 Pillow；Blender 只在 `blender` / `reopen` 操作时需要，MP4 只在请求它时需要 ffmpeg。其余步骤可以独立使用。

## 五分钟示例

```bash
python examples/create_demo.py --output /tmp/puppet-demo
python scripts/toolbox.py run --config /tmp/puppet-demo/pipeline.json --report /tmp/puppet-demo/run.json
python scripts/toolbox.py run --config /tmp/puppet-demo/pipeline.json --report /tmp/puppet-demo/run.json
python scripts/toolbox.py blender --config /tmp/puppet-demo/blender.json
```

前两条产生一个无人体假设的机械铰链样例、回组图、关节图、拆件表、给定姿态表、连接测量和 ZIP。第二次运行复用成功且输入/产物未变的步骤。Blender 示例有两个 Action，轨迹已经写在 `motion.json`，工具只负责写入与核验。

修改示例或素材前先复制到自己的目录。示例生成器会更新该目录的示例文件；Blender 为避免覆盖编辑成果，已有 `rig.blend` 时要求换一个输出目录。

## 操作及通用场景

所有操作支持 `--config config.json`。配置内路径相对配置文件；命令行直接给出的路径相对当前工作目录。可显式引用绝对路径或其他目录的输入。目录输出应与输入分离，工具会保护引用的输入文件。

| 命令 | 输入配置 | 适用场景与产物 |
|---|---|---|
| `info` | `source` | 任意可读图像的尺寸、模式、alpha 极值和包围盒；不判断语义 |
| `extract` | `source, mask, output`，可选 `padding` | 已有遮罩的部件、道具、装饰裁剪；输出 RGBA 与 `.png.json` 原坐标记录；空选区 `skipped` |
| `masks` | `masks: [路径…], method, output` | 同尺寸灰度遮罩的 `union / intersect / subtract`；不自动选最大连通域 |
| `register` | `source, anchors, output`，可选 `size: [宽,高]` | 已知对应点的相似变换配准；输出图像和锚点残差 |
| `patch` | `source, patch, mask, output`，可选 `protect_mask` | 已配准补片按遮罩合成；保护遮罩任何非零像素都逐像素保留原值 |
| `render` | `manifest, output`，可选 `pose, enforce_limits` | 静态层、任意层级已有组件回组，或按明确变换预览 |
| `preview` | `manifest, output`，可选 `poses, reference, columns, cell_size, font` | 回组、带 ID 拆件表；有节点才画关节，有推测 mask 才高亮，有姿态/参考图才生成对应图 |
| `check` | `manifest`，可选 `poses, radius, alpha_threshold, review, output` | 引用、图像、父子和坐标检查；给定姿态的连接交叠像素与几何越界测量 |
| `blender` | `manifest, output`，可选 `motion_plan, render, resolution, blender, threads` | 静态平面或刚性骨架导入、贴图打包、给定轨迹写入 Action、顶点检查和保存 |
| `reopen` | `blend, scene_report, output`，可选 `blender, threads` | 从保存文件检查已声明对象、单骨权重、层次深度、打包纹理、关键帧及区间中点变换 |
| `media` | `frames, output`，可选 `formats, fps, background, columns, cell_size, sheet_max_frames, ffmpeg, font` | 任意图像序列 → GIF / MP4 / 联系表，无需角色、manifest 或 Blender |
| `package` | `files: [路径…], output`，可选 `required, archive_root, manifest` | 显式文件清单 → ZIP、CRC 校验、SHA256、缺失文件记录；没有固定数量或动作名称 |
| `run` | `steps`，另加 `--report 路径` | 按需编排上述操作；计时、内容缓存、续跑、局部失败隔离 |

简单命令：

```bash
python scripts/toolbox.py info --source reference.png
python scripts/toolbox.py extract --source reference.png --mask selected.png --output parts/selected.png
python scripts/toolbox.py render --manifest manifest.json --output preview/rest.png
python scripts/toolbox.py preview --manifest manifest.json --poses poses.json --output preview
python scripts/toolbox.py check --manifest manifest.json --output measurements.json
python scripts/toolbox.py media --frames frames --output media --formats gif,mp4,sheet --fps 24
```

`register` 配置示例：

```json
{"source":"donor.png","anchors":[{"from":[10,20],"to":[30,40]},{"from":[60,20],"to":[80,40]}],"size":[256,256],"output":"registered.png"}
```

至少两组不同的点。求解平移、旋转和统一缩放，不能替代透视/非刚性匹配。遮罩必须与相应输入图同尺寸，明确选区由调用者提供。

## 数据与明确轨迹

manifest 见 [manifest.md](manifest.md)。静态部件可省略 `nodes`、`node`、关节范围和动作计划；RGB、全不透明矩形均可输入。动画节点的 `pivot_global`、父子和参考坐标由调用者明确给出。相同逻辑 `z_index` 按数组顺序稳定绘制，Blender 转成不同对象深度。

`render` 的内嵌 `pose` 和 `poses.json` 中的姿态使用同一结构：

```json
{"poses":[{"id":"sample","angles":{"hinge":30},"translations":{"control":[5,-2]},"scales":{"hinge":[1.1,0.9]}}]}
```

角度为相对参考姿态的顺时针角度；位移是父变换前、参考屏幕轴下的像素位移；缩放沿参考屏幕轴。子节点跟随父变换。未给出的角度、位移、缩放分别为 0、[0,0]、[1,1]。变换可以调用标准库模块 `puppet_core.py` 的 `pose_transforms / apply / inverse`；`pivot_local = pivot_global - crop_origin`。

Blender `motion_plan`：

```json
{"fps":24,"clips":[{"id":"provided trajectory","frames":[{"frame":1},{"frame":13,"angles":{"hinge":30},"translations":{"control":[20,0]}}]}]}
```

每个 clip 有独立 Action；帧号显式且不重复，键间线性插值。也接受旧式 `poses` 数组，缺少帧号时按每 12 帧写一个姿态。多个 clip 的 fps 统一由顶层定义。名称不受人体部位约束，外部节点名映射为稳定内部骨名。仅对提供范围的节点加旋转限位；超出已声明范围的输入会报错，不静默裁小目标。非均匀缩放会改变片的形状，需要调用者明确要求。

静态导入不要求动作计划。导入产生自己拥有的场景，保留其他场景。默认渲染为源尺寸约一半；`resolution: [宽,高]` 可覆盖，需保持原宽高比。像素转 Blender 单位为 0.01；所有骨轴平行于世界 +Y，屏幕正角对应骨局部 Z 负角。

重开配置例子：

```json
{"blend":"blender/rig.blend","scene_report":"blender/io-report.json","output":"blender/reopen.json"}
```

后台受宿主沙箱限制时，使用已获准的 Blender 后台入口执行同一脚本，不绕过权限：

```bash
blender --background --factory-startup -t 2 --python-exit-code 1 --python scripts/blender_io.py -- --manifest manifest.json --out blender --render
blender --background blender/rig.blend -t 2 --python-exit-code 1 --python scripts/blender_io.py -- --reopen-report blender/io-report.json --out blender/reopen.json
```

## 编排、报告与续跑

`examples/create_demo.py` 生成的 `pipeline.json` 是可运行配置。每步包含 `id, op, config`，可选 `depends_on: [步骤ID…]`、`required: false`；`config` 可以是内嵌对象或另一个 JSON 文件路径。只声明真实数据依赖，不把所有步骤串成一条强制链。

- `ok` 仅表示计算成功；`cached` 表示成功结果与输入、代码、产物哈希都未变。
- `partial` 表示部分产物或请求未满足。例如无 ffmpeg 时继续产 GIF/联系表。已有部分产物可供下游使用，但全流程仍记录该必需步骤未完成。
- `failed / blocked` 仅影响依赖它的步骤。互不依赖的步骤继续执行。空选区为 `skipped`，不会伪造部件。
- 有必需步骤未满足，总状态 `partial`；`required:false` 只改变汇总，不掩盖该步的问题。退出码：0 成功、2 部分或跳过、1 无效输入/执行错误。
- `--force` 重跑；平常重复同一命令读取 `--report` 续跑。失败/部分结果不缓存为成功。报告含逐步耗时和实际产物。
- 缓存使用配置、脚本与实际输入文件内容，包括 manifest 引用的纹理/推测 mask。输出被删或改写会重跑。Blender 版本或编码器更换后应使用 `--force`，环境版本不在缓存键中。

所有数值报告默认 `visual_review: pending`。`check --config` 的 `review` 可以引用另行实际编写的审查 JSON，保留原记录；工具不自动写“视觉通过”。关节窗口交叠量并不证明整条衣缝无缺口；几何越界可能只是透明留白。参考图差分也不能替代目视。

媒体按自然文件名顺序读取 PNG/JPEG/WebP；混合尺寸在左上对齐补齐，MP4 奇数尺寸补偶数；GIF/MP4 合成指定背景。默认 `sheet_max_frames=24` 只控制联系表采样，动画仍使用全部输入帧。当前媒体实现会把序列加载到内存，长序列建议分段处理。中文标签可显式提供 `font`；默认字体不保证含中文字形。

打包保留目录结构时显式设置 `archive_root`，文件须处于该根目录内。未设置时用文件名并拒绝重名；不自动收集整个工作目录。`required` 缺失仍输出可用的部分包与缺失清单，总状态为 `partial`。

不包括自动识别人体、设计隐藏结构、生成通用步态/坐姿或自动宣布视觉验收。那些决策仍依据参考图与动作要求。

为 `package` 提供 `manifest` 时，还会检查纹理/推测 mask 是否在包内且相对引用可迁移；绝对路径即使本机可读，也会报告不可迁移。工具不会自动改写原 manifest。默认参考画布会裁切远距离移动；用 `check` 的 bounds 检查越界，需要更大舞台时由调用者扩大 manifest 的 source_size，并明确调整坐标/相机布局。

## 回归测试

```bash
python -m unittest discover -s tests -v
python tests/blender_smoke.py --blender /Applications/Blender.app/Contents/MacOS/Blender
```

第一条不依赖 Blender 或 ffmpeg，覆盖数据、像素、失败隔离和缓存。第二条需要可运行的 Blender，在全新临时目录内创建静态/局部骨架样例，实际保存、渲染并重开核验两个 Action 和中点；不会操作当前打开的 UI 场景。已验证 Blender 4.5.12 LTS，其他版本请先运行此测试。

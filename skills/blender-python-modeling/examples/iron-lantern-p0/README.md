<a id="iron-lantern-pilot"></a>

# 铁皮灯笼试作

这个示例是通过经过审核和校准的像素锚点来构建飓风灯。它使用了翻制的储液器、玻璃和灯罩的轮廓，以及两根管道和电线的扫描路径。此外，还使用了作为封闭网格的穿孔 collar。源扫描文件仅提供引导线。生成的 Blender 文件包含了独立的程序化几何图形，可以单独编辑为独立的模块，并将这两根引导线图像打包在一起。

试点项目主要针对外部遮挡和三个特定功能的检查。凹槽处理、硬件细节、内部构造以及生产材料均不在本次测试的范围内。前部和右侧的渲染图是同一扫描结果的垂直投影图，并非单张照片的估算结果。

<a id="run-in-blender"></a>

## 在 Blender 中运行

为本次任务创建新的输出目录，将示例的 Blender 路径换为本机可执行文件路径。本例在 Blender 5.2.3 LTS 上运行过。输入取自 Rajil Jose Macatangay 制作并以 CC0 发布的 [Poly Haven Lantern 01](https://polyhaven.com/a/Lantern_01)，使用[Kiln 基准测试站点](https://github.com/elithril/blender-kiln/blob/e9a421467dd95d0de71d45b3d331f8efa4b80f26/site/public/assets/glb/truth-lantern.glb)分发的扫描模型。

```powershell
$blender = 'G:/SteamLibrary/steamapps/common/Blender/blender.exe'
$pilot = (Resolve-Path skills/blender-python-modeling/examples/iron-lantern-p0).Path
$out = (New-Item -ItemType Directory outputs/iron-lantern-p0-replay).FullName
Invoke-WebRequest 'https://raw.githubusercontent.com/elithril/blender-kiln/e9a421467dd95d0de71d45b3d331f8efa4b80f26/site/public/assets/glb/truth-lantern.glb' -OutFile "$out/truth-lantern.glb"
& $blender -b --factory-startup --python-exit-code 1 --python "$pilot/capture_reference.py" -- $out
```

对照 `landmarks.json` 检查三幅参考渲染图。示例中的预模型观察结果涵盖了该固定扫描在指定框架中的情况。在允许构建之前，请准备好并检查实时指南。

```powershell
& $blender -b --factory-startup --python-exit-code 1 --python "$pilot/calibrate.py" -- prepare $out
& $blender --factory-startup "$out/workspace.blend" --python "$pilot/calibrate.py" -- capture $out calibration
```

请查看实际的 正面、右侧 视窗截图，然后使用 `workspace.json` 和 [参考工作区收件格式](../../references/reference-workspace-tool.md#2-inspect-calibration-then-open-the-build-gate) 中的签名来编写 `calibration-review.json`。构建过程需要 receipt。

```powershell
& $blender -b --factory-startup --python-exit-code 1 --python "$pilot/run_pilot.py" -- $out
& "$pilot/compare.ps1" -OutputDirectory $out
& $blender --factory-startup "$out/after.blend" --python "$pilot/calibrate.py" -- capture $out overlay-after
```

该基线模型故意设计了一个过大的储液池，以及一个堵塞通风口的插入件和较短的上部管座。三个候选的参数变化在`run_pilot.py`中有所规定。每一轮重建一个模块，以固定比例进行渲染，将候选参数与之前的状态进行比较，并验证其他模块的几何形状和材料分配。`verification.json`记录了保存的快照的测量数据、接受度以及哈希值。使用来自某个运行的文件，该运行的报告已经 `status: passed`。

在检查了比较渲染图和视口叠加图之后，记录`comparison-findings.json`。给它一个从`verification.json`获得的被认可的`snapshot_sha256`，一个与校准收据具有相同每个视图字段的`views`映射，以及一个由模块ID键定的`features`映射。每个被审查的功能都有`reference`、`candidate`、`view`和`comparison`字段。运行审查阶段，将这一证据绑定到保存的文件，并验证现有的模块台账。

```powershell
& $blender -b --factory-startup --python-exit-code 1 --python "$pilot/run_pilot.py" -- $out review
```

有符号的座位间隙来源于对储液器和罩体表面的两个评估管端点的探测。负数表示端点中心进入接收部分。通过两个前通风窗口进行开口检查。这些检查涵盖了声明中的位置，但并不能证明是否存在自相交、内部空气通道或制造间隙。

<a id="p1-fixed-camera-feature-and-material-review"></a>

## P1：固定镜头特征与材质审查

在P0阶段之后运行此程序。重放功能会验证两个被接受的快照哈希值。该程序根据P0正交校准来推导相机参数，并在[P1计划](p1-review.json)中的每个问题上以相同的比例裁剪参考图像。另外，还有一个单独的《灯笼01》三分之一个预览，用于提供外观指导。该预览并不控制裁剪后的相机参数。

对于金属区域，重放使用了 Amal Kumar 的 [锈铁04](https://polyhaven.com/a/rusty_metal_04) 技术。它保留了扫描得到的磨损分布，将基础颜色调暗至暗色系，并减少了边缘和金属丝的粗糙度。在预览比例下，使用扫描得到的高度作为凸起效果，而球体则采用程序化的玻璃色调。相同的材料配方在内存中的两个快照上均适用。每个特征都记录了材料区域、映射哈希值和设置。

```powershell
$p0 = (Resolve-Path outputs/iron-lantern-p0).Path
$p1 = (New-Item -ItemType Directory outputs/iron-lantern-p1-replay).FullName
$plan = Get-Content "$pilot/p1-review.json" -Raw | ConvertFrom-Json
$textures = (New-Item -ItemType Directory -Force "$p1/textures/$($plan.source.id)").FullName
foreach ($map in $plan.source.maps.PSObject.Properties) {
    $url = $plan.source.map_url_prefix + $map.Value.suffix + '_1k.jpg'
    Invoke-WebRequest $url -OutFile "$textures/$($map.Name).jpg"
}
$ref = 'https://raw.githubusercontent.com/elithril/blender-kiln/e9a421467dd95d0de71d45b3d331f8efa4b80f26/site/public/assets/img/ref-Lantern_01.webp'
Invoke-WebRequest $ref -OutFile "$p1/appearance-reference.webp"
& $blender --background --factory-startup --disable-autoexec --python-exit-code 1 `
    --python "$pilot/review_p1.py" -- $p0 $p1
& "$pilot/compare.ps1" -OutputDirectory $p1 -FeatureReview
```

请追加 `--feature hood-seat` 以仅重新渲染关节裁剪部分。同时检查参考、黏土和材料面板。渲染后的结果涵盖了执行和 input/output 哈希值。只有在检查了结果之后，才将视觉对比结果添加到账本中。关于通用配置字段，请参阅 [本地审核配方](../../references/local-feature-review.md#fixed-camera-review-for-a-local-correction)。

<a id="p2-isolated-glb-round-trip"></a>

## P2：独立环境下的 GLB 回读

使用已接受的 P0 快照和 P1 纹理下载。P2 会生成一个可编辑的单独导出基线，包含 16 个网格，进行三角化处理，并为每个对象生成一组 UV 坐标。长线吊索和侧管采用基于扫描的展平方式，并配有单独的封盖。对这些三个部件进行的第一次智能 UV 处理尝试出现了重叠问题，未能通过门检。

金属角色使用UV映射的基色图像，以及从P1扫描中得到的绿色粗糙度和蓝色金属效果图像。玻璃则保留了Principled的透明效果。P1的三平面投影和凹凸效果在Blender预览中可见。P2则携带源颜色以及roughness/metallic映射，以便携式glTF材料通道的形式呈现。

```powershell
$p2 = (New-Item -ItemType Directory outputs/iron-lantern-p2-replay).FullName
& $blender --background --factory-startup --disable-autoexec --python-exit-code 1 `
    --python "$pilot/export_p2.py" -- $p0 $p1 $p2
```

在空白 Blender 场景中回读实际导出文件，核验正面的两个通风窗、提环以及全部四个管座。在原采样位置向导入网格表面投射射线检查管座，因此不依赖顶点顺序。`roundtrip.json` 记录最终 GLB 哈希、尺寸、原始及导入后的几何检查、材质和 UV 检查，以及回读后的渲染结果。使用 `delivery-source.blend` 和集合 `iron-lantern-p0::model` 进行独立静态验证，步骤见[通用审计](../../references/export-and-packaging.md#static-textured-glb-audit)。

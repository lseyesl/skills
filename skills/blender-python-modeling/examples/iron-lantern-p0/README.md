# Iron lantern pilot

This example builds a hurricane lantern from reviewed, calibrated pixel anchors. It uses turned profiles for the reservoir, glass and hood, swept paths for the two tubes and wires, and a perforated collar built as a closed mesh. The source scan only supplies guides. The generated Blender files contain independent procedural geometry, editable as separate modules, and pack the two guide images.

The pilot targets the exterior blockout and three scoped feature checks. Knurling, hardware detail, internal workings and production materials remain outside this run. The front and right are orthographic renders of the same scan, not estimates from a single photograph.

## Run in Blender

Use a fresh task output folder. Replace the Blender path with your executable. The example was exercised in Blender 5.2.3 LTS. The input is [Poly Haven Lantern 01](https://polyhaven.com/a/Lantern_01), by Rajil Jose Macatangay, CC0, using the scan distributed in [Kiln's benchmark site](https://github.com/elithril/blender-kiln/blob/e9a421467dd95d0de71d45b3d331f8efa4b80f26/site/public/assets/glb/truth-lantern.glb).

```powershell
$blender = 'G:/SteamLibrary/steamapps/common/Blender/blender.exe'
$pilot = (Resolve-Path skills/blender-python-modeling/examples/iron-lantern-p0).Path
$out = (New-Item -ItemType Directory outputs/iron-lantern-p0-replay).FullName
Invoke-WebRequest 'https://raw.githubusercontent.com/elithril/blender-kiln/e9a421467dd95d0de71d45b3d331f8efa4b80f26/site/public/assets/glb/truth-lantern.glb' -OutFile "$out/truth-lantern.glb"
& $blender -b --factory-startup --python-exit-code 1 --python "$pilot/capture_reference.py" -- $out
```

Inspect the three reference renders against `landmarks.json`. The example's pre-model observations cover this pinned scan in the specified frame. Prepare and inspect the live guides before allowing a build.

```powershell
& $blender -b --factory-startup --python-exit-code 1 --python "$pilot/calibrate.py" -- prepare $out
& $blender --factory-startup "$out/workspace.blend" --python "$pilot/calibrate.py" -- capture $out calibration
```

Review the actual front/right viewport captures, then write `calibration-review.json` using the signature in `workspace.json` and the [reference workspace receipt format](../../references/reference-workspace-tool.md#2-inspect-calibration-then-open-the-build-gate). The build requires that receipt.

```powershell
& $blender -b --factory-startup --python-exit-code 1 --python "$pilot/run_pilot.py" -- $out
& "$pilot/compare.ps1" -OutputDirectory $out
& $blender --factory-startup "$out/after.blend" --python "$pilot/calibrate.py" -- capture $out overlay-after
```

The baseline intentionally has an oversized reservoir, an insert blocking the vent and short upper tube seats. The three candidate parameter changes are prescribed in `run_pilot.py`. Each round rebuilds one module, rerenders at fixed scale, checks the candidate against the previous state, and verifies the other modules' geometry and material assignments. `verification.json` records the measurements, acceptance and hashes of the saved snapshots. Use files from a run whose report has `status: passed`.

After inspecting the comparison renders and viewport overlays, record `comparison-findings.json`. Give it the accepted `snapshot_sha256` from `verification.json`, a `views` map with the same per-view fields as the calibration receipt, and a `features` map keyed by module ID. Each reviewed feature has `reference`, `candidate`, `view` and `comparison` fields. Run the review stage to bind this evidence to the saved file and validate the existing module ledger.

```powershell
& $blender -b --factory-startup --python-exit-code 1 --python "$pilot/run_pilot.py" -- $out review
```

Signed seat gaps come from probes at both evaluated tube endpoints against the reservoir and hood surfaces. Negative means the endpoint center enters the receiving part. Aperture checks sample through both front vent windows. These checks cover the declared locations and do not certify self-intersections, internal air passages, or manufacturing clearances.

## P1 fixed-camera feature and material review

Run this after P0 passes. The replay verifies the two accepted snapshot hashes.
It derives the camera from the P0 orthographic calibration and crops the reference
at the same scale for each issue in [the P1 plan](p1-review.json). A separate
three-quarter preview of Lantern 01 supplies appearance guidance. It does not
control the crop's camera.

For the metal regions, the replay uses [Rusty Metal 04](https://polyhaven.com/a/rusty_metal_04)
by Amal Kumar, CC0. It keeps the scans' wear distribution, tones the base color
down toward the dark lantern, and reduces roughness on rims and wire relative to
the body. It uses the scanned height as bump at preview scale and a procedural
glass tint for the globe. The same material recipe runs on both snapshots in
memory. Each feature manifest records material regions, map hashes, and settings.

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

Append `--feature hood-seat` to rerender only the joint crop. Inspect the
reference, clay and material panels together. The rendered receipt covers
execution and input/output hashes. Add the visual comparison to the ledger only
after inspecting the result. For generic config fields, see the
[local review recipe](../../references/local-feature-review.md#fixed-camera-review-for-a-local-correction).

## P2 isolated GLB round trip

Use the accepted P0 snapshot and the P1 texture downloads. P2 prepares a
separate editable export baseline with 16 meshes, triangulates, and generates
one UV set per object. The long wire bail and side tubes use a sweep-based
unroll with separate caps. The first Smart UV attempt on these three parts
had overlaps and failed the gate.

The metal roles use UV-mapped base-color images and packed green roughness /
blue metallic images derived from the P1 scans. Glass retains Principled
transmission. P1's triplanar projection and bump belong to the Blender preview.
P2 carries the sourced color and roughness/metallic maps in portable glTF
material channels.

```powershell
$p2 = (New-Item -ItemType Directory outputs/iron-lantern-p2-replay).FullName
& $blender --background --factory-startup --disable-autoexec --python-exit-code 1 `
    --python "$pilot/export_p2.py" -- $p0 $p1 $p2
```

The replay verifies the exported bytes in an empty Blender scene, including
the two front vent windows, the lifting loop, and all four tube seats. Seat
probes use rays on imported mesh surfaces at the original sample positions,
so they do not depend on vertex order. `roundtrip.json` records the final
GLB hash, dimensions, raw and imported geometry checks, material and UV
results, and post-import renders. For independent static verification use the
[general audit](../../references/export-and-packaging.md#static-textured-glb-audit)
with `delivery-source.blend` and collection `iron-lantern-p0::model`.

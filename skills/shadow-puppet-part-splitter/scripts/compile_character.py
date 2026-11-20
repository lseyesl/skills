#!/usr/bin/env python3
"""Compile reviewed pixel-space annotations into source-preserving rig assets.
No semantic segmentation or hidden anatomy inference. Requires Pillow only.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw
from puppet_core import require, pair, normalize
from puppet import render, load_manifest


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


def binary(im, label):
    require(im.mode == "L", label+": mask must be L")
    require(set(im.tobytes()) <= {0, 255}, label+": ownership masks must be binary; put soft alpha in source")
    return im


def region(spec, size, base):
    require(isinstance(spec, dict), "region must be an object")
    require(bool(spec.get("mask")) != bool(spec.get("polygons")), "region needs exactly one of mask/polygons")
    if spec.get("mask"):
        with Image.open(base/spec["mask"]) as im:
            require(im.size == size, "mask size mismatch")
            result = binary(im.copy(), str(spec["mask"]))
    else:
        result = Image.new("L", size)
        draw = ImageDraw.Draw(result)
        for points in spec["polygons"]:
            require(isinstance(points, list) and len(points) >= 3 and all(pair(x) for x in points), "invalid polygon")
            require(all(0 <= x < size[0] and 0 <= y < size[1] for x,y in points), "polygon outside source")
            draw.polygon([tuple(x) for x in points], fill=255)
    for points in spec.get("holes", []):
        require(len(points) >= 3 and all(pair(x) for x in points), "invalid hole")
        require(all(0 <= x < size[0] and 0 <= y < size[1] for x,y in points), "hole outside source")
        ImageDraw.Draw(result).polygon([tuple(x) for x in points], fill=0)
    return result


def count(im):
    return sum(im.histogram()[1:])


def visible_diff(a, b):
    # Ignore RGB under zero alpha, but compare both alpha and premultiplied RGB.
    channels=[]
    for im in (a,b):
        alpha=im.getchannel("A")
        channels.append(Image.merge("RGBA", tuple(ImageChops.multiply(im.getchannel(c), alpha) for c in "RGB")+(alpha,)))
    d=ImageChops.difference(*channels)
    changed=Image.new("L", a.size)
    for channel in d.split():
        changed=ImageChops.lighter(changed, channel)
    return changed


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compile_character(annotation, output):
    annotation=Path(annotation).resolve(); base=annotation.parent
    output=Path(output).resolve()
    require(not output.exists(), "output already exists; use a new version directory")
    data=read(annotation)
    require(isinstance(data, dict), "annotation must be an object")
    require(data.get("schema_version") == "character-annotation-1", "unsupported annotation schema")
    require(data.get("hidden_policy") in ("concept-covered", "inferred-repair"), "explicit hidden_policy required")
    source=(base/data["source"]).resolve()
    if data.get('source_sha256'):
        require(sha256(source) == data['source_sha256'], 'source hash mismatch: review annotation against selected image')
    with Image.open(source) as im:
        original=im.convert("RGBA")
    require(data.get("source_size") == list(original.size), "annotation/source dimensions mismatch")
    subject=region(data["subject"], original.size, base)
    alpha=ImageChops.multiply(original.getchannel("A"), subject)
    require(alpha.getbbox(), "empty subject")
    target=original.copy(); target.putalpha(alpha)
    parts=data["parts"]; ids=[p["id"] for p in parts]
    require(parts and len(set(ids))==len(ids) and all(re.fullmatch(r"[A-Za-z0-9_-]+",x) for x in ids), "invalid/duplicate part id")
    require(data.get("ownership") in ("exclusive", "ordered-last-wins"), "explicit ownership policy required")
    support=alpha.point(lambda x: 255 if x else 0)
    masks=[ImageChops.multiply(region(p["visible"],original.size,base),support) for p in parts]
    used=Image.new("L",original.size); overlaps=Image.new("L",original.size)
    for mask in masks:
        overlaps=ImageChops.lighter(overlaps,ImageChops.multiply(used,mask))
        used=ImageChops.lighter(used,mask)
    missing=ImageChops.subtract(support,used)
    require(not missing.getbbox(), f"unassigned subject pixels: {count(missing)}; fix annotations")
    require(data["ownership"] != "exclusive" or not overlaps.getbbox(), f"overlapping owners: {count(overlaps)}; resolve or explicitly choose ordered-last-wins")
    used=Image.new("L",original.size)
    for i in reversed(range(len(masks))):
        owned=ImageChops.subtract(masks[i],used)
        used=ImageChops.lighter(used,masks[i]); masks[i]=owned
        require(owned.getbbox(), f"empty owner: {parts[i]['id']}")
    # Validate hierarchy before writing anything. No padding/rotation changes coordinates.
    manifest={"schema_version":"1.0", "coordinate_system":"image-pixels-y-down", "source_size":list(original.size), "nodes":data.get("nodes",[]), "parts":[]}
    images=[]; repair_masks=[]
    for p,mask in zip(parts,masks):
        vis=original.copy(); vis.putalpha(ImageChops.multiply(alpha,mask))
        inferred=Image.new("L",original.size)
        if p.get("repair"):
            require(data["hidden_policy"]=="inferred-repair", "repair forbidden by concept-covered")
            repair=p["repair"]
            require(isinstance(repair.get("reason"),str) and repair["reason"].strip(), "repair needs reason")
            with Image.open(base/repair["file"]) as im:
                require(im.mode=="RGBA" and im.size==original.size, "repair must be full-canvas RGBA")
                patch=im.copy()
            inferred=ImageChops.multiply(patch.getchannel("A"),region(repair["region"],original.size,base))
            # An inferred pixel must never overwrite its part's observed pixels.
            inferred=ImageChops.multiply(inferred,ImageChops.invert(mask))
            require(inferred.getbbox(), "empty repair")
            patch.putalpha(inferred); patch.alpha_composite(vis); vis=patch
        box=vis.getbbox(); item={"id":p["id"],"label":p.get("label",p["id"]),"node":p.get("node"),"z_index":p["z_index"],"file":f"parts/{p['id']}.png","crop_origin":list(box[:2]),"pixel_size":[box[2]-box[0],box[3]-box[1]],"inferred":bool(inferred.getbbox())}
        if item["inferred"]:
            item["inferred_region_mask"]=f"masks/{p['id']}-inferred.png"
            item["notes"]=p["repair"]["reason"]
        manifest["parts"].append(item); images.append(vis.crop(box)); repair_masks.append(inferred.crop(box))
    for key in ('occlusion_rules', 'expected_parents'):
        if key in data: manifest[key] = data[key]
    normalize(manifest)
    manifest['compilation'] = {'report': 'compile-report.json'}
    output.mkdir(parents=True)
    for sub in ("parts","masks","preview"):
        (output/sub).mkdir()
    for p,im,mask,repair in zip(manifest["parts"], images, masks, repair_masks):
        im.save(output/p["file"]); mask.save(output/"masks"/f"{p['id']}-visible.png")
        if p["inferred"]: repair.save(output/p["inferred_region_mask"])
    write(output/"manifest.json", manifest)
    target.save(output/"preview/source-subject.png")
    rest=render(output/"manifest.json", diagnostic=True); rest.save(output/"preview/reassembled.png")
    diff=visible_diff(target,rest); diff.save(output/"preview/rest-difference.png")
    overlaps.save(output/"preview/ownership-overlap.png")
    labels=Image.new("RGBA",original.size)
    for i,(p,mask) in enumerate(zip(parts,masks)):
        color=((71*i+60)%220+30,(117*i+30)%220+30,(41*i+90)%220+30,255)
        layer=Image.new("RGBA",original.size,color); layer.putalpha(mask); labels.alpha_composite(layer)
        box=mask.getbbox(); ImageDraw.Draw(labels).text((box[0],box[1]),p["id"],fill="white")
    labels.save(output/"preview/ownership.png")
    report={"status":"pass" if not diff.getbbox() else "blocked", "source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(), "annotation_sha256":hashlib.sha256(annotation.read_bytes()).hexdigest(), "source":str(source), "annotation":str(annotation), "parts":len(parts), "unassigned_pixels":0,"requested_overlap_pixels":count(overlaps),"rest_changed_pixels":count(diff),"hidden_policy":data["hidden_policy"],"visual_review":"pending", "motion_review":"pending", "limitations":["Ownership/rest equality do not prove semantic boundaries or motion readiness.","Video RGB retains baked background/lighting within the selected subject; alpha recovery is not performed."]}
    if manifest.get('occlusion_rules') or manifest.get('expected_parents'):
        from layer_diagnostics import layers
        layer_out = output/'preview/layers'
        layer_out.mkdir()
        layer_report = layers(output/'manifest.json', {'frames':[{'frame':0}]}, layer_out)
        write(layer_out/'report.json', layer_report)
        report['layer_constraints'] = layer_report['status']
        if layer_report['status'] == 'fail': report['status'] = 'blocked'
    dependencies = {annotation, source}
    def collect(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in ('mask', 'file') and isinstance(item, str):
                    dependencies.add((base/item).resolve())
                else:
                    collect(item)
        elif isinstance(value, list):
            for item in value: collect(item)
    collect(data)
    report['input_sha256'] = {str(path): sha256(path) for path in sorted(dependencies)}
    report['source_binding'] = 'verified' if data.get('source_sha256') else 'legacy-unbound'
    report['output_sha256'] = {str(path.relative_to(output)): sha256(path)
                               for path in sorted(output.rglob('*')) if path.is_file()}
    write(output/"compile-report.json", report)
    if report['status'] == 'pass': load_manifest(output/"manifest.json")
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("annotation",type=Path); parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    try:
        report=compile_character(args.annotation,args.output)
        print(json.dumps(report,ensure_ascii=False))
        if report["status"]!="pass": parser.exit(2,"assembly blocked: inspect compile report, pixel difference and layer diagnostics; assets are not approved\n")
    except (ValueError,KeyError,TypeError,OSError) as exc:
        parser.exit(1,f"error: {exc}\n")

if __name__=="__main__": main()

#!/usr/bin/env python3
"""Validate exported 2D parts and render reference/relative joint poses.

Does not segment images, infer anatomy, or certify visual quality.
"""
import argparse
import json
import math
from pathlib import Path

from PIL import Image


from puppet_core import (require, number, pair, asset, index, read_manifest,
                         IDENTITY, multiply, inverse, pose_transforms, transforms)


def load_manifest(path):
    path = Path(path).resolve()
    data = read_manifest(path)
    for part in data['parts']:
        key = part['id']
        with Image.open(asset(path.parent, part['file'])) as im:
            require(list(im.size) == part['pixel_size'], f'{key}: pixel_size mismatch')
            alpha = im.convert('RGBA').getchannel('A')
            require(alpha.getextrema()[1] > 0, f'{key}: part empty')
            mask_name = part.get('inferred_region_mask')
            if mask_name:
                with Image.open(asset(path.parent, mask_name)) as mask:
                    require(mask.mode == 'L' and mask.size == im.size, f'{key}: expected same-size L mask')
                    require(mask.getextrema()[1] > 0, f'{key}: empty inferred mask')
                    require(all(not m or a for m, a in zip(mask.tobytes(), alpha.tobytes())),
                            f'{key}: inferred mask marks transparent pixels')
    return data


def render(path, angles=None, pose=None, enforce_limits=True):
    path = Path(path).resolve()
    data = load_manifest(path)
    matrices = pose_transforms(data, pose if pose is not None else {'angles': {} if angles is None else angles}, enforce_limits)
    canvas = Image.new('RGBA', tuple(data['source_size']))
    for part in sorted(data['parts'], key=lambda p: p['z_index']):
        with Image.open(asset(path.parent, part['file'])) as source:
            im = source.convert('RGBA')
            ox, oy = part['crop_origin']
            matrix = matrices[part['node']]
            if matrix == IDENTITY:
                canvas.alpha_composite(im, (ox, oy))
            else:
                inv = list(inverse(matrix))
                inv[2] -= ox
                inv[5] -= oy
                layer = im.transform(canvas.size, Image.Transform.AFFINE, inv,
                                     resample=Image.Resampling.BILINEAR)
                canvas.alpha_composite(layer)
    return canvas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "render"))
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--angles", default="{}", help="JSON node-to-relative-angle mapping")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "check":
            data = load_manifest(args.manifest)
            print(json.dumps({"status": "valid", "nodes": len(data["nodes"]),
                              "parts": len(data["parts"]), "visual_qa": "not_checked"}))
        else:
            require(args.output is not None, "render requires --output")
            data = load_manifest(args.manifest)
            root = args.manifest.resolve().parent
            protected = {args.manifest.resolve()}
            for part in data["parts"]:
                protected.add(asset(root, part["file"]))
                if part.get("inferred_region_mask"):
                    protected.add(asset(root, part["inferred_region_mask"]))
            # Keep previews from overwriting source parts, masks or the manifest.
            require(not args.output.resolve().is_relative_to(args.manifest.resolve().parent / "parts")
                    and not args.output.resolve().is_relative_to(args.manifest.resolve().parent / "masks")
                    and args.output.resolve() not in protected, "output would overwrite asset data")
            require(args.output.suffix.lower() == ".png", "output must be PNG")
            image = render(args.manifest, json.loads(args.angles))
            args.output.parent.mkdir(parents=True, exist_ok=True)
            image.save(args.output)
            print(f"Rendered {args.output}; visual QA remains required")
    except (ValueError, OSError, TypeError, KeyError) as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    main()

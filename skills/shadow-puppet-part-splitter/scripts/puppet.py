#!/usr/bin/env python3
"""Validate exported 2D parts and render reference/relative joint poses.

Does not segment images, infer anatomy, or certify visual quality.
"""
import argparse
import json
import math
from pathlib import Path

from PIL import Image


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def pair(value, integer=False):
    return (isinstance(value, list) and len(value) == 2
            and all(number(v) and (not integer or isinstance(v, int)) for v in value))


def asset(root, name):
    require(isinstance(name, str) and name, "asset path must be a nonempty string")
    path = (root / name).resolve()
    require(not Path(name).is_absolute() and path.is_relative_to(root), "asset escapes manifest directory")
    require(path.is_file(), f"asset missing: {name}")
    return path


def index(items, label):
    require(isinstance(items, list) and items, f"{label} must be a nonempty array")
    result = {}
    for item in items:
        require(isinstance(item, dict), f"{label} item must be an object")
        key = item.get("id")
        require(isinstance(key, str) and key and key not in result, f"invalid/duplicate {label} id: {key}")
        result[key] = item
    return result


def load_manifest(path):
    path = Path(path).resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(data, dict), "manifest must be an object")
    require(data.get("schema_version") == "1.0", "unsupported schema_version")
    require(data.get("coordinate_system") == "image-pixels-y-down", "unsupported coordinate_system")
    size = data.get("source_size")
    require(pair(size, True) and min(size) > 0, "invalid source_size")
    nodes = index(data.get("nodes"), "nodes")
    parts = index(data.get("parts"), "parts")
    for key, node in nodes.items():
        require(pair(node.get("pivot_global")), f"{key}: invalid pivot_global")
        parent = node.get("parent")
        require("parent" in node and (parent is None or isinstance(parent, str) and parent in nodes),
                f"{key}: unknown parent")
        bounds = node.get("rotation_range")
        require(pair(bounds) and bounds[0] <= 0 <= bounds[1], f"{key}: invalid rotation_range")
    # Iterative traversal also handles deep hierarchies without recursion failure.
    done = set()
    for key in nodes:
        chain = set()
        cursor = key
        while cursor is not None and cursor not in done:
            require(cursor not in chain, f"parent cycle at {cursor}")
            chain.add(cursor)
            cursor = nodes[cursor]["parent"]
        done.update(chain)
    z_values = set()
    for key, part in parts.items():
        node_id = part.get("node")
        require(isinstance(node_id, str) and node_id in nodes, f"{key}: unknown node")
        for field in ("label", "character_id"):
            require(isinstance(part.get(field), str) and part[field], f"{key}: missing {field}")
        origin, size, pivot = (part.get(f) for f in ("crop_origin", "pixel_size", "pivot_local"))
        require(pair(origin, True), f"{key}: invalid crop_origin")
        require(pair(size, True) and min(size) > 0, f"{key}: invalid pixel_size")
        require(pair(pivot), f"{key}: invalid pivot_local")
        expected = [nodes[node_id]["pivot_global"][i] - origin[i] for i in range(2)]
        require(all(abs(pivot[i] - expected[i]) < 1e-6 for i in range(2)), f"{key}: pivot mismatch")
        z = part.get("z_index")
        require(isinstance(z, int) and not isinstance(z, bool) and z not in z_values,
                f"{key}: invalid/duplicate z_index")
        z_values.add(z)
        image_path = asset(path.parent, part.get("file"))
        with Image.open(image_path) as im:
            require(im.format == "PNG" and im.mode == "RGBA", f"{key}: expected RGBA PNG")
            require(list(im.size) == size, f"{key}: pixel_size mismatch")
            alpha = im.getchannel("A")
            lo, hi = alpha.getextrema()
            require(hi > 0 and lo == 0, f"{key}: part empty or lacks transparent pixels")
            require(isinstance(part.get("inferred"), bool), f"{key}: missing inferred boolean")
            mask_name = part.get("inferred_region_mask")
            if part["inferred"]:
                require(bool(mask_name), f"{key}: inferred mask required")
            else:
                require(mask_name is None, f"{key}: non-inferred part has inferred mask")
            if mask_name:
                with Image.open(asset(path.parent, mask_name)) as mask:
                    require(mask.format == "PNG" and mask.mode == "L" and mask.size == im.size,
                            f"{key}: expected same-size L PNG mask")
                    require(mask.getextrema()[1] > 0, f"{key}: empty inferred mask")
                    require(all(not m or a for m, a in zip(mask.tobytes(), alpha.tobytes())),
                            f"{key}: inferred mask marks transparent pixels")
    return data


IDENTITY = (1, 0, 0, 0, 1, 0)


def multiply(a, b):
    return (a[0]*b[0]+a[1]*b[3], a[0]*b[1]+a[1]*b[4], a[0]*b[2]+a[1]*b[5]+a[2],
            a[3]*b[0]+a[4]*b[3], a[3]*b[1]+a[4]*b[4], a[3]*b[2]+a[4]*b[5]+a[5])


def transforms(data, angles):
    require(isinstance(angles, dict), "angles must be an object")
    nodes = {n["id"]: n for n in data["nodes"]}
    require(all(k in nodes for k in angles), "unknown angle node")
    for key, value in angles.items():
        require(number(value), f"{key}: angle must be finite")
        lo, hi = nodes[key]["rotation_range"]
        require(lo <= value <= hi, f"{key}: angle outside rotation_range")
    result = {None: IDENTITY}
    for key in nodes:
        pending = []
        cursor = key
        while cursor not in result:
            pending.append(cursor)
            cursor = nodes[cursor]["parent"]
        for cursor in reversed(pending):
            node = nodes[cursor]
            x, y = node["pivot_global"]
            theta = math.radians(angles.get(cursor, 0))
            c, s = math.cos(theta), math.sin(theta)
            local = (c, -s, x-c*x+s*y, s, c, y-s*x-c*y)
            result[cursor] = multiply(result[node["parent"]], local)
    return result


def render(path, angles=None):
    path = Path(path).resolve()
    data = load_manifest(path)
    matrices = transforms(data, {} if angles is None else angles)
    canvas = Image.new("RGBA", tuple(data["source_size"]))
    for part in sorted(data["parts"], key=lambda p: p["z_index"]):
        with Image.open(asset(path.parent, part["file"])) as im:
            ox, oy = part["crop_origin"]
            a, b, tx, d, e, ty = matrices[part["node"]]
            if (a, b, tx, d, e, ty) == IDENTITY:
                canvas.alpha_composite(im, (ox, oy))
            else:
                # Inverse rigid transform maps output canvas to cropped input.
                inverse = (a, d, -a*tx-d*ty-ox, b, e, -b*tx-e*ty-oy)
                layer = im.transform(canvas.size, Image.Transform.AFFINE, inverse,
                                     resample=Image.Resampling.BILINEAR)
                canvas = Image.alpha_composite(canvas, layer)
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

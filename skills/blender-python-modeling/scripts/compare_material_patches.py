"""Compare declared midtone patches on registered 8-bit sRGB images."""
import argparse
import json
from pathlib import Path

import numpy as np
from reference_fit.evaluation import color_delta, read, sampled_colors


def compare(reference, render, patches):
    if reference.shape[:2] != render.shape[:2]:
        raise ValueError("Reference and render must share a calibrated canvas")
    for image in (reference, render):
        if image.ndim != 3 or image.shape[2] not in (3, 4) or image.dtype != np.uint8:
            raise ValueError("Supply 8-bit sRGB color images")
    if not isinstance(patches, dict) or not patches:
        raise ValueError("Declare at least one named material patch")
    height, width = reference.shape[:2]
    results = {}
    for name, box in patches.items():
        if not isinstance(box, list) or len(box) != 4 or any(type(v) is not int for v in box):
            raise ValueError(f"Invalid pixel rectangle for {name}")
        left, top, right, bottom = box
        if not (0 <= left < right <= width and 0 <= top < bottom <= height):
            raise ValueError(f"Patch outside canvas or empty: {name}")
        a, b = (image[top:bottom, left:right] for image in (reference, render))
        for crop in (a, b):
            if crop.shape[2] == 4 and (crop[:, :, 3] != 255).any():
                raise ValueError(f"Patch includes transparent pixels: {name}")
        mask = np.ones(a.shape[:2], dtype=np.uint8)
        results[name] = {
            "box": box,
            "reference_srgb": sampled_colors(a, {name: mask})[name]["hex"],
            "render_srgb": sampled_colors(b, {name: mask})[name]["hex"],
            "delta_e76": color_delta(a, b, mask, mask)["delta_e76"],
        }
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("reference", "render", "patches"):
        parser.add_argument(key, type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(read(args.reference), read(args.render),
                             json.loads(args.patches.read_text())), indent=2))

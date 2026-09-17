#!/usr/bin/env python3
"""Deterministic synthetic test for analyze_reference_images.py."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import cv2
import numpy as np

from analyze_reference_images import main


def write_shape(path: Path, width: int, height: int, notch: bool = False) -> None:
    image = np.full((400, 500, 3), 245, dtype=np.uint8)
    x0 = (500 - width) // 2
    y0 = (400 - height) // 2
    cv2.rectangle(image, (x0, y0), (x0 + width, y0 + height), (40, 90, 180), -1)
    if notch:
        cv2.rectangle(image, (x0 + width // 3, y0), (x0 + 2 * width // 3, y0 + height // 5), (245, 245, 245), -1)
    if not cv2.imwrite(str(path), image):
        raise RuntimeError(f"failed to write {path}")


def run_test() -> None:
    with tempfile.TemporaryDirectory(prefix="blender-reference-analysis-") as temp:
        root = Path(temp)
        front = root / "front.png"
        side = root / "side.png"
        top = root / "top.png"
        candidate = root / "candidate.png"
        output = root / "analysis.json"
        debug = root / "debug"
        write_shape(front, 300, 200, notch=True)  # W/H = 1.5
        write_shape(side, 200, 200)  # D/H = 1.0
        write_shape(top, 300, 200)  # W/D = 1.5
        write_shape(candidate, 294, 200, notch=True)

        code = main(
            [
                "--view", f"front={front}",
                "--view", f"side={side}",
                "--view", f"top={top}",
                "--candidate", f"front={candidate}",
                "--output", str(output),
                "--debug-dir", str(debug),
            ]
        )
        assert code == 0
        result = json.loads(output.read_text(encoding="utf-8"))
        fused = result["multi_view_dimensions"]
        assert fused["available"] is True
        assert fused["log_ratio_rms_residual"] < 0.03, fused
        assert abs(fused["dimensions"]["width"] - 1.0) < 0.03, fused
        assert abs(fused["dimensions"]["depth"] - 2 / 3) < 0.04, fused
        assert abs(fused["dimensions"]["height"] - 2 / 3) < 0.04, fused
        comparison = result["render_comparison"]["front"]
        assert comparison["score"] > 0.85, comparison
        assert (debug / "front-reference.png").is_file()
        assert (debug / "front-candidate.png").is_file()
        print(json.dumps({"ok": True, "dimensions": fused["dimensions"], "comparison": comparison}))


if __name__ == "__main__":
    run_test()

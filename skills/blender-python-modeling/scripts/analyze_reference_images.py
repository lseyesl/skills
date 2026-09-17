#!/usr/bin/env python3
"""Extract normalized modeling evidence from AI-generated reference images."""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import cv2
    import numpy as np
except ModuleNotFoundError as exc:  # pragma: no cover - dependency guidance
    raise SystemExit(
        "Missing dependency. Run through the skill project: "
        "uv run --project /path/to/blender-python-modeling "
        "python /path/to/blender-python-modeling/scripts/analyze_reference_images.py ..."
    ) from exc


SCHEMA_VERSION = 1
ORTHOGRAPHIC_LABELS = {
    "front": "front",
    "back": "front",
    "side": "side",
    "left": "side",
    "right": "side",
    "top": "top",
}


@dataclass
class Analysis:
    record: dict[str, Any]
    mask: Any
    contour: Any


def parse_labeled_paths(values: list[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"expected LABEL=PATH, got {value!r}")
        label, raw_path = value.split("=", 1)
        label = label.strip().lower()
        path = Path(raw_path).expanduser().resolve()
        if not label or label in result:
            raise ValueError(f"empty or duplicate label: {label!r}")
        if not path.is_file():
            raise FileNotFoundError(path)
        result[label] = path
    return result


def resize_image(image: Any, max_dimension: int) -> tuple[Any, float]:
    height, width = image.shape[:2]
    scale = min(1.0, max_dimension / max(height, width))
    if scale == 1.0:
        return image, scale
    resized = cv2.resize(
        image,
        (max(1, round(width * scale)), max(1, round(height * scale))),
        interpolation=cv2.INTER_AREA,
    )
    return resized, scale


def clean_mask(mask: Any) -> Any:
    mask = (mask > 0).astype(np.uint8) * 255
    size = max(3, int(round(min(mask.shape[:2]) * 0.008)) | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if count <= 1:
        return mask
    areas = stats[1:, cv2.CC_STAT_AREA]
    largest = int(areas.max())
    kept = np.zeros_like(mask)
    height, width = mask.shape
    for index in range(1, count):
        x, y, w, h, area = stats[index]
        touches_border = x == 0 or y == 0 or x + w >= width or y + h >= height
        if area >= largest * 0.04 and not (touches_border and area < largest):
            kept[labels == index] = 255
    return kept


def foreground_mask(image: Any, alpha: Any | None) -> tuple[Any, str]:
    height, width = image.shape[:2]
    if alpha is not None and int(alpha.max()) - int(alpha.min()) > 16:
        return clean_mask((alpha > 16).astype(np.uint8) * 255), "alpha"

    border = np.concatenate(
        (image[0], image[-1], image[:, 0], image[:, -1]), axis=0
    ).astype(np.float32)
    background = np.median(border, axis=0)
    distance = np.linalg.norm(image.astype(np.float32) - background, axis=2)
    upper = max(1.0, float(np.percentile(distance, 99)))
    distance_u8 = np.clip(distance * 255.0 / upper, 0, 255).astype(np.uint8)
    _, mask = cv2.threshold(distance_u8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = clean_mask(mask)
    occupancy = float(np.count_nonzero(mask)) / mask.size

    if occupancy < 0.01 or occupancy > 0.92:
        grabcut_mask = np.full((height, width), cv2.GC_PR_BGD, dtype=np.uint8)
        inset_x = max(1, round(width * 0.02))
        inset_y = max(1, round(height * 0.02))
        rectangle = (inset_x, inset_y, width - 2 * inset_x, height - 2 * inset_y)
        bg_model = np.zeros((1, 65), np.float64)
        fg_model = np.zeros((1, 65), np.float64)
        cv2.grabCut(
            image,
            grabcut_mask,
            rectangle,
            bg_model,
            fg_model,
            5,
            cv2.GC_INIT_WITH_RECT,
        )
        mask = np.where(
            (grabcut_mask == cv2.GC_FGD) | (grabcut_mask == cv2.GC_PR_FGD),
            255,
            0,
        ).astype(np.uint8)
        return clean_mask(mask), "grabcut"
    return mask, "border-color-distance"


def largest_contour(mask: Any) -> Any:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        raise ValueError("no foreground contour detected")
    return max(contours, key=cv2.contourArea)


def iou(first: Any, second: Any) -> float:
    intersection = np.count_nonzero((first > 0) & (second > 0))
    union = np.count_nonzero((first > 0) | (second > 0))
    return float(intersection / union) if union else 1.0


def symmetry_scores(mask: Any, bbox: tuple[int, int, int, int]) -> dict[str, float]:
    x, y, width, height = bbox
    crop = mask[y : y + height, x : x + width]
    return {
        "vertical": round(iou(crop, cv2.flip(crop, 1)), 4),
        "horizontal": round(iou(crop, cv2.flip(crop, 0)), 4),
    }


def dominant_line_angles(image: Any, mask: Any) -> list[dict[str, float]]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edges = cv2.bitwise_and(edges, mask)
    minimum = max(12, round(min(image.shape[:2]) * 0.08))
    lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180,
        threshold=max(15, minimum // 2),
        minLineLength=minimum,
        maxLineGap=max(4, minimum // 6),
    )
    if lines is None:
        return []
    bins = np.zeros(36, dtype=np.float64)
    for x1, y1, x2, y2 in lines[:, 0]:
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180.0
        length = math.hypot(x2 - x1, y2 - y1)
        bins[int(angle // 5) % 36] += length
    total = float(bins.sum()) or 1.0
    selected: list[dict[str, float]] = []
    for index in np.argsort(bins)[::-1]:
        if bins[index] <= 0:
            break
        angle = index * 5.0 + 2.5
        if all(abs(((angle - item["angle_deg"] + 90) % 180) - 90) >= 12 for item in selected):
            selected.append(
                {"angle_deg": round(angle, 1), "support": round(float(bins[index] / total), 4)}
            )
        if len(selected) == 4:
            break
    return selected


def palette_hex(image: Any, mask: Any, count: int = 3) -> list[dict[str, Any]]:
    pixels = image[mask > 0]
    if len(pixels) == 0:
        return []
    if len(pixels) > 12000:
        indices = np.linspace(0, len(pixels) - 1, 12000, dtype=np.int32)
        pixels = pixels[indices]
    data = pixels.astype(np.float32)
    clusters = min(count, len(data))
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
    cv2.setRNGSeed(0)
    compactness, labels, centers = cv2.kmeans(
        data, clusters, None, criteria, 5, cv2.KMEANS_PP_CENTERS
    )
    del compactness
    counts = np.bincount(labels.ravel(), minlength=clusters)
    result = []
    for index in np.argsort(counts)[::-1]:
        blue, green, red = [int(round(value)) for value in centers[index]]
        result.append(
            {
                "hex": f"#{red:02x}{green:02x}{blue:02x}",
                "fraction": round(float(counts[index] / counts.sum()), 4),
            }
        )
    return result


def normalized_contour(contour: Any, bbox: tuple[int, int, int, int]) -> list[list[float]]:
    perimeter = cv2.arcLength(contour, True)
    simplified = cv2.approxPolyDP(contour, max(1.0, perimeter * 0.003), True).reshape(-1, 2)
    if len(simplified) > 128:
        indices = np.linspace(0, len(simplified) - 1, 128, dtype=np.int32)
        simplified = simplified[indices]
    x, y, width, height = bbox
    center_x = x + width / 2.0
    center_y = y + height / 2.0
    scale = float(max(width, height))
    return [
        [round((float(px) - center_x) / scale, 6), round((center_y - float(py)) / scale, 6)]
        for px, py in simplified
    ]


def hole_count(mask: Any) -> int:
    _, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return 0
    return int(sum(1 for item in hierarchy[0] if item[3] >= 0))


def normalized_mask(mask: Any, bbox: tuple[int, int, int, int], size: int = 256) -> Any:
    x, y, width, height = bbox
    crop = mask[y : y + height, x : x + width]
    scale = (size - 8) / max(width, height)
    resized = cv2.resize(
        crop,
        (max(1, round(width * scale)), max(1, round(height * scale))),
        interpolation=cv2.INTER_NEAREST,
    )
    canvas = np.zeros((size, size), dtype=np.uint8)
    offset_x = (size - resized.shape[1]) // 2
    offset_y = (size - resized.shape[0]) // 2
    canvas[offset_y : offset_y + resized.shape[0], offset_x : offset_x + resized.shape[1]] = resized
    return canvas


def analyze_image(label: str, path: Path, max_dimension: int = 1600) -> Analysis:
    raw = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if raw is None:
        raise ValueError(f"cannot read image: {path}")
    alpha = raw[:, :, 3] if raw.ndim == 3 and raw.shape[2] == 4 else None
    image = raw[:, :, :3] if raw.ndim == 3 else cv2.cvtColor(raw, cv2.COLOR_GRAY2BGR)
    image, resize_scale = resize_image(image, max_dimension)
    if alpha is not None and resize_scale != 1.0:
        alpha = cv2.resize(alpha, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_AREA)

    mask, method = foreground_mask(image, alpha)
    contour = largest_contour(mask)
    x, y, width, height = cv2.boundingRect(contour)
    area = float(cv2.contourArea(contour))
    box_area = float(width * height) or 1.0
    occupancy = float(np.count_nonzero(mask)) / mask.size
    border_pixels = np.concatenate((mask[0], mask[-1], mask[:, 0], mask[:, -1]))
    border_contact = float(np.count_nonzero(border_pixels)) / len(border_pixels)
    confidence = max(
        0.0,
        min(1.0, 0.5 * min(1.0, area / box_area) + 0.5 * (1.0 - min(1.0, border_contact * 10))),
    )
    angles = dominant_line_angles(image, mask)
    orthogonal_support = sum(
        item["support"]
        for item in angles
        if min(abs(item["angle_deg"]), abs(item["angle_deg"] - 90), abs(item["angle_deg"] - 180)) <= 10
    )
    canonical = ORTHOGRAPHIC_LABELS.get(label)
    projection = "orthographic_like" if canonical and orthogonal_support >= 0.35 else "unknown"

    record = {
        "label": label,
        "path": str(path),
        "image_size": {"width": image.shape[1], "height": image.shape[0]},
        "segmentation": {
            "method": method,
            "confidence": round(confidence, 4),
            "occupancy": round(occupancy, 4),
            "border_contact": round(border_contact, 4),
        },
        "silhouette": {
            "bbox_px": {"x": x, "y": y, "width": width, "height": height},
            "aspect_width_over_height": round(width / height, 6),
            "solidity_in_bbox": round(area / box_area, 4),
            "holes": hole_count(mask),
            "symmetry": symmetry_scores(mask, (x, y, width, height)),
            "normalized_contour": normalized_contour(contour, (x, y, width, height)),
        },
        "line_evidence": {"dominant_angles": angles},
        "palette": palette_hex(image, mask),
        "camera_hypothesis": {
            "projection": projection,
            "confidence": round(min(0.7, orthogonal_support), 4),
            "note": "evidence only; AI imagery does not provide calibrated camera metadata",
        },
        "scale": {"mode": "normalized", "absolute_known": False},
    }
    return Analysis(record, normalized_mask(mask, (x, y, width, height)), contour)


def fuse_dimensions(analyses: dict[str, Analysis]) -> dict[str, Any]:
    equations: list[list[float]] = []
    observations: list[float] = []
    used: list[str] = []
    seen_canonical: set[str] = set()
    for label, analysis in analyses.items():
        canonical = ORTHOGRAPHIC_LABELS.get(label)
        if canonical is None or canonical in seen_canonical:
            continue
        if analysis.record["camera_hypothesis"]["projection"] != "orthographic_like":
            continue
        ratio = analysis.record["silhouette"]["aspect_width_over_height"]
        if canonical == "front":
            row = [1.0, 0.0, -1.0]  # log(W/H)
        elif canonical == "side":
            row = [0.0, 1.0, -1.0]  # log(D/H)
        else:
            row = [1.0, -1.0, 0.0]  # log(W/D)
        equations.append(row)
        observations.append(math.log(ratio))
        used.append(label)
        seen_canonical.add(canonical)

    if len(equations) < 2:
        return {
            "available": False,
            "reason": "need at least two orthographic-like labeled views among front/side/top",
            "used_views": used,
        }
    matrix = np.array(equations + [[1.0, 1.0, 1.0]], dtype=np.float64)
    vector = np.array(observations + [0.0], dtype=np.float64)
    solution, _, _, _ = np.linalg.lstsq(matrix, vector, rcond=None)
    dimensions = np.exp(solution)
    dimensions /= dimensions.max()
    residuals = np.array(equations) @ solution - np.array(observations)
    rms = float(np.sqrt(np.mean(residuals**2)))
    warnings = []
    if rms > 0.12:
        warnings.append("orthographic ratios contradict one another; keep alternative proportions")
    return {
        "available": True,
        "mode": "normalized",
        "largest_dimension": 1.0,
        "dimensions": {
            "width": round(float(dimensions[0]), 6),
            "depth": round(float(dimensions[1]), 6),
            "height": round(float(dimensions[2]), 6),
        },
        "used_views": used,
        "log_ratio_rms_residual": round(rms, 6),
        "confidence": round(max(0.0, min(0.9, 0.45 + 0.15 * len(used) - rms)), 4),
        "warnings": warnings,
    }


def compare(reference: Analysis, candidate: Analysis) -> dict[str, Any]:
    silhouette_iou = iou(reference.mask, candidate.mask)
    shape_distance = float(cv2.matchShapes(reference.contour, candidate.contour, cv2.CONTOURS_MATCH_I1, 0.0))
    reference_aspect = reference.record["silhouette"]["aspect_width_over_height"]
    candidate_aspect = candidate.record["silhouette"]["aspect_width_over_height"]
    aspect_log_error = abs(math.log(candidate_aspect / reference_aspect))
    score = (
        0.55 * silhouette_iou
        + 0.30 * math.exp(-5.0 * shape_distance)
        + 0.15 * math.exp(-3.0 * aspect_log_error)
    )
    return {
        "silhouette_iou": round(silhouette_iou, 4),
        "shape_distance": round(shape_distance, 6),
        "aspect_log_error": round(aspect_log_error, 6),
        "score": round(max(0.0, min(1.0, score)), 4),
        "note": "camera mismatch can lower this score even when geometry is correct",
    }


def save_debug_overlay(path: Path, analysis: Analysis, output: Path) -> None:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    target = analysis.record["image_size"]
    if image.shape[1] != target["width"] or image.shape[0] != target["height"]:
        image = cv2.resize(
            image,
            (target["width"], target["height"]),
            interpolation=cv2.INTER_AREA,
        )
    bbox = analysis.record["silhouette"]["bbox_px"]
    x, y, width, height = (bbox[key] for key in ("x", "y", "width", "height"))
    cv2.rectangle(image, (x, y), (x + width, y + height), (0, 255, 0), 2)
    contour = analysis.contour
    cv2.drawContours(image, [contour], -1, (0, 0, 255), 2)
    cv2.putText(
        image,
        analysis.record["label"],
        (max(5, x), max(20, y - 8)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2,
        cv2.LINE_AA,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), image)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--view", action="append", default=[], metavar="LABEL=PATH", help="reference view")
    parser.add_argument("--candidate", action="append", default=[], metavar="LABEL=PATH", help="matching Blender render")
    parser.add_argument("--output", required=True, type=Path, help="JSON output path")
    parser.add_argument("--debug-dir", type=Path, help="optional overlay directory")
    parser.add_argument("--max-dimension", type=int, default=1600)
    parser.add_argument("--known-largest-dimension", type=float, help="optional user-approved scale anchor")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.view:
        raise SystemExit("at least one --view LABEL=PATH is required")
    references = parse_labeled_paths(args.view)
    candidates = parse_labeled_paths(args.candidate)
    unknown_candidates = sorted(set(candidates) - set(references))
    if unknown_candidates:
        raise SystemExit(f"candidate labels have no reference: {unknown_candidates}")
    if args.known_largest_dimension is not None and args.known_largest_dimension <= 0:
        raise SystemExit("--known-largest-dimension must be positive")

    analyses = {
        label: analyze_image(label, path, args.max_dimension)
        for label, path in references.items()
    }
    candidate_analyses = {
        label: analyze_image(label, path, args.max_dimension)
        for label, path in candidates.items()
    }
    fused = fuse_dimensions(analyses)
    if args.known_largest_dimension is not None and fused.get("available"):
        fused["mode"] = "anchored"
        fused["largest_dimension"] = args.known_largest_dimension
        fused["dimensions"] = {
            key: round(value * args.known_largest_dimension, 6)
            for key, value in fused["dimensions"].items()
        }
    if args.known_largest_dimension is not None:
        for analysis in analyses.values():
            analysis.record["scale"] = {
                "mode": "anchored",
                "absolute_known": True,
                "known_largest_dimension": args.known_largest_dimension,
            }

    result = {
        "schema_version": SCHEMA_VERSION,
        "scale_policy": {
            "mode": "anchored" if args.known_largest_dimension is not None else "normalized",
            "absolute_dimension_known": args.known_largest_dimension is not None,
            "warning": None
            if args.known_largest_dimension is not None
            else "absolute scale is unknowable from uncalibrated AI images",
        },
        "views": {label: analysis.record for label, analysis in analyses.items()},
        "multi_view_dimensions": fused,
        "render_comparison": {
            label: compare(analyses[label], analysis)
            for label, analysis in candidate_analyses.items()
        },
        "limitations": [
            "hidden geometry is not reconstructed",
            "camera estimates are uncalibrated evidence",
            "AI-generated views may contradict one another",
            "silhouette agreement does not prove correct topology or depth",
        ],
    }

    args.output = args.output.expanduser().resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.debug_dir:
        debug_dir = args.debug_dir.expanduser().resolve()
        for label, path in references.items():
            save_debug_overlay(path, analyses[label], debug_dir / f"{label}-reference.png")
        for label, path in candidates.items():
            save_debug_overlay(path, candidate_analyses[label], debug_dir / f"{label}-candidate.png")
    print(json.dumps({"output": str(args.output), "views": sorted(analyses), "ok": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Check the final review bundle against the exported file and its fixed-view records."""
import json
from pathlib import Path

from reference_review import require_design_review
from reference_preparation import _file, require_preparation


def check_delivery(ledger, ledger_path, review_path, model_path):
    if not review_path or not model_path:
        raise ValueError("Final delivery requires --review and --model")
    base = review_path.resolve().parent
    bundle = json.loads(review_path.read_text())
    if Path(_file(bundle["ledger"], base)[0]) != ledger_path.resolve():
        raise ValueError("Wrong module ledger")
    model, digest = _file(bundle["model"], base)
    if Path(model) != model_path.resolve():
        raise ValueError("Reviewed model differs from requested delivery")
    prep = Path(_file(bundle["preparation"], base)[0])
    decision = json.loads(prep.read_text())
    mode = {"user_waived": "waived", "no_reference": "original"}.get(decision["route"], "reference")
    require_preparation(prep, ledger["task_id"], mode=mode)
    if mode == "original" and any(m.get("evidence") == "observed" for m in ledger["modules"]):
        raise ValueError("Observed reference modules require reference preparation")
    guides = {_file(item, prep.parent) for item in decision["construction_images"]}
    controlling = {}
    covered = set()
    views = bundle["views"]
    if not isinstance(views, list) or not views:
        raise ValueError("Missing fixed-view comparisons")
    for view in views:
        if guides:
            guide = _file(view["reference"], base)
            name = view["name"]
            if not isinstance(name, str) or not name.strip() or name in controlling:
                raise ValueError("A unique construction view name is required")
            controlling[name] = {"image": guide[0]}
            covered.add(guide)
        if view["model_sha256"] != digest:
            raise ValueError("Final render record is for another model revision")
        cameras = []
        for stage in ("before", "after"):
            shot = view[stage]
            _file(shot["image"], base)
            camera = shot["camera"]
            for key in ("world_matrix", "projection_matrix", "resolution"):
                size = 2 if key == "resolution" else 16
                if not isinstance(camera[key], list) or len(camera[key]) != size or not all(
                        type(v) in (float, int) for v in camera[key]):
                    raise ValueError("Invalid recorded camera " + key)
            cameras.append(camera)
        if cameras[0] != cameras[1]:
            raise ValueError("Baseline and final camera settings differ")
        _file(view["comparison"], base)
    if covered != guides:
        raise ValueError("Final views must cover the reviewed construction guides")
    if len(guides) > 1:
        design, _ = _file(bundle["multiview_review"], base)
        require_design_review({"views": controlling, "multiview_review": design}, base)
        if json.loads(Path(design).read_text())["readiness"] != "passed":
            raise ValueError("Partial construction review cannot certify a final whole-model match")
    regions = bundle["regions"]
    required = {m["id"] for m in ledger["modules"] if m.get("required")}
    if not required or not isinstance(regions, dict) or not required <= regions.keys():
        raise ValueError("Missing required region reviews")
    for name, region in regions.items():
        if region["state"] not in ("reviewed", "residual"):
            raise ValueError("Open work remains in " + name)
        for field in ("local", "surroundings"):
            _file(region[field], base)
        if region["state"] == "residual":
            _file(region["attempt_log"], base)
            if not isinstance(region["reason"], str) or not region["reason"].strip():
                raise ValueError("Missing residual diagnosis for " + name)
    if bundle["actionable_items"] != []:
        raise ValueError("Whole-model review still has actionable items")
    for key in ("structural_report", "contact_sheet", "perspective_view"):
        path, _ = _file(bundle[key], base)
        if Path(path) != (ledger_path.resolve().parent / ledger["final_review"][key]).resolve():
            raise ValueError("Final review points to different " + key)
    return {"model_sha256": digest, "fixed_views": len(views),
            "residuals": [name for name, region in regions.items() if region["state"] == "residual"]}

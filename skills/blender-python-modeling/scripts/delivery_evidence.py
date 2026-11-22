"""Check the final review bundle against the exported file and its fixed-view records."""
import json
from pathlib import Path

from reference_review import require_design_review
from reference_preparation import _file, require_preparation, selected_style


def check_projected_features(module, region, base, digest):
    """Validate declared cross-angle inspections; a reviewer judges the renders."""
    features = module.get("projected_features", [])
    if not features:
        return
    if not isinstance(features, list) or not all(isinstance(f, str) and f.strip() for f in features):
        raise ValueError("Declare the projected feature names for " + module["id"])
    review = region.get("projection_review", {})
    if review.get("model_sha256") != digest:
        raise ValueError("Missing or stale projection review for " + module["id"])
    comparisons = set()
    for angle in ("front", "oblique", "profile"):
        shot = review.get("views", {}).get(angle, {})
        _, image_hash = _file(shot.get("comparison"), base)
        if image_hash in comparisons:
            raise ValueError("Projection checks require distinct crops for each angle")
        comparisons.add(image_hash)
        for feature in features:
            check = shot.get("features", {}).get(feature, {})
            if not isinstance(check.get("finding"), str) or not check["finding"].strip():
                raise ValueError(f"Describe {angle} placement and readability of {feature}")
            if check.get("status") == "passed":
                continue
            if check.get("status") == "occluded":
                if isinstance(check.get("occluder"), str) and check["occluder"].strip():
                    continue
                raise ValueError(f"Identify what occludes {feature} in {angle}")
            if check.get("status") == "residual" and any(
                    issue.get("status") == "exhausted" and issue.get("projected_feature") == feature
                    and issue.get("projection_angle") == angle for issue in region.get("visual_findings", [])):
                continue
            raise ValueError(f"Reopen {feature} in {angle}: review missing or regression unresolved")


def check_style_sample(bundle, base, digest):
    decision_path = Path(_file(bundle["preparation"], base)[0])
    style = selected_style(json.loads(decision_path.read_text()))
    if style is None:
        return
    review = bundle.get("style_review", {})
    if (review.get("model_sha256"), review.get("id"), review.get("region")) != (
            digest, style["id"], style["region"]):
        raise ValueError("Missing or stale style review for the selected region and model")
    evidence = [_file(review.get(key), base)[1] for key in ("reference_crop", "clay", "material")]
    if len(set(evidence)) != len(evidence):
        raise ValueError("Use distinct reference, clay and material samples")
    for channel in ("shape", "surface"):
        result = review.get(channel, {})
        if result.get("status") != "passed" or not str(result.get("finding") or "").strip():
            raise ValueError(f"Reopen style {channel} for {style['region']}")


def check_refinement(ledger, ledger_path, review_path, model_path):
    """Check known visual defects even when source provenance prevents certification."""
    if not review_path or not model_path:
        raise ValueError("Refinement review requires --review and --model")
    base = review_path.resolve().parent
    bundle = json.loads(review_path.read_text())
    model, digest = _file(bundle["model"], base)
    if Path(model) != model_path.resolve() or Path(_file(bundle["ledger"], base)[0]) != ledger_path.resolve():
        raise ValueError("Refinement review is for a different ledger or model")
    regions = bundle["regions"]
    required = {m["id"] for m in ledger["modules"] if m.get("required")}
    if not required or not isinstance(regions, dict) or not required <= regions.keys():
        raise ValueError("Missing required region reviews")
    if bundle["actionable_items"] != []:
        raise ValueError("Continue the remaining actionable items")
    for name, region in regions.items():
        findings = region.get("visual_findings", [])
        if not isinstance(findings, list) or region["state"] not in ("reviewed", "residual"):
            raise ValueError("Open or malformed visual review: " + name)
        if region["state"] == "residual" and not findings:
            raise ValueError("Reopen " + name + ": residual needs a specific finding and repair evidence")
        for field in ("local", "surroundings"):
            _file(region[field], base)
        residual = False
        for finding in findings:
            for key in ("symptom", "view", "change", "result"):
                if not isinstance(finding.get(key), str) or not finding[key].strip():
                    raise ValueError("Missing " + key + " for " + name)
            if finding["view"] not in {v.get("name") for v in bundle["views"]}:
                raise ValueError("Missing controlling comparison view for " + name)
            if finding.get("model_sha256") != digest:
                raise ValueError("Recheck " + name + " against the current model")
            source = finding.get("reference_status")
            if source not in ("existing_sufficient", "supplement_reviewed"):
                raise ValueError("Use concept-multiview-sheet for missing or unclear views: " + name)
            reference = _file(finding["reference"], base)
            if source == "supplement_reviewed":
                record_path = Path(_file(finding["generation_record"], base)[0])
                record = json.loads(record_path.read_text())
                if reference not in {_file(item, record_path.parent) for item in record["outputs"]}:
                    raise ValueError("Generation record does not include the reviewed supplement for " + name)
            if _file(finding["before"], base)[1] == _file(finding["after"], base)[1]:
                raise ValueError("Provide the tested repair candidate or rejected trial for " + name)
            state = finding["status"]
            if state not in ("fixed", "exhausted"):
                raise ValueError("Continue repair: " + name)
            if state == "exhausted":
                if not isinstance(finding.get("reopen_when"), str) or not finding["reopen_when"].strip():
                    raise ValueError("Missing condition to revisit " + name)
                residual = True
        if residual != (region["state"] == "residual"):
            raise ValueError("Region status contradicts visual findings: " + name)
        if residual:
            _file(region["attempt_log"], base)
            if not isinstance(region.get("reason"), str) or not region["reason"].strip():
                raise ValueError("Missing residual diagnosis for " + name)
    for module in ledger["modules"]:
        if module.get("projected_features"):
            check_projected_features(module, regions[module["id"]], base, digest)
    check_style_sample(bundle, base, digest)
    return digest


def check_original_comparisons(bundle, base, originals, digest, modules):
    """Require direct model comparisons for source images absent from fixed construction views."""
    if not originals:
        return
    required = {(m["id"], feature) for m in modules
                if m.get("required") and m.get("evidence") == "observed"
                for feature in m.get("signature_features", [])}
    reviewed = set()
    seen = set()
    for entry in bundle.get("original_comparisons", []):
        source = _file(entry["source"], base)
        if source not in originals or entry.get("model_sha256") != digest:
            raise ValueError("Compare the current model directly with the original source")
        seen.add(source)
        if not str(entry.get("registration") or "").strip():
            raise ValueError("Describe the source-view pose and camera registration")
        images = [source] + [_file(entry[key], base) for key in ("clay", "final_render", "comparison")]
        if len({sha for _, sha in images}) != len(images):
            raise ValueError("Provide distinct original, clay, final render and comparison evidence")
        for finding in entry["features"]:
            if finding.get("status") != "matched" or not str(finding.get("finding") or "").strip():
                raise ValueError("Reopen the original-source feature: " + str(finding.get("feature")))
            reviewed.add((finding["module"], finding["feature"]))
    if seen != originals or required - reviewed:
        raise ValueError("Missing direct original-source comparisons or observed signature features")


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
    if mode == "reference" and decision.get("facts", {}).get("scope", "whole_model") == "whole_model":
        originals = {_file(item, prep.parent) for item in decision["source_images"]}
        # A source already used in a fixed view has its own comparison above.
        missing = originals - covered
        check_original_comparisons(bundle, base, missing, digest,
                                   ledger["modules"] if missing == originals else [])
    if len(guides) > 1:
        design, _ = _file(bundle["multiview_review"], base)
        require_design_review({"views": controlling, "multiview_review": design}, base)
        if json.loads(Path(design).read_text())["readiness"] != "passed":
            raise ValueError("Partial construction review cannot certify a final whole-model match")
    regions = bundle["regions"]
    for key in ("structural_report", "contact_sheet", "perspective_view"):
        path, _ = _file(bundle[key], base)
        if Path(path) != (ledger_path.resolve().parent / ledger["final_review"][key]).resolve():
            raise ValueError("Final review points to different " + key)
    return {"model_sha256": digest, "fixed_views": len(views),
            "residuals": [name for name, region in regions.items() if region["state"] == "residual"]}

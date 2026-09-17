"""Validate reference-module coverage and completion claims.

This is a bookkeeping gate, not a visual similarity evaluator.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


STAGES = {"blockout", "feature-complete", "final"}
STATUSES = {"missing", "blockout", "simplified", "matched", "not-applicable"}
PRIORITIES = {"primary", "secondary", "tertiary"}
EVIDENCE = {"observed", "inferred", "unknown"}


def validate_ledger(payload: dict[str, Any], stage_override: str | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    stage = stage_override or payload.get("target_stage")
    if stage not in STAGES:
        errors.append(f"target_stage must be one of {sorted(STAGES)}")

    modules = payload.get("modules")
    if not isinstance(modules, list) or not modules:
        errors.append("modules must be a non-empty list")
        modules = []

    seen_ids: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(modules):
        prefix = f"modules[{index}]"
        if not isinstance(raw, dict):
            errors.append(f"{prefix} must be an object")
            continue
        module_id = raw.get("id")
        if not isinstance(module_id, str) or not module_id.strip():
            errors.append(f"{prefix}.id must be a non-empty string")
            module_id = f"invalid-{index}"
        elif module_id in seen_ids:
            errors.append(f"duplicate module id: {module_id}")
        seen_ids.add(module_id)

        status = raw.get("status")
        priority = raw.get("priority")
        evidence = raw.get("evidence")
        required = raw.get("required") is True
        expected = raw.get("expected_instances", 1)
        implemented = raw.get("implemented_instances", 0)
        features = raw.get("signature_features")
        matched_features = raw.get("matched_signature_features")
        objects = raw.get("implementation_objects")
        approved = raw.get("user_approved_simplification") is True

        if status not in STATUSES:
            errors.append(f"{module_id}: invalid status {status!r}")
        if priority not in PRIORITIES:
            errors.append(f"{module_id}: invalid priority {priority!r}")
        if evidence not in EVIDENCE:
            errors.append(f"{module_id}: invalid evidence {evidence!r}")
        if not isinstance(expected, int) or expected < 1:
            errors.append(f"{module_id}: expected_instances must be a positive integer")
            expected = 1
        if not isinstance(implemented, int) or implemented < 0:
            errors.append(f"{module_id}: implemented_instances must be a non-negative integer")
            implemented = 0
        if not isinstance(features, list) or not features or not all(isinstance(item, str) and item.strip() for item in features):
            errors.append(f"{module_id}: signature_features must contain at least one non-empty item")
            features = []
        if not isinstance(matched_features, list) or not all(isinstance(item, str) and item.strip() for item in matched_features):
            errors.append(f"{module_id}: matched_signature_features must be a list of non-empty strings")
            matched_features = []
        unknown_features = sorted(set(matched_features) - set(features))
        if unknown_features:
            errors.append(f"{module_id}: matched_signature_features contains unknown items {unknown_features}")
        if status in {"blockout", "simplified", "matched"} and (not isinstance(objects, list) or not objects):
            errors.append(f"{module_id}: implemented status requires implementation_objects")
        if status == "matched" and implemented < expected:
            errors.append(f"{module_id}: matched but implemented_instances {implemented} < expected_instances {expected}")
        if status == "matched" and set(matched_features) != set(features):
            missing_features = sorted(set(features) - set(matched_features))
            errors.append(f"{module_id}: matched status requires every signature feature; missing {missing_features}")
        if status == "simplified" and not str(raw.get("simplification_reason", "")).strip():
            errors.append(f"{module_id}: simplified status requires simplification_reason")
        if required and status == "not-applicable":
            errors.append(f"{module_id}: required module cannot be not-applicable")
        if evidence == "observed" and not raw.get("source_views"):
            errors.append(f"{module_id}: observed module requires source_views")

        normalized.append({
            "id": module_id,
            "required": required,
            "priority": priority,
            "status": status,
            "approved": approved,
        })

    required_modules = [item for item in normalized if item["required"]]
    counts = Counter(item["status"] for item in required_modules)
    unapproved_simplified = [
        item["id"] for item in required_modules
        if item["status"] == "simplified" and not item["approved"]
    ]
    missing = [item["id"] for item in required_modules if item["status"] == "missing"]

    if stage == "blockout":
        errors.extend(
            f"{item['id']}: required primary module is missing at blockout gate"
            for item in required_modules
            if item["priority"] == "primary" and item["status"] == "missing"
        )
    elif stage == "feature-complete":
        errors.extend(
            f"{item['id']}: primary module must be matched at feature-complete gate"
            for item in required_modules
            if item["priority"] == "primary" and item["status"] != "matched"
        )
        errors.extend(
            f"{item['id']}: required primary/secondary module is missing at feature-complete gate"
            for item in required_modules
            if item["priority"] in {"primary", "secondary"} and item["status"] == "missing"
        )
    elif stage == "final":
        errors.extend(f"{module_id}: required module is missing at final gate" for module_id in missing)
        errors.extend(
            f"{module_id}: simplified module lacks explicit user approval at final gate"
            for module_id in unapproved_simplified
        )
        errors.extend(
            f"{item['id']}: blockout status cannot pass the final gate"
            for item in required_modules
            if item["status"] == "blockout"
        )

    required_count = len(required_modules)
    present_count = sum(counts[name] for name in ("matched", "simplified", "blockout"))
    matched_count = counts["matched"]
    report = {
        "ok": not errors,
        "task_id": payload.get("task_id"),
        "target_stage": stage,
        "required_modules": required_count,
        "counts": {name: counts[name] for name in ("matched", "simplified", "blockout", "missing", "not-applicable")},
        "presence_coverage": round(present_count / required_count, 4) if required_count else 0.0,
        "full_fidelity_coverage": round(matched_count / required_count, 4) if required_count else 0.0,
        "unapproved_simplified": unapproved_simplified,
        "errors": errors,
        "warnings": warnings,
        "ready_to_claim_complete": stage == "final" and not errors,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--stage", choices=sorted(STAGES))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.ledger.read_text(encoding="utf-8"))
    report = validate_ledger(payload, args.stage)
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()

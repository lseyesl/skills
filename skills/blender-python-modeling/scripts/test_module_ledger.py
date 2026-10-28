"""Deterministic tests for the module-ledger completion gate."""

from __future__ import annotations

import importlib.util
import copy
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_module_ledger.py")
SPEC = importlib.util.spec_from_file_location("validate_module_ledger", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def item(module_id: str, priority: str, status: str, *, approved: bool = False, expected: int = 1, implemented: int = 1) -> dict:
    features = ["recognizable feature"]
    return {
        "id": module_id,
        "name": module_id,
        "evidence": "observed",
        "source_views": ["front"],
        "priority": priority,
        "required": True,
        "expected_instances": expected,
        "implemented_instances": implemented,
        "signature_features": features,
        "matched_signature_features": features if status == "matched" else [],
        "feature_reviews": [{"feature": features[0], "status": "matched",
                             "reference": "reference.png#hull-outline", "candidate": "front.png",
                             "view": "front", "comparison": "Outline and attachment landmarks agree; hidden rear is inferred."}]
                            if status == "matched" else [],
        "status": status,
        "implementation_objects": [] if status == "missing" else [f"GEO_{module_id}"],
        "user_approved_simplification": approved,
        "simplification_reason": "approved output constraint" if status == "simplified" else "",
    }


def ledger(stage: str, modules: list[dict]) -> dict:
    return {"schema_version": 1, "task_id": "test", "target_stage": stage, "modules": modules,
            "final_review": {"status": "passed", "structural_report": "quality.json",
                             "contact_sheet": "views.png", "perspective_view": "hero.png",
                             "unresolved_issues": []}}


def main() -> None:
    blockout = MODULE.validate_ledger(ledger("blockout", [item("hull", "primary", "blockout"), item("vent", "secondary", "missing", implemented=0)]))
    assert blockout["ok"] and not blockout["ready_to_claim_complete"]

    unapproved = MODULE.validate_ledger(ledger("final", [item("hull", "primary", "matched"), item("seat", "secondary", "simplified")]))
    assert not unapproved["ok"] and unapproved["unapproved_simplified"] == ["seat"]

    approved = MODULE.validate_ledger(ledger("final", [item("hull", "primary", "matched"), item("seat", "secondary", "simplified", approved=True)]))
    assert approved["ok"] and approved["ready_to_claim_complete"]
    assert approved["presence_coverage"] == 1.0 and approved["full_fidelity_coverage"] == 0.5

    repeated = MODULE.validate_ledger(ledger("final", [item("thrusters", "secondary", "matched", expected=2, implemented=1)]))
    assert not repeated["ok"]

    valid = ledger("final", [item("leaf", "primary", "matched")])
    # Old label-only ledgers must not claim a visual pass.
    labels_only = copy.deepcopy(valid)
    del labels_only["modules"][0]["feature_reviews"]
    assert not MODULE.validate_ledger(labels_only)["ready_to_claim_complete"]

    incomplete = copy.deepcopy(valid)
    incomplete["modules"][0]["signature_features"].append("readable branching veins")
    incomplete["modules"][0]["matched_signature_features"].append("readable branching veins")
    assert not MODULE.validate_ledger(incomplete)["ok"]

    for field in ("reference", "candidate", "view", "comparison"):
        no_evidence = copy.deepcopy(valid)
        no_evidence["modules"][0]["feature_reviews"][0][field] = "  "
        assert not MODULE.validate_ledger(no_evidence)["ok"], field

    rejected = copy.deepcopy(valid)
    rejected["modules"][0]["feature_reviews"][0]["status"] = "rejected"
    assert not MODULE.validate_ledger(rejected)["ok"]

    stale = copy.deepcopy(valid)
    stale["modules"][0]["review_invalidated"] = "User reports no visible secondary veins"
    assert not MODULE.validate_ledger(stale)["ready_to_claim_complete"]

    no_final = copy.deepcopy(valid)
    del no_final["final_review"]
    assert not MODULE.validate_ledger(no_final)["ready_to_claim_complete"]
    for field in ("structural_report", "contact_sheet", "perspective_view", "unresolved_issues"):
        no_final = copy.deepcopy(valid)
        del no_final["final_review"][field]
        assert not MODULE.validate_ledger(no_final)["ok"], field
    unresolved = copy.deepcopy(valid)
    unresolved["final_review"]["unresolved_issues"] = ["Leaf points forward rather than upward"]
    assert not MODULE.validate_ledger(unresolved)["ok"]

    # Malformed evidence is rejected with diagnostics rather than a crash.
    for value in (None, {}, [None], [{"feature": []}], [{"feature": "unknown"}]):
        malformed = copy.deepcopy(valid)
        malformed["modules"][0]["feature_reviews"] = value
        assert not MODULE.validate_ledger(malformed)["ok"]
    duplicate = copy.deepcopy(valid)
    duplicate["modules"][0]["feature_reviews"] *= 2
    assert not MODULE.validate_ledger(duplicate)["ok"]
    assert MODULE.validate_ledger(valid)["ready_to_claim_complete"]
    print("module ledger tests: ok (original gates, per-feature evidence, stale feedback, final review, malformed records)")


if __name__ == "__main__":
    main()

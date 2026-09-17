"""Deterministic tests for the module-ledger completion gate."""

from __future__ import annotations

import importlib.util
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
        "status": status,
        "implementation_objects": [] if status == "missing" else [f"GEO_{module_id}"],
        "user_approved_simplification": approved,
        "simplification_reason": "approved output constraint" if status == "simplified" else "",
    }


def ledger(stage: str, modules: list[dict]) -> dict:
    return {"schema_version": 1, "task_id": "test", "target_stage": stage, "modules": modules}


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
    print("module ledger tests: ok")


if __name__ == "__main__":
    main()

"""Exercise the actual final command with synthetic evidence files."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from test_module_ledger import item, ledger


class FinalDeliveryTests(unittest.TestCase):
    def test_final_cli(self):
        with tempfile.TemporaryDirectory() as work:
            base = Path(work)

            def write(name, data):
                raw = json.dumps(data).encode()
                (base / name).write_bytes(raw)
                return {"path": name, "sha256": hashlib.sha256(raw).hexdigest()}

            record = ledger("final", [item("hull", "primary", "matched")])
            bundle = {"ledger": write("ledger.json", record), "model": write("model.glb", "fixture")}
            guides = [write(name + ".png", name) for name in ("front", "side")]
            review = {"status": "passed", "finding": "fixture", "construction_images": guides}
            design = {"schema_version": 1, "purpose": "fixture", "pose": "fixed", "readiness": "passed",
                      "allowed_regions": ["hull"], "review_artifacts": ["front.png"],
                      "checks": {key: {"status": "passed", "finding": "fixture"} for key in
                                 ("pose", "proportions", "projection", "structure", "appearance", "axes")},
                      "views": {Path(g["path"]).stem: {"image": g["path"], "sha256": g["sha256"],
                                "role": "controlling", "controls": ["hull"], "finding": "fixture"} for g in guides}}
            bundle["multiview_review"] = write("design.json", design)
            prep = {"task_id": "test", "schema_version": 1, "purpose": "fixture", "reason": "fixture",
                    "route": "existing_reviewed", "source_images": guides, "construction_images": guides,
                    "existing_review": write("existing.json", review), "facts": {"projection": "orthographic",
                    "needs_hidden_shape": False, "needs_pose_normalization": False}}
            bundle["preparation"] = write("prep.json", prep)
            for field in ("structural_report", "contact_sheet", "perspective_view"):
                bundle[field] = write(record["final_review"][field], field)
            picture = write("comparison.png", "synthetic")
            camera = {"resolution": [640, 480], "projection_matrix": list(range(16)), "world_matrix": list(range(16))}
            shot = {"image": picture, "camera": camera}
            view = {"before": shot, "after": shot, "model_sha256": bundle["model"]["sha256"], "comparison": picture}
            view.update(name="front", reference=guides[0])
            side = dict(view, name="side", reference=guides[1])
            bundle.update(views=[view, side], actionable_items=[], regions={"hull": {
                "local": picture, "surroundings": picture, "state": "reviewed"}})

            def run(*args):
                write("review.json", bundle)
                cmd = [sys.executable, str(SCRIPTS / "validate_module_ledger.py"), "ledger.json", *args]
                result = subprocess.run(cmd, cwd=base, capture_output=True, text=True)
                report = json.loads(result.stdout)
                self.assertEqual(result.returncode == 0, report["ready_to_claim_complete"])
                return report["ready_to_claim_complete"]

            args = ["--model", "model.glb", "--review", "review.json"]
            self.assertFalse(run())
            self.assertTrue(run(*args))
            bundle["views"].remove(side)
            self.assertFalse(run(*args))
            bundle["views"].append(side)
            view["after"] = dict(shot, camera=dict(camera, resolution=[300, 200]))
            self.assertFalse(run(*args))
            view["after"] = shot
            bundle["actionable_items"].append("repair cuff")
            self.assertFalse(run(*args))
            bundle["actionable_items"].clear()
            region = bundle["regions"].pop("hull")
            self.assertFalse(run(*args))
            bundle["regions"]["hull"] = region
            write("model.glb", "updated")
            self.assertFalse(run(*args))

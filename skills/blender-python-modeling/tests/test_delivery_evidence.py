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
                    "style_selection": {"id": "unlisted", "reason": "Synthetic calibration fixture"},
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
            prep["style_selection"] = dict(id="papercraft", reason="layered cut edges",
                                            region="cuff", shape_cue="raised fold", surface_cue="fine grain")
            bundle["preparation"] = write("prep.json", prep)
            self.assertFalse(run(*args))
            style = dict(id="papercraft", region="cuff", model_sha256=bundle["model"]["sha256"],
                         reference_crop=picture, clay=write("clay.png", "clay"), material=write("color.png", "paper"),
                         shape=dict(status="passed", finding="fold reads in silhouette"),
                         surface=dict(status="open", finding="cuff appears uniformly smooth"))
            bundle["style_review"] = style
            self.assertFalse(run(*args))
            style["surface"] = dict(status="passed", finding="fine paper variations agree at final scale")
            self.assertTrue(run(*args))
            style["model_sha256"] = "previous model"
            self.assertFalse(run(*args))
            style["model_sha256"] = bundle["model"]["sha256"]
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
            region.update(state="residual", reason="side unclear", attempt_log=write("attempt.txt", "trial"))
            self.assertFalse(run(*args))
            finding = dict(symptom="missing profile", view="side", change="rebuild profile",
                           result="shape reviewed", model_sha256=bundle["model"]["sha256"],
                           reference_status="missing", reference=guides[1], before=picture,
                           after=write("candidate.png", "trial render"), status="fixed")
            region.update(state="reviewed", visual_findings=[finding])
            self.assertFalse(run(*args))
            finding["reference_status"] = "supplement_reviewed"
            finding["generation_record"] = write("generation.json", {"outputs": [guides[0]]})
            self.assertFalse(run(*args))
            finding["generation_record"] = write("generation.json", {"outputs": [guides[1]]})
            self.assertTrue(run(*args))
            # Reproduces the false close: front looks clean, profile lip disappeared.
            record["modules"][0]["projected_features"] = ["eyes", "lip"]
            bundle["ledger"] = write("ledger.json", record)
            self.assertFalse(run(*args))
            angles = {}
            for angle in ("front", "oblique", "profile"):
                angles[angle] = {"comparison": write(angle + "-crop.png", angle),
                                 "features": {f: {"status": "passed", "finding": "fixture alignment"}
                                              for f in ("eyes", "lip")}}
            projection = {"model_sha256": bundle["model"]["sha256"], "views": angles}
            region["projection_review"] = projection
            self.assertTrue(run(*args))
            profile = angles["profile"]["features"]
            profile["lip"] = {"status": "open", "finding": "lip line faded after removing frontal duplicate"}
            self.assertFalse(run(*args))
            profile["lip"]["status"] = "passed"
            profile["lip"]["finding"] = "lip visible at the guide corner after UV adjustment"
            profile["eyes"]["status"] = "occluded"
            self.assertFalse(run(*args))
            profile["eyes"]["occluder"] = "nose hides far eye; near eye checked"
            self.assertTrue(run(*args))
            comparisons = angles.pop("oblique")
            self.assertFalse(run(*args))
            angles["oblique"] = comparisons
            projection["model_sha256"] = "old revision"
            self.assertFalse(run(*args))
            projection["model_sha256"] = bundle["model"]["sha256"]
            # A provenance failure must not suppress the independent refinement result.
            prep["source_images"] = []
            bundle["preparation"] = write("prep.json", prep)
            def report():
                run(*args, "--output", "result.json")
                return json.loads((base / "result.json").read_text())
            finding["status"] = "open"
            result = report()
            self.assertFalse(result["refinement_evidence_checked"])
            self.assertTrue(any("Continue repair" in err for err in result["errors"]))
            finding.update(status="exhausted", reopen_when="new measured depth")
            region["state"] = "residual"
            result = report()
            self.assertTrue(result["refinement_evidence_checked"])
            self.assertFalse(result["ready_to_claim_complete"])
            prep["source_images"] = guides
            bundle["preparation"] = write("prep.json", prep)
            finding["status"] = "fixed"
            region["state"] = "reviewed"
            write("model.glb", "updated")
            self.assertFalse(run(*args))

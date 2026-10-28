"""Synthetic geometry tests; not a real character segmentation benchmark."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "puppet.py"
spec = importlib.util.spec_from_file_location("puppet", SCRIPT)
puppet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(puppet)


def fixture(root):
    """Known parts and an independently drawn source with a transparent hole."""
    root = Path(root)
    (root / "parts").mkdir(parents=True, exist_ok=True)
    (root / "masks").mkdir(exist_ok=True)
    source = Image.new("RGBA", (96, 96))
    draw = ImageDraw.Draw(source)
    draw.rectangle((12, 12, 43, 65), fill="red")
    draw.rectangle((20, 20, 26, 26), fill=(0, 0, 0, 0))
    draw.rectangle((40, 38, 75, 49), fill="blue")
    draw.rectangle((73, 40, 82, 47), fill="yellow")
    source.save(root / "source.png")
    torso = Image.new("RGBA", (36, 58))
    draw = ImageDraw.Draw(torso)
    draw.rectangle((2, 2, 33, 55), fill="red")
    draw.rectangle((10, 10, 16, 16), fill=(0, 0, 0, 0))
    torso.save(root / "parts/torso.png")
    arm = Image.new("RGBA", (40, 16))
    ImageDraw.Draw(arm).rectangle((2, 2, 37, 13), fill="blue")
    arm.save(root / "parts/arm.png")
    hand = Image.new("RGBA", (14, 12))
    ImageDraw.Draw(hand).rectangle((2, 2, 11, 9), fill="yellow")
    hand.save(root / "parts/hand.png")
    mask = Image.new("L", arm.size)
    ImageDraw.Draw(mask).rectangle((2, 2, 5, 13), fill=255)
    mask.save(root / "masks/arm.png")
    data = {
        "schema_version": "1.0", "coordinate_system": "image-pixels-y-down", "source_size": [96, 96],
        "nodes": [
            {"id": "torso", "parent": None, "pivot_global": [40, 40], "rotation_range": [-90, 90]},
            {"id": "arm", "parent": "torso", "pivot_global": [40, 40], "rotation_range": [-90, 90]},
            {"id": "hand", "parent": "arm", "pivot_global": [74, 44], "rotation_range": [-90, 90]}],
        "parts": []}
    for i, (key, origin, size, pivot) in enumerate([
            ("torso", [10, 10], [36, 58], [30, 30]),
            ("arm", [38, 36], [40, 16], [2, 4]),
            ("hand", [71, 38], [14, 12], [3, 6])]):
        part = {"id": key, "label": key, "character_id": "synthetic", "node": key,
                "file": f"parts/{key}.png", "crop_origin": origin, "pixel_size": size,
                "pivot_local": pivot, "z_index": i, "inferred": key == "arm"}
        if key == "arm":
            part["inferred_region_mask"] = "masks/arm.png"
        data["parts"].append(part)
    path = root / "manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path, data, source


class PuppetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path, self.data, self.source = fixture(self.temp.name)

    def save(self, data):
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def test_rest_pose_is_pixel_exact(self):
        result = puppet.render(self.path)
        self.assertEqual(result.tobytes(), self.source.tobytes())

    def test_holes_and_empty_background_survive(self):
        result = puppet.render(self.path)
        self.assertEqual(result.getpixel((23, 23))[3], 0)
        self.assertEqual(result.getpixel((0, 0))[3], 0)
        self.assertEqual(result.getpixel((30, 30)), (255, 0, 0, 255))

    def test_positive_rotation_is_clockwise_and_child_follows(self):
        result = puppet.render(self.path, {"arm": 90})
        self.assertEqual(result.getpixel((36, 65)), (0, 0, 255, 255))
        self.assertEqual(result.getpixel((36, 78)), (255, 255, 0, 255))
        self.assertEqual(result.getpixel((65, 44))[3], 0)

    def test_combined_parent_child_transform(self):
        m = puppet.transforms(self.data, {"torso": 30, "arm": 60})["hand"]
        # Rest hand pivot (74,44) rotates 90 degrees about (40,40).
        x, y = 74, 44
        self.assertAlmostEqual(m[0]*x + m[1]*y + m[2], 36)
        self.assertAlmostEqual(m[3]*x + m[4]*y + m[5], 74)

    def test_shared_node_and_independent_draw_order(self):
        extra = copy.deepcopy(self.data["parts"][-1])
        extra.update(id="hand_back", z_index=-1)
        self.data["parts"].append(extra)
        self.data["nodes"].reverse()
        self.save(self.data)
        self.assertEqual(puppet.render(self.path).tobytes(), self.source.tobytes())

    def test_rotation_sweep_renders(self):
        for angle in (-30, -15, 0, 15, 30):
            with self.subTest(angle=angle):
                result = puppet.render(self.path, {"arm": angle, "hand": -angle})
                self.assertIsNotNone(result.getbbox())
                self.assertEqual(result.size, (96, 96))

    def test_invalid_manifest_cases(self):
        cases = [
            ("cycle", lambda d: d["nodes"][0].update(parent="hand")),
            ("missing parent", lambda d: d["nodes"][1].update(parent="absent")),
            ("unknown node", lambda d: d["parts"][0].update(node="absent")),
            ("duplicate id", lambda d: d["parts"][1].update(id="torso")),
            ("duplicate z", lambda d: d["parts"][1].update(z_index=0)),
            ("pivot", lambda d: d["parts"][1].update(pivot_local=[0, 0])),
            ("size", lambda d: d["parts"][1].update(pixel_size=[1, 1])),
            ("missing mask", lambda d: d["parts"][1].pop("inferred_region_mask")),
            ("missing asset", lambda d: d["parts"][0].update(file="missing.png")),
            ("outside path", lambda d: d["parts"][0].update(file="../outside.png")),
            ("nonfinite", lambda d: d["nodes"][0].update(pivot_global=[float("nan"), 0])),
            ("bad range", lambda d: d["nodes"][0].update(rotation_range=[10, 30])),
            ("bad parent type", lambda d: d["nodes"][0].update(parent=[]))]
        for name, mutate in cases:
            with self.subTest(case=name):
                data = copy.deepcopy(self.data)
                mutate(data)
                self.save(data)
                with self.assertRaises(ValueError):
                    puppet.load_manifest(self.path)

    def test_wrong_mask_and_non_rgba_rejected(self):
        mask = self.path.parent / "masks/arm.png"
        Image.new("L", (1, 1), 255).save(mask)
        with self.assertRaisesRegex(ValueError, "same-size"):
            puppet.load_manifest(self.path)
        fixture(self.path.parent)
        Image.new("RGB", (40, 16), "blue").save(self.path.parent / "parts/arm.png")
        with self.assertRaisesRegex(ValueError, "RGBA"):
            puppet.load_manifest(self.path)

    def test_mask_cannot_mark_transparent_pixels(self):
        mask = Image.new("L", (40, 16), 255)
        mask.save(self.path.parent / "masks/arm.png")
        with self.assertRaisesRegex(ValueError, "transparent pixels"):
            puppet.load_manifest(self.path)

    def test_invalid_angles_rejected(self):
        for angles in ({"typo": 0}, {"arm": 100}, {"arm": float("inf")}, {"arm": True}, []):
            with self.subTest(angles=angles), self.assertRaises(ValueError):
                puppet.render(self.path, angles)

    def test_cli_check_render_and_error(self):
        check = subprocess.run([sys.executable, str(SCRIPT), "check", str(self.path)],
                               capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertEqual(json.loads(check.stdout)["visual_qa"], "not_checked")
        output = self.path.parent / "preview/rest.png"
        result = subprocess.run([sys.executable, str(SCRIPT), "render", str(self.path),
                                 "--output", str(output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(output.exists())
        result = subprocess.run([sys.executable, str(SCRIPT), "render", str(self.path),
                                 "--angles", '{"typo":10}', "--output", str(output)],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)

    def test_cli_protects_referenced_assets_outside_standard_folders(self):
        custom = self.path.parent / "custom.png"
        original = (self.path.parent / "parts/torso.png").read_bytes()
        custom.write_bytes(original)
        self.data["parts"][0]["file"] = "custom.png"
        self.save(self.data)
        result = subprocess.run([sys.executable, str(SCRIPT), "render", str(self.path),
                                 "--output", str(custom)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(custom.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()

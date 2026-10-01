"""Offline tests for controlled PointPillars height examples."""

import importlib.util
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "pipeline-qc-cases.py"


def load_script():
    spec = importlib.util.spec_from_file_location("pipeline_qc_cases", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def payload():
    return {
        "frame_id": "demo",
        "dataset": "KITTI",
        "delta": 1.73,
        "voxel_size": 0.16,
        "z_ground": -0.08,
        "boxes": [
            {"label": "vehicles", "x": 10.0, "y": 2.0, "z": 0.5, "length": 4.0,
             "width": 1.8, "height": 1.5, "yaw": 0.2, "score": 0.9},
            {"label": "pedestrian", "x": 15.0, "y": -1.0, "z": 0.9, "length": 0.7,
             "width": 0.5, "height": 1.7, "yaw": -0.4, "score": 0.7},
        ],
    }


class CasesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "boxes-demo.json"
        self.output = self.root / "out"

    def write(self, data):
        self.source.write_text(json.dumps(data), encoding="utf-8")

    def test_three_cases_keep_source_and_change_only_target_z(self):
        self.write(payload())
        before = self.source.read_bytes()
        load_script().generate_cases(self.source, self.output)
        self.assertEqual(self.source.read_bytes(), before)
        correct = json.loads((self.output / "case-correct.json").read_text())
        batch = json.loads((self.output / "case-batch-z.json").read_text())
        one = json.loads((self.output / "case-one-box-z.json").read_text())
        offset = payload()["delta"] + payload()["z_ground"]
        self.assertEqual(correct["boxes"], payload()["boxes"])
        self.assertTrue(all(case["training_only"] for case in (correct, batch, one)))
        self.assertEqual(len({case["source_prediction_sha256"] for case in (correct, batch, one)}), 1)
        for index, original in enumerate(correct["boxes"]):
            self.assertAlmostEqual(batch["boxes"][index]["z"], original["z"] - offset)
            expected = original["z"] - offset if index == 0 else original["z"]
            self.assertAlmostEqual(one["boxes"][index]["z"], expected)
            for changed in (batch, one):
                self.assertEqual({k: v for k, v in changed["boxes"][index].items() if k != "z"},
                                 {k: v for k, v in original.items() if k != "z"})
        manifest = json.loads((self.output / "manifest.json").read_text())
        self.assertEqual(manifest["source_frame"], "pcd-source")
        self.assertEqual(manifest["model_dataset"], "KITTI")
        self.assertAlmostEqual(manifest["height_offset_m"], offset)
        self.assertIn("not ground truth", manifest["warning"].lower())

    def test_bad_input_is_rejected_before_output_is_written(self):
        invalid = []
        for field, value in (("dataset", "WAYMO"), ("delta", 0),
                             ("delta", True), ("z_ground", float("nan")),
                             ("delta", 0.08)):
            item = payload()
            item[field] = value
            invalid.append(item)
        for field, value in (("z", float("inf")), ("x", True),
                             ("length", 0), ("label", "car")):
            item = payload()
            item["boxes"][0][field] = value
            invalid.append(item)
        item = payload()
        item["boxes"] = []
        invalid.append(item)
        item = payload()
        item["boxes"] = item["boxes"][:1]
        invalid.append(item)
        item = payload()
        item["delta"] = 1e308
        item["boxes"][0]["z"] = -1e308
        invalid.append(item)
        for item in invalid:
            with self.subTest(item=item):
                self.write(item)
                with self.assertRaises((ValueError, SystemExit)):
                    load_script().generate_cases(self.source, self.output)
                self.assertFalse(self.output.exists())

    def test_duplicate_keys_and_nonempty_output_are_rejected(self):
        self.source.write_text('{"frame_id":"demo","frame_id":"other"}', encoding="utf-8")
        with self.assertRaises((ValueError, SystemExit)):
            load_script().generate_cases(self.source, self.output)
        self.assertFalse(self.output.exists())
        self.write(payload())
        self.output.mkdir()
        (self.output / "keep.txt").write_text("keep")
        with self.assertRaises((ValueError, SystemExit)):
            load_script().generate_cases(self.source, self.output)
        self.assertEqual((self.output / "keep.txt").read_text(), "keep")

    def test_pcd_stem_must_match_frame_before_writing(self):
        self.write(payload())
        pcd = self.root / "other.pcd"
        pcd.write_bytes(b"not a PCD")
        with self.assertRaises((ValueError, SystemExit)):
            load_script().generate_cases(self.source, self.output, pcd)
        self.assertFalse(self.output.exists())

    def test_cli_renders_labeled_side_views_from_matching_pcd(self):
        self.write(payload())
        pcd = self.root / "demo.pcd"
        header = b"FIELDS x y z rgb\nPOINTS 1\nDATA binary\n"
        pcd.write_bytes(header + struct.pack("<ffff", 10.0, 2.0, 0.0, 0.0))
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--prediction", str(self.source),
             "--out", str(self.output), "--pcd", str(pcd)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("correct", "batch-z", "one-box-z"):
            self.assertTrue((self.output / f"side-{name}.png").is_file())
        manifest = json.loads((self.output / "manifest.json").read_text())
        self.assertEqual(manifest["cases"]["batch-z"]["plot"], "side-batch-z.png")


if __name__ == "__main__":
    unittest.main()

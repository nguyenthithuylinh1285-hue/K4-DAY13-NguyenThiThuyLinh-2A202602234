"""Make controlled height-error examples from a KITTI PointPillars prediction.

The source JSON already contains boxes converted back to the PCD source frame.
This script does not run inference or make ground-truth annotations. The two
modified cases only simulate forgetting the inverse height conversion.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

MAX_PREDICTION_BYTES = 10_000_000
MAX_BOXES = 10_000
LABELS = {"vehicles", "pedestrian", "two-wheels"}
NUMBER_FIELDS = ("x", "y", "z", "length", "width", "height", "yaw", "score")
WARNING = "TRAINING ONLY: not ground truth, not for CVAT import or quality claims."


def unique_object(pairs):
    """Reject ambiguous JSON objects, including duplicate nested box keys."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def finite_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number, not a boolean")
    return value


def validate(payload):
    if not isinstance(payload, dict):
        raise ValueError("Prediction must be a JSON object")
    expected = {"frame_id", "dataset", "delta", "voxel_size", "z_ground", "boxes"}
    if set(payload) != expected:
        raise ValueError(f"Prediction fields must be exactly: {', '.join(sorted(expected))}")
    frame = payload.get("frame_id")
    if not isinstance(frame, str) or not frame.strip() or Path(frame).name != frame:
        raise ValueError("frame_id must be a nonempty PCD stem")
    if payload.get("dataset") != "KITTI":
        raise ValueError("Only KITTI source-frame predictions are supported")
    delta = finite_number(payload.get("delta"), "delta")
    if delta <= 0:
        raise ValueError("delta must be positive")
    ground = finite_number(payload.get("z_ground"), "z_ground")
    offset = delta + ground
    if not math.isfinite(offset) or math.isclose(offset, 0, abs_tol=1e-12):
        raise ValueError("delta + z_ground must be finite and nonzero")
    if finite_number(payload.get("voxel_size"), "voxel_size") <= 0:
        raise ValueError("voxel_size must be positive")
    boxes = payload.get("boxes")
    if not isinstance(boxes, list) or not (2 <= len(boxes) <= MAX_BOXES):
        raise ValueError(f"boxes must contain 2 to {MAX_BOXES} objects so the batch and one-box cases differ")
    for index, box in enumerate(boxes):
        if not isinstance(box, dict) or box.get("label") not in LABELS:
            raise ValueError(f"boxes[{index}].label must be a KITTI label")
        if set(box) != set(NUMBER_FIELDS) | {"label"}:
            raise ValueError(f"boxes[{index}] has missing or unexpected fields")
        for field in NUMBER_FIELDS:
            value = finite_number(box.get(field), f"boxes[{index}].{field}")
            if field in ("length", "width", "height") and value <= 0:
                raise ValueError(f"boxes[{index}].{field} must be positive")
        if not math.isfinite(box["z"] - offset):
            raise ValueError(f"boxes[{index}].z minus height offset must be finite")
    return offset


def write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8")


def generate_cases(prediction, out, pcd=None):
    """Validate everything, then write three examples and a diagnostic manifest."""
    prediction = Path(prediction)
    out = Path(out)
    if not prediction.is_file() or not prediction.name.startswith("boxes-") or prediction.suffix != ".json":
        raise ValueError("--prediction must name an existing boxes-*.json file")
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError("--out must be absent or an empty directory; refusing overwrite")
    if out.resolve() == prediction.parent.resolve():
        raise ValueError("--out must differ from the prediction directory")
    if prediction.stat().st_size > MAX_PREDICTION_BYTES:
        raise ValueError(f"Prediction exceeds {MAX_PREDICTION_BYTES} bytes")
    raw = prediction.read_bytes()
    try:
        source = json.loads(raw, object_pairs_hook=unique_object,
                            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"Invalid JSON constant: {value}")))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid prediction JSON: {error}") from error
    offset = validate(source)

    points = None
    if pcd is not None:
        pcd = Path(pcd)
        if not pcd.is_file() or pcd.suffix.lower() != ".pcd" or pcd.stem != source["frame_id"]:
            raise ValueError("--pcd must be an existing PCD whose stem matches frame_id")
        # Imported only for optional plotting; ordinary JSON generation needs stdlib only.
        from preannotate import read_xyz

        points = read_xyz(pcd)
        import matplotlib  # Check plotting dependency before writing any output.

    digest = hashlib.sha256(raw).hexdigest()
    cases = {}
    descriptions = {
        "correct": "Unmodified source-frame prediction copy; model output, not an accuracy reference.",
        "batch-z": "Every box z is shifted down by delta + z_ground, simulating a missed inverse conversion.",
        "one-box-z": "Only the first box z is shifted down by delta + z_ground, simulating an object-local error.",
    }
    for name in descriptions:
        case = copy.deepcopy(source)
        case["training_only"] = True
        case["source_prediction_sha256"] = digest
        case["case"] = name
        case["warning"] = WARNING
        if name == "batch-z":
            for box in case["boxes"]:
                box["z"] -= offset
        elif name == "one-box-z":
            case["boxes"][0]["z"] -= offset
        cases[name] = case

    manifest = {
        "training_only": True,
        "warning": WARNING,
        "source_prediction": prediction.name,
        "source_prediction_sha256": digest,
        "frame_id": source["frame_id"],
        "source_frame": "pcd-source",
        "model_dataset": source["dataset"],
        "delta_m": source["delta"],
        "z_ground_m": source["z_ground"],
        "height_offset_m": offset,
        "box_count": len(source["boxes"]),
        "cases": {
            name: {"json": f"case-{name}.json", "plot": f"side-{name}.png" if points is not None else None,
                   "description": description}
            for name, description in descriptions.items()
        },
    }
    out.mkdir(parents=True, exist_ok=True)
    for name, case in cases.items():
        write_json(out / f"case-{name}.json", case)
    write_json(out / "manifest.json", manifest)
    if points is not None:
        from preannotate import draw_side_view

        for name, case in cases.items():
            draw_side_view(points, case["boxes"], out / f"side-{name}.png",
                           source["delta"], source["voxel_size"])
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prediction", required=True, type=Path, help="Existing boxes-*.json from preannotate.py")
    parser.add_argument("--out", required=True, type=Path, help="Absent or empty output directory")
    parser.add_argument("--pcd", type=Path, help="Matching source PCD for optional side-view plots")
    args = parser.parse_args()
    try:
        manifest = generate_cases(args.prediction, args.out, args.pcd)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(f"Wrote {len(manifest['cases'])} training-only cases to {args.out}. {WARNING}")


if __name__ == "__main__":
    main()

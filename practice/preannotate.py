"""Run a PointPillars checkpoint on one Robotaxi scan.

The cloud's origin is on the ground. ``--from`` selects the dataset the
checkpoint was trained on. That preset supplies the kept range, the pillar
height, the default sensor height, and the class names. ``delta`` is the
sensor height:

    z_model = z_source - z_ground - delta
    z_source = z_model + delta + z_ground

``x`` and ``y`` already match both presets: forward and left. A KITTI
``--full-scene`` run adds one 180 degree pass so the rear rectangle is seen
by the same front-only window. ``--voxel-size`` is the pillar edge in the
ground plane.

The KITTI checkpoint does not use the lab heading. Its yaw 0 points left,
and the angle is mirrored. On these scans the car arrow matches the label
when the lab heading is ``pi/2 - yaw + pi``. The z it returns is the bottom
of the box, so the stored center is that bottom plus half the height.
Waymo keeps yaw 0 forward and z at the center.

The scan stores ``rgb``, not lidar reflectance. One constant cannot feed
every head of this checkpoint. Reflectance 0 puts car-sized boxes on cars
and leaves cyclists and pedestrians empty. Reflectance 0.7 does the
opposite. KITTI therefore reads the cloud twice and keeps each class from
the read that can see it. A cyclist or pedestrian whose center lies inside
a car box is dropped, because that read also draws those classes on cars.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import struct
from dataclasses import dataclass
from pathlib import Path

PCD_RECORD = 16
KITTI_CKPT = Path("/opt/PointPillars/pretrained/epoch_160.pth")


@dataclass(frozen=True)
class Preset:
    """One trained dataset's window, height, passes, and class names.

    Attributes:
        name: Value of ``--from``.
        range: ``xmin, ymin, zmin, xmax, ymax, zmax`` in the model frame.
        voxel_z: Pillar height in meters. ``--voxel-size`` sets only x and y.
        h_sensor: Default ``delta`` in meters.
        labels: Checkpoint class index to a CVAT label name.
        passes: Passes used when ``--full-scene`` is set. Without that flag
            only ``identity`` runs.
        ckpt: Baked checkpoint. ``None`` means ``--ckpt`` is required.
        heading: ``kitti`` mirrors the checkpoint yaw into the lab frame.
            ``forward`` already uses yaw 0 as forward.
        z_bottom: True when the checkpoint z is the bottom face, not the center.
        reads: Each entry is a reflectance and the class names kept from
            that read. The cloud has no intensity, so the value is constant.
    """

    name: str
    range: tuple[float, float, float, float, float, float]
    voxel_z: float
    h_sensor: float
    labels: dict[int, str]
    passes: tuple[str, ...]
    ckpt: Path | None
    heading: str
    z_bottom: bool
    reads: tuple[tuple[float, tuple[str, ...]], ...]


PRESETS = {
    "KITTI": Preset(
        name="KITTI",
        range=(0.0, -39.68, -3.0, 69.12, 39.68, 1.0),
        voxel_z=4.0,
        h_sensor=1.73,
        labels={0: "pedestrian", 1: "two-wheels", 2: "vehicles"},
        passes=("identity", "yaw180"),
        ckpt=KITTI_CKPT,
        heading="kitti",
        z_bottom=True,
        reads=(
            (0.0, ("vehicles",)),
            (0.7, ("pedestrian", "two-wheels")),
        ),
    ),
    "WAYMO": Preset(
        name="WAYMO",
        range=(-74.88, -74.88, -2.0, 74.88, 74.88, 4.0),
        voxel_z=6.0,
        h_sensor=2.03,
        labels={0: "vehicles", 1: "pedestrian", 2: "two-wheels"},
        passes=("identity",),
        ckpt=None,
        heading="forward",
        z_bottom=False,
        reads=((0.0, ("vehicles", "pedestrian", "two-wheels")),),
    ),
}


def z_to_model(z_source: float, z_ground: float, delta: float) -> float:
    """Shift a source-frame height into the checkpoint frame.

    Args:
        z_source: Height in the scan, meters.
        z_ground: Estimated ground height in the scan, meters.
        delta: Sensor height assumed by the checkpoint, meters.

    Returns:
        Height in the model frame.
    """
    return z_source - z_ground - delta


def z_to_source(z_model: float, z_ground: float, delta: float) -> float:
    """Shift a model-frame height back into the scan frame.

    Args:
        z_model: Height in the checkpoint frame, meters.
        z_ground: Estimated ground height in the scan, meters.
        delta: Sensor height that was subtracted before inference, meters.

    Returns:
        Height in the scan frame.
    """
    return z_model + delta + z_ground


def parse_deltas(text: str) -> list[float]:
    """Parse a comma-separated list of sensor heights.

    Args:
        text: Values such as ``0,0.2,1.73``.

    Returns:
        Floats in the given order.

    Raises:
        SystemExit: If the list is empty or a value is not a number.
    """
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if not parts:
        raise SystemExit("Pass at least one delta, for example 0,0.2,1.73")
    try:
        return [float(part) for part in parts]
    except ValueError as error:
        raise SystemExit(f"Could not parse deltas {text!r}") from error


def find_pcd(data_dir: Path, frame: str) -> Path:
    """Find one binary PCD in a file, a flat directory, or a Datumaro export.

    Args:
        data_dir: File or directory mounted into the container.
        frame: PCD stem. Empty means the only ``.pcd`` in the directory.

    Returns:
        Path to the PCD.

    Raises:
        SystemExit: If the file is missing or the directory is ambiguous.
    """
    if data_dir.is_file():
        return data_dir
    candidates = []
    if frame:
        candidates = [
            data_dir / f"{frame}.pcd",
            data_dir / "point_clouds" / "default" / f"{frame}.pcd",
            data_dir / "pointcloud" / f"{frame}.pcd",
        ]
        found = [path for path in candidates if path.is_file()]
        if len(found) == 1:
            return found[0]
        raise SystemExit(f"No single PCD for frame {frame!r} under {data_dir}")
    names = sorted(data_dir.rglob("*.pcd"))
    if len(names) != 1:
        raise SystemExit(f"Pass --frame. Found {len(names)} PCD files under {data_dir}")
    return names[0]


def read_xyz(path: Path) -> list[tuple[float, float, float]]:
    """Read xyz from a binary PCD with fields ``x y z rgb``.

    Args:
        path: PCD path.

    Returns:
        Coordinates in file order.

    Raises:
        SystemExit: If the header is not the expected binary layout.
    """
    raw = path.read_bytes()
    marker = b"DATA binary\n"
    index = raw.find(marker)
    if index < 0:
        raise SystemExit(f"{path.name}: only PCD DATA binary is supported")
    header = raw[:index].decode("ascii", errors="strict")
    fields = {}
    for line in header.splitlines():
        parts = line.split()
        if parts:
            fields[parts[0]] = parts[1:]
    if fields.get("FIELDS") != ["x", "y", "z", "rgb"]:
        raise SystemExit(f"{path.name}: expected FIELDS x y z rgb")
    count = int(fields["POINTS"][0])
    body = raw[index + len(marker) :]
    if len(body) < count * PCD_RECORD:
        raise SystemExit(f"{path.name}: body is shorter than POINTS")
    return [struct.unpack_from("<fff", body, offset * PCD_RECORD) for offset in range(count)]


def estimate_ground(points: list[tuple[float, float, float]], bin_m: float = 0.05) -> float:
    """Return the histogram peak of ``z`` as the ground height.

    Args:
        points: Scan coordinates.
        bin_m: Histogram bin width, in meters.

    Returns:
        Center of the fullest bin. ``0`` when the scan is empty.

    Raises:
        SystemExit: If ``bin_m`` is not positive.
    """
    if bin_m <= 0:
        raise SystemExit("bin_m must be positive")
    if not points:
        return 0.0
    counts: dict[int, int] = {}
    for _x, _y, z in points:
        bucket = int(z // bin_m)
        counts[bucket] = counts.get(bucket, 0) + 1
    peak = max(counts, key=counts.get)
    return (peak + 0.5) * bin_m


def grid_ok(voxel_xy: float, preset: Preset) -> None:
    """Require the bird's-eye grid to be divisible by the backbone stride.

    Args:
        voxel_xy: Pillar edge in x and y, meters.
        preset: Dataset window. The span is ``xmax - xmin`` and ``ymax - ymin``.

    Raises:
        SystemExit: If the resulting grid is not divisible by 8.
    """
    if voxel_xy <= 0:
        raise SystemExit("--voxel-size must be positive")
    span_x = preset.range[3] - preset.range[0]
    span_y = preset.range[4] - preset.range[1]
    cells_x = round(span_x / voxel_xy)
    cells_y = round(span_y / voxel_xy)
    if cells_x % 8 or cells_y % 8:
        raise SystemExit(
            f"voxel size {voxel_xy} gives a {cells_x}x{cells_y} grid on {preset.name}. "
            "Use a size that divides that range into multiples of 8, such as 0.16."
        )


def load_model(voxel_xy: float, score_thresh: float, ckpt: Path, preset: Preset):
    """Load a PointPillars checkpoint on CPU.

    Args:
        voxel_xy: Pillar size in x and y, meters.
        score_thresh: Minimum class score stored on the module.
        ckpt: Checkpoint file.
        preset: Supplies ``voxel_z``, the point-cloud range, and class count.

    Returns:
        An eval-mode ``PointPillars`` module.
    """
    import torch
    from pointpillars.model.pointpillars import PointPillars

    model = PointPillars(
        nclasses=len(preset.labels),
        voxel_size=[voxel_xy, voxel_xy, preset.voxel_z],
        point_cloud_range=list(preset.range),
    )
    state = torch.load(ckpt, map_location=torch.device("cpu"))
    model.load_state_dict(state)
    model.score_thr = score_thresh
    model.eval()
    return model


def model_xy(x: float, y: float, pass_name: str) -> tuple[float, float]:
    """Map a source-frame point into the pass the checkpoint expects.

    Args:
        x: Source-frame forward coordinate, meters.
        y: Source-frame left coordinate, meters.
        pass_name: ``identity`` or ``yaw180``.

    Returns:
        Coordinates in the model window for this pass.

    Raises:
        SystemExit: If ``pass_name`` is not known.
    """
    if pass_name == "identity":
        return x, y
    if pass_name == "yaw180":
        return -x, -y
    raise SystemExit(f"Unknown pass {pass_name}")


def lab_heading(yaw: float, preset: Preset) -> float:
    """Turn a checkpoint heading into the lab frame.

    Args:
        yaw: Heading from the checkpoint, radians.
        preset: Selects the angle convention. ``kitti`` uses
            ``pi/2 - yaw + pi``: yaw 0 points left, the rotation is mirrored,
            and the car arrow is the opposite end from the raw decode.
            ``forward`` is already yaw 0 forward.

    Returns:
        Heading wrapped to ``[-pi, pi]``, with 0 pointing forward.

    Raises:
        SystemExit: If ``preset.heading`` is not known.
    """
    if preset.heading == "kitti":
        yaw = math.pi / 2 - yaw + math.pi
    elif preset.heading != "forward":
        raise SystemExit(f"Unknown heading convention {preset.heading}")
    return math.atan2(math.sin(yaw), math.cos(yaw))


def source_xy_yaw(x: float, y: float, yaw: float, pass_name: str) -> tuple[float, float, float]:
    """Map a model-frame box back into the source frame.

    Args:
        x: Box center in the pass window, meters.
        y: Box center in the pass window, meters.
        yaw: Heading in the pass window, radians.
        pass_name: ``identity`` or ``yaw180``.

    Returns:
        Source-frame center and heading. Size is unchanged by the caller.

    Raises:
        SystemExit: If ``pass_name`` is not known.
    """
    if pass_name == "identity":
        return x, y, yaw
    if pass_name == "yaw180":
        yaw_source = math.atan2(math.sin(yaw + math.pi), math.cos(yaw + math.pi))
        return -x, -y, yaw_source
    raise SystemExit(f"Unknown pass {pass_name}")


def in_range(x: float, y: float, z: float, window: tuple[float, float, float, float, float, float]) -> bool:
    """Return whether a model-frame point lies inside the open preset window.

    Args:
        x: Forward coordinate in the pass window, meters.
        y: Left coordinate in the pass window, meters.
        z: Height in the model frame, meters.
        window: ``xmin, ymin, zmin, xmax, ymax, zmax``.

    Returns:
        True when every coordinate is strictly inside the window.
    """
    xmin, ymin, zmin, xmax, ymax, zmax = window
    return xmin < x < xmax and ymin < y < ymax and zmin < z < zmax


def merge_boxes(boxes: list[dict]) -> list[dict]:
    """Drop a lower-scoring box that duplicates a kept box of the same label.

    Two boxes are the same object when either center lies inside the other
    box's footprint. Two people standing close together keep both boxes,
    because neither center falls inside the other's footprint.

    Args:
        boxes: Boxes in the source frame, each with ``label``, ``x``, ``y``,
            ``length``, ``width``, ``yaw``, and ``score``.

    Returns:
        Kept boxes, highest score first.
    """
    ordered = sorted(boxes, key=lambda box: box["score"], reverse=True)
    kept = []
    for box in ordered:
        if any(
            other["label"] == box["label"] and (center_in_box(box, other) or center_in_box(other, box))
            for other in kept
        ):
            continue
        kept.append(box)
    return kept


def center_in_box(inner: dict, outer: dict, pad_m: float = 0.0) -> bool:
    """Return whether ``inner``'s ground-plane center lies inside ``outer``.

    Args:
        inner: Box whose center is tested.
        outer: Box that may contain that center.
        pad_m: Extra margin added on length and width, meters.

    Returns:
        True when the center is inside the padded rectangle.
    """
    dx = inner["x"] - outer["x"]
    dy = inner["y"] - outer["y"]
    cosine = math.cos(outer["yaw"])
    sine = math.sin(outer["yaw"])
    along = cosine * dx + sine * dy
    across = -sine * dx + cosine * dy
    return abs(along) <= outer["length"] / 2 + pad_m and abs(across) <= outer["width"] / 2 + pad_m


def drop_boxes_on_cars(boxes: list[dict]) -> list[dict]:
    """Remove a cyclist or pedestrian whose center sits inside a car box.

    The footprint is not padded, so a person standing next to a car is kept.

    Args:
        boxes: Merged boxes in the source frame.

    Returns:
        Cars, plus the smaller classes that are not standing on a car.
    """
    cars = [box for box in boxes if box["label"] == "vehicles"]
    kept = []
    for box in boxes:
        if box["label"] != "vehicles" and any(center_in_box(box, car) for car in cars):
            continue
        kept.append(box)
    return kept


def infer(
    model,
    points_xyz,
    delta: float,
    z_ground: float,
    preset: Preset,
    pass_name: str,
    reflectance: float,
    keep_labels: set[str],
):
    """Run one pass and return boxes in the source frame.

    Args:
        model: Eval-mode PointPillars module.
        points_xyz: Source-frame coordinates.
        delta: Sensor height subtracted before the model, meters.
        z_ground: Ground height in the source frame, meters.
        preset: Range, heading, and class names for this checkpoint.
        pass_name: ``identity`` or ``yaw180``.
        reflectance: Constant fourth feature for this read.
        keep_labels: Class names stored from this read. Other classes the
            checkpoint emits are ignored.

    Returns:
        Dicts with label, center, size, yaw, and score.
    """
    import numpy as np
    import torch

    rows = []
    for x, y, z in points_xyz:
        mx, my = model_xy(x, y, pass_name)
        z_model = z_to_model(z, z_ground, delta)
        if not in_range(mx, my, z_model, preset.range):
            continue
        rows.append((mx, my, z_model, reflectance))
    if not rows:
        return []
    cloud = torch.from_numpy(np.asarray(rows, dtype=np.float32))
    with torch.no_grad():
        result = model(batched_pts=[cloud], mode="test")[0]
    if not isinstance(result, dict):
        return []
    boxes = []
    for bbox, label, score in zip(result["lidar_bboxes"], result["labels"], result["scores"]):
        name = preset.labels.get(int(label))
        if name is None or name not in keep_labels:
            continue
        x, y, z_model, width, length, height, yaw = [float(value) for value in bbox]
        if preset.z_bottom:
            z_model += height / 2
        sx, sy, syaw = source_xy_yaw(x, y, lab_heading(yaw, preset), pass_name)
        boxes.append(
            {
                "label": name,
                "x": sx,
                "y": sy,
                "z": z_to_source(z_model, z_ground, delta),
                "length": length,
                "width": width,
                "height": height,
                "yaw": syaw,
                "score": float(score),
            }
        )
    return boxes


def draw_side_view(points, boxes, path: Path, delta: float, voxel_xy: float) -> None:
    """Write an x-z side view with one rectangle per box.

    Args:
        points: Source-frame coordinates.
        boxes: Boxes already converted back to the source frame.
        path: PNG destination.
        delta: Sensor height used for this run, printed on the figure.
        voxel_xy: Pillar size printed on the figure.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    step = max(1, len(points) // 8000)
    xs = [point[0] for point in points[::step]]
    zs = [point[2] for point in points[::step]]
    figure, axis = plt.subplots(figsize=(10, 4))
    axis.scatter(xs, zs, s=1, c="#9aa4b2", linewidths=0)
    axis.axhline(0.0, color="#1f4b99", linewidth=1)
    for box in boxes:
        corner = (box["x"] - box["length"] / 2, box["z"] - box["height"] / 2)
        color = "#c0392b" if box["label"] == "vehicles" else "#e67e22"
        rectangle = plt.Rectangle(
            corner, box["length"], box["height"], fill=False, edgecolor=color, linewidth=1.2
        )
        axis.add_patch(rectangle)
    axis.set_xlabel("x (m)")
    axis.set_ylabel("z (m)")
    axis.set_title(f"delta={delta:g}  voxel={voxel_xy:g}  boxes={len(boxes)}")
    rear = min((box["x"] for box in boxes), default=0.0)
    axis.set_xlim(-70 if rear < -5 else -20, 70)
    axis.set_ylim(-4, 4)
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=120)
    plt.close(figure)


def token(value: float) -> str:
    """Return a filename-safe rendering of a float.

    Args:
        value: Delta or voxel size.

    Returns:
        The number with a dot, without trailing zeros.
    """
    return f"{value:.2f}".rstrip("0").rstrip(".")


SUMMARY_FIELDS = ["frame_id", "dataset", "delta", "voxel_size", "n_boxes", "mean_z"]


def write_summary(path: Path, rows: list[dict]) -> None:
    """Append summary rows, writing a header when the file is new.

    Args:
        path: CSV path.
        rows: Records keyed by ``SUMMARY_FIELDS``.

    Raises:
        SystemExit: If an existing file has a different header, such as one
            written by an older version of this script.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists() or path.stat().st_size == 0
    if not new_file:
        with path.open(encoding="utf-8", newline="") as handle:
            header = next(csv.reader(handle), [])
        if header != SUMMARY_FIELDS:
            raise SystemExit(f"{path} has columns {header}, expected {SUMMARY_FIELDS}. Move it aside and re-run.")
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    """Parse the scan, the dataset preset, and the pillar size.

    Returns:
        Arguments. ``deltas`` is ``None`` when the preset height should be used.
    """
    parser = argparse.ArgumentParser(description="Pre-label one PCD with PointPillars.")
    parser.add_argument("--data", type=Path, default=Path("/data"), help="PCD file or a directory that contains it.")
    parser.add_argument("--out", type=Path, default=Path("/out"), help="Directory for JSON, PNG, and summary.csv.")
    parser.add_argument("--frame", default="", help="PCD stem. Required when --data holds more than one cloud.")
    parser.add_argument(
        "--from",
        dest="dataset",
        default="KITTI",
        choices=tuple(PRESETS),
        help="Dataset the checkpoint was trained on. Default KITTI.",
    )
    parser.add_argument(
        "--full-scene",
        action="store_true",
        help="Run every pass in the preset. KITTI then adds a 180 degree rear pass.",
    )
    parser.add_argument(
        "--deltas",
        default=None,
        help="Comma-separated sensor heights in meters. Default is the preset height.",
    )
    parser.add_argument("--voxel-size", type=float, default=0.16, help="Pillar size in x and y, meters.")
    parser.add_argument("--score-thresh", type=float, default=0.3)
    parser.add_argument(
        "--ckpt",
        type=Path,
        default=None,
        help="PointPillars checkpoint. KITTI defaults to the file baked into the image.",
    )
    return parser.parse_args()


def resolve_ckpt(preset: Preset, ckpt: Path | None) -> Path:
    """Return the checkpoint for this preset.

    Args:
        preset: Selected dataset. WAYMO has no baked file.
        ckpt: Path passed on the command line, or ``None``.

    Returns:
        An existing checkpoint path.

    Raises:
        SystemExit: If WAYMO has no ``--ckpt``, or the file is missing.
    """
    chosen = ckpt if ckpt is not None else preset.ckpt
    if chosen is None:
        raise SystemExit(f"--from {preset.name} needs --ckpt. This image has no {preset.name} weights.")
    if not chosen.is_file():
        raise SystemExit(f"Missing checkpoint {chosen}")
    return chosen


def main() -> None:
    """Sweep ``delta`` on one frame and write a side view per level."""
    args = parse_args()
    preset = PRESETS[args.dataset]
    deltas = parse_deltas(args.deltas if args.deltas else f"{preset.h_sensor:g}")
    grid_ok(args.voxel_size, preset)
    ckpt = resolve_ckpt(preset, args.ckpt)
    passes = preset.passes if args.full_scene else ("identity",)
    pcd = find_pcd(args.data, args.frame)
    points = read_xyz(pcd)
    z_ground = estimate_ground(points)
    frame = pcd.stem
    print(f"frame={frame} dataset={preset.name} points={len(points)} z_ground={z_ground:.3f} passes={','.join(passes)}")
    model = load_model(args.voxel_size, args.score_thresh, ckpt, preset)
    summary = []
    for delta in deltas:
        boxes = []
        for pass_name in passes:
            for reflectance, labels in preset.reads:
                boxes.extend(
                    infer(
                        model,
                        points,
                        delta,
                        z_ground,
                        preset,
                        pass_name,
                        reflectance,
                        set(labels),
                    )
                )
        boxes = drop_boxes_on_cars(merge_boxes(boxes))
        mean_z = ""
        if boxes:
            mean_z = f"{sum(box['z'] for box in boxes) / len(boxes):.3f}"
        tag = f"{frame}-delta-{token(delta)}-voxel-{token(args.voxel_size)}"
        payload = {
            "frame_id": frame,
            "dataset": preset.name,
            "delta": delta,
            "voxel_size": args.voxel_size,
            "z_ground": z_ground,
            "boxes": boxes,
        }
        json_path = args.out / f"boxes-{tag}.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        draw_side_view(points, boxes, args.out / f"side-{tag}.png", delta, args.voxel_size)
        summary.append(
            {
                "frame_id": frame,
                "dataset": preset.name,
                "delta": f"{delta:g}",
                "voxel_size": f"{args.voxel_size:g}",
                "n_boxes": len(boxes),
                "mean_z": mean_z,
            }
        )
        rear = sum(box["x"] < 0 for box in boxes)
        counts = {}
        for box in boxes:
            counts[box["label"]] = counts.get(box["label"], 0) + 1
        tally = " ".join(f"{name}={count}" for name, count in sorted(counts.items()))
        print(
            f"delta={delta:g} voxel={args.voxel_size:g} boxes={len(boxes)} "
            f"rear={rear} mean_z={mean_z or '-'} {tally}"
        )
    write_summary(args.out / "summary.csv", summary)


if __name__ == "__main__":
    main()

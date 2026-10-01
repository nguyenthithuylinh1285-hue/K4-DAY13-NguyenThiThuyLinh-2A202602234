"""CPU stand-in for the CUDA bird's-eye NMS used at inference.

The checkpoint and the PointPillars head are unchanged. Only the final
suppression runs on CPU, because the upstream ``nms_gpu`` kernel needs CUDA.
"""

import math

import torch


def boxes_overlap_bev(boxes_a, boxes_b):
    """Return a zero overlap matrix.

    Args:
        boxes_a: Boxes of shape (M, 5).
        boxes_b: Boxes of shape (N, 5).

    Returns:
        A zero tensor of shape (M, N). Training-time IoU is not used here.
    """
    return boxes_a.new_zeros((boxes_a.shape[0], boxes_b.shape[0]))


def boxes_iou_bev(boxes_a, boxes_b):
    """Return a zero IoU matrix.

    Args:
        boxes_a: Boxes of shape (M, 5).
        boxes_b: Boxes of shape (N, 5).

    Returns:
        A zero tensor of shape (M, N).
    """
    return boxes_overlap_bev(boxes_a, boxes_b)


def _corners(box):
    """Return the four ground-plane corners of one rotated-box record.

    Matches ``rotate_around_center`` in the upstream CUDA kernel, which turns
    the axis-aligned rectangle by ``-yaw`` around its center.

    Args:
        box: Sequence ``x1, y1, x2, y2, yaw``.

    Returns:
        Four ``(x, y)`` tuples in order around the rectangle.
    """
    x1, y1, x2, y2, yaw = (float(value) for value in box)
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2
    cosine = math.cos(yaw)
    sine = math.sin(yaw)
    corners = []
    for x, y in ((x1, y1), (x2, y1), (x2, y2), (x1, y2)):
        dx = x - center_x
        dy = y - center_y
        corners.append((dx * cosine + dy * sine + center_x, -dx * sine + dy * cosine + center_y))
    return corners


def _clip(subject, edge_start, edge_end):
    """Keep the part of a convex polygon on the left of one directed edge.

    Args:
        subject: Polygon vertices.
        edge_start: First point of the clipping edge.
        edge_end: Second point of the clipping edge.

    Returns:
        Clipped polygon vertices. Empty when nothing is left.
    """

    def side(point):
        return (edge_end[0] - edge_start[0]) * (point[1] - edge_start[1]) - (edge_end[1] - edge_start[1]) * (
            point[0] - edge_start[0]
        )

    output = []
    for index, current in enumerate(subject):
        previous = subject[index - 1]
        current_side = side(current)
        previous_side = side(previous)
        if current_side >= 0:
            if previous_side < 0:
                ratio = previous_side / (previous_side - current_side)
                output.append((previous[0] + ratio * (current[0] - previous[0]), previous[1] + ratio * (current[1] - previous[1])))
            output.append(current)
        elif previous_side >= 0:
            ratio = previous_side / (previous_side - current_side)
            output.append((previous[0] + ratio * (current[0] - previous[0]), previous[1] + ratio * (current[1] - previous[1])))
    return output


def _area(polygon):
    """Return the unsigned shoelace area of a polygon.

    Args:
        polygon: Vertices in order.

    Returns:
        Area in square meters.
    """
    total = 0.0
    for index, current in enumerate(polygon):
        previous = polygon[index - 1]
        total += previous[0] * current[1] - current[0] * previous[1]
    return abs(total) / 2


def _counter_clockwise(polygon):
    """Return the polygon with counter-clockwise vertex order.

    Args:
        polygon: Vertices of a convex polygon.

    Returns:
        The same vertices, reversed when the signed area is negative.
    """
    signed = sum(
        polygon[index - 1][0] * current[1] - current[0] * polygon[index - 1][1]
        for index, current in enumerate(polygon)
    )
    return polygon if signed >= 0 else polygon[::-1]


def _rotated_iou(box_a, box_b):
    """Ground-plane IoU of two rotated-box records.

    Args:
        box_a: Sequence ``x1, y1, x2, y2, yaw``.
        box_b: Same layout as ``box_a``.

    Returns:
        IoU in ``[0, 1]``.
    """
    corners_a = _counter_clockwise(_corners(box_a))
    corners_b = _counter_clockwise(_corners(box_b))
    area_a = _area(corners_a)
    area_b = _area(corners_b)
    overlap = corners_a
    for index, edge_end in enumerate(corners_b):
        if not overlap:
            break
        overlap = _clip(overlap, corners_b[index - 1], edge_end)
    inter = _area(overlap) if len(overlap) >= 3 else 0.0
    union = area_a + area_b - inter
    return inter / union if union > 1e-6 else 0.0


def _rotated_iou_matrix(boxes):
    """Pairwise rotated ground-plane IoU of rotated-box records.

    Args:
        boxes: Tensor (N, 5) as ``x1, y1, x2, y2, yaw``.

    Returns:
        IoU matrix of shape (N, N).
    """
    records = boxes.detach().cpu().tolist()
    radius = [math.hypot(box[2] - box[0], box[3] - box[1]) / 2 for box in records]
    center = [((box[0] + box[2]) / 2, (box[1] + box[3]) / 2) for box in records]
    overlap = torch.zeros((len(records), len(records)), dtype=torch.float32)
    for row in range(len(records)):
        overlap[row, row] = 1.0
        for column in range(row + 1, len(records)):
            gap = math.hypot(center[row][0] - center[column][0], center[row][1] - center[column][1])
            if gap >= radius[row] + radius[column]:
                continue
            value = _rotated_iou(records[row], records[column])
            overlap[row, column] = value
            overlap[column, row] = value
    return overlap


def nms_cuda(boxes, scores, thresh, pre_maxsize=None, post_max_size=None):
    """Greedy NMS with the same signature as the CUDA helper.

    Args:
        boxes: Tensor (N, 5), ``x1, y1, x2, y2, yaw``.
        scores: Tensor (N,).
        thresh: Drop a lower-scoring box when IoU is above this value.
        pre_maxsize: Optional cap before NMS.
        post_max_size: Optional cap after NMS.

    Returns:
        Kept indices into the original ``scores`` tensor, highest score first.
        Overlap is the rotated ground-plane IoU, as in the CUDA kernel.
    """
    order = scores.sort(0, descending=True)[1]
    if pre_maxsize is not None:
        order = order[:pre_maxsize]
    ordered = boxes[order]
    overlap = _rotated_iou_matrix(ordered)
    suppressed = torch.zeros(ordered.size(0), dtype=torch.bool)
    keep = []
    for index in range(ordered.size(0)):
        if suppressed[index]:
            continue
        keep.append(index)
        suppressed |= overlap[index] > thresh
        suppressed[index] = False
    kept = order[torch.tensor(keep, dtype=torch.long)] if keep else order[:0]
    if post_max_size is not None:
        kept = kept[:post_max_size]
    return kept.contiguous()

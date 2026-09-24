"""Connected component analysis, line clustering, and comic balloon filtering."""
from typing import List, Dict, Tuple, Any
import numpy as np


def connected_components(mask: np.ndarray) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """Label connected ink components (4-connected) iteratively.

    Returns:
        labels: 2D int32 array where 0 is background, >0 is component ID.
        comps: List of dicts with keys: id, x0, y0, x1, y1, pixels.
    """
    H, W = mask.shape
    labels = np.zeros((H, W), dtype=np.int32)
    comps = []
    cur_id = 0
    ys, xs = np.nonzero(mask)
    stack = []

    for sy, sx in zip(ys, xs):
        if labels[sy, sx]:
            continue
        cur_id += 1
        labels[sy, sx] = cur_id
        stack.append((sy, sx))
        minx = maxx = sx
        miny = maxy = sy
        npix = 0

        while stack:
            y, x = stack.pop()
            npix += 1
            if x < minx: minx = x
            if x > maxx: maxx = x
            if y < miny: miny = y
            if y > maxy: maxy = y

            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and not labels[ny, nx]:
                    labels[ny, nx] = cur_id
                    stack.append((ny, nx))

        comps.append({
            "id": cur_id,
            "x0": int(minx),
            "y0": int(miny),
            "x1": int(maxx) + 1,
            "y1": int(maxy) + 1,
            "pixels": npix,
        })

    return labels, comps


def tighten(mask: np.ndarray) -> np.ndarray:
    """Crop mask tightly to its nonzero bounding box."""
    ys, xs = np.nonzero(mask)
    if not len(ys):
        return mask
    return mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def drop_rules(
    comps: List[Dict[str, Any]],
    width: int,
    height: int,
    max_w_frac: float = 0.55,
    max_h_frac: float = 0.42
) -> List[Dict[str, Any]]:
    """Filter out panel borders, dialogue balloon contours, and guide lines.

    In comic artwork, speech balloon outlines and panel gutters often create
    massive connected components spanning most of the panel. This drops them.
    """
    return [
        c for c in comps
        if (c["x1"] - c["x0"]) < max_w_frac * width
        and (c["y1"] - c["y0"]) < max_h_frac * height
    ]


def filter_noise(comps: List[Dict[str, Any]], min_pixels: int = 8) -> List[Dict[str, Any]]:
    """Remove tiny dust specks and paper grain."""
    return [c for c in comps if c["pixels"] >= min_pixels]


def group_lines(comps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Cluster components into text lines by clustering bottom edges.

    Standard vertical overlap merging fails on hand-lettered text because
    descenders from line 1 and ascenders from line 2 interlock.
    Clustering the bottom edges of core letterforms cleanly separates rows.
    """
    if not comps:
        return []

    hs = sorted(c["y1"] - c["y0"] for c in comps)
    h = hs[len(hs) // 2] if hs else 20
    if h == 0:
        h = 20

    core = [c for c in comps if 0.45 * h <= (c["y1"] - c["y0"]) <= 1.8 * h] or comps
    bottoms = sorted(c["y1"] for c in core)

    bases = []
    run = [bottoms[0]]
    for b in bottoms[1:]:
        if b - run[-1] > 0.45 * h:
            bases.append(run)
            run = [b]
        else:
            run.append(b)
    bases.append(run)

    base_y = [sorted(r)[len(r) // 2] for r in bases]
    lines = [{"base": b, "items": []} for b in base_y]

    for c in comps:
        cy = (c["y0"] + c["y1"]) / 2.0
        best = min(range(len(base_y)), key=lambda k: abs(cy - (base_y[k] - 0.35 * h)))
        lines[best]["items"].append(c)

    # Sort lines vertically and components horizontally
    active_lines = [ln for ln in lines if ln["items"]]
    for ln in active_lines:
        ln["items"].sort(key=lambda c: c["x0"])
        ln["x0"] = min(c["x0"] for c in ln["items"])
        ln["x1"] = max(c["x1"] for c in ln["items"])
        ln["y0"] = min(c["y0"] for c in ln["items"])
        ln["y1"] = max(c["y1"] for c in ln["items"])

    active_lines.sort(key=lambda l: l["base"])
    return active_lines

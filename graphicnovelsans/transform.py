"""Geometric and morphological transformations: Bold dilation and Italic shear."""
import math
from typing import List, Tuple
import numpy as np
from .segment import connected_components


def _circular_disc(radius: int) -> List[Tuple[int, int]]:
    """Return relative (dy, dx) coordinates for a circular disc."""
    offsets = []
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dy * dy + dx * dx <= radius * radius + radius:
                offsets.append((dy, dx))
    return offsets


def _shift_mask(mask: np.ndarray, dy: int, dx: int, fill: bool = False) -> np.ndarray:
    """Translate mask by (dy, dx) without circular wrap."""
    out = np.full(mask.shape, fill, dtype=bool)
    H, W = mask.shape
    out[max(0, dy):min(H, H + dy), max(0, dx):min(W, W + dx)] = \
        mask[max(0, -dy):min(H, H - dy), max(0, -dx):min(W, W - dx)]
    return out


def _grow_mask(mask: np.ndarray, radius: int) -> np.ndarray:
    out = np.zeros_like(mask)
    for dy, dx in _circular_disc(radius):
        out |= _shift_mask(mask, dy, dx, fill=False)
    return out


def _shrink_mask(mask: np.ndarray, radius: int) -> np.ndarray:
    out = np.ones_like(mask)
    for dy, dx in _circular_disc(radius):
        out &= _shift_mask(mask, dy, dx, fill=True)
    return out


def dilate_with_counter_protection(mask: np.ndarray, radius: int) -> np.ndarray:
    """Dilate ink mask while protecting internal counter holes.

    Direct outline offsetting causes ugly self-intersecting loops and notch
    artifacts at pen stroke intersections. Dilating in pixel space keeps
    natural stroke overlaps intact.

    Crucially, simply dilating closes small counter holes in letters like
    '8', 'e', 'o', 'B', 'a'. This algorithm identifies internal enclosed
    holes and gently shrinks them rather than flooding them, keeping the
    letter legible as a Bold.
    """
    if radius < 1:
        return mask

    # Pad mask to allow stroke expansion
    H, W = mask.shape
    pad = np.zeros((H + 2 * radius, W + 2 * radius), dtype=bool)
    pad[radius:radius + H, radius:radius + W] = mask

    # Dilate ink
    dilated = _grow_mask(pad, radius)

    # Invert to find empty spaces and identify closed counters vs page background
    labels, comps = connected_components(~pad)
    pad_h, pad_w = pad.shape

    for c in comps:
        # If the component touches the canvas outer boundary, it is external page space
        if c["x0"] == 0 or c["y0"] == 0 or c["x1"] == pad_w or c["y1"] == pad_h:
            continue

        # This is an internal counter hole
        hole = labels == c["id"]
        # Shrink the hole by (radius - 1) down to 0
        for k in range(radius - 1, -1, -1):
            keep = _shrink_mask(hole, k)
            if keep.any():
                dilated &= ~keep
                break

    return dilated


def shear_contours(
    contours: List[List[Tuple[float, float]]],
    shear: float
) -> List[List[Tuple[float, float]]]:
    """Apply horizontal shear to font contours: (x + y * shear, y)."""
    if abs(shear) < 1e-6:
        return contours
    return [[(x + y * shear, y) for x, y in c] for c in contours]


def calculate_italic_shear(natural_slant: float, target_lean_degrees: float = 11.0) -> float:
    """Compute the shear needed to transform the natural hand lean to target lean."""
    if target_lean_degrees == 0.0:
        return 0.0
    target_tan = math.tan(math.radians(target_lean_degrees))
    return target_tan - natural_slant

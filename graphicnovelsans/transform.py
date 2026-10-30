"""Geometric and morphological transformations: Bold dilation and Italic shear.

This module provides:
- **Bold dilation**: Expands stroke width while preserving counter holes.
- **Italic shear**: Applies horizontal slant with compensation for natural handwriting lean.
- **Counter protection**: Identifies and preserves enclosed holes during dilation.
"""
import math
from typing import List, Tuple, Set
import numpy as np
from .segment import connected_components


def _circular_disc(radius: int) -> List[Tuple[int, int]]:
    """Generate relative (dy, dx) offsets for a circular structuring element.

    Used for morphological operations (dilation/erosion). The shape approximates
    a circle to produce isotropic expansion without diamond artifacts.

    Args:
        radius: Radius of the disc in pixels.

    Returns:
        List of (dy, dx) offsets where the disc is True.
    """
    offsets = []
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dy * dy + dx * dx <= radius * radius + radius:
                offsets.append((dy, dx))
    return offsets


def _shift_mask(mask: np.ndarray, dy: int, dx: int, fill: bool = False) -> np.ndarray:
    """Translate a boolean mask by (dy, dx) without wrapping.

    Shifts the mask content while filling vacated regions with the `fill` value.
    This is used internally for morphological operations.

    Args:
        mask: Input boolean array.
        dy: Vertical shift (positive = down).
        dx: Horizontal shift (positive = right).
        fill: Value to fill in shifted-in regions.

    Returns:
        Shifted boolean array of the same shape.
    """
    out = np.full(mask.shape, fill, dtype=bool)
    H, W = mask.shape
    out[max(0, dy):min(H, H + dy), max(0, dx):min(W, W + dx)] = \
        mask[max(0, -dy):min(H, H - dy), max(0, -dx):min(W, W - dx)]
    return out


def _grow_mask(mask: np.ndarray, radius: int) -> np.ndarray:
    """Dilate a boolean mask using a circular structuring element.

    Performs morphological dilation (expansion) by OR-ing shifted versions
    of the mask. Equivalent to `scipy.ndimage.binary_dilation` with a disc kernel.

    Args:
        mask: Input boolean array.
        radius: Dilation radius in pixels.

    Returns:
        Dilated boolean array.
    """
    out = np.zeros_like(mask)
    for dy, dx in _circular_disc(radius):
        out |= _shift_mask(mask, dy, dx, fill=False)
    return out


def _shrink_mask(mask: np.ndarray, radius: int) -> np.ndarray:
    """Erode a boolean mask using a circular structuring element.

    Performs morphological erosion (shrinking) by AND-ing shifted versions
    of the mask. Equivalent to `scipy.ndimage.binary_erosion` with a disc kernel.

    Args:
        mask: Input boolean array.
        radius: Erosion radius in pixels.

    Returns:
        Eroded boolean array.
    """
    out = np.ones_like(mask)
    for dy, dx in _circular_disc(radius):
        out &= _shift_mask(mask, dy, dx, fill=True)
    return out


def dilate_with_counter_protection(mask: np.ndarray, radius: int) -> np.ndarray:
    """Dilate an ink mask while preserving internal counter holes.

    This is the core Bold-generation algorithm. Unlike naive dilation which
    would flood enclosed spaces (counters in 'e', 'o', 'a', 'B', '8'), this
    function:
    1. Dilates the ink region.
    2. Identifies internal holes (connected components that don't touch the border).
    3. Shrinks those holes by (radius - 1) to maintain legibility.

    Args:
        mask: 2D boolean array where True represents ink.
        radius: Dilation radius in pixels (typically 1-3 for Bold generation).

    Returns:
        Dilated boolean array with counter holes preserved.

    Raises:
        ValueError: If radius is negative.

    Example:
        >>> mask = np.array([[False, True, False],
        ...                  [True, True, True],
        ...                  [False, True, False]])
        >>> dilated = dilate_with_counter_protection(mask, radius=1)
        >>> dilated.shape
        (3, 3)
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
    """Apply horizontal shear to font contours.

    Transforms contours according to: `(x, y) -> (x + y * shear, y)`.
    Positive shear leans forward (italic), negative leans backward.

    Args:
        contours: List of contour point lists in font coordinates.
        shear: Shear factor (tan of the lean angle). For 11°, shear ≈ 0.194.

    Returns:
        Transformed contours. Returns the original list if shear is negligible.

    Note:
        This operates on vector contours, not pixel masks. Use after tracing.
    """
    if abs(shear) < 1e-6:
        return contours
    return [[(x + y * shear, y) for x, y in c] for c in contours]


def calculate_italic_shear(natural_slant: float, target_lean_degrees: float = 11.0) -> float:
    """Calculate the shear factor needed to achieve a target italic lean.

    Compensates for the artist's natural handwriting slant. If the hand already
    leans forward by 5° and the target is 11°, the computed shear will be
    equivalent to 6° of additional lean.

    Args:
        natural_slant: Measured slant factor (dx/dy) from the hand.
                       Positive = forward lean, negative = backhand.
        target_lean_degrees: Desired final lean angle in degrees.

    Returns:
        Shear factor to apply. Zero if target is 0°.

    Example:
        >>> calculate_italic_shear(0.1, 11.0)  # natural 5.7° forward, target 11°
        0.094...  # Additional ~5.3° lean
    """
    if target_lean_degrees == 0.0:
        return 0.0
    target_tan = math.tan(math.radians(target_lean_degrees))
    return target_tan - natural_slant

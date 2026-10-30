"""Contour tracing, polygon simplification, and curvature-sensitive Bézier fitting.

This module converts binary ink masks into vector contours suitable for TrueType
font compilation. It employs:
- Marching Squares for initial contour extraction
- Ramer-Douglas-Peucker (RDP) for polygon simplification
- Curvature-aware quadratic Bézier fitting for smooth curves

Key considerations:
- Upscaling (UPSCALE=4) before tracing reduces stair-step artifacts.
- Contours are oriented clockwise for outer shapes, counter-clockwise for holes.
- Sharp corners (>52°) remain on-curve; gentle turns become off-curve control points.
"""
import math
from typing import List, Tuple, Any, Optional
from dataclasses import dataclass
import numpy as np

UPSCALE: int = 4  #: Supersampling factor prior to tracing to reduce aliasing artifacts.


@dataclass(frozen=True)
class ContourPoint:
    """A single point in a contour path."""
    x: float
    y: float

    def __iter__(self):
        yield self.x
        yield self.y


Contour = List[ContourPoint]
Contours = List[Contour]


def _rdp(pts: List[ContourPoint], eps: float) -> List[ContourPoint]:
    """Simplify a polygon using the Ramer-Douglas-Peucker algorithm.

    Preserves significant geometric features while removing redundant vertices.
    Ideal for reducing the point count from marching squares without losing
    the essential shape of hand-drawn letters.

    Args:
        pts: Ordered list of contour points.
        eps: Simplification tolerance. Points farther than this distance from
             the simplified line segment are kept.

    Returns:
        A simplified list of contour points. The first and last points are always preserved.

    Example:
        >>> pts = [ContourPoint(0,0), ContourPoint(1,1), ContourPoint(2,0)]
        >>> _rdp(pts, eps=0.5)
        [ContourPoint(x=0.0, y=0.0), ContourPoint(x=2.0, y=0.0)]
    """
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        ax, ay = pts[a]
        bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        n = math.hypot(dx, dy)
        best = -1.0
        bi = -1
        for i in range(a + 1, b):
            px, py = pts[i]
            if n == 0:
                dist = math.hypot(px - ax, py - ay)
            else:
                dist = abs(dy * (px - ax) - dx * (py - ay)) / n
            if dist > best:
                best = dist
                bi = i
        if best > eps:
            keep[bi] = True
            stack.append((a, bi))
            stack.append((bi, b))
    return [p for p, k in zip(pts, keep) if k]


def rdp_simplify(points: Contour, epsilon: float = 1.0) -> Contour:
    """Public wrapper for RDP simplification.

    Args:
        points: Input contour points.
        epsilon: Simplification tolerance.

    Returns:
        Simplified contour.
    """
    return _rdp(points, epsilon)


def _marching_squares(bin_img: np.ndarray) -> Contours:
    """Extract closed contours using the Marching Squares algorithm.

    Converts a 2D boolean mask into a set of closed polygon contours by
    interpolating edges between grid cells where the value changes from
    background to foreground.

    Args:
        bin_img: 2D boolean array where True represents ink.

    Returns:
        List of contours, where each contour is a list of (x, y) points.
        Points are in pixel coordinates relative to the upscaled image.

    Note:
        The algorithm pads the input image by 1 pixel to handle edge cases
        and ensures all contours are closed loops.
    """
    """Extract closed contours using marching squares over the pixel grid."""
    H, W = bin_img.shape
    g = np.zeros((H + 2, W + 2), dtype=bool)
    g[1:-1, 1:-1] = bin_img

    segs = {}
    for y in range(g.shape[0] - 1):
        row_tl = g[y, :-1]
        row_tr = g[y, 1:]
        row_bl = g[y + 1, :-1]
        row_br = g[y + 1, 1:]
        code = (row_tl.astype(np.uint8) << 3) | (row_tr.astype(np.uint8) << 2) \
             | (row_br.astype(np.uint8) << 1) | row_bl.astype(np.uint8)

        for x in np.nonzero((code != 0) & (code != 15))[0]:
            c = int(code[x])
            T = (x + 0.5, y + 0.0)
            B = (x + 0.5, y + 1.0)
            L = (x + 0.0, y + 0.5)
            R = (x + 1.0, y + 0.5)
            table = {
                1:  [(L, B)], 2:  [(B, R)], 3:  [(L, R)], 4:  [(R, T)],
                5:  [(L, T), (R, B)], 6:  [(B, T)], 7:  [(L, T)],
                8:  [(T, L)], 9:  [(T, B)], 10: [(T, R), (B, L)],
                11: [(T, R)], 12: [(R, L)], 13: [(R, B)], 14: [(B, L)],
            }
            for a, b in table.get(c, []):
                segs.setdefault(a, []).append(b)

    contours = []
    used = set()
    for start in list(segs.keys()):
        for k in range(len(segs[start])):
            if (start, k) in used:
                continue
            used.add((start, k))
            poly = [start]
            cur = segs[start][k]
            stuck = False
            while cur != start:
                poly.append(cur)
                nxts = segs.get(cur, [])
                chosen = None
                for ci, nxt in enumerate(nxts):
                    if (cur, ci) not in used:
                        used.add((cur, ci))
                        chosen = nxt
                        break
                if chosen is None:
                    stuck = True
                    break
                cur = chosen
            if not stuck and len(poly) >= 3:
                # Shift lattice offset back into original pixel frame
                contours.append([(p[0] - 1.0, p[1] - 1.0) for p in poly])

    return contours


def _polygon_area(poly: Contour) -> float:
    """Calculate the signed area of a polygon using the Shoelace formula.

    Positive area indicates counter-clockwise winding; negative indicates clockwise.

    Args:
        poly: List of contour points defining a closed polygon.

    Returns:
        Signed area (float).
    """
    s = 0.0
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        s += x0 * y1 - x1 * y0
    return s / 2.0


def _point_inside_poly(pt: ContourPoint, poly: Contour) -> bool:
    """Ray casting algorithm to determine if a point is inside a polygon.

    Args:
        pt: Point to test.
        poly: Polygon vertices in order.

    Returns:
        True if the point is strictly inside the polygon.
    """
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i - 1) % n]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0 + 1e-12) + x0:
            inside = not inside
    return inside


def _vertex_turn_angle(a: ContourPoint, b: ContourPoint, c: ContourPoint) -> float:
    """Calculate the interior angle at vertex b formed by edges ab and bc.

    Args:
        a: Previous vertex.
        b: Current vertex (the angle vertex).
        c: Next vertex.

    Returns:
        Angle in degrees (0.0 to 180.0).
    """
    """Angle in degrees between edges meeting at vertex b."""
    v1 = (b[0] - a[0], b[1] - a[1])
    v2 = (c[0] - b[0], c[1] - b[1])
    n1 = math.hypot(*v1)
    n2 = math.hypot(*v2)
    if n1 == 0 or n2 == 0:
        return 0.0
    cos_theta = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
    return math.degrees(math.acos(cos_theta))


def trace_mask_to_contours(
    mask: np.ndarray,
    scale: float,
    baseline_offset: float,
    epsilon: float = 1.7
) -> Contours:
    """Convert a binary ink mask into vector contours with correct winding.

    This is the core raster-to-vector conversion step. It:
    1. Upscales the mask to reduce aliasing.
    2. Extracts raw contours via Marching Squares.
    3. Simplifies polygons using RDP.
    4. Transforms coordinates to font space (y-up).
    5. Ensures correct winding (outer=CCW, inner=CW for TrueType).

    Args:
        mask: 2D boolean array where True represents ink.
        scale: Scaling factor from source pixels to font units (UPM).
        baseline_offset: Vertical offset in source pixels from the top of the mask to the baseline.
        epsilon: RDP simplification tolerance (in source pixels). Higher values = fewer points.

    Returns:
        List of contours in font coordinate system. Outer contours are clockwise (negative area),
        inner contours (holes) are counter-clockwise (positive area).

    Raises:
        ValueError: If the mask is empty or contains no valid contours.

    Example:
        >>> mask = np.array([[False, True], [True, True]])
        >>> contours = trace_mask_to_contours(mask, scale=10.0, baseline_offset=5.0)
        >>> len(contours)
        1
    """
    if not mask.any():
        return []

    up = UPSCALE
    big = np.repeat(np.repeat(mask, up, axis=0), up, axis=1)
    raw_contours = _marching_squares(big)

    simplified = []
    for c in raw_contours:
        if len(c) < 3:
            continue
        pts = rdp_simplify(c + [c[0]], epsilon=epsilon * up / 2.0)[:-1]
        if len(pts) >= 3:
            # Transform to font units (y-up coordinate system)
            fpts = [((x / up) * scale, (baseline_offset - y / up) * scale) for x, y in pts]
            simplified.append(fpts)

    if not simplified:
        return []

    # Sort contours by descending absolute area
    order = sorted(range(len(simplified)), key=lambda i: -abs(_polygon_area(simplified[i])))
    depth = []
    for i in range(len(simplified)):
        d = sum(
            1 for j in range(len(simplified))
            if j != i and abs(_polygon_area(simplified[j])) > abs(_polygon_area(simplified[i]))
            and _point_inside_poly(simplified[i][0], simplified[j])
        )
        depth.append(d)

    # In TrueType y-up coordinates: outer contours (even depth) must be clockwise (negative area).
    # Holes (odd depth) must be counter-clockwise (positive area).
    fixed = []
    for i in order:
        want_neg = (depth[i] % 2 == 0)
        p = simplified[i]
        if (_polygon_area(p) < 0) != want_neg:
            p = p[::-1]
        fixed.append(p)

    return fixed


def draw_contour_to_pen(
    pen: Any,
    pts: Contour,
    corner_deg: float = 52.0,
    short_edge: float = 26.0
) -> None:
    """Convert a contour into quadratic Bézier curves for a FontTools pen.

    This function intelligently decides which vertices should be on-curve points
    and which should be off-curve control points based on local curvature:
    - **Sharp corners** (turn angle > `corner_deg`) remain on-curve.
    - **Short edges** (length < `short_edge`) are preserved as on-curve to maintain detail.
    - **Gentle curves** become off-curve control points for smooth interpolation.

    Args:
        pen: A FontTools-compatible pen object (e.g., TTGlyphPen). Must implement
             `moveTo`, `lineTo`, `qCurveTo`, and `closePath`.
        pts: List of contour points in font coordinates.
        corner_deg: Angle threshold (degrees) for sharp corners. Angles greater than
                    this are considered sharp. Default: 52.0°.
        short_edge: Length threshold (font units) for edge preservation. Edges shorter
                    than this are treated as on-curve. Default: 26.0.

    Note:
        The algorithm handles closed loops by wrapping around the first point.
        If all points are gentle curves, a single `qCurveTo` is emitted.

    Example:
        >>> from fontTools.pens.ttGlyphPen import TTGlyphPen
        >>> pen = TTGlyphPen(None)
        >>> pts = [ContourPoint(0,0), ContourPoint(10,10), ContourPoint(20,0)]
        >>> draw_contour_to_pen(pen, pts, corner_deg=52.0)
    """
    n = len(pts)
    if n < 3:
        return

    on = []
    for i in range(n):
        a = pts[(i - 1) % n]
        b = pts[i]
        c = pts[(i + 1) % n]
        e1 = math.hypot(b[0] - a[0], b[1] - a[1])
        e2 = math.hypot(c[0] - b[0], c[1] - b[1])
        is_corner = _vertex_turn_angle(a, b, c) > corner_deg or min(e1, e2) > short_edge * 4
        on.append(is_corner)

    if not any(on):
        pen.qCurveTo(*[tuple(p) for p in pts], None)
        pen.closePath()
        return

    start_idx = on.index(True)
    seq = [(pts[(start_idx + k) % n], on[(start_idx + k) % n]) for k in range(n)]

    pen.moveTo(tuple(seq[0][0]))
    pending = []
    for p, is_on in seq[1:]:
        if is_on:
            if pending:
                pen.qCurveTo(*[tuple(q) for q in pending], tuple(p))
                pending = []
            else:
                pen.lineTo(tuple(p))
        else:
            pending.append(p)

    if pending:
        pen.qCurveTo(*[tuple(q) for q in pending], tuple(seq[0][0]))

    pen.closePath()

"""Contour tracing, polygon simplification, and curvature-sensitive Bézier fitting."""
import math
from typing import List, Tuple, Any
import numpy as np

UPSCALE = 4  # Supersampling factor prior to tracing


def _rdp(pts: List[Tuple[float, float]], eps: float) -> List[Tuple[float, float]]:
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


def rdp_simplify(points: List[Tuple[float, float]], epsilon: float = 1.0) -> List[Tuple[float, float]]:
    return _rdp(points, epsilon)


def _marching_squares(bin_img: np.ndarray) -> List[List[Tuple[float, float]]]:
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


def _polygon_area(poly: List[Tuple[float, float]]) -> float:
    s = 0.0
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        s += x0 * y1 - x1 * y0
    return s / 2.0


def _point_inside_poly(pt: Tuple[float, float], poly: List[Tuple[float, float]]) -> bool:
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i - 1) % n]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0 + 1e-12) + x0:
            inside = not inside
    return inside


def _vertex_turn_angle(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> float:
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
) -> List[List[Tuple[float, float]]]:
    """Convert binary ink mask into font-unit vector contours with proper winding.

    Args:
        mask: 2D boolean mask.
        scale: Font units per source pixel.
        baseline_offset: Source pixels from glyph top to the baseline.
        epsilon: RDP simplification tolerance.
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
    pts: List[Tuple[float, float]],
    corner_deg: float = 52.0,
    short_edge: float = 26.0
) -> None:
    """Emit contour to a FontTools pen as quadratic Béziers.

    Vertices with a sharp turn (> corner_deg) or short edges (pen detail) stay
    on-curve. Gentle turns become off-curve quadratic control points, giving the
    handwritten curve feel.
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

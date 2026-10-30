"""Automated 40-band edge profiling, flank sidebearings, and band-gap kerning engine.

This module implements a specialized kerning algorithm optimized for comic lettering:
1. **Edge Profiling**: Slices glyphs into 40 horizontal bands to capture vertical variation.
2. **Flank Sidebearings**: Calculates LSB/RSB based on clear space targets.
3. **Band-Gap Kerning**: Adjusts spacing based on the narrowest gap between adjacent glyphs.

Key Constants:
    BANDS: Number of horizontal slices (higher = more precise but slower).
    LIMIT: Minimum adjustment magnitude to apply (filters noise).
    MAXNEG/MAXPOS: Absolute limits on kerning values.
    TUCK: Maximum allowed overlap as a fraction of advance width.
    MIN_TIGHT/MAX_TIGHT: Target range for closest approach (prevents collisions/holes).
    AREA: Target clear space on each flank (sidebearing calculation).
    FLANK_FLOOR: Minimum sidebearing to prevent negative spacing.
"""
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass

# Import typography constants used in default arguments
from .typography import DESCENDER, ASCENDER, X_HEIGHT

# Kerning Algorithm Constants
BANDS: int = 40
LIMIT: int = 12
MAXNEG: int = -300
MAXPOS: int = 150
TUCK: float = 0.50
MIN_TIGHT: int = 52
MAX_TIGHT: int = 200
AREA: float = 62.0
FLANK_FLOOR: float = 10.0

This module implements a specialized kerning algorithm optimized for comic lettering:
1. **Edge Profiling**: Slices glyphs into 40 horizontal bands to capture vertical variation.
2. **Flank Sidebearings**: Calculates LSB/RSB based on clear space targets.
3. **Band-Gap Kerning**: Adjusts spacing based on the narrowest gap between adjacent glyphs.

Key Constants:
    BANDS: Number of horizontal slices (higher = more precise but slower).
    LIMIT: Minimum adjustment magnitude to apply (filters noise).
    MAXNEG/MAXPOS: Absolute limits on kerning values.
    TUCK: Maximum allowed overlap as a fraction of advance width.
    MIN_TIGHT/MAX_TIGHT: Target range for closest approach (prevents collisions/holes).
    AREA: Target clear space on each flank (sidebearing calculation).
    FLANK_FLOOR: Minimum sidebearing to prevent negative spacing.
"""
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass

# Kerning Algorithm Constants
BANDS: int = 40
LIMIT: int = 12
MAXNEG: int = -300
MAXPOS: int = 150
TUCK: float = 0.50
MIN_TIGHT: int = 52
MAX_TIGHT: int = 200
AREA: float = 62.0
FLANK_FLOOR: float = 10.0


@dataclass(frozen=True)
class EdgeProfile:
    """Edge profile data for a single glyph.

    Attributes:
        bands: List of (leftmost_x, rightmost_x) tuples for each band. None if no ink in band.
        adv: Advance width of the glyph.
        ink: Total number of ink pixels (approximate).
    """
    bands: List[Tuple[float, float]]
    adv: float
    ink: int


def _densify_contour(contour: List[Tuple[float, float]], step: float = 12.0) -> List[Tuple[float, float]]:
    out = []
    n = len(contour)
    for i in range(n):
        x0, y0 = contour[i]
        x1, y1 = contour[(i + 1) % n]
        d = max(abs(x1 - x0), abs(y1 - y0))
        k = max(1, int(d / step))
        for t in range(k):
            out.append((x0 + (x1 - x0) * t / k, y0 + (y1 - y0) * t / k))
    return out


def compute_edge_profile(
    contours: List[List[Tuple[float, float]]],
    advance: float,
    descender: float = DESCENDER,
    ascender: float = ASCENDER,
    shift: float = 0.0
) -> EdgeProfile:
    """Slice a glyph into horizontal bands and record edge positions.

    Creates a 40-band profile from the descender to the ascender, capturing
    the leftmost and rightmost ink position in each band. This profile is
    used for both sidebearing calculation and kerning pair analysis.

    Args:
        contours: List of glyph contours in font coordinates.
        advance: Glyph advance width.
        descender: Baseline offset for the bottom of the band system (default: -220).
        ascender: Baseline offset for the top of the band system (default: 800).
        shift: Horizontal shift to apply to all points (for kerning calculations).

    Returns:
        EdgeProfile containing the band data, advance, and ink count.

    Note:
        Bands are indexed 0 (bottom) to 39 (top). A band value of None indicates
        no ink intersects that horizontal slice.
    """
    bands = [None] * BANDS
    span = (ascender - descender) / float(BANDS)

    for c in contours:
        for x, y in _densify_contour(c):
            i = int((y - descender) / span)
            if 0 <= i < BANDS:
                x_shifted = x + shift
                b = bands[i]
                bands[i] = (x_shifted, x_shifted) if b is None else (min(b[0], x_shifted), max(b[1], x_shifted))

    return {
        "bands": bands,
        "adv": advance,
        "ink": sum(1 for b in bands if b is not None)
    }


def compute_flanks(
    bands: List[Optional[Tuple[float, float]]],
    descender: float = DESCENDER,
    ascender: float = ASCENDER,
    zone: Tuple[float, float] = (0, X_HEIGHT),
    target_area: float = AREA,
    floor: float = FLANK_FLOOR
) -> Tuple[float, float]:
    """Calculate Left and Right Sidebearings from an edge profile.

    Determines the optimal spacing around a glyph by analyzing the clear space
    on its left and right flanks within the x-height zone. The algorithm aims
    for a target clear space (`AREA`) while respecting a minimum floor.

    Args:
        bands: Edge profile bands from `compute_edge_profile`.
        descender: Bottom of the band system.
        ascender: Top of the band system.
        zone: (y_min, y_max) range to analyze for sidebearings (default: x-height zone).
        target_area: Desired clear space on each flank.
        floor: Minimum allowed sidebearing value.

    Returns:
        Tuple of (LSB, RSB) in font units.

    Note:
        If no ink is found in the specified zone, the function falls back to
        analyzing the entire glyph height.
    """
    span = (ascender - descender) / float(len(bands))
    zl, zh = zone
    idx = [
        i for i, b in enumerate(bands)
        if b is not None and zl <= descender + (i + 0.5) * span <= zh
    ]
    if not idx:
        idx = [i for i, b in enumerate(bands) if b is not None]
    if not idx:
        return floor, floor

    ink = [bands[i] for i in idx]
    x0 = min(b[0] for b in bands if b is not None)
    x1 = max(b[1] for b in bands if b is not None)

    left_inset = sum(b[0] - x0 for b in ink) / len(ink)
    right_inset = sum(x1 - b[1] for b in ink) / len(ink)

    lsb = max(floor, target_area - left_inset)
    rsb = max(floor, target_area - right_inset)
    return lsb, rsb


def compute_kern_pairs(
    profiles: Dict[str, EdgeProfile],
    limit: int = LIMIT
) -> Dict[Tuple[str, str], int]:
    """Calculate optimal kerning adjustments for all glyph pairs.

    Analyzes the closest approach between every ordered pair of glyphs in the
    provided profiles. Adjustments are made to:
    - Prevent collisions (gap < MIN_TIGHT)
    - Reduce visual holes (gap > MAX_TIGHT)

    Args:
        profiles: Dictionary mapping glyph names to their EdgeProfiles.
        limit: Minimum adjustment magnitude to include in the result.

    Returns:
        Dictionary mapping (glyph_a, glyph_b) tuples to adjustment values (font units).
        Positive values push glyphs apart; negative values allow overlap (tuck).

    Note:
        Adjustments are clamped to [MAXNEG, MAXPOS] and filtered by `limit`.
        Tucking is limited to TUCK * advance_width of the leading glyph.
    """
    gaps = {}
    names = sorted(profiles)

    for a in names:
        pa = profiles[a]
        for b in names:
            pb = profiles[b]
            gap = None
            for ba, bb in zip(pa["bands"], pb["bands"]):
                if ba is None or bb is None:
                    continue
                g = (pa["adv"] - ba[1]) + bb[0]
                gap = g if gap is None else min(gap, g)

            if gap is None:
                continue

            shared = sum(1 for ba, bb in zip(pa["bands"], pb["bands"]) if ba is not None and bb is not None)
            tall = max(pa["ink"], pb["ink"])
            gaps[(a, b)] = (gap, shared / float(tall) if tall else 0.0)

    kerns = {}
    for (a, b), (gap, frac) in gaps.items():
        if gap < MIN_TIGHT:
            # Collision prevention
            v = MIN_TIGHT - gap
        elif gap > MAX_TIGHT:
            # Hole closure, attenuated by shared vertical overlap
            v = frac * (MAX_TIGHT - gap)
        else:
            continue

        v = int(round(max(v, -TUCK * profiles[a]["adv"])))
        if abs(v) < limit:
            continue

        kerns[(a, b)] = max(MAXNEG, min(MAXPOS, v))

    return kerns


def generate_fea(kerns: Dict[Tuple[str, str], int], path: str) -> str:
    """Write an OpenType Feature file for kern lookup."""
    with open(path, "w", encoding="utf-8") as f:
        f.write("# generated by graphicnovelsans kern engine\n")
        f.write("feature kern {\n")
        for (a, b), v in sorted(kerns.items()):
            f.write(f"    pos {a} {b} {v};\n")
        f.write("} kern;\n")
    return path


def create_legacy_kern_table(kerns: Dict[Tuple[str, str], int], glyph_order: set, cap: int = 10920) -> Any:
    """Build a format-0 legacy binary 'kern' table for older applications."""
    from fontTools.ttLib import newTable
    from fontTools.ttLib.tables import _k_e_r_n as K

    keep = kerns
    if len(keep) > cap:
        top = sorted(keep.items(), key=lambda kv: -abs(kv[1]))[:cap]
        keep = dict(top)

    st = K.KernTable_format_0(apple=False)
    st.format = 0
    st.version = 0
    st.coverage = 1
    st.tupleIndex = None
    st.kernTable = {
        k: v for k, v in keep.items()
        if k[0] in glyph_order and k[1] in glyph_order
    }

    t = newTable("kern")
    t.version = 0
    t.kernTables = [st]
    return t, len(st.kernTable)

"""Derive kerning from the glyphs' own outlines, band by band.

One sidebearing per glyph cannot space a hand. A capital T's crossbar runs to
the edge of its advance, but at x-height there is nothing there but the stem, so
whatever follows sits in a hole. Measuring the free space in horizontal bands and
kerning by the *tightest* band closes the hole without letting the ink collide:
the pair ends up showing the same clear space at its closest approach as two
flat-sided letters would.
"""
import os

BANDS  = 40      # horizontal slices from descender to ascender
LIMIT  = 12      # drop adjustments smaller than this, so the table stays honest
MAXNEG = -300    # never tuck a glyph further than this under its neighbour
MAXPOS = 150     # nor push one this far away to resolve an overlap
TUCK   = 0.50    # nor back past the midpoint of the letter it follows

# A dead band, not a target. Once every glyph is spaced on its own flanks the
# typical pair is already right, so kerning has only the two ends of the
# distribution left to fix: pairs whose ink now comes too close, and pairs with a
# hole no sidebearing can reach because the letters only meet at one height.
# Kerning to a single value instead put a correction on 4639 of 5476 pairs, which
# is not a kern table -- it is a tracking change wearing one's clothes.
MIN_TIGHT = 52   # closest the ink of two letters may ever come
MAX_TIGHT = 200  # widest their closest approach may be before it reads as a gap


def densify(contour, step=12.0):
    """Walk each edge in short steps.

    The contours are RDP-simplified, so a bowl's leftmost point is usually
    between two stored vertices. Sampling along the edges finds it; sampling the
    vertices alone would report the bowl as narrower than it is and kern the
    pair into a collision.
    """
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


def profile(contours, adv, lo, hi, shift=0.0):
    """Per-band (leftmost, rightmost) ink for one glyph, in font units.

    `shift` is the sidebearing translation the glyph will get, so the profile is
    measured in the same frame as the advance width.
    """
    bands = [None] * BANDS
    span = (hi - lo) / float(BANDS)
    for c in contours:
        for x, y in densify(c):
            i = int((y - lo) / span)
            if i < 0 or i >= BANDS:
                continue
            x += shift
            b = bands[i]
            bands[i] = (x, x) if b is None else (min(b[0], x), max(b[1], x))
    return {"bands": bands, "adv": adv,
            "ink": sum(1 for b in bands if b is not None)}


AREA   = 62      # font units of average clear space wanted on each flank
FLANK  = 10      # a sidebearing never goes below this; tucking is kerning's job


def flanks(bands, adv, lo, hi, zone, area=AREA, floor=FLANK):
    """Left and right sidebearings for one glyph, from its own edge profile.

    A single side bearing for every letter is what forced the kern table to
    carry 3807 pairs: a round 'o' and a flat 'n' were given identical flanks, so
    every pair involving a curve came out loose and every one of them needed a
    correction. Averaging each flank's inset over the band range where letters
    actually meet, and spacing to a constant average instead, moves that work
    out of the table and into the metrics -- where software that ignores kerning
    still benefits from it.
    """
    span = (hi - lo) / float(len(bands))
    zl, zh = zone
    idx = [i for i, b in enumerate(bands)
           if b is not None and zl <= lo + (i + 0.5) * span <= zh]
    if not idx:                       # a mark that lives outside the zone
        idx = [i for i, b in enumerate(bands) if b is not None]
    if not idx:
        return floor, floor
    ink = [bands[i] for i in idx]
    x0 = min(b[0] for b in bands if b is not None)
    x1 = max(b[1] for b in bands if b is not None)
    left = sum(b[0] - x0 for b in ink) / len(ink)
    right = sum(x1 - b[1] for b in ink) / len(ink)
    return max(floor, area - left), max(floor, area - right)


def pairs(profiles, target=None, limit=LIMIT):
    """Kern value per ordered glyph pair, from the tightest shared band.

    The tightest band is the one that decides: it is where the two letters come
    closest, so it is the only place a collision can start. Kerning to it lets a
    'T' pull an 'o' up under its crossbar by 150 units while leaving 'ry' alone,
    because the r's arm and the y's shoulder are already as close as ink gets.
    """
    gaps, names = {}, sorted(profiles)
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
            if gap is None:       # nothing shares a band, so nothing can touch
                continue
            shared = sum(1 for ba, bb in zip(pa["bands"], pb["bands"])
                         if ba is not None and bb is not None)
            tall = max(pa["ink"], pb["ink"])
            gaps[(a, b)] = (gap, shared / float(tall) if tall else 0.0)
    out = {}
    for (a, b), (gap, frac) in gaps.items():
        if gap < MIN_TIGHT:
            # Protective, so it is never attenuated: if the ink can touch at one
            # height, one height is enough to make the pair unreadable.
            v = MIN_TIGHT - gap
        elif gap > MAX_TIGHT:
            # Closing a hole, and here the measurement has to be discounted by
            # how much of the two letters actually face each other. A period
            # standing beside an 'F' shares three bands of forty, and in those
            # three there is nothing but the F's stem, so the gap measures 292
            # units -- pulling by that much slid the period under the F and
            # 'E-mail' lost its hyphen entirely. Scaling by the shared fraction
            # of the taller glyph turns that into the light tuck it should be.
            v = frac * (MAX_TIGHT - gap)
        else:
            continue
        # And never pull the second letter back past the middle of the first.
        v = int(round(max(v, -TUCK * profiles[a]["adv"])))
        if abs(v) < limit:
            continue
        out[(a, b)] = max(MAXNEG, min(MAXPOS, v))
    return out


def write_fea(kerns, path):
    """A kern feature block, one rule per pair. Kept as a readable artifact."""
    with open(path, "w") as f:
        f.write("# generated by kern.py -- pair values from band gap profiles\n")
        f.write("feature kern {\n")
        for (a, b), v in sorted(kerns.items()):
            f.write(f"    pos {a} {b} {v};\n")
        f.write("} kern;\n")
    return path


def legacy_table(kerns, glyph_order, cap=10920):
    """A format-0 `kern` table for applications that never learned GPOS.

    Format 0 is binary-searched by the consumer, so the count has a practical
    ceiling; if there are more pairs than that, the largest adjustments are the
    ones worth keeping.
    """
    from fontTools.ttLib import newTable
    from fontTools.ttLib.tables import _k_e_r_n as K
    keep = kerns
    if len(keep) > cap:
        top = sorted(keep.items(), key=lambda kv: -abs(kv[1]))[:cap]
        keep = dict(top)
    st = K.KernTable_format_0(apple=False)
    st.format = 0
    st.version = 0
    st.coverage = 1                      # horizontal, kerning values
    st.tupleIndex = None
    st.kernTable = {k: v for k, v in keep.items()
                    if k[0] in glyph_order and k[1] in glyph_order}
    t = newTable("kern")
    t.version = 0
    t.kernTables = [st]
    return t, len(st.kernTable)

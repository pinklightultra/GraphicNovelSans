"""Turn the labelled glyph bank into a TrueType font.

Every record names one glyph and remembers where it came from, so the pixels are
re-cut from the page rather than from a lossy intermediate. Selection is by hand
(picks.json) because transcript alignment named glyphs too unreliably to trust;
placement is by character class, so a single bad x-height estimate in one source
block cannot tilt a whole line.
"""
import json, math, os, string
import numpy as np
from PIL import Image
import glyphlab as G
import paths as P

UPM       = 1000
X_HEIGHT  = 437          # matches the hand's own x-height / cap ratio (~0.62)
ASCENDER  = 800
DESCENDER = -220
SIDE      = 0.055        # side bearing as a fraction of em
XREF      = "acemnorsuvwxz"   # neither ascender nor descender

_page_cache = {}
def page(n):
    if n not in _page_cache:
        _page_cache[n] = G.load_page(n)
    return _page_cache[n]

_crop_cache = {}
def crop_labels(pg, rect):
    """Component labels for a source block, so a record can isolate its own ink."""
    key = (pg, tuple(rect))
    if key not in _crop_cache:
        sub = page(pg).crop(tuple(rect))
        _crop_cache[key] = G.components(G.ink_mask(sub))
    return _crop_cache[key]


def cut(r):
    """Boolean ink mask for one record, with neighbouring letters removed."""
    rect = r["rect"]
    x0, y0, x1, y1 = r["box"]
    if r.get("cids"):
        lab, _ = crop_labels(r["page"], rect)
        sub = lab[y0 - rect[1]:y1 - rect[1], x0 - rect[0]:x1 - rect[0]]
        return np.isin(sub, r["cids"])
    return G.ink_mask(page(r["page"]).crop((x0, y0, x1, y1)))


def block_xheight(records):
    """Pixel x-height per source block, from its own no-ascender lowercase."""
    by = {}
    for r in records:
        if r["char"] in XREF:
            by.setdefault((r["page"], tuple(r["rect"])), []).append(r["box"][3] - r["box"][1])
    return {k: sorted(v)[len(v) // 2] for k, v in by.items() if len(v) >= 2}


def norm_bitmap(m, size=32):
    """Thumbnail that keeps the aspect ratio, so a candidate of the wrong shape
    cannot score well just because its ink pattern is vaguely similar."""
    h, w = m.shape
    tw = max(1, min(size * 2, int(round(size * w / float(h)))))
    im = Image.fromarray((m * 255).astype(np.uint8)).resize((tw, size), Image.BILINEAR)
    canvas = np.zeros((size, size * 2), dtype=np.float32)
    canvas[:, :tw] = np.asarray(im, dtype=np.float32) / 255.0
    return canvas


# What a glyph of this letter should measure, in x-heights. This is the check
# that catches a source block whose scale was estimated badly, and it catches
# welds: an "o" that comes out cap-height tall is not an "o", and a "G" twice as
# wide as it is tall is a G with the next letter still attached.
XONLY = set("acemnorsuvwxz")
DESC  = set("gpqy")
TALL  = set("bdfhklt") | set("0123456789")
WIDE  = set("mwMW")
PUNCT = set(".,'\"!?:;()$-")


def plausible(ch, mask, scale):
    h = mask.shape[0] * scale
    w = mask.shape[1] * scale
    X = X_HEIGHT
    if ch in XONLY:      lo, hi = 0.80 * X, 1.35 * X
    elif ch in DESC:     lo, hi = 1.15 * X, 2.10 * X
    elif ch == "i":      lo, hi = 0.80 * X, 1.75 * X
    elif ch == "j":      lo, hi = 1.30 * X, 2.70 * X
    elif ch in TALL:     lo, hi = 1.15 * X, 1.95 * X
    elif ch.isupper():   lo, hi = 1.15 * X, 2.00 * X
    elif ch in "!?$()":  lo, hi = 1.00 * X, 2.10 * X
    elif ch in ".,'\"": lo, hi = 0.10 * X, 0.80 * X
    elif ch == ":":      lo, hi = 0.45 * X, 1.25 * X
    elif ch == "-":      lo, hi = 0.05 * X, 0.50 * X
    else:                lo, hi = 0.10 * X, 2.30 * X
    if not (lo <= h <= hi):
        return False
    if ch in WIDE:            wlo, whi = 0.70 * X, 2.30 * X
    elif ch in PUNCT:         wlo, whi = 0.06 * X, 0.95 * X
    elif ch in "il1":         wlo, whi = 0.06 * X, 0.70 * X
    else:                     wlo, whi = 0.18 * X, 1.45 * X
    if not (wlo <= w <= whi):
        return False
    ar = w / max(h, 1e-6)
    return ar <= (2.4 if ch in WIDE or ch in PUNCT or ch == "-" else 1.6)


# Resolution floor. A five-pixel-tall scrap can be scaled to the right size but
# carries no letterform, and because it is shapeless it scores well against
# everything, so it has to be excluded before the vote rather than after.
def sharp(ch, r):
    if r["xh"] < 14 or not r.get("xh_ok"):
        return False
    need = 25 if ch in PUNCT else 60
    return r["mask"].sum() >= need and (r["box"][3] - r["box"][1]) >= 14


def pick_by_cluster(cands, thresh=0.52):
    """Choose the instance backed by the largest group of instances that agree
    with it. A plain medoid is the average of a mixed pool, so a few mislabels
    drag it toward nothing in particular; the biggest tight cluster is the shape
    the hand actually writes, and its size is a confidence number worth keeping.
    """
    if len(cands) == 1:
        cands[0]["support"] = 1
        cands[0]["agreement"] = 1.0
        return cands[0]
    bms = [norm_bitmap(c["mask"]).ravel() for c in cands]
    M = np.stack(bms)
    inter = np.minimum(M[:, None, :], M[None, :, :]).sum(-1)
    union = np.maximum(M[:, None, :], M[None, :, :]).sum(-1)
    S = np.divide(inter, union, out=np.zeros_like(inter), where=union > 0)
    np.fill_diagonal(S, 0.0)
    nb = (S >= thresh).sum(1)
    best, bi = (-1, -1.0), 0
    for i in range(len(cands)):
        m = S[i][S[i] >= thresh]
        key = (int(nb[i]), float(m.mean()) if m.size else float(S[i].max()))
        if key > best:
            best, bi = key, i
    cands[bi]["support"] = int(nb[bi]) + 1
    cands[bi]["agreement"] = round(best[1], 3)
    return cands[bi]


def medoid(cands):
    """The instance most like every other instance of the same character.
    A handful of misaligned labels cannot outvote the true majority."""
    if len(cands) == 1:
        return cands[0]
    bms = [norm_bitmap(c["mask"]) for c in cands]
    n = len(bms)
    best, bi = -1.0, 0
    for i in range(n):
        s = 0.0
        for j in range(n):
            if i == j:
                continue
            inter = np.minimum(bms[i], bms[j]).sum()
            union = np.maximum(bms[i], bms[j]).sum()
            s += inter / union if union else 0.0
        s /= (n - 1)
        if s > best:
            best, bi = s, i
    cands[bi]["agreement"] = best
    return cands[bi]


# ------------------------------------------------------------- outline fitting
def _area(p):
    s = 0.0
    for i in range(len(p)):
        x0, y0 = p[i]; x1, y1 = p[(i + 1) % len(p)]
        s += x0 * y1 - x1 * y0
    return s / 2.0


def _inside(pt, poly):
    x, y = pt
    c = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]; x1, y1 = poly[(i - 1) % n]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0 + 1e-12) + x0:
            c = not c
    return c


def _turn(a, b, c):
    """Angle in degrees between the two edges meeting at b."""
    v1 = (b[0] - a[0], b[1] - a[1])
    v2 = (c[0] - b[0], c[1] - b[1])
    n1 = math.hypot(*v1); n2 = math.hypot(*v2)
    if n1 == 0 or n2 == 0:
        return 0.0
    d = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
    return math.degrees(math.acos(d))


def draw_contour(pen, pts, corner_deg=52.0, short=26.0):
    """Emit one contour as quadratics. A sharp vertex stays on-curve; a gentle one
    becomes a control point, which is what makes the strokes read as handwriting
    rather than as a polygon. Short edges are always corners -- they are pen
    detail, not curvature, and smoothing them eats the ink."""
    n = len(pts)
    if n < 3:
        return
    on = []
    for i in range(n):
        a, b, c = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
        e1 = math.hypot(b[0] - a[0], b[1] - a[1])
        e2 = math.hypot(c[0] - b[0], c[1] - b[1])
        on.append(_turn(a, b, c) > corner_deg or min(e1, e2) > short * 4)
    if not any(on):
        pen.qCurveTo(*[tuple(p) for p in pts], None)
        pen.closePath()
        return
    s = on.index(True)
    seq = [(pts[(s + k) % n], on[(s + k) % n]) for k in range(n)]
    pen.moveTo(tuple(seq[0][0]))
    pend = []
    for p, isOn in seq[1:]:
        if isOn:
            if pend:
                pen.qCurveTo(*[tuple(q) for q in pend], tuple(p)); pend = []
            else:
                pen.lineTo(tuple(p))
        else:
            pend.append(p)
    if pend:
        pen.qCurveTo(*[tuple(q) for q in pend], tuple(seq[0][0]))
    pen.closePath()


def outline(mask, scale, base_off, eps=1.7):
    """mask: ink for one glyph. scale: font units per source pixel.
    base_off: source pixels from the glyph's top edge down to the baseline."""
    up = G.UPSCALE
    big = np.repeat(np.repeat(mask, up, axis=0), up, axis=1)
    cs = G.trace_glyph(big, eps=eps * up / 2.0)
    out = []
    for c in cs:
        pts = [((x / up) * scale, (base_off - y / up) * scale) for x, y in c]
        out.append(pts)
    if not out:
        return []
    order = sorted(range(len(out)), key=lambda i: -abs(_area(out[i])))
    depth = []
    for i in range(len(out)):
        d = sum(1 for j in range(len(out))
                if j != i and abs(_area(out[j])) > abs(_area(out[i]))
                and _inside(out[i][0], out[j]))
        depth.append(d)
    fixed = []
    for i in order:
        want_neg = (depth[i] % 2 == 0)      # outer clockwise in a y-up frame
        p = out[i]
        if (_area(p) < 0) != want_neg:
            p = p[::-1]
        fixed.append(p)
    return fixed


# Height and baseline placement per character, in x-heights. Every glyph here is
# a single accidental sample, so the source rect's estimated x-height is a shaky
# ruler -- one bad estimate and that whole rect's letters render a third too big.
# Deriving scale from what the character is instead makes the line sit flat. It
# costs the natural size jitter of real handwriting, which is a fair trade for a
# font that reads.  (height, depth below baseline)
CLASS = {
    "t": (1.32, 0.0), "i": (1.40, 0.0), "j": (1.85, 0.55),
    "Q": (1.55, 0.16),
    ".": (0.18, 0.0), ",": (0.38, 0.20), ":": (0.74, 0.0), ";": (0.92, 0.18),
    "'": (0.34, -1.06), '"': (0.34, -1.06), "-": (0.10, -0.42),
    "!": (1.45, 0.0), "?": (1.50, 0.0),
    "(": (1.80, 0.26), ")": (1.80, 0.26), "$": (1.80, 0.12),
}
for _c in "acemnorsuvwxz":
    CLASS[_c] = (1.00, 0.0)
for _c in "bdfhkl":
    CLASS[_c] = (1.55, 0.0)
for _c in "gpqy":
    CLASS[_c] = (1.74, 0.52)
for _c in string.ascii_uppercase + string.digits:
    CLASS.setdefault(_c, (1.55, 0.0))


def tighten(m):
    ys, xs = np.nonzero(m)
    if not len(ys):
        return m
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def natural_slant(drawn, band=0.22, tall=300):
    """The lean the hand already has, as dx/dy between the top and bottom of a
    glyph's ink.

    Worth measuring rather than assuming, because this hand turned out to be
    backhand: its median stem runs 7.6 degrees *left* of vertical. A textbook
    12-degree oblique therefore produced a 4-degree italic that nobody would read
    as italic. Shearing relative to what the hand actually does gets the lean the
    style name promises. Shear adds exactly its tangent to this measure, which is
    what makes the correction a subtraction rather than a guess.
    """
    import kern as K
    out = []
    for ch, cs in drawn.items():
        pts = [p for c in cs for p in K.densify(c, 8.0)]
        if not pts:
            continue
        ys = [p[1] for p in pts]
        lo, hi = min(ys), max(ys)
        if hi - lo < tall:            # a period has no stem to have an angle
            continue
        h = (hi - lo) * band
        top = [p[0] for p in pts if p[1] >= hi - h]
        bot = [p[0] for p in pts if p[1] <= lo + h]
        out.append((sum(top) / len(top) - sum(bot) / len(bot)) / (hi - lo - h))
    if not out:
        return 0.0
    out.sort()
    return out[len(out) // 2]


def _disc(r):
    return [(dy, dx) for dy in range(-r, r + 1) for dx in range(-r, r + 1)
            if dy * dy + dx * dx <= r * r + r]          # a disc, not a square


def _shift(m, dy, dx, fill):
    """Translate a mask, filling what moves in from outside. Explicit rather than
    np.roll, which wraps -- and a wrapped descender lands on the ascender."""
    out = np.full(m.shape, fill, dtype=bool)
    H, W = m.shape
    out[max(0, dy):min(H, H + dy), max(0, dx):min(W, W + dx)] = \
        m[max(0, -dy):min(H, H - dy), max(0, -dx):min(W, W - dx)]
    return out


def _grow(m, r):
    out = np.zeros_like(m)
    for dy, dx in _disc(r):
        out |= _shift(m, dy, dx, False)
    return out


def _shrink(m, r):
    out = np.ones_like(m)
    for dy, dx in _disc(r):
        out &= _shift(m, dy, dx, True)
    return out


def dilate(m, r):
    """Grow the ink by r source pixels in every direction, counters protected.

    Bold is made here, on the pixels, rather than by offsetting the finished
    outline: the hand's strokes taper and overlap, and an outline offset opens
    the joins into little notches where two strokes cross. Growing the mask keeps
    the joins closed and keeps the letter looking like the same hand holding a
    fatter pen.

    Growing alone is not enough. The counters in this hand are only a few source
    pixels across, and a plain dilation filled them: bold '8' came out a solid
    blob and 'e' closed up. So each enclosed hole is shrunk rather than flooded --
    by one pixel less than the strokes grew, and not at all if it is too small to
    survive that. A weight that closes a counter is a weight that changes what
    letter it is.
    """
    if r < 1:
        return m
    pad = np.zeros((m.shape[0] + 2 * r, m.shape[1] + 2 * r), dtype=bool)
    pad[r:r + m.shape[0], r:r + m.shape[1]] = m
    out = _grow(pad, r)
    lab, comps = G.components(~pad)
    for c in comps:
        if c["x0"] == 0 or c["y0"] == 0 or \
           c["x1"] == pad.shape[1] or c["y1"] == pad.shape[0]:
            continue                       # that is the page, not a counter
        hole = lab == c["id"]
        for k in range(r - 1, -1, -1):     # k=0 leaves the hole untouched
            keep = _shrink(hole, k)
            if keep.any():
                out &= ~keep
                break
    return out


def place(ch, mask):
    """(scale, base_off) putting this glyph at its class height and baseline."""
    h, depth = CLASS.get(ch, (1.30, 0.0))
    px = max(mask.shape[0], 1)
    scale = (X_HEIGHT * h) / float(px)
    return scale, px * (h - depth) / h


# ------------------------------------------------------------------ glyph names
NAMES = {
    " ": "space", ".": "period", ",": "comma", "'": "quotesingle", '"': "quotedbl",
    "!": "exclam", "?": "question", ":": "colon", ";": "semicolon",
    "(": "parenleft", ")": "parenright", "$": "dollar", "-": "hyphen",
}
DIG = "zero one two three four five six seven eight nine".split()


def gname(ch):
    if ch in NAMES:
        return NAMES[ch]
    if ch.isdigit():
        return DIG[int(ch)]
    if ch.isupper():
        return ch
    return ch


_rect_cache = {}


def rect_geom(pg, rect):
    """Re-segment a source rect and return (x_height, [line dicts]).

    Transcript alignment named these components unreliably, but the segmentation
    itself is sound, so a hand-picked component is identified by its rect and
    index and re-measured here. The median letterlike height is the x-height:
    most letters in running text sit on the x-height band, and every x-only
    pick measured 1.0-1.3 of this value.
    """
    key = (pg, tuple(rect))
    if key in _rect_cache:
        return _rect_cache[key]
    sub = G.load_page(pg).crop(tuple(rect))
    lab, comps = G.components(G.ink_mask(sub))
    comps = [c for c in comps if c["pixels"] >= 12]
    comps = G.letterlike(G.drop_rules(comps, tuple(rect), 0.60, 0.60))
    hs = sorted(c["y1"] - c["y0"] for c in comps)
    xh = hs[len(hs) // 2] if hs else 20
    out = (max(6, xh), G.group_lines(comps))
    _rect_cache[key] = out
    return out


def cids_for(pg, rect, box):
    """Component ids inside a picked box.

    Without these, cutting a glyph means thresholding its whole bounding box,
    which drags in whatever the neighbouring letter pokes into that rectangle --
    an R comes out as "Ro". Older manifests predate the ids, so they are
    recovered here by matching the box back to the segmentation.
    """
    lab, comps = crop_labels(pg, rect)
    x0, y0, x1, y1 = (box[0] - rect[0], box[1] - rect[1],
                      box[2] - rect[0], box[3] - rect[1])
    exact = [c["id"] for c in comps
             if (c["x0"], c["y0"], c["x1"], c["y1"]) == (x0, y0, x1, y1)]
    if exact:
        return exact
    # no exact match (a clipped pick): take components mostly inside the box
    out = []
    for c in comps:
        w = min(c["x1"], x1) - max(c["x0"], x0)
        h = min(c["y1"], y1) - max(c["y0"], y0)
        if w > 0 and h > 0 and w * h >= 0.55 * (c["x1"] - c["x0"]) * (c["y1"] - c["y0"]):
            out.append(c["id"])
    return out


def pick_base(pg, rect, box):
    """Baseline for a hand-picked box: the baseline of the line it sits on."""
    xh, lines = rect_geom(pg, rect)
    cy = (box[1] + box[3]) / 2.0 - rect[1]
    best, bd = None, 1e9
    for ln in lines:
        d = abs(ln["base"] - cy)
        if d < bd:
            best, bd = ln, d
    return rect[1] + (best["base"] if best else box[3] - rect[1])


def resolve_picks():
    """Hand-read glyph choices, keyed by character.

    Two address forms. `cand` points into a per-character candidate grid
    (sheet, row character, column). `man` points at a contact-sheet manifest
    index. `merge` unions several manifest components into one glyph, for
    letters the hand drew as separate strokes.
    """
    path = P.data("picks.json")
    if not os.path.exists(path):
        return {}
    spec = P.load(path)
    out = {}
    for ch, (sheet, row, col) in spec.get("cand", {}).items():
        cands = P.load(P.data(f"cand_{sheet}.json"))
        r = dict(cands[row][col])
        r["char"] = ch
        out[ch] = r
    for ch, (sheet, idx) in spec.get("man", {}).items():
        m = P.load(P.data(f"man{sheet}.json"))[str(idx)]
        out[ch] = dict(char=ch, page=m["page"], rect=m["rect"],
                       box=m["box"], pixels=m["pixels"],
                       cids=m.get("cids") or cids_for(m["page"], m["rect"], m["box"]))
    for ch, (sheet, idxs) in spec.get("merge", {}).items():
        m = P.load(P.data(f"man{sheet}.json"))
        ps = [m[str(i)] for i in idxs]
        bs = [p["box"] for p in ps]
        out[ch] = dict(char=ch, page=ps[0]["page"], rect=ps[0]["rect"],
                       box=[min(b[0] for b in bs), min(b[1] for b in bs),
                            max(b[2] for b in bs), max(b[3] for b in bs)],
                       pixels=sum(p["pixels"] for p in ps),
                       cids=[i for p in ps for i in
                             (p.get("cids") or cids_for(p["page"], p["rect"], p["box"]))])
    for ch, (sheet, idx, frac) in spec.get("clip", {}).items():
        m = P.load(P.data(f"man{sheet}.json"))[str(idx)]
        b = list(m["box"])
        w = b[2] - b[0]
        out[ch] = dict(char=ch, page=m["page"], rect=m["rect"], pixels=m["pixels"],
                       cids=m.get("cids"),
                       box=[int(b[0] + frac[0] * w), b[1], int(b[0] + frac[1] * w), b[3]])
    for ch, r in out.items():
        # Candidate-grid records predate the ids too, and without them `cut` falls
        # back to thresholding the whole box, which picks up a neighbour's speck.
        if not r.get("cids"):
            r["cids"] = cids_for(r["page"], r["rect"], r["box"])
        r["xh"] = rect_geom(r["page"], r["rect"])[0]
        r["xh_ok"] = True
        r["hand"] = True
        r["pick"] = True
        r.setdefault("base", None)
        if r["base"] is None:
            r["base"] = pick_base(r["page"], r["rect"], r["box"])
        r["mask"] = tighten(cut(r))
    # Synthesis runs last so it can borrow a mask that is already resolved.
    for ch, op in spec.get("synth", {}).items():
        kind, srcs = op[0], op[1:]
        if any(s not in out for s in srcs):
            continue
        if kind == "mirror":
            m = out[srcs[0]]["mask"][:, ::-1].copy()
        elif kind == "copy":
            m = out[srcs[0]]["mask"].copy()
        elif kind == "dotted":
            # The hand left this j undotted, and an undotted j reads as a comma.
            # The dot goes over whichever stroke reaches highest, which is the stem.
            base, dot = (out[s]["mask"] for s in srcs)
            top = np.nonzero(base[0])[0]
            cx = int(top.mean()) if len(top) else base.shape[1] // 2
            gap = max(2, int(0.35 * dot.shape[0]))
            m = np.zeros((dot.shape[0] + gap + base.shape[0],
                          max(base.shape[1], cx + dot.shape[1])), dtype=bool)
            x = min(max(0, cx - dot.shape[1] // 2), m.shape[1] - dot.shape[1])
            m[:dot.shape[0], x:x + dot.shape[1]] = dot
            m[dot.shape[0] + gap:, :base.shape[1]] = base
        elif kind == "pair":
            # A double quote is the same stroke twice. Merging two neighbouring
            # strokes off the page instead gave a shape that read as a 'y', because
            # the hand set them at different heights.
            one = out[srcs[0]]["mask"]
            gap = max(2, int(0.55 * one.shape[1]))
            m = np.zeros((one.shape[0], one.shape[1] * 2 + gap), dtype=bool)
            m[:, :one.shape[1]] = one
            m[:, one.shape[1] + gap:] = one
        elif kind == "stack":
            top, bot = (out[s]["mask"] for s in srcs)
            w = max(top.shape[1], bot.shape[1])
            gap = max(2, int(0.9 * top.shape[0]))
            m = np.zeros((top.shape[0] + gap + bot.shape[0], w), dtype=bool)
            m[:top.shape[0], (w - top.shape[1]) // 2:][:, :top.shape[1]] = top
            m[top.shape[0] + gap:, (w - bot.shape[1]) // 2:][:, :bot.shape[1]] = bot
        else:
            continue
        src = out[srcs[0]]
        out[ch] = dict(char=ch, page=src["page"], rect=src["rect"], box=src["box"],
                       pixels=int(m.sum()), xh=src["xh"], xh_ok=True, hand=True,
                       pick=True, synth=kind, base=src["base"], mask=m)
    return out


def gather():
    recs = P.load(P.data("bank_auto.json"))
    xh = block_xheight(recs)
    # blocks with too little lowercase still get a usable scale from their own
    # letter heights -- coarser, but better than dropping the block
    solid = set(xh)
    for r in recs:
        k = (r["page"], tuple(r["rect"]))
        if k not in xh:
            hs = sorted(q["box"][3] - q["box"][1] for q in recs
                        if (q["page"], tuple(q["rect"])) == k)
            xh[k] = max(6, int(0.72 * hs[len(hs) // 2]))
    by = {}
    for r in recs:
        w = r["box"][2] - r["box"][0]; h = r["box"][3] - r["box"][1]
        if w < 3 or h < 3 or w > 400 or h > 400:
            continue
        m = cut(r)
        if m.sum() < 12:
            continue
        r["mask"] = m
        r["xh"] = xh[(r["page"], tuple(r["rect"]))]
        r["xh_ok"] = (r["page"], tuple(r["rect"])) in solid
        by.setdefault(r["char"], []).append(r)
    return by


# The four RIBBI styles. `weight` is how many font units of extra ink the strokes
# get; it is converted to source pixels per glyph, because one glyph's source is a
# 15-pixel 'n' and another's is a 108-pixel display capital, and a fixed pixel
# radius would make the second look barely touched. `slant` is a true oblique --
# the hand never wrote a cursive italic, so inventing one would be inventing
# letterforms it never made.
STYLES = {
    "Regular":     dict(weight=0,  lean=0.0),
    "Bold":        dict(weight=34, lean=0.0),
    "Italic":      dict(weight=0,  lean=11.0),
    "Bold Italic": dict(weight=34, lean=11.0),
}
FS = {"Regular": 0x40, "Bold": 0x20, "Italic": 0x01, "Bold Italic": 0x21}
MAC = {"Regular": 0, "Bold": 1, "Italic": 2, "Bold Italic": 3}
# The band range where letters actually touch each other in running text, and so
# the only part of a glyph's silhouette that should decide its sidebearings.
ZONE = (0, X_HEIGHT)


def build(style="Regular", out_path=None):
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    from fontTools.feaLib.builder import addOpenTypeFeatures
    import kern as K

    spec = STYLES[style]
    weight, lean = spec["weight"], spec["lean"]
    slug = style.replace(" ", "")
    if out_path is None:
        out_path = "BLUE175.ttf" if style == "Regular" else f"BLUE175-{slug}.ttf"

    by = gather()
    picked = resolve_picks()
    chosen, glyphs, metrics, notes = {}, {}, {}, []

    for ch, cands in sorted(by.items()):
        if ch in picked:
            continue        # a hand-read pick outranks anything the vote finds
        for c in cands:
            c["scale"] = X_HEIGHT / float(c["xh"])
        fit = [c for c in cands
               if plausible(ch, c["mask"], c["scale"]) and sharp(ch, c)]
        if not fit:      # rare characters get a relaxed pass rather than a gap
            fit = [c for c in cands if plausible(ch, c["mask"], c["scale"])]
        # prefer confidently aligned instances, but never lose a rare character
        good = [c for c in fit if c.get("hand") or c.get("cost", 99) <= 32]
        pool = good or fit or cands
        pick = pick_by_cluster(pool)
        pick["pool"] = len(pool)
        pick["seen"] = len(cands)
        chosen[ch] = pick

    for ch, r in picked.items():
        r["pool"] = r["seen"] = 1
        chosen[ch] = r

    # Glyph 0 is .notdef by definition, and a character mapped to glyph 0 is
    # dropped when the cmap compiles -- leaving space first cost the space glyph
    # its mapping, so text only looked spaced because .notdef has an advance.
    order = [".notdef", "space"] + [gname(c) for c in sorted(chosen)]

    # First pass: trace. The outlines have to exist before they can be spaced,
    # because each glyph's sidebearings are read off its own edge profile.
    drawn = {}
    for ch, r in sorted(chosen.items()):
        m = tighten(r["mask"])
        scale, base_off = place(ch, m)
        # the same apparent stroke gain everywhere, in each glyph's own pixels
        px = max(1, int(round(weight / scale))) if weight else 0
        if px:
            m = dilate(m, px)
            base_off += px          # the padded frame's top edge moved up by px
        drawn[ch] = (outline(m, scale, base_off), r, px)

    # Shear, once the whole alphabet exists to be measured against.
    natural = natural_slant({c: v[0] for c, v in drawn.items()})
    shear = math.tan(math.radians(lean)) - natural if lean else 0.0
    if shear:
        drawn = {ch: ([[(x + y * shear, y) for x, y in c] for c in cs], r, px)
                 for ch, (cs, r, px) in drawn.items()}

    # Second pass: space each glyph on its own flanks, then fit it to them.
    final, profiles = {}, {}
    for ch, (cs, r, px) in sorted(drawn.items()):
        raw = K.profile(cs, 0, DESCENDER, ASCENDER)
        lsb, rsb = K.flanks(raw["bands"], 0, DESCENDER, ASCENDER, ZONE)
        xs = [p[0] for c in cs for p in c] or [0.0]
        x0, x1 = min(xs), max(xs)
        adv = int(round(lsb + (x1 - x0) + rsb))
        cs = [[(x + lsb - x0, y) for x, y in c] for c in cs]
        name = gname(ch)
        pen = TTGlyphPen(None)
        for c in cs:
            draw_contour(pen, c)
        final[name] = pen.glyph()
        metrics[name] = (adv, int(round(lsb)))
        profiles[name] = K.profile(cs, adv, DESCENDER, ASCENDER)
        # Every glyph is one hand-read sample, so a vote count would say nothing.
        # What is worth reporting is where the ink came from and how it was made.
        kind = r.get("synth") or ("merge" if len(r.get("cids") or []) > 1 else "cut")
        notes.append((ch, kind, r["page"], tuple(r["box"]), len(cs), adv, px))

    final[".notdef"] = TTGlyphPen(None).glyph()
    metrics[".notdef"] = (int(0.30 * UPM), 0)
    final["space"] = TTGlyphPen(None).glyph()
    metrics["space"] = (int(0.30 * UPM), 0)

    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder([n for n in order if n in final])
    fb.setupCharacterMap({ord(" "): "space",
                          **{ord(c): gname(c) for c in chosen}})
    fb.setupGlyf(final)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=ASCENDER, descent=DESCENDER, lineGap=0)
    fb.setupNameTable({
        "familyName": "BLUE175 Hand", "styleName": style,
        "uniqueFontIdentifier": f"BLUE175Hand-{slug}-1.1",
        "fullName": f"BLUE175 Hand {style}", "psName": f"BLUE175Hand-{slug}",
        "version": "Version 1.1",
        "designer": "Justin Severn (lettering); traced from BLUE175",
    })
    fb.setupOS2(sTypoAscender=ASCENDER, sTypoDescender=DESCENDER,
                usWinAscent=ASCENDER, usWinDescent=-DESCENDER,
                sxHeight=X_HEIGHT, sCapHeight=700, achVendID="B175",
                usWeightClass=700 if weight else 400,
                fsSelection=FS[style])
    fb.setupPost(italicAngle=-lean)
    fb.font["head"].macStyle = MAC[style]

    # Kerning twice over: GPOS for anything from this century, and a format-0
    # `kern` table because plenty of software still reads only that one.
    kerns = K.pairs(profiles)
    fea = K.write_fea(kerns, P.out(f"kern-{slug}.fea"))
    addOpenTypeFeatures(fb.font, fea)
    legacy, npairs = K.legacy_table(kerns, set(final))
    fb.font["kern"] = legacy

    fb.save(P.out(out_path))
    return notes, out_path, len(kerns), npairs, natural, shear


def webfont(path):
    """The same font as WOFF2, for the web. Needs brotli."""
    from fontTools.ttLib import TTFont
    f = TTFont(path)
    f.flavor = "woff2"
    dst = os.path.splitext(path)[0] + ".woff2"
    f.save(dst)
    return dst


if __name__ == "__main__":
    import sys
    styles = sys.argv[1:] or list(STYLES)
    for i, st in enumerate(styles):
        n, path, nk, nlegacy, nat, shear = build(st)
        webfont(P.out(path))
        if i == 0:
            print(f"{len(n)} glyphs")
            synth = sum(1 for r in n if r[1] not in ("cut", "merge"))
            for ch, kind, pg, box, nc, adv, px in n:
                print(f"  {ch!r:5} {kind:<7} p{pg:<3} box={box} "
                      f"contours={nc:<2} adv={adv}")
            print(f"{len(n) - synth} traced from the page, {synth} synthesised "
                  f"from another glyph because no clean instance exists in the "
                  f"source")
        px = sum(r[6] for r in n) / float(len(n))
        print(f"{path:26} {len(n)} glyphs, {nk} kern pairs "
              f"({nlegacy} in kern), mean dilation {px:.1f}px, "
              f"hand leans {math.degrees(math.atan(nat)):+.1f}deg, "
              f"sheared {math.degrees(math.atan(shear)):+.1f}deg")

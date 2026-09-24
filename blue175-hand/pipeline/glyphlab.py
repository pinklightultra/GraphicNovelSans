"""BLUE175 handwriting -> font pipeline.

Ink is light blue on white. The red channel separates it cleanly (ink ~147, paper 255).
"""
import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import paths

INK_MAX_RED = 225          # red channel below this = ink
UPSCALE = 4                # supersample before tracing


def load_page(n):
    path = os.path.join(paths.PAGES, f"p{n:02d}.webp")
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path}: the source pages are not in this repo; set "
                                "BLUE175_PAGES to the folder holding p01.webp .. p15.webp")
    return Image.open(path).convert("RGB")


def ink_strength(img):
    """0..1 float array, 1 = full ink."""
    a = np.asarray(img, dtype=np.float32)
    red = a[:, :, 0]
    s = (255.0 - red) / (255.0 - 150.0)
    return np.clip(s, 0.0, 1.0)


def ink_mask(img, thresh=None):
    a = np.asarray(img, dtype=np.int16)
    t = INK_MAX_RED if thresh is None else thresh
    return a[:, :, 0] < t


def label_font(px):
    try:
        return ImageFont.truetype("arialbd.ttf", px)
    except OSError:
        return ImageFont.load_default()


# ---------------------------------------------------------------- grid overlay
def grid_overlay(n, out, step=100, scale=1.0):
    img = load_page(n).convert("RGB")
    W, H = img.size
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype("arialbd.ttf", 22)
    except Exception:
        f = ImageFont.load_default()
    for x in range(0, W, step):
        d.line([(x, 0), (x, H)], fill=(255, 0, 0) if x % 500 == 0 else (255, 170, 170), width=1)
    for y in range(0, H, step):
        d.line([(0, y), (W, y)], fill=(0, 140, 0) if y % 500 == 0 else (170, 220, 170), width=1)
    for x in range(0, W, step):
        for y in range(0, H, 500):
            d.text((x + 2, y + 2), str(x), fill=(200, 0, 0), font=f)
    for y in range(0, H, step):
        d.text((3, y + 2), str(y), fill=(0, 110, 0), font=f)
    if scale != 1.0:
        img = img.resize((int(W * scale), int(H * scale)), Image.LANCZOS)
    img.save(paths.out(out))
    return img.size


# ------------------------------------------------------- connected components
def components(mask):
    """4-connected labelling, iterative. Returns label array and list of dicts."""
    H, W = mask.shape
    lab = np.zeros((H, W), dtype=np.int32)
    comps = []
    cur = 0
    ys, xs = np.nonzero(mask)
    stack = []
    for sy, sx in zip(ys, xs):
        if lab[sy, sx]:
            continue
        cur += 1
        lab[sy, sx] = cur
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
                if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and not lab[ny, nx]:
                    lab[ny, nx] = cur
                    stack.append((ny, nx))
        comps.append(dict(id=cur, x0=int(minx), y0=int(miny), x1=int(maxx) + 1,
                          y1=int(maxy) + 1, pixels=npix))
    return lab, comps


def group_lines(comps, gap=None):
    """Cluster components into text lines by clustering bottom edges.

    Interval-overlap merging fails on handwriting: a descender from one row and an
    ascender from the next interlock, welding the two rows together. Bottom edges
    cluster far more cleanly, so the line bases come from the typical-height
    components only, then every component (dots, descenders) is assigned to the
    nearest base band.
    """
    if not comps:
        return []
    hs = sorted(c["y1"] - c["y0"] for c in comps)
    h = hs[len(hs) // 2] or 1
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

    lines = [dict(base=b, items=[]) for b in base_y]
    for c in comps:
        cy = (c["y0"] + c["y1"]) / 2
        best = min(range(len(base_y)), key=lambda k: abs(cy - (base_y[k] - 0.35 * h)))
        lines[best]["items"].append(c)
    lines = [ln for ln in lines if ln["items"]]
    for ln in lines:
        ln["items"].sort(key=lambda c: c["x0"])
        ln["y0"] = min(c["y0"] for c in ln["items"])
        ln["y1"] = max(c["y1"] for c in ln["items"])
    lines.sort(key=lambda l: l["base"])
    return lines


# --------------------------------------------------------------- contact sheet
def drop_rules(comps, rect, max_w_frac=0.55, max_h_frac=0.42):
    """Panel borders and speech-balloon outlines come back as one huge component
    that would otherwise weld every text line together."""
    W = rect[2] - rect[0]
    H = rect[3] - rect[1]
    return [c for c in comps
            if (c["x1"] - c["x0"]) < max_w_frac * W and (c["y1"] - c["y0"]) < max_h_frac * H]


def contact_sheet(page, rect, out, min_pixels=12, cell=110, cols=14, gap_line=6,
                  max_w_frac=0.55, max_h_frac=0.42):
    """Segment a rectangle into components, render a numbered contact sheet.

    Returns the manifest: [(index, page, comp bbox in page coords, line#)]
    """
    img = load_page(page)
    x0, y0, x1, y1 = rect
    sub = img.crop(rect)
    mask = ink_mask(sub)
    lab, comps = components(mask)
    comps = [c for c in comps if c["pixels"] >= min_pixels]
    comps = drop_rules(comps, rect, max_w_frac, max_h_frac)
    lines = group_lines(comps, gap=gap_line)

    manifest = []
    idx = 0
    rows = []
    for li, ln in enumerate(lines):
        row = []
        for c in ln["items"]:
            idx += 1
            manifest.append(dict(i=idx, page=page, line=li,
                                 box=(x0 + c["x0"], y0 + c["y0"], x0 + c["x1"], y0 + c["y1"]),
                                 rect=rect, cid=c["id"], pixels=c["pixels"]))
            row.append((idx, c))
        rows.append(row)

    # layout: one visual row per text line, wrapped at `cols`
    laid = []
    for row in rows:
        for k in range(0, len(row), cols):
            laid.append(row[k:k + cols])
    Wsheet = cell * cols + 20
    Hsheet = cell * len(laid) + 20
    sheet = Image.new("RGB", (Wsheet, Hsheet), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype("arialbd.ttf", 18)
    except Exception:
        f = ImageFont.load_default()
    subarr = np.asarray(sub)
    for r, row in enumerate(laid):
        for cix, (i, c) in enumerate(row):
            glyph = Image.fromarray(
                np.where(lab[c["y0"]:c["y1"], c["x0"]:c["x1"]] == c["id"], 0, 255).astype(np.uint8)
            ).convert("RGB")
            gw, gh = glyph.size
            sc = min((cell - 34) / max(gw, 1), (cell - 34) / max(gh, 1), 3.0)
            glyph = glyph.resize((max(1, int(gw * sc)), max(1, int(gh * sc))), Image.LANCZOS)
            px = 10 + cix * cell
            py = 10 + r * cell
            d.rectangle([px, py, px + cell - 6, py + cell - 6], outline=(220, 220, 220))
            sheet.paste(glyph, (px + (cell - 6 - glyph.width) // 2,
                                py + 22 + (cell - 34 - glyph.height) // 2))
            d.text((px + 4, py + 2), str(i), fill=(200, 0, 0), font=f)
    sheet.save(paths.out(out))
    return manifest, (Wsheet, Hsheet)


# ------------------------------------------------------------------- tracing
def _moore_trace(bin_img):
    """Return list of contours (lists of (x,y) pixel-corner points) for a binary
    array, using marching-squares on the pixel grid. Outer + hole contours."""
    H, W = bin_img.shape
    g = np.zeros((H + 2, W + 2), dtype=bool)
    g[1:-1, 1:-1] = bin_img
    # marching squares over corner lattice
    # state at (y,x) from the 2x2 cell (y-1,x-1),(y-1,x),(y,x-1),(y,x)
    segs = {}
    for y in range(g.shape[0] - 1):
        row_tl = g[y, :-1]; row_tr = g[y, 1:]
        row_bl = g[y + 1, :-1]; row_br = g[y + 1, 1:]
        code = (row_tl.astype(np.uint8) << 3) | (row_tr.astype(np.uint8) << 2) \
             | (row_br.astype(np.uint8) << 1) | row_bl.astype(np.uint8)
        for x in np.nonzero((code != 0) & (code != 15))[0]:
            c = int(code[x])
            # edge midpoints of the cell whose top-left lattice point is (x,y)
            T = (x + 0.5, y + 0.0)
            B = (x + 0.5, y + 1.0)
            L = (x + 0.0, y + 0.5)
            R = (x + 1.0, y + 0.5)
            # directed segments so that ink is on the left  (y down)
            table = {
                1:  [(L, B)], 2:  [(B, R)], 3:  [(L, R)], 4:  [(R, T)],
                5:  [(L, T), (R, B)], 6:  [(B, T)], 7:  [(L, T)],
                8:  [(T, L)], 9:  [(T, B)], 10: [(T, R), (B, L)],
                11: [(T, R)], 12: [(R, L)], 13: [(R, B)], 14: [(B, L)],
            }
            for a, b in table[c]:
                segs.setdefault(a, []).append(b)

    contours = []
    used = set()
    for start in list(segs.keys()):
        for k in range(len(segs[start])):
            if (start, k) in used:
                continue
            pt = start
            ki = k
            path = []
            guard = 0
            while True:
                guard += 1
                if guard > 400000:
                    break
                used.add((pt, ki))
                path.append(pt)
                nxts = segs.get(pt)
                if not nxts:
                    break
                nxt = nxts[ki] if ki < len(nxts) else nxts[0]
                pt = nxt
                nxts2 = segs.get(pt)
                if not nxts2:
                    break
                ki = 0
                if len(nxts2) > 1:
                    for j in range(len(nxts2)):
                        if (pt, j) not in used:
                            ki = j
                            break
                if (pt, ki) in used:
                    break
            if len(path) >= 6:
                contours.append(path)
    return contours


def _rdp(pts, eps):
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        ax, ay = pts[a]; bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        n = math.hypot(dx, dy)
        best = -1.0; bi = -1
        for i in range(a + 1, b):
            px, py = pts[i]
            if n == 0:
                dist = math.hypot(px - ax, py - ay)
            else:
                dist = abs(dy * (px - ax) - dx * (py - ay)) / n
            if dist > best:
                best = dist; bi = i
        if best > eps:
            keep[bi] = True
            stack.append((a, bi)); stack.append((bi, b))
    return [p for p, k in zip(pts, keep) if k]


def _signed_area(pts):
    s = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        s += x0 * y1 - x1 * y0
    return s / 2.0


def trace_glyph(mask_crop, eps=1.6):
    """mask_crop: bool array (True = ink), already supersampled.
    Returns list of contours as lists of (x, y) in crop pixel coords (y down)."""
    raw = _moore_trace(mask_crop)
    out = []
    for c in raw:
        c = _rdp(c, eps)
        # drop the duplicated closing point if present
        if len(c) > 2 and c[0] == c[-1]:
            c = c[:-1]
        if len(c) >= 3 and abs(_signed_area(c)) > 3.0:
            out.append(c)
    return out


# ------------------------------------------------------------- line discovery
def find_lines(page, min_h=14, max_h=95, min_pixels=25, xgap_mult=2.2):
    """Whole-page pass: components in letter-size range, clustered into lines,
    each line split into runs at wide horizontal gaps."""
    img = load_page(page)
    mask = ink_mask(img)
    lab, comps = components(mask)
    keep = [c for c in comps
            if c["pixels"] >= min_pixels
            and min_h <= (c["y1"] - c["y0"]) <= max_h
            and (c["x1"] - c["x0"]) <= 260]
    lines = group_lines(keep)
    runs = []
    for ln in lines:
        hs = sorted(c["y1"] - c["y0"] for c in ln["items"])
        h = hs[len(hs) // 2] or 1
        cur = []
        for c in ln["items"]:
            if cur and c["x0"] - cur[-1]["x1"] > xgap_mult * h:
                runs.append((cur, h, ln["base"]))
                cur = []
            cur.append(c)
        if cur:
            runs.append((cur, h, ln["base"]))
    out = []
    for items, h, base in runs:
        if len(items) < 3:
            continue
        out.append(dict(
            box=(min(c["x0"] for c in items) - 3, min(c["y0"] for c in items) - 3,
                 max(c["x1"] for c in items) + 3, max(c["y1"] for c in items) + 3),
            n=len(items), h=int(h), base=int(base)))
    out.sort(key=lambda r: (r["box"][1], r["box"][0]))
    return out


def line_map(page, out, min_h=22, scale=0.72):
    """Overlay numbered boxes on the page so lines can be chosen by index."""
    runs = [r for r in find_lines(page) if r["h"] >= min_h]
    img = load_page(page).convert("RGB")
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype("arialbd.ttf", 26)
    except Exception:
        f = ImageFont.load_default()
    for i, r in enumerate(runs, 1):
        d.rectangle(r["box"], outline=(220, 0, 0), width=2)
        d.text((r["box"][0] + 2, r["box"][1] - 26), str(i), fill=(200, 0, 130), font=f)
    W, H = img.size
    img.resize((int(W * scale), int(H * scale)), Image.LANCZOS).save(paths.out(out))
    return runs


def letterlike(comps, keep_dots=True):
    """Reject hatching and art strokes. Hatch marks are long thin diagonals: low
    bbox fill and a tiny minor axis. Letters fill a useful fraction of their box."""
    out = []
    if not comps:
        return out
    # Height reference weighted by ink: a rect that clips a hatched drawing is
    # mostly tiny marks by count, so an unweighted median collapses and then
    # rejects the real lettering as "too tall".
    order = sorted(comps, key=lambda c: c["y1"] - c["y0"])
    total = sum(c["pixels"] for c in order)
    acc, hmed = 0, order[-1]["y1"] - order[-1]["y0"]
    for c in order:
        acc += c["pixels"]
        if acc >= total * 0.5:
            hmed = (c["y1"] - c["y0"]) or 1
            break
    for c in comps:
        w = c["x1"] - c["x0"]
        h = c["y1"] - c["y0"]
        fill = c["pixels"] / float(w * h)
        if keep_dots and w <= 0.45 * hmed and h <= 0.45 * hmed and fill > 0.45:
            out.append(c)          # period, i-dot, comma
            continue
        if min(w, h) < 6:
            continue
        if fill < 0.26:
            continue
        if h < 0.35 * hmed or h > 2.2 * hmed:
            continue
        if w > 3.2 * hmed:
            continue
        out.append(c)
    return out


def run_score(page, run, img=None):
    """Prefer long, large, height-consistent runs -- i.e. real caption lettering."""
    return run["n"] * run["h"]


# ------------------------------------------------------------- harvest sheets
def harvest_sheet(targets, out, manifest_path, min_pixels=25, cell=104, cols=16):
    """targets: list of (page, rect). Dense flow layout, numbered, plus a JSON
    manifest keyed by the printed index (page, source rect, component box)."""
    import json
    flow = []
    manifest = {}
    idx = 0
    cache = {}
    for page, rect in targets:
        if page not in cache:
            cache[page] = load_page(page)
        sub = cache[page].crop(rect)
        lab, comps = components(ink_mask(sub))
        comps = [c for c in comps if c["pixels"] >= min_pixels]
        comps = drop_rules(comps, rect, 0.60, 0.60)
        comps = letterlike(comps)
        for ln in group_lines(comps):
            for c in ln["items"]:
                idx += 1
                manifest[str(idx)] = dict(
                    page=page, rect=list(rect),
                    box=[rect[0] + c["x0"], rect[1] + c["y0"],
                         rect[0] + c["x1"], rect[1] + c["y1"]],
                    pixels=c["pixels"])
                flow.append((idx, np.where(lab[c["y0"]:c["y1"], c["x0"]:c["x1"]] == c["id"],
                                           0, 255).astype(np.uint8)))
    nrows = (len(flow) + cols - 1) // cols
    sheet = Image.new("RGB", (cell * cols + 20, cell * max(nrows, 1) + 20), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype("arialbd.ttf", 17)
    except Exception:
        f = ImageFont.load_default()
    for k, (i, arr) in enumerate(flow):
        r, cix = divmod(k, cols)
        g = Image.fromarray(arr).convert("RGB")
        sc = min((cell - 32) / max(g.width, 1), (cell - 32) / max(g.height, 1), 3.0)
        g = g.resize((max(1, int(g.width * sc)), max(1, int(g.height * sc))), Image.LANCZOS)
        px, py = 10 + cix * cell, 10 + r * cell
        d.rectangle([px, py, px + cell - 6, py + cell - 6], outline=(225, 225, 225))
        sheet.paste(g, (px + (cell - 6 - g.width) // 2, py + 20 + (cell - 32 - g.height) // 2))
        d.text((px + 3, py + 1), str(i), fill=(200, 0, 0), font=f)
    sheet.save(paths.out(out))
    with open(paths.out(manifest_path), "w") as fh:
        json.dump(manifest, fh)
    return manifest, sheet.size


def targets_for(page, min_h, budget=170, min_n=4):
    runs = [r for r in find_lines(page) if r["h"] >= min_h and r["n"] >= min_n]
    runs.sort(key=lambda r: (r["box"][1], r["box"][0]))
    out, tot = [], 0
    for r in runs:
        if tot + r["n"] > budget:
            continue
        out.append((page, tuple(r["box"])))
        tot += r["n"]
    return out


def best_targets(pages, min_h=26, budget=190, per_page=None):
    picked = []
    for page in pages:
        runs = [r for r in find_lines(page) if r["h"] >= min_h and r["n"] >= 5]
        runs.sort(key=lambda r: -run_score(page, r))
        if per_page:
            runs = runs[:per_page]
        for r in runs:
            picked.append((page, tuple(r["box"]), r["n"] * r["h"]))
    picked.sort(key=lambda t: -t[2])
    out, tot = [], 0
    for page, box, sc in picked:
        n = max(1, sc // 30)
        if tot + n > budget:
            continue
        out.append((page, box))
        tot += n
    return out


# ----------------------------------------------------------------- auto-label
# The contact-sheet route needs a human to name every glyph. But the transcript
# already says what each line reads, so alignment can name them: order the
# components left to right and match them against the expected string, allowing
# a component to cover several welded letters and a letter to be split across
# two components (i, j, ?, !, ").
def _xoverlap(a, b):
    lo = max(a["x0"], b["x0"]); hi = min(a["x1"], b["x1"])
    return max(0, hi - lo) / float(min(a["x1"] - a["x0"], b["x1"] - b["x0"]) or 1)


def align_line(items, expected, weld_pen=14.0, aw=None):
    """items: components sorted by x. expected: string with spaces stripped.
    Returns list of (char, [component indices]) for confident pairs only."""
    n, m = len(items), len(expected)
    if not n or not m:
        return []
    if aw is None:
        aw = (items[-1]["x1"] - items[0]["x0"]) / float(m)
    # Drift is the real enemy: an alignment can stay monotonic yet sit several
    # letters out of step. Components and letters both run left to right at a
    # roughly even rate, so tie the two index fractions together.
    pos_w = 6.0 * aw
    areas = sorted(it["pixels"] for it in items)
    amed = areas[len(areas) // 2] or 1
    small = [it["pixels"] < 0.40 * amed for it in items]
    INF = float("inf")
    D = [[INF] * (m + 1) for _ in range(n + 1)]
    P = [[None] * (m + 1) for _ in range(n + 1)]
    D[0][0] = 0.0
    for i in range(n + 1):
        for j in range(m + 1):
            if D[i][j] == INF:
                continue
            base = D[i][j]
            # one component covers k letters
            for k in (1, 2, 3, 4):
                if i < n and j + k <= m:
                    w = items[i]["x1"] - items[i]["x0"]
                    c = (base + abs(w - k * aw) + weld_pen * (k - 1) ** 2
                         + pos_w * abs((i + 1) / n - (j + k) / m))
                    if c < D[i + 1][j + k]:
                        D[i + 1][j + k] = c; P[i + 1][j + k] = (i, j, 1, k)
            # a stray art mark: consume a component without naming it. Only a
            # small mark may be skipped -- letting the DP discard letter-sized
            # ink is what lets it "name" every character by drifting.
            if i < n:
                c = (base + (30.0 if small[i] else 150.0)
                     + pos_w * abs((i + 1) / n - j / m))
                if c < D[i + 1][j]:
                    D[i + 1][j] = c; P[i + 1][j] = (i, j, 1, 0)
            # two components form one letter (dot over a stem, split serif)
            if i + 1 < n and j < m and _xoverlap(items[i], items[i + 1]) > 0.35:
                w = max(items[i]["x1"], items[i + 1]["x1"]) - min(items[i]["x0"], items[i + 1]["x0"])
                c = (base + abs(w - aw) + 2.0
                     + pos_w * abs((i + 2) / n - (j + 1) / m))
                if c < D[i + 2][j + 1]:
                    D[i + 2][j + 1] = c; P[i + 2][j + 1] = (i, j, 2, 1)
    if D[n][m] == INF:
        return None
    cost = D[n][m] / max(m, 1)
    out = []
    i, j = n, m
    while P[i][j]:
        pi, pj, nc, nk = P[i][j]
        if nk == 1:
            out.append((expected[pj], list(range(pi, pi + nc))))
        # nk == 0 is a skipped stray mark; nk > 1 is a weld, neither is nameable
        i, j = pi, pj
    out.reverse()
    return out, cost


def autolabel(page, rect, expected, min_pixels=16, verbose=False):
    """Segment a rect known to read `expected` and name each glyph.

    Lines are flattened into one reading-order sequence and aligned against the
    whole string, so the transcript can be pasted in without reproducing the
    hand-lettered line breaks. Each glyph keeps its own line baseline.
    """
    img = load_page(page)
    sub = img.crop(rect)
    lab, comps = components(ink_mask(sub))
    comps = [c for c in comps if c["pixels"] >= min_pixels]
    comps = drop_rules(comps, rect, 0.60, 0.60)
    comps = letterlike(comps)
    lines = group_lines(comps)
    seq, bases = [], []
    for ln in lines:
        for c in ln["items"]:
            seq.append(c); bases.append(ln["base"])
    flat = "".join(expected.split())
    # Average letter width has to be summed per line. Measuring it end to end
    # across a wrapped block gives a meaningless span, and every width-based
    # cost in the alignment then compares against nonsense.
    inked = sum(ln["items"][-1]["x1"] - ln["items"][0]["x0"] for ln in lines)
    got = align_line(seq, flat, aw=inked / float(max(len(flat), 1)))
    if got is None:
        return [], [f"p{page} {rect}: align failed ({len(seq)}c / {len(flat)}ch)"]
    pairs, cost = got
    recs = []
    for ch, idxs in pairs:
        cs = [seq[k] for k in idxs]
        recs.append(dict(
            char=ch, page=page,
            box=[rect[0] + min(c["x0"] for c in cs), rect[1] + min(c["y0"] for c in cs),
                 rect[0] + max(c["x1"] for c in cs), rect[1] + max(c["y1"] for c in cs)],
            cids=[c["id"] for c in cs], rect=list(rect),
            base=rect[1] + bases[idxs[0]],
            pixels=sum(c["pixels"] for c in cs)))
    for r in recs:
        r["cost"] = cost
    rep = [f"p{page} {rect} {len(seq)}c/{len(flat)}ch -> {len(recs)} named  cost={cost:.1f}"]
    return recs, rep


def blocks(page, min_h=19, min_n=3, xtol=0.45, ygap=1.6):
    """Merge line runs into caption blocks: runs that overlap horizontally and
    sit within ygap line-heights of each other belong to the same block."""
    runs = [r for r in find_lines(page) if r["h"] >= min_h and r["n"] >= min_n]
    runs.sort(key=lambda r: (r["box"][1], r["box"][0]))
    out = []
    for r in runs:
        x0, y0, x1, y1 = r["box"]
        placed = False
        for b in out:
            bx0, by0, bx1, by1 = b["box"]
            ov = max(0, min(x1, bx1) - max(x0, bx0))
            if ov > xtol * min(x1 - x0, bx1 - bx0) and y0 - by1 < ygap * b["h"]:
                b["box"] = (min(x0, bx0), min(y0, by0), max(x1, bx1), max(y1, by1))
                b["n"] += r["n"]; b["h"] = max(b["h"], r["h"]); b["rows"] += 1
                placed = True
                break
        if not placed:
            out.append(dict(box=r["box"], n=r["n"], h=r["h"], rows=1))
    out.sort(key=lambda b: (b["box"][1], b["box"][0]))
    return out

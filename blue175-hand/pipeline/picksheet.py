"""Every candidate for the digits that read wrong, shown two ways so a human can pick.

The eye has now picked wrong twice on this font. Both times the mistake was the
same: the candidate was judged as *ink*, blown up, where a heavier stroke looks
like a better letter. At 44px the clock-face `2` turned into an `L` and the
clock `5` into an `S`. So every candidate here gets rendered twice --
`ink_<ch>.png` is the source ink at 6x, and `set_<ch>.png` is the same shape
built into a real font and set at reading size, in isolation, in a number, and
beside the letter readers actually confuse it with.

**The second image is the one that decides.** The first is only there to show
what the hand had to work with.

Candidates come from three places and get deduped on (page, box): the
auto-labelled bank (`bank_auto.json`, whose labels are unreliable, so a pool can
contain a shape that is not the character at all), the per-character candidate
grids (`cand_other.json`), and the hand-picked contact sheets. Bank records have
no `picks.json` address, so the pool is written back out as `manPick<ch>.json`
and addressed as a `man` sheet -- that is the only address form that can name an
arbitrary component.

Ordering: the shipping pick is always row `a`, then the rest by source ink
descending. Bigger source traces cleaner, but it is not the same as reading
better -- the `2` that won was the smallest of its top four.
"""
import json, os, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import glyphlab as G
import build as B
import paths as P

PICKS = P.data("picks.json")
MAXROWS = 8          # rows per character, so 8 builds total rather than one per candidate

# The digits blind readers get wrong, with what they get read as.
TARGETS = {
    "0": ("O", "0 00 2018 $40.00   Oo0 O0O 100"),
    "1": ("l/I", "1 11 1985 11:15   Il1 l1l 100"),
    "2": ("3/7/Z", "2 22 2018 $127.00   Zz2 Z2Z 25"),
    "3": ("B", "3 33 2013 $3.00   Bb3 B3B 30"),
    "5": ("S", "5 55 1985 $5.50   Ss5 S5S 50"),
    "8": ("b", "8 88 2018 $8.00   Bb8 b8b 80"),
}

# Which pool rows are actually this character, read off `ink_<ch>.png`.
#
# The bank's labels come from transcript alignment and are unreliable, so a pool
# of 8 for `1` is one bare stroke plus seven shapes that are an `a`, a `b`, a `k`
# and four blobs. Dropping those is not the same judgment as choosing between two
# real candidates -- it is a spelling check, and the ink sheet still shows every
# row so the call is auditable. What survives is the finding: **four of these six
# digits have exactly one usable candidate in fifteen pages.**
KEEP = {
    "0": "ac",     # a closed loop, and one whose left half filled with ink
    "1": "a",      # one bare stroke, which is the whole problem
    "2": "abde",   # the real choice
    "3": "abc",    # the other real choice
    "5": "ac",     # both are the hand's `S`
    "8": "a",      # the other bank row is a `4`
}

# Digit entries in the hand-picked sheets. These sheets index by contact-sheet
# position and record no character, so the ones in play are named explicitly.
MAN = {
    "0": [("H", 316), ("2013", 1)],
    "1": [("Dollar", 10), ("2013", 2)],
    "2": [("Dollar", 11), ("Clock", 2), ("2013", 0)],
    "3": [("Years", 37), ("2013", 3), ("3", 0), ("3", 1), ("3", 2), ("30", 0)],
    "5": [("Years", 24), ("Clock2", 2)],
    "8": [("Years", 7)],
}


def label_font(px):
    for p in (r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\arial.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, px)
    return ImageFont.load_default()


def pool(ch):
    """Every distinct source component that might be this character.

    Deduped on (page, box) because the bank and the candidate grid overlap: the
    same ink appears in both with different provenance.
    """
    seen, out = set(), []

    def add(r, src):
        key = (r["page"], tuple(r["box"]))
        if key in seen:
            return
        seen.add(key)
        out.append(dict(page=r["page"], rect=list(r["rect"]), box=list(r["box"]),
                        pixels=r.get("pixels", 0), cids=r.get("cids"), src=src))

    cur = B.resolve_picks().get(ch)
    if cur:
        add(cur, "shipping")
    for sheet, idx in MAN.get(ch, []):
        p = P.data(f"man{sheet}.json")
        if not os.path.exists(p):
            continue
        m = P.load(p).get(str(idx))
        if m:
            add(m, f"man {sheet} {idx}")
    grid = P.load(P.data("cand_other.json")).get(ch, [])
    for i, r in enumerate(grid):
        add(r, f"cand other {ch} {i}")
    for r in P.load(P.data("bank_auto.json")):
        if r["char"] == ch:
            add(r, f"bank p{r['page']}")

    head, rest = out[:1], out[1:]
    rest.sort(key=lambda r: -r["pixels"])
    return head + rest


def write_pool(ch, cands):
    """The pool as a `man` sheet, which is the only address form for arbitrary ink."""
    P.dump({str(i): c for i, c in enumerate(cands)}, P.data(f"manPick{ch}.json"), indent=1)


def mask_of(c, ch):
    r = dict(c)
    r["cids"] = c.get("cids") or B.cids_for(c["page"], c["rect"], c["box"])
    return B.tighten(B.cut(r))


def ink(pools, cell=132, gap=14, pad=40):
    """Source ink at 6x, nearest-neighbour, so the pixels are visible as pixels."""
    lf, sf = label_font(17), label_font(13)
    for ch, cands in pools.items():
        tiles = []
        for i, c in enumerate(cands):
            m = mask_of(c, ch)
            im = Image.fromarray((~m * 255).astype("uint8")).convert("RGB")
            s = min(cell / max(m.shape[0], 1), cell / max(m.shape[1], 1), 8)
            im = im.resize((max(1, int(m.shape[1] * s)), max(1, int(m.shape[0] * s))),
                           Image.NEAREST)
            tiles.append((chr(97 + i), im, c, m))
        W = pad * 2 + sum(t[1].width + gap for t in tiles)
        H = pad * 2 + cell + 46
        out = Image.new("RGB", (max(W, 400), H), (255, 255, 255))
        d = ImageDraw.Draw(out)
        d.text((pad, 12), f"'{ch}'  candidates, source ink at up to 8x "
                          f"(readers call it {TARGETS[ch][0]})", font=lf, fill=(20, 20, 20))
        x = pad
        for tag, im, c, m in tiles:
            out.paste(im, (x, pad + (cell - im.height)))
            d.text((x, pad + cell + 6), tag, font=lf, fill=(180, 30, 30))
            d.text((x + 16, pad + cell + 8),
                   f"{m.shape[1]}x{m.shape[0]} p{c['page']}", font=sf, fill=(110, 110, 110))
            d.text((x, pad + cell + 26), c["src"][:22], font=sf, fill=(140, 140, 140))
            x += im.width + gap
        out.save(P.out(f"ink_{ch}.png"))
        print(f"ink_{ch}.png  {len(tiles)} candidates  {out.size}")


def kept(ch, cands):
    """(tag, index, cand) for the rows worth setting in a font."""
    return [(chr(97 + i), i, c) for i, c in enumerate(cands)
            if chr(97 + i) in KEEP.get(ch, "")]


def variants(pools):
    """Build one font per candidate index.

    Row i of every character shares font i, so the build count is the widest
    pool rather than the sum of all of them.
    """
    idxs = sorted({i for ch, cs in pools.items() for _, i, _ in kept(ch, cs)})
    keep = P.load(PICKS)
    shutil.copy(PICKS, P.out("picks.json.pick.bak"))
    try:
        for i in idxs:
            spec = json.loads(json.dumps(keep))
            for ch, cands in pools.items():
                if i >= len(cands) or chr(97 + i) not in KEEP.get(ch, ""):
                    continue
                for s in ("cand", "man", "merge", "clip", "synth"):
                    spec.get(s, {}).pop(ch, None)
                spec.setdefault("man", {})[ch] = [f"Pick{ch}", i]
            P.dump(spec, PICKS, indent=1)
            B.build("Regular", out_path=f"PICK-{i}.ttf")
            print(f"PICK-{i}.ttf built")
    finally:
        P.dump(keep, PICKS, indent=1)


def sets(pools, size=44, big=88, pad=44):
    """The rows that decide: each candidate set at reading size, and once large.

    Large is second and deliberately smaller than the ink sheet's 8x. A glyph
    judged at display size is not judged.
    """
    import render
    lf, sf = label_font(17), label_font(13)
    faces = {}
    for ch, cands in pools.items():
        text = TARGETS[ch][1]
        rows = []
        for tag, i, c in kept(ch, cands):
            f = faces.setdefault((i, size), render.Face(P.out(f"PICK-{i}.ttf"), size))
            g = faces.setdefault((i, big), render.Face(P.out(f"PICK-{i}.ttf"), big))
            rows.append((tag, c, f, g))
        lh = int(big * 1.9)
        W = int(pad * 2 + 120 + max(r[2].getlength(text) for r in rows)
                + max(r[3].getlength(ch + ch) for r in rows) + 40)
        out = Image.new("RGB", (W, pad * 2 + 34 + lh * len(rows)), (255, 255, 255))
        d = ImageDraw.Draw(out)
        d.text((pad, 14), f"'{ch}'  each candidate set at {size}px, then {big}px "
                          f"(readers call it {TARGETS[ch][0]})", font=lf, fill=(20, 20, 20))
        y = pad + 34
        for tag, c, f, g in rows:
            d.text((pad, y + big * 0.35), tag, font=lf, fill=(180, 30, 30))
            d.text((pad + 16, y + big * 0.37), c["src"][:20], font=sf, fill=(150, 150, 150))
            f.text(out, (pad + 120, y + int(big * 0.30)), text, (30, 40, 60))
            g.text(out, (int(pad + 130 + f.getlength(text) + 30), y), ch + ch, (30, 40, 60))
            y += lh
        out.save(P.out(f"set_{ch}.png"))
        print(f"set_{ch}.png  {len(rows)} rows  {out.size}")


def combine(prefix, out):
    """Stack the per-character sheets, so this is two windows rather than twelve."""
    ims = [Image.open(P.out(f"{prefix}_{ch}.png")) for ch in TARGETS]
    W, H = max(i.width for i in ims), sum(i.height for i in ims)
    big = Image.new("RGB", (W, H), (255, 255, 255))
    y = 0
    for i, im in enumerate(ims):
        big.paste(im, (0, y))
        y += im.height
        if i < len(ims) - 1:
            ImageDraw.Draw(big).line([(30, y - 1), (W - 30, y - 1)], fill=(215, 215, 215))
    big.save(P.out(out))
    print(out, big.size)


if __name__ == "__main__":
    import sys
    pools = {}
    for ch in TARGETS:
        p = pool(ch)[:MAXROWS]
        write_pool(ch, p)
        pools[ch] = p
        print(f"'{ch}' pool {len(p)} of {len(pool(ch))}")
    stage = sys.argv[1] if sys.argv[1:] else "all"
    if stage in ("all", "ink"):
        ink(pools)
    if stage in ("all", "build"):
        variants(pools)
    if stage in ("all", "set"):
        sets(pools)
    if stage in ("all", "set", "ink", "combine"):
        combine("ink", "picks_ink.png")
        combine("set", "picks_set.png")

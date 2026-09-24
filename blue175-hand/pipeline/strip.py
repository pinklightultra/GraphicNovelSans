"""Read one source block at high zoom with its components numbered.

A contact sheet shows glyphs out of context, which is exactly what made naming
them guesswork. Keeping the word intact and putting an index under each
component lets a letter be identified from its neighbours and then addressed by
number.
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import glyphlab as G
import paths as P

def strip(page, rect, min_pixels=12, zoom=3, out=None, tag="", raw=False):
    sub = G.load_page(page).crop(tuple(rect))
    lab, comps = G.components(G.ink_mask(sub))
    comps = [c for c in comps if c["pixels"] >= min_pixels]
    comps = G.drop_rules(comps, tuple(rect), 0.60, 0.60)
    # Display lettering is far taller than the running text around it, so the
    # letter-likeness filter throws it away as an outlier. For those blocks the
    # raw components are what we want.
    if not raw:
        comps = G.letterlike(comps)
    comps.sort(key=lambda c: (c["y0"] // 30, c["x0"]))
    w, h = sub.size
    im = Image.new("RGB", (w * zoom, h * zoom + 26), (255, 255, 255))
    im.paste(sub.resize((w * zoom, h * zoom), Image.LANCZOS), (0, 0))
    d = ImageDraw.Draw(im)
    f = ImageFont.load_default()
    man = {}
    for i, c in enumerate(comps):
        man[i] = dict(page=page, rect=list(rect), pixels=c["pixels"], cids=[c["id"]],
                      box=[rect[0] + c["x0"], rect[1] + c["y0"],
                           rect[0] + c["x1"], rect[1] + c["y1"]])
        d.rectangle([c["x0"] * zoom, c["y0"] * zoom,
                     c["x1"] * zoom, c["y1"] * zoom], outline=(230, 120, 120))
        d.text((c["x0"] * zoom, max(0, c["y0"] * zoom - 11)), str(i), fill=(200, 0, 0), font=f)
    d.text((4, h * zoom + 6), f"p{page} {tuple(rect)}  {len(comps)} comps  {tag}", fill=(0, 0, 0), font=f)
    if out:
        im.save(P.out(out))
    return im, man


def sheet(jobs, out="strip.png", manifest="manS.json", zoom=3):
    """Stack several blocks into one image, numbering across the whole set."""
    ims, man, off = [], {}, 0
    for pg, rect, mp, tag, *rest in jobs:
        im, m = strip(pg, rect, mp, zoom, tag=tag, raw=bool(rest and rest[0]))
        for k, v in m.items():
            man[off + k] = v
        d = ImageDraw.Draw(im)
        f = ImageFont.load_default()
        for k, v in m.items():
            x = (v["box"][0] - rect[0]) * zoom
            y = max(0, (v["box"][1] - rect[1]) * zoom - 11)
            d.rectangle([x, y, x + 22, y + 11], fill=(255, 255, 255))
            d.text((x, y), str(off + k), fill=(200, 0, 0), font=f)
        off += len(m)
        ims.append(im)
    W = max(i.width for i in ims)
    H = sum(i.height + 8 for i in ims)
    can = Image.new("RGB", (W, H), (245, 245, 245))
    y = 0
    for i in ims:
        can.paste(i, (0, y)); y += i.height + 8
    can.save(P.out(out))
    P.dump(man, P.out(manifest))
    print(out, can.size, off, "components ->", manifest)

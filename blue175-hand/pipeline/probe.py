"""Show the cut mask for named manifest entries, labelled by index.

A numbered strip proves where a component sits in its word, but not what `cut`
actually extracts from it -- a weld or a clipped box only shows up once the
component ids are applied. This renders candidates the same way the font will,
so a pick can be checked before it is written down.
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw

import glyphlab as G
import build
import paths as P


def cells(items, out="probe.png", cell=140, cols=10):
    """items: (label, manifest_name, index) -- render each entry's cut mask."""
    rows = (len(items) + cols - 1) // cols
    im = Image.new("RGB", (cols * cell, rows * cell), "white")
    d = ImageDraw.Draw(im)
    for i, (label, sheet, idx) in enumerate(items):
        m = P.load(P.data(f"man{sheet}.json"))[str(idx)]
        rec = dict(char="?", page=m["page"], rect=m["rect"], box=m["box"],
                   cids=m.get("cids") or build.cids_for(m["page"], m["rect"], m["box"]))
        mask = build.tighten(build.cut(rec))
        cx, cy = (i % cols) * cell, (i // cols) * cell
        d.rectangle([cx, cy, cx + cell - 1, cy + cell - 1], outline=(220, 220, 220))
        if mask.size:
            g = Image.fromarray((~mask * 255).astype(np.uint8))
            s = min((cell - 30) / max(g.width, 1), (cell - 30) / max(g.height, 1))
            g = g.resize((max(1, int(g.width * s)), max(1, int(g.height * s))), Image.NEAREST)
            im.paste(g, (cx + (cell - g.width) // 2, cy + 24 + (cell - 24 - g.height) // 2))
        d.text((cx + 4, cy + 4), f"{label} {sheet}[{idx}]", fill=(200, 0, 0))
    im.save(P.out(out))
    print(out, im.size, len(items), "cells")


if __name__ == "__main__":
    spec = json.loads(sys.argv[1])
    cells([tuple(s) for s in spec], out=sys.argv[2] if len(sys.argv) > 2 else "probe.png")

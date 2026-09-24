"""Render, for each character, its plausible instances side by side so the right
one can be chosen by eye. Alignment gets the glyph bank close; this is the step
that makes it correct."""
import json, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import build as B, glyphlab as G
import paths as P

CELL = 96


def sheet(chars, out, ncand=9):
    by = B.gather()
    rows = []
    for ch in chars:
        cs = by.get(ch, [])
        for c in cs:
            c["scale"] = B.X_HEIGHT / float(c["xh"])
        fit = [c for c in cs if B.plausible(ch, c["mask"], c["scale"])]
        fit.sort(key=lambda c: (not c.get("hand"), -c["mask"].sum()))
        rows.append((ch, fit[:ncand]))
    W = CELL * (ncand + 1) + 20
    H = CELL * len(rows) + 20
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    big = G.label_font(40)
    sm = G.label_font(15)
    idx = {}
    for r, (ch, cands) in enumerate(rows):
        py = 10 + r * CELL
        d.rectangle([10, py, 10 + CELL - 4, py + CELL - 4], fill=(240, 240, 245))
        d.text((26, py + 22), ch if ch.strip() else "sp", fill=(150, 0, 0), font=big)
        idx[ch] = []
        for k, c in enumerate(cands):
            px = 10 + (k + 1) * CELL
            m = c["mask"]
            gi = Image.fromarray(np.where(m, 0, 255).astype(np.uint8)).convert("RGB")
            sc = min((CELL - 26) / max(gi.width, 1), (CELL - 26) / max(gi.height, 1), 4.0)
            gi = gi.resize((max(1, int(gi.width * sc)), max(1, int(gi.height * sc))), Image.LANCZOS)
            d.rectangle([px, py, px + CELL - 4, py + CELL - 4], outline=(215, 215, 215))
            img.paste(gi, (px + (CELL - 4 - gi.width) // 2, py + 18 + (CELL - 26 - gi.height) // 2))
            tag = f"{k}{'*' if c.get('hand') else ''}"
            d.text((px + 3, py + 1), tag, fill=(0, 90, 200), font=sm)
            idx[ch].append(dict(page=c["page"], box=c["box"], rect=c["rect"],
                                base=c["base"], cids=c.get("cids"),
                                pixels=c["pixels"], hand=bool(c.get("hand"))))
    img.save(P.out(out))
    P.dump(idx, P.out(out.replace(".png", ".json")))
    return img.size


if __name__ == "__main__":
    which = sys.argv[1]
    sets = {
        "upper": list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
        "lower": list("abcdefghijklmnopqrstuvwxyz"),
        "other": list("0123456789") + list(".,'\"!?()$-"),
    }
    print(sheet(sets[which], f"cand_{which}.png"))

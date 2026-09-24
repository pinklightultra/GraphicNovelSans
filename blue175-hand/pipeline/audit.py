"""Show every chosen glyph's actual pixels next to the character it was assigned.

Reading the rendered font is indirect: a wrong glyph and a badly placed glyph
look similar on the page. This puts the source ink itself under a label, so a
mis-assignment is obvious in one pass.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import build
import paths as P

def sheet(out="audit.png", cell=110, cols=13):
    picked = build.resolve_picks()
    keys = sorted(picked, key=lambda c: (c.isdigit(), not c.isalpha(), c.swapcase()))
    rows = (len(keys) + cols - 1) // cols
    im = Image.new("RGB", (cols * cell, rows * (cell + 20)), (255, 255, 255))
    d = ImageDraw.Draw(im)
    f = ImageFont.load_default()
    for i, ch in enumerate(keys):
        r = picked[ch]
        m = build.tighten(r["mask"])
        h, w = m.shape
        s = min((cell - 12) / h, (cell - 12) / w)
        g = Image.fromarray(((~m) * 255).astype(np.uint8)).resize(
            (max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)
        cx, cy = (i % cols) * cell, (i // cols) * (cell + 20)
        im.paste(g, (cx + (cell - g.width) // 2, cy + 20 + (cell - 12 - g.height) // 2))
        d.rectangle([cx, cy, cx + cell - 1, cy + cell + 18], outline=(220, 220, 220))
        note = r.get("synth") or ""
        d.text((cx + 5, cy + 4), f"{ch}  {note}", fill=(200, 0, 0), font=f)
    im.save(P.out(out))
    print(out, im.size, len(keys), "glyphs")

if __name__ == "__main__":
    sheet()

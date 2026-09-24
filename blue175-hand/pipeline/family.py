"""Show the four styles together, and show what the kern table is doing.

Two things need proving separately. That Bold is heavier without being a blot and
that Italic leans without falling over is a matter of looking at the same words in
all four. That the kern table earns its 702 pairs is not visible in a single
render at all, so the pair rows are drawn twice -- once shaped with the feature on
and once with it off -- and the difference is the whole argument.
"""
import os
from PIL import Image, ImageDraw, ImageFont
import render

import paths as P
STYLES = [("Regular", "BLUE175.ttf"), ("Bold", "BLUE175-Bold.ttf"),
          ("Italic", "BLUE175-Italic.ttf"), ("Bold Italic", "BLUE175-BoldItalic.ttf")]
INK = (58, 92, 156)
PAPER = (250, 251, 247)
LABEL = (170, 90, 90)

SAMPLE = "Handgloves quiz $127.00"
WORDS = "The times are precarious, the precarious are timed."
# The pairs the table has the strongest opinion about, tucks first and then the
# protective ones. Ordinary words barely move: most of the spacing work is in the
# sidebearings, and a kern table that changed every word would mean they were wrong.
PAIRS = "LT hT bT 3T 6T $5T  wd rx ry sJ ?V (2 F. M,"


def page(out="family.png", size=44, width=1500):
    im = Image.new("RGB", (width, 210 + 150 * len(STYLES)), PAPER)
    d = ImageDraw.Draw(im)
    lab = ImageFont.load_default()
    y = 30
    for name, path in STYLES:
        f = render.Face(P.font(path), size)
        d.text((40, y), f"{name}  ({os.path.basename(path)})", font=lab, fill=LABEL)
        f.text(im, (40, y + 16), SAMPLE, INK)
        f.text(im, (40, y + 16 + int(size * 1.5)), WORDS, INK)
        y += 150

    d.text((40, y + 6), "kern feature ON, then OFF -- same string, same size",
           font=lab, fill=LABEL)
    on = render.Face(P.font("BLUE175.ttf"), size)
    off = render.Face(P.font("BLUE175.ttf"), size, kern=False)
    on.text(im, (40, y + 24), PAIRS, INK)
    off.text(im, (40, y + 24 + int(size * 1.5)), PAIRS, (150, 150, 150))
    d.text((width - 300, y + 24), f"on  {on.getlength(PAIRS):.0f}px", font=lab,
           fill=LABEL)
    d.text((width - 300, y + 24 + int(size * 1.5)),
           f"off {off.getlength(PAIRS):.0f}px", font=lab, fill=LABEL)
    im.save(P.out(out))
    print(out, im.size)


if __name__ == "__main__":
    page()

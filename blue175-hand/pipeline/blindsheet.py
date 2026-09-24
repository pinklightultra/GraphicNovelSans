"""Render a recognition test for a reader who has never seen the source.

Prose is a soft test: a reader who half-recognises a word repairs it from
context and the font gets credit it did not earn. So the sheet mixes running
sentences with pangrams, random syllables and a line of the exact pairs a
hand-cut font is likely to collapse (I/l/1, O/0, S/5, Z/2, x/X). The line
numbers are drawn in a system font, so nothing about the answer key is set in
the font under test.

The last four lines are set in Bold, Italic and Bold Italic. A derived weight can
fail in ways the upright never does -- dilation can fill a counter shut, and shear
can turn one letter into another -- so they have to be read blind too, and the
reader is not told which line is which style. Everything is shaped through
HarfBuzz, so the kerning under test is the kerning that ships.
"""
import json, os
from PIL import Image, ImageDraw, ImageFont
import render

import paths as P
INK = (30, 40, 60)

REG = "BLUE175.ttf"
BOLD = "BLUE175-Bold.ttf"
ITAL = "BLUE175-Italic.ttf"
BI = "BLUE175-BoldItalic.ttf"

# (style file, text)
LINES = [
    (REG,  "The quick brown fox jumps over a lazy dog"),
    (REG,  "Pack my box with five dozen liquor jugs"),
    (REG,  "Parking enforcement has become a crucial revenue stream"),
    (REG,  "I spend ten minutes after I clock in pretending to be busy"),
    (REG,  "vex bulk myth zone quiz jade wharf gyp"),
    (REG,  "0123456789 and $127.00 in 2018"),
    (REG,  "Wait, who? (yes!) 'ok' - fine; go: now."),
    (REG,  "BLUE175 Hand set in Northwest Orlando"),
    (REG,  "kf7 zqp3 dwx9 mb2 vth6 yjl8 rcn4"),
    (REG,  "Il1 O0o Ss5 Zz2 Xx Cc Vv Ww Uu"),
    (BOLD, "The store is positioned as a Christian answer"),
    (BOLD, "bdpq gaoe mn Il1 O0o Ss5 8 jump quiz"),
    (ITAL, "Twice in one day, and the light was awful"),
    (ITAL, "wharf gyp vex Il1 O0o Ss5 Zz2 kb7 quiz"),
    (BI,   "Ten minutes done. Thank god it is over."),
]


def sheet(out="blindtest.png", key="blindtest_key.json", size=44, pad=60):
    faces = {}
    for f, _ in LINES:
        faces.setdefault(f, render.Face(P.font(f), size))
    num = ImageFont.load_default()
    lh = int(size * 2.1)
    W = int(pad * 2 + 60 + max(faces[f].getlength(t) for f, t in LINES))
    im = Image.new("RGB", (W, pad * 2 + lh * len(LINES)), (255, 255, 255))
    d = ImageDraw.Draw(im)
    y = pad
    for i, (f, t) in enumerate(LINES, 1):
        d.text((pad, y + size * 0.45), f"{i:02d}", font=num, fill=(150, 150, 150))
        faces[f].text(im, (pad + 60, y), t, INK)
        y += lh
    im.save(P.out(out))
    P.dump({f"{i:02d}": t for i, (_, t) in enumerate(LINES, 1)}, P.out(key), indent=1)
    print(out, im.size, len(LINES), "lines;", key, "written")


if __name__ == "__main__":
    sheet()

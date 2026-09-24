"""Render the built font so the charset can be read back by eye.

A font's real test is whether a stranger can read it, so the proof shows every
glyph twice: alone under its expected character, then in running words where
neighbouring shapes have to stay distinct. The running words go through the
shaper, not through Pillow, so what they show includes the kerning.
"""
import os
from PIL import Image, ImageDraw, ImageFont
import render
import paths as P

TTF = P.font("BLUE175.ttf")
INK = (60, 90, 150)


def sheet(out="proof.png", size=64):
    f = render.Face(TTF, size)
    lab = ImageFont.load_default()
    rows = ["ABCDEFGHIJKLM", "NOPQRSTUVWXYZ",
            "abcdefghijklm", "nopqrstuvwxyz",
            "0123456789", "..,'\"!?()$-:"]
    words = ["Handgloves quiz", "The King of Queens",
             "vexing fjord waltz", "$127.00 zero", "BLUE175"]
    W, pad, lh = 1500, 40, size + 46
    H = pad * 2 + lh * (len(rows) + len(words)) + 90
    im = Image.new("RGB", (W, H), (252, 252, 250))
    d = ImageDraw.Draw(im)
    y = pad
    for r in rows:
        x = pad
        for ch in r:
            f.text(im, (x, y + 22), ch, INK)
            d.text((x, y), ch, font=lab, fill=(190, 70, 70))
            x += f.getlength(ch) + 14
        y += lh
    y += 30
    for w in words:
        f.text(im, (pad, y), w, INK)
        d.text((pad, y - 12), w, font=lab, fill=(190, 70, 70))
        y += lh
    im.save(P.out(out))
    print(out, im.size)


if __name__ == "__main__":
    sheet()

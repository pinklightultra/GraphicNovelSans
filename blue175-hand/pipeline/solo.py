"""One font per sheet, same texts, so the `2` is judged the way a real page is read.

The round-3 mixed sheet had both `2` candidates on it, and that is a cue a reader
would never get in life: seeing two distinct shapes on one page forces you to
tell them apart, which flatters both. It put the new `2` at 23/24 and the old at
5/24. On the single-font prose sheet the same new `2` was read correctly by one
reader out of three and as `Z` by the other two -- and each of those readers was
internally consistent, all six right or all six wrong.

So the unit of measurement is not the character, it is the reader: a reader
decides once what this shape is,
and per-character counts just multiply that decision by frequency. Which means
the only honest comparison is one font per sheet, identical texts, several
readers per arm, counting **how many readers** got the glyph rather than how many
instances.

Four readers an arm is still a small n. It is enough to separate "every reader
reads it" from "no reader reads it", which is the size of gap that matters here,
and not enough to rank two glyphs that both half-work.
"""
import json, os
from PIL import Image, ImageDraw, ImageFont

import paths as P

TEXTS = [
    "0123456789 and $127.00 in 2018",
    "kf7 zqp3 dwx9 mb2 vth6 yjl8 rcn4",
    "I clock in at 7:25 and leave at 12:30",
    "Pack my box with 22 dozen liquor jugs",
    "The quick brown fox jumps over a lazy dog",
    "Il1 O0o Ss5 Zz2 Xx Cc Vv Ww Uu",
]


def sheet(font, out, key, size=44, pad=60):
    import render
    face = render.Face(P.font(font), size)
    num = ImageFont.load_default()
    lh = int(size * 2.1)
    W = int(pad * 2 + 60 + max(face.getlength(t) for t in TEXTS))
    im = Image.new("RGB", (W, pad * 2 + lh * len(TEXTS)), (255, 255, 255))
    d = ImageDraw.Draw(im)
    y = pad
    for i, t in enumerate(TEXTS, 1):
        d.text((pad, y + size * 0.45), f"{i:02d}", font=num, fill=(150, 150, 150))
        face.text(im, (pad + 60, y), t, (30, 40, 60))
        y += lh
    im.save(P.out(out))
    P.dump({f"{i:02d}": t for i, t in enumerate(TEXTS, 1)}, P.out(key), indent=1)
    print(out, im.size, font)


def score(key, reads, ch="2"):
    """Per-reader accuracy on one character, because the reader is the unit."""
    import abscore
    truth = P.load(P.read(key))
    for r in reads:
        got = P.load(P.read(r))
        hits = seen = errs = chars = 0
        saw = []
        for k in sorted(truth):
            t, g = truth[k], got.get(k, "")
            d, pairs = abscore.align(t, g)
            errs += d
            chars += len(t)
            for tc, gc in pairs:
                if tc == ch:
                    seen += 1
                    hits += tc == gc
                    saw.append(gc or "_")
        print(f"  {r:22} CER {errs/chars:6.2%}   {ch!r} {hits:2}/{seen:<2} "
              f"read as {''.join(saw)}")


if __name__ == "__main__":
    import sys
    if sys.argv[1:] and sys.argv[1] == "score":
        for arm, font in (("A", "VAR-A.ttf (old 2)"), ("E", "VAR-E.ttf (new 2)")):
            print(f"arm {arm}  {font}")
            score(f"solo{arm}_key.json",
                  [f"solo{arm}_read{i}.json" for i in (1, 2, 3, 4)])
    else:
        sheet("VAR-A.ttf", "soloA.png", "soloA_key.json")
        sheet("VAR-E.ttf", "soloE.png", "soloE_key.json")

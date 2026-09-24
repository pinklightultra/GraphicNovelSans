"""Set a page of real text in the finished font.

The proof sheet answers whether the glyphs are right. This answers the question
the font was made for: does a paragraph of the author's own prose, typed rather
than lettered, still look like their hand and still read as sentences.
"""
import os
from PIL import Image, ImageDraw
import render

import paths as P

TTF = P.font("BLUE175.ttf")
ITALIC = P.font("BLUE175-Italic.ttf")
BOLD = P.font("BLUE175-Bold.ttf")
INK = (58, 92, 156)
PAPER = (250, 251, 247)

TITLE = "BLUE175 Hand"
PARAS = [
    """I work at what I can only describe as Northwest Orlando's 2nd most
    abandoned mall. This job works great for me. You can pretty much do
    whatever. I spend ten minutes after I clock in pretending to be busy. The
    store is positioned as a "Christian answer to Hot Topic," and you would
    think, were the promise to take itself seriously, they would have started
    years ago.""",
    """Parking enforcement has become a crucial revenue stream. Us few store
    workers are therefore deputized. Though, I want to stress, this is not
    legal action: the fines are technically opt-in, and they are paid out to us
    as a kind of small commission. $127.00, if you were wondering. Twice in one
    day.""",
    """The times are precarious, the precarious are timed. So said an awful poet
    at an open mic I went to (mine). Ten minutes done. The light. Thank god
    it's over.""",
]


def wrap(font, text, limit):
    """Greedy wrap on measured advance width, not on character count.

    The font's advances vary a lot -- a hand-cut 'm' is three times an 'i' --
    so wrapping by column count leaves a ragged overflowing edge.
    """
    lines, line = [], ""
    for word in " ".join(text.split()).split(" "):
        trial = f"{line} {word}".strip()
        if line and font.getlength(trial) > limit:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines


def page(out="specimen.png", size=40, width=1240):
    f = render.Face(TTF, size)
    ft = render.Face(BOLD, int(size * 2.0))
    lines = []
    for i, p in enumerate(PARAS):
        if i:
            lines.append("")
        lines += wrap(f, p, width - 140)
    lh = int(size * 1.85)
    H = 150 + int(size * 2.6) + lh * len(lines)
    im = Image.new("RGB", (width, H), PAPER)
    d = ImageDraw.Draw(im)
    ft.text(im, (70, 60), TITLE, INK)
    y = 70 + int(size * 2.6)
    d.line([70, y, width - 70, y], fill=(200, 210, 225), width=2)
    y += 40
    for ln in lines:
        f.text(im, (70, y), ln, INK)
        y += lh
    im.save(P.out(out))
    print(out, im.size, len(lines), "lines")


if __name__ == "__main__":
    page()

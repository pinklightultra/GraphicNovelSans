"""Head-to-head digit picks at reading size, measured rather than eyeballed.

The clock-face repick of `2`, `5` and `6` was judged at 105px, looked better,
and measured worse at 44px: three readers went 4.35/4.68/6.52 to 7.19/7.36/9.20.
`2` and `5` had changed together, so the pooled table could not say which one
paid for it Hence a crossed design.

ROUND 1 -- 2x2, old vs new `2` crossed with old vs new `5`:

    arm  2               5
    A    Dollar 11       Years 24      both old   (the pre-repick baseline)
    B    Clock 2         Clock2 2      both new   (what shipped, regressed)
    C    Dollar 11       Clock2 2      new 5 only
    D    Clock 2         Years 24      new 2 only

Result, and it is mostly a lesson about the readers: all four arms scored an
*identical* 30.65% CER, down to the character, with every non-tested digit
matching arm for arm. Both `2` picks came out 0/78 and both `5` picks 6/72. The
tell is the perfect identity -- three independent readers do not agree to the
character unless they are each answering per *shape* rather than per instance,
which is what one of them said it was doing. Round 1's protocol let a reader fix
one reading for a glyph and apply it down the whole sheet, so its absolute rates
measure a lookup table, not legibility. Round 2's prompt adds "judge each
character on its own shape", and the same arm A `2` goes from 0/39 to 31/39.

What survives round 1 is the direction, not the numbers: the old `2` is read as
`3`, the new one as `L`, consistently and by everyone. Two failures of the same
size into different letters.

ROUND 2 -- the pick round 1 says is missing. `cand_other['2'][3]` on page 1 is
the only `2` in the source with a closed bottom bar, which is the stroke that
separates a `2` from a `3` and from a `7`. It is squat, 21x20 against the old
pick's 18x32, and `place()` normalises on height, so it comes out wide. Whether
that costs more than the missing bar buys is exactly what a reader can answer
and I cannot.

    arm  2
    A    Dollar 11              the round-1 baseline, carried forward unchanged
    E    cand other 2 col 3     the bottom-bar candidate

`5` is held at Years 24 in every arm from here: every `5` in the source is the
same letterform as the hand's `S` (`five_cands.png`), so no pick can fix
`5`->`S` and there is nothing to cross it against. `6` is held at Clock2 1,
the one clock-face repick that worked.

Same texts in every arm of a round, so the character census is identical arm to
arm and a per-glyph count is comparable across arms. Rounds 1 and 2 are
deliberately context-free -- a reader who can repair `$127.00` from knowing what
money looks like is not reading the glyphs -- which is also why their absolute
rates are far above the prose sheet's and must never be quoted against it. Only
compare within a round. Arm A is carried through every round for exactly that
reason: it is the fixed point the other arms are measured against.
"""
import json, os, random, shutil
from PIL import Image, ImageDraw, ImageFont
import paths as P

PICKS = P.data("picks.json")

# arm -> {char: [section, *address]}, addresses as picks.json spells them
ROUNDS = {
    1: {
        "A": {"2": ["man", "Dollar", 11], "5": ["man", "Years", 24]},
        "B": {"2": ["man", "Clock", 2],   "5": ["man", "Clock2", 2]},
        "C": {"2": ["man", "Dollar", 11], "5": ["man", "Clock2", 2]},
        "D": {"2": ["man", "Clock", 2],   "5": ["man", "Years", 24]},
    },
    2: {
        "A": {"2": ["man", "Dollar", 11],       "5": ["man", "Years", 24]},
        "E": {"2": ["cand", "other", "2", 3],   "5": ["man", "Years", 24]},
    },
    # Same two arms as round 2, prose contexts instead of digit soup. Round 2 said
    # the bottom-bar `2` wins 36/39 to 31/39; a 15-line prose read of the built
    # font then had it wrong 18/18, every instance read as `Z`. A sheet of nothing
    # but digits and a sheet of sentences are different tests, and the one that
    # decides what ships is the one that looks like text.
    3: {
        "A": {"2": ["man", "Dollar", 11],       "5": ["man", "Years", 24]},
        "E": {"2": ["cand", "other", "2", 3],   "5": ["man", "Years", 24]},
    },
}

TEXTS = {
    1: [
        "0123456789 Ss5 Zz2 Il1 O0o",
        "$127.00 in 2018 and 52 of 25",
        "kf7 zqp3 mb2 vth6 yjl8 rcn4 x5s",
        "5S2Z 25 55 22 S5 Z2 250 675",
    ],
    3: [
        "0123456789 and $127.00 in 2018",
        "I clock in at 7:25 and leave at 12:30",
        "Pack my box with 22 dozen liquor jugs",
        "Il1 O0o Ss5 Zz2 Xx Cc Vv Ww",
    ],
}
TEXTS[2] = TEXTS[1]

SECTIONS = ("cand", "man", "merge", "clip", "synth")


def apply_arm(spec, arm):
    """Put this arm's picks into a copy of the spec.

    A character has to be removed from every other section first: `resolve_picks`
    walks the sections in order and a later one silently wins, so leaving the old
    `man` entry in place while adding a `cand` one builds the arm you did not ask
    for.
    """
    spec = json.loads(json.dumps(spec))
    for ch, addr in arm.items():
        for s in SECTIONS:
            spec.get(s, {}).pop(ch, None)
        spec.setdefault(addr[0], {})[ch] = addr[1:]
    return spec


def variants(rnd):
    """Build one Regular per arm. picks.json is the build's only input, so the
    arm is applied by editing it in place and putting it back afterwards."""
    import build as B
    keep = P.load(PICKS)
    shutil.copy(PICKS, P.out("picks.json.ab.bak"))
    out = {}
    try:
        for arm, picks in ROUNDS[rnd].items():
            P.dump(apply_arm(keep, picks), PICKS, indent=1)
            path = f"VAR-{arm}.ttf"
            notes, path, nk, nlegacy, nat, shear = B.build("Regular", out_path=path)
            out[arm] = path
            print(f"arm {arm}: {path}  {len(notes)} glyphs  {nk} kern pairs  "
                  + "  ".join(f"{c}={a}" for c, a in picks.items()))
    finally:
        P.dump(keep, PICKS, indent=1)
    return out


def sheet(rnd, out=None, key=None, size=44, pad=60, seed=175):
    """One sheet, arms shuffled so the reader cannot track which font is which."""
    import render
    arms = list(ROUNDS[rnd])
    out = out or f"abtest{rnd}.png"
    key = key or f"abtest{rnd}_key.json"
    faces = {a: render.Face(P.out(f"VAR-{a}.ttf"), size) for a in arms}
    lines = [(a, t) for a in arms for t in TEXTS[rnd]]
    random.Random(seed).shuffle(lines)
    num = ImageFont.load_default()
    lh = int(size * 2.1)
    W = int(pad * 2 + 60 + max(faces[a].getlength(t) for a, t in lines))
    im = Image.new("RGB", (W, pad * 2 + lh * len(lines)), (255, 255, 255))
    d = ImageDraw.Draw(im)
    y = pad
    for i, (a, t) in enumerate(lines, 1):
        d.text((pad, y + size * 0.45), f"{i:02d}", font=num, fill=(150, 150, 150))
        faces[a].text(im, (pad + 60, y), t, (30, 40, 60))
        y += lh
    im.save(P.out(out))
    P.dump({f"{i:02d}": {"arm": a, "text": t} for i, (a, t) in enumerate(lines, 1)},
           P.out(key), indent=1)
    print(out, im.size, len(lines), "lines;", key, "written")


if __name__ == "__main__":
    import sys
    rnd = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    if "sheet" not in sys.argv:
        variants(rnd)
    sheet(rnd)

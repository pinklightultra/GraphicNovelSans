"""An RTF that proves the installed family works in a word processor.

RTF rather than COM automation on purpose: driving a running Word over COM can
wedge it, and a 200-page draft was open in it at the time. A file Word merely
*opens* cannot wedge a running instance or touch the document already in
it. RTF also needs no library, and its font table is explicit enough to prove the
point: the styles are asked for as `\\b` and `\\i` against one family name, so if
Word renders them it is doing RIBBI family linkage off the OS/2 and head flags
rather than being handed four unrelated fonts.

`\\kerning1` matters. Word's pair kerning is **off** by default, so a document
that does not ask for it is a picture of the unkerned font -- the same trap
Pillow set in `render.py`.
"""
import os

FAM = "BLUE175 Hand"
import paths as P

# (label, rtf prefix, text). The label is set in Calibri so it cannot be confused
# with the specimen it labels.
ROWS = [
    ("Regular",     r"\b0\i0", "The quick brown fox jumps over the lazy dog"),
    ("Bold",        r"\b\i0",  "The quick brown fox jumps over the lazy dog"),
    ("Italic",      r"\b0\i",  "The quick brown fox jumps over the lazy dog"),
    ("Bold Italic", r"\b\i",   "The quick brown fox jumps over the lazy dog"),
]

# Pairs the band-gap kerner actually moved, so the proof is visible rather than asserted.
KERN = "Wavy AVAST To Yo. rye f, P, ry we vy 7, 2."


def rtf():
    p = []
    a = p.append
    a(r"{\rtf1\ansi\ansicpg1252\deff0")
    a(r"{\fonttbl{\f0\fswiss Calibri;}{\f1\fnil " + FAM + r";}}")
    a(r"{\colortbl;\red30\green40\blue60;\red130\green130\blue130;}")
    a(r"\kerning1\viewkind4\uc1")

    # First paragraph is the font itself, so the ribbon's font box reads the
    # family name in a screenshot and the cursor lands ready to type in it.
    a(r"\pard\sa200\kerning1\f1\fs44\cf1 BLUE175 Hand, installed and typed here.\par")
    a(r"\pard\sa240\f0\fs20\cf2 Traced from the hand-lettering in BLUE175. "
      r"Click into any line below and type: this is the installed system font, "
      r"not a picture. Bold and italic come from the family, not from Word "
      r"faking a slant.\par")

    for label, style, text in ROWS:
        a(r"\pard\sa60\f0\fs18\cf2 " + label + r"\par")
        a(r"\pard\sa200\f1\fs36\cf1 " + style + " " + text + r"\b0\i0\par")

    a(r"\pard\sa60\f0\fs18\cf2 Digits, and the ones the source cannot fix "
      r"(5 reads as S, 8 as b, 1 as l)\par")
    a(r"\pard\sa200\f1\fs36\cf1 0123456789  $127.00 in 2018  11:15  25%\par")

    a(r"\pard\sa60\f0\fs18\cf2 Kerned pairs, 718 of them in Regular. "
      r"Word pair kerning is off by default; this document turns it on.\par")
    a(r"\pard\sa200\f1\fs36\cf1 " + KERN + r"\par")

    a(r"\pard\sa60\f0\fs18\cf2 Type here\par")
    a(r"\pard\sa200\f1\fs36\cf1 \par")
    a("}")
    return "\n".join(p)


if __name__ == "__main__":
    out = P.out("BLUE175-sample.rtf")
    with open(out, "w", encoding="ascii") as f:
        f.write(rtf())
    print(out, os.path.getsize(out), "bytes")

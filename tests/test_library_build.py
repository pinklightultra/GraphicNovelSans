import os
import numpy as np
from fontTools.ttLib import TTFont
from graphicnovelsans import ComicFont


def _make_letter_mask(letter: str, h: int = 40, w: int = 30) -> np.ndarray:
    """Generate a simple synthetic letter mask for unit testing."""
    m = np.zeros((h, w), dtype=bool)
    if letter in "HhNnIi1":
        m[:, 2:6] = True
        m[:, -6:-2] = True
        m[h // 2 - 2:h // 2 + 2, :] = True
    elif letter in "Oo0":
        m[2:-2, 2:-2] = True
        m[6:-6, 6:-6] = False
    elif letter in "Aa":
        m[2:, 2:6] = True
        m[2:, -6:-2] = True
        m[2:6, :] = True
        m[h // 2 - 2:h // 2 + 2, :] = True
    else:
        m[4:-4, 4:-4] = True
    return m


def test_comic_font_end_to_end_build(tmp_path):
    font = ComicFont(family_name="TestComicHand", designer="Test Cartoonist")

    # Add core sample letters
    test_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,!?'()$-"
    for ch in test_chars:
        # Intentionally skip 'q', ')', '"', ';' to test automatic synthesis
        if ch in ("q", ")", '"', ";"):
            continue
        mask = _make_letter_mask(ch)
        font.add_glyph(ch, mask)

    # Auto-synthesize missing
    synthesized = font.synthesize_missing()
    assert "q" in synthesized
    assert ")" in synthesized
    assert '"' in synthesized
    assert ";" in synthesized

    # Build all 4 styles
    out_dir = str(tmp_path / "fonts")
    res = font.build(output_dir=out_dir)

    assert os.path.exists(res["styles"]["Regular"]["ttf"])
    assert os.path.exists(res["styles"]["Regular"]["woff2"])
    assert os.path.exists(res["styles"]["Bold"]["ttf"])
    assert os.path.exists(res["styles"]["Italic"]["ttf"])
    assert os.path.exists(res["styles"]["Bold Italic"]["ttf"])

    # Verify OpenType table integrity for each style
    for style, sinfo in res["styles"].items():
        ttf = TTFont(sinfo["ttf"])
        assert ttf["name"].getDebugName(1) == "TestComicHand"
        assert ttf["name"].getDebugName(2) == style
        if sinfo["kern_pairs"] > 0:
            assert "GPOS" in ttf
        assert "kern" in ttf
        assert "glyf" in ttf
        assert "cmap" in ttf

        # Verify WOFF2
        woff2 = TTFont(sinfo["woff2"])
        assert woff2.flavor == "woff2"
        assert len(woff2.getGlyphOrder()) == len(ttf.getGlyphOrder())

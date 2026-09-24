import string

import pytest
from fontTools.ttLib import TTFont

from conftest import STYLES, shipped

CHARSET = set(string.ascii_letters + string.digits + " .,-:;?!'\"()$")
# style -> (fsSelection, macStyle, weight, italic angle, legacy kern pairs)
RIBBI = {
    "Regular":     (0x40, 0, 400, 0.0, 718),
    "Bold":        (0x20, 1, 700, 0.0, 639),
    "Italic":      (0x01, 2, 400, -11.0, 877),
    "Bold Italic": (0x21, 3, 700, -11.0, 730),
}


@pytest.mark.parametrize("style", STYLES)
def test_one_family_four_linked_styles(style):
    f = TTFont(shipped(style))
    assert f["name"].getDebugName(1) == "BLUE175 Hand"
    assert f["name"].getDebugName(2) == style
    sel, mac, weight, angle, _ = RIBBI[style]
    assert (f["OS/2"].fsSelection, f["head"].macStyle, f["OS/2"].usWeightClass,
            f["post"].italicAngle) == (sel, mac, weight, angle)


@pytest.mark.parametrize("style", STYLES)
def test_charset(style):
    assert {chr(c) for c in TTFont(shipped(style)).getBestCmap()} == CHARSET


@pytest.mark.parametrize("style", STYLES)
def test_kerning_is_in_both_tables(style):
    f = TTFont(shipped(style))
    legacy = f["kern"].kernTables[0].kernTable
    assert len(legacy) == RIBBI[style][4]
    gpos = f["GPOS"].table.LookupList.Lookup
    assert gpos and gpos[0].LookupType == 2          # pair adjustment


@pytest.mark.parametrize("style", STYLES)
def test_the_web_fonts_are_the_same_fonts(style):
    ttf, web = TTFont(shipped(style)), TTFont(shipped(style, "woff2"))
    assert web.flavor == "woff2"
    for t in ("glyf", "hmtx", "cmap", "GPOS", "kern", "name", "OS/2"):
        assert ttf[t].compile(ttf) == web[t].compile(web), t

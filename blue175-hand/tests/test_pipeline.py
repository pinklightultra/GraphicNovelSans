import os

import numpy as np
import pytest
from fontTools.ttLib import TTFont
from PIL import Image

import glyphlab as G
import kern as K
import paths
from conftest import STYLES, have_pages, shipped


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def test_band_kerning_tucks_a_T_and_leaves_flat_pairs_alone():
    T = K.profile([rect(0, 650, 500, 700), rect(225, 0, 275, 700)], 500, -220, 800)
    o = K.profile([rect(0, 0, 400, 437)], 400, -220, 800)
    n = K.profile([rect(40, 0, 360, 437)], 400, -220, 800)
    kerns = K.pairs({"T": T, "o": o, "n": n})
    assert kerns[("T", "o")] < 0
    assert ("n", "n") not in kerns                          # already in the dead band
    assert kerns[("o", "o")] > 0                            # ink that touches is pushed apart


def test_ink_is_the_red_channel():
    a = np.full((20, 30, 3), 255, np.uint8)
    a[5:15, 4:8] = (147, 190, 230)                          # the hand's light blue
    a[5:15, 20:24] = (147, 190, 230)
    mask = G.ink_mask(Image.fromarray(a))
    assert mask.sum() == 80
    labels, comps = G.components(mask)
    assert len(comps) == 2


def test_missing_pages_say_where_to_point(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "PAGES", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="BLUE175_PAGES"):
        G.load_page(1)


def test_a_run_reads_its_own_output_before_the_committed_copy(out):
    assert paths.font("BLUE175.ttf") == shipped("Regular")
    (out / "BLUE175.ttf").write_bytes(b"")
    assert paths.font("BLUE175.ttf") == str(out / "BLUE175.ttf")


@pytest.mark.skipif(not have_pages(), reason="set BLUE175_PAGES to the source pages")
@pytest.mark.parametrize("style", STYLES)
def test_a_rebuild_from_the_pages_is_the_shipped_font(style, out):
    import build
    _, path, *_ = build.build(style)
    made, ship = TTFont(str(out / path)), TTFont(shipped(style))
    for t in ship.reader.keys():
        if t != "head":                                     # created/modified dates
            assert made.reader[t] == ship.reader[t], t

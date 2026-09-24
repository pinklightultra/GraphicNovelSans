import numpy as np
from PIL import Image

import render
from conftest import shipped


def test_kerning_moves_what_it_should():
    on, off = render.Face(shipped("Regular"), 60), render.Face(shipped("Regular"), 60, kern=False)
    assert on.getlength("h2") < off.getlength("h2")        # the tightest pair in the table
    assert on.getlength("r y") == off.getlength("r y")      # nothing kerns across a space
    assert on.getlength("ry") > off.getlength("ry")         # ink that would touch is pushed


def test_text_lands_on_the_canvas_and_is_repeatable():
    face = render.Face(shipped("Bold"), 44)
    ims = []
    for _ in range(2):
        im = Image.new("RGB", (600, 120), (255, 255, 255))
        face.text(im, (10, 10), "The quick brown fox", (30, 40, 60))
        ims.append(np.asarray(im))
    assert (ims[0] < 255).any() and np.array_equal(*ims)

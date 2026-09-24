import numpy as np
from PIL import Image
from graphicnovelsans.ingest import extract_ink_mask, otsu_threshold


def test_black_on_white_extraction():
    img = Image.new("L", (100, 100), color=255)
    # Draw dark stroke
    a = np.asarray(img).copy()
    a[30:70, 40:60] = 20
    mask = extract_ink_mask(Image.fromarray(a), mode="black_on_white")
    assert mask.sum() == 40 * 20
    assert mask[50, 50] == True
    assert mask[10, 10] == False


def test_alpha_extraction():
    img = Image.new("RGBA", (100, 100), color=(0, 0, 0, 0))
    a = np.asarray(img).copy()
    a[20:50, 20:50] = (30, 40, 60, 255)
    mask = extract_ink_mask(Image.fromarray(a), mode="alpha")
    assert mask.sum() == 30 * 30
    assert mask[25, 25] == True
    assert mask[5, 5] == False


def test_blue_pencil_drop():
    # Non-photo blue stroke (high blue/green, low red) vs black ink stroke
    img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    a = np.asarray(img).copy()
    # Blue pencil sketch
    a[10:40, 10:40] = (160, 210, 255)
    # Dark black ink
    a[50:80, 50:80] = (30, 30, 30)

    mask = extract_ink_mask(Image.fromarray(a), mode="blue_pencil_drop")
    # Blue sketch is dropped, black ink is retained
    assert not mask[20, 20]
    assert mask[60, 60]

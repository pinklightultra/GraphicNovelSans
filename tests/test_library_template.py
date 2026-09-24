import os
from PIL import Image, ImageDraw
from graphicnovelsans import ComicFont
from graphicnovelsans.template import generate_lettering_sheet, extract_from_lettering_sheet


def test_template_generation_and_extraction(tmp_path):
    tpl_path = str(tmp_path / "test_template.png")
    generate_lettering_sheet(tpl_path, all_caps=True, width=1240, height=1754)
    assert os.path.exists(tpl_path)

    # Simulate an artist drawing letters into the template cells
    img = Image.open(tpl_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    # In cell for 'A' (col 0, row 0), draw dark ink
    margin_x = int(120 * 1240 / 2480)
    margin_top = int(280 * 1754 / 3508)
    margin_bottom = int(140 * 1754 / 3508)
    avail_w = 1240 - 2 * margin_x
    avail_h = 1754 - margin_top - margin_bottom
    cols = 13
    rows = 4
    cell_w = avail_w // cols
    cell_h = avail_h // rows

    # Draw dark black letter 'A' in cell (col 0, row 0)
    x0, y0 = margin_x, margin_top
    draw.rectangle([x0 + 20, y0 + 30, x0 + cell_w - 20, y0 + cell_h - 20], fill=(20, 20, 20))

    filled_path = str(tmp_path / "filled_template.png")
    img.save(filled_path)

    # Extract
    extracted = extract_from_lettering_sheet(filled_path, all_caps=True)
    assert "A" in extracted
    assert extracted["A"]["pixels"] > 50

    # Test via ComicFont
    font = ComicFont("TemplateComicHand")
    count = font.load_lettering_sheet(filled_path, all_caps=True)
    assert count >= 1
    assert "A" in font.glyphs

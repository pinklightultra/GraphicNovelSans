"""Lettering Sheet Harvest Example.

Demonstrates the primary comic artist workflow:
1. Generate an all-caps or full comic lettering template.
2. Simulate a cartoonist filling in the template with their hand-lettering.
3. Automatically extract, segment, and identify all glyphs from the drawing.
4. Auto-synthesize any missing characters.
5. Compile the complete 4-style linked family (Regular, Bold, Italic, Bold Italic).
"""
import os
from PIL import Image, ImageDraw, ImageFont
from graphicnovelsans import ComicFont
from graphicnovelsans.template import generate_lettering_sheet, extract_from_lettering_sheet


def run_demo():
    print("=== Comic Artist Workflow: Template Generation & Ingestion ===")

    # Step 1: Generate template
    template_path = "examples/lettering_template.png"
    print(f"\n1. Generating lettering sheet template -> {template_path}")
    generate_lettering_sheet(
        template_path,
        all_caps=True,
        title="BLUE175 Lettering Template",
        width=1240,
        height=1754
    )

    # Step 2: Simulate cartoonist's hand-lettered drawings into cells
    print("\n2. Artist drawing letters into cells...")
    sheet_im = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(sheet_im)

    try:
        artist_hand = ImageFont.truetype("DejaVuSans-Bold.ttf", 46)
    except OSError:
        artist_hand = ImageFont.load_default()

    # Layout dimensions
    margin_x = int(120 * 1240 / 2480)
    margin_top = int(280 * 1754 / 3508)
    margin_bottom = int(140 * 1754 / 3508)
    avail_w = 1240 - 2 * margin_x
    avail_h = 1754 - margin_top - margin_bottom
    cols = 13
    rows = 4
    cell_w = avail_w // cols
    cell_h = avail_h // rows

    all_caps_chars = [
        "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
        "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "!", "?", "$",
        ".", ",", ":", ";", "'", '"', "(", ")", "-", " ", " ", " ", " "
    ]

    for idx, ch in enumerate(all_caps_chars):
        if ch.strip() == "":
            continue
        r = idx // cols
        c = idx % cols
        x0 = margin_x + c * cell_w
        y0 = margin_top + r * cell_h

        # In dark ink, draw character with natural placement
        draw.text((x0 + 16, y0 + 18), ch, fill=(25, 30, 45), font=artist_hand)

    drawn_sheet_path = "examples/artist_filled_sheet.png"
    sheet_im.save(drawn_sheet_path)
    print(f"   Simulated drawn sheet saved -> {drawn_sheet_path}")

    # Step 3: Load into ComicFont and harvest
    print(f"\n3. Automatically extracting glyphs from sheet...")
    font = ComicFont(
        family_name="BLUE175 Studio",
        designer="Justin Severn",
        ink_mode="black_on_white"
    )
    count = font.load_lettering_sheet(drawn_sheet_path, all_caps=True, ink_mode="black_on_white")
    print(f"   Successfully harvested {count} characters!")

    # Step 4: Auto-synthesize missing lowercase and punctuation
    synthesized = font.synthesize_missing()
    if synthesized:
        print(f"\n4. Synthesized missing characters: {', '.join(synthesized)}")

    # Step 5: Build all 4 font styles
    out_dir = "examples/output_fonts"
    print(f"\n5. Compiling font family into {out_dir}...")
    res = font.build(output_dir=out_dir)

    print(f"\nCompleted {res['family']} build!")
    for st, info in res["styles"].items():
        print(f"  [{st:12}] TTF: {info['ttf']} | WOFF2: {info['woff2']} ({info['kern_pairs']} kern pairs)")


if __name__ == "__main__":
    run_demo()

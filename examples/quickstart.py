"""GraphicNovelSans Quickstart Example.

Demonstrates:
1. Generating a lettering template for an artist to draw into
2. Building a 4-style font family with automatic bold dilation,
   natural slant compensation for italic, missing glyph synthesis,
   and automated band-gap kerning.
"""
import os
import numpy as np
from PIL import Image
from graphicnovelsans import ComicFont

def main():
    print("=== GraphicNovelSans: Quickstart Comic Font Builder ===")

    # 1. Generate a Lettering Sheet Template
    template_path = "comic_lettering_sheet.png"
    print(f"\n1. Generating printable/digital lettering sheet -> {template_path}")
    ComicFont.create_template(
        output_path=template_path,
        all_caps=True,
        title="My Custom Comic Font Template"
    )
    print(f"   Created {template_path} (Open in Procreate, Clip Studio Paint, or print)")

    # 2. Initialize font project
    font = ComicFont(
        family_name="Kapow Sans",
        designer="Indie Comic Artist",
        version="1.0"
    )

    # 3. Simulate an artist drawing sample characters
    print("\n2. Simulating artist's hand-drawn lettering input...")
    from PIL import ImageDraw, ImageFont
    try:
        f = ImageFont.truetype("DejaVuSans-Bold.ttf", 44)
    except OSError:
        f = ImageFont.load_default()

    sample_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,!?'()$-"
    for ch in sample_chars:
        # Create an individual letter tile
        tile = Image.new("L", (80, 80), color=255)
        d = ImageDraw.Draw(tile)
        d.text((20, 15), ch, fill=0, font=f)
        font.add_glyph(ch, np.asarray(tile))

    # 4. Auto-synthesize any missing glyphs
    synthesized = font.synthesize_missing()
    if synthesized:
        print(f"3. Auto-synthesized missing characters: {', '.join(synthesized)}")

    # 5. Build full 4-style family (Regular, Bold, Italic, Bold Italic)
    out_dir = "./output_fonts"
    print(f"\n4. Compiling 4-style linked family into {out_dir}...")
    result = font.build(output_dir=out_dir)

    print(f"\nSuccessfully generated {result['family']}!")
    print(f"Natural hand slant detected: {result['natural_slant_degrees']:+.1f}°")
    for style, sinfo in result["styles"].items():
        print(f"  • {style:12} -> TTF: {sinfo['ttf']} ({sinfo['glyph_count']} glyphs, {sinfo['kern_pairs']} kern pairs)")

if __name__ == "__main__":
    main()

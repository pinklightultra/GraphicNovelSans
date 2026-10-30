"""Integration tests for full GraphicNovelSans pipeline."""
import pytest
import tempfile
import os
import numpy as np
from graphicnovelsans import ComicFont


def test_full_pipeline_template_to_build():
    """Test complete pipeline: template → extract → build."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Step 1: Generate template
        template_path = os.path.join(tmpdir, "template.png")
        ComicFont.create_template(template_path, all_caps=True)
        
        assert os.path.exists(template_path)
        
        # Step 2: Create a synthetic filled sheet (simulate hand-drawn)
        # In real use, this would be a scanned image
        from PIL import Image
        sheet = Image.new("RGB", (2480, 3508), (255, 255, 255))
        
        # Draw some "ink" in a few cells (simulating filled template)
        arr = np.array(sheet)
        
        # Draw "A" in first cell (approximate location)
        margin_x, margin_top = 120, 280
        cell_w, cell_h = (2480 - 240) // 13, (3508 - 280 - 140) // 4
        
        # Draw a simple "A" shape
        for y in range(margin_top + 50, margin_top + 200):
            for x in range(margin_x + 50, margin_x + 150):
                if abs(x - margin_x - 100) < 5 or abs(y - margin_top - 100) < 5:
                    arr[y, x] = [0, 0, 0]  # Black ink
        
        filled_path = os.path.join(tmpdir, "filled.png")
        Image.fromarray(arr).save(filled_path)
        
        # Step 3: Build font
        font = ComicFont("Test Hand", "Tester", ink_mode="black_on_white")
        count = font.load_lettering_sheet(filled_path, all_caps=True, ink_mode="black_on_white")
        
        # Should extract at least one character
        assert count > 0
        
        # Step 4: Build family
        output_dir = os.path.join(tmpdir, "fonts")
        result = font.build(output_dir, styles=["Regular"])
        
        assert "Test Hand" in result["family"]
        assert "Regular" in result["styles"]
        
        ttf_path = result["styles"]["Regular"]["ttf"]
        woff2_path = result["styles"]["Regular"]["woff2"]
        
        assert os.path.exists(ttf_path)
        assert os.path.exists(woff2_path)


def test_synthesis_then_build():
    """Test that synthesized glyphs can be used in font build."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create minimal glyphs manually
        font = ComicFont("Synth Test", "Tester")
        
        # Add only '(' and 'p'
        mask_paren = np.zeros((20, 20), dtype=bool)
        mask_paren[5:15, 5:8] = True  # Simple curve
        font.add_glyph("(", mask_paren)
        
        mask_p = np.zeros((20, 20), dtype=bool)
        mask_p[5:15, 5:8] = True
        mask_p[5:10, 8:12] = True  # Loop
        font.add_glyph("p", mask_p)
        
        # Synthesize missing ')' and 'q'
        synthesized = font.synthesize_missing()
        
        assert ")" in synthesized
        assert "q" in synthesized
        assert ")" in font.glyphs
        assert "q" in font.glyphs
        
        # Build should succeed with synthesized glyphs
        output_dir = os.path.join(tmpdir, "fonts")
        result = font.build(output_dir, styles=["Regular"])
        
        assert result["family"] == "Synth Test"


def test_all_caps_vs_mixed_layout():
    """Test that all_caps flag affects extraction correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Generate both templates
        caps_template = os.path.join(tmpdir, "caps.png")
        mixed_template = os.path.join(tmpdir, "mixed.png")
        
        ComicFont.create_template(caps_template, all_caps=True)
        ComicFont.create_template(mixed_template, all_caps=False)
        
        assert os.path.exists(caps_template)
        assert os.path.exists(mixed_template)
        
        # They should be different sizes/content
        from PIL import Image
        caps_img = Image.open(caps_template)
        mixed_img = Image.open(mixed_template)
        
        # Both should be same dimensions (same canvas size)
        assert caps_img.size == mixed_img.size

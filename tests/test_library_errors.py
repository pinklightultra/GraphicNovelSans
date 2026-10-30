"""Tests for error handling and validation in GraphicNovelSans."""
import pytest
import numpy as np
from graphicnovelsans import ComicFont
from graphicnovelsans.ingest import extract_ink_mask
from graphicnovelsans.builder import build_family


def test_invalid_ink_mode_raises_error():
    """Test that invalid ink_mode raises ValueError."""
    font = ComicFont(ink_mode="invalid_mode")
    with pytest.raises(ValueError, match="Invalid ink_mode"):
        # Try to add a glyph with invalid mode
        font.add_glyph("A", np.zeros((10, 10), dtype=bool), ink_mode="bad_mode")


def test_add_glyph_empty_char_raises_error():
    """Test that empty character string raises ValueError."""
    font = ComicFont()
    with pytest.raises(ValueError, match="Invalid character"):
        font.add_glyph("", np.zeros((10, 10), dtype=bool))


def test_add_glyph_multi_char_raises_error():
    """Test that multi-character string raises ValueError."""
    font = ComicFont()
    with pytest.raises(ValueError, match="Invalid character"):
        font.add_glyph("AB", np.zeros((10, 10), dtype=bool))


def test_build_no_glyphs_raises_error():
    """Test that building with no glyphs raises ValueError."""
    font = ComicFont()
    with pytest.raises(ValueError, match="no glyphs have been added"):
        font.build()


def test_build_invalid_style_raises_error():
    """Test that invalid style raises ValueError."""
    font = ComicFont()
    # Add a dummy glyph
    font.add_glyph("A", np.ones((10, 10), dtype=bool))
    
    with pytest.raises(ValueError, match="Invalid styles"):
        font.build(styles=["Regular", "InvalidStyle"])


def test_extract_ink_mask_invalid_mode():
    """Test that invalid mode in extract_ink_mask raises ValueError."""
    with pytest.raises(ValueError, match="Invalid ink extraction mode"):
        extract_ink_mask(np.zeros((10, 10)), mode="bad_mode")


def test_extract_ink_mask_invalid_threshold():
    """Test that invalid threshold raises ValueError."""
    with pytest.raises(ValueError, match="Threshold must be between"):
        extract_ink_mask(np.zeros((10, 10)), threshold=300)


def test_build_family_empty_glyphs():
    """Test that build_family with empty glyphs raises ValueError."""
    with pytest.raises(ValueError, match="glyphs dictionary is empty"):
        build_family({}, "Test Font", "./dist")


def test_build_family_invalid_style():
    """Test that build_family with invalid style raises ValueError."""
    glyphs = {"A": {"mask": np.ones((10, 10), dtype=bool)}}
    with pytest.raises(ValueError, match="Invalid styles"):
        build_family(glyphs, "Test Font", "./dist", styles=["BadStyle"])
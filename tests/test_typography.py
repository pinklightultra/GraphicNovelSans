"""Tests for typography module: metrics, placement, slant measurement."""
import pytest
import numpy as np
from graphicnovelsans.typography import (
    place_glyph, measure_natural_slant, char_to_glyph_name,
    UPM, X_HEIGHT, ASCENDER, DESCENDER, CAP_HEIGHT
)


def test_constants_defined():
    """Test that typography constants are reasonable."""
    assert UPM == 1000
    assert X_HEIGHT == 437
    assert ASCENDER == 800
    assert DESCENDER == -220
    assert CAP_HEIGHT == 700


def test_place_glyph_lowercase():
    """Test placement of lowercase letter."""
    mask = np.ones((50, 30), dtype=bool)  # 50px tall, 30px wide
    
    scale, offset = place_glyph("a", mask)
    
    # Scale should map x-height to font units
    expected_scale = (X_HEIGHT * 1.0) / 50.0
    assert abs(scale - expected_scale) < 0.01
    
    # Offset should place baseline correctly
    assert offset > 0


def test_place_glyph_capital():
    """Test placement of capital letter."""
    mask = np.ones((80, 50), dtype=bool)  # Taller than lowercase
    
    scale, offset = place_glyph("A", mask)
    
    # Capitals have height 1.55 x-heights
    expected_scale = (X_HEIGHT * 1.55) / 80.0
    assert abs(scale - expected_scale) < 0.01


def test_place_glyph_punctuation():
    """Test placement of punctuation."""
    mask = np.ones((20, 20), dtype=bool)
    
    scale, offset = place_glyph(".", mask)
    
    # Period has small height (0.18 x-heights)
    assert scale > 0
    assert offset > 0


def test_measure_natural_slant_vertical():
    """Test slant measurement on vertical stems."""
    # Vertical rectangle (no slant)
    contours = [[(0, 0), (10, 0), (10, 100), (0, 100)]]
    contours_by_char = {"I": contours}
    
    slant = measure_natural_slant(contours_by_char)
    
    assert abs(slant) < 0.01  # Nearly zero


def test_measure_natural_slant_forward():
    """Test slant measurement on forward-leaning stems."""
    # Forward-leaning rectangle with sufficient height (>300)
    contours = [[(0, 0), (10, 0), (40, 400), (30, 400)]]
    contours_by_char = {"I": contours}
    
    slant = measure_natural_slant(contours_by_char)
    
    # Should detect positive slant (dx/dy = 30/400 = 0.075)
    assert slant > 0
    assert abs(slant - 0.075) < 0.01


def test_measure_natural_slant_empty():
    """Test slant measurement with no contours."""
    slant = measure_natural_slant({})
    assert slant == 0.0


def test_char_to_glyph_name_standard():
    """Test glyph name mapping for standard characters."""
    assert char_to_glyph_name(".") == "period"
    assert char_to_glyph_name(",") == "comma"
    assert char_to_glyph_name("'") == "quotesingle"
    assert char_to_glyph_name('"') == "quotedbl"
    assert char_to_glyph_name("!") == "exclam"
    assert char_to_glyph_name("?") == "question"


def test_char_to_glyph_name_digit():
    """Test glyph name mapping for digits."""
    assert char_to_glyph_name("0") == "zero"
    assert char_to_glyph_name("5") == "five"
    assert char_to_glyph_name("9") == "nine"


def test_char_to_glyph_name_letter():
    """Test glyph name mapping for letters."""
    assert char_to_glyph_name("A") == "A"
    assert char_to_glyph_name("z") == "z"
    assert char_to_glyph_name(" ") == "space"
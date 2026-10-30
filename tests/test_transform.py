"""Tests for transform module: dilation, shear, counter protection."""
import pytest
import numpy as np
from graphicnovelsans.transform import (
    dilate_with_counter_protection, shear_contours, calculate_italic_shear,
    _circular_disc, _shift_mask, _grow_mask, _shrink_mask
)


def test_circular_disc_shape():
    """Test that circular disc has roughly circular shape."""
    disc = _circular_disc(3)
    
    assert len(disc) > 0
    # Check max extent is approximately radius
    max_dy = max(abs(dy) for dy, dx in disc)
    max_dx = max(abs(dx) for dy, dx in disc)
    assert max_dy == 3
    assert max_dx == 3


def test_shift_mask_positive():
    """Test shifting mask down and right."""
    mask = np.zeros((5, 5), dtype=bool)
    mask[1, 1] = True
    
    shifted = _shift_mask(mask, dy=2, dx=2)
    
    assert shifted[3, 3] == True
    assert shifted[1, 1] == False


def test_shift_mask_negative():
    """Test shifting mask up and left."""
    mask = np.zeros((5, 5), dtype=bool)
    mask[3, 3] = True
    
    shifted = _shift_mask(mask, dy=-2, dx=-2)
    
    assert shifted[1, 1] == True
    assert shifted[3, 3] == False


def test_grow_mask_expands():
    """Test that grow_mask expands the mask."""
    mask = np.zeros((10, 10), dtype=bool)
    mask[5, 5] = True
    
    grown = _grow_mask(mask, radius=2)
    
    # Center should still be True
    assert grown[5, 5] == True
    # Neighbors should be True
    assert grown[5, 7] == True
    assert grown[7, 5] == True


def test_shrink_mask_contracts():
    """Test that shrink_mask contracts the mask."""
    mask = np.zeros((10, 10), dtype=bool)
    mask[3:7, 3:7] = True  # 4x4 square
    
    shrunk = _shrink_mask(mask, radius=1)
    
    # Edges should be False
    assert shrunk[3, 3] == False
    assert shrunk[6, 6] == False
    # Center should still be True
    assert shrunk[4, 4] == True


def test_dilate_with_counter_protection_preserves_holes():
    """Test that dilate_with_counter_protection preserves internal holes."""
    # Create a ring (letter 'O' shape)
    mask = np.zeros((30, 30), dtype=bool)
    mask[5:25, 5:25] = True  # Outer square
    mask[10:20, 10:20] = False  # Inner hole
    
    dilated = dilate_with_counter_protection(mask, radius=2)
    
    # Hole should still exist (center should be False)
    assert not dilated[15, 15]  # Center of hole should still be False
    # Some hole area should remain
    hole_area = (~dilated[12:18, 12:18]).sum()
    assert hole_area > 0


def test_dilate_with_counter_protection_no_radius():
    """Test that radius=0 returns original mask."""
    mask = np.zeros((10, 10), dtype=bool)
    mask[5, 5] = True
    
    result = dilate_with_counter_protection(mask, radius=0)
    
    assert np.array_equal(result, mask)


def test_shear_contours_zero_shear():
    """Test that zero shear returns original contours."""
    contours = [[(0, 0), (10, 0), (10, 10), (0, 10)]]
    
    result = shear_contours(contours, shear=0.0)
    
    assert result == contours


def test_shear_contours_positive_shear():
    """Test positive shear (forward lean)."""
    contours = [[(0, 0), (10, 0), (10, 10), (0, 10)]]
    
    result = shear_contours(contours, shear=0.2)
    
    # Top points should shift right
    assert result[0][2][0] > 10  # (10, 10) -> (12, 10)
    assert result[0][3][0] > 0   # (0, 10) -> (2, 10)


def test_calculate_italic_shear_target_zero():
    """Test that target lean of 0 returns 0 shear."""
    shear = calculate_italic_shear(natural_slant=0.1, target_lean_degrees=0.0)
    assert shear == 0.0


def test_calculate_italic_shear_compensation():
    """Test shear calculation compensates for natural slant."""
    # Natural slant of 0.1 (~5.7° forward), target 11°
    shear = calculate_italic_shear(natural_slant=0.1, target_lean_degrees=11.0)
    
    # Should be positive (additional forward lean needed)
    assert shear > 0
    # tan(11°) ≈ 0.194, so shear ≈ 0.194 - 0.1 = 0.094
    assert 0.08 < shear < 0.11


def test_calculate_italic_shear_backhand():
    """Test shear calculation for backhand (negative natural slant)."""
    # Backhand of -0.1 (~5.7° backward), target 11°
    shear = calculate_italic_shear(natural_slant=-0.1, target_lean_degrees=11.0)
    
    # Should be larger positive to compensate
    assert shear > 0.19  # More than tan(11°) alone
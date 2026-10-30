"""Tests for segment module: connected components, noise filtering, line clustering."""
import pytest
import numpy as np
from graphicnovelsans.segment import (
    connected_components, tighten, drop_rules, filter_noise, group_lines
)


def test_connected_components_single_blob():
    """Test detection of a single connected component."""
    mask = np.zeros((10, 10), dtype=bool)
    mask[3:6, 3:6] = True  # 3x3 square
    
    labels, comps = connected_components(mask)
    
    assert len(comps) == 1
    assert comps[0]["pixels"] == 9
    assert comps[0]["x0"] == 3
    assert comps[0]["y0"] == 3
    assert comps[0]["x1"] == 6
    assert comps[0]["y1"] == 6


def test_connected_components_multiple_blobs():
    """Test detection of multiple disconnected components."""
    mask = np.zeros((10, 10), dtype=bool)
    mask[2:4, 2:4] = True   # Top-left blob
    mask[7:9, 7:9] = True   # Bottom-right blob
    
    labels, comps = connected_components(mask)
    
    assert len(comps) == 2
    assert comps[0]["pixels"] == 4
    assert comps[1]["pixels"] == 4


def test_connected_components_diagonal_touching():
    """Test that diagonal pixels are NOT connected (4-connectivity)."""
    mask = np.zeros((5, 5), dtype=bool)
    mask[2, 2] = True
    mask[3, 3] = True  # Diagonal
    
    labels, comps = connected_components(mask)
    
    # Should be 2 separate components in 4-connectivity
    assert len(comps) == 2


def test_tighten_empty_mask():
    """Test tighten on empty mask returns original."""
    mask = np.zeros((10, 10), dtype=bool)
    result = tighten(mask)
    assert np.array_equal(result, mask)


def test_tighten_crops_to_content():
    """Test that tighten crops tightly to content."""
    mask = np.zeros((20, 20), dtype=bool)
    mask[5:10, 8:12] = True  # Content in middle
    
    result = tighten(mask)
    
    assert result.shape == (5, 4)  # Tight crop
    assert result.all()  # All True in cropped region


def test_drop_rules_filters_large_components():
    """Test that drop_rules removes components spanning most of canvas."""
    width, height = 100, 100
    comps = [
        {"id": 1, "x0": 0, "y0": 0, "x1": 90, "y1": 10, "pixels": 900},  # Wide strip
        {"id": 2, "x0": 10, "y0": 10, "x1": 20, "y1": 20, "pixels": 100},  # Small
        {"id": 3, "x0": 0, "y0": 0, "x1": 10, "y1": 95, "pixels": 950},  # Tall strip
    ]
    
    filtered = drop_rules(comps, width, height, max_w_frac=0.55, max_h_frac=0.42)
    
    assert len(filtered) == 1
    assert filtered[0]["id"] == 2


def test_filter_noise_removes_small_dust():
    """Test that filter_noise removes tiny components."""
    comps = [
        {"id": 1, "x0": 0, "y0": 0, "x1": 2, "y1": 2, "pixels": 3},  # Dust
        {"id": 2, "x0": 10, "y0": 10, "x1": 15, "y1": 15, "pixels": 25},  # Valid
        {"id": 3, "x0": 20, "y0": 20, "x1": 21, "y1": 21, "pixels": 1},  # Tiny dust
    ]
    
    filtered = filter_noise(comps, min_pixels=5)
    
    assert len(filtered) == 1
    assert filtered[0]["id"] == 2


def test_group_lines_clusters_by_baseline():
    """Test that group_lines clusters components into text lines."""
    # Simulate two lines of text
    comps = [
        {"id": 1, "x0": 10, "y0": 10, "x1": 20, "y1": 30, "pixels": 100},  # Line 1
        {"id": 2, "x0": 25, "y0": 10, "x1": 35, "y1": 30, "pixels": 100},  # Line 1
        {"id": 3, "x0": 10, "y0": 50, "x1": 20, "y1": 70, "pixels": 100},  # Line 2
        {"id": 4, "x0": 25, "y0": 50, "x1": 35, "y1": 70, "pixels": 100},  # Line 2
    ]
    
    lines = group_lines(comps)
    
    assert len(lines) == 2
    assert len(lines[0]["items"]) == 2
    assert len(lines[1]["items"]) == 2
    
    # Check horizontal sorting
    assert lines[0]["items"][0]["x0"] < lines[0]["items"][1]["x0"]


def test_group_lines_empty_input():
    """Test group_lines with empty input."""
    lines = group_lines([])
    assert lines == []
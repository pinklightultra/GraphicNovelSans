"""Tests for trace module: contour tracing, simplification, Bézier fitting."""
import pytest
import numpy as np
from graphicnovelsans.trace import (
    rdp_simplify, trace_mask_to_contours, draw_contour_to_pen,
    _polygon_area, _point_inside_poly
)


def test_rdp_simplify_line():
    """Test RDP simplification on a straight line."""
    # 10 points on a line
    pts = [(i, i) for i in range(10)]
    
    simplified = rdp_simplify(pts, epsilon=1.0)
    
    # Should reduce to just endpoints
    assert len(simplified) == 2
    assert simplified[0] == (0, 0)
    assert simplified[-1] == (9, 9)


def test_rdp_simplify_curve():
    """Test RDP simplification preserves significant curve."""
    # Points forming a semi-circle
    import math
    pts = [(math.cos(theta), math.sin(theta)) for theta in np.linspace(0, math.pi, 20)]
    
    simplified = rdp_simplify(pts, epsilon=0.1)
    
    # Should keep some intermediate points
    assert len(simplified) > 2
    assert len(simplified) < 20


def test_polygon_area_square():
    """Test polygon area calculation."""
    # Square of side 10
    square = [(0, 0), (10, 0), (10, 10), (0, 10)]
    
    area = _polygon_area(square)
    
    assert abs(area - 100.0) < 0.01


def test_polygon_area_triangle():
    """Test polygon area for triangle."""
    triangle = [(0, 0), (10, 0), (5, 10)]
    
    area = _polygon_area(triangle)
    
    # Area = 0.5 * base * height = 50
    assert abs(area - 50.0) < 0.01


def test_point_inside_poly():
    """Test point-in-polygon detection."""
    square = [(0, 0), (10, 0), (10, 10), (0, 10)]
    
    assert _point_inside_poly((5, 5), square) == True
    assert _point_inside_poly((-1, 5), square) == False
    assert _point_inside_poly((11, 5), square) == False


def test_trace_mask_to_contours_simple():
    """Test contour tracing on a simple shape."""
    # 10x10 square
    mask = np.zeros((20, 20), dtype=bool)
    mask[5:15, 5:15] = True
    
    contours = trace_mask_to_contours(mask, scale=1.0, baseline_offset=10.0)
    
    assert len(contours) >= 1
    # Each contour should have at least 3 points
    for c in contours:
        assert len(c) >= 3


def test_trace_mask_to_contours_empty():
    """Test contour tracing on empty mask."""
    mask = np.zeros((10, 10), dtype=bool)
    
    contours = trace_mask_to_contours(mask, scale=1.0, baseline_offset=5.0)
    
    assert contours == []


def test_trace_mask_to_contours_hole():
    """Test contour tracing with a hole (ring shape)."""
    mask = np.zeros((30, 30), dtype=bool)
    mask[5:25, 5:25] = True  # Outer square
    mask[10:20, 10:20] = False  # Inner hole
    
    contours = trace_mask_to_contours(mask, scale=1.0, baseline_offset=15.0)
    
    # Should have outer and inner contours
    assert len(contours) >= 2


def test_draw_contour_to_pen_basic():
    """Test drawing contour to pen."""
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    
    pts = [(0, 0), (10, 0), (10, 10), (0, 10)]
    pen = TTGlyphPen(None)
    
    # Should not raise
    draw_contour_to_pen(pen, pts)
    
    glyph = pen.glyph()
    assert glyph is not None
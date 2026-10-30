# API Reference: Trace Module

Converts binary masks into vector contours using marching squares, polygon simplification, and quadratic Bézier fitting.

## Constants
| Name | Value | Description |
| :--- | :--- | :--- |
| `UPSCALE` | 4 | Supersampling factor before tracing |

## Functions

### `trace_mask_to_contours(mask, scale, baseline_offset, epsilon=1.7)`
Converts binary ink mask into font-unit vector contours with proper winding.
- **Parameters**:
  - `mask`: Boolean NumPy array.
  - `scale`: Font units per source pixel.
  - `baseline_offset`: Source pixels from top to baseline.
  - `epsilon`: RDP simplification tolerance.
- **Returns**: List of contour point lists in font coordinate system.

### `draw_contour_to_pen(pen, pts, corner_deg=52.0, short_edge=26.0)`
Emits contour to a FontTools pen as quadratic Béziers. Sharp corners stay on-curve; gentle turns become off-curve control points.
- **Parameters**:
  - `pen`: FontTools TTGlyphPen instance.
  - `pts`: Contour point list.
  - `corner_deg`: Angle threshold for sharp corners.
  - `short_edge`: Length threshold for detail preservation.
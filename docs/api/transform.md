# API Reference: Transform Module

Applies geometric transformations: bold dilation with counter protection and italic shear.

## Functions

### `dilate_with_counter_protection(mask, radius)`
Dilates ink mask while preserving internal counter holes (e.g., in 'e', 'o', 'B').
- **Parameters**:
  - `mask`: Boolean NumPy array.
  - `radius`: Dilation radius in pixels.
- **Returns**: Dilated boolean array with holes intact.

### `shear_contours(contours, shear)`
Applies horizontal shear: `(x + y * shear, y)`.
- **Parameters**:
  - `contours`: List of contour point lists.
  - `shear`: Shear factor (tan of angle).
- **Returns**: Transformed contours.

### `calculate_italic_shear(natural_slant, target_lean_degrees=11.0)`
Computes shear needed to reach target lean from natural handwriting slant.
- **Returns**: Shear factor (float).
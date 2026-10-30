# API Reference: Typography Module

Defines typographical metrics, character classes, baseline placement, and slant measurement.

## Constants
| Name | Value | Description |
| :--- | :--- | :--- |
| `UPM` | 1000 | Units per em |
| `X_HEIGHT` | 437 | x-height in font units |
| `ASCENDER` | 800 | Ascender height |
| `DESCENDER` | -220 | Descender depth |
| `CAP_HEIGHT` | 700 | Capital letter height |

## Functions

### `place_glyph(char, mask)`
Calculates scale and baseline offset for a glyph based on its character class.
- **Returns**: `(scale, baseline_offset)` tuple.

### `measure_natural_slant(contours_by_char, band_fraction=0.22, min_height=300.0)`
Measures the natural handwriting slant (dx/dy) from contour data.
- **Returns**: Slant factor (float).

### `char_to_glyph_name(char)`
Maps character to OpenType/TrueType glyph name (e.g., `"A"` → `"A"`, `"."` → `"period"`).
- **Returns**: String glyph name.
# API Reference: Kern Module

Implements 40-band edge profiling and band-gap kerning algorithms optimized for comic lettering spacing.

## Constants
| Name | Value | Meaning |
| :--- | :--- | :--- |
| `BANDS` | 40 | Horizontal slices from descender to ascender |
| `LIMIT` | 12 | Minimum kern adjustment to apply |
| `MAXNEG` | -300 | Maximum tuck (overlap) |
| `MAXPOS` | 150 | Maximum push apart |
| `TUCK` | 0.50 | Max tuck as fraction of advance |
| `MIN_TIGHT` | 52 | Closest allowed ink approach |
| `MAX_TIGHT` | 200 | Widest approach before visual hole |
| `AREA` | 62 | Target clear space on flanks |
| `FLANK_FLOOR` | 10 | Minimum sidebearing floor |

## Functions

### `compute_edge_profile(contours, advance, descender=-220, ascender=800, shift=0.0)`
Slices glyph into 40 horizontal bands, recording leftmost/rightmost ink per band.
- **Returns**: `{"bands": [...], "adv": float, "ink": int}`

### `compute_flanks(bands, descender=-220, ascender=800, zone=(0, 437), target_area=62, floor=10)`
Derives Left/Right Sidebearings (LSB, RSB) from silhouette.
- **Returns**: `(lsb, rsb)` tuple.

### `compute_kern_pairs(profiles, limit=12)`
Calculates optimal kerning adjustments for all ordered pairs.
- **Returns**: Dict mapping `(glyph_a, glyph_b)` → adjustment value.

### `generate_fea(kerns, path)`
Writes an OpenType Feature file for kern lookup.
- **Returns**: Path to generated `.fea` file.

### `create_legacy_kern_table(kerns, glyph_order, cap=10920)`
Builds a format-0 legacy binary `kern` table for older apps.
- **Returns**: `(table_object, pair_count)`
# API Reference: Builder Module

Compiles glyph collections into TrueType (`.ttf`) and WOFF2 (`.woff2`) font files with dual kerning tables (GPOS + legacy `kern`).

## Functions

### `build_style(style_name, glyphs, family_name, output_dir, designer="Comic Artist", version="1.0", natural_slant=None)`
Generates a single font style.

- **Parameters**:
  - `style_name`: One of `"Regular"`, `"Bold"`, `"Italic"`, `"Bold Italic"`.
  - `glyphs`: Dict of character → mask data.
  - `family_name`: Font family name.
  - `output_dir`: Destination folder.
  - `designer`: Author name for metadata.
  - `version`: Semantic version string.
  - `natural_slant`: Pre-measured handwriting slant (optional).
- **Returns**: Dictionary with file paths, glyph count, kern pair count, and shear applied.

### `build_family(glyphs, family_name, output_dir, designer="Comic Artist", version="1.0", styles=None)`
Generates all requested styles in one pass.

- **Parameters**: Same as `build_style`, plus `styles` (list of style names).
- **Returns**: Dictionary with family name, per-style results, and measured natural slant.

**Output Files**:
Each style produces:
- `{FamilyName}{Style}.ttf`
- `{FamilyName}{Style}.woff2`
- Temporary `.fea` file (deleted after compilation)
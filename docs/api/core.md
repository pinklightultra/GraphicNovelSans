# API Reference: Core Module

The `graphicnovelsans.core` module contains the main `ComicFont` class, which orchestrates the entire font generation pipeline.

## Class: `ComicFont`

Represents a font family being constructed.

### Constructor

```python
ComicFont(
    family_name: str = "Comic Hand",
    designer: str = "Comic Artist",
    version: str = "1.0",
    ink_mode: str = "auto"
)
```

- `family_name`: Font family name (used in metadata and filenames).
- `designer`: Author credit.
- `version`: Semantic version string.
- `ink_mode`: Default ink extraction mode (`auto`, `black_on_white`, `alpha`, `blue_pencil_drop`, `red_channel`).

### Methods

#### `add_glyph(char, image_or_mask, ink_mode=None)`

Adds a single character drawing. Accepts a path, PIL Image, or boolean mask. Raises `ValueError` if no ink is detected.

#### `load_lettering_sheet(sheet_path, all_caps=False, ink_mode="blue_pencil_drop")`

Extracts all characters from a filled template. Returns the count of extracted glyphs.

#### `synthesize_missing()`

Auto-generates missing glyphs from existing ones. Returns a list of newly synthesized characters.

#### `build(output_dir="./dist", styles=None, auto_synthesize=True)`

Compiles the font family. Returns a dict with `family`, `styles` (per-style paths and glyph/kern counts), and `natural_slant`.

#### Static: `create_template(output_path, all_caps=False, title="...")`

Generates a printable lettering sheet. Returns the absolute path to the saved image.

### Example

```python
from graphicnovelsans import ComicFont

font = ComicFont("My Hand", "Alice", ink_mode="blue_pencil_drop")
count = font.load_lettering_sheet("sheet.png")
print(f"Loaded {count} glyphs")
synth = font.synthesize_missing()
if synth:
    print(f"Synthesized: {synth}")
result = font.build("./fonts")
print(result)
```
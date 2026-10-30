# API Reference: Template Module

Generates printable/digital lettering sheets and extracts glyphs from filled templates.

## Functions

### `generate_lettering_sheet(output_path, all_caps=False, title="GraphicNovelSans Lettering Template", width=2480, height=3508)`
Creates a high-resolution lettering canvas with light blue guide text that gets filtered during extraction.
- **Parameters**:
  - `output_path`: Destination file path.
  - `all_caps`: If `True`, generate uppercase-only layout.
  - `title`: Header text.
  - `width`, `height`: Canvas size in pixels.
- **Returns**: Absolute path to saved image.

### `extract_from_lettering_sheet(sheet_image, all_caps=False, ink_mode="blue_pencil_drop")`
Automatically segments and identifies characters from a filled template.
- **Parameters**:
  - `sheet_image`: Path or PIL Image.
  - `all_caps`: Match the template layout used.
  - `ink_mode`: Extraction strategy (see `ingest.extract_ink_mask`).
- **Returns**: Dict mapping character → glyph data (`{"char": "...", "mask": ..., ...}`).
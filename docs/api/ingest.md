# API Reference: Ingest Module

The `graphicnovelsans.ingest` module handles image loading and ink mask extraction, supporting diverse artist workflows from digital transparent layers to blue-pencil sketches.

## Functions

### `load_image(source)`
Loads an image from various sources.

- **Parameters**:
  - `source`: Path (str), PIL Image object, or NumPy array.
- **Returns**: PIL Image object.
- **Raises**: `FileNotFoundError` if path doesn't exist; `TypeError` for unsupported types.

### `extract_ink_mask(image, mode="auto", threshold=None, invert=False)`
Extracts a boolean mask where `True` indicates ink.

- **Parameters**:
  - `image`: Path, PIL Image, or NumPy array.
  - `mode`: Extraction strategy:
    - `auto`: Detects transparency or defaults to black-on-white.
    - `black_on_white`: Standard dark ink on light paper.
    - `alpha`: Uses alpha channel for digital inks.
    - `blue_pencil_drop`: Filters non-photo blue sketch lines.
    - `red_channel`: Isolates red-channel ink (BLUE175 style).
    - `white_on_black`: Light ink on dark background.
  - `threshold`: Optional custom threshold (0–255).
  - `invert`: If `True`, inverts the mask.
- **Returns**: Boolean NumPy array (height × width).

### `otsu_threshold(gray)`
Computes Otsu's optimal binarization threshold for grayscale arrays.
- **Parameters**: `gray` — 2D NumPy array.
- **Returns**: Integer threshold (0–255).
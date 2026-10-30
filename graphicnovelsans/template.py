"""Lettering sheet template generation and automated character extraction.

This module enables a seamless workflow for comic artists:
1. **Template Generation**: Creates a printable/digital lettering sheet with
   light-blue guide characters that are automatically filtered during extraction.
2. **Automated Extraction**: Parses filled sheets and maps each cell to its
   corresponding character without manual tagging.

Key Features:
- Non-photo blue guide lines (filtered by `blue_pencil_drop` mode).
- Registration markers for alignment.
- Baseline and x-height indicators in each cell.
- Support for both full alphabet and all-caps layouts.
"""
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .ingest import load_image, extract_ink_mask
from .segment import tighten

#: Characters to include in a full alphabet template (6 rows × 13 columns).
ESSENTIAL_CHARS = [
    # Row 1: Uppercase A-M
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
    # Row 2: Uppercase N-Z
    "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
    # Row 3: Lowercase a-m
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
    # Row 4: Lowercase n-z
    "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
    # Row 5: Digits 0-9 & Punctuation
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "!", "?", "$",
    # Row 6: Remaining Punctuation
    ".", ",", ":", ";", "'", '"', "(", ")", "-", " ", " ", " ", " "
]

ALL_CAPS_CHARS = [
    # Row 1: A-M
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
    # Row 2: N-Z
    "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
    # Row 3: 0-9 & Core Punctuation
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "!", "?", "$",
    # Row 4: Punctuation
    ".", ",", ":", ";", "'", '"', "(", ")", "-", " ", " ", " ", " "
]


def generate_lettering_sheet(
    output_path: str,
    all_caps: bool = False,
    title: str = "GraphicNovelSans Lettering Template",
    width: int = 2480,
    height: int = 3508
) -> str:
    """Generate a high-resolution printable or digital lettering template.

    Creates a blank canvas with light-blue guide characters, baseline markers,
    and registration corners. The template is designed to be filled by hand
    (paper + pen) or digitally (Procreate, Clip Studio Paint, Photoshop).

    Args:
        output_path: Destination file path (PNG recommended).
        all_caps: If True, generate uppercase-only layout (4 rows).
        title: Header text displayed at the top of the sheet.
        width: Canvas width in pixels (default: 2480 ≈ A4 at 300 DPI).
        height: Canvas height in pixels (default: 3508 ≈ A4 at 300 DPI).

    Returns:
        Absolute path to the saved image file.

    Example:
        >>> path = generate_lettering_sheet("my_sheet.png", all_caps=False)
        >>> print(f"Template saved to {path}")
        Template saved to /home/user/my_sheet.png
    """
    chars = ALL_CAPS_CHARS if all_caps else ESSENTIAL_CHARS
    cols = 13
    rows = (len(chars) + cols - 1) // cols

    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 48)
        font_guide = ImageFont.truetype("DejaVuSans.ttf", 72)
        font_label = ImageFont.truetype("DejaVuSans.ttf", 26)
    except OSError:
        font_title = font_guide = font_label = ImageFont.load_default()

    margin_x = 120
    margin_top = 280
    margin_bottom = 140
    avail_w = width - 2 * margin_x
    avail_h = height - margin_top - margin_bottom

    cell_w = avail_w // cols
    cell_h = avail_h // rows

    # Header
    draw.text((margin_x, 90), title, fill=(40, 40, 60), font=font_title)
    sub = "Draw each character in its cell using dark ink. Light blue guides will be ignored."
    draw.text((margin_x, 170), sub, fill=(110, 110, 130), font=font_label)

    # 4 Corner registration markers (for auto alignment)
    marker_size = 40
    for cx, cy in [(40, 40), (width - 40 - marker_size, 40),
                   (40, height - 40 - marker_size),
                   (width - 40 - marker_size, height - 40 - marker_size)]:
        draw.rectangle([cx, cy, cx + marker_size, cy + marker_size], fill=(0, 0, 0))

    guide_color = (195, 220, 255)       # Non-photo blue prompt
    line_color = (210, 230, 255)        # Light grid
    baseline_color = (180, 205, 250)    # Baseline indicator

    for idx, ch in enumerate(chars):
        if ch.strip() == "":
            continue
        r = idx // cols
        c = idx % cols
        x0 = margin_x + c * cell_w
        y0 = margin_top + r * cell_h
        x1 = x0 + cell_w
        y1 = y0 + cell_h

        # Cell border
        draw.rectangle([x0, y0, x1, y1], outline=line_color, width=2)

        # Baseline (72% down cell) & x-height (48% down cell)
        base_y = int(y0 + 0.72 * cell_h)
        xh_y = int(y0 + 0.48 * cell_h)
        draw.line([(x0 + 8, base_y), (x1 - 8, base_y)], fill=baseline_color, width=2)
        draw.line([(x0 + 8, xh_y), (x1 - 8, xh_y)], fill=line_color, width=1)

        # Small label in corner
        draw.text((x0 + 8, y0 + 6), ch, fill=(160, 170, 190), font=font_label)

        # Centered faint prompt letter
        draw.text((x0 + cell_w // 2 - 20, y0 + cell_h // 2 - 40), ch, fill=guide_color, font=font_guide)

    img.save(output_path)
    return output_path


def extract_from_lettering_sheet(
    sheet_image: Any,
    all_caps: bool = False,
    ink_mode: str = "blue_pencil_drop"
) -> Dict[str, Dict[str, Any]]:
    """Extract glyphs from a filled lettering sheet.

    Automatically segments the image into individual character cells, extracts
    the ink mask, and returns a dictionary ready for font building. Light-blue
    guide characters are filtered out by the `ink_mode`.

    Args:
        sheet_image: Path to the filled sheet image or a PIL Image object.
        all_caps: Must match the template layout used (True for all-caps sheets).
        ink_mode: Extraction strategy (default: `blue_pencil_drop`).

    Returns:
        Dictionary mapping character strings to glyph data:
        `{char: {"char": char, "mask": bool_array, "synthetic": False, ...}}`

    Raises:
        ValueError: If the image cannot be loaded or no ink is found.

    Example:
        >>> glyphs = extract_from_lettering_sheet("filled_sheet.png")
        >>> len(glyphs)
        52  # All letters extracted
        >>> "A" in glyphs
        True
    """
    img = load_image(sheet_image).convert("RGB")
    width, height = img.size

    # Extract ink mask (drops light blue guidelines)
    mask = extract_ink_mask(img, mode=ink_mode)

    chars = ALL_CAPS_CHARS if all_caps else ESSENTIAL_CHARS
    cols = 13
    rows = (len(chars) + cols - 1) // cols

    margin_x = int(120 * width / 2480)
    margin_top = int(280 * height / 3508)
    margin_bottom = int(140 * height / 3508)

    avail_w = width - 2 * margin_x
    avail_h = height - margin_top - margin_bottom

    cell_w = avail_w // cols
    cell_h = avail_h // rows

    extracted = {}

    for idx, ch in enumerate(chars):
        if ch.strip() == "":
            continue
        r = idx // cols
        c = idx % cols
        x0 = margin_x + c * cell_w
        y0 = margin_top + r * cell_h
        x1 = x0 + cell_w
        y1 = y0 + cell_h

        # Inset slightly inside cell to avoid cell border
        inset_x = int(0.08 * cell_w)
        inset_y = int(0.08 * cell_h)
        sub_mask = mask[y0 + inset_y:y1 - inset_y, x0 + inset_x:x1 - inset_x]

        # Filter out corner label by zeroing top-left 25% if needed
        # Or take largest connected component inside the cell
        tight_mask = tighten(sub_mask)
        if tight_mask.sum() >= 15:
            extracted[ch] = {
                "char": ch,
                "mask": tight_mask,
                "synthetic": False,
                "pixels": int(tight_mask.sum())
            }

    return extracted

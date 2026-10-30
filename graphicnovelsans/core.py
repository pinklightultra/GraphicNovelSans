"""Main ComicFont class orchestrator.

This module provides the high-level `ComicFont` class, which serves as the
primary entry point for users. It abstracts away the complexity of image
processing, glyph synthesis, and font compilation into a simple, intuitive API.

Workflow:
    1. Instantiate `ComicFont` with metadata.
    2. Load glyphs via `load_lettering_sheet()` or `add_glyph()`.
    3. Optionally call `synthesize_missing()` for rare characters.
    4. Call `build()` to generate the font family.
"""
import os
from typing import Dict, List, Tuple, Any, Optional, Union
import numpy as np
from PIL import Image

from .ingest import load_image, extract_ink_mask
from .segment import tighten
from .synthesis import synthesize_missing_glyphs
from .builder import build_family, build_style
from .template import generate_lettering_sheet, extract_from_lettering_sheet


class ComicFont:
    """High-level orchestrator for comic font generation.

    This is the main public API. It allows artists to transform hand-drawn
    lettering into a professional 4-style font family (Regular, Bold, Italic,
    Bold Italic) with automatic kerning and glyph synthesis.

    Attributes:
        family_name: Font family name (used in metadata and filenames).
        designer: Author credit for the font.
        version: Semantic version string.
        ink_mode: Default ink extraction mode.
        glyphs: Internal dictionary of extracted glyphs.

    Example:
        >>> from graphicnovelsans import ComicFont
        >>> font = ComicFont("My Hand", "Alice", ink_mode="blue_pencil_drop")
        >>> count = font.load_lettering_sheet("sheet.png")
        >>> print(f"Loaded {count} glyphs")
        Loaded 52
        >>> synthesized = font.synthesize_missing()
        >>> print(f"Synthesized: {synthesized}")
        Synthesized: [')', 'q', 'z']
        >>> result = font.build("./fonts")
        >>> print(result['family'])
        My Hand
    """

    def __init__(
        self,
        family_name: str = "Comic Hand",
        designer: str = "Comic Artist",
        version: str = "1.0",
        ink_mode: str = "auto"
    ):
        self.family_name = family_name
        self.designer = designer
        self.version = version
        self.ink_mode = ink_mode
        self.glyphs: Dict[str, Dict[str, Any]] = {}

    def add_glyph(
        self,
        char: str,
        image_or_mask: Union[str, Image.Image, np.ndarray],
        ink_mode: Optional[str] = None
    ) -> None:
        """Add a single character drawing to the font.

        Extracts an ink mask from the provided image, tightens it to the
        bounding box, and stores it in the glyph collection.

        Args:
            char: Single character string (e.g., "A", "a", "!", ".").
            image_or_mask: Path to image file, PIL Image, numpy array, or
                           pre-extracted boolean mask.
            ink_mode: Override the default ink extraction mode for this glyph.

        Raises:
            ValueError: If `char` is empty, multiple characters, or no ink is detected.
            FileNotFoundError: If `image_or_mask` is a non-existent path.
            TypeError: If `image_or_mask` is of an unsupported type.

        Example:
            >>> font.add_glyph("A", "letter_A.png")
            >>> font.add_glyph("!", mask_array)
        """
        # Validate character input
        if not char or len(char) > 1:
            raise ValueError(f"Invalid character: {char!r}. Expected a single character string.")

        # Validate ink_mode if overridden
        if ink_mode is not None:
            valid_modes = ["auto", "black_on_white", "alpha", "blue_pencil_drop", "red_channel", "white_on_black"]
            if ink_mode not in valid_modes:
                raise ValueError(f"Invalid ink_mode: {ink_mode!r}. Valid options: {valid_modes}")

        mode = ink_mode or self.ink_mode
        if isinstance(image_or_mask, np.ndarray) and image_or_mask.dtype == bool:
            mask = image_or_mask
        else:
            mask = extract_ink_mask(image_or_mask, mode=mode)

        tight_mask = tighten(mask)
        if not tight_mask.any():
            raise ValueError(f"No ink found for character {char!r}. Check contrast and ink mode.")

        self.glyphs[char] = {
            "char": char,
            "mask": tight_mask,
            "synthetic": False,
            "pixels": int(tight_mask.sum())
        }

    def load_lettering_sheet(
        self,
        sheet_path: Union[str, Image.Image],
        all_caps: bool = False,
        ink_mode: str = "blue_pencil_drop"
    ) -> int:
        """Extract all characters from a filled lettering template sheet.

        Automatically segments the image into individual character cells,
        extracts ink masks, and populates the glyph collection.

        Args:
            sheet_path: Path to the filled sheet image or a PIL Image object.
            all_caps: Must match the template layout used.
            ink_mode: Ink extraction strategy (default: `blue_pencil_drop`).

        Returns:
            Number of characters successfully extracted.

        Raises:
            ValueError: If no characters are found in the sheet, or if `ink_mode` is invalid.
            FileNotFoundError: If `sheet_path` does not exist.

        Example:
            >>> font = ComicFont()
            >>> count = font.load_lettering_sheet("filled_sheet.png")
            >>> print(f"Extracted {count} glyphs")
            Extracted 52
        """
        # Validate ink_mode
        valid_modes = ["auto", "black_on_white", "alpha", "blue_pencil_drop", "red_channel"]
        if ink_mode not in valid_modes:
            raise ValueError(f"Invalid ink_mode: {ink_mode!r}. Valid options: {valid_modes}")

        extracted = extract_from_lettering_sheet(sheet_path, all_caps=all_caps, ink_mode=ink_mode)
        
        if not extracted:
            raise ValueError("No characters were extracted from the sheet. "
                           "Check that the image has high contrast, the ink mode is correct, "
                           "and characters are drawn within the guide boxes.")
        
        self.glyphs.update(extracted)
        return len(extracted)

    def synthesize_missing(self) -> List[str]:
        """Automatically synthesize missing characters from existing glyphs.

        Applies heuristic rules to generate rare or omitted characters:
        - Mirroring: `)` from `(`, `q` from `p`.
        - Case copying: `z` from `Z`, etc.
        - Stacking: `;` from `.` + `,`.

        Modifies `self.glyphs` in-place and returns the list of new characters.

        Returns:
            Sorted list of newly synthesized character strings.

        Example:
            >>> font = ComicFont()
            >>> font.load_lettering_sheet("partial_sheet.png")  # Missing q, ), ;
            >>> synthesized = font.synthesize_missing()
            >>> print(synthesized)
            [')', ';', 'q']
        """
        before = set(self.glyphs.keys())
        self.glyphs = synthesize_missing_glyphs(self.glyphs)
        after = set(self.glyphs.keys())
        return sorted(list(after - before))

    def build(
        self,
        output_dir: str = "./dist",
        styles: Optional[List[str]] = None,
        auto_synthesize: bool = True
    ) -> Dict[str, Any]:
        """Build a complete 4-style font family (TTF + WOFF2).

        Orchestrates the full pipeline:
        1. Synthesizes missing glyphs (if enabled).
        2. Vectorizes all glyphs.
        3. Computes sidebearings and kerning pairs.
        4. Generates Regular, Bold, Italic, and Bold Italic styles.
        5. Outputs both `.ttf` and `.woff2` files.

        Args:
            output_dir: Destination directory (created if it doesn't exist).
            styles: List of styles to generate. Default: all 4 RIBBI styles.
            auto_synthesize: Whether to synthesize missing glyphs first.

        Returns:
            Dictionary with keys:
            - `family`: Font family name.
            - `styles`: Dict of style name → file paths and metrics.
            - `output_dir`: Output directory path.
            - `natural_slant_degrees`: Measured handwriting slant.

        Raises:
            ValueError: If no glyphs have been added, or if an invalid style is requested.
            PermissionError: If the output directory is not writable.

        Example:
            >>> font = ComicFont("My Hand", "Alice")
            >>> font.load_lettering_sheet("sheet.png")
            >>> result = font.build("./fonts", styles=["Regular", "Bold"])
            >>> print(result['styles']['Regular']['ttf'])
            ./fonts/MyHandRegular.ttf
        """
        if not self.glyphs:
            raise ValueError("Cannot build font: no glyphs have been added. "
                           "Call load_lettering_sheet() or add_glyph() first.")

        # Validate styles
        valid_styles = ["Regular", "Bold", "Italic", "Bold Italic"]
        if styles is not None:
            invalid = [s for s in styles if s not in valid_styles]
            if invalid:
                raise ValueError(f"Invalid styles: {invalid}. Valid options: {valid_styles}")

        if auto_synthesize:
            self.synthesize_missing()

        return build_family(
            glyphs=self.glyphs,
            family_name=self.family_name,
            output_dir=output_dir,
            designer=self.designer,
            version=self.version,
            styles=styles
        )

    @staticmethod
    def create_template(
        output_path: str = "lettering_template.png",
        all_caps: bool = False,
        title: str = "GraphicNovelSans Lettering Template"
    ) -> str:
        """Generate a high-resolution printable or digital lettering template.

        Convenience static method that delegates to `generate_lettering_sheet()`.

        Args:
            output_path: Destination file path.
            all_caps: Generate uppercase-only layout.
            title: Header text for the template.

        Returns:
            Absolute path to the saved template image.

        Example:
            >>> template_path = ComicFont.create_template("my_template.png")
            >>> print(f"Print {template_path} and start lettering!")
        """
        return generate_lettering_sheet(output_path, all_caps=all_caps, title=title)

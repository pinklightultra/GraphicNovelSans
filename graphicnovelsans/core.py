"""Main ComicFont class orchestrator."""
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
    """High-level Comic Font Generator.

    Allows comic artists, illustrators, and letterers to turn handwriting
    drawings into a complete 4-style TrueType / WOFF2 font family with
    automatic bold dilation, slant-calibrated italic, and band-gap kerning.
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
        """Add a single character's ink drawing to the font."""
        mode = ink_mode or self.ink_mode
        if isinstance(image_or_mask, np.ndarray) and image_or_mask.dtype == bool:
            mask = image_or_mask
        else:
            mask = extract_ink_mask(image_or_mask, mode=mode)

        tight_mask = tighten(mask)
        if not tight_mask.any():
            raise ValueError(f"No ink found for character {char!r}")

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

        Returns:
            Count of successfully extracted characters.
        """
        extracted = extract_from_lettering_sheet(sheet_path, all_caps=all_caps, ink_mode=ink_mode)
        self.glyphs.update(extracted)
        return len(extracted)

    def synthesize_missing(self) -> List[str]:
        """Automatically synthesize missing characters (q from p, ) from (, etc.).

        Returns:
            List of newly synthesized character strings.
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
        """Build desktop TrueType and web WOFF2 fonts with dual kerning tables.

        Args:
            output_dir: Directory where fonts will be saved.
            styles: Styles to generate (default: Regular, Bold, Italic, Bold Italic).
            auto_synthesize: If True, automatically synthesizes missing glyphs before building.

        Returns:
            Dictionary with build metadata and output file paths.
        """
        if not self.glyphs:
            raise ValueError("Cannot build font: no glyphs have been added.")

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
        """Generate a high-resolution printable / digital lettering sheet."""
        return generate_lettering_sheet(output_path, all_caps=all_caps, title=title)

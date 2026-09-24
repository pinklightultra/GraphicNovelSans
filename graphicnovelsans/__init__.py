"""GraphicNovelSans — Comic font creation library for cartoonists and illustrators."""

from .core import ComicFont
from .ingest import extract_ink_mask, load_image
from .template import generate_lettering_sheet, extract_from_lettering_sheet
from .synthesis import synthesize_missing_glyphs

__version__ = "1.0.0"
__all__ = [
    "ComicFont",
    "extract_ink_mask",
    "load_image",
    "generate_lettering_sheet",
    "extract_from_lettering_sheet",
    "synthesize_missing_glyphs",
]

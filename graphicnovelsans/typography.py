"""Typographical metrics, character classification, baseline placement, and slant measurement."""
import math
import string
from typing import Dict, Tuple, List
import numpy as np

# Standard typographical units
UPM = 1000
X_HEIGHT = 437       # Matches typical hand-lettering x-height to cap ratio (~0.62)
ASCENDER = 800
DESCENDER = -220
CAP_HEIGHT = 700

# Typographical placement classes: (height_in_xheights, depth_below_baseline_in_xheights)
CLASS: Dict[str, Tuple[float, float]] = {
    "t": (1.32, 0.0),
    "i": (1.40, 0.0),
    "j": (1.85, 0.55),
    "Q": (1.55, 0.16),
    ".": (0.18, 0.0),
    ",": (0.38, 0.20),
    ":": (0.74, 0.0),
    ";": (0.92, 0.18),
    "'": (0.34, -1.06),
    '"': (0.34, -1.06),
    "-": (0.10, -0.42),
    "!": (1.45, 0.0),
    "?": (1.50, 0.0),
    "(": (1.80, 0.26),
    ")": (1.80, 0.26),
    "$": (1.80, 0.12),
}

# Standard lowercase without ascender or descender
for _c in "acemnorsuvwxz":
    CLASS[_c] = (1.00, 0.0)

# Lowercase ascenders
for _c in "bdfhkl":
    CLASS[_c] = (1.55, 0.0)

# Lowercase descenders
for _c in "gpqy":
    CLASS[_c] = (1.74, 0.52)

# Uppercase and digits
for _c in string.ascii_uppercase + string.digits:
    CLASS.setdefault(_c, (1.55, 0.0))


def place_glyph(char: str, mask: np.ndarray) -> Tuple[float, float]:
    """Calculate scale and baseline offset for a glyph based on its character class.

    This ensures natural hand jitter doesn't ruin the line: letters sit flat on
    the baseline with consistent proportions across words.

    Returns:
        scale: Font units per source pixel.
        baseline_offset: Source pixels from the glyph top edge down to the baseline.
    """
    h_class, depth_class = CLASS.get(char, (1.30, 0.0))
    pixel_height = max(mask.shape[0], 1)
    scale = (X_HEIGHT * h_class) / float(pixel_height)
    baseline_offset = pixel_height * (h_class - depth_class) / h_class
    return scale, baseline_offset


def measure_natural_slant(
    contours_by_char: Dict[str, List[List[Tuple[float, float]]]],
    band_fraction: float = 0.22,
    min_height: float = 300.0
) -> float:
    """Measure the natural handwriting slant as dx/dy.

    Many cartoonists naturally write with a backhand (leaning left).
    Measuring the actual stem angle allows us to compensate accurately
    so that generated italics lean with intentional, readable forward poise.
    """
    slants = []
    for ch, contours in contours_by_char.items():
        # Densify contours
        pts = []
        for c in contours:
            n = len(c)
            for i in range(n):
                p0 = c[i]
                p1 = c[(i + 1) % n]
                dist = max(abs(p1[0] - p0[0]), abs(p1[1] - p0[1]))
                steps = max(1, int(dist / 8.0))
                for t in range(steps):
                    pts.append((p0[0] + (p1[0] - p0[0]) * t / steps,
                                p0[1] + (p1[1] - p0[1]) * t / steps))

        if not pts:
            continue

        ys = [p[1] for p in pts]
        lo, hi = min(ys), max(ys)
        if hi - lo < min_height:
            continue

        band_h = (hi - lo) * band_fraction
        top = [p[0] for p in pts if p[1] >= hi - band_h]
        bot = [p[0] for p in pts if p[1] <= lo + band_h]

        if top and bot:
            dx = (sum(top) / len(top)) - (sum(bot) / len(bot))
            dy = (hi - lo - band_h)
            if dy > 0:
                slants.append(dx / dy)

    if not slants:
        return 0.0
    slants.sort()
    return slants[len(slants) // 2]


# Standard glyph names
GLYPH_NAMES: Dict[str, str] = {
    " ": "space",
    ".": "period",
    ",": "comma",
    "'": "quotesingle",
    '"': "quotedbl",
    "!": "exclam",
    "?": "question",
    ":": "colon",
    ";": "semicolon",
    "(": "parenleft",
    ")": "parenright",
    "$": "dollar",
    "-": "hyphen",
}
DIGIT_NAMES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]


def char_to_glyph_name(char: str) -> str:
    """Map character to OpenType/TrueType glyph name."""
    if char in GLYPH_NAMES:
        return GLYPH_NAMES[char]
    if char.isdigit():
        return DIGIT_NAMES[int(char)]
    return char

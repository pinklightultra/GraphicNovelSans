"""Image ingestion and ink extraction for comics and handwritten artwork.

Supports diverse artist workflows:
- Digital ink with transparent background (Procreate, Clip Studio Paint, Photoshop)
- Black ink on white paper (scans, camera photos)
- Blue-pencil drop (filtering out non-photo blue sketching pencil under black ink)
- Red-channel ink separation (as in BLUE175's light-blue lettering)
- Auto-detection mode
"""
import os
from typing import Union, Optional
import numpy as np
from PIL import Image


def load_image(source: Union[str, Image.Image, np.ndarray]) -> Image.Image:
    """Load an image from a path, existing PIL Image, or numpy array."""
    if isinstance(source, str):
        if not os.path.exists(source):
            raise FileNotFoundError(f"Image not found at path: {source}")
        return Image.open(source)
    if isinstance(source, Image.Image):
        return source
    if isinstance(source, np.ndarray):
        return Image.fromarray(source)
    raise TypeError(f"Unsupported image source type: {type(source)}")


def otsu_threshold(gray: np.ndarray) -> int:
    """Compute Otsu's optimal binarization threshold."""
    hist, _ = np.histogram(gray, bins=256, range=(0, 256))
    total = gray.size
    current_max, threshold = 0.0, 128
    sum_total = np.dot(np.arange(256), hist)
    weight_back, sum_back = 0.0, 0.0

    for i in range(256):
        weight_back += hist[i]
        if weight_back == 0:
            continue
        weight_fore = total - weight_back
        if weight_fore == 0:
            break
        sum_back += i * hist[i]
        mean_back = sum_back / weight_back
        mean_fore = (sum_total - sum_back) / weight_fore
        between_var = weight_back * weight_fore * ((mean_back - mean_fore) ** 2)
        if between_var > current_max:
            current_max = between_var
            threshold = i

    return threshold


def extract_ink_mask(
    image: Union[str, Image.Image, np.ndarray],
    mode: str = "auto",
    threshold: Optional[int] = None,
    invert: bool = False
) -> np.ndarray:
    """Extract a 2D boolean mask where True indicates ink, False indicates paper.

    Args:
        image: Path to image, PIL Image, or numpy array.
        mode: Ingestion mode:
            - 'auto': Automatically chooses 'alpha' if transparency exists, else 'black_on_white'.
            - 'black_on_white': Standard dark ink on light background.
            - 'alpha': Transparent background; alpha channel defines ink.
            - 'blue_pencil_drop': Removes non-photo blue (cyan/blue sketching lines) and retains dark ink.
            - 'red_channel': Isolates light-blue/cyan ink using the red channel (as in BLUE175).
            - 'white_on_black': Light ink on dark background.
        threshold: Optional custom integer threshold (0-255).
        invert: If True, inverts the final ink mask.

    Returns:
        2D boolean numpy array of shape (height, width).
    """
    img = load_image(image)

    # Auto mode resolution
    if mode == "auto":
        if img.mode in ("RGBA", "LA") or ("transparency" in img.info):
            # Check if alpha actually varies
            rgba = img.convert("RGBA")
            alpha = np.asarray(rgba)[:, :, 3]
            if (alpha < 250).any():
                mode = "alpha"
            else:
                mode = "black_on_white"
        else:
            mode = "black_on_white"

    if mode == "alpha":
        rgba = img.convert("RGBA")
        alpha = np.asarray(rgba)[:, :, 3]
        t = threshold if threshold is not None else 32
        mask = alpha > t

    elif mode == "black_on_white":
        gray = np.asarray(img.convert("L"))
        if threshold is None:
            # Otsu thresholding with safety clamp
            t = otsu_threshold(gray)
            # Comic scans are mostly white paper; ensure threshold isn't too light
            t = min(t, 210)
        else:
            t = threshold
        mask = gray <= t

    elif mode == "white_on_black":
        gray = np.asarray(img.convert("L"))
        t = threshold if threshold is not None else otsu_threshold(gray)
        mask = gray > t

    elif mode == "blue_pencil_drop":
        # Non-photo blue has high blue & green, but low red difference with paper.
        # Ink is dark across R, G, and B.
        rgb = np.asarray(img.convert("RGB"), dtype=np.int16)
        r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
        # Luminance
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        # Blue excess: non-photo blue has b > r + 30 and g > r + 20
        is_blue_sketch = (b > r + 25) & (g > r + 15) & (lum > 140)
        t = threshold if threshold is not None else 180
        mask = (lum < t) & (~is_blue_sketch)

    elif mode == "red_channel":
        # Ink has low red (< threshold), white paper has high red (~255)
        rgb = np.asarray(img.convert("RGB"), dtype=np.int16)
        t = threshold if threshold is not None else 225
        mask = rgb[:, :, 0] < t

    else:
        raise ValueError(f"Unknown ink extraction mode: {mode}")

    if invert:
        mask = ~mask

    return mask.astype(bool)

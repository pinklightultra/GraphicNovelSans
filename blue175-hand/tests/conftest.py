import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "pipeline"))

import paths  # noqa: E402

STYLES = {"Regular": "", "Bold": "-Bold", "Italic": "-Italic", "Bold Italic": "-BoldItalic"}


def shipped(style, ext="ttf"):
    return os.path.join(REPO, "fonts", ext, f"BLUE175{STYLES[style]}.{ext}")


@pytest.fixture(autouse=True)
def out(tmp_path, monkeypatch):
    """Every test writes into its own folder, never into the repo."""
    monkeypatch.setattr(paths, "OUT", str(tmp_path))
    return tmp_path


def have_pages():
    return os.path.exists(os.path.join(paths.PAGES, "p01.webp"))

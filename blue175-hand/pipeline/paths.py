"""Where the pipeline reads and writes.

Kept as separate trees so a run can never overwrite what it was built from:

  pages       the fifteen source pages, p01.webp .. p15.webp at 1600x2129. They
              are not in this repo; set BLUE175_PAGES to the folder holding them.
  data/       the hand-made selections: which ink on which page is which letter.
  out/        everything a run writes. BLUE175_OUT moves it.

Two committed trees are read when a run has not made its own copy yet:
`fonts/ttf` for the shipped fonts, and `legibility/` for the recorded blind
reads. So the proof sheets and the scorers work on a fresh clone with no pages.
"""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = os.environ.get("BLUE175_PAGES") or os.path.join(REPO, "pages")
DATA = os.path.join(REPO, "data")
OUT = os.environ.get("BLUE175_OUT") or os.path.join(REPO, "out")
FONTS = os.path.join(REPO, "fonts", "ttf")
READS = os.path.join(REPO, "legibility")


def data(name):
    return os.path.join(DATA, name)


def out(name):
    os.makedirs(OUT, exist_ok=True)
    return os.path.join(OUT, name)


def font(name):
    """A font this run built, else the shipped one."""
    return _first(name, OUT, FONTS)


def read(name):
    """An answer key or a transcription: this run's, else the recorded one."""
    return _first(name, OUT, READS)


def _first(name, *dirs):
    for d in dirs:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return os.path.join(dirs[-1], name)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump(obj, path, **kw):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, **kw)

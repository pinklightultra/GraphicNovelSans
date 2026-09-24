import os

import pytest
from PIL import Image, ImageChops

import blindsheet
import paths
import score

# errors out of 598 characters, per recorded read of legibility/blindtest.png
READS = {"ship_read1": 27, "ship_read2": 26, "ship_read3": 27,
         "final_indep1": 26, "final_indep2": 17, "final_indep3": 25}


@pytest.mark.parametrize("read,errs", READS.items())
def test_recorded_reads_score_as_published(read, errs, capsys):
    assert score.score(read=read + ".json") == pytest.approx(errs / 598)


def test_the_sheet_that_was_read_is_set_in_the_shipped_fonts(out):
    """The prose reads were taken before the final build, so prove they read these glyphs."""
    blindsheet.sheet()
    made = Image.open(out / "blindtest.png").convert("RGB")
    read = Image.open(os.path.join(paths.READS, "blindtest.png")).convert("RGB")
    assert made.size == read.size and ImageChops.difference(made, read).getbbox() is None
    assert paths.load(out / "blindtest_key.json") == \
        paths.load(os.path.join(paths.READS, "blindtest_key.json"))

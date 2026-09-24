import numpy as np
from graphicnovelsans.synthesis import synthesize_missing_glyphs


def test_synthesis_rules():
    # Setup mock glyphs
    p_mask = np.zeros((30, 20), dtype=bool)
    p_mask[5:15, 5:15] = True
    paren_mask = np.zeros((30, 10), dtype=bool)
    paren_mask[2:28, 2:8] = True
    dot_mask = np.ones((6, 6), dtype=bool)
    comma_mask = np.ones((10, 6), dtype=bool)

    glyphs = {
        "p": {"mask": p_mask},
        "(": {"mask": paren_mask},
        ".": {"mask": dot_mask},
        ",": {"mask": comma_mask},
        "Z": {"mask": p_mask.copy()},
        "'": {"mask": dot_mask.copy()},
    }

    result = synthesize_missing_glyphs(glyphs)

    # q should be mirrored from p
    assert "q" in result
    assert result["q"]["synthetic"] is True

    # ) should be mirrored from (
    assert ")" in result
    assert result[")"]["synthetic"] is True

    # z should be copied from Z
    assert "z" in result

    # " should be paired from '
    assert '"' in result

    # ; should be stacked from . and ,
    assert ";" in result

    # : should be stacked from . and .
    assert ":" in result

"""Automatic synthesis of missing glyphs from available hand-drawn characters."""
from typing import Dict, Any
import numpy as np


def synthesize_missing_glyphs(glyphs: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Synthesize missing characters using available hand-lettered glyphs.

    Comic artists often omit rare letters (e.g. 'q', 'z') or punctuation
    (';', '"', ')'). This module automatically fills in the gaps using
    geometric and typographic combination rules.
    """
    out = dict(glyphs)

    # 1. Mirror parenthesis: ) from (
    if ")" not in out and "(" in out:
        base = out["("]
        out[")"] = {
            "mask": base["mask"][:, ::-1].copy(),
            "synthetic": True,
            "origin": "mirror from ("
        }

    # 2. Mirror q from p
    if "q" not in out and "p" in out:
        base = out["p"]
        out["q"] = {
            "mask": base["mask"][:, ::-1].copy(),
            "synthetic": True,
            "origin": "mirror from p"
        }
    elif "p" not in out and "q" in out:
        base = out["q"]
        out["p"] = {
            "mask": base["mask"][:, ::-1].copy(),
            "synthetic": True,
            "origin": "mirror from q"
        }

    # 3. Copy case pairs: z <-> Z, x <-> X, c <-> C, o <-> O, v <-> V, w <-> W, s <-> S
    case_pairs = [("z", "Z"), ("x", "X"), ("c", "C"), ("o", "O"), ("v", "V"), ("w", "W"), ("s", "S")]
    for lower, upper in case_pairs:
        if lower not in out and upper in out:
            out[lower] = {
                "mask": out[upper]["mask"].copy(),
                "synthetic": True,
                "origin": f"copied from {upper}"
            }
        elif upper not in out and lower in out:
            out[upper] = {
                "mask": out[lower]["mask"].copy(),
                "synthetic": True,
                "origin": f"copied from {lower}"
            }

    # 4. Pair quotes: " from '
    if '"' not in out and "'" in out:
        one = out["'"]["mask"]
        gap = max(2, int(0.55 * one.shape[1]))
        pair_mask = np.zeros((one.shape[0], one.shape[1] * 2 + gap), dtype=bool)
        pair_mask[:, :one.shape[1]] = one
        pair_mask[:, one.shape[1] + gap:] = one
        out['"'] = {
            "mask": pair_mask,
            "synthetic": True,
            "origin": "paired from '"
        }

    # 5. Semicolon: stack . and ,
    if ";" not in out and "." in out and "," in out:
        top = out["."]["mask"]
        bot = out[","]["mask"]
        w = max(top.shape[1], bot.shape[1])
        gap = max(2, int(0.9 * top.shape[0]))
        h = top.shape[0] + gap + bot.shape[0]
        stack_mask = np.zeros((h, w), dtype=bool)
        stack_mask[:top.shape[0], (w - top.shape[1]) // 2:(w - top.shape[1]) // 2 + top.shape[1]] = top
        stack_mask[top.shape[0] + gap:, (w - bot.shape[1]) // 2:(w - bot.shape[1]) // 2 + bot.shape[1]] = bot
        out[";"] = {
            "mask": stack_mask,
            "synthetic": True,
            "origin": "stack of . and ,"
        }

    # 6. Colon: stack . and .
    if ":" not in out and "." in out:
        top = out["."]["mask"]
        bot = out["."]["mask"]
        w = top.shape[1]
        gap = max(2, int(1.4 * top.shape[0]))
        h = top.shape[0] + gap + bot.shape[0]
        stack_mask = np.zeros((h, w), dtype=bool)
        stack_mask[:top.shape[0], :] = top
        stack_mask[top.shape[0] + gap:, :] = bot
        out[":"] = {
            "mask": stack_mask,
            "synthetic": True,
            "origin": "stack of . and ."
        }

    # 7. Dotted j: if j exists but has no dot, place . on top
    if "j" in out and "." in out:
        j_mask = out["j"]["mask"]
        dot_mask = out["."]["mask"]
        # If j height is not much taller than x-height, it might lack a dot
        if not out["j"].get("dotted"):
            top_pixels = np.nonzero(j_mask[0])[0]
            cx = int(top_pixels.mean()) if len(top_pixels) else j_mask.shape[1] // 2
            gap = max(2, int(0.35 * dot_mask.shape[0]))
            total_h = dot_mask.shape[0] + gap + j_mask.shape[0]
            total_w = max(j_mask.shape[1], cx + dot_mask.shape[1])
            m = np.zeros((total_h, total_w), dtype=bool)
            x_dot = min(max(0, cx - dot_mask.shape[1] // 2), total_w - dot_mask.shape[1])
            m[:dot_mask.shape[0], x_dot:x_dot + dot_mask.shape[1]] = dot_mask
            m[dot_mask.shape[0] + gap:, :j_mask.shape[1]] = j_mask
            out["j"] = {
                "mask": m,
                "synthetic": True,
                "dotted": True,
                "origin": "dotted j from j + ."
            }

    # 8. Hyphen from minus or flat bar
    if "-" not in out:
        # Create a simple proportional bar if missing
        bar = np.ones((8, 36), dtype=bool)
        out["-"] = {
            "mask": bar,
            "synthetic": True,
            "origin": "generated bar"
        }

    return out

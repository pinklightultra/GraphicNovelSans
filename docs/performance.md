# Performance Notes

GraphicNovelSans processes a modest number of glyphs per build (typically
50–100 characters), so overall build times are dominated by a few hot paths.
This document records where time goes and what trade-offs exist.

## Benchmark Summary

Measured on a synthetic workload (100 iterations of a representative glyph):

| Operation | Time (100 iters) | Dominant cost |
| :--- | :--- | :--- |
| Contour tracing | ~3.9 s | `_marching_squares` (~2.9 s) |
| Bold dilation | ~3.9 s | `connected_components` (~3.6 s) |
| Kerning (26×26 pairs) | ~0.7 s | `compute_kern_pairs` |

## Hot Paths

### `trace._marching_squares`
Pure-Python loop over grid cells and segment linking. This is the single
largest cost in the pipeline. It scales with upscaled image area
(`UPSCALE = 4`, so 16× the source pixels).

**Possible future optimization:** vectorize the segment table construction
with NumPy, or port the contour walk to a compiled routine. Not done now
because correctness of winding/closure is delicate and current speed is
acceptable for per-glyph processing.

### `segment.connected_components`
Iterative flood fill in pure Python. Called by
`transform.dilate_with_counter_protection` once per dilation to locate
counter holes.

**Possible future optimization:** use `scipy.ndimage.label` when SciPy is
available, falling back to the current implementation otherwise. Avoided as
a hard dependency to keep the install lightweight.

### `kern.compute_kern_pairs`
O(n²) over glyphs, which is expected and cheap for typical alphabets
(≤ ~100 glyphs → ≤ 10,000 pairs).

## Guidance

- For interactive use (one sheet at a time), current performance is fine.
- For batch processing hundreds of sheets, the two hot paths above are the
  places to optimize first.
- Reducing `UPSCALE` in `trace.py` trades trace fidelity for speed.
>>>>>>> REPLACE
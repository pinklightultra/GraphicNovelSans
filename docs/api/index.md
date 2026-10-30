# API Reference

The `graphicnovelsans` library exposes a high-level `ComicFont` class alongside lower-level utilities for image ingestion, glyph synthesis, and font compilation.

## Modules

| Module | Purpose |
| :--- | :--- |
| [`core`](core.md) | Main `ComicFont` orchestrator class. |
| [`ingest`](ingest.md) | Image loading and ink mask extraction. |
| [`template`](template.md) | Lettering sheet generation and parsing. |
| [`synthesis`](synthesis.md) | Automatic missing-glyph generation. |
| [`builder`](builder.md) | TrueType / WOFF2 compilation. |
| [`kern`](kern.md) | Kerning pair calculation. |
| [`segment`](segment.md) | Character bounding-box detection and tightening. |
| [`transform`](transform.md) | Geometric transformations (slant, dilate, flip). |
| [`typography`](typography.md) | Metrics, baselines, and glyph positioning. |
| [`trace`](trace.md) | Raster-to-outline contour tracing. |

## Public Exports

The top-level package exports the following symbols:

```python
from graphicnovelsans import (
    ComicFont,
    extract_ink_mask,
    load_image,
    generate_lettering_sheet,
    extract_from_lettering_sheet,
    synthesize_missing_glyphs,
)
```

- `ComicFont`: High-level orchestrator.
- `extract_ink_mask`, `load_image`: From `ingest`.
- `generate_lettering_sheet`, `extract_from_lettering_sheet`: From `template`.
- `synthesize_missing_glyphs`: From `synthesis`.
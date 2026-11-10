# Troubleshooting

## "No ink found for character 'X'"

`add_glyph` raises `No ink found for character 'X'` when that drawing has no ink after extraction.

A sheet that yields nothing raises a different error. The CLI prints:

```text
Error: No characters were extracted from the sheet. Check contrast and ink mode.
```

What to check:

- The strokes are dark. A light gray mark can fall under the threshold.
- The ink mode matches the drawing. Blue pencil under dark ink wants `--ink-mode blue_pencil_drop`. Black ink on white paper wants `--ink-mode black_on_white`. A transparent layer wants `--ink-mode alpha`.
- The drawing sits inside its cell, and the page has no heavy shadow or extra marks in the cell.

## A character you left blank is missing

`build` does not report a synthesis failure. It fills a missing character only when the source glyph is present:

- `q` needs `p`, and `p` needs `q`
- `)` needs `(`
- `"` needs `'`
- `;` needs `.` and `,`
- `:` needs `.`
- lowercase or uppercase `c`, `o`, `s`, `v`, `w`, `x`, or `z` needs the other case

A missing `-` becomes a plain bar. Every other blank cell is left out of the font. Draw it and rebuild.

## The outlines look blocky

The contours are traced from the pixels in the sheet. A small drawing stays blocky. Draw the sheet larger. The template from `graphicnovelsans template` is 2480×3508 pixels. `build` accepts PNG, JPG, and WebP, so export to one of those.

## The spacing is uneven

Sidebearings come from each glyph's edge, and then a kerning pass adds pairs. A stroke that touches the cell border is part of the ink, so the sidebearing is measured from that stray mark. Keep the drawing off the cell edges. The generated kerning is what ships in the font; a later edit belongs in a font editor.

## "Error: Permission denied"

The output directory is not writable. Pass `-o` with a directory your user can write to. `build` creates the directory when the parent is writable.

## Reporting a problem

Open a GitHub issue with the operating system, the Python version, the command you ran, the traceback, and a sample of the sheet if you can share it.

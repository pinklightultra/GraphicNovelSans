# Quickstart

This builds a new font family from a lettering sheet. It does not rebuild the BLUE175 Hand files that ship in `blue175-hand/fonts/`. Those were cut by `blue175-hand/pipeline/build.py`.

## Prerequisites

- Python 3.8 or newer, and `graphicnovelsans` installed from this repository. See [Installation](installation.md).
- A pen, or an image editor.

## Step 1: Generate a lettering sheet

```bash
graphicnovelsans template --output lettering_template.png
```

The file is a 2480×3508 PNG (A4 at 300 DPI) with light-blue guide characters, a cell grid, and a baseline and an x-height line in each cell. Draw with dark ink. `--ink-mode blue_pencil_drop`, the `build` default, keeps dark strokes and drops non-photo blue.

`--all-caps` writes an uppercase-only sheet.

## Step 2: Fill in the cells

The full sheet has a cell for `A-Z`, `a-z`, `0-9`, and `. , : ; ' " ( ) - ! ? $`. There is no space cell. `build` adds a space glyph itself.

You can leave a cell empty when another character can stand in:

- `q` if you drew `p`, or `p` if you drew `q`
- `)` if you drew `(`
- `"` if you drew `'`
- `;` if you drew `.` and `,`
- `:` if you drew `.`
- the other case of `c`, `o`, `s`, `v`, `w`, `x`, or `z`

A blank `-` is filled with a plain bar. Any other empty cell is missing from the font.

Save the sheet as a PNG, JPG, or WebP.

## Step 3: Build the family

```bash
graphicnovelsans build filled_sheet.png -n "My Comic Hand" -d "Your Name"
```

The default ink mode is `blue_pencil_drop`. Fonts are written to `./dist/`. Spaces are removed from the family name, and Regular has no style suffix:

```text
MyComicHand.ttf
MyComicHand-Bold.ttf
MyComicHand-Italic.ttf
MyComicHand-BoldItalic.ttf
```

Each style is also written as `.woff2`.

## Step 4: Install the fonts you just built

On macOS, copy the `.ttf` files into `~/Library/Fonts/`. On Linux, copy them into `~/.local/share/fonts/` and run `fc-cache -f`. On Windows, select the files, right-click, and choose Install. Restart any application that was already open.

## Next

- Ink modes are listed in the [CLI reference](cli-guide.md).
- The library API is in the [API reference](api/index.md).

# CLI Reference

The `graphicnovelsans` command has two subcommands, `template` and `build`. It builds a new family from a sheet. It does not rebuild the BLUE175 Hand files in `blue175-hand/fonts/`.

## Exit codes

- `0`: the command finished.
- `1`: the program reported an error, including a missing input file, a sheet with no characters, or no subcommand.
- `2`: argparse rejected the arguments.

---

## Command: `template`
Generates a blank lettering sheet for drawing characters.

### Syntax

```bash
graphicnovelsans template [-h] [-o OUTPUT] [--all-caps] [--title TITLE]
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `-o, --output` | `lettering_template.png` | Output file path |
| `--all-caps` | `False` | Generate uppercase-only layout |
| `--title` | `"GraphicNovelSans Lettering Template"` | Custom header text |

### Example

```bash
graphicnovelsans template -o my_caps_template.png --all-caps --title "Super Hero Letters"
```

---

## Command: `build`

Builds a 4-style font family from a filled lettering sheet.

### Syntax

```bash
graphicnovelsans build INPUT [-h] [-n NAME] [-d DESIGNER] [-o OUT] [--all-caps] [--ink-mode MODE]
```

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `INPUT` | — | Path to filled lettering sheet (PNG/JPG/WebP) |
| `-n, --name` | `"Comic Hand"` | Font family name |
| `-d, --designer` | `"Comic Artist"` | Designer credit |
| `-o, --out` | `"./dist"` | Output directory |
| `--all-caps` | `False` | Input uses all-caps template |
| `--ink-mode` | `"blue_pencil_drop"` | Ink extraction mode |

### Ink Modes

| Mode | Best For |
|------|----------|
| `auto` | Auto-detect transparency or black-on-white |
| `black_on_white` | Dark ink on white paper |
| `alpha` | Digital layers with transparency |
| `blue_pencil_drop` | Dark ink over non-photo blue (default) |
| `red_channel` | Light-blue ink, separated on the red channel |

Spaces are removed from the family name. Regular has no style suffix; the other files use a hyphen and the style with the space removed. `My Comic Hand` is written as `MyComicHand.ttf`, `MyComicHand-Bold.ttf`, `MyComicHand-Italic.ttf`, and `MyComicHand-BoldItalic.ttf`, plus a `.woff2` for each.

### Example

```bash
graphicnovelsans build filled_sheet.png -n "My Comic Hand" -d "Your Name" --ink-mode black_on_white
```

---

## Tips

- Keep strokes off the cell borders. A mark on the border is measured as part of the glyph.
- Draw dark strokes. The default ink mode, `blue_pencil_drop`, keeps dark ink and drops non-photo blue.
- Empty cells are filled only in the cases listed in the [quickstart](quickstart.md). A missing `q` is mirrored from `p`, and a missing `p` is mirrored from `q`.
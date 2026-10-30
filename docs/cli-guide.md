# CLI Reference

The `graphicnovelsans` command-line interface offers two primary subcommands: `template` and `build`.

## Global Options
Exit codes:
- `0`: Success
- `1`: General error (e.g., missing file)
- `2`: Invalid arguments

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
| `blue_pencil_drop` | Blue pencil sketches (default) |
| `red_channel` | Red-channel isolation (BLUE175 style) |

### Example

```bash
graphicnovelsans build filled_sheet.png -n "Blue175 Hand" -d "Justin" --ink-mode red_channel
```

### Exit Codes

- `0`: Success
- `1`: General error (missing file, invalid args)
- `2`: Invalid arguments

---

## Tips

- Ensure characters don't touch template borders.
- Use high-contrast, dark strokes for best results.
- Missing glyphs like `q` are auto-generated from `p`; draw at least one of each pair.
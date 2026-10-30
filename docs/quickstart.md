# Quickstart: Create Your First Comic Font

Welcome to GraphicNovelSans! In this guide, you will go from a blank screen to installing your very own custom comic font in under 5 minutes.

## Prerequisites
- Python 3.8 or higher installed.
- An image editor (optional, for digital drawing) or paper + pen.

## Step 1: Generate Your Lettering Sheet
First, we need a template to draw your characters on. This ensures consistent sizing and spacing.

Run this command in your terminal:

```bash
graphicnovelsans template --output lettering_template.png
```

This generates a high-resolution PNG with light-blue guide boxes. Draw your characters neatly inside each box using a dark pen or digital brush. If using blue pencils, keep the guide lines light so they're easy to filter out later.

## Step 2: Fill Out the Template

Draw all 26 letters (A–Z), numbers (0–9), and common punctuation. You can skip `q`, `p`, `)`, etc.—they'll be auto-generated from their counterparts. Save your finished sheet as `filled_sheet.png` (300 DPI recommended).

## Step 3: Build Your Font

```bash
graphicnovelsans build filled_sheet.png -n "My Comic Hand" -d "Your Name"
```

Defaults: ink mode `blue_pencil_drop`, auto-synthesis enabled, output to `./dist/` with 4 styles.

## Step 4: Install & Test Your Font

On macOS/Linux, copy the `.ttf` files to `~/Library/Fonts/` (macOS) or `~/.local/share/fonts/` (Linux), then refresh the font cache. On Windows, right-click each `.ttf` and choose "Install".

## Next Steps

- Customize ink extraction with `--ink-mode`.
- Dive into the CLI Reference for advanced options.
- Explore the API to integrate into your own tools.

Enjoy your custom comic font! 🎉
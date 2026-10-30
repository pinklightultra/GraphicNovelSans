# Troubleshooting

Encountering issues? Here are solutions to common problems.

## 1. "No ink found for character 'X'"
**Cause:** The tool couldn't distinguish the character from the background.
**Solutions:**
- **Check Contrast:** Ensure your drawing is dark enough. Light gray strokes may be filtered out.
- **Adjust Ink Mode:** If you used blue pencil, ensure `--ink-mode blue_pencil_drop` is set. If using black ink, try `--ink-mode black_on_white`.
- **Clean Background:** Remove any stray marks or shadows from the character box.

## 2. "Glyph synthesis failed for 'q'"
**Cause:** The source character ('p') was too distorted or rotated incorrectly.
**Solutions:**
- **Manual Fix:** Draw the missing character manually on a new sheet and rebuild.
- **Check Alignment:** Ensure your 'p' is upright. The synthesis algorithm assumes standard orientation.

## 3. Font looks "blocky" or pixelated
**Cause:** The input image resolution was too low.
**Solutions:**
- **Increase Resolution:** Re-export your drawing at 300 DPI or higher.
- **Vectorize:** If drawing digitally, export as SVG/PDF and convert to high-res PNG before processing.

## 4. Spacing looks uneven (Kerning issues)
**Cause:** Comic lettering often has variable spacing that standard algorithms struggle with.
**Solutions:**
- **Adjust Box Size:** In your template, ensure characters aren't touching the borders. Leave a small margin.
- **Manual Kerning:** For production use, you may need to fine-tune kerning pairs in a dedicated font editor (e.g., FontForge, Glyphs) after generation.

## 5. "Permission denied" on Windows/Mac
**Cause:** The `dist` folder or target directory is locked or read-only.
**Solutions:**
- Run the terminal as Administrator (Windows) or use `sudo` (Mac/Linux) if necessary.
- Ensure the output folder exists and is writable.

## Still stuck?
Check the issue tracker to see if others have reported your problem, or submit a new issue with:
1. Your OS version.
2. The exact command you ran.
3. A sample of your input image (if possible).
# GraphicNovelSans 🎨

**Turn your handwriting into a professional comic font family in minutes.**

GraphicNovelSans is a powerful, open-source tool designed for comic artists, illustrators, and letterers. It transforms hand-drawn character sheets into fully functional, multi-style TrueType and WOFF2 font families with intelligent kerning and automatic glyph synthesis.

Whether you draw on paper with blue pencils or digitally in Procreate, GraphicNovelSans handles the heavy lifting of font engineering so you can focus on storytelling.

## ✨ Key Features

- **🖌️ Smart Ink Extraction**: Automatically isolates black ink from blue pencil sketches, red channels, or digital layers.
- **✨ Auto-Synthesis**: Missing 'q'? No 'z'? The engine intelligently generates missing glyphs from existing ones (e.g., flipping 'p' to make 'q').
- **📐 4-Style Generation**: Instantly creates Regular, Bold, Italic, and Bold Italic variants with mathematically calibrated slants.
- **⚡ Dual Format Export**: Outputs both desktop `.ttf` files and web-optimized `.woff2` files.
- **🎯 Comic-Optimized Kerning**: Specialized band-gap algorithms ensure perfect spacing for dialogue bubbles.
- **🔒 Local Processing**: All image processing happens on your machine. Your art never leaves your computer.

## 🚀 Quick Start

### Installation
Requires Python 3.8+.

```bash
pip install graphicnovelsans
```

Or for development:

```bash
git clone https://github.com/yourusername/graphicnovelsans.git
cd graphicnovelsans
pip install -e .
```

### Step 1: Generate a Template
Create a printable lettering sheet:

```bash
graphicnovelsans template --output my_template.png
```

Open `my_template.png` in your favorite art tool (or print it) and draw your characters inside the boxes.

### Step 2: Build Your Font
Once your sheet is filled:

```bash
graphicnovelsans build my_template.png -n "My Comic Hand" -d "Your Name"
```

By default, this extracts blue-pencil or black ink, auto-synthesizes missing glyphs (like `q` from `p`), and outputs a 4-style family.

### Output
Fonts land in `./dist/`:

```text
My Comic HandRegular.ttf + .woff2
My Comic HandBold.ttf + .woff2
My Comic HandItalic.ttf + .woff2
My Comic HandBoldItalic.ttf + .woff2
```

## 🧪 Examples
See `examples/` for sample sheets and scripts.

## 📚 Documentation
Full docs: https://yourusername.github.io/graphicnovelsans

- Installation
- Quickstart Guide
- CLI Reference
- API Docs

## 🤝 Contributing
We welcome contributions! See `docs/contributing.md` for guidelines.

## 📄 License
MIT License – see `LICENSE` for details.

Made with ❤️ by Justin Severn and the community.

## 📢 Latest Changes (v1.1.0)

- **Enhanced Documentation**: Every function now has detailed docstrings with examples.
- **Robust Error Handling**: Clear error messages and graceful failures.
- **Expanded Test Suite**: 58 tests covering all modules and edge cases.
- **Type Safety**: Full type hints for better IDE support and refactoring.

See [CHANGELOG.md](CHANGELOG.md) for full details.
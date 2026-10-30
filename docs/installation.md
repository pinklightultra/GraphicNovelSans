# Installation

## Requirements
- Python 3.8 or higher
- pip (Python package installer)

## Standard Installation

```bash
pip install graphicnovelsans
```

## Development Installation

```bash
git clone https://github.com/yourusername/graphicnovelsans.git
cd graphicnovelsans
pip install -e ".[test]"
```

## Verify Installation

```bash
graphicnovelsans --help
```

You should see the `template` and `build` subcommands.

## Optional Dependencies

- ImageMagick (optional): advanced image preprocessing on some platforms.
- Node.js (optional): only needed for the example web demo.

## Uninstallation

```bash
pip uninstall graphicnovelsans
```
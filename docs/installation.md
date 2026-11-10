# Installation

## BLUE175 Hand

The font in this repository is BLUE175 Hand: Regular, Bold, Italic, and Bold Italic, in `blue175-hand/fonts/ttf/`. Install all four. The family name, the web fonts, the specimen, and the character coverage are in the [repository README](https://github.com/pinklightultra/GraphicNovelSans/blob/main/README.md).

Those files are not produced by the `graphicnovelsans` command. The pipeline that cut them is in `blue175-hand/`.

## The library

`graphicnovelsans` is not published on PyPI. Install it from a clone. Python 3.8 or newer:

```bash
git clone https://github.com/pinklightultra/GraphicNovelSans.git
cd GraphicNovelSans
python -m pip install -e .
```

To run the tests:

```bash
python -m pip install -e ".[test]"
pytest
```

Check the command:

```bash
graphicnovelsans --help
```

The help lists the `template` and `build` subcommands.

Remove the package with `python -m pip uninstall graphicnovelsans`.

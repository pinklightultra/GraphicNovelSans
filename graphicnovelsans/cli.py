"""Command-line interface for GraphicNovelSans.

Provides two subcommands:
- `template`: Generate a printable lettering sheet.
- `build`: Build a font family from a filled sheet.

Usage:
    graphicnovelsans template -o my_template.png
    graphicnovelsans build filled_sheet.png -n "My Font" -d "Artist Name"
"""
import argparse
import sys
from .core import ComicFont


def main():
    """Entry point for the CLI. Parses arguments and dispatches to subcommands."""
    parser = argparse.ArgumentParser(
        prog="graphicnovelsans",
        description="Turn hand-lettered drawings into 4-style TrueType/WOFF2 font families.",
        epilog="Examples:\n"
               "  graphicnovelsans template -o sheet.png\n"
               "  graphicnovelsans build sheet.png -n 'My Font' -d 'Artist'",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: template
    tpl_parser = subparsers.add_parser(
        "template",
        help="Generate a printable/digital lettering sheet template",
        description="Creates a high-resolution template with light-blue guide characters."
    )
    tpl_parser.add_argument("-o", "--output", default="lettering_template.png", help="Output template image path")
    tpl_parser.add_argument("--all-caps", action="store_true", help="Generate all-caps layout (uppercase only)")
    tpl_parser.add_argument("--title", default="GraphicNovelSans Lettering Template", help="Custom header title")

    # Command: build
    build_parser = subparsers.add_parser(
        "build",
        help="Build a font family from a filled lettering sheet",
        description="Extracts ink, synthesizes missing glyphs, and compiles a 4-style font family."
    )
    build_parser.add_argument("input", metavar="SHEET", help="Path to filled lettering sheet (PNG/JPG/WebP)")
    build_parser.add_argument("-n", "--name", default="Comic Hand", help="Font family name")
    build_parser.add_argument("-d", "--designer", default="Comic Artist", help="Designer credit")
    build_parser.add_argument("-o", "--out", default="./dist", help="Output directory for fonts")
    build_parser.add_argument("--all-caps", action="store_true", help="Input uses all-caps template")
    build_parser.add_argument(
        "--ink-mode",
        default="blue_pencil_drop",
        choices=["auto", "black_on_white", "alpha", "blue_pencil_drop", "red_channel"],
        help="Ink extraction mode (default: blue_pencil_drop for blue pencil sketches)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "template":
            print(f"Generating lettering template -> {args.output}...")
            ComicFont.create_template(args.output, all_caps=args.all_caps, title=args.title)
            print("Done! Print or open in Procreate / Clip Studio Paint / Photoshop.")

        elif args.command == "build":
            # Validate input file exists before proceeding
            import os
            if not os.path.exists(args.input):
                print(f"Error: Input file not found: {args.input}", file=sys.stderr)
                sys.exit(1)

            print(f"Loading lettering sheet from {args.input}...")
            font = ComicFont(family_name=args.name, designer=args.designer, ink_mode=args.ink_mode)
            
            try:
                count = font.load_lettering_sheet(args.input, all_caps=args.all_caps, ink_mode=args.ink_mode)
            except ValueError as e:
                print(f"Error extracting glyphs: {e}", file=sys.stderr)
                sys.exit(1)

            if count == 0:
                print("Error: No characters were extracted from the sheet. Check contrast and ink mode.", file=sys.stderr)
                sys.exit(1)

            print(f"Extracted {count} character drawings.")

            synthesized = font.synthesize_missing()
            if synthesized:
                print(f"Auto-synthesized {len(synthesized)} missing glyphs: {', '.join(synthesized)}")

            print(f"Compiling 4-style linked family into {args.out}...")
            try:
                res = font.build(output_dir=args.out)
            except ValueError as e:
                print(f"Error building font: {e}", file=sys.stderr)
                sys.exit(1)

            print(f"Successfully built {res['family']}!")
            for style, sinfo in res["styles"].items():
                print(f"  [{style}] TTF: {sinfo['ttf']} | WOFF2: {sinfo['woff2']} ({sinfo['kern_pairs']} kern pairs)")

    except FileNotFoundError as e:
        print(f"Error: File not found - {e}", file=sys.stderr)
        sys.exit(1)
    except PermissionError as e:
        print(f"Error: Permission denied - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

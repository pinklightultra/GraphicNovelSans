# Changelog

All notable changes to GraphicNovelSans will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-10-30

### Added
- Comprehensive type hints across all modules.
- Extensive docstrings with usage examples for every public function.
- Robust error handling with descriptive messages and proper exit codes.
- 52 new tests covering edge cases, error paths, and integration scenarios.
- `EdgeProfile` dataclass for type-safe kerning calculations.
- CLI help text with usage examples.
- `docs/performance.md` documenting hot paths and optimization guidance.

### Changed
- Improved `dilate_with_counter_protection` algorithm documentation.
- Enhanced `measure_natural_slant` to handle backhand writing styles.
- Updated `build_family` to validate style names before processing.
- Moved developer scripts into a dedicated `scripts/` directory.

### Fixed
- Fixed duplicate docstring block in `kern.py`.
- Fixed `EdgeProfile` attribute access in `builder.py` and `kern.py`.
- Fixed `ContourPoint` type alias to use tuple for compatibility.
- Corrected threshold validation bounds in `extract_ink_mask`.

### Security
- No security vulnerabilities identified.

## [1.0.0] - 2024-XX-XX

### Added
- Initial release with core font generation pipeline.
- Support for 4-style font families (Regular, Bold, Italic, Bold Italic).
- Automatic glyph synthesis for missing characters.
- Blue-pencil and red-channel ink extraction modes.
- Dual-format export (TTF + WOFF2).
- Band-gap kerning optimized for comic lettering.

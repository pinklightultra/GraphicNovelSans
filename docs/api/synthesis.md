# API Reference: Synthesis Module

Automatically generates missing glyphs from existing hand-drawn characters using geometric transformations and composition rules.

## Functions

### `synthesize_missing_glyphs(glyphs)`
Fills gaps in the glyph set using available characters.

- **Input**: Dictionary mapping character strings to glyph data (`{"mask": ..., "synthetic": False, ...}`).
- **Returns**: Enriched dictionary with newly synthesized glyphs marked `"synthetic": True`.

**Supported Syntheses**:
| Missing Glyph | Source | Method |
| :--- | :--- | :--- |
| `)` | `(` | Horizontal mirror |
| `q` | `p` | Horizontal mirror |
| `p` | `q` | Horizontal mirror |
| `z`, `x`, `c`, `o`, `v`, `w`, `s` | Case pair | Direct copy |
| `"` | `'` | Duplicate + gap |
| `;` | `.`, `,` | Stack vertically |
| `:` | `.` | Stack vertically |
| `j` (dotted) | `j`, `.` | Add dot on top |
| `-` | — | Generate bar |

**Example**:
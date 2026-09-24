"""Font compilation engine: builds TrueType, WOFF2, GPOS, and legacy kern tables."""
import os
import math
from typing import Dict, List, Tuple, Any, Optional

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.feaLib.builder import addOpenTypeFeatures
from fontTools.ttLib import TTFont

from .typography import (
    UPM, X_HEIGHT, ASCENDER, DESCENDER, CAP_HEIGHT,
    place_glyph, measure_natural_slant, char_to_glyph_name
)
from .trace import trace_mask_to_contours, draw_contour_to_pen
from .transform import (
    dilate_with_counter_protection, shear_contours, calculate_italic_shear
)
from .kern import (
    compute_edge_profile, compute_flanks, compute_kern_pairs,
    generate_fea, create_legacy_kern_table
)

# RIBBI style definitions
STYLES_SPEC = {
    "Regular":     {"weight_class": 400, "weight_units": 0,  "lean_degrees": 0.0,   "fs": 0x40, "mac": 0},
    "Bold":        {"weight_class": 700, "weight_units": 34, "lean_degrees": 0.0,   "fs": 0x20, "mac": 1},
    "Italic":      {"weight_class": 400, "weight_units": 0,  "lean_degrees": 11.0,  "fs": 0x01, "mac": 2},
    "Bold Italic": {"weight_class": 700, "weight_units": 34, "lean_degrees": 11.0,  "fs": 0x21, "mac": 3},
}


def build_style(
    style_name: str,
    glyphs: Dict[str, Dict[str, Any]],
    family_name: str,
    output_dir: str,
    designer: str = "Comic Artist",
    version: str = "1.0",
    natural_slant: Optional[float] = None
) -> Dict[str, Any]:
    """Compile a single font style (TTF and WOFF2) with metrics and kerning."""
    os.makedirs(output_dir, exist_ok=True)
    spec = STYLES_SPEC[style_name]
    slug = style_name.replace(" ", "")
    ttf_filename = f"{family_name.replace(' ', '')}.ttf" if style_name == "Regular" else f"{family_name.replace(' ', '')}-{slug}.ttf"
    ttf_path = os.path.join(output_dir, ttf_filename)

    weight_units = spec["weight_units"]
    target_lean = spec["lean_degrees"]

    # 1. First pass: vectorize & place glyphs
    drawn = {}
    for ch, gdata in sorted(glyphs.items()):
        mask = gdata["mask"]
        scale, base_off = place_glyph(ch, mask)

        # Apparent stroke weight gain in source pixels
        dilation_px = max(1, int(round(weight_units / scale))) if weight_units else 0
        if dilation_px:
            mask = dilate_with_counter_protection(mask, dilation_px)
            base_off += dilation_px

        contours = trace_mask_to_contours(mask, scale, base_off)
        drawn[ch] = (contours, dilation_px)

    # 2. Slant compensation
    if natural_slant is None:
        natural_slant = measure_natural_slant({c: v[0] for c, v in drawn.items()})

    shear = calculate_italic_shear(natural_slant, target_lean) if target_lean != 0.0 else 0.0
    if abs(shear) > 1e-5:
        drawn = {
            ch: (shear_contours(cs, shear), px)
            for ch, (cs, px) in drawn.items()
        }

    # 3. Flank sidebearings and pen drawing
    final_glyphs = {}
    metrics = {}
    profiles = {}

    for ch, (cs, px) in sorted(drawn.items()):
        raw = compute_edge_profile(cs, 0, DESCENDER, ASCENDER)
        lsb, rsb = compute_flanks(raw["bands"], DESCENDER, ASCENDER, (0, X_HEIGHT))
        xs = [p[0] for c in cs for p in c] or [0.0]
        x0, x1 = min(xs), max(xs)
        adv = int(round(lsb + (x1 - x0) + rsb))
        # Shift contours by LSB
        cs = [[(x + lsb - x0, y) for x, y in c] for c in cs]

        gname = char_to_glyph_name(ch)
        pen = TTGlyphPen(None)
        for c in cs:
            draw_contour_to_pen(pen, c)

        final_glyphs[gname] = pen.glyph()
        metrics[gname] = (adv, int(round(lsb)))
        profiles[gname] = compute_edge_profile(cs, adv, DESCENDER, ASCENDER)

    # Add .notdef and space
    final_glyphs[".notdef"] = TTGlyphPen(None).glyph()
    metrics[".notdef"] = (int(0.30 * UPM), 0)
    final_glyphs["space"] = TTGlyphPen(None).glyph()
    metrics["space"] = (int(0.30 * UPM), 0)

    glyph_order = [".notdef", "space"] + [char_to_glyph_name(c) for c in sorted(glyphs)]

    # 4. OpenType assembly via FontBuilder
    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder([n for n in glyph_order if n in final_glyphs])
    fb.setupCharacterMap({
        ord(" "): "space",
        **{ord(c): char_to_glyph_name(c) for c in glyphs}
    })
    fb.setupGlyf(final_glyphs)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=ASCENDER, descent=DESCENDER, lineGap=0)
    fb.setupNameTable({
        "familyName": family_name,
        "styleName": style_name,
        "uniqueFontIdentifier": f"{family_name.replace(' ', '')}-{slug}-{version}",
        "fullName": f"{family_name} {style_name}",
        "psName": f"{family_name.replace(' ', '')}-{slug}",
        "version": f"Version {version}",
        "designer": designer,
    })
    fb.setupOS2(
        sTypoAscender=ASCENDER,
        sTypoDescender=DESCENDER,
        sTypoLineGap=0,
        usWinAscent=ASCENDER,
        usWinDescent=-DESCENDER,
        sxHeight=X_HEIGHT,
        sCapHeight=CAP_HEIGHT,
        achVendID="GNVL",
        usWeightClass=spec["weight_class"],
        fsSelection=spec["fs"]
    )
    fb.setupPost(italicAngle=-target_lean)
    fb.font["head"].macStyle = spec["mac"]

    # 5. Dual kerning: GPOS + format-0 legacy kern
    kerns = compute_kern_pairs(profiles)
    if kerns:
        fea_path = os.path.join(output_dir, f"kern-{slug}.fea")
        generate_fea(kerns, fea_path)
        addOpenTypeFeatures(fb.font, fea_path)
        if os.path.exists(fea_path):
            os.remove(fea_path)
    legacy_table, legacy_pairs_count = create_legacy_kern_table(kerns, set(final_glyphs))
    fb.font["kern"] = legacy_table

    # Save TTF
    fb.save(ttf_path)

    # Save WOFF2
    woff2_filename = os.path.splitext(ttf_filename)[0] + ".woff2"
    woff2_path = os.path.join(output_dir, woff2_filename)
    tt_w = TTFont(ttf_path)
    tt_w.flavor = "woff2"
    tt_w.save(woff2_path)

    return {
        "style": style_name,
        "ttf": ttf_path,
        "woff2": woff2_path,
        "glyph_count": len(final_glyphs),
        "kern_pairs": len(kerns),
        "legacy_kern_pairs": legacy_pairs_count,
        "natural_slant": natural_slant,
        "applied_shear": shear
    }


def build_family(
    glyphs: Dict[str, Dict[str, Any]],
    family_name: str,
    output_dir: str,
    designer: str = "Comic Artist",
    version: str = "1.0",
    styles: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Compile all requested styles for the font family."""
    if styles is None:
        styles = ["Regular", "Bold", "Italic", "Bold Italic"]

    # Measure natural slant across Regular base
    sample_drawn = {}
    for ch, gdata in glyphs.items():
        scale, base_off = place_glyph(ch, gdata["mask"])
        sample_drawn[ch] = trace_mask_to_contours(gdata["mask"], scale, base_off)
    natural_slant = measure_natural_slant(sample_drawn)

    results = {}
    for st in styles:
        res = build_style(
            style_name=st,
            glyphs=glyphs,
            family_name=family_name,
            output_dir=output_dir,
            designer=designer,
            version=version,
            natural_slant=natural_slant
        )
        results[st] = res

    return {
        "family": family_name,
        "styles": results,
        "output_dir": output_dir,
        "natural_slant_degrees": math.degrees(math.atan(natural_slant))
    }

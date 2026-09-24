"""Comic Panel Typesetting Demo using BLUE175 Hand.

Demonstrates how comic artists can take their generated font family and
typeset dialogue directly into comic book panels and speech balloons
with HarfBuzz pair kerning and automatic style switching (Regular, Bold, Italic).
"""
import os
import math
from PIL import Image, ImageDraw, ImageFont
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen


class _FlattenPen(BasePen):
    def __init__(self, glyph_set, step=3.0):
        super().__init__(glyph_set)
        self.step = step
        self.contours = []
        self._cur = None

    def _moveTo(self, pt):
        self._cur = [pt]

    def _lineTo(self, pt):
        self._cur.append(pt)

    def _qCurveToOne(self, off, pt):
        p0 = self._cur[-1]
        n = max(2, min(24, int((abs(pt[0] - p0[0]) + abs(pt[1] - p0[1])) / self.step) + 1))
        for i in range(1, n + 1):
            t = i / n
            u = 1 - t
            self._cur.append((u * u * p0[0] + 2 * u * t * off[0] + t * t * pt[0],
                              u * u * p0[1] + 2 * u * t * off[1] + t * t * pt[1]))

    def _closePath(self):
        if self._cur and len(self._cur) > 2:
            self.contours.append(self._cur)
        self._cur = None

    _endPath = _closePath


class ComicRenderer:
    def __init__(self, font_path: str, size: int):
        self.blob = hb.Blob.from_file_path(font_path)
        self.face = hb.Face(self.blob)
        self.hb_font = hb.Font(self.face)
        self.tt = TTFont(font_path)
        self.upm = self.face.upem
        self.size = size
        self.scale = size / float(self.upm)
        self.order = self.tt.getGlyphOrder()
        self.glyphs = self.tt.getGlyphSet()
        self._cache = {}

    def get_length(self, text: str) -> float:
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb_font, buf, {"kern": True})
        return sum(pos.x_advance for pos in buf.glyph_positions) * self.scale

    def draw_text(self, img: Image.Image, pos: tuple, text: str, color=(30, 40, 60)):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb_font, buf, {"kern": True})
        ss = 4
        x, y = pos
        cx = 0

        for info, p in zip(buf.glyph_infos, buf.glyph_positions):
            gname = self.order[info.codepoint]
            gx = x + (cx + p.x_offset) * self.scale
            gy = y - p.y_offset * self.scale

            if gname not in self._cache:
                pen = _FlattenPen(self.glyphs, step=2.0)
                self.glyphs[gname].draw(pen)
                self._cache[gname] = pen.contours

            contours = self._cache[gname]
            if contours:
                poly_list = []
                for c in contours:
                    poly_list.append([
                        ((gx + px * self.scale) * ss,
                         (gy + (800 - py) * self.scale) * ss)
                        for px, py in c
                    ])

                # Bounding box for local rasterization
                all_pts = [pt for poly in poly_list for pt in poly]
                min_x = max(0, int(min(p[0] for p in all_pts) // ss))
                min_y = max(0, int(min(p[1] for p in all_pts) // ss))
                max_x = min(img.width, int(max(p[0] for p in all_pts) // ss + 2))
                max_y = min(img.height, int(max(p[1] for p in all_pts) // ss + 2))

                w_sub = (max_x - min_x) * ss
                h_sub = (max_y - min_y) * ss
                if w_sub > 0 and h_sub > 0:
                    mask_im = Image.new("L", (w_sub, h_sub), 0)
                    mask_draw = ImageDraw.Draw(mask_im)
                    for poly in poly_list:
                        shifted = [(p[0] - min_x * ss, p[1] - min_y * ss) for p in poly]
                        mask_draw.polygon(shifted, fill=255)

                    small_mask = mask_im.resize((max_x - min_x, max_y - min_y), Image.LANCZOS)
                    color_tile = Image.new("RGB", small_mask.size, color)
                    img.paste(color_tile, (min_x, min_y), small_mask)

            cx += p.x_advance


def render_comic_strip(output_path: str = "examples/blue175_comic_strip.png"):
    font_dir = "blue175-hand/fonts/ttf"
    reg = ComicRenderer(os.path.join(font_dir, "BLUE175.ttf"), 32)
    bold = ComicRenderer(os.path.join(font_dir, "BLUE175-Bold.ttf"), 32)
    italic = ComicRenderer(os.path.join(font_dir, "BLUE175-Italic.ttf"), 32)

    width, height = 1400, 520
    im = Image.new("RGB", (width, height), (248, 249, 246))
    draw = ImageDraw.Draw(im)

    try:
        caption_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
    except OSError:
        caption_font = ImageFont.load_default()

    # Panel Layout: 3 comic panels
    panel_w = 400
    panel_h = 440
    gutter = 30
    left_margin = (width - (3 * panel_w + 2 * gutter)) // 2

    # BLUE175 Dialogue excerpts from Justin's comic
    panels_data = [
        {
            "num": "PANEL 1",
            "bg": (238, 242, 247),
            "balloon_y": 70,
            "balloon_h": 190,
            "lines": [
                ("I work at what I can only describe as", reg),
                ("Northwest Orlando's 2nd most", bold),
                ("abandoned mall. Great job for me.", reg),
            ],
            "tail": [(200, 260), (170, 320), (220, 260)]
        },
        {
            "num": "PANEL 2",
            "bg": (245, 242, 238),
            "balloon_y": 60,
            "balloon_h": 220,
            "lines": [
                ("Parking enforcement is technically", reg),
                ("opt-in. Paid to us as commission.", reg),
                ("$127.00, if you were wondering.", bold),
                ("Twice in one day.", italic),
            ],
            "tail": [(200, 280), (240, 340), (220, 280)]
        },
        {
            "num": "PANEL 3",
            "bg": (240, 244, 241),
            "balloon_y": 80,
            "balloon_h": 180,
            "lines": [
                ("The times are precarious,", reg),
                ("the precarious are timed.", italic),
                ("Ten minutes done. Thank god.", bold),
            ],
            "tail": [(200, 260), (190, 320), (230, 260)]
        }
    ]

    for i, pdata in enumerate(panels_data):
        px = left_margin + i * (panel_w + gutter)
        py = 40

        # Draw panel background & dark ink border
        draw.rectangle([px, py, px + panel_w, py + panel_h], fill=pdata["bg"], outline=(40, 40, 50), width=4)

        # Panel header label
        draw.text((px + 16, py + 14), pdata["num"], fill=(130, 140, 155), font=caption_font)

        # Draw comic speech balloon
        bx0 = px + 24
        by0 = py + pdata["balloon_y"]
        bx1 = px + panel_w - 24
        by1 = by0 + pdata["balloon_h"]

        # Balloon body (rounded rectangle)
        draw.rounded_rectangle([bx0, by0, bx1, by1], radius=24, fill=(255, 255, 255), outline=(40, 40, 50), width=3)

        # Balloon tail
        tail_pts = [(px + p[0], py + p[1]) for p in pdata["tail"]]
        draw.polygon(tail_pts, fill=(255, 255, 255))
        draw.line([tail_pts[0], tail_pts[1], tail_pts[2]], fill=(40, 40, 50), width=3)

        # Typeset dialogue lines inside balloon
        text_y = by0 + 24
        for line_str, face in pdata["lines"]:
            lw = face.get_length(line_str)
            text_x = bx0 + (bx1 - bx0 - lw) / 2.0
            face.draw_text(im, (text_x, text_y), line_str, color=(35, 45, 65))
            text_y += 42

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    im.save(output_path)
    print(f"Generated comic strip demo -> {output_path} ({width}x{height})")


if __name__ == "__main__":
    render_comic_strip()

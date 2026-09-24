"""Render text through the finished font the way a layout engine would.

Pillow places glyphs by advance width alone unless it was built against Raqm,
and this Pillow was not, so a Pillow proof of a kerned font is a picture of the
unkerned font -- the exact thing the proof is supposed to check. Shaping the
string with HarfBuzz and filling the outlines here means what appears on the page
is what the GPOS table actually does, and a `kern=False` render is available for
comparison.
"""
import numpy as np
import uharfbuzz as hb
from PIL import Image, ImageDraw, ImageChops
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen

SS = 4          # supersample factor; the outlines are curves, the canvas is not
FLAT = 3.0      # curve flattening step, in supersampled pixels


class Flatten(BasePen):
    """Collect a glyph as polygons in font units, curves already subdivided."""

    def __init__(self, glyphSet, step):
        super().__init__(glyphSet)
        self.step = step
        self.contours = []
        self._c = None

    def _moveTo(self, pt):
        self._c = [pt]

    def _lineTo(self, pt):
        self._c.append(pt)

    def _n(self, *pts):
        d = sum(abs(pts[i][0] - pts[i - 1][0]) + abs(pts[i][1] - pts[i - 1][1])
                for i in range(1, len(pts)))
        return max(2, min(24, int(d / self.step) + 1))

    def _qCurveToOne(self, off, pt):
        p0 = self._c[-1]
        for i in range(1, self._n(p0, off, pt) + 1):
            t = i / self._n(p0, off, pt)
            u = 1 - t
            self._c.append((u * u * p0[0] + 2 * u * t * off[0] + t * t * pt[0],
                            u * u * p0[1] + 2 * u * t * off[1] + t * t * pt[1]))

    def _curveToOne(self, a, b, pt):
        p0 = self._c[-1]
        n = self._n(p0, a, b, pt)
        for i in range(1, n + 1):
            t = i / n
            u = 1 - t
            self._c.append((u**3 * p0[0] + 3 * u * u * t * a[0]
                            + 3 * u * t * t * b[0] + t**3 * pt[0],
                            u**3 * p0[1] + 3 * u * u * t * a[1]
                            + 3 * u * t * t * b[1] + t**3 * pt[1]))

    def _closePath(self):
        if self._c and len(self._c) > 2:
            self.contours.append(self._c)
        self._c = None

    _endPath = _closePath


class Face:
    """One font at one size, with a Pillow-shaped interface."""

    def __init__(self, path, size, kern=True):
        blob = hb.Blob.from_file_path(path)
        self.face = hb.Face(blob)
        self.hb = hb.Font(self.face)
        self.tt = TTFont(path)
        self.upm = self.face.upem
        self.size = size
        self.k = size / float(self.upm)
        self.feat = {"kern": bool(kern)}
        self.order = self.tt.getGlyphOrder()
        self.glyphs = self.tt.getGlyphSet()
        self.ascent = self.tt["hhea"].ascent
        self.descent = self.tt["hhea"].descent
        self._cache = {}

    # ---------------------------------------------------------------- shaping
    def shape(self, text):
        """(glyph name, x, y) per glyph in font units, kerning applied."""
        if not text:            # blank lines between paragraphs are legitimate
            return [], 0
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb, buf, self.feat)
        out, x, y = [], 0, 0
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            out.append((self.order[info.codepoint], x + pos.x_offset,
                        y + pos.y_offset))
            x += pos.x_advance
            y += pos.y_advance
        return out, x

    def getlength(self, text):
        return self.shape(text)[1] * self.k

    # ------------------------------------------------------------- rasterising
    def mask(self, name):
        """Supersampled ink for one glyph, plus its offset from the origin.

        Even-odd across the glyph's own contours, which is right here because
        every contour came from one connected mask: an 'o' is a bowl inside an
        outline, and nothing overlaps anything else.
        """
        if name in self._cache:
            return self._cache[name]
        pen = Flatten(self.glyphs, FLAT / (self.k * SS))
        self.glyphs[name].draw(pen)
        if not pen.contours:
            self._cache[name] = (None, 0, 0)
            return self._cache[name]
        s = self.k * SS
        pts = [[(x * s, -y * s) for x, y in c] for c in pen.contours]
        xs = [p[0] for c in pts for p in c]
        ys = [p[1] for c in pts for p in c]
        x0, y0 = int(np.floor(min(xs))) - 1, int(np.floor(min(ys))) - 1
        w = int(np.ceil(max(xs))) - x0 + 2
        h = int(np.ceil(max(ys))) - y0 + 2
        acc = Image.new("1", (w, h), 0)
        for c in pts:
            lay = Image.new("1", (w, h), 0)
            ImageDraw.Draw(lay).polygon([(x - x0, y - y0) for x, y in c], fill=1)
            acc = ImageChops.logical_xor(acc, lay)
        self._cache[name] = (np.asarray(acc), x0, y0)
        return self._cache[name]

    def alpha(self, text):
        """Antialiased coverage for one line, with the baseline at row `ascent`."""
        glyphs, adv = self.shape(text)
        W = max(1, int(np.ceil(adv * self.k)) + 4)
        H = int(np.ceil((self.ascent - self.descent) * self.k)) + 4
        big = np.zeros((H * SS, W * SS), dtype=bool)
        base = int(round(self.ascent * self.k * SS))
        for name, gx, gy in glyphs:
            m, mx, my = self.mask(name)
            if m is None:
                continue
            px = int(round(gx * self.k * SS)) + mx
            py = base - int(round(gy * self.k * SS)) + my
            x0, y0 = max(0, px), max(0, py)
            x1 = min(big.shape[1], px + m.shape[1])
            y1 = min(big.shape[0], py + m.shape[0])
            if x1 <= x0 or y1 <= y0:
                continue
            big[y0:y1, x0:x1] |= m[y0 - py:y1 - py, x0 - px:x1 - px]
        a = big.reshape(H, SS, W, SS).mean(axis=(1, 3))
        return a, int(round(self.ascent * self.k))

    def text(self, im, xy, s, fill):
        """Draw `s` with xy at the top of the ascender, matching Pillow's default."""
        a, _ = self.alpha(s)
        x, y = int(xy[0]), int(xy[1])
        h, w = a.shape
        box = np.asarray(im.crop((x, y, x + w, y + h)), dtype=np.float32)
        if box.shape[:2] != (h, w):        # clipped at the edge of the canvas
            h, w = box.shape[0], box.shape[1]
            a = a[:h, :w]
        col = np.array(fill, dtype=np.float32)
        out = box * (1 - a[..., None]) + col * a[..., None]
        im.paste(Image.fromarray(out.astype(np.uint8)), (x, y))

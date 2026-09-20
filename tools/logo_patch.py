# 타이틀 로고 아래 「スターフォックス ゼロ」(title.wta 0번 RGBA8 텍스처) → 「스타폭스 제로」
import os, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import addrlib
import wtex

from paths import NOTO as FONT_PATH
SS = 4
TEXT = '스타폭스 제로'
# (erase box x0, y0, x1, y1), text span x0..x1, ink top..bottom — measured from the original texture
REGIONS = [
    dict(erase=(190, 492, 559, 523), span=(195, 555), ink=(497, 522)),
    dict(erase=(1672, 190, 2040, 224), span=(1676, 2035), ink=(194, 219)),
]
SHEAR = 0.28      # italic slant like the original katakana
WEIGHT = 900
EMB = 0.25        # extra emboldening (px)
XSCALE = 1.15     # the original katakana is wide and squat
GAP_RATIO = 0.48  # gap between syllables relative to syllable width
SPACE_RATIO = 0.9 # extra width of the word space


def _font(size):
    f = ImageFont.truetype(FONT_PATH, size)
    f.set_variation_by_axes([WEIGHT])
    return f


def _render_syllable(ch, ink_h):
    """-> float alpha array (at 1x) for one italic syllable, tightly cropped, height ink_h"""
    size = int(ink_h * SS * 1.25)
    for _ in range(6):
        im = Image.new('L', (size * 3, size * 3))
        ImageDraw.Draw(im).text((size, size), '한', font=_font(size), fill=255,
                                stroke_width=int(EMB * SS), stroke_fill=255)
        a = np.array(im)
        ys = np.nonzero(a.max(1) > 40)[0]
        size = max(8, round(size * ink_h * SS / (ys[-1] - ys[0] + 1)))
    im = Image.new('L', (size * 3, size * 3))
    ImageDraw.Draw(im).text((size, size), ch, font=_font(size), fill=255,
                            stroke_width=int(EMB * SS), stroke_fill=255)
    # shear: x' = x + SHEAR * (h - y)
    w, h = im.size
    im = im.transform((w + int(SHEAR * h), h), Image.AFFINE, (1, SHEAR, -SHEAR * h, 0, 1, 0), Image.BICUBIC)
    im = im.resize((int(im.width * XSCALE), im.height), Image.BICUBIC)
    a = np.array(im).astype(np.float32)
    ys = np.nonzero(a.max(1) > 10)[0]
    xs = np.nonzero(a.max(0) > 10)[0]
    return a[ys[0]:ys[-1] + 1, xs[0]:xs[-1] + 1]


def _down(a):
    h, w = a.shape
    a = np.pad(a, ((0, (-h) % SS), (0, (-w) % SS)))
    return a.reshape(a.shape[0] // SS, SS, a.shape[1] // SS, SS).mean((1, 3))


def paint(rgba):
    out = rgba.copy()
    for r in REGIONS:
        ex0, ey0, ex1, ey1 = r['erase']
        box = out[ey0:ey1, ex0:ex1]
        gray = (np.abs(box[:, :, 0].astype(int) - box[:, :, 1]) < 16) & (np.abs(box[:, :, 1].astype(int) - box[:, :, 2]) < 16)
        box[gray] = (255, 255, 255, 0)
        y0, y1 = r['ink']
        ink_h = y1 - y0
        glyphs = [None if c == ' ' else _render_syllable(c, ink_h) for c in TEXT]
        sx0, sx1 = r['span']
        scale = ink_h * SS / max(g.shape[0] for g in glyphs if g is not None)
        glyphs = [None if g is None else np.array(Image.fromarray(g).resize(
            (max(1, round(g.shape[1] * scale)), max(1, round(g.shape[0] * scale))),
            Image.Resampling.LANCZOS)).clip(0, 255) for g in glyphs]
        widths = [g.shape[1] if g is not None else 0 for g in glyphs]
        avg = np.mean([w for w in widths if w])
        gap = avg * GAP_RATIO
        x = 0.0
        placements = []
        for g, w, ch in zip(glyphs, widths, TEXT):
            if g is not None:
                placements.append((round(x), g))
                x += w + gap
            else:
                x += avg * SPACE_RATIO
        total = max(xi + g.shape[1] for xi, g in placements)
        if total > (sx1 - sx0) * SS:
            raise ValueError('Title lettering exceeds its texture region')
        canvas = np.zeros((ink_h * SS, (sx1 - sx0) * SS), np.float32)
        offset = round((canvas.shape[1] - total) / 2)
        for xi, g in placements:
            h, w = g.shape
            canvas[:h, offset + xi:offset + xi + w] = g
        alpha = _down(canvas)
        ah, aw = alpha.shape
        dst = out[y0:y0 + ah, sx0:sx0 + aw]
        # original text: near-white with a slight darker band in the lower half
        rows = np.linspace(0, 1, ah)[:, None]
        shade = np.where(rows < 0.45, 255, 244)
        a8 = alpha.clip(0, 255)
        keep = a8 > dst[:, :, 3]
        for c in range(3):
            dst[:, :, c] = np.where(keep, shade, dst[:, :, c])
        dst[:, :, 3] = np.maximum(dst[:, :, 3], a8.round().astype(np.uint8))
    return out


def build_title_wtp(dat_dir):
    wta = open(os.path.join(dat_dir, 'title.wta'), 'rb').read()
    wtp = bytearray(open(os.path.join(dat_dir, 'title.wtp'), 'rb').read())
    e = wtex.wta_entries(wta)[0]
    assert (e['w'], e['h'], e['fmt']) == (2048, 1024, 0x41A), e
    raw, info = wtex.decode_entry(e, bytes(wtp))
    rgba = np.frombuffer(bytes(raw), np.uint8).reshape(e['h'], e['w'], 4)
    new = paint(rgba)
    enc = addrlib.swizzle(e['w'], e['h'], info.height, e['fmt'], e['tile'], e['swz'], info.pitch, 32, new.tobytes())
    assert len(enc) == e['isz']
    wtp[e['off']:e['off'] + e['isz']] = enc
    return bytes(wtp), new


if __name__ == '__main__':
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'work', 'orig', 'ui__ui_title.dat')
    rgba = np.load(os.path.join(d, 'title0_rgba.npy'))
    new = paint(rgba)
    for i, (x0, y0, x1, y1) in enumerate([(150, 470, 880, 550), (1640, 180, 2048, 245)]):
        before = Image.fromarray(rgba[y0:y1, x0:x1])
        after = Image.fromarray(new[y0:y1, x0:x1])
        bg = Image.new('RGBA', (after.width, after.height * 2 + 6), (50, 50, 110, 255))
        bg.alpha_composite(before, (0, 0))
        bg.alpha_composite(after, (0, after.height + 6))
        bg = bg.resize((bg.width * 3, bg.height * 3), Image.NEAREST)
        bg.save('logo_preview_%d.png' % i)

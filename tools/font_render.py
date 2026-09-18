# Korean glyph renderer matching Star Fox Zero MCD font styles.
# RG8 atlas: G = glyph body, R = body + ~1px outline.
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from paths import NOTO as FONT_PATH
SS = 4  # supersampling

# measured from the original atlases (per font id, at reference cell height h_ref)
#   ink: CJK ink height, wght: Noto weight, emb: extra emboldening px, outline: R-G px, margin: side bearing px
STYLES = {
    1:  dict(h_ref=57,  ink=31.5, wght=800, emb=0.0, outline=1.0, margin=6),
    2:  dict(h_ref=55,  ink=28,   wght=800, emb=0.0, outline=1.0, margin=6),
    3:  dict(h_ref=70,  ink=36.5, wght=900, emb=0.5, outline=1.0, margin=7),
    4:  dict(h_ref=127, ink=73,   wght=900, emb=1.0, outline=1.5, margin=11),
    5:  dict(h_ref=53,  ink=29.5, wght=900, emb=0.5, outline=1.0, margin=5),
    7:  dict(h_ref=57,  ink=31,   wght=450, emb=0.0, outline=1.0, margin=6),
    8:  dict(h_ref=246, ink=144,  wght=900, emb=2.0, outline=0.0, margin=12),
    10: dict(h_ref=86,  ink=49.5, wght=900, emb=0.8, outline=1.0, margin=5),
}
HANGUL_MARGIN = 0.5
DEFAULT_STYLE = dict(h_ref=57, ink=33, wght=700, emb=0.0, outline=1.0, margin=6)

_cache = {}


def _font(size, wght):
    k = (size, wght)
    if k not in _cache:
        f = ImageFont.truetype(FONT_PATH, size)
        f.set_variation_by_axes([wght])
        _cache[k] = f
    return _cache[k]


def style_for(fid, h):
    st = dict(STYLES.get(fid, DEFAULT_STYLE))
    s = h / st['h_ref']
    for k in ('ink', 'emb', 'outline', 'margin'):
        st[k] *= s
    return st


def _ink_bbox(a, thr=40):
    ys = np.nonzero(a.max(1) > thr)[0]
    xs = np.nonzero(a.max(0) > thr)[0]
    if len(ys) == 0:
        return None
    return xs[0], ys[0], xs[-1] + 1, ys[-1] + 1


_size_cache = {}


def _pixel_size(st):
    """font px size (at SS) so that '田' ink height == st['ink'] * SS"""
    key = (round(st['ink'], 2), st['wght'])
    if key not in _size_cache:
        size = int(st['ink'] * SS * 1.1)
        for _ in range(8):
            a = _raw('田', size, st['wght'], 0)
            x0, y0, x1, y1 = _ink_bbox(a)
            size = max(8, round(size * st['ink'] * SS / (y1 - y0)))
        _size_cache[key] = size
    return _size_cache[key]


def _raw(ch, size, wght, stroke):
    f = _font(size, wght)
    pad = size // 2 + stroke + 4
    im = Image.new('L', (size * 2 + pad * 2, size * 2 + pad * 2))
    ImageDraw.Draw(im).text((pad, pad), ch, font=f, fill=255, stroke_width=stroke, stroke_fill=255)
    return np.array(im)


def _down(a):
    h, w = a.shape
    a = a[:h - h % SS, :w - w % SS].astype(np.float32)
    return a.reshape(h // SS, SS, w // SS, SS).mean((1, 3))


def render_glyph(ch, fid, h):
    """-> (RG uint8 array [h, adv, 2], advance width)"""
    st = style_for(fid, h)
    size = _pixel_size(st)
    emb = int(round(st['emb'] * SS))
    out = int(round((st['emb'] + st['outline']) * SS))
    body = _raw(ch, size, st['wght'], emb)
    outl = _raw(ch, size, st['wght'], out) if out > emb else body
    # vertical placement: reference ideograph centred in the cell (same origin for every char)
    ref = _raw('田', size, st['wght'], emb)
    rx0, ry0, rx1, ry1 = _ink_bbox(ref)
    ref_cy = (ry0 + ry1) / 2
    bb = _ink_bbox(outl)
    H = h * SS
    full = 0xAC00 <= ord(ch) <= 0xD7A3 or 0x3000 <= ord(ch) <= 0x9FFF or 0xFF00 <= ord(ch) <= 0xFFEF
    # Japanese text relies on negative kerning; Hangul gets tighter side bearings instead (text kerning is 0)
    margin = int(round(st['margin'] * (HANGUL_MARGIN if full else 1.0) * SS))
    if bb is None:  # blank
        adv = int(round((rx1 - rx0) / SS / 2 + 2 * st['margin']))
        return np.zeros((h, adv, 2), np.uint8), adv
    x0, _, x1, _ = bb
    if full:  # fixed full-width box, centred like the reference ideograph
        box_w = (rx1 - rx0) + (out - emb) * 2
        cx = (x0 + x1) / 2
        left = cx - box_w / 2
        width = box_w
    else:
        left = x0
        width = x1 - x0
    adv_ss = int(np.ceil((width + 2 * margin) / SS)) * SS
    ox = int(round(left - (adv_ss - width) / 2))
    oy = int(round(ref_cy - H / 2 - 0.02 * H))  # originals sit ~2% below centre
    canvas_b = np.zeros((H, adv_ss), np.uint8)
    canvas_o = np.zeros((H, adv_ss), np.uint8)
    for src, dst in ((body, canvas_b), (outl, canvas_o)):
        sy0, sx0 = max(oy, 0), max(ox, 0)
        sy1, sx1 = min(oy + H, src.shape[0]), min(ox + adv_ss, src.shape[1])
        dst[sy0 - oy:sy1 - oy, sx0 - ox:sx1 - ox] = src[sy0:sy1, sx0:sx1]
    g = _down(canvas_b)
    r = np.maximum(_down(canvas_o), g)
    rg = np.stack([r, g], -1).round().clip(0, 255).astype(np.uint8)
    return rg, adv_ss // SS

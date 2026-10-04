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
    5:  dict(h_ref=53,  ink=29.5, wght=900, emb=0.0, outline=1.0, margin=5),
    7:  dict(h_ref=57,  ink=31,   wght=450, emb=0.0, outline=1.0, margin=6),
    8:  dict(h_ref=246, ink=144,  wght=900, emb=2.0, outline=0.0, margin=12),
    10: dict(h_ref=86,  ink=49.5, wght=900, emb=0.8, outline=1.0, margin=5),
}
HANGUL_MARGIN = 0.5
DEFAULT_STYLE = dict(h_ref=57, ink=33, wght=700, emb=0.0, outline=1.0, margin=6)


def redraw(fid, ch):
    """원본 글리프를 재사용하지 않고 Noto 로 다시 그릴 글자인가.
    한글이 쓰이는 폰트(STYLES)에서는 가나·한자를 뺀 모든 글자(영문·숫자·기호·그리스 문자 등)를
    한글과 같은 글꼴로 맞춘다. 한글이 없는 폰트(크레디트·저작권 표기 등)는 원본 그대로 둔다."""
    o = ord(ch)
    return fid in STYLES and not (0x3040 <= o <= 0x30FF or 0x4E00 <= o <= 0x9FFF)

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


def _hdilate(a, r):
    """가로 방향으로만 r 픽셀 굵게(덧칠). 사방으로 굵게 하면 ㅌ·ㅂ·ㅊ처럼 가로획이 촘촘한
    자모의 틈이 막히므로, 세로획만 두껍게 하고 가로획 사이 틈은 그대로 둔다."""
    if r <= 0:
        return a
    out = a.copy()
    for s in range(1, r + 1):
        out[:, s:] = np.maximum(out[:, s:], a[:, :-s])
        out[:, :-s] = np.maximum(out[:, :-s], a[:, s:])
    return out


def _down(a):
    h, w = a.shape
    a = a[:h - h % SS, :w - w % SS].astype(np.float32)
    return a.reshape(h // SS, SS, w // SS, SS).mean((1, 3))


def render_glyph(ch, fid, h, fixed_adv=None, max_adv=None):
    """-> (RG uint8 array [h, adv, 2], advance width)
    fixed_adv: 진행 폭을 이 값(px)으로 고정하고 글자를 가운데 둔다(숫자를 원본처럼 고정폭으로).
    max_adv: 진행 폭이 이 값(px, 원본 글리프 폭)을 넘지 않게 한다(줄 길이가 원본보다 늘지 않게)."""
    st = style_for(fid, h)
    size = _pixel_size(st)
    emb = int(round(st['emb'] * SS))
    out = int(round((st['emb'] + st['outline']) * SS))
    # 덧칠(emb)은 가로로만, 외곽선(out - emb)은 사방으로
    body = _hdilate(_raw(ch, size, st['wght'], 0), emb)
    outl = _hdilate(_raw(ch, size, st['wght'], out - emb), emb) if out > emb else body
    # vertical placement: reference ideograph centred in the cell (same origin for every char)
    ref = _hdilate(_raw('田', size, st['wght'], 0), emb)
    rx0, ry0, rx1, ry1 = _ink_bbox(ref)
    ref_cy = (ry0 + ry1) / 2
    bb = _ink_bbox(outl)
    H = h * SS
    # 한글·가나·한자만 전각 칸. CJK 구두점(「」、。 등)은 영문처럼 잉크 기준 폭으로 둔다
    full = 0xAC00 <= ord(ch) <= 0xD7A3 or 0x3040 <= ord(ch) <= 0x9FFF
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
        adv_ss = int(np.ceil((width + 2 * margin) / SS)) * SS
        ox = int(round(left - (adv_ss - width) / 2))
    else:
        # 영문·숫자·기호: 글꼴에 설계된 진행 폭(좌우 여백 포함)에 외곽선 두께만 더한다
        f = _font(size, st['wght'])
        nat = f.getlength(ch)
        ink = x1 - x0
        natural = nat + 2 * out
        want = natural
        if fixed_adv:
            want = fixed_adv * SS
        elif max_adv:
            want = min(want, max_adv * SS)
        want = max(want, ink)
        adv_ss = int(np.ceil(want / SS)) * SS
        if want >= natural:
            # 글꼴 원점을 칸 가운데에: 외곽선 래스터 왼쪽 끝 x0 는 글꼴 bbox 왼쪽 - out 에 해당
            pen = (adv_ss - nat) / 2
            ox = int(round(x0 - (pen + f.getbbox(ch)[0] - out)))
        else:
            # 원본 폭으로 줄였을 때는 잉크를 가운데에
            ox = int(round(x0 - (adv_ss - ink) / 2))
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

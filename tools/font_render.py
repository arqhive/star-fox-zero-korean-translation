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
HANGUL_MARGIN = 0.5   # 새로 그리는 가나·한자·전각 기호와 한글 칸의 여백 배율
# 게임은 글자마다 폰트 메트릭 b 만큼 다음 글자를 당겨 찍는다(h_ref 기준 px, 각 MCD 폰트 표의 값).
TRACK = {1: -5, 2: -8, 3: -9, 4: -11, 5: -6, 7: -6, 8: -19, 10: -1}
# 한글 배치. 칸 폭(진행 폭)은 처음부터 쓰던 같은 폭 칸 그대로 두고, 당김이 센 폰트만 글자를 작게 그려
# 칸 가운데에 둔다. 줄 길이가 이전 빌드와 같아서 작은 설정 상자도 그대로 들어가고, 글자가 줄어든 만큼
# 글자 사이 틈이 생긴다(100% 에서는 폰트 2·3·5·7 이 실기에서 겹쳤음, 2026-10-05).
# 비례폭(HANGUL_GAP)은 틈이 고르지만 줄이 길어져 작은 상자에서 넘쳤다 → None 으로 둔다.
HANGUL_GAP = None
HANGUL_SCALE = {1: 0.88, 2: 0.88, 3: 0.88, 5: 0.88, 7: 0.88}   # 폰트별 한글 크기 배율(없으면 1.0)
# 한글 번역 MCD 에서 바꾸는 띄어쓰기 폭(폰트 메트릭 w). 폰트 3 은 원본이 4px 라 당김(-9)에 묻혀
# 띄어쓰기가 사라진다(「섹터α우주」). 19 는 제목 줄이 너무 길어져서 12 로(이전 빌드보다 최대 +16px).
SPACE_W = {3: 12.0}


def hangul_scale(fid):
    return HANGUL_SCALE.get(fid, 1.0) if isinstance(HANGUL_SCALE, dict) else HANGUL_SCALE
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


def render_glyph(ch, fid, h):
    """-> (RG uint8 array [h, adv, 2], advance width)"""
    st = style_for(fid, h)
    hangul = 0xAC00 <= ord(ch) <= 0xD7A3
    if hangul:
        st['ink'] *= hangul_scale(fid)
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
    full = 0xAC00 <= ord(ch) <= 0xD7A3 or 0x3000 <= ord(ch) <= 0x9FFF or 0xFF00 <= ord(ch) <= 0xFFEF
    # 원문 커닝은 사실상 0 이다(예전 '일본어는 음수 커닝' 가정은 틀렸음, 2026-10-05 측정)
    margin = int(round(st['margin'] * (HANGUL_MARGIN if full else 1.0) * SS))
    if bb is None:  # blank
        adv = int(round((rx1 - rx0) / SS / 2 + 2 * st['margin']))
        return np.zeros((h, adv, 2), np.uint8), adv
    x0, _, x1, _ = bb
    if hangul and HANGUL_GAP is not None:  # 한글 비례폭
        h_ref = STYLES.get(fid, DEFAULT_STYLE)['h_ref']
        side = (HANGUL_GAP * h - TRACK.get(fid, 0) * h / h_ref) / 2 * SS
        left = x0
        width = x1 - x0
        adv_ss = int(np.ceil((width + 2 * side) / SS)) * SS
        ox = int(round(left - (adv_ss - width) / 2))
        margin = None
    elif full:  # fixed full-width box, centred like the reference ideograph
        if hangul and hangul_scale(fid) != 1.0:
            # 칸 폭은 원래 크기(100%) 기준 그대로 두고 글자만 작게 그려 가운데에 둔다.
            # 줄 길이는 이전과 같아서(작은 설정 상자도 그대로 들어감) 글자가 줄어든 만큼 틈이 생긴다.
            st0 = style_for(fid, h)
            r0 = _ink_bbox(_hdilate(_raw('田', _pixel_size(st0), st0['wght'], 0), emb))
            box_w = (r0[2] - r0[0]) + (out - emb) * 2
        else:
            box_w = (rx1 - rx0) + (out - emb) * 2
        cx = (x0 + x1) / 2
        left = cx - box_w / 2
        width = box_w
    else:
        left = x0
        width = x1 - x0
    if margin is not None:
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

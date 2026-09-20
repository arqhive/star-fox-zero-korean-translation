# 엔딩 청구서 텍스처(ui_ending.dat ending.wta #1, BC1 1024x1024) 한글화
#   python invoice_patch.py  → invoice_preview.png (원본/수정본 비교)
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import wtex  # pos_map / wta_entries_any / decode

HERE = os.path.dirname(os.path.abspath(__file__))
from paths import NOTO, PEN
SS = 4
TEX_INDEX = 1

PRINT = (40, 47, 34)
# name: (ink bbox of the original text x0,y0,x1,y1), text, font, weight, align, colour, extra
ITEMS = [
    ('title',    (431, 55, 590, 115), '청구서',              'noto', 900, 'center', (74, 145, 15), {'original_shading': True}),
    ('koneria',  (169, 159, 411, 210), '코네리아 방위',       'pen', 0,   'center', (8, 10, 8), {'line': 211, 'scale': 0.90}),
    ('gun',      (470, 194, 490, 213), '군',                 'noto', 700, 'left',   PRINT, {}),
    ('pepper',   (586, 164, 800, 210), '페퍼 장군',           'pen', 0,   'center', (20, 22, 20), {'line': 211, 'scale': 0.94}),
    ('den',      (843, 194, 863, 213), '귀하',               'noto', 700, 'left',   PRINT, {}),
    ('kaki',     (583, 232, 881, 252), '다음 금액을 청구합니다.', 'noto', 700, 'right',  PRINT, {}),
    ('andross',  (176, 279, 342, 328), '안돌프',              'pen', 0,   'center', (20, 22, 20), {'line': 329, 'scale': 0.92}),
    ('heiki',    (414, 311, 546, 331), '군 병기 격추 수',      'noto', 700, 'left',   PRINT, {}),
    ('kini',     (799, 311, 894, 331), '기에 따라,',           'noto', 700, 'left',   PRINT, {}),
    ('seikyu2',  (696, 448, 881, 468), '위 금액을 청구합니다.',  'noto', 700, 'right',  PRINT, {}),
    ('yatoware', (440, 502, 582, 522), '용병 유격대',          'noto', 900, 'center', (123, 162, 88), {'outline': (73, 92, 63)}),
    ('sign',     (340, 599, 682, 649), '폭스 맥클라우드',       'pen', 0,   'center', (20, 22, 20), {'scale': 0.96}),
]


def _font(kind, size, weight):
    if kind == 'pen':
        return ImageFont.truetype(PEN, size)
    f = ImageFont.truetype(NOTO, size)
    f.set_variation_by_axes([weight])
    return f


def _render_mask(text, kind, weight, ink_h, stroke=0):
    """alpha mask (float 0..255, at 1x) whose ink height ~= ink_h"""
    # Handwriting has unusually tall consonants/descenders: measure the actual phrase.
    ref = '한글' if kind == 'noto' else text
    size = int(ink_h * SS * 1.3)
    for _ in range(6):
        f = _font(kind, size, weight)
        im = Image.new('L', (int(f.getlength(ref)) + size * 2, size * 3))
        ImageDraw.Draw(im).text((size, size), ref, font=f, fill=255)
        ys = np.nonzero(np.array(im).max(1) > 40)[0]
        size = max(8, round(size * ink_h * SS / (ys[-1] - ys[0] + 1)))
    f = _font(kind, size, weight)
    w = int(f.getlength(text)) + size * 2
    im = Image.new('L', (w, size * 3))
    ImageDraw.Draw(im).text((size, size), text, font=f, fill=255, stroke_width=stroke, stroke_fill=255)
    a = np.array(im).astype(np.float32)
    ys = np.nonzero(a.max(1) > 10)[0]
    xs = np.nonzero(a.max(0) > 10)[0]
    a = a[ys[0]:ys[-1] + 1, xs[0]:xs[-1] + 1]
    if kind == 'pen' and not stroke:
        # Enforce the final ink height, including faint antialiasing pixels.
        target_h = max(1, int(ink_h * SS))
        target_w = max(1, round(a.shape[1] * target_h / a.shape[0]))
        a = np.array(Image.fromarray(a).resize((target_w, target_h), Image.Resampling.LANCZOS))
    h, w = a.shape
    a = np.pad(a, ((0, (-h) % SS), (0, (-w) % SS)))
    return a.reshape(a.shape[0] // SS, SS, a.shape[1] // SS, SS).mean((1, 3))


def _title_shading(rgb, box, height):
    """Recover the original green ink's vertical colour profile, not its lettering."""
    x0, y0, x1, y1 = box
    src = rgb[y0:y1 + 1, x0:x1 + 1].astype(np.float32)
    green = (src[:, :, 1] - src[:, :, 0] > 15) & (src[:, :, 1] - src[:, :, 2] > 45)
    rows = np.flatnonzero(green.sum(1) >= 8)
    if not len(rows):
        raise ValueError('Original invoice title has no usable green ink')
    colours = np.array([np.median(src[y, green[y]], axis=0) for y in rows])
    positions = np.linspace(0, len(src) - 1, height)
    return np.stack([np.interp(positions, rows, colours[:, c]) for c in range(3)], -1)[:, None, :]


def _inpaint(img, mask, iters=400):
    """Laplace fill of masked pixels from their surroundings"""
    out = img.astype(np.float32).copy()
    ys, xs = np.nonzero(mask)
    y0, y1, x0, x1 = ys.min() - 1, ys.max() + 2, xs.min() - 1, xs.max() + 2
    sub = out[y0:y1, x0:x1]
    m = mask[y0:y1, x0:x1]
    # start from row-wise mean of unmasked pixels to converge faster
    for c in range(3):
        ch = sub[:, :, c]
        rowmean = np.where(m, np.nan, ch)
        rm = np.nanmean(rowmean, axis=1)
        ch[m] = np.broadcast_to(rm[:, None], ch.shape)[m]
    for _ in range(iters):
        avg = (np.roll(sub, 1, 0) + np.roll(sub, -1, 0) + np.roll(sub, 1, 1) + np.roll(sub, -1, 1)) / 4
        sub[m] = avg[m]
    return out


def paint(rgb):
    img = rgb.astype(np.float32).copy()
    lum = rgb.mean(2)
    sat = rgb.max(2) - rgb.min(2)
    for name, (x0, y0, x1, y1), text, kind, weight, align, colour, extra in ITEMS:
        # 1) erase original ink (dark or green pixels) inside the padded bbox, keep rows of the underline
        px0, py0, px1, py1 = x0 - 3, y0 - 3, x1 + 4, y1 + 2
        region = np.zeros(lum.shape, bool)
        region[py0:py1, px0:px1] = True
        ink = region & ((lum < 200) | (sat > 40))
        # grow the mask by 2px to remove anti-aliased halos
        grown = ink.copy()
        for _ in range(2):
            g = grown.copy()
            g[1:] |= grown[:-1]; g[:-1] |= grown[1:]; g[:, 1:] |= grown[:, :-1]; g[:, :-1] |= grown[:, 1:]
            grown = g & region
        if 'line' in extra:  # fill through the underline rows too, so its grey does not bleed upwards
            ly = extra['line']
            grown[ly:ly + 4, px0:px1] = True
        img = _inpaint(img, grown)
        if 'line' in extra:  # redraw the underline rows from a clean stretch of the same line
            ly = extra['line']
            clean = [x for x in range(px0, px1) if not ink[ly - 4:ly + 5, x].any()]
            if len(clean) < 5:  # fall back to the stretch just left of the text
                clean = list(range(px0 - 12, px0))
            prof = np.median(rgb[ly:ly + 4, clean].astype(np.float32), axis=1)
            img[ly:ly + 4, px0:px1] = prof[:, None, :]
        # 2) render Korean with the same ink height
        ink_h = y1 - y0 + 1
        if kind == 'noto':
            ink_h = int(round(ink_h * 0.95))
        ink_h = int(round(ink_h * extra.get('scale', 1.0)))
        mask = _render_mask(text, kind, weight, ink_h)
        if kind == 'pen':
            max_h = min(y1 - y0 + 1, extra.get('line', y1 + 4) - 3 - y0)
            max_w = x1 - x0 + 1
            scale = min(1.0, max_h / mask.shape[0], max_w / mask.shape[1])
            if scale < 1:
                mask = np.array(Image.fromarray(mask).resize(
                    (max(1, int(mask.shape[1] * scale)), max(1, int(mask.shape[0] * scale))),
                    Image.Resampling.LANCZOS))
            mask = mask.clip(0, 255)
        h, w = mask.shape
        cy = (y0 + y1) / 2
        ty = int(round(cy - h / 2))
        if 'line' in extra:  # sit on the underline like handwriting
            ty = extra['line'] - 3 - h
        if align == 'center':
            tx = int(round((x0 + x1) / 2 - w / 2))
        elif align == 'right':
            tx = x1 + 1 - w
        else:
            tx = x0
        if 'outline' in extra:
            om = _render_mask(text, kind, weight, ink_h, stroke=SS)
            oh, ow = om.shape
            oy, ox = ty - (oh - h) // 2, tx - (ow - w) // 2
            a = (om / 255.0)[:, :, None]
            img[oy:oy + oh, ox:ox + ow] = img[oy:oy + oh, ox:ox + ow] * (1 - a) + np.array(extra['outline']) * a
        a = (mask / 255.0)[:, :, None]
        fill = _title_shading(rgb, (x0, y0, x1, y1), h) if extra.get('original_shading') else np.array(colour)
        img[ty:ty + h, tx:tx + w] = img[ty:ty + h, tx:tx + w] * (1 - a) + fill * a
    return img.round().clip(0, 255).astype(np.uint8)


# ---------------- BC1 ----------------
def _to565(c):
    c = np.clip(np.round(c), 0, 255).astype(int)
    return (c[..., 0] * 31 + 127) // 255 << 11 | (c[..., 1] * 63 + 127) // 255 << 5 | (c[..., 2] * 31 + 127) // 255


def _from565(v):
    r = (v >> 11) & 31; g = (v >> 5) & 63; b = v & 31
    return np.stack([(r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)], -1).astype(np.float32)


def bc1_encode_block(px):
    """px: (16,3) float -> 8 bytes (opaque 4-colour mode)"""
    mean = px.mean(0)
    d = px - mean
    if np.abs(d).max() < 1:
        axis = np.array([1.0, 1.0, 1.0]) / np.sqrt(3)
    else:
        _, _, vt = np.linalg.svd(d, full_matrices=False)
        axis = vt[0]
    t = d @ axis
    best = None
    for lo_q, hi_q in ((0, 100), (3, 97), (8, 92)):
        lo = mean + axis * np.percentile(t, lo_q)
        hi = mean + axis * np.percentile(t, hi_q)
        c0, c1 = int(_to565(hi)), int(_to565(lo))
        if c0 < c1:
            c0, c1 = c1, c0
        if c0 == c1:
            if c0 > 0:
                c1 = c0 - 1
            else:
                c0 = 1
        e0, e1 = _from565(np.array(c0)), _from565(np.array(c1))
        pal = np.stack([e0, e1, (2 * e0 + e1) / 3, (e0 + 2 * e1) / 3])
        dist = ((px[:, None, :] - pal[None]) ** 2).sum(-1)
        idx = dist.argmin(1)
        err = dist[np.arange(16), idx].sum()
        if best is None or err < best[0]:
            best = (err, c0, c1, idx)
    _, c0, c1, idx = best
    bits = 0
    for i, v in enumerate(idx):
        bits |= int(v) << (2 * i)
    return (int(c0).to_bytes(2, 'little') + int(c1).to_bytes(2, 'little') + bits.to_bytes(4, 'little'))


def build_ending_wtp(dat_dir):
    wta = open(os.path.join(dat_dir, 'ending.wta'), 'rb').read()
    wtp = bytearray(open(os.path.join(dat_dir, 'ending.wtp'), 'rb').read())
    te = wtex.wta_entries_any(wta)[TEX_INDEX]
    assert (te['w'], te['h'], te['fmt']) == (1024, 1024, 0x431), te
    blob = bytes(wtp[te['off']:te['off'] + te['isz']])
    orig = np.array(wtex.decode_surface(te, blob).convert('RGB'))
    new = paint(orig)
    idx, unit, bw, bh = wtex.pos_map(te['w'], te['h'], te['fmt'], te['tile'], te['swz'])
    raw = bytearray(blob)
    changed = 0
    diff = (orig != new).any(2)
    for by in range(bh):
        for bx in range(bw):
            if not diff[by * 4:by * 4 + 4, bx * 4:bx * 4 + 4].any():
                continue
            block = new[by * 4:by * 4 + 4, bx * 4:bx * 4 + 4].reshape(16, 3).astype(np.float32)
            p = int(idx[by * bw + bx]) * unit
            raw[p:p + 8] = bc1_encode_block(block)
            changed += 1
    wtp[te['off']:te['off'] + te['isz']] = raw
    result = np.array(wtex.decode_surface(te, bytes(raw)).convert('RGB'))
    return bytes(wtp), orig, new, result, changed


if __name__ == '__main__':
    d = os.path.join(HERE, '..', 'work', 'orig', 'ui__ui_ending.dat')
    wtp, orig, new, result, changed = build_ending_wtp(d)
    print('re-encoded blocks', changed, 'mean abs err vs painted', float(np.abs(result.astype(int) - new).mean()))
    crop = (40, 30, 985, 690)
    a = Image.fromarray(orig).crop(crop)
    b = Image.fromarray(result).crop(crop)
    sheet = Image.new('RGB', (a.width, a.height * 2 + 10))
    sheet.paste(a, (0, 0)); sheet.paste(b, (0, a.height + 10))
    sheet.save(os.path.join(HERE, 'invoice_preview.png'))
    b.save(os.path.join(HERE, 'invoice_after.png'))

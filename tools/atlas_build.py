# Build translated mess*.mcd + glyph atlas (.wta/.wtp) for one UI DAT folder.
import os, struct, json
import numpy as np
import addrlib
import wtex
import font_render
from mcd_tool import MCD
from mcd_text import apply_translations

GAP = 2    # pixels between glyphs (positions stay on a 4px grid)
ALIGN = 4
MAX_DIM = 2048


def _align(v):
    return (v + ALIGN - 1) // ALIGN * ALIGN


def pack(sizes, W, H):
    """skyline bottom-left packing on a 4px grid; sizes: list of (w, h) -> [(x, y)] or None"""
    order = sorted(range(len(sizes)), key=lambda i: (-sizes[i][1], -sizes[i][0]))
    sky = [[0, 0, W]]  # segments [x, y, width]
    pos = [None] * len(sizes)
    for i in order:
        w, h = _align(sizes[i][0] + GAP), _align(sizes[i][1] + GAP)
        best = None
        for si in range(len(sky)):
            x = sky[si][0]
            if x + w > W:
                break
            # max height over the span [x, x+w)
            y, rem, sj = 0, w, si
            while rem > 0:
                y = max(y, sky[sj][1])
                rem -= sky[sj][2]
                sj += 1
            if y + sizes[i][1] > H:
                continue
            if best is None or (y + h, x) < (best[0] + h, best[1]):
                best = (y, x, si)
        if best is None:
            return None
        y, x, si = best
        pos[i] = (x, y)
        # update skyline
        new = [x, y + h, w]
        out, end = [], x + w
        for seg in sky:
            sx, sy, sw = seg
            if sx + sw <= x or sx >= end:
                out.append(seg)
            else:
                if sx < x:
                    out.append([sx, sy, x - sx])
                if sx + sw > end:
                    out.append([end, sy, sx + sw - end])
        out.append(new)
        out.sort()
        merged = []
        for seg in out:
            if merged and merged[-1][1] == seg[1] and merged[-1][0] + merged[-1][2] == seg[0]:
                merged[-1][2] += seg[2]
            else:
                merged.append(seg)
        sky = merged
    return pos


def candidate_dims(w0, h0):
    dims = set()
    w = 64
    while w <= MAX_DIM:
        h = 64
        while h <= MAX_DIM:
            if w >= w0 and h >= h0:
                dims.add((w, h))
            h *= 2
        w *= 2
    return sorted(dims, key=lambda d: (d[0] * d[1], d[1]))


def encode_rg8(img, info_src):
    H, W = img.shape[:2]
    info = addrlib.getSurfaceInfo(7, W, H, 1, 1, info_src['tile'], 0, 0)
    data = img.astype(np.uint8).tobytes()
    assert len(data) == info.surfSize, (len(data), info.surfSize)
    return addrlib.swizzle(W, H, info.height, 7, info_src['tile'], info_src['swz'], info.pitch, 16, data), info


def patch_wta(wta, W, H, isz, pitch):
    b = bytearray(wta)
    i = wtex.wta_info(wta)
    s = i['inft']
    old_isz = struct.unpack('>I', b[s + 0x20:s + 0x24])[0]
    old_size = struct.unpack('>I', b[i['sizt']:i['sizt'] + 4])[0]  # = image size + 0x11c in originals
    struct.pack_into('>I', b, i['sizt'], old_size - old_isz + isz)
    struct.pack_into('>II', b, s + 4, W, H)
    struct.pack_into('>I', b, s + 0x20, isz)
    struct.pack_into('>I', b, s + 0x3C, pitch)
    # texture register words (see memory notes): word0 = (w-1)<<19 | (w/8-1)<<8 | low byte
    w0, w1 = struct.unpack('>II', b[s + 0x88:s + 0x90])
    w0 = ((W - 1) << 19) | ((W // 8 - 1) << 8) | (w0 & 0xFF)
    w1 = (w1 & ~0x1FFF) | (H - 1)
    struct.pack_into('>II', b, s + 0x88, w0, w1)
    return bytes(b)


def build(dat_dir, rows, log=print):
    base = [f for f in os.listdir(dat_dir) if f.endswith('.mcd')][0][:-4]
    p = os.path.join(dat_dir, base)
    orig_mcd = open(p + '.mcd', 'rb').read()
    wta = open(p + '.wta', 'rb').read()
    info = wtex.wta_info(wta)
    if info['fmt'] != 7:
        raise RuntimeError('%s: RG8 이외 포맷(0x%x) 아틀라스는 지원하지 않음' % (base, info['fmt']))
    atlas_npy = p + '_atlas.npy'
    if os.path.exists(atlas_npy):
        orig_img = np.load(atlas_npy)
    else:
        orig_img, _ = wtex.decode(wta, open(p + '.wtp', 'rb').read())
    oH, oW = orig_img.shape[:2]

    m = MCD(orig_mcd)
    orig = {}  # (font, char) -> (pixels, glyph tuple)
    for f, c, gi in m.symbols:
        g = struct.unpack('>I9f', m.glyphs[gi])
        x1, y1, x2, y2 = round(g[1] * oW), round(g[2] * oH), round(g[3] * oW), round(g[4] * oH)
        orig[(f, c)] = (orig_img[y1:y2, x1:x2], g)
    tex_hash = struct.unpack('>I', m.glyphs[0][:4])[0] if m.glyphs else info['hash']

    used = apply_translations(m, rows, lambda f, c: b'')
    tiles, metas, new_chars = [], [], 0
    for f, c in used:
        if (f, c) in orig:
            px, g = orig[(f, c)]
            tiles.append(px)
            metas.append(g[5:])
        else:
            fm = struct.unpack('>I4f', m.font_metrics(f))
            fh = int(round(fm[2]))
            px, adv = font_render.render_glyph(chr(c), f, fh)
            tiles.append(px)
            metas.append((float(adv), float(fh), 0.0, fm[3], fm[4]))
            new_chars += 1

    sizes = [(t.shape[1], t.shape[0]) for t in tiles]
    for W, H in candidate_dims(oW, oH):
        pos = pack(sizes, W, H)
        if pos:
            break
    else:
        raise RuntimeError('%s: 글리프 %d개가 %dx%d 안에 들어가지 않음' % (base, len(tiles), MAX_DIM, MAX_DIM))

    img = np.zeros((H, W, 2), np.uint8)
    glyphs = []
    for t, (x, y), meta in zip(tiles, pos, metas):
        h, w = t.shape[:2]
        img[y:y + h, x:x + w] = t
        glyphs.append(struct.pack('>I9f', tex_hash, x / W, y / H, (x + w) / W, (y + h) / H, *meta))
    m.glyphs = glyphs

    wtp_img, sinfo = encode_rg8(img, info)
    wtp = wtp_img + b'\0' * 0x80
    new_wta = patch_wta(wta, W, H, len(wtp_img), sinfo.pitch) if (W, H) != (oW, oH) else wta
    log('%-22s 글리프 %4d (신규 %4d)  텍스처 %dx%d%s' % (base, len(used), new_chars, W, H,
        '' if (W, H) == (oW, oH) else '  ← 원본 %dx%d에서 확대' % (oW, oH)))
    return {base + '.mcd': m.build(), base + '.wta': new_wta, base + '.wtp': wtp}, img

# WTA/WTP (single GX2 texture per mess*.wta) helpers
import struct, os, numpy as np
from PIL import Image
import addrlib
_maps = {}
def wta_info(wta):
    cnt = struct.unpack('>I', wta[8:12])[0]
    offt, sizt, flt, idt, inft = struct.unpack('>5I', wta[12:32])
    assert cnt == 1, cnt
    off = struct.unpack('>I', wta[offt:offt+4])[0]
    size = struct.unpack('>I', wta[sizt:sizt+4])[0]
    texhash = struct.unpack('>I', wta[idt:idt+4])[0]
    g = struct.unpack('>16I', wta[inft:inft+64])
    keys = 'dim w h depth mips fmt aa use isz iptr msz mptr tile swz align pitch'.split()
    d = dict(zip(keys, g)); d.update(off=off, size=size, hash=texhash, inft=inft, sizt=sizt)
    return d
def decode(wta, wtp):
    i = wta_info(wta)
    fmt = i['fmt']
    info = addrlib.getSurfaceInfo(fmt, i['w'], i['h'], 1, 1, i['tile'], 0, 0)
    bpp = addrlib.surfaceGetBitsPerPixel(fmt)
    raw = addrlib.deswizzle(i['w'], i['h'], info.height, fmt, i['tile'], i['swz'], info.pitch, bpp, wtp[i['off']:i['off']+i['isz']])
    if fmt == 7:
        return np.frombuffer(raw, np.uint8).reshape(i['h'], i['w'], 2).copy(), i
    n = {0x31: 1, 0x32: 2, 0x33: 3, 0x34: 4, 0x35: 5}[fmt & 0xff]
    return np.array(Image.frombytes('RGBA', (i['w'], i['h']), raw, 'bcn', n)), i


# ---- multi-texture WTA (stride 0xC0 GX2 surface records) ----
def wta_entries(wta):
    cnt = struct.unpack('>I', wta[8:12])[0]
    offt, sizt, flt, idt, inft = struct.unpack('>5I', wta[12:32])
    keys = 'dim w h depth mips fmt aa use isz iptr msz mptr tile swz align pitch'.split()
    out = []
    for i in range(cnt):
        s = inft + i * 0xC0
        d = dict(zip(keys, struct.unpack('>16I', wta[s:s + 64])))
        d.update(index=i, inft=s,
                 off=struct.unpack('>I', wta[offt + 4 * i:offt + 4 * i + 4])[0],
                 hash=struct.unpack('>I', wta[idt + 4 * i:idt + 4 * i + 4])[0])
        out.append(d)
    return out


def decode_entry(e, wtp):
    fmt = e['fmt']
    info = addrlib.getSurfaceInfo(fmt, e['w'], e['h'], 1, 1, e['tile'], 0, 0)
    bpp = addrlib.surfaceGetBitsPerPixel(fmt)
    raw = addrlib.deswizzle(e['w'], e['h'], info.height, fmt, e['tile'], e['swz'], info.pitch, bpp,
                            wtp[e['off']:e['off'] + e['isz']])
    return raw, info


# ---- 범용 GX2 텍스처 디코드 (pos_map 캐시 사용) ----
_maps = {}


def pos_map(w, h, fmt, tile, swz):
    """deswizzle index map (in pixel/block units), cached per surface layout"""
    key = (w, h, fmt, tile, swz)
    if key in _maps:
        return _maps[key]
    info = addrlib.getSurfaceInfo(fmt, w, h, 1, 1, tile, 0, 0)
    bpp = addrlib.surfaceGetBitsPerPixel(fmt)
    bw, bh = w, h
    if fmt & 0xFF in (0x31, 0x32, 0x33, 0x34, 0x35):
        bw, bh = (w + 3) // 4, (h + 3) // 4
    unit = bpp // 8
    pipe = (swz >> 8) & 1
    bank = (swz >> 9) & 3
    idx = np.empty(bw * bh, np.int64)
    k = 0
    for y in range(bh):
        for x in range(bw):
            if tile in (0, 1):
                p = (y * info.pitch + x) * unit
            elif tile in (2, 3):
                p = addrlib.computeSurfaceAddrFromCoordMicroTiled(x, y, bpp, info.pitch, tile)
            else:
                p = addrlib.computeSurfaceAddrFromCoordMacroTiled(x, y, bpp, info.pitch, info.height, tile, pipe, bank)
            idx[k] = p // unit
            k += 1
    _maps[key] = (idx, unit, bw, bh)
    return _maps[key]


def decode_surface(e, blob):
    fmt = e['fmt']
    idx, unit, bw, bh = pos_map(e['w'], e['h'], fmt, e['tile'], e['swz'])
    need = (idx.max() + 1) * unit
    data = np.frombuffer(blob[:need].ljust(need, b'\0'), np.uint8).reshape(-1, unit)
    raw = data[idx].tobytes()
    f = fmt & 0xFF
    size = (e['w'], e['h'])
    if f in (0x31, 0x32, 0x33, 0x34, 0x35):
        n = {0x31: 1, 0x32: 2, 0x33: 3, 0x34: 4, 0x35: 5}[f]
        mode = 'RGBA' if n <= 3 else ('L' if n == 4 else 'RGB')
        im = Image.frombytes(mode, size, raw, 'bcn', n)
    elif f == 0x1A:
        im = Image.frombytes('RGBA', size, raw)
    elif f == 0x07:
        a = np.frombuffer(raw, np.uint8).reshape(e['h'], e['w'], 2)
        im = Image.fromarray(np.stack([a[:, :, 0], a[:, :, 1], np.zeros_like(a[:, :, 0])], -1))
    elif f == 0x01:
        im = Image.frombytes('L', size, raw)
    else:
        return None
    return im


def wta_entries_any(wta):
    if wta[:4] not in (b'\0BTW', b'WTB\0') or len(wta) < 32:
        return []
    cnt = struct.unpack('>I', wta[8:12])[0]
    if cnt == 0 or cnt > 4096:
        return []
    offt, sizt, flt, idt, inft = struct.unpack('>5I', wta[12:32])
    keys = 'dim w h depth mips fmt aa use isz iptr msz mptr tile swz align pitch'.split()
    out = []
    for i in range(cnt):
        s = inft + i * 0xC0
        if s + 64 > len(wta):
            break
        d = dict(zip(keys, struct.unpack('>16I', wta[s:s + 64])))
        d['off'] = struct.unpack('>I', wta[offt + 4 * i:offt + 4 * i + 4])[0]
        d['i'] = i
        out.append(d)
    return out



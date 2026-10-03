# 굵기 검사: python stroke_check.py
#  폰트ID별로 원본 일본어 글리프와 한글 글리프의 평균 획 두께(px)를 비교한다.
#  비율이 1.00 에서 크게 벗어나는 폰트는 font_render.STYLES 의 wght/emb 를 조정한다.
#  아틀라스는 메모리에서만 만들고 파일은 쓰지 않는다(빌드 아님).
import os, sys, json, struct
import numpy as np
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths, wtex, atlas_build, font_render
from mcd_tool import MCD

KEYS = ['ui__ui_core', 'ui__ui_hud', 'ui__ui_ending', 'ui__ui_msg_area_3', 'ui__ui_msg_common', 'ui__ui_pause']


def is_ja(c):
    return 0x3041 <= c <= 0x30FF or 0x4E00 <= c <= 0x9FFF


def is_ko(c):
    return 0xAC00 <= c <= 0xD7A3


def stroke_w(g):
    """G 채널(본체) → 획 두께. 거리변환 능선값 x2 의 평균을 문턱값 5개로 평균"""
    ws = []
    for thr in (64, 96, 128, 160, 192):
        m = g > thr
        if m.sum() < 20:
            return None
        dt = ndimage.distance_transform_edt(m)
        ridge = (dt >= ndimage.maximum_filter(dt, size=3)) & (dt >= 1)
        if not ridge.any():
            return None
        ws.append(2 * float(dt[ridge].mean()))
    return float(np.mean(ws))


def glyphs(mcd, atlas, pred):
    m = MCD(mcd)
    H, W = atlas.shape[:2]
    out = {}
    for f, c, gi in m.symbols:
        if pred(c):
            g = struct.unpack('>I9f', m.glyphs[gi])
            x1, y1, x2, y2 = round(g[1] * W), round(g[2] * H), round(g[3] * W), round(g[4] * H)
            out.setdefault(f, []).append(atlas[y1:y2, x1:x2, 1])
    return out


def main():
    acc = {}
    for key in KEYS:
        d = os.path.join(paths.ORIG, key + '.dat')
        if not os.path.isdir(d):
            print('%s: 원본 추출본 없음 (patch.py 를 한 번 돌려 work/orig 를 만들 것)' % key)
            continue
        base = [f for f in os.listdir(d) if f.endswith('.mcd')][0][:-4]
        p = os.path.join(d, base)
        npy = p + '_atlas.npy'
        oimg = np.load(npy) if os.path.exists(npy) else wtex.decode(
            open(p + '.wta', 'rb').read(), open(p + '.wtp', 'rb').read())[0]
        rows = json.load(open(os.path.join(paths.TEXT, key + '.json'), encoding='utf-8'))
        files, nimg = atlas_build.build(d, rows, log=lambda *a: None)
        for f, lst in glyphs(open(p + '.mcd', 'rb').read(), oimg, is_ja).items():
            acc.setdefault(f, [[], []])[0].extend(lst)
        for f, lst in glyphs(files[base + '.mcd'], nimg, is_ko).items():
            acc.setdefault(f, [[], []])[1].extend(lst)
    print('폰트  원본n 한글n   원본획  한글획   비율  wght/emb')
    for f in sorted(acc):
        a = [w for w in map(stroke_w, acc[f][0]) if w]
        b = [w for w in map(stroke_w, acc[f][1]) if w]
        if a and b:
            st = font_render.STYLES.get(f, font_render.DEFAULT_STYLE)
            ma, mb = np.mean(a), np.mean(b)
            print('%4d %6d %5d %8.2f %7.2f %6.2f  %s/%s' % (f, len(a), len(b), ma, mb, mb / ma, st['wght'], st['emb']))


if __name__ == '__main__':
    main()

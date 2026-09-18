"""스타폭스 제로 한글 패치 — 원본 data003.cpk 에서 한글판 data003.cpk 를 만든다.

  python tools/patch.py [원본 data003.cpk] [-o 출력폴더] [--force]

원본을 찾지 못하면 현재 폴더와 저장소 루트에서 data003.cpk 를 찾는다.
게임 데이터는 저장소에 들어 있지 않으며, 본인이 소유한 게임에서 덤프한 파일이 필요하다.
"""
import argparse, hashlib, os, shutil, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np

import paths
import atlas_build, logo_patch, invoice_patch, repack, wtex
from cpk import CPK
from datx import parse_dat
from mcd_tool import MCD
import json, glob


def sha1(path):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''):
            h.update(b)
    return h.hexdigest()


def find_source(arg):
    if arg:
        return arg
    for d in (os.getcwd(), paths.ROOT, os.path.join(paths.ROOT, '..')):
        p = os.path.join(d, paths.CPK_NAME)
        if os.path.exists(p):
            return p
    raise SystemExit('원본 %s 를 찾지 못했습니다. 경로를 인자로 넘겨 주세요.' % paths.CPK_NAME)


def load_rows():
    """번역 JSON 중 ko 가 채워진 것만"""
    rows = {}
    for jp in sorted(glob.glob(os.path.join(paths.TEXT, '*.json'))):
        key = os.path.basename(jp)[:-5]
        if key in paths.SKIP_KEYS:
            continue
        rs = json.load(open(jp, encoding='utf-8'))
        if any(r['ko'] for r in rs):
            rows[key] = rs
    return rows


def extract(cpk, keys, log):
    """CPK 에서 번역 대상 DAT 을 work/orig 로 풀어 놓는다 (이미 있으면 건너뜀)"""
    need = {}
    for key in keys:
        dst = os.path.join(paths.ORIG, key + '.dat')
        if os.path.exists(dst + '.dat') and glob.glob(os.path.join(dst, '*.mcd')):
            continue
        need[paths.dat_path(key)] = (key, dst)
    if not need:
        return
    log('원본에서 %d개 파일 추출 중.....' % len(need))
    for e in cpk.files:
        if e['name'] not in need:
            continue
        key, dst = need[e['name']]
        d = cpk.read(e)
        os.makedirs(dst, exist_ok=True)
        open(dst + '.dat', 'wb').write(d)
        for n, o, s in parse_dat(d)[0]:
            open(os.path.join(dst, n), 'wb').write(d[o:o + s])
        log('  %s' % e['name'])


def build(src, out_dir, force=False, log=print):
    t0 = time.time()
    size = os.path.getsize(src)
    log('원본: %s (%d bytes)' % (src, size))
    if size != paths.ORIG_SIZE:
        msg = '원본 크기가 다릅니다 (기대 %d). 일본판 data003.cpk 가 맞는지 확인하세요.' % paths.ORIG_SIZE
        if not force:
            raise SystemExit(msg + '  무시하려면 --force')
        log('경고: ' + msg)
    else:
        h = sha1(src)
        if h != paths.ORIG_SHA1:
            msg = '원본 SHA-1 이 다릅니다: %s' % h
            if not force:
                raise SystemExit(msg + '  무시하려면 --force')
            log('경고: ' + msg)

    rows = load_rows()
    os.makedirs(paths.ORIG, exist_ok=True)
    cpk = CPK(src)
    extract(cpk, rows, log)

    replace, expect = {}, {}
    for key, rs in rows.items():
        dat_dir = os.path.join(paths.ORIG, key + '.dat')
        files, _ = atlas_build.build(dat_dir, rs, log=log)
        if key == 'ui__ui_title':      # 타이틀 로고 속 가타카나 → 한글
            files['title.wtp'], _ = logo_patch.build_title_wtp(dat_dir)
            log('%-22s 타이틀 로고 이미지 교체' % 'title.wtp')
        if key == 'ui__ui_ending':     # 엔딩 청구서 이미지 → 한글
            files['ending.wtp'], _, painted, decoded, nblk = invoice_patch.build_ending_wtp(dat_dir)
            assert np.abs(decoded.astype(int) - painted).mean() < 1.0, 'invoice BC1 error too large'
            log('%-22s 청구서 이미지 교체 (블록 %d개)' % ('ending.wtp', nblk))
        orig_dat = open(dat_dir + '.dat', 'rb').read()
        name = paths.dat_path(key)
        replace[name] = repack.repack_dat(orig_dat, files)
        mcd_name = [n for n in files if n.endswith('.mcd')][0]
        expect[name] = (mcd_name, {r['id']: r['ko'] for r in rs if r['ko']})

    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, paths.CPK_NAME)
    repack.repack_cpk(src, dst, replace, log=log)

    log('검증 중...')
    c = CPK(dst)
    for e in c.files:
        if e['name'] not in replace:
            continue
        d = c.read(e)
        assert d == replace[e['name']], e['name']
        ents, _ = parse_dat(d)
        mcd_name, tr = expect[e['name']]
        o, s = [(o, s) for n, o, s in ents if n == mcd_name][0]
        m = MCD(d[o:o + s])
        for k, v in tr.items():
            i, j = map(int, k.split('.'))
            assert m.section_text(m.messages[i]['sections'][j]) == v, (e['name'], k)
    c.f.close()
    log('완료: %s  (%.0f초)' % (dst, time.time() - t0))
    return dst


def main():
    ap = argparse.ArgumentParser(description='스타폭스 제로 한글 패치 빌더')
    ap.add_argument('source', nargs='?', help='원본 data003.cpk 경로')
    ap.add_argument('-o', '--out', default=os.path.join(paths.ROOT, 'out'), help='출력 폴더')
    ap.add_argument('--force', action='store_true', help='원본 검사 실패해도 진행')
    a = ap.parse_args()
    dst = build(find_source(a.source), a.out, a.force)
    print()
    print('SD카드(SDCafiine): sd:/wiiu/sdcafiine/%s/<임의이름>/content/%s' % (paths.TITLE_ID, paths.CPK_NAME))
    print('Cemu: graphicPacks/<팩이름>/content/%s (rules.txt 의 titleIds = %s)' % (paths.CPK_NAME, paths.TITLE_ID))
    print('만들어진 파일:', dst)


if __name__ == '__main__':
    main()

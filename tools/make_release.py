"""배포용 패치 꾸러미 만들기 (임베디드 파이썬 + 스크립트 패처).

원본 data003.cpk 와 빌드 결과를 비교해, 바뀐 파일만 골라 release/patcher/payload 에 담는다.
 - mess*.mcd/.wta/.wtp (한글 텍스트·글자 아틀라스)  -> full  (새 파일 통째로)
 - 그 밖의 .wtp (한글로 고친 그림)                  -> delta (달라진 4KB 블록만)

사용: python tools/make_release.py <원본 data003.cpk> [--built out/data003.cpk] [--version v0.9]
release/python 에 python.org embeddable 을 풀어 두면 zip 에 함께 담는다.
"""
import argparse, hashlib, json, os, shutil, sys, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'release', 'patcher', 'lib'))
import paths
from cpk_lib import open_cpk, extract
from dat_lib import read_dat

REL = os.path.join(paths.ROOT, 'release')
MODNAME = 'StarFoxZero_KR'
BLOCK = 4096


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''):
            h.update(b)
    return h.hexdigest()


def diff_blocks(a, b):
    """같은 길이의 두 바이트열에서 달라진 4KB 블록 구간 목록"""
    assert len(a) == len(b)
    spans = []
    for off in range(0, len(a), BLOCK):
        if a[off:off + BLOCK] != b[off:off + BLOCK]:
            if spans and spans[-1][0] + spans[-1][1] == off:
                spans[-1][1] += min(BLOCK, len(a) - off)
            else:
                spans.append([off, min(BLOCK, len(a) - off)])
    return spans


def build_payload(src, dst, version):
    pay = os.path.join(REL, 'patcher', 'payload')
    if os.path.isdir(pay):
        shutil.rmtree(pay)
    os.makedirs(pay)

    f0, h0, t0 = open_cpk(src)
    f1, h1, t1 = open_cpk(dst)
    man = {'title': paths.TITLE_ID, 'mod': MODNAME, 'version': version,
           'source': {'size': os.path.getsize(src), 'md5': md5(src)},
           'result': {'size': os.path.getsize(dst), 'md5': md5(dst)},
           'dats': {}}
    total = 0
    for a, b in zip(t0, t1):
        assert a['FileName'] == b['FileName']
        if a['FileSize'] == b['FileSize']:
            f0.seek(h0['TocOffset'] + a['FileOffset'])
            f1.seek(h1['TocOffset'] + b['FileOffset'])
            if f0.read(a['FileSize']) == f1.read(b['FileSize']):
                continue
        da = {e['name']: e['data'] for e in read_dat(extract(f0, h0, a))}
        db = {e['name']: e['data'] for e in read_dat(extract(f1, h1, b))}
        assert set(da) == set(db), a['FileName']
        key = (a['DirName'] + '/' if a['DirName'] else '') + a['FileName']
        entries = []
        for name in db:
            if da[name] == db[name]:
                continue
            base = '%s__%s' % (a['FileName'][:-4], name)
            if len(da[name]) == len(db[name]) and not name.lower().startswith('mess'):
                spans = diff_blocks(da[name], db[name])
                blob = b''.join(db[name][o:o + n] for o, n in spans)
                open(os.path.join(pay, base + '.delta'), 'wb').write(blob)
                entries.append({'name': name, 'mode': 'delta', 'file': base + '.delta', 'spans': spans})
                total += len(blob)
            else:
                open(os.path.join(pay, base + '.bin'), 'wb').write(db[name])
                entries.append({'name': name, 'mode': 'full', 'file': base + '.bin'})
                total += len(db[name])
        man['dats'][key] = entries
        print('%-24s %d개 파일' % (key, len(entries)))
    f0.close()
    f1.close()
    json.dump(man, open(os.path.join(pay, 'manifest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('payload %s B  (DAT %d개)' % ('{:,}'.format(total), len(man['dats'])))
    return man


def make_zip(version):
    name = 'StarFoxZero_KO_%s' % version
    out = os.path.join(REL, name + '.zip')
    items = [('README_한국어.txt', os.path.join(REL, 'README_한국어.txt')),
             ('패치하기.bat', os.path.join(REL, '패치하기.bat'))]
    for folder in ('patcher', 'python'):
        root = os.path.join(REL, folder)
        if not os.path.isdir(root):
            print('경고: %s 없음 (파이썬 임베더블을 release/python 에 풀어 두세요)' % folder)
            continue
        for r, ds, fs in os.walk(root):
            ds[:] = [d for d in ds if d != '__pycache__']
            for f in fs:
                p = os.path.join(r, f)
                items.append((os.path.relpath(p, REL).replace('\\', '/'), p))
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for arc, p in items:
            z.write(p, '%s/%s' % (name, arc))
    print('zip: %s (%.1f MB)' % (out, os.path.getsize(out) / 1e6))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source', help='원본 data003.cpk')
    ap.add_argument('--built', default=os.path.join(paths.ROOT, 'out', 'data003.cpk'), help='한글판 data003.cpk')
    ap.add_argument('--version', default='v0.9')
    a = ap.parse_args()
    build_payload(a.source, a.built, a.version)
    make_zip(a.version)


if __name__ == '__main__':
    main()

# 번역 검사: python lint.py [json이름 ...]   (생략 시 전체)
#  - 태그({I n},{G0},{/G0}) 보존, 일본어 남음/미번역, 줄 폭(원문 같은 파일·폰트 최대 폭 대비), 줄 수
import sys, os, json, glob, re, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcd_tool import MCD, parse_text, CTRL_SPACE
HERE = os.path.dirname(os.path.abspath(__file__))
from paths import WORK, ORIG, TEXT
CACHE = os.path.join(WORK, 'adv_cache.json')
SKIP = {'ui__ui_option', 'ui__ui_gallery'}
TAG = re.compile(r'\{/?[A-Z]\d*\}')
JP = re.compile(r'[぀-ヿ一-鿿]')

def _load_cache():
    try:
        return json.load(open(CACHE))
    except Exception:  # missing or being written by another process
        return {}


adv_cache = _load_cache()


def new_adv(font, ch, h):
    k = '%d/%d/%04x' % (font, h, ord(ch))
    if k not in adv_cache:
        import font_render
        adv_cache[k] = font_render.render_glyph(ch, font, h)[1]
    return adv_cache[k]


def main(names):
    problems = 0
    for jp in sorted(glob.glob(os.path.join(TEXT, '*.json'))):
        key = os.path.basename(jp)[:-5]
        if key in SKIP or (names and key not in names):
            continue
        rows = json.load(open(jp, encoding='utf-8'))
        mcds = glob.glob(os.path.join(ORIG, key + '.dat', '*.mcd'))
        if not mcds:   # 원본을 아직 추출하지 않은 파일 (번역 대상이 아님)
            continue
        m = MCD(open(mcds[0], 'rb').read())
        glyph_adv = {}
        for f, c, gi in m.symbols:
            glyph_adv[(f, c)] = struct.unpack('>I9f', m.glyphs[gi])[5]
        fonts = {}
        for f in m.fonts:
            fid, w, h, b, hz = struct.unpack('>I4f', f)
            fonts[fid] = (w, int(round(h)))
        # original line widths per font
        maxw = collections.defaultdict(float)
        maxlines = collections.defaultdict(int)
        for i, msg in enumerate(m.messages):
            for j, sec in enumerate(msg['sections']):
                font = sec['c'] >> 16
                maxlines[font] = max(maxlines[font], len(sec['lines']))
                for ln in sec['lines']:
                    w = 0
                    for v, q in ln['toks']:
                        if v < 0x8000:
                            w += glyph_adv[m.symbols[v][:2]] + (q - 0x10000 if q >= 0x8000 else q)
                        elif v == CTRL_SPACE:
                            w += fonts[font][0]
                        else:
                            w += fonts[font][1] * 0.8  # icon guess
                    maxw[(font, i, j)] = w
        per_font_max = collections.defaultdict(float)
        for (font, i, j), w in maxw.items():
            per_font_max[font] = max(per_font_max[font], w)
        orig_w = {}
        for (font, i, j), w in maxw.items():
            orig_w[(i, j)] = w
        out = []
        for r in rows:
            i, j = map(int, r['id'].split('.'))
            sec = m.messages[i]['sections'][j]
            font = sec['c'] >> 16
            ja, ko = r['ja'], r['ko']
            needs = bool(JP.search(TAG.sub('', ja)))
            if not ko:
                if needs:
                    out.append((r['id'], '미번역', ja))
                continue
            if sorted(TAG.findall(ja)) != sorted(TAG.findall(ko)):
                out.append((r['id'], '태그 불일치', '%s  ->  %s' % (ja, ko)))
            if JP.search(ko):
                out.append((r['id'], '일본어/한자 남음', ko))
            try:
                lines = parse_text(ko)
            except ValueError as e:
                out.append((r['id'], '태그 오류', ko))
                continue
            fw, fh = fonts[font]
            limit = per_font_max[font]
            for ln in lines:
                w = 0
                for t in ln:
                    if t[0] == 'ch':
                        w += glyph_adv.get((font, ord(t[1]))) or new_adv(font, t[1], fh)
                    elif t[0] == 'sp':
                        w += fw
                    else:
                        w += fh * 0.8
                if w > limit * 1.0 + 1:
                    out.append((r['id'], '줄 폭 초과 %.0f%% (최대 %.0fpx)' % (w / limit * 100, limit), ko.replace('\n', '⏎')))
            if len(lines) > maxlines[font]:
                out.append((r['id'], '줄 수 %d > 원본 최대 %d' % (len(lines), maxlines[font]), ko.replace('\n', '⏎')))
        if out:
            print('== %s (%d건)' % (key, len(out)))
            for x in out:
                print('  %s [%s] %s' % x)
        problems += len(out)
    merged = _load_cache()
    merged.update(adv_cache)
    tmp = '%s.%d.tmp' % (CACHE, os.getpid())
    json.dump(merged, open(tmp, 'w'))
    os.replace(tmp, CACHE)
    print('문제 합계', problems)


if __name__ == '__main__':
    main(set(a.replace('.json', '') for a in sys.argv[1:]))

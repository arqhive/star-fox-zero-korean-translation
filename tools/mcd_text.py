# MCD <-> 번역 JSON
#   python mcd_text.py export            : work/orig/*/*.mcd -> work/text/<dat>.json
#   python mcd_text.py check             : 번역 JSON 태그/문자 검사 + 필요한 한글 글자 목록 출력
# 번역 텍스트 표기: 줄바꿈 \n, 공백 ' ', 버튼 아이콘 {I숫자}, 강조 그룹 {G0}...{/G0}, 중괄호 문자 {{ }}
import sys, os, glob, json, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcd_tool import MCD, parse_text, CTRL_SPACE

from paths import WORK as ROOT, ORIG, TEXT


def mcd_files():
    return sorted(glob.glob(os.path.join(ORIG, '*', '*.mcd')))


def json_path(mcd_path):
    return os.path.join(TEXT, os.path.basename(os.path.dirname(mcd_path))[:-4] + '.json')


def export():
    os.makedirs(TEXT, exist_ok=True)
    total = 0
    for f in mcd_files():
        m = MCD(open(f, 'rb').read())
        ev = m.event_names()
        rows = []
        for i, msg in enumerate(m.messages):
            for j, sec in enumerate(msg['sections']):
                rows.append(dict(id='%04d.%d' % (i, j), event=ev.get(i, ''), font=sec['c'] >> 16,
                                 ja=m.section_text(sec), ko=''))
        jp = json_path(f)
        if os.path.exists(jp):
            old = {r['id']: r['ko'] for r in json.load(open(jp, encoding='utf-8'))}
            for r in rows:
                r['ko'] = old.get(r['id'], '')
        json.dump(rows, open(jp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        total += len(rows)
        print('%-28s %4d' % (os.path.basename(jp), len(rows)))
    print('total entries', total)


def apply_translations(m, rows, glyph_provider):
    """rows: [{id, ko}], glyph_provider(font_id, char) -> 40-byte glyph record for every used char.
    Rebuilds the symbol/glyph tables so they hold exactly the (font, char) pairs in use."""
    ko = {r['id']: r['ko'] for r in rows if r.get('ko')}
    old_syms, old_glyphs = m.symbols, m.glyphs
    orig_glyph = {(s[0], s[1]): old_glyphs[s[2]] for s in old_syms}
    # pass 1: token lists using (font, char) keys
    for i, msg in enumerate(m.messages):
        for j, sec in enumerate(msg['sections']):
            font = sec['c'] >> 16
            key = '%04d.%d' % (i, j)
            if key in ko:
                fm = m.font_metrics(font)
                f1, f2 = struct.unpack('>II', fm[12:20])
                new_lines = []
                for ln in parse_text(ko[key]):
                    toks = []
                    for t in ln:
                        if t[0] == 'ch':
                            toks.append(((font, ord(t[1])), 0))
                        elif t[0] == 'sp':
                            toks.append((CTRL_SPACE, font))
                        else:
                            toks.append(t)
                    new_lines.append(dict(toks=toks, f1=f1, f2=f2))
                sec['lines'] = new_lines
            else:
                for ln in sec['lines']:
                    ln['toks'] = [((old_syms[v][0], old_syms[v][1]), q) if v < 0x8000 else (v, q)
                                  for v, q in ln['toks']]
    # pass 2: new symbol table sorted by (font, char)
    used = sorted({v for msg in m.messages for sec in msg['sections'] for ln in sec['lines']
                   for v, q in ln['toks'] if isinstance(v, tuple)})
    index = {k: n for n, k in enumerate(used)}
    m.symbols = [(f, c, n) for n, (f, c) in enumerate(used)]
    # glyph_provider=None keeps the original glyphs (only valid when no new characters are used)
    m.glyphs = [glyph_provider(*k) if glyph_provider else orig_glyph[k] for k in used]
    for msg in m.messages:
        for sec in msg['sections']:
            for ln in sec['lines']:
                ln['toks'] = [(index[v], q) if isinstance(v, tuple) else (v, q) for v, q in ln['toks']]
    return used


def check():
    need = set()
    bad = 0
    for f in mcd_files():
        jp = json_path(f)
        if not os.path.exists(jp):
            continue
        for r in json.load(open(jp, encoding='utf-8')):
            if not r['ko']:
                continue
            try:
                lines = parse_text(r['ko'])
            except ValueError as e:
                print(os.path.basename(jp), r['id'], e)
                bad += 1
                continue
            for ln in lines:
                need.update(t[1] for t in ln if t[0] == 'ch')
    print('태그 오류', bad, '/ 사용 글자 수', len(need))


if __name__ == '__main__':
    {'export': export, 'check': check}[sys.argv[1]]()

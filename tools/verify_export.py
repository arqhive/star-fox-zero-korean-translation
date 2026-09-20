# 내보낸 JSON 이 원본 MCD 전문을 빠짐없이 담았는지 대조
#   python verify_export.py <json경로>
import sys, glob, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcd_tool import MCD

p = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.expanduser('~'), 'Desktop', 'star-fox-zero.json')
ORIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'work', 'orig')

d = json.load(open(p, encoding='utf-8'))
ent = d['entries'] if isinstance(d, dict) and 'entries' in d else d
print('파일:', p)
print('최상위 키:', list(d)[:8] if isinstance(d, dict) else type(d).__name__)
print('항목 수:', len(ent))
print('첫 항목:', json.dumps(ent[0], ensure_ascii=False)[:200])

orig = {}
for f in sorted(glob.glob(os.path.join(glob.escape(ORIG), '*', '*.mcd'))):
    m = MCD(open(f, 'rb').read())
    key = os.path.basename(os.path.dirname(f))[:-4]
    orig[key] = sum(len(x['sections']) for x in m.messages)

keyfield = 'file' if 'file' in ent[0] else None
exp = {}
for e in ent:
    exp[e.get(keyfield, '?')] = exp.get(e.get(keyfield, '?'), 0) + 1
print('원본 MCD: 파일 %d개 / 항목 %d개' % (len(orig), sum(orig.values())))
print('JSON    : 파일 %d개 / 항목 %d개' % (len(exp), sum(exp.values())))
mismatch = [(k, orig.get(k), exp.get(k)) for k in set(orig) | set(exp) if orig.get(k) != exp.get(k)]
print('파일별 불일치:', mismatch if mismatch else '없음')

bad = miss = notr = 0
for f in sorted(glob.glob(os.path.join(glob.escape(ORIG), '*', '*.mcd'))):
    key = os.path.basename(os.path.dirname(f))[:-4]
    m = MCD(open(f, 'rb').read())
    rows = {e['id']: e for e in ent if e.get(keyfield) == key}
    for i, msg in enumerate(m.messages):
        for j, sec in enumerate(msg['sections']):
            t = m.section_text(sec)
            r = rows.get('%04d.%d' % (i, j))
            if r is None:
                miss += 1
            elif r['ja'] != t:
                bad += 1
            elif not r.get('ko') and any(ord(c) > 0x3000 for c in t):
                notr += 1
print('누락: %d | 원문 불일치: %d | 일본어인데 번역 빈 항목: %d' % (miss, bad, notr))

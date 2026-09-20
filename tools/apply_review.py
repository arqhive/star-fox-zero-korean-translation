# 리뷰본 JSON 의 ko 를 translation/text/*.json 에 반영
#   python apply_review.py <리뷰본.json>
import sys, json, glob, os, sys, io

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import TEXT

rev_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.expanduser('~'), 'Downloads', 'star-fox-zero.reviewed.json')
rev = json.load(open(rev_path, encoding='utf-8'))
ent = rev['entries'] if isinstance(rev, dict) and 'entries' in rev else rev
new = {(e['file'], e['id']): (e.get('ko') or '') for e in ent}
ja = {(e['file'], e['id']): e['ja'] for e in ent}

changed = 0
for jp in sorted(glob.glob(os.path.join(TEXT, '*.json'))):
    key = os.path.basename(jp)[:-5]
    raw = io.open(jp, 'rb').read()
    crlf = b'\r\n' in raw
    rows = json.loads(raw.decode('utf-8'))
    hit = False
    for r in rows:
        k = (key, r['id'])
        if k not in new:
            continue
        assert r['ja'] == ja[k], '원문 불일치: %s %s' % k
        if r['ko'] != new[k]:
            r['ko'] = new[k]
            changed += 1
            hit = True
    if hit:
        s = json.dumps(rows, ensure_ascii=False, indent=1)
        if crlf:
            s = s.replace('\n', '\r\n')
        io.open(jp, 'wb').write(s.encode('utf-8'))
print('반영한 항목:', changed)

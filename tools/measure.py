# 후보 문장의 줄 폭을 실제 글리프 폭으로 재서 한계와 비교
#   python measure.py <파일키> <항목id> "후보1" "후보2" ...
import sys, os, json, glob, struct, collections
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
from mcd_tool import MCD, parse_text, CTRL_SPACE
import lint as lintmod


def widths(key, eid, candidates):
    m = MCD(open(glob.glob(os.path.join(glob.escape(os.path.join(REPO, 'work', 'orig', key + '.dat')), '*.mcd'))[0], 'rb').read())
    glyph_adv = {}
    for f, c, gi in m.symbols:
        glyph_adv[(f, c)] = struct.unpack('>I9f', m.glyphs[gi])[5]
    fonts = {}
    for f in m.fonts:
        fid, w, h, b, hz = struct.unpack('>I4f', f)
        fonts[fid] = (w, int(round(h)))
    per_font_max = collections.defaultdict(float)
    for i, msg in enumerate(m.messages):
        for j, sec in enumerate(msg['sections']):
            font = sec['c'] >> 16
            for ln in sec['lines']:
                w = 0
                for v, q in ln['toks']:
                    if v < 0x8000:
                        w += glyph_adv[m.symbols[v][:2]] + (q - 0x10000 if q >= 0x8000 else q)
                    elif v == CTRL_SPACE:
                        w += fonts[font][0]
                    else:
                        w += fonts[font][1] * 0.8
                per_font_max[font] = max(per_font_max[font], w)
    i, j = map(int, eid.split('.'))
    font = m.messages[i]['sections'][j]['c'] >> 16
    fw, fh = fonts[font]
    limit = per_font_max[font]
    print('%s %s  폰트 %d  한계 %.0fpx' % (key, eid, font, limit))
    for cand in candidates:
        for n, ln in enumerate(parse_text(cand)):
            w = 0
            for t in ln:
                if t[0] == 'ch':
                    w += glyph_adv.get((font, ord(t[1]))) or lintmod.new_adv(font, t[1], fh)
                elif t[0] == 'sp':
                    w += fw
                else:
                    w += fh * 0.8
            mark = 'OK ' if w <= limit + 1 else '초과'
            print('  %s %3.0f%%  줄%d  %s' % (mark, w / limit * 100, n + 1, cand.split('\n')[n]))


if __name__ == '__main__':
    widths(sys.argv[1], sys.argv[2], sys.argv[3:])

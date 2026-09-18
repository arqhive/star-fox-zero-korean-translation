# Star Fox Zero (Wii U) MCD message file parser / builder.
# Big-endian PlatinumGames MCD:
#   header 10*u32: msg_off,msg_cnt, sym_off,sym_cnt, glyph_off,glyph_cnt, font_off,font_cnt, evt_off,evt_cnt
#   layout: header, text(u16 stream), msgs(16), sections(20), lines(24), symbols(8), glyphs(40), fonts(20), events(40)
#   every table after text starts at the next multiple of 4 strictly past the previous one (1..4 zero bytes)
#   text: pairs (symbol_idx, kerning s16) | 0x8001 font = space | 0x8003 n = icon | 0x800c/0x800d q = group | 0x8000 = end
import struct, json, re

CTRL_SPACE, CTRL_ICON, CTRL_GRP_B, CTRL_GRP_E, CTRL_END = 0x8001, 0x8003, 0x800C, 0x800D, 0x8000


class MCD:
    def __init__(self, data=None):
        if data is not None:
            self.parse(data)

    def parse(self, m):
        mo, mc, so, sc, go, gc, fo, fc, eo, ec = struct.unpack('>10I', m[:40])
        self.symbols = [struct.unpack('>HHI', m[so + i * 8:so + i * 8 + 8]) for i in range(sc)]
        self.glyphs = [m[go + i * 40:go + i * 40 + 40] for i in range(gc)]
        self.fonts = [m[fo + i * 20:fo + i * 20 + 20] for i in range(fc)]
        self.events = []
        for i in range(ec):
            h, idx = struct.unpack('>II', m[eo + i * 40:eo + i * 40 + 8])
            self.events.append((h, idx, m[eo + i * 40 + 8:eo + i * 40 + 40]))
        self.messages = []
        for i in range(mc):
            s_off, s_cnt, seq, hsh = struct.unpack('>4I', m[mo + i * 16:mo + i * 16 + 16])
            secs = []
            for j in range(s_cnt):
                l_off, l_cnt, a, b, c = struct.unpack('>5I', m[s_off + j * 20:s_off + j * 20 + 20])
                lines = []
                for k in range(l_cnt):
                    t, z, L1, L2, f1, f2 = struct.unpack('>6I', m[l_off + k * 24:l_off + k * 24 + 24])
                    w = struct.unpack('>%dH' % L1, m[t:t + 2 * L1])
                    toks, p = [], 0
                    while w[p] != CTRL_END:
                        toks.append((w[p], w[p + 1]))
                        p += 2
                    assert p == L1 - 1 and z == 0 and L1 == L2
                    lines.append(dict(toks=toks, f1=f1, f2=f2))
                secs.append(dict(a=a, b=b, c=c, lines=lines))
            self.messages.append(dict(seq=seq, hash=hsh, sections=secs))

    # ---- font helpers ----
    def font_ids(self):
        return [struct.unpack('>I', f[:4])[0] for f in self.fonts]

    def font_metrics(self, fid):
        for f in self.fonts:
            if struct.unpack('>I', f[:4])[0] == fid:
                return f
        raise KeyError(fid)

    # ---- text conversion ----
    def tokens_to_text(self, toks):
        s = []
        for v, q in toks:
            if v < 0x8000:
                ch = chr(self.symbols[v][1])
                s.append('{{' if ch == '{' else '}}' if ch == '}' else ch)
            elif v == CTRL_SPACE:
                s.append(' ')
            elif v == CTRL_ICON:
                s.append('{I%d}' % q)
            elif v == CTRL_GRP_B:
                s.append('{G%d}' % q)
            elif v == CTRL_GRP_E:
                s.append('{/G%d}' % q)
            else:
                s.append('{X%04x:%d}' % (v, q))
        return ''.join(s)

    def section_text(self, sec):
        return '\n'.join(self.tokens_to_text(l['toks']) for l in sec['lines'])

    def event_names(self):
        return {idx: name.split(b'\0')[0].decode('ascii') for h, idx, name in self.events}

    # ---- serialization ----
    def build(self):
        out = bytearray(40)
        def pad():  # always advance to the next multiple of 4 (1..4 zero bytes)
            out.extend(b'\0' * (4 - len(out) % 4))
        # text blob
        line_off = {}
        for i, msg in enumerate(self.messages):
            for j, sec in enumerate(msg['sections']):
                for k, ln in enumerate(sec['lines']):
                    line_off[(i, j, k)] = len(out)
                    for v, q in ln['toks']:
                        out += struct.pack('>HH', v, q & 0xFFFF)
                    out += struct.pack('>H', CTRL_END)
        pad()
        msg_off = len(out)
        nsec = sum(len(m['sections']) for m in self.messages)
        nline = sum(len(s['lines']) for m in self.messages for s in m['sections'])
        sec_base = msg_off + 16 * len(self.messages) + 4  # tables are 4-aligned already
        line_base = sec_base + 20 * nsec + 4
        si = li = 0
        msgs, secs, lines = bytearray(), bytearray(), bytearray()
        for i, msg in enumerate(self.messages):
            msgs += struct.pack('>4I', sec_base + si * 20, len(msg['sections']), msg['seq'], msg['hash'])
            for j, sec in enumerate(msg['sections']):
                secs += struct.pack('>5I', line_base + li * 24, len(sec['lines']), sec['a'], sec['b'], sec['c'])
                si += 1
                for k, ln in enumerate(sec['lines']):
                    L = len(ln['toks']) * 2 + 1
                    lines += struct.pack('>6I', line_off[(i, j, k)], 0, L, L, ln['f1'], ln['f2'])
                    li += 1
        out += msgs; pad(); assert len(out) == sec_base
        out += secs; pad(); assert len(out) == line_base
        out += lines; pad()
        sym_off = len(out)
        for s in self.symbols:
            out += struct.pack('>HHI', *s)
        pad(); glyph_off = len(out)
        for g in self.glyphs:
            out += g
        pad(); font_off = len(out)
        for f in self.fonts:
            out += f
        pad(); evt_off = len(out)
        for h, idx, name in self.events:
            out += struct.pack('>II', h, idx) + name
        out[:40] = struct.pack('>10I', msg_off, len(self.messages), sym_off, len(self.symbols),
                               glyph_off, len(self.glyphs), font_off, len(self.fonts),
                               evt_off, len(self.events))
        return bytes(out)


TAG_RE = re.compile(r'\{\{|\}\}|\{I(\d+)\}|\{G(\d+)\}|\{/G(\d+)\}|\{X([0-9a-fA-F]{4}):(\d+)\}|(.)', re.S)


def parse_text(s):
    """Translated text -> list of lines, each a list of ('ch',c)|('sp',)|(ctrl,param)."""
    lines, cur = [], []
    for mt in TAG_RE.finditer(s):
        g = mt.group(0)
        if g == '{{':
            cur.append(('ch', '{'))
        elif g == '}}':
            cur.append(('ch', '}'))
        elif mt.group(1):
            cur.append((CTRL_ICON, int(mt.group(1))))
        elif mt.group(2):
            cur.append((CTRL_GRP_B, int(mt.group(2))))
        elif mt.group(3):
            cur.append((CTRL_GRP_E, int(mt.group(3))))
        elif mt.group(4):
            cur.append((int(mt.group(4), 16), int(mt.group(5))))
        elif g == '\n':
            lines.append(cur); cur = []
        elif g in (' ', '　'):
            cur.append(('sp',))
        elif g in '{}':
            raise ValueError('잘못된 태그: %r' % s)
        else:
            cur.append(('ch', g))
    lines.append(cur)
    return lines

# Render MCD sections the way the game lays them out (glyph advance + kerning) for visual checks.
import struct
import numpy as np
from PIL import Image
from mcd_tool import MCD, CTRL_SPACE


def render_sections(mcd_bytes, atlas, keys, scale=1.0):
    m = MCD(mcd_bytes)
    H, W = atlas.shape[:2]
    lines_img = []
    for i, j in keys:
        sec = m.messages[i]['sections'][j]
        font = sec['c'] >> 16
        fm = struct.unpack('>I4f', m.font_metrics(font))
        fh = int(round(fm[2]))
        for ln in sec['lines']:
            parts = []
            for v, q in ln['toks']:
                if v < 0x8000:
                    g = struct.unpack('>I9f', m.glyphs[m.symbols[v][2]])
                    x1, y1, x2, y2 = round(g[1] * W), round(g[2] * H), round(g[3] * W), round(g[4] * H)
                    t = atlas[y1:y2, x1:x2]
                    k = q - 0x10000 if q >= 0x8000 else q
                    if k and parts:
                        parts[-1] = parts[-1][:, :max(1, parts[-1].shape[1] + k)] if k < 0 else \
                            np.pad(parts[-1], ((0, 0), (0, k), (0, 0)))
                    parts.append(t)
                elif v == CTRL_SPACE:
                    parts.append(np.zeros((fh, int(fm[1]), 2), np.uint8))
                else:
                    parts.append(np.full((fh, 8, 2), 90, np.uint8))  # icon / tag marker
            if not parts:
                continue
            h = max(p.shape[0] for p in parts)
            row = np.concatenate([np.pad(p, ((0, h - p.shape[0]), (0, 0), (0, 0))) for p in parts], 1)
            lines_img.append(row)
    Wd = max(r.shape[1] for r in lines_img)
    sheet = np.concatenate([np.pad(r, ((0, 0), (0, Wd - r.shape[1]), (0, 0))) for r in lines_img], 0)
    rgb = np.zeros(sheet.shape[:2] + (3,), np.uint8)
    rgb[:, :, 0] = sheet[:, :, 0]
    rgb[:, :, 1] = sheet[:, :, 1]
    im = Image.fromarray(rgb)
    if scale != 1.0:
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    return im

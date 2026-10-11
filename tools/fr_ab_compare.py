# -*- coding: utf-8 -*-
"""基础版 vs 真人质感版 左右对照总览（核验身份/服装一致性）"""
import os
import sys

import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

ROOT = r'D:/work/minimax_h3/assets/凡人/character'
SRC_DIR = r'D:/work/minimax_h3/generated-images'
OUT = r'D:/work/minimax_h3/logs/_fr_check/views_15_ab_compare.jpg'

# (角色, 基础版路径)
PAIRS = [
    ('南宫婉', r'南宫婉/人物三视图（基础）.png'),
    ('紫灵', r'紫灵/人物三视图（基础）.png'),
    ('跟班A', r'跟班A/人物三视图（校服）.png'),
    ('跟班B', r'跟班B/人物三视图（校服）.png'),
    ('宋玉', r'宋玉/人物三视图（基础）.png'),
    ('元瑶', r'元瑶/人物人视图（基础）.png'),
    ('凌玉灵', r'凌玉灵/人物三视图（基础）.png'),
    ('墨彩环', r'墨彩环/人物三视图（基础）.png'),
    ('李缨宁', r'李缨宁/人物三视图（基础）.png'),
    ('柳眉', r'柳眉/人物三视图（基础）.png'),
    ('梅凝', r'梅凝/人物三视图（基础）.png'),
    ('燕如嫣', r'燕如嫣/人物三视图（基础）.png'),
    ('穆兰圣女', r'穆兰圣女/人物三视图（基础）.png'),
    ('辛如音', r'辛如音/人物三视图（基础）.png'),
    ('银月', r'银月/人物三视图（基础）.png'),
]

TILE_H = 300
PAD = 8
LABEL_H = 26

tiles = []
for i, (name, base_rel) in enumerate(PAIRS):
    pair = []
    for p in (os.path.join(ROOT, base_rel), os.path.join(SRC_DIR, '%s_真人质感_三视图基础.png' % name)):
        if not os.path.exists(p):
            print('MISS', p)
            pair = None
            break
        img = cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            print('FAIL decode', p)
            pair = None
            break
        h, w = img.shape[:2]
        s = TILE_H / h
        pair.append(cv2.resize(img, (int(w * s), TILE_H), interpolation=cv2.INTER_AREA))
    if not pair:
        continue
    pw = pair[0].shape[1] + pair[1].shape[1] + PAD
    canvas = np.full((TILE_H + LABEL_H, pw, 3), 255, np.uint8)
    canvas[LABEL_H:, :pair[0].shape[1]] = pair[0]
    canvas[LABEL_H:, pair[0].shape[1] + PAD:] = pair[1]
    cv2.putText(canvas, str(i + 1), (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    tiles.append(canvas)
    print('%-6s ok' % name)

COLS = 3
rows = []
for i in range(0, len(tiles), COLS):
    chunk = tiles[i:i + COLS]
    rw = sum(t.shape[1] for t in chunk) + PAD * (len(chunk) + 1)
    rh = max(t.shape[0] for t in chunk) + PAD * 2
    row = np.full((rh, rw, 3), 235, np.uint8)
    x = PAD
    for t in chunk:
        row[PAD:PAD + t.shape[0], x:x + t.shape[1]] = t
        x += t.shape[1] + PAD
    rows.append(row)

W = max(r.shape[1] for r in rows)
H = sum(r.shape[0] for r in rows)
sheet = np.full((H, W, 3), 235, np.uint8)
y = 0
for r in rows:
    sheet[y:y + r.shape[0], 0:r.shape[1]] = r
    y += r.shape[0]

ok, buf = cv2.imencode('.jpg', sheet, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
buf.tofile(OUT)
print('SHEET', OUT, sheet.shape[1], 'x', sheet.shape[0])
print('顺序:', ' | '.join('%d=%s' % (i + 1, n) for i, (n, _) in enumerate(PAIRS)))

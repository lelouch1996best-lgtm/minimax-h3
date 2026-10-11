# -*- coding: utf-8 -*-
"""凡人 16 人真人质感三视图总览拼图（核验用，ASCII 输出路径）"""
import os
import sys

import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

SRC_DIR = r'D:/work/minimax_h3/generated-images'
OUT = r'D:/work/minimax_h3/logs/_fr_check/views_16_overview.jpg'

NAMES = ['南宫婉', '紫灵', '跟班A', '跟班B', '宋玉', '元瑶', '凌玉灵', '墨彩环',
         '李缨宁', '柳眉', '梅凝', '燕如嫣', '穆兰圣女', '文思月', '辛如音', '银月']

TILE_H = 380
COLS = 4
PAD = 8
LABEL_H = 30

tiles = []
for i, n in enumerate(NAMES):
    p = os.path.join(SRC_DIR, '%s_真人质感_三视图基础.png' % n)
    if not os.path.exists(p):
        print('MISS', n)
        continue
    img = cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        print('FAIL', n)
        continue
    h, w = img.shape[:2]
    s = TILE_H / h
    img = cv2.resize(img, (int(w * s), TILE_H), interpolation=cv2.INTER_AREA)
    canvas = np.full((TILE_H + LABEL_H, img.shape[1], 3), 255, np.uint8)
    canvas[LABEL_H:, :] = img
    cv2.putText(canvas, str(i + 1), (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    tiles.append(canvas)
    print('%-8s %dx%d' % (n, w, h))

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

os.makedirs(os.path.dirname(OUT), exist_ok=True)
ok, buf = cv2.imencode('.jpg', sheet, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
buf.tofile(OUT)
print('SHEET', OUT, sheet.shape[1], 'x', sheet.shape[0])
print('顺序:', ' | '.join('%d=%s' % (i + 1, n) for i, n in enumerate(NAMES)))

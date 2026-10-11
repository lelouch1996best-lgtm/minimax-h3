# -*- coding: utf-8 -*-
"""三视图核验：裁关键区域放大，用于逐项肉眼核对"""
import os
import sys

import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

SRC = r'D:/work/minimax_h3/generated-images/灶门炭治郎_真人质感_三视图基础.png'
OUT = r'D:/work/minimax_h3/logs/_gm_check'
os.makedirs(OUT, exist_ok=True)

img = cv2.imdecode(np.fromfile(SRC, np.uint8), cv2.IMREAD_COLOR)
H, W = img.shape[:2]
print('source size', W, 'x', H)

crops = {
    'A_closeup_head': (0.00, 0.00, 0.32, 0.62),
    'B_front_head': (0.28, 0.00, 0.56, 0.42),
    'C_front_full': (0.26, 0.00, 0.57, 1.00),
    'D_side_head': (0.52, 0.00, 0.76, 0.42),
    'E_back_full': (0.72, 0.00, 1.00, 1.00),
}

for k, (x1, y1, x2, y2) in crops.items():
    c = img[int(y1 * H):int(y2 * H), int(x1 * W):int(x2 * W)]
    ch, cw = c.shape[:2]
    s = min(3.0, 1500.0 / max(ch, cw))
    if s > 1:
        c = cv2.resize(c, (int(cw * s), int(ch * s)), interpolation=cv2.INTER_CUBIC)
    dst = os.path.join(OUT, k + '.png')
    ok, buf = cv2.imencode('.png', c)
    buf.tofile(dst)
    print('OK', dst, c.shape[1], 'x', c.shape[0])

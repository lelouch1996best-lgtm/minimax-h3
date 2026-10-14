# -*- coding: utf-8 -*-
"""裁切韩立设定稿各分区，用于逐格肉眼核验。"""
import os
import sys

import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

SRC = sys.argv[1] if len(sys.argv) > 1 else r'D:/work/minimax_h3/generated-images/韩立_噬金虫甲风雷翅_设定稿_v2.png'
OUT = sys.argv[2] if len(sys.argv) > 2 else r'D:/work/minimax_h3/logs/hl_setting_check_v2'

img = cv2.imdecode(np.fromfile(SRC, dtype=np.uint8), cv2.IMREAD_COLOR)
if img is None:
    print('DECODE_FAIL')
    sys.exit(1)
h, w = img.shape[:2]
print('SIZE %dx%d' % (w, h))

os.makedirs(OUT, exist_ok=True)


def crop(name, x0, y0, x1, y1):
    sub = img[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]
    p = os.path.join(OUT, name + '.png')
    ok, buf = cv2.imencode('.png', sub)
    buf.tofile(p)
    print('%-12s %4dx%-4d  exists=%s  %dKB' % (name, sub.shape[1], sub.shape[0],
                                               os.path.exists(p), os.path.getsize(p) / 1024))


MODE = sys.argv[3] if len(sys.argv) > 3 else '5'
if MODE == '5':
    crop('1_face', 0.00, 0.00, 0.23, 1.00)
    crop('2_front', 0.23, 0.00, 0.65, 0.56)
    crop('3_side', 0.23, 0.54, 0.65, 1.00)
    crop('4_wing', 0.65, 0.00, 1.00, 0.56)
    crop('5_armor', 0.65, 0.54, 1.00, 1.00)
else:
    crop('1_face', 0.00, 0.00, 0.25, 0.60)
    crop('2_armor', 0.00, 0.55, 0.27, 1.00)
    crop('3_front', 0.22, 0.00, 0.51, 0.60)
    crop('4_side', 0.47, 0.00, 0.65, 0.60)
    crop('5_back', 0.61, 0.00, 1.00, 0.60)
    crop('6_weapon', 0.46, 0.55, 0.75, 1.00)
    crop('7_wing', 0.71, 0.55, 1.00, 1.00)

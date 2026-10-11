# -*- coding: utf-8 -*-
"""裁放伊之助两张三视图的关键区域，用于肉眼核验"""
import os
import sys

import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

OUT = r'D:/work/minimax_h3/logs/_gm_check'
os.makedirs(OUT, exist_ok=True)

JOBS = [
    ('base', r'D:/work/minimax_h3/generated-images/嘴平伊之助_真人质感_三视图基础.png'),
    ('mask', r'D:/work/minimax_h3/generated-images/嘴平伊之助_真人质感_三视图猪头套.png'),
]

for tag, path in JOBS:
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    print('%-6s %dx%d' % (tag, w, h))
    # 左列特写（约 0-33% 宽度）
    crop = img[0:h, 0:int(w * 0.33)]
    crop = cv2.resize(crop, None, fx=1.6, fy=1.6, interpolation=cv2.INTER_CUBIC)
    p = os.path.join(OUT, 'ino_%s_A_closeup.png' % tag)
    cv2.imwrite(p, crop)
    print('   ', p)
    # 右列三视图（约 33%-100%），整体放大 1.3 倍
    crop = img[0:h, int(w * 0.32):w]
    crop = cv2.resize(crop, None, fx=1.3, fy=1.3, interpolation=cv2.INTER_CUBIC)
    p = os.path.join(OUT, 'ino_%s_B_views.png' % tag)
    cv2.imwrite(p, crop)
    print('   ', p)

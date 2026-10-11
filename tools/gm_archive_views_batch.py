# -*- coding: utf-8 -*-
"""批量归档主角团三视图到素材包正式位置"""
import os
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8')

SRC_DIR = r'D:/work/minimax_h3/generated-images'
ROOT = r'D:/work/minimax_h3/assets/鬼灭之刃/character'
NAMES = ['灶门炭治郎', '灶门祢豆子', '我妻善逸', '嘴平伊之助', '富冈义勇',
         '蝴蝶忍', '炼狱杏寿郎', '栗花落香奈乎', '宇髄天元', '甘露寺蜜璃']

ok = 0
for n in NAMES:
    src = os.path.join(SRC_DIR, '%s_真人质感_三视图基础.png' % n)
    if not os.path.exists(src):
        print('MISS %-10s %s' % (n, src))
        continue
    dst_dir = os.path.join(ROOT, n)
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, '人物三视图（基础）.png')
    shutil.copy2(src, dst)
    ok += 1
    print('OK  %-10s %6.0fKB  %s' % (n, os.path.getsize(dst) / 1024, dst))

print('归档 %d / %d' % (ok, len(NAMES)))

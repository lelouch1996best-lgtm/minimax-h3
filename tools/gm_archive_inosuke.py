# -*- coding: utf-8 -*-
"""归档嘴平伊之助的两张三视图到素材包正式位置"""
import os
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8')

GEN = r'D:/work/minimax_h3/generated-images'
CHAR = r'D:/work/minimax_h3/assets/鬼灭之刃/character/嘴平伊之助'

PAIRS = [
    ('嘴平伊之助_真人质感_三视图基础.png', '人物三视图（基础）.png'),
    ('嘴平伊之助_真人质感_三视图猪头套.png', '人物三视图（猪头套）.png'),
]

for src_name, dst_name in PAIRS:
    src = os.path.join(GEN, src_name)
    dst = os.path.join(CHAR, dst_name)
    if not os.path.exists(src):
        print('MISS  %s' % src)
        continue
    shutil.copy2(src, dst)
    print('OK    %6.0fKB  %s' % (os.path.getsize(dst) / 1024, dst))

print()
print('=== 归档后目录 ===')
for f in sorted(os.listdir(CHAR)):
    p = os.path.join(CHAR, f)
    if os.path.isfile(p):
        print('  %-32s %7.0fKB' % (f, os.path.getsize(p) / 1024))
    else:
        n = len([x for x in os.listdir(p) if os.path.isfile(os.path.join(p, x))])
        print('  [%s]  %d 项' % (f, n))

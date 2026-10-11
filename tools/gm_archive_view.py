# -*- coding: utf-8 -*-
"""把生成的三视图归档到素材包正式位置（命名对齐凡人包）"""
import os
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8')

SRC = r'D:/work/minimax_h3/generated-images/灶门炭治郎_真人质感_三视图基础.png'
DST = r'D:/work/minimax_h3/assets/鬼灭之刃/character/灶门炭治郎/人物三视图（基础）.png'

os.makedirs(os.path.dirname(DST), exist_ok=True)
shutil.copy2(SRC, DST)
print('OK', DST)
print('size %.0f KB' % (os.path.getsize(DST) / 1024))

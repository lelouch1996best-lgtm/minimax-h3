# -*- coding: utf-8 -*-
"""15 张真人质感三视图归档到角色目录 + 更新 _人物资产索引.md"""
import os
import re
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT = r'D:/work/minimax_h3/assets/凡人/character'
SRC_DIR = r'D:/work/minimax_h3/generated-images'
INDEX = os.path.join(ROOT, '_人物资产索引.md')

# 角色 -> (生成图名, 索引行附加说明)
ARCHIVE = [
    ('南宫婉', '基础', ''),
    ('紫灵', '基础', '半透明紫色面纱、金冠紫宝石经核验完整保留'),
    ('跟班A', '校服', '无「基础」形态，以「校服」三视图（v2 重制）为身份源；坏笑保留、自然站姿'),
    ('跟班B', '校服', '无「基础」形态，以「校服」三视图（v2 重制）为身份源；银框圆眼镜保留'),
    ('宋玉', '基础', '银翼发饰保留'),
    ('元瑶', '基础', '身份源为历史错拼文件「人物人视图（基础）.png」'),
    ('凌玉灵', '基础', ''),
    ('墨彩环', '基础', ''),
    ('李缨宁', '基础', ''),
    ('柳眉', '基础', '金色角状发饰保留'),
    ('梅凝', '基础', '金色蝴蝶发饰保留'),
    ('燕如嫣', '基础', ''),
    ('穆兰圣女', '基础', '眉间白痣、银冠翠绿宝石经放大核验完整保留'),
    ('辛如音', '基础', ''),
    ('银月', '基础', '狐耳与狐尾按真实毛发质感写实化保留（用户确认方案）'),
]

# 1) 归档
for name, src_tag, _ in ARCHIVE:
    src = os.path.join(SRC_DIR, '%s_真人质感_三视图基础.png' % name)
    dst = os.path.join(ROOT, name, '人物三视图（真人质感-基础）.png')
    if not os.path.exists(src):
        print('MISS SRC', name)
        continue
    shutil.copy2(src, dst)
    print('ARCHIVED %-6s -> %s (%.0fKB)' % (name, dst, os.path.getsize(dst) / 1024))

# 2) 更新索引：文首加批次说明
with open(INDEX, encoding='utf-8') as f:
    text = f.read()

anchor = '覆盖 21 个角色（不含跟班A、跟班B、马姓老者）'
batch_note = ('\n> 全批次统一变体（2026-10-07）：`真人质感-基础`＝造型与「基础」完全一致，仅渲染替换为'
              '**真人实拍质感**（真实皮肤毛孔、织物纹理、白底两列版式：左面部特写＋右三视图），'
              '65535 `gpt-image-2` 图生图、以各自「基础」三视图为参考图生成；'
              '首批覆盖 15 名女性角色（跟班A/B 无「基础」，以校服版为身份源）。'
              '文思月因上游安全审核误拒暂缺（其基础版深 V 纱裙触发误判，两次重试均拒）。')
if '真人质感-基础`＝造型与「基础」完全一致' not in text:
    text = text.replace(anchor, anchor + batch_note, 1)
    print('INDEX header note added')

# 3) 每个角色的表追加行
for name, src_tag, extra in ARCHIVE:
    src_desc = '「%s」三视图' % src_tag if src_tag != '基础' else '「基础」三视图'
    row = ('| 真人质感-基础 | 造型与「%s」完全一致，仅渲染改为真人实拍质感（见文首 2026-10-07 批次说明）；'
           '2026-10-07 由 65535 `gpt-image-2` 以%s为参考图生成%s |'
           % (src_tag, src_desc, ('；' + extra) if extra else ''))
    # 定位该角色 section 的表格最后一行
    m = re.search(r'(## %s（女）\n(?:.*\n)*?)(\n## |\Z|\n辅助资产)' % re.escape(name), text)
    if not m:
        print('INDEX MISS section', name)
        continue
    seg = m.group(1)
    lines = seg.rstrip('\n').split('\n')
    last_table = max(i for i, l in enumerate(lines) if l.startswith('|'))
    lines.insert(last_table + 1, row)
    new_seg = '\n'.join(lines) + '\n'
    text = text.replace(seg, new_seg, 1)
    print('INDEX row added:', name)

with open(INDEX, 'w', encoding='utf-8', newline='\n') as f:
    f.write(text)
print('INDEX saved')

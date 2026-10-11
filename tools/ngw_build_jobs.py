# -*- coding: utf-8 -*-
"""从 NGW_H3提示词.md 的六段代码块提取 prompt，写入 Ref2VA jobs JSON。

六段顺序固定（见 h3-prompt-writing/references/ref-en.txt）：
  subject_definitions -> summary -> retention_analysis -> detailed_description
  -> overall_soundscape -> non_diegetic_music
用段标题（行首无缩进、且以 _ 或 detailed_description 结尾的行）定位，
避免抓到文件开头的命令代码块。
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

MD = r'D:/work/minimax_h3/南宫婉灵动表情/NGW_H3提示词.md'
OUT = r'D:/work/minimax_h3/南宫婉灵动表情/NGW-jobs.json'

text = open(MD, encoding='utf-8').read()

SECTIONS = ['subject_definitions', 'summary', 'retention_analysis',
            'detailed_description', 'overall_soundscape', 'non_diegetic_music']

# 定位六段：从 "## 六段提示词" 之后的代码块里按段标题切分
marker = text.index('## 六段提示词')
body = text[marker:]

# 行扫描取第一个围栏代码块（避免正则里反引号在 shell/ heredoc 中被转义）
lines = body.split('\n')
start = next((i for i, l in enumerate(lines) if l.strip().startswith('```')), -1)
if start < 0:
    raise SystemExit('FATAL: 未找到围栏起始行')
end = next((i for i in range(start + 1, len(lines)) if lines[i].strip().startswith('```')), -1)
if end < 0:
    raise SystemExit('FATAL: 未找到围栏结束行')
full = '\n'.join(lines[start + 1:end])

if not full.strip().startswith('subject_definitions'):
    raise SystemExit('FATAL: 代码块首行应为 subject_definitions，实际=%r' % full.strip()[:40])

lines = full.split('\n')
sections = {}
cur = None
buf = []
for ln in lines:
    st = ln.strip()
    hit = next((s for s in SECTIONS if st == s), None)
    if hit:
        if cur:
            sections[cur] = '\n'.join(buf).strip()
        cur = hit
        buf = []
    elif cur is not None:
        buf.append(ln)
if cur:
    sections[cur] = '\n'.join(buf).strip()

missing = [s for s in SECTIONS if s not in sections or not sections[s]]
if missing:
    raise SystemExit('FATAL: 缺段 ' + ', '.join(missing))

# run_t8balance.py 期望 prompt_file（指向含六段的 md），并自行 extract_prompt
PROMPT_MD = r'D:/work/minimax_h3/南宫婉灵动表情/NGW_H3提示词.md'
prompt = '\n\n'.join(s + ':\n' + sections[s] for s in SECTIONS)

# 红线自检
CLAUSE = 'No subtitles, captions, or on-screen text appear at any point in the video.'
if prompt.count(CLAUSE) < 1:
    raise SystemExit('FATAL: 无字幕红线缺失')
if not prompt.startswith('subject_definitions:'):
    raise SystemExit('FATAL: 段序错乱，首段应为 subject_definitions，实际=%r' % prompt[:40])
if not os.path.exists(PROMPT_MD):
    raise SystemExit('FATAL: prompt_file 不存在 ' + PROMPT_MD)
if '[Shot 1]' not in sections['detailed_description']:
    raise SystemExit('FATAL: 缺 [Shot 1]')
for t in ['00:05.000', '00:10.000']:
    if t not in sections['detailed_description']:
        raise SystemExit('FATAL: 缺切镜时间码 ' + t)

for s in SECTIONS:
    print('%-22s %5d chars' % (s, len(sections[s])))
print('TOTAL prompt chars = %d' % len(prompt))

jobs = [{
    'tag': 'NGW01',
    'out': '南宫婉_灵动表情_运镜_15s',
    'seconds': 15,
    'prompt_file': PROMPT_MD,
    'images': [
        r'D:/work/minimax_h3/assets/凡人/character/南宫婉/人物三视图（真人质感-基础）.png',
        r'D:/work/minimax_h3/generated-images/南宫婉_古典美_电影滤镜_人物展示.png',
    ],
}]

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(jobs, f, ensure_ascii=False, indent=2)

print('WROTE %s (%d bytes)' % (OUT, os.path.getsize(OUT)))
for p in jobs[0]['images']:
    print('  img exists=%s %s' % (os.path.exists(p), os.path.basename(p)))

# -*- coding: utf-8 -*-
"""从 md 的 ```text 围栏提取 Ref2VA 六段提示词 → 写jobs JSON（run_t8balance.py 格式）。

run_t8balance.py 要求：
  - job字段 = {tag, out, seconds, prompt_file, images[]}（不要内联 prompt）
  - extract_prompt() 正则 = r"```text\n(.*?)\n```" → 围栏必须带 text 语言标记
  - 行扫描取围栏（避免 shell/heredoc 里反引号被转义，re.findall 会失效）
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

MD = r'D:/work/minimax_h3/南宫婉灵动表情/MPL_H3提示词.md'
OUT = r'D:/work/minimax_h3/南宫婉灵动表情/MPL-jobs.json'

SECTIONS = ['subject_definitions', 'summary', 'retention_analysis',
            'detailed_description', 'overall_soundscape', 'non_diegetic_music']
CLAUSE = 'No subtitles, captions, or on-screen text appear at any point in the video.'

text = open(MD, encoding='utf-8').read()
body = text[text.index('## 六段提示词'):]

lines = body.split('\n')
start = next((i for i, l in enumerate(lines) if l.strip().startswith('```')), -1)
if start < 0:
    raise SystemExit('FATAL: 未找到围栏起始行')
end = next((i for i in range(start + 1, len(lines)) if lines[i].strip().startswith('```')), -1)
if end < 0:
    raise SystemExit('FATAL: 未找到围栏结束行')
full = '\n'.join(lines[start + 1:end])

sections, cur, buf = {}, None, []
for ln in full.split('\n'):
    st = ln.strip()
    hit = next((s for s in SECTIONS if st == s), None)
    if hit:
        if cur:
            sections[cur] = '\n'.join(buf).strip()
        cur, buf = hit, []
    elif cur is not None:
        buf.append(ln)
if cur:
    sections[cur] = '\n'.join(buf).strip()

missing = [s for s in SECTIONS if not sections.get(s)]
if missing:
    raise SystemExit('FATAL: 缺段 ' + ', '.join(missing))

prompt = '\n\n'.join(s + ':\n' + sections[s] for s in SECTIONS)
if prompt.count(CLAUSE) < 1:
    raise SystemExit('FATAL: 无字幕红线缺失')
if not prompt.startswith('subject_definitions:'):
    raise SystemExit('FATAL: 段序错乱')
if '[Shot 1]' not in sections['detailed_description']:
    raise SystemExit('FATAL: 缺 [Shot 1]')
for t in ('00:05.000', '00:10.000'):
    if t not in sections['detailed_description']:
        raise SystemExit('FATAL: 缺切镜时间码 ' + t)

for s in SECTIONS:
    print('%-22s %5d chars' % (s, len(sections[s])))
print('TOTAL prompt chars = %d' % len(prompt))
print('closeup mentions = %d' % prompt.lower().count('close-up'))

IMGS = [
    r'D:/work/minimax_h3/assets/凡人/character/幕沛灵/人物三视图（真人质感-基础）.png',
    r'D:/work/minimax_h3/generated-images/幕沛灵_古典美_电影滤镜_面部特写.png',
]
jobs = [{
    'tag': 'MPL01',
    'out': '幕沛灵_面部特写_灵动表情_15s',
    'seconds': 15,
    'prompt_file': MD,
    'images': IMGS,
}]

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(jobs, f, ensure_ascii=False, indent=2)
print('WROTE %s (%d bytes)' % (OUT, os.path.getsize(OUT)))
for p in IMGS:
    print('  img exists=%s %s' % (os.path.exists(p), os.path.basename(p)))

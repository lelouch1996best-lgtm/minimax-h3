# -*- coding: utf-8 -*-
"""选择风格出图 —— 用指定风格的 sref 给提示词批量定调出图。

用法：
  python render_tone.py --tone TONE-01 --prompt "…" --out <目录> --tag shot15
  python render_tone.py --tone TONE-01 --prompts-file shots.json --out <目录>
  python render_tone.py --tone TONE-01 --dry-run --prompt "…"     # 只看请求体

shots.json 格式（数组，或 {"shots": [...]}）：
  [{"tag": "shot15", "prompt": "…", "negative": "可选覆盖", "sw": 550}]

说明：POST 一律不自动重试（防重复扣费）。一次调用一次计费，请先 --dry-run 核对。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tone_lib as T  # noqa: E402


def load_shots(args):
    if args.prompt:
        return [{'tag': args.tag or 'shot', 'prompt': args.prompt}]
    if args.prompts_file:
        with open(args.prompts_file, encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = data.get('shots') or []
        return data
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tone', default='', help='风格 ID 或 slug')
    ap.add_argument('--prompt', default='', help='单条提示词')
    ap.add_argument('--prompts-file', default='', help='批量提示词 JSON')
    ap.add_argument('--out', default='.', help='输出目录')
    ap.add_argument('--tag', default='', help='输出文件名前缀（单条时用）')
    ap.add_argument('--sw', type=int, default=None, help='覆盖风格权重')
    ap.add_argument('--negative', default='', help='覆盖负向词')
    ap.add_argument('--list', action='store_true', help='只列风格，不出图')
    ap.add_argument('--dry-run', action='store_true', help='只打印请求体')
    args = ap.parse_args()

    idx = T.load_index()
    if args.list:
        for t in idx.get('tones', []):
            print('%-9s %-24s sw=%s  %s' % (t['id'], t.get('name', ''), t.get('sw', '-'),
                                            '已上传' if t.get('sref_url') else '未上传'))
        return 0

    if not args.tone:
        print('必须用 --tone 指定风格（--list 可看全部）')
        return 1
    tone = T.find_tone(idx, args.tone)
    if not tone:
        print('未找到风格: %s' % args.tone)
        return 1
    if not tone.get('sref_url'):
        print('风格 %s 尚未上传图床（sref_url 为空），无法定调出图' % tone['id'])
        return 1

    shots = load_shots(args)
    if not shots:
        print('没有可执行的提示词（给 --prompt 或 --prompts-file）')
        return 1

    sw = args.sw if args.sw is not None else tone.get('sw', 500)
    print('风格: [%s] %s   sw=%s   v%s' % (tone['id'], tone.get('name', ''), sw, tone.get('version')))
    print('sref: %s' % tone['sref_url'])
    print('计划出图 %d 条' % len(shots))

    if args.dry_run:
        for s in shots:
            body = {'prompt': s.get('prompt', ''), 'sref': tone['sref_url'],
                    'sw': int(s.get('sw', sw)), 'version': str(tone.get('version', '7')),
                    'size': tone.get('size', '16:9'), 'quality': str(tone.get('quality', '2'))}
            print(json.dumps(body, ensure_ascii=False, indent=2)[:600])
            print('-' * 60)
        print('(dry-run，未提交)')
        return 0

    results = []
    for s in shots:
        tag = s.get('tag') or 'shot'
        neg = s.get('negative') or args.negative or tone.get('negative', '')
        print('\n>>> %s' % tag)
        tid, paths = T.mj_generate(
            prompt=s.get('prompt', ''), sref_url=tone['sref_url'],
            out_dir=args.out, tag='%s_%s' % (tone['id'], tag), negative=neg,
            sw=int(s.get('sw', sw)), version=tone.get('version'),
            size=tone.get('size'), quality=tone.get('quality'))
        print('    task_id=%s  下载 %d 个文件' % (tid, len(paths)))
        for p in paths:
            print('    %s' % p)
        results.append({'tag': tag, 'task_id': tid, 'files': [str(p) for p in paths]})

    print('\n汇总:')
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())

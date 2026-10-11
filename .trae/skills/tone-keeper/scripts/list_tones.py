# -*- coding: utf-8 -*-
"""预览已有风格 —— 列出全部基调，或生成一张预览联系表。

用法：
  python list_tones.py                 # 文本列表（含六维定义摘要）
  python list_tones.py --sheet         # 生成九宫格联系表 PNG，供肉眼预览
  python list_tones.py --sheet --out X.png
  python list_tones.py --json          # 机器可读
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tone_lib as T  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sheet', action='store_true', help='生成预览联系表 PNG')
    ap.add_argument('--json', action='store_true', help='输出 JSON')
    ap.add_argument('--out', default='', help='联系表输出路径')
    args = ap.parse_args()

    idx = T.load_index()
    tones = idx.get('tones', [])

    if args.json:
        print(json.dumps(tones, ensure_ascii=False, indent=2))
        return 0

    if not tones:
        print('风格库为空：%s' % T.index_path())
        print('用 add_tone.py 新增第一个风格。')
        return 0

    if args.sheet:
        out = args.out or str(T.library_dir() / '_预览联系表.png')
        p = T.make_contact_sheet(tones, out)
        print('联系表已生成: %s' % p)
        for t in tones:
            print('  %-9s %s' % (t['id'], t.get('name', '')))
        return 0

    print('风格库目录: %s' % T.library_dir())
    print('共 %d 个风格' % len(tones))
    print('=' * 78)
    for t in tones:
        kp = T.key_image_path(t)
        print('[%s] %s' % (t['id'], t.get('name', '')))
        print('    slug     : %s' % t.get('slug', ''))
        print('    sref     : %s' % (('已登记 ' + t['sref_url'][:60] + '…') if t.get('sref_url') else '未上传'))
        print('    sw / 版本: %s / v%s' % (t.get('sw', '-'), t.get('version', '-')))
        print('    基准图   : %s%s' % (kp, '' if kp.exists() else '  [缺失]'))
        dims = t.get('dims') or {}
        for k, v in dims.items():
            print('    %-8s : %s' % (k, v))
        if t.get('desc'):
            print('    定义     : %s' % t['desc'])
        if t.get('notes'):
            print('    备注     : %s' % t['notes'])
        print('-' * 78)
    return 0


if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-
"""新增风格 —— 登记一张已有基准图，或用 65535 生成基准图后再登记。

流程：基准图 → 压出 sref 源 → 上传图床拿公网直链 → 写入 tones.json。

用法：
  # A) 登记已有基准图（最常见）
  python add_tone.py --id TONE-02 --name "幻境暖调" --from-image "D:/.../SC-03.png"

  # B) 用 65535 生成基准图后登记（可带参考图，多张用 --ref 重复给）
  python add_tone.py --id TONE-03 --name "雪夜冷灰" \
      --prompt "<完整基准图提示词>" --ref "<参考图1>" --ref "<参考图2>"

  # C) 已有图床直链，跳过上传
  python add_tone.py --id TONE-04 --name "…" --from-image X.png --sref-url "https://…"

可选：
  --dims-file  六维定义 JSON（{"色彩":"…","光影":"…","质感":"…","影调":"…","镜头":"…","参照系":"…"}）
  --desc       一句话定义（整体风格描述）
  --sw         风格权重，默认取 config.json 的 mj_api.sw
  --negative   覆盖默认负向词
  --source     来源说明（如 "65535 双参考图 SC-05 + CH-01"）
  --notes      备注
  --no-upload  只登记本地，不传图床（sref_url 留空，出图前需补）
"""
import argparse
import datetime
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tone_lib as T  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', required=True, help='风格 ID，如 TONE-02')
    ap.add_argument('--name', required=True, help='风格名称，如「中国电影感古风·冷青」')
    ap.add_argument('--slug', default='', help='英文短名，默认由 ID 生成')
    ap.add_argument('--from-image', default='', help='已有基准图路径')
    ap.add_argument('--prompt', default='', help='用 65535 生成基准图的提示词')
    ap.add_argument('--ref', action='append', default=[], help='参考图路径（可多次）')
    ap.add_argument('--sref-url', default='', help='已有图床直链，跳过上传')
    ap.add_argument('--dims-file', default='', help='六维定义 JSON 文件')
    ap.add_argument('--desc', default='', help='一句话定义')
    ap.add_argument('--sw', type=int, default=None)
    ap.add_argument('--version', default=None)
    ap.add_argument('--negative', default='')
    ap.add_argument('--source', default='')
    ap.add_argument('--notes', default='')
    ap.add_argument('--no-upload', action='store_true')
    args = ap.parse_args()

    tid = args.id.strip().upper()
    idx = T.load_index()
    if T.find_tone(idx, tid):
        print('已存在同 ID 风格：%s（如需替换请先手动移除）' % tid)
        return 1

    if not args.from_image and not args.prompt:
        print('必须给 --from-image（登记已有图）或 --prompt（生成新基准图）')
        return 1

    slug = args.slug or tid.lower().replace('tone-', 'tone')
    tone = {'id': tid, 'name': args.name, 'slug': slug}
    folder = T.tone_folder(tone)
    folder.mkdir(parents=True, exist_ok=True)

    # 1) 得到基准图
    key_png = folder / 'key.png'
    if args.prompt:
        print('用 65535 生成基准图…')
        T.gen_base_image(args.prompt, key_png, refs=args.ref or None)
        print('  基准图: %s' % key_png)
    else:
        src = Path(args.from_image)
        if not src.exists():
            print('基准图不存在: %s' % src)
            return 1
        if src.suffix.lower() in ('.png', '.bmp'):
            shutil.copy2(src, key_png)
        else:
            # 非 PNG 统一转存为 PNG，保证预览一致
            im = T.read_image(src)
            import cv2
            cv2.imencode('.png', im)[1].tofile(str(key_png))
        print('  基准图: %s' % key_png)

    # 2) 压出 sref 源
    sref_jpg = folder / 'sref.jpg'
    T.make_sref_source(key_png, sref_jpg)
    kb = sref_jpg.stat().st_size / 1024
    print('  sref 源: %s（%.0f KB）' % (sref_jpg, kb))

    # 3) 图床直链
    sref_url = args.sref_url.strip()
    if not sref_url and not args.no_upload:
        print('  上传图床…')
        r = T.upload_image(sref_jpg)
        sref_url = r.get('url', '')
        print('  直链: %s' % sref_url)
    elif args.no_upload:
        print('  （跳过上传，sref_url 留空）')

    # 4) 六维定义
    dims = {}
    if args.dims_file:
        with open(args.dims_file, encoding='utf-8') as f:
            dims = json.load(f)

    tone.update({
        'key_image': 'key.png',
        'sref_image': 'sref.jpg',
        'sref_url': sref_url,
        'sw': int(args.sw if args.sw is not None else T.CONFIG.get('mj_api', {}).get('sw', 500)),
        'version': args.version or T.CONFIG.get('mj_api', {}).get('version', '7'),
        'size': T.CONFIG.get('mj_api', {}).get('size', '16:9'),
        'quality': T.CONFIG.get('mj_api', {}).get('quality', '2'),
        'negative': args.negative or T.default_negative(),
        'dims': dims,
        'desc': args.desc,
        'source': args.source,
        'notes': args.notes,
        'created': datetime.date.today().isoformat(),
    })

    idx.setdefault('tones', []).append(tone)
    idx.setdefault('version', 1)
    T.save_index(idx)
    print('已登记风格 %s → %s' % (tid, T.index_path()))
    return 0


if __name__ == '__main__':
    sys.exit(main())

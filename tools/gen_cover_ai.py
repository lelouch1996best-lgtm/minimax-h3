# -*- coding: utf-8 -*-
"""通用封面生图（65535 图生图，单张提交，不抽卡）。

提示词从简（2026-10-11 用户指定）：
    只给「参考图 + 标题」，不复述身份/服装/光位/负面清单等长段规格——
    参考图本身已经承载身份、场景、影调，复述反而容易和参考图打架、增加漂移。
    一律走 tools/gen_cover_ai.py 生成，不要再手写长提示词脚本。

用法：
    python tools/gen_cover_ai.py --ref <参考图> --title "<封面标题>" \
        [--out <输出png>] [--size 9:16] [--extra "<可选：最多一句补充约束>"]

示例：
    python tools/gen_cover_ai.py \
        --ref "D:/work/minimax_h3/一脚踩出的坑爹时刻/发布/_src_s31.jpg" \
        --title "一脚踩断刹车板，才发现它是塑料的" \
        --out "D:/work/minimax_h3/generated-images/坑爹时刻_E1_封面AI_9x16.png" \
        --extra "竖幅 9:16，不要水印、logo、二维码"

说明：
  - 需要环境变量 S65535_API_KEY。
  - 参考图建议先用 cv2 读入校验（含中文路径安全）；这里直接走 np.fromfile + imdecode。
  - 输出为 PNG（原尺寸 2k），后续用 make_cover.py --src 生成三平台 8 位 RGB 封面。
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

API = os.environ.get('S65535_API_KEY')
BASE = 'https://task-api-1-cn.65535.space'
MODEL = 'gpt-image-2.5-flare'

# 2026-10-12：结果 CDN 会 403 掉无 UA 的 urllib 请求（实测踩到）→ 统一带浏览器 UA
_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')


def build_prompt(title, extra=''):
    """一句式提示词：参考图 + 标题，其余交给模型。"""
    p = '请根据我给的参考图和标题，设计一个封面，标题内容是"%s"' % title
    extra = (extra or '').strip()
    if extra:
        p += '。' + extra
    return p


def load_b64(path, long_edge=1536, q=86):
    raw = np.fromfile(path, dtype=np.uint8)          # 中文路径安全
    img = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError('图片解码失败: ' + path)
    h, w = img.shape[:2]
    scale = long_edge / max(h, w)
    if scale < 1:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), q])
    if not ok:
        raise RuntimeError('JPEG 编码失败: ' + path)
    b = buf.tobytes()
    print('    参考图 %s  %dx%d  %.0fKB' % (os.path.basename(path), img.shape[1], img.shape[0], len(b) / 1024))
    return 'data:image/jpeg;base64,' + base64.b64encode(b).decode('ascii')


def api(method, path, payload=None, timeout=180):
    url = BASE + path
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8') if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Authorization', 'Bearer ' + API)
    req.add_header('User-Agent', _UA)
    if data:
        req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ref', required=True, help='参考图（单张；优先复用核验抽帧）')
    ap.add_argument('--title', required=True, help='封面标题内容')
    ap.add_argument('--out', help='输出 PNG 路径（默认为 <cwd>/cover_ai.png）')
    ap.add_argument('--size', default='9:16', help='画幅，默认 9:16 竖幅')
    ap.add_argument('--extra', default='', help='可选：最多一句补充约束')
    args = ap.parse_args()

    if not API:
        print('FATAL: S65535_API_KEY 未设置')
        return 1
    if not os.path.exists(args.ref):
        print('FATAL: 参考图不存在: ' + args.ref)
        return 1

    out = args.out or os.path.join(os.getcwd(), 'cover_ai.png')
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)

    prompt = build_prompt(args.title, args.extra)
    print('[提示词] ' + prompt)

    print('[1/3] 编码参考图')
    uri = load_b64(args.ref)

    print('[2/3] 提交任务（%s / %s / 2k / n=1）' % (MODEL, args.size))
    payload = {
        'kind': 'image', 'model': MODEL,
        'input': {'prompt': prompt, 'size': args.size, 'resolution': '2k', 'n': 1, 'image': [uri]},
    }
    resp = api('POST', '/v1/tasks', payload)
    tid = resp.get('id') or resp.get('task_id')
    if not tid:
        print('提交失败:', json.dumps(resp, ensure_ascii=False)[:600])
        return 1
    print('    task ->', tid)

    print('[3/3] 轮询')
    st = {}
    for i in range(120):
        time.sleep(5)
        try:
            st = api('GET', '/v1/tasks/' + str(tid), timeout=60)
        except urllib.error.HTTPError:
            continue
        s = st.get('status')
        if s in ('done', 'failed'):
            print('    [%02d] %s' % (i, s))
            break
    if st.get('status') != 'done':
        print('未成功:', json.dumps(st, ensure_ascii=False)[:500])
        return 1

    urls = st.get('result_urls') or []
    if not urls:
        print('无 result_urls:', json.dumps(st, ensure_ascii=False)[:400])
        return 1
    # 2026-10-12：结果 CDN（task1.65535.space）对无 UA 的 urllib 直接 403 →
    # 必须带浏览器 UA + Referer，且逐 URL 兜底重试（任务已 done 时别白白重跑）。
    blob = None
    for u in urls:
        try:
            req = urllib.request.Request(u)
            req.add_header('User-Agent', _UA)
            req.add_header('Referer', BASE + '/')
            req.add_header('Accept', '*/*')
            with urllib.request.urlopen(req, timeout=180) as r:
                blob = r.read()
            break
        except Exception as e:
            print('    下载失败 %s ...: %s' % (u[:80], e))
    if blob is None:
        print('全部结果 URL 下载失败；任务已 done，可用 --resume-task 补拉（见日志）')
        return 1
    with open(out, 'wb') as f:                        # 中文路径安全
        f.write(blob)
    print('    -> %.0fKB  %s' % (len(blob) / 1024, out))
    return 0


if __name__ == '__main__':
    sys.exit(main())

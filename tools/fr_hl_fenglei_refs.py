# -*- coding: utf-8 -*-
"""凡人修仙传 · 韩立「风雷翅」参考图搜索与下载（Tavily include_images）

流程：多 query 搜图 -> 去重 -> curl 下载（带 UA，Python urllib 易被 403）-> cv2 校验真图
      -> 落盘 raw.json + 拼联系表 contact_sheet.jpg 供肉眼核验

输出目录：assets/凡人/character/韩立/_refs_fenglei/
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')


def get_key():
    k = os.environ.get('TAVILY_API_KEY', '').strip()
    if k:
        return k
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as h:
            v, _ = winreg.QueryValueEx(h, 'TAVILY_API_KEY')
            return v.strip()
    except Exception:
        return ''


KEY = get_key()
RAW = r'D:/work/minimax_h3/assets/凡人/character/韩立/_refs_fenglei'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

QUERIES = [
    '凡人修仙传 韩立 风雷翅 动画 剧照',
    '凡人修仙传 风雷翅 翅膀 设定',
    '韩立 风雷翅 雷鹏 法宝 特效',
]


def tv(q):
    body = json.dumps({
        'query': q,
        'search_depth': 'advanced',
        'max_results': 8,
        'include_images': True,
        'include_image_descriptions': True,
    }).encode('utf-8')
    req = urllib.request.Request(
        'https://api.tavily.com/search',
        data=body,
        headers={'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode('utf-8'))


def dl(url, path):
    r = subprocess.run(['curl', '-sSL', '--max-time', '60', '-A', UA, '-o', path, url],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(path) or os.path.getsize(path) < 3000:
        return None
    raw = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if img is None:
        return None
    return img


def main():
    if not KEY:
        print('NO_TAVILY_KEY')
        return 1
    os.makedirs(RAW, exist_ok=True)

    items = []
    for q in QUERIES:
        try:
            data = tv(q)
        except (urllib.error.HTTPError, Exception) as e:
            print('ERR %s -> %r' % (q, e))
            continue
        imgs = data.get('images') or []
        print('QUERY "%s" -> %d images' % (q, len(imgs)))
        for it in imgs:
            if isinstance(it, dict):
                items.append({'url': it.get('url', ''), 'desc': it.get('description', ''), 'q': q})
            else:
                items.append({'url': it, 'desc': '', 'q': q})
        time.sleep(1)

    seen, uniq = set(), []
    for it in items:
        u = it['url']
        if u and u not in seen:
            seen.add(u)
            uniq.append(it)
    print('UNIQUE %d' % len(uniq))

    ok = []
    for i, it in enumerate(uniq, 1):
        name = 'r%02d.jpg' % i
        p = os.path.join(RAW, name)
        img = dl(it['url'], p)
        if img is None:
            continue
        h, w = img.shape[:2]
        if w < 200 or h < 200:
            continue
        it['file'] = name
        it['size'] = [w, h]
        ok.append(it)
        print('  [%02d] %dx%d  %s' % (len(ok), w, h, it['url'][:80]))
        time.sleep(0.3)

    with open(os.path.join(RAW, 'raw.json'), 'w', encoding='utf-8') as f:
        json.dump(ok, f, ensure_ascii=False, indent=1)

    if not ok:
        print('NO_IMAGES')
        return 1

    cols, cell = 5, 300
    rows = (len(ok) + cols - 1) // cols
    sheet = np.full((rows * (cell + 26), cols * cell, 3), 245, np.uint8)
    for idx, it in enumerate(ok):
        img = cv2.imdecode(np.fromfile(os.path.join(RAW, it['file']), dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        h, w = img.shape[:2]
        s = min(cell / w, cell / h)
        th = cv2.resize(img, (max(1, int(w * s)), max(1, int(h * s))), interpolation=cv2.INTER_AREA)
        r, c = divmod(idx, cols)
        y0 = r * (cell + 26) + 22
        x0 = c * cell
        sheet[y0:y0 + th.shape[0], x0:x0 + th.shape[1]] = th
        cv2.putText(sheet, str(idx + 1), (x0 + 6, r * (cell + 26) + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (30, 30, 200), 2)
    sp = os.path.join(RAW, 'contact_sheet.jpg')
    okk, buf = cv2.imencode('.jpg', sheet, [int(cv2.IMWRITE_JPEG_QUALITY), 86])
    buf.tofile(sp)
    print('SHEET %s  %dx%d  exists=%s' % (sp, sheet.shape[1], sheet.shape[0], os.path.exists(sp)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

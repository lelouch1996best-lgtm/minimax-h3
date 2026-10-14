# -*- coding: utf-8 -*-
"""65535 任务结果下载器（带 User-Agent，绕过 COS 直链 403）

背景：65535 `result_urls` 的 COS 直链在 2026-10-12 起对无 UA 的请求返回 HTTP 403，
      带常规浏览器 UA 即可正常下载。本工具专门用于「任务已扣费成功、仅下载失败」时
      补下载，避免重跑造成重复扣费。

用法：
  python tools/dl65535.py <task_id> [输出路径]
  不给输出路径时默认写入 generated-images/<task_id>.png
"""
import json
import os
import subprocess
import sys
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

API = os.environ.get('S65535_API_KEY')
BASE = 'https://task-api-1-cn.65535.space'
OUT = r'D:/work/minimax_h3/generated-images'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')


def api_get(path, timeout=60):
    req = urllib.request.Request(BASE + path)
    req.add_header('Authorization', 'Bearer ' + API)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def download(url, dst, timeout=300):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    r = subprocess.run(['curl', '-sS', '--max-time', str(timeout), '-A', UA, '-o', dst, url],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(dst) or os.path.getsize(dst) == 0:
        raise RuntimeError('curl 下载失败: %s' % ((r.stderr or r.stdout).strip()[:300]))
    return os.path.getsize(dst)


def main():
    args = sys.argv[1:]
    if not args:
        print('用法: python tools/dl65535.py <task_id> [输出路径]')
        sys.exit(1)
    tid = args[0]
    dst = args[1] if len(args) > 1 else os.path.join(OUT, tid + '.png')

    if not API:
        print('FATAL: S65535_API_KEY 未设置')
        sys.exit(1)

    st = api_get('/v1/tasks/' + tid)
    status = st.get('status')
    if status != 'done':
        print('任务状态非 done: %s' % status)
        print(json.dumps(st, ensure_ascii=False)[:400])
        sys.exit(1)

    urls = st.get('result_urls') or []
    if not urls:
        print('无 result_urls')
        sys.exit(1)

    n = download(urls[0], dst)
    print('OK %.0fKB -> %s' % (n / 1024, dst))


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""tone-keeper 共享库

职责：风格库读写、基准图压缩、图床上传、65535 出图、MJ sref 出图。

纯标准库实现网络与会话逻辑；仅像素处理（压图 / 联系表）依赖 cv2 / PIL，
因此涉及像素操作的入口应在 config.json 指定的 python_exe（venv）下运行。
"""
from __future__ import annotations

import base64
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = SKILL_DIR / 'config.json'
INDEX_NAME = 'tones.json'


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding='utf-8') as f:
            return json.load(f)
    return {}


CONFIG = load_config()


def library_dir() -> Path:
    p = (os.environ.get('TONE_LIBRARY_DIR')
         or CONFIG.get('library_dir')
         or r'D:/work/minimax_h3/assets/风格库')
    return Path(p)


def python_exe() -> str:
    return CONFIG.get('python_exe') or sys.executable


def index_path() -> Path:
    return library_dir() / INDEX_NAME


def load_index() -> dict:
    p = index_path()
    if not p.exists():
        return {'version': 1, 'tones': []}
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def save_index(idx: dict) -> None:
    p = index_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)


def find_tone(idx: dict, tone_id: str):
    """按 id 或 slug 查找风格，大小写不敏感。"""
    key = str(tone_id or '').strip().upper()
    low = str(tone_id or '').strip().lower()
    for t in idx.get('tones', []):
        if str(t.get('id', '')).upper() == key:
            return t
        if str(t.get('slug', '')).lower() == low:
            return t
    return None


def tone_folder(tone: dict) -> Path:
    return library_dir() / ('%s_%s' % (tone['id'], tone.get('slug') or 'tone'))


def default_negative() -> str:
    return CONFIG.get('default_negative', '')


def key_image_path(tone: dict) -> Path:
    p = Path(tone.get('key_image') or 'key.png')
    return p if p.is_absolute() else tone_folder(tone) / p


def sref_image_path(tone: dict) -> Path:
    p = Path(tone.get('sref_image') or 'sref.jpg')
    return p if p.is_absolute() else tone_folder(tone) / p


# ============================================================ 图片处理（cv2 / PIL）
def _cv2():
    import cv2
    import numpy as np
    return cv2, np


def read_image(path):
    cv2, np = _cv2()
    im = cv2.imdecode(np.fromfile(str(path), dtype='uint8'), cv2.IMREAD_COLOR)
    if im is None:
        raise RuntimeError('无法读取图片: %s' % path)
    return im


def make_sref_source(src, dst, max_side: int = None, quality: int = None) -> Path:
    """把基准图压成 sref 源（长边 max_side / JPEG q<quality>），确保远小于图床 1MiB 上限。"""
    cv2, _ = _cv2()
    max_side = int(max_side or CONFIG.get('sref_max_side', 1536))
    quality = int(quality or CONFIG.get('sref_jpeg_quality', 90))
    im = read_image(src)
    h, w = im.shape[:2]
    s = max_side / float(max(h, w))
    if s < 1.0:
        im = cv2.resize(im, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    cv2.imencode('.jpg', im, [int(cv2.IMWRITE_JPEG_QUALITY), quality])[1].tofile(str(dst))
    return dst


def make_contact_sheet(tone_list, out_path, cols: int = 3, cell_w: int = 560, pad: int = 16) -> Path:
    """把所有风格的基准图拼成一张预览联系表（带 ID / 名称标签）。"""
    from PIL import Image, ImageDraw, ImageFont

    try:
        font = ImageFont.truetype(r'C:/Windows/Fonts/msyh.ttc', 20)
    except Exception:
        font = ImageFont.load_default()

    items = []
    for t in tone_list:
        kp = key_image_path(t)
        if kp.exists():
            items.append((t, Image.open(kp).convert('RGB')))
    if not items:
        raise RuntimeError('没有可预览的基准图（检查 key_image 路径）')

    cell_h = int(cell_w * 9 / 16)
    label_h = 34
    rows = (len(items) + cols - 1) // cols
    W = cols * (cell_w + pad) + pad
    H = rows * (cell_h + label_h + pad) + pad
    sheet = Image.new('RGB', (W, H), (245, 245, 243))
    dr = ImageDraw.Draw(sheet)

    for i, (t, im) in enumerate(items):
        r, c = divmod(i, cols)
        x = pad + c * (cell_w + pad)
        y = pad + r * (cell_h + label_h + pad)
        sheet.paste(im.resize((cell_w, cell_h), Image.LANCZOS), (x, y))
        dr.rectangle([x, y, x + cell_w, y + cell_h], outline=(180, 178, 173), width=1)
        dr.text((x + 4, y + cell_h + 6),
                '%s  %s' % (t['id'], t.get('name', '')),
                fill=(30, 30, 30), font=font)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    return out_path


# ============================================================ 图床上传
def upload_image(path) -> dict:
    """调用 WorkBuddy 资料库图床组件，返回 {url, width, height}。"""
    script = CONFIG.get('upload_script')
    if not script or not Path(script).exists():
        raise RuntimeError('未找到图床上传脚本（config.json → upload_script）')
    r = subprocess.run([python_exe(), str(script), str(path)],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    out = (r.stdout or '') + '\n' + (r.stderr or '')
    m = re.search(r'KS_IMAGE_UPLOAD_OK\s+(\{.*\})', out)
    if not m:
        raise RuntimeError('图床上传失败:\n' + out[-800:])
    return json.loads(m.group(1))


# ============================================================ 65535 出图（基准图）
def _image_api(method, path, payload=None, timeout: int = 180):
    api = CONFIG.get('image_api', {})
    base = api.get('base')
    key = os.environ.get(api.get('key_env', 'S65535_API_KEY'), '')
    if not key:
        raise RuntimeError('环境变量 %s 未设置' % api.get('key_env'))
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8') if payload is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    req.add_header('Authorization', 'Bearer ' + key)
    if data:
        req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def _to_data_uri(path, max_side: int = 1536, quality: int = 86) -> str:
    cv2, _ = _cv2()
    im = read_image(path)
    h, w = im.shape[:2]
    s = max_side / float(max(h, w))
    if s < 1.0:
        im = cv2.resize(im, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode('.jpg', im, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError('JPEG 编码失败: %s' % path)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.tobytes()).decode('ascii')


def gen_base_image(prompt, out_path, refs=None, size: str = '16:9', resolution: str = '2k',
                   poll_interval: int = 6, max_rounds: int = 90) -> Path:
    """用 65535 生成基准图（refs 非空即图生图，可传多张参考图）。"""
    api = CONFIG.get('image_api', {})
    body = {'kind': 'image', 'model': api.get('model', 'gpt-image-2.5-flare'),
            'input': {'prompt': prompt, 'size': size, 'resolution': resolution, 'n': 1}}
    if refs:
        body['input']['image'] = [_to_data_uri(r) for r in refs]
    rsp = _image_api('POST', '/v1/tasks', body)
    tid = rsp.get('id') or rsp.get('task_id')
    if not tid:
        raise RuntimeError('提交异常，未返回 task_id: %s' % json.dumps(rsp, ensure_ascii=False)[:400])
    for _ in range(max_rounds):
        time.sleep(poll_interval)
        st = _image_api('GET', '/v1/tasks/' + str(tid), timeout=60)
        s = st.get('status')
        if s in ('done', 'failed'):
            if s != 'done':
                raise RuntimeError('生成失败: %s' % json.dumps(st.get('error') or st, ensure_ascii=False)[:400])
            urls = st.get('result_urls') or []
            if not urls:
                raise RuntimeError('无 result_urls')
            with urllib.request.urlopen(urls[0], timeout=180) as r:
                blob = r.read()
            out_path = Path(out_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, 'wb') as f:
                f.write(blob)
            return out_path
    raise RuntimeError('轮询超时（task_id=%s）' % tid)


# ============================================================ MJ sref 出图
_MJ_POLL_INTERVAL = 8
_MJ_POLL_TIMEOUT = 420


def _build_opener():
    for p in ('http://127.0.0.1:7890',):
        m = re.match(r'https?://([^:/]+):(\d+)', p)
        if not m:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            try:
                s.connect((m.group(1), int(m.group(2))))
                return urllib.request.build_opener(
                    urllib.request.ProxyHandler({'https': p, 'http': p}))
            except OSError:
                pass
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _download(opener, url, path):
    with opener.open(url, timeout=120) as r, open(path, 'wb') as f:
        f.write(r.read())


def mj_generate(prompt, sref_url, out_dir, tag, negative='', sw=None,
                version=None, size=None, quality=None, speed=None):
    """提交一次 MJ sref 出图并下载（网格 + 4 张单图）。

    返回 (task_id, [文件路径...])。POST 不自动重试（防重复扣费）。
    """
    api = CONFIG.get('mj_api', {})
    base = api.get('base', 'https://api.apib.ai/v1').rstrip('/')
    key = os.environ.get(api.get('key_env', 'APIMART_API_KEY'), '')
    if not key:
        raise RuntimeError('环境变量 %s 未设置' % api.get('key_env'))
    opener = _build_opener()

    body = {'prompt': prompt,
            'size': size or api.get('size', '16:9'),
            'speed': speed or api.get('speed', 'fast'),
            'version': str(version or api.get('version', '7'))}
    if negative:
        body['negative_prompt'] = negative
    if sref_url:
        body['sref'] = sref_url
        body['sw'] = int(sw if sw is not None else api.get('sw', 500))
    q = quality if quality is not None else api.get('quality')
    if q:
        body['quality'] = str(q)

    req = urllib.request.Request(
        base + '/midjourney/generations',
        data=json.dumps(body).encode('utf-8'),
        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'},
        method='POST')
    with opener.open(req, timeout=60) as r:
        rsp = json.loads(r.read().decode('utf-8'))
    data = rsp.get('data') or []
    if isinstance(data, dict):
        data = [data]
    if not data or not data[0].get('task_id'):
        raise RuntimeError('MJ 提交异常: %s' % json.dumps(rsp, ensure_ascii=False)[:400])
    task_id = data[0]['task_id']

    start = time.time()
    while True:
        req = urllib.request.Request('%s/midjourney/%s' % (base, task_id),
                                     headers={'Authorization': 'Bearer ' + key}, method='GET')
        with opener.open(req, timeout=60) as r:
            d = json.loads(r.read().decode('utf-8'))
        d = d.get('data') or d
        if isinstance(d, list):
            d = d[0]
        status = (d.get('status') or '').lower()
        if status in ('success', 'completed', 'succeeded'):
            break
        if status in ('failed', 'failure', 'error', 'canceled', 'cancelled'):
            raise RuntimeError('MJ 任务失败: %s' % json.dumps(d, ensure_ascii=False)[:400])
        if time.time() - start > _MJ_POLL_TIMEOUT:
            raise RuntimeError('MJ 轮询超时，task_id=%s（可 --query 重查）' % task_id)
        time.sleep(_MJ_POLL_INTERVAL)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    grid = d.get('grid_image_url') or ''
    if grid:
        p = out_dir / ('%s_%s_grid.jpg' % (tag, task_id))
        _download(opener, grid, p)
        paths.append(p)
    for i, u in enumerate(d.get('image_urls') or [], 1):
        p = out_dir / ('%s_%s_%d.jpg' % (tag, task_id, i))
        _download(opener, u, p)
        paths.append(p)
    return task_id, paths

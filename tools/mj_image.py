#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mj_image.py — APIMart Midjourney 生图固化脚本（imagine → 轮询 → 下载）

仅依赖 Python 标准库。POST 一律不自动重试（防重复扣费）。

典型用法：
  # 1) 文生图（最简）
  python mj_image.py --prompt "a silver-haired fox girl in a moonlit forest" --out out_dir

  # 2) 风格参考(sref) + 角色参考(cref)
  python mj_image.py --prompt "..." \
      --sref https://.../style.jpg --sw 400 \
      --cref https://.../char.jpg --cw 60 \
      --version 7 --size 16:9 --speed fast --out out_dir

  # 3) 垫图（image prompt）
  python mj_image.py --prompt "turn this into a dreamy fantasy scene" \
      --image-urls https://.../input.jpg --iw 1.5 --out out_dir

  # 4) 只查询已有任务并下载（不扣费）
  python mj_image.py --query task_01XXXX --out out_dir

  # 5) 只看请求体，不真正提交
  python mj_image.py --prompt test --dry-run
"""

import argparse
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = os.environ.get("APIMART_BASE_URL", "https://api.apib.ai/v1").rstrip("/")
LOCAL_PROXY_CANDIDATES = ["http://127.0.0.1:7890"]
POLL_INTERVAL = 8
POLL_TIMEOUT = 420


def eprint(*args):
    print(*args, file=sys.stderr, flush=True)


def _proxy_alive(proxy_url):
    m = re.match(r"https?://([^:/]+):(\d+)", proxy_url)
    if not m:
        return False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        try:
            s.connect((m.group(1), int(m.group(2))))
            return True
        except OSError:
            return False


def _build_opener():
    if os.environ.get("APIMART_NO_PROXY") == "1":
        return urllib.request.build_opener(urllib.request.ProxyHandler({}))
    if os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY"):
        return urllib.request.build_opener()
    for p in LOCAL_PROXY_CANDIDATES:
        if _proxy_alive(p):
            eprint(f"[proxy] 检测到本地代理 {p}，走代理")
            return urllib.request.build_opener(urllib.request.ProxyHandler({"https": p, "http": p}))
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


OPENER = _build_opener()


def api_key():
    key = os.environ.get("APIMART_API_KEY", "").strip()
    if not key:
        eprint("错误：环境变量 APIMART_API_KEY 未设置")
        sys.exit(1)
    return key


def post_json(url, body, key):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with OPENER.open(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        eprint(f"HTTP {e.code}: {detail}")
        sys.exit(1)
    except urllib.error.URLError as e:
        eprint(f"网络错误（不自动重试，防重复扣费）: {e.reason}")
        sys.exit(1)


def get_json(url, key):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"}, method="GET")
    try:
        with OPENER.open(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        eprint(f"HTTP {e.code}: {detail}")
        sys.exit(1)


def download(url, out_dir, name):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = ".jpg"
    m = re.search(r"\.(png|jpg|jpeg|webp)(?:\?|$)", url)
    if m:
        ext = "." + m.group(1).replace("jpeg", "jpg")
    path = out_dir / f"{name}{ext}"
    with OPENER.open(url, timeout=120) as resp, open(path, "wb") as f:
        f.write(resp.read())
    return path


def poll_and_download(task_id, out_dir, key, tag):
    url = f"{BASE_URL}/midjourney/{task_id}"
    start = time.time()
    while True:
        rsp = get_json(url, key)
        data = rsp.get("data") or rsp
        if isinstance(data, list):
            data = data[0]
        status = (data.get("status") or "").lower()
        progress = data.get("progress", "")
        eprint(f"[{int(time.time()-start)}s] status={status} progress={progress}")
        if status in ("success", "completed", "succeeded"):
            grid = data.get("grid_image_url") or ""
            urls = data.get("image_urls") or []
            paths = []
            if grid:
                p = download(grid, out_dir, f"{tag}_{task_id}_grid")
                paths.append(p)
                eprint(f"九宫格: {p}")
            for i, u in enumerate(urls, 1):
                p = download(u, out_dir, f"{tag}_{task_id}_{i}")
                paths.append(p)
                eprint(f"图 {i}: {p}")
            return paths
        if status in ("failed", "failure", "error", "canceled", "cancelled"):
            eprint(f"任务失败: {json.dumps(data, ensure_ascii=False)[:800]}")
            sys.exit(1)
        if time.time() - start > POLL_TIMEOUT:
            eprint(f"轮询超时（{POLL_TIMEOUT}s），task_id={task_id}，可稍后用 --query 重查")
            sys.exit(2)
        time.sleep(POLL_INTERVAL)


def main():
    ap = argparse.ArgumentParser(description="APIMart Midjourney 生图")
    ap.add_argument("--prompt", default="", help="提示词（可含 MJ 原生 flags）")
    ap.add_argument("--negative", default="", help="负向提示词（--no）")
    ap.add_argument("--image-urls", nargs="*", default=[], help="垫图 URL 列表")
    ap.add_argument("--iw", type=float, help="垫图权重 0-3")
    ap.add_argument("--sref", default="", help="风格参考图 URL")
    ap.add_argument("--sw", type=int, help="风格权重 0-1000")
    ap.add_argument("--cref", default="", help="角色参考图 URL（仅 v6/6.1/niji6）")
    ap.add_argument("--cw", type=int, help="角色权重 0-100（0=仅脸部）")
    ap.add_argument("--oref", default="", help="万能参考图 URL（v7+，替代 cref）")
    ap.add_argument("--ow", type=int, help="万能参考权重 0-1000（v7+）")
    ap.add_argument("--version", default="7", help="版本: 8.2/8.1/7/6.1/5.2/5.1")
    ap.add_argument("--niji", action="store_true", help="Niji 模式（配合 --version 7/6）")
    ap.add_argument("--size", default="16:9", help="画幅如 16:9 / 9:16 / 1:1")
    ap.add_argument("--stylize", type=int, help="--s 0-1000")
    ap.add_argument("--chaos", type=int, help="--c 0-100")
    ap.add_argument("--quality", help="--q 0.25/0.5/1/2")
    ap.add_argument("--raw", action="store_true", help="raw 模式")
    ap.add_argument("--seed", type=int, help="随机种子")
    ap.add_argument("--speed", default="fast", choices=["relax", "fast", "turbo"])
    ap.add_argument("--out", default=".", help="下载目录")
    ap.add_argument("--tag", default="mj", help="输出文件名前缀")
    ap.add_argument("--query", default="", help="只查询已有任务并下载（不扣费）")
    ap.add_argument("--dry-run", action="store_true", help="只打印请求体，不提交")
    args = ap.parse_args()

    key = api_key()

    if args.query:
        poll_and_download(args.query, args.out, key, args.tag)
        return

    if not args.prompt and not args.image_urls:
        eprint("错误：--prompt 与 --image-urls 至少给一个")
        sys.exit(1)

    body = {"prompt": args.prompt, "size": args.size, "speed": args.speed}
    if args.niji:
        body["niji"] = True
    body["version"] = args.version
    if args.image_urls:
        body["image_urls"] = args.image_urls
    if args.iw is not None:
        body["iw"] = args.iw
    if args.negative:
        body["negative_prompt"] = args.negative
    if args.sref:
        body["sref"] = args.sref
    if args.sw is not None:
        body["sw"] = args.sw
    if args.cref:
        body["cref"] = args.cref
    if args.cw is not None:
        body["cw"] = args.cw
    if args.oref or args.ow is not None:
        extra = []
        if args.oref:
            extra.append(f"--oref {args.oref}")
        if args.ow is not None:
            extra.append(f"--ow {args.ow}")
        body["prompt"] = body["prompt"].rstrip() + " " + " ".join(extra)
    if args.stylize is not None:
        body["stylize"] = args.stylize
    if args.chaos is not None:
        body["chaos"] = args.chaos
    if args.quality:
        body["quality"] = args.quality
    if args.raw:
        body["raw"] = True
    if args.seed is not None:
        body["seed"] = args.seed

    eprint("请求体:")
    eprint(json.dumps(body, ensure_ascii=False, indent=2))
    if args.dry_run:
        eprint("(dry-run，未提交)")
        return

    rsp = post_json(f"{BASE_URL}/midjourney/generations", body, key)
    data = rsp.get("data") or []
    if isinstance(data, dict):
        data = [data]
    if not data or not data[0].get("task_id"):
        eprint(f"提交异常，未返回 task_id: {json.dumps(rsp, ensure_ascii=False)[:500]}")
        sys.exit(1)
    task_id = data[0]["task_id"]
    eprint(f"已提交 task_id={task_id}")

    paths = poll_and_download(task_id, args.out, key, args.tag)
    print(json.dumps({"task_id": task_id, "files": [str(p) for p in paths]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_t8balance.py — 宫装女友系列 · Step 5 出片固化脚本（RunningHub 6A 应用 API · t8balance）

把「参考图 openapi 上传 → 同步间隔 → payload 构建 → 并发≤3 提交 → 轮询 → 下载 → 断点续跑」
固化为一条命令。2026-09-19 由 E11 临时脚本升格固化，仅标准库 + runninghub 技能脚本。

典型用法
--------
  # 1) 任务定义 JSON（每段一条 job）：
  #    [
  #      {"tag": "E12A", "seconds": "10",
  #       "prompt_file": "d:\\...\\提示词\\E12A.md",
  #       "image": "d:\\...\\images\\E12A_李缨宁_闺房夜窗鱼灯.png"},
  #      ...
  #    ]
  # 2) 出片（断点续跑：同命令再执行即可）
  python tools/run_t8balance.py --jobs E12-jobs.json \
      --out-dir "<分集目录>\\video" --rec-dir "<分集目录>\\任务记录"

  # 只上传参考图拿 openapi 短路径（不出片）
  python tools/run_t8balance.py --jobs E12-jobs.json --out-dir ... --rec-dir ... --upload-only

  # 只看将构建的 payload 摘要（不传图不提交）
  python tools/run_t8balance.py --jobs E12-jobs.json --out-dir ... --rec-dir ... --dry-run

硬规矩（SKILL.md 口径，脚本已内置）
--------------------------------
  * 账户同时最多 3 个任务（421 自动等 30s 重试）
  * 上传后勿立即提交：openapi 图写入工作区有分钟级同步延迟（默认等 180s，--sync-wait 可调）
  * mp0.86 下 plus 只稳定跑 ≤10s；≥13s 用 --instance ultra
  * 提交用 curl.exe --max-time（超时不等于未送达，绝不立即重试）
  * node 6 = 参考图，node 35-42 = None（t8balance 无 64/69 文武戏节点）
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

RH_SCRIPTS = r"d:\work\minimax_h3\.trae\skills\runninghub\scripts"
sys.path.insert(0, RH_SCRIPTS)
from runninghub import require_api_key, upload_file  # 6A：返回 openapi/<hash>.png（勿用 runninghub_app！）

BASE_TMPL = "https://www.runninghub.cn/openapi/v2/run/ai-app/{app}"
QUERY = "https://www.runninghub.cn/openapi/v2/query"
DEFAULT_APP = "2095868555916038145"          # t8balance（以 assets\应用注册表.md 为准）
DEFAULT_LEDGER = r"d:\work\minimax_h3\韩老魔的宫装女友\任务记录\上传结果.json"
NODE_IDS_NONE = ["35", "36", "37", "38", "39", "40", "41", "42"]


def extract_prompt(md_path):
    txt = open(md_path, encoding="utf-8").read()
    m = re.search(r"```text\n(.*?)\n```", txt, re.S)
    if not m:
        raise SystemExit(f"[X] {md_path} 里没找到 ```text 围栏提示词")
    return m.group(1).strip()


def load_ledger(path):
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    return {}


def save_ledger(path, ledger):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)


def openapi_short(url_or_path):
    """upload_file 返回带签名的完整 URL；提取 openapi/<hash>.png。已是短路径则原样返回。"""
    s = str(url_or_path)
    if s.startswith("openapi/"):
        return s
    m = re.search(r"(openapi/[0-9a-f]+\.\w+)", s)
    if not m:
        raise SystemExit(f"[X] 无法从上传结果提取 openapi 短路径：{s[:120]}")
    return m.group(1)


def upload_image(local, ledger, ledger_path, key):
    """内容寻址上传；同路径复用 ledger 记录（隔天链接失效时强制重传）。"""
    ap = os.path.abspath(local)
    name = os.path.basename(ap)
    ent = ledger.get(name)
    if ent and ent.get("openapi", "").startswith("openapi/") and ent.get("path") == ap \
            and ent.get("uploaded_on") == time.strftime("%Y-%m-%d"):
        print(f"  复用 ledger：{name} -> {ent['openapi']}")
        return ent["openapi"], time.time() - 86400  # 老图视作早已同步
    print(f"  上传 {name} ...")
    url = upload_file(key, ap)
    short = openapi_short(url)
    ledger[name] = {"path": ap, "openapi": short,
                    "uploaded_on": time.strftime("%Y-%m-%d"),
                    "episode": os.path.basename(os.path.dirname(os.path.dirname(ap)))}
    save_ledger(ledger_path, ledger)
    print(f"  上传完成 -> {short}")
    return short, time.time()


def build_payload(tag, prompt, image_short, seconds, aspect, mp, instance, rec_dir):
    nodes = [
        {"nodeId": "27", "fieldName": "value", "fieldValue": str(seconds)},
        {"nodeId": "28", "fieldName": "prompt", "fieldValue": prompt},
        {"nodeId": "29", "fieldName": "aspect_ratio", "fieldValue": aspect},
        {"nodeId": "29", "fieldName": "megapixels", "fieldValue": str(mp)},
        {"nodeId": "6", "fieldName": "image", "fieldValue": image_short},
    ] + [{"nodeId": n, "fieldName": "image", "fieldValue": "None"} for n in NODE_IDS_NONE]
    payload = {"nodeInfoList": nodes, "instanceType": instance, "usePersonalQueue": "false"}
    pp = os.path.join(rec_dir, f"t8balance-{tag}-payload.json")
    with open(pp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload, pp


def submit(payload_path, app, key):
    cmd = ["curl.exe", "-s", "-S", "-X", "POST", BASE_TMPL.format(app=app),
           "-H", f"Authorization: Bearer {key}",
           "-H", "Content-Type: application/json",
           "--data-binary", f"@{payload_path}", "--max-time", "60"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    try:
        return json.loads(r.stdout)
    except (ValueError, TypeError):
        return {"parse_error": (r.stdout or r.stderr or "")[:400]}


def query(tid, key):
    cmd = ["curl.exe", "-s", "-S", "-X", "POST", QUERY,
           "-H", f"Authorization: Bearer {key}",
           "-H", "Content-Type: application/json",
           "-d", json.dumps({"taskId": tid}), "--max-time", "30"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    try:
        return json.loads(r.stdout)
    except (ValueError, TypeError):
        return {"parse_error": (r.stdout or r.stderr or "")[:300]}


def download(url, dst):
    subprocess.run(["curl.exe", "-s", "-S", "-L", "-o", dst, url, "--max-time", "300"],
                   capture_output=True)


def main():
    ap = argparse.ArgumentParser(description="Step 5 出片（t8balance 6A 应用 API，含上传/并发/断点续跑）")
    ap.add_argument("--jobs", required=True, help="任务定义 JSON（tag/prompt_file/image/seconds）")
    ap.add_argument("--out-dir", required=True, help="成片目录（分集 video\\）")
    ap.add_argument("--rec-dir", required=True, help="回执目录（分集 任务记录\\）")
    ap.add_argument("--ledger", default=DEFAULT_LEDGER, help="上传映射 ledger（跨集共享）")
    ap.add_argument("--app", default=DEFAULT_APP, help="webappId（默认 t8balance）")
    ap.add_argument("--aspect", default="9:16 (Portrait Widescreen)")
    ap.add_argument("--mp", default="0.86", help="megapixels（默认 0.86）")
    ap.add_argument("--instance", default="plus", choices=["default", "plus", "ultra"],
                    help="实例档位；mp0.86 下 plus 只稳定 ≤10s，≥13s 用 ultra")
    ap.add_argument("--sync-wait", type=float, default=180,
                    help="参考图上传到提交的同步间隔秒（默认 180）")
    ap.add_argument("--max-concurrent", type=int, default=3)
    ap.add_argument("--poll", type=float, default=20)
    ap.add_argument("--timeout", type=int, default=7200)
    ap.add_argument("--upload-only", action="store_true", help="只上传参考图并登记 ledger")
    ap.add_argument("--dry-run", action="store_true", help="只打印 payload 摘要，不传图不提交")
    a = ap.parse_args()

    os.makedirs(a.out_dir, exist_ok=True)
    os.makedirs(a.rec_dir, exist_ok=True)
    jobs = json.load(open(a.jobs, encoding="utf-8"))
    key = require_api_key(None)
    ledger = load_ledger(a.ledger)

    state_path = os.path.join(a.rec_dir, "t8balance-run-state.json")
    state = json.load(open(state_path, encoding="utf-8")) if os.path.exists(state_path) else {}

    def save():
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    # ---- 1) 提示词 + 参考图（上传/复用；dry-run 只展示不传图） ----
    ready = {}
    for j in jobs:
        tag = j["tag"]
        prompt = extract_prompt(j["prompt_file"])
        img = j["image"]
        if str(img).startswith("openapi/"):
            short, up_at = str(img), time.time() - 86400
        elif a.dry_run:
            short, up_at = f"<本地待传> {os.path.basename(img)}", 0
        else:
            short, up_at = upload_image(img, ledger, a.ledger, key)
        ready[tag] = {"prompt": prompt, "image": short, "ready_at": up_at + a.sync_wait}
        if a.dry_run:
            print(f"[dry-run] {tag}: seconds={j.get('seconds', '10')} "
                  f"image={short}\n  prompt 前 120 字：{prompt[:120]}\n")

    if a.upload_only or a.dry_run:
        print("OPENAPI_MAPPING")
        for tag, r in ready.items():
            print(f"  {tag} -> {r['image']}")
        return 0

    # ---- 2) 提交（并发 ≤ max_concurrent，尊重同步间隔；421 退避） ----
    def alive_count():
        return sum(1 for v in state.values()
                   if v.get("task_id") and not v.get("status"))

    for j in jobs:
        tag = j["tag"]
        if state.get(tag, {}).get("task_id"):
            continue
        wait = ready[tag]["ready_at"] - time.time()
        if wait > 0:
            print(f"  {tag}：等待同步间隔 {wait:.0f}s ...")
            time.sleep(max(wait, 0))
        while alive_count() >= a.max_concurrent:
            time.sleep(30)
        payload, pp = build_payload(tag, ready[tag]["prompt"], ready[tag]["image"],
                                    j.get("seconds", "10"), a.aspect, a.mp,
                                    a.instance, a.rec_dir)
        res = submit(pp, a.app, key)
        # 421 = 并发超限，等 30s 重提同一 payload（零风险）
        tries = 0
        while (res.get("errorCode") == "421" or "421" in str(res.get("msg", ""))) and tries < 10:
            tries += 1
            print(f"  {tag}：421 并发超限，30s 后重提（第 {tries} 次）")
            time.sleep(30)
            res = submit(pp, a.app, key)
        tid = res.get("taskId") or (res.get("data") or {}).get("taskId") or res.get("data")
        state[tag] = {"task_id": tid, "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
        save()
        with open(os.path.join(a.rec_dir, f"t8balance-{tag}-submit.json"), "w",
                  encoding="utf-8") as f:
            json.dump({"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "resp": res}, f,
                      ensure_ascii=False, indent=2)
        print(f"SUBMITTED {tag} {tid}")

    # ---- 3) 轮询 + 下载 ----
    t0 = time.time()
    while time.time() - t0 < a.timeout:
        active = {t: v for t, v in state.items()
                  if v.get("task_id") and v.get("status") not in ("SUCCESS", "FAILED")}
        if not active:
            break
        for t, v in list(active.items()):
            q = query(v["task_id"], key)
            s = q.get("status")
            if s in ("SUCCESS", "FAILED"):
                v["status"] = s
                v["usage"] = q.get("usage")
                save()
                with open(os.path.join(a.rec_dir, f"t8balance-{t}-result.json"), "w",
                          encoding="utf-8") as f:
                    json.dump(q, f, ensure_ascii=False, indent=2)
                u = q.get("usage") or {}
                print(f"STATUS {t} {s} coins={u.get('consumeCoins')} "
                      f"sec={u.get('taskCostTime')} err={q.get('errorCode')}")
                if s == "SUCCESS":
                    urls = [o.get("url") for o in (q.get("results") or []) if o.get("url")]
                    if urls:
                        dst = os.path.join(
                            a.out_dir, f"宫装女友{t}_" + time.strftime("%Y%m%d-%H%M%S") + ".mp4")
                        download(urls[0], dst)
                        v["local"] = dst
                        save()
                        print(f"DOWNLOADED {dst}")
                elif str(q.get("errorCode")) == "805":
                    print(f"  ↑ {t}：805 OOM——≥13s 须 --instance ultra 重跑该 job")
        if active:
            time.sleep(a.poll)

    # ---- 4) 汇总 ----
    print("\n===== 汇总 =====")
    rc = 0
    for j in jobs:
        v = state.get(j["tag"], {})
        print(f"{j['tag']}: {v.get('status') or '未提交'}  task={v.get('task_id')}  "
              f"coins={(v.get('usage') or {}).get('consumeCoins')}  local={v.get('local')}")
        if v.get("status") != "SUCCESS":
            rc = 2
    return rc


if __name__ == "__main__":
    sys.exit(main())

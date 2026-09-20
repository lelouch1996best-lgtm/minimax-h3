#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
t8balance 多参考直采一键脚本（dance 技能·路径 B「提示词反推 + 三视图直采」固化，2026-09-20）

与路径 A（run_dance_transfer.py 动作迁移）互补：本脚本不生成真人参考图，
直接把 N 张人物三视图 + 1 张场景图挂到 t8balance（Ref2VA）多参考槽，
动作与画面完全由反推的 H3 提示词驱动。

一次完成：上传全部参考图（node 6/35/36/37…）-> 等工作区同步 -> 构建 payload
-> 提交 RunningHub 应用 2095868555916038145 -> 421 自动退避 -> 静默轮询
-> 自动下载成片 -> 写任务记录。断点续跑：state 文件记录 task_id，重跑只轮询不重提。

参考槽与 Picture 编号（顺序即编号，已被勾栏听曲/三人舞实测验证）：
  第 1 张 -> node 6  = <Picture 1>（主角/C 位）
  第 2 张 -> node 35 = <Picture 2>
  第 3 张 -> node 36 = <Picture 3>
  第 4 张 -> node 37 = <Picture 4>（通常放场景图）
  第 5~9 张 -> node 38/39/40/41/42 = <Picture 5…9>
未使用的槽位自动填 "None"。提示词 markdown 中必须用 ```text 围栏包裹 H3 提示词。

用法：
  # 任务定义 JSON（images 顺序 = Picture 编号）：
  # {
  #   "tag": "D04",
  #   "prompt_file": "d:\\...\\提示词\\D04.md",
  #   "images": [
  #     "d:\\...\\character\\幕沛灵\\人物三视图（红宫装）.png",
  #     "d:\\...\\character\\紫灵\\人物三视图（宫装）.png",
  #     "d:\\...\\character\\文思月\\人物三视图（宫装）.png",
  #     "d:\\...\\scene\\学校\\场景-学校走廊.png"
  #   ],
  #   "seconds": "10"
  # }
  python run_t8balance_ref2va.py --job D04-job.json \
      -o "D:\\...\\D04-...\\video\\D04_三视图直采.mp4"

  # 续接已提交任务（超时/中断后只轮询，防重复扣费）
  python run_t8balance_ref2va.py --task-id <taskId> -o 成片.mp4

硬规矩（与 tools/run_t8balance.py 一致）：
  * 上传后等满 180s 再提交（openapi 图写入工作区有分钟级同步延迟）
  * mp0.86 + plus 只稳定 ≤10s；≥13s 用 --instance ultra
  * ledger 以「绝对路径」为键，避免不同角色三视图同名（人物三视图（宫装）.png）撞键
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote
import urllib.request

# 复用 runninghub 技能的 API 封装（本脚本位于 .trae/skills/dance/scripts/）
RH_SCRIPTS = Path(__file__).resolve().parents[2] / "runninghub" / "scripts"
sys.path.insert(0, str(RH_SCRIPTS))
from runninghub import require_api_key  # noqa: E402

APP = "2095868555916038145"  # t8balance（以 assets\应用注册表.md 为准）
BASE_TMPL = "https://www.runninghub.cn/openapi/v2/run/ai-app/{app}"
QUERY = "https://www.runninghub.cn/openapi/v2/query"

# 参考槽位：第 1 张走主 LoadImage（node 6），其后依次 35..42
SLOT_NODE_1 = "6"
SLOT_NODES = ["35", "36", "37", "38", "39", "40", "41", "42"]
ALL_SLOTS = [SLOT_NODE_1] + SLOT_NODES  # 最多 9 张参考图

DEFAULT_LEDGER = r"d:\work\minimax_h3\韩老魔的歌舞团\任务记录\上传结果.json"


def curl_json(args: list[str]) -> dict:
    r = subprocess.run(["curl.exe", "-s", "-S"] + args,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return json.loads(r.stdout)
    except (ValueError, TypeError):
        return {"parse_error": (r.stdout or r.stderr or "")[:400]}


def extract_prompt(md_path: str) -> str:
    txt = Path(md_path).read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    m = re.search(r"```text\n(.*?)\n```", txt, re.S)
    if not m:
        raise SystemExit(f"[X] {md_path} 没找到 ```text 围栏提示词")
    return m.group(1).strip()


def load_json(p: str | Path, default):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


def save_json(p: str | Path, obj) -> None:
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def openapi_short(url_or_path: str) -> str:
    s = str(url_or_path)
    if s.startswith("openapi/"):
        return s
    m = re.search(r"(openapi/[0-9a-f]+\.\w+)", s)
    if not m:
        raise SystemExit(f"[X] 无法提取 openapi 短路径：{s[:120]}")
    return m.group(1)


def upload_one(local: str, ledger: dict, ledger_path: str, key: str, sync_wait: float):
    """内容寻址上传；ledger 以绝对路径为键（同名三视图不再撞键）。当天同路径直接复用。"""
    ap = os.path.abspath(local)
    today = time.strftime("%Y-%m-%d")
    ent = ledger.get(ap)
    if ent and str(ent.get("openapi", "")).startswith("openapi/") and ent.get("uploaded_on") == today:
        print(f"  复用 ledger：{os.path.basename(ap)} -> {ent['openapi']}", flush=True)
        return ent["openapi"], time.time() - 86400  # 老图视作早已同步
    print(f"  上传 {ap} ...", flush=True)
    # 复用 runninghub 技能的上传封装
    rh_scripts_dir = str(Path(__file__).resolve().parents[2] / "runninghub" / "scripts")
    if rh_scripts_dir not in sys.path:
        sys.path.insert(0, rh_scripts_dir)
    from runninghub import upload_file
    sh = openapi_short(upload_file(key, ap))
    ledger[ap] = {"path": ap, "openapi": sh, "uploaded_on": today, "episode": "dance-ref2va"}
    save_json(ledger_path, ledger)
    print(f"  -> {sh}", flush=True)
    return sh, time.time()


def build_payload(prompt: str, shorts: dict, seconds: str, aspect: str, mp: str, instance: str):
    nodes = [
        {"nodeId": "27", "fieldName": "value", "fieldValue": str(seconds)},
        {"nodeId": "28", "fieldName": "prompt", "fieldValue": prompt},
        {"nodeId": "29", "fieldName": "aspect_ratio", "fieldValue": aspect},
        {"nodeId": "29", "fieldName": "megapixels", "fieldValue": str(mp)},
    ]
    for nid in ALL_SLOTS:
        nodes.append({"nodeId": nid, "fieldName": "image",
                      "fieldValue": shorts.get(nid, "None")})
    return {"nodeInfoList": nodes, "instanceType": instance, "usePersonalQueue": "false"}


def submit(payload_path: str, key: str) -> dict:
    return curl_json(["-X", "POST", BASE_TMPL.format(app=APP),
                      "-H", f"Authorization: Bearer {key}",
                      "-H", "Content-Type: application/json",
                      "--data-binary", f"@{payload_path}", "--max-time", "60"])


def query(tid: str, key: str) -> dict:
    return curl_json(["-X", "POST", QUERY,
                      "-H", f"Authorization: Bearer {key}",
                      "-H", "Content-Type: application/json",
                      "-d", json.dumps({"taskId": tid}), "--max-time", "30"])


def download(url: str, dst: str) -> None:
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    quoted = quote(url, safe=":/&?=%._-~")
    urllib.request.urlretrieve(quoted, dst)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="t8balance 多参考直采（dance 路径 B：三视图/场景图 + 反推提示词直接出片）",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--job", help="任务定义 JSON：tag/prompt_file/images[]/seconds")
    ap.add_argument("--output", "-o", help="成片输出路径（.mp4）")
    ap.add_argument("--task-id", help="续接已提交任务：只轮询+下载，不重新提交（防重复扣费）")
    ap.add_argument("--aspect", default="9:16 (Portrait Widescreen)", help="node29 aspect_ratio")
    ap.add_argument("--mp", default="0.86", help="megapixels，默认 0.86")
    ap.add_argument("--instance", default="plus", choices=["default", "plus", "ultra"],
                    help="实例档位；mp0.86 下 plus 稳定 ≤10s，≥13s 用 ultra")
    ap.add_argument("--sync-wait", type=float, default=180, help="上传到提交的同步间隔秒（默认 180）")
    ap.add_argument("--ledger", default=DEFAULT_LEDGER, help="上传映射 ledger（项目级共享）")
    ap.add_argument("--record-dir", help="任务记录目录（默认输出文件上上级目录的 任务记录\\）")
    ap.add_argument("--state-name", default=None, help="state/payload/result 文件名前缀（默认 job 的 tag）")
    ap.add_argument("--poll-interval", type=float, default=20, help="轮询间隔秒（默认 20）")
    ap.add_argument("--max-wait", type=int, default=7200, help="最长等待秒（默认 7200）")
    ap.add_argument("--dry-run", action="store_true", help="只打印 payload 摘要，不传图不提交")
    args = ap.parse_args()

    if not args.task_id and not (args.job and args.output):
        print("ERROR: 需要 --job 与 -o；或用 --task-id 续接已有任务", flush=True)
        return 1
    if args.task_id and not args.output:
        print("ERROR: 续接模式仍需要 -o 指定成片输出路径", flush=True)
        return 1

    # ---- 解析任务定义（dry-run 完全离线：不读 key、不建目录、不传图）----
    if not args.task_id:
        job = load_json(args.job, None)
        if not isinstance(job, dict):
            print("ERROR: --job JSON 必须是单个任务对象（不是数组）", flush=True)
            return 1
        tag = job.get("tag") or args.state_name or "ref2va"
        images = job.get("images") or []
        if not 1 <= len(images) <= len(ALL_SLOTS):
            print(f"ERROR: images 数量须在 1~{len(ALL_SLOTS)} 之间（当前 {len(images)}）", flush=True)
            return 1
        for img in images:
            if not os.path.exists(img):
                print(f"ERROR: 参考图不存在：{img}", flush=True)
                return 1
        seconds = str(job.get("seconds", "10"))
        prompt = extract_prompt(job["prompt_file"])

        if args.dry_run:
            # 只拼 payload 摘要：占位 openapi 路径，不读 key、不传图、不写 ledger/state、不提交
            placeholders = {ALL_SLOTS[i]: f"openapi/dryrun-P{i + 1}.png"
                            for i in range(len(images))}
            payload = build_payload(prompt, placeholders, seconds,
                                    args.aspect, args.mp, args.instance)
            print("===== dry-run payload 摘要（未传图未提交）=====", flush=True)
            print(f"  job={args.job}  tag={tag}  images={len(images)}  seconds={seconds}",
                  flush=True)
            slot_names = {n: (f"Picture {i + 1}") for i, n in enumerate(ALL_SLOTS)}
            for n in payload["nodeInfoList"]:
                v = n["fieldValue"]
                v = v if len(str(v)) <= 120 else str(v)[:120] + "..."
                extra = f"  <- {slot_names[n['nodeId']]}" if n["nodeId"] in slot_names else ""
                print(f"  node {n['nodeId']:>2} {n['fieldName']:<12} = {v}{extra}", flush=True)
            print(f"instance={args.instance}", flush=True)
            return 0

    # 以下为真实提交/续接：需要 API key 与输出目录
    key = require_api_key(None)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    record_dir = Path(args.record_dir) if args.record_dir else out_path.parent.parent / "任务记录"
    record_dir.mkdir(parents=True, exist_ok=True)

    # ---- 续接模式 ----
    if args.task_id:
        tag = args.state_name or "resume"
        state = {"task_id": str(args.task_id)}
        print(f"RESUME task={args.task_id}", flush=True)
    else:
        state_path = record_dir / f"t8balance-{tag}-state.json"
        state = load_json(state_path, {})
        if state.get("task_id"):
            print(f"续跑：{tag} 已有 task_id={state['task_id']}，只轮询", flush=True)
        else:
            ledger = load_json(args.ledger, {})
            print(f"[1/3] 上传 {len(images)} 张参考图 ...", flush=True)
            shorts: dict[str, str] = {}
            ready_at = 0.0
            for idx, img in enumerate(images):
                nid = ALL_SLOTS[idx]
                if str(img).startswith("openapi/"):
                    shorts[nid] = str(img)
                    up_at = time.time() - 86400
                else:
                    shorts[nid], up_at = upload_one(img, ledger, args.ledger, key, args.sync_wait)
                ready_at = max(ready_at, up_at + args.sync_wait)

            payload = build_payload(prompt, shorts, seconds, args.aspect, args.mp, args.instance)
            payload_path = record_dir / f"t8balance-{tag}-payload.json"
            save_json(payload_path, payload)
            print(f"[2/3] payload 已保存：{payload_path}", flush=True)

            wait = ready_at - time.time()
            if wait > 0:
                print(f"  等待工作区同步 {wait:.0f}s ...", flush=True)
                time.sleep(wait)

            res = submit(str(payload_path), key)
            tries = 0
            while (res.get("errorCode") == "421" or "421" in str(res.get("msg", ""))) and tries < 10:
                tries += 1
                print(f"  421 并发超限，30s 后重提（{tries}）", flush=True)
                time.sleep(30)
                res = submit(str(payload_path), key)
            save_json(record_dir / f"t8balance-{tag}-submit.json",
                      {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "resp": res})
            tid = res.get("taskId") or (res.get("data") or {}).get("taskId") or res.get("data")
            if not tid or not str(tid).isdigit():
                print("[X] 提交失败，响应：" + json.dumps(res, ensure_ascii=False)[:600], flush=True)
                return 1
            state = {"task_id": str(tid), "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                     "job_images": images, "seconds": seconds}
            save_json(state_path, state)
            print(f"SUBMITTED {tag} {tid}", flush=True)

    # ---- 轮询（低 token：状态变化才输出）----
    print("[3/3] 轮询 ...", flush=True)
    last_status = None
    t0 = time.time()
    final = None
    while time.time() - t0 < args.max_wait:
        q = query(state["task_id"], key)
        s = q.get("status")
        if s != last_status:
            print(f"STATUS {s} code={q.get('errorCode') or ''}", flush=True)
            last_status = s
        if s in ("SUCCESS", "FAILED"):
            final = q
            break
        time.sleep(args.poll_interval)

    if final is None:
        print(f"[X] 轮询超时 task={state['task_id']} —— 续接命令: "
              f"--task-id {state['task_id']} -o \"{out_path}\"（勿重复提交，会重复扣费）", flush=True)
        return 2

    save_json(record_dir / f"t8balance-{tag}-result.json", final)
    u = final.get("usage") or {}
    print(f"DONE {final.get('status')} coins={u.get('consumeCoins')} "
          f"sec={u.get('taskCostTime')} err={final.get('errorCode')}", flush=True)

    if final.get("status") != "SUCCESS":
        if str(final.get("errorCode")) == "805":
            print("  ↑ 805 OOM：用 --instance ultra 重跑（新建 job/state）", flush=True)
        return 2

    urls = [o.get("url") for o in (final.get("results") or []) if o.get("url")]
    if not urls:
        print("ERROR: SUCCESS 但无输出文件 " + json.dumps(final.get("results"), ensure_ascii=False), flush=True)
        return 1
    download(urls[0], str(out_path))
    state["local"] = str(out_path)
    state["status"] = "SUCCESS"
    save_json(record_dir / f"t8balance-{tag}-state.json", state)
    print(f"OUTPUT_FILE:{out_path}", flush=True)
    if u.get("consumeCoins") is not None:
        print(f"COST:{u['consumeCoins']} coins", flush=True)
    if u.get("taskCostTime") is not None:
        print(f"TASK_DURATION:{u['taskCostTime']}s", flush=True)
    print(f"RECORD:{record_dir}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

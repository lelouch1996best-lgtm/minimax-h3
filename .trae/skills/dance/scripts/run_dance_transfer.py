#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
舞蹈动作迁移一键脚本（dance 技能固化，2026-09-19）

一次完成：上传参考图/舞蹈视频 -> 提交 RunningHub 应用 1975951975441412098
-> 静默轮询（状态变化才输出一行，省 token）-> 自动下载成片（URL 含空格自动编码）
-> 自动写任务记录 JSON。

用法：
  提交并等待（长任务，建议后台运行）：
    python run_dance_transfer.py --image 参考图.png --video 舞蹈.mp4 -o 成片.mp4
  续接已提交任务（超时/中断后，只轮询不重提，防重复扣费）：
    python run_dance_transfer.py --task-id <taskId> -o 成片.mp4

默认值：plus 实例（该应用 15s 竖屏在默认实例实测失败）、720P、VITPOSE、
轮询 15 秒一次、最长等 60 分钟。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote
import urllib.request

# 复用 runninghub 技能的 API 封装（本脚本位于 .trae/skills/dance/scripts/）
RH_SCRIPTS = Path(__file__).resolve().parents[2] / "runninghub" / "scripts"
sys.path.insert(0, str(RH_SCRIPTS))
from runninghub import resolve_api_key, BASE_URL, POLL_ENDPOINT, poll_once, fix_mov_to_mp4  # noqa: E402
from runninghub_app import get_node_info, submit_task, apply_modifications  # noqa: E402

WEBAPP_ID = "1975951975441412098"


def download(url: str, out: Path) -> None:
    """下载结果文件；结果 URL 文件名可能含空格，需 URL 编码（D01 实测 curl 会 rc=3）。"""
    out.parent.mkdir(parents=True, exist_ok=True)
    quoted = quote(url, safe=":/&?=%._-~")
    urllib.request.urlretrieve(quoted, str(out))


def main() -> None:
    ap = argparse.ArgumentParser(
        description="舞蹈动作迁移一键脚本（dance 技能）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--image", help="参考图绝对路径（node 299：人物外观+场景，全身真人质感图）")
    ap.add_argument("--video", help="舞蹈源视频绝对路径（node 574：动作轨迹）")
    ap.add_argument("--output", "-o", required=True, help="成片输出路径（.mp4）")
    ap.add_argument("--instance", default="plus", choices=["default", "plus"],
                    help="GPU 实例，默认 plus（默认实例对该应用 15s 竖屏任务实测失败）")
    ap.add_argument("--resolution", default="2", choices=["1", "2", "3"],
                    help="分辨率：1=480P 2=720P(默认) 3=1080P(最多10秒)")
    ap.add_argument("--pose", default=None, choices=["1", "2", "3"],
                    help="姿势选择：1=VITPOSE(默认不传) 2=SDPOSE 3=WUWUPOSE")
    ap.add_argument("--task-id", help="续接已提交任务：只轮询+下载，不重新提交（防重复扣费）")
    ap.add_argument("--poll-interval", type=int, default=15, help="轮询间隔秒数（默认 15）")
    ap.add_argument("--max-wait", type=int, default=3600, help="最长等待秒数（默认 3600）")
    ap.add_argument("--record-dir", help="任务记录目录（默认输出文件上上级目录的 任务记录\\）")
    args = ap.parse_args()

    api_key = resolve_api_key(None)
    if not api_key:
        print("ERROR: RunningHub API key 未配置", flush=True)
        sys.exit(1)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # ---- 提交（或续接）----
    if args.task_id:
        task_id = args.task_id
        print(f"RESUME task={task_id}", flush=True)
    else:
        if not (args.image and args.video):
            print("ERROR: 需要 --image 与 --video；或用 --task-id 续接已有任务", flush=True)
            sys.exit(1)
        node_args = [f"566:select={args.resolution}"]
        if args.pose:
            node_args.append(f"563:select={args.pose}")
        file_args = [f"299:image={args.image}", f"574:video={args.video}"]
        node_list = get_node_info(api_key, WEBAPP_ID)
        node_list = apply_modifications(api_key, node_list, node_args, file_args)
        data = submit_task(api_key, WEBAPP_ID, node_list, args.instance)
        task_id = str(data["taskId"])
        print(f"SUBMITTED task={task_id}", flush=True)

    # ---- 静默轮询：只在状态变化时输出一行 ----
    poll_url = f"{BASE_URL}{POLL_ENDPOINT}"
    last_status = None
    final = None
    deadline = time.time() + args.max_wait
    while time.time() < deadline:
        time.sleep(args.poll_interval)
        resp = poll_once(api_key, poll_url, task_id)
        if resp is None:
            continue  # 瞬时网络错误：静默重试，不打印
        st = resp.get("status", "UNKNOWN")
        if st != last_status:
            print(f"STATUS {st}", flush=True)
            last_status = st
        if st == "SUCCESS":
            final = resp
            break
        if st == "FAILED":
            print("FAILED " + json.dumps(resp, ensure_ascii=False), flush=True)
            sys.exit(1)

    if final is None:
        print(f"TIMEOUT {args.max_wait}s task={task_id} "
              f"—— 续接命令: --task-id {task_id}，勿重复提交（会重复扣费）", flush=True)
        sys.exit(2)

    # ---- 下载结果（自动 URL 编码）----
    results = final.get("results") or []
    usage = final.get("usage") or {}
    downloads: list[str] = []
    for i, item in enumerate(results, 1):
        url = item.get("url") or item.get("outputUrl")
        if not url:
            continue
        ext = (item.get("outputType") or "").lower() or "mp4"
        if ext == "mov":
            ext = "mp4"  # fix_mov_to_mp4 会转封装
        if len(results) == 1:
            target = out_path if out_path.suffix.lower() == f".{ext}" else out_path.with_suffix(f".{ext}")
        else:
            target = out_path.with_name(f"{out_path.stem}_{i}.{ext}")
        download(url, target)
        fix_mov_to_mp4(str(target))
        downloads.append(str(target))

    if not downloads:
        print("ERROR: SUCCESS 但无输出文件 " + json.dumps(results, ensure_ascii=False), flush=True)
        sys.exit(1)

    # ---- 写任务记录 ----
    record = {
        "taskId": task_id,
        "webappId": WEBAPP_ID,
        "instanceType": args.instance,
        "status": "SUCCESS",
        "usage": usage,
        "input": {
            "node299_image": args.image,
            "node574_video": args.video,
            "node566_resolution": args.resolution,
            "node563_pose": args.pose or "VITPOSE(默认)",
        },
        "output": downloads,
        "finishedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    record_dir = Path(args.record_dir) if args.record_dir else out_path.parent.parent / "任务记录"
    record_dir.mkdir(parents=True, exist_ok=True)
    record_path = record_dir / f"runninghub-迁移-{task_id}.json"
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- 汇总输出（固定行格式，便于解析）----
    for d in downloads:
        print(f"OUTPUT_FILE:{d}", flush=True)
    coins = usage.get("consumeCoins")
    if coins is not None:
        print(f"COST:{coins} coins", flush=True)
    dur = usage.get("taskCostTime")
    if dur is not None:
        print(f"TASK_DURATION:{dur}s", flush=True)
    print(f"RECORD:{record_path}", flush=True)


if __name__ == "__main__":
    main()
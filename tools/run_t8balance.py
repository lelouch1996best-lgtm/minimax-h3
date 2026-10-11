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
  #       "images": ["d:\\...\\imgs\\角色A三视图.png",      # -> image1 (node 6)
  #                  "d:\\...\\imgs\\场景B.png",           # -> image2 (node 35)
  #                  "openapi/<hash>.png"]},              # -> image3 (node 36)
  #      ...
  #    ]
  #    兼容旧写法：只给 "image"（单个）等价于 images 长度 1；已是 openapi/ 短路径则跳过上传。
  #    9 个图槽顺序固定为 IMAGE_NODES；不足的槽自动填 "None"。
  # 2) 出片（断点续跑：同命令再执行即可）
  python tools/run_t8balance.py --jobs E12-jobs.json \
      --out-dir "<分集目录>\\video" --rec-dir "<分集目录>\\任务记录"

  # 2b) 【不推荐｜2026-10-10 用户反馈该模型出片有问题】30s 版应用，勿默认使用
  #     仅留档；除非明确要求并已核验出片质量，否则一律用上面的默认 t8balance。
  python tools/run_t8balance.py --jobs E12-jobs.json --app t8balance30 \
      --mode wen --dyn 1.5 --mp 0.4 --instance plus \
      --out-dir "<分集目录>\\video" --rec-dir "<分集目录>\\任务记录"

  # 只上传参考图拿 openapi 短路径（不出片）
  python tools/run_t8balance.py --jobs E12-jobs.json --out-dir ... --rec-dir ... --upload-only

  # 只看将构建的 payload 摘要（不传图不提交）
  python tools/run_t8balance.py --jobs E12-jobs.json --out-dir ... --rec-dir ... --dry-run

硬规矩（SKILL.md 口径，脚本已内置）
--------------------------------
  * 账户同时最多 3 个任务（421 自动等 30s 重试）
  * 上传后勿立即提交：openapi 图写入工作区有分钟级同步延迟（默认等 180s，--sync-wait 可调）
  * mp0.72 下 plus 可跑 14—15s（E14 实测）；mp0.86 下 plus 只稳定跑 ≤10s，≥13s 用 --instance ultra
  * 提交用 curl.exe --max-time（超时不等于未送达，绝不立即重试）
  * node 6 = 参考图，node 35-42 = None

应用档位（--app，2026-10-07 由 `--info` 动态查得，勿凭记忆改）
-----------------------------------------------------------
  t8balance    2095868555916038145  旧「双采 V2」13 节点：无文武戏、无动态强度，时长上限 15s
                                    ★ 默认档位（2026-10-10 起）。t8balance30 出片质量有问题，勿默认使用
  t8balance30  2103216854566268930  新「30秒直出-最强文武双修均衡版」15 节点：
                                     ⚠️ 2026-10-10 用户反馈该模型出片有问题 —— 仅留档，不推荐
                                     + node 65 模式选择（--mode wen/wu，0=文戏/1=武戏）
                                     + node 61 动态强度（--dyn，默认 1.5，范围 -10~10）
                                     + node 27 时长最长 30s（mp 默认 0.4，30s 建议降 mp）
  --app 也可直接传裸 appId；命中已知档位则自动套用其节点映射。
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
DEFAULT_LEDGER = r"d:\work\minimax_h3\韩老魔的宫装女友\任务记录\上传结果.json"
# 9 个图槽的 nodeId，顺序即 image1..image9（SKILL.md §6A 节点表：6, 35—42）
IMAGE_NODES = ["6", "35", "36", "37", "38", "39", "40", "41", "42"]

# ---- 应用档位（appId + 该应用独有的可覆盖节点） ----
# 节点信息一律以 `runninghub_app.py --info <appId>` 动态查询为准，本表只存"映射关系"。
APPS = {
    "t8balance": {
        "app": "2095868555916038145",
        "label": "T8 平衡版（双采 V2，旧）",
        "max_seconds": 15,
        "default_mp": "0.72",
        "mode_node": None,      # 无文武戏选择
        "dyn_node": None,       # 无动态强度
    },
    "t8balance30": {
        "app": "2103216854566268930",
        "label": "30秒直出-最强文武双修均衡版（多参双采）⚠️出片质量有问题，不推荐",
        "max_seconds": 30,
        "default_mp": "0.4",    # 应用自身默认值（1采总像素，2采 1.5 倍）
        "mode_node": "65",      # easy anythingIndexSwitch：index 0=文戏 1=武戏
        "dyn_node": "61",       # Float 动态强度，默认 1.5，范围 -10~10
    },
}
DEFAULT_APP = "t8balance"          # ★ 默认档位（2026-10-10 定）；t8balance30 出片有问题故不作默认
_APP_BY_ID = {v["app"]: k for k, v in APPS.items()}


def resolve_app(name_or_id):
    """--app 接受档位别名或裸 appId；返回 (档位名, 档位 dict)。未知 appId 走通用档位。"""
    if name_or_id in APPS:
        return name_or_id, APPS[name_or_id]
    if name_or_id in _APP_BY_ID:
        k = _APP_BY_ID[name_or_id]
        return k, APPS[k]
    return name_or_id, {"app": name_or_id, "label": f"未登记应用 {name_or_id}",
                        "max_seconds": None, "default_mp": None,
                        "mode_node": None, "dyn_node": None}


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


def ledger_key(local):
    """ledger 键：用「上级目录/文件名」，避免同名文件跨角色串号。

    🔴 坑（2026-10-10 踩，白跑 3 个任务）：本项目四个角色的三视图文件名完全
    相同（都是 `人物三视图（真人质感-基础）.png`），只用 basename 当键会让
    后一个角色覆盖前一个 → 多个角色解析到同一个 openapi hash，去重后再丢掉
    重复槽位，最终 <Picture 2> 整条丢失、全都指向同一个人的脸。
    用「上级目录（角色名）/文件名」做键即天然唯一。
    """
    ap = os.path.abspath(local)
    parent = os.path.basename(os.path.dirname(ap))
    return parent + "/" + os.path.basename(ap)


def upload_image(local, ledger, ledger_path, key):
    """内容寻址上传；同路径复用 ledger 记录（隔天链接失效时强制重传）。"""
    ap = os.path.abspath(local)
    name = ledger_key(local)
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


def build_payload(tag, prompt, image_list, seconds, aspect, mp, instance, rec_dir,
                  profile=None, profile_name="t8balance", mode="wen", dyn=1.5):
    """image_list：按 image1..image9 顺序排列的 openapi 短路径；不足 9 个的槽自动填 "None"。

    profile 为 APPS 档位 dict；mode（wen/wu）与 dyn 只在该档位确有对应节点时才写入 payload，
    故同一份 job 定义可在旧/新应用间切换而不会给旧应用塞入未知 nodeId。
    """
    profile = profile or APPS["t8balance"]
    shorts = [str(s) for s in image_list][:len(IMAGE_NODES)]
    shorts += ["None"] * (len(IMAGE_NODES) - len(shorts))
    nodes = [
        {"nodeId": "27", "fieldName": "value", "fieldValue": str(seconds)},
        {"nodeId": "28", "fieldName": "prompt", "fieldValue": prompt},
        {"nodeId": "29", "fieldName": "aspect_ratio", "fieldValue": aspect},
        {"nodeId": "29", "fieldName": "megapixels", "fieldValue": str(mp)},
    ]
    if profile.get("mode_node"):     # 文武戏选择（0=文戏 1=武戏）
        nodes.append({"nodeId": profile["mode_node"], "fieldName": "index",
                      "fieldValue": "0" if mode == "wen" else "1"})
    if profile.get("dyn_node"):      # 动态强度
        nodes.append({"nodeId": profile["dyn_node"], "fieldName": "value",
                      "fieldValue": str(dyn)})
    nodes += [{"nodeId": n, "fieldName": "image", "fieldValue": s}
              for n, s in zip(IMAGE_NODES, shorts)]
    payload = {"nodeInfoList": nodes, "instanceType": instance, "usePersonalQueue": "false"}
    pp = os.path.join(rec_dir, f"{profile_name}-{tag}-payload.json")
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
    ap.add_argument("--app", default=DEFAULT_APP,
                    help="应用档位别名（t8balance / t8balance30）或裸 appId"
                         "（默认 t8balance；t8balance30 出片质量问题，不推荐）")
    ap.add_argument("--mode", default="wen", choices=["wen", "wu"],
                    help="文武戏选择：wen=文戏(0) / wu=武戏(1)；仅 t8balance30 的 node 65 生效（该档不推荐）")
    ap.add_argument("--dyn", type=float, default=1.5,
                    help="动态强度 -10~10（默认 1.5）；仅 t8balance30 的 node 61 生效（该档不推荐）")
    ap.add_argument("--prefix", default="宫装女友", help="成片文件名前缀（默认 宫装女友）")
    ap.add_argument("--aspect", default="9:16 (Portrait Widescreen)")
    ap.add_argument("--mp", default=None,
                    help="megapixels；不填用档位默认（t8balance 0.72 / t8balance30 0.4）")
    ap.add_argument("--instance", default="plus", choices=["default", "plus", "ultra"],
                    help="实例档位；mp0.72 下 plus 可跑 14—15s，mp0.86 下 plus 只稳定 ≤10s；"
                         "长段（≥20s）建议 --mp 0.4 起步，OOM 再加 --instance ultra")
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

    # ---- 0) 应用档位解析（别名 → appId + 该应用独有节点） ----
    app_name, profile = resolve_app(a.app)
    if a.mp is None:
        a.mp = profile.get("default_mp") or "0.72"
    print(f"应用档位：{app_name} — {profile['label']}  appId={profile['app']}  "
          f"mp={a.mp} instance={a.instance}"
          + (f"  模式={'武戏' if a.mode == 'wu' else '文戏'}／动态强度={a.dyn}"
             if profile.get("mode_node") else "  （该应用无文武戏/动态强度节点）"))
    for j in jobs:
        sec = float(j.get("seconds", "10"))
        mx = profile.get("max_seconds")
        if mx and sec > mx:
            print(f"  [!] {j['tag']} 时长 {sec}s 超过档位记录的 {mx}s 上限——"
                  f"确认该应用确实支持再继续（{app_name} 未验证过该时长）")

    state_path = os.path.join(a.rec_dir, f"{app_name}-run-state.json")
    state = json.load(open(state_path, encoding="utf-8")) if os.path.exists(state_path) else {}

    def save():
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    # ---- 1) 提示词 + 参考图（上传/复用；dry-run 只展示不传图） ----
    ready = {}
    for j in jobs:
        tag = j["tag"]
        prompt = extract_prompt(j["prompt_file"])
        srcs = j.get("images") or [j["image"]]
        shorts, up_ats = [], []
        for img in srcs:
            if str(img).startswith("openapi/"):
                short, up_at = str(img), time.time() - 86400
            elif a.dry_run:
                short, up_at = f"<本地待传> {os.path.basename(str(img))}", 0
            else:
                short, up_at = upload_image(img, ledger, a.ledger, key)
            shorts.append(short)
            up_ats.append(up_at)
        ready[tag] = {"prompt": prompt, "images": shorts,
                      "ready_at": (max(up_ats) if up_ats else time.time()) + a.sync_wait}
        if a.dry_run:
            print(f"[dry-run] {tag}: seconds={j.get('seconds', '10')} "
                  f"images({len(shorts)})={shorts}\n  prompt 前 120 字：{prompt[:120]}\n")

    if a.upload_only or a.dry_run:
        print("OPENAPI_MAPPING")
        for tag, r in ready.items():
            print(f"  {tag} -> {r['images']}")
        return 0

    # ---- 2) 提交（并发 ≤ max_concurrent，尊重同步间隔；421 退避） ----
    def alive_count():
        return sum(1 for v in state.values()
                   if v.get("task_id") and not v.get("status"))

    def poll_active():
        """轮询进行中的任务：更新状态 → 落 result 回执 → 下载成片。

        供「提交阶段的并发等待」与「提交后的主轮询」共用。
        旧版只在提交全部结束后才轮询，导致并发满 3 后卡在等待里
        永远等不到状态更新（死锁）——每批量 >3 个 job 必触发。
        """
        changed = False
        for t, v in list(state.items()):
            if not v.get("task_id") or v.get("status") in ("SUCCESS", "FAILED"):
                continue
            q = query(v["task_id"], key)
            s = q.get("status")
            if s in ("SUCCESS", "FAILED"):
                v["status"] = s
                v["usage"] = q.get("usage")
                v["err"] = q.get("errorCode")
                changed = True
                save()
                with open(os.path.join(a.rec_dir, f"{app_name}-{t}-result.json"), "w",
                          encoding="utf-8") as f:
                    json.dump(q, f, ensure_ascii=False, indent=2)
                u = q.get("usage") or {}
                print(f"STATUS {t} {s} coins={u.get('consumeCoins')} "
                      f"sec={u.get('taskCostTime')} err={q.get('errorCode')}")
                if s == "SUCCESS":
                    urls = [o.get("url") for o in (q.get("results") or []) if o.get("url")]
                    if urls:
                        dst = os.path.join(
                            a.out_dir, f"{a.prefix}{t}_" + time.strftime("%Y%m%d-%H%M%S") + ".mp4")
                        download(urls[0], dst)
                        v["local"] = dst
                        save()
                        print(f"DOWNLOADED {dst}")
                elif str(q.get("errorCode")) == "805":
                    print(f"  ↑ {t}：805 OOM（零扣费）——先降 --mp（如 0.4），仍 OOM 再加 "
                          f"--instance ultra，换新 tag 重跑该 job")
        return changed

    for j in jobs:
        tag = j["tag"]
        st = state.get(tag, {})
        # 已成功/进行中的跳过；FAILED 允许重提（805 OOM 零扣费，重提无风险）
        if st.get("task_id") and st.get("status") != "FAILED":
            continue
        if st.get("status") == "FAILED":
            print(f"  {tag}：上次 FAILED(err={st.get('err')})，重置后重提")
        wait = ready[tag]["ready_at"] - time.time()
        if wait > 0:
            print(f"  {tag}：等待同步间隔 {wait:.0f}s ...")
            time.sleep(max(wait, 0))
        while alive_count() >= a.max_concurrent:
            poll_active()          # 边等边轮询：否则空位永远等不到（旧版死锁）
            if alive_count() >= a.max_concurrent:
                time.sleep(a.poll)
        payload, pp = build_payload(tag, ready[tag]["prompt"], ready[tag]["images"],
                                    j.get("seconds", "10"), a.aspect, a.mp,
                                    a.instance, a.rec_dir,
                                    profile=profile, profile_name=app_name,
                                    mode=a.mode, dyn=a.dyn)
        res = submit(pp, profile["app"], key)
        # 421 = 并发超限，等 30s 重提同一 payload（零风险）
        tries = 0
        while (res.get("errorCode") == "421" or "421" in str(res.get("msg", ""))) and tries < 10:
            tries += 1
            print(f"  {tag}：421 并发超限，30s 后重提（第 {tries} 次）")
            time.sleep(30)
            res = submit(pp, profile["app"], key)
        tid = res.get("taskId") or (res.get("data") or {}).get("taskId") or res.get("data")
        state[tag] = {"task_id": tid, "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
        save()
        with open(os.path.join(a.rec_dir, f"{app_name}-{tag}-submit.json"), "w",
                  encoding="utf-8") as f:
            json.dump({"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "resp": res}, f,
                      ensure_ascii=False, indent=2)
        print(f"SUBMITTED {tag} {tid}")

    # ---- 3) 轮询 + 下载 ----
    t0 = time.time()
    while time.time() - t0 < a.timeout:
        if alive_count() == 0:
            break
        poll_active()
        if alive_count():
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

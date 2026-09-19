#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publish_episode.py — 宫装女友双平台发布固化脚本（B站 + 抖音）

把「B站投稿（含创作声明一次带入）-> B站回读核验 -> 抖音投稿 -> 抖音回读核验
-> 生成台账块」固化为一条命令，仅依赖 Python 标准库。

设计依据（2026-09-19 实测，详见 SKILL 7.1/7.2）：
  * B站创作声明必须用 `--submit web --extra-fields '{"creation_statement":{"id":1}}'`
    一次带入；`--submit app` 不携带该字段，会退化成「投稿后再补刀」。
  * 抖音天然一次到位（sau 浏览器自动化，发布表单内选自主声明），无事后补设。
  * 抖音可能弹短信验证码风控门：脚本会识别并在此等待 verify_code.txt（无 BOM 写入）。

典型用法：
  # 1) 双平台发布（自动读分集目录里的《E{NN}-双平台发布文案.txt》）
  python publish_episode.py --episode E09

  # 2) 只看将要执行的命令，不真正发布
  python publish_episode.py --episode E09 --dry-run

  # 3) 只发 B站
  python publish_episode.py --episode E09 --platform bilibili

  # 4) 已知短信验证码，直接带上（避免等待）
  python publish_episode.py --episode E10 --platform douyin --dy-code 123456

  # 5) 只回读核验已发布稿件（不发布）
  python publish_episode.py --episode E09 --verify-only

  # 6) 清理误投/测试稿件
  python publish_episode.py --delete-bili aid=117296378943400
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------- 配置

PROJECT_ROOT = Path(r"d:\work\minimax_h3")
SERIES_DIR = PROJECT_ROOT / "韩老魔的宫装女友"
SAU_EXE = Path(r"D:\work\social-auto-upload\.venv\Scripts\sau.exe")
COOKIE_DIR = Path(r"D:\work\social-auto-upload\cookies")
VERIFY_CODE_FILE = Path(r"D:\work\social-auto-upload\verify_code.txt")

BILI_ACCOUNT = "bilibili_main"
DY_ACCOUNT = "creator"
DY_COOKIE = COOKIE_DIR / "douyin_creator.json"
TID = "47"                      # 动画·短片/同人
BILI_LINE = "bda2"              # bldsa 线路证书过期，固定走 bda2
AI_DECLARATION = "内容由AI生成"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

DOUYIN_GATE_HINTS = ("检测到短信验证码", "获取验证码", "短信验证码")

if hasattr(sys.stdout, "buffer"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def log(msg):
    print(msg, flush=True)


def show_cmd(cmd):
    return subprocess.list2cmdline([str(c) for c in cmd])


# ---------------------------------------------------------------- 通用

def http_json(url, headers, data=None, method=None):
    body = None
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers,
                                method=method or ("POST" if body else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode("utf-8", "ignore")[:300]}
    except Exception as e:                                   # noqa: BLE001
        return {"error": str(e)}


def load_cookies(path):
    """返回 (cookie_header, jar, token_info)"""
    raw = json.load(open(path, encoding="utf-8"))
    cookies = raw.get("cookie_info", {}).get("cookies") or raw.get("cookies") or []
    header = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
    return header, raw


# ---------------------------------------------------------------- 定位分集资产

def resolve_episode(episode=None, directory=None):
    if directory:
        d = Path(directory)
        if not d.is_dir():
            raise SystemExit(f"[X] 目录不存在：{d}")
        return d
    hits = sorted(p for p in SERIES_DIR.glob(f"{episode}-*") if p.is_dir())
    if not hits:
        raise SystemExit(f"[X] 未找到分集目录 {episode}-* （在 {SERIES_DIR}）")
    if len(hits) > 1:
        log(f"[!] 匹配到多个目录，取第一个：{[h.name for h in hits]}")
    return hits[0]


def resolve_video(ep_dir, episode):
    """优先 5B 混音发布版 E{NN}.mp4 -> 原始成片 -> 合集命名 -> 兜底任意 mp4"""
    vdir = ep_dir / "video"
    if not vdir.is_dir():
        raise SystemExit(f"[X] 无 video 目录：{vdir}")
    mp4s = [p for p in vdir.glob("*.mp4")]
    if not mp4s:
        raise SystemExit(f"[X] video 目录下没有 mp4：{vdir}")

    def rank(p):
        n = p.name
        if n == f"{episode}.mp4":
            return 0                                  # 混音发布版
        if n.startswith(f"宫装女友{episode}_"):
            return 1                                  # 原始成片
        if "合集" in n and "NM" not in n:
            return 2
        if "NM" in n:
            return 9                                  # 无 BGM 素材，不优先
        return 5

    mp4s.sort(key=lambda p: (rank(p), p.name))
    return mp4s[0]


def resolve_cover(ep_dir, episode):
    imgs = [p for p in (ep_dir / "images").glob(f"{episode}*.png")]
    if not imgs:
        imgs = [p for p in (ep_dir / "images").glob("*.png")]
    imgs = [p for p in imgs if "场景" not in p.name]
    if not imgs:
        raise SystemExit(f"[X] 未找到封面参考图：{ep_dir / 'images'}")
    imgs.sort(key=lambda p: p.name)
    return imgs[0]


# ---------------------------------------------------------------- 文案包解析

def parse_copy_file(ep_dir, episode):
    """解析《E{NN}-双平台发布文案.txt》；缺失则返回 {}"""
    cands = sorted(ep_dir.glob(f"{episode}-*发布文案*.txt")) + sorted(ep_dir.glob("*双平台发布文案*.txt"))
    if not cands:
        return {}, None
    path = cands[0]
    text = path.read_text(encoding="utf-8", errors="replace")

    def block(name):
        m = re.search(rf"^##\s*{name}.*?$(.*?)(?=^##\s|\Z)", text, re.S | re.M)
        return m.group(1) if m else ""

    def field(body, label):
        m = re.search(rf"^-\s*{label}[^：:]*[：:]\s*(.+?)(?=^-\s|\Z)", body, re.S | re.M)
        return m.group(1).strip() if m else ""

    def multi(body, label):
        """简介可能多行，压成一行"""
        v = field(body, label)
        return re.sub(r"\s+", " ", v).strip()

    dy, bili = block(r"抖音"), block(r"B\s*站")
    topics = re.findall(r"^\s*\d+\.\s*#(.+?)\s*$", dy, re.M)
    tags_raw = field(bili, r"标签")
    tags = [t.strip() for t in re.split(r"[,，]", tags_raw) if t.strip()]

    out = {
        "douyin": {
            "title": multi(dy, r"标题"),
            "desc": multi(dy, r"简介"),
            "topics": topics,
        },
        "bilibili": {
            "title": multi(bili, r"标题"),
            "desc": multi(bili, r"简介"),
            "tags": tags,
        },
    }
    return out, path


# ---------------------------------------------------------------- B 站
# B 站底层机制统一复用全局技能脚本，避免两处实现分叉：
#   c:\Users\Administrator\.trae-cn\skills\sau-upload\scripts\bili_publish.py

BILI_HELPER = Path(r"c:\Users\Administrator\.trae-cn\skills\sau-upload\scripts\bili_publish.py")


def _load_bili_helper():
    if not BILI_HELPER.exists():
        raise SystemExit(f"[X] 缺少全局 B站发布脚本：{BILI_HELPER}\n"
                         f"    请确认 sau-upload 技能已安装（其 scripts/bili_publish.py）")
    import importlib.util
    spec = importlib.util.spec_from_file_location("bili_publish", BILI_HELPER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bili = _load_bili_helper()


def bili_upload(video, cover, title, desc, tags, dry_run=False):
    """投稿（--submit web 一次带入创作声明）；具体实现在全局 bili_publish.py"""
    log("\n=== B 站投稿（web 接口，创作声明一次带入） ===")
    res = bili.upload(str(video), title, desc, tags, cover=str(cover),
                      tid=TID, account=BILI_ACCOUNT, line=BILI_LINE, dry_run=dry_run)
    if not dry_run and res.get("submit_interface") == "app":
        res["warn"] = "走成了 APP 接口，创作声明不会一次带入！"
    return res


def bili_verify(aid):
    return bili.verify(aid, account=BILI_ACCOUNT)


def bili_delete(aid):
    return bili.delete(aid, account=BILI_ACCOUNT)


# ---------------------------------------------------------------- 抖音

def douyin_upload(video, cover, title, desc, topics, dy_code=None, dry_run=False,
                  code_timeout=900):
    cmd = [
        str(SAU_EXE), "douyin", "upload-video",
        "--account", DY_ACCOUNT,
        "--file", str(video),
        "--headless",
        "--title", title[:30],
        "--desc", desc,
        "--tags", ",".join(topics[:5]),                    # 硬上限 5 个
        "--thumbnail", str(cover),
        "--declaration", AI_DECLARATION,
    ]
    log("\n=== 抖音投稿（sau 浏览器自动化，自主声明随表单一次选定） ===")
    log("  " + show_cmd(cmd))
    if dry_run:
        return {"dry_run": True, "cmd": cmd}

    if dy_code:
        VERIFY_CODE_FILE.write_text(str(dy_code), encoding="utf-8")   # 无 BOM

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", bufsize=1)
    gate_seen = False
    gate_wait_deadline = None
    tail = []
    for line in proc.stdout:
        line = line.rstrip("\n")
        log("  " + line)
        tail.append(line)
        if not gate_seen and any(h in line for h in DOUYIN_GATE_HINTS):
            gate_seen = True
            gate_wait_deadline = time.time() + code_timeout
            log("\n" + "!" * 62)
            log("!! 抖音短信验证码风控门已触发（硬暂停）")
            log("!! 请查看手机短信，把 6 位验证码写入：")
            log(f"!!   {VERIFY_CODE_FILE}     （必须是 UTF-8 无 BOM）")
            log(f"!! 脚本将在此等待最多 {code_timeout // 60} 分钟，写入后自动继续。")
            log("!" * 62 + "\n")
        if gate_seen and not VERIFY_CODE_FILE.exists():
            if time.time() > gate_wait_deadline:
                proc.kill()
                return {"gate_timeout": True, "raw_tail": "\n".join(tail[-40:])}
            time.sleep(2)
    proc.wait()
    out = "\n".join(tail)

    res = {"returncode": proc.returncode, "gate_seen": gate_seen,
           "published": "视频发布成功" in out, "raw_tail": out[-600:]}
    if "自主声明已选择" in out:
        res["declaration_selected"] = True
    return res


def douyin_verify(limit=6):
    cookie, raw = load_cookies(DY_COOKIE)
    hdr = {"User-Agent": UA, "Cookie": cookie,
           "Referer": "https://creator.douyin.com/creator-micro/content/manage"}
    params = {"aid": "2906", "count": str(limit), "cursor": "0", "type": "1",
              "publish_time_type": "0", "need_charge_info": "false"}
    url = "https://creator.douyin.com/web/api/media/aweme/post/?" + urllib.parse.urlencode(params)
    j = http_json(url, hdr)
    out = []
    for a in (j.get("aweme_list") or []):
        desc = a.get("desc") or ""
        st = a.get("status") or {}
        out.append({
            "aweme_id": a.get("aweme_id"),
            "desc": desc,
            "topics": re.findall(r"#([^#\s]+)", desc),
            "public": not st.get("self_see"),
            "reviewing": st.get("in_reviewing"),
            "private": st.get("is_private"),
            "url": f"https://www.douyin.com/video/{a.get('aweme_id')}",
        })
    return out


# ---------------------------------------------------------------- 台账块

def build_markdown(episode, bili_res, bili_ver, dy_res, dy_items, copy_path,
                   video, cover, ep_dir):
    now = time.strftime("%Y-%m-%d %H:%M")
    rel = lambda p: str(Path(p).relative_to(SERIES_DIR)).replace("\\", "/")  # noqa: E731
    lines = [f"- **发布状态（{now} 双平台已发布）**："]
    if bili_res and not bili_res.get("dry_run"):
        bvid = bili_res.get("bvid", "?")
        aid = bili_res.get("aid", "?")
        lines.append(
            f"- **B站投稿**：账号 {BILI_ACCOUNT}，bvid **{bvid}**，aid {aid}，"
            f"https://www.bilibili.com/video/{bvid} ；state {bili_ver.get('state')}"
            f"（{bili_ver.get('state_desc')}），创作声明 **id={bili_ver.get('decl_id')}"
            f"（{bili_ver.get('decl_text')}）**；分区 tid {bili_ver.get('tid')}，"
            f"{bili_ver.get('tags')} 标签，封面=`{rel(cover)}`；`--submit web` 一次带入声明")
    if dy_res and not dy_res.get("dry_run") and dy_items:
        d = dy_items[0]
        lines.append(
            f"- **抖音投稿**：账号 {DY_ACCOUNT}，aweme_id **{d['aweme_id']}**，{d['url']} ；"
            f"公开={d['public']}，话题 {len(d['topics'])} 个「{' '.join('#' + t for t in d['topics'])}」"
            f"，封面同上，自主声明「{AI_DECLARATION}」随发布表单一次选定"
            + ("；**触发短信验证码门**" if (dy_res or {}).get("gate_seen") else "；未触发短信风控门"))
    if copy_path:
        lines.append(f"- 发布文案：`{rel(copy_path)}`")
    lines.append(f"- 成片：`{rel(video)}`")
    return "\n".join(lines)


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="宫装女友双平台发布固化脚本")
    ap.add_argument("--episode", help="集号，如 E09")
    ap.add_argument("--dir", help="直接指定分集目录（覆盖 --episode 定位）")
    ap.add_argument("--platform", default="both", choices=["both", "bilibili", "douyin"])
    ap.add_argument("--dry-run", action="store_true", help="只打印将要执行的命令")
    ap.add_argument("--verify-only", action="store_true", help="只回读核验，不发布")
    ap.add_argument("--bili-aid", type=int, help="配合 --verify-only 指定 B站 aid")
    ap.add_argument("--dy-code", help="抖音 6 位短信验证码（已知时直接带上）")
    ap.add_argument("--code-timeout", type=int, default=900, help="等待验证码秒数，默认 900")
    ap.add_argument("--delete-bili", metavar="AID=<id>", help="删除指定 B站稿件（不可逆）")
    args = ap.parse_args()

    if args.delete_bili:
        aid = int(re.sub(r"^\D*", "", args.delete_bili))
        log(f"删除 B站稿件 aid={aid} ...")
        log(json.dumps(bili_delete(aid), ensure_ascii=False))
        log("回读：" + json.dumps(bili_verify(aid), ensure_ascii=False))
        return 0

    if not args.episode and not args.dir:
        ap.error("需要 --episode 或 --dir")

    ep_dir = resolve_episode(args.episode, args.dir)
    episode = args.episode or ep_dir.name.split("-")[0]
    log(f"分集目录：{ep_dir}")

    if args.verify_only:
        if args.bili_aid:
            log("B站回读：" + json.dumps(bili_verify(args.bili_aid), ensure_ascii=False, indent=2))
        log("抖音回读：")
        for d in douyin_verify():
            log(f"  {d['aweme_id']} public={d['public']} topics={d['topics']}\n    {d['desc'][:60]}")
        return 0

    copy_data, copy_path = parse_copy_file(ep_dir, episode)
    if copy_path:
        log(f"文案包：{copy_path.name}")
    else:
        log("[!] 未找到发布文案包，将要求命令行提供标题/简介（本脚本不含创作文案）")

    video, cover = resolve_video(ep_dir, episode), resolve_cover(ep_dir, episode)
    log(f"成片：{video.name}（{video.stat().st_size:,} 字节）")
    log(f"封面：{cover.name}")

    by, bl = copy_data.get("douyin", {}), copy_data.get("bilibili", {})
    if not bl.get("title"):
        raise SystemExit("[X] 解析不到 B站标题，请检查文案包格式或改用人工发布")

    bili_res = bili_ver = None
    dy_res = None
    dy_items = []

    if args.platform in ("both", "bilibili"):
        bili_res = bili_upload(video, cover, bl["title"], bl["desc"], bl["tags"],
                               dry_run=args.dry_run)
        if not args.dry_run and bili_res.get("aid"):
            log("\n--- B站回读核验 ---")
            time.sleep(3)
            bili_ver = bili_verify(bili_res["aid"])
            log(json.dumps(bili_ver, ensure_ascii=False, indent=2))
            ok = bili_ver.get("decl_id") == 1
            log(f">>> 创作声明核验：{'PASS（一次到位）' if ok else 'FAIL —— 需走兜底补设'}")

    if args.platform in ("both", "douyin"):
        if not by.get("title"):
            raise SystemExit("[X] 解析不到抖音标题")
        dy_res = douyin_upload(video, cover, by["title"], by["desc"], by["topics"],
                               dy_code=args.dy_code, dry_run=args.dry_run,
                               code_timeout=args.code_timeout)
        if not args.dry_run and dy_res.get("gate_timeout"):
            log("[X] 等待验证码超时，抖音未发布；写入 verify_code.txt 后重跑本命令")
        elif not args.dry_run:
            log("\n--- 抖音回读核验 ---")
            time.sleep(5)
            dy_items = douyin_verify()
            for d in dy_items[:2]:
                log(f"  {d['aweme_id']} public={d['public']} topics={len(d['topics'])} -> {d['topics']}")

    if args.dry_run:
        return 0

    # 结果落盘 + 台账块
    result = {
        "episode": episode,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "video": str(video), "cover": str(cover),
        "bilibili": {"upload": bili_res, "verify": bili_ver},
        "douyin": {"upload": dy_res, "recent": dy_items[:2]},
    }
    rec = ep_dir / "任务记录"
    rec.mkdir(exist_ok=True)
    (rec / "publish_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    md = build_markdown(episode, bili_res, bili_ver or {}, dy_res, dy_items,
                        copy_path, video, cover, ep_dir)
    (rec / "publish_taizhang_block.md").write_text(md, encoding="utf-8")
    log("\n=== 台账块（可直接粘贴进总纲/资产清单，亦已存 任务记录/publish_taizhang_block.md） ===")
    log(md)
    log(f"\n结果：{rec / 'publish_result.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

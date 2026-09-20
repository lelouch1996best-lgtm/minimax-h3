#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
concat_and_mix.py — 宫装女友系列 · Step 5B 合成固化脚本（拼接 + 统一 BGM 后置混音）

把「concat 流拷贝拼接 → BGM 不足自动 aloop 循环 → 垫底混音（淡入/淡出）→
ffprobe + volumedetect 校验 → merge_summary.json 落盘」固化为一条命令。
2026-09-19 由 E11 临时脚本升格固化，仅标准库。

典型用法
--------
  python tools/concat_and_mix.py ^
      --segs "video\\宫装女友E12A_xxx.mp4" "video\\宫装女友E12B_xxx.mp4" ^
      --bgm "assets\\bgm\\bgm_国风甜妹_温馨撒娇_001.m4a" ^
      --out "E12-xxx合集\\video\\E12.mp4" ^
      --rec-dir "E12-xxx合集\\任务记录"

  # 不加 BGM 只拼接
  python tools/concat_and_mix.py --segs a.mp4 b.mp4 --out E12.mp4

说明
----
  * 段顺序 = --segs 顺序（剧情顺序）
  * BGM 短于成片自动 `aloop=loop=-1:size=2e9` 循环铺满（Step 5B.2 规则）
  * BGM 音量默认 0.25 垫底，人声/环境音（[0:a]）为主轨；duration=first 保证不超视频
  * 视频流 -c copy 不重编码；concat 流拷贝失败时自动转码兜底（-c:v libx264 -crf 18）
  * 校验：ffprobe 时长/规格 + volumedetect（非静音、无削波），结果写 merge_summary.json
"""

import argparse
import json
import os
import subprocess
import sys

FFMPEG = subprocess.run(
    [sys.executable, "-c", "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"],
    capture_output=True, text=True).stdout.strip()
FFPROBE = os.path.join(os.path.dirname(FFMPEG), "ffprobe.exe")
if not os.path.exists(FFPROBE):
    FFPROBE = "ffprobe"


def probe(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-print_format", "json",
                        "-show_format", "-show_streams", path],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return json.loads(r.stdout)


def dur(path):
    return float(probe(path)["format"]["duration"])


def run_quiet(cmd):
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def mean_vol(path):
    r = run_quiet([FFMPEG, "-i", path, "-af", "volumedetect", "-f", "null", "-"])
    out = (r.stderr or "") + (r.stdout or "")
    lines = [l for l in out.splitlines() if "mean_volume" in l or "max_volume" in l]
    return " | ".join(x.split("]")[-1].strip() for x in lines)


def main():
    ap = argparse.ArgumentParser(description="Step 5B：多段拼接 + 统一 BGM 后置混音")
    ap.add_argument("--segs", nargs="+", required=True, help="各段 mp4（按剧情顺序）")
    ap.add_argument("--bgm", help="BGM 文件（省略则只拼接）")
    ap.add_argument("--out", required=True, help="输出正片路径（惯例 E{NN}.mp4）")
    ap.add_argument("--rec-dir", help="中间件/摘要目录（默认与 out 同目录）")
    ap.add_argument("--bgm-volume", type=float, default=0.25)
    ap.add_argument("--fade-in", type=float, default=0.5)
    ap.add_argument("--fade-out", type=float, default=1.6)
    ap.add_argument("--no-summary", action="store_true")
    a = ap.parse_args()

    segs = []
    for p in a.segs:
        if not os.path.exists(p):
            raise SystemExit(f"[X] 段不存在：{p}")
        segs.append(os.path.abspath(p))
    rec = a.rec_dir or os.path.dirname(os.path.abspath(a.out))
    os.makedirs(rec, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)

    print("===== 段清单 =====")
    for p in segs:
        print(f"  {round(dur(p), 3)}s  {os.path.getsize(p):,}B  {os.path.basename(p)}")

    # ---- 1) concat 流拷贝（失败转码兜底） ----
    listp = os.path.join(rec, "concat_list.txt")
    with open(listp, "w", encoding="utf-8") as f:
        for p in segs:
            f.write("file '%s'\n" % p.replace("\\", "/"))
    joined = os.path.join(rec, "_concat_copy.mp4")
    r = run_quiet([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", listp,
                   "-c", "copy", joined])
    mode = "concat -c copy"
    if not os.path.exists(joined):
        print("流拷贝失败，转码兜底 ...")
        r = run_quiet([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", listp,
                       "-c:v", "libx264", "-crf", "18", "-c:a", "aac", joined])
        mode = "concat 转码 (libx264 crf18)"
        if not os.path.exists(joined):
            raise SystemExit(f"[X] 拼接失败：\n{r.stderr[-1500:]}")
    D = dur(joined)
    print(f"拼接完成：{round(D, 3)}s  {os.path.getsize(joined):,}B  （{mode}）")

    # ---- 2) BGM 垫底混音 ----
    bgm_info = None
    out = a.out
    if a.bgm:
        bd = dur(a.bgm)
        fade_st = max(D - a.fade_out, 0)
        chain = (f"[1:a]aloop=loop=-1:size=2e9,atrim=0:{D},"
                 f"volume={a.bgm_volume},"
                 f"afade=t=in:st=0:d={a.fade_in},"
                 f"afade=t=out:st={fade_st:.3f}:d={a.fade_out}[bgm];"
                 f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=0[a]")
        r = run_quiet([FFMPEG, "-y", "-i", joined, "-i", a.bgm,
                       "-filter_complex", chain, "-map", "0:v", "-map", "[a]",
                       "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", out])
        if not os.path.exists(out):
            raise SystemExit(f"[X] 混音失败：\n{r.stderr[-2000:]}")
        bgm_info = {"file": os.path.basename(a.bgm), "source_duration": round(bd, 3),
                    "looped": bd < D, "volume": a.bgm_volume,
                    "fade_in": a.fade_in,
                    "fade_out": f"st={fade_st:.3f} d={a.fade_out}"}
        print(f"混音完成：{'aloop 循环铺满（源曲短于成片）' if bd < D else '单遍铺满'}，"
              f"volume={a.bgm_volume}")
    else:
        os.replace(joined, out)
        joined = out
        print("未指定 BGM，拼接件即成品")

    # ---- 3) 校验 + 摘要 ----
    pi = probe(out)
    v = next(s for s in pi["streams"] if s["codec_type"] == "video")
    au = next((s for s in pi["streams"] if s["codec_type"] == "audio"), None)
    vol = mean_vol(out)
    print("\n===== 成片 =====")
    print(f"  {out}")
    print(f"  {float(pi['format']['duration']):.3f}s  {os.path.getsize(out):,}B  "
          f"{v['width']}x{v['height']} {v['codec_name']}"
          + (f" + {au['codec_name']} {au.get('sample_rate')}Hz ch={au.get('channels')}" if au else ""))
    print(f"  {vol}")

    if not a.no_summary:
        summary = {
            "segments": [{"file": os.path.basename(p), "duration": round(dur(p), 3),
                          "bytes": os.path.getsize(p)} for p in segs],
            "segment_sum": round(sum(dur(p) for p in segs), 3),
            "concat": {"file": os.path.basename(joined), "mode": mode,
                       "duration": round(D, 3), "bytes": os.path.getsize(joined)},
            "bgm": bgm_info,
            "final": {"file": out,
                      "duration": round(float(pi["format"]["duration"]), 3),
                      "bytes": os.path.getsize(out),
                      "video": f"{v['width']}x{v['height']} {v['codec_name']}",
                      "audio": (f"{au['codec_name']} {au.get('sample_rate')}Hz "
                                f"ch={au.get('channels')}") if au else None,
                      "volumedetect": vol},
        }
        sp = os.path.join(rec, "merge_summary.json")
        with open(sp, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"  摘要 -> {sp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

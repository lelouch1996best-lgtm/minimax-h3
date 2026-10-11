#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""av_align.py - 音画对齐分解器：把「镜头切点 + 台词转写 + 声音包络」合成一条时间轴。

解决的问题：
  1) 均匀间隔抽帧会跨过镜头切点 -> 漏镜头、漏信息。改成内容驱动切分。
  2) 原片没有硬字幕 -> 台词全靠听。改成走音轨转写，拿带时间码的台词。
  3) 两条轴各看各的，对不上。改成按时间码合并成一张《音画对齐表》。

流程：
  元信息 -> 抽音轨(wav) -> 场景切分(OpenCV) -> 逐镜头代表帧 + 台词段补帧
        -> 音轨转写(whisper-1, 带 segments) -> 音频 RMS 包络(静音/有声)
        -> 合并输出 音画对齐表.md + av_align.json + frames/

必须用 venv python 运行（cv2 / numpy）：
  "C:\\Users\\Administrator\\.workbuddy\\binaries\\python\\envs\\default\\Scripts\\python.exe" tools/av_align.py --video X.mp4 --out-dir Y

常用：
  --no-asr              只做镜头切分与抽帧（不花转写费）
  --music               音源是纯音乐 -> 强制关闭 prompt、按 10s 切段（防幻觉歌词）
  --scan-fps 4          场景检测的采样帧率（越大越准越慢）
  --cut-thresh 0.42     切镜阈值，漏镜就调小；误切就调大
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))


# ---------------------------------------------------------------- 基础工具

def find_ffmpeg():
    """按「imageio_ffmpeg 包 -> site-packages 扫描 -> PATH」顺序找可用的 ffmpeg."""
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and Path(exe).exists():
            return exe
    except Exception:
        pass
    try:
        import site
        roots = list(site.getsitepackages())
        try:
            roots.append(site.getusersitepackages())
        except Exception:
            pass
        for root in roots:
            if not root:
                continue
            d = Path(root) / "imageio_ffmpeg" / "binaries"
            if d.is_dir():
                for p in sorted(d.glob("ffmpeg*.exe")):
                    return str(p)
    except Exception:
        pass
    return shutil.which("ffmpeg")


def imwrite_safe(path, img):
    """cv2.imwrite 在中文路径会静默失败 -> 走 imencode + Python open(wb)."""
    ext = Path(path).suffix or ".jpg"
    ok, buf = cv2.imencode(ext, img, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    if not ok:
        raise RuntimeError(f"编码失败: {path}")
    with open(path, "wb") as f:
        f.write(buf.tobytes())


def imread_safe(path):
    data = np.fromfile(str(path), dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def probe(video):
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"打不开视频: {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return {"fps": fps, "frames": total, "w": w, "h": h,
            "duration": (total / fps) if fps else 0.0}


# ---------------------------------------------------------------- 音轨

def extract_wav(ffmpeg, video, wav_path):
    """抽 16k 单声道 wav（whisper 友好 + 体积小）."""
    if not ffmpeg:
        raise RuntimeError("找不到 ffmpeg（venv 里的 imageio_ffmpeg）")
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", str(video),
           "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav_path)]
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0 or not Path(wav_path).exists():
        raise RuntimeError("抽音轨失败: " + p.stderr.decode("utf-8", "replace")[:400])
    return Path(wav_path)


def wav_info(wav_path):
    with wave.open(str(wav_path), "rb") as w:
        return {"sr": w.getframerate(), "ch": w.getnchannels(),
                "sw": w.getsampwidth(), "n": w.getnframes()}


def split_wav(wav_path, chunk_sec, out_dir):
    """把 wav 切成若干段，返回 [(start_sec, path), ...]."""
    info = wav_info(wav_path)
    sr = info["sr"]
    per = int(chunk_sec * sr)
    out = []
    with wave.open(str(wav_path), "rb") as w:
        idx = 0
        start = 0
        while True:
            frames = w.readframes(per)
            if not frames:
                break
            p = Path(out_dir) / f"chunk_{idx:03d}.wav"
            with wave.open(str(p), "wb") as o:
                o.setnchannels(info["ch"])
                o.setsampwidth(info["sw"])
                o.setframerate(sr)
                o.writeframes(frames)
            out.append((start, p))
            start += len(frames) / (sr * info["sw"] * info["ch"])
            idx += 1
    return out


def group_utterances(words, lang, gap=0.35, max_len=12.0):
    """把词级时间戳按「静音间隔」聚成句：间隔 > gap 或单句超 max_len 就断句.

    中/日文逐字直接拼；其他语言用空格拼。句时间码 = 首词 start 到末词 end。
    """
    if not words:
        return []
    joiner = "" if lang.lower().startswith(("zh", "ja", "yue", "cn")) else " "
    groups, cur = [], []
    for w in words:
        s = float(w.get("start", 0.0))
        e = float(w.get("end", 0.0))
        t = w.get("word", "") or w.get("text", "")
        if cur and (s - cur[-1][1]) > gap:
            groups.append(cur)
            cur = []
        if cur and (e - cur[0][0]) > max_len:
            groups.append(cur)
            cur = []
        cur.append((s, e, t))
    if cur:
        groups.append(cur)
    out = []
    for g in groups:
        txt = joiner.join(x[2] for x in g).strip()
        if txt:
            out.append((round(g[0][0], 3), round(g[-1][1], 3), txt))
    return out


def asr_segments(wav_path, tmp_dir, language, prompt, model, chunk_sec, log,
                 utt_gap=0.35, granularity="word"):
    """转写 wav -> [(start, end, text), ...]；长音频自动切段并累加时间偏移.

    优先词级时间戳（实测精度远高于 segment 级：segment 会被 5s 网格吸附），
    拿不到 words 时退回 segments，再退回整段文本。
    """
    import transcribe_audio as ta

    info = wav_info(wav_path)
    dur = info["n"] / info["sr"]

    def one(path, offset, fallback_dur):
        d = ta.transcribe(str(path), model=model, language=language, prompt=prompt,
                          timeout=1800,
                          granularity=(granularity if granularity != "none" else None))
        words = d.get("words") or []
        if words:
            got = group_utterances(words, language, gap=utt_gap)
            if got:
                return [(offset + a, offset + b, t) for a, b, t in got]
        segs = d.get("segments") or []
        if segs:
            log(f"  [提示] 该段无词级时间戳，退回段级（时间码精度较低）")
            return [(offset + float(s.get("start", 0)), offset + float(s.get("end", 0)),
                     (s.get("text") or "").strip()) for s in segs if s.get("text")]
        txt = (d.get("text") or "").strip()
        return [(offset, offset + fallback_dur, txt)] if txt else []

    if dur <= chunk_sec:
        return one(wav_path, 0.0, dur)

    parts = split_wav(wav_path, chunk_sec, tmp_dir)
    log(f"  音轨 {dur:.1f}s 超长 -> 切 {len(parts)} 段独立转写")
    segs = []
    for off, p in parts:
        pi = wav_info(p)
        try:
            segs.extend(one(p, off, pi["n"] / pi["sr"]))
        except RuntimeError as e:
            log(f"  [段 {off:.0f}s] 转写失败: {e}")
    return segs


def audio_events(wav_path, win=0.1, floor_db=-38.0, loud_db=-8.0):
    """RMS 包络 -> 静音/轻声/有声/响亮 区段，用于标注无台词节拍与 BGM 起落."""
    with wave.open(str(wav_path), "rb") as w:
        sr, ch, sw, n = (w.getframerate(), w.getnchannels(),
                         w.getsampwidth(), w.getnframes())
        raw = w.readframes(n)
    if sw != 2:
        return []
    a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        a = a.reshape(-1, ch).mean(axis=1)
    m = (len(a) // max(1, int(sr * win))) * int(sr * win)
    if m == 0:
        return []
    r = a[:m].reshape(-1, int(sr * win))
    rms = np.sqrt((r ** 2).mean(axis=1)) + 1e-9
    db = 20.0 * np.log10(rms / max(rms.max(), 1e-9))

    def klass(v):
        if v < floor_db:
            return "静音"
        if v < floor_db + 12:
            return "轻声"
        if v < loud_db:
            return "有声"
        return "响亮"

    labels = [klass(v) for v in db]
    events = []
    cur, t0 = labels[0], 0.0
    for i in range(1, len(labels)):
        if labels[i] != cur:
            events.append({"start": round(t0, 2), "end": round(i * win, 2), "type": cur})
            cur, t0 = labels[i], i * win
    events.append({"start": round(t0, 2), "end": round(len(labels) * win, 2), "type": cur})
    # 合并 <0.3s 的碎段，去掉一闪而过的标签
    merged = []
    for e in events:
        if merged and (e["end"] - e["start"]) < 0.3:
            merged[-1]["end"] = e["end"]
        elif merged and merged[-1]["type"] == e["type"]:
            merged[-1]["end"] = e["end"]
        else:
            merged.append(e)
    return merged


# ---------------------------------------------------------------- 场景切分

def scan_shots(video, info, scan_fps, thresh, min_shot, log):
    """内容驱动切镜：HSV 直方图相关性 + 灰度像素差，逐帧扫描."""
    cap = cv2.VideoCapture(str(video))
    fps = info["fps"]
    step = max(1, int(round(fps / scan_fps)))
    samples = []
    prev_hist = prev_gray = None
    i = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if i % step == 0:
            t = i / fps
            small = cv2.resize(fr, (192, 108))
            hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [48, 48], [0, 180, 0, 256])
            cv2.normalize(hist, hist)
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            if prev_hist is not None:
                corr = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                md = float(np.mean(cv2.absdiff(prev_gray, gray))) / 255.0
                score = 0.6 * (1.0 - max(0.0, corr)) + 0.4 * md
                samples.append((round(t, 3), round(float(score), 4)))
            prev_hist, prev_gray = hist, gray
        i += 1
    cap.release()

    cuts = [0.0]
    for t, sc in samples:
        if sc >= thresh and (t - cuts[-1]) >= min_shot:
            cuts.append(t)
    dur = info["duration"]
    if cuts[-1] < dur - 0.05:
        cuts.append(round(dur, 3))

    shots = [{"idx": k + 1, "start": cuts[k], "end": cuts[k + 1]}
             for k in range(len(cuts) - 1)]
    top = sorted(samples, key=lambda x: -x[1])[:10]
    return shots, top


def nearest(v, arr):
    return min(arr, key=lambda x: abs(x - v)) if arr else None


def grab_frames(video, info, shots, segs, out_dir, max_frames, log):
    """每镜头抽首/中/尾 + 该镜头内每句台词的中点补帧."""
    cap = cv2.VideoCapture(str(video))
    fps = info["fps"]
    made = []
    for sh in shots:
        t0, t1 = sh["start"], sh["end"]
        span = t1 - t0
        times = [t0 + min(0.08, span * 0.1), (t0 + t1) / 2.0, t1 - min(0.08, span * 0.1)]
        for s0, s1, _txt in segs:
            mid = (s0 + s1) / 2.0
            if t0 <= mid <= t1:
                times.append(mid)
        seen, uniq = set(), []
        for t in sorted(times):
            t = round(max(t0, min(t, t1 - 0.02)), 2)
            if t < 0:
                continue
            key = round(t, 1)
            if key in seen:
                continue
            seen.add(key)
            uniq.append(t)
        sh["frames"] = []
        for t in uniq:
            if len(made) >= max_frames:
                break
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, int(round(t * fps))))
            ok, fr = cap.read()
            if not ok:
                continue
            name = f"S{sh['idx']:02d}_t{t:07.2f}.jpg"
            p = Path(out_dir) / name
            imwrite_safe(p, fr)
            sh["frames"].append({"t": t, "file": name})
            made.append(p)
    cap.release()
    log(f"  代表帧 {len(made)} 张 -> {out_dir}")
    return made


def contact_sheet(files, out_path, cols=4, w=320):
    imgs = []
    for p in files[:32]:
        im = imread_safe(p)
        if im is None:
            continue
        h = int(im.shape[0] * w / im.shape[1])
        imgs.append(cv2.resize(im, (w, h)))
    if not imgs:
        return None
    rh = max(i.shape[0] for i in imgs)
    rows = []
    for k in range(0, len(imgs), cols):
        chunk = imgs[k:k + cols]
        while len(chunk) < cols:
            chunk.append(np.zeros_like(imgs[0]))
        rows.append(np.hstack(chunk))
    sheet = np.vstack(rows)
    imwrite_safe(out_path, sheet)
    return out_path


# ---------------------------------------------------------------- 合并输出

def assign_shot(shots, s, e):
    """按重叠时长归属：跨镜台词归给重叠最大的那个镜头."""
    best, best_ov = None, 0.0
    for sh in shots:
        ov = min(e, sh["end"]) - max(s, sh["start"])
        if ov > best_ov:
            best, best_ov = sh, ov
    return best


def merge(shots, segs, events):
    for sh in shots:
        sh["dialogue"] = []
        sh["dialogue_times"] = []
        sh["dialogue_starting"] = []
    for s, e, t in segs:
        if not t:
            continue
        owner = assign_shot(shots, s, e)
        if owner is not None:
            owner["dialogue"].append(t)
            owner["dialogue_times"].append({"start": s, "end": e, "text": t})
        # 记录「起句所在的镜头」：跨镜台词可能被判给下一个镜头，
        # 但起句那一镜也是它的画面依据，不能看起来像"本镜无台词"
        for sh in shots:
            if sh["start"] - 0.02 <= s <= sh["end"] + 0.02:
                sh["dialogue_starting"].append({
                    "start": s, "end": e, "text": t,
                    "owner": owner["idx"] if owner is not None else None})
                break
    for sh in shots:
        sh["audio"] = []
        for ev in events:
            if ev["end"] < sh["start"] or ev["start"] > sh["end"]:
                continue
            ov = min(ev["end"], sh["end"]) - max(ev["start"], sh["start"])
            if ov > 0:
                sh["audio"].append((ov, ev["type"]))
        if not sh["audio"]:
            sh["sound"] = "-"
        else:
            sh["audio"].sort(key=lambda x: -x[0])
            sh["sound"] = sh["audio"][0][1]


def write_md(path, video, info, shots, segs, events, ffmpeg, note):
    L = []
    L.append(f"# 音画对齐表 - {Path(video).name}\n")
    L.append(f"> 源片：`{video}`  ")
    L.append(f"> 规格：{info['w']}x{info['h']} / {info['fps']:.3f}fps / "
             f"{info['frames']} 帧 / {info['duration']:.2f}s  ")
    L.append(f"> 镜头数：{len(shots)} ｜ 台词句数：{len(segs)} ｜ ffmpeg：`{ffmpeg}`  ")
    if note:
        L.append(f"> ⚠️ {note}  ")
    L.append("")
    L.append("## 一、镜头级分解（合并轴）\n")
    L.append("| # | 时间段 | 时长 | 声音 | 本镜台词 | 代表帧 |")
    L.append("|---|---|---|---|---|---|")
    for sh in shots:
        base = " ／ ".join(sh["dialogue"]) if sh["dialogue"] else ""
        spill = [d for d in sh.get("dialogue_starting", []) if d.get("owner") != sh["idx"]]
        cell = base or "-"
        if spill:
            marks = "、".join(f"S{d['owner']:02d}" if d.get("owner") else "?" for d in spill)
            cell = (base + " " if base else "") + f"(另有 {len(spill)} 句起于本镜 → {marks})"
        fr = " / ".join(f["file"] for f in sh.get("frames", [])) or "-"
        L.append(f"| S{sh['idx']:02d} | {sh['start']:.2f}-{sh['end']:.2f}s | "
                 f"{sh['end']-sh['start']:.2f}s | {sh['sound']} | {cell} | {fr} |")
    L.append("")
    L.append("## 二、台词轴（whisper 时间码，按句）\n")
    if segs:
        L.append("| 起 | 止 | 时长 | 台词 | 所属镜头 |")
        L.append("|---|---|---|---|---|")
        for s, e, t in segs:
            if not t:
                continue
            sh = assign_shot(shots, s, e)
            own = f"S{sh['idx']:02d}" if sh is not None else "-"
            L.append(f"| {s:.2f} | {e:.2f} | {e-s:.2f} | {t} | {own} |")
    else:
        L.append("_未转写或无语音_")
    L.append("")
    L.append("## 三、声音事件轴（静音段 = 无台词节拍）\n")
    L.append("| 起 | 止 | 时长 | 类型 | 备注 |")
    L.append("|---|---|---|---|---|")
    for ev in events:
        note = ""
        if ev["type"] == "响亮" and (ev["end"] - ev["start"]) >= 0.8:
            hit = any((min(ev["end"], e) - max(ev["start"], s)) > 0.15 for s, e, _t in segs)
            if not hit:
                note = "响亮但无转写文字（音乐/音效，或漏转）"
        L.append(f"| {ev['start']:.2f} | {ev['end']:.2f} | "
                 f"{ev['end']-ev['start']:.2f} | {ev['type']} | {note} |")
    L.append("")
    L.append("## 四、下一步\n")
    L.append("- 漏镜？调小 `--cut-thresh`（当前样本见 json 的 `cut_candidates`）重扫，")
    L.append("  或对存疑时间段用 `frame-extract --times \"a,b,c\"` 定点补帧肉眼复核")
    L.append("- 台词错字？把正确专有名词写进 `--prompt` 重跑；纯音乐素材加 `--music`")
    L.append("- 本表是《镜头分解.md》的**输入**：镜头段落已切好，逐段 Read 代表帧填人物/服装/动作/镜头语言\n")
    Path(path).write_text("\n".join(L), encoding="utf-8")


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--model", default="whisper-1")
    ap.add_argument("--prompt", help="引导专有名词/人名写法；音乐素材不要传")
    ap.add_argument("--music", action="store_true",
                    help="音源是纯音乐：强制不传 prompt 且按 10s 切段，防幻觉歌词")
    ap.add_argument("--scan-fps", type=float, default=4.0)
    ap.add_argument("--cut-thresh", type=float, default=0.42)
    ap.add_argument("--min-shot", type=float, default=0.5)
    ap.add_argument("--chunk", type=float, default=600.0, help="ASR 单段秒数上限")
    ap.add_argument("--granularity", choices=["word", "segment", "none"], default="word",
                    help="word=词级时间戳（默认，精度高）；segment=段级（会被 5s 吸附）")
    ap.add_argument("--utt-gap", type=float, default=0.35,
                    help="句间静音超过多少秒就断句（词级模式用）")
    ap.add_argument("--max-frames", type=int, default=80)
    ap.add_argument("--no-asr", action="store_true")
    a = ap.parse_args()

    def log(m):
        print(m, flush=True)

    video = Path(a.video)
    if not video.exists():
        log(f"找不到视频: {video}")
        return 2
    out = Path(a.out_dir)
    frames_dir = out / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    note = ""
    info = probe(video)
    log(f"[元信息] {info['w']}x{info['h']} {info['fps']:.3f}fps "
        f"{info['frames']}帧 {info['duration']:.2f}s")

    ffmpeg = find_ffmpeg()
    log(f"[ffmpeg] {ffmpeg}")

    # --- 音轨 ---
    wav = None
    events, segs = [], []
    if ffmpeg:
        try:
            wav = extract_wav(ffmpeg, video, out / "audio16k.wav")
            log(f"[音轨] {wav.name} "
                f"({Path(wav).stat().st_size/1e6:.2f} MB)")
            events = audio_events(wav)
            log(f"[包络] {len(events)} 个声音区段")
        except Exception as e:
            note = f"抽音轨失败（{e}），本次只做画面轴"
            log("[音轨] " + note)
    else:
        note = "找不到 ffmpeg，本次只做画面轴"
        log("[音轨] " + note)

    # --- 转写 ---
    if wav and not a.no_asr:
        prompt = None if a.music else a.prompt
        chunk = 10.0 if a.music else a.chunk
        if a.music:
            log("[转写] music 模式：不传 prompt + 10s 切段（防幻觉歌词）")
        try:
            segs = asr_segments(wav, out, a.lang, prompt, a.model, chunk, log,
                                utt_gap=a.utt_gap, granularity=a.granularity)
            log(f"[转写] {len(segs)} 句（粒度 {a.granularity}）")
        except Exception as e:
            note = (note + " / " if note else "") + f"转写失败：{e}"
            log("[转写] 失败: " + str(e))
    elif a.no_asr:
        log("[转写] --no-asr，跳过")

    # --- 场景切分 ---
    shots, top = scan_shots(video, info, a.scan_fps, a.cut_thresh, a.min_shot, log)
    log(f"[切镜] {len(shots)} 个镜头（阈值 {a.cut_thresh}）")

    # --- 抽帧 ---
    files = grab_frames(video, info, shots, segs, frames_dir, a.max_frames, log)
    sheet = contact_sheet(files, out / "联系表.jpg") if files else None

    # --- 合并 ---
    merge(shots, segs, events)
    data = {
        "video": str(video), "spec": info, "out_dir": str(out),
        "shot_count": len(shots), "dialogue_count": len(segs),
        "cut_thresh": a.cut_thresh, "scan_fps": a.scan_fps,
        "cut_candidates": [{"t": t, "score": s} for t, s in top],
        "shots": shots,
        "dialogue": [{"start": s, "end": e, "text": t} for s, e, t in segs],
        "audio_events": events,
        "note": note,
    }
    (out / "av_align.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    md = out / "音画对齐表.md"
    write_md(md, str(video), info, shots, segs, events, ffmpeg, note)
    if sheet:
        log(f"[联系表] {sheet}")

    log("")
    log(f"[完成] 镜头 {len(shots)} / 台词 {len(segs)} 句 / 声音区段 {len(events)}")
    if top:
        log("[切镜候选分] " + ", ".join(f"{t:.2f}s:{s:.2f}" for t, s in top[:6]))
        log("  -> 若明显漏镜，把 --cut-thresh 调小到候选分之下重跑")
    log(f"[输出] {md}")
    log(f"[输出] {out / 'av_align.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

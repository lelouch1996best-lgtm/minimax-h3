# -*- coding: utf-8 -*-
"""Rebuild the campus MV against the new BGM (bgm.mp3, 188s) — no subtitles.

Strategy (learned from v1):
  * v1 issues: `-filter_complex_script` is broken in ffmpeg 7.1, xfade is unstable
    on long concat chains, and Chinese paths break script files.
  * v2 fixes: render each clip separately into an ASCII-path work dir, then stitch
    with the concat demuxer (no giant filtergraph at all), transitions done as
    white dips inside each clip.
"""
import os, subprocess, sys, math, json, shutil

FF = r"C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
VID_DIR = r"D:\work\minimax_h3\漂亮的恶意复刻\video"
BGM = os.path.join(VID_DIR, "bgm.mp3")
WORK = r"C:\Users\Administrator\AppData\Local\Temp\mv_v2"   # ASCII path, avoids CN-path bugs
SRC_CACHE = os.path.join(VID_DIR, "mv_build")               # reuse v1 rendered clips? no, re-render
os.makedirs(WORK, exist_ok=True)

BGM_START = 20.0          # skip the 20s intro
FPS = 24
W, H = 1280, 720

# ---------------------------------------------------------------- sources
S = {}
for f in os.listdir(VID_DIR):
    if f.endswith(".mp4") and not f.startswith("漂亮的恶意_"):
        parts = f[:-4].split("_")
        key = parts[-2] if f.startswith("learned") else parts[1]
        S[key] = os.path.join(VID_DIR, f)

def src(prefix):
    for k, v in S.items():
        if prefix in k:
            return v
    raise KeyError(prefix)

E01 = src("黄枫学院"); E02 = src("转学生来了"); E03 = src("第一集"); E04 = src("玄骨")
ixpbi = src("ixpbi"); jumzi = src("jumzi"); tqdjx = src("tqdjx"); jmexs = src("jmexs")
llavc = src("llavc"); yzuzq = src("yzuzq"); qhmbt = src("qhmbt"); mtykz = src("mtykz")
qgdmp = src("qgdmp"); aypdy = src("aypdy"); sqfme = src("sqfme"); veebe = src("veebe")
tdoje = src("tdoje"); aklnt = src("aklnt"); ixknq = src("ixknq")

# ---------------------------------------------------------------- 30-shot edit
# (source, in-point, duration, chapter-boundary-after?)
SEGS = [
    # ---- ACT 1 校园日常 (shots 1-7) ----
    (E01,    0.3, 6.2, 0),   # 01 校门开场
    (sqfme,  1.5, 5.6, 0),   # 02 白鸽樱花窗
    (mtykz,  0.8, 5.6, 0),   # 03 图书馆金光梯
    (llavc,  3.8, 5.4, 0),   # 04 炸鸡日落
    (jumzi,  4.1, 5.6, 0),   # 05 楼梯书本翻倒
    (qgdmp,  8.8, 5.6, 0),   # 06 三女生课桌笑
    (jmexs,  4.5, 5.6, 1),   # 07 粉色信纸特写  << chapter
    # ---- ACT 2 心动信号 (shots 8-15) ----
    (ixknq,  8.8, 5.4, 0),   # 08 白板男生
    (tqdjx,  0.3, 5.4, 0),   # 09 教室挂灯笼
    (aypdy,  0.3, 5.4, 0),   # 10 篮球扣篮
    (aklnt,  4.6, 5.4, 0),   # 11 咖啡厅服务生
    (ixknq,  4.2, 5.4, 0),   # 12 走廊奔跑
    (tdoje,  4.0, 5.8, 0),   # 13 雨夜共伞
    (yzuzq,  9.2, 5.4, 0),   # 14 窗边自习
    (qgdmp,  4.2, 5.4, 1),   # 15 黑板面纱微笑  << chapter
    # ---- ACT 3 暗流涌动 (shots 16-23) ----
    (jmexs,  9.0, 5.4, 0),   # 16 面纱三女走廊
    (veebe,  0.3, 5.8, 0),   # 17 深夜储物柜
    (qhmbt,  0.3, 5.8, 0),   # 18 天台牵手
    (qhmbt,  8.6, 5.8, 0),   # 19 雨中泪光
    (ixpbi,  8.4, 5.8, 0),   # 20 夜景天台对峙
    (E02,    4.5, 5.8, 0),   # 21 客厅对峙
    (E02,    9.3, 5.4, 0),   # 22 转学生特写
    (E03,    0.5, 5.6, 1),   # 23 第一集开场    << chapter
    # ---- ACT 4 真相浮现 (shots 24-30) ----
    (E04,    1.0, 5.6, 0),   # 24 玄骨
    (E04,    8.7, 5.6, 0),   # 25 玄骨书卡
    (E03,    7.6, 5.4, 0),   # 26 大理石厅少女
    (mtykz,  8.5, 5.4, 0),   # 27 图书馆另一时刻
    (sqfme,  9.0, 5.4, 0),   # 28 樱花窗另一时刻
    (jumzi,  9.5, 5.4, 0),   # 29 楼梯另一时刻
    (E01,    8.6, 6.2, 0),   # 30 结尾校门特写
]
n = len(SEGS)
total = sum(s[2] for s in SEGS)
print("shots: %d   total: %.2f s" % (n, total))

# ---------------------------------------------------------------- onsets for snapping
def onsets():
    import struct
    SR = 22050
    raw = subprocess.run([FF, "-loglevel", "error", "-i", BGM, "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True).stdout
    N = len(raw) // 4
    x = struct.unpack("<%df" % N, raw[:N * 4])
    hop = 512
    m = N // hop
    env = []
    for i in range(m):
        s = 0.0
        for j in range(i * hop, (i + 1) * hop, 4):
            s += x[j] * x[j]
        env.append(math.sqrt(s / (hop / 4)))
    flux = [max(0.0, env[i] - env[i - 1]) for i in range(1, m)]
    sm = [sum(flux[max(0, i - 2):i + 3]) / 5 for i in range(len(flux))]
    thr = sorted(sm)[int(len(sm) * 0.80)] * 1.25
    pk = []
    for i in range(2, len(sm) - 2):
        t = i * hop / SR
        if sm[i] > thr and sm[i] >= sm[i - 1] and sm[i] >= sm[i + 1]:
            if pk and t - pk[-1] < 0.28:
                continue
            pk.append(t)
    return pk

beats = onsets()
print("onsets detected: %d" % len(beats))

bounds, t = [], 0.0
for _, _, d, _ in SEGS:
    bounds.append(t)
    t += d
snapped = 0
for i in range(1, n):
    if SEGS[i - 1][3] != 1:      # only snap at chapter boundaries
        continue
    b = bounds[i]
    cand = [x for x in beats if abs(x - b) <= 0.45]
    if cand:
        bounds[i] = min(cand, key=lambda x: abs(x - b))
        snapped += 1
print("chapter boundaries snapped: %d" % snapped)

durs = [((bounds[i + 1] if i + 1 < n else total) - bounds[i]) for i in range(n)]
for i in range(n):
    in_pt, d = SEGS[i][1], durs[i]
    if in_pt + d > 14.90:          # auto clamp: pull the in-point back
        new_in = max(0.0, 14.90 - d)
        print("  clamp shot %d in-point %.2f -> %.2f (needs %.2f)" % (i, in_pt, new_in, in_pt + d))
        SEGS[i] = (SEGS[i][0], new_in, SEGS[i][2], SEGS[i][3])
        in_pt = new_in
    assert in_pt + d <= 14.98, "shot %d still overruns source (%.2f)" % (i, in_pt + d)
print("video total: %.2f s" % sum(durs))

# ---------------------------------------------------------------- palette (Korean fresh)
def base_chain():
    return ("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,fps=%d,"
            "eq=brightness=0.045:saturation=1.13:contrast=0.93:gamma=1.03,"
            "colorbalance=rs=.02:bs=.06:rm=-.02:bm=.03:rh=.04:bh=-.03,"
            "split[a][b];[b]gblur=sigma=10[bb];[a][bb]blend=all_mode=screen:all_opacity=0.11"
            % (W, H, W, H, FPS))

# ---------------------------------------------------------------- pass 1 : render clips
print("\npass 1: rendering %d clips ->" % n)
for i in range(n):
    f, in_pt, _, _ = SEGS[i]
    d = durs[i]
    vf = base_chain()
    fi, fo = 0.0, 0.0
    if i == 0:
        fi = 1.4                                     # cold open from white
    if i == n - 1:
        fo = 2.6                                     # final fade to white
    if i >= 1 and SEGS[i - 1][3] == 1:               # chapter: dip in from white
        fi = max(fi, 0.50)
    if SEGS[i][3] == 1:                              # chapter: dip out to white
        fo = max(fo, 0.50)
    if fi > 0:
        vf += ",fade=t=in:st=0:d=%.2f:color=white" % fi
    if fo > 0:
        vf += ",fade=t=out:st=%.2f:d=%.2f:color=white" % (d - fo, fo)
    vf += ",format=yuv420p"
    outp = os.path.join(WORK, "c%02d.mp4" % i)
    cmd = [FF, "-y", "-loglevel", "error",
           "-ss", "%.3f" % in_pt, "-t", "%.3f" % d, "-i", f,
           "-vf", vf, "-an",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "17",
           "-r", str(FPS), "-video_track_timescale", "24000",
           outp]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("FAIL clip %d: %s" % (i, r.stderr[-600:])); sys.exit(1)
    print("  c%02d  %-14s in=%5.2f  dur=%4.2f%s"
          % (i, os.path.basename(f)[:14], in_pt, d,
             "   <<chapter" if SEGS[i][3] else ""))

# ---------------------------------------------------------------- pass 2 : stitch + audio
listf = os.path.join(WORK, "concat.txt")
with open(listf, "w", encoding="utf-8") as fh:
    for i in range(n):
        fh.write("file '%s'\n" % os.path.join(WORK, "c%02d.mp4" % i).replace("\\", "/"))

vtotal = sum(durs)
bgm_end = BGM_START + vtotal
out = os.path.join(VID_DIR, "漂亮的恶意_校园MV_2.mp4")
af = ("atrim=%.3f:%.3f,asetpts=PTS-STARTPTS,"
      "afade=t=in:st=0:d=0.7,"
      "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,"
      "afade=t=out:st=%.2f:d=2.6") % (BGM_START, bgm_end, vtotal - 2.6)

cmd = [FF, "-y", "-loglevel", "error",
       "-f", "concat", "-safe", "0", "-i", listf,
       "-i", BGM,
       "-map", "0:v", "-map", "1:a",
       "-af", af,
       "-c:v", "libx264", "-preset", "medium", "-crf", "18",
       "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "192k",
       "-shortest", "-movflags", "+faststart", out]

print("\npass 2: stitching %d clips + audio (BGM %.1f -> %.1f s)..." % (n, BGM_START, bgm_end))
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode != 0:
    print("FAIL stitch:", r.stderr[-1500:]); sys.exit(1)

json.dump({"shots": n, "total": vtotal, "durs": durs, "bounds": bounds,
           "bgm_start": BGM_START, "bgm_end": bgm_end},
          open(os.path.join(WORK, "timeline_v2.json"), "w"))
print("DONE ->", out)
print("length: %.2f s" % vtotal)

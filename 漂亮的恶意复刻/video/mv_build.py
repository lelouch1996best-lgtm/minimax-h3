# -*- coding: utf-8 -*-
"""Build a 2-3 min K-style campus music MV from local clips."""
import os, subprocess, sys, math, json

FF = r"C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
VID_DIR = r"D:\work\minimax_h3\漂亮的恶意复刻\video"
OUT_DIR = os.path.join(VID_DIR, "mv_build")
BGM = os.path.join(os.environ.get("TMP", "/tmp"), "bgm_kpop.mp3")
FONT = "C\\:/Windows/Fonts/msyhbd.ttc"
os.makedirs(OUT_DIR, exist_ok=True)

# ---------- sources ----------
S = {}
for f in os.listdir(VID_DIR):
    if f.endswith(".mp4"):
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

# ---------- timeline: (source, start, dur, transition_to_next) ----------
# transition: 'cut' (hard) or 'fade' (0.5s xfade, chapter boundary)
SEGS = [
    # ACT1 校园日常 ~53.8s
    (E01,   0.3,  9.7, "fade"),   # 1 开场 校门+标题
    (sqfme, 5.4,  6.2, "cut"),    # 2 白鸽与樱花窗
    (mtykz, 0.3,  6.4, "cut"),    # 3 图书馆金光梯
    (llavc, 3.8,  6.8, "cut"),    # 4 炸鸡日落
    (jumzi, 4.1,  6.6, "cut"),    # 5 楼梯书本翻倒
    (qgdmp, 9.0,  6.0, "cut"),    # 6 三女生课桌笑
    (jmexs, 4.5,  6.1, "cut"),    # 7 粉色信纸特写
    (ixknq, 9.0,  6.0, "fade"),   # 8 白板男生
    # ACT2 心动信号 ~45.3s
    (tqdjx, 0.3,  5.6, "cut"),    # 9 教室挂灯笼
    (aypdy, 0.3,  5.4, "cut"),    # 10 篮球扣篮
    (aklnt, 4.6,  5.6, "cut"),    # 11 咖啡厅服务生
    (ixknq, 4.4,  5.6, "cut"),    # 12 走廊奔跑
    (tdoje, 4.2,  6.6, "cut"),    # 13 雨夜共伞
    (yzuzq, 9.4,  5.6, "cut"),    # 14 窗边自习
    (qgdmp, 4.4,  5.4, "cut"),    # 15 黑板前面纱微笑
    (jmexs, 9.0,  5.5, "fade"),   # 16 面纱三女走廊
    # ACT3 暗流涌动 ~32.0s
    (veebe, 0.3,  6.3, "fade"),   # 17 深夜储物柜
    (qhmbt, 0.3,  6.3, "cut"),    # 18 天台牵手
    (qhmbt, 8.6,  6.4, "cut"),    # 19 雨中泪光
    (ixpbi, 8.6,  6.3, "cut"),    # 20 夜景天台对峙
    (E02,   4.5,  6.7, "fade"),   # 21 客厅对峙
    # ACT4 真相浮现 ~16.2s
    (E04,   8.7,  5.5, "cut"),    # 22 玄骨书卡
    (E03,   7.6,  5.5, "cut"),    # 23 大理石厅少女
    (E01,   9.8,  5.2, "cut"),    # 24 结尾校门特写
]
TOTAL = sum(s[2] for s in SEGS)  # 147.3s pre-xfade -> ~145.8s after 3 xfades

# ---------- beat/onset detection ----------
def onsets():
    import array, struct
    SR = 22050
    cmd = [FF, "-loglevel", "error", "-i", BGM, "-ac", "1", "-ar", str(SR),
           "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    n = len(raw) // 4
    x = struct.unpack("<%df" % n, raw[: n * 4])
    hop = 512  # ~23ms
    m = n // hop
    e = [0.0] * m
    for i in range(m):
        s = 0.0
        for j in range(i * hop, (i + 1) * hop, 8):
            s += x[j] * x[j]
        e[i] = math.sqrt(s / (hop / 8))
    flux = [max(0.0, e[i] - e[i - 1]) for i in range(1, m)]
    # smooth
    sm = [sum(flux[max(0, i - 2): i + 3]) / 5 for i in range(len(flux))]
    thr = sorted(sm)[int(len(sm) * 0.75)] * 1.4
    peaks = []
    t0 = 1.0  # skip intro silence-ish
    for i in range(2, len(sm) - 2):
        t = i * hop / SR
        if sm[i] > thr and sm[i] >= sm[i - 1] and sm[i] >= sm[i + 1] and t >= t0:
            if peaks and t - peaks[-1][0] < 0.30:
                if sm[i] > peaks[-1][1]:
                    peaks[-1] = (t, sm[i])
            else:
                peaks.append((t, sm[i]))
    return [p[0] for p in peaks]

try:
    beats = onsets()
    print("onsets:", len(beats))
except Exception as ex:
    print("onset detect failed:", ex)
    beats = []

# ---------- snap hard-cut boundaries to onsets ----------
bounds = []  # absolute start times of each segment
t = 0.0
for _, _, d, _ in SEGS:
    bounds.append(t)
    t += d
n = len(SEGS)
abs_end = [bounds[i] + SEGS[i][2] for i in range(n)]
snapped = 0
for i in range(1, n):
    if SEGS[i - 1][3] != "cut":
        continue
    b = bounds[i]
    cand = [x for x in beats if abs(x - b) <= 0.45]
    if not cand:
        continue
    nb = min(cand, key=lambda x: abs(x - b))
    dprev = nb - bounds[i - 1]
    dnext = bounds[i + 1] - nb if i + 1 < n else (TOTAL - nb)
    start_i, start_next = SEGS[i][1], SEGS[i + 1][1] if i + 1 < n else 0
    if 3.5 <= dprev <= 14.9 - SEGS[i - 1][1] and 3.5 <= dnext <= 14.9 - start_next:
        bounds[i] = nb
        snapped += 1
print("snapped boundaries:", snapped)

# repair: clamp every segment inside its source duration (iterative)
for _ in range(6):
    changed = False
    for i in range(n):
        d = (bounds[i + 1] if i + 1 < n else TOTAL) - bounds[i]
        if SEGS[i][1] + d > 14.95:
            excess = SEGS[i][1] + d - 14.95
            if i + 1 < n:
                bounds[i + 1] -= excess
            else:
                TOTAL -= excess
            changed = True
        elif d < 3.0 and i + 1 < n:
            bounds[i + 1] = bounds[i] + 3.0
            changed = True
    if not changed:
        break

durs = []
for i in range(n):
    durs.append((bounds[i + 1] if i + 1 < n else TOTAL) - bounds[i])
for i in range(n):
    end = SEGS[i][1] + durs[i]
    assert end <= 15.05, (i, end)

# ---------- pass 1: render graded segments ----------
def grade_chain(extra=""):
    g = ("scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,fps=24,"
         "eq=brightness=0.045:saturation=1.14:contrast=0.92:gamma=1.03,"
         "colorbalance=rs=.02:bs=.06:rm=-.02:bm=.03:rh=.04:bh=-.03,"
         "split[a][b];[b]gblur=sigma=10[bb];[a][bb]blend=all_mode=screen:all_opacity=0.12,"
         "format=yuv420p" + extra)
    return g

for i in range(n):
    f, st, _, _ = SEGS[i]
    d = durs[i]
    outp = os.path.join(OUT_DIR, "seg_%02d.mp4" % i)
    if os.path.exists(outp) and abs(os.path.getmtime(outp) - os.path.getmtime(f)) < 5:
        pass
    vf = grade_chain()
    # white fade for opening / ending
    if i == 0:
        vf += ",fade=t=in:st=0:d=1.2:color=white"
    if i == n - 1:
        vf += ",fade=t=out:st=%.2f:d=2.0:color=white" % (d - 2.0)
    # white-dip transitions at chapter boundaries
    if i >= 1 and SEGS[i - 1][3] == "fade":
        vf += ",fade=t=in:st=0:d=0.5:color=white"
    if i < n - 1 and SEGS[i][3] == "fade":
        vf += ",fade=t=out:st=%.2f:d=0.5:color=white" % (d - 0.5)
    cmd = [FF, "-y", "-loglevel", "error", "-ss", "%.2f" % st, "-t", "%.2f" % d,
           "-i", f, "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "17", outp]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("FAIL seg", i, r.stderr[-500:]); sys.exit(1)
    print("seg %02d ok  src=%s start=%.2f dur=%.2f" % (i, os.path.basename(f), st, d))

# ---------- pass 2: assemble with xfade/concat + titles + audio ----------
ins = []
for i in range(n):
    ins += ["-i", os.path.join(OUT_DIR, "seg_%02d.mp4" % i)]
ins += ["-i", BGM]

# chapter dips consume no overlap; shorten last segment to match BGM length
durs[n - 1] -= 1.5

# compute real boundary times on final timeline (pure concat, no overlap)
tl = 0.0
tl_bounds = []  # timeline time where segment i starts
for i in range(n):
    tl_bounds.append(tl)
    tl += durs[i]
final_len = tl
print("final length:", round(final_len, 2))

fc = []
# normalize timebase & pts for every segment input (xfade requires matching tb)
for i in range(n):
    fc.append("[%d:v]settb=AVTB,fps=24,setpts=PTS-STARTPTS[n%d]" % (i, i))
prev = "[n0]"
fc.append("".join("[n%d]" % i for i in range(n)) + "concat=n=%d:v=1:a=0[vout]" % n)

# ---------- drawtext helper ----------
def dt(text, t0, t1, size, y, alpha=0.92, color="white"):
    alpha = float(alpha)
    return ("drawtext=fontfile='%s':text='%s':fontsize=%d:fontcolor=%s:"
            "x=(w-text_w)/2:y=%d:shadowx=2:shadowy=3:shadowcolor=black@0.55:"
            "alpha='if(lt(t,%d),0,if(lt(t,%d),(t-%d)/0.8,if(lt(t,%d),%.2f,"
            "if(lt(t,%d),%.2f*(%d-t)/0.8,0))))'"
            % (FONT, text, size, color, y, t0, t0 + 0.8, t0, t1 - 0.8, alpha,
               t1, alpha, t1))

# ---------- stage A: join segments ----------
joined = os.path.join(OUT_DIR, "joined.mp4")
cmdA = ([FF, "-y", "-loglevel", "error"] + ins +
        ["-filter_complex", ";".join(fc), "-map", "[vout]",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
         "-an", joined])
print("stage A: joining...")
r = subprocess.run(cmdA, capture_output=True, text=True)
if r.returncode != 0:
    print("FAIL stage A:", r.stderr); sys.exit(1)

# ---------- stage B: titles + audio ----------
b8 = tl_bounds[8]     # ACT2 start
b16 = tl_bounds[16]   # ACT3 start
b21 = tl_bounds[21]   # ACT4 start
vf = ",".join([
    dt("漂亮的恶意", 1.2, 8.6, 120, 260, alpha=1.0),
    dt("PRETTY MALICE · 校园音乐特辑", 1.8, 8.6, 34, 420, alpha=0.95),
    dt("第一章 · 新学期", tl_bounds[1] + 2, b8 - 2, 30, 640),
    dt("第二章 · 心动信号", b8 + 3, b16 - 2, 30, 640),
    dt("第三章 · 暗流涌动", b16 + 3, b21 - 2, 30, 640),
    dt("第四章 · 真相浮现", b21 + 3, b21 + 8, 30, 640),
    dt("漂亮的恶意 · 完", final_len - 4.6, final_len - 0.5, 76, 300, alpha=1.0),
    dt("BGM · Korea Korean Pop Music — HitsLab (Pixabay)", final_len - 4.4,
       final_len - 0.5, 26, 420, alpha=0.9),
    "format=yuv420p",
])
af = ("atrim=0:%.2f,afade=t=in:st=0:d=0.5,"
      "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,"
      "afade=t=out:st=%.2f:d=2.4" % (final_len, final_len - 2.4))

out = os.path.join(VID_DIR, "漂亮的恶意_校园MV_Kpop.mp4")
cmdB = ([FF, "-y", "-loglevel", "error", "-i", joined, "-i", BGM,
         "-vf", vf, "-af", af,
         "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-c:a", "aac", "-b:a", "192k",
         "-shortest", "-movflags", "+faststart", out])

print("stage B: titles + audio...")
r = subprocess.run(cmdB, capture_output=True, text=True)
if r.returncode != 0:
    print("FAIL stage B:", r.stderr[-1500:]); sys.exit(1)
print("DONE:", out, round(final_len, 2), "s")
json.dump({"final_len": final_len, "tl_bounds": tl_bounds, "durs": durs},
          open(os.path.join(OUT_DIR, "timeline.json"), "w"))

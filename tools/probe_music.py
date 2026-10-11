#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_music.py — 粗测音频：BPM、时长、能量分段（用于写词卡结构）。"""
import sys
import wave
import numpy as np
from pathlib import Path

src = Path(sys.argv[1])
FF = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
pcm = src.with_suffix(".probe.wav")
import subprocess
subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
                "-ac", "1", "-ar", "22050", str(pcm)], check=True)

with wave.open(str(pcm)) as w:
    sr = w.getframerate()
    n = w.getnframes()
    x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
dur = n / sr
print(f"duration {dur:.2f}s  sr {sr}")

# 简易 BPM：自相关，限定 60-180
hop = 512
frames = x[: (len(x) // hop) * hop].reshape(-1, hop)
env = np.sqrt((frames ** 2).mean(axis=1) + 1e-9)
on = env > np.percentile(env, 55)
sr_e = sr / hop
lo, hi = int(60 / 60 * sr_e), int(180 / 60 * sr_e)
ac = np.correlate(env - env.mean(), env - env.mean(), mode="full")[len(env) - 1:]
cands = []
for k in range(max(1, lo), min(len(ac), hi)):
    if ac[k] > ac[k - 1] and ac[k] >= ac[k + 1]:
        cands.append((ac[k], k))
cands.sort(reverse=True)
tops = cands[:5]
seen = []
for v, k in tops:
    bpm = 60 * sr_e / k
    if all(abs(bpm - s) > 4 for s in seen):
        seen.append(bpm)
print("BPM candidates:", [round(b, 1) for b in seen[:3]])

# 分段能量，看 intro/verse/chorus 结构
win = int(sr * 2)
nwin = int(dur // 2)
rows = []
for i in range(nwin):
    seg = x[i * win:(i + 1) * win]
    if len(seg) == 0:
        break
    rms = float(np.sqrt((seg ** 2).mean() + 1e-9))
    zcr = float((np.diff(np.sign(seg)) != 0).mean())
    rows.append((i * 2, rms, zcr))
mx = max(r[1] for r in rows) or 1
print("\n t(s)   rms%  zcr")
line = ""
for t, r, z in rows:
    bar = "#" * int(r / mx * 40)
    line += f"{t:4d} {r/mx*100:5.1f} {z:5.2f} {bar}\n"
print(line)
pcm.unlink(missing_ok=True)

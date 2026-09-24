# Step 5B 细则 · 多段合成与统一 BGM

**触发**：仅当同一剧本需要两段以上视频组合时执行（`E{NN}A`/`E{NN}B` 段目录，或多段拼成一集）。单片集一律不走：原生成片即成品，不混 BGM、不产 `E{NN}.mp4`、不登记曲库。拆片合并件即本集唯一正片、占基号 E{NN}。

完整版 ffmpeg：`python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"`（系统 PATH 精简版缺 aac 编码器与 jpg 编码器）。

## 5B.1 拼接视频

同批次段（编码/分辨率/帧率一致）优先 concat 流拷贝：

```powershell
# list.txt 每行一条：file '<段绝对路径>'（剧情顺序，UTF-8 无 BOM）
& <完整版ffmpeg> -f concat -safe 0 -i list.txt -c copy "<合集目录>\video\E{NN}_拼接.mp4"
```

流拷贝失败（时间戳/参数不一致）转码统一：`-c:v libx264 -crf 18 -c:a aac`，分辨率以实际出片为准。拼接后 ffprobe 核验总时长 ≈ 各段之和、音视频流齐全。

## 5B.2 选 BGM（先曲库后生成）

1. 读 `d:\work\minimax_h3\assets\bgm\BGM曲库.md`（不存在视为空库，走 5B.3）
2. 按本集情绪/氛围匹配「风格/情绪标签」（撒娇温馨/调皮玩梗/吃醋/好奇兴奋/心疼软萌/吃瓜/傲娇小得瑟，叠加闺房暖光/月夜等场景词）
3. 有候选：列出候选（文件/标签/时长/使用记录）请用户拍板；无人介入取标签最贴合且使用次数最少的一条
4. 无候选：走 5B.3
5. 曲库曲长不足：优先换更长候选；确需短曲在 5B.4 用 `aloop=loop=-1:size=2e9` 循环铺满
6. 未入曲库的旧 BGM 缺生成元数据，确需复用先补登记

## 5B.3 get-music 生成

经 `get-music` 技能（APIMart，需 `APIMART_API_KEY`；base url `https://api.apib.ai/v1`，国内可直连）。一律固化脚本，不裸拼 HTTP：

```powershell
python d:\work\minimax_h3\tools\new_music.py `
  --title "bgm_<风格>_<情绪>_<序号>" `
  --prompt "<英文提示词，以 instrumental, no vocals 结尾>" `
  --bpm <按情绪> --length <视频总时长±5s> `
  --out "d:\work\minimax_h3\assets\bgm" --trim <视频总时长>
```

- 风格锚点：国风甜妹向轻音乐（古筝/竹笛/木吉他/尤克里里+轻打击，如 `playful sweet Chinese guzheng and acoustic guitar, light percussion, warm gentle, 100 bpm, instrumental, no vocals`）
- 情绪 → BPM：温馨撒娇 70—90、明快调皮 100—120、吃瓜好奇 90—110
- 序号＝曲库同前缀最大序号 +1；`--trim` 截时长并加淡入淡出，产 m4a + wav（混音用 m4a）
- **提交失败勿重发 POST（重复扣费）**，用 `--query <task_id>` 幂等补查补下载；`<标题>.result.json` 移入本集 `任务记录\`，封面图即用即删

## 5B.4 混音合成

`tools/concat_and_mix.py` 已固化（5B.1+5B.4 一条命令）：

```powershell
python d:\work\minimax_h3\tools\concat_and_mix.py `
  --segs "<段1>" "<段2>" ["<段3>"] `
  --bgm "d:\work\minimax_h3\assets\bgm\<曲>.m4a" `
  --out "<合集目录>\video\E{NN}.mp4" `
  --rec-dir "<合集目录>\任务记录"
```

参数：`--bgm-volume 0.25`（默认）、`--fade-in 0.5`、`--fade-out 1.6`、`--no-summary`。流程：concat 流拷贝（失败转 libx264 crf18）→ BGM 短于成片时 aloop 循环铺满 → 垫底混音 → ffprobe/volumedetect 校验 → `merge_summary.json`。

手工兜底滤镜（单片例外混音或脚本不可用时）：

```powershell
& <完整版ffmpeg> -i "<输入视频>" -i "<bgm>.m4a" `
  -filter_complex "[1:a]volume=0.25[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=0[a]" `
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k `
  "<输出>.mp4"
```

- 产出统一命名 **`E{NN}.mp4`**，落合集目录 `video\`（单片例外经用户书面批准才混音产出，台账注明）
- BGM 音量 0.2—0.3（人声环境音为主、垫底）；`duration=first` 不超时
- 复用曲库且曲长超出：先 `--trim` 重截或滤镜补 afade
- 混音后校验：ffprobe 确认音轨非静音；发布用件＝拆片合集用 `E{NN}.mp4`，单片用原生成片

## 5B.5 登记曲库（必做）

`assets\bgm\` 与 `BGM曲库.md` 不存在时创建：

```markdown
# BGM 曲库（全局共享，跨剧集复用）

| 文件 | 风格/情绪标签 | BPM | 时长 | 来源 | 生成提示词 | 首次用于 | 使用记录 |
|---|---|---|---|---|---|---|---|
```

- 新生成：追加一行（文件名、标签、BPM、时长、来源＝模型+task_id、**生成提示词原文**、首次用于、使用记录）
- 复用已有：仅「使用记录」列追加集号
- 本集台账同步注明合成版路径、BGM 文件与来源（曲库复用/新生成+task_id）

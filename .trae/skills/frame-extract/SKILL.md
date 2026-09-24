---
name: "frame-extract"
description: "视频抽帧（核验/反推动作/取尾帧/联系表）的统一入口，直接用 Python+OpenCV 抽帧，不尝试 ffmpeg。Invoke when 需要从 mp4 抽帧、成片抽帧核验、截取尾帧/首帧、生成 contact sheet，或其他技能（h3-drama-producer 等）提到抽帧时。"
---

# 视频抽帧（OpenCV 专用）

从视频中抽取静态帧，用于成片质量核验、反推参考片动作、取集间衔接尾帧、生成联系表。

## 触发条件

- 用户或其他技能要求"抽帧""提帧""截帧""看几帧画面""抽帧核验"
- 需要取视频首帧/尾帧/指定时刻画面（衔接帧、封面候选）
- 需要把多个时刻拼成一张 contact sheet（联系表）减少读图次数

## 核心规则：只用 OpenCV，不碰 ffmpeg

**本机 PATH 上的 ffmpeg 是精简版，没有 image2 muxer，无法输出图片帧**；先试 ffmpeg 再回退 OpenCV 每次都要浪费多轮探测与报错。因此：

- 抽帧一律直接用本技能自带脚本 `scripts\extract_frames.py`（Python + cv2）
- **禁止先尝试 `ffmpeg` 命令抽帧**；也不要现写临时 cv2 脚本——本脚本已覆盖全部常用场景
- ffmpeg 仅用于"视频流拷贝拼接/截段重封装"等非抽帧用途，不在本技能范围

依赖：Python 3 + `opencv-python`（本机已装 cv2 4.x）。缺包时 `pip install opencv-python`。

## 使用方式

脚本路径：`d:\work\minimax_h3\.trae\skills\frame-extract\scripts\extract_frames.py`

### 1. 均匀抽帧（默认，成片核验/动作反推）

```powershell
python "d:\work\minimax_h3\.trae\skills\frame-extract\scripts\extract_frames.py" `
  --video "<视频.mp4>" --out "<输出目录>" --count 5
```

- `--count N`：在全片均匀取 N 个时刻（默认 5），自动包含首帧与尾帧附近
- `--interval S`：与 `--count` 二选一，按固定秒数间隔抽（如 `--interval 1` = 每秒一帧）
- 适合：10s 成片核验取 5 帧（约 0/2.5/5/7.5/尾）、参考片 1fps 反推动作

### 2. 指定时刻抽帧

```powershell
python "...\extract_frames.py" --video "<视频.mp4>" --out "<目录>" `
  --times 0,2.5,5,8
```

- `--times`：逗号分隔的秒数，文件名按时刻命名（`t00.0s.jpg`、`t02.5s.jpg`）

### 3. 取尾帧 / 首帧（集间衔接、封面）

```powershell
# 尾帧（方案 B 衔接集首帧）
python "...\extract_frames.py" --video "<前一集.mp4>" --out "<目录>" --last
# 首帧
python "...\extract_frames.py" --video "<视频.mp4>" --out "<目录>" --first
```

- 默认输出 jpg；加 `--png` 输出 png（衔接帧建议 png 无损）
- 可配 `--name E01-E02` 指定文件名

### 4. 联系表（多帧拼一张，省读图）

```powershell
python "...\extract_frames.py" --video "<视频.mp4>" --out "<目录>" `
  --sheet --count 6 --cols 3
```

- `--sheet`：把抽到的帧缩放后拼成一张 contact sheet（`contact_sheet.jpg`），帧上标注时刻
- 抽帧核验时优先用联系表：1 张图替代多次 Read
- `--sheet-width` 控制单帧缩略宽（默认 360）

## 通用参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `--video` | 必填 | 源视频路径 |
| `--out` | 必填 | 输出目录（自动创建） |
| `--count N` | 5 | 均匀抽帧数量（含首尾） |
| `--interval S` | — | 固定秒间隔（与 count 二选一） |
| `--times a,b,c` | — | 指定时刻（秒） |
| `--first` / `--last` | — | 只取首帧 / 尾帧 |
| `--sheet` | — | 输出联系表而非逐帧 jpg |
| `--cols` | 3 | 联系表列数 |
| `--height PX` | 0 | 帧缩放到此高（0=原尺寸，核验建议保留原尺寸） |
| `--png` | — | 输出 png（默认 jpg，质量 92） |
| `--name` | — | 首/尾帧文件名前缀 |

脚本始终先打印视频元信息：`fps / 总帧数 / 宽×高 / 时长`，可用于核对分辨率与帧数。

## 抽帧后的核验

抽出的帧用 Read 工具逐张查看（或 Read 联系表一张），按调用方标准核验：

- 成片核验：角色身份/服装与三视图一致、场景正确、动作符合提示词、无多余人物、无文字水印/UI
- 动作反推：逐帧记录人物姿态、队形、节拍，供写提示词
- 核验不通过：改提示词/参数重跑出片，再重新抽帧，不直接交付

## 输出位置约定

- 成片核验帧、临时反推帧属中间产物，输出到当前任务的临时工作目录
- 衔接尾帧/封面属交付资产，输出到对应项目的 `衔接帧\` / `images\` 目录

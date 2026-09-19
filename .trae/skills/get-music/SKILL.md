---
name: "get-music"
description: "基于 APIMart 音乐生成 API 生成音乐，支持 Flow Music（flowmusic）与 Suno V6（suno）两种模型，覆盖风格提示词/歌词/BPM/时长控制。当用户要求生成音乐、AI 作曲、文字生成音乐、写歌、创作歌曲、生成 BGM/纯音乐，或提到 flow music / suno 时调用。"
---

# APIMart 音乐生成（Flow Music + Suno V6）

基于 APIMart 的音乐生成 API，一次请求生成一首或多首音乐。支持两种模型：**Flow Music**（`model="flowmusic"`）与 **Suno V6**（`model="suno"`）。两者共用提交与查询端点，均异步：先提交拿 `task_id`，再轮询取结果下载音频。

## 触发条件

- 用户要求「生成音乐 / AI 作曲 / 文字生成音乐 / 写歌 / 创作歌曲 / 生成一段音乐 / 做 BGM / 纯音乐 / 歌曲」等
- 用户提到 flow music、suno、APIMart 音乐生成

## 前置条件

1. 需要 APIMart API Key，访问 <https://apimart.ai/keys> 获取
2. API Key 优先从环境变量 `APIMART_API_KEY` 读取；若不存在则向用户索要，**严禁编造或猜测 Key**

## 认证与基础 URL

所有接口均使用 Bearer Token 认证：

```
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

基础 URL：`https://api.apimart.ai/v1`

## 执行方式：优先使用固化脚本

项目内已有固化脚本 `tools/new_music.py`（纯标准库，无第三方依赖），**生成/查询音乐一律优先调用它**，不要每次在终端临时拼 HTTP 命令，以保证流程一致、可复现。

```powershell
# Flow Music 纯音乐，生成并精修到 30.4 秒（0.5s 淡入 / 1.4s 淡出）
python tools/new_music.py --title "E01 BGM" `
  --prompt "playful sweet acoustic guitar and ukulele, instrumental, no vocals" `
  --bpm 100 --length 30 --out "<输出目录>" --trim 30.4

# Suno V6 纯音乐
python tools/new_music.py --model suno --version v6 --instrumental `
  --prompt "warm healing piano and strings, no vocals" --out "<输出目录>"

# 只查询/补下载已有任务（不扣费）
python tools/new_music.py --query <task_id> --out "<输出目录>"

# 提交前先核对请求体（不联网、不需要 key）
python tools/new_music.py --title test --prompt "piano, instrumental" --dry-run
```

脚本行为约定（已实测）：

- 提交（POST，收费）**不做失败自动重发**，网络中断时提示改用 `--query`，避免重复扣费；查询（GET，幂等）会自动重试。
- 任务刚提交的约 60 秒内返回 404 / `Invalid task ID` 会自动等待重试；429/5xx 自动退避重试；`failed` 读取 `error.message`；`unknown` 继续等待，超时后提示手动 `--query`，绝不超时重发 POST。
- 完成后自动下载全部音轨与封面到 `--out`，并写一份 `<标题>.result.json` 原始响应；`--no-download` 只回显元数据。
- `--trim N` 用完整版 ffmpeg（自动取 `imageio_ffmpeg` 自带 ffmpeg；系统 PATH 里的精简版缺 aac 编码器会被跳过）截取前 N 秒并淡入淡出，同时产出 m4a + wav，`--no-wav` 可关。
- 网络：脚本优先尊重 `HTTPS_PROXY`/`HTTP_PROXY`，否则自动探测本地 `127.0.0.1:7890` 代理，再不行才直连。实测 `api.apimart.ai` 在本机直连会被 DNS 污染（解析到 31.13.85.53 等不可达 IP），需先开启 Clash 类代理；音频域名 `getapib.org` 可直连。

## 模型选择

| 模型 | `model` 值 | 特点 |
|------|-----------|------|
| Flow Music | `flowmusic` | 风格提示词 + 可选歌词 + BPM + 时长，参数简洁 |
| Suno V6 | `suno` | 灵感/自定义双模式、版本（v6 系列）、人声性别、风格/创意/音频三权重、纯音乐、最长 360 秒 |

## 核心使用流程：从脚本故事到纯音乐

本 skill 最常用的场景之一是：用户提供一个**脚本/故事/剧情**，据其创作**纯音乐（无歌词、无人声的背景音乐 BGM）**。按「分析 → 提示词 → 生成 → 汇总」四步走。

### 第 1 步：分析脚本，提取配乐要素

通读脚本，先产出 6 项要素，作为提示词的依据：

- 情绪基调：整段脚本的核心情绪（温暖/治愈/悲伤/紧张/史诗/悬疑/梦幻/明快等）
- 情绪弧线：起承转合，标注情绪起伏点（判断是否需要拆成多段配乐）
- 场景氛围：若有多场景，逐个标注氛围关键词
- 节奏（BPM）：舒缓 60~80、中等 90~120、明快 120~140、激烈 140+
- 配器：按情绪选音色（钢琴/大提琴/弦乐/木吉他/管弦乐/合成器/竖琴/打击等）
- 目标时长：配合脚本或画面长度（Flow Music 1~240s，Suno 10~360s）

### 第 2 步：生成纯音乐提示词

把要素转成**英文**描述性提示词（两个模型英文提示词效果更稳定），公式：

`[风格 genre], [情绪 mood], [配器 instrumentation], [节奏 bpm], [场景意象 imagery], instrumental, no vocals`

情绪 → 配乐速查表：

| 情绪 | 配器 | BPM | 风格关键词 |
|------|------|-----|-----------|
| 温暖治愈 | 木吉他、钢琴、弦乐 | 70~90 | warm, gentle, acoustic |
| 悲伤/抒情 | 钢琴、大提琴、弦乐 | 60~80 | melancholic, emotional, cinematic strings |
| 紧张/悬疑 | 合成器、低音、打击 | 100~130 | tense, dark, pulsing, suspenseful |
| 史诗/激昂 | 管弦乐、铜管、打击 | 120~140 | epic, orchestral, heroic |
| 梦幻/空灵 | 合成器、竖琴、pad | 60~80 | dreamy, ethereal, ambient |
| 明快/轻松 | 木吉他、尤克里里、轻打击 | 100~120 | upbeat, cheerful, light |

### 第 3 步：选定模型并提交

纯音乐两种实现：

- **Suno（纯音乐最直接）**：设 `instrumental: true`，用灵感模式 `custom:false`，`prompt` 写场景情绪描述：
  ```json
  { "model": "suno", "version": "v6", "custom": false, "instrumental": true,
    "prompt": "warm healing piano and strings, gentle, 80 bpm, no vocals" }
  ```
  需要更长或更精细可再加 `duration`、`style_weight`、`audio_format` 等。

- **Flow Music**：`sound_prompt` 描述纯音乐，**不传 `lyrics`**，可精确控制 `bpm`/`length`：
  ```json
  { "model": "flowmusic", "title": "治愈开场", "sound_prompt": "warm healing piano and strings, 80 bpm, instrumental", "bpm": "80", "length": 60 }
  ```

选型建议：要精确 BPM/时长、参数简单、短时长 → Flow Music；要更长时长（可达 360s）、更丰富的音乐质感、风格/人声等权重调节 → Suno。

### 第 4 步：轮询取结果

按下方「工作流（异步任务，两步完成）」中的查询步骤轮询，完成后取 `audio_url`（Flow Music 另有 `wav_url`）。

### 多场景 / 多情绪段落

脚本若含多段不同情绪，逐段重复第 1~3 步，每段用独立 `title` + 独立 `task_id`，最后把各段 `audio_url` 按脚本顺序汇总成完整 BGM 集（命名建议 `01_开场温暖`、`02_高潮史诗` 之类）。

## 工作流（异步任务，两步完成）

### 第一步：提交生成任务

`POST https://api.apimart.ai/v1/music/generations`

提交成功响应（200）：

```json
{
  "code": 200,
  "data": [
    { "status": "submitted", "task_id": "task_01K8AYYM6R03TGZ3Q2P0TZVNPX" }
  ]
}
```

从 `data[0].task_id` 取任务 ID。`submitted` 仅表示已受理，尚无最终音频。

### 第二步：查询任务结果

`GET https://api.apimart.ai/v1/music/tasks/{task_id}`

路径参数：`task_id`（必填，提交接口返回的 `data[0].task_id`）。

查询参数（可选）：`language`（默认 `zh`，可选 `zh` / `en` / `ja` / `ko`，只影响错误与提示文案，不改变歌曲语言）。

任务状态 `data.status` 的取值：

- Flow Music：`pending` / `processing` / `completed` / `failed`
- Suno V6：额外可能出现 `unknown`

轮询建议：Suno 首次等待约 3 秒、之后每 5~10 秒一次；Flow Music 每 10~20 秒一次。`status` 为 `completed` 时从 `data.result.music[]` 取结果；`failed` 时读 `data.error.message`；`unknown` 时保留任务 ID 稍后手动刷新，**不要**因超时自动重发收费的 POST。

通用查询响应字段：`id`、`status`、`progress`、`created`、`cost`（美元金额）、`credits_cost`（积分）、`result`、`error`（失败原因）。Suno 额外有 `estimated_time`（预计耗时，仅参考）。

## 模型 A：Flow Music（`model="flowmusic"`）

提交请求体字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | 固定传 `flowmusic`（大小写不敏感） |
| `sound_prompt` | string | 否* | 音乐风格或声音描述，如 `upbeat pop music with piano` |
| `lyrics` | string | 否* | 歌词文本，如 `[Verse 1]\n黑夜再长也会天亮\n...` |
| `title` | string | 否 | 生成音乐标题 |
| `bpm` | string | 否 | BPM（每分钟节拍数），必须 ≥ 1，如 `"120"` |
| `length` | integer | 否 | 生成时长（秒），支持 1 ~ 240；为参考值，实际音频时长可能更长（实测 length=30 生成 ≈58s） |
| `seed` | string | 否 | 随机种子，用于复现（同请求同 seed 结果相近但不保证一致） |

> *约束：`sound_prompt` 与 `lyrics` **不可同时为空**，至少传一个。每次请求仅生成一首音乐。

完成后的 `result.music[]` 元素包含：`clip_id`、`title`、`duration_seconds`、`lyrics`、`audio_url`（m4a）、`wav_url`（wav）、`image_url`（封面 jpg）。

使用场景：

```json
// 场景 1：纯风格提示词
{ "model": "flowmusic", "title": "My Song", "sound_prompt": "upbeat pop music with piano", "bpm": "120", "length": 60 }

// 场景 2：歌词 + 风格成曲
{ "model": "flowmusic", "title": "坚持", "lyrics": "[Verse 1]\n黑夜再长也会天亮\n...", "sound_prompt": "energetic rock with electric guitar", "length": 120 }
```

## 模型 B：Suno V6（`model="suno"`）

### 模式

由 `custom` 决定文本字段含义：

- `custom=false`（默认，灵感模式）：`prompt` 作灵感描述。`title`、`style`、`negative_tags`、`auto_lyrics`、`persona_id` 被忽略。
- `custom=true`（自定义模式）：`prompt` 作歌词，上述自定义字段生效。

`style_weight`、`weirdness_constraint`、`audio_weight`、`vocal_gender` 在两种模式均生效。

### 版本与自定义模型

- 公共版本仅 `v6` / `v6-wild` / `v6-mini`。
- 主生成必须提供 `version` 或 `custom_model_id` 两者之一；公共 `version` 与 `custom_model_id` 不能同时发送。
- `custom_model_id` 是创建自定义模型任务返回的完整 UUID，与 `version`、`persona_id` 互斥，提供后按自定义模型价格档计费。
- 注意：`custom:true`（自定义歌词）与 `custom_model_id`（自定义模型）是两个不同概念。

### 提交请求体字段

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `model` | string | `suno` | 固定传 `suno`（不传也默认 `suno`） |
| `custom` | boolean | `false` | `false` 灵感 / `true` 自定义（`prompt` 作歌词） |
| `instrumental` | boolean | `false` | `true` 纯音乐、无人声 |
| `version` | string | — | `v6` / `v6-wild` / `v6-mini`，与 `custom_model_id` 二选一（至少一个） |
| `custom_model_id` | string | — | 自定义模型 UUID，与 `version`、`persona_id` 互斥 |
| `prompt` | string | — | 灵感描述或歌词。`custom=false` 必填 ≤3000 字符；`custom=true` 且 `instrumental=false` 必填 ≤5000 字符；自定义纯音乐可省略 |
| `title` | string | — | 标题（≤80 字符），仅 `custom=true` 生效 |
| `style` | string | — | 风格标签（≤1000 字符），仅 `custom=true` 生效（注意用 `style` 不是 `tags`） |
| `negative_tags` | string | — | 负向风格标签（不希望出现的风格），仅 `custom=true` 生效 |
| `auto_lyrics` | boolean | — | `true` 对输入歌词二次创作，仅 `custom=true` 生效 |
| `persona_id` | string | — | Persona 风格 ID，仅 `custom=true` 生效，与 `custom_model_id` 互斥 |
| `vocal_gender` | string | — | `Male` / `Female`（也接受 `m`/`f`/`male`/`female`），两种模式均生效 |
| `style_weight` | number | — | 风格权重 0.00~1.00，两种模式均生效 |
| `weirdness_constraint` | number | — | 创意度 0.00~1.00，两种模式均生效 |
| `audio_weight` | number | — | 音频权重 0.00~1.00，两种模式均生效 |
| `variety` | string | — | 风格变化程度 `off`/`normal`/`high`/`extra`/`max`，无固定默认 |
| `max_mode` | boolean | `false` | Max 模式，启用需 `custom=true`，按 2 倍计费 |
| `audio_format` | string | — | `mp3` / `m4a` / `wav`，省略由服务自选 |
| `duration` | integer | — | 目标时长 10~360 秒，仅 `custom=true` 可用；实际以结果为准 |

完成后的 `result.music[]` 元素包含：`audio_id`、`status`、`title`、`lyrics`、`tags`、`display_tags`、`duration`（允许小数）、`audio_url`（不保证 `.mp3` 后缀，按返回 URL 使用）、`image_url`、`image_large_url`。权重返回值 `0` 是有效值，勿按 falsy 隐藏。

### 引用源音轨

对已有作品做后续操作（封面/续写/替换等）时，用 `task_id` + `audio_index`（源任务 `data.result.music[]` 中的原始位置，从 1 开始，默认 1）引用源音轨，不能用 `audio_id`、`music_id` 或 `audio_url` 替代。

### 使用场景

```json
// 灵感模式（prompt 作灵感描述）
{ "model": "suno", "custom": false, "version": "v6", "prompt": "深夜城市 lo-fi 钢琴配雨声" }

// 自定义模式（prompt 作歌词）
{
  "model": "suno", "version": "v6", "custom": true, "instrumental": false,
  "prompt": "[Verse]\n雨夜霓虹灯下的街道",
  "title": "深夜驾驶",
  "style": "synthwave, female vocal, cinematic",
  "vocal_gender": "Female",
  "style_weight": 0.6, "weirdness_constraint": 0.3, "audio_weight": 0.5
}
```

## 错误码

Flow Music 错误响应 `body.error.code` 为字符串；Suno 为数字。综合如下：

| HTTP | Flow Music `code` | Suno `code` | 含义与处理 |
|------|-------------------|-------------|-----------|
| 400 | `invalid_request` | `invalid_request_error` | 参数错误（如必需字段为空/互斥字段同传），核对参数重试 |
| 401 | — | `authentication_error` | API Key 缺失或错误，检查 `Authorization` |
| 402 | — | `payment_required` | 余额不足，提示用户充值 |
| 403 | `quota_not_enough` | `permission_error` | 余额不足（flowmusic）/ 无权限（suno） |
| 404 | `task_not_found`（查询） | — | 任务 ID 不存在或拼错，核对 `task_id` |
| 429 | `rate_limit_error` | `rate_limit_error` | 过于频繁/容量饱和，稍后重试 |
| 500 | — | `server_error` | 服务内部错误，稍后重试 |
| 502 | — | `bad_gateway` | 网关错误，稍后重试 |

## 提示词写作建议

- Flow Music：`sound_prompt` 写得越具体越好（风格、情绪、乐器、BPM、人声方向），如 `warm indie folk ballad, acoustic guitar, soft female vocals, 70 bpm, wistful and hopeful`
- Suno 灵感模式：`prompt` 描述风格/情绪/场景即可，如 `深夜城市 lo-fi 钢琴配雨声`
- 纯音乐：Flow Music 省略 `lyrics` 并用 `sound_prompt` 描述无 vocals；Suno 设 `instrumental:true`
- 需要指定唱词：Flow Music 用带 `[Verse]/[Chorus]` 标签的 `lyrics`；Suno 用 `custom:true` 且 `prompt` 传歌词
- 歌词可先用 APIMart 歌词生成接口得到后回填

## 输出要求

完成任务后向用户汇报：所用模型、歌曲标题、时长、任务 ID、下载链接（`audio_url`，Flow Music 另有 `wav_url`）及封面图（`image_url`）。
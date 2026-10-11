---
name: tone-keeper
description: Manage a reusable film-look tone library (基调/风格库) that locks colour, light and texture across every shot of a film. Use when the user wants to 定基调 / 定调 / 统一色调 / 定风格参考 / 用滤镜风格出图, asks to preview, add or pick a style for generation, or needs all shots of one production aligned to a single cinematic look. Covers previewing existing tones, adding a new tone (from an existing still or by generating a key visual), and rendering shots locked to a chosen tone via Midjourney sref.
agent_created: true
---

# Tone Keeper

## 用途

把一个片子的**视觉基调**（色调 / 光感 / 质感）沉淀成可复用的「风格」，供该片全部镜头对齐，防止跨镜色调漂移。

一个「风格」= 一张**基准图**（人类可看的定调画面）+ 一个**sref 源**（压缩后上传图床，供出图引用）+ 一条**公网直链** + 一组**六维定义**。

三种操作：**预览已有风格**、**新增风格**、**选择风格出图**。

## 核心概念

- **基准图（key image）**：定调画面本体，不进正片，只作风格样本与肉眼核验依据。
- **sref 源**：基准图压到长边 1536 / JPEG q90（远小于图床 1 MiB 上限）后的版本，用于上传。
- **sref 直链**：图床返回的公网 URL。MJ 的 `sref` 参数**只吃公网 URL，不接 base64**，这是必须绕图床的唯一原因。
- **定调 ≠ 定人**：sref 只提取色彩 / 光影 / 质感，**不搬运人脸与纹样**。人物身份永远以角色三视图为唯一基准；风格只管影调。
- **一风格一基调**：冷暖两界（如幻境暖金 / 现实冷青）应各自登记为一个风格，用 `--tone` 分别选用，不要试图用一个风格覆盖两种色温。

## 环境

所有脚本用 **venv python** 运行（压图 / 联系表依赖 cv2 与 PIL）：

```bash
PY="C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
SK="D:/work/minimax_h3/.trae/skills/tone-keeper/scripts"
```

风格库位置、图床脚本、API 与默认参数全部在 `config.json`；可用环境变量 `TONE_LIBRARY_DIR` 临时覆盖库路径（跨项目复用场景）。

## 操作一：预览已有风格

```bash
# 文本列表（含六维定义、sref 状态、基准图路径）
"$PY" "$SK/list_tones.py"

# 生成一张九宫格预览联系表，供肉眼比对（推荐先给用户看这张）
"$PY" "$SK/list_tones.py" --sheet
#   → <风格库>/_预览联系表.png

# 机器可读
"$PY" "$SK/list_tones.py" --json
```

给用户选风格时，先跑 `--sheet`，再用 `present_files` 把联系表推给用户，附上每个风格的 ID 与一句话定义。

## 操作二：新增风格

```bash
# A) 登记一张已有图当基准图（最常见）
"$PY" "$SK/add_tone.py" --id TONE-02 --name "幻境暖调·暖金柔焦" \
    --from-image "D:/work/minimax_h3/心魔劫_穆沛灵/assets/场景/SC-03_幻境内室卧榻.png" \
    --desc "暖金橙、明亮微过曝、柔焦、木质粗布软材质" \
    --dims-file "<六维 JSON 路径>" \
    --source "由 SC-03 卧榻图派生"

# B) 用 65535 生成基准图后登记（可带参考图，--ref 可重复）
"$PY" "$SK/add_tone.py" --id TONE-03 --name "雪夜冷灰" \
    --prompt "<完整基准图提示词>" \
    --ref "<参考图1>" --ref "<参考图2>"

# C) 已有图床直链，跳过上传
"$PY" "$SK/add_tone.py" --id TONE-04 --name "…" --from-image X.png --sref-url "https://…"
```

`add_tone.py` 会依次完成：基准图落盘 → 压出 sref 源 → 上传图床拿直链 → 写入 `tones.json`。

六维定义模板见 `assets/dims模板.json`（色彩 / 光影 / 质感 / 影调 / 镜头 / 参照系）。**六维文字要写得可执行**——它既是出图时的措辞来源，也是风格库的人类说明书。

## 操作三：选择风格出图

```bash
# 只列风格 ID
"$PY" "$SK/render_tone.py" --list

# 单条
"$PY" "$SK/render_tone.py" --tone TONE-01 --prompt "<该镜内容描述>" \
    --out "<输出目录>" --tag shot15

# 批量（shots.json = [{"tag":"…","prompt":"…","sw":550}, …]）
"$PY" "$SK/render_tone.py" --tone TONE-01 --prompts-file shots.json --out "<目录>"

# 先核对请求体，不提交
"$PY" "$SK/render_tone.py" --tone TONE-01 --prompt "…" --dry-run
```

出图走 Midjourney `sref` + `sw`（默认 500 / v7 / q2 / 16:9）。**POST 一律不自动重试**——提交即计费，重试等于重复扣费；批量前先 `--dry-run` 核对。

## 风格库结构

```
<library_dir>/
├── tones.json                      # 索引：id / name / slug / dims / sref_url / sw / negative / created …
├── _预览联系表.png                  # list_tones.py --sheet 产物
└── <ID>_<slug>/
    ├── key.png                     # 基准图
    └── sref.jpg                    # sref 源（≤ 1 MiB）
```

## 红线与已知坑

- 🔴 **sref 会诱发脑补的「国风印章 / 书法题字」**（实测 4 张中 2 张）。成片默认不出字幕是硬规则，因此：负向词必须含 `Chinese seal, red stamp, calligraphy, inscribed text, signature mark, character text`（已在 `config.json.default_negative`），且**出图后逐张检查四角与边缘**。
- ⚠️ **MJ 会自行增补场景元素**（佛像、灯笼、烛台等）。提示词须显式声明「只有 X 别无他物」，并把不想要的元素写进负向词。
- ⚠️ **sref 源必须 ≤ 1 MiB**。`make_sref_source` 已按长边 1536 / q90 压好；换更大 `max_side` 前先确认体积。
- ⚠️ **不要用 sref 去锁人物身份**。身份漂移属预期行为，要定人请走三视图图生图或 MJ `oref`。

## 参考

- `references/接口与配方参考.md` —— 两条 API 的请求/响应细节、六维定义写法、标准负向词、已踩坑记录。
- `assets/dims模板.json` —— 六维定义空白模板。

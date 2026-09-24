---
name: "h3-drama-producer"
description: "End-to-end H3 drama pipeline: script-first episodes (flexible 5-15s), element identification (characters/scenes/props), asset retrieval with 65535 generation fallback, h3-prompt-writing Ref2VA prompts, and three RunningHub submission modes (App API by appId, workflow by workflowId, or template-generated workflow JSON). Invoke when user provides a 剧情大纲 wanting H3 scripts, prompts, assets, workflows, or video production."
---

# H3 剧情视频生产流水线

根据用户提供的创意或完整剧本，完成从剧本到成片的端到端生产：剧本创作（创意时调用 story-craft）→ 分集 → 元素识别 → 资产检索（缺失时 65535 补全）→ H3 提示词（h3-prompt-writing）→ RunningHub 出片（三种提交方式）。核心原则：**每一步动手生成之前，先把关键决策问清楚，绝不跳步生成。**

## 触发条件

用户给出创意、剧情大纲、故事想法、IP 二创点子或完整剧本，并希望生成 H3 视频剧本、资产清单、提示词或直接出片时。用户说"生成一个短剧""把大纲变成视频""做工作流""出片"等均触发。

## H3 能力边界（决策依据）

| 规格 | 值 |
|---|---|
| 单集时长 | 4—15 秒灵活（h3-prompt-writing 支持），常用 5/10/15 秒档 |
| 单片上限 | 15 秒，超过必须分集 |
| 最大画幅 | 1344×768（16:9，0.98MP） |
| 帧率 | 24fps，帧数须落在 17k+5 网格（取 ≥ 时长×24 的最小网格值） |
| 常用帧数换算 | 5s→124 帧，8s→192 帧，10s→243 帧，12s→294 帧，15s→362 帧 |

## 流程总览

```
用户输入（创意 或 完整剧本）
  → Step 1 判断输入类型（完整剧本直接用；创意调用 story-craft 创作）
  → Step 2 根据剧本分集（每集 5-15s 按剧情节奏定）+ 确认资源包与输出目录
  → Step 3 元素识别与资产检索（角色/场景/道具 → 本地检索 → 缺失清单）
  → Step 4 缺失资产补全（65535：审批表格 → 生成 → 核验 → 归档）
  → Step 5 生成 H3 提示词（h3-prompt-writing，Ref2VA 六段结构，所有资产已就位）
  → Step 6 选择提交方式（6A 应用API / 6B 工作流直连 / 6C 模板工作流）
  → Step 7 图片上传（runninghub，按提交方式走对应接口）
  → Step 8 构建 payload 并校验
  → Step 9 用户确认
  → Step 10 出片（提交/轮询/下载/费用展示/归档）
```

## Step 1 — 剧本创作（先判断输入类型）

收到用户输入后，**先判断是"完整剧本"还是"创意"**：

| 输入类型 | 判断特征 | 处理 |
|---|---|---|
| **完整剧本** | 已有明确场景划分、逐场动作描述、具体对白文本 | 直接落盘 `<剧名>-剧本.md`，**跳过创作**，进入 Step 2 |
| **创意** | 只有故事梗概、人物设定、一句话点子、情节走向，没有逐场展开 | 调用 `story-craft` 技能先创作完整剧本 |

判断口径：拿不准时问用户"这是完整剧本还是创意大纲？"，不要替用户猜。

### 创意 → 剧本（调用 story-craft）

调用 `story-craft` 技能（原创剧情/人物灵魂设定方向）创作，**按 H3 短剧的容量约束定制写法**：

- 每一"场"对应未来一集（4—15 秒容量），写作时按短剧节拍控制场景颗粒度
- 对白精炼：单集对白总量控制在 15 秒内能自然说完
- 每场标注情绪节拍与转折点，方便 Step 2 分集定时长
- 人物出场即给出造型要点（服装、发型、标志性特征），对应未来三视图

### 剧本要素（两种来源最终统一为）

- 场景标题、动作描述、对白（标注说话人）、情绪与节拍标注
- 剧本为总分结构：先完整故事，后分集；分集是剧本的产物，不是剧本的前提
- **不再先问时长**——时长决策推迟到 Step 2 分集时

写完（或整理完）展示给用户，确认故事走向、人物关系、关键场面后才进入分集。剧本落盘 `<剧名>-剧本.md`。

## Step 2 — 根据剧本分集（每集时长不固定）

- **每集时长在 4—15 秒之间按剧情节奏灵活确定**，不强制统一 15s：
  - 单一动作/一个笑点 → 5 秒
  - 一个小转折 → 8—10 秒
  - 一次完整的关系变化/三段式 → 12—15 秒
- 分集依据：场景切换点、情绪节拍、叙事单元完整性
- 每集必须有**独立完整的小弧线**（开场可理解、结尾有钩子或收束），不是把故事硬切几段
- 设计**跨集锚点**保证系列连续感：核心道具流转、贯穿母题、固定角色造型、集尾悬念钩子
- 分集表先向用户展示，格式：

| 集号 | 时长 | 场景 | 核心事件 | 对白摘要 | 帧数 | 衔接 |
|---|---|---|---|---|---|---|
| E01 | 10s | 御书房 | ... | ... | 243 | →E02：A |
| E02 | 12s | 御书房 | ... | ... | 294 | 无 |

### 集间衔接规划

集与集之间画面需要连续时（同一动作跨集、长镜头拆分、无缝转场），在分集表"衔接"列标注并让用户选方案：

| 方案 | 做法 | 优缺点 |
|---|---|---|
| **A 衔接图先行** | Step 4 用 65535 先生成衔接帧图片（E01 末镜头画面），E02 以它为首帧 | 可提前准备、出片可并行；但衔接图是"预期"的尾帧，与 E01 实际成片尾帧可能有偏差 |
| **B 截取尾帧** | Step 10 中 E01 出片后截取真实尾帧，作为 E02 首帧 | 衔接精准；但 E02 必须等 E01 完成，串行出片 |

- 无画面连续需求时标"无"（默认）
- 衔接集（后一集）的提示词在 Step 5 改用 **I2VA 首帧驱动模式**（h3-prompt-writing），画面从首帧开始向前发展
- 衔接帧归档 `<项目>\衔接帧\E01-E02.png`（项目私有）

- **同时确认资源包与输出目录名**：
  - 资源包：角色/场景/道具资产所在的 IP 资产目录，默认 `assets\凡人\`；制作其他 IP（仙逆等）时指定对应包，包不存在时提示用户后续按 Step 4 补建
  - 输出目录：默认 `d:\work\minimax_h3\<剧名>\`，用户另有指定以用户为准

目录内最终交付物：

```
<剧名>-剧本.md             完整剧本
<剧名>-分集剧本.md          分集结构表 + 跨集锚点 + 各集完整提示词
<剧名>N.md                 每集一份提示词（E01→1.md，E02→2.md…）
资产清单.md                 角色/场景/道具资产与 Picture 槽对应关系
衔接帧\                     集间衔接帧（有衔接需求时）
任务记录\                   payload、上传映射
video\                     成片
```

## Step 3 — 元素识别与资产检索

### 3.1 元素识别

从剧本中提取三类元素，输出元素清单表（先展示，用户确认后再检索）：

| 类别 | 名称 | 关键特征 | 出场集数 | 对应 Picture 槽 |
|---|---|---|---|---|
| 角色 | 李缨宁 | 宫装、长发、玉簪 | E01-E04 | Picture 1 |
| 场景 | 御书房 | 暖烛光、书架 | E01, E03 | Picture 2 |
| 道具 | 家传玉佩 | 青玉、红绳 | E02-E04 | Picture 3 |

- **角色**：名字 + 造型（一套造型对应一张三视图）
- **场景**：场景名 + 氛围特征（空镜，不含人物）
- **道具**：贯穿剧情的关键道具（可选，仅核心道具需参考图）

### 3.2 资产检索

资产分两层：**IP 级共享**（`assets\<资源包>\` 下 character/scene/props，跨项目复用）与**项目级私有**（`<项目>\` 下 scene/props，本剧情专属）。检索顺序一律**项目私有 → IP 共享 → 备用源**。

- **角色**（候选根目录按优先级探测：用户指定目录 → `<项目根>\assets\<资源包>\character\` → `E:\短剧平台\凡人二创\人物图\`（凡人包备用源））：
  - 命名：`人物三视图（{造型}）.png`；面部特写 `特写图.png`；设定卡 `详细信息图.png`
  - 检索：`Get-ChildItem <资产目录> -Recurse -File -Filter "*三视图*"`，按人物名匹配文件夹
  - 找到后**用 Read 工具查看图片内容**，记录实际形象与服装
  - **同一人物有多张三视图时，必须先询问用户选哪张**（说明各张差异）
- **场景**（先项目私有再 IP 共享）：
  - 项目私有：`<项目>\scene\`
  - IP 共享：`<项目根>\assets\<资源包>\scene\`，子目录按标签分类（`scene\学校\`、`scene\城市夜景\`）
  - 命名 `场景-{场景名}.png`；共享库配套 `场景索引.md`（人类可读）与 `场景索引.json`（agent 可解析，含 tags）
  - **画风一致性闸门（强制）**：找到候选场景图后必须用 Read 同时查看场景图与本集角色三视图，逐项比对渲染风格（如：国产 3D 动画 CG / 真人写实照片 / 2D 插画、皮肤质感、光影、景深）。**画风不一致时禁止直接使用，必须停下明确提醒用户**：说明差异（如"场景为真人写实风、三视图为 3D 动画 CG 风"）、风险（Ref2VA 会以占画面更大的场景图为准统一全片风格，迫使角色脸被"翻译"成场景画风，导致五官走形——2026-09《勾栏听曲》六集实测教训），并给出选项：图生图重绘场景为三视图同画风 / 更换场景 / 用户书面确认接受风险。不得替用户默认放行。
- **道具**（先项目私有再 IP 共享）：
  - 项目私有：`<项目>\props\`
  - IP 共享：`<项目根>\assets\<资源包>\props\`
  - 命名 `道具-{名称}.png`

检索结果写入 `资产清单.md`：元素、类别、文件名、绝对路径、外观说明、Picture 槽对应关系。**找不到的标"缺失"**，进入 Step 4 补全。清单末尾附引用示例（Ref2VA 格式，`<Picture N>` 与 t8lite imageN 槽一一对应）：

```
<Picture 1>: <人物A>身份与服装参考（<绝对路径>）
<Picture 2>: <场景B>环境参考（<绝对路径>）
```

## Step 4 — 缺失资产补全（65535 生成）

Step 3 检索不到的角色/场景/道具，用 **65535 API** 生成。**生成前必须先审批**：

### 4.1 审批表格

整理缺失资产生成计划，表格展示给用户：

| 序号 | 元素 | 类型 | 生成方式 | 生成提示词 | 参考图 | 归档路径 | 预期产出 |
|---|---|---|---|---|---|---|---|
| 1 | 李缨宁（宫装） | 角色三视图 | 图生图 | 正面/侧面/背面三视图，宫装…锁定脸部与发型 | 人物三视图（常服）.png | assets\凡人\character\李缨宁\人物三视图（宫装）.png | 全身三视图 |
| 2 | 御书房 | 场景空镜 | 文生图 | 空镜，暖烛光书架，无人物 | - | <项目>\scene\宫殿\场景-御书房.png | 场景图 |
| 3 | 家传玉佩 | 道具 | 文生图 | 青玉玉佩特写，红绳… | - | assets\凡人\props\道具-家传玉佩.png | 道具图 |

生成提示词要领：

- **角色补全**：以最接近的现有造型三视图为参考图，**锁定脸部/发型/身份锚点，仅修改服装**；提示词明确"保持面部、发型、瞳色与参考图完全一致"
- **场景**：文生图空镜，不含人物，氛围特征与剧本描述一致；**必须显式锁定与角色三视图相同的渲染画风**（如三视图为 3D 动画 CG，提示词写明 "3D Chinese donghua CG animation style, stylized rendered look, matching a 3D animated film, NOT live-action / photorealistic / real photo"），从源头避免场景与角色画风冲突。生成后用 Read 与三视图并排核验画风，不一致即调词重生成。**特例**：目标画风为**真人写实**时（如 `palace-girlfriend-trending` / `dance` 两个系列），画质段直接照抄 `assets\真人质感美术基准.md` §6.2 真人质感段 + §5 反向约束，不要另写一套
- **道具**：文生图特写，特征与剧本关键道具描述一致；画风同样须与成片目标画风一致

### 4.2 生成与归档

1. 用户批准表格后调用 65535 生成（任务定义存档 `任务记录\任务-{元素名}.json`）
2. **人工核验**：角色核验身份锚点（发型、瞳色、标志性配饰/妆容）是否保留；**场景/道具核验画风是否与角色三视图一致**——核验不通过则调提示词重生成，场景画风冲突未解决不得归档使用
3. 按表格归档路径落盘。归档规则：**人物三视图必归 IP 共享** `assets\<资源包>\character\<人物名>\`；场景/道具按通用性判断——跨集跨项目可复用归 `assets\<资源包>\`（scene/props），本剧情专属归 `<项目>\`（scene/props），拿不准问用户。新 IP 资源包不存在时按 `assets\<IP名>\{character,scene,props}\` 结构创建
4. 同步更新 `资产清单.md` 与索引：**新增人物三视图不手写，跑 `python tools\sync_character_index.py` 预览、确认后加 `--write` 写回**（凡人包为默认目录；其他资源包用 `--base` 指向其 character 目录；脚本规则见 `assets\凡人\资源包使用规范.md` §7）；场景类另更新 `场景索引.md`

### 4.3 衔接帧生成（方案 A）

分集表标注了方案 A 的衔接，衔接帧在审批表格中**一并生成**：

- 审批表格"类型"填"衔接帧"，建议以 E01 末镜头涉及的角色/场景参考图做图生图（构图、人物姿态、光线与 E01 末镜头描述一致）
- 生成提示词要点：画面即 E02 的首帧起点——人物位置、朝向、动作起点必须与 E02 剧本开场吻合
- 归档 `<项目>\衔接帧\E01-E02.png`，命名 `衔接帧-ENN-ENN+1.png`（项目私有）
- 衔接帧在 Step 7 与其他参考图一起上传，填入 E02 payload 的首帧图槽

补全后**所有参考图就位**，再进入提示词生成——确保 retention_analysis 基于实际图片撰写，无需事后回填。

## Step 5 — 生成 H3 提示词（h3-prompt-writing）

通过 Skill 工具调用 `h3-prompt-writing` 技能（**不得仅读其参考文件代替调用**——技能正文可能含参考文件之外的规则），按 Ref2VA 原生结构生成每集提示词：

- 按其 `references/ref-en.txt`（Ref2VA）规范执行，读规范后再动笔
- **每集时长按 Step 2 分集表**（4—15s 灵活，不再固定 15s）
- **所有参考图已就位**（Step 3 检索 + Step 4 补全）：`subject_definitions` 与 `retention_analysis` 直接基于实际图片内容撰写，与资产清单逐项核对，不留占位描述
- 六段结构：subject_definitions → summary → retention_analysis → detailed_description → overall_soundscape → non_diegetic_music
- **衔接集**（分集表"衔接"列非"无"的后一集）改用 h3-prompt-writing 的 **I2VA 首帧驱动模式**（读其 base-en.txt 规范）：首帧 = 衔接帧（方案 A）或上一集尾帧（方案 B），`detailed_description` 的 `[Shot 1]` 从首帧画面开始向前发展，人物姿态与动作起点与首帧严格一致
- 衔接集首帧的实现按提交方式区分：6A 无独立首帧节点时，衔接帧/尾帧放入 image1 槽并在提示词中声明 `<Picture 1>` 为首帧画面基准（retention_analysis 注明"作为视频第一帧使用"）；6C 工作流可自由接线，建议接独立首帧 LoadImage
- 对白格式 `<d>[Mandarin Chinese] …</d>` + 说话人编号 (S1)(S2)；画面内可见文字保留原语言
- 镜头格式：`[Shot 1]` 无时间戳开头，后续 `[Shot N] At MM:SS.mmm`
- 时间线无缺口覆盖 0—Ns
- 先写总纲 `<剧名>-分集剧本.md`，再按 `<剧名>N.md` 逐集落盘

音频控制（无声字幕/纯环境音/纯人声模式）见附录。

## Step 6 — 选择提交方式（三选一）

**选择入口：先读注册表**。`<项目根>\assets\应用注册表.md` 是本地收藏夹（RunningHub API 查不到"我的收藏"，`--list` 返回的是应用市场全量推荐，7 万+ 条，无法定位个人常用应用）。把表中已登记的应用 / 工作流 / 模板连同用途展示给用户选择。

| 方式 | 前置条件 | 选择入口 | 适用 |
|---|---|---|---|
| **6A 应用 API** | appId + 节点映射 | 注册表"应用"表（t8lite/jp/jplite/t8balance） | 常规批量出片（t8lite 首选） |
| **6B 工作流直连** | workflowId | 注册表"工作流"表 | 已有调好的 ComfyUI 工作流 |
| **6C 模板工作流** | 工作流模板 JSON | 注册表"模板"表 + `assets\工作流模板\` 目录 | 需要自定义节点图（分辨率锁定、多参考图接线等） |

**选择流程**：

1. 读注册表，把已登记条目（名称、ID、用途、备注）展示给用户
2. 用户选定已登记条目 → 直接走对应分支
3. 用户要用的不在表内（新 appId/workflowId/模板）→ 先 `--info` 查节点确认可用，**首次调用成功后登记进注册表**（名称、ID、用途、备注）
4. 也可扫 `assets\工作流模板\` 目录补充模板选项

### 6A 应用 API（appId 直调，批量出片首选）

用 `nodeInfoList` 覆盖节点字段，**无需生成或管理工作流 JSON**。

**节点映射获取（纯动态，无需维护文档）**：任何 appId 用 `--info` 都能拿到完整节点信息（nodeId、fieldName、description、当前值、可选值枚举），且永远与应用当前版本同步：

   ```powershell
   python "d:\work\minimax_h3\.trae\skills\runninghub\scripts\runninghub_app.py" --info <WEBAPP_ID>
   ```
   调用 `GET /api/webapp/apiCallDemo?apiKey={key}&webappId={id}`，自动返回该应用全部可修改节点，包括 SWITCH/FLOAT/LIST 等字段的可选值（如文戏=0/武戏=1、全部画幅选项）——信息比静态文档更全且不会过时。

- 端点：`POST https://www.runninghub.cn/openapi/v2/run/ai-app/<webappId>`，Header `Authorization: Bearer <RUNNINGHUB_API_KEY>`
- webappId 以应用注册表为准（t8lite 2026-09 版：2097935043799896065）
- 文戏剧集标准 nodeInfoList（t8lite）：

| nodeId | fieldName | 值 | 说明 |
|---|---|---|---|
| 64 / 69 | index | "0" | 文武戏设置（0=文戏） |
| 27 | value | 秒数 | 时长（按分集表，如 "10"） |
| 28 | prompt | Ref2VA 六段提示词 | <Picture N> 对应 imageN 槽 |
| 29 | aspect_ratio | "16:9 (Widescreen)" | 画幅 |
| 6, 35–42 | image | `openapi/<hash>.png` 或 "None" | image1–9 槽，空槽填 "None" |

### 6B 工作流直连（workflowId）

用 workflowId 直接运行平台上已有的 ComfyUI 工作流。**参数修改机制与 6A 完全相同**——`--node` 改提示词/时长等文本字段、`--file` 传图、`--instance` 选显存档位，全部通过 nodeInfoList 覆盖，可修改范围由 `--info` 查询结果决定。节点格式动态查询、无需手工维护文档（新工作流首次调用成功后登记进注册表即可）：

```powershell
# 动态查询节点格式（POST /api/openapi/getJsonApiFormat）
python "d:\work\minimax_h3\.trae\skills\runninghub\scripts\run_workflow_api.py" --info <WORKFLOW_ID>

# 提交（POST /task/openapi/create）
python "...\run_workflow_api.py" --run <WORKFLOW_ID> `
  --node "36:prompt=<提示词>" `
  --file "37:image=<本地图片路径>" `
  --instance plus -o "<输出路径>"
```

- `--info` 自动解析并展示 LoadImage、CR Prompt Text、PrimitiveFloat、VHS_VideoCombine、MiniMaxH3AudioConditioningT8 等节点的 nodeId、class_type、widget_fields
- 查询结果可缓存到 `任务记录\` 避免重复查询，但不强制
- 适合：6C 生成的定制工作流 JSON 导入 RunningHub 平台后（平台分配 workflowId），或用户在平台上调好的工作流

### 6C 模板生成工作流 JSON

扫描 `d:\work\minimax_h3\assets\工作流模板\` 目录，列出模板并**询问用户选哪个**（以目录实际文件为准）：

| 模板 | 特点 | 适用 |
|---|---|---|
| (文武双修均衡版)MiniMax H3双采参考生视频V2.json | 官方 Ref2VA，自然语言提示词，9 参考图槽，ResolutionSelector 切分辨率 | 稳定、保守画质 |
| T8加速工作流.json | 社区模型+LoRA+SolAttn+双时钟 8 步采样，strict_prompt_tags 结构化提示词 | 快速出片、成本低 |

用 Python 脚本基于模板生成新 JSON（脚本写完运行，验证后删除临时脚本）。定制项：

1. **提示词**：填入 CR Prompt Text 节点
2. **分辨率**：锁定 1344×768，移除 ResolutionSelector 及其链路（links 和节点都清干净）
3. **时长**：帧数按 Step 2 分集表（17k+5 网格）；基础模板用 ImpactSwitch 档位（15s=第11档），T8 模板用 PrimitiveFloat 节点（值=秒数）
4. **参考图**：涉及几个元素就接几个 LoadImage 到 ref_image_N 槽
5. **输出前缀**：改为 `MiniMaxH3/<剧名>`

**T8 模板特别注意**：提示词必须为 Ref2VA 六段结构（Step 5 已由 h3-prompt-writing 生成，直接填入）；模板默认 1 个 LoadImage，第二个人物需复制节点、分配新 id 和新 link 接入 ref_image_1 槽（同步更新源节点 outputs.links、目标节点 inputs.link、links 数组、last_node_id/last_link_id）。

**通用陷阱**：

- `widgets_values` 结构不统一（list / dict / 标量）——修改前必须先用 Python 打印真实结构再赋值
- 帧数槽位因节点而异（可能 w[2] 是 height），改之前先核对节点输入定义
- 文本节点赋值保持原结构：列表就 `[PROMPT]`，标量就直接字符串

产出的 JSON 有两种去向：(a) 导入 RunningHub 平台拿 workflowId，走 6B 提交；(b) 直接作为任务提交。

## Step 7 — 图片上传（runninghub）

**上传接口按提交方式区分**：

| 提交方式 | 上传接口 | 返回格式 | 填入位置 |
|---|---|---|---|
| 6A 应用 API | `POST /openapi/v2/media/upload/binary`（form-data `file=@路径`，Bearer 认证） | `openapi/<hash>.png` | nodeInfoList 的 image 字段 |
| 6B / 6C | `runninghub_app.upload_file()`（`POST /task/openapi/upload`） | `api/xxx.png` | LoadImage 节点 `widgets_values[0]` |

6A 上传代码（nodeInfoList 用 `openapi/` 短路径）：

```python
import sys
sys.path.insert(0, r'd:\work\minimax_h3\.trae\skills\runninghub\scripts')
from runninghub import require_api_key, upload_file   # 注意：来自 runninghub，不是 runninghub_app
key = require_api_key(None)
short = upload_file(key, r'<本地图片绝对路径>')   # 返回 https://.../input/openapi/<hash>.png
# 从返回 URL 提取 openapi/<hash>.png 填入 nodeInfoList 的 image 字段
```

6B/6C 上传代码：

```python
import sys
sys.path.insert(0, r'd:\work\minimax_h3\.trae\skills\runninghub\scripts')
from runninghub import require_api_key
from runninghub_app import upload_file
key = require_api_key(None)
name = upload_file(key, r'<本地图片绝对路径>')   # 返回 api/xxx.png
```

**勿混用两个模块（2026-09-19 E11 实测踩坑）**：`runninghub.upload_file`（6A，走 `/openapi/v2/media/upload/binary`，返回 `openapi/<hash>.png`）与 `runninghub_app.upload_file`（6B/6C，走 `/task/openapi/upload`，返回 `api/xxx.png`）是**两套不同接口**——6A 任务若误 import `runninghub_app` 拿到 `api/` 路径填进 nodeInfoList，会在 LoadImage 报「No such file or directory」。宫装女友系列（t8balance）属 6A，一律用 `runninghub.upload_file`。

- 先 `python <runninghub脚本> --check` 确认 API Key 有效
- 两套接口均**内容寻址**：同一文件返回相同 hash 文件名，隔天重传文件名不变；跨集复用角色无需重传，路径映射缓存在 `任务记录\上传结果.json`
- **上传链接仅一天有效**：正式出片前如隔天需重新上传（文件名不变，nodeInfoList/工作流无需改）
- 上传不产生费用
- **上传后勿立即提交任务**：openapi/api 短路径写入工作区有分钟级同步延迟，上传后秒提交会在 LoadImage 节点报「No such file or directory」**零扣费失败**（2026-09-18 E05 实测 node 6）；上传与提交之间留 2—5 分钟，失败后隔几分钟重提同一 payload 即可，不算 payload 错误。**规则正本见 `runninghub` 技能 SKILL.md「长任务执行规范」§4**（含内容寻址与链接有效期的完整口径）

## Step 8 — 构建 payload 并校验

### 8.1 构建 payload（可选值先问用户）

构建前用 `--info` 拉取所选应用/工作流的节点定义，**SWITCH / LIST 等带可选值的节点，把选项列给用户选择**，不要擅自填默认值：

- 例（t8lite）：文武戏设置 64/69 → `0=文戏 / 1=武戏`；分辨率 29 → `1:1 / 2:3 / 3:2 / 3:4 / 4:3 / 9:16 / 16:9 / 21:9`
- 展示时标注推荐默认（如文戏、16:9），用户可直接回车确认
- 提示词（nodeId 28）与时长（nodeId 27）按 Step 5 和分集表自动填，不需问

各方式 payload 形态：

- 6A：每集一份 nodeInfoList JSON（含用户选定的可选值）
- 6B：`--node` / `--file` 参数组（可选值同样以 `--info` 结果为准，先问再填）
- 6C：工作流 JSON（上传文件名已填入 LoadImage）
- 每集 payload 存档 `任务记录\t8lite-ENN-payload.json`（或 `-workflow-ENN-payload.json`），便于复盘与重跑

### 8.2 校验清单（全部通过才进入确认）

- [ ] 提示词：`<Picture N>` 引用与图片数量、顺序一致；时间段无缺口覆盖 0—Ns
- [ ] 六段结构齐全；[Shot N] 数量正确；首镜头无时间戳、其余带 At 时间戳；对白 `<d>` 与 (Sx) 齐全
- [ ] 每集时长与 Step 2 分集表一致；帧数落在 17k+5 网格
- [ ] **方案 B 衔接集的首帧槽此时为空是预期**（等 Step 10 截尾帧后填入），校验时标记"待填"放行，勿当缺失报错
- [ ] 6C 额外：链路完整性（links 两端节点存在、槽位不越界、互指一致、无悬空引用、被删节点无残留）；分辨率 1344×768 已锁定且 width/height 输入 link 已断开；last_node_id / last_link_id 已更新；JSON 可正常解析
- [ ] retention_analysis 与全部参考图实际内容一致（Step 4 资产已全部就位，无占位描述残留）
- [ ] **画风一致性复核（强制闸门）**：出片前再次用 Read 并排查看本集全部角色三视图与场景图，确认渲染画风一致；不一致则**停止提交并提醒用户**（按 Step 3.2 画风闸门处理），未经用户书面确认不得带画风冲突提交

## Step 9 — 用户确认（出片确认卡）

- **总批准不豁免本步骤**：用户说"开始生成视频""直接出片"只表示进入出片阶段，不表示替用户做出方式与参数决策——Step 6 的方式选择、Step 8.1 的可选值、本步骤的费用批准仍须走完
- 将方式、参数、费用打包为**一张确认卡**一次性展示（替代逐项三问，兼顾规则与效率）：

```
【出片确认卡】
提交方式：t8lite（6A 应用 API，plus 实例）——来自注册表，可换 jp/jplite/t8balance/工作流/模板
参数：文戏（64/69=0）｜15s｜16:9 (Widescreen)｜image1-4 = 韩立/南宫婉/幕沛灵/场景
预估费用：3 集 × ~160 coins ≈ 480 coins（plus 实测基准）
payload 摘要：E01-E03，每集提示词开头 100 字
→ 确认提交？或指定任一项调整。
```

- 用户批准后才提交；任一项调整则改完重新展示确认卡
- 预估费用参考 Step 10 实测基准（plus：15s/集约 160 RH 币、400 秒），按各集时长线性估算

## Step 10 — 出片（按 Step 6 所选方式执行）

### 硬性约束

- **账户同时最多 3 个任务**：超限返回 errorCode `421`（"api queue limit reached"），多集按 ≤3 并发批次提交
- **instanceType 按时长选择（t8balance/Ref2VA/mp0.86，2026-09-18 实测）**：default（24G）必 OOM；**plus（48G）只能稳定跑 ≤10s**——13s 与 15s 即使串行独占也在 node 19 SamplerCustomAdvanced 处 `torch.OutOfMemoryError`（errorCode 805，零扣费；容量临界在 10s 与 13s 之间）；**≥13s 直接用 `ultra`（84G）**，不必先试 plus（805 零扣费但每轮浪费约 6–17 分钟轮询）
- 费用与耗时参考（2026-09 实测）：t8lite plus 15s/集约 160 RH 币、400 秒左右；t8balance 9:16/mp0.86/单参考图：**plus 10s 213—240 币、485—599 秒**（E02/E04/E05/E06/E07 实测区间）；**ultra 13s=510 币/850s、15s=604 币/1006s**（E09/E08 实测首跑，约为 plus 10s 单价的 2.1—2.5 倍）；其他时长/机型组合仍须首跑后回填，勿线性臆造

### instanceType 选择

| 类型 | 显存 | 适用 |
|---|---|---|
| `default` | 24G | 简单任务，Ref2VA 多图必 OOM |
| `plus` | 48G | **Ref2VA 10s 及以内必须用此**；mp0.86 下 13s/15s 必 OOM（805 零扣费，2026-09-18 实测） |
| `ultra` | 84G | **mp0.86 ≥13s（15s 等）用此**；成本约 plus 10s 的 2.1—2.5 倍 |

### HTTP 客户端可靠性（防重复扣费）

**规则正本见 `runninghub` 技能 SKILL.md「长任务执行规范」§2 + §3**：核心是「超时不等于未送达」——POST 挂起/超时时请求体可能已到达服务端并已创建任务，重试即重复扣费；因此**提交一律用 `curl.exe --max-time`**（禁 `requests` / `urllib` 裸提交）、**挂起后绝不立即重试**（至少等 2—3 分钟再对账）、**已拿到 taskId 的一律走续接不重提**。本节只保留本技能方式下的具体命令与兜底写法，不重复规则正文。

本技能（6A/6B/6C）提交与查询命令：

```powershell
# 提交任务
curl.exe -s -X POST 'https://www.runninghub.cn/openapi/v2/run/ai-app/{appId}' `
  -H 'Authorization: Bearer {API_KEY}' `
  -H 'Content-Type: application/json' `
  --data-binary '@payload.json' `
  --max-time 60

# 查询任务
curl.exe -s -X POST 'https://www.runninghub.cn/openapi/v2/query' `
  -H 'Authorization: Bearer {API_KEY}' `
  -H 'Content-Type: application/json' `
  -d '{\"taskId\":\"...\"}' `
  --max-time 30
```

> PowerShell 将 `curl` 别名为 `Invoke-WebRequest`，必须显式写 `curl.exe`。

如必须用 Python（curl.exe 不可用时），禁用自动重试、短超时、失败后等 180 秒：

```python
import requests, time
from requests.adapters import HTTPAdapter
session = requests.Session()
session.mount("https://", HTTPAdapter(max_retries=0))  # 禁止自动重试
try:
    resp = session.post(url, json=payload, timeout=(10, 30))  # (connect, read)
    task_id = resp.json().get("taskId")
    if task_id:
        return task_id
except Exception:
    time.sleep(180)  # 绝不立即重试——任务可能已在运行
```

### 查询与费用展示

- 查询：`POST /openapi/v2/query` body `{"taskId": ...}`，状态 QUEUED / RUNNING / SUCCESS / FAILED
- **查询响应 `results` 是列表不是字典**——按列表遍历取 `url`：

```json
{
  "taskId": "...",
  "status": "SUCCESS",
  "results": [{"url": "https://...", "nodeId": "21", "outputType": "mp4", "text": null}],
  "usage": {"consumeCoins": "164", "taskCostTime": "410"}
}
```

```python
# 正确
for o in result.get("results", []):
    url = o.get("url", "")
# 错误 — results 不是字典
result.get("results", {}).get("output", [])  # 静默失败
```

- **费用与耗时必须向用户展示**：`usage.consumeCoins`（RH 币）、`usage.taskCostTime`（秒）、`usage.consumeMoney`、`usage.thirdPartyConsumeMoney`。格式示例：`E06: DONE (410s, 164 coins)`

### 批量出片流程（以 6 集为例）

1. 提交 E01-E03（谨慎时 E01-E02）
2. **脚本内**每 20-30 秒轮询，有一个完成立即下载
3. 提交下一集填补空位（421 时等 30 秒重试）
4. 重复直到全部提交
5. 下载剩余结果

> **agent 层的等待方式另按 `runninghub` 技能「长任务执行规范」§1 执行**：脚本后台运行（非阻塞）、只在状态变化时输出一行，agent 每 **3—5 分钟**查一次且回读 `output_character_count ≤500`，禁止高频轮询回读。脚本内 20-30s 轮询与 agent 低频回读不冲突（前者是服务端查询，后者是 token 成本）。

### 衔接依赖串行出片（方案 B）

分集表标注了方案 B 的衔接集**不参与并行批量**，按依赖顺序串行：

1. 前一集 SUCCESS → 立即下载
2. **截取尾帧**：调用 `frame-extract` 技能（抽帧统一入口，直接走 OpenCV，**不要尝试 ffmpeg、不要现写 cv2 脚本**）：
   ```powershell
   python "d:\work\minimax_h3\.trae\skills\frame-extract\scripts\extract_frames.py" `
     --video "<前一集成片.mp4>" --out "<项目>\衔接帧" --last --png --name E01-E02
   ```
3. 尾帧上传 runninghub，填入衔接集 payload 的首帧图槽
4. 提交衔接集，继续轮询

方案 A 的衔接集无此限制，衔接帧已在 Step 4 生成、Step 7 上传，随批次正常提交。

### 下载与归档

- 结果 URL **仅 24 小时有效**，SUCCESS 后立即下载到 `<项目>\video\<剧名>ENN_时间戳.mp4`
- **每集下载后必须抽帧核验才允许交付**：调用 `frame-extract` 技能（抽帧统一入口，OpenCV 直抽，禁止先试 ffmpeg）。10s 成片默认 `--count 5` 均匀五帧，或 `--sheet --count 6` 出一张联系表减少读图；核验角色身份/服装、场景、动作、无多余人物、无文字水印
- 核验不通过：改提示词/参数重跑，再重新抽帧；不得跳过核验直接交付
- 每集更新 `资产清单.md` 中的 task ID 与视频路径

### 目录约定（2026-09 起）

```
<项目根>\
  assets\              共享资源总目录
    工作流模板\         6C 模板工作流
    应用注册表.md       appId/workflowId/模板 收藏夹（Step 6 选择入口）
    凡人\              IP 资源包（后续可扩展 仙逆\ 等，结构相同）
      character\       人物三视图（含 _人物资产索引.md）
      scene\           通用场景库（按标签分子目录，含场景索引）
      props\           可复用道具
  <剧名>\              项目目录
    video\             成片（<剧名>ENN_时间戳.mp4）
    任务记录\           payload（t8lite-ENN-payload.json）、上传映射（上传结果.json）、65535 任务定义（任务-*.json）
    衔接帧\             集间衔接帧（衔接帧-ENN-ENN+1.png，项目私有）
    scene\             项目私有场景
    props\             项目私有道具
```

生成图的临时下载副本即用即删，不设临时目录。

## 附录：Ref2VA 提示词结构规范

### 六段结构（固定顺序）

| 段 | 用途 |
|---|---|
| `subject_definitions` | 用 Picture 标签定义每个主体 |
| `summary` | 一段概述，含 [reference generation, keyframe completion] 标签 |
| `retention_analysis` | 指定每张参考图保留/改变什么 |
| `detailed_description` | 逐镜头时间线 + 对白 |
| `overall_soundscape` | 环境音描述 |
| `non_diegetic_music` | 背景音乐描述 |

### 对白语言规则

- 自言自语/内心独白：角色母语
- 与他人对话：故事设定语言
- 用 `<d>[Language]dialogue text</d>` 标签
- 画面内不应出现字幕

### 音频控制规则

生成**仅含音效和人声、无字幕无背景音乐**的视频时：

| 规则 | 实现 |
|---|---|
| 无字幕 | 不写任何 on-screen text；在 summary 或 detailed_description 开头声明 "No subtitles, captions, or on-screen text appear at any point in the video." |
| 无背景音乐 | `non_diegetic_music` 设为 `N/A`，不描述任何乐器或配乐 |
| 仅音效 | `overall_soundscape` 只写环境音和物理声音（风声、脚步、布料摩擦等） |
| 仅人声 | 对白用 `<Subject N> (Sx)` + `<d>[Language]text</d>`，无旁白 |

音频最小化模板：

```text
overall_soundscape: [Environmental ambience and physical sound effects only. Examples: wind, fabric rustling, footsteps, distant crowd murmurs. No music instruments, no score.]

non_diegetic_music: N/A
```

## 交付规范

- 每个文件用 computer:// 链接交付，附一句话说明
- 分集剧本交付时列出集数、时长、核心事件对照表
- 出片交付时每集附费用与耗时
- 主动建议下一步：选集出片、调提示词、补资产、换提交方式

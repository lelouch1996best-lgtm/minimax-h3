---
name: "h3-drama-producer"
description: "Turns plot outlines into multi-episode MiniMax H3 scripts, asset inventories, and ComfyUI workflow JSONs. Invoke when user provides a 剧情大纲 wanting H3 prompts, episode splits, assets, or workflows."
---

# H3 剧情视频生产流水线

根据用户提供的剧情大纲，产出：分集 H3 提示词（.md）、资产清单（.md）、定制工作流（.json）。核心原则：**每一步动手生成之前，先把关键决策问清楚，绝不跳步生成。**

## 触发条件

用户给出剧情大纲 / 故事想法 / IP 二创点子，并希望生成 H3 视频剧本、资产清单或 ComfyUI 工作流时。用户说"生成一个短剧""把大纲变成视频提示词""做工作流"等均触发。

## H3 能力边界（决策依据）

| 规格 | 值 |
|---|---|
| 单片时长上限 | 15 秒（另有 5s / 10s 档） |
| 最大画幅 | 1344×768（16:9，0.98MP） |
| 帧率 | 24fps，帧数须落在 17k+5 网格 |
| 常用帧数换算 | 5s→124 帧，10s→243 帧，15s→362 帧 |

## 流程总览

```
剧情大纲
  → Step 1 询问时长（附推荐）
  → Step 2 分集规划（>15s 时）
  → Step 3 确认输出目录名
  → Step 4 调用 prompt skill 生成剧本 → 《剧名N.md》逐集落盘
  → Step 5 检索本地人物三视图 → 资产清单.md（多张时先问用户）
  → Step 6 列出工作流模板，询问用户选哪个
  → Step 7 按模板定制生成工作流 JSON（图片经 runninghub 上传）
  → Step 8 校验 → 交付
  → Step 9 出片（可选）：t8lite 应用 API 提交生成，成片归档 video\
```

## Step 1 — 询问时长（必须先问，不问不许生成）

收到大纲后第一件事：询问目标总时长，并**主动给出推荐**。推荐口径：

- **5 秒**：单一动作、单一笑点、一帧名场面（适合切片、玩梗）
- **10 秒**：一个完整小转折（起→转→收）
- **15 秒**：一次完整的关系变化或三段式叙事（推荐默认值）
- **15 秒以上**：H3 无法单片承载，必须分集（进 Step 2）

用户报出大于 15 秒的总时长（如 45 秒、60 秒）时，不要拒绝，直接进入分集规划。

## Step 2 — 分集规划

- 每集不超过 15 秒；总时长 ÷ 15 向上取整为集数（45s→3集，60s→4集）
- 每集必须有**独立完整的小弧线**（本集开场可理解、结尾有钩子或收束），不是把一个故事硬切三段
- 设计**跨集锚点**保证系列连续感：核心道具的流转、贯穿母题（如同一轮月）、固定角色造型、集尾悬念钩子
- 分集方案先向用户展示（集数、每集副题、每集核心事件、串联锚点），用户认可后再进入生成

## Step 3 — 确认输出目录

正式输出前必须与用户确认目录名。默认在项目根下新建：

```
d:\work\minimax_h3\<剧名>\
```

用户另有指定（如 E 盘目录）时以用户为准。目录内最终交付物：

```
<剧名>1.md  <剧名>2.md  …   每集一份完整提示词（用户指定的《剧名N》命名方式）
<剧名>-分集剧本.md          总纲：分集结构表 + 跨集锚点 + 全部提示词
资产清单.md                 人物三视图路径与用途
<剧名>-工作流.json          定制工作流（按所选模板，可有多份）
```

## Step 4 — 生成剧本

按 Step 1 确定的单集时长，调用对应子技能（不要用错时长版本）：

| 单集时长 | 调用技能 |
|---|---|
| 5 秒 | `minimax-h3-prompt` |
| 10 秒 | `minimax-h3-prompt-10s` |
| 15 秒 | `minimax-h3-prompt-15s` |

- 用户未选模式（文戏/武戏/九宫格）时，先让子技能走完它的模式询问流程
- 逐集生成，每集均为可直接复制进 H3 的完整提示词：开头 `@图片N` 引用行 → "生成一段Ns、16:9、2K、原生立体声……" 正文 → 人物锁定 → 0—Ns 无缺口时间线 → 剪辑表演规则 → 视觉材质 → 声音设计 → 一致性收束
- 人物服装描述必须与 Step 5 找到的三视图实际画面一致，不得凭空想象
- 先写总纲文件，再按《剧名N.md》逐集拆分落盘

## Step 5 — 资产检索、场景索引与补图归档

### 5.1 人物三视图检索与命名规范

根据剧本中出现的人物，去用户的资产目录按**人物名找三视图**：

- 候选资产根目录（按优先级探测）：
  - 用户当场指定的目录
  - `<项目根>\fanrenCharacter\`
  - `E:\短剧平台\凡人二创\人物图\`
- 命名约定：
  - 标准全身三视图：`人物三视图（{造型}）.png`，例如 `人物三视图（校服）.png`、`人物三视图（皮夹克）.png`
  - 面部特写：`特写图.png`
  - 文字设定卡：`详细信息图.png`
- 检索方式：`Get-ChildItem <资产目录> -Recurse -File -Filter "*三视图*"`，按人物名匹配文件夹
- 找到后**用 Read 工具查看图片内容**，把实际人物形象、服装描述写入清单，并据此修正提示词中的服装描述
- **同一人物有多张三视图时，必须先询问用户选哪张**（说明各张差异，如基础版/球队版），确认后再写入
- 找不到三视图的人物在清单中如实标注"未找到"

### 5.2 场景参考图索引

高频场景应生成空镜参考图并建立索引，保证多集环境一致性：

- 场景图目录：`<项目根>\<项目名>\scene\`（或用户指定）
- 子目录按标签分类，例如 `scene\学校\`、 `scene\城市夜景\`、 `scene\餐饮\`
- 命名约定：`场景-{场景名}.png`，例如 `场景-A班教室.png`
- 索引文件：
  - `场景索引.md`（人类可读，含目录结构、标签、覆盖集数、氛围）
  - `场景索引.json`（agent 可解析，含 `tags` 数组与场景列表）
- 使用方式：与角色三视图一起上传到 runninghub，作为 Ref2VA / I2VA 的环境参考；空镜图不含人物，避免与角色绑定

### 5.3 缺失资产补全与归档

人物三视图缺失时，可按以下流程补全：

1. 以现有最接近的造型三视图为参考，用图生图方式锁定脸部/发型/身份锚点，仅修改服装。
2. 生成的新三视图按 `<资产根>\<人物名>\人物三视图（{造型}）.png` 归档（人物三视图优先归入 `fanrenCharacter`）。
3. 同步更新 `<资产根>\_人物资产索引.md` 和项目内的 `资产清单.md`。
4. 场景图缺失时，用文生图生成空镜，按 `场景-{场景名}.png` 归档并补充 `场景索引.md`。

> 安全提醒：调用外部生图服务前需向用户确认；生成结果需人工核验身份锚点（发型、瞳色、标志性配饰/妆容）是否保留。

- 输出 `资产清单.md`：人物、文件名、绝对路径、外观说明、与 H3 提示词的 @图片N 引用对应关系。清单末尾附引用示例：
  ```
  @图片1作为<人物A>身份与服装参考（<绝对路径>）
  @图片2作为<人物B>身份与服装参考（<绝对路径>）
  ```

## Step 6 — 工作流模板选择

扫描 `d:\work\minimax_h3\工作流模板\` 目录，列出可用模板并**询问用户选哪个**。已收录模板：

| 模板 | 特点 | 适用 |
|---|---|---|
| 基础模板.json | 官方 Ref2VA，自然语言提示词，9 个参考图槽，ResolutionSelector 切分辨率 | 稳定、保守画质 |
| t8加速.json | 社区模型+LoRA+SolAttn+双时钟 8 步采样，strict_prompt_tags 结构化提示词 | 快速出片、成本低 |

用户指定其他模板时，先解析该 JSON 的节点结构再定制。

## Step 7 — 工作流定制

用 Python 脚本基于所选模板生成新 JSON（脚本写完运行，验证后删除临时脚本）。通用定制项：

1. **提示词**：填入对应文本节点（CR Prompt Text）
2. **分辨率**：锁定 1344×768 到模型/条件节点，移除 ResolutionSelector 及其链路（links 和节点都要清干净）
3. **时长**：15s→362 帧；基础模板的时长用 ImpactSwitch 档位（15s=第11档），T8 模板用 PrimitiveFloat 节点（值=秒数）
4. **参考图**：剧本涉及几个人物，就接几个 LoadImage 到 ref_image_N 槽
5. **输出前缀**：改为 `MiniMaxH3/<剧名>` 便于归档

**T8 模板特别注意**（与基础模板差异大）：

- 提示词必须改写为 Ref2VA 六段结构：先调用 `h3-prompt-writing` 技能并读其 `references/ref-en.txt` 规范
- 六段顺序：subject_definitions → summary → retention_analysis → detailed_description → overall_soundscape → non_diegetic_music
- 对白格式 `<d>[Mandarin Chinese] …</d>` + 说话人编号 (S1)(S2)；画面内可见文字保留原语言
- 镜头格式：`[Shot 1]` 无时间戳开头，后续 `[Shot N] At MM:SS.mmm`
- 模板默认只有 1 个 LoadImage，第二个人物需复制该节点、分配新 id 和新 link，接入空置的 ref_image_1 槽（同时更新源节点 outputs.links、目标节点 inputs.link、links 数组、last_node_id/last_link_id）

**通用陷阱**：

- `widgets_values` 结构不统一：可能是 list、dict 或标量——修改前必须先用 Python 打印真实结构再赋值
- 帧数在 widgets_values 中的槽位因节点而异（可能 w[2] 是 height），改之前先核对节点输入定义
- 文本节点赋值保持原结构：列表就 `[PROMPT]`，标量就直接字符串

## Step 8 — 图片上传（runninghub）

工作流要用的参考图必须先经 runninghub 上传，再把返回的文件名填入 LoadImage 节点：

```python
import sys
sys.path.insert(0, r'd:\work\minimax_h3\.trae\skills\runninghub\scripts')
from runninghub import require_api_key
from runninghub_app import upload_file
key = require_api_key(None)
name = upload_file(key, r'<本地图片绝对路径>')   # 返回 api/xxx.png
```

- 先 `python <runninghub脚本> --check` 确认 API Key 有效
- 返回的 `api/xxx.png` 填入对应 LoadImage 节点的 `widgets_values[0]`
- **t8lite 应用 API（v2）需用新上传接口**：`POST https://www.runninghub.cn/openapi/v2/media/upload/binary`（form-data `file=@路径`，`Authorization: Bearer <key>`），返回 `data.fileName` 形如 `openapi/<hash>.png`，填入 nodeInfoList 的 image 字段
- 两套上传接口均内容寻址：同一文件返回相同 hash 文件名，隔天重传文件名不变
- **上传链接仅一天有效**：正式跑工作流前如隔天需重新上传
- 上传不产生费用

## Step 9 — 校验清单（生成后必做）

用 Python 校验脚本逐项检查，全部通过才交付：

- [ ] 提示词：@图片N 引用行与 LoadImage 数量、顺序一致；时间段无缺口覆盖 0—Ns
- [ ] T8 版：六段结构齐全；[Shot N] 数量正确；首镜头无时间戳、其余带 At 时间戳；对白 `<d>` 与 (Sx) 齐全
- [ ] 链路完整性：所有 links 的两端节点存在、槽位不越界、源节点 outputs 与目标节点 inputs 的 link 引用互指一致；无悬空引用；被删节点无残留
- [ ] 分辨率 1344×768 已锁定，width/height 输入 link 已断开
- [ ] 帧数正确（5s→124 / 10s→243 / 15s→362）
- [ ] last_node_id / last_link_id 已更新
- [ ] JSON 可正常解析

## Step 9 — 成片生成（t8lite 应用 API，当前首选）

剧本与工作流校验通过、**用户确认后**才提交出片。硬性约束：

- **用户 RunningHub 账户同时最多 3 个任务**：多集出片按 ≤3 并发批次提交，勿超
- **instanceType 必须用 `plus`（48G 显存）**：default（24G）跑 Ref2VA 1344×768×362 帧必在 SamplerCustomAdvanced 处 `torch.OutOfMemoryError`（2026-09 实测）
- 费用与耗时参考（plus，2026-09 实测）：15s/集约 160 RH 币、400 秒左右

### API 调用要点

- 端点：`POST https://www.runninghub.cn/openapi/v2/run/ai-app/<webappId>`，Header `Authorization: Bearer <RUNNINGHUB_API_KEY>`
- webappId 与字段以 `<项目根>\应用API文档\t8lite.md` 为准（2026-09 版：2097935043799896065）
- 文戏剧集标准 nodeInfoList：

| nodeId | fieldName | 值 | 说明 |
|---|---|---|---|
| 64 / 69 | index | "0" | 文武戏设置（0=文戏） |
| 27 | value | "15" | 时长（秒） |
| 28 | prompt | Ref2VA 六段提示词 | 与工作流 JSON 节点 36 相同（英文六段可用，<Picture N> 对应 imageN 槽） |
| 29 | aspect_ratio | "16:9 (Widescreen)" | 画幅 |
| 6, 35–42 | image | `openapi/<hash>.png` 或 "None" | image1–9 槽，按 <Picture 1..9> 顺序填，空槽填 "None" |

- 查询：`POST /openapi/v2/query` body `{"taskId": ...}`，状态 QUEUED / RUNNING / SUCCESS / FAILED
- 结果 URL **仅 24 小时有效**，SUCCESS 后立即下载到 `<项目>\video\<剧名>ENN_时间戳.mp4`
- 每集提交 payload 存档 `任务记录\t8lite-ENN-payload.json`，便于复盘与重跑

### 目录约定（2026-09 起，取代 generated-images）

```
<项目>\
  video\        成片（<剧名>ENN_时间戳.mp4）
  任务记录\      65535 任务定义（任务-*.json）、上传映射（上传结果.json）、t8lite payload、旧提示词存档
  scene\        场景正式资产（生成图正式版归档处）
  fanrenCharacter\  人物三视图正式资产
```

生成图的临时下载副本即用即删，**不再设 generated-images 临时目录**。

## 交付规范

- 每个文件用 computer:// 链接交付，附一句话说明
- 分集剧本交付时列出集数、副题、核心事件对照表
- 主动建议下一步：选集跑工作流、调提示词、换模板

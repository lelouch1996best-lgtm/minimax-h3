# Step 5 细则 · 出片（t8balance）

本文件是 SKILL.md Step 5 的展开：payload、Ref2VA 提示词结构、双人/拆片模板化、contact sheet 抽帧、费用基准。

## 5.1 决策锁定表（替 h3-drama-producer 答掉交互）

| 决策项 | 锁定值 |
|---|---|
| 输入类型 | 完整剧本（直接进分集，不再创作） |
| 输出目录 | 本集分集目录（Step 3 已建） |
| 提示词落位 | `提示词\`：单片 `E{NN}.md`，拆片段 `E{NN}A.md`/`E{NN}B.md`；成片 `video\`、配音 `voice\`、回执 `任务记录\` |
| 角色资产 | Step 4 生成图（拆片：场景图派生的各段关键帧），跳过角色/场景检索；4.5 时 node 6 三视图 + node 35 场景图 |
| 提交方式 | 6A 应用 API · t8balance |
| 画幅/像素 | 9:16 / 0.86（用户明确才改 1.0） |
| 实例 | plus（多参考负载/OOM 升 ultra） |
| 时长 | 按剧本，单片 10—15s |
| 音频 | `non_diegetic_music=N/A`、overall_soundscape 只写环境音与人声；拆片统一 BGM 延后 Step 5B |

**费用批准门**：确认卡须用户确认；goal/无人值守时指令已含费用授权（如「做完并发布」）则放行记账，否则 `update_goal(status="blocked")`。

## 5.2 拆片段衔接：关键帧预生成、并发出片（2026-09-22 起唯一路径）

拆片集所有段的 node 6 统一使用 Step 4 路径乙预生成的关键帧（`scene` 场景图 → `keyframe` 派生），流程：

1. **出片前**：场景图与全部关键帧先生成并核验通过（房间布局逐处对齐、人数正确，细则见 ref-generation §4.3/§4.4）
2. **提交时**：各段 node 6＝本段关键帧（node 35=None），**多段并发提交**（账户同时 ≤3 任务，超限 errorCode 421 自动退避），不再串行等上段成片
3. **段间接力**：段首画面＝关键帧字面首帧（summary 任务类型 `[keyframe completion]`）；相邻段的提示词按剧情接力写（B 段首句承接 A 段落点），各段 detailed_description 按本段秒表独立写

**不再截视频尾帧**：截帧是压缩低质画面，与 65535 生成图有代差，会导致后段画质劣化——这是本路径替代旧"截尾帧串行"的原因。`frame-extract` 在本流程中只用于出片后核验（contact sheet），产物**不得回流为任何段的参考图**。

特殊首帧（剧情要求某个无法由关键帧模板表达的特定画面）：按 keyframe job 单独写 `action`/`scene` 重生成该段关键帧即可，全部首帧仍走 65535 生成；不得用截帧。

## 5.3 出片脚本与长任务规范

提交/轮询/下载一律 `tools/run_t8balance.py`：任务定义 JSON（tag/提示词 md/参考图/秒数），自动完成 openapi 上传（内容寻址、登记跨集 `任务记录/上传结果.json`）、`--sync-wait 180` 同步等待、并发 ≤3（421 退避）、20s 轮询、SUCCESS 即下载、断点续跑；`--upload-only` 只传图。

跨技能通用规范正本在 `runninghub` 技能「长任务执行规范」：低 token 等待（后台跑、每 3—5 分钟查一次、回读 ≤500 字符）、防重复扣费（首提失败零扣费，隔几分钟重提同一 payload）、上传与提交留 2—5 分钟。

## 5.4 t8balance payload 骨架

注意 t8balance **无 64/69 文武戏节点**。

```json
{
  "nodeInfoList": [
    {"nodeId": "27", "fieldName": "value", "fieldValue": "<秒数：10—15，mp0.86 单片可填 15>"},
    {"nodeId": "28", "fieldName": "prompt", "fieldValue": "<Ref2VA 六段提示词>"},
    {"nodeId": "29", "fieldName": "aspect_ratio", "fieldValue": "9:16 (Portrait Widescreen)"},
    {"nodeId": "29", "fieldName": "megapixels", "fieldValue": "0.86"},
    {"nodeId": "6",  "fieldName": "image", "fieldValue": "openapi/<hash>.png  ← Step 4 生成图（拆片＝本段 keyframe 关键帧；4.5：node 6=三视图）"},
    {"nodeId": "35", "fieldName": "image", "fieldValue": "None  ← 4.5 时填场景图"},
    {"nodeId": "36", "fieldName": "image", "fieldValue": "None"},
    {"nodeId": "37", "fieldName": "image", "fieldValue": "None"},
    {"nodeId": "38", "fieldName": "image", "fieldValue": "None"},
    {"nodeId": "39", "fieldName": "image", "fieldValue": "None"},
    {"nodeId": "40", "fieldName": "image", "fieldValue": "None"},
    {"nodeId": "41", "fieldName": "image", "fieldValue": "None"},
    {"nodeId": "42", "fieldName": "image", "fieldValue": "None"}
  ],
  "instanceType": "plus",
  "usePersonalQueue": "false"
}
```

## 5.5 Ref2VA 提示词写法

六段结构（字段细则以 h3-prompt-writing 技能为正本）：`subject_definitions` → `summary` → `detailed_description`（按秒）→ `retention_analysis` → `overall_soundscape` → `non_diegetic_music`。

**通用硬要求**：

- 开头声明：`No subtitles, captions, or on-screen text appear at any point in the video.`
- realistic live-action style + first-person boyfriend-POV；画风对齐参考图现实感（生活感/手机随手拍/自然光），**不写** cinematic、shallow depth of field、8K、film-grade、studio lighting、beauty filter
- 对白：`<Subject 1> (S1) <d>[Chinese] …</d>`
- 互动逐拍译镜头内可执行动作（道具怼镜头/目光扫镜头确认/前倾半寸/摊掌索要/停一拍等回应后接招），在 summary 与 detailed_description 按秒写清，不写抽象情绪；验收口径＝成片看得出"女友在等回应、并因回应而接招"
- 男友只能用 `the off-screen person whose viewpoint the camera is` / `off-screen presence`；**禁** `her boyfriend`、`a man`、`second person`、`reaction shot of him`；男友无 `<d>` 对白
- L2 非语言音写 overall_soundscape（一声短"嗯"/半声轻笑，整段 ≤2 次、总时长 ≤1s）
- L3 手部安全措辞（interaction-playbook §7）：只手+前臂、≤0.6s、画面占比 ≤1/5、不出现脸/头/躯干
- 音频最小化：`overall_soundscape: [Environmental ambience and physical sound effects only…]`、`non_diegetic_music: N/A`；仅用户事先书面批准内置 BGM 才正常撰写

**可直接复用的英文句式**（更多见 interaction-playbook §7）：

- 怼机：`she tips the phone toward the lens as if showing him the screen, her eyes flicking to the camera once to check that he is watching`
- 等回应+接招：`she leans half an inch closer, looks straight into the lens and pauses for a beat as if waiting for his reply, then gives a small pleased nod, as if answering a silent reaction from him`
- 索要收束：`she opens her palm flat toward the camera and holds it there through the last beat, eyebrows raised, waiting for him to agree`
- 男友反应音：`a single soft low "mm" from the off-screen person whose viewpoint the camera is, followed by a light breath of laughter, kept very subtle`
- L3 手部：`for about half a second only the edge of his forearm and hand with a sleeve cuff enter the frame from the bottom edge; his face, head and body never appear, and no second person is ever visible in the frame`

## 5.6 双人/拆片模板化（省提示词环节 token）

同一剧本拆 A/B/C 段或双人多段时，**共用片段只写一次**，各段文件引用而非重抄：

- **共用 `subject_definitions`**：人物身份锚点（脸型/五官/发型发饰/服装形制，双人各一份）抽成一份定义文本，写在 A 段提示词内，B/C 段注明「subject_definitions 沿用 `提示词\E{NN}A.md` 定义，不另改」；身份措辞逐字一致，禁止各段换说法
- **共用 retention 锚点**：参考图引用与保留项（人物五官/服装/场景陈设/光线基准）同样只写一次，各段只增量写本段新增道具与动作差异
- **各段独立写**：`summary`、`detailed_description`（按本段秒表）、段尾落点；拆片段首句承接上段（接力互动）
- 双人同框：两位女友分别 S1/S2，对白各自 `<d>` 标注；互动可含两位女友之间的动作，但**对镜头（男友）的发问/索取节拍每段仍 ≥1 个**，段尾仍落回男友
- 写新段提示词时用 SEARCH 式引用旧段（直接读 A 段文件取共用文本），不要凭记忆重写身份段，避免漂移与返工

## 5.7 抽帧核验：contact sheet 一次出图（省图片 token）

不要逐帧单独截图再逐张读图。用 `frame-extract` 技能（抽帧统一入口，OpenCV 直抽，**不用 ffmpeg**）把多个时间点采样、缩放后拼成**一张联系表**，一次读图完成全段核验：

```powershell
python "d:\work\minimax_h3\.trae\skills\frame-extract\scripts\extract_frames.py" `
  --video "<成片>.mp4" --out "<分集>\任务记录" `
  --sheet --interval 1 --cols 3 --sheet-width 270
```

- `--interval 1`＝每秒 1 格（按需改 `--interval 2` 每 2 秒）；`--sheet-width 270` 缩到 270 宽省 token；`--cols 3`＝每行 3 格（按片长配合 `--count` 选格数，15s 用 15 帧 3×5、10s 用 10 帧 3×4）。联系表输出名为 `contact_sheet.jpg`，可按需重命名归档
- 一张联系表核验：身份锚点、真人质感、场景一致、无文字水印、互动节拍（怼机/对视/摊掌）、（双人）不混脸无第三人、（L3）无第二人躯干脸
- 拆片集每段各出一张；拼接点另可在合集上对 14s/29s 等接缝时间各抽一格拼一张接缝表
- 发现疑点格再针对该时间点单抽全分辨率帧细查；正常不回退到逐帧读图

## 5.8 费用与耗时基准（估算与批准门用）

| 配置 | 费用（币） | 耗时（秒） |
|---|---|---|
| plus / 9:16 / mp0.86 / 10s / 单参考（1056×1920） | 194—240 | 485—599 |
| plus / mp1.0 / 10s（1152×2080，含早期双参考因素，仅粗估） | 289—293 | 722—732 |
| 15s 干净 plus 基准 | 待首跑如实回填，不做线性臆造 | — |

早期双参考图约 258—309 币、640—770 秒；低像素实例（如 mp0.72）费用更低。余额不足时展示估算请用户充值。

# 路径 B · Ref2VA 舞蹈反推提示词写法（t8balance 三视图直采）

本文件是 dance 技能路径 B（提示词反推 + 人物三视图/场景图直采）的提示词规范与范例。
首个实测成功案例：2026-09-20 三人走廊街舞（幕沛灵 C 位 + 紫灵 + 文思月 + 学校走廊，
10s/9:16/mp0.86/plus，任务 2101519123640184834，一次过审，三人身份零串色）。

## 0. 适用前提

- 提示词写**英文**，整篇放进 markdown 的 ` ```text ` 围栏（脚本只提取围栏内容提交 node 28）。
- 参考图 = 原始三视图 PNG + 场景图，**不经过 65535 再生成**；它们只提供身份/服装/环境依据，
  绝不能让模型把三视图拼版、白底、多视图排版带进成片（必须在 summary 显式禁止）。
- Picture 编号 = 上传槽位顺序：第 1 张 node 6 → `<Picture 1>`，第 2 张 node 35 → `<Picture 2>`，
  第 3 张 node 36 → `<Picture 3>`，第 4 张 node 37 → `<Picture 4>`（场景图通常放最后）。
- 时长硬约束：mp0.86 + plus 只稳定 **≤10s**；源舞更长时按节拍截到 10s（或改 ultra）。

## 1. 反推舞蹈（先看懂再写）

1. 用 `frame-extract` 技能按 1fps 抽帧（`--interval 1 --height 480`，OpenCV 直抽，不用 ffmpeg），逐帧读动作。
2. 输出一张**节拍表**：时间点 / 队形 / 下肢动作 / 上肢手势 / 镜头 / 备注，例如：
   - 0–2.5s：C 位单人低角度腾空大跳（屈膝收腿、一臂冲天）
   - 2.5–5s：三人 V 字队形落位，高抬腿交叉步前进，手臂在脸前交叉/打开
   - 5–8s：宽站距左右律动，屈臂前刺、手腕上挑、髋部左右顶
   - 8–10s：同步侧弓步展臂定格，纱袖裙摆扇开，停半拍
3. 同时记下**必须排除的源画面元素**：手机播放 UI、状态栏、电量、暂停按钮、字幕、水印
   （用户上传的舞往往是手机录屏，这些会被模型学进画面，必须在 summary 点名禁止）。

## 2. 多角色身份锁定（路径 B 成败关键）

三视图直采没有真人参考图做外观中转，多角色时靠**双锚定**防串脸/串衣：

1. **服色强区分**：每个角色选服装主色差异最大的造型（红 / 紫 / 淡紫实测可分清；
   避免两个角色同为白/粉系）。单人舞无此问题。
2. **站位写死**：retention_analysis 每人条目里明确
   `she always occupies the LEFT/RIGHT side of the formation`，C 位写 `always stays centered`。
3. **发型/瞳色/标志性饰件**逐条列进 subject_definitions 与 retention（高髻金步摇 / 高马尾 /
   编发半扎、蓝瞳 / 紫瞳 / 棕瞳、额心坠等），三人至少有两个维度不同。
4. 场景也定义成一个 Subject（`<Subject N> is the environment in <Picture N>`），
   把空间结构、光源、材质写清；画面里若有招牌/海报，写
   `rendered as completely blank, unreadable neutral surfaces` 防乱码文字。

## 3. 提示词骨架（七段，顺序固定）

```text
subject_definitions:
<Subject 1> is ... in <Picture 1>, the center dancer: 脸型/肤色/瞳色/唇色，发型发饰，
  服装逐件描述（抹胸/纱袖/裙片/拖尾），气质定位。
<Subject 2> is ... in <Picture 2>, the left dancer: 同上，并点 LEFT。
<Subject 3> is ... in <Picture 3>, the right dancer: 同上，并点 RIGHT。
<Subject 4> is the environment in <Picture 4>: 空间透视、地面材质、墙/门窗、光源方向。

summary:
[reference generation] 一句话总览：时长/画幅/风格/几人/在哪/跳什么。
  顺时间线概述全部舞句（opens ... then ... transitions ... ends ...）。
  必须包含的硬约束：
  - native vertical 9:16, filling frame edge to edge, no black bars/pillarbox/letterbox
  - <Picture N> provide only identity/costume guidance; three-view sheet layouts and
    plain backgrounds are never reproduced
  - No phone screen interface, status bar, battery icon, subtitles, captions, watermarks,
    or on-screen text

retention_analysis:
<Subject N> (appears in [Shot x]...): fully_preserved - 该角色每一镜保留的五官/发型/服装
  清单原样复述；左右位/C 位站位再写一遍。

detailed_description:
  一段世界风格：真人电影感、肤质、运镜（手持/低角度）、光线混合、地面反射、
  纱料运动逻辑（sharp isolations vs soft fabric motion）、满帧无黑边。
[Shot 1] ... 具体动作、手脚位置、表情、布料动态、镜头、环境关系。
[Shot 2] At 00:02.500, ...（切点用 At HH:MM:SS.mmm）
[Shot 3] At 00:05.000, ...
[Shot 4] At 00:08.000, ...

overall_soundscape:
  环境音 + 动作音效（脚步/鞋底点地、纱料破空 whoosh、饰件碰撞 clink、呼吸）；
  明确 no spoken words / no phone interface sounds。

non_diegetic_music:
  BPM、曲风、配器、各切点的配乐事件（drop fill / downbeats / final hard hit）。
```

注意：

- `[Shot N]` 数量按时段切，切点时间要单调递增、总长不超过设定秒数；结尾定格写
  `hold the freeze for half a beat`。
- 对话用 `<d>[Mandarin Chinese] …</d>`（舞蹈复刻一般无对白，不用写）。
- 动作描述用舞蹈通用英文：power jump / V-formation / crossing steps / high knees /
  wide stance / bent-arm stabs / hip sways / side-lunge / freeze；每镜都带表情与视线
  （eyes locked on the camera），群舞强调 synchronized / mirror-symmetric / identical amplitude。

## 4. 完整成片范例（2026-09-20 实测版）

文件：`d:\work\minimax_h3\三视图直采复刻\提示词\trio-corridor-dance.md`
任务记录：`d:\work\minimax_h3\三视图直采复刻\任务记录\t8balance-trio-corridor-dance-{payload,submit,result}.json`
成片：`d:\work\minimax_h3\三视图直采复刻\video\三视图直采_trio-corridor-dance_20260920-120203.mp4`

该范例即本规范的完整落地，新任务直接复制其围栏内容做角色/动作/场景替换：

- 替换 subject_definitions / retention 的角色描述（身份信息以三视图**读图**为准，不信索引文字）
- 替换 detailed_description 的风格段与 4 个 [Shot] 舞句（来自本次节拍表）
- 替换 Subject 环境段为所选场景图的实际空间
- soundscape/music 跟随舞种调整（街舞 120 BPM trap；古典舞改民乐/管弦 + 丝竹 whoosh 类比）

## 5. 出片后抽帧核验（路径 B 必做，与路径 A 不同）

路径 A 不抽帧；路径 B **必须**按 1s/3s/5s/7s/9s（及结尾）抽帧人眼核验，因为动作是提示词生成的：

1. 每个角色身份一致（不换脸/不串衣/服色位置正确）
2. 舞句与节拍表吻合（跳/进/律动/定格四个阶段都在）
3. 场景透视正确、无三视图拼版白底泄漏
4. 无手机 UI/字幕/水印/黑边
5. 无多臂多腿等畸形（高速挥臂处允许自然运动模糊）

不合格 → 针对问题改提示词对应段重跑（身份问题强化 retention 与站位锚定；动作问题改 [Shot]
描述；时长/805 问题换 ultra）。抽帧统一用 `frame-extract` 技能（OpenCV，`--times 1,3,5,7,9`
或 `--sheet` 联系表），不再使用 ffmpeg。

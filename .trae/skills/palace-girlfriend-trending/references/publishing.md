# Step 7 细则 · 双平台发布（B 站 + 抖音）

首选一条命令（2026-09-19 起固化，多项目通用，`--project` 默认 palace）：

```powershell
python d:\work\minimax_h3\tools\publish_episode.py --episode E{NN}
```

自动完成：定位分集目录与成片/封面 → 解析《E{NN}-双平台发布文案.txt》→ B 站投稿（`--submit web` + `--extra-fields` 一次带创作声明）→ B 站回读 → 抖音投稿（自主声明表单选定，识别短信风控门并原地等 `verify_code.txt`）→ 抖音回读 → 落 `任务记录/publish_result.json` + 生成 `publish_taizhang_block.md`。

参数：`--platform bilibili|douyin`、`--dry-run`、`--verify-only --bili-aid <aid>`、`--dy-code <6位码>`、`--delete-bili AID=<id>`（不可逆）。
**前置**：分集根部文案包必须存在（脚本不生成创意文案；缺则调用 `publish-copywriting` 技能撰写），缺失报错退出。

## 硬暂停门：抖音短信验证码

日志出现「📱 检测到短信验证码弹窗」「已点击获取验证码」后：

1. **立即停止当前回合一切工具调用**（不读盘/不轮询/不重试），把「请查看手机短信，把 6 位验证码发我」作为回合终点，保持等待
2. goal/无人值守：先 `update_goal(status="blocked")`（说明等抖音验证码）再结束回合
3. 收到码后**无 BOM 写入**：`[System.IO.File]::WriteAllText('D:\work\social-auto-upload\verify_code.txt', '<验证码>')`（Set-Content -Encoding UTF8 带 BOM 必然失败；上传器读后自动删文件）
4. 日志「🥳 视频发布成功」即可；验证码被污染重试后会失效，别反复提交
5. 禁止未收到码前继续执行/轮询/自动重试

## 7.0 发布前准备

| 项 | 约定 |
|---|---|
| sau 路径 | `D:\work\social-auto-upload\.venv\Scripts\sau.exe`（绝对路径，不 cd） |
| B 站账号 | `bilibili_main`（韩老魔的女友们） |
| 抖音账号 | `creator` |
| 登录态 | 各跑 `sau <平台> check --account <账号>`；B 站 check=invalid 多为 bldsa 线路证书过期（非 cookie 失效），直接 `--line bda2` 试投，直连也失败才修 cookie |
| 成片 | 拆片合集用 `E{NN}.mp4`；单片用原生成片 `video\宫装女友E{NN}_时间戳.mp4` |
| 封面 | **直接用 Step 4 参考图 PNG**（双平台同一张，不从成片截帧）；脚本优先取文案包头部「封面」行指定图，未指定才按文件名选；**未采用的参考图候选移出 `images\`**（移 `任务记录\`）；接口拒收 PNG 才转 JPG |
| 抽帧工具 | `frame-extract` 技能（Python+OpenCV，不使用 ffmpeg） |

平台文案差异：

| | B 站 | 抖音 |
|---|---|---|
| 标题 | ≤80 字，剧名+集号 | ≤30 字，口语钩子（sau 自动截 30） |
| 分区 | `--tid 47` | 无 |
| 标签/话题 | 10—12 个，第 1 个建议热搜原文（可含空格） | **最多 5 个，多了必乱码**；第 1 个＝热搜原文原样 |
| 版权 | 自制+禁转载 | 无 |
| AI 声明 | 投稿时一次带入（`--submit web --extra-fields`） | `--declaration "内容由AI生成"` 表单选定 |
| 发布 | 立即/定时 | 立即/定时 `--schedule "YYYY-MM-DD HH:MM"` |

## 7.1 B 站发布（手工兜底）

底层统一走全局脚本，不手拼 biliup：`c:\Users\Administrator\.trae-cn\skills\sau-upload\scripts\bili_publish.py`。API 层细节（转义坑、vupre 回读、删除端点）以 sau-upload 技能「Bilibili 创作声明」节为全球唯一权威版本。

```powershell
python "c:\Users\Administrator\.trae-cn\skills\sau-upload\scripts\bili_publish.py" upload `
  --file "<成片>" --title "<标题>" --desc "<简介>" `
  --tags "<标签1,标签2,...>" --cover "<参考图PNG>" --tid 47
```

- 固定：`--submit web` + `--extra-fields '{"creation_statement":{"id":1}}'`（`--submit app` 不带字段）；账号 bilibili_main；`--line bda2`
- 回读：`verify --aid <aid>`，`decl_id==1` 且 `state==0`；兜底 `set-decl`；清理 `delete --aid`（回读 state=-100）
- 发布后 `GET https://api.bilibili.com/x/web-interface/view?bvid=<bvid>` 确认 code=0
- 定时稿 state=30；用户手动提前发布不重复发

## 7.2 抖音发布（手工兜底）

```powershell
& 'D:\work\social-auto-upload\.venv\Scripts\sau.exe' douyin upload-video `
  --account creator --file "<成片>" --headless `
  --title "<≤30字>" --desc "<简介>" `
  --tags "<话题1>" "<话题2>" "<话题3>" "<话题4>" "<话题5>" `
  --thumbnail "<封面PNG>" --declaration "内容由AI生成"
```

- 声明天然一次到位（日志「🧾 自主声明已选择」在发布成功前），无事后补设
- 默认无头；页面卡死/弹窗不渲染才换有头或停掉重发，重发前先 API 查重避免发两遍
- **成功不看退出码**：exit 0/1（沙箱阻止日志写入时 Bad file descriptor）都正常，以日志「视频发布成功」+API 回读为准
- 回读：`GET https://creator.douyin.com/web/api/media/aweme/post/?aid=2906&count=10&cursor=0&type=1&publish_time_type=0&need_charge_info=false`（cookie + Referer creator.douyin.com）；取 `aweme_list[0].aweme_id`，链接 `https://www.douyin.com/video/{aweme_id}`，查 desc 话题与 `status.is_private/is_delete/in_reviewing/is_prohibited`；刚发布 self_see=True 等 1 分钟复查

## 7.3 抖音话题：5 上限 + 热搜原文

- **硬上限 5 个话题实体**：第 6 个起不转换且 IME 把中文打乱码，平台限制，重试/放慢无效
- 构成：①热搜标题原文原样（一字不改/不缩写/不换近义）②剧名 1 个 ③IP 名 1—2 个 ④品类泛标签 1 个
- **取词机械规则（不改词）**：含空格只去空格；含 `·｜：，` 取分隔符前主段或去符连体；仍不可用取最长完整短语；超约 20 字在词边界截完整前半；被平台拒或无可搜索性退化为原题核心原词并台账注明
- 文案包 `## 抖音` 块内必须**编号列表** `N. #话题名`（脚本解析硬要求；写成单行可能解析为空→零话题发布）；文案包「热点」行与第 1 话题字面一致，回读核对
- 已发布乱码/零话题修复：作品编辑页（`https://creator.douyin.com/creator-micro/content/post/video?mid={aweme_id}&enter_from=edit_item`），清空 `div.zone-container[contenteditable="true"]` 后 **`keyboard.insert_text()` 粘贴整段绕过 IME**，只留 5 话题提交；老 modify API 已失效只能 UI 改

## 7.4 发布收尾

两平台回读后报告：链接、标题、AI 声明状态、封面、话题、公开状态；坑记入总纲；更新台账（Step 8）。

## 项目目录结构

```
d:\work\minimax_h3\韩老魔的宫装女友\
  宫装女友-总纲.md            跨集台账+发布记录（只留根目录）
  资产清单.md                 参考图/成片/发布块总登记（只留根目录）
  任务记录\上传结果.json       RunningHub 上传回执（跨集复用）
  E{NN}-{关键词}\             单片集，六子目录：
    剧本\E{NN}-{关键词}-剧本.md
    提示词\E{NN}.md
    images\E{NN}_{角色}_{场景}.png    node 6 唯一主参考（兼封面）
    video\宫装女友E{NN}_时间戳.mp4    单片即最终件（无BGM）
    video\E{NN}_验收抽帧_*.jpg        按需
    voice\*.mp3
    任务记录\t8balance-E{NN}-{payload,submit,result}.json
    E{NN}-双平台发布文案.txt
  E{NN}A-{关键词}上\ E{NN}B-{关键词}下\   拆片段目录，各含六子目录：
    提示词\E{NN}A.md / E{NN}B.md
    images\E{NN}A_keyframe.png            本段关键帧（本段 node 6，由场景图派生；禁止截视频帧）
    video\宫装女友E{NN}A_时间戳.mp4
    任务记录\t8balance-E{NN}A-*.json
  E{NN}-{关键词}合集\
    images\E{NN}_scene_{场景}.png          全片一张文生图场景空镜（各关键帧的第一基准）
    video\E{NN}_拼接.mp4 → E{NN}.mp4
    任务记录\  concat_list、merge_summary、BGM result.json
```

E01/E02 历史结构（`BGM\` 子目录、A1/A2 分段、无前缀图名、封面候选、旧文案名）不强改，重发按实际路径取。

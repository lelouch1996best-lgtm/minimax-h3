#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publish_episode.py — 双平台发布固化脚本（B站 + 抖音）· 多项目通用

把「B站投稿（含创作声明一次带入）-> B站回读核验 -> 抖音投稿 -> 抖音回读核验
-> 生成台账块」固化为一条命令，仅依赖 Python 标准库。

**多项目通用**（2026-09-19 起）：`--project` 选择项目（默认 palace）。各项目的目录名、
子目录名、成片/封面命名、账号差异全部收敛在下面的 `PROJECTS` 配置里，脚本主体不再写死
任何单一系列的字面量——新系列只需在 `PROJECTS` 里加一条。

| project | 项目目录 | 集号 | 参考图目录 | 发布版成片 | 抖音账号 |
|---|---|---|---|---|---|
| `palace` | 韩老魔的宫装女友 | `E{NN}` | `images\\` | `E{NN}.mp4` | creator |
| `dance` | 韩老魔的歌舞团 | `D{NN}` | `images\\`（**项目级**，2026-09-20 起） | `D{NN}.mp4` | douyin_dance |

设计依据（2026-09-19 实测，详见 SKILL 7.1/7.2）：
  * B站创作声明必须用 `--submit web --extra-fields '{"creation_statement":{"id":1}}'`
    一次带入；`--submit app` 不携带该字段，会退化成「投稿后再补刀」。
  * 抖音天然一次到位（sau 浏览器自动化，发布表单内选自主声明），无事后补设。
  * 抖音可能弹短信验证码风控门：脚本会识别并在此等待 verify_code.txt（无 BOM 写入）。

典型用法：
  # 1) 双平台发布（自动读分集目录里的《E{NN}-双平台发布文案.txt》）
  python publish_episode.py --episode E09

  # 2) dance 系列（D{NN} 集号 + 参考图\\ 目录 + douyin_dance 账号）
  python publish_episode.py --project dance --episode D01

  # 3) 只看将要执行的命令，不真正发布
  python publish_episode.py --episode E09 --dry-run

  # 4) 只发 B站
  python publish_episode.py --episode E09 --platform bilibili

  # 5) 已知短信验证码，直接带上（避免等待）
  python publish_episode.py --episode E10 --platform douyin --dy-code 123456

  # 6) 只回读核验已发布稿件（不发布）
  python publish_episode.py --episode E09 --verify-only

  # 7) 清理误投/测试稿件
  python publish_episode.py --delete-bili aid=117296378943400

  # 8) 用另一个 B站账号发（不改 PROJECTS，只在本次生效）
  python publish_episode.py --episode E09 --bili-account hehuajiu
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------- 配置

PROJECT_ROOT = Path(r"d:\work\minimax_h3")
SAU_EXE = Path(r"D:\work\social-auto-upload\.venv\Scripts\sau.exe")
COOKIE_DIR = Path(r"D:\work\social-auto-upload\cookies")
VERIFY_CODE_FILE = Path(r"D:\work\social-auto-upload\verify_code.txt")

TID = "47"                      # 动画·短片/同人
BILI_LINE = "bda2"              # bldsa 线路证书过期，固定走 bda2
AI_DECLARATION = "内容由AI生成"

# 项目配置：新系列只加一条，脚本主体不写死系列字面量
PROJECTS = {
    "palace": {
        "cn": "宫装女友（韩老魔的宫装女友）",
        "dir": "韩老魔的宫装女友",
        "image_dir": "images",          # 参考图（兼封面）目录
        "video_dir": "video",
        "record_dir": "任务记录",
        # 成片优先级（数字小者优先）：5B 混音发布版 E{NN}.mp4 > 原始成片 > 合集 > 无BGM素材
        "video_prefer": ["{ep}.mp4"],
        "video_prefix": "宫装女友{ep}_",
        "cover_exclude": "场景",         # 4.5 场景图 `..._场景.png` 不作封面
        "bili_account": "bilibili_main",
        "dy_account": "creator",
        "dy_cookie": "douyin_creator.json",
    },
    "dance": {
        "cn": "韩老魔的歌舞团（舞蹈复刻）",
        "dir": "韩老魔的歌舞团",
        # 2026-09-20 用户指定：dance 全部生成图落**项目级** images\（跨任务复用），不再用分集 参考图\
        "image_dir": "images",
        "image_dir_at_root": True,
        "video_dir": "video",
        "record_dir": "任务记录",
        # D{NN}.mp4 = Step 5 混音发布版；D{NN}_舞蹈迁移.mp4 = 迁移成片（自带源舞原声）
        "video_prefer": ["{ep}.mp4"],
        "video_prefix": "{ep}_舞蹈迁移",
        "cover_exclude": "",
        "bili_account": "bilibili_main",
        "dy_account": "douyin_dance",
        "dy_cookie": "douyin_douyin_dance.json",   # sau 命名规则＝douyin_{account}.json（2026-09-20 D02 实测校正）
    },
    # 2026-10-07 新增：合集类项目（整片一个文件，非分集目录）。
    # 用法：python publish_episode.py --project guoqing --dir "韩老魔的国庆接待"
    # episode 由目录名推出（无「-」时即目录名本身），成片在 `成片\`、封面与文案在 `发布\`。
    "guoqing": {
        "cn": "韩老魔的国庆接待（7 集合集 · 三平台）",
        "dir": "韩老魔的国庆接待",
        "image_dir": "发布",
        "video_dir": "成片",
        "record_dir": "任务记录",
        "video_prefer": ["{ep}-全片.mp4"],
        "video_prefix": "{ep}-全片",
        "cover_exclude": "",
        "bili_account": "bilibili_main",
        # 2026-10-07 用户指定：抖音改用「秦洛喝花酒」（sau account=qinluo_huajiu）。
        # 注意该账号同时是快手账号名，且平台昵称与 sau account 名**不同名**
        # （sau 用拼音 qinluo_huajiu，平台昵称是中文「秦洛喝花酒」）。
        "dy_account": "qinluo_huajiu",
        "dy_cookie": "douyin_qinluo_huajiu.json",
        # 2026-10-09 快手「秦洛喝花酒」账号已注销 → 统一改用「秦洛」
        "ks_account": "秦洛",               # 快手账号（CLI 无 AI 声明参数）
    },
    # 2026-10-08 新增：《这就叫专业》抖音源片复刻（8 段合集 · 三平台）。
    # 同 guoqing 结构：成片在 `成片\`，封面与文案在 `发布\`。
    # ⚠️ 抖音源片有烧录字幕 → 复刻版按「默认成片不出字幕」红线**无字幕**，
    #    仅保留台词音轨 + 后期节拍词，无字幕版更符合三平台审核（AI 声明 + 无字幕更安全）。
    "zjzhi": {
        "cn": "这就叫专业（韩立×银月 · 8 段合集 · 三平台）",
        "dir": "这就叫专业",
        "image_dir": "发布",
        "video_dir": "成片",
        "record_dir": "任务记录",
        "video_prefer": ["{ep}-全片.mp4"],
        "video_prefix": "{ep}-全片",
        "cover_exclude": "",
        "bili_account": "bilibili_main",
        "dy_account": "qinluo_huajiu",
        "dy_cookie": "douyin_qinluo_huajiu.json",
        # 2026-10-09 快手「秦洛喝花酒」已注销 → 改「秦洛」（当前快手唯一账号，免闸门）
        "ks_account": "秦洛",
    },
    # 2026-10-09 新增：恶搞系列第五集《一脚踹碎》（原创仙侠恶搞 · 三平台）。
    # 成片在 `法天象地\成片\成片.mp4`（45.63s 竖屏），封面与文案在 `法天象地\发布\`。
    # ⚠️ episode 固定为「第五集」（目录名推导会得到 "第五集"，故video_prefix 用空串匹配成片.mp4）。
    "eg5": {
        "cn": "一脚踹碎法天象地（恶搞仙侠第5集 · 三平台）",
        "dir": "法天象地",
        "image_dir": "发布",
        "video_dir": "成片",
        "record_dir": "任务记录",
        "video_prefer": ["{ep}.mp4"],
        "video_prefix": "",
        "cover_exclude": "",
        # 2026-10-09 华先生指定：B站=喝花酒（个人主号）、抖音=qinluo_huajiu、快手=秦洛（第2 个号）
        "bili_account": "喝花酒",
        "dy_account": "qinluo_huajiu",
        "dy_cookie": "douyin_qinluo_huajiu.json",
        "ks_account": "秦洛",
    },
    # 2026-10-09 新增：灵动表情系列《看够了吗》（南宫婉×幕沛灵 · 面部特写 · 三平台）。
    # 成片在 `南宫婉灵动表情\成片\1.mp4`（30.17s 竖屏，两条 15s 拼接），封面与文案在同目录 `发布\`。
    # ⚠️ episode 固定为「1」（成片名为纯数字 1.mp4，无集号前缀）→ video_prefix 用空串匹配。
    "lingdong": {
        "cn": "看够了吗（南宫婉×幕沛灵 · 灵动表情 · 三平台）",
        "dir": "南宫婉灵动表情",
        "image_dir": "发布",
        "video_dir": "成片",
        "record_dir": "任务记录",
        "video_prefer": ["{ep}.mp4"],
        "video_prefix": "",
        "cover_exclude": "_src_",
        # 2026-10-09 华先生指定：B站=bilibili_main、抖音=creator、快手=秦洛
        "bili_account": "bilibili_main",
        "dy_account": "creator",
        "dy_cookie": "douyin_creator.json",
        "ks_account": "秦洛",
    },
    # 2026-10-11 新增：《一脚踩出的坑爹时刻》第1集（韩立 · 原创恶搞 · 四平台）。
    # 成片在 `成片\1.mp4`（40.15s 竖屏 1080×1944，含 S3 台词字幕），封面与文案在 `发布\`。
    # ⚠️ episode 固定为「1」（成片名纯数字 1.mp4）→ video_prefix 用空串匹配。
    # 四平台账号（2026-10-11 用户指定）：B站=bilibili_main、抖音=qinluo_huajiu、快手=秦洛、小红书=秦洛。
    "kengdie": {
        "cn": "一脚踩出的坑爹时刻（韩立 · 原创恶搞 · 四平台）",
        "dir": "一脚踩出的坑爹时刻",
        "image_dir": "发布",
        "video_dir": "成片",
        "record_dir": "任务记录",
        "video_prefer": ["{ep}.mp4"],
        "video_prefix": "",
        "cover_exclude": "_src_",
        "bili_account": "bilibili_main",
        "dy_account": "qinluo_huajiu",
        "dy_cookie": "douyin_qinluo_huajiu.json",
        "ks_account": "秦洛",
        "xhs_account": "秦洛",
    },
}

CFG = PROJECTS["palace"]        # main() 里按 --project 覆盖


def series_dir():
    return PROJECT_ROOT / CFG["dir"]


UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

DOUYIN_GATE_HINTS = ("检测到短信验证码", "获取验证码", "短信验证码")

if hasattr(sys.stdout, "buffer"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def log(msg):
    print(msg, flush=True)


def show_cmd(cmd):
    return subprocess.list2cmdline([str(c) for c in cmd])


# ---------------------------------------------------------------- 通用

def http_json(url, headers, data=None, method=None):
    body = None
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers,
                                method=method or ("POST" if body else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode("utf-8", "ignore")[:300]}
    except Exception as e:                                   # noqa: BLE001
        return {"error": str(e)}


def load_cookies(path):
    """返回 (cookie_header, jar, token_info)"""
    raw = json.load(open(path, encoding="utf-8"))
    cookies = raw.get("cookie_info", {}).get("cookies") or raw.get("cookies") or []
    header = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
    return header, raw


# ---------------------------------------------------------------- 多账号闸门

LIST_ACCOUNTS_HELPER = Path(
    r"c:\Users\Administrator\.workbuddy\skills\sau-upload\scripts\list_accounts.py")


def available_accounts(platform):
    """读 cookies/ 目录，返回该平台的账号名列表。复用 skill 脚本，避免两处逻辑分叉。"""
    if not LIST_ACCOUNTS_HELPER.exists():
        return None                                  # 脚本缺失 → 不拦截（不误伤）
    import importlib.util
    spec = importlib.util.spec_from_file_location("sau_list_accounts", LIST_ACCOUNTS_HELPER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    data = mod.list_accounts(platform)
    return [it["account"] for it in data.get(platform, [])]


def gate_multi_account(platform):
    """返回需要用户确认的提示行列表；空列表 = 无需确认。

    规则（2026-10-08 华先生明令）：某平台本地有 ≥2 个账号时，
    即使 PROJECTS 里有默认值，也必须先让用户选，不允许默默发。
    """
    notes = {
        "bilibili_main": "韩老魔的宫装女友",
        "xiongda": "熊大爱吃青菜",
        "喝花酒": "秦洛爱喝花酒（用户个人主号）",
        "creator": "抖音主号",
        "douyin_dance": "韩老魔的歌舞团",
        "qinluo_huajiu": "秦洛喝花酒",
        "秦洛": "快手/小红书账号（2026-10-09 起唯一快手账号；2026-10-10 登录的小红书同账号名）",
    }
    targets = []
    if platform in ("both", "three", "four", "bilibili"):
        targets.append(("bilibili", CFG["bili_account"]))
    if platform in ("both", "three", "four", "douyin"):
        targets.append(("douyin", CFG["dy_account"]))
    if platform in ("three", "four", "kuaishou"):
        targets.append(("kuaishou", CFG.get("ks_account", "")))
    if platform in ("four", "xiaohongshu"):
        targets.append(("xiaohongshu", CFG.get("xhs_account", "")))

    lines = []
    for plat, current in targets:
        accts = available_accounts(plat)
        if not accts or len(accts) < 2:
            continue                                   # 0 个（未登录）或 1 个（唯一账号）→ 免问
        lines.append(f"[{plat}] 本机有 {len(accts)} 个账号：")
        for a in accts:
            mark = "  ← 当前默认" if a == current else ""
            note = notes.get(a, "")
            lines.append(f"    - {a}{'（' + note + '）' if note else ''}{mark}")
    if not lines:
        return []
    lines += [
        "",
        "处理方式（二选一）：",
        "  A) 重新运行并显式指定，例如：",
        "     --bili-account <账号> --dy-account <账号> --ks-account <账号>",
        "  B) 已在别处跟用户确认过账号，补 --confirm-accounts跳过闸门",
        "或先跑全量枚举：python tools/publish_episode.py --list-accounts",
    ]
    return lines


# ---------------------------------------------------------------- 定位分集资产

def resolve_episode(episode=None, directory=None):
    if directory:
        d = Path(directory)
        if not d.is_dir():
            raise SystemExit(f"[X] 目录不存在：{d}")
        return d
    sd = series_dir()
    hits = sorted(p for p in sd.glob(f"{episode}-*") if p.is_dir())
    if not hits:
        raise SystemExit(f"[X] 未找到分集目录 {episode}-* （在 {sd}）")
    if len(hits) > 1:
        log(f"[!] 匹配到多个目录，取第一个：{[h.name for h in hits]}")
    return hits[0]


def resolve_video(ep_dir, episode):
    """选成片，2026-09-20 起按 BGM 规矩收窄后的口径：

    单片集 → **原生成片**（`宫装女友E{NN}_时间戳.mp4`）优先，混音版不再参与；
    拆片集/多段合集 → 该目录内只有拼接件与混音版，取混音发布版 `E{NN}.mp4`。
    """
    vdir = ep_dir / CFG["video_dir"]
    if not vdir.is_dir():
        raise SystemExit(f"[X] 无 video 目录：{vdir}")
    mp4s = [p for p in vdir.glob("*.mp4")]
    if not mp4s:
        raise SystemExit(f"[X] video 目录下没有 mp4：{vdir}")

    prefer = [t.format(ep=episode) for t in CFG["video_prefer"]]
    prefix = CFG["video_prefix"].format(ep=episode)

    def rank(p):
        n = p.name
        if n.startswith(prefix):
            return 0                                  # 原始成片（单片集发布件，优先）
        if n in prefer:
            return 1                                  # 混音发布版（拆片集/多段合集的合集目录内）
        if "合集" in n and "NM" not in n:
            return 2
        if "NM" in n:
            return 9                                  # 无 BGM 素材，不优先
        return 5

    mp4s.sort(key=lambda p: (rank(p), p.name))
    return mp4s[0]


def resolve_cover(ep_dir, episode, prefer=""):
    """封面解析：优先用文案包「封面」行指定的图（2026-09-20 起），否则按文件名取第一张。

    prefer：文案包头部「封面」行里的路径（绝对路径或相对项目根/分集根），空则忽略。
    """
    if prefer:
        cand = Path(prefer)
        tries = [cand] if cand.is_absolute() else [series_dir() / cand, ep_dir / cand]
        for c in tries:
            if c.is_file():
                return c
        log(f"[!] 文案包指定的封面不存在（{prefer}），改用自动选取")
    idir = ep_dir / CFG["image_dir"]
    if CFG.get("image_dir_at_root") or not idir.is_dir():
        # dance：生成图统一落项目级 images\（跨任务复用）；palace 维持分集目录
        idir = series_dir() / CFG["image_dir"]
    imgs = [p for p in idir.glob(f"{episode}*.png")]
    if not imgs:
        imgs = [p for p in idir.glob("*.png")]
    if not imgs:
        # 2026-10-09：封面生成器可能落 .jpg（如 tools/ngw_mpl_make_cover.py）→ 补一轮 jpg
        imgs = [p for p in idir.glob(f"{episode}*.jpg")]
    if not imgs:
        imgs = [p for p in idir.glob("*.jpg")]
    ex = CFG.get("cover_exclude") or ""
    if ex:
        imgs = [p for p in imgs if ex not in p.name]
    if not imgs:
        raise SystemExit(f"[X] 未找到封面参考图：{idir}")
    imgs.sort(key=lambda p: p.name)
    return imgs[0]


# ---------------------------------------------------------------- 文案包解析

DOUYIN_TOPIC_LIMIT = 5                 # 抖音话题硬上限（多传必乱码，见 SKILL 7.3）


def _clean_topics(seq):
    out, seen = [], set()
    for t in seq:
        t = re.sub(r"\s+", "", str(t)).strip("`*·、,，#＃|｜\"'“”")
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def parse_topics(dy_block, full_text):
    """解析抖音话题，返回 (topics, warnings)。

    规范格式＝编号列表 `1. #话题名`（SKILL 7.3，2026-09-19 起）；兼容单行 `#a #b #c` 与逗号串。
    并校验话题中是否含文案包头部「热点」行的热搜标题原文（用户 2026-09-19 指定：热搜标题原样做话题）。
    """
    warn = []
    m = re.search(r"^-\s*\**\s*话题[^：:]*[：:]\s*(.+?)(?=^-\s|\Z)", dy_block, re.S | re.M)
    raw = m.group(1).strip() if m else ""

    nums = re.findall(r"^\s*\d+[.、]\s*#?\s*(.+?)\s*$", raw, re.M)
    if nums:
        topics = _clean_topics(nums)
    else:
        body = re.sub(r"[（(][^）)]*[)）]", " ", raw or dy_block)   # 去掉「（硬上限 5 个）」这类注记
        topics = _clean_topics(re.findall(r"#([^#\s,，、|｜]+)", body))
        if not topics:
            topics = _clean_topics(re.split(r"[,，、\s]+", body))

    if len(topics) > DOUYIN_TOPIC_LIMIT:
        warn.append(f"话题 {len(topics)} 个超硬上限 {DOUYIN_TOPIC_LIMIT}，仅取前 {DOUYIN_TOPIC_LIMIT} 个："
                    + " ".join("#" + t for t in topics[:DOUYIN_TOPIC_LIMIT]))
        topics = topics[:DOUYIN_TOPIC_LIMIT]
    if not topics:
        warn.append("未解析到话题：抖音块请写成编号列表 `1. #话题名`（见 SKILL 7.3）；本次将不带话题发布")

    head = re.split(r"^##\s", full_text, flags=re.M)[0]
    hot = _clean_topics(re.findall(r"[「『](.+?)[」』]", head))
    if hot and topics and not any(t in hot for t in topics):
        warn.append(f"话题里没有热搜标题原文（如「{hot[0]}」）：按 SKILL 7.3，第 1 个话题应为热搜标题原样")
    return topics, warn


def parse_copy_file(ep_dir, episode):
    """解析《E{NN}-双平台发布文案.txt》；缺失则返回 {}"""
    # 2026-10-07：放宽为任意「*发布文案*.txt」（原先写死「双平台」，
    # 三平台/单平台文案包匹配不到 → 回退到无文案分支）
    cands = list(dict.fromkeys(
        sorted(ep_dir.glob(f"{episode}-*发布文案*.txt"))
        + sorted(ep_dir.glob("*发布文案*.txt"))))
    if not cands:
        return {}, None
    path = cands[0]
    text = path.read_text(encoding="utf-8", errors="replace")

    def block(name):
        # 标题行可带前缀/后缀（如「## 一、B 站（账号：xxx）」「## 二、抖音」），只要含关键字即可
        m = re.search(rf"^##[^\n]*{name}[^\n]*$(.*?)(?=^##[^\n]*$|\Z)", text, re.S | re.M)
        return m.group(1) if m else ""

    def field(body, label):
        # 兼容 `- 标题（≤30 字）：` 与 `- **标题**（≤30 字）：` 两种写法
        m = re.search(rf"^-\s*\**\s*{label}[^：:]*[：:]\s*(.+?)(?=^-\s|\Z)", body, re.S | re.M)
        return m.group(1).strip() if m else ""

    def dewrap(s):
        """去掉 markdown 反引号与多余空白（文案包常把值写成 `...`，多行简介每行都带反引号）"""
        return re.sub(r"\s+", " ", str(s).replace("`", " ")).strip()

    def multi(body, label):
        """简介可能多行，压成一行"""
        return dewrap(field(body, label))

    dy, bili, ks = block(r"抖音"), block(r"B\s*站"), block(r"快手")
    xhs = block(r"小红书")
    topics, topic_warn = parse_topics(dy, text)
    for w in topic_warn:
        log(f"[!] 抖音话题：{w}")
    tags_raw = field(bili, r"标签")
    tags = [t for t in (dewrap(x) for x in re.split(r"[,，]", tags_raw)) if t]

    # 头部「封面」行：支持 `路径` 包裹或裸路径（.png/.jpg），供 resolve_cover 优先使用
    head = re.split(r"^##\s", text, flags=re.M)[0]
    cm = (re.search(r"封面[^\n]*?`([^`]+?\.(?:png|jpg|jpeg))`", head, re.I)
          or re.search(r"封面[^\n]*?([^\s`（(]+\.(?:png|jpg|jpeg))", head, re.I))
    cover_pref = cm.group(1).strip() if cm else ""

    out = {
        "cover": cover_pref,
        "douyin": {
            "title": multi(dy, r"标题"),
            "desc": multi(dy, r"简介"),
            "topics": topics,
        },
        "bilibili": {
            "title": multi(bili, r"标题"),
            "desc": multi(bili, r"简介"),
            "tags": tags,
        },
        # 2026-10-07：快手块（可选；无该块时 title 为空，调用方按需跳过）
        "kuaishou": {
            "title": multi(ks, r"标题"),
            "desc": multi(ks, r"简介"),
            "tags": [t for t in (dewrap(x) for x in re.split(r"[,，]", field(ks, r"标签"))) if t],
        },
        # 2026-10-11：小红书块（可选；无该块时 title 为空，调用方按需跳过）
        "xiaohongshu": {
            "title": multi(xhs, r"标题"),
            "desc": multi(xhs, r"简介"),
            "tags": [t for t in (dewrap(x) for x in re.split(r"[,，]", field(xhs, r"标签"))) if t],
        },
    }
    return out, path


# ---------------------------------------------------------------- B 站
# B 站底层机制统一复用全局技能脚本，避免两处实现分叉：
#   c:\Users\Administrator\.trae-cn\skills\sau-upload\scripts\bili_publish.py

BILI_HELPER = Path(r"c:\Users\Administrator\.trae-cn\skills\sau-upload\scripts\bili_publish.py")


def _load_bili_helper():
    if not BILI_HELPER.exists():
        raise SystemExit(f"[X] 缺少全局 B站发布脚本：{BILI_HELPER}\n"
                         f"    请确认 sau-upload 技能已安装（其 scripts/bili_publish.py）")
    import importlib.util
    spec = importlib.util.spec_from_file_location("bili_publish", BILI_HELPER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bili = _load_bili_helper()


def bili_upload(video, cover, title, desc, tags, dry_run=False):
    """投稿（--submit web 一次带入创作声明）；具体实现在全局 bili_publish.py"""
    log("\n=== B 站投稿（web 接口，创作声明一次带入） ===")
    res = bili.upload(str(video), title, desc, tags, cover=str(cover),
                      tid=TID, account=CFG["bili_account"], line=BILI_LINE, dry_run=dry_run)
    if not dry_run and res.get("submit_interface") == "app":
        res["warn"] = "走成了 APP 接口，创作声明不会一次带入！"
    return res


def bili_verify(aid):
    return bili.verify(aid, account=CFG["bili_account"])


def bili_delete(aid):
    return bili.delete(aid, account=CFG["bili_account"])


# ---------------------------------------------------------------- 抖音

def douyin_upload(video, cover, title, desc, topics, dy_code=None, dry_run=False,
                  code_timeout=900):
    cmd = [
        str(SAU_EXE), "douyin", "upload-video",
        "--account", CFG["dy_account"],
        "--file", str(video),
        "--headless",
        "--title", title[:30],
        "--desc", desc,
        "--tags", ",".join(topics[:5]),                    # 硬上限 5 个
        "--thumbnail", str(cover),
        "--declaration", AI_DECLARATION,
    ]
    log("\n=== 抖音投稿（sau 浏览器自动化，自主声明随表单一次选定） ===")
    log("  " + show_cmd(cmd))
    if dry_run:
        return {"dry_run": True, "cmd": cmd}

    if dy_code:
        VERIFY_CODE_FILE.write_text(str(dy_code), encoding="utf-8")   # 无 BOM

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", bufsize=1)
    gate_seen = False
    gate_wait_deadline = None
    tail = []
    for line in proc.stdout:
        line = line.rstrip("\n")
        log("  " + line)
        tail.append(line)
        if not gate_seen and any(h in line for h in DOUYIN_GATE_HINTS):
            gate_seen = True
            gate_wait_deadline = time.time() + code_timeout
            log("\n" + "!" * 62)
            log("!! 抖音短信验证码风控门已触发（硬暂停）")
            log("!! 请查看手机短信，把 6 位验证码写入：")
            log(f"!!   {VERIFY_CODE_FILE}     （必须是 UTF-8 无 BOM）")
            log(f"!! 脚本将在此等待最多 {code_timeout // 60} 分钟，写入后自动继续。")
            log("!" * 62 + "\n")
        if gate_seen and not VERIFY_CODE_FILE.exists():
            if time.time() > gate_wait_deadline:
                proc.kill()
                return {"gate_timeout": True, "raw_tail": "\n".join(tail[-40:])}
            time.sleep(2)
    proc.wait()
    out = "\n".join(tail)

    res = {"returncode": proc.returncode, "gate_seen": gate_seen,
           "published": "视频发布成功" in out, "raw_tail": out[-600:],
           "cover": cover_status_from_log(out)}
    if "自主声明已选择" in out:
        res["declaration_selected"] = True
    return res


def douyin_verify(limit=6):
    cookie, raw = load_cookies(COOKIE_DIR / CFG["dy_cookie"])
    hdr = {"User-Agent": UA, "Cookie": cookie,
           "Referer": "https://creator.douyin.com/creator-micro/content/manage"}
    params = {"aid": "2906", "count": str(limit), "cursor": "0", "type": "1",
              "publish_time_type": "0", "need_charge_info": "false"}
    url = "https://creator.douyin.com/web/api/media/aweme/post/?" + urllib.parse.urlencode(params)
    j = http_json(url, hdr)
    out = []
    for a in (j.get("aweme_list") or []):
        desc = a.get("desc") or ""
        st = a.get("status") or {}
        out.append({
            "aweme_id": a.get("aweme_id"),
            "desc": desc,
            "topics": re.findall(r"#([^#\s]+)", desc),
            "public": not st.get("self_see"),
            "reviewing": st.get("in_reviewing"),
            "private": st.get("is_private"),
            "url": f"https://www.douyin.com/video/{a.get('aweme_id')}",
        })
    return out


# ---------------------------------------------------------------- 快手
# 2026-10-07 新增。注意：`sau kuaishou upload-video` **没有 --declaration 参数**
# （抖音有，快手没有）→ AI 生成标注无法随表单带入，需人工在创作者后台确认。

def kuaishou_upload(video, cover, title, desc, tags, dry_run=False):
    cmd = [
        str(SAU_EXE), "kuaishou", "upload-video",
        "--account", CFG["ks_account"],
        "--file", str(video),
        "--headless",
        "--title", title,
        "--desc", desc,
        "--tags", ",".join(tags[:6]),
        "--thumbnail", str(cover),
    ]
    log("\n=== 快手投稿（sau；CLI 无 AI 声明参数，需后台人工确认） ===")
    log("  " + show_cmd(cmd))
    if dry_run:
        return {"dry_run": True, "cmd": cmd}

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", bufsize=1)
    tail = []
    for line in proc.stdout:
        line = line.rstrip("\n")
        log("  " + line)
        tail.append(line)
    proc.wait()
    out = "\n".join(tail)
    hit = [k for k in ("发布成功", "投稿成功", "上传成功", "作品已发布") if k in out]
    return {"returncode": proc.returncode, "published": bool(hit),
            "matched": hit, "cover": cover_status_from_log(out), "raw_tail": out[-800:]}


def kuaishou_verify():
    """快手无开放回读接口（对比抖音 creator API），只能以 sau 日志 + 人工后台复核为判据。"""
    return {"note": "快手 CLI 无回读接口；以投稿日志 + 创作者后台人工复核为准"}


# ---------------------------------------------------------------- 小红书
# 2026-10-11 新增。`sau xiaohongshu upload-video` **没有 --declaration 参数**
# （抖音有，快手/小红书都没有）→ AI 生成标注无法随表单带入，需人工在创作者后台确认。
# shell 里现成的 4 平台发布：`--platform four` 会依次跑 B站 → 抖音 → 快手 → 小红书。

def xiaohongshu_upload(video, cover, title, desc, tags, dry_run=False):
    cmd = [
        str(SAU_EXE), "xiaohongshu", "upload-video",
        "--account", CFG.get("xhs_account", ""),
        "--file", str(video),
        "--headless",
        "--title", title[:20],                             # 小红书标题显示上限 20 字
        "--desc", desc,
        "--tags", ",".join(tags[:10]),                     # 话题 ≤10 个（写正文/走 tags）
        "--thumbnail", str(cover),
    ]
    log("\n=== 小红书投稿（sau；CLI 无 AI 声明参数，需后台人工确认） ===")
    log("  " + show_cmd(cmd))
    if dry_run:
        return {"dry_run": True, "cmd": cmd}

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", bufsize=1)
    tail = []
    for line in proc.stdout:
        line = line.rstrip("\n")
        log("  " + line)
        tail.append(line)
    proc.wait()
    out = "\n".join(tail)
    hit = [k for k in ("发布成功", "投稿成功", "上传成功", "作品已发布", "发布完成") if k in out]
    return {"returncode": proc.returncode, "published": bool(hit),
            "matched": hit, "cover": cover_status_from_log(out), "raw_tail": out[-800:]}


def xiaohongshu_verify():
    """小红书无开放回读接口（同快手），以 sau 日志 + 创作者后台人工复核为判据。"""
    return {"note": "小红书 CLI 无回读接口；以投稿日志 + 创作者后台人工复核为准"}


# ---------------------------------------------------------------- 封面状态解析
# 2026-10-11：sau 已能回读封面是否真的生效（快手：回读预览图；小红书：回读缩略图）。
# 生效/失败都会打结构化日志 → 台账不再无脑写「封面同上」，改按日志如实标注。
COVER_OK_MARKERS = ("封面已应用", "封面已经设置完成", "封面已上传到预览")
COVER_FAIL_MARKERS = ("封面未生效", "待人工处理")


def cover_status_from_log(out: str):
    """从 sau 输出判定封面应用结果：'ok' / 'fail' / None（未回读到）。"""
    if any(m in out for m in COVER_FAIL_MARKERS):
        return "fail"
    if any(m in out for m in COVER_OK_MARKERS):
        return "ok"
    return None


def _cover_phrase(res):
    c = (res or {}).get("cover")
    if c == "ok":
        return "封面已应用 ✅"
    if c == "fail":
        return "**封面未生效 🚨（需人工到创作者后台更换）**"
    return "封面状态未知（CLI 未回读）"


# ---------------------------------------------------------------- 台账块

def build_markdown(episode, bili_res, bili_ver, dy_res, dy_items, copy_path,
                   video, cover, ep_dir, ks_res=None, xhs_res=None):
    now = time.strftime("%Y-%m-%d %H:%M")

    def rel(p):
        """转项目相对路径。--dir 可能传相对路径（如 `这就叫专业`），
        直接 relative_to(绝对 series_dir()) 会抛 ValueError（2026-10-08 踩到）→ 先绝对化。"""
        try:
            return str(Path(p).resolve().relative_to(series_dir().resolve())).replace("\\", "/")
        except ValueError:
            return str(p).replace("\\", "/")
    lines = [f"- **发布状态（{now} 已发布）**："]
    if bili_res and not bili_res.get("dry_run"):
        bvid = bili_res.get("bvid", "?")
        aid = bili_res.get("aid", "?")
        lines.append(
            f"- **B站投稿**：账号 {CFG['bili_account']!r}，bvid **{bvid}**，aid {aid}，"
            f"https://www.bilibili.com/video/{bvid} ；state {bili_ver.get('state')}"
            f"（{bili_ver.get('state_desc')}），创作声明 **id={bili_ver.get('decl_id')}"
            f"（{bili_ver.get('decl_text')}）**；分区 tid {bili_ver.get('tid')}，"
            f"{bili_ver.get('tags')} 标签，封面=`{rel(cover)}`；`--submit web` 一次带入声明")
    if dy_res and not dy_res.get("dry_run") and dy_items:
        d = dy_items[0]
        lines.append(
            f"- **抖音投稿**：账号 {CFG['dy_account']!r}，aweme_id **{d['aweme_id']}**，{d['url']} ；"
            f"公开={d['public']}，话题 {len(d['topics'])} 个「{' '.join('#' + t for t in d['topics'])}」"
            f"，{_cover_phrase(dy_res)}，自主声明「{AI_DECLARATION}」随发布表单一次选定"
            + ("；**触发短信验证码门**" if (dy_res or {}).get("gate_seen") else "；未触发短信风控门"))
    if ks_res and not ks_res.get("dry_run"):
        lines.append(
            f"- **快手投稿**：账号 {CFG.get('ks_account')!r}，日志判定 "
            f"{'已发布' if ks_res.get('published') else '**未确认发布**'}"
            f"（命中关键词 {ks_res.get('matched') or '无'}），{_cover_phrase(ks_res)}"
            f"；⚠️ **CLI 无 AI 声明参数**，需后台人工确认是否补「AI 生成」标注")
    if xhs_res and not xhs_res.get("dry_run"):
        lines.append(
            f"- **小红书投稿**：账号 {CFG.get('xhs_account')!r}，日志判定 "
            f"{'已发布' if xhs_res.get('published') else '**未确认发布**'}"
            f"（命中关键词 {xhs_res.get('matched') or '无'}），{_cover_phrase(xhs_res)}"
            f"；⚠️ **CLI 无 AI 声明参数**，需后台人工确认是否补「AI 生成」标注")
    if copy_path:
        lines.append(f"- 发布文案：`{rel(copy_path)}`")
    lines.append(f"- 成片：`{rel(video)}`")
    return "\n".join(lines)


# ---------------------------------------------------------------- main

def main():
    global CFG
    ap = argparse.ArgumentParser(description="双平台发布固化脚本（B站 + 抖音）· 多项目通用")
    ap.add_argument("--project", default="palace", choices=sorted(PROJECTS),
                    help="项目：palace 宫装女友（默认）/ dance 歌舞团；决定项目目录、子目录名与账号")
    ap.add_argument("--episode", help="集号，如 E09（palace）/ D01（dance）")
    ap.add_argument("--dir", help="直接指定分集目录（覆盖 --episode 定位）")
    # 2026-10-07：新增 three（B站+抖音+快手）与 kuaishou 单平台。
    # `both` 保持原语义（B站+抖音）不变，保证 palace / dance 行为零变化。
    ap.add_argument("--platform", default="both",
                    choices=["both", "three", "four", "bilibili", "douyin", "kuaishou", "xiaohongshu"],
                    help="both=B站+抖音（默认，原语义）；three=+快手；four=B站+抖音+快手+小红书；或单平台")
    ap.add_argument("--bili-account", help="覆盖项目的 B站账号标签（如 hehuajiu）；"
                                           "对应 cookies\\bilibili_<标签>.json，不改动 PROJECTS 原表")
    ap.add_argument("--dry-run", action="store_true", help="只打印将要执行的命令")
    ap.add_argument("--verify-only", action="store_true", help="只回读核验，不发布")
    ap.add_argument("--bili-aid", type=int, help="配合 --verify-only 指定 B站 aid")
    ap.add_argument("--dy-code", help="抖音 6 位短信验证码（已知时直接带上）")
    ap.add_argument("--code-timeout", type=int, default=900, help="等待验证码秒数，默认 900")
    ap.add_argument("--delete-bili", metavar="AID=<id>", help="删除指定 B站稿件（不可逆）")
    # 2026-10-08 华先生明令：多账号平台发布前必须先给用户选账号，不能默默用默认值。
    ap.add_argument("--list-accounts", action="store_true",
                    help="列出本机各平台已登录账号后退出（发布前必跑）")
    ap.add_argument("--accounts-platform",
                    choices=["douyin", "kuaishou", "xiaohongshu", "bilibili"],
                    help="配合 --list-accounts 限定平台（注意与 --platform 不同：后者是发布目标）")
    ap.add_argument("--check", action="store_true",
                    help="配合 --list-accounts：逐个调 sau check 验证登录态")
    ap.add_argument("--json", action="store_true",
                    help="配合 --list-accounts：机器读输出")
    ap.add_argument("--dy-account", help="覆盖项目的抖音账号（多账号时必须显式指定）")
    ap.add_argument("--ks-account", help="覆盖项目的快手账号")
    ap.add_argument("--xhs-account", help="覆盖项目的小红书账号")
    ap.add_argument("--confirm-accounts", action="store_true",
                    help="确认已就账号选择做过用户确认，跳过多账号拦截")
    # 2026-10-09：同一目录存在多个成片/多份文案包时（如法天象地 45s 版与 24s 版并存），
    # 按名字排序会选错 → 显式指定绝对路径，不再依赖匹配。
    ap.add_argument("--video", help="显式指定成片绝对路径（覆盖 resolve_video 自动选取）")
    ap.add_argument("--copy", help="显式指定发布文案包绝对路径（覆盖自动匹配）")
    args = ap.parse_args()

    if args.list_accounts:
        # 子进程跑（不能用 runpy：会把宿主 sys.argv 一并带进去）
        if not LIST_ACCOUNTS_HELPER.exists():
            raise SystemExit(f"[X] 缺少账号枚举脚本：{LIST_ACCOUNTS_HELPER}")
        cmd = [sys.executable, str(LIST_ACCOUNTS_HELPER)]
        if args.accounts_platform:
            cmd += ["--platform", args.accounts_platform]
        if args.check:
            cmd.append("--check")
        if args.json:
            cmd.append("--json")
        return subprocess.call(cmd)

    CFG = PROJECTS[args.project]
    if args.bili_account or args.dy_account or args.ks_account or args.xhs_account:
        # 复制一份再改写，避免污染 PROJECTS 原表（同一进程内多项目复用时的隐患）
        CFG = dict(CFG)
        for key, val in (("bili_account", args.bili_account),
                         ("dy_account", args.dy_account),
                         ("ks_account", args.ks_account),
                         ("xhs_account", args.xhs_account)):
            if val:
                CFG[key] = val
                log(f"{key}：已覆盖为 {val!r}")
    log(f"项目：{CFG['cn']}（{CFG['dir']}）")

    if args.delete_bili:
        aid = int(re.sub(r"^\D*", "", args.delete_bili))
        log(f"删除 B站稿件 aid={aid} ...")
        log(json.dumps(bili_delete(aid), ensure_ascii=False))
        log("回读：" + json.dumps(bili_verify(aid), ensure_ascii=False))
        return 0

    if not args.episode and not args.dir:
        ap.error("需要 --episode 或 --dir")

    ep_dir = resolve_episode(args.episode, args.dir)
    episode = args.episode or ep_dir.name.split("-")[0]
    log(f"分集目录：{ep_dir}")

    if args.verify_only:
        if args.bili_aid:
            log("B站回读：" + json.dumps(bili_verify(args.bili_aid), ensure_ascii=False, indent=2))
        log("抖音回读：")
        for d in douyin_verify():
            log(f"  {d['aweme_id']} public={d['public']} topics={d['topics']}\n    {d['desc'][:60]}")
        return 0

    copy_data, copy_path = parse_copy_file(ep_dir, episode)
    # 2026-10-09：--copy 显式指定文案包（如同目录并存多版本文案）
    if args.copy:
        p = Path(args.copy)
        if not p.is_file():
            raise SystemExit(f"[X] --copy 指定的文案包不存在：{p}")
        copy_data = parse_copy_file(p.parent, p.name.split("-")[0])[0] or {}
        copy_path = p
    # 2026-10-09：把文案包原文带进 copy_data，供分平台封面解析复用各平台块的「封面」行。
    if copy_path and copy_path.is_file():
        copy_data["_raw"] = copy_path.read_text(encoding="utf-8", errors="replace")
    if copy_path:
        log(f"文案包：{copy_path.name}")
    else:
        log("[!] 未找到发布文案包，将要求命令行提供标题/简介（本脚本不含创作文案）")

    video = resolve_video(ep_dir, episode)
    # 2026-10-09：--video 显式指定成片（同目录并存精简版/完整版时用）
    if args.video:
        v = Path(args.video)
        if not v.is_file():
            raise SystemExit(f"[X] --video 指定的成片不存在：{v}")
        video = v
    cover = resolve_cover(ep_dir, episode, copy_data.get("cover", ""))
    log(f"成片：{video.name}（{video.stat().st_size:,} 字节）")
    log(f"封面：{cover.name}" + ("（文案包指定）" if copy_data.get("cover") else "（自动选取）"))

    # 2026-10-09：B站要 16:9、抖音/快手要 3:4 —— 三平台不能共用同一张封面。
    # 文案包头部/各平台块里若写了 `- **封面**：` 路径，优先按平台取；否则在封面所在目录
    # 按「封面_{平台名}」或含平台关键词的文件名找；都没有则退回共用cover。
    def _cover_for(platform_keys, base_cover):
        block_body = ""
        for name in platform_keys:
            m = re.search(rf"^##[^\n]*{name}[^\n]*$(.*?)(?=^##[^\n]*$|\Z)",
                          copy_data.get("_raw", ""), re.S | re.M)
            if m:
                block_body = m.group(1)
                break
        cm = (re.search(r"封面[^\n]*?`([^`]+?\.(?:png|jpg|jpeg))`", block_body, re.I)
              or re.search(r"封面[^\n]*?([^\s`（(]+\.(?:png|jpg|jpeg))", block_body, re.I))
        if cm:
            cand = Path(cm.group(1).strip())
            for c in ([cand] if cand.is_absolute()
                      else [series_dir() / cand, ep_dir / cand]):
                if c.is_file():
                    return c
        cdir = base_cover.parent
        pats = [f"封面_{k}" for k in platform_keys] + list(platform_keys)
        for pat in pats:
            hits = sorted(cdir.glob(f"*{pat}*.jpg")) + sorted(cdir.glob(f"*{pat}*.png"))
            if hits:
                return hits[0]
        return base_cover

    cover_dy = _cover_for(["抖音", "dy"], cover)
    cover_ks = _cover_for(["快手", "kuaishou"], cover)
    cover_xhs = _cover_for(["小红书", "xhs"], cover)
    if (cover_dy != cover) or (cover_ks != cover) or (cover_xhs != cover):
        log(f"分平台封面：抖音={cover_dy.name}　快手={cover_ks.name}　小红书={cover_xhs.name}")

    by, bl = copy_data.get("douyin", {}), copy_data.get("bilibili", {})
    if not bl.get("title"):
        raise SystemExit("[X] 解析不到 B站标题，请检查文案包格式或改用人工发布")

    # 2026-10-08 华先生明令：多账号平台发布前必须先让用户选账号。
    # PROJECTS 里的账号只是历史默认值，不代表用户本次的选择 —— 未显式确认就中止。
    if not args.confirm_accounts and not args.dry_run:
        gate = gate_multi_account(args.platform)
        if gate:
            raise SystemExit(
                "\n".join(["[X] 多账号平台未确认账号，已中止发布（--dry-run 不受此限制）", ""]
                          + gate))

    bili_res = bili_ver = None
    dy_res = None
    dy_items = []

    if args.platform in ("both", "three", "four", "bilibili"):
        bili_res = bili_upload(video, cover, bl["title"], bl["desc"], bl["tags"],
                               dry_run=args.dry_run)
        if not args.dry_run and bili_res.get("aid"):
            log("\n--- B站回读核验 ---")
            time.sleep(3)
            bili_ver = bili_verify(bili_res["aid"])
            log(json.dumps(bili_ver, ensure_ascii=False, indent=2))
            ok = bili_ver.get("decl_id") == 1
            log(f">>> 创作声明核验：{'PASS（一次到位）' if ok else 'FAIL —— 需走兜底补设'}")

    if args.platform in ("both", "three", "four", "douyin"):
        if not by.get("title"):
            raise SystemExit("[X] 解析不到抖音标题")
        dy_res = douyin_upload(video, cover_dy, by["title"], by["desc"], by["topics"],
                               dy_code=args.dy_code, dry_run=args.dry_run,
                               code_timeout=args.code_timeout)
        if not args.dry_run and dy_res.get("gate_timeout"):
            log("[X] 等待验证码超时，抖音未发布；写入 verify_code.txt 后重跑本命令")
        elif not args.dry_run:
            log("\n--- 抖音回读核验 ---")
            time.sleep(5)
            dy_items = douyin_verify()
            for d in dy_items[:2]:
                log(f"  {d['aweme_id']} public={d['public']} topics={len(d['topics'])} -> {d['topics']}")

    ks_res = None
    if args.platform in ("three", "four", "kuaishou"):
        ksd = copy_data.get("kuaishou", {})
        if not ksd.get("title"):
            log("[!] 文案包无快手块（或缺标题），跳过快手")
        else:
            ks_res = kuaishou_upload(video, cover_ks, ksd["title"], ksd.get("desc", ""),
                                     ksd.get("tags", []), dry_run=args.dry_run)
            if not args.dry_run:
                log("\n--- 快手核验 ---")
                log("  " + json.dumps(kuaishou_verify(), ensure_ascii=False))
                log("  （快手无开放回读接口，请以创作者后台为准）")

    xhs_res = None
    if args.platform in ("four", "xiaohongshu"):
        xsd = copy_data.get("xiaohongshu", {})
        if not xsd.get("title"):
            log("[!] 文案包无小红书块（或缺标题），跳过小红书")
        else:
            xhs_res = xiaohongshu_upload(video, cover_xhs, xsd["title"], xsd.get("desc", ""),
                                         xsd.get("tags", []), dry_run=args.dry_run)
            if not args.dry_run:
                log("\n--- 小红书核验 ---")
                log("  " + json.dumps(xiaohongshu_verify(), ensure_ascii=False))
                log("  （小红书无开放回读接口，请以创作者后台为准）")

    if args.dry_run:
        return 0

    # 结果落盘 + 台账块
    this_run = {
        "episode": episode,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "video": str(video), "cover": str(cover),
        "bilibili": {"upload": bili_res, "verify": bili_ver},
        "douyin": {"upload": dy_res, "recent": dy_items[:2]},
        "kuaishou": {"upload": ks_res},
        "xiaohongshu": {"upload": xhs_res},
    }
    rec = ep_dir / CFG["record_dir"]
    rec.mkdir(exist_ok=True)
    result_file = rec / "publish_result.json"

    # 2026-10-11：单平台补发必须与既有台账**合并**，不得覆盖 ——
    # 补发快手时曾把 B站/抖音/小红书的完整记录冲成只剩快手。
    prev = {}
    if result_file.exists():
        try:
            prev = json.loads(result_file.read_text(encoding="utf-8"))
        except Exception:
            prev = {}

    def _keep(key):
        """本轮该平台没发（upload 为空）→ 沿用既有记录。"""
        cur = this_run[key]
        if not cur.get("upload"):
            old = prev.get(key)
            if old and old.get("upload"):
                log(f"[i] 本轮未发布 {key}，台账沿用既有记录")
                return old
        return cur

    platforms = ("bilibili", "douyin", "kuaishou", "xiaohongshu")
    result = dict(this_run)
    for _k in platforms:
        result[_k] = _keep(_k)

    if any(result[_k] is not this_run[_k] for _k in platforms):
        # 有沿用项 = 本轮属补发：保留首发时间，另记本轮时间
        result["time"] = prev.get("time", this_run["time"])
        result["last_run_time"] = this_run["time"]

    result_file.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    md = build_markdown(episode,
                        result["bilibili"].get("upload"),
                        result["bilibili"].get("verify") or {},
                        result["douyin"].get("upload"),
                        result["douyin"].get("recent") or [],
                        copy_path, video, cover, ep_dir,
                        ks_res=result["kuaishou"].get("upload"),
                        xhs_res=result["xiaohongshu"].get("upload"))
    (rec / "publish_taizhang_block.md").write_text(md, encoding="utf-8")
    log("\n=== 台账块（可直接粘贴进总纲/资产清单，亦已存 任务记录/publish_taizhang_block.md） ===")
    log(md)
    log(f"\n结果：{rec / 'publish_result.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

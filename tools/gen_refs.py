#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_refs.py — 凡人 IP 真人质感参考图批量生成（65535 gpt-image-2 图生图固化脚本）

把「拼提示词 → 提交 → 轮询 → 下载 → 审核拒绝重试」固化为一条命令，仅标准库。
2026-09-19 由 E11 临时脚本升格固化；同日按 profile 参数化，**dance 与 palace 两系列共用**
（palace-girlfriend-trending 近景 / dance 全身舞蹈参考）。
2026-09-20 按用户指定：`fullbody` 追加**正面照**硬约束（正脸正身、不侧身不回眸），
因为动作迁移模型需要看到人物正面，侧身/回眸的参考图会导致出片认不出正脸。

基准正本 = d:\work\minimax_h3\assets\真人质感美术基准.md（改基准先改正本，再同步本脚本）。

典型用法
--------
  # 1) 写任务定义 JSON（每段一条 job，字段见下方 JOBS 说明）
  # 2) 生成（断点续跑：同命令再执行即可，已 done 的 job 跳过）
  python tools/gen_refs.py --jobs E12-refs.json \
      --out "<分集目录>\\images" --rec "<分集目录>\\任务记录"

  # dance 系列（全身构图）：job 里写 "profile": "fullbody"，或整体覆盖
  python tools/gen_refs.py --jobs D01-refs.json --profile fullbody \
      --out "<任务目录>\\参考图" --rec "<任务目录>\\任务记录"

  # 双人同框（palace 双女主集，2026-09-20 E12 起）：
  #   首选「多图直传」：job 里写 "profile": "portrait_duo"，"sanyi": [左角色三视图, 右角色三视图]，
  #   prompt 用位置指认身份（第 1 张＝某人、第 2 张＝另一人）；2026-09-20 E12 实测接口接受数组并正常出图
  #   备选「拼版单图」：先用 PIL 把两张三视图左右拼成一张（左 A 右 B、无文字），再按单图传入
  python tools/gen_refs.py --jobs E12-refs.json --out "<分集目录>\\images" --rec "<分集目录>\\任务记录"

  # 审核拒绝的 job 改词/换造型后重试
  python tools/gen_refs.py --jobs E12-refs.json --out ... --rec ... --redo

  # 只看提示词不提交
  python tools/gen_refs.py --jobs E12-refs.json --out ... --rec ... --dry-run

任务定义 JSON（列表，每项一个 job）
----------------------------------
  [
    {
      "tag":  "E12A",                              # 段号/任务名（回执命名用）
      "out":  "E12A_李缨宁_闺房夜窗鱼灯.png",        # 归档文件名（落 --out 目录）
      "sanyi": "d:\\...\\人物三视图（宫装）.png",     # 源三视图（身份基准）；可传路径列表＝多张直传（双人同框用）
      "lock": "严格保持参考图中同一女性的面部五官、脸型、发型发饰与服装形制不变（以参考图为唯一身份基准，不换人、不改发型与服装形制）；她身着参考图中那套淡粉金双色传统宫装，层叠飘逸广袖，宫髻配发饰。",
      "age":  "一位明确的成年女性，气质温婉沉稳。",     # 年龄/气质锚点（可省，用默认）
      "scene": "……",                               # 剧本场景（要素具体化）
      "action": "……",                              # 动作/情绪（默认句式「人物正在…」）
      # —— 可选：profile 与槽位覆盖（缺省 profile=portrait，行为与历史一致）——
      "profile": "portrait",                       # portrait 近景(默认) / fullbody 全身(dance)
      "light": "烛光/窗光/灯笼光/室内暖灯",           # 现场光源举例（缺省取 profile 默认）
      "action_line": "人物正在…，姿态自然如被随手抓拍…",  # 整句覆盖动作行（dance 用）
      "negative_extra": "……",                      # 追加反向约束（缺省取 profile 附加）
      # —— 审核拒绝回退（可选，推荐填上，E11 教训）——
      "fallback_sanyi": "d:\\...\\人物三视图（红色宫装）.png",  # 同角色另一造型三视图
      "fallback_lock":  "……她身着参考图中那套红色系传统宫装……"  # 换造型后的身份锁定段
    }
  ]

审核拒绝重试链（自动，无需人工干预）
----------------------------------
  attempt 1：原始 prompt
  attempt 2：改年龄/气质措辞（三十岁上下 + 沉稳端庄，E07 解法）
  attempt 3：换 fallback_sanyi 同角色另一造型（E11 解法，最省）
  仍拒 → 标记 failed 并提示走 SKILL.md §4.5 双参考备用方案（勿再用 65535 硬试）
  三解法链正本：assets\\真人质感美术基准.md §7.3

模板说明：真人质感段与反向约束段照抄上述基准正本 §6，勿精简。
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.request

API = "https://task-api-1-cn.65535.space"
DEFAULT_AGE = "一位明确的成年女性，气质温婉沉稳。"
AGE_RETRY = "一位三十岁上下的成年女性，气质沉稳端庄、温和持重。"

# ---------------------------------------------------------------- 基准模板
# 正本：d:\work\minimax_h3\assets\真人质感美术基准.md（dance 与 palace 两系列唯一权威源）
# 本脚本只把该基准落成可执行模板。改基准请先改正本 §6，再同步此处，勿在 SKILL.md 里另抄一份。
# profile 差异只有两处：构图段 {composition} 与 profile 附加反向约束 {negative_extra}。

COMPOSITION_PORTRAIT = """竖屏 9:16 单人画面，第一人称男友视角平视近景，人物位于画面中央；
生活照式的自然取景：允许轻微倾斜、留白不均、不完全居中的构图，但人物始终是画面主体、面部完整清晰。
画面只保留一个人物，三视图排版仅作身份参考，不要出现拼贴/多视图/白背景。"""

COMPOSITION_DUO = """竖屏 9:16 双人同框画面，第一人称男友视角平视近景，两位女性并排位于画面中景（一人略前一人略后错开），
两人的面部都完整清晰、互不遮挡；生活照式的自然取景：允许轻微倾斜、留白不均、不完全居中，但两位始终是画面主体。
画面只保留这两位女性，不出现第三个人物；三视图/设定稿排版仅作身份参考，不要出现拼贴/多视图/白背景。"""

COMPOSITION_FULLBODY = """竖屏 9:16 单人全身画面，人物从头到脚完整入画，脚底不裁切，全身占画面主体，构图自然；
人物正面朝向镜头、正脸正身（不侧身、不背身、不回眸），五官与身形正面清晰可辨；
生活照式的自然取景：允许轻微倾斜、留白不均、不完全居中，但人物始终是画面主体、面部与全身清晰。
画面只保留一个人物，三视图排版仅作身份参考，不要出现拼贴/多视图/白背景。"""

REALISM = """这要像一张自然的生活照：{person}，真实到像是现实中随手拍下的一张照片，
而不是影棚拍摄、商业时尚大片或 CG 渲染。真实亚洲女性皮肤质感，可见毛孔、细小绒毛、
自然泛红与微小瑕疵，保留柔和的阴影过渡；面部比例与骨相真实，不放大眼睛、不改脸型、
不做磨皮美颜，保留眉/眼/脸颊/嘴部左右轻微不对称；头发有飞散碎发、不均匀发束与轻微毛躁，
不是根根分明的发丝；现场光源自然（{light}），皮肤上有真实明暗；
手机随手拍的观感：允许轻微手持抖动带来的柔焦、轻微噪点与锐化痕迹、略粗糙的分辨率，
不使用高端相机的大片感，背景不刻意虚化、环境细节清晰可辨；
表情自然克制（浅笑或放松的中性表情），姿态是"被随手拍到的瞬间"而不是摆拍；
身材与身体比例真实，不做夸张曲线与模特级修图。"""

NEGATIVE_COMMON = """避免：CGI、3D 渲染、娃娃皮肤、瓷肌、过度磨皮、美颜 App 瘦脸大眼、眼睛过大、面部完全对称、
睫毛过度锐化、油蜡感高光、影棚打光、商业时尚大片、刻意轮廓光、极端背景虚化、过度 HDR、
毛孔纹理过度锐化、不真实的解剖比例；
画面无任何文字、字幕、水印、logo，无第二个人物，无现代物品穿帮；
手与手指的数量、关节、长度、交叠与握持合理（无多指、无粘连）；
首饰不重复不悬空、不穿模，背景陈设不变形不重复。"""

# 双人同框版：只把「无第二个人物」改为「只有这两位女性、无第三个人物」，其余逐字一致
NEGATIVE_DUO = """避免：CGI、3D 渲染、娃娃皮肤、瓷肌、过度磨皮、美颜 App 瘦脸大眼、眼睛过大、面部完全对称、
睫毛过度锐化、油蜡感高光、影棚打光、商业时尚大片、刻意轮廓光、极端背景虚化、过度 HDR、
毛孔纹理过度锐化、不真实的解剖比例；
画面无任何文字、字幕、水印、logo，**画面只有这两位女性、不出现第三个人物**，无现代物品穿帮；
手与手指的数量、关节、长度、交叠与握持合理（无多指、无粘连、无多余的手）；
两位女性不得合并为一张脸、不得互换身份、不得出现第三个身影或镜中重影；
首饰不重复不悬空、不穿模，背景陈设不变形不重复。"""

PROFILES = {
    # 近景 · 男友 POV（palace-girlfriend-trending 默认）
    "portrait": {
        "composition": COMPOSITION_PORTRAIT,
        "light": "烛光/窗光/灯笼光/室内暖灯",
        "negative_extra": "",
        "person": "一位明确的成年女性",
    },
    # 近景 · 男友 POV · 双人同框（palace 双女主集；身份来源＝两张三视图的左右拼版）
    # 2026-09-20 E12 新增：本题材下输入参考图为「左 A + 右 B」的身份拼版，画面内仍是两位主体人物
    "portrait_duo": {
        "composition": COMPOSITION_DUO,
        "light": "烛光/窗光/灯笼光/室内暖灯",
        "negative_extra": "",
        "person": "两位明确的成年女性（各自成年、气质明显不同）",
        "negative_common": NEGATIVE_DUO,
        "age_retry": "两位三十岁上下的成年女性，气质沉稳端庄、温和持重。",
    },
    # 全身 · 舞蹈/动作迁移（dance 默认）
    # 2026-09-20 用户指定：参考图必须是**正面照**（正脸正身），否则迁移模型看不到人物正面
    "fullbody": {
        "composition": COMPOSITION_FULLBODY,
        "light": "大殿窗光/烛火/灯盏",
        "negative_extra": "\n全身完整：不裁切头部、不裁切脚部、不出现半身或只有上半身的构图；"
                          "\n朝向正面：不侧身、不背对镜头、不回眸侧脸、不低头遮脸、不出现背面或侧面视角；",
        "person": "一位明确的成年女性",
    },
}

TEMPLATE = """{composition}

{lock}
{age}

{realism}

场景：{scene}。
{action_line}

{negative}"""


def render_prompt(job, lock, age):
    """按 job 的 profile / light / negative_extra / action_line 渲染完整提示词。
    缺省 profile=portrait，输出与历史版本逐字一致。
    profile 可覆盖 negative_common（双人同框用）与 person（人数措辞）。"""
    name = job.get("profile") or "portrait"
    prof = PROFILES.get(name)
    if prof is None:
        raise SystemExit(f"[X] 未知 profile：{name}（可选 {'/'.join(PROFILES)}）")
    negative = (job.get("negative_common") or prof.get("negative_common") or NEGATIVE_COMMON) \
        + prof["negative_extra"]
    if job.get("negative_extra"):
        negative += "\n" + job["negative_extra"]
    # 动作句：默认「人物正在…」句式（palace 沿用）；job 可用 action_line 整句覆盖（dance / 双人用）
    action_line = job.get("action_line") or (
        f"人物正在{job['action']}；情绪按剧本给，但须呈现为自然瞬间，不做夸张摆拍。")
    person = job.get("person") or prof.get("person") or "一位明确的成年女性"
    return TEMPLATE.format(
        composition=job.get("composition") or prof["composition"],
        lock=lock,
        age=age,
        realism=REALISM.format(light=job.get("light") or prof["light"], person=person),
        scene=job["scene"],
        action_line=action_line,
        negative=negative,
    )


def eprint(*a):
    print(*a, file=sys.stderr, flush=True)


def post_json(url, payload, key, timeout=90):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def get_json(url, key, timeout=45):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def build_prompt(job, attempt):
    """attempt: 1 原始 / 2 改年龄措辞 / 3 换造型（年龄措辞保留）"""
    lock = job["lock"]
    sanyi = job["sanyi"]
    prof = PROFILES.get(job.get("profile") or "portrait", {})
    age = job.get("age") or DEFAULT_AGE
    if attempt >= 2:
        age = (job.get("age_retry") or prof.get("age_retry") or AGE_RETRY)
    if attempt >= 3:
        if not job.get("fallback_sanyi"):
            return None, None
        sanyi = job["fallback_sanyi"]
        lock = job.get("fallback_lock") or job["lock"]
    prompt = render_prompt(job, lock, age)
    return prompt, sanyi


def submit(job, attempt, key, rec_dir, model, size, resolution, n):
    prompt, sanyi = build_prompt(job, attempt)
    if prompt is None:
        return None, None
    # 参考图：单个路径 → 传字符串（历史行为逐字不变）；路径列表 → 传数组（多角色身份基准直传）
    # 2026-09-20 E12 实测：input.image 传数组（两张三视图）被接口接受并正常出图，
    # 是「双人同框」的首选做法（省掉本地拼版），拼版仅作备选。
    refs = sanyi if isinstance(sanyi, list) else [sanyi]
    images = ["data:image/png;base64," + base64.b64encode(open(p, "rb").read()).decode()
              for p in refs]
    payload = {"kind": "image", "model": model,
               "input": {"prompt": prompt, "size": size,
                         "resolution": resolution, "n": n,
                         "image": images if len(images) > 1 else images[0]}}
    rp = os.path.join(rec_dir, f"65535-{job['tag']}-request.json")
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    res = post_json(f"{API}/v1/tasks", payload, key)
    return res, sanyi


def download(r, dst):
    urls = r.get("result_urls") or []
    if not urls:
        data = ((r.get("result") or {}).get("data") or [])
        urls = [d.get("url") for d in data if d.get("url")]
    if not urls:
        return False
    urllib.request.urlretrieve(urls[0], dst)
    return True


def main():
    ap = argparse.ArgumentParser(description="真人质感参考图批量生成（65535 图生图，含审核拒绝重试链；profile 分近景/全身）")
    ap.add_argument("--jobs", required=True, help="任务定义 JSON 文件")
    ap.add_argument("--out", required=True, help="图片归档目录（分集 images\\）")
    ap.add_argument("--rec", required=True, help="回执目录（分集 任务记录\\）")
    ap.add_argument("--state", help="状态文件（默认 <jobs>.state.json）")
    ap.add_argument("--model", default="gpt-image-2")
    ap.add_argument("--size", default="9:16")
    ap.add_argument("--resolution", default="2k")
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--poll", type=float, default=6, help="轮询间隔秒（默认 6）")
    ap.add_argument("--timeout", type=int, default=1800, help="总轮询超时秒（默认 1800）")
    ap.add_argument("--profile", choices=sorted(PROFILES),
                    help="构图 profile 全局覆盖：portrait 近景（默认）/ portrait_duo 双人同框 / "
                         "fullbody 全身（dance）；job 内 profile 字段可单独覆盖本参数")
    ap.add_argument("--redo", action="store_true", help="清除 failed/未完成记录后重跑这些 job")
    ap.add_argument("--dry-run", action="store_true", help="只打印各 attempt 提示词，不提交")
    a = ap.parse_args()

    key = os.environ.get("S65535_API_KEY", "").strip()
    if not a.dry_run and not key:
        eprint("错误：未找到环境变量 S65535_API_KEY。")
        return 1
    os.makedirs(a.out, exist_ok=True)
    os.makedirs(a.rec, exist_ok=True)

    jobs = json.load(open(a.jobs, encoding="utf-8"))
    if a.profile:
        # 全局 profile 只兜底，不覆盖 job 内已显式写的 profile
        for j in jobs:
            j.setdefault("profile", a.profile)
    state_path = a.state or (a.jobs + ".state.json")
    state = json.load(open(state_path, encoding="utf-8")) if os.path.exists(state_path) else {}

    def save():
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    if a.redo:
        drop = [k for k, v in state.items() if v.get("status") != "done" or not v.get("local")]
        for k in drop:
            state.pop(k, None)
        save()
        print(f"REDO_CLEARED {drop}")

    if a.dry_run:
        def _sanyi_label(s):
            if not s:
                return "（未配置 fallback，跳过）"
            if isinstance(s, list):
                return " + ".join(os.path.basename(x) for x in s)
            return os.path.basename(s)
        for j in jobs:
            for att in (1, 2, 3):
                p, s = build_prompt(j, att)
                print(f"===== {j['tag']} attempt{att} "
                      f"({'原始' if att == 1 else '改年龄措辞' if att == 2 else '换造型'})"
                      f" sanyi={_sanyi_label(s)} =====")
                if p:
                    print(p)
                else:
                    print("（该 job 未配置 fallback_sanyi，attempt3 不可用）")
                print()
        return 0

    # ---- 提交未完成的 job（含重试链推进） ----
    for j in jobs:
        st = state.get(j["tag"]) or {}
        if st.get("local"):
            continue  # 已完成并落盘
        if st.get("task_id") and not st.get("final") and st.get("status") != "rejected":
            continue  # 在途任务，交给轮询循环
        attempt = st.get("next_attempt") or 1
        while attempt <= 3:
            res, sanyi = submit(j, attempt, key, a.rec, a.model, a.size, a.resolution, a.n)
            if res is None:
                state[j["tag"]] = {"status": "failed",
                                   "reason": f"重试链在 attempt{attempt} 不可用（未配置 fallback_sanyi）",
                                   "out": j["out"]}
                save()
                print(f"SKIP {j['tag']}：attempt{attempt} 不可用（无 fallback_sanyi），链耗尽")
                break
            tid = res.get("id")
            print(f"SUBMIT {j['tag']} attempt{attempt} {tid} {res.get('status')}")
            state[j["tag"]] = {"task_id": tid, "attempt": attempt,
                               "out": j["out"], "submit": res}
            save()
            # 同步等首查，快速失败（审核拒绝通常秒级返回 failed）
            time.sleep(4)
            r = get_json(f"{API}/v1/tasks/{tid}", key)
            if r.get("status") == "failed" and "审核拒绝" in (r.get("error_message") or ""):
                state[j["tag"]] = {"task_id": tid, "attempt": attempt,
                                   "status": "rejected", "out": j["out"], "result": r,
                                   "next_attempt": attempt + 1}
                save()
                print(f"REJECTED {j['tag']} attempt{attempt} -> 走重试链")
                attempt += 1
                continue
            break  # 进入正常轮询 / 或其他状态交给轮询循环

    # ---- 轮询 ----
    t0 = time.time()
    while time.time() - t0 < a.timeout:
        pending = {k: v for k, v in state.items()
                   if v.get("task_id") and not v.get("final")}
        if not pending:
            break
        for k, v in list(pending.items()):
            r = get_json(f"{API}/v1/tasks/{v['task_id']}", key)
            st_ = r.get("status")
            if st_ in ("done", "failed"):
                v["final"] = st_
                v["result"] = r
                save()
                print(f"RESULT {k} {st_} {r.get('error_code') or ''} {r.get('error_message') or ''}")
                if st_ == "done":
                    dst = os.path.join(a.out, v["out"])
                    if download(r, dst):
                        v["local"] = dst
                        save()
                        print(f"DOWNLOADED {dst}")
            else:
                v["status"] = st_
                save()
        if pending:
            time.sleep(a.poll)

    # ---- 汇总 ----
    print("\n===== 汇总 =====")
    for j in jobs:
        v = state.get(j["tag"], {})
        print(f"{j['tag']}: {v.get('final') or v.get('status') or '未提交'}"
              f"  attempt={v.get('attempt')}  local={v.get('local')}")
        if v.get("final") == "failed" or v.get("status") == "rejected":
            print(f"  ↑ 提示：若重试链（改措辞→换造型）均被拒，按 SKILL.md §4.5 走三视图+场景图双参考，勿再用 65535 硬试")
    ok = all(state.get(j["tag"], {}).get("local") for j in jobs)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""海贼王 · 三视图批量生成驱动（调用 byted-ark-seedream-skill）。

用法：
  set ARK_API_KEY=ark-xxx
  python tools\op_gen_views.py --only 蒙奇D路飞     # 单个试跑
  python tools\op_gen_views.py                     # 全部 10 人

设计要点：
  - 参考图以 JSON 数组传入（部分 CDN URL 含逗号，不能用逗号分隔写法）。
  - 用 subprocess 列表参数调用，规避 PowerShell 吞引号问题。
  - 解析 stdout JSON 取 local_path，按包内规范重命名落到 character/{角色}/人物三视图（基础）.png。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

SKILL = r"d:\life\xinjiang\.trae\skills\byted-ark-seedream-skill"
ROOT = os.path.join("D:", os.sep, "work", "minimax_h3", "assets", "海贼王")
CHDIR = os.path.join(ROOT, "character")
RAW = os.path.join(ROOT, "_refs_raw")
GEN_TMP = os.path.join(ROOT, "_gen_tmp")
OUT_NAME = "人物三视图（基础）.png"

COMPOSITION = (
    "完整角色设定稿，白色背景，同画布分左右两列排版："
    "第一列超精细面部特写（占30%宽度），第二列角色标准三视图（正面 / 侧面 / 背面）（占70%宽度）。"
)
LOCK = (
    "严格保持参考图中同一人物的面部五官、脸型、发型发饰与服装形制不变"
    "（以参考图为唯一身份基准，不换人、不改发型与服装形制）。"
)
REALISM = (
    "这要像一张真实的真人质感角色设定照：真实亚洲人皮肤质感，可见毛孔、细小绒毛、自然泛红与微小瑕疵，"
    "保留柔和的阴影过渡；面部比例与骨相真实，不放大眼睛、不改脸型、不做磨皮美颜，"
    "保留眉/眼/脸颊/嘴部左右轻微不对称；头发有飞散碎发、不均匀发束与轻微毛躁，不是根根分明的发丝；"
    "影棚柔和的自然光，皮肤上有真实明暗；高清写实3D渲染质感，非平面二次元插画。"
)
NOTEXT = (
    "画面中不出现任何文字、字母、数字、标注或水印"
    "（包括「正面 / 侧面 / 背面」等视角标签与角色名）。"
)
NEGATIVE = (
    "避免：娃娃皮肤、瓷肌、过度磨皮、美颜 App 瘦脸大眼、眼睛过大、面部完全对称、睫毛过度锐化、"
    "油蜡感高光、商业时尚大片、刻意轮廓光、极端背景虚化、过度 HDR、毛孔纹理过度锐化、不真实的解剖比例；"
    "画面无第二个人物，无现代物品穿帮；手与手指的数量、关节、长度、交叠与握持合理（无多指、无粘连）；"
    "首饰不重复不悬空、不穿模。"
)

# 角色形态锚点（非人形角色必须显式声明，避免被画成普通人类）
FORM = {
    "蒙奇D路飞": "角色为成年男性，黑色蓬乱短发，左眼下方一道横向刀疤，头戴草帽（浅草色、红色缎带），红色无袖开襟背心 + 蓝色及膝短裤 + 草鞋。",
    "罗罗诺亚索隆": "角色为成年男性，绿色短发，左眼一道竖直长疤且左眼闭合，左耳三枚金色耳环，腰间绿色腹卷，开襟衬衫 + 深色长裤长靴，腰佩三把刀。",
    "娜美": "角色为成年女性，橘色波浪长发，左肩有风车与橘子刺青，蓝白比基尼式上衣 + 牛仔裤。",
    "乌索普": "角色为成年男性，黑色卷发束成小辫，长鼻子（显著特征），黄色头巾 + 工装背带裤。",
    "山治": "角色为成年男性，金色短发，刘海遮住右眼，卷眉毛，短须，黑色西装 + 蓝色衬衫 + 领带。",
    "托尼托尼乔巴": "角色为驯鹿人形态（非人类，体型小巧约90厘米），蓝色鼻子，头戴粉色大礼帽（白色十字标记），有鹿角，上身赤裸 + 红色短裤。",
    "妮可罗宾": "角色为成年女性，黑色长发垂肩，神情沉稳，深色连衣裙。",
    "弗兰奇": "角色为成年男性改造人（体型高大健硕，非普通人类），蓝色短发，双臂为红色机械结构，胸口有动力炉，夏威夷花衬衫。",
    "布鲁克": "角色为活着的骷髅（纯骨骼、无血肉，非人类），黑色爆炸头卷发 + 高礼帽，深色燕尾服，手持手杖剑。",
    "甚平": "角色为鲸鲨鱼人（非人类，体型庞大），蓝色皮肤，橙黄色束发髻，獠牙，和服式上衣 + 宽腰带。",
}


def build_prompt(cn):
    return "\n".join([COMPOSITION, LOCK, FORM[cn], REALISM, NOTEXT, NEGATIVE])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--size", default="2K")
    ap.add_argument("--model", default="auto")
    args = ap.parse_args()

    key = os.environ.get("ARK_API_KEY", "").strip()
    if not key.startswith("ark-"):
        print("缺少 ARK_API_KEY 环境变量（需 ark- 开头）")
        return 2

    bases = json.load(open(os.path.join(RAW, "_base_urls.json"), encoding="utf-8"))
    targets = [args.only] if args.only else list(FORM.keys())

    summary = []
    for cn in targets:
        refs = bases.get(cn) or []
        if not refs:
            print("SKIP(无参考图)", cn)
            summary.append((cn, "skip", ""))
            continue
        prompt = build_prompt(cn)
        argv = ["node", "scripts/generate.js",
                "--model", args.model,
                "--api_key", key,
                "--prompt", prompt,
                "--reference_images", json.dumps(refs, ensure_ascii=False),
                "--size", args.size,
                "--output_format", "png",
                "--optimize", "false"]
        print("=== 生成 %s（参考图 %d 张） ===" % (cn, len(refs)))
        env = dict(os.environ)
        env["ARK_SEEDREAM_SAVE_PATH"] = GEN_TMP
        r = subprocess.run(argv, cwd=SKILL, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env)
        if r.stderr:
            for line in r.stderr.strip().splitlines():
                print("   [stderr]", line)
        try:
            res = json.loads(r.stdout)
        except Exception:
            print("   [解析失败] stdout:", (r.stdout or "")[:400])
            summary.append((cn, "parse-fail", ""))
            continue
        if not res.get("success"):
            print("   [失败]", res.get("error"))
            summary.append((cn, "fail", str(res.get("error"))[:60]))
            continue
        img = (res.get("images") or [{}])[0]
        lp = img.get("local_path")
        url = img.get("url")
        dst_dir = os.path.join(CHDIR, cn)
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, OUT_NAME)
        if lp and os.path.exists(lp):
            shutil.copy2(lp, dst)
            print("   ✅ 落盘:", dst)
            summary.append((cn, "ok", dst))
        else:
            print("   ⚠️ 未取到本地文件，在线链接:", url)
            summary.append((cn, "url-only", url or ""))

    print("\n=== 汇总 ===")
    for cn, st, info in summary:
        print("  %-10s %-10s %s" % (cn, st, info))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

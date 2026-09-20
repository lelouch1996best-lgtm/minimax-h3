# -*- coding: utf-8 -*-
"""基准同步校验：tools/gen_refs.py 的模板常量 == assets/真人质感美术基准.md 正本代码块

两系列共用一套基准后，最大风险是「正本改了、脚本没改」。本脚本把该风险变成可检测：
正则抽出正本 §5 / §6.1 / §6.2 的代码块，与 gen_refs.py 的常量逐字比对。
用法：python check_baseline_sync.py   （0=一致，1=漂移）
"""
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(r"d:\work\minimax_h3")
DOC = ROOT / "assets" / "真人质感美术基准.md"
SCRIPT = ROOT / "tools" / "gen_refs.py"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def section_blocks(doc_text, heading_keyword, expect):
    # 取指定小节内的代码块（按三反引号围栏，按出现顺序）
    parts = re.split(r"\n(?=#{2,3} )", doc_text)
    for p in parts:
        first = p.split("\n", 1)[0]
        if heading_keyword in first:
            blocks = re.findall(r"```[a-z]*\n(.*?)\n```", p, re.S)
            if len(blocks) < expect:
                return None, f"小节「{first.strip()}」代码块不足（找到 {len(blocks)}，期望 {expect}）"
            return blocks, None
    return None, f"未找到小节：{heading_keyword}"


def norm(s):
    return s.strip().replace("\r\n", "\n")


def main():
    doc = DOC.read_text(encoding="utf-8")
    g = load_module(SCRIPT, "gen_refs")

    failures = []

    blocks, err = section_blocks(doc, "6.1 构图段", 2)
    if err:
        failures.append(err)
    else:
        pairs = [("COMPOSITION_PORTRAIT", blocks[0]), ("COMPOSITION_FULLBODY", blocks[1])]
        for const_name, doc_text in pairs:
            if norm(getattr(g, const_name)) != norm(doc_text):
                failures.append(f"{const_name} 与正本 §6.1 不一致")

    blocks, err = section_blocks(doc, "6.2 真人质感段", 1)
    if err:
        failures.append(err)
    else:
        # 正本用中文占位 {光源}/{人物}，脚本用 {light}/{person}
        want = norm(blocks[0]).replace("{光源}", "{light}").replace("{人物}", "{person}")
        if norm(g.REALISM) != want:
            failures.append("REALISM 与正本 §6.2 不一致")

    blocks, err = section_blocks(doc, "5. 常用反向约束", 1)
    if err:
        failures.append(err)
    else:
        if norm(g.NEGATIVE_COMMON) != norm(blocks[0]):
            failures.append("NEGATIVE_COMMON 与正本 §5 不一致")

    # profile 附加反向约束
    if "全身完整：不裁切头部、不裁切脚部、不出现半身或只有上半身的构图；" \
            not in g.PROFILES["fullbody"]["negative_extra"]:
        failures.append("fullbody.negative_extra 缺「全身完整」硬约束")
    if g.PROFILES["portrait"]["negative_extra"] != "":
        failures.append("portrait.negative_extra 应为空（近景不加全身约束）")

    if failures:
        print("[FAIL] 正本与脚本已漂移：")
        for f in failures:
            print("  -", f)
        print(f"\n正本：{DOC}\n脚本：{SCRIPT}\n改基准请先改正本 §5/§6，再同步脚本常量。")
        return 1

    print("[PASS] gen_refs.py 模板常量与正本逐字一致（构图×2 / 真人质感 / 反向约束 + profile 差异）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

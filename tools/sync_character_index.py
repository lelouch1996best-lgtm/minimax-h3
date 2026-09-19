#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
凡人 · 人物形象索引自动同步脚本

作用：扫描 character 目录下的所有角色文件夹与三视图/人视图图片，与
      `_人物资产索引.md` 对比，自动补登记「新增角色」和「新增形象」。

规则：
  * 标准命名 `人物三视图（{形象}）.png/.jpg` 与变体 `人物*视图（{形象}）.png`
    → 识别为「形象」，缺失时自动补一行「以图片为准」。
  * 非标准命名的图片（特写图 / 详细信息图 / 风雷翅 / 兽形态 / 人类质感等）
    → 不作自动登记，仅在报告中列出，交由人工判断。

用法：
  python sync_character_index.py             # 预览（dry-run），不写文件
  python sync_character_index.py --write     # 实际把新增条目写回索引
  python sync_character_index.py --base <dir> # 指定 character 目录（默认自动推断）
"""

import os
import re
import sys
from pathlib import Path

# 默认 character 根目录：本脚本位于 tools/ 下，自动向上推断
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_BASE = SCRIPT_DIR.parent / "assets" / "凡人" / "character"
INDEX_NAME = "_人物资产索引.md"

IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp")

# 已知男性角色（用于新增角色时推断性别，可按需扩充）
MALE_NAMES = {"韩立", "玄骨", "王蝉", "马姓老者", "极阴", "蛮胡子", "青易", "火龙童子"}

# 女性形象线索（用于新增角色时推断性别，可按需扩充）
FEMALE_HINTS = ("宫装", "泳装", "校服", "白礼服", "凤冠霞帔", "敦煌", "比基尼", "和服")

# 匹配 `人物三视图（形象）.png` / `人物人视图（形象）.png` 等
VIEW_RE = re.compile(r"^人物.+?视图（(.+)）\.(?:png|jpg|jpeg|webp)$", re.IGNORECASE)


def scan(base_dir: Path):
    """扫描目录，返回 {角色名: {"variants": [(形象, 文件名)], "others": [文件名]}}"""
    chars = {}
    if not base_dir.is_dir():
        print(f"[错误] 目录不存在：{base_dir}")
        return chars
    for entry in sorted(base_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_"):
            continue
        variants, others = [], []
        for f in sorted(p.name for p in entry.iterdir() if p.is_file()):
            if not f.lower().endswith(IMG_EXTS):
                continue
            m = VIEW_RE.match(f)
            if m:
                variants.append((m.group(1), f))
            else:
                others.append(f)
        chars[entry.name] = {"variants": variants, "others": others}
    return chars


def parse_index(index_path: Path):
    """解析索引，返回 (lines, {角色名: {"gender", "variants", "start", "end"}})"""
    if not index_path.is_file():
        print(f"[错误] 索引不存在：{index_path}")
        return [], {}
    lines = index_path.read_text(encoding="utf-8").splitlines()

    headers = [i for i, ln in enumerate(lines) if ln.startswith("## ")]
    sections = {}
    for idx, s in enumerate(headers):
        header = lines[s][3:].strip()
        m = re.match(r"^(.*?)（(.+?)）$", header)
        name = m.group(1) if m else header
        gender = m.group(2) if m else ""
        e = headers[idx + 1] if idx + 1 < len(headers) else len(lines)

        variants = set()
        for j in range(s, e):
            ln = lines[j]
            if not ln.startswith("|"):
                continue
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if not cells or cells[0] in ("", "形象") or cells[0].startswith("-"):
                continue
            variants.add(cells[0])
        sections[name] = {"gender": gender, "variants": variants, "start": s, "end": e}
    return lines, sections


def guess_gender(name, variant_names):
    if name in MALE_NAMES:
        return "男"
    for v in variant_names:
        for hint in FEMALE_HINTS:
            if hint in v:
                return "女"
    return "女"  # 默认按女性标注，见报告中的待核对提示


def make_row(variant, filename):
    """构造表格行；标准三视图命名不加注，非标准（人视图等）在行内标注文件名"""
    if filename.startswith("人物三视图（"):
        return f"| {variant} | 以图片为准 |"
    return f"| {variant} | 以图片为准（文件：`{filename}`） |"


def apply(lines, index, chars, new_chars, new_variants):
    """对 lines 做增补，返回新的 lines（此时不落盘）"""
    # 1) 已有角色补形象：插到该角色表格最后一行之后
    inserts = []  # (插入位置, [多行])
    for name, vlist in new_variants.items():
        s, e = index[name]["start"], index[name]["end"]
        last_row = s
        for j in range(s, e):
            if lines[j].startswith("|"):
                last_row = j
        rows = [make_row(v, f) for v, f in vlist]
        inserts.append((last_row + 1, rows))

    # 从后向前插入，避免下标错位
    for pos, rows in sorted(inserts, key=lambda x: -x[0]):
        for i, r in enumerate(rows):
            lines.insert(pos + i, r)

    # 2) 新增角色：整段追加到文件末尾
    for name in new_chars:
        variants = chars[name]["variants"]
        gender = guess_gender(name, [v for v, _ in variants])
        section = [f"## {name}（{gender}）", "", "| 形象 | 外观描述 |", "| --- | --- |"]
        section += [make_row(v, f) for v, f in variants]
        if lines and lines[-1] != "":
            lines.append("")
        lines.extend(section)
    return lines


def main():
    args = [a for a in sys.argv[1:]]
    write = "--write" in args
    base = DEFAULT_BASE
    if "--base" in args:
        i = args.index("--base")
        if i + 1 < len(args):
            base = Path(args[i + 1])
    index_path = base / INDEX_NAME

    chars = scan(base)
    lines, index = parse_index(index_path)
    if not lines:
        return

    new_chars = [n for n in chars if n not in index]
    new_variants = {}  # name -> [(variant, filename)]
    new_others = {}    # name -> [文件名]（非标准命名，未在正文出现）
    for name, info in chars.items():
        if name in index:
            known = index[name]["variants"]
            for v, f in info["variants"]:
                if v not in known:
                    new_variants.setdefault(name, []).append((v, f))
            section_text = "\n".join(lines[index[name]["start"]:index[name]["end"]])
            for f in info["others"]:
                if f not in section_text:
                    new_others.setdefault(name, []).append(f)

    # 输出报告
    total = len(new_chars) + sum(len(v) for v in new_variants.values())
    print("=" * 60)
    print(f"角色目录   : {base}")
    print(f"索引文件   : {index_path}")
    print(f"已登记角色 : {len(index)}   扫描角色 : {len(chars)}")
    print("=" * 60)

    if new_chars:
        print(f"\n[新增角色] {len(new_chars)} 个")
        for n in new_chars:
            vs = [v for v, _ in chars[n]["variants"]]
            print(f"  - {n}（{guess_gender(n, vs)}）: {', '.join(vs)}（性别按启发式，请核对）")

    if new_variants:
        print(f"\n[新增形象] {sum(len(v) for v in new_variants.values())} 处")
        for name, vlist in new_variants.items():
            for v, f in vlist:
                print(f"  - {name} / {v}  ({f})")

    if new_others:
        print(f"\n[非标准命名图片·未自动登记] 需人工判断")
        for name, flist in new_others.items():
            for f in flist:
                print(f"  - {name} / {f}")

    if total == 0 and not new_others:
        print("\n[结论] 无新增，索引不需要更新。")
        return

    if not write:
        print("\n[预览模式] 以上为待处理变更，未写入文件。确认无误后加 --write 执行。")
        return

    # 落盘
    apply(lines, index, chars, new_chars, new_variants)
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n[已写入] 索引文件已更新。")

    if new_chars:
        print("[提醒] 新增角色均按「以图片为准」登记，性别为启发式推断，请人工核对后补正文描述。")


if __name__ == "__main__":
    main()
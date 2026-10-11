# -*- coding: utf-8 -*-
"""从 run-state 生成《心魔劫·慕沛灵》全片进度表（只读，不改任何文件）。

用法：
    python tools/xmj_progress.py            # 打印 markdown 表
    python tools/xmj_progress.py --write    # 写入 心魔劫_穆沛灵/_全片进度表.md
"""
import json, os, sys, io

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = os.path.join(ROOT, "心魔劫_穆沛灵")
RS = os.path.join(PROJ, "任务记录", "t8balance30-run-state.json")

# 分镜总表（v2）：镜号 -> (场次, 景别, 运镜, 秒数, 层)
SHOTS = [
    ("01", "1-1", "大全景", "缓推", 6, "幻境"),
    ("02", "1-1", "中景", "固定", 5, "幻境"),
    ("03", "1-1", "中景", "缓摇", 6, "层3闪回"),
    ("04", "1-1", "特写", "固定", 4, "层3闪回"),
    ("05", "1-1", "中景", "固定", 5, "层3闪回"),
    ("06", "1-1", "近景", "缓推", 6, "层3闪回"),
    ("07", "1-1", "空镜", "固定", 8, "幻境"),
    ("08", "1-2", "中景", "俯拍", 6, "幻境"),
    ("09", "1-2", "特写", "微推", 6, "幻境"),
    ("10", "1-2", "近景", "固定", 10, "幻境"),
    ("11", "1-2", "特写", "固定", 7, "幻境"),
    ("12A", "1-2", "近景", "缓推", 12, "幻境"),
    ("12B", "1-2", "插入组", "快切", 10, "层3回闪"),
    ("13", "1-2", "特写", "固定", 6, "幻境"),
    ("14", "1-2", "空镜", "固定", 5, "幻境→现实"),
    ("15", "1-3", "全景", "缓降", 8, "现实"),
    ("16", "1-3", "近景", "微推", 8, "现实"),
    ("17", "1-3", "中景", "固定", 6, "现实"),
    ("18", "1-3", "特写", "固定", 10, "现实"),
    ("19", "1-3", "全景", "固定", 7, "现实"),
    ("20", "1-4", "特写", "微距", 5, "现实"),
    ("21", "1-4", "特写", "固定", 5, "现实"),
    ("23", "1-4", "全景", "缓拉", 12, "现实"),
]

# tag 映射（与 job 文件的 tag 一致；跑过多个 tag 的镜，取**最终成功**的那个）
#   12A 先 805 后成功 → E12Ad；12B v1 失败 195 币 → v2 成功 → E12B2；21 v1 无痕失败 → v2 → E21b
PREFERRED_TAG = {"12A": "E12Ad", "12B": "E12B2", "21": "E21b", "01": "E01"}
for s in SHOTS:
    PREFERRED_TAG.setdefault(s[0], "E" + s[0])


def main():
    write = "--write" in sys.argv
    rs = {}
    if os.path.exists(RS):
        with open(RS, encoding="utf-8") as f:
            rs = json.load(f)

    lines = []
    lines.append("# 《心魔劫·慕沛灵》全片进度表（自动生成）\n")
    lines.append(f"> 数据源：`任务记录/t8balance30-run-state.json`｜生成脚本：`tools/xmj_progress.py`\n")
    lines.append("| 镜 | 场次 | 景别 | 运镜 | 秒 | 层 | tag | 状态 | 币 | 耗时 | 成片 |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")

    done = coins = spent = 0
    total_sec = 0
    for sid, scene, shot_t, move, sec, layer in SHOTS:
        total_sec += sec
        tag = PREFERRED_TAG[sid]
        e = rs.get(tag) or {}
        # 某些镜跑过多个 tag（如 12A 先 805 后成功、12B v1 失败 v2 成功）
        # → 只要偏好 tag 不是 SUCCESS，就在同前缀里回退找 SUCCESS 的记录
        if e.get("status") != "SUCCESS":
            for k, v in rs.items():
                if k.startswith("E" + sid) and v.get("status") == "SUCCESS":
                    if v.get("usage", {}).get("consumeCoins"):
                        e, tag = v, k
                        break
        st = e.get("status") or ("已提交·运行中" if e.get("task_id") else "未提交")
        us = e.get("usage") or {}
        c = us.get("consumeCoins") or ""
        t = us.get("taskCostTime") or ""
        loc = os.path.basename(e.get("local", "")) if e.get("local") else ""
        if st == "SUCCESS":
            done += 1
            try:
                coins += int(c)
            except Exception:
                pass
        # 全口径实付：同前缀所有终态任务的币之和（含失败/返工）
        for k, v in rs.items():
            if k.startswith("E" + sid):
                try:
                    spent += int((v.get("usage") or {}).get("consumeCoins") or 0)
                except Exception:
                    pass
        lines.append(f"| {sid} | {scene} | {shot_t} | {move} | {sec} | {layer} | {tag} | {st} | {c} | {t} | {loc} |")

    lines.append("")
    lines.append(f"**合计**：{len(SHOTS)} 镜 / {total_sec}s 标称｜**已成功 {done} 镜**｜"
                 f"**成片成本 {coins} 币**｜**含返工实付 {spent} 币**")
    md = "\n".join(lines)

    print(md)
    if write:
        out = os.path.join(PROJ, "_全片进度表.md")
        with io.open(out, "w", encoding="utf-8") as f:
            f.write(md + "\n")
        print("\n[written]", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()

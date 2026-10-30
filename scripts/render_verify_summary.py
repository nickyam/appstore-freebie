#!/usr/bin/env python3
"""
把 verify_live_freebies.py 产出的 JSON 报告渲染成 Markdown 摘要
（写入 GitHub Actions 的 $GITHUB_STEP_SUMMARY）。

只读脚本：只读取 --report 指定的 JSON，写入 --out 指定的文本文件，
不碰 data/ 与 app/。
"""
import argparse
import json
import os
import sys


def render(report):
    lines = []
    lines.append("### 限免有效性校验报告")
    lines.append("")
    lines.append("- 失效条目（需下架）：**%s** 条" % report.get("total_stale", 0))
    lines.append("- 疑似下架（交由跑批 DELIST_MISS 处理）：%s 条"
                 % report.get("total_missing", 0))
    lines.append("- 生成时间：%s" % report.get("generated_at", "?"))
    lines.append("")
    lines.append("| 地区 | 在架限免 | 在架特价 | IAP 限免 | 失效 | 疑似下架 | 备注 |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in report.get("regions", []):
        note = r.get("skip_reason", "") if r.get("skipped") else ""
        lines.append("| %s | %d | %d | %d | %d | %d | %s |" % (
            r.get("region", "?").upper(),
            r.get("freebies", 0), r.get("deals", 0), r.get("iap_events", 0),
            len(r.get("stale", [])), len(r.get("missing", [])),
            note.replace("|", "/") or "—",
        ))
    lines.append("")

    any_stale = False
    for r in report.get("regions", []):
        stale = r.get("stale", [])
        if not stale:
            continue
        any_stale = True
        lines.append("#### %s 区失效条目明细" % r.get("region", "?").upper())
        lines.append("")
        for s in stale:
            lines.append("- `%s` **%s** — 站上显示 %s → 现价 %s（%s）" % (
                s.get("id", ""), s.get("name", ""),
                s.get("shown", ""), s.get("now", ""), s.get("why", "")))
        lines.append("")

    if not any_stale:
        lines.append("✅ 未发现失效条目 —— 在架的限免/特价全部仍然有效。")
        lines.append("")
        lines.append("> 本工作流为只读校验：未改任何数据、未提交任何文件。")
    else:
        lines.append("> ⚠️ 已触发 daily 跑批，由 `generate.py` 执行下架。")
        lines.append("> 本工作流自身仍为只读：未直接改任何数据。")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="渲染校验报告为 Markdown 摘要")
    ap.add_argument("--report", required=True, help="verify_live_freebies.py 产出的 JSON")
    ap.add_argument("--out", required=True, help="输出的 Markdown 文件（- 表示 stdout）")
    ap.add_argument("--stale", default=None, help="覆盖报告中的失效条数")
    ap.add_argument("--missing", default=None, help="覆盖报告中的疑似下架条数")
    args = ap.parse_args()

    try:
        with open(args.report, "r", encoding="utf-8") as f:
            report = json.load(f)
    except (OSError, ValueError) as e:
        print("[warn] 读取报告失败: %s" % e, file=sys.stderr)
        report = {"regions": [], "total_stale": 0, "total_missing": 0}

    if args.stale is not None:
        report["total_stale"] = int(args.stale)
    if args.missing is not None:
        report["total_missing"] = int(args.missing)

    md = render(report)
    if args.out == "-":
        print(md)
    else:
        with open(args.out, "a", encoding="utf-8") as f:
            f.write(md + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

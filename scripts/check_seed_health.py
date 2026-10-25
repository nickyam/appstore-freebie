#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
播种健康检查（A 方案：防静默失败）
==================================
背景：daily.yml 的 seed 步骤带 continue-on-error，反斗 API 在播种时段不可达时
      整步被静默跳过——manifest 不变、页面照常生成，没人知道播种已经死了
      （2026-10-24/25 连续两班零新增，直到人工核查才发现）。

机制：seed_iap_from_apprcn.py 每次运行都往 data/iap-history-{region}.json 的
      meta 写心跳（seed_last_ok / seed_last_fail / seed_last_error）；本脚本在
      daily.yml 中紧跟 seed 步骤执行，**不带 continue-on-error**——心跳异常即使
      任务失败（红 X + 邮件），把"静默失败"变成"响亮失败"。

判定（满足任一即 exit 1）：
  · 从未成功播种（无 seed_last_ok）
  · 最近一次成功播种距今 > SEED_MAX_AGE_H（默认 30h，容上班次延迟 2~3h）
  · 最近一次失败比最近一次成功更新（seed_last_fail > seed_last_ok）

用法：python3 check_seed_health.py [--max-age-hours 30]
"""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATA_DIR = os.path.join(REPO, "data")
REGIONS = ["cn", "us"]


def parse_ts(ts):
    try:
        return datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ") \
            .replace(tzinfo=datetime.timezone.utc)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description="反斗播种健康检查（防静默失败）")
    ap.add_argument("--max-age-hours", type=float, default=30.0,
                    help="成功心跳最大允许陈旧时长（小时），默认 30")
    args = ap.parse_args()

    now = datetime.datetime.now(datetime.timezone.utc)
    bad = []

    for region in REGIONS:
        p = os.path.join(DATA_DIR, f"iap-history-{region}.json")
        if not os.path.exists(p):
            bad.append(f"{region}: iap-history 文件不存在（从未采集过？）")
            continue
        try:
            meta = json.load(open(p, encoding="utf-8")).get("meta", {})
        except Exception as e:
            bad.append(f"{region}: 读取失败 {e}")
            continue

        ok = parse_ts(meta.get("seed_last_ok") or "")
        fail = parse_ts(meta.get("seed_last_fail") or "")

        if ok is None:
            bad.append(f"{region}: 从未播种成功（meta 无 seed_last_ok，"
                       f"last_fail={meta.get('seed_last_fail') or '无'}）")
            continue
        age_h = (now - ok).total_seconds() / 3600.0
        if age_h > args.max_age_hours:
            bad.append(f"{region}: 播种陈旧 {age_h:.1f}h > {args.max_age_hours:.0f}h"
                       f"（last_ok={meta.get('seed_last_ok')}）")
            continue
        if fail and fail > ok:
            bad.append(f"{region}: 最近一次播种失败"
                       f"（{str(meta.get('seed_last_error') or '')[:80]}"
                       f" @ {meta.get('seed_last_fail')}）")
            continue
        print(f"[ok] {region}: 播种健康（last_ok={meta.get('seed_last_ok')}，"
              f"{age_h:.1f}h 前）")

    if bad:
        for b in bad:
            print("[FAIL] " + b)
        print("播种健康检查未通过：反斗快照可能持续不可达或播种逻辑故障，"
              "请检查 daily 工作流 seed 步骤日志（该步骤 continue-on-error，"
              "失败不阻断，只能靠本检查兜底报警）")
        sys.exit(1)
    print("播种健康检查通过")


if __name__ == "__main__":
    main()

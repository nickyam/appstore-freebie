#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据健康检查（A 方案：防静默失败）
==================================
背景：daily.yml 里 seed / iap_collector 步骤都带 continue-on-error，出问题时
      整步被静默跳过——manifest 不变、页面照常生成、CI 全绿，没人知道采集
      已经死了（2026-10-24/25 连续两班零新增，2026-11-19 播种心跳停滞两天，
      都是人工核查才发现）。本脚本是 daily.yml 的**末步且不带 continue-on-error**，
      把"静默失败"变成"红 X + 邮件"。

检查两项（任一异常即 exit 1）：

1) 播种健康 —— seed_iap_from_apprcn.py 每次运行往 data/iap-history-{region}.json
   的 meta 写心跳（seed_last_ok / seed_last_fail / seed_last_error）：
   · 从未成功播种（无 seed_last_ok）
   · 最近一次成功播种距今 > SEED_MAX_AGE_H（默认 33h：正常间隔 24h + 跑批 2~3h
     + 排队/重试余量；30h 在跑批慢的班次会贴边误报）
   · 最近一次失败比最近一次成功更新（seed_last_fail > seed_last_ok）

2) 采集新鲜度 —— iap_collector.py 写盘时打 meta.collected_at（UTC 时间戳）：
   · 距今 > --max-collect-age-hours（默认 15h）→ 说明连续两班以上没写成功
     （产出闸门拦下 / 接口被墙 / ECS 没触发 / 整班失败），站点数据已在悄悄变旧。
     正常班际间隔 6h（单班跑批 ≤3.5h），15h 不会误报。
   · 缺 collected_at（升级后首班还没跑）只提示、不报错，避免推送后立刻假红。

用法：python3 check_seed_health.py [--max-age-hours 33] [--max-collect-age-hours 15]
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


def check_seed(region, meta, now, max_age_h, bad):
    ok = parse_ts(meta.get("seed_last_ok") or "")
    fail = parse_ts(meta.get("seed_last_fail") or "")

    if ok is None:
        bad.append(f"{region}: 从未播种成功（meta 无 seed_last_ok，"
                   f"last_fail={meta.get('seed_last_fail') or '无'}）")
        return
    age_h = (now - ok).total_seconds() / 3600.0
    if age_h > max_age_h:
        bad.append(f"{region}: 播种陈旧 {age_h:.1f}h > {max_age_h:.0f}h"
                   f"（last_ok={meta.get('seed_last_ok')}）")
        return
    if fail and fail > ok:
        bad.append(f"{region}: 最近一次播种失败"
                   f"（{str(meta.get('seed_last_error') or '')[:80]}"
                   f" @ {meta.get('seed_last_fail')}）")
        return
    print(f"[ok] {region}: 播种健康（last_ok={meta.get('seed_last_ok')}，"
          f"{age_h:.1f}h 前）")


def check_collect(region, meta, now, max_collect_age_h, bad):
    """采集新鲜度：iap_collector 每班写 collected_at，陈旧即说明连续多班没落盘。"""
    ts = parse_ts(meta.get("collected_at") or "")
    if ts is None:
        print(f"[warn] {region}: 尚无 collected_at（升级后首班未跑），"
              f"本项暂不判定")
        return
    age_h = (now - ts).total_seconds() / 3600.0
    if age_h > max_collect_age_h:
        bad.append(f"{region}: 内购采集陈旧 {age_h:.1f}h > {max_collect_age_h:.0f}h"
                   f"（collected_at={meta.get('collected_at')}，"
                   f"processed={meta.get('processed')}/{meta.get('pool_size')}）"
                   f" —— 疑似产出闸门拦下 / 接口被墙 / 调度未触发")
        return
    print(f"[ok] {region}: 采集新鲜（{meta.get('collected_at')}，{age_h:.1f}h 前，"
          f"处理 {meta.get('processed')}/{meta.get('pool_size')}）")


def main():
    ap = argparse.ArgumentParser(description="数据健康检查（防静默失败）")
    ap.add_argument("--max-age-hours", type=float, default=33.0,
                    help="成功播种心跳最大允许陈旧时长（小时），默认 33")
    ap.add_argument("--max-collect-age-hours", type=float, default=15.0,
                    help="内购采集最大允许陈旧时长（小时），默认 15（班际间隔 6h）")
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

        check_seed(region, meta, now, args.max_age_hours, bad)
        check_collect(region, meta, now, args.max_collect_age_hours, bad)

    if bad:
        for b in bad:
            print("[FAIL] " + b)
        print("数据健康检查未通过：播种或内购采集已连续失败/停滞，站点数据正在变旧。"
              "请查 daily 工作流对应步骤日志（seed / Collect IAP prices 均带 "
              "continue-on-error，失败不阻断，只能靠本检查兜底报警）")
        sys.exit(1)
    print("数据健康检查通过")


if __name__ == "__main__":
    main()

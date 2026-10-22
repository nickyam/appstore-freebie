#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从「反斗限免」(apprcn) 拉取「内购限免」清单，bootstrap 进 IAP 监控库（P2 配套种子器）
===================================================================================

背景
----
iap_collector.py 的监控池来自 data/history-{region}.json（与 app 限免同池，~3800 个），
逐 IAP 累积价格历史来识别「付费 → 0」跳变 = 真·内购限免事件。但冷启动期要从 ~3800 App
里撞上「正在搞内购免费活动」的 App，纯靠运气——可能数日都撞不到一个。

反斗限免 API（monitor-appstore.apprcn.com/api/v1/snapshot）自带两个金矿字段：
  - iap[]        : 当前正在搞「内购限免」的 App（全局 76 个，每条含 regions[].items[]
                  内购名 / 现价 / free 标志）。这是「哪个 App 的哪个内购现在免费」的权威源。
  - iap_alerts[] : 历史上「iap_became_free」告警（含 created_at + old_price→0 跳变证据），
                  能明确区分「促销限免（曾付费）」与「永久免费（噪声）」。

注意：iap[] 与 iap_alerts[] 都是**全局列表**（与请求时的 region 参数无关），需按子字段
      region 自行过滤。

本脚本做什么
------------
1. 拉取 cn / us 两份 snapshot（带重试；可用 --cache-dir 复用本地缓存避免重复请求）。
2. 从 iap[] 抽取各 region「当前 free=True」的内购项 → 当前确实免费的内购（真相源）。
3. 从 iap_alerts[] 抽取各 region 的 became_free 告警 → 促销限免证据（含原价锚点）。
4. bootstrap 进 data/iap-history-{region}.json：
     - 命中 became_free → ever_paid=True、free_since=告警日、原价（有则显示，无则标「曾付费」）
       → 立即进 iap-free 限时免费事件流。
     - 未命中 became_free → 保守标 ever_paid=False（永久免费），只进 iap-current-free 列表，
       不污染限免事件（等 iap_collector 后续实爬再校正）。
5. 复用 iap_collector.detect_events 重新生成 iap-free-{region}.json / iap-current-free-{region}.json。
6. 把涉及的 app_id 注入 data/history-{region}.json 监控池（沿用 seed_from_apprcn.seed_entry
   格式，幂等跳过已存在），让 iap_collector 后续持续跟踪促销结束、捕获「恢复原价」。

安全
----
- 只增量补「iap-history 里尚不存在」的 (app_id, iap) 组合，绝不覆盖已有真实价格历史。
- 只把 app_id 补进 history 池里「尚不存在」的键，绝不覆盖 app 限免的真实基线。
- 全程不爬 Apple（apprcn 已给足双区数据），无 US 地理限制，本地即可双区播种。

用法
----
  python3 seed_iap_from_apprcn.py                 # 双区播种（cn+us）
  python3 seed_iap_from_apprcn.py --regions cn    # 仅 cn
  python3 seed_iap_from_apprcn.py --cache-dir /tmp # 复用 /tmp/apprcn_{region}.json
  python3 seed_iap_from_apprcn.py --dry-run        # 只打印，不写文件
"""
import sys
import os
import json
import time
import datetime
import argparse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATA_DIR = os.path.join(REPO, "data")
sys.path.insert(0, HERE)

from iap_collector import detect_events, save_json  # noqa: E402
from seed_from_apprcn import seed_entry, utc_today  # noqa: E402

SNAPSHOT_URL = "https://monitor-appstore.apprcn.com/api/v1/snapshot?region={region}&type=free"
UA = "Mozilla/5.0 (compatible; AppFreebieBot/1.0; +https://appstore.nickyam.com)"


def http_get_json(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_snapshot(region, cache_dir=None):
    cache = os.path.join(cache_dir, f"apprcn_{region}.json") if cache_dir else None
    if cache and os.path.exists(cache):
        try:
            return json.load(open(cache, encoding="utf-8"))
        except Exception:
            pass
    last_err = None
    for attempt in range(5):
        try:
            data = http_get_json(SNAPSHOT_URL.format(region=region))
            if data.get("ok"):
                return data
        except Exception as e:
            last_err = e
        time.sleep(3 + attempt * 2)
    raise RuntimeError("snapshot(%s) 拉取失败: %s" % (region, last_err))


def ts_to_date(ts):
    try:
        return datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return utc_today().isoformat()


def collect_current_free(data, region):
    """从 iap[] 抽取本 region 当前 free=True 的内购项。返回 list of dict。"""
    out = []
    for app in (data.get("iap") or []):
        aid = str(app.get("app_id"))
        app_name = app.get("name") or ""
        for r in (app.get("regions") or []):
            if r.get("region") != region:
                continue
            for it in (r.get("items") or []):
                if not it.get("free"):
                    continue
                out.append({
                    "app_id": aid,
                    "app_name": app_name,
                    "iap_name": it.get("name") or "",
                    "price_text": it.get("price_text") or "免费",
                    "base_price": app.get("base_price"),
                })
    return out


def collect_became_free(data, region):
    """从 iap_alerts[] 抽取本 region 的 became_free 告警。返回 {app_id: {name_lower: {...}}}。"""
    m = {}
    for a in (data.get("iap_alerts") or []):
        if a.get("kind") != "iap_became_free":
            continue
        if a.get("region") != region:
            continue
        aid = str(a.get("app_id"))
        name = (a.get("item_name") or "").strip().lower()
        rec = {
            "date": ts_to_date(a.get("created_at")),
            "old_price_text": a.get("old_price_text"),
        }
        m.setdefault(aid, {})[name] = rec
    return m


def pick_alert(became, aid, iap_name):
    """为某 (app_id, iap) 选一个 became_free 证据。优先精确名匹配；否则若 App 仅一条告警则复用。"""
    app_map = became.get(aid)
    if not app_map:
        return None
    exact = app_map.get(iap_name.strip().lower())
    if exact:
        return exact
    if len(app_map) == 1:
        return next(iter(app_map.values()))
    return None


def bootstrap_iap_history(region, current_free, became, today):
    hist_path = os.path.join(DATA_DIR, f"iap-history-{region}.json")
    hist = {"meta": {"region": region, "version": 1}, "items": {}}
    if os.path.exists(hist_path):
        try:
            hist = json.load(open(hist_path, encoding="utf-8"))
        except Exception:
            pass
    hist.setdefault("items", {})
    added = 0
    for cf in current_free:
        aid = cf["app_id"]
        iap_name = cf["iap_name"]
        key = f"{aid}::{iap_name}"
        if key in hist["items"]:
            continue  # 绝不覆盖已有真实价格历史
        alert = pick_alert(became, aid, iap_name)
        if alert:
            old = alert["old_price_text"]
            first_price = old if old else "—"  # 无原价锚点：用 — 表示原价未知
            ever_paid = True
            last_paid_date = alert["date"]
            free_since = alert["date"]
            changes = {alert["date"]: first_price, today: cf["price_text"]}
        else:
            first_price = cf["price_text"]
            ever_paid = False
            last_paid_date = None
            free_since = None
            changes = {today: cf["price_text"]}
        hist["items"][key] = {
            "app_id": aid,
            "app_name": cf["app_name"],
            "name": iap_name,
            "region": region,
            "first_date": today,
            "first_price": first_price,
            "last_date": today,
            "last_price": cf["price_text"],
            "last_change_date": today,
            "ever_paid": ever_paid,
            "last_paid_date": last_paid_date,
            "free_since": free_since,
            "changes": changes,
        }
        added += 1
    hist["meta"].update({"updated": today, "seeded_from": "apprcn",
                         "seed_added": added, "seed_total": len(hist["items"])})
    return hist, added


def seed_pool(region, data, today):
    """把 iap[] 涉及的 app_id 注入 history-{region}.json 监控池（幂等）。返回新增数。"""
    hist_path = os.path.join(DATA_DIR, f"history-{region}.json")
    hist = {}
    if os.path.exists(hist_path):
        try:
            hist = json.load(open(hist_path, encoding="utf-8"))
        except Exception:
            hist = {}
    added = 0
    for app in (data.get("iap") or []):
        aid = str(app.get("app_id"))
        if aid in hist:
            continue
        bp = app.get("base_price") or 0.0
        try:
            anchor = float(bp)
        except Exception:
            anchor = 0.0
        hist[aid] = seed_entry(anchor, today, today - datetime.timedelta(days=1))
        added += 1
    return hist, hist_path, added


def main():
    ap = argparse.ArgumentParser(description="从反斗限免种子化内购限免 IAP 库")
    ap.add_argument("--regions", default="cn,us", help="逗号分隔，默认 cn,us")
    ap.add_argument("--cache-dir", default="", help="复用本地 snapshot 缓存目录")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不写文件")
    args = ap.parse_args()
    regions = [r.strip() for r in args.regions.split(",") if r.strip()]

    today = utc_today()
    today_str = today.isoformat()

    for region in regions:
        print(f"\n=== region={region} ===")
        data = fetch_snapshot(region, args.cache_dir or None)
        current_free = collect_current_free(data, region)
        became = collect_became_free(data, region)
        print(f"[info] 当前免费内购项: {len(current_free)} | became_free 告警(App级): {sum(len(v) for v in became.values())}")

        hist, added = bootstrap_iap_history(region, current_free, became, today_str)
        if not args.dry_run:
            save_json(f"iap-history-{region}.json", hist)
        print(f"[iap-history-{region}] 新增 {added}，现有 {len(hist['items'])} 条")

        # 直接复用 detect_events 生成输出（不爬 Apple）
        events, current = detect_events(hist, region, today_str)
        if not args.dry_run:
            save_json(f"iap-free-{region}.json",
                      {"updated": today_str, "region": region,
                       "count": len(events), "events": events})
            save_json(f"iap-current-free-{region}.json",
                      {"updated": today_str, "region": region,
                       "count": len(current), "items": current})
        promo = sum(1 for e in events)
        perm = sum(1 for c in current if c.get("permanent_free"))
        print(f"[iap-free-{region}] 限时免费事件 {len(events)}（其中促销 {promo}）")
        print(f"[iap-current-free-{region}] 当前免费内购 {len(current)}（永久 {perm} / 促销 {len(current)-perm}）")

        # 注入监控池
        pooled, hist_path, padd = seed_pool(region, data, today)
        if not args.dry_run:
            os.makedirs(DATA_DIR, exist_ok=True)
            json.dump(pooled, open(hist_path, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
        print(f"[history-{region}] 监控池新增 App: {padd}（池总量 {len(pooled)}）")

    if args.dry_run:
        print("\n[dry-run] 未写任何文件")


if __name__ == "__main__":
    main()

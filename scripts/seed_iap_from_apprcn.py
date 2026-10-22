#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从「反斗限免」(apprcn) 拉取「内购限免」清单，bootstrap 进 IAP 监控库（P2 配套种子器）
===================================================================================

设计原则（2026-10-22 用户拍板）
------------------------------
**只保留「限时内购免费」（有 became_free 促销证据 + 当前确实免费）。**
任何「一直免费 / 永久免费」的内购都不符合要求，一律不注入、不展示。

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
4. bootstrap 进 data/iap-history-{region}.json（**只注入限时项**）：
     - 仅当某 (app_id, 内购名) 同时命中「当前 free」与「became_free 证据」才注入；
       ever_paid=True、free_since=告警日、原价（有则显示，无则标「—」）。
     - 未命中 became_free 的「当前免费」内购 → 视为永久免费噪声，**一律跳过不注入**。
     - 用 manifest 记录本脚本管理的键，重跑时先清理再用最新快照重建，避免累积/残留。
     - 首次迁移：清除历史中所有 ever_paid=False 的键（彻底移除一切「一直免费」噪声）。
5. 复用 iap_collector.detect_events 重新生成 iap-free-{region}.json / iap-current-free-{region}.json
   （全程不爬 Apple，无 US 地理限制，本地即可双区播种）。
6. 把 became_free 涉及的 app_id 注入 data/history-{region}.json 监控池（幂等），
   让 iap_collector 后续持续跟踪促销结束、捕获「恢复原价」。

安全
----
- 不覆盖 P1 iap_collector 真实爬取的数据（仅清理 ever_paid=False 噪声 + 管理自有键）。
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
MANIFEST_PATH = os.path.join(DATA_DIR, ".seed_iap_apprcn_manifest.json")


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


def load_manifest():
    if os.path.exists(MANIFEST_PATH):
        try:
            return json.load(open(MANIFEST_PATH, encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_manifest(m):
    os.makedirs(DATA_DIR, exist_ok=True)
    json.dump(m, open(MANIFEST_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def bootstrap_iap_history(region, current_free, became, today, manifest):
    """只注入「当前免费 + became_free 证据」的限时内购；清理永久免费噪声与旧 apprcn 键。

    返回 (hist, added, manifest)。
    """
    hist_path = os.path.join(DATA_DIR, f"iap-history-{region}.json")
    hist = {"meta": {"region": region, "version": 1}, "items": {}}
    if os.path.exists(hist_path):
        try:
            hist = json.load(open(hist_path, encoding="utf-8"))
        except Exception:
            pass
    hist.setdefault("items", {})
    items = hist["items"]

    # 1) 清理上次本脚本管理的键
    old_keys = manifest.get(region, [])
    for k in old_keys:
        items.pop(k, None)

    # 2) 首次迁移：清除所有「一直免费」噪声（ever_paid=False），符合「只保留限时」原则
    if not old_keys:
        for k in list(items):
            if items[k].get("ever_paid") is False:
                items.pop(k, None)

    # 3) 注入当前限时项（仅 became_free 命中）
    new_keys = []
    added = 0
    for cf in current_free:
        aid = cf["app_id"]
        iap_name = cf["iap_name"]
        key = f"{aid}::{iap_name}"
        alert = pick_alert(became, aid, iap_name)
        if not alert:
            continue  # 无促销证据 → 视为永久免费，跳过
        old = alert["old_price_text"]
        first_price = old if old else "—"  # 无原价锚点：用 — 表示原价未知
        rec = {
            "app_id": aid,
            "app_name": cf["app_name"],
            "name": iap_name,
            "region": region,
            "first_date": today,
            "first_price": first_price,
            "last_date": today,
            "last_price": cf["price_text"],
            "last_change_date": today,
            "ever_paid": True,
            "last_paid_date": alert["date"],
            "free_since": alert["date"],
            "changes": {alert["date"]: first_price, today: cf["price_text"]},
            "source": "apprcn",
        }
        items[key] = rec  # 覆盖（含上版无 source 的同名限时键）
        new_keys.append(key)
        added += 1

    hist["meta"].update({"updated": today, "seeded_from": "apprcn",
                         "seed_added": added, "seed_total": len(items)})
    manifest[region] = new_keys
    return hist, added, manifest


def seed_pool(region, became, today):
    """把 became_free 涉及的 app_id 注入 history-{region}.json 监控池（幂等）。返回新增数。"""
    hist_path = os.path.join(DATA_DIR, f"history-{region}.json")
    hist = {}
    if os.path.exists(hist_path):
        try:
            hist = json.load(open(hist_path, encoding="utf-8"))
        except Exception:
            hist = {}
    added = 0
    for aid in became:  # became 的 keys 即 app_id（字符串）
        if aid in hist:
            continue
        hist[aid] = seed_entry(0.0, today, today - datetime.timedelta(days=1))
        added += 1
    return hist, hist_path, added


def main():
    ap = argparse.ArgumentParser(description="从反斗限免种子化「限时」内购限免 IAP 库")
    ap.add_argument("--regions", default="cn,us", help="逗号分隔，默认 cn,us")
    ap.add_argument("--cache-dir", default="", help="复用本地 snapshot 缓存目录")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不写文件")
    args = ap.parse_args()
    regions = [r.strip() for r in args.regions.split(",") if r.strip()]

    today = utc_today()
    today_str = today.isoformat()
    manifest = load_manifest()

    for region in regions:
        print(f"\n=== region={region} ===")
        data = fetch_snapshot(region, args.cache_dir or None)
        current_free = collect_current_free(data, region)
        became = collect_became_free(data, region)
        n_became = sum(len(v) for v in became.values())
        print(f"[info] 当前免费内购项: {len(current_free)} | became_free 告警: {n_became}")

        hist, added, manifest = bootstrap_iap_history(region, current_free, became, today_str, manifest)
        if not args.dry_run:
            save_json(f"iap-history-{region}.json", hist)
        print(f"[iap-history-{region}] 新增限时 {added}，现有 {len(hist['items'])} 条（仅限时）")

        # 直接复用 detect_events 生成输出（不爬 Apple）
        events, current = detect_events(hist, region, today_str)
        if not args.dry_run:
            save_json(f"iap-free-{region}.json",
                      {"updated": today_str, "region": region,
                       "count": len(events), "events": events})
            save_json(f"iap-current-free-{region}.json",
                      {"updated": today_str, "region": region,
                       "count": len(current), "items": current})
        perm = sum(1 for c in current if c.get("permanent_free"))
        print(f"[iap-free-{region}] 限时免费事件 {len(events)}")
        print(f"[iap-current-free-{region}] 当前免费内购 {len(current)}（永久 {perm}）")

        # 注入监控池（仅 became_free 涉及的 app_id）
        pooled, hist_path, padd = seed_pool(region, became, today)
        if not args.dry_run:
            os.makedirs(DATA_DIR, exist_ok=True)
            json.dump(pooled, open(hist_path, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
        print(f"[history-{region}] 监控池新增 App: {padd}（池总量 {len(pooled)}）")

    if not args.dry_run:
        save_manifest(manifest)
        print(f"\n[manifest] 已更新 {MANIFEST_PATH}")
    else:
        print("\n[dry-run] 未写任何文件")


if __name__ == "__main__":
    main()

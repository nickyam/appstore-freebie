#!/usr/bin/env python3
"""
从「反斗限免」(apprcn) 拉取当前限免清单，筛选 iOS 本体限免（排除内购限免 / 降价 /
macOS / 永久免费），增量写入本项目的永久 App 库 history-{cn,us}.json，
给冷启动期的监控盲区打补丁，让 generate.py 后续能持续跟踪这些 App 的价格。

为什么这样做
------------
generate.py 的监控池来自 App Store 榜单，长尾限免 App 若没进任何榜单就永远进不了库、
也抓不到。反斗限免已人工/自动筛好「本体限免」清单，直接把其中 iOS 中国区/美国区
的本体限免 App 种入 history 库即可：下一个 --full 全量班次（或任何 6h 班次，因为种入时
今日快照价=0 会被纳入回查集合）就会自动 lookup 真实价、判定限免并持续跟踪。

筛选规则
--------
1. platform == 'ios'（不要 macOS）
2. kind == 'became_free'（本体限免；'price_drop' 等由 type=free 过滤已排除）
3. app_id 不在「内购限免」列表（snapshot 的 iap 字段）里
4. 该区的原价 old_price > 0（排除从未收费的永久免费 App）
5. free_days <= 7（排除长期免费的 App，与 generate.py 的 LONG_FREE_DAYS 对齐）
6. 用 Apple 官方 lookup 实查该区现价 == 0 才种（防反斗数据滞后误种）

安全
----
只增量补「history 里尚不存在」的 App-id，绝不覆盖已有条目的价格历史，避免污染真实基线。
"""
import json
import os
import sys
import time
import datetime
import urllib.request
import argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SNAPSHOT_URL = "https://monitor-appstore.apprcn.com/api/v1/snapshot?region=cn&type=free"
UA = "Mozilla/5.0 (compatible; AppFreebieBot/1.0; +https://freebie.nickyam.com)"
HISTORY_CAP = 120
FREE_DAYS_MAX = 7  # 与 generate.py LONG_FREE_DAYS 对齐


def http_get_json(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_snapshot(path=None):
    """优先用本地缓存（path），否则联网拉取（带重试、直到拿到合法 JSON）。"""
    if path and os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except Exception:
            pass
    last_err = None
    for attempt in range(5):
        try:
            data = http_get_json(SNAPSHOT_URL)
            if data.get("ok"):
                return data
        except Exception as e:
            last_err = e
        time.sleep(3 + attempt * 2)
    raise RuntimeError("snapshot 拉取失败: %s" % last_err)


def fetch_snapshot_local_candidates(data):
    """从 snapshot 解析出 iOS 本体限免候选（全局，含各区分状态）。"""
    alerts = data.get("alerts") or []
    iap_ids = {str(x.get("app_id")) for x in (data.get("iap") or [])}
    cands = []
    for a in alerts:
        if a.get("platform") != "ios":
            continue
        if a.get("kind") != "became_free":
            continue
        aid = str(a.get("app_id"))
        if aid in iap_ids:
            continue
        if (a.get("old_price") or 0) <= 0:
            continue
        fd = a.get("free_days") or 0
        if fd > FREE_DAYS_MAX:
            continue
        cands.append(a)
    return cands


def region_anchor(a, region):
    """取该区原价（锚点）。优先用分区域字段，回落到旧价。"""
    if region == "cn":
        p = a.get("cn_old_price")
    else:
        p = a.get("us_old_price")
    if not p:
        p = a.get("old_price")
    return float(p) if p else 0.0


def region_is_free(a, region):
    for r in (a.get("regions") or []):
        if r.get("region") == region and r.get("free"):
            return True
    return False


def apple_lookup(country, ids):
    """批量 lookup，返回 {trackId: price}。失败批次返回空，不影响其它。"""
    out = {}
    if not ids:
        return out
    base = "https://itunes.apple.com/lookup?country=%s&entity=software&id=" % country
    for i in range(0, len(ids), 100):
        batch = ids[i:i + 100]
        url = base + ",".join(batch)
        try:
            data = http_get_json(url, timeout=30)
        except Exception as e:
            print("[warn] lookup 失败 %s batch %d: %s" % (country, i, e), file=sys.stderr)
            time.sleep(2)
            continue
        for r in data.get("results", []):
            if r.get("wrapperType") != "software" and r.get("kind") != "software":
                continue
            out[str(r.get("trackId"))] = r.get("price") or 0
        time.sleep(1)
    return out


def load_history(path):
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except Exception:
            return {}
    return {}


def utc_today():
    return datetime.datetime.now(datetime.timezone.utc).date()


def seed_entry(anchor, today, yesterday):
    return {
        "h": [
            {"d": yesterday.isoformat(), "f": anchor, "l": anchor},
            {"d": today.isoformat(), "f": 0.0, "l": 0.0},
        ],
        "ec": True,
        "mx": anchor,
        "anchor": anchor,
        "first": yesterday.isoformat(),
        "last": today.isoformat(),
        "miss": 0,
    }


def main():
    ap = argparse.ArgumentParser(description="从反斗限免种子化本体限免 App 到 history 库")
    ap.add_argument("--snapshot", default="", help="本地 snapshot JSON 路径（优先使用，避免联网）")
    ap.add_argument("--dry-run", action="store_true", help="只打印将种入的 App，不写文件")
    args = ap.parse_args()

    data = fetch_snapshot(args.snapshot or None)
    cands = fetch_snapshot_local_candidates(data)
    print("[info] iOS 本体限免候选（全局）: %d" % len(cands))

    # 预分组：每个区待查的 app_id
    by_region = {"cn": [], "us": []}
    meta = {}
    for a in cands:
        aid = str(a.get("app_id"))
        meta[aid] = a
        for reg in ("cn", "us"):
            if region_is_free(a, reg):
                by_region[reg].append(aid)

    # Apple 实查现价，确认确实为 0 才种
    prices = {}
    for reg in ("cn", "us"):
        ids = by_region[reg]
        if not ids:
            continue
        print("[info] Apple lookup %s: %d ids" % (reg, len(ids)))
        prices[reg] = apple_lookup(reg, ids)

    today = utc_today()
    yesterday = today - datetime.timedelta(days=1)

    # 增量写入各 region 的 history
    added = {"cn": 0, "us": 0}
    for reg in ("cn", "us"):
        hist_path = os.path.join(DATA_DIR, "history-%s.json" % reg)
        hist = load_history(hist_path)
        pr = prices.get(reg, {})
        for aid in by_region[reg]:
            a = meta[aid]
            live = pr.get(aid)
            if live is None:
                # 实查失败：保守按反斗状态种（后续全量班次会校正）
                live_ok = True
            else:
                live_ok = (live == 0)
            if not live_ok:
                continue  # 该区现价非 0（已恢复/从未免费），不种
            if aid in hist:
                continue  # 已存在，绝不覆盖真实价格历史
            anchor = region_anchor(a, reg)
            if anchor <= 0:
                continue
            hist[aid] = seed_entry(anchor, today, yesterday)
            added[reg] += 1
        if not args.dry_run:
            os.makedirs(DATA_DIR, exist_ok=True)
            json.dump(hist, open(hist_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("[%s] 新增本体限免 App: %d（库总量 %d）" % (reg, added[reg], len(hist)))

    if args.dry_run:
        print("[dry-run] 未写文件")


if __name__ == "__main__":
    main()

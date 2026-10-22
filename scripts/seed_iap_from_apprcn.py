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
import re
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
ITUNES_LOOKUP = "https://itunes.apple.com/lookup?id={ids}&country={region}&limit=200"
UA = "Mozilla/5.0 (compatible; AppFreebieBot/1.0; +https://appstore.nickyam.com)"
MANIFEST_PATH = os.path.join(DATA_DIR, ".seed_iap_apprcn_manifest.json")


def http_get_json(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def esc_html(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;") \
                      .replace(">", "&gt;").replace('"', "&quot;")


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


def lookup_apps(region, app_ids):
    """iTunes lookup 批量补 App 元数据（图标/开发者/分类/评分/官方链接）。

    iTunes API 无地域跳转（与 apps.apple.com 商品页不同），本地双区均可直查。
    返回 {app_id: {name, dev, genre, rating, icon, url}}。
    """
    meta = {}
    ids = sorted(app_ids)
    for i in range(0, len(ids), 100):
        batch = ids[i:i + 100]
        url = ITUNES_LOOKUP.format(ids=",".join(batch), region=region)
        try:
            data = http_get_json(url, timeout=30)
        except Exception as e:
            print(f"[warn] iTunes lookup({region}, {len(batch)} ids) 失败: {e}")
            continue
        for r in (data.get("results") or []):
            aid = str(r.get("trackId") or "")
            if not aid:
                continue
            g = r.get("genres")
            genre = g[0] if isinstance(g, list) and g else (r.get("primaryGenreName", "") or "")
            meta[aid] = {
                "name": r.get("trackName") or "",
                "dev": r.get("artistName") or "",
                "genre": genre,
                "rating": r.get("averageUserRating") or 0,
                "icon": r.get("artworkUrl512") or r.get("artworkUrl100") or "",
                "url": r.get("trackViewUrl") or "",
            }
        time.sleep(1)
    return meta


def enrich_events(region, events, current, data, appmeta):
    """给事件/当前免费项补充 icon/dev/genre/rating/page 字段（就地修改）。"""
    snap_icons = {str(a.get("app_id")): (a.get("artwork_url") or "")
                  for a in (data.get("iap") or [])}
    for coll in (events, current):
        for e in coll:
            aid = e["app_id"]
            m = appmeta.get(aid) or {}
            e["icon"] = m.get("icon") or snap_icons.get(aid, "")
            e["dev"] = m.get("dev", "")
            e["genre"] = m.get("genre", "")
            e["rating"] = m.get("rating", 0)
            if m.get("url"):
                e["url"] = m["url"]
            # 全部给站内独立页（无评分也生成，与本体限免「无评分不收录」策略不同：
            # IAP 页面数量少、由 seed/iap_collector 主动维护，prune 会跳过 type=iap 页）
            e["page"] = f"app/{region}-{aid}.html"


def write_iap_pages(region, events, appmeta, today):
    """为限时内购 App 生成独立详情页（复用 app-page.html 模板），返回写入数。

    页面 __APP__.type = "iap"，前端 renderDetail 据此渲染「内购限时免费」区块，
    且不会被 iTunes 实时 App 自身价格覆盖头部「免费」标记。
    同一 App 多个内购限免 → 一个页面聚合展示。
    """
    tpl_path = os.path.join(REPO, "app-page.html")
    if not os.path.exists(tpl_path):
        print("[warn] app-page.html 模板缺失，跳过 IAP 独立页生成")
        return 0
    with open(tpl_path, encoding="utf-8") as f:
        tpl = f.read()
    app_dir = os.path.join(REPO, "app")
    os.makedirs(app_dir, exist_ok=True)

    by_app, order = {}, []
    for e in events:
        if e["app_id"] not in by_app:
            order.append(e["app_id"])
        by_app.setdefault(e["app_id"], []).append(e)

    free_label = "免费" if region == "cn" else "Free"
    count = 0
    for aid in order:
        evs = by_app[aid]
        m = appmeta.get(aid) or {}
        name = evs[0].get("app_name") or m.get("name") or f"App {aid}"
        iap_names = [x["iap"] for x in evs]
        iap_disp = "、".join(iap_names[:3]) + ("…" if len(iap_names) > 3 else "")
        if len(evs) == 1:
            title = "%s 内购「%s」限时免费 · 苹果限免雷达" % (name, iap_names[0])
        else:
            title = "%s 内购限时免费（%d 项）· 苹果限免雷达" % (name, len(evs))
        orig = next((x.get("last_paid_price") for x in evs
                     if x.get("last_paid_price") and x["last_paid_price"] != "—"), "")
        fs = min((x.get("free_since") or today) for x in evs)
        days = max((x.get("days_free") or 0) for x in evs)
        if orig:
            desc = "%s 的内购项目「%s」原价 %s，现在限时免费（自 %s 起）。附 App 介绍、截图与中美两区价格对比。" % (
                name, iap_disp, orig, fs)
        else:
            desc = "%s 的内购项目「%s」现在限时免费（自 %s 起）。附 App 介绍、截图与中美两区价格对比。" % (
                name, iap_disp, fs)
        page_rel = "app/%s-%s.html" % (region, aid)
        item = {
            "id": aid, "name": name,
            "dev": m.get("dev", ""), "genre": m.get("genre", ""),
            "normal": orig, "current": free_label,
            "icon": evs[0].get("icon", ""), "rating": evs[0].get("rating", 0),
            "url": evs[0].get("url", ""), "region": region,
            "type": "iap",
            "iap": "、".join(iap_names),
            "iap_items": [{"name": x["iap"],
                           "last_paid_price": x.get("last_paid_price", ""),
                           "free_since": x.get("free_since", ""),
                           "days_free": x.get("days_free", 0)} for x in evs],
            "free_since": fs, "days_free": days,
            "is_new": days == 0,
            "series": [], "phistory": [],
        }
        ld = {
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            "name": name,
            "operatingSystem": "iOS",
            "applicationCategory": m.get("genre", ""),
            "offers": {"@type": "Offer", "price": "0",
                       "priceCurrency": "CNY" if region == "cn" else "USD"},
            "url": item.get("url", ""),
        }
        html = tpl
        html = html.replace("__TITLE__", esc_html(title))
        html = html.replace("__DESC__", esc_html(desc))
        html = html.replace("__OG_TITLE__", esc_html(title))
        html = html.replace("__OG_DESC__", esc_html(desc))
        html = html.replace("__APP_NAME__", esc_html(name))
        html = html.replace("__PAGE_DATE__", today)
        html = html.replace("__APP_LD__", json.dumps(ld, ensure_ascii=False, indent=2))
        app_json = json.dumps(item, ensure_ascii=False).replace("</", "<\\/")
        html = html.replace("window.__APP__ = null;", "window.__APP__ = " + app_json + ";")
        page_url = "https://appstore.limzero.com/" + page_rel
        html = html.replace("__CANON__", esc_html(page_url))
        html = html.replace("__OG_URL__", esc_html(page_url))
        og_img = item.get("icon", "")
        if og_img:
            og_img = re.sub(r'/(\d+)x(\d+)bb(\.\w+)$', r'/512x512bb\3', og_img)
        html = html.replace("__OG_IMAGE__", esc_html(og_img))
        with open(os.path.join(REPO, page_rel), "w", encoding="utf-8") as f:
            f.write(html)
        count += 1
    return count


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

        # 直接复用 detect_events 生成输出（不爬 Apple 商品页）
        events, current = detect_events(hist, region, today_str)

        # 补 App 元数据（图标/开发者/分类/评分）→ 独立详情页 + 首页真图标
        appmeta = lookup_apps(region, {e["app_id"] for e in events} | {c["app_id"] for c in current})
        enrich_events(region, events, current, data, appmeta)
        if not args.dry_run:
            npages = write_iap_pages(region, events, appmeta, today_str)
            print(f"[app pages] IAP 独立页写入 {npages} 个")

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
        # 刷新 sitemap（IAP 独立页落在 app/ 下，复用 generate.py 的全量收录逻辑）
        try:
            from generate import write_sitemap
            print(f"[sitemap] urls={write_sitemap()}")
        except Exception as e:
            print(f"[warn] sitemap 刷新失败: {e}")
    else:
        print("\n[dry-run] 未写任何文件")


if __name__ == "__main__":
    main()

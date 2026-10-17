#!/usr/bin/env python3
"""
App Store 限免清单生成器（cn 中国商店）
========================================
思路：
- 苹果的 iTunes RSS 榜单与 Search API 均为官方、免密钥接口。
- 每天抓取「免费榜」与「付费榜」Top 200，再用 lookup 拿到每个 App 的精确价格。
- 与本地保存的「常规价基线」(baseline.json) 对比：
    * 当前价格=0 且基线>0  → 限免（平时收费，今天免费）
    * 当前价格>0 且 <基线   → 特价（降价但未免费）
- 输出 data/free-today.json 供前端渲染；更新 baseline.json。

首次运行仅播种基线（不报限免）；次日 09:00 起即可检出限免。
全部数据来自 Apple 官方，图标/截图均走苹果 CDN 链接，不转存。
"""
import json
import os
import re
import sys
import time
import datetime
import urllib.request
import urllib.error

COUNTRY = "cn"
FREE_LIMIT = 200
PAID_LIMIT = 200
RSS_BASE = f"https://itunes.apple.com/{COUNTRY}/rss"
LOOKUP = f"https://itunes.apple.com/lookup?country={COUNTRY}&entity=software&id="

UA = "Mozilla/5.0 (compatible; AppFreebieBot/1.0; +https://example.com)"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
BASELINE_PATH = os.path.join(DATA_DIR, "baseline.json")
OUT_PATH = os.path.join(DATA_DIR, "free-today.json")


def http_get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_chart(kind, limit):
    url = f"{RSS_BASE}/{kind}/limit={limit}/json"
    try:
        data = http_get_json(url)
    except Exception as e:
        print(f"[warn] 拉取榜单失败 {kind}: {e}", file=sys.stderr)
        return []
    entries = data.get("feed", {}).get("entry", [])
    if not isinstance(entries, list):
        entries = [entries] if entries else []
    apps = []
    for e in entries:
        name = (e.get("im:name") or {}).get("label", "")
        dev = (e.get("im:artist") or {}).get("label", "")
        id_obj = e.get("id") or {}
        aid = None
        if isinstance(id_obj, dict):
            aid = (id_obj.get("attributes") or {}).get("im:id")
            if not aid:
                m = re.search(r"id(\d+)", id_obj.get("label", ""))
                if m:
                    aid = m.group(1)
        category = (e.get("category") or {}).get("attributes", {}).get("label", "")
        imgs = e.get("im:image") or []
        icon = imgs[-1].get("label") if imgs else ""
        if aid:
            apps.append({"id": str(aid), "name": name, "dev": dev, "category": category, "icon": icon})
    return apps


def lookup(ids):
    out = {}
    if not ids:
        return out
    for i in range(0, len(ids), 100):
        batch = ids[i:i + 100]
        url = LOOKUP + ",".join(batch)
        try:
            data = http_get_json(url)
        except Exception as e:
            print(f"[warn] lookup 失败 batch {i}: {e}", file=sys.stderr)
            time.sleep(2)
            continue
        for r in data.get("results", []):
            if r.get("wrapperType") != "software" and r.get("kind") != "software":
                continue
            out[str(r.get("trackId"))] = r
        time.sleep(1)  # 礼貌限速，远低于 20次/分
    return out


def main():
    free_apps = fetch_chart("topfreeapplications", FREE_LIMIT)
    paid_apps = fetch_chart("toppaidapplications", PAID_LIMIT)

    baseline = {}
    if os.path.exists(BASELINE_PATH):
        try:
            with open(BASELINE_PATH, encoding="utf-8") as f:
                baseline = json.load(f)
        except Exception:
            baseline = {}

    ids = [a["id"] for a in (free_apps + paid_apps) if a.get("id")]
    details = lookup(ids)

    freebies = []
    deals = []

    def record(cid, d):
        baseline[cid] = {
            "name": d.get("trackName", ""),
            "dev": d.get("artistName", ""),
            "genre": d.get("genre", ""),
            "price": d.get("price", 0) or 0,
            "formatted": d.get("formattedPrice", ""),
            "icon": d.get("artworkUrl100", "") or d.get("artworkUrl512", ""),
            "url": d.get("trackViewUrl", ""),
        }

    # 限免：当前免费、基线>0
    for a in free_apps:
        d = details.get(a["id"])
        if not d:
            continue
        cur = d.get("price", 0) or 0
        cid = a["id"]
        prev = baseline.get(cid)
        if cur == 0 and prev is not None and prev.get("price", 0) > 0:
            freebies.append({
                "id": cid,
                "name": d.get("trackName", ""),
                "dev": d.get("artistName", ""),
                "genre": d.get("genre", ""),
                "normal": prev.get("formatted", ""),
                "current": d.get("formattedPrice", "免费"),
                "icon": d.get("artworkUrl100", "") or d.get("artworkUrl512", ""),
                "url": d.get("trackViewUrl", ""),
            })
        record(cid, d)

    # 特价：当前>0 且 <基线
    for a in paid_apps:
        d = details.get(a["id"])
        if not d:
            continue
        cur = d.get("price", 0) or 0
        cid = a["id"]
        prev = baseline.get(cid)
        if prev is not None and cur > 0 and cur < prev.get("price", 0):
            deals.append({
                "id": cid,
                "name": d.get("trackName", ""),
                "dev": d.get("artistName", ""),
                "genre": d.get("genre", ""),
                "normal": prev.get("formatted", ""),
                "current": d.get("formattedPrice", ""),
                "icon": d.get("artworkUrl100", "") or d.get("artworkUrl512", ""),
                "url": d.get("trackViewUrl", ""),
            })
        record(cid, d)

    # 按名称排序，稳定输出
    freebies.sort(key=lambda x: x["name"])
    deals.sort(key=lambda x: x["name"])

    today = datetime.date.today().isoformat()
    result = {
        "date": today,
        "country": COUNTRY,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "freebies": freebies,
        "deals": deals,
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    with open(BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(baseline, f, ensure_ascii=False, indent=2)

    print(f"[ok] date={today} freebies={len(freebies)} deals={len(deals)} baseline_size={len(baseline)}")


if __name__ == "__main__":
    main()

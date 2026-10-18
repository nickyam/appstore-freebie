#!/usr/bin/env python3
"""
App Store 限免清单生成器（支持 cn 中国区 / us 美国区）
====================================================
思路：
- 苹果的 iTunes RSS 榜单与 Search API 均为官方、免密钥接口。
- 通过 --country 参数指定地区（cn / us），每天抓取「免费榜」与「付费榜」Top 200，
  再用 lookup 拿到每个 App 的精确价格。
- 与本地保存的「常规价基线」(baseline-{country}.json) 对比：
    * 当前价格=0 且基线>0  → 限免（平时收费，今天免费）
    * 当前价格>0 且 <基线   → 特价（降价但未免费）
- 输出 data/free-today-{country}.json 供前端渲染；更新 baseline-{country}.json。

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
import argparse

FREE_LIMIT = 200
PAID_LIMIT = 200
UA = "Mozilla/5.0 (compatible; AppFreebieBot/1.0; +https://example.com)"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")


def http_get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_chart(country, kind, limit):
    rss_base = f"https://itunes.apple.com/{country}/rss"
    url = f"{rss_base}/{kind}/limit={limit}/json"
    try:
        data = http_get_json(url)
    except Exception as e:
        print(f"[warn] 拉取榜单失败 {country}/{kind}: {e}", file=sys.stderr)
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


def lookup(country, ids):
    lookup_url = f"https://itunes.apple.com/lookup?country={country}&entity=software&id="
    out = {}
    if not ids:
        return out
    for i in range(0, len(ids), 100):
        batch = ids[i:i + 100]
        url = lookup_url + ",".join(batch)
        try:
            data = http_get_json(url)
        except Exception as e:
            print(f"[warn] lookup 失败 {country} batch {i}: {e}", file=sys.stderr)
            time.sleep(2)
            continue
        for r in data.get("results", []):
            if r.get("wrapperType") != "software" and r.get("kind") != "software":
                continue
            out[str(r.get("trackId"))] = r
        time.sleep(1)  # 礼貌限速，远低于 20次/分
    return out


def main():
    parser = argparse.ArgumentParser(description="App Store 限免清单生成器")
    parser.add_argument("--country", required=True, choices=["cn", "us"], help="地区：cn 中国区 / us 美国区")
    args = parser.parse_args()
    country = args.country

    baseline_path = os.path.join(DATA_DIR, f"baseline-{country}.json")
    out_path = os.path.join(DATA_DIR, f"free-today-{country}.json")

    free_apps = fetch_chart(country, "topfreeapplications", FREE_LIMIT)
    paid_apps = fetch_chart(country, "toppaidapplications", PAID_LIMIT)

    baseline = {}
    if os.path.exists(baseline_path):
        try:
            with open(baseline_path, encoding="utf-8") as f:
                baseline = json.load(f)
        except Exception:
            baseline = {}

    ids = [a["id"] for a in (free_apps + paid_apps) if a.get("id")]
    details = lookup(country, ids)

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
                "current": "免费",  # 限免统一以中文展示
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
        "country": country,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "freebies": freebies,
        "deals": deals,
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump(baseline, f, ensure_ascii=False, indent=2)

    print(f"[ok] country={country} date={today} freebies={len(freebies)} deals={len(deals)} baseline_size={len(baseline)}")


if __name__ == "__main__":
    main()

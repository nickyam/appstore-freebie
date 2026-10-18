#!/usr/bin/env python3
"""
App Store 限免清单生成器（支持 cn 中国区 / us 美国区）
====================================================
核心思路
--------
- 苹果 iTunes RSS 榜单 + Search API 均为官方、免密钥接口。
- 限免（价格=0）的 App 永远不会出现在「付费榜」，而刚变免费的 App 也未必挤进
  「免费榜 TopN」，所以单纯扫描当天榜单在数学上几乎抓不到限免。
- 本生成器采用「**宽监控池 + 全量回查**」策略：
    1. 按 22 个分类抓取各自「付费榜 Top100」→ 覆盖数千个"容易做限免"的付费 App；
    2. 附带抓取「免费榜 Top100」→ 兜住已经冲上免费榜的限免 App；
    3. 把上述 ID 与本地历史基线(baseline) **取并集**，全部用 lookup 核对实时价；
    4. 与基线价格对比——只有"昨天还收费、今天变 0 元"的才标【限免】，
       价格降低但未免费的单独归【特价】；
    5. 基线每日漂移为当前价，确保限免/特价只在新变化当天被报出。
- 首次运行仅播种基线（不报限免）；次日 09:00 起即可稳定检出。
- 所有数据来自 Apple 官方，图标直接引用苹果 CDN，不转存。
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

# 各分类付费榜 Top100 共同组成"易限免监控池"
GENRE_LIMIT = 100
FREE_LIMIT = 100
UA = "Mozilla/5.0 (compatible; AppFreebieBot/1.0; +https://freebie.nickyam.com)"
MAX_DISPLAY = 100  # 前端最多展示的限免/特价数量（基线仍全量保留）

# iOS App 全部一级分类 genre id
GENRE_IDS = [
    6000, 6001, 6002, 6003, 6004, 6005, 6006, 6007, 6008, 6009,
    6010, 6011, 6012, 6013, 6014, 6015, 6016, 6017, 6018, 6019,
    6020, 6021,
]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")


def http_get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_chart(country, kind, limit, genre=None):
    rss_base = f"https://itunes.apple.com/{country}/rss"
    url = f"{rss_base}/{kind}/limit={limit}"
    if genre:
        url += f"/genre={genre}"
    url += "/json"
    try:
        data = http_get_json(url)
    except Exception as e:
        print(f"[warn] 拉取榜单失败 {country}/{kind}/{genre}: {e}", file=sys.stderr)
        return []
    entries = data.get("feed", {}).get("entry", [])
    if not isinstance(entries, list):
        entries = [entries] if entries else []
    ids = []
    for e in entries:
        id_obj = e.get("id") or {}
        aid = None
        if isinstance(id_obj, dict):
            aid = (id_obj.get("attributes") or {}).get("im:id")
            if not aid:
                m = re.search(r"id(\d+)", id_obj.get("label", ""))
                if m:
                    aid = m.group(1)
        if aid:
            ids.append(str(aid))
    return ids


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
        time.sleep(1)  # 礼貌限速，远低于 20 次/分
    return out


def main():
    parser = argparse.ArgumentParser(description="App Store 限免清单生成器")
    parser.add_argument("--country", required=True, choices=["cn", "us"], help="地区：cn 中国区 / us 美国区")
    args = parser.parse_args()
    country = args.country
    free_label = "免费" if country == "cn" else "Free"

    baseline_path = os.path.join(DATA_DIR, f"baseline-{country}.json")
    out_path = os.path.join(DATA_DIR, f"free-today-{country}.json")

    # 1) 构建宽监控池：22 个分类付费榜 + 免费榜
    watch_ids = []
    for g in GENRE_IDS:
        watch_ids += fetch_chart(country, "toppaidapplications", GENRE_LIMIT, genre=g)
    watch_ids += fetch_chart(country, "topfreeapplications", FREE_LIMIT)
    # 2) 叠加历史基线（持久监控，哪怕跌出榜单也继续跟踪）
    baseline = {}
    if os.path.exists(baseline_path):
        try:
            with open(baseline_path, encoding="utf-8") as f:
                baseline = json.load(f)
        except Exception:
            baseline = {}
    watch_ids += list(baseline.keys())
    # 去重保序
    seen = set()
    union = []
    for x in watch_ids:
        if x not in seen:
            seen.add(x)
            union.append(x)

    details = lookup(country, union)

    freebies = []
    deals = []

    def record(cid, d):
        baseline[cid] = {
            "name": d.get("trackName", ""),
            "dev": d.get("artistName", ""),
            "genre": d.get("genre", ""),
            "price": d.get("price", 0) or 0,
            "formatted": d.get("formattedPrice", ""),
            "icon": d.get("artworkUrl512") or d.get("artworkUrl100", ""),
            "rating": d.get("averageUserRating") or 0,
            "url": d.get("trackViewUrl", ""),
        }

    for cid, d in details.items():
        cur = d.get("price", 0) or 0
        prev = baseline.get(cid)
        prev_price = prev.get("price", 0) if prev else None
        if prev_price is not None and prev_price > 0 and cur == 0:
            freebies.append({
                "id": cid,
                "name": d.get("trackName", ""),
                "dev": d.get("artistName", ""),
                "genre": d.get("genre", ""),
                "normal": prev.get("formatted", ""),
                "current": free_label,
                "icon": d.get("artworkUrl512") or d.get("artworkUrl100", ""),
                "rating": d.get("averageUserRating") or 0,
                "url": d.get("trackViewUrl", ""),
            })
        elif prev_price is not None and cur > 0 and cur < prev_price:
            deals.append({
                "id": cid,
                "name": d.get("trackName", ""),
                "dev": d.get("artistName", ""),
                "genre": d.get("genre", ""),
                "normal": prev.get("formatted", ""),
                "current": d.get("formattedPrice", ""),
                "icon": d.get("artworkUrl512") or d.get("artworkUrl100", ""),
                "rating": d.get("averageUserRating") or 0,
                "url": d.get("trackViewUrl", ""),
            })
        record(cid, d)

    # 按评分降序 → 名称升序，优先展示优质 App
    def sort_key(x):
        return (-(x.get("rating") or 0), x.get("name") or "")
    freebies.sort(key=sort_key)
    deals.sort(key=sort_key)

    today = datetime.date.today().isoformat()
    result = {
        "date": today,
        "country": country,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "freebies": freebies[:MAX_DISPLAY],
        "deals": deals[:MAX_DISPLAY],
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump(baseline, f, ensure_ascii=False, indent=2)

    print(f"[ok] country={country} date={today} monitored={len(union)} "
          f"freebies={len(freebies)} deals={len(deals)} baseline_size={len(baseline)}")


if __name__ == "__main__":
    main()

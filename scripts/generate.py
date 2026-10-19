#!/usr/bin/env python3
"""
App Store 限免清单生成器（支持 cn 中国区 / us 美国区）
====================================================
核心思路
--------
- 苹果 iTunes RSS 榜单 + Search API 均为官方、免密钥接口。
- 限免（价格=0）的 App 永远不会出现在「付费榜」，而刚变免费的 App 也未必挤进
  「免费榜 TopN」，所以单纯扫描当天榜单在数学上几乎抓不到限免。
- 本生成器采用「**宽监控池 + 全量回查 + 促销粘性（promo watchlist）**」策略：
    1. 按 22 个分类抓取各自「付费榜 Top100」→ 覆盖数千个"容易做限免"的付费 App；
    2. 附带抓取「免费榜 Top100」→ 兜住已经冲上免费榜的限免 App；
    3. 与本地历史基线(baseline)、促销观察名单(promo-watch)取并集，全部用 lookup 核对实时价；
    4. 促销粘性规则（核心约定）：
       - 新发现「昨天收费、今天 0 元」→ 限免；「降价但未免费」→ 特价；
         同时写入 promo-watch，并**锚定其原价 normal**；
       - 已在 promo-watch 中的 App 每日继续回查：
         · 价格仍为 0              → 继续按限免展示；
         · 价格仍低于锚定原价      → 继续按特价展示；
         · 价格恢复原价及以上      → **自动下架**，移出 promo-watch；
       - 促销期间**基线价格不漂移**（保持锚定原价），只有恢复原价后才漂移为新常规价。
    5. 因此一旦某 App 进入促销，只要活动没结束（价格维持在促销水平），条目就会持续
       留在网站上，不会因为"基线被漂移成促销价"而在次日消失。
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


def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


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
    promo_path = os.path.join(DATA_DIR, f"promo-watch-{country}.json")

    # 1) 构建宽监控池：22 个分类付费榜 + 免费榜
    watch_ids = []
    for g in GENRE_IDS:
        watch_ids += fetch_chart(country, "toppaidapplications", GENRE_LIMIT, genre=g)
    watch_ids += fetch_chart(country, "topfreeapplications", FREE_LIMIT)

    # 2) 加载历史基线 + 促销观察名单，并叠加进监控池（持久跟踪，哪怕跌出榜单）
    baseline = load_json(baseline_path)
    promo = load_json(promo_path)
    watch_ids += list(baseline.keys())
    watch_ids += list(promo.keys())

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
    new_promo = {}  # 今日促销状态快照（恢复原价的 App 自然被剔除）

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
        prev = baseline.get(cid) or {}
        base_price = prev.get("price", 0) or 0
        name = d.get("trackName", "")
        dev = d.get("artistName", "")
        genre = d.get("genre", "")
        icon = d.get("artworkUrl512") or d.get("artworkUrl100", "")
        rating = d.get("averageUserRating") or 0
        url = d.get("trackViewUrl", "")

        in_promo = cid in promo
        # 原价锚点：促销中的 App 用 watchlist 锚定价；新 App 用基线价
        if in_promo:
            normal_price = promo[cid].get("normal") or base_price or 0
            normal_fmt = promo[cid].get("normal_fmt") or prev.get("formatted", "")
        else:
            normal_price = base_price
            normal_fmt = prev.get("formatted", "")

        is_free = normal_price > 0 and cur == 0
        is_deal = normal_price > 0 and cur > 0 and cur < normal_price

        if in_promo and not is_free and not is_deal:
            # 已恢复原价（或高于原价）→ 自动下架：移出观察名单，基线漂移为新常规价
            record(cid, d)
            continue

        if is_free or is_deal:
            # 进入/维持促销：保持原价锚点，促销期间基线不漂移
            new_promo[cid] = promo[cid] if in_promo else {"normal": normal_price, "normal_fmt": normal_fmt}
            if prev:
                baseline[cid] = dict(prev)  # 保留原价条目（含 price/formatted 锚点）
            item = {
                "id": cid,
                "name": name,
                "dev": dev,
                "genre": genre,
                "normal": normal_fmt,
                "current": free_label if is_free else d.get("formattedPrice", ""),
                "icon": icon,
                "rating": rating,
                "url": url,
            }
            (freebies if is_free else deals).append(item)
        else:
            # 正常价 → 基线漂移为当前价（反映最新常规价）
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
    with open(promo_path, "w", encoding="utf-8") as f:
        json.dump(new_promo, f, ensure_ascii=False, indent=2)

    print(f"[ok] country={country} date={today} monitored={len(union)} "
          f"freebies={len(freebies)} deals={len(deals)} "
          f"promo_watch={len(new_promo)} baseline_size={len(baseline)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
App Store 限免清单生成器（支持 cn 中国区 / us 美国区）
====================================================
核心思路
--------
- 苹果 iTunes RSS 榜单 + Lookup 接口均为官方、免密钥接口。
- 限免（价格=0）的 App 永远不会出现在「付费榜」，而刚变免费的 App 也未必挤进
  「免费榜 TopN」，所以单纯扫描当天榜单在数学上几乎抓不到限免。
- 本生成器采用「**宽监控池 + 30 天历史价格基线 + 日内轮询 + 促销粘性**」策略：

  1. 宽监控池：22 个一级分类的「付费榜 Top100」+「畅销榜 Top100」+ 整体「免费榜 Top200」，
     覆盖数千个"容易做限免"的 App；
  2. 叠加本地 30 天价格历史（history）与历史基线，哪怕 App 跌出榜单也持续跟踪；
  3. 每个 App 每区独立保存至少 30 天价格快照（每日首价 f / 末价 l）；
  4. 判定：
     · 限免：当前价=0 且 30 天历史中曾>0（基线判定），且连续为 0 的天数≤7（排除长期免费）；
       同时天然覆盖「日内闪免」（今日首价>0、末价=0）与「跨天」（昨日>0、今日=0）；
     · 降价：当前价 < 30 天最高价 且 降幅≥50%；
  5. 促销粘性：已在促销（限免/降价）中的 App 每日继续回查，价格回升到原价及以上自动下架；
  6. 排除永久免费：30 天全程为 0、从未收费的 App 不收录。

- 首次运行：若历史为空但有旧 baseline，则以 baseline 当日价播种一天；否则仅初始化，
  次日 09:00 起即可稳定检出（30 天基线约一个月内逐步填满）。
- 所有数据来自 Apple 官方，图标直接引用苹果 CDN，不转存。
- 调度：GitHub Actions 每 2 小时全量跑一次（含榜单重建 + 全量回查），
  捕捉日内临时限免/闪免；Cloudflare 自动部署、阿里云镜像每 2 小时同步。
"""
import json
import os
import re
import sys
import time
import datetime
import urllib.request
import argparse

# ===== 监控池规模 =====
GENRE_LIMIT = 100       # 每分类 付费榜 TopN（RSS 单源上限 100）
GROSS_LIMIT = 100       # 每分类 畅销榜 TopN
FREE_LIMIT = 200        # 整体 免费榜 TopN（RSS 可能截断到 100，无害）
HISTORY_DAYS = 30       # 价格历史保留天数
LONG_FREE_DAYS = 7       # 连续为 0 超过该天数 → 不再算限时免费
DEAL_DROP_PCT = 0.50    # 降价判定：降幅 ≥ 50%（相对 30 天最高价）
UA = "Mozilla/5.0 (compatible; AppFreebieBot/1.0; +https://freebie.nickyam.com)"
MAX_DISPLAY = 100       # 前端最多展示的限免/特价数量（历史仍全量保留）

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


def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


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


def app_genre(d):
    # iTunes lookup 已不再返回单数 genre 字段，改用本地化分类数组 / 英文主分类
    g = d.get("genres")
    if isinstance(g, list) and g:
        return g[0]
    return d.get("primaryGenreName", "") or ""


def fmt_price(country, price):
    if price == 0:
        return "免费" if country == "cn" else "Free"
    return ("¥%.2f" % price) if country == "cn" else ("$%.2f" % price)


def load_history(path):
    return load_json(path)


def seed_from_baseline(history, baseline):
    """首次无历史时，用旧 baseline 的当日价播种一天，给跨天判定一个起点。"""
    today = datetime.date.today().isoformat()
    for cid, rec in (baseline or {}).items():
        p = rec.get("price", 0) or 0
        history[cid] = [{"d": today, "f": p, "l": p}]
    return history


def update_history(history, cid, today, price):
    h = history.get(cid)
    if h and h[-1].get("d") == today:
        h[-1]["l"] = price          # 今日多次轮询：末价更新，首价保留
    else:
        h = (h or []) + [{"d": today, "f": price, "l": price}]
        history[cid] = h
    # 裁剪到 HISTORY_DAYS
    cutoff = (datetime.date.today() - datetime.timedelta(days=HISTORY_DAYS - 1)).isoformat()
    history[cid] = [e for e in history[cid] if e.get("d", "") >= cutoff]


def derive(history):
    days = history or []
    vals = [p for e in days for p in (e.get("f", 0) or 0, e.get("l", 0) or 0)]
    ever_charged = any(p > 0 for p in vals)
    max_price = max(vals) if vals else 0
    # 连续为 0 的天数（从最新一天往前数，当天需首末均为 0 才算零天）
    cz = 0
    for e in reversed(days):
        if (e.get("f", 0) or 0) == 0 and (e.get("l", 0) or 0) == 0:
            cz += 1
        else:
            break
    # 上一轮价格（用于"新触发"排序/闪免识别）
    if len(days) >= 2:
        prev = days[-2].get("l", 0) or 0
    elif days:
        prev = days[-1].get("f", 0) or 0
    else:
        prev = 0
    cur = days[-1].get("l", 0) if days else 0
    return ever_charged, max_price, cz, prev, cur


def main():
    parser = argparse.ArgumentParser(description="App Store 限免清单生成器")
    parser.add_argument("--country", required=True, choices=["cn", "us"], help="地区：cn 中国区 / us 美国区")
    args = parser.parse_args()
    country = args.country
    free_label = "免费" if country == "cn" else "Free"

    history_path = os.path.join(DATA_DIR, f"history-{country}.json")
    out_path = os.path.join(DATA_DIR, f"free-today-{country}.json")

    # 1) 构建宽监控池：22 分类 付费榜 + 畅销榜 + 整体免费榜
    watch_ids = []
    for g in GENRE_IDS:
        watch_ids += fetch_chart(country, "toppaidapplications", GENRE_LIMIT, genre=g)
        watch_ids += fetch_chart(country, "topgrossingapplications", GROSS_LIMIT, genre=g)
    watch_ids += fetch_chart(country, "topfreeapplications", FREE_LIMIT)

    # 2) 加载 30 天历史；若为空用旧 baseline 播种一天
    history = load_history(history_path)
    if not history:
        baseline = load_json(os.path.join(DATA_DIR, f"baseline-{country}.json"))
        if baseline:
            history = seed_from_baseline(history, baseline)
            print(f"[info] seeded history from baseline: {len(history)} apps")

    # 3) 叠加历史中的所有 App（持续跟踪，哪怕跌出榜单）
    watch_ids += list(history.keys())

    # 去重保序
    seen = set()
    union = []
    for x in watch_ids:
        if x not in seen:
            seen.add(x)
            union.append(x)

    details = lookup(country, union)
    today = datetime.date.today().isoformat()

    freebies = []
    deals = []

    for cid, d in details.items():
        cur = d.get("price", 0) or 0
        name = d.get("trackName", "")
        dev = d.get("artistName", "")
        genre = app_genre(d)
        icon = d.get("artworkUrl512") or d.get("artworkUrl100", "")
        rating = d.get("averageUserRating") or 0
        url = d.get("trackViewUrl", "")

        # 写入/更新今日价格快照
        update_history(history, cid, today, cur)
        ever_charged, max_price, cz, prev, cur = derive(history[cid])

        is_free = False
        is_deal = False
        if cur == 0:
            # 限免：曾收费 + 非长期免费
            if ever_charged and cz <= LONG_FREE_DAYS:
                is_free = True
        else:
            # 降价：相对 30 天最高价降幅 ≥ 50%
            if ever_charged and max_price > 0 and cur < max_price \
                    and (max_price - cur) / max_price >= DEAL_DROP_PCT:
                is_deal = True

        if is_free or is_deal:
            newly = (cur == 0 and prev > 0)  # 本轮/本日新触发
            # 原价锚点：优先用 30 天历史最高价（限免/降价都适用），否则回落 prev / 当前
            anchor = max_price if max_price > 0 else (prev if prev > 0 else cur)
            item = {
                "id": cid,
                "name": name,
                "dev": dev,
                "genre": genre,
                "normal": fmt_price(country, anchor),
                "current": free_label if is_free else fmt_price(country, cur),
                "icon": icon,
                "rating": rating,
                "url": url,
                "region": country,
                "type": "free" if is_free else "deal",
                "_new": newly,
            }
            (freebies if is_free else deals).append(item)

    # 排序：新触发的限免/降价优先，其次评分高、名称
    def sort_key(x):
        return (-(1 if x.get("_new") else 0), -(x.get("rating") or 0), x.get("name") or "")
    freebies.sort(key=sort_key)
    deals.sort(key=sort_key)

    result = {
        "date": today,
        "country": country,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "freebies": [{k: v for k, v in it.items() if k != "_new"} for it in freebies[:MAX_DISPLAY]],
        "deals": [{k: v for k, v in it.items() if k != "_new"} for it in deals[:MAX_DISPLAY]],
    }

    save_json(out_path, result)
    save_json(history_path, history)

    print(f"[ok] country={country} date={today} monitored={len(union)} "
          f"history={len(history)} freebies={len(freebies)} deals={len(deals)} "
          f"(display free≤{MAX_DISPLAY}, deal≤{MAX_DISPLAY})")


if __name__ == "__main__":
    main()

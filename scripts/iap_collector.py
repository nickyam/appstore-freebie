#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IAP 价格历史采集器（P1）—— 内购限免的正式数据源
==============================================
与 P0 探针（iap_probe.py）的核心区别：P0 只看「当前是否免费」的快照；本采集器
**逐 IAP 累积价格历史**，从而识别「付费 → 0」的跳变 = 真·内购限免事件，
并自动把「永久免费（tier-0 噪声）」与「促销限免」区分开。

数据流：
  data/history-{region}.json 的 app ID 池（与 app 限免同池，稳定不漂移）
    → 每日抓 apps.apple.com/{region}/app/id{id} 商品页
    → 解析 IAP 名+价（复用 iap_probe 的解析）
    → 更新 data/iap-history-{region}.json（仅记录「变价日」，压缩存储）
    → 产出 data/iap-free-{region}.json      （真·限免事件，排除永久免费）
         data/iap-current-free-{region}.json（当前所有免费内购，含永久并标注）
    → 事件流经 iTunes lookup 富化（评分/图标/开发者/分类），无评分事件一律剔除
      （与本体限免「无评分不收录」规则一致，2026-10-23 用户拍板；iTunes lookup
      无地域限制，GitHub runner 双区均可直查）

冷启动：首日只播种（ever_paid=False，free_since=None），不报事件；
        从第 2 次采集起可捕获「付费→0」跳变；观察数日稳定性后，
        永久免费项（ever_paid=False）自动归入「常驻免费」，不再污染限免 feed。

CI 注意：本采集器产出的 4 个 data/iap-*.json 由独立的 iap.yml 负责 git add，
         不要塞进 daily*.yml/seed.yml 的 PATHS（避免改坏已加固的 CI 铁律）。

用法：
  python3 iap_collector.py --region cn [--limit 2000] [--delay 0.3]
  python3 iap_collector.py --region us [--limit 2000]
  python3 iap_collector.py --selftest     # 用合成历史验证事件检测逻辑
"""
import sys, os, re, json, html, time, argparse, urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from iap_probe import fetch, parse_iap, is_free  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Safari/605.1.15")
TITLE_RE = re.compile(r'<title>(.*?)</title>', re.S)
FREE_WINDOW = 7  # 连续免费 ≤7 天算有效限免事件；超过则过期（与 app 限免同逻辑）
ITUNES_LOOKUP = "https://itunes.apple.com/lookup?id={ids}&country={region}&limit=200"


def parse_app_name(body):
    m = TITLE_RE.search(body)
    if not m:
        return ""
    t = html.unescape(m.group(1).replace("‎", "").strip())
    t = re.sub(r'\s*-?\s*App\s*-?\s*App Store.*$', '', t, flags=re.I).strip()
    return t


def load_pool(region, limit):
    """每日复查池 = 保底池 + 主池（App 榜单池）。

    保底池（2026-10-25 用户拍板，根治「僵尸条目」）：
      · data/iap-history-{region}.json 中 last_price 仍为免费的 app；
      · data/iap-current-free-{region}.json 中在挂的 app（发布集，双保险）。
    背景：主池按榜单滚动，限免 App 掉出榜单后即从池中消失，其「恢复付费」
    永远检测不到，会在网站上僵尸显示最多 FREE_WINDOW(7) 天。保底池排在主池
    前面，保证不被 limit 裁掉；代价是每次挤掉少量主池尾部 App 的复查机会。
    """
    ids, seen = [], set()

    def add(aid):
        aid = str(aid)
        if aid and aid not in seen:
            seen.add(aid)
            ids.append(aid)

    hist_path = os.path.join(REPO, "data", f"iap-history-{region}.json")
    if os.path.exists(hist_path):
        try:
            hist = json.load(open(hist_path, encoding="utf-8"))
            for rec in hist.get("items", {}).values():
                if is_free(rec.get("last_price") or ""):
                    add(rec.get("app_id"))
        except Exception as e:
            print(f"    [warn] 读 iap-history 保底池失败: {e}")

    cur_path = os.path.join(REPO, "data", f"iap-current-free-{region}.json")
    if os.path.exists(cur_path):
        try:
            cur = json.load(open(cur_path, encoding="utf-8"))
            for it in cur.get("items", []):
                add(it.get("app_id"))
        except Exception as e:
            print(f"    [warn] 读 iap-current-free 保底池失败: {e}")

    p = os.path.join(REPO, "data", f"history-{region}.json")
    if os.path.exists(p):
        d = json.load(open(p, encoding="utf-8"))
        for x in d.keys():
            add(x)
    else:
        from iap_probe import get_game_ids
        for i, _ in get_game_ids(region, min(limit, 200)):
            add(i)
    return ids[:limit]


def load_history(region):
    p = os.path.join(REPO, "data", f"iap-history-{region}.json")
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    return {"meta": {"region": region, "version": 1}, "items": {}}


def save_json(name, obj):
    with open(os.path.join(REPO, "data", name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def fetch_with_retry(url, region, tries=3):
    last = None
    for i in range(tries):
        try:
            final, body = fetch(url, region)
            if region == "us" and f"/{region}/" not in final:
                return None, "geo_blocked"
            return body, None
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code in (403, 429):
                time.sleep(2 * (i + 1))
                continue
            return None, last
        except Exception as e:
            last = str(e)
            time.sleep(1)
    return None, last


def update_history(hist, region, app_id, app_name, today, iaps):
    items = hist["items"]
    for (name, price) in iaps:
        key = f"{app_id}::{name}"
        free = is_free(price)
        rec = items.get(key)
        if rec is None:
            rec = {
                "app_id": app_id, "app_name": app_name, "name": name, "region": region,
                "first_date": today, "first_price": price,
                "last_date": today, "last_price": price,
                "last_change_date": today,
                "ever_paid": not free,
                "last_paid_date": (today if not free else None),
                "free_since": None,
                "changes": {today: price},
            }
            items[key] = rec
            continue
        # 已存在：仅在价格变化时记录
        if rec["last_price"] != price:
            rec["changes"][today] = price
            rec["last_change_date"] = today
            rec["last_date"] = today
            rec["last_price"] = price
            if not free:
                rec["ever_paid"] = True
                rec["last_paid_date"] = today
                rec["free_since"] = None          # 促销结束
            else:
                # 付费 → 免费 跳变
                if rec["ever_paid"] or rec.get("last_paid_date"):
                    rec["free_since"] = today
        else:
            rec["last_date"] = today  # 仅刷新新鲜度，不记变价


def detect_events(hist, region, today):
    events, current_free = [], []
    for key, rec in hist["items"].items():
        if not is_free(rec["last_price"]):
            continue
        permanent = not rec["ever_paid"]
        entry = {
            "app_id": rec["app_id"], "app_name": rec.get("app_name", ""),
            "iap": rec["name"], "price": rec["last_price"],
            "permanent_free": permanent, "since": rec["last_date"],
        }
        current_free.append(entry)
        if permanent:
            continue  # 永久免费噪声，不进限免事件
        fs = rec.get("free_since")
        if not fs:
            continue
        try:
            d_free = (datetime.strptime(today, "%Y-%m-%d") -
                      datetime.strptime(fs, "%Y-%m-%d")).days
        except Exception:
            d_free = 0
        if 0 <= d_free <= FREE_WINDOW:
            events.append({
                "app_id": rec["app_id"], "app_name": rec.get("app_name", ""),
                "iap": rec["name"], "price": rec["last_price"],
                "free_since": fs, "days_free": d_free,
                "last_paid_date": rec.get("last_paid_date"),
                "last_paid_price": (list(rec["changes"].values())[-2]
                                    if len(rec["changes"]) >= 2 else rec["first_price"]),
                "url": f"https://apps.apple.com/{region}/app/id{rec['app_id']}",
            })
    return events, current_free


def enrich_events_itunes(region, events):
    """给限免事件补 App 元数据（评分/图标/开发者/分类），并剔除无评分事件。

    背景：detect_events 直接产出的事件只有价格字段、没有 rating；前端首页的
    「无评分不收录」过滤（rating !== 0）对缺字段（undefined）会失效，无评分
    事件会漏进首页。iTunes lookup 与 apps.apple.com 商品页不同，无地域跳转，
    GitHub runner（美国）双区均可直查，100 id/批。

    规则（2026-10-23 用户拍板，与本体限免一致）：rating<=0 的事件一律不收录。
    站内独立页 app/{region}-{id}.html 由 generate.py 每 6h 班次写入（D 架构，
    全站唯一写页人）；此处仅当文件已存在才给 page 字段——新事件在采集器运行后、
    generate 出页前的窗口期内回退 App Store 外链，避免 404。
    """
    if not events:
        return events
    ids = sorted({e["app_id"] for e in events})
    meta = {}
    for i in range(0, len(ids), 100):
        batch = ids[i:i + 100]
        url = ITUNES_LOOKUP.format(ids=",".join(batch), region=region)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"[warn] iTunes lookup({region}, {len(batch)} ids) 失败: {e}")
            continue
        for r in (data.get("results") or []):
            aid = str(r.get("trackId") or "")
            if not aid:
                continue
            g = r.get("genres")
            meta[aid] = {
                "name": r.get("trackName") or "",
                "dev": r.get("artistName") or "",
                "genre": (g[0] if isinstance(g, list) and g
                          else (r.get("primaryGenreName") or "")),
                "rating": r.get("averageUserRating") or 0,
                "icon": r.get("artworkUrl512") or r.get("artworkUrl100") or "",
                "url": r.get("trackViewUrl") or "",
            }
        time.sleep(1)
    out = []
    for e in events:
        m = meta.get(e["app_id"]) or {}
        rating = m.get("rating") or 0
        if rating <= 0:
            continue  # 无评分不收录（与本体限免规则一致）
        e["rating"] = rating
        e["icon"] = m.get("icon", "")
        e["dev"] = m.get("dev", "")
        e["genre"] = m.get("genre", "")
        if m.get("url"):
            e["url"] = m["url"]
        if not e.get("app_name") and m.get("name"):
            e["app_name"] = m["name"]
        page_rel = "app/%s-%s.html" % (region, e["app_id"])
        if os.path.exists(os.path.join(REPO, page_rel)):
            e["page"] = page_rel
        out.append(e)
    return out


def run(region, limit, delay):
    # 按北京时间（UTC+8）翻日：内购限免的 NEW 角标与「已免费 N 天」在北京时间凌晨 0 点更新，
    # 而非 CI runner 的 UTC 午夜（=北京时间 16:00），避免用户感知到的「今天」滞后。
    today = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d")
    print(f"[*] IAP 采集 region={region} limit={limit} today={today}")
    hist = load_history(region)
    pool = load_pool(region, limit)
    print(f"[*] 池大小 {len(pool)}")
    ok = skip = 0
    for i, app_id in enumerate(pool, 1):
        url = f"https://apps.apple.com/{region}/app/id{app_id}"
        body, err = fetch_with_retry(url, region)
        if err:
            skip += 1
            if i <= 3 or i % 100 == 0:
                print(f"  [{i}] {app_id} 跳过({err})")
            continue
        try:
            app_name = parse_app_name(body)
            iaps = parse_iap(body)
        except Exception:
            skip += 1
            continue
        update_history(hist, region, app_id, app_name, today, iaps)
        ok += 1
        if i % 50 == 0:
            print(f"  ... {i}/{len(pool)} 已处理 {ok}，跳过 {skip}")
        time.sleep(delay)
    hist["meta"].update({"updated": today, "pool_size": len(pool),
                         "processed": ok, "skipped": skip})
    save_json(f"iap-history-{region}.json", hist)
    events, current_free = detect_events(hist, region, today)
    events = enrich_events_itunes(region, events)  # 补评分富化；无评分不收录
    save_json(f"iap-free-{region}.json",
              {"updated": today, "region": region, "count": len(events), "events": events})
    save_json(f"iap-current-free-{region}.json",
              {"updated": today, "region": region,
               "count": len(current_free), "items": current_free})
    print(f"[*] 完成：处理 {ok}，跳过 {skip}")
    print(f"    当前免费内购 {len(current_free)}（含永久），真·限免事件 {len(events)}")
    print(f"    历史 iap-history-{region}.json 条目 {len(hist['items'])}")
    return events


def selftest():
    fake = {"meta": {}, "items": {
        "123::礼包A": {"app_id": "123", "app_name": "测试游戏", "name": "礼包A",
            "region": "cn", "first_date": "2026-10-20", "first_price": "¥6.00",
            "last_date": "2026-10-22", "last_price": "免费", "last_change_date": "2026-10-22",
            "ever_paid": True, "last_paid_date": "2026-10-21", "free_since": "2026-10-22",
            "changes": {"2026-10-20": "¥6.00", "2026-10-22": "免费"}},
        "123::常驻免费": {"app_id": "123", "app_name": "测试游戏", "name": "常驻免费",
            "region": "cn", "first_date": "2026-10-20", "first_price": "免费",
            "last_date": "2026-10-22", "last_price": "免费", "last_change_date": "2026-10-20",
            "ever_paid": False, "last_paid_date": None, "free_since": None,
            "changes": {"2026-10-20": "免费"}},
    }}
    events, cur = detect_events(fake, "cn", "2026-10-22")
    assert any(e["iap"] == "礼包A" for e in events), "应检测到 礼包A 限免事件"
    assert not any(e["iap"] == "常驻免费" for e in events), "永久免费不应进事件"
    print("SELFTEST PASS：付费→免费 被正确识别为限免事件；永久免费被正确排除。")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", choices=["cn", "us"], default="cn")
    ap.add_argument("--limit", type=int, default=2000)
    ap.add_argument("--delay", type=float, default=0.3)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    run(args.region, args.limit, args.delay)


if __name__ == "__main__":
    main()

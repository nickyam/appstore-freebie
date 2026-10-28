#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0 探针 —— App Store 热门免费游戏「内购限免」可行性探测
========================================================
目的：验证「抓 App Store 商品页 → 解析 IAP 列表 → 找出当前以 0 价格（免费/Free）促销的内购项」
      这一玩法在真实数据上是否成立，并给出每周可捕获的免费内购条目数量，作为是否立项的功能探针。

数据源：
  1) Apple RSS：top-free-games（genre=6014）取各区当前热门 F2P 游戏 ID（避免硬编码、随榜单漂移）。
  2) App Store 商品页 apps.apple.com/{region}/app/id{id}：服务端渲染的 IAP 列表。

IAP DOM 结构（2026-10 实测 CN/US）：
  <details …> … <ul>
    <li><div class="text-pair"><span>60点券</span> <span>¥6.00</span></div></li>
    <li><div class="text-pair"><span>10点券</span> <span>¥1.00</span></div></li>
    …
  </ul>
  价格 span 形如 "¥6.00" / "$0.99" / "免费"(cn) / "Free"(us)。
  注意：开发者信息区也有 text-pair（如统一社会信用代码含数字），必须用「价格以货币符号开头 或 为免费词」过滤。

地理限制：
  US 商品页在中国大陆 IP 会被 301 跳转到 apps.apple.com/cn/iphone/today，
  故 US 抓取必须在境外执行（GitHub Actions 美国 runner）。本脚本会自动识别并跳过被跳转的 US 条目。

用法：
  python3 iap_probe.py --region cn --limit 50
  python3 iap_probe.py --region us --limit 50
输出：文本报告 + 同目录 iap_probe_{region}.json（结构化结果，便于后续转成正式采集器）。
"""
import sys, re, json, html, time, argparse, urllib.request

RSS = "https://itunes.apple.com/{region}/rss/topfreeapplications/limit={limit}/genre=6014/json"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Safari/605.1.15")
FREE_TOKENS = {"免费", "free"}  # 注意：free trial / 免费试用 不是真免费内购，见 is_trial_iap 剔除

# 试用 / 试玩 / 体验版 / 体验卡 / 体验券 / trial / free trial 一律不算「内购限免」
# （它们只是免费试用，不是真·促销限免；Apple 常把试用期标成 免费/Free，故必须按名字剔除）
TRIAL_KEYWORDS = ("试用", "试玩", "体验版", "体验卡", "体验券", "trial")
def is_trial_iap(name):
    n = (name or "").lower()
    return any(k in n for k in TRIAL_KEYWORDS)

# 价格必须以货币符号开头，或恰好是免费词（避免误吞开发者信息里的数字串）
IAP_PRICE_RE = re.compile(r'^(?:¥|\$|us\$)\s?[\d,]+(?:\.\d{2})?$', re.I)
TEXT_PAIR_RE = re.compile(r'<div class="text-pair[^"]*">(.*?)</div>', re.S)
SPAN_RE = re.compile(r'<span>(.*?)</span>', re.S)


def fetch(url, region, timeout=15):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "zh-CN,zh;q=0.9" if region == "cn" else "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        final = r.geturl()
        body = r.read().decode("utf-8", "ignore")
    return final, body


def get_game_ids(region, limit):
    final, body = fetch(RSS.format(region=region, limit=limit), region)
    d = json.loads(body)
    out = []
    for e in d["feed"]["entry"]:
        out.append((e["id"]["attributes"]["im:id"], e["im:name"]["label"]))
    return out


def parse_iap(body):
    """返回 [(name, price), ...] 仅含合法 IAP 价格项。"""
    items = []
    for m in TEXT_PAIR_RE.finditer(body):
        spans = SPAN_RE.findall(m.group(1))
        if len(spans) < 2:
            continue
        name = html.unescape(re.sub(r'\s+', ' ', spans[0])).strip()
        price = html.unescape(re.sub(r'\s+', ' ', spans[1])).strip()
        if is_trial_iap(name):
            continue                      # 试用/试玩/体验版等只是免费试用，不算内购限免
        p = price.strip()
        if IAP_PRICE_RE.match(p) or p.lower() in FREE_TOKENS:
            items.append((name, price))
    # 去重（Apple 页面偶尔重复）
    seen, uniq = set(), []
    for n, p in items:
        k = (n, p)
        if k not in seen:
            seen.add(k)
            uniq.append((n, p))
    return uniq


def is_free(price):
    p = price.strip()
    if p.lower() in FREE_TOKENS:
        return True
    if re.fullmatch(r'(?:¥|\$|us\$)?\s*0(?:\.00)?', p, re.I):
        return True
    return False


def run(region, limit, delay=0.4):
    print(f"[*] 拉取 {region} 热门免费游戏榜单 (genre=6014, limit={limit}) …")
    games = get_game_ids(region, limit)
    return _scan(region, games, delay)


def run_custom(region, games, delay, limit):
    games = games[:limit]
    print(f"[*] 自定义 ID 池：共 {len(games)} 个 app，开始抓取商品页解析 IAP …\n")
    return _scan(region, games, delay)


def _scan(region, games, delay):
    print(f"[*] 共 {len(games)} 款，开始抓取商品页解析 IAP …\n")

    rows = []          # 每款 app 的明细
    free_hits = []     # 命中免费内购的 (app, iap_name, price)
    blocked = 0
    total_iap = 0
    apps_with_iap = 0
    apps_with_free = 0

    for i, (aid, name) in enumerate(games, 1):
        url = f"https://apps.apple.com/{region}/app/id{aid}"
        try:
            final, body = fetch(url, region)
        except Exception as e:
            print(f"  [{i:>2}/{len(games)}] {name} (id={aid}) 抓取失败: {e}")
            rows.append({"id": aid, "name": name, "error": str(e), "iap": [], "free": []})
            continue

        # 地理跳转判定（仅 US 会触发）：最终 URL 不在本区 → 被跳回 CN，跳过
        if region == "us" and f"/{region}/" not in final:
            blocked += 1
            print(f"  [{i:>2}/{len(games)}] {name} (id={aid}) 被地理跳转到 {final} → 跳过(需境外 runner)")
            rows.append({"id": aid, "name": name, "geo_blocked": True, "iap": [], "free": []})
            continue

        iap = parse_iap(body)
        frees = [(n, p) for (n, p) in iap if is_free(p)]
        total_iap += len(iap)
        if iap:
            apps_with_iap += 1
        if frees:
            apps_with_free += 1
            for (n, p) in frees:
                free_hits.append({"app": name, "id": aid, "iap": n, "price": p})

        flag = "★免费内购" if frees else ("IAP" if iap else "无IAP")
        print(f"  [{i:>2}/{len(games)}] {name[:18]:<18} IAP={len(iap):>2} 免费={len(frees):>2}  {flag}")
        rows.append({"id": aid, "name": name, "iap_count": len(iap),
                     "free_count": len(frees), "iap": iap, "free": frees})
        time.sleep(delay)

    report = {
        "region": region,
        "scanned": len(games),
        "geo_blocked": blocked,
        "apps_with_iap": apps_with_iap,
        "apps_with_free_iap": apps_with_free,
        "total_iap_items": total_iap,
        "free_iap_hits": len(free_hits),
        "free_hits": free_hits,
        "rows": rows,
    }
    return report


def summarize(r):
    print("\n" + "=" * 60)
    print(f"P0 探针报告 · 区域={r['region'].upper()} · 扫描 {r['scanned']} 款热门免费游戏")
    print("=" * 60)
    if r["geo_blocked"]:
        print(f"  ⚠ 地理拦截跳过: {r['geo_blocked']} 款（US 须境外 runner）")
    print(f"  含 IAP 的 app : {r['apps_with_iap']}/{r['scanned']}")
    print(f"  含免费内购 app: {r['apps_with_free_iap']}/{r['scanned']}")
    print(f"  解析到的 IAP 条目总数: {r['total_iap_items']}")
    print(f"  命中的「免费内购」条目: {r['free_iap_hits']}")
    print("-" * 60)
    if r["free_hits"]:
        print("  免费内购清单：")
        for h in r["free_hits"]:
            print(f"    • {h['app']}  →  《{h['iap']}》 价格={h['price']}")
    else:
        print("  本轮未捕获任何免费内购条目。")
    print("-" * 60)
    # 验收线：每周可捕获 ≥3 条免费内购 ⇒ 玩法成立
    verdict = "✅ 成立：每周可捕获足量免费内购，建议立项" if r["free_iap_hits"] >= 3 else \
              ("⚠ 偏弱：免费内购样本偏少，需扩大监控池或结合人工/UGC" if r["free_iap_hits"] > 0 else
               "❌ 本轮 0 命中：纯自动化抓取暂不划算，建议走 UGC/人工策展")
    print("  验收结论:", verdict)
    print("=" * 60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", choices=["cn", "us"], default="cn")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--delay", type=float, default=0.4)
    ap.add_argument("--out", default=None, help="结果 JSON 输出路径")
    ap.add_argument("--ids-file", default=None,
                    help="自定义 app ID 池（JSON：list[str] 或 {id:...} 字典的键）。"
                         "指定后跳过 RSS，直接对给定 ID 做 IAP 扫描（用于长尾/全量探测）。")
    args = ap.parse_args()

    if args.ids_file:
        raw = json.load(open(args.ids_file, encoding="utf-8"))
        ids = list(raw.keys()) if isinstance(raw, dict) else list(raw)
        ids = [str(x) for x in ids][:args.limit]
        games = [(i, i) for i in ids]  # name 暂用 id
        r = run_custom(args.region, games, args.delay, args.limit)
    else:
        r = run(args.region, args.limit, args.delay)
    summarize(r)
    out = args.out or f"iap_probe_{args.region}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=2)
    print(f"[*] 结构化结果已写入 {out}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
探测 App Store App 是否含内购 —— 为「本体限免」卡片打「含内购 / 纯买断」徽章供数
==============================================================================
用法：
  python3 probe_iap_presence.py --region cn
  python3 probe_iap_presence.py --region us

为什么需要它
------------
iTunes Lookup 接口的 features 字段**不含**内购信息（连王者荣耀/微信都只返回
iosUniversal）；AMP API 需要鉴权。唯一可靠的免费信号是 App Store 商品页里的
JSON 字段 `"hasInAppPurchases"`（布尔）。

关键坑（2026-10-26 实测踩过）
-----------------------------
1. 商品页里 hasInAppPurchases **会出现几十次**——除本页 App 自身外，还包含
   「相关推荐 / 更多来自同一开发者」里**别的 App** 的数据。取「第一个匹配」会
   串味（实测把无内购 App 误判为有内购）。正确做法：先收集所有
   "(AdamId|adamId|trackId|appId)":"<id>" 的位置，再把每个 hasInAppPurchases
   归属给它**前面最近**的 id（距离 <900 字符），最后只取目标 id 自己的值。
2. **US 商品页在中国大陆 IP 会被 301 跳到 cn 落地页**（落地页里同样有
   hasInAppPurchases → 假阳性）。故 US 必须境外执行；本工作流跑在 GitHub
   Actions 的 ubuntu-latest（美国 IP）上，两区都满足。脚本会用最终 URL 校验
   /{region}/ 前缀，不符则记 geo_blocked 跳过。
3. 页面常被截断 → 需容错读取 http.client.IncompleteRead 的 partial 内容
   （App 自身属性在页面靠前部分，不受影响）。

数据流
------
候选集 = data/history-{region}.json 中「当前免费(末次价=0)且曾收费」的 App
        ∪ data/free-today-{region}.json 上一班的本体限免名单
  → 抓商品页取 hasInAppPurchases
  → 合并进 data/iap-presence-{region}.json（增量缓存：只探没探过的）
  → generate.py 读取该文件，给本体限免条目加 has_iap 字段 → 前端打徽章

首次全量约 330 个 App（cn 135 + us 199），增量后每班仅新增数十个。
"""
import sys, os, re, json, time, argparse, datetime, urllib.request, http.client
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Safari/605.1.15")
ID_RE = re.compile(r'"(?:AdamId|adamId|trackId|appId)"\s*:\s*"?(\d{6,12})"?')
IAP_RE = re.compile(r'"hasInAppPurchases"\s*:\s*(true|false)')
RECHECK_DAYS = 30          # 开发者可能后续新增内购 → 超过该天数复检一次
MAX_WORKERS = 4            # 并发线程数（对 Apple 保持克制）


def fetch(url, region, timeout=25):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "zh-CN,zh;q=0.9" if region == "cn" else "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        try:
            raw = r.read()
        except http.client.IncompleteRead as e:
            raw = e.partial
        return raw.decode("utf-8", "ignore"), r.geturl()


def owner_map(body):
    """把每个 hasInAppPurchases 归属到它前面最近的 id 字段。"""
    ids = [(m.start(), m.group(1)) for m in ID_RE.finditer(body)]
    out = {}
    for m in IAP_RE.finditer(body):
        p = m.start()
        prev = [(pos, i) for pos, i in ids if pos < p and p - pos < 900]
        if not prev:
            continue
        out.setdefault(prev[-1][1], m.group(1))
    return out


def probe_one(aid, region):
    url = f"https://apps.apple.com/{region}/app/id{aid}"
    rec = {"id": str(aid)}
    try:
        body, final = fetch(url, region)
    except Exception as e:
        rec["error"] = str(e)[:200]
        return rec
    if region == "us" and f"/{region}/" not in final:
        rec["geo_blocked"] = True          # 被跳到 cn 落地页 → 本机不能判美区
        return rec
    own = owner_map(body).get(str(aid))
    if own is None:
        return rec                         # 页面结构异常 → 不写缓存，下轮重试
    rec["has_iap"] = (own == "true")
    return rec


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def candidate_ids(region):
    """候选集：历史库里当前免费(曾收费)的 App ∪ 上一班本体限免名单。"""
    out = set()
    hist = load_json(os.path.join(DATA_DIR, f"history-{region}.json"), {}) or {}
    for cid, e in hist.items():
        h = e.get("h") or []
        if e.get("ec") and h and (h[-1].get("l") == 0):
            out.add(str(cid))
    ft = load_json(os.path.join(DATA_DIR, f"free-today-{region}.json"), {}) or {}
    for x in ft.get("freebies", []):
        if x.get("type") == "free" and x.get("id"):
            out.add(str(x["id"]))
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", choices=["cn", "us"], required=True)
    ap.add_argument("--workers", type=int, default=MAX_WORKERS)
    ap.add_argument("--delay", type=float, default=0.15)
    ap.add_argument("--limit", type=int, default=99999)
    a = ap.parse_args()

    cache_path = os.path.join(DATA_DIR, f"iap-presence-{a.region}.json")
    cache = load_json(cache_path, {}) or {}
    items = cache.get("items", {}) if isinstance(cache, dict) else {}

    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    stale_before = (datetime.datetime.now(datetime.timezone.utc)
                    - datetime.timedelta(days=RECHECK_DAYS)).strftime("%Y-%m-%d")

    cands = candidate_ids(a.region)[:a.limit]
    todo = []
    for aid in cands:
        rec = items.get(aid)
        if not rec or rec.get("checked", "") < stale_before:
            todo.append(aid)

    print(f"[{a.region}] 候选 {len(cands)} 个，需探测 {len(todo)} 个"
          f"（缓存已有 {len(cands) - len(todo)}）")

    ok = blk = err = 0
    if todo:
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=max(1, a.workers)) as ex:
            results = list(ex.map(lambda x: probe_one(x, a.region), todo))
        for rec in results:
            if rec.get("geo_blocked"):
                blk += 1
                print(f"  ⚠ id{rec['id']} 被地理跳转（需境外 IP）")
                continue
            if rec.get("error"):
                err += 1
                print(f"  ✗ id{rec['id']} {rec['error']}")
                continue
            if "has_iap" not in rec:
                continue
            items[rec["id"]] = {"has_iap": rec["has_iap"], "checked": today}
            ok += 1
        print(f"[{a.region}] 探测完成：成功 {ok} / 地理拦截 {blk} / 错误 {err}"
              f" / 用时 {time.time() - t0:.0f}s")

    out = {
        "updated": today,
        "region": a.region,
        "count": len(items),
        "items": items,
    }
    tmp = cache_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, cache_path)
    print(f"[written] {cache_path}（条目 {len(items)}）")


if __name__ == "__main__":
    main()

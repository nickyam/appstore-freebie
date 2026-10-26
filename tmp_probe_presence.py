#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时探针：判定 App Store App 是否有内购（hasInAppPurchases），cn/us 同一口径。

用法：
  python3 tmp_probe_presence.py --region cn --ids-file tmp_ids_cn.json --out tmp_result_cn.json
  python3 tmp_probe_presence.py --region us --ids-file tmp_ids_us.json --out tmp_result_us.json

关键点：
  1) 商品页里 hasInAppPurchases 会出现几十次（相关推荐位里的别的 App），
     必须按 AdamId/trackId 归属到「本页 App 自身」再取值，否则会串味。
  2) US 商品页在大陆 IP 会被 301 跳到 cn 落地页 → 记 geo_blocked，需境外 runner。
"""
import sys, re, json, time, argparse, urllib.request, http.client

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Safari/605.1.15")
ID_RE = re.compile(r'"(?:AdamId|adamId|trackId|appId)"\s*:\s*"?(\d{6,12})"?')
IAP_RE = re.compile(r'"hasInAppPurchases"\s*:\s*(true|false)')
# 兜底：页面文案里出现「App 内购买 / In-App Purchases」也算有内购
TXT_RE = re.compile(r'(App 内购买项目|含有 App 内购买项目|In-App Purchases|Offers In-App Purchases)')


def fetch(url, region, timeout=25):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "zh-CN,zh;q=0.9" if region == "cn" else "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        try:
            raw = r.read()
        except http.client.IncompleteRead as e:
            raw = e.partial          # 页面偶尔被截断，用已读部分（属性一般在开头）
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
    rec["final"] = final
    if region == "us" and f"/{region}/" not in final:
        rec["geo_blocked"] = True
        return rec
    om = owner_map(body)
    own = om.get(str(aid))
    if own is not None:
        rec["has_iap"] = (own == "true")
        rec["source"] = "hasInAppPurchases"
    else:
        # 兜底：自身条目没抓到，用页面文案判定（弱信号，仅当该页只有这一个 App 上下文时用）
        hit = bool(TXT_RE.search(body))
        rec["has_iap"] = hit
        rec["source"] = "text_fallback"
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", choices=["cn", "us"], required=True)
    ap.add_argument("--ids-file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--delay", type=float, default=0.2)
    ap.add_argument("--limit", type=int, default=99999)
    a = ap.parse_args()

    raw = json.load(open(a.ids_file, encoding="utf-8"))
    ids = [str(x) for x in (list(raw.keys()) if isinstance(raw, dict) else raw)][:a.limit]
    print(f"[*] {a.region}: 开始探测 {len(ids)} 个 App …")

    out, t0 = [], time.time()
    for i, aid in enumerate(ids, 1):
        rec = probe_one(aid, a.region)
        out.append(rec)
        if i % 10 == 0 or i == len(ids):
            has = sum(1 for r in out if r.get("has_iap") is True)
            blk = sum(1 for r in out if r.get("geo_blocked"))
            err = sum(1 for r in out if r.get("error"))
            print(f"  {i}/{len(ids)}  有内购={has}  拦截={blk}  错误={err}  用时={time.time()-t0:.0f}s", flush=True)
        time.sleep(a.delay)

    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    has = sum(1 for r in out if r.get("has_iap") is True)
    no = sum(1 for r in out if r.get("has_iap") is False)
    blk = sum(1 for r in out if r.get("geo_blocked"))
    err = sum(1 for r in out if r.get("error"))
    print(f"[done] region={a.region} 总={len(out)} 有内购={has} 无内购={no} 地理拦截={blk} 错误={err}")
    print(f"[written] {a.out}")


if __name__ == "__main__":
    main()

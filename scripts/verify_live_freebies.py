#!/usr/bin/env python3
"""
在线限免有效性轻量校验器（只读）
====================================
为什么需要它
------------
主跑批（daily.yml）每 6 小时一轮，GitHub Actions 排队再拖 1~3 小时，
而 Apple 的限免促销是「随时可能结束」的：全站每天约有 24 条限免到期
（cn ≈8 条 + us ≈16 条）。这意味着一条已恢复收费的 App，最长可能
在网站上多挂 9 小时 —— 用户点进去发现要钱，直接伤站点信任与 SEO。

本脚本解决的就是这个「暴露窗口」问题，且刻意做得极轻：
  · 只查「当前在架」的条目（cn 89 + us 140 条限免 + 34 条特价 ≈ 263 条），
    不扫全库（7000~10000 条），不跑榜单，不跑内购采集；
  · 实测两区全量 lookup 仅需 6.6 秒（iTunes lookup 100 id/批）。

🔴 只读铁律（与 AGENTS.md 一致）
--------------------------------
本脚本**绝不写任何文件**：不写 data/、不写 app/、不生成 HTML、不改 git。
它只做一件事——把「在架但已失效」的条目清单打印到 stdout（可选写 JSON
报告到 --report 指定的路径，那也只在校验者自己指定时发生）。
真正的下架动作**一律由 generate.py 执行**（全站唯一写页人），
本脚本只负责「发现并上报」，由调用方决定是否触发跑批。

判定规则（与 generate.py 的 derive()/判定逻辑逐条对齐，勿单方面改口径）
--------------------------------------------------------------------------
  · 限免（free-today-*.json 的 freebies）：当前价 != 0 → 已恢复收费 → 失效。
    注：generate.py 判定限免还需「曾收费(ever_charged)」且「连续为 0 天数 ≤ 7」，
    但这两条都是「历史属性」，不会因为本次价格查询而改变；一个条目既然在架，
    就说明上一轮它已通过全部判定。此处只需看「现在还是不是 0」。
  · 特价（deals）：generate.py 判定为降价需满足
        cur < 历史最高价(max_price) 且 (max_price-cur)/max_price >= 50%
    故失效条件为：当前价 >= 历史最高价（折扣结束），
    或折扣幅度已跌破 50% 门槛。
    历史最高价取自 data/history-{region}.json 的 mx 字段（与 generate.py 的
    max_price 同源；mx 缺失时用 h 序列里的最大值兜底，与 derive() 一致）。
  · IAP 限免（iap-free-*.json 的 events）：本体 App 仍在 App Store 即视为有效
    （IAP 价格由 iap_collector 负责采集，本脚本不重复判定内购价）。
  · 「查不到该 App」（lookup 未命中）：**不直接判定失效**。可能是下架、也可能是
    区域/接口临时异常。统一记为「疑似下架」单独上报，由跑批的 DELIST_MISS
    机制（连续 3 次查不到才删）处理。

接口异常保护（重要）
--------------------
若某一区的 lookup 整批 0 命中（网络故障 / 接口改版 / 被限流），绝不能把它
当成「全部条目失效」——那会触发一次无意义的全站跑批。此情形下该区直接判为
「跳过（接口异常）」，并在报告中标注，不计入失效清单。
只有「部分命中 + 部分确实变价」才认定有失效条目。

用法
----
  python3 scripts/verify_live_freebies.py                  # 人读格式，stdout
  python3 scripts/verify_live_freebies.py --region cn      # 只查中国区
  python3 scripts/verify_live_freebies.py --report /tmp/v.json   # 另存 JSON 报告
  python3 scripts/verify_live_freebies.py --quiet          # 只在有失效时输出
  python3 scripts/verify_live_freebies.py --data-dir /path/to/data   # 指定数据目录
                                                          # （ECS 上用它指向站点部署目录，
                                                          #   校验「用户此刻正在看的那份数据」）

退出码（供 workflow / cron 判定）
----------------------------------
  0 = 全部有效（或已跳过的区域），无失效条目
  1 = 发现失效条目（需下架）
  2 = 运行异常（数据文件缺失 / 无法解析等）

注意：US 区在大陆 IP 上查 lookup 接口本身是正常的（实测返回 currency=USD、
      trackViewUrl 为 /us/ 路径）。会 301 跳 cn 落地页的是**商品页**
      apps.apple.com/us/app/...，不是 lookup 接口。但为防接口行为变化或
      代理改写，本脚本仍对返回数据做「区域自检」：currency 与 trackViewUrl
      的区域前缀必须与所查地区一致，否则该区判为「跳过（疑似 geo 劫持）」
      而不是「失效」——绝不因地理问题误报下架。
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

# ===== 路径与常量 =====
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
# 默认数据目录 = 仓库 data/；可用 --data-dir 覆盖（ECS 上指向站点部署目录，
# 以校验「用户此刻正在看的那份数据」）。
DATA_DIR = os.path.join(REPO, "data")

LOOKUP_URL = "https://itunes.apple.com/lookup?country={region}&entity=software&id="
BATCH_SIZE = 100          # iTunes lookup 单批上限（与 iap_collector 一致）
BATCH_DELAY = 0.35        # 批间限速（秒）
UA = "Mozilla/5.0 (compatible; AppFreebieBot/1.0; +https://appstore.nickyam.com)"

DEAL_DROP_PCT = 0.50      # 特价判定门槛，与 generate.py 的 DEAL_DROP_PCT 一致


# ===== 工具 =====
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fmt_price(region, v):
    """与 generate.py 的 fmt_price 同口径，用于日志展示。"""
    if v <= 0:
        return "免费" if region == "cn" else "Free"
    return ("¥%.2f" % v) if region == "cn" else ("$%.2f" % v)


def parse_price(text):
    """把 free-today JSON 里的价格字符串（'¥68.00' / '$4.99'）解析成数字。
    解析失败返回 None（表示不可用于判定，而非 0）。"""
    if text is None:
        return None
    s = str(text).strip()
    if not s:
        return None
    if s in ("免费", "Free", "free"):
        return 0.0
    s = re.sub(r"[^\d.]", "", s)
    try:
        return float(s)
    except ValueError:
        return None


def lookup(region, ids, timeout=30):
    """批量查 iTunes lookup。返回 (结果字典, 整批命中数)。
    结果字典 key 为 app id（字符串）。"""
    out = {}
    hit = 0
    for i in range(0, len(ids), BATCH_SIZE):
        batch = ids[i:i + BATCH_SIZE]
        url = LOOKUP_URL.format(region=region) + ",".join(batch)
        req = urllib.request.Request(
            url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError) as e:
            print("[warn] %s 区 lookup 批次失败 (offset=%d): %s" % (region, i, e),
                  file=sys.stderr)
            continue
        results = data.get("results") or []
        hit += len(results)
        for r in results:
            tid = r.get("trackId")
            if tid is not None:
                out[str(tid)] = r
        if i + BATCH_SIZE < len(ids):
            time.sleep(BATCH_DELAY)
    return out, hit


def max_price_of(history, cid):
    """取该 App 的历史最高价，与 generate.py 的 derive() 同口径：
    优先 mx 字段；mx 为 0/缺失时用 h 序列中 f/l 的最大值兜底。"""
    e = history.get(cid)
    if not e:
        return None
    mx = e.get("mx") or 0
    if mx:
        return float(mx)
    h = e.get("h") or []
    vals = []
    for x in h:
        vals.append(x.get("f", 0) or 0)
        vals.append(x.get("l", 0) or 0)
    return float(max(vals)) if vals else None


# ===== 校验主体 =====
def verify_region(region):
    """校验一个地区。返回该区的结果字典。"""
    res = {
        "region": region,
        "skipped": False,
        "skip_reason": "",
        "checked": 0,
        "freebies": 0,
        "deals": 0,
        "iap_events": 0,
        "stale": [],      # 已失效（在架但价格已变）→ 需下架
        "missing": [],    # 疑似下架（lookup 未命中）→ 交由跑批 DELIST_MISS 处理
    }

    ft_path = os.path.join(DATA_DIR, "free-today-%s.json" % region)
    if not os.path.exists(ft_path):
        res["skipped"] = True
        res["skip_reason"] = "缺少 %s" % os.path.basename(ft_path)
        return res
    try:
        ft = load_json(ft_path)
    except Exception as e:
        res["skipped"] = True
        res["skip_reason"] = "解析 %s 失败: %s" % (os.path.basename(ft_path), e)
        return res

    freebies = ft.get("freebies") or []
    deals = ft.get("deals") or []
    res["freebies"] = len(freebies)
    res["deals"] = len(deals)

    hist_path = os.path.join(DATA_DIR, "history-%s.json" % region)
    history = {}
    if os.path.exists(hist_path):
        try:
            history = load_json(hist_path)
        except Exception:
            history = {}

    # 收集要查的 id（限免 + 特价）
    items = []
    for x in freebies:
        items.append(("free", x))
    for x in deals:
        items.append(("deal", x))
    ids = [str(x.get("id")) for _, x in items if x.get("id")]
    # 去重但保持顺序
    seen, ordered = set(), []
    for i in ids:
        if i not in seen:
            seen.add(i)
            ordered.append(i)
    res["checked"] = len(ordered)

    if not ordered:
        res["skip_reason"] = "该区无在架条目"
        res["skipped"] = True
        return res

    details, hit = lookup(region, ordered)

    # ---- 接口异常保护：整批 0 命中 → 该区跳过，不算失效 ----
    if hit == 0:
        res["skipped"] = True
        res["skip_reason"] = ("lookup 整批 0 命中（%d 条全部未返回），"
                              "判为接口异常而非全部失效，本区跳过" % len(ordered))
        return res

    # ---- 区域自检：数据必须确实属于所查地区，否则整区跳过 ----
    geo_ok, geo_msg = check_geo_consistency(region, details)
    if not geo_ok:
        res["skipped"] = True
        res["skip_reason"] = "%s（%s），本区跳过，不计入失效" % (geo_msg, region)
        return res
    res["geo_check"] = geo_msg

    for kind, x in items:
        cid = str(x.get("id"))
        r = details.get(cid)
        name = x.get("name") or ""
        if r is None:
            res["missing"].append({
                "id": cid, "name": name, "kind": kind,
                "shown": x.get("current") or "",
            })
            continue
        price = r.get("price", 0) or 0
        if kind == "free":
            # 限免失效：当前价 != 0
            if price != 0:
                res["stale"].append({
                    "id": cid, "name": name, "kind": "free",
                    "shown": x.get("current") or "免费",
                    "now": fmt_price(region, price),
                    "now_raw": price,
                    "why": "已恢复收费（原为限免）",
                })
        else:
            # 特价失效：折扣结束，或幅度跌破 50% 门槛
            mp = max_price_of(history, cid)
            if mp is None or mp <= 0:
                # 无历史最高价 → 无法判定，跳过（不误报）
                continue
            if price >= mp:
                res["stale"].append({
                    "id": cid, "name": name, "kind": "deal",
                    "shown": x.get("current") or "",
                    "now": fmt_price(region, price),
                    "now_raw": price,
                    "why": "折扣结束（现价已回到原价 %s）" % fmt_price(region, mp),
                })
            elif (mp - price) / mp < DEAL_DROP_PCT:
                res["stale"].append({
                    "id": cid, "name": name, "kind": "deal",
                    "shown": x.get("current") or "",
                    "now": fmt_price(region, price),
                    "now_raw": price,
                    "why": "折扣幅度跌破 50%%（原价 %s → 现价 %s）"
                           % (fmt_price(region, mp), fmt_price(region, price)),
                })

    # ---- IAP 限免：本体 App 是否仍在 App Store ----
    iap_path = os.path.join(DATA_DIR, "iap-free-%s.json" % region)
    if os.path.exists(iap_path):
        try:
            iap = load_json(iap_path)
            events = iap.get("events") or []
            res["iap_events"] = len(events)
            if events:
                iap_ids = [str(e.get("app_id")) for e in events if e.get("app_id")]
                iap_seen, iap_ordered = set(), []
                for i in iap_ids:
                    if i not in iap_seen:
                        iap_seen.add(i)
                        iap_ordered.append(i)
                iap_details, iap_hit = lookup(region, iap_ordered)
                if iap_hit == 0 and iap_ordered:
                    print("[warn] %s 区 IAP lookup 整批 0 命中，跳过 IAP 校验" % region,
                          file=sys.stderr)
                else:
                    for e in events:
                        aid = str(e.get("app_id"))
                        if aid not in iap_details:
                            res["missing"].append({
                                "id": aid, "name": e.get("app_name") or "",
                                "kind": "iap", "shown": e.get("price") or "",
                            })
        except Exception as ex:
            print("[warn] %s 区 IAP 校验失败: %s" % (region, ex), file=sys.stderr)

    return res


def check_geo_consistency(region, details):
    """区域自检：确认 lookup 返回的数据确实属于所查地区。
    判据（任一不满足即视为疑似 geo 劫持/接口改道）：
      1) currency 与地区匹配：cn → CNY，us → USD；
      2) trackViewUrl 的区域段与地区匹配：/cn/ 或 /us/。
    返回 (是否可信, 说明文字)。
    """
    want_cur = {"cn": "CNY", "us": "USD"}.get(region)
    want_seg = "/%s/" % region
    checked = 0
    bad_cur = 0
    bad_seg = 0
    for r in details.values():
        if want_cur:
            cur = r.get("currency")
            if cur:
                checked += 1
                if cur != want_cur:
                    bad_cur += 1
        url = r.get("trackViewUrl") or ""
        if url:
            checked += 1
            if want_seg not in url:
                bad_seg += 1
    if checked == 0:
        return False, "返回数据无 currency/trackViewUrl，无法自检"
    if bad_cur or bad_seg:
        return False, ("疑似 geo 劫持：%d 条 currency 不符 / %d 条 trackViewUrl 区域段不符"
                       % (bad_cur, bad_seg))
    return True, "区域自检通过（%d 项）" % checked


def render_text(results):
    """人读格式的报告。"""
    lines = []
    total_stale = 0
    total_missing = 0
    lines.append("=" * 62)
    lines.append("限免有效性轻量校验报告")
    lines.append("=" * 62)
    for r in results:
        tag = "【跳过】" if r["skipped"] else ""
        lines.append("")
        lines.append("── %s 区 %s" % (r["region"].upper(), tag))
        if r["skipped"]:
            lines.append("    原因: %s" % r["skip_reason"])
            continue
        lines.append("    在架: 限免 %d 条 / 特价 %d 条 / IAP 限免 %d 条"
                     % (r["freebies"], r["deals"], r["iap_events"]))
        lines.append("    实际查询: %d 个唯一 id" % r["checked"])
        if r["stale"]:
            lines.append("    ⚠ 失效条目 %d 条（需下架）:" % len(r["stale"]))
            for s in r["stale"]:
                lines.append("       [%s] %s  %s" % (s["kind"], s["id"], s["name"]))
                lines.append("           站上显示 %s → 现价 %s（%s）"
                             % (s["shown"], s["now"], s["why"]))
        else:
            lines.append("    ✓ 无失效条目")
        if r["missing"]:
            lines.append("    ? 疑似下架 %d 条（lookup 未命中，交由跑批处理）:"
                         % len(r["missing"]))
            for m in r["missing"][:20]:
                lines.append("       [%s] %s  %s" % (m["kind"], m["id"], m["name"]))
            if len(r["missing"]) > 20:
                lines.append("       ...（其余 %d 条省略）"
                             % (len(r["missing"]) - 20))
        total_stale += len(r["stale"])
        total_missing += len(r["missing"])
    lines.append("")
    lines.append("─" * 62)
    lines.append("合计: 失效 %d 条 / 疑似下架 %d 条" % (total_stale, total_missing))
    lines.append("（本脚本只读不改数据；下架由 generate.py 在跑批时执行）")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(
        description="校验在架限免/特价条目的当前有效性（只读，不改任何数据）")
    ap.add_argument("--region", choices=["cn", "us"], help="只校验指定地区（默认两区都查）")
    ap.add_argument("--report", help="把 JSON 报告写到该路径（可选）")
    ap.add_argument("--data-dir", default=None,
                    help="数据目录（默认仓库 data/）。ECS 上指向站点部署目录的 data/，"
                         "以校验「用户此刻正在看的那份数据」")
    ap.add_argument("--quiet", action="store_true",
                    help="只在发现失效条目时输出正文")
    args = ap.parse_args()

    global DATA_DIR
    if args.data_dir:
        DATA_DIR = os.path.abspath(args.data_dir)
        if not os.path.isdir(DATA_DIR):
            print("[error] 数据目录不存在: %s" % DATA_DIR, file=sys.stderr)
            return 2

    regions = [args.region] if args.region else ["cn", "us"]
    results = []
    for region in regions:
        try:
            results.append(verify_region(region))
        except Exception as e:
            results.append({
                "region": region, "skipped": True,
                "skip_reason": "校验过程异常: %s" % e,
                "checked": 0, "freebies": 0, "deals": 0, "iap_events": 0,
                "stale": [], "missing": [],
            })

    total_stale = sum(len(r["stale"]) for r in results)
    total_missing = sum(len(r["missing"]) for r in results)

    if args.report:
        try:
            with open(args.report, "w", encoding="utf-8") as f:
                json.dump({
                    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "total_stale": total_stale,
                    "total_missing": total_missing,
                    "regions": results,
                }, f, ensure_ascii=False, indent=2)
            print("[info] JSON 报告已写入 %s" % args.report)
        except OSError as e:
            print("[warn] 写报告失败: %s" % e, file=sys.stderr)

    if args.quiet and total_stale == 0:
        print("[ok] 未发现失效条目（校验 %d 个地区）" % len(results))
    else:
        print(render_text(results))

    return 1 if total_stale > 0 else 0


if __name__ == "__main__":
    sys.exit(main())

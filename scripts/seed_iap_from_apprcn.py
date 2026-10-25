#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从「反斗限免」(apprcn) 拉取「内购限免」清单，bootstrap 进 IAP 监控库（P2 配套种子器）
===================================================================================

设计原则（2026-10-22 用户拍板）
------------------------------
**只保留「限时内购免费」（有 became_free 促销证据 + 当前确实免费）。**
任何「一直免费 / 永久免费」的内购都不符合要求，一律不注入、不展示。

反斗限免 API（monitor-appstore.apprcn.com/api/v1/snapshot）自带两个金矿字段：
  - iap[]        : 当前正在搞「内购限免」的 App（全局 76 个，每条含 regions[].items[]
                  内购名 / 现价 / free 标志）。这是「哪个 App 的哪个内购现在免费」的权威源。
  - iap_alerts[] : 历史上「iap_became_free」告警（含 created_at + old_price→0 跳变证据），
                  能明确区分「促销限免（曾付费）」与「永久免费（噪声）」。

注意：iap[] 与 iap_alerts[] 都是**全局列表**（与请求时的 region 参数无关），需按子字段
      region 自行过滤。

本脚本做什么（D 架构，2026-10-23 起）
------------------------------------
1. 拉取 cn / us 两份 snapshot（带重试；可用 --cache-dir 复用本地缓存避免重复请求）。
2. 从 iap[] 抽取各 region「当前 free=True」的内购项，从 iap_alerts[] 抽取 became_free
   告警 → 促销限免证据（含原价锚点）。
3. bootstrap 进 data/iap-history-{region}.json（**只注入限时项**，manifest 管理自有键）：
   - 仅当某 (app_id, 内购名) 同时命中「当前 free」与「became_free 证据」才注入；
     ever_paid=True、free_since=告警日、原价（有则显示，无则标「—」）。
   - 未命中 became_free 的「当前免费」内购 → 视为永久免费噪声，**一律跳过不注入**。
   - 无评分（rating<=0）的 App 一律不收录（与本体限免规则一致，需先 iTunes lookup）。
   - 首次迁移：清除历史中所有 ever_paid=False 的键（彻底移除一切「一直免费」噪声）。
4. 把 became_free 涉及的 app_id 注入 data/history-{region}.json 监控池（幂等），
   让 iap_collector 后续持续跟踪促销结束、捕获「恢复原价」。

不再做的事（已移交，单一写入方原则）
----------------------------------
- iap-free / iap-current-free JSON 与事件判定 → iap_collector 独写（每日 06:30）；
- IAP 独立页生成 / 过期清理 / sitemap → generate.py 独写（每 6h 班次，全站唯一写页人）。
代价：新发现的内购限免约延迟一天进入首页与独立页（次日采集器出事件、generate 出页）；
收益：反斗限免 API 故障不再影响页面生产，两个脚本不再抢写同一批 JSON。

安全
----
- 不覆盖 P1 iap_collector 真实爬取的数据（仅清理 ever_paid=False 噪声 + 管理自有键）。
- 全程不爬 Apple 商品页（apprcn 已给足双区数据；iTunes lookup 无地域限制）。

用法
----
  python3 seed_iap_from_apprcn.py                 # 双区播种（cn+us）
  python3 seed_iap_from_apprcn.py --regions cn    # 仅 cn
  python3 seed_iap_from_apprcn.py --cache-dir /tmp # 复用 /tmp/apprcn_{region}.json
  python3 seed_iap_from_apprcn.py --dry-run        # 只打印，不写文件
"""
import sys
import os
import json
import time
import datetime
import argparse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATA_DIR = os.path.join(REPO, "data")
sys.path.insert(0, HERE)

from iap_collector import save_json  # noqa: E402
from seed_from_apprcn import seed_entry, utc_today  # noqa: E402

SNAPSHOT_URL = "https://monitor-appstore.apprcn.com/api/v1/snapshot?region={region}&type=free"
ITUNES_LOOKUP = "https://itunes.apple.com/lookup?id={ids}&country={region}&limit=200"
UA = "Mozilla/5.0 (compatible; AppFreebieBot/1.0; +https://appstore.nickyam.com)"
MANIFEST_PATH = os.path.join(DATA_DIR, ".seed_iap_apprcn_manifest.json")


def http_get_json(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def esc_html(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;") \
                      .replace(">", "&gt;").replace('"', "&quot;")


def fetch_snapshot(region, cache_dir=None):
    cache = os.path.join(cache_dir, f"apprcn_{region}.json") if cache_dir else None
    if cache and os.path.exists(cache):
        try:
            return json.load(open(cache, encoding="utf-8"))
        except Exception:
            pass
    last_err = None
    for attempt in range(5):
        try:
            data = http_get_json(SNAPSHOT_URL.format(region=region))
            if data.get("ok"):
                return data
        except Exception as e:
            last_err = e
        time.sleep(3 + attempt * 2)
    raise RuntimeError("snapshot(%s) 拉取失败: %s" % (region, last_err))


def ts_to_date(ts):
    try:
        return datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return utc_today().isoformat()


def collect_current_free(data, region):
    """从 iap[] 抽取本 region 当前 free=True 的内购项。返回 list of dict。"""
    out = []
    for app in (data.get("iap") or []):
        aid = str(app.get("app_id"))
        app_name = app.get("name") or ""
        for r in (app.get("regions") or []):
            if r.get("region") != region:
                continue
            for it in (r.get("items") or []):
                if not it.get("free"):
                    continue
                out.append({
                    "app_id": aid,
                    "app_name": app_name,
                    "iap_name": it.get("name") or "",
                    "price_text": it.get("price_text") or "免费",
                    "base_price": app.get("base_price"),
                })
    return out


def collect_became_free(data, region):
    """从 iap_alerts[] 抽取本 region 的 became_free 告警。返回 {app_id: {name_lower: {...}}}。"""
    m = {}
    for a in (data.get("iap_alerts") or []):
        if a.get("kind") != "iap_became_free":
            continue
        if a.get("region") != region:
            continue
        aid = str(a.get("app_id"))
        name = (a.get("item_name") or "").strip().lower()
        rec = {
            "date": ts_to_date(a.get("created_at")),
            "old_price_text": a.get("old_price_text"),
        }
        m.setdefault(aid, {})[name] = rec
    return m


def collect_active_iap_ids(data, region):
    """iap[] 中本 region 当前有内购促销的 app_id 集合（双驱动候选集，B 方案）。

    2026-10-25 用户拍板：反斗 cn 区 48 条 became_free 告警中 47 条 App 不在
    榜单池——内购限免主力是榜外小工具/相机类 App，光靠 became_free 注入不够，
    把当前所有内购活跃 App 一并注入监控池，采集器持续跟踪其 IAP 价格变化
    （价格仍由我们自己爬、事件仍由我们自己的规则判定，只是候选集对路）。
    """
    ids = set()
    for app in (data.get("iap") or []):
        regions = [r.get("region") for r in (app.get("regions") or [])]
        if region not in regions:
            continue
        aid = str(app.get("app_id") or "")
        if aid:
            ids.add(aid)
    return ids


def pick_alert(became, aid, iap_name):
    """为某 (app_id, iap) 选一个 became_free 证据。优先精确名匹配；否则若 App 仅一条告警则复用。"""
    app_map = became.get(aid)
    if not app_map:
        return None
    exact = app_map.get(iap_name.strip().lower())
    if exact:
        return exact
    if len(app_map) == 1:
        return next(iter(app_map.values()))
    return None


def load_manifest():
    if os.path.exists(MANIFEST_PATH):
        try:
            return json.load(open(MANIFEST_PATH, encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_manifest(m):
    os.makedirs(DATA_DIR, exist_ok=True)
    json.dump(m, open(MANIFEST_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def _utc_now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_seed_meta(region, **fields):
    """往 data/iap-history-{region}.json 的 meta 写播种健康字段（A 方案：防静默失败）。

    心跳落在 iap-history meta：该文件由采集器每班刷新但只动 updated/pool_size 等
    字段，seed_* 字段会被保留；文件每日被 CI 提交，陈旧状态在 git 历史里也可见。
    """
    p = os.path.join(DATA_DIR, f"iap-history-{region}.json")
    hist = {"meta": {"region": region, "version": 1}, "items": {}}
    if os.path.exists(p):
        try:
            hist = json.load(open(p, encoding="utf-8"))
        except Exception:
            pass
    hist.setdefault("meta", {})["region"] = region
    hist["meta"].update(fields)
    try:
        save_json(f"iap-history-{region}.json", hist)
    except Exception as e:
        print(f"[warn] 写 seed 健康字段失败: {e}")


def mark_seed_ok(region):
    _write_seed_meta(region, seed_last_ok=_utc_now_iso(), seed_last_error="")


def mark_seed_fail(region, err):
    _write_seed_meta(region, seed_last_fail=_utc_now_iso(),
                     seed_last_error=str(err)[:200])


def bootstrap_iap_history(region, current_free, became, today, manifest, appmeta=None):
    """只注入「当前免费 + became_free 证据」的限时内购；清理永久免费噪声与旧 apprcn 键。

    无评分（rating<=0）的 App 一律不收录——与本体限免「无评分不收录」规则一致
    （2026-10-23 用户拍板）。appmeta 由 iTunes lookup 提供，缺省时不过滤（兼容旧调用）。

    返回 (hist, added, manifest)。
    """
    appmeta = appmeta or {}
    hist_path = os.path.join(DATA_DIR, f"iap-history-{region}.json")
    hist = {"meta": {"region": region, "version": 1}, "items": {}}
    if os.path.exists(hist_path):
        try:
            hist = json.load(open(hist_path, encoding="utf-8"))
        except Exception:
            pass
    hist.setdefault("items", {})
    items = hist["items"]

    # 1) 清理上次本脚本管理的键
    old_keys = manifest.get(region, [])
    for k in old_keys:
        items.pop(k, None)

    # 2) 首次迁移：清除所有「一直免费」噪声（ever_paid=False），符合「只保留限时」原则
    if not old_keys:
        for k in list(items):
            if items[k].get("ever_paid") is False:
                items.pop(k, None)

    # 3) 注入当前限时项（仅 became_free 命中 + 有评分）
    new_keys = []
    added = 0
    skipped_unrated = 0
    for cf in current_free:
        aid = cf["app_id"]
        iap_name = cf["iap_name"]
        key = f"{aid}::{iap_name}"
        alert = pick_alert(became, aid, iap_name)
        if not alert:
            continue  # 无促销证据 → 视为永久免费，跳过
        if (appmeta.get(aid, {}).get("rating") or 0) <= 0:
            skipped_unrated += 1   # 无评分不收录（与本体限免规则一致）
            continue
        old = alert["old_price_text"]
        first_price = old if old else "—"  # 无原价锚点：用 — 表示原价未知
        rec = {
            "app_id": aid,
            "app_name": cf["app_name"],
            "name": iap_name,
            "region": region,
            "first_date": today,
            "first_price": first_price,
            "last_date": today,
            "last_price": cf["price_text"],
            "last_change_date": today,
            "ever_paid": True,
            "last_paid_date": alert["date"],
            "free_since": alert["date"],
            "changes": {alert["date"]: first_price, today: cf["price_text"]},
            "source": "apprcn",
        }
        items[key] = rec  # 覆盖（含上版无 source 的同名限时键）
        new_keys.append(key)
        added += 1

    hist["meta"].update({"updated": today, "seeded_from": "apprcn",
                         "seed_added": added, "seed_total": len(items)})
    manifest[region] = new_keys
    return hist, added, manifest, skipped_unrated


def seed_pool(region, became, today, extra_ids=None):
    """把 became_free + 内购活跃(iap[]) 的 app_id 注入 history-{region}.json 监控池（幂等）。

    extra_ids：collect_active_iap_ids 产出的内购活跃 App 集合（B 方案，2026-10-25）。
    返回 (hist, hist_path, added_became, added_active)。
    """
    hist_path = os.path.join(DATA_DIR, f"history-{region}.json")
    hist = {}
    if os.path.exists(hist_path):
        try:
            hist = json.load(open(hist_path, encoding="utf-8"))
        except Exception:
            hist = {}
    added_became = 0
    for aid in became:  # became 的 keys 即 app_id（字符串）
        if aid in hist:
            continue
        hist[aid] = seed_entry(0.0, today, today - datetime.timedelta(days=1))
        hist[aid]["ec"] = False   # 主应用价格未知：不谎称"曾收费"（防误入本体限免；
        added_became += 1          # 观测到付费价后 update_history 会自动自愈为 True）
    added_active = 0
    for aid in sorted(extra_ids or []):
        aid = str(aid)
        if aid and aid not in hist:
            hist[aid] = seed_entry(0.0, today, today - datetime.timedelta(days=1))
            hist[aid]["ec"] = False  # 同上：IAP 注入 ≠ 本体曾收费
            added_active += 1

    # 可达性保证：采集器 load_pool 按字典序取前 limit(2000)，池尾注入可能永远
    # 轮不到复查。每次把「热点集」（became_free + 内购活跃）重排到池前部。
    hot = [str(a) for a in became if str(a) in hist]
    for aid in sorted(extra_ids or []):
        aid = str(aid)
        if aid in hist and aid not in hot:
            hot.append(aid)
    if hot:
        # ec 自愈（2026-10-26 补）：旧代码注入的假 ec=True（主应用价格未知却声称
        # "曾收费"）会把"主应用从未收费"的 App 误列进本体限免（显示 免费→免费）。
        # 判据：无任何价格证据（mx=0 且 anchor=0）→ ec 重置 False；有真实价格
        # 历史的条目不动（update_history 观测到付费价也会自动置 True）。
        healed = 0
        for aid in hot:
            e = hist.get(aid) or {}
            if e.get("ec") and not (e.get("mx") or 0) and not (e.get("anchor") or 0):
                e["ec"] = False
                healed += 1
        if healed:
            print(f"[history-{region}] ec 自愈：{healed} 个无价格证据的注入条目重置 ec=False")
        reordered = {aid: hist[aid] for aid in hot}
        for k, v in hist.items():
            if k not in reordered:
                reordered[k] = v
        hist = reordered
    return hist, hist_path, added_became, added_active


def lookup_apps(region, app_ids):
    """iTunes lookup 批量补 App 元数据（图标/开发者/分类/评分/官方链接）。

    iTunes API 无地域跳转（与 apps.apple.com 商品页不同），本地双区均可直查。
    返回 {app_id: {name, dev, genre, rating, icon, url}}。
    """
    meta = {}
    ids = sorted(app_ids)
    for i in range(0, len(ids), 100):
        batch = ids[i:i + 100]
        url = ITUNES_LOOKUP.format(ids=",".join(batch), region=region)
        try:
            data = http_get_json(url, timeout=30)
        except Exception as e:
            print(f"[warn] iTunes lookup({region}, {len(batch)} ids) 失败: {e}")
            continue
        for r in (data.get("results") or []):
            aid = str(r.get("trackId") or "")
            if not aid:
                continue
            g = r.get("genres")
            genre = g[0] if isinstance(g, list) and g else (r.get("primaryGenreName", "") or "")
            meta[aid] = {
                "name": r.get("trackName") or "",
                "dev": r.get("artistName") or "",
                "genre": genre,
                "rating": r.get("averageUserRating") or 0,
                "icon": r.get("artworkUrl512") or r.get("artworkUrl100") or "",
                "url": r.get("trackViewUrl") or "",
            }
        time.sleep(1)
    return meta


def main():
    ap = argparse.ArgumentParser(
        description="从反斗限免播种「限时」内购 IAP history（D 架构：只播种，不写页）")
    ap.add_argument("--regions", default="cn,us", help="逗号分隔，默认 cn,us")
    ap.add_argument("--cache-dir", default="", help="复用本地 snapshot 缓存目录")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不写文件")
    args = ap.parse_args()
    regions = [r.strip() for r in args.regions.split(",") if r.strip()]

    today = utc_today()
    today_str = today.isoformat()
    manifest = load_manifest()
    failures = []

    for region in regions:
        print(f"\n=== region={region} ===")
        try:
            data = fetch_snapshot(region, args.cache_dir or None)
        except Exception as e:
            # A 方案：拉取失败必须留痕（seed_last_fail），否则 continue-on-error 会静默吞掉
            print(f"[error] snapshot({region}) 拉取失败: {e}")
            mark_seed_fail(region, e)
            failures.append(region)
            continue
        current_free = collect_current_free(data, region)
        became = collect_became_free(data, region)
        active_ids = collect_active_iap_ids(data, region)  # B 方案：内购活跃候选集
        n_became = sum(len(v) for v in became.values())
        print(f"[info] 当前免费内购项: {len(current_free)} | became_free 告警: {n_became} "
              f"| 内购活跃 App: {len(active_ids)}")

        # 先 lookup 拿评分（无评分 App 不收录，需在注入前知道评分）
        appmeta = lookup_apps(region,
                              {cf["app_id"] for cf in current_free} | set(became.keys()))

        hist, added, manifest, skipped_unrated = bootstrap_iap_history(
            region, current_free, became, today_str, manifest, appmeta)
        if not args.dry_run:
            save_json(f"iap-history-{region}.json", hist)
            mark_seed_ok(region)  # A 方案：成功心跳（dry-run 不写）
        print(f"[iap-history-{region}] 新增限时 {added}（无评分跳过 {skipped_unrated}），"
              f"现有 {len(hist['items'])} 条（仅限时）")

        # 注入监控池（became_free + 内购活跃 App，幂等）
        pooled, hist_path, padd_became, padd_active = seed_pool(
            region, became, today, extra_ids=active_ids)
        if not args.dry_run:
            os.makedirs(DATA_DIR, exist_ok=True)
            json.dump(pooled, open(hist_path, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
        print(f"[history-{region}] 监控池新增 App: became_free {padd_became} + "
              f"内购活跃 {padd_active}（池总量 {len(pooled)}）")

    if failures:
        # 工作流该步骤带 continue-on-error，此处 exit 1 仅作标记；
        # 真正的报警由后续 check_seed_health.py 步骤完成（防静默失败）。
        print(f"\n[error] 以下 region 播种失败: {failures}")
        sys.exit(1)

    if not args.dry_run:
        save_manifest(manifest)
        print(f"\n[manifest] 已更新 {MANIFEST_PATH}")
        print("[info] 事件判定与独立页由 iap_collector（每日 06:30）/ generate（每 6h）接管，"
              "新发现的限免约次日进首页与独立页")
    else:
        print("\n[dry-run] 未写任何文件")


if __name__ == "__main__":
    main()

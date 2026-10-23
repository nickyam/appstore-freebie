#!/usr/bin/env python3
"""
App Store 限免清单生成器（支持 cn 中国区 / us 美国区）
====================================================
核心思路
--------
- 苹果 iTunes RSS 榜单 + Lookup 接口均为官方、免密钥接口。
- 限免（价格=0）的 App 永远不会出现在「付费榜」，而刚变免费的 App 也未必挤进
  「免费榜 TopN」，所以单纯扫描当天榜单在数学上几乎抓不到限免。
- 本生成器采用「**宽监控池 + 永久 App 库（以 id 为键）**」策略：

  1. 宽监控池：22 个一级分类的「付费榜 Top100」+「畅销榜 Top100」+ 整体「免费榜 Top200」，
     覆盖数千个"容易做限免"的 App；
  2. 永久 App 库（history）：任何被拉取过的 App 都建档（每日价格快照 + 标量基线），
     · 标量基线（ever_charged / 历史最高价 / 原价锚点）**永久保存**，不再因超期丢失，
       解决「见过一次的原常规价」随 30 天窗口消失的问题；
     · 每日新增的榜单 App-id 自动入库；下架 App（连续 3 次 lookup 查不到）自动删除；
  3. 每轮回查集合 union：始终含榜单 App（抓新鲜限免）；
     常规 6 小时班次仅额外含「促销中可能掉榜」的库内 App（现价=0 或仍处折扣）以提速；
     「每日一班」全量模式(--full) 把库内全部 App 一并回查，捕获长尾/掉榜 App 的缓慢价格变化；
  4. 判定：
     · 限免：当前价=0 且 曾>0（基线判定），且连续为 0 的天数≤7（排除长期免费）；
       同时天然覆盖「日内闪免」（今日首价>0、末价=0）与「跨天」（昨日>0、今日=0）；
     · 降价：当前价 < 历史最高价 且 降幅≥50%；
  5. 促销粘性：已在促销（限免/降价）中的 App 持续回查，价格回升到原价及以上自动下架；
  6. 排除永久免费：全程为 0、从未收费的 App 不收录。

- 首次运行：若库为空但有旧 baseline，则以 baseline 当日价播种一天；否则仅初始化，
  基线随每日回查逐月填满。
- 所有数据来自 Apple 官方，图标直接引用苹果 CDN，不转存。
- 调度：GitHub Actions 每 6 小时跑常规班次（榜单 + 促销中 App，快）；
  每日一班 --full 全量回查（抓长尾/掉榜 App）；Cloudflare 自动部署、阿里云镜像每 6 小时同步。
- 页面生产总入口：本体限免/特价独立页与「内购限免」独立页（type=iap，数据源
  data/iap-free-{country}.json，由 iap_collector 独写）均由本脚本生成、清理、
  打戳、收 sitemap——全站唯一写页人（2026-10-23 D 架构；反斗限免种子器退化为
  纯 history 播种，第三方 API 脱离页面生产关键路径）。
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
APP_PAGE_MAX_AGE_DAYS = 365   # 独立页超过该天数且不在当期清单 → 删除（限制 app/ 与 sitemap 无限膨胀）
HISTORY_MAX_ENTRIES = 50000   # 永久库软上限，超出时淘汰最早建档且非当期限免/特价的条目
LONG_FREE_DAYS = 7       # 连续为 0 超过该天数 → 不再算限时免费
DEAL_DROP_PCT = 0.50    # 降价判定：降幅 ≥ 50%（相对历史最高价）
HISTORY_CAP = 120       # 每 App 保留的每日价格快照上限（用于曲线），标量基线永久保存
DELIST_MISS = 3         # 连续 N 次 lookup 查不到（下架）→ 从库删除
REL_POOL_SIZE = 18      # 详情页「同时期的其他限免」烘焙池大小；前端每次访问随机抽 6 个展示
UA = "Mozilla/5.0 (compatible; AppFreebieBot/1.0; +https://appstore.nickyam.com)"

# iOS App 全部一级分类 genre id
GENRE_IDS = [
    6000, 6001, 6002, 6003, 6004, 6005, 6006, 6007, 6008, 6009,
    6010, 6011, 6012, 6013, 6014, 6015, 6016, 6017, 6018, 6019,
    6020, 6021,
]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
APP_DIR = os.path.join(BASE_DIR, "app")                      # App 详情独立页目录
PAGE_TEMPLATE = os.path.join(BASE_DIR, "app-page.html")     # 独立页模板


def esc_html(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;") \
                      .replace(">", "&gt;").replace('"', "&quot;")


def write_app_pages(items, country, today):
    """为当期限免/特价 App 生成独立详情页（SEO + 可分享 URL）。

    同时给每个 item 写入 page 字段（供首页卡片点击直接跳转）。
    """
    if not os.path.exists(PAGE_TEMPLATE):
        print("[warn] app-page.html 模板缺失，跳过独立页生成")
        return 0
    with open(PAGE_TEMPLATE, encoding="utf-8") as f:
        tpl = f.read()
    os.makedirs(APP_DIR, exist_ok=True)
    count = 0
    for item in items:
        page_rel = "app/%s-%s.html" % (country, item["id"])  # 相对路径；配合各页 <base href="/">，详情页也能正确解析
        item["page"] = page_rel
        is_free = item.get("type") == "free"
        name = item.get("name", "")
        if is_free:
            title = "%s 正在限时免费 · 苹果限免雷达" % name
            desc = "%s（%s）原价 %s，现在限时免费。附中美两区价格对比、近 30 天价格走势、官方截图与介绍。" % (
                name, item.get("dev", ""), item.get("normal", ""))
        else:
            title = "%s 正在降价（%s → %s）· 苹果限免雷达" % (
                name, item.get("normal", ""), item.get("current", ""))
            desc = "%s（%s）现价 %s（原价 %s）。附中美两区价格对比、近 30 天价格走势、官方截图与介绍。" % (
                name, item.get("dev", ""), item.get("current", ""), item.get("normal", ""))
        ld = {
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            "name": name,
            "operatingSystem": "iOS",
            "applicationCategory": item.get("genre", ""),
            "offers": {
                "@type": "Offer",
                "price": "0" if is_free else "",
                "priceCurrency": "CNY" if country == "cn" else "USD",
            },
            "url": item.get("url", ""),
        }
        html = tpl
        html = html.replace("__TITLE__", esc_html(title))
        html = html.replace("__DESC__", esc_html(desc))
        html = html.replace("__OG_TITLE__", esc_html(title))
        html = html.replace("__OG_DESC__", esc_html(desc))
        html = html.replace("__APP_NAME__", esc_html(name))
        html = html.replace("__PAGE_DATE__", today)
        html = html.replace("__APP_LD__", json.dumps(ld, ensure_ascii=False, indent=2))
        app_json = json.dumps(item, ensure_ascii=False).replace("</", "<\\/")
        html = html.replace("window.__APP__ = null;", "window.__APP__ = " + app_json + ";")
        page_url = "https://appstore.limzero.com/" + page_rel
        html = html.replace("__CANON__", esc_html(page_url))
        html = html.replace("__OG_URL__", esc_html(page_url))
        og_img = item.get("icon", "")
        if og_img:
            og_img = re.sub(r'/(\d+)x(\d+)bb(\.\w+)$', r'/512x512bb\3', og_img)
        html = html.replace("__OG_IMAGE__", esc_html(og_img))
        with open(os.path.join(BASE_DIR, page_rel), "w", encoding="utf-8") as f:
            f.write(html)
        count += 1
    return count


def load_iap_events(country):
    """读取「限时内购免费」事件：data/iap-free-{country}.json（iap_collector 独写）。

    返回 events list；文件缺失/损坏/结构异常返回 None——与「空清单」严格区分：
    None = 无数据源，此时既不写页也不清理，避免误删已有 IAP 页。
    """
    p = os.path.join(DATA_DIR, f"iap-free-{country}.json")
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return None
    evs = d.get("events")
    return evs if isinstance(evs, list) else None


def write_iap_pages(country, today):
    """为「限时内购免费」App 生成独立详情页（type=iap），返回 (写入数, 保留页集合)。

    数据源：data/iap-free-{country}.json。事件已由 iap_collector 经 iTunes lookup
    富化（评分/图标/开发者/分类，无评分事件在采集端已剔除），同一 App 多个内购
    限免 → 一个页面聚合展示（iap_items）。

    架构（2026-10-23 D 方案，用户拍板）：generate 是全站唯一写页人——本体页、
    IAP 页、过期清理、资源戳、sitemap 全部在此收口；反斗限免种子器退化为纯
    history 播种，第三方 API 脱离页面生产关键路径。保留页集合交给
    cleanup_iap_pages 清理促销结束的过期页；无数据源时返回 (0, None)，
    调用方据此跳过清理（安全默认：不清源不明的页）。
    """
    if not os.path.exists(PAGE_TEMPLATE):
        print("[warn] app-page.html 模板缺失，跳过 IAP 独立页生成")
        return 0, None
    events = load_iap_events(country)
    if events is None:
        return 0, None
    with open(PAGE_TEMPLATE, encoding="utf-8") as f:
        tpl = f.read()
    os.makedirs(APP_DIR, exist_ok=True)

    by_app, order = {}, []
    for e in events:
        aid = str(e.get("app_id") or "")
        if not aid:
            continue
        if aid not in by_app:
            order.append(aid)
        by_app.setdefault(aid, []).append(e)

    free_label = "免费" if country == "cn" else "Free"
    keep = set()
    count = 0
    for aid in order:
        evs = by_app[aid]
        name = evs[0].get("app_name") or f"App {aid}"
        iap_names = [x.get("iap") or "" for x in evs]
        iap_disp = "、".join(iap_names[:3]) + ("…" if len(iap_names) > 3 else "")
        if len(evs) == 1:
            title = "%s 内购「%s」限时免费 · 苹果限免雷达" % (name, iap_names[0])
        else:
            title = "%s 内购限时免费（%d 项）· 苹果限免雷达" % (name, len(evs))
        orig = next((x.get("last_paid_price") for x in evs
                     if x.get("last_paid_price") and x["last_paid_price"] != "—"), "")
        fs = min((x.get("free_since") or today) for x in evs)
        days = max((x.get("days_free") or 0) for x in evs)
        if orig:
            desc = "%s 的内购项目「%s」原价 %s，现在限时免费（自 %s 起）。附 App 介绍、截图与中美两区价格对比。" % (
                name, iap_disp, orig, fs)
        else:
            desc = "%s 的内购项目「%s」现在限时免费（自 %s 起）。附 App 介绍、截图与中美两区价格对比。" % (
                name, iap_disp, fs)
        page_rel = "app/%s-%s.html" % (country, aid)
        item = {
            "id": aid, "name": name,
            "dev": evs[0].get("dev", ""), "genre": evs[0].get("genre", ""),
            "normal": orig, "current": free_label,
            "icon": evs[0].get("icon", ""), "rating": evs[0].get("rating", 0),
            "url": evs[0].get("url", ""), "region": country,
            "type": "iap",
            "iap": "、".join(iap_names),
            "iap_items": [{"name": x.get("iap", ""),
                           "last_paid_price": x.get("last_paid_price", ""),
                           "free_since": x.get("free_since", ""),
                           "days_free": x.get("days_free", 0)} for x in evs],
            "free_since": fs, "days_free": days,
            "is_new": days == 0,
            "series": [], "phistory": [],
        }
        ld = {
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            "name": name,
            "operatingSystem": "iOS",
            "applicationCategory": item["genre"],
            "offers": {"@type": "Offer", "price": "0",
                       "priceCurrency": "CNY" if country == "cn" else "USD"},
            "url": item["url"],
        }
        html = tpl
        html = html.replace("__TITLE__", esc_html(title))
        html = html.replace("__DESC__", esc_html(desc))
        html = html.replace("__OG_TITLE__", esc_html(title))
        html = html.replace("__OG_DESC__", esc_html(desc))
        html = html.replace("__APP_NAME__", esc_html(name))
        html = html.replace("__PAGE_DATE__", today)
        html = html.replace("__APP_LD__", json.dumps(ld, ensure_ascii=False, indent=2))
        app_json = json.dumps(item, ensure_ascii=False).replace("</", "<\\/")
        html = html.replace("window.__APP__ = null;", "window.__APP__ = " + app_json + ";")
        page_url = "https://appstore.limzero.com/" + page_rel
        html = html.replace("__CANON__", esc_html(page_url))
        html = html.replace("__OG_URL__", esc_html(page_url))
        og_img = item.get("icon", "")
        if og_img:
            og_img = re.sub(r'/(\d+)x(\d+)bb(\.\w+)$', r'/512x512bb\3', og_img)
        html = html.replace("__OG_IMAGE__", esc_html(og_img))
        with open(os.path.join(BASE_DIR, page_rel), "w", encoding="utf-8") as f:
            f.write(html)
        keep.add(page_rel)
        count += 1
    return count, keep


def cleanup_iap_pages(country, keep_pages):
    """删除本区已不在 iap-free 事件清单内的 IAP 独立页（促销结束/无评分剔除）。

    只删「type=iap」页（正则识别 __APP__ 内联数据），本体限免页绝不碰。
    keep_pages=None → 无数据源，跳过清理（不删源不明的页）。
    须在 write_sitemap 之前调用，确保被删页不残留进 sitemap。
    """
    if keep_pages is None or not os.path.isdir(APP_DIR):
        return 0
    removed = 0
    prefix = country + "-"
    for fn in sorted(os.listdir(APP_DIR)):
        if not (fn.startswith(prefix) and fn.endswith(".html")):
            continue
        rel = "app/" + fn
        if rel in keep_pages:
            continue
        try:
            txt = open(os.path.join(APP_DIR, fn), encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        if not re.search(r'"type"\s*:\s*"iap"', txt):
            continue                      # 本体限免页，不碰
        try:
            os.remove(os.path.join(APP_DIR, fn))
            removed += 1
            print("[info] 删除过期 IAP 页: %s" % rel)
        except OSError:
            pass
    return removed


def write_sitemap():
    """重写 sitemap.xml：主页面 + 全部「有评分」的 App 独立页。

    收录规则（与收录闸门一致）：只有页面本身含评分（rating>0）的 App 才进 sitemap。
    无评分 App 的独立页由 prune_unrated_pages 在 sitemap 之前删除，故此处磁盘上仅剩有评分页，
    sitemap 直接收录全部 app/*.html 即可——即便该 App 已从限免清单掉出（如价格恢复），
    只要它有评分，独立页仍保留并被搜索引擎收录。
    """
    base = "https://appstore.limzero.com"
    paths = ["", "about.html", "privacy.html", "terms.html"]
    if os.path.isdir(APP_DIR):
        for fn in sorted(os.listdir(APP_DIR)):
            if fn.endswith(".html"):
                paths.append("app/" + fn)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for p in paths:
        lines.append("  <url>")
        lines.append("    <loc>%s/%s</loc>" % (base, p))
        lines.append("    <changefreq>daily</changefreq>")
        lines.append("  </url>")
    lines.append("</urlset>")
    with open(os.path.join(BASE_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return len(paths)


def _asset_version():
    """资源版本号：取 assets/js/app.js 与 assets/css/style.css 的内容哈希（短）。
    资源内容不变则版本号不变，避免每日生成都用 git-sha 导致所有 HTML 被改写、git 历史膨胀。"""
    import hashlib
    digests = []
    for rel in ("assets/js/app.js", "assets/css/style.css"):
        p = os.path.join(BASE_DIR, rel)
        try:
            with open(p, "rb") as f:
                digests.append(hashlib.sha256(f.read()).hexdigest())
        except Exception:
            digests.append("0")
    if digests and all(d == "0" for d in digests):
        # 资源读不到时退化到 git-sha / 日期，保证一定有戳
        import subprocess
        try:
            fallback = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], cwd=BASE_DIR,
                stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            fallback = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
        return fallback or "static"
    return hashlib.sha256("".join(digests).encode("utf-8")).hexdigest()[:10]


SECURITY_HEAD = """  <!-- HTTPS 优先：http 输入一律跳 https（服务器 80 端口受阿里云合规拦截，nginx 的 301 可能发不出去，这里用 JS 兜底） -->
  <script>
    if (location.protocol === 'http:') {
      location.replace('https://' + location.host + location.pathname + location.search + location.hash);
    }
  </script>
  <!-- HSTS：告诉浏览器一年只允许用 https 访问本站，从源头杜绝明文 http -->
  <meta http-equiv="Strict-Transport-Security" content="max-age=31536000; includeSubDomains" />
"""


def sync_includes():
    """把「http→https 兜底 + HSTS」安全头脚本作为单一信源注入所有页面（用 START/END 标记包裹，幂等可重复运行）。
    消除 index/about/404/privacy/terms/app-page 六处完全相同的重复块，改一处即全局生效。"""
    start, end = "<!--SHARED_SECURITY_START-->", "<!--SHARED_SECURITY_END-->"
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    repl = start + "\n" + SECURITY_HEAD + "\n  " + end
    count = 0
    for root, dirs, files in os.walk(BASE_DIR):
        if "/.git" in root:
            continue
        for fn in files:
            if not fn.endswith(".html"):
                continue
            p = os.path.join(root, fn)
            try:
                s = open(p, encoding="utf-8").read()
            except Exception:
                continue
            ns = pat.sub(repl, s)
            if ns != s:
                open(p, "w", encoding="utf-8").write(ns)
                count += 1
    print("[info] shared security block synced: %d files" % count)


def sync_base_tag():
    """确保所有 HTML（含 app/ 下的历史详情页）都带 <base href="/">。

    详情页位于 /app/ 目录下，若缺 <base>，页内相对资源/链接会相对 /app/ 解析：
      · 相对页链接 app/cn-xxx.html → /app/app/cn-xxx.html → 404；
      · 相对数据路径 data/xxx.json → /app/data/xxx.json → 拉不到数据。
    当期清单内的 App 由 write_app_pages 用新模板重写（自带 base），
    但已不在清单里的历史页不会重写，故需全量扫尾补齐（幂等，只补不改）。
    已存在非根 base 的页面一律保留（子路径部署时由人工统一改写）。"""
    base_tag = '<base href="/" />'
    pat_has = re.compile(r"<base\s[^>]*>", re.I)
    pat_head = re.compile(r"(<head[^>]*>)", re.I)
    count = 0
    for root, dirs, files in os.walk(BASE_DIR):
        if "/.git" in root:
            continue
        for fn in files:
            if not fn.endswith(".html"):
                continue
            p = os.path.join(root, fn)
            try:
                s = open(p, encoding="utf-8").read()
            except Exception:
                continue
            if pat_has.search(s):
                continue          # 已有 base（无论根还是子路径）→ 不动
            m = pat_head.search(s)
            if not m:
                continue          # 非标准 HTML（无 head）→ 跳过
            ns = s[:m.end()] + "\n  " + base_tag + s[m.end():]
            try:
                open(p, "w", encoding="utf-8").write(ns)
                count += 1
            except Exception:
                continue
    print("[info] base tag synced: %d files" % count)


def stamp_asset_version():
    """用资源内容哈希自动生成静态资源版本号，统一替换所有 HTML 的 ?v=。

    取代手工维护 ?v=：资源内容不变则版本号不变，缓存（Cloudflare/Aliyun 的
    immutable 长缓存）随之稳定；资源一旦改动，版本号自动变化使旧缓存失效，
    避免「改了 JS 却发旧版」，也不会因 git-sha 每日变化而制造大量 git churn。"""
    ver = _asset_version()
    pat = re.compile(r"(\?v=)[A-Za-z0-9._-]+")
    count = 0
    for root, dirs, files in os.walk(BASE_DIR):
        if "/.git" in root:
            continue
        for fn in files:
            if not fn.endswith(".html"):
                continue
            p = os.path.join(root, fn)
            try:
                s = open(p, encoding="utf-8").read()
            except Exception:
                continue
            ns = pat.sub(r"\g<1>" + ver, s)
            if ns != s:
                open(p, "w", encoding="utf-8").write(ns)
                count += 1
    print("[info] asset version stamped: %s (%d files)" % (ver, count))


def prune_app_pages(max_age_days):
    """清理 App 独立页，限制 app/ 目录与 sitemap 无限膨胀。

    删除规则（须在 write_sitemap 之前调用，确保被删页不残留进 sitemap）：
      · 无用户评分（rating==0）的页；
      · 有评分但页面生成日期早于 max_age_days 天（该 App 长期未再进入限免/特价，
        对 SEO 与抓取预算价值递减）。
    当期清单里的 App 每次运行都会被重写（data-page-date 为当天），因此不会被误删。
    """
    if not os.path.isdir(APP_DIR):
        return 0
    removed = 0
    cutoff = (datetime.date.today() - datetime.timedelta(days=max_age_days)).isoformat()
    for fn in os.listdir(APP_DIR):
        if not fn.endswith(".html"):
            continue
        path = os.path.join(APP_DIR, fn)
        try:
            txt = open(path, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        m = re.search(r'"rating"\s*:\s*([0-9.]+)', txt)
        rated = bool(m and float(m.group(1)) > 0)
        # IAP 内购限免页豁免「无评分/过期」清理：由本文件 write_iap_pages +
        # cleanup_iap_pages 按 iap-free 事件清单专门管理（D 架构，2026-10-23）
        if re.search(r'"type"\s*:\s*"iap"', txt):
            continue
        pd = re.search(r'data-page-date="([0-9-]+)"', txt)
        page_date = pd.group(1) if pd else ""
        if (not rated) or (page_date and page_date < cutoff):
            try:
                os.remove(path)
                removed += 1
                print("[info] prune page: %s" % fn)
            except OSError:
                pass
    return removed


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
    """加载永久 App 库；兼容旧版「列表」格式（cid -> [{d,f,l}]）并按需迁移。"""
    raw = load_json(path)
    if not raw:
        return {}
    out = {}
    for cid, v in raw.items():
        if isinstance(v, list):
            # 旧格式：价格快照列表 → 转换为带标量基线的库条目
            h = v
            vals = [p for e in h for p in (e.get("f", 0) or 0, e.get("l", 0) or 0)]
            out[cid] = {
                "h": h[-HISTORY_CAP:],
                "ec": any(p > 0 for p in vals),
                "mx": max(vals) if vals else 0,
                "anchor": max(vals) if vals else 0,
                "first": h[0].get("d", "") if h else "",
                "last": h[-1].get("d", "") if h else "",
                "miss": 0,
            }
        else:
            out[cid] = v
    return out


def utc_today():
    """以 UTC 为准取「今天」。
    数据日期(date)与 generated_at(UTC) 保持同一时区，避免
    「日期 10-19 / 更新于 10-20」的观感矛盾；GitHub Actions runner 本就是 UTC，
    历史日期键也与既有数据连续。显式用 UTC 而非 date.today()，保证本地调试
    （UTC+8 机器）与线上行为一致。"""
    return datetime.datetime.now(datetime.timezone.utc).date()


def seed_from_baseline(history, baseline):
    """首次无库时，用旧 baseline 的当日价播种一天，给跨天判定一个起点。"""
    today = utc_today().isoformat()
    for cid, rec in (baseline or {}).items():
        p = rec.get("price", 0) or 0
        history[cid] = {
            "h": [{"d": today, "f": p, "l": p}],
            "ec": p > 0,
            "mx": p,
            "anchor": p if p > 0 else 0,
            "first": today,
            "last": today,
            "miss": 0,
        }
    return history


def new_entry():
    return {"h": [], "ec": False, "mx": 0, "anchor": 0, "first": "", "last": "", "miss": 0}


def update_history(history, cid, today, price, found):
    """更新库条目：found=是否本次 lookup 命中（命中刷新价格/基线，未命中 miss+1）。"""
    e = history.get(cid) or new_entry()
    if not e.get("first"):
        e["first"] = today
    if found:
        e["miss"] = 0
        e["last"] = today
        h = e["h"]
        if h and h[-1].get("d") == today:
            h[-1]["l"] = price          # 今日多次轮询：末价更新，首价保留
        else:
            h = h + [{"d": today, "f": price, "l": price}]
            e["h"] = h[-HISTORY_CAP:]
        if price > 0:
            e["ec"] = True
            if price > e["mx"]:
                e["mx"] = price
            if price > e["anchor"]:
                e["anchor"] = price     # 原价锚点 = 历史最高收费价
    else:
        e["miss"] += 1                  # 查不到 → 疑似下架，累计 miss
    history[cid] = e


def derive(entry):
    """从库条目推导判定所需字段：曾收费 / 历史最高价 / 连续为 0 天数 / 上价 / 现价。"""
    e = entry or new_entry()
    h = e.get("h") or []
    ever_charged = e.get("ec")
    if ever_charged is None:
        vals = [p for x in h for p in (x.get("f", 0) or 0, x.get("l", 0) or 0)]
        ever_charged = any(p > 0 for p in vals)
    max_price = e.get("mx") or 0
    if not max_price and h:
        max_price = max(p for x in h for p in (x.get("f", 0) or 0, x.get("l", 0) or 0))
    # 连续为 0 的天数（从最新一天往前数，当天需首末均为 0 才算零天）
    cz = 0
    for x in reversed(h):
        if (x.get("f", 0) or 0) == 0 and (x.get("l", 0) or 0) == 0:
            cz += 1
        else:
            break
    if len(h) >= 2:
        prev = h[-2].get("l", 0) or 0
    elif h:
        prev = h[-1].get("f", 0) or 0
    else:
        prev = 0
    cur = h[-1].get("l", 0) if h else 0
    return ever_charged, max_price, cz, prev, cur


def main():
    parser = argparse.ArgumentParser(description="App Store 限免清单生成器")
    parser.add_argument("--country", required=True, choices=["cn", "us"], help="地区：cn 中国区 / us 美国区")
    parser.add_argument("--full", action="store_true",
                        help="全量模式：把永久库中所有 App 一并回查（默认仅扫榜单 + 促销中 App，更快）")
    args = parser.parse_args()
    country = args.country
    full = args.full
    free_label = "免费" if country == "cn" else "Free"

    history_path = os.path.join(DATA_DIR, f"history-{country}.json")
    out_path = os.path.join(DATA_DIR, f"free-today-{country}.json")
    watch_path = os.path.join(DATA_DIR, f"watch-{country}.json")

    today = utc_today().isoformat()

    # 1) 构建宽监控池：22 分类 付费榜 + 畅销榜 + 整体免费榜
    chart_ids = []
    for g in GENRE_IDS:
        chart_ids += fetch_chart(country, "toppaidapplications", GENRE_LIMIT, genre=g)
        chart_ids += fetch_chart(country, "topgrossingapplications", GROSS_LIMIT, genre=g)
    chart_ids += fetch_chart(country, "topfreeapplications", FREE_LIMIT)

    # 2) 加载永久 App 库；若为空用旧 baseline 播种一天
    history = load_history(history_path)
    if not history:
        baseline = load_json(os.path.join(DATA_DIR, f"baseline-{country}.json"))
        if baseline:
            history = seed_from_baseline(history, baseline)
            print(f"[info] seeded library from baseline: {len(history)} apps")

    # 3) 一次性把旧「补充追踪池」watch 并入永久库（保留原价锚点 + 首见日），
    #    并入后删除 watch 文件，统一为单一 App 库。
    watch = load_json(watch_path)
    if watch:
        for cid, w in watch.items():
            e = history.get(cid) or new_entry()
            anc = w.get("anchor") or 0
            if anc > 0:
                e["ec"] = True
                e["mx"] = max(e["mx"], anc)
                e["anchor"] = max(e["anchor"], anc)
            if not e.get("first"):
                e["first"] = w.get("first", today)
            e["last"] = w.get("last", today)
            e["miss"] = 0
            history[cid] = e
        try:
            os.remove(watch_path)
        except OSError:
            pass
        print(f"[info] folded watch into library: {len(watch)} apps")

    # 4) 构建本轮回查集合 union：
    #    · 始终含榜单 App（捕捉新鲜限免）；
    #    · 非全量模式：仅额外含「促销中可能掉榜」的库内 App（现价=0 或 现价为历史折扣），
    #      避免每 6 小时全库回查；全量模式(--full，每日一班)则含库内全部 App。
    union = list(chart_ids)
    seen = set(union)
    if full:
        for cid in history.keys():
            if cid not in seen:
                seen.add(cid); union.append(cid)
    else:
        for cid, e in history.items():
            if cid in seen:
                continue
            h = e.get("h") or []
            if not h:
                continue
            cur = h[-1].get("l", 0) or 0
            anchor = e.get("anchor") or 0
            if cur == 0 or (anchor > 0 and cur > 0 and cur < anchor * (1 - DEAL_DROP_PCT)):
                seen.add(cid); union.append(cid)   # 仍在促销/降价 → 续查

    details = lookup(country, union)

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

        # 写入/更新今日价格快照 + 标量基线（命中 lookup）
        update_history(history, cid, today, cur, found=True)
        ever_charged, max_price, cz, prev, cur = derive(history[cid])

        is_free = False
        is_deal = False
        if cur == 0:
            # 限免：曾收费 + 非长期免费
            if ever_charged and cz <= LONG_FREE_DAYS:
                is_free = True
        else:
            # 降价：相对历史最高价降幅 ≥ 50%
            if ever_charged and max_price > 0 and cur < max_price \
                    and (max_price - cur) / max_price >= DEAL_DROP_PCT:
                is_deal = True

        if is_free or is_deal:
            # 规则：无用户评分（评论）的应用不收录到限免/特价清单
            if not rating:
                continue
            if is_free:
                newly = (cur == 0 and prev > 0)            # 本轮/本日新触发（限免）
            else:
                newly = (prev > 0 and cur > 0 and cur < prev)  # 较昨日继续/新降价（特价）
            # 原价锚点：优先用库内记录的原价（永久保鲜），否则回落到历史最高价 / prev / 当前
            anchor = (history[cid] or {}).get("anchor") or 0
            if anchor <= 0:
                anchor = max_price if max_price > 0 else (prev if prev > 0 else cur)
            # 每日末价序列（旧→新），供前端画价格曲线 / 算历史最低
            hlist = history[cid].get("h") or []
            series = [x.get("l", 0) or 0 for x in hlist]
            # 带日期的价格历史（旧→新），供详情页大曲线
            phistory = [{"d": x.get("d", ""), "p": x.get("l", 0) or 0} for x in hlist]
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
                "is_new": newly,
                "series": series,
                "phistory": phistory,
            }
            (freebies if is_free else deals).append(item)

    # 回查集合里命中失败的 App：累计 miss（疑似下架）
    for cid in union:
        if cid not in details:
            update_history(history, cid, today, 0, found=False)

    # 清理：连续 miss 达阈值 → 判定下架，从库删除
    delisted = 0
    for cid in [c for c, e in history.items() if (e.get("miss") or 0) >= DELIST_MISS]:
        del history[cid]; delisted += 1
    if delisted:
        print(f"[info] delisted (miss≥{DELIST_MISS}): {delisted} apps")

    # 库规模上限保护：超出时淘汰「最早建档且当前不在限免/特价」的条目，避免无限膨胀
    if len(history) > HISTORY_MAX_ENTRIES:
        keep_ids = {str(x["id"]) for x in (freebies + deals)}
        cand = [cid for cid in history if cid not in keep_ids]
        cand.sort(key=lambda c: history[c].get("first") or "")
        over = len(history) - HISTORY_MAX_ENTRIES
        for cid in cand[:over]:
            del history[cid]
        print(f"[info] history capped: removed {min(over, len(cand))} idle entries")

    # 排序：新触发的限免/降价优先，其次评分高、名称
    def sort_key(x):
        return (-(1 if x.get("is_new") else 0), -(x.get("rating") or 0), x.get("name") or "")
    freebies.sort(key=sort_key)
    deals.sort(key=sort_key)

    # 为每个 item 附带「同时期的其他限免/特价」轻量推荐（id/name/icon/genre/type/page/rating/region），
    # 供详情页直出，避免详情页为推荐再拉取整份 free-today JSON。
    # 池子放宽到 REL_POOL_SIZE（前端每次访问随机抽 6 个展示）——若只烘焙 6 个，
    # 洗牌后仍是同一批 App，每个详情页显示的推荐完全一样（用户反馈"固定不合理"）。
    pool_sorted = sorted(freebies + deals, key=sort_key)
    for it in (freebies + deals):
        others = [x for x in pool_sorted if x["id"] != it["id"]][:REL_POOL_SIZE]
        it["rel"] = [
            {"id": x["id"], "name": x.get("name", ""), "icon": x.get("icon", ""),
             "genre": x.get("genre", ""), "type": x.get("type", ""),
             # 此处 x["page"] 尚未被 write_app_pages 赋值（那段在本块之后才跑），
             # 故此处按与生成器一致的公式直接给出相对站根的详情页路径，
             # 否则推荐卡片的 page 会是空串 → 渲染成不可点击的 div。
             "page": x.get("page") or ("app/%s-%s.html" % (country, x["id"])),
             "rating": x.get("rating", 0),
             "region": x.get("region", country)} for x in others
        ]

    result = {
        "date": today,
        "country": country,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "freebies": freebies,
        "deals": deals,
    }

    # App 详情独立页（写入 page 字段供首页卡片直接跳转；须在 save_json 前执行）
    page_items = result["freebies"] + result["deals"]
    pages_written = write_app_pages(page_items, country, today)

    # IAP 内购限免独立页（D 架构：generate 唯一写页人；数据源 = iap_collector 独写的
    # data/iap-free-{country}.json；无数据源时返回 (0, None)，下方据此跳过清理）
    iap_written, iap_keep = write_iap_pages(country, today)

    save_json(out_path, result)
    save_json(history_path, history)

    # 先清理独立页（本体：无评分/过期；IAP：促销结束），再写 sitemap；
    # sitemap 只收录磁盘上仍保留的页
    pruned = prune_app_pages(APP_PAGE_MAX_AGE_DAYS)
    iap_pruned = cleanup_iap_pages(country, iap_keep)
    sm_urls = write_sitemap()

    print(f"[ok] country={country} full={full} date={today} monitored={len(union)} "
          f"library={len(history)} freebies={len(freebies)} deals={len(deals)} "
          f"(全量输出，无展示上限)")
    print(f"[ok] app pages written={pages_written} iap pages={iap_written} "
          f"sitemap_urls={sm_urls} pruned={pruned} iap_pruned={iap_pruned}")
    sync_includes()
    sync_base_tag()
    stamp_asset_version()


if __name__ == "__main__":
    main()

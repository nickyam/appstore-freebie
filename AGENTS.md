# AGENTS.md — 苹果限免雷达（appstore-freebie）

> 最后复核：2026-10-27。本文件是**索引与红线清单**，权威细节以各脚本头部 docstring 为准；当铁律 7 的播种班 limit、监控池规模或判定阈值变更时，必须同步回顾本文件。

纯静态站点：抓苹果中国区/美国区官方价格，识别「限时免费」App 与降价特价。
架构 = Cloudflare Pages（静态托管）+ GitHub Actions（每日比价）+ 阿里云 ECS（准点触发 CI）。
改任何代码前，先读相关脚本的头部 docstring——项目大量设计决策和踩坑记录写在那里。

## 不可违反的铁律（违反 = 线上事故）

1. **generate.py 是全站唯一写页人（D 架构，2026-10-23）**
   - app/*.html 独立页、sitemap.xml、资源戳 ?v=、安全头注入（sync_includes）、IAP 页清理，全部收口在 `scripts/generate.py`。
   - 其它脚本（seed_*、iap_collector、probe_iap_presence）**不得**写 HTML、改 sitemap、改根级静态页。
   - 反斗限免种子器已退化为纯 history 播种，第三方 API 脱离页面生产关键路径。

2. **data JSON 的 schema 是三方契约，改前必须同步**
   以下文件的结构被 generate.py 和前端 assets/js/app.js 读取，改动前必须三方同步：
   - `history-{region}.json`：永久 App 库，条目含 h(每日快照)/ec(曾收费)/mx/anchor/first/last/miss。
   - `iap-history-{region}.json`：复合键 `app_id::iap_name`；changes 仅记变价日；meta 里写播种心跳 seed_last_ok/seed_last_fail（check_seed_health 依赖）。
   - `iap-free-{region}.json`：events 数组；**page 字段由 generate.py 回写**，采集器不要自己写 page（时序会导致首页卡片回退 App Store 外链）。
   - `iap-current-free-{region}.json`：items 数组。
   - `iap-presence-{region}.json`：items = {app_id: {has_iap, checked}}。
   - `free-today-{region}.json`：date/country/generated_at/freebies/deals；每条含 rel/series/phistory/has_iap/page。

3. **时间一律以北京时间（UTC+8）翻日**
   generate.py 用 `bj_today()`、iap_collector 用 `UTC+8` 计算"今天"；不能用 runner 的 UTC（否则用户在北京时间下午才看到"今天"更新）。历史日期键切到北京日后用绝对重算，不损坏数据。

4. **判定规则不可改坏**
   - 限免：当前价=0 且 曾收费(ec) 且 连续免费天数 ≤ 7（LONG_FREE_DAYS）。
   - 降价：当前价 < 历史最高价 且 降幅 ≥ 50%（DEAL_DROP_PCT）。
   - 永久免费（全程 0）不收录；**无评分（rating≤0）一律不收录**（本体与内购统一规则）。
   - 内购限免：仅「付费→0」跳变算事件；ever_paid=False 的永久免费内购归入"常驻免费"，不进事件 feed。**试用 / 试玩 / 体验版 / 体验卡 / 体验券 / trial / free trial 类内购一律不算内购限免**（只是免费试用，不是真·促销限免；Apple 常把试用期标成 免费/Free，故在 `iap_probe.is_trial_iap` 按名字剔除，且 `FREE_TOKENS` 不含 free trial/免费试用）。
   - **订阅的「免费试用 intro offer」同样不算限免**（2026-10-28 修，勿回退）：Apple 会把订阅的每个档位连同试用期价格一起列在 IAP 列表里，表现为**同一内购名出现多个价格、其中一条是 ¥0.00/$0.00**（实测：Currency Pro ¥148+¥0、Offline Pages Pro ¥38/¥22/¥15/¥0、永久会员 ¥98/¥158/¥0、Bonus Workout Pack 1~4）。真·限免在页面上只会剩**单独一条** ¥0.00（如 PDF Scanner Pro ¥8→¥0、Unlock All Rhymes ¥38→¥0）。故：① `iap_probe.parse_iap` 同名归并时丢弃 0 价、保留最贵在售价；② `iap_collector.detect_events` 对 ever_paid 条目做**付费轨迹校验**——`changes` 中查不到任何付费价的一律不认（订阅试用会让同批次两次写入同一复合键、付费价被 0 覆盖，导致 changes 全 0 而 first_price 残留付费价，这是误报的指纹）。

5. **CI 铁律：PATHS 必须覆盖所有被改写文件**
   daily.yml / daily-full.yml 的 `git add $PATHS` 必须包含 generate.py 与采集器会写到的全部文件（6 个根级 html、app/、sitemap.xml、全部 data/ 产物、.seed_iap_apprcn_manifest.json）。
   漏加任何一项 → "已改未暂存" → git pull --rebase 拒绝 → **整班红**。IAP 采集的 4 个 iap-*.json 由 daily.yml 负责 add，不要拆分到别的 workflow。

6. **资源版本号机制**
   HTML 里的 `?v=` 由 generate.py 的 stamp_asset_version() 按 assets/js/app.js 与 assets/css/style.css 的内容哈希自动生成。
   不要手工改 HTML 里的 ?v=。改了 JS/CSS 后要重跑 generate（或手动刷新资源戳），否则缓存不失效、线上发旧版。

7. **分级调度的 limit 是安全阀，必须随池增长回顾（2026-10-27）**
   - 主池按"最近变价日"降序；播种班(UTC 22/23) limit=4500、其余班 2000。
   - 该值的安全前提是"**有 IAP 的 app 数 < 4500**"。一旦监控池扩大使有 IAP 的 app 数接近/超过 4500，播种班会开始裁掉"变价日期较旧但有 IAP"的 app；极端情况下一个"从未被扫过、无记录但有 IAP 且恰好限免"的 app 会被挤出漏检。
   - 新候选经 `seed_iap_from_apprcn.py` 的 bootstrap 打 `today` 日期、排最前，已大幅缓解盲区；但 limit 不是越大越好（更大 = 更长单班时长、更易与下一班串行抢推 main）。
   - **约定：监控池规模变更时，一并回顾并把 4500 调大。**

## 常见坑（踩过的，别再踩）

- **US 地区必须在美国 IP 跑**：US 商品页/itunes 接口在大陆 IP 会被 301 跳 cn 落地页 → 假阳性/geo_blocked。GitHub runner（美国 IP）满足；本地跑 us 区会失败。
- **itunes lookup 的 features 字段不含内购信息**：探测内购只能抓商品页的 `hasInAppPurchases` 字段，且该字段在页面出现几十次（含"相关推荐"里别的 App），必须归属到它**前面最近**的 id（owner_map 窗口 900/4000 字符），直接取第一个匹配会串味。
- **苹果图标/截图走官方 CDN，不转存**（商标与 AdSense 合规）。
- **限速**：lookup 100 id/批 + time.sleep 限速；商品页遇到 429/403 要指数退避重试，失败不写缓存、下轮再试，绝不把"未知"当 false。
- **保底池**（iap_collector load_pool）：iap-history 仍免费 ∪ iap-current-free 在挂 的 App 排最前、不被 limit 裁掉——这是"恢复付费"检测的关键，保证僵尸条目不超过 7 天。
- **分级调度**（详见铁律 7）：主池按"最近变价日"降序；播种班(UTC 22/23) limit=4500、其余班 2000；有 IAP 的 App 数接近/超过 4500 时同步调大。

## 验证与运行

- 改 iap_collector 后：`python3 scripts/iap_collector.py --selftest`（合成历史验证付费→免费判定）。
- 改 daily*.yml 后：校验 YAML 语法。
- 改 generate 相关：谨慎跑 `python3 scripts/generate.py --country cn --full`（会写 data 与 app/，确认在可回滚环境或 CI 验证）。
- 本地预览：`python3 -m http.server 8080`。
- 手动全量采集：`python3 scripts/iap_collector.py --region cn --limit 0 --delay 0.3`。

## 修改守则

- 先读被改脚本的头部 docstring（决策依据都在里面）。
- 小步改动、保留已有注释里的设计理由；不要为了"更简洁"重写已验证的判定/采集逻辑。
- 动 data schema / generate 输出 / 前端读取 三者之一时，必须同步另外两者。

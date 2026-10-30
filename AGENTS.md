# AGENTS.md — 苹果限免雷达（appstore-freebie）

> 最后复核：2026-10-30。本文件是**索引与红线清单**，权威细节以各脚本头部 docstring 为准；当铁律 7 的播种班 limit、监控池规模或判定阈值变更时，必须同步回顾本文件。

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
   - **🔴 本地改 JS/CSS 时，严禁本地人工批量 bump 全站 HTML 的版本号（2026-10-29 事故）**：
     本地若把 530 个 HTML 的 `?v=` 全部改掉并提交，必然与 CI 的 `daily: App Store 限免更新` 提交
     改在同一行 → **每次 pull 都是 530 个冲突文件**，GitHub Desktop 直接卡死（实测 2026-10-29）。
   - 正确做法：**本地只提交源码**（scripts/、assets/、README、index.html 等静态源文件），
     版本号交给 CI 跑批时自动 bump。若急需线上生效，手动 dispatch 一次 daily 即可。
   - `app/*.html` 是 CI 生成产物，本地无论怎么改都会被 CI 下次跑批覆盖，**永远不要提交它们**。
   - index.html / about.html / 404.html / privacy.html / terms.html / app-page.html 是静态源文件
     （stamp 只改写 `?v=` 行，其余内容保留），功能开关要改在这里而不是产物里。

7. **分级调度的 limit 是安全阀，必须随池增长回顾（2026-10-27）**
   - 主池按"最近变价日"降序；播种班(UTC 22/23) limit=4500、其余班 2000。
   - 该值的安全前提是"**有 IAP 的 app 数 < 4500**"。一旦监控池扩大使有 IAP 的 app 数接近/超过 4500，播种班会开始裁掉"变价日期较旧但有 IAP"的 app；极端情况下一个"从未被扫过、无记录但有 IAP 且恰好限免"的 app 会被挤出漏检。
   - 新候选经 `seed_iap_from_apprcn.py` 的 bootstrap 打 `today` 日期、排最前，已大幅缓解盲区；但 limit 不是越大越好（更大 = 更长单班时长、更易与下一班串行抢推 main）。
   - **约定：监控池规模变更时，一并回顾并把 4500 调大。**

8. **校验脚本只读：发现失效 ≠ 可以自己下架（2026-10-30 新增）**
   - `scripts/verify_live_freebies.py`（+ `scripts/render_verify_summary.py`）是**纯只读**的：
     只读 data/ 与 iTunes lookup 接口，把「在架但已恢复收费 / 折扣已结束」的条目列成清单。
     **绝不写 `data/`、绝不写 `app/`、不生成任何 HTML、不改 git。**
   - 下架动作**一律**由 `scripts/generate.py` 执行（见铁律 1：全站唯一写页人）。
     校验 → 发现失效 → 触发 daily 跑批 → generate.py 用既有的「促销粘性」逻辑下架，
     这条链路上**不允许有第二个写页方**。
   - `scripts/verify_and_trigger.sh`（部署在 ECS `/root/freebie-deploy/`）只做
     「读 + dispatch」两件事，同样不碰站点数据文件。
   - 判定口径必须与 generate.py 对齐（见铁律 4）：限免看现价是否 ≠0；
     特价看现价是否已回到历史最高价(history 的 `mx`)或降幅跌破 50%。
     **单方面放宽口径 = 误下架 = 事故。**
   - 两个必须保留的误报防护（勿删）：
     ① **整批 lookup 0 命中** → 判为接口异常，该区**跳过**，绝不当成「全部失效」；
     ② **区域自检**（currency 与 trackViewUrl 区域段须与所查地区一致）→
        不一致则该区跳过，防地理劫持导致误判。
   - 校验的**数据源**在 ECS 上是「站点部署目录里的 data/」（用户此刻正在看的那份），
     不是从 GitHub clone —— 大陆→GitHub 链路不稳会拖垮校验时效，
     且 main 可能还没同步到站点，验的不是用户看到的东西。

## 常见坑（踩过的，别再踩）

- **US 商品页必须在美国 IP 跑，但 lookup 接口不用**（2026-10-30 实测更正）：
  旧表述「US 商品页/itunes 接口在大陆 IP 会被 301 跳 cn 落地页」过宽——**301 只发生在商品页**
  （`apps.apple.com/us/app/...`，iap_collector / probe_iap_presence 抓的就是它，必须走境外 runner）。
  而 **`itunes.apple.com/lookup` 接口本身实测不受影响**：在大陆 ECS（121.40.250.144）与本地跑 us 区，
  返回的 `currency` 均为 USD、`trackViewUrl` 均为 `/us/` 路径、价格正确。
  故 `verify_live_freebies.py` 可以在 ECS（大陆 IP）上校验 us 区；
  脚本内仍保留「区域自检」（currency + trackViewUrl 区域段）作为兜底，
  一旦接口行为变化则该区跳过而非误报下架。
- **itunes lookup 的 features 字段不含内购信息**：探测内购只能抓商品页的 `hasInAppPurchases` 字段，且该字段在页面出现几十次（含"相关推荐"里别的 App），必须归属到它**前面最近**的 id（owner_map 窗口 900/4000 字符），直接取第一个匹配会串味。
- **苹果图标/截图走官方 CDN，不转存**（商标与 AdSense 合规）。
- **限速**：lookup 100 id/批 + time.sleep 限速；商品页遇到 429/403 要指数退避重试，失败不写缓存、下轮再试，绝不把"未知"当 false。
- **保底池**（iap_collector load_pool）：iap-history 仍免费 ∪ iap-current-free 在挂 的 App 排最前、不被 limit 裁掉——这是"恢复付费"检测的关键，保证僵尸条目不超过 7 天。
- **分级调度**（详见铁律 7）：主池按"最近变价日"降序；播种班(UTC 22/23) limit=4500、其余班 2000；有 IAP 的 App 数接近/超过 4500 时同步调大。

## 验证与运行

- 改 iap_collector 后：`python3 scripts/iap_collector.py --selftest`（合成历史验证付费→免费判定）。
- 改 daily*.yml / verify-freebies.yml 后：校验 YAML 语法。
- 改 generate 相关：谨慎跑 `python3 scripts/generate.py --country cn --full`（会写 data 与 app/，确认在可回滚环境或 CI 验证）。
- 本地预览：`python3 -m http.server 8080`。
- 手动全量采集：`python3 scripts/iap_collector.py --region cn --limit 0 --delay 0.3`。
- **查限免是否还有效（只读，随时可跑）**：`python3 scripts/verify_live_freebies.py`
  （实测两区 6.6 秒；加 `--report /tmp/v.json` 出 JSON，`--data-dir` 指定数据目录）。
  退出码 0=无失效 / 1=有失效 / 2=异常。**它不会改任何数据**，下架由 generate.py 负责。
- **校验脚本部署到 ECS**（改了 `verify_live_freebies.py` 后需重新复制，否则 ECS 跑的还是旧版）：
  `scp -i ~/.ssh/id_aliyun scripts/verify_live_freebies.py root@121.40.250.144:/root/freebie-deploy/`
  ECS 上 `bash /root/freebie-deploy/verify_and_trigger.sh` 可手动跑一轮（约 10 秒）。
  cron：`/etc/cron.d/freebie-verify`，每 2 小时的 :10 分（避开跑批 dispatch 点与 :30 同步）。

## 哪些改动要等 CI、哪些不用（速查表）

> 一句话：改"会重新生成站点的源头" → 等 CI；改"纯静态源文件" → 不等 CI。
> "改完不生效"的三连根因：① 旧 HTML 没重新生成；② `?v=` 戳没变、浏览器用 7 天缓存里的旧 JS/CSS；③ CI 串行排队要 1~2h。这三件都由 Actions 串起来做，所以"改代码=等 CI"。

**必须走 CI 重新生成（改完要 dispatch daily + 硬刷新才生效）：**
- `scripts/generate.py`、`scripts/iap_collector.py` 等采集/生成逻辑、算法判定阈值
- 任何 `data/*.json` schema 或判定规则
- 前端 `assets/js/app.js`、`assets/css/style.css`（→ generate 的 `stamp_asset_version` 自动 bump 戳）
- `data/*.json` 内容变化、新增/删除 App 卡片、sitemap

**不用等 CI（改完 push、CF Pages 部署即可，几秒~几分钟生效）：**
- 纯静态源文件：`index.html`、`about.html`、`404.html`、`privacy.html`、`terms.html`、`app-page.html`
  （stamp 只改写它们里的 `?v=` 行，其余内容原样保留；功能开关、广告代码位都改这里）

**永远不要手动改/不要提交：**
- `app/*.html`（CI 生成产物，下次跑批会被覆盖）
- 任何 HTML 里的 `?v=`（交 `stamp_asset_version` 自动算，手刷 530 个 = 530 冲突事故，见铁律 6）

**校验类脚本（只读，不影响线上）：**
- `scripts/verify_live_freebies.py`、`scripts/render_verify_summary.py`、`scripts/verify_and_trigger.sh`
  —— 改动它们**不影响**任何线上页面（不改 data/、不改 app/），push 即生效；
  但改完 `verify_live_freebies.py` 后**必须重新 scp 到 ECS**（见「验证与运行」一节），
  否则 ECS cron 跑的仍是旧版。`.github/workflows/verify-freebies.yml` 改的是 CI 行为，需 push 后生效。

**想提前生效**：push 后 SSH 跑 `/root/freebie-deploy/trigger_daily.sh`（或 curl dispatch daily），仍受串行排队延迟约束。
**验证生效**：`Cmd+Shift+R` 硬刷新，看源码里 `app.js?v=` 是否等于本地算的 `sha256(sha256(app.js)+sha256(style.css))[:10]`。

## 修改守则

- 先读被改脚本的头部 docstring（决策依据都在里面）。
- 小步改动、保留已有注释里的设计理由；不要为了"更简洁"重写已验证的判定/采集逻辑。
- 动 data schema / generate 输出 / 前端读取 三者之一时，必须同步另外两者。

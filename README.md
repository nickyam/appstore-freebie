# 苹果限免雷达 · App Store 每日限免清单（中国区 / 美国区）

一个**零后端、零服务器**的纯静态站点：每天自动比对苹果**中国区与美国区** App Store 官方价格，
找出「平时收费、限时免费」的 App 与降价特价，生成静态 JSON 由前端渲染。
数据来自 Apple 官方接口（iTunes RSS + Search API），图标走苹果 CDN，不做转存。

> 设计原则：站点本身**零后端**——Cloudflare Pages 静态托管 + GitHub Actions 跑批，
> 阿里云 ECS **只做两件事**（不参与数据计算）：
> ① 准点调用 `workflow_dispatch` 触发跑批（绕开免费 runner 排队长尾）；
> ② 跑一个国内镜像站（`appstore.limzero.com`，rsync 拉产物）。
> 分工是「阿里云只做合规与调度、内容/前端走 CF」。

---

## 工作原理

1. **GitHub Actions** 每 6 小时（北京时间 00:00 / 06:00 / 12:00 / 18:00 由 ECS 触发）分别运行 `scripts/generate.py --country cn` 与 `--country us`：
   - 构建「宽监控池」：抓取苹果 **22 个分类的付费榜 Top100 + 畅销榜 Top100** + 整体免费榜 Top200（去重后每区数千个易做限免的 App），
     再与本地**价格历史**（`data/history-{country}.json`，每 App 最多 120 条日快照 + 永久原价基线）取并集——**哪怕 App 跌出榜单也持续跟踪**；
   - 用官方 `lookup` 接口逐个核对实时价格（按 100 个/批、礼貌限速）；
   - 以**永久价格基线**判定（取代旧版「只和前一天比」；原价见过一次就永久记住，不随窗口裁剪消失），每 App 每区独立保存价格快照：
     - 限免：当前价 = 0，且历史基线中**曾 > 0**，且连续为 0 的天数 ≤ 7（排除永久免费 / 长期免费）；天然覆盖「日内闪免」与「跨天」两种触发；
     - 降价（特价）：当前价 < 历史最高价，且**降幅 ≥ 50%**；
   - 按「新触发优先、其次用户评分降序」排序，输出 `data/free-today-{country}.json`（每类最多展示 100 条，历史仍全量保留），历史回写后 commit 回仓库。
2. **Cloudflare Pages** 部署仓库静态文件；前端 `assets/js/app.js` 按所选地区拉取
   同域 `data/free-today-{country}.json` 渲染，顶部菜单可在「🇨🇳 中国区 / 🇺🇸 美国区」间切换，卡片展示图标 / 开发者 / 分类 / 评分 / 价格。

> 历史为空时首次运行只初始化（不报限免）；**1~2 天后**基线逐步建立即可稳定检出。监控池与历史越跑越准，限免/特价覆盖随天数提升。

---

## 本地预览

```bash
cd appstore-freebie
python3 -m http.server 8080
# 浏览器打开 http://127.0.0.1:8080/，用顶部菜单切换中国区/美国区
```

可选：本地手动跑一次生成器看真实数据（会写 history / free-today）：
```bash
python3 scripts/generate.py --country cn
python3 scripts/generate.py --country us
```

---

## 部署步骤

### 1. 推到 GitHub（本机已 git init + 首次 commit，请你在 GitHub Desktop 推送）
- 在 GitHub 新建一个**公开或私有**仓库（私有也支持免费 Actions + Pages）。
- 推送本目录。

### 2. Cloudflare Pages 接入
- Pages → 连接 Git 仓库 → 选该仓库。
- Build 设置：**Build command 留空**，**Output directory 填 `/`**（根目录即静态站）。
- 自定义域已配置：`appstore.nickyam.com`（Pages 后台添加，SSL 已启用，状态活动）。
- `index.html` / `robots.txt` / `sitemap.xml` 内已写入该域名，无需再改。

### 3. 启用每日更新
- 主跑批 `daily.yml`（每日 00:00/06:00/12:00/18:00 北京 4 班）与全量回查 `daily-full.yml`（每日 03:30 北京）均由阿里云 ECS 在精确北京时刻调用 GitHub `workflow_dispatch` 触发（绕过免费 runner 的排队延迟），不再依赖 GitHub 自带 cron。
- 也可在 Actions 页面手动 **Run workflow** 立即跑一次。
- 每次 Actions 提交 `data/free-today-*.json` 会触发 Pages 重新部署（自动）。

### 4. 子路径部署（可选）
所有内部链接已相对化并统一 `<base href="/">`：若要把站点部署到子路径（如 `example.com/freebie/`），
只需把**所有 HTML 页面**里的 `<base href="/">` 改为 `<base href="/freebie/">` 即可，无需改动其它代码
（canonical / sitemap / og:url 仍按域名绝对地址生成，不受影响）。

---

## AdSense 接入（变现）

- 发布商 ID `ca-pub-7114121088728794`，已配在 `index.html` 的 `<head>` 与各处 `data-ad-client`。
- **全站开启 Auto Ads**（页面级自动广告，`enable_page_level_ads: true`）：插位交给 Google
  判定，代码里不再手工搬运列表广告位。
- 详情页（`app/*.html`）另保留**一个手动顶部展示位**（`adSlotHTML()` / `pushAd()`，
  slot `7735913921`），作为 Auto Ads 之外的稳定补充。

### 卡片网格里的「自家推荐卡」（取代原 In-feed 广告）
- 列表按固定间隔插入**自建推荐卡**而非谷歌 in-feed 广告：`assets/js/app.js` 的
  `PROMO_INTERVAL`（当前 18，设 0 关闭）+ `PROMO_ITEMS`（4 条轮播：凌零集 / LibreTV /
  美区 Apple ID 指南 / 极限零点）。纯静态 HTML，不加载任何第三方脚本。
- **为什么放弃 in-feed 广告（2026-11 定案，勿回退）**：卡片由 JS 动态生成，Google 的 feed
  自动扫描看不到 DOM 里的 `.card`，只能手工配 layout-key；跨域 iframe 让广告高度无法与内容卡
  对齐，且一页请求十几次时只有前几个被填充、其余全 unfilled 留下空方框。换自家推荐卡后既保住
  页面节奏，又把流量导回自有资产。

### 图片加载
- 卡片图标、详情页截图均已带 `loading="lazy"`；图标走苹果官方 CDN，不转存。

### ⚠️ 合规要点（关系到账号生死）
- 本页已带**原创编辑内容**（限免是什么、我们怎么算、免责声明），避免被判「薄内容 / 抓取内容」。
- App 图标/截图均走苹果官方 CDN 链接，**不要转存到自己的服务器**（符合苹果商标与素材规范）。
- 不要做「下载返利 / 激励」，那是 AdSense 明确禁止的；本页仅为信息展示 + 跳转 App Store。
- 价格与可用性以 App Store 内显示为准，页面已注明免责。

---

## 自定义

- **加更多地区**：在 `daily.yml` 增加一步 `python scripts/generate.py --country <区码>`，
  并在 `assets/js/app.js` 的 `REGIONS` 里加对应项（区码如 `jp`、`gb`、`hk` 等）。
- **调监控池 / 展示量**：`scripts/generate.py` 顶部 `GENRE_LIMIT`（每分类付费榜条数，RSS 实测每源上限 100）、
  `GROSS_LIMIT`（每分类畅销榜条数）、`FREE_LIMIT`（免费榜条数）、`APP_PAGE_MAX_AGE_DAYS`（独立页过期清理天数，默认 365）、`HISTORY_MAX_ENTRIES`（价格库软上限，默认 50000）、
  `DEAL_DROP_PCT`（降价判定降幅阈值）、`MAX_DISPLAY`（前端最多展示的限免/特价数）均可调。
  > 注：原 `HISTORY_DAYS` 常量已废弃移除——价格历史改为「每 App 每区独立快照（`HISTORY_CAP=120` 条）+ 永久原价基线」持久化，不再按总天数裁剪；「30 天」只用于详情页价格走势图展示。
- **改调度频率**：生成节奏由 ECS 的 `/etc/cron.d/freebie-dispatch`（daily.yml 每日 4 班 00:00/06:00/12:00/18:00 北京）与 `/etc/cron.d/freebie-dispatch-full`（daily-full.yml 每日 03:30 北京）控制，镜像同步 `/etc/cron.d/freebie-sync` 每 2 小时拉取一次即可；调度都在 ECS 的 `/etc/cron.d/` 下，改频率直接改对应文件，无需动 GitHub cron。
- **出英文版拉海外流量**：复制一套 `index.html` 文案为英文，可抬高 AdSense RPM（中国区流量 RPM 偏低）。

---

## 文件结构

```
appstore-freebie/
├── index.html              # 前端页面（含原创编辑文案 + AdSense 位 + 区域切换菜单）
├── assets/
│   ├── css/style.css
│   └── js/app.js           # 按地区拉取 data/free-today-{country}.json 并渲染
├── scripts/generate.py     # 比价生成器（支持 --country cn/us，GitHub Actions 调用）
├── data/
│   ├── history-cn.json     # 中国区价格历史（每 App 独立快照 + 永久原价基线；🔴 不上线，见下）
│   ├── history-us.json     # 美国区 30 天价格历史
│   ├── free-today-cn.json  # 中国区每日限免/特价清单（前端读取）
│   └── free-today-us.json  # 美国区每日限免/特价清单（前端读取）
├── .github/workflows/daily.yml
├── robots.txt / sitemap.xml
└── README.md
```

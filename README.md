# 限免日报 · App Store 每日限免清单（中国区 / 美国区）

一个**零后端、零服务器**的纯静态站点：每天自动比对苹果**中国区与美国区** App Store 官方价格，
找出「平时收费、限时免费」的 App 与降价特价，生成静态 JSON 由前端渲染。
数据来自 Apple 官方接口（iTunes RSS + Search API），图标走苹果 CDN，不做转存。

> 设计原则：全部跑在 Cloudflare Pages（静态托管）+ GitHub Actions（每日比价），
> **不依赖你那台阿里云服务器**，符合「阿里云只跑合规计算、内容/前端走 CF」的分工。

---

## 工作原理

1. **GitHub Actions** 每天 09:00（北京时间）分别运行 `scripts/generate.py --country cn` 与 `--country us`：
   - 构建「宽监控池」：抓取苹果 **22 个分类的付费榜 Top100** + 免费榜 Top100（覆盖约 1500 个易做限免的付费 App），
     再与本地历史「常规价基线」(`data/baseline-{country}.json`) 取并集——**哪怕 App 跌出榜单也持续跟踪**；
   - 用官方 `lookup` 接口逐个核对实时价格（按 100 个/批、礼貌限速）；
   - 与基线价格对比：
     - 当前价 = 0 且基线 > 0 → **限免**（价格归零即判，不再依赖付费榜——数学上付费榜永远抓不到限免）
     - 当前价 > 0 且 < 基线 → **特价**
   - 按**用户评分降序**排序（优先展示优质 App），输出 `data/free-today-{country}.json`，基线漂移为当前价后回写，commit 回仓库。
2. **Cloudflare Pages** 部署仓库静态文件；前端 `assets/js/app.js` 按所选地区拉取
   同域 `data/free-today-{country}.json` 渲染，顶部菜单可在「🇨🇳 中国区 / 🇺🇸 美国区」间切换，卡片展示图标 / 开发者 / 分类 / 评分 / 价格。

> 首次运行只播种基线（不报限免）；**第二天起**即可稳定检出限免 / 特价。基线随每日比价自然增长，监控池越跑越准。

---

## 本地预览

```bash
cd appstore-freebie
python3 -m http.server 8080
# 浏览器打开 http://127.0.0.1:8080/，用顶部菜单切换中国区/美国区
```

可选：本地手动跑一次生成器看真实数据（会写 baseline / free-today）：
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
- 自定义域已配置：`freebie.nickyam.com`（Pages 后台添加，SSL 已启用，状态活动）。
- `index.html` / `robots.txt` / `sitemap.xml` 内已写入该域名，无需再改。

### 3. 启用每日更新
- 推送后 GitHub Actions 自动激活（`daily.yml` 里的 `cron`）。
- 也可在 Actions 页面手动 **Run workflow** 立即跑一次。
- 每次 Actions 提交 `data/free-today-*.json` 会触发 Pages 重新部署（自动）。

---

## AdSense 接入（变现）

- `index.html` 已挂自动广告脚本，发布商 ID 为 `ca-pub-7114121088728794`
  （如需更换，改 `<head>` 与各处 `data-ad-client`）。
- 页面内 `<ins data-ad-slot="0000000000">` 的 `0000000000` 换成你在 AdSense 建的**内容广告单元 ID**。
- 在 AdSense 后台「添加站点」提交你的域名，审核通过后广告自动生效。

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
  `FREE_LIMIT`（免费榜条数）、`MAX_DISPLAY`（前端最多展示的限免/特价数）可调。
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
│   ├── baseline-cn.json    # 中国区常规价基线（每日更新）
│   ├── baseline-us.json    # 美国区常规价基线（每日更新）
│   ├── free-today-cn.json  # 中国区每日限免/特价清单（前端读取）
│   └── free-today-us.json  # 美国区每日限免/特价清单（前端读取）
├── .github/workflows/daily.yml
├── robots.txt / sitemap.xml
└── README.md
```

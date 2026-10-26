// 苹果限免雷达前端：地区数据渲染 + 中英双语 i18n + 日/夜主题切换 + 搜索/分类筛选
(function () {
  'use strict';

  // ===== 双语字典 =====
  var I18N = {
    zh: {
      logo: '苹果限免雷达',
      nav_about: '关于',
      hero_title: '今日 App Store 限免清单',
      hero_sub: '每天自动扫描苹果官方价格，捕捉「昨天还收费、今天免费领」的降价信号——苹果限免雷达帮你盯住每一次捡漏机会。',
      region_cn: '🇨🇳 中国区',
      region_us: '🇺🇸 美国区',
      intro_h2: '什么是「限免」？我们怎么挑？',
      intro_p1: '<b>限免（限时免费）</b>指的是开发者把平时收费的 App 在一段时间内免费开放下载——你今天下了就永久免费，过后恢复原价。这类活动在 App Store 上每天都在发生，但散落在海量应用里，肉眼根本盯不过来。',
      intro_p2: '我们同时覆盖<b>中国区</b>与<b>美国区</b>两个商店：用顶部菜单切换，列表与价格会自动刷新。无论你在哪个区，都能一眼看到当天的好货。',
      intro_p3: '我们的做法很直接，也最可靠：',
      intro_li1: '每天扫描苹果<b>官方</b>全部 22 个分类的「付费榜 Top100」「畅销榜 Top100」以及整体「免费榜 Top200」，合并去重后每区覆盖约 3,900–4,100 款 App，再用苹果官方接口逐个核对实时价格；',
      intro_li2: '和你<b>历史常规价</b>做对比——只有「昨天还收费、今天变 0 元」的，才会被标记为<b>限免</b>；',
      intro_li3: '价格只是降低但没到免费的，单独归到<b>特价</b>一栏，方便比价；',
      intro_li4: '所有价格与可用性以苹果商店为准，可能随时变动，<b>下单前请务必在 App Store 内确认</b>。',
      intro_p4: '所有数据来自 Apple 公开接口，App 图标均直接引用苹果 CDN，不做转存。点击任意 App 即可跳转对应地区的 App Store 详情页。',
      sec_free: '🔓 本体限免',
      sec_deal: '💰 特价打折（降价未免费）',
      sec_iap: '🎮 内购限免',
      region_cn: '中国区',
      region_us: '美国区',
      iap_empty: '内购限免正在累积数据，需连续观察数日才能捕捉「付费→免费」的跳变。',
      iap_nodata: '该区暂未采集内购数据（美国区需走境外 CI）。',
      iap_perm_note: '个常驻免费内购（永久 tier-0 赠品，不计入限免）',
      iap_days: '已免费',
      iap_original: '原价',
      iap_today: '今日起免费',
      iap_perm_tag: '常驻免费(赠品)',
      iap_cur_free: '当前免费',
      dt_iap_title: '🎁 内购限时免费',
      back_top: '返回顶部',
      loading: '加载中…',
      free_empty: '今天没有检出限免 App，明天再来看看～',
      deal_empty: '今天没有降价的特价 App。',
      filter_empty: '没有符合当前筛选条件的 App。',
      search_ph: '搜索 App 名称 / 开发者…',
      genre_all: '全部分类',
      footer_copyright: '苹果限免雷达 · 数据每日自动更新 · 非苹果官方站点',
      card_store: 'App Store',
      card_free_price: '免费',
      date_prefix: '更新时间：',
      err_line: '数据暂时无法加载，请稍后刷新',
      err_box: '数据暂时无法加载，请稍后刷新重试。',
      about_badge: '🍎 关于本站',
      about_h1: '关于苹果限免雷达',
      about_lead: '苹果限免雷达每天自动扫描中国区与美国区 App Store 的官方价格，把「昨天还收费、今天限时免费」的优质 App 挑出来，附原价对比、用户评分与近 30 天价格走势，帮你省下每一分钱。',
      intro_p5: 'App 一旦进入限免或特价，只要活动没结束（价格还维持在促销水平），就会一直留在当天的清单里；等价格恢复原价后自动下架——所以你隔几天回来看，好货不会悄悄消失。',
      about_q_h2: '常见问题',
      about_q1: '<b>限免下载的 App，以后还收费吗？</b>不会。限免期间用 Apple ID 下载后会永久绑定你的账户，以后再下载也免费；卸载重装同样免费。',
      about_q2: '<b>为什么列表里有些 App 标着原价？</b>那是为了方便你判断省了多少——「¥98 ← 免费」表示该 App 原价 ¥98、当前限时免费。',
      about_q3: '<b>数据多久更新一次？</b>每 6 小时自动更新（北京时间 02:00 / 08:00 / 14:00 / 20:00）；页面加载失败时，点击左上角站名即可立即刷新。',
      about_note: '⚠️ 本站为非官方独立站点，与 Apple Inc. 无任何隶属关系。所有价格与可用性以 App Store 实时显示为准，本页不构成购买建议。',
      about_dis_h: '免责声明',
      about_dis_p: '本站价格与可用性来自 Apple 官方接口，可能随时变动；限免/特价活动由开发者设定，本站不构成购买建议。请以下单时 App Store 内显示为准。本站为非官方独立站点，与 Apple Inc. 无任何隶属关系。',
      ab_what_h: '我们做什么',
      ab_what_p1: '「苹果限免雷达」是一个专注 App Store 限免与特价的每日信息聚合服务。我们自动扫描苹果中国区与美国区的官方价格，把「昨天还收费、今天限时免费」的优质 App 挑出来，同时标出降幅明显的「特价」App，并附原价对比、用户评分与近 30 天价格走势，帮你用最低成本发现好应用。',
      ab_what_p2: '无论你习惯用中国区还是美国区 Apple ID，都能在顶部一键切换，列表、价格与货币会自动刷新——两个商店的好货，一个页面尽收眼底。',
      ab_method_h: '数据从哪来，怎么挑',
      ab_method_li1: '广撒网：每日扫描苹果官方全部 22 个分类的「付费榜 Top100」「畅销榜 Top100」以及整体「免费榜 Top200」，合并去重后每区覆盖约 3,900–4,100 款 App，构成监控池；',
      ab_method_li2: '精核对：用苹果官方接口（iTunes Lookup）逐个回查实时价格与评分，数据源头为 Apple 一手数据，不依赖任何第三方聚合；',
      ab_method_li3: '判限免：只有「当前售价 0 元、近 30 天曾收费、且连续免费天数不超过 7 天」的 App 才标记为限免——天然覆盖日内闪免与跨天活动，并自动排除长期 / 永久免费的应用；',
      ab_method_li4: '判特价：当前价低于近 30 天最高价、且降幅达到或超过 50% 的，单独归入「特价」一栏，方便比价；',
      ab_method_li5: '保质量：仅收录有真实用户评分（评分人数 > 0）的 App；所有 App 图标均直接引用苹果官方 CDN，不做本地转存，点击即跳转对应地区的 App Store 详情页。',
      ab_update_h: '多久更新一次',
      ab_update_p: '数据由后台任务每 6 小时自动刷新一次（北京时间 02:00 / 08:00 / 14:00 / 20:00）。页面偶发加载失败时，点击左上角站名即可立即强制刷新。',
      ab_arch_h: '技术架构',
      ab_arch_p: '本站是纯静态站点：没有后端服务器、没有数据库，全部页面由构建脚本预生成后通过 Cloudflare Pages 全球 CDN 分发，并在中国大陆设有边缘镜像以优化访问速度；全站强制 HTTPS 加密传输。',
      home_intro_text: '每天自动扫描苹果官方价格，捕捉「昨天还收费、今天免费领」的降价信号，覆盖中国区与美国区。',
      home_intro_link: '了解我们怎么挑 →',
      stat_free: '本体限免',
      stat_deal: '特价打折',
      stat_iap: '内购限免',
      stat_saved: '今日可省',
      badge_new: 'NEW',
      badge_iap: '含内购',
      badge_pure: '纯买断',
      foot_privacy: '隐私政策',
      foot_terms: '使用条款',
      foot_rights: '保留所有权利',
      dt_screenshots: '应用截图',
      dt_about: '应用介绍',
      dt_no_desc: '暂无官方介绍。',
      dt_price_history: '近 30 天价格走势',
      dt_cross: '中美两区现价对比',
      dt_qr: '扫码前往 App Store',
      dt_mt_note: '· 内容由机器翻译，仅供参考',
      dt_qr_btn: '手机扫码',
      back_home: '← 返回首页',
      dt_close_hint: '点击任意处关闭',
      dt_genre_link: '查看该分类的今日限免',
      dt_same_period: '同时期的其他限免',
      dt_go: '在 App Store 打开',
      dt_ver: '版本',
      dt_size: '大小',
      dt_age: '年龄分级',
      dt_rating_count: '个评分',
      no_rating: '暂无评分',
      dt_loading: '详情加载中…',
      dt_loadfail: '详情加载失败，请稍后重试或直接前往 App Store。',
      dt_not_in: '该区暂未上架',
      dt_none: '无',
      dt_fullpage: '查看完整页面',
      pv_badge: '📋 隐私政策',
      pv_h1: '隐私政策',
      pv_lead: '「苹果限免雷达」（下称「本站」）非常重视你的隐私。本政策说明本站收集哪些信息、如何使用，以及你拥有的选择权。',
      pv_s1h: '一、我们不收集个人信息',
      pv_s1: '本站为纯静态信息聚合站点：无需注册、无需登录，不设账号系统，不主动收集你的姓名、邮箱、手机号等任何个人信息。',
      pv_s2h: '二、服务器日志',
      pv_s2: '与绝大多数网站一样，托管与 CDN 服务商会记录访问日志（如 IP 地址、浏览器类型、访问时间、所请求页面），仅用于安全防护（防盗链、防攻击、速率限制）与必要的流量统计，不用于用户画像，也不会与第三方共享用于营销目的。',
      pv_s3h: '三、Cookie 与本地存储',
      pv_s3: '本站仅在你的浏览器 localStorage 中保存偏好设置（界面语言、深色模式、地区选择），以便下次访问时保持你的选择。这些数据只存在你自己的设备上，不含任何跟踪标识；清除浏览器数据即可删除。',
      pv_s4h: '四、第三方服务',
      pv_s4a: '<b>Apple</b>：本站数据来自 App Store 公开接口；点击 App 卡片会跳转到 Apple 的页面，后续受 Apple 隐私政策约束。',
      pv_s4b: '<b>Google AdSense</b>：本站展示 Google 提供的广告。Google 及其合作伙伴可能使用 Cookie 根据你的访问投放广告；你可以在「Google 广告设置」中关闭个性化广告。',
      pv_s4c: '<b>Cloudflare / 阿里云</b>：为本站提供 CDN 加速与托管服务。',
      pv_s4d: '<b>翻译与二维码</b>：在 App 详情页，若界面语言与 App 原始语言不同，本站会调用 Google 翻译 / MyMemory 接口实时翻译介绍文案；分享用的二维码由 api.qrserver.com 生成。这些请求仅在你查看详情时从你的浏览器发出，本站不留存任何文本或链接。',
      pv_s5h: '五、数据安全',
      pv_s5: '本站全站强制 HTTPS 加密传输；不设任何用户数据上传通道。',
      pv_s6h: '六、未成年人',
      pv_s6: '本站不面向未成年人收集任何数据。',
      pv_s7h: '七、政策更新',
      pv_s7: '本政策如有修订，将在本页发布并更新「最后更新」日期；继续使用本站即视为接受修订后的政策。',
      pv_s8h: '八、联系我们',
      pv_s8: '如对本政策有任何疑问或建议，欢迎通过运营者的博客站点与我们联系。',
      pv_s9h: '九、你的权利',
      pv_s9: '你对自己的个人信息享有访问、更正与删除等权利。由于本站不存储任何个人信息、也不设账号系统，通常无需专门操作；如你希望查询或删除由托管 / CDN 服务商记录的、与本站相关的服务器访问日志，可通过下方联系方式向我们提出请求，我们将在合理范围内配合处理。',
      pv_s10h: '十、数据保留',
      pv_s10: '服务器访问日志由托管与 CDN 服务商按各自策略留存，仅用于安全防护与必要的运维审计，留存期限不超过实现该等目的所必需的期间；你浏览器中的 localStorage 偏好数据在你清除浏览器数据时即被删除。',
      pv_updated: '最后更新：2026-10-20',
      tm_badge: '📋 使用条款',
      tm_h1: '使用条款',
      tm_lead: '访问或使用「苹果限免雷达」（下称「本站」）即表示你已阅读并同意本条款；如不同意，请停止使用本站。',
      tm_s1h: '一、服务性质',
      tm_s1: '本站是免费的信息聚合站点，通过苹果官方公开接口自动汇总 App Store（中国区 / 美国区）的价格变动信息，供个人参考使用。',
      tm_s2h: '二、信息准确性',
      tm_s2: '限免与特价活动由 App 开发者自行设定，价格与可用性随时可能变动。本站尽力保证数据及时、准确，但不承诺实时无误；<b>一切请以 App Store 内实际显示为准</b>。',
      tm_s3h: '三、非官方声明',
      tm_s3: '本站为独立站点，与 Apple Inc. 及其关联公司无任何隶属或合作关系；App Store、iPhone 等商标归 Apple Inc. 所有。',
      tm_s4h: '四、知识产权',
      tm_s4: 'App 名称、图标、开发者信息等归其权利人所有，本站仅作信息引用。本站自行撰写的文字与站点设计版权归本站所有，未经书面许可不得转载、镜像或批量抓取。',
      tm_s5h: '五、广告',
      tm_s5: '本站通过 Google AdSense 等方式展示广告以维持运营；广告内容由广告主负责，不代表本站立场，本站不对广告中的产品或服务作担保。',
      tm_s6h: '六、责任限制',
      tm_s6: '在适用法律允许的最大范围内，本站不对因使用或依赖本站信息而产生的任何直接或间接损失（包括但不限于误购、错过促销）承担责任。',
      tm_s7h: '七、条款变更',
      tm_s7: '本条款可能随时修订，修订后在本页公布；修订后继续使用本站即视为接受新条款。',
      tm_s8h: '八、法律适用与争议解决',
      tm_s8: '本条款的解释、效力及争议解决均适用中华人民共和国法律（不含冲突法规则）。因使用本站而产生的任何争议，双方应首先友好协商解决；协商不成的，任何一方均可向本站运营者所在地有管辖权的人民法院提起诉讼。',
      tm_updated: '最后更新：2026-10-20',
      nf_badge: '🧭 页面不存在',
      nf_h1: '404',
      nf_lead: '你访问的页面不存在，或内容已被移动 / 下架。',
      nf_tip: '可以试试下面这些：',
      nf_home: '回到首页',
      nf_about: '了解本站',
      nf_updated: '最后更新：2026-10-21'
    },
    en: {
      logo: 'Apple Freebie Radar',
      nav_about: 'About',
      hero_title: "Today's App Store Freebies",
      hero_sub: 'We scan Apple’s official prices every day and catch the drop signals — paid yesterday, free today — so you never miss a steal.',
      region_cn: '🇨🇳 China',
      region_us: '🇺🇸 United States',
      intro_h2: 'What is a "limited-time freebie" and how we pick?',
      intro_p1: '<b>Limited-time freebie</b> means a developer temporarily makes a paid app free to download — grab it today and it stays free forever, then the price returns. These happen on the App Store daily but are buried among millions of apps, impossible to track by eye.',
      intro_p2: 'We cover both the <b>China</b> and <b>United States</b> stores: switch from the top menu and the list and prices refresh automatically. Either region, you see the day’s best picks at a glance.',
      intro_p3: 'Our method is simple and reliable:',
      intro_li1: 'Every day we scan Apple’s <b>official</b> Top100 Paid and Top100 Grossing across all 22 categories, plus the overall Top200 Free chart; after dedup that’s ~3,900–4,100 apps per region, then we verify each app’s live price via Apple’s official API;',
      intro_li2: 'We compare against your <b>historical regular price</b> — only apps that were paid yesterday and hit 0 today get flagged as <b>free</b>;',
      intro_li3: 'Apps that dropped in price but aren’t free go in a separate <b>Deals</b> column for easy comparison;',
      intro_li4: 'All prices and availability are subject to Apple and may change anytime — <b>always confirm in the App Store before purchasing</b>.',
      intro_p4: 'All data comes from Apple’s public APIs; app icons link directly to Apple’s CDN, not re-hosted. Tap any app to jump to its App Store page in that region.',
      sec_free: '🔓 App Freebies',
      sec_deal: '💰 Price Drops (reduced price)',
      sec_iap: '🎮 In-App Freebies',
      region_cn: 'China',
      region_us: 'US',
      iap_empty: 'IAP freebie data is still accumulating — it takes several days of observation to catch a paid→free flip.',
      iap_nodata: 'No IAP data collected for this region yet (US requires an overseas CI runner).',
      iap_perm_note: 'permanent free IAPs (tier-0 gifts, excluded from freebies)',
      iap_days: 'free for',
      iap_original: 'was',
      iap_today: 'Free since today',
      iap_perm_tag: 'Permanent free (gift)',
      iap_cur_free: 'Currently free',
      dt_iap_title: '🎁 IAP Limited-Time Free',
      back_top: 'Back to top',
      loading: 'Loading…',
      free_empty: 'No limited-time free apps found today. Check back tomorrow.',
      deal_empty: 'No price-drop deals found today.',
      filter_empty: 'No apps match the current filter.',
      search_ph: 'Search app name or developer…',
      genre_all: 'All categories',
      footer_copyright: 'Freebie Radar · updated daily · not an official Apple site',
      card_store: 'App Store',
      card_free_price: 'Free',
      date_prefix: 'Updated: ',
      err_line: 'Data temporarily unavailable, please refresh later',
      err_box: 'Data temporarily unavailable, please refresh and retry.',
      about_badge: '🍎 About',
      about_h1: 'About Apple Freebie Radar',
      about_lead: 'Apple Freebie Radar scans official App Store prices every day, surfacing apps that went from paid yesterday to free today — with original-price comparison and user ratings.',
      intro_p5: 'Once an app goes free or discounted, it stays in the daily list as long as the promo lasts (price remains below the regular price); it drops off automatically once the price returns — so good deals won’t quietly disappear when you check back days later.',
      about_q_h2: 'FAQ',
      about_q1: '<b>Will an app I claimed during a freebie cost money later?</b> No. Downloading during the free window binds it to your Apple ID permanently — future downloads and re-installs stay free.',
      about_q2: '<b>Why do some apps show a struck-through price?</b> So you can see the saving — “$9.99 → Free” means the regular price is $9.99 and it’s free right now.',
      about_q3: '<b>How often is data updated?</b> Automatically every 6 hours (02:00 / 08:00 / 14:00 / 20:00 Beijing time); if loading fails, click the site name at the top-left to refresh immediately.',
      about_note: '⚠️ This is an independent, unofficial site with no affiliation to Apple Inc. All prices and availability are subject to the App Store. This page is not purchase advice.',
      about_dis_h: 'Disclaimer',
      about_dis_p: 'Prices and availability on this site come from Apple’s official API and may change anytime; free/deal events are set by developers and this site is not purchase advice. Always rely on what shows in the App Store at checkout. This is an independent, unofficial site with no affiliation to Apple Inc.',
      ab_what_h: 'What we do',
      ab_what_p1: 'Apple Freebie Radar is a daily aggregator focused on App Store limited-time freebies and price drops. We automatically scan Apple’s official China and US store prices, surface apps that went from paid yesterday to free today, flag notable price-drop "Deals", and attach original-price comparison, user ratings and a 30-day price trend — so you can find great apps at the lowest cost.',
      ab_what_p2: 'Whether you use a China or US Apple ID, switch with one tap at the top — the list, prices and currency refresh automatically. The best picks from both stores, in one place.',
      ab_method_h: 'Where the data comes from, and how we pick',
      ab_method_li1: 'Wide net: every day we scan Apple’s official Top100 Paid and Top100 Grossing across all 22 categories, plus the overall Top200 Free chart. After dedup, that’s ~3,900–4,100 apps per region in the monitoring pool;',
      ab_method_li2: 'Precise check: we re-verify each app’s live price and ratings via Apple’s official API (iTunes Lookup). The data source is Apple’s first-party feed — no third-party aggregator in the middle;',
      ab_method_li3: 'Freebie rule: an app is flagged as a freebie only if its current price is 0, it was paid within the last 30 days, and it has been free for no more than 7 consecutive days — naturally covering intraday flash-freebies and multi-day runs, while excluding permanently/long-term free apps;',
      ab_method_li4: 'Deal rule: apps whose current price is below their 30-day high and have dropped 50% or more get their own "Deals" column for easy comparison;',
      ab_method_li5: 'Quality gate: we only list apps with real user ratings (rating count > 0). All app icons link directly to Apple’s official CDN, not re-hosted; tap to jump to the App Store page in that region.',
      ab_update_h: 'How often is it updated',
      ab_update_p: 'A background job refreshes the data automatically every 6 hours (02:00 / 08:00 / 14:00 / 20:00 Beijing time). If a page fails to load, click the site name at the top-left to force an immediate refresh.',
      ab_arch_h: 'Technical architecture',
      ab_arch_p: 'This site is fully static: no backend server, no database. Every page is pre-built by a script and delivered through Cloudflare Pages’ global CDN, with an edge mirror in mainland China for faster access. The entire site enforces HTTPS.',
      home_intro_text: 'We scan official App Store prices daily to catch the drop signals — paid yesterday, free today — across the China and US stores.',
      home_intro_link: 'How we pick →',
      stat_free: 'App freebies',
      stat_deal: 'Price drops',
      stat_iap: 'IAP freebies',
      stat_saved: 'You save',
      badge_new: 'NEW',
      badge_iap: 'With IAP',
      badge_pure: 'No IAP',
      foot_privacy: 'Privacy Policy',
      foot_terms: 'Terms of Use',
      foot_rights: 'All rights reserved',
      dt_screenshots: 'Screenshots',
      dt_about: 'About this app',
      dt_no_desc: 'No official description available.',
      dt_price_history: 'Price trend (last 30 days)',
      dt_cross: 'CN vs US current price',
      dt_qr: 'Scan to open in App Store',
      dt_mt_note: '· Machine translation, for reference only',
      dt_qr_btn: 'Scan to download',
      back_home: '← Back to home',
      dt_close_hint: 'Tap anywhere to close',
      dt_genre_link: 'Browse today\u2019s deals in this category',
      dt_same_period: 'More free right now',
      dt_go: 'Open in App Store',
      dt_ver: 'Version',
      dt_size: 'Size',
      dt_age: 'Age rating',
      dt_rating_count: ' ratings',
      no_rating: 'No ratings yet',
      dt_loading: 'Loading details…',
      dt_loadfail: 'Failed to load details. Please retry or open the App Store directly.',
      dt_not_in: 'Not available in this store',
      dt_none: 'None',
      dt_fullpage: 'Full page',
      pv_badge: '📋 Privacy Policy',
      pv_h1: 'Privacy Policy',
      pv_lead: 'Apple Freebie Radar ("this site") takes your privacy seriously. This policy explains what information we collect, how it is used, and the choices you have.',
      pv_s1h: '1. We do not collect personal information',
      pv_s1: 'This site is a static information aggregator: no sign-up, no login, no account system. We do not collect your name, email, phone number, or any other personal information.',
      pv_s2h: '2. Server logs',
      pv_s2: "Like most websites, our hosting and CDN providers record access logs (such as IP address, browser type, time of visit, and requested pages), used solely for security protection (anti-hotlinking, anti-abuse, rate limiting) and essential traffic statistics — never for user profiling, and never shared with third parties for marketing.",
      pv_s3h: '3. Cookies and local storage',
      pv_s3: "We only store your preferences (language, dark mode, region) in your browser's localStorage so your choices persist. This data lives on your own device, contains no tracking identifiers, and can be removed anytime by clearing browser data.",
      pv_s4h: '4. Third-party services',
      pv_s4a: "<b>Apple</b>: data comes from public App Store APIs; tapping an app card takes you to Apple's pages, which are governed by Apple's privacy policy.",
      pv_s4b: '<b>Google AdSense</b>: this site shows ads served by Google. Google and its partners may use cookies to serve ads based on your visits; you can opt out of personalized ads in Google Ads Settings.',
      pv_s4c: '<b>Cloudflare / Aliyun</b>: provide CDN acceleration and hosting for this site.',
      pv_s4d: '<b>Translation &amp; QR code</b>: on an app detail page, if your interface language differs from the app\'s original language, this site calls the Google Translate / MyMemory API to translate the description on the fly; the share QR code is generated by api.qrserver.com. These requests are sent only from your browser when you view the detail page, and this site stores none of the text or links.',
      pv_s5h: '5. Data security',
      pv_s5: 'This site enforces HTTPS for all traffic and provides no channel for uploading user data.',
      pv_s6h: '6. Minors',
      pv_s6: 'This site does not knowingly collect any data from minors.',
      pv_s7h: '7. Updates to this policy',
      pv_s7: 'If this policy is revised, it will be published on this page with an updated "Last updated" date. Continued use of the site constitutes acceptance of the revised policy.',
      pv_s8h: '8. Contact us',
      pv_s8: "If you have any questions or suggestions about this policy, feel free to reach us via the operator's blog.",
      pv_s9h: '9. Your rights',
      pv_s9: 'You have rights to access, correct and delete your personal information. Since this site stores no personal information and has no account system, no action is usually required. If you wish to query or delete server access logs related to this site held by our hosting/CDN providers, contact us via the details below and we will cooperate within reasonable limits.',
      pv_s10h: '10. Data retention',
      pv_s10: 'Server access logs are retained by our hosting and CDN providers under their own policies, solely for security and essential operational audit, for no longer than necessary. The localStorage preferences on your device are removed as soon as you clear your browser data.',
      pv_updated: 'Last updated: 2026-10-20',
      tm_badge: '📋 Terms of Use',
      tm_h1: 'Terms of Use',
      tm_lead: 'By accessing or using Apple Freebie Radar ("this site"), you agree to these terms. If you do not agree, please stop using the site.',
      tm_s1h: '1. Nature of the service',
      tm_s1: "This site is a free information aggregator that automatically compiles App Store (China / US) price changes via Apple's official public APIs, for personal reference only.",
      tm_s2h: '2. Accuracy of information',
      tm_s2: 'Freebie and deal events are set by app developers and may change at any time. We strive for timely, accurate data but do not guarantee real-time correctness — <b>always rely on what the App Store actually shows</b>.',
      tm_s3h: '3. Unofficial declaration',
      tm_s3: 'This site is independent and has no affiliation or partnership with Apple Inc. or its subsidiaries. App Store, iPhone and related trademarks belong to Apple Inc.',
      tm_s4h: '4. Intellectual property',
      tm_s4: "App names, icons and developer info belong to their respective owners and are cited for informational purposes only. This site's original text and design are copyrighted; reproduction, mirroring or bulk scraping without written permission is prohibited.",
      tm_s5h: '5. Advertising',
      tm_s5: "This site displays ads (e.g., Google AdSense) to sustain operations. Ad content is the responsibility of advertisers, does not represent this site's views, and is not warranted by this site.",
      tm_s6h: '6. Limitation of liability',
      tm_s6: 'To the maximum extent permitted by applicable law, this site is not liable for any direct or indirect losses arising from the use of or reliance on its information (including but not limited to mistaken purchases or missed promotions).',
      tm_s7h: '7. Changes to these terms',
      tm_s7: 'These terms may be revised at any time and will be published on this page. Continued use after revision constitutes acceptance of the new terms.',
      tm_s8h: '8. Governing law and dispute resolution',
      tm_s8: 'These terms are governed by the laws of the People’s Republic of China (excluding conflict-of-law rules). Any dispute arising from the use of this site shall first be resolved through friendly negotiation; if negotiation fails, either party may bring a lawsuit in the competent court located in the place where the operator is based.',
      tm_updated: 'Last updated: 2026-10-20',
      nf_badge: '🧭 Page Not Found',
      nf_h1: '404',
      nf_lead: 'The page you are looking for does not exist, or the content has been moved or removed.',
      nf_tip: 'You can try one of these:',
      nf_home: 'Back to Home',
      nf_about: 'About this site',
      nf_updated: 'Last updated: 2026-10-21'
    }
  };

  var CURRENT_LANG = 'zh';
  var state = { search: '', genre: '' };        // 筛选状态
  var currentData = { free: [], deals: [], iap: [] };  // 当前区已加载数据（含内购限免）
  var iapLoaded = false;   // 内购数据是否已加载（未加载前不渲染，避免覆盖「加载中…」）
  var iapNoData = false;   // 该区是否无内购数据（由 loadIap 的 no-data 分支处理）

  // ===== 地区配置 =====
  // 数据文件路径用【相对路径】data/...，配合各页 <base href="/">：
  // 首页在 / 下、详情页在 /app/ 下都能正确解析为 /data/...，避免「详情页相对路径 404」导致推荐区消失。
  var REGIONS = {
    cn: { file: 'data/free-today-cn.json', label: '中国区', label_en: 'China' },
    us: { file: 'data/free-today-us.json', label: '美国区', label_en: 'United States' }
  };
  // App Store 中文分类 → 英文（数据里 genre 存的是中文，英文界面显示时转换）
  var GENRE_EN = {
    '工具': 'Utilities', '健康健美': 'Health & Fitness', '旅游': 'Travel', '教育': 'Education',
    '游戏': 'Games', '财务': 'Finance', '摄影与录像': 'Photo & Video', '效率': 'Productivity',
    '社交': 'Social Networking', '音乐': 'Music', '娱乐': 'Entertainment', '生活': 'Lifestyle',
    '新闻': 'News', '购物': 'Shopping', '图书': 'Books', '美食佳饮': 'Food & Drink',
    '导航': 'Navigation', '商务': 'Business', '天气': 'Weather', '体育': 'Sports',
    '参考资料': 'Reference', '医疗': 'Medical', '商品指南': 'Catalogs', '杂志报刊': 'Magazines & Newspapers',
    '开发者工具': 'Developer Tools', '图形和设计': 'Graphics & Design', '公用程序': 'Utilities'
  };
  function genreLabel(g) {
    if (!g) return g;
    return (CURRENT_LANG === 'en' && GENRE_EN[g]) ? GENRE_EN[g] : g;
  }
  var REGION_KEY = 'freebie-region';
  var LANG_KEY = 'freebie-lang';
  var THEME_KEY = 'freebie-theme';

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }

  // ===== 语言 =====
  function getLang() {
    var s = lsGet(LANG_KEY);
    return (s === 'en' || s === 'zh') ? s : 'zh';
  }
  function applyLang(lang) {
    CURRENT_LANG = I18N[lang] ? lang : 'zh';
    var dict = I18N[CURRENT_LANG];
    document.documentElement.lang = CURRENT_LANG === 'en' ? 'en' : 'zh-CN';
    var nodes = document.querySelectorAll('[data-i18n]');
    for (var i = 0; i < nodes.length; i++) {
      var key = nodes[i].getAttribute('data-i18n');
      if (dict[key] != null) nodes[i].innerHTML = dict[key];
    }
    var phNodes = document.querySelectorAll('[data-i18n-ph]');
    for (var j = 0; j < phNodes.length; j++) {
      var pk = phNodes[j].getAttribute('data-i18n-ph');
      if (dict[pk] != null) phNodes[j].setAttribute('placeholder', dict[pk]);
    }
    // 品牌名按域名 + 语言统一由 applyBrand() 处理（见该函数），此处不再重复替换
    applyBrand();   // 让 logo / 页脚 / 标题 在切语言时同步为对应语言品牌名
    var bt = document.getElementById('backTop');   // 返回顶部按钮（JS 注入，跟随语言）
    if (bt) bt.setAttribute('aria-label', dict.back_top);
    var y = document.getElementById('year');
    if (y) y.textContent = new Date().getFullYear();
    var lb = document.getElementById('langBtn');
    if (lb) {
      var ll = document.getElementById('langLabel');
      var tgt = CURRENT_LANG === 'en' ? '中文' : 'EN';   // 按钮显示「点击后切换到的语言」
      if (ll) ll.textContent = tgt; else lb.textContent = tgt;
    }
    var allOpt = document.querySelector('#genreFilter option[value=""]');
    if (allOpt) allOpt.textContent = dict.genre_all;
    var og = document.querySelector('meta[property="og:locale"]');
    if (og) og.setAttribute('content', CURRENT_LANG === 'en' ? 'en' : 'zh_CN');
  }

  // ===== 主题 =====
  function systemPrefersDark() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }
  function isDarkNow() {
    var t = document.documentElement.dataset.theme;
    if (t === 'dark') return true;
    if (t === 'light') return false;
    return systemPrefersDark();
  }
  function applyTheme(theme) {
    if (theme === 'dark') document.documentElement.dataset.theme = 'dark';
    else if (theme === 'light') document.documentElement.dataset.theme = 'light';
    else delete document.documentElement.dataset.theme; // 跟随系统
    var dark = isDarkNow();
    var tb = document.getElementById('themeBtn');
    if (tb) {
      tb.setAttribute('aria-label', dark ? '切换浅色模式' : '切换深色模式');
      tb.setAttribute('aria-pressed', dark ? 'true' : 'false');
    }
  }
  function getTheme() { return lsGet(THEME_KEY); }

  // ===== 渲染辅助 =====
  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function debounce(fn, ms) {
    var t;
    return function () {
      var a = arguments, c = this;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(c, a); }, ms);
    };
  }

  // 从格式化价格串（如 "¥98.00" / "$9.99" / "免费"）中提取数值；免费/无法解析返回 null
  function parsePrice(s) {
    if (s == null) return null;
    var cleaned = String(s).replace(/[^0-9.,]/g, '').replace(/,/g, '');
    if (cleaned === '') return null;
    var v = parseFloat(cleaned);
    return isNaN(v) ? null : v;
  }

  // 聚合金额格式化：用地区货币符号 + 千分位、取整（用于「今日可省」大数展示）
  function formatMoney(country, v) {
    var sym = country === 'us' ? '$' : '¥';
    return sym + Math.round(v || 0).toLocaleString('en-US');
  }

  // 把相对站根的页路径（如 "app/cn-123.html"）解析为最终跳转地址。
  // 优先用 <base> 的 href（子路径部署时指向 /freebie/），否则退回 origin 根——
  // 这样即便详情页（/app/ 目录下）缺少 <base> 兜底，也不会叠成 /app/app/... 导致 404。
  function resolvePageUrl(p) {
    if (!p) return p;
    var b = document.querySelector('base');
    var root = (b && b.getAttribute('href')) || (location.origin + '/');
    if (root.slice(-1) !== '/') root += '/';
    return root + String(p).replace(/^\//, '');
  }

  function appCard(app, kind) {
    var dict = I18N[CURRENT_LANG];
    var card = app.page ? el('a', 'card') : el('div', 'card');
    if (app.page) {
      card.href = resolvePageUrl(app.page);
      card.setAttribute('aria-label', (app.name || '') + ' · ' + dict.card_store);
    }
    if (app.icon) {
      var img = el('img');
      img.src = app.icon;
      img.alt = app.name || 'app';
      img.loading = 'lazy';
      card.appendChild(img);
    } else {
      card.appendChild(el('div', null, '📱'));
    }
    var info = el('div', 'info');
    var nameRow = el('div', 'name-row');
    nameRow.appendChild(el('span', 'name', esc(app.name || '—')));
    if (app.is_new) nameRow.appendChild(el('span', 'new-badge', esc(dict.badge_new)));
    info.appendChild(nameRow);
    info.appendChild(el('div', 'dev', esc(app.dev || '')));
    if (app.genre) info.appendChild(el('div', 'genre', esc(app.genre)));
    // 评分行：★ 分数 + 「含内购 / 纯买断」徽章（徽章放这一行而非名称行——
    // 名称行右侧被 NEW 徽章和长名称挤占，且橙色徽章会与橙色评分星撞色）。
    // 本体限免（free）与特价（deal）都带徽章；has_iap 由后端探测
    // （data/iap-presence-*.json）给出，缺失时不显示徽章（不把「未知」误标成
    // 「纯买断」）。
    var ratingRow = el('div', 'rating');
    if (app.rating && app.rating > 0) {
      ratingRow.textContent = '★ ' + (Math.round(app.rating * 10) / 10).toFixed(1);
    } else {
      ratingRow.className = 'rating norate';
      ratingRow.textContent = dict.no_rating;
    }
    if ((kind === 'free' || kind === 'deal') && typeof app.has_iap === 'boolean') {
      ratingRow.appendChild(el('span', app.has_iap ? 'iap-badge' : 'pure-badge',
        esc(app.has_iap ? dict.badge_iap : dict.badge_pure)));
    }
    info.appendChild(ratingRow);
    var price = el('div', 'price');
    if (app.normal) price.appendChild(el('span', 'old', esc(app.normal)));
    var newCls = kind === 'free' ? 'new free' : 'new deal';
    // 限免标签必须用当前语言的文案（dict.card_free_price），不能用后端烤进 JSON 的
    // app.current —— 那个是按「区域」写死的（cn='免费' / us='Free'），
    // 于是英文站看国区卡片显示中文「免费」、中文站看美区卡片显示英文「Free」。
    // 特价卡仍用 app.current（真实价格数字，货币符号随区域正确）。
    var newText = kind === 'free' ? dict.card_free_price : (app.current || '');
    price.appendChild(el('span', newCls, esc(newText)));
    info.appendChild(price);
    card.appendChild(info);
    // 卡片整体可点：用 <a> 直出链接（键盘 / 读屏 / 搜索引擎均可访问）；无独立页时退化为 div + click
    card.classList.add('card-click');
    if (!app.page) {
      card.addEventListener('click', function () {
        if (app.page) location.href = resolvePageUrl(app.page);
      });
    }
    return card;
  }

  function renderList(containerId, data, kind, emptyText) {
    var box = document.getElementById(containerId);
    if (!box) return;   // 非首页（关于/隐私/条款页）无列表容器，直接跳过
    box.innerHTML = '';
    if (!data || data.length === 0) {
      box.appendChild(el('div', 'empty', emptyText));
      return;
    }
    var grid = el('div', 'grid');
    data.forEach(function (a, i) {
      grid.appendChild(appCard(a, kind));
    });
    box.appendChild(grid);
    // 列表中部广告位已交由 Auto Ads（页面级自动广告）托管，不再手动插入。
  }

  // ===== 内购限免（P2，已上线 main）=====
  // 数据源：data/iap-free-{region}.json（真·限免事件，付费→0 跳变，已排除永久免费）
  //        data/iap-current-free-{region}.json（当前所有免费内购）
  var lastAppSaved = 0;   // 本体限免/特价的可省金额（load 时算好，loadIap 追加 IAP 部分）
  function iapCard(it, region, isEvent) {
    var dict = I18N[CURRENT_LANG];
    var storeUrl = it.url || ('https://apps.apple.com/' + region + '/app/id' + it.app_id);
    var card = el('a', 'card');
    if (it.page) {
      card.href = resolvePageUrl(it.page);   // 站内独立详情页（与本体限免卡片一致）
    } else {
      card.href = storeUrl;                  // 无独立页（无评分等）→ 回退 App Store 外链
      card.target = '_blank';
      card.rel = 'noopener';
    }
    card.setAttribute('aria-label', (it.app_name || '') + ' · ' + (it.iap || '') + ' · ' + dict.card_store);
    if (it.icon) {
      var img = el('img');
      img.src = it.icon;
      img.alt = it.app_name || 'app';
      img.loading = 'lazy';
      img.onerror = function () {           // 图标加载失败 → 退回 📱 占位（与本体卡片一致）
        var d = el('div', 'iap-ico', '📱');
        if (img.parentNode) img.parentNode.replaceChild(d, img);
      };
      card.appendChild(img);
    } else {
      card.appendChild(el('div', 'iap-ico', '📱'));
    }
    var info = el('div', 'info');
    var nameRow = el('div', 'name-row');
    nameRow.appendChild(el('span', 'name', esc(it.app_name || '—')));
    if (isEvent && it.days_free === 0) nameRow.appendChild(el('span', 'new-badge', esc(dict.badge_new)));
    info.appendChild(nameRow);
    info.appendChild(el('div', 'dev', esc(it.dev || '')));            // 开发者
    if (it.genre) info.appendChild(el('div', 'genre', esc(it.genre)));  // 分类标签
    if (it.rating && it.rating > 0) {
      info.appendChild(el('div', 'rating', '★ ' + (Math.round(it.rating * 10) / 10).toFixed(1)));
    } else {
      info.appendChild(el('div', 'rating norate', esc(dict.no_rating)));
    }
    // 末行：内购项名 + 免费时长/原价（绿色「免费」价格行已去掉；🎮 图标已按用户要求移除）
    var meta;
    if (isEvent && it.days_free != null) {
      meta = esc(it.iap || '') + ' · ' +
        (it.days_free === 0
          ? dict.iap_today
          : dict.iap_days + ' ' + it.days_free + ' ' + (CURRENT_LANG === 'en' ? 'days' : '天')) +
        (it.last_paid_price ? (' · ' + dict.iap_original + ' ' + esc(it.last_paid_price)) : '');
    } else {
      meta = esc(it.iap || '') + (it.permanent_free ? (' · ' + dict.iap_perm_tag) : (' · ' + dict.iap_cur_free));
    }
    info.appendChild(el('div', 'dev', meta));
    card.appendChild(info);
    return card;
  }

  function loadIap(region) {
    var dict = I18N[CURRENT_LANG];
    var box = document.getElementById('iapFreeList');
    if (!box) return;   // 非首页无容器则跳过
    var fUrl = resolvePageUrl('data/iap-free-' + region + '.json');
    var cUrl = resolvePageUrl('data/iap-current-free-' + region + '.json');
    Promise.all([
      fetch(fUrl, { cache: 'no-cache' }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }),
      fetch(cUrl, { cache: 'no-cache' }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; })
    ]).then(function (res) {
      var evData = res[0], curData = res[1];
      if (!evData && !curData) {
        box.innerHTML = ''; box.appendChild(el('div', 'empty', dict.iap_nodata));
        var si0 = document.getElementById('statIap'); if (si0) si0.textContent = '0';
        var ss0 = document.getElementById('statSaved');
        if (ss0) ss0.textContent = formatMoney(region, lastAppSaved);   // 无 IAP 数据 → 回退本体金额
        currentData.iap = [];
        iapNoData = true;
        iapLoaded = true;
        return;
      }
      var events = ((evData && evData.events) || []).filter(function (e) { return e.rating !== 0; });
      var curItems = ((curData && curData.items) || []).filter(function (it) { return it.rating !== 0; });
      var evKeys = {};
      events.forEach(function (e) { evKeys[e.app_id + '::' + e.iap] = true; });
      var curNonPerm = curItems.filter(function (it) { return !it.permanent_free; });
      var feed = events.concat(curNonPerm.filter(function (it) { return !evKeys[it.app_id + '::' + it.iap]; }));
      // 标记每条是否为「限免事件」（用于卡片角标），供 renderIapFiltered 复用
      feed.forEach(function (it) { it.__isEvent = !!evKeys[it.app_id + '::' + it.iap]; });
      // 计算已免费天数（0 = 今天才限免，与 days_free 同一口径）：事件用 days_free，
      // current 条目用 since 日期换算；供排序「NEW 最先、从新到旧」
      var nowMs = Date.now();
      feed.forEach(function (it) {
        if (it.__isEvent) { it.__days = (it.days_free != null ? it.days_free : 999); return; }
        var t = it.since ? Date.parse(it.since) : NaN;
        it.__days = isNaN(t) ? 999 : Math.max(0, Math.floor((nowMs - t) / 864e5));
      });
      feed.sort(function (a, b) {
        return a.__days - b.__days || (b.rating || 0) - (a.rating || 0) ||
               (a.app_name || '').localeCompare(b.app_name || '');
      });
      currentData.iap = feed;
      iapNoData = false;
      iapLoaded = true;
      // 内购原价计入「今日可省」（基于全量 feed，不随搜索变化；与本体限免/特价累加，切区时由 load() 重置本体部分）
      var iapSaved = 0;
      feed.forEach(function (it) {
        if (it.last_paid_price) { var p = parsePrice(it.last_paid_price); if (p) iapSaved += p; }
      });
      var ss = document.getElementById('statSaved');
      if (ss) ss.textContent = formatMoney(region, lastAppSaved + iapSaved);
      // 渲染交给 renderIapFiltered：统一应用当前的搜索/分类筛选（与本体/特价列表行为一致）
      renderIapFiltered();
    });
  }

  // 内购限免列表的筛选（搜索 + 分类）：与 filterApps 行为一致，避免搜索时内购区不跟着过滤
  function filterIap(list) {
    if (!list || !list.length) return [];
    var q = state.search.trim().toLowerCase();
    return list.filter(function (it) {
      if (state.genre && it.genre !== state.genre) return false;
      if (q) {
        var hay = ((it.app_name || '') + ' ' + (it.dev || '') + ' ' + (it.genre || '') + ' ' + (it.iap || '')).toLowerCase();
        if (hay.indexOf(q) === -1) return false;
      }
      return true;
    });
  }

  // 按当前筛选渲染内购限免列表（搜索/分类变化时由 renderFiltered 调用；数据加载完成由 loadIap 调用）
  function renderIapFiltered() {
    var box = document.getElementById('iapFreeList');
    if (!box) return;                       // 非首页无容器则跳过
    if (!iapLoaded) return;                 // 数据尚未加载，保留「加载中…」，避免闪烁
    if (iapNoData) return;                  // 无数据分支由 loadIap 直接渲染，不覆盖
    var dict = I18N[CURRENT_LANG];
    var feed = filterIap(currentData.iap);
    var countEl = document.getElementById('iapFreeCount');
    if (countEl) countEl.textContent = feed.length;
    var si = document.getElementById('statIap');   // 统计条「内购限免」格同步筛选后条数
    if (si) si.textContent = feed.length;
    box.innerHTML = '';
    if (feed.length === 0) {
      // 区分「该区真没有任何内购数据」与「被当前筛选过滤空」：前者提示累积中，后者提示无匹配
      box.appendChild(el('div', 'empty', currentData.iap.length === 0 ? dict.iap_empty : dict.filter_empty));
      return;
    }
    var grid = el('div', 'grid');
    feed.forEach(function (it) {
      grid.appendChild(iapCard(it, getRegion(), it.__isEvent));
    });
    box.appendChild(grid);
  }

  // 注：原列表中部手动广告逻辑已移除，中部广告改由 Google 自动广告补充。

  // ===== 筛选 =====
  // 计算条目已处于当前状态（限免/现价）的天数：series 为每日末价序列（旧→新，末位=今天）。
  // 限免数末尾连续 0 的个数；特价数末尾连续等于现价的个数。1 = 今天刚触发（NEW），越大越旧。
  function stateDays(a) {
    var s = a.series || [];
    if (!s.length) return a.is_new ? 1 : 999;   // 无历史数据：新条目当 1 天，其余排末尾
    var cur = a.type === 'free' ? 0 : (parsePrice(a.current) || 0);
    var n = 0;
    for (var i = s.length - 1; i >= 0; i--) {
      var v = s[i] || 0;
      if (Math.abs(v - cur) < 0.005) n++; else break;
    }
    return Math.max(n, 1);
  }

  // 列表排序：NEW（今天刚触发）最先，其余按已持续天数从新到旧，再按评分
  function sortApps(list) {
    return (list || []).slice().sort(function (a, b) {
      return (b.is_new ? 1 : 0) - (a.is_new ? 1 : 0) ||
             stateDays(a) - stateDays(b) ||
             (b.rating || 0) - (a.rating || 0) ||
             (a.name || '').localeCompare(b.name || '');
    });
  }

  function filterApps(list) {
    if (!list || !list.length) return [];
    var q = state.search.trim().toLowerCase();
    return list.filter(function (a) {
      if (state.genre && a.genre !== state.genre) return false;
      if (q) {
        var hay = ((a.name || '') + ' ' + (a.dev || '') + ' ' + (a.genre || '')).toLowerCase();
        if (hay.indexOf(q) === -1) return false;
      }
      return true;
    });
  }

  function fillGenres() {
    var sel = document.getElementById('genreFilter');
    if (!sel) return;
    var set = {};
    currentData.free.concat(currentData.deals).forEach(function (a) { if (a.genre) set[a.genre] = 1; });
    var genres = Object.keys(set).sort();
    var keep = sel.querySelector('option[value=""]');
    sel.innerHTML = '';
    if (keep) sel.appendChild(keep);
    genres.forEach(function (g) {
      var o = el('option', null, esc(genreLabel(g)));
      o.value = g;
      sel.appendChild(o);
    });
    if (state.genre && !set[state.genre]) state.genre = ''; // 当前区无此分类则重置
    sel.value = state.genre;
  }

  function renderFiltered() {
    var dict = I18N[CURRENT_LANG];
    var free = sortApps(filterApps(currentData.free));
    var deals = sortApps(filterApps(currentData.deals));
    var freeEmpty = currentData.free.length === 0 ? dict.free_empty : dict.filter_empty;
    var dealEmpty = currentData.deals.length === 0 ? dict.deal_empty : dict.filter_empty;
    renderList('freeList', free, 'free', freeEmpty);
    renderList('dealList', deals, 'deal', dealEmpty);
    renderIapFiltered();   // 内购限免同步受搜索/分类筛选影响（与本体、特价列表一致）
  }

  function showError(region) {
    var dict = I18N[CURRENT_LANG];
    ['freeList', 'dealList'].forEach(function (id) {
      var b = document.getElementById(id);
      if (b) b.innerHTML = '<div class="empty">' + esc(dict.err_box) + '</div>';
    });
    var dl = document.getElementById('dateLine');
    if (dl) dl.textContent = dict.err_line;
    var sf = document.getElementById('statFree'); if (sf) sf.textContent = '0';
    var sd = document.getElementById('statDeal'); if (sd) sd.textContent = '0';
    var si = document.getElementById('statIap'); if (si) si.textContent = '0';
    var ss = document.getElementById('statSaved'); if (ss) ss.textContent = formatMoney(region || 'cn', 0);
  }

  function load(region) {
    var meta = REGIONS[region];
    if (!meta) region = 'cn', meta = REGIONS.cn;

    var dict = I18N[CURRENT_LANG];
    var btns = document.querySelectorAll('#regionSwitch .region-btn');
    for (var i = 0; i < btns.length; i++) {
      var on = btns[i].getAttribute('data-region') === region;
      btns[i].classList.toggle('active', on);
      btns[i].setAttribute('aria-pressed', on ? 'true' : 'false');
    }

    fetch(resolvePageUrl(meta.file), { cache: 'no-cache' })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (d) {
        var dl = document.getElementById('dateLine');
        if (dl) {
          var stamp = d.generated_at ? d.generated_at + ' UTC' : (d.date || '—');
          dl.textContent = dict.date_prefix + stamp;
        }
        var free = d.freebies || [];
        var deals = d.deals || [];
        currentData.free = free;
        currentData.deals = deals;
        var fc = document.getElementById('freeCount'); if (fc) fc.textContent = free.length;
        var dc = document.getElementById('dealCount'); if (dc) dc.textContent = deals.length;
        // 统计条：限免/特价条数 + 今日可省总额（限免按原价计，特价按差额计）
        var sf = document.getElementById('statFree'); if (sf) sf.textContent = free.length;
        var sd = document.getElementById('statDeal'); if (sd) sd.textContent = deals.length;
        var saved = 0;
        free.forEach(function (a) { var p = parsePrice(a.normal); if (p) saved += p; });
        deals.forEach(function (a) {
          var anc = parsePrice(a.normal), cur = parsePrice(a.current);
          if (anc != null && cur != null) saved += (anc - cur);
          else if (anc != null) saved += anc;
        });
        lastAppSaved = saved;   // 本体部分可省金额（IAP 数据到账后在此基础上累加，见 loadIap）
        var ss = document.getElementById('statSaved'); if (ss) ss.textContent = formatMoney(region, saved);
        fillGenres();
        renderFiltered();
        loadIap(region);   // 内购限免：双区切换联动
        // 独立页兜底：详情(iTunes)比数据先返回时，推荐区块曾渲染为空，这里补一次
        if (detailApp) {
          var ex = document.getElementById('dtExtra');
          if (ex && !ex.querySelector('.dt-related')) renderRecommend(detailApp, ex);
        }
      })
      .catch(function () { showError(region); });
  }

  function bindControls() {
    var langBtn = document.getElementById('langBtn');
    if (langBtn) langBtn.addEventListener('click', function () {
      var next = (CURRENT_LANG === 'en') ? 'zh' : 'en';
      lsSet(LANG_KEY, next);
      applyLang(next);
      // 独立页模式：语言切换后重渲染详情（文案随语言变）
      if (window.__APP__ && document.getElementById('detailBody')) {
        renderDetail(window.__APP__, document.getElementById('detailBody'), null);
        return;
      }
      load(getRegion());
    });
    var themeBtn = document.getElementById('themeBtn');
    if (themeBtn) themeBtn.addEventListener('click', function () {
      var next = isDarkNow() ? 'light' : 'dark';
      lsSet(THEME_KEY, next);
      applyTheme(next);
    });

    var rb = document.querySelectorAll('#regionSwitch .region-btn');
    for (var i = 0; i < rb.length; i++) {
      rb[i].addEventListener('click', function () {
        var r = this.getAttribute('data-region');
        if (r === getRegion()) return;
        lsSet(REGION_KEY, r);
        load(r);
      });
    }

    // 搜索 + 分类筛选（纯前端过滤已加载数据，不发网请求）
    var si = document.getElementById('searchInput');
    if (si) {
      var runFilter = debounce(function () { renderFiltered(); }, 160);
      si.addEventListener('input', function () {
        state.search = this.value;
        runFilter();
      });
    }
    var gf = document.getElementById('genreFilter');
    if (gf) gf.addEventListener('change', function () {
      state.genre = this.value;
      renderFiltered();
    });

    // 搜索图标 → 弹出搜索/分类面板（图标位于语言胶囊前）
    var searchTrigger = document.getElementById('searchTrigger');
    var searchPop = document.getElementById('searchPop');
    if (searchTrigger && searchPop) {
      searchTrigger.addEventListener('click', function (e) {
        e.stopPropagation();
        if (searchPop.hasAttribute('hidden')) {
          searchPop.removeAttribute('hidden');
          searchTrigger.setAttribute('aria-expanded', 'true');
          var si = document.getElementById('searchInput');
          if (si) si.focus();
        } else {
          searchPop.setAttribute('hidden', '');
          searchTrigger.setAttribute('aria-expanded', 'false');
        }
      });
      document.addEventListener('click', function (e) {
        if (!searchPop.hasAttribute('hidden') && e.target !== searchTrigger && !searchPop.contains(e.target)) {
          searchPop.setAttribute('hidden', '');
          searchTrigger.setAttribute('aria-expanded', 'false');
        }
      });
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && !searchPop.hasAttribute('hidden')) {
          searchPop.setAttribute('hidden', '');
          searchTrigger.setAttribute('aria-expanded', 'false');
          searchTrigger.focus();
        }
      });
    }

    // 点击站名「苹果限免雷达」：首页=刷新数据；关于页=回首页
    var logo = document.getElementById('logoHome');
    if (logo) logo.addEventListener('click', function () {
      if (!document.getElementById('freeList')) {
        location.href = resolvePageUrl('index.html');
        return;
      }
      var dict = I18N[CURRENT_LANG];
      var dl = document.getElementById('dateLine');
      if (dl) dl.textContent = dict.loading;
      ['freeList', 'dealList'].forEach(function (id) {
        var b = document.getElementById(id);
        if (b) b.innerHTML = '<div class="loading">' + dict.loading + '</div>';
      });
      load(getRegion());
    });
  }

  function getRegion() {
    var saved = lsGet(REGION_KEY);
    if (saved && REGIONS[saved]) return saved;
    return 'cn';
  }

  // 站点品牌：按域名 + 语言区分（同仓库部署到 limzero / nickyam 两套域名）
  function brandName() {
    var h = location.hostname;
    var en = CURRENT_LANG === 'en';
    if (h.indexOf('limzero') >= 0) return en ? 'Lim Freebies' : '极零限免';
    if (h.indexOf('nickyam') >= 0) return en ? 'Yam Freebies' : '涯木限免';
    // 本地预览（localhost/127.0.0.1）按主镜像品牌显示，预览即所见即所得
    if (h === 'localhost' || h === '127.0.0.1' || h === '') return en ? 'Lim Freebies' : '极零限免';
    return en ? 'Apple Freebie Radar' : '苹果限免雷达';
  }
  var lastBrand = null;

  function setMeta(key, val) {
    var m = document.querySelector('meta[property="' + key + '"]') ||
            document.querySelector('meta[name="' + key + '"]');
    if (!m) {
      m = document.createElement('meta');
      m.setAttribute('property', key);
      document.head.appendChild(m);
    }
    m.setAttribute('content', val);
  }

  // 把品牌名写进可见文案 + SEO 元信息（按当前域名自动取值，兼容首页/关于页）
  function applyBrand() {
    var name = brandName();
    function swap(s) {
      if (!s) return s;
      if (lastBrand) s = s.split(lastBrand).join(name);
      return s.split('苹果限免雷达').join(name).split('Apple Freebie Radar').join(name);
    }
    var url = location.origin + location.pathname;
    var logo = document.getElementById('siteLogo');
    if (logo) logo.textContent = name;
    var fs = document.getElementById('footerSiteName');
    if (fs) fs.textContent = name;
    document.title = swap(document.title || '');
    ['og:site_name', 'og:title', 'twitter:title', 'og:description', 'twitter:description', 'description'].forEach(function (key) {
      var m = document.querySelector('meta[property="' + key + '"]') ||
              document.querySelector('meta[name="' + key + '"]');
      if (!m) return;
      m.setAttribute('content', swap(m.getAttribute('content') || ''));
    });
    var canon = document.querySelector('link[rel="canonical"]');
    if (canon) canon.setAttribute('href', url);
    setMeta('og:url', url);
    // 正文里带品牌名的 data-i18n 节点（页脚版权、hero 文案等）也要按域名替换，
    // logo / 标题 / 页脚名之外的地方不能漏（#8 把这部分从 applyLang 收拢到此处）
    var inodes = document.querySelectorAll('[data-i18n]');
    for (var i = 0; i < inodes.length; i++) {
      inodes[i].innerHTML = swap(inodes[i].innerHTML || '');
    }
      try {
        var ld = document.querySelector('script[type="application/ld+json"]');
        if (ld) {
          var o = JSON.parse(ld.textContent);
          // 独立页的 JSON-LD 是 App 级 SoftwareApplication，不能被站点品牌覆盖
          if (!window.__APP__ && o.name) o.name = name;
          o.url = url;
          ld.textContent = JSON.stringify(o);
        }
      } catch (e) {}
    lastBrand = name;
  }

  // ===== 应用详情浮层 =====
  var detailSetup = false;
  function curSym(region) { return region === 'us' ? '$' : '¥'; }
  function fmtCur(currency, price) {
    if (price == null) return '—';
    if (price === 0) return I18N[CURRENT_LANG].card_free_price;
    var sym = currency === 'USD' ? '$' : (currency === 'CNY' ? '¥' : (currency || ''));
    return sym + (Math.round(price * 100) / 100).toFixed(2);
  }
  function fmtSize(bytes) {
    if (!bytes) return '';
    var mb = bytes / (1024 * 1024);
    return mb >= 1024 ? (mb / 1024).toFixed(2) + ' GB' : mb.toFixed(1) + ' MB';
  }

  var jsonpSeq = 0;
  // JSONP 拉取（iTunes lookup 原生支持 callback=，绕开 CORS，兼容性最好）
  // 返回：结果对象 / 'NOT_IN_STORE'（接口通但该区无此 App）/ null（网络失败）
  function fetchLookup(id, country) {
    return new Promise(function (resolve) {
      var lang = country === 'cn' ? 'zh_cn' : 'en_us';
      var cb = 'dtCbp' + (++jsonpSeq) + '_' + Date.now();
      var url = 'https://itunes.apple.com/lookup?id=' + encodeURIComponent(id) +
                '&country=' + country + '&entity=software&lang=' + lang + '&callback=' + cb;
      var script = document.createElement('script');
      var done = false;
      function cleanup() {
        try { delete window[cb]; } catch (e) { window[cb] = undefined; }
        if (script.parentNode) script.parentNode.removeChild(script);
      }
      window[cb] = function (data) {
        done = true;
        cleanup();
        var r = (data && data.results && data.results.length) ? data.results[0] : null;
        resolve(r || 'NOT_IN_STORE');
      };
      script.onerror = function () { if (!done) { done = true; cleanup(); resolve(null); } };
      setTimeout(function () { if (!done) { done = true; cleanup(); resolve(null); } }, 8000);
      script.src = url;
      document.head.appendChild(script);
    });
  }

  // 价格历史大图：每个节点标价格（上方）+ 日期（下方旋转，避免多节点重叠），
  // 最低价节点高亮（实心大点 + 彩色加粗价格），渐变面积 + 底部轴线。
  // viewBox 固定 760x240、等比缩放（不再 preserveAspectRatio="none" 拉伸文字）；
  // 窄屏由 .pc-wrap 提供横向滚动，保证每个日期/价格都可读。
  function priceChart(phistory, kind, region) {
    if (!phistory || phistory.length < 2) return '';
    var W = 760, H = 240, padL = 26, padR = 26, padT = 20, padB = 58;
    var pts = phistory.map(function (x) { return x.p; });
    var min = Math.min.apply(null, pts), max = Math.max.apply(null, pts);
    var range = (max - min) || 1;
    var color = kind === 'free' ? '#34c759' : '#ff9f0a';
    var sym = curSym(region);
    var n = phistory.length;
    function fmt(v) { return sym + (Math.round(v * 100) / 100); }
    function xy(i, v) {
      var x = padL + (W - padL - padR) * (i / (n - 1));
      var y = (H - padB) - (H - padT - padB) * ((v - min) / range);
      return [x, y];
    }
    var line = phistory.map(function (x, i) { var p = xy(i, x.p); return p[0].toFixed(1) + ',' + p[1].toFixed(1); }).join(' ');
    var area = 'M' + padL + ',' + (H - padB) + ' L' + line.split(' ').join(' L') + ' L' + (W - padR) + ',' + (H - padB) + ' Z';
    var minIdx = pts.indexOf(min);
    var axisY = H - padB;
    var s = '<svg class="pc-chart" viewBox="0 0 ' + W + ' ' + H + '" aria-hidden="true">';
    s += '<defs><linearGradient id="pcg" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0" stop-color="' + color + '" stop-opacity="0.16"/>' +
      '<stop offset="1" stop-color="' + color + '" stop-opacity="0.02"/></linearGradient></defs>';
    s += '<line x1="' + padL + '" y1="' + axisY + '" x2="' + (W - padR) + '" y2="' + axisY + '" stroke="var(--border)" stroke-width="1"/>';
    s += '<path d="' + area + '" fill="url(#pcg)"/>';
    s += '<polyline points="' + line + '" fill="none" stroke="' + color + '" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>';
    for (var i = 0; i < n; i++) {
      var p = xy(i, pts[i]);
      var cx = p[0].toFixed(1), cy = p[1].toFixed(1);
      var isMin = i === minIdx;
      // 圆点：最低价实心放大，其余空心
      s += '<circle cx="' + cx + '" cy="' + cy + '" r="' + (isMin ? 4.5 : 3) + '" fill="' + (isMin ? color : 'var(--surface)') + '" stroke="' + color + '" stroke-width="' + (isMin ? 2 : 1.5) + '"/>';
      // 价格：节点上方，白描边光晕保证压在面积上也可读
      s += '<text x="' + cx + '" y="' + (p[1] - 9).toFixed(1) + '" font-size="11" font-weight="' + (isMin ? '700' : '600') + '" fill="' + (isMin ? color : 'var(--ink)') + '" text-anchor="middle" style="paint-order:stroke" stroke="var(--surface)" stroke-width="3" stroke-linejoin="round">' + fmt(pts[i]) + '</text>';
      // 日期：轴下旋转 52°，text-anchor=end 让文字末端对准节点
      var d = phistory[i].d.slice(5);
      var dy = axisY + 14;
      s += '<text x="' + cx + '" y="' + dy + '" font-size="10" fill="var(--muted)" text-anchor="end" transform="rotate(-52 ' + cx + ' ' + dy + ')">' + d + '</text>';
    }
    s += '</svg>';
    return s;
  }

  // 同时期的其他限免：当区当前清单里除本 App 外的限免/特价（新触发优先、评分次之），
  // 复用首页同款卡片（自带跳独立页点击）
  function samePeriodHTML(app) {
    var dict = I18N[CURRENT_LANG];
    var pool = currentData.free.concat(currentData.deals).filter(function (a) {
      return a.id !== app.id;
    });
    if (!pool.length) return { html: '', items: [] };
    pool.sort(function (x, y) {
      return (y.is_new ? 1 : 0) - (x.is_new ? 1 : 0) || (y.rating || 0) - (x.rating || 0);
    });
    pool = pool.slice(0, 18);   // 交由 renderRecommend 随机抽 6（若这里就截到 6，洗牌后仍是同一批）
    return { html: '<div class="dt-related dt-period"><h3>' + esc(dict.dt_same_period) + '</h3><div class="grid" id="dtSameGrid"></div></div>', items: pool };
  }

  // 固定广告位 HTML 构造（仅用于顶部/头部手动位 7735913921）。
  // 说明：innerHTML 插入的 <script> 不会自动执行，所以这里只输出 <ins>，
  // 由 renderDetail 在插入 DOM 后手动 push 一次触发广告请求。
  // 其余广告位（列表中部、独立页尾部等）已交由 Auto Ads 页面级自动广告托管。
  function adSlotHTML(slot, cls) {
    return '<div class="ad-slot ' + (cls || 'dt-ad') + '">' +
      '<ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-7114121088728794" ' +
      'data-ad-slot="' + slot + '" data-ad-format="auto" data-full-width-responsive="true"></ins>' +
      '</div>';
  }
  function pushAd(container, cls) {
    var ins = container.querySelector('.' + cls + ' ins.adsbygoogle');
    if (ins) {
      try { (window.adsbygoogle = window.adsbygoogle || []).push({}); }
      catch (e) { /* 广告脚本未就绪时静默跳过，不影响正文 */ }
    }
  }

  // 「同时期的其他限免」区块（独立页最底部）。
  // 独立页里数据（free-today JSON）与 iTunes 详情是并发请求的，谁先返回不确定；
  // 若详情先到，currentData 还是空的，这里就会渲染出空区块。
  // 因此 load() 拿到数据后会再调一次本函数补渲染（内部先清掉旧区块，不会重复）。
  // 独立页尾部广告位已交由 Auto Ads 托管，本函数不再插入手动广告。
  var detailApp = null;   // 当前独立页正在展示的 App
  function renderRecommend(app, extra) {
    if (!app || !extra) return;
    // 同一页生命周期内只随机一次并缓存：详情页会先后用「iTunes 详情」和「列表数据」渲染两次，
    // 每次重新洗牌会导致推荐列表跳动。
    var picked = app.__relPicked;
    if (!picked) {
      var items;
      if (app.rel && app.rel.length) {
        items = app.rel.slice();   // 优先用生成时内联的轻量推荐，避免详情页再拉整份 JSON
      } else {
        items = samePeriodHTML(app).items;
      }
      // 随机洗牌后取前 6：避免每个详情页都显示同一批固定推荐（用户反馈"固定不合理"），
      // 每次访问都随机，但始终来自同区同期的限免/特价池，保持相关性。
      for (var i = items.length - 1; i > 0; i--) {
        var j = Math.floor(Math.random() * (i + 1));
        var t = items[i]; items[i] = items[j]; items[j] = t;
      }
      picked = items.slice(0, 6);
      if (picked.length) app.__relPicked = picked;
    }
    var box = document.createElement('div');
    box.innerHTML = '<div class="dt-related dt-period"><h3>' + esc(I18N[CURRENT_LANG].dt_same_period) +
      '</h3><div class="grid" id="dtSameGrid"></div></div>';
    var olds = extra.querySelectorAll('.dt-related');
    for (var k = 0; k < olds.length; k++) extra.removeChild(olds[k]);
    while (box.firstChild) extra.appendChild(box.firstChild);
    // 独立页尾部广告位已交由 Auto Ads 托管，不再手动插入。
    var sg = extra.querySelector('#dtSameGrid');
    if (sg) picked.forEach(function (a) { sg.appendChild(appCard(a, a.type === 'deal' ? 'deal' : 'free')); });
  }

  // 渲染详情内容（独立详情页；panel 为空表示独立页模式）
  function renderDetail(app, body, panel) {
    var dict = I18N[CURRENT_LANG];
    if (!body) return;
    if (!panel) detailApp = app;   // 独立页模式：记住当前 App，供 load() 补渲染推荐区块

    // 基础信息（无需网络，价格后续用实时 iTunes 数据覆盖）
    var ratingStr = (app.rating && app.rating > 0) ? ('★ ' + (Math.round(app.rating * 10) / 10).toFixed(1)) : '';
    var genreHref = app.genre ? resolvePageUrl('index.html?genre=' + encodeURIComponent(app.genre) + '&region=' + esc(app.region || 'cn')) : '';
    var isIapPage = app.type === 'iap';   // IAP 限免详情页：头部「免费」指内购而非 App 本体
    var base = '<div class="dt-head">' +
      (app.icon ? '<img class="dt-icon" src="' + esc(app.icon) + '" alt=""/>' : '<div class="dt-icon dt-ic">📱</div>') +
      '<div class="dt-hinfo"><h2 class="dt-name">' + esc(app.name || '') + '</h2>' +
      '<div class="dt-dev">' + esc(app.dev || '') + '</div>' +
      '<div class="dt-meta">' +
      (app.genre ? '<a class="dt-chip chip-link" href="' + esc(genreHref) + '" title="' + esc(dict.dt_genre_link) + '">' + esc(genreLabel(app.genre)) + '</a>' : '') +
      ((ratingStr || true) ? '<span class="dt-chip' + (ratingStr ? '' : ' norate') + '">' + esc(ratingStr ? '⭐ ' + ratingStr.replace('★ ', '') : dict.no_rating) + '</span>' : '') +
      (isIapPage && app.iap ? '<span class="dt-chip">' + esc(app.iap) + '</span>' : '') +
      // 本体限免 / 特价详情页：标明该 App 本身是否还有内购（与首页卡片徽章同源）
      (!isIapPage && (app.type === 'free' || app.type === 'deal') && typeof app.has_iap === 'boolean' ?
        '<span class="dt-chip dt-chip-' + (app.has_iap ? 'iap' : 'pure') + '">' +
        esc(app.has_iap ? dict.badge_iap : dict.badge_pure) + '</span>' : '') +
      '</div>' +
      '<div class="dt-price"><span class="dt-cur ' + ((app.type === 'free' || isIapPage) ? 'free' : 'deal') + '" id="dtPrice">' + esc((app.type === 'free' || isIapPage) ? dict.card_free_price : (app.current || '')) + '</span>' +
      (app.normal ? '<span class="dt-old" id="dtOld">' + esc(app.normal) + '</span>' : '') + '</div>' +
      '</div>' +
      '<div class="dt-side">' +
      '<button type="button" class="dt-qr-btn" id="dtQrBtn" aria-label="' + esc(dict.dt_qr_btn) + '">' +
        '<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">' +
        '<rect x="3" y="3" width="7" height="7" rx="1.2"/><rect x="14" y="3" width="7" height="7" rx="1.2"/><rect x="3" y="14" width="7" height="7" rx="1.2"/>' +
        '<path stroke-linecap="round" d="M14 14h3v3h-3zM20 14h1M14 20h1M17.5 20H21M20 17v1.5"/></svg>' +
        '<span>' + esc(dict.dt_qr_btn) + '</span></button>' +
      '<a class="dt-go-sm" href="' + esc(app.url || '#') + '" target="_blank" rel="noopener">' + esc(dict.dt_go) + '</a>' +
      '</div>' +
      '</div>' +
    // 独立页：App 头部卡片（dt-head）正下方插入固定广告位；首页弹窗内不放广告
    (panel ? '' : adSlotHTML('7735913921', 'dt-ad')) +
      '<div class="dt-section" id="dtExtra"><div class="dt-loading">' + esc(dict.dt_loading) + '</div></div>';
    body.innerHTML = base;

    // innerHTML 插入的脚本不会执行，这里手动触发一次广告请求
    if (!panel) pushAd(body, 'dt-ad');

    // 独立页面包屑
    var crumb = document.getElementById('appCrumb');
    if (crumb) crumb.textContent = (app.name || '') + (app.genre ? ' · ' + genreLabel(app.genre) : '');

    // 实时拉 iTunes：当前区（截图/介绍/版本等）+ 对区（现价对比）
    var other = app.region === 'cn' ? 'us' : 'cn';
    Promise.all([fetchLookup(app.id, app.region), fetchLookup(app.id, other)])
      .then(function (res) {
        var self = res[0], ot = res[1];
        var extra = document.getElementById('dtExtra');
        if (!extra) return;

        // 头部价格用 iTunes 实时值覆盖快照：原价划掉 + 现价/免费（已恢复原价则不划）
        // IAP 详情页跳过：头部「免费」指内购，App 本体价格在下方两区对比里看
        var pe = document.getElementById('dtPrice'), oe = document.getElementById('dtOld');
        var live = (self && typeof self.price === 'number') ? self.price : null;
        var liveCur = (self && self.currency) || null;
        var normalNum = app.normal ? parseFloat(String(app.normal).replace(/[^0-9.]/g, '')) : NaN;
        if (pe && app.type !== 'iap') {
          if (live === 0) {
            pe.textContent = dict.card_free_price; pe.className = 'dt-cur free';
            if (oe && app.normal) { oe.textContent = app.normal; oe.style.display = ''; }
          } else if (live != null) {
            if (!isNaN(normalNum) && normalNum > 0 && live >= normalNum - 0.005) {
              // 已恢复原价：现价=原价，只显示现价，不再划线
              pe.textContent = esc(fmtCur(liveCur, live)); pe.className = 'dt-cur';
              if (oe) oe.style.display = 'none';
            } else {
              pe.textContent = esc(fmtCur(liveCur, live)); pe.className = 'dt-cur deal';
              if (oe && app.normal) { oe.textContent = app.normal; oe.style.display = ''; }
            }
          }
        }

        var html = '';

        // 中美两区现价对比
        html += '<div class="dt-section"><h3>' + esc(dict.dt_cross) + '</h3><div class="dt-cross">';
        html += crossRow('🇨🇳 ' + (CURRENT_LANG === 'en' ? 'China' : '中国区'), self, app.region === 'cn');
        html += crossRow('🇺🇸 ' + (CURRENT_LANG === 'en' ? 'United States' : '美国区'), ot, app.region === 'us');
        html += '</div></div>';

        // 价格历史曲线
        var chart = priceChart(app.phistory, app.type, app.region);
        if (chart) html += '<div class="dt-section"><h3>' + esc(dict.dt_price_history) + '</h3><div class="pc-wrap">' + chart + '</div></div>';

        // 内购限免信息（type=iap 专属）
        if (app.type === 'iap') {
          html += '<div class="dt-section"><h3>' + esc(dict.dt_iap_title) + '</h3><div class="dt-metarow dt-iap-list">';
          var iapItems = (app.iap_items && app.iap_items.length) ? app.iap_items
            : [{ name: app.iap || '', last_paid_price: app.normal || '', free_since: app.free_since || '', days_free: app.days_free || 0 }];
          iapItems.forEach(function (x) {
            var line = esc(x.name || '—');
            if (x.last_paid_price && x.last_paid_price !== '—') line += '<span class="dt-dot">·</span>' + esc(dict.iap_original) + ' ' + esc(x.last_paid_price);
            line += '<span class="dt-dot">→</span><span class="free">' + esc(dict.card_free_price) + '</span>';
            if (x.free_since) line += '<span class="dt-dot">·</span>' + esc(dict.iap_days) + ' ' + esc(String(x.days_free || 0)) + (CURRENT_LANG === 'en' ? ' days' : ' 天');
            html += '<div>' + line + '</div>';
          });
          html += '</div></div>';
        }

        // 截图
        var shots = (self && self.screenshotUrls) ? self.screenshotUrls.slice(0, 6) : [];
        if (shots.length) {
          html += '<div class="dt-section"><h3>' + esc(dict.dt_screenshots) + '</h3><div class="dt-shots">';
          shots.forEach(function (s) { html += '<img src="' + esc(s) + '" alt="" loading="lazy"/>'; });
          html += '</div></div>';
        }

        // 基本信息（版本/大小/分级）
        var metaBits = [];
        if (self && self.version) metaBits.push(esc(dict.dt_ver) + ' ' + esc(self.version));
        if (self && self.fileSizeBytes) metaBits.push(esc(dict.dt_size) + ' ' + esc(fmtSize(self.fileSizeBytes)));
        if (self && self.trackContentRating) metaBits.push(esc(dict.dt_age) + ' ' + esc(self.trackContentRating));
        if (self && self.userRatingCount) metaBits.push(esc(String(self.userRatingCount)) + esc(dict.dt_rating_count));
        if (metaBits.length) html += '<div class="dt-metarow">' + metaBits.join('<span class="dt-dot">·</span>') + '</div>';

        // 介绍
        var desc = (self && self.description) ? self.description : '';
        html += '<div class="dt-section"><h3>' + esc(dict.dt_about) + '</h3>' +
          '<div class="dt-desc">' + (desc ? esc(desc).replace(/\n/g, '<br/>') : esc(dict.dt_no_desc)) + '</div></div>';

        // 同类推荐 + 同时期的其他限免（后者复用首页卡片，置于页面最底部）
        extra.innerHTML = html;
        renderRecommend(app, extra);
        // 介绍原文语言与页面语言不一致 → 自动机器翻译（段落级缓存，失败保留原文）
        var descEl = extra.querySelector('.dt-desc');
        if (descEl && desc) {
          var needTr = (CURRENT_LANG === 'en' && cjkRatio(desc) > 0.15) ||
                       (CURRENT_LANG === 'zh' && cjkRatio(desc) <= 0.15);
          if (needTr) {
            translateDesc(desc, CURRENT_LANG).then(function (r) {
              if (!r || !r.text || r.text === desc || !document.contains(descEl)) return;
              descEl.innerHTML = esc(r.text).replace(/\n/g, '<br/>');
              if (r.ok) {
                var note = document.createElement('div');
                note.className = 'dt-mt-note';
                note.textContent = I18N[CURRENT_LANG].dt_mt_note;
                descEl.appendChild(note);
              }
            });
          }
        }
        if (panel) panel.scrollTop = 0;
      })
      .catch(function () {
        var extra = document.getElementById('dtExtra');
        if (extra) extra.innerHTML = '<div class="dt-section"><div class="dt-loading">' + esc(dict.dt_loadfail) + '</div></div>';
      });
  }

  function crossRow(label, info, isCurrent) {
    var dict = I18N[CURRENT_LANG];
    var price;
    if (info === 'NOT_IN_STORE') price = esc(dict.dt_not_in);
    else if (info && typeof info.price === 'number') price = esc(fmtCur(info.currency, info.price));
    else price = '—';   // 查询失败（网络等），不误标「未上架」
    return '<div class="dt-cross-row' + (isCurrent ? ' cur' : '') + '">' +
      '<span class="dt-cr-label">' + label + (isCurrent ? ' <span class="dt-cur-tag">' + (CURRENT_LANG === 'en' ? 'current' : '当前') + '</span>' : '') + '</span>' +
      '<span class="dt-cr-price">' + price + '</span></div>';
  }

  // ===== 应用介绍自动翻译（免费接口 + localStorage 缓存 + 失败回退原文） =====
  function cjkRatio(s) {
    var cjk = (s.match(/[\u4e00-\u9fff]/g) || []).length;
    return cjk / Math.max(1, s.replace(/\s/g, '').length);
  }
  function hashStr(s) {
    var h = 5381;
    for (var i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) >>> 0;
    return h.toString(36);
  }
  function trGet(key) {
    try { var c = lsGet(key); return c ? JSON.parse(c).v : null; } catch (e) { return null; }
  }
  function trSet(key, val) {
    try { lsSet(key, JSON.stringify({ t: Date.now(), v: val })); } catch (e) {}
  }
  function translateChunk(text, sl, tl) {
    // Google 质量更好但大陆网络不可达；失败自动切 MyMemory 兜底
    var g = fetch('https://translate.googleapis.com/translate_a/single?client=gtx&sl=' + sl + '&tl=' + tl + '&dt=t&q=' + encodeURIComponent(text))
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j || !j[0]) throw new Error('bad');
        var out = j[0].map(function (seg) { return seg[0]; }).join('');
        if (!out) throw new Error('empty');
        return out;
      });
    var m = fetch('https://api.mymemory.translated.net/get?q=' + encodeURIComponent(text) + '&langpair=' + sl + '|' + tl)
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var t = j && j.responseData && j.responseData.translatedText;
        if (!t || /MYMEMORY WARNING/i.test(t)) throw new Error('bad');
        return t;
      });
    return g.catch(function () { return m; });
  }
  // 按 UTF-8 字节切分（MyMemory 免费接口单请求上限 ~500 字节），避免在多字节字符中途截断
  function splitByBytes(text, maxBytes) {
    var pieces = [], cur = '', curBytes = 0;
    for (var i = 0; i < text.length; i++) {
      var ch = text[i];
      var b = encodeURIComponent(ch).replace(/%[0-9A-F]{2}/g, 'U').length; // ASCII=1，CJK≈3
      if (curBytes + b > maxBytes && cur) { pieces.push(cur); cur = ''; curBytes = 0; }
      cur += ch; curBytes += b;
    }
    if (cur) pieces.push(cur);
    return pieces;
  }

  // 整段介绍按段落、再按字节拆分后并行翻译（带 localStorage 缓存、失败回退原文）
  function translateDesc(text, targetLang) {
    var sl = cjkRatio(text) > 0.15 ? 'zh' : 'en';
    var tl = targetLang === 'en' ? 'en' : 'zh';
    if (sl === tl) return Promise.resolve(null);
    var MAX_BYTES = 450;   // 留余量以低于 MyMemory 的 500 字节上限
    var paras = text.split('\n');
    var out = {};
    var failed = false;
    var tasks = [];
    paras.forEach(function (p, idx) {
      if (!p.trim()) return;
      splitByBytes(p, MAX_BYTES).forEach(function (seg) {
        var key = 'freebie-tr:' + tl + ':' + hashStr(seg);
        var cached = trGet(key);
        if (cached) { (out[idx] = out[idx] || []).push(cached); return; }
        tasks.push(translateChunk(seg, sl, tl).then(function (v) {
          trSet(key, v);
          (out[idx] = out[idx] || []).push(v);
        }).catch(function () {
          failed = true;
          (out[idx] = out[idx] || []).push(seg);   // 回退原文
        }));
      });
    });
    return Promise.all(tasks).then(function () {
      var result = [];
      paras.forEach(function (p, idx) { result.push((out[idx] || []).join('')); });
      return { text: result.join('\n'), ok: !failed };
    });
  }

  // 灯箱：应用截图放大 / 二维码浮层 共用（点击任意处或 Esc 关闭）
  var lbEl = null;
  function openLightbox(html) {
    if (!lbEl) {
      lbEl = document.createElement('div');
      lbEl.className = 'dt-lightbox';
      lbEl.innerHTML = '<div class="dt-lb-inner"></div>';
      lbEl.addEventListener('click', closeLightbox);
      document.body.appendChild(lbEl);
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && lbEl && !lbEl.hidden) closeLightbox();
      });
    }
    lbEl.firstChild.innerHTML = html;
    lbEl.hidden = false;
    document.body.style.overflow = 'hidden';
  }
  function closeLightbox() {
    if (!lbEl) return;
    lbEl.hidden = true;
    lbEl.firstChild.innerHTML = '';
    document.body.style.overflow = '';
  }

  // 独立页事件委托：同类推荐跳页 / 截图点击放大 / 二维码按钮弹浮层
  function setupDetailEvents() {
    if (detailSetup) return;
    detailSetup = true;
    var body = document.getElementById('detailBody');
    if (body) body.addEventListener('click', function (e) {
      // 截图放大
      var shot = e.target.closest('.dt-shots img');
      if (shot) {
        openLightbox('<img class="dt-lb-img" src="' + shot.getAttribute('src') + '" alt=""/>');
        return;
      }
      // 二维码浮层
      if (e.target.closest('#dtQrBtn')) {
        var dict = I18N[CURRENT_LANG];
        var ap = window.__APP__;
        if (ap && ap.url) {
          openLightbox('<div class="dt-lb-card">' +
            '<img src="https://api.qrserver.com/v1/create-qr-code/?size=300x300&margin=10&data=' + encodeURIComponent(ap.url) + '" alt="QR"/>' +
            '<div class="dt-lb-cap">' + esc(dict.dt_qr) + '</div>' +
            '<div class="dt-lb-hint">' + esc(dict.dt_close_hint) + '</div></div>');
        }
        return;
      }
    });
  }

  // 返回顶部（苹果风：毛玻璃圆形 + 雪佛龙箭头；滚动 400px 后淡入）
  // JS 注入而非写死 HTML：所有加载 app.js 的页面（首页/详情页）自动获得，单一信源
  function setupBackTop() {
    if (document.getElementById('backTop')) return;
    var dict = I18N[CURRENT_LANG] || I18N.zh;
    var btn = document.createElement('button');
    btn.id = 'backTop';
    btn.type = 'button';
    btn.className = 'back-top';
    btn.setAttribute('aria-label', dict.back_top);
    btn.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" ' +
      'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<path d="M6 14l6-6 6 6"/></svg>';
    btn.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    document.body.appendChild(btn);
    var ticking = false;
    window.addEventListener('scroll', function () {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () {
        btn.classList.toggle('show', (window.scrollY || window.pageYOffset || 0) > 400);
        ticking = false;
      });
    }, { passive: true });
    btn.classList.toggle('show', (window.scrollY || window.pageYOffset || 0) > 400);
  }

  function init() {
    applyTheme(getTheme());   // 主题（null=跟随系统）
    applyLang(getLang());     // 语言
    applyBrand();             // 站点品牌（域名自适应）
    bindControls();
    setupDetailEvents();      // 独立页同类推荐跳页事件
    setupBackTop();           // 返回顶部按钮（首页 + 详情页通用）
    // 独立详情页模式：页面 URL 形如 app/{region}-{id}.html，数据内联于 window.__APP__
    if (window.__APP__ && document.getElementById('detailBody')) {
      var ap = window.__APP__;
      if (!ap.rel || !ap.rel.length) load(ap.region || 'cn');  // 旧页无内联推荐时才拉整份清单
      renderDetail(ap, document.getElementById('detailBody'), null);
      return;
    }
    // 首页支持 URL 参数：/index.html?genre=工具&region=cn（独立页分类标签跳转过来）
    if (!window.__APP__ && typeof URLSearchParams === 'function') {
      var qs = new URLSearchParams(location.search);
      var qRegion = qs.get('region'), qGenre = qs.get('genre');
      if (qRegion && REGIONS[qRegion]) lsSet(REGION_KEY, qRegion);
      if (qGenre) state.genre = qGenre;
    }
    load(getRegion());        // 拉数据
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

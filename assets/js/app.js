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
      intro_li1: '每天抓取苹果<b>官方</b>全部 22 个分类的付费榜 Top100 与免费榜（去重后每区约 2000 款 App），再用苹果官方接口逐个核对实时价格；',
      intro_li2: '和你<b>历史常规价</b>做对比——只有「昨天还收费、今天变 0 元」的，才会被标记为<b>限免</b>；',
      intro_li3: '价格只是降低但没到免费的，单独归到<b>特价</b>一栏，方便比价；',
      intro_li4: '所有价格与可用性以苹果商店为准，可能随时变动，<b>下单前请务必在 App Store 内确认</b>。',
      intro_p4: '所有数据来自 Apple 公开接口，App 图标均直接引用苹果 CDN，不做转存。点击任意 App 即可跳转对应地区的 App Store 详情页。',
      sec_free: '🔓 今日限免',
      sec_deal: '💰 今日特价（降价未免费）',
      loading: '加载中…',
      free_empty: '今天没有检出限免 App，明天再来看看～',
      deal_empty: '今天没有降价的特价 App。',
      filter_empty: '没有符合当前筛选条件的 App。',
      search_ph: '搜索 App 名称 / 开发者…',
      genre_all: '全部分类',
      footer_copyright: '苹果限免雷达 · 数据每日自动更新 · 非苹果官方站点',
      card_store: 'App Store',
      card_free_price: '免费',
      date_prefix: '数据时间：',
      err_line: '数据暂时无法加载，请稍后刷新',
      err_box: '数据暂时无法加载，请稍后刷新重试。',
      about_badge: '🍎 关于本站',
      about_h1: '关于苹果限免雷达',
      about_lead: '「苹果限免雷达」每天自动扫描 App Store 官方价格，把「昨天还收费、今天免费领」的优质 App 挑出来，附原价对比与用户评分，帮你省下每一分钱。',
      intro_p5: 'App 一旦进入限免或特价，只要活动没结束（价格还维持在促销水平），就会一直留在当天的清单里；等价格恢复原价后自动下架——所以你隔几天回来看，好货不会悄悄消失。',
      about_q_h2: '常见问题',
      about_q1: '<b>限免下载的 App，以后还收费吗？</b>不会。限免期间用 Apple ID 下载后会永久绑定你的账户，以后再下载也免费；卸载重装同样免费。',
      about_q2: '<b>为什么列表里有些 App 标着原价？</b>那是为了方便你判断省了多少——「¥98 ← 免费」表示该 App 原价 ¥98、当前限时免费。',
      about_q3: '<b>数据多久更新一次？</b>每 6 小时自动更新（北京时间 02:00 / 08:00 / 14:00 / 20:00）；页面加载失败时，点击左上角站名即可立即刷新。',
      about_note: '⚠️ 本站为非官方独立站点，与 Apple Inc. 无任何隶属关系。所有价格与可用性以 App Store 实时显示为准，本页不构成购买建议。',
      about_dis_h: '免责声明',
      about_dis_p: '本站价格与可用性来自 Apple 官方接口，可能随时变动；限免/特价活动由开发者设定，本站不构成购买建议。请以下单时 App Store 内显示为准。本站为非官方独立站点，与 Apple Inc. 无任何隶属关系。',
      home_intro_text: '每天自动扫描苹果官方价格，捕捉「昨天还收费、今天免费领」的降价信号，覆盖中国区与美国区。',
      home_intro_link: '了解我们怎么挑 →',
      stat_free: '今日限免',
      stat_deal: '今日特价',
      stat_saved: '今日可省',
      badge_new: 'NEW',
      lowest_30: '30天最低',
      foot_privacy: '隐私政策',
      foot_terms: '使用条款',
      foot_rights: '保留所有权利',
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
      pv_s5h: '五、数据安全',
      pv_s5: '本站全站强制 HTTPS 加密传输；不设任何用户数据上传通道。',
      pv_s6h: '六、未成年人',
      pv_s6: '本站不面向未成年人收集任何数据。',
      pv_s7h: '七、政策更新',
      pv_s7: '本政策如有修订，将在本页发布并更新「最后更新」日期；继续使用本站即视为接受修订后的政策。',
      pv_s8h: '八、联系我们',
      pv_s8: '如对本政策有任何疑问或建议，欢迎通过运营者的博客站点与我们联系。',
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
      tm_updated: '最后更新：2026-10-20'
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
      intro_li1: 'Every day we pull Apple’s <b>official</b> paid Top100 across all 22 categories plus the free chart (≈2,000 unique apps per region after dedup), then verify each app’s live price via Apple’s official API;',
      intro_li2: 'We compare against your <b>historical regular price</b> — only apps that were paid yesterday and hit 0 today get flagged as <b>free</b>;',
      intro_li3: 'Apps that dropped in price but aren’t free go in a separate <b>Deals</b> column for easy comparison;',
      intro_li4: 'All prices and availability are subject to Apple and may change anytime — <b>always confirm in the App Store before purchasing</b>.',
      intro_p4: 'All data comes from Apple’s public APIs; app icons link directly to Apple’s CDN, not re-hosted. Tap any app to jump to its App Store page in that region.',
      sec_free: '🔓 Free Today',
      sec_deal: '💰 Deals Today (price drop)',
      loading: 'Loading…',
      free_empty: 'No limited-time free apps found today. Check back tomorrow.',
      deal_empty: 'No price-drop deals found today.',
      filter_empty: 'No apps match the current filter.',
      search_ph: 'Search app name or developer…',
      genre_all: 'All categories',
      footer_copyright: 'Freebie Radar · updated daily · not an official Apple site',
      card_store: 'App Store',
      card_free_price: 'Free',
      date_prefix: 'Data updated: ',
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
      home_intro_text: 'We scan official App Store prices daily to catch the drop signals — paid yesterday, free today — across the China and US stores.',
      home_intro_link: 'How we pick →',
      stat_free: 'Free today',
      stat_deal: 'Deals today',
      stat_saved: 'You save',
      badge_new: 'NEW',
      lowest_30: '30-day low',
      foot_privacy: 'Privacy Policy',
      foot_terms: 'Terms of Use',
      foot_rights: 'All rights reserved',
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
      pv_s5h: '5. Data security',
      pv_s5: 'This site enforces HTTPS for all traffic and provides no channel for uploading user data.',
      pv_s6h: '6. Minors',
      pv_s6: 'This site does not knowingly collect any data from minors.',
      pv_s7h: '7. Updates to this policy',
      pv_s7: 'If this policy is revised, it will be published on this page with an updated "Last updated" date. Continued use of the site constitutes acceptance of the revised policy.',
      pv_s8h: '8. Contact us',
      pv_s8: "If you have any questions or suggestions about this policy, feel free to reach us via the operator's blog.",
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
      tm_updated: 'Last updated: 2026-10-20'
    }
  };

  var CURRENT_LANG = 'zh';
  var state = { search: '', genre: '' };        // 筛选状态
  var currentData = { free: [], deals: [] };     // 当前区已加载数据

  // ===== 地区配置 =====
  var REGIONS = {
    cn: { file: 'data/free-today-cn.json', label: '中国区', label_en: 'China' },
    us: { file: 'data/free-today-us.json', label: '美国区', label_en: 'United States' }
  };
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
    // 品牌名按域名替换（同仓库多域名：limzero=极零限免 / nickyam=涯木限免）
    var brand = siteName();
    for (var k = 0; k < nodes.length; k++) {
      var html = nodes[k].innerHTML;
      if (!html) continue;
      if (html.indexOf('苹果限免雷达') >= 0) {
        nodes[k].innerHTML = html.split('苹果限免雷达').join(brand);
      } else if (html.indexOf('Freebie Radar') >= 0) {
        nodes[k].innerHTML = html.split('Freebie Radar').join(brand);
      }
    }
    var y = document.getElementById('year');
    if (y) y.textContent = new Date().getFullYear();
    var lb = document.getElementById('langBtn');
    if (lb) lb.textContent = CURRENT_LANG === 'en' ? '🇨🇳' : '🇺🇸';
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

  // 30 天价格迷你曲线（inline SVG sparkline）
  function sparkline(series, kind) {
    if (!series || series.length < 2) return '';
    var W = 118, H = 30, pad = 3;
    var vals = series.map(function (v) { return v || 0; });
    var min = Math.min.apply(null, vals);
    var max = Math.max.apply(null, vals);
    var n = vals.length;
    var range = (max - min) || 1;
    var pts = vals.map(function (v, i) {
      var x = pad + (W - 2 * pad) * (i / (n - 1));
      var y = (H - pad) - (H - 2 * pad) * ((v - min) / range);
      return x.toFixed(1) + ',' + y.toFixed(1);
    });
    var color = kind === 'free' ? '#34c759' : '#ff9f0a';
    return '<svg class="spark" width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" ' +
      'aria-hidden="true" focusable="false"><polyline points="' + pts.join(' ') + '" fill="none" ' +
      'stroke="' + color + '" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/></svg>';
  }

  function appCard(app, kind) {
    var dict = I18N[CURRENT_LANG];
    var card = el('div', 'card');
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
    if (app.rating && app.rating > 0) {
      info.appendChild(el('div', 'rating', '★ ' + (Math.round(app.rating * 10) / 10).toFixed(1)));
    }
    var price = el('div', 'price');
    if (app.normal) price.appendChild(el('span', 'old', esc(app.normal)));
    var newCls = kind === 'free' ? 'new free' : 'new deal';
    var newText = app.current || (kind === 'free' ? dict.card_free_price : '');
    price.appendChild(el('span', newCls, esc(newText)));
    info.appendChild(price);
    // 30 天价格迷你曲线 + 历史最低标记
    var series = app.series || [];
    var curVal = series.length ? (series[series.length - 1] || 0) : 0;
    var minVal = series.length ? Math.min.apply(null, series) : 0;
    var isLow = series.length >= 1 && curVal <= minVal;
    var extra = el('div', 'price-extra');
    var sp = sparkline(series, kind);
    if (sp) extra.innerHTML = sp;
    if (isLow) extra.appendChild(el('span', 'low-tag', esc(dict.lowest_30)));
    if (sp || isLow) info.appendChild(extra);
    card.appendChild(info);
    if (app.url) {
      var go = el('a', 'go', dict.card_store);
      go.href = app.url;
      go.target = '_blank';
      go.rel = 'noopener';
      card.appendChild(go);
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
    data.forEach(function (a) { grid.appendChild(appCard(a, kind)); });
    box.appendChild(grid);
  }

  // ===== 筛选 =====
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
      var o = el('option', null, esc(g));
      o.value = g;
      sel.appendChild(o);
    });
    if (state.genre && !set[state.genre]) state.genre = ''; // 当前区无此分类则重置
    sel.value = state.genre;
  }

  function renderFiltered() {
    var dict = I18N[CURRENT_LANG];
    var free = filterApps(currentData.free);
    var deals = filterApps(currentData.deals);
    var freeEmpty = currentData.free.length === 0 ? dict.free_empty : dict.filter_empty;
    var dealEmpty = currentData.deals.length === 0 ? dict.deal_empty : dict.filter_empty;
    renderList('freeList', free, 'free', freeEmpty);
    renderList('dealList', deals, 'deal', dealEmpty);
  }

  function showError() {
    var dict = I18N[CURRENT_LANG];
    ['freeList', 'dealList'].forEach(function (id) {
      var b = document.getElementById(id);
      if (b) b.innerHTML = '<div class="empty">' + esc(dict.err_box) + '</div>';
    });
    var dl = document.getElementById('dateLine');
    if (dl) dl.textContent = dict.err_line;
    var sf = document.getElementById('statFree'); if (sf) sf.textContent = '0';
    var sd = document.getElementById('statDeal'); if (sd) sd.textContent = '0';
    var ss = document.getElementById('statSaved'); if (ss) ss.textContent = '¥0';
  }

  function load(region) {
    var meta = REGIONS[region];
    if (!meta) region = 'cn', meta = REGIONS.cn;

    var dict = I18N[CURRENT_LANG];
    var btns = document.querySelectorAll('#regionSwitch .region-btn');
    for (var i = 0; i < btns.length; i++) {
      btns[i].classList.toggle('active', btns[i].getAttribute('data-region') === region);
    }

    fetch(meta.file, { cache: 'no-cache' })
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
        var ss = document.getElementById('statSaved'); if (ss) ss.textContent = formatMoney(region, saved);
        fillGenres();
        renderFiltered();
      })
      .catch(function () { showError(); });
  }

  function bindControls() {
    var langBtn = document.getElementById('langBtn');
    if (langBtn) langBtn.addEventListener('click', function () {
      var next = (CURRENT_LANG === 'en') ? 'zh' : 'en';
      lsSet(LANG_KEY, next);
      applyLang(next);
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
    if (si) si.addEventListener('input', function () {
      state.search = this.value;
      renderFiltered();
    });
    var gf = document.getElementById('genreFilter');
    if (gf) gf.addEventListener('change', function () {
      state.genre = this.value;
      renderFiltered();
    });

    // 点击站名「苹果限免雷达」：首页=刷新数据；关于页=回首页
    var logo = document.getElementById('logoHome');
    if (logo) logo.addEventListener('click', function () {
      if (!document.getElementById('freeList')) {
        location.href = 'index.html';
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

  // 站点品牌：按域名区分（同仓库部署到 limzero / nickyam 两套域名）
  function siteName() {
    var h = location.hostname;
    if (h.indexOf('limzero') >= 0) return '极零限免';
    if (h.indexOf('nickyam') >= 0) return '涯木限免';
    // 本地预览（localhost/127.0.0.1）按主镜像品牌显示，预览即所见即所得
    if (h === 'localhost' || h === '127.0.0.1' || h === '') return '极零限免';
    return '苹果限免雷达';
  }

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
    var name = siteName();
    var url = location.origin + location.pathname;
    var logo = document.getElementById('siteLogo');
    if (logo) logo.textContent = name;
    var fs = document.getElementById('footerSiteName');
    if (fs) fs.textContent = name;
    var title = document.title || '';
    if (title.indexOf('苹果限免雷达') >= 0) document.title = title.split('苹果限免雷达').join(name);
    ['og:site_name', 'og:title', 'twitter:title', 'og:description', 'twitter:description', 'description'].forEach(function (key) {
      var m = document.querySelector('meta[property="' + key + '"]') ||
              document.querySelector('meta[name="' + key + '"]');
      if (!m) return;
      var c = m.getAttribute('content') || '';
      if (c.indexOf('苹果限免雷达') >= 0) m.setAttribute('content', c.split('苹果限免雷达').join(name));
    });
    var canon = document.querySelector('link[rel="canonical"]');
    if (canon) canon.setAttribute('href', url);
    setMeta('og:url', url);
    try {
      var ld = document.querySelector('script[type="application/ld+json"]');
      if (ld) {
        var o = JSON.parse(ld.textContent);
        if (o.name) o.name = name;
        o.url = url;
        ld.textContent = JSON.stringify(o);
      }
    } catch (e) {}
  }

  function init() {
    applyTheme(getTheme());   // 主题（null=跟随系统）
    applyLang(getLang());     // 语言
    applyBrand();             // 站点品牌（域名自适应）
    bindControls();
    load(getRegion());        // 拉数据
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

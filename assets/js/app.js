// 限免日报前端：按地区拉取对应 data/free-today-{region}.json 并渲染
(function () {
  var YEAR = document.getElementById('year');
  if (YEAR) YEAR.textContent = new Date().getFullYear();

  var REGIONS = {
    cn: { label: '中国区', file: 'data/free-today-cn.json', badge: '🍎 中国区 · 每日 09:00 自动更新' },
    us: { label: '美国区', file: 'data/free-today-us.json', badge: '🍎 美国区 · 每日 09:00 自动更新' }
  };
  var STORE_KEY = 'freebie-region';

  function getRegion() {
    var saved = null;
    try { saved = localStorage.getItem(STORE_KEY); } catch (e) {}
    if (saved && REGIONS[saved]) return saved;
    return 'cn';
  }

  function setRegion(r) {
    try { localStorage.setItem(STORE_KEY, r); } catch (e) {}
  }

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

  function appCard(app, kind) {
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
    info.appendChild(el('div', 'name', esc(app.name || '未命名')));
    info.appendChild(el('div', 'dev', esc(app.dev || '')));
    if (app.genre) info.appendChild(el('div', 'genre', esc(app.genre)));
    if (app.rating && app.rating > 0) {
      info.appendChild(el('div', 'rating', '★ ' + (Math.round(app.rating * 10) / 10).toFixed(1)));
    }
    var price = el('div', 'price');
    if (app.normal) {
      price.appendChild(el('span', 'old', esc(app.normal)));
    }
    var newCls = kind === 'free' ? 'new free' : 'new deal';
    price.appendChild(el('span', newCls, esc(app.current || (kind === 'free' ? '免费' : ''))));
    info.appendChild(price);
    card.appendChild(info);
    if (app.url) {
      var go = el('a', 'go', 'App Store');
      go.href = app.url;
      go.target = '_blank';
      go.rel = 'noopener';
      card.appendChild(go);
    }
    return card;
  }

  function renderList(containerId, data, kind, emptyText) {
    var box = document.getElementById(containerId);
    box.innerHTML = '';
    if (!data || data.length === 0) {
      box.appendChild(el('div', 'empty', emptyText));
      return;
    }
    var grid = el('div', 'grid');
    data.forEach(function (a) { grid.appendChild(appCard(a, kind)); });
    box.appendChild(grid);
  }

  function showError(msg) {
    ['freeList', 'dealList'].forEach(function (id) {
      var b = document.getElementById(id);
      if (b) b.innerHTML = '<div class="empty">' + esc(msg) + '</div>';
    });
    var dl = document.getElementById('dateLine');
    if (dl) dl.textContent = '数据暂时无法加载，请稍后刷新';
  }

  function load(region) {
    var meta = REGIONS[region];
    if (!meta) region = 'cn', meta = REGIONS.cn;

    // 更新菜单高亮
    var btns = document.querySelectorAll('#regionSwitch .region-btn');
    btns.forEach(function (b) {
      b.classList.toggle('active', b.getAttribute('data-region') === region);
    });
    var badge = document.getElementById('regionBadge');
    if (badge) badge.textContent = meta.badge;

    fetch(meta.file, { cache: 'no-cache' })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (d) {
        var dl = document.getElementById('dateLine');
        if (dl) {
          var gen = d.generated_at ? '（更新于 ' + d.generated_at + ' UTC）' : '';
          dl.textContent = '数据日期：' + (d.date || '—') + ' · ' + meta.label + gen;
        }
        var free = d.freebies || [];
        var deals = d.deals || [];
        var fc = document.getElementById('freeCount'); if (fc) fc.textContent = free.length;
        var dc = document.getElementById('dealCount'); if (dc) dc.textContent = deals.length;
        renderList('freeList', free, 'free', '今天没有检出限免 App，明天再来看看～');
        renderList('dealList', deals, 'deal', '今天没有降价的特价 App。');
      })
      .catch(function (e) { showError('加载失败：' + e.message); });
  }

  function init() {
    var region = getRegion();
    setRegion(region);
    var btns = document.querySelectorAll('#regionSwitch .region-btn');
    btns.forEach(function (b) {
      b.addEventListener('click', function () {
        var r = b.getAttribute('data-region');
        if (r === getRegion()) return;
        setRegion(r);
        load(r);
      });
    });
    load(region);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

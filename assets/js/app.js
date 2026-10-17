// 限免日报前端：拉取同域 data/free-today.json 并渲染
(function () {
  var YEAR = document.getElementById('year');
  if (YEAR) YEAR.textContent = new Date().getFullYear();

  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
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

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
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

  function init() {
    fetch('data/free-today.json', { cache: 'no-cache' })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (d) {
        var dl = document.getElementById('dateLine');
        if (dl) {
          var gen = d.generated_at ? '（更新于 ' + d.generated_at + ' UTC）' : '';
          dl.textContent = '数据日期：' + (d.date || '—') + ' · 中国区' + gen;
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

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

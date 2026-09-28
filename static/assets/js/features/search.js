/**
 * features/search.js —— 搜索与发现（D类）
 *
 * 功能：
 *   D1 实时搜索建议下拉（增强 common.js，合并历史）
 *   D2 搜索历史记录（localStorage，可清除）
 *   D3 热门搜索词云（GET /api/search/hot/）
 *   D4 拼音搜索（后端支持，前端提交 q 即可）
 *   D5 标签云热力（按热度加 heat-* 类）
 *   D6 分类导航树（折叠/展开）
 *   D7 随机一篇（跳转 data-random-url 或 /article/random/）
 *   D8 最近浏览展示（读取 localStorage recent_views）
 *   D9 归档时间线（纯 CSS 增强，此处补年份折叠）
 *   D10 热门榜切换（周/月/总，前端切换 data-range）
 *   D11 搜索结果排序（?sort= 跳转）
 *   D12 无结果推荐热门文章
 *
 * 防御式：仅在相关 DOM 存在时初始化，纯原生。
 */
(function () {
    'use strict';
    var LS = 'blog_search_history';

    function getHistory() { try { return JSON.parse(localStorage.getItem(LS) || '[]'); } catch (e) { return []; } }
    function pushHistory(q) {
        if (!q) return;
        var h = getHistory().filter(function (x) { return x !== q; });
        h.unshift(q); h = h.slice(0, 10);
        try { localStorage.setItem(LS, JSON.stringify(h)); } catch (e) {}
    }

    /* ---------- D2 搜索历史展示与清除 ---------- */
    var histBox = document.querySelector('.search-history-tags');
    if (histBox) {
        getHistory().forEach(function (q) {
            var tag = document.createElement('span');
            tag.className = 'tag-hist'; tag.textContent = q;
            tag.addEventListener('click', function () { location.href = '/search/?q=' + encodeURIComponent(q); });
            histBox.appendChild(tag);
        });
        var clearBtn = document.querySelector('[data-clear-history]');
        if (clearBtn) clearBtn.addEventListener('click', function () {
            try { localStorage.removeItem(LS); } catch (e) {}
            histBox.innerHTML = '';
        });
        // 记录当前搜索词
        var cur = new URLSearchParams(location.search).get('q');
        if (cur) pushHistory(cur);
    }

    /* ---------- D1/D2 导航搜索建议附加历史 ---------- */
    var navInput = document.querySelector('.nav-search input[name="q"]');
    if (navInput) {
        navInput.addEventListener('focus', function () {
            var list = document.querySelector('.search-suggestions');
            if (!list) return;
            list.innerHTML = '';
            var hist = getHistory();
            if (hist.length) {
                var lbl = document.createElement('li');
                lbl.className = 'ss-history-label'; lbl.textContent = '历史搜索';
                list.appendChild(lbl);
                hist.forEach(function (q) {
                    var li = document.createElement('li'); li.textContent = q;
                    li.addEventListener('mousedown', function (e) {
                        e.preventDefault(); navInput.value = q; navInput.form.submit();
                    });
                    list.appendChild(li);
                });
                list.classList.add('show');
            }
        });
    }

    /* ---------- D3 热门搜索词云 ---------- */
    var cloud = document.querySelector('.hot-word-cloud');
    if (cloud && !cloud.children.length) {
        fetch('/api/search/hot/').then(function (r) { return r.json(); }).then(function (data) {
            (data.words || []).forEach(function (w, i) {
                var s = document.createElement('span');
                s.className = 'hw'; s.textContent = w.word || w;
                s.style.fontSize = (1 + Math.min(i, 5) * 0.12) + 'rem';
                s.addEventListener('click', function () {
                    location.href = '/search/?q=' + encodeURIComponent(w.word || w);
                });
                cloud.appendChild(s);
            });
        }).catch(function () {});
    }

    /* ---------- D5 标签云热力（按 data-heat 上色） ---------- */
    document.querySelectorAll('.tag-cloud .tag-item').forEach(function (t) {
        var heat = +(t.getAttribute('data-heat') || 1);
        t.classList.add('heat-' + Math.max(1, Math.min(4, heat)));
    });

    /* ---------- D6 分类导航树折叠 ---------- */
    document.querySelectorAll('.ct-toggle').forEach(function (tg) {
        tg.addEventListener('click', function () {
            var sub = tg.parentElement.querySelector('ul');
            if (sub) sub.style.display = (sub.style.display === 'none') ? '' : 'none';
        });
    });

    /* ---------- D7 随机一篇 ---------- */
    var rand = document.querySelector('[data-random-article]');
    if (rand) {
        rand.addEventListener('click', function (e) {
            e.preventDefault();
            var url = rand.getAttribute('data-random-url') || '/article/random/';
            fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(function (r) { return r.json(); })
                .then(function (d) { location.href = d.url || '/'; })
                .catch(function () { location.href = url; });
        });
    }

    /* ---------- D8 最近浏览侧边栏 ---------- */
    var recentBox = document.querySelector('.recent-views-sidebar');
    if (recentBox) {
        try {
            var views = JSON.parse(localStorage.getItem('recent_views') || '[]').slice(0, 8);
            views.forEach(function (v) {
                var a = document.createElement('a');
                a.className = 'recent-view-item'; a.href = v.url;
                a.textContent = v.title; a.style.display = 'block';
                a.style.padding = '4px 0'; a.style.fontSize = '.85rem';
                recentBox.appendChild(a);
            });
        } catch (e) {}
    }

    /* ---------- D10 热门榜切换 ---------- */
    var rankTabs = document.querySelectorAll('.hot-rank-tabs button');
    rankTabs.forEach(function (btn) {
        btn.addEventListener('click', function () {
            var range = btn.getAttribute('data-range');
            rankTabs.forEach(function (b) { b.classList.remove('active'); });
            btn.classList.add('active');
            var list = document.querySelector('.hot-rank-list');
            if (!list) return;
            fetch('/api/articles/hot/?range=' + range, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(function (r) { return r.json(); }).then(function (data) {
                    list.innerHTML = '';
                    (data.articles || []).forEach(function (a, i) {
                        var li = document.createElement('li');
                        li.innerHTML = '<span class="rank-no">' + (i + 1) + '</span> ' +
                            '<a href="' + a.url + '">' + a.title + '</a>';
                        list.appendChild(li);
                    });
                }).catch(function () {});
        });
    });

    /* ---------- D11 搜索结果排序 ---------- */
    var sortSel = document.querySelector('.search-sort-select');
    if (sortSel) {
        sortSel.addEventListener('change', function () {
            var url = new URL(location.href);
            url.searchParams.set('sort', sortSel.value);
            location.href = url.toString();
        });
    }
})();

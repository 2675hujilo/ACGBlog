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
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';
    //> 声明变量「LS」（ls），用于保存对应数据，初始为字符串
    var LS = 'blog_search_history';

    // =========================================================
    // 【函数】getHistory
    // 功能：获取「history」相关逻辑（get history）
    // 参数：无
    // 返回：函数体内有 return，返回对应结果
    // 注意：读写本地存储，注意容量限制与 JSON 解析异常
    // =========================================================
    function getHistory() { try { return JSON.parse(localStorage.getItem(LS) || '[]'); } catch (e) { return []; } }
    // =========================================================
    // 【函数】pushHistory
    // 功能：处理「push history」相关逻辑（search）
    // 参数：
    //   - q：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function pushHistory(q) {
        //> 条件判断：满足括号内条件时执行对应分支
        if (!q) return;
        //> 声明变量「h」（h），用于保存对应数据
        var h = getHistory().filter(function (x) { return x !== q; });
        //> 操作「h」的相关方法/属性
        h.unshift(q); h = h.slice(0, 10);
        //> 尝试执行可能出错的代码，出错则进入 catch
        try { localStorage.setItem(LS, JSON.stringify(h)); } catch (e) {}
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- D2 搜索历史展示与清除 ---------- */
    //> 声明变量「histBox」（hist box），用于保存对应数据，保存 DOM/窗口相关对象
    var histBox = document.querySelector('.search-history-tags');
    //> 条件判断：满足括号内条件时执行对应分支
    if (histBox) {
        //> 遍历数组/类数组中的每一项并执行回调
        getHistory().forEach(function (q) {
            //> 声明变量「tag」（tag），用于保存对应数据，保存 DOM/窗口相关对象
            var tag = document.createElement('span');
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            tag.className = 'tag-hist'; tag.textContent = q;
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            tag.addEventListener('click', function () { location.href = '/search/?q=' + encodeURIComponent(q); });
            //> 把子节点追加到当前元素内部末尾
            histBox.appendChild(tag);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        //> 声明变量「clearBtn」（clear btn），用于保存对应数据，保存 DOM/窗口相关对象
        var clearBtn = document.querySelector('[data-clear-history]');
        //> 条件判断：满足括号内条件时执行对应分支
        if (clearBtn) clearBtn.addEventListener('click', function () {
            //> 尝试执行可能出错的代码，出错则进入 catch
            try { localStorage.removeItem(LS); } catch (e) {}
            //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
            histBox.innerHTML = '';
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        // 记录当前搜索词
        //> 声明变量「cur」（cur），用于保存对应数据
        var cur = new URLSearchParams(location.search).get('q');
        //> 条件判断：满足括号内条件时执行对应分支
        if (cur) pushHistory(cur);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- D1/D2 导航搜索建议附加历史 ---------- */
    //> 声明变量「navInput」（nav input），用于保存对应数据，保存 DOM/窗口相关对象
    var navInput = document.querySelector('.nav-search input[name="q"]');
    //> 条件判断：满足括号内条件时执行对应分支
    if (navInput) {
        //> 绑定「focus」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        navInput.addEventListener('focus', function () {
            //> 声明变量「list」（list），用于保存对应数据，保存 DOM/窗口相关对象
            var list = document.querySelector('.search-suggestions');
            //> 条件判断：满足括号内条件时执行对应分支
            if (!list) return;
            //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
            list.innerHTML = '';
            //> 声明变量「hist」（hist），用于保存对应数据
            var hist = getHistory();
            //> 条件判断：满足括号内条件时执行对应分支
            if (hist.length) {
                //> 声明变量「lbl」（lbl），用于保存对应数据，保存 DOM/窗口相关对象
                var lbl = document.createElement('li');
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                lbl.className = 'ss-history-label'; lbl.textContent = '历史搜索';
                //> 把子节点追加到当前元素内部末尾
                list.appendChild(lbl);
                //> 遍历数组/类数组中的每一项并执行回调
                hist.forEach(function (q) {
                    //> 声明变量「li」（li），用于保存对应数据，保存 DOM/窗口相关对象
                    var li = document.createElement('li'); li.textContent = q;
                    //> 绑定「mousedown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
                    li.addEventListener('mousedown', function (e) {
                        //> 阻止事件的默认行为（如表单提交、链接跳转）
                        e.preventDefault(); navInput.value = q; navInput.form.submit();
                    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                    });
                    //> 把子节点追加到当前元素内部末尾
                    list.appendChild(li);
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                });
                //> 为元素添加一个或多个样式类
                list.classList.add('show');
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- D3 热门搜索词云 ---------- */
    //> 声明变量「cloud」（cloud），用于保存对应数据，保存 DOM/窗口相关对象
    var cloud = document.querySelector('.hot-word-cloud');
    //> 条件判断：满足括号内条件时执行对应分支
    if (cloud && !cloud.children.length) {
        //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
        fetch('/api/search/hot/').then(function (r) { return r.json(); }).then(function (data) {
            //> 遍历数组/类数组中的每一项并执行回调
            (data.words || []).forEach(function (w, i) {
                //> 声明变量「s」（s），用于保存对应数据，保存 DOM/窗口相关对象
                var s = document.createElement('span');
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                s.className = 'hw'; s.textContent = w.word || w;
                //> 给「s.style.fontSize」赋值，更新其保存的状态
                s.style.fontSize = (1 + Math.min(i, 5) * 0.12) + 'rem';
                //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
                s.addEventListener('click', function () {
                    //> 对 URL 参数做编码，防止特殊字符破坏链接或被注入
                    location.href = '/search/?q=' + encodeURIComponent(w.word || w);
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                });
                //> 把子节点追加到当前元素内部末尾
                cloud.appendChild(s);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }).catch(function () {});
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- D5 标签云热力（按 data-heat 上色） ---------- */
    //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
    document.querySelectorAll('.tag-cloud .tag-item').forEach(function (t) {
        //> 声明变量「heat」（heat），用于保存对应数据
        var heat = +(t.getAttribute('data-heat') || 1);
        //> 为元素添加一个或多个样式类
        t.classList.add('heat-' + Math.max(1, Math.min(4, heat)));
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- D6 分类导航树折叠 ---------- */
    //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
    document.querySelectorAll('.ct-toggle').forEach(function (tg) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        tg.addEventListener('click', function () {
            //> 声明变量「sub」（sub），用于保存对应数据
            var sub = tg.parentElement.querySelector('ul');
            //> 条件判断：满足括号内条件时执行对应分支
            if (sub) sub.style.display = (sub.style.display === 'none') ? '' : 'none';
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- D7 随机一篇 ---------- */
    //> 声明变量「rand」（rand），用于保存对应数据，保存 DOM/窗口相关对象
    var rand = document.querySelector('[data-random-article]');
    //> 条件判断：满足括号内条件时执行对应分支
    if (rand) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        rand.addEventListener('click', function (e) {
            //> 阻止事件的默认行为（如表单提交、链接跳转）
            e.preventDefault();
            //> 声明变量「url」（url），用于保存对应数据
            var url = rand.getAttribute('data-random-url') || '/article/random/';
            //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
            fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                .then(function (r) { return r.json(); })
                //> 通过赋值跳转页面
                .then(function (d) { location.href = d.url || '/'; })
                //> 通过赋值跳转页面
                .catch(function () { location.href = url; });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- D8 最近浏览侧边栏 ---------- */
    //> 声明变量「recentBox」（recent box），用于保存对应数据，保存 DOM/窗口相关对象
    var recentBox = document.querySelector('.recent-views-sidebar');
    //> 条件判断：满足括号内条件时执行对应分支
    if (recentBox) {
        //> 尝试执行可能出错的代码，出错则进入 catch
        try {
            //> 声明变量「views」（views），用于保存对应数据
            var views = JSON.parse(localStorage.getItem('recent_views') || '[]').slice(0, 8);
            //> 遍历数组/类数组中的每一项并执行回调
            views.forEach(function (v) {
                //> 声明变量「a」（a），用于保存对应数据，保存 DOM/窗口相关对象
                var a = document.createElement('a');
                //> 给「a.className」赋值，更新其保存的状态
                a.className = 'recent-view-item'; a.href = v.url;
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                a.textContent = v.title; a.style.display = 'block';
                //> 给「a.style.padding」赋值，更新其保存的状态
                a.style.padding = '4px 0'; a.style.fontSize = '.85rem';
                //> 把子节点追加到当前元素内部末尾
                recentBox.appendChild(a);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        } catch (e) {}
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- D10 热门榜切换 ---------- */
    //> 声明变量「rankTabs」（rank tabs），用于保存对应数据，保存 DOM/窗口相关对象
    var rankTabs = document.querySelectorAll('.hot-rank-tabs button');
    //> 遍历数组/类数组中的每一项并执行回调
    rankTabs.forEach(function (btn) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        btn.addEventListener('click', function () {
            //> 声明变量「range」（range），用于保存对应数据
            var range = btn.getAttribute('data-range');
            //> 移除元素的一个或多个样式类
            rankTabs.forEach(function (b) { b.classList.remove('active'); });
            //> 为元素添加一个或多个样式类
            btn.classList.add('active');
            //> 声明变量「list」（list），用于保存对应数据，保存 DOM/窗口相关对象
            var list = document.querySelector('.hot-rank-list');
            //> 条件判断：满足括号内条件时执行对应分支
            if (!list) return;
            //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
            fetch('/api/articles/hot/?range=' + range, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                .then(function (r) { return r.json(); }).then(function (data) {
                    //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
                    list.innerHTML = '';
                    //> 遍历数组/类数组中的每一项并执行回调
                    (data.articles || []).forEach(function (a, i) {
                        //> 声明变量「li」（li），用于保存对应数据，保存 DOM/窗口相关对象
                        var li = document.createElement('li');
                        //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
                        li.innerHTML = '<span class="rank-no">' + (i + 1) + '</span> ' +
                            //> 该行执行对应的脚本逻辑（结合上下文理解）
                            '<a href="' + a.url + '">' + a.title + '</a>';
                        //> 把子节点追加到当前元素内部末尾
                        list.appendChild(li);
                    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                    });
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                }).catch(function () {});
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- D11 搜索结果排序 ---------- */
    //> 声明变量「sortSel」（sort sel），用于保存对应数据，保存 DOM/窗口相关对象
    var sortSel = document.querySelector('.search-sort-select');
    //> 条件判断：满足括号内条件时执行对应分支
    if (sortSel) {
        //> 绑定「change」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        sortSel.addEventListener('change', function () {
            //> 声明变量「url」（url），用于保存对应数据
            var url = new URL(location.href);
            //> 操作「url.searchParams」的相关方法/属性
            url.searchParams.set('sort', sortSel.value);
            //> 通过赋值跳转页面
            location.href = url.toString();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

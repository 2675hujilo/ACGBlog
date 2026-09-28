/* Bug11 文件头注释
 * 文章功能脚本：详情页点赞、收藏、分享、复制链接等按钮的异步行为与状态切换。
 * 用 session 防重复，结果通过 moeToast 与计数更新反馈。
 */
/* article_features.js —— 详情页增强：
 *   63. 星级评分（点击提交 /api/articles/<pk>/rate/）
 *   55. 版本快照弹窗（查看快照按钮 → 左右对比）
 *   60. 打印本文按钮（window.print()）
 *   65. 复制 Markdown 目录到剪贴板
 * 本脚本通过 <script data-article-id=...> 属性传入当前文章信息。
 */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';
    //> 声明变量「self」（self），用于保存对应数据，保存 DOM/窗口相关对象
    var self = document.currentScript || document.querySelector('script[data-article-id]');
    //> 声明变量「ARTICLE_ID」（article id），用于保存对应数据
    var ARTICLE_ID = self ? self.dataset.articleId : null;
    //> 声明变量「ARTICLE_TITLE」（article title），用于保存对应数据
    var ARTICLE_TITLE = self ? self.dataset.articleTitle : '';
    //> 声明变量「ARTICLE_VIEWS」（article views），用于保存对应数据
    var ARTICLE_VIEWS = self ? self.dataset.articleViews : '0';
    //> 声明变量「ARTICLE_COVER」（article cover），用于保存对应数据，值为一个函数
    var ARTICLE_COVER = (self && self.dataset.articleCover) || '';

    /* ---------- 63. 星级评分 ---------- */
    //> 声明变量「widget」（widget），用于保存对应数据，保存 DOM/窗口相关对象
    var widget = document.getElementById('rating-widget');
    //> 条件判断：满足括号内条件时执行对应分支
    if (widget) {
        //> 声明变量「stars」（stars），用于保存对应数据
        var stars = widget.querySelectorAll('.star');
        //> 声明变量「my」（my），用于保存对应数据
        var my = widget.dataset.my;
        // 初始高亮已评分
        //> 调用函数「paintStars」并传入参数执行对应逻辑
        paintStars(parseInt(my, 10) || 0);
        // =========================================================
        // 【函数】paintStars
        // 功能：处理「paint stars」相关逻辑（article_features）
        // 参数：
        //   - n：传入的参数（含义结合调用处与函数体）
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function paintStars(n) {
            //> 遍历数组/类数组中的每一项并执行回调
            stars.forEach(function (s) {
                //> 切换样式类（有则移除、无则添加），可传第二参强制状态
                s.classList.toggle('on', parseInt(s.dataset.value, 10) <= n);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 遍历数组/类数组中的每一项并执行回调
        stars.forEach(function (s) {
            //> 声明变量「val」（val），用于保存对应数据
            var val = parseInt(s.dataset.value, 10);
            //> 绑定「mouseenter」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            s.addEventListener('mouseenter', function () { paintStars(val); });
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            s.addEventListener('click', function () {
                //> 调用函数「submitRate」并传入参数执行对应逻辑
                submitRate(val);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        //> 绑定「mouseleave」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        widget.addEventListener('mouseleave', function () { paintStars(parseInt(my, 10) || 0); });

        // =========================================================
        // 【函数】submitRate
        // 功能：提交「rate」相关逻辑（submit rate）
        // 参数：
        //   - val：传入的参数（含义结合调用处与函数体）
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function submitRate(val) {
            //> 声明变量「fd」（fd），用于保存对应数据
            var fd = new FormData();
            //> 操作「fd」的相关方法/属性
            fd.append('score', val);
            //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
            fetch(widget.dataset.url, {
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                method: 'POST',
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                body: fd,
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                headers: { 'X-CSRFToken': csrftoken() },
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                credentials: 'same-origin'
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }).then(function (r) { return r.json(); }).then(function (data) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (data.success) {
                    //> 给「my」赋值，更新其保存的状态
                    my = data.my;
                    //> 调用函数「paintStars」并传入参数执行对应逻辑
                    paintStars(my);
                    //> 声明变量「avg」（avg），用于保存对应数据
                    var avg = widget.querySelector('.rating-avg');
                    //> 条件判断：满足括号内条件时执行对应分支
                    if (avg) avg.textContent = '⭐ ' + data.avg + '（' + data.count + '人）';
                    //> 调用函数「toast」并传入参数执行对应逻辑
                    toast('评分成功喵~ ' + my + '⭐');
                //> 以上条件都不满足时执行的兜底分支
                } else {
                    //> 调用函数「toast」并传入参数执行对应逻辑
                    toast(data.error || '评分失败喵~');
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }).catch(function () { toast('网络开小差了喵~'); });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- 55. 版本快照弹窗 ---------- */
    //> 声明变量「modal」（modal），用于保存对应数据，保存 DOM/窗口相关对象
    var modal = document.getElementById('snapshot-modal');
    //> 条件判断：满足括号内条件时执行对应分支
    if (modal) {
        //> 声明变量「beforeEl」（before el），用于保存对应数据，保存 DOM/窗口相关对象
        var beforeEl = document.getElementById('snapshot-before');
        //> 声明变量「afterEl」（after el），用于保存对应数据，保存 DOM/窗口相关对象
        var afterEl = document.getElementById('snapshot-after');
        //> 声明变量「titleEl」（title el），用于保存对应数据，保存 DOM/窗口相关对象
        var titleEl = document.getElementById('snapshot-modal-title');
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        document.querySelectorAll('.snapshot-btn').forEach(function (btn) {
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            btn.addEventListener('click', function () {
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                titleEl.textContent = btn.dataset.title || '版本快照对比';
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                beforeEl.textContent = btn.dataset.before || '（无内容）';
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                afterEl.textContent = btn.dataset.after || '（无内容）';
                //> 给「modal.hidden」赋值，更新其保存的状态
                modal.hidden = false;
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        //> 声明变量「closeBtn」（close btn），用于保存对应数据，保存 DOM/窗口相关对象
        var closeBtn = document.getElementById('snapshot-close');
        //> 条件判断：满足括号内条件时执行对应分支
        if (closeBtn) closeBtn.addEventListener('click', function () { modal.hidden = true; });
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        modal.addEventListener('click', function (e) { if (e.target === modal) modal.hidden = true; });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- 60. 打印本文 ---------- */
    //> 声明变量「printBtn」（print btn），用于保存对应数据，保存 DOM/窗口相关对象
    var printBtn = document.getElementById('print-btn');
    //> 条件判断：满足括号内条件时执行对应分支
    if (printBtn) printBtn.addEventListener('click', function () { window.print(); });

    /* ---------- 65. 复制 Markdown 目录 ---------- */
    //> 声明变量「tocCopy」（toc copy），用于保存对应数据，保存 DOM/窗口相关对象
    var tocCopy = document.getElementById('toc-copy-btn');
    //> 条件判断：满足括号内条件时执行对应分支
    if (tocCopy) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        tocCopy.addEventListener('click', function () {
            //> 声明变量「body」（body），用于保存对应数据，保存 DOM/窗口相关对象
            var body = document.querySelector('.article-body');
            //> 条件判断：满足括号内条件时执行对应分支
            if (!body) return;
            //> 声明变量「headings」（headings），用于保存对应数据
            var headings = body.querySelectorAll('h1, h2, h3, h4, h5');
            //> 声明变量「lines」（lines），用于保存对应数据
            var lines = ['## 目录'];
            //> 遍历数组/类数组中的每一项并执行回调
            headings.forEach(function (h) {
                //> 声明变量「level」（level），用于保存对应数据
                var level = parseInt(h.tagName.substring(1), 10);
                //> 声明变量「indent」（indent），用于保存对应数据
                var indent = new Array(level).join('  ');  // 按层级缩进
                //> 声明变量「text」（text），用于保存对应数据
                var text = h.textContent.trim();
                //> 操作「lines」的相关方法/属性
                lines.push(indent + '- [' + text + '](#' + (h.id || '') + ')');
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            //> 声明变量「md」（md），用于保存对应数据
            var md = lines.join('\n');
            //> 条件判断：满足括号内条件时执行对应分支
            if (navigator.clipboard && navigator.clipboard.writeText) {
                //> 读取浏览器/设备信息（如 userAgent、剪贴板、地理）
                navigator.clipboard.writeText(md).then(function () {
                    //> 调用函数「toast」并传入参数执行对应逻辑
                    toast('目录已复制喵~📋');
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                }).catch(function () { fallbackCopy(md); });
            //> 以上条件都不满足时执行的兜底分支
            } else {
                //> 调用函数「fallbackCopy」并传入参数执行对应逻辑
                fallbackCopy(md);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // =========================================================
    // 【函数】fallbackCopy
    // 功能：处理「fallback copy」相关逻辑（article_features）
    // 参数：
    //   - text：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function fallbackCopy(text) {
        //> 声明变量「ta」（ta），用于保存对应数据，保存 DOM/窗口相关对象
        var ta = document.createElement('textarea');
        //> 给「ta.value」赋值，更新其保存的状态
        ta.value = text;
        //> 把子节点追加到当前元素内部末尾
        document.body.appendChild(ta);
        //> 操作「ta」的相关方法/属性
        ta.select();
        //> 尝试执行可能出错的代码，出错则进入 catch
        try { document.execCommand('copy'); toast('目录已复制喵~📋'); }
        //> 捕获并处理 try 中抛出的异常，避免程序中断
        catch (e) { toast('复制失败喵~'); }
        //> 操作「document.body」的相关方法/属性
        document.body.removeChild(ta);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- 64. 记录阅读历史 ---------- */
    //> 条件判断：满足括号内条件时执行对应分支
    if (ARTICLE_ID) {
        //> 尝试执行可能出错的代码，出错则进入 catch
        try {
            //> 声明变量「key」（key），用于保存对应数据，初始为字符串
            var key = 'reading_history';
            //> 声明变量「list」（list），用于保存对应数据
            var list = JSON.parse(localStorage.getItem(key) || '[]');
            // 去重：移除同 id 的旧记录
            //> 按条件筛选元素，返回满足条件的新数组
            list = list.filter(function (it) { return String(it.id) !== String(ARTICLE_ID); });
            //> 操作「list」的相关方法/属性
            list.unshift({
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                id: ARTICLE_ID,
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                title: ARTICLE_TITLE,
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                cover: ARTICLE_COVER,
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                views: ARTICLE_VIEWS,
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                time: Date.now()
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            //> 条件判断：满足括号内条件时执行对应分支
            if (list.length > 10) list = list.slice(0, 10);  // 最多保留 10 篇
            //> 操作 localStorage（持久化本地存储），注意容量与解析异常
            localStorage.setItem(key, JSON.stringify(list));
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        } catch (e) {}
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- 工具：读取 CSRF token ---------- */
    // =========================================================
    // 【函数】csrftoken
    // 功能：处理「csrftoken」相关逻辑（article_features）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function csrftoken() {
        //> 声明变量「m」（m），用于保存对应数据，保存 DOM/窗口相关对象
        var m = document.cookie.match(/csrftoken=([^;]+)/);
        //> 返回结果并结束当前函数
        return m ? decodeURIComponent(m[1]) : '';
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    /* ---------- 工具：轻量 toast 提示 ---------- */
    // =========================================================
    // 【函数】toast
    // 功能：处理「toast」相关逻辑（article_features）
    // 参数：
    //   - msg：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function toast(msg) {
        //> 声明变量「t」（t），用于保存对应数据，保存 DOM/窗口相关对象
        var t = document.getElementById('global-toast');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!t) {
            //> 创建新的 DOM 元素节点，后续需挂载到文档才显示
            t = document.createElement('div');
            //> 给「t.id」赋值，更新其保存的状态
            t.id = 'global-toast';
            //> 给「t.className」赋值，更新其保存的状态
            t.className = 'global-toast';
            //> 把子节点追加到当前元素内部末尾
            document.body.appendChild(t);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 读写纯文本内容，不解析 HTML，可防 XSS
        t.textContent = msg;
        //> 为元素添加一个或多个样式类
        t.classList.add('show');
        //> 清除对应的定时器，防止其继续执行
        clearTimeout(t._timer);
        //> 移除元素的一个或多个样式类
        t._timer = setTimeout(function () { t.classList.remove('show'); }, 2200);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

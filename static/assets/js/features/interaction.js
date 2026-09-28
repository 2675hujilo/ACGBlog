/* Bug11 文件头注释
 * 交互功能脚本：图片上传、异步提交、悬浮/拖拽等通用交互的接线。
 * Bug4 起评论图片上传成功后插入 <img>，并兼容统一信封 {code,data:{url}} 与扁平 {url}。
 */
/**
 * features/interaction.js —— 互动增强（C类）
 *
 * 功能：
 *   C1 文章踩（POST data-dislike-url）
 *   C2 评论排序（最新/最热，前端重排）
 *   C3 长评论自动折叠（超阈值字数）
 *   C4 评论区搜索（前端过滤高亮）
 *   C5 评论举报（POST data-report-url）
 *   C6 图片评论（评论框图片上传按钮）
 *   C7 评论楼层跳转（点楼层号滚动定位）
 *   C8 只看楼主（过滤非楼主评论）
 *   C9 评论热度🔥标记（点赞数超阈值）
 *   C10 收藏夹管理（前端展示+切换）
 *   C11 评论字数统计（增强样式）
 *   C12 评论草稿自动保存（localStorage）
 *   C13 评论撤回（5分钟内，DELETE data-recall-url）
 *   C14 点赞爱心爆炸粒子（监听 like 成功）
 *   C15 分享后感谢弹窗
 *
 * 防御式：按 data-* 属性 / 类名存在才绑定，纯原生，无依赖。
 */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';

    // =========================================================
    // 【函数】cookie
    // 功能：处理「cookie」相关逻辑（interaction）
    // 参数：
    //   - name：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function cookie(name) {
        //> 声明变量「m」（m），用于保存对应数据，保存 DOM/窗口相关对象
        var m = document.cookie.match(new RegExp('(^| )' + name + '=([^;]*)(;|$)'));
        //> 返回结果并结束当前函数
        return m ? decodeURIComponent(m[2]) : null;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // =========================================================
    // 【函数】post
    // 功能：处理「post」相关逻辑（interaction）
    // 参数：
    //   - url：传入的参数（含义结合调用处与函数体）
    //   - method：传入的参数（含义结合调用处与函数体）
    //   - body：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function post(url, method, body) {
        //> 返回结果并结束当前函数
        return fetch(url, {
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            method: method || 'POST',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            headers: {
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                'X-CSRFToken': cookie('csrftoken'),
                //> 使用 XHR 发起传统异步请求
                'X-Requested-With': 'XMLHttpRequest',
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                'Content-Type': 'application/json'
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            },
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            credentials: 'same-origin',
            //> 把 JS 数据序列化为 JSON 字符串
            body: body ? JSON.stringify(body) : undefined
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }).then(function (r) { return r.json(); });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // =========================================================
    // 【函数】toast
    // 功能：处理「toast」相关逻辑（interaction）
    // 参数：
    //   - msg：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function toast(msg) {
        //> 声明变量「t」（t），用于保存对应数据，保存 DOM/窗口相关对象
        var t = document.getElementById('global-toast');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!t) { t = document.createElement('div'); t.id = 'global-toast'; document.body.appendChild(t); }
        //> 读写纯文本内容，不解析 HTML，可防 XSS
        t.textContent = msg; t.classList.add('show');
        //> 移除元素的一个或多个样式类
        clearTimeout(t._timer); t._timer = setTimeout(function () { t.classList.remove('show'); }, 1600);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- C1 文章踩（D2修复：计数读 dislike_count、文字/标题随状态切换） ---------- */
    //> 声明变量「dislikeBtn」（dislike btn），用于保存对应数据，保存 DOM/窗口相关对象
    var dislikeBtn = document.querySelector('[data-dislike-url]');
    //> 条件判断：满足括号内条件时执行对应分支
    if (dislikeBtn) {
        //> 声明变量「dislikeText」（dislike text），用于保存对应数据
        var dislikeText = dislikeBtn.querySelector('.like-text');
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        dislikeBtn.addEventListener('click', function () {
            //> 读取元素的 HTML 属性值
            post(dislikeBtn.getAttribute('data-dislike-url'), 'POST').then(function (d) {
                //> 声明变量「disliked」（disliked），用于保存对应数据
                var disliked = d.disliked !== false;
                //> 切换样式类（有则移除、无则添加），可传第二参强制状态
                dislikeBtn.classList.toggle('disliked', disliked);
                // 后端返回 dislike_count；兼容旧字段名 count
                //> 声明变量「n」（n），用于保存对应数据，值为一个函数
                var n = (typeof d.dislike_count === 'number') ? d.dislike_count : d.count;
                //> 条件判断：满足括号内条件时执行对应分支
                if (typeof n === 'number') {
                    //> 声明变量「c」（c），用于保存对应数据，保存 DOM/窗口相关对象
                    var c = document.querySelector('[data-dislike-count]');
                    //> 条件判断：满足括号内条件时执行对应分支
                    if (c) c.textContent = n;
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
                //> 条件判断：满足括号内条件时执行对应分支
                if (dislikeText) dislikeText.textContent = disliked ? '已踩喵' : '踩一下喵';
                //> 给「dislikeBtn.title」赋值，更新其保存的状态
                dislikeBtn.title = disliked ? '再点一下取消踩喵~' : '踩一下这篇文章';
                //> 调用函数「toast」并传入参数执行对应逻辑
                toast(disliked ? '已踩~' : '取消踩~');
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }).catch(function () { toast('操作失败'); });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- C2 评论排序 ---------- */
    //> 声明变量「sortBtns」（sort btns），用于保存对应数据，保存 DOM/窗口相关对象
    var sortBtns = document.querySelectorAll('.comment-sort button');
    //> 遍历数组/类数组中的每一项并执行回调
    sortBtns.forEach(function (btn) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        btn.addEventListener('click', function () {
            //> 移除元素的一个或多个样式类
            sortBtns.forEach(function (b) { b.classList.remove('active'); });
            //> 为元素添加一个或多个样式类
            btn.classList.add('active');
            //> 声明变量「wrap」（wrap），用于保存对应数据，保存 DOM/窗口相关对象
            var wrap = document.querySelector('.comment-list') || document.body;
            //> 声明变量「items」（items），用于保存对应数据
            var items = Array.prototype.slice.call(wrap.querySelectorAll('.comment-item'));
            //> 声明变量「mode」（mode），用于保存对应数据
            var mode = btn.getAttribute('data-sort');
            //> 操作「items」的相关方法/属性
            items.sort(function (a, b) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (mode === 'hot') {
                    //> 返回结果并结束当前函数
                    return (+(b.getAttribute('data-likes') || 0)) - (+(a.getAttribute('data-likes') || 0));
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
                //> 返回结果并结束当前函数
                return (+(b.getAttribute('data-time') || 0)) - (+(a.getAttribute('data-time') || 0));
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            //> 把子节点追加到当前元素内部末尾
            items.forEach(function (it) { wrap.appendChild(it); });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- C3 长评论折叠 / C9 热度标记 ---------- */
    //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
    document.querySelectorAll('.comment-item').forEach(function (item) {
        //> 声明变量「text」（text），用于保存对应数据
        var text = item.querySelector('.comment-text');
        //> 声明变量「likes」（likes），用于保存对应数据
        var likes = +(item.getAttribute('data-likes') || 0);
        //> 条件判断：满足括号内条件时执行对应分支
        if (likes >= 20) item.classList.add('comment-hot');
        //> 条件判断：满足括号内条件时执行对应分支
        if (text && text.textContent.length > 120) {
            //> 为元素添加一个或多个样式类
            item.classList.add('comment-folded');
            //> 声明变量「btn」（btn），用于保存对应数据，保存 DOM/窗口相关对象
            var btn = document.createElement('button');
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            btn.className = 'fold-toggle'; btn.textContent = '展开全文 ▾';
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            btn.addEventListener('click', function () {
                //> 声明变量「folded」（folded），用于保存对应数据
                var folded = item.classList.toggle('comment-folded');
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                btn.textContent = folded ? '展开全文 ▾' : '收起 ▴';
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            //> 在参考子节点之前插入新子节点
            text.parentNode.insertBefore(btn, text.nextSibling);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- C4 评论区搜索 ---------- */
    //> 声明变量「cSearch」（c search），用于保存对应数据，保存 DOM/窗口相关对象
    var cSearch = document.querySelector('.comment-search-box input');
    //> 条件判断：满足括号内条件时执行对应分支
    if (cSearch) {
        //> 绑定「input」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        cSearch.addEventListener('input', function () {
            //> 声明变量「q」（q），用于保存对应数据
            var q = cSearch.value.trim().toLowerCase();
            //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
            document.querySelectorAll('.comment-item').forEach(function (it) {
                //> 声明变量「hit」（hit），用于保存对应数据
                var hit = !q || (it.textContent || '').toLowerCase().indexOf(q) >= 0;
                //> 给「it.style.display」赋值，更新其保存的状态
                it.style.display = hit ? '' : 'none';
                //> 切换样式类（有则移除、无则添加），可传第二参强制状态
                it.classList.toggle('highlight', !!q && hit);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- C5 评论举报（bug11：萌系原因弹窗，事件委托兼容动态评论） ---------- */
    //> 声明变量「reportModal」（report modal），用于保存对应数据
    var reportModal = null;
    // =========================================================
    // 【函数】ensureReportModal
    // 功能：处理「ensure report modal」相关逻辑（interaction）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function ensureReportModal() {
        //> 条件判断：满足括号内条件时执行对应分支
        if (reportModal) return reportModal;
        //> 创建新的 DOM 元素节点，后续需挂载到文档才显示
        reportModal = document.createElement('div');
        //> 给「reportModal.className」赋值，更新其保存的状态
        reportModal.className = 'moe-report-mask';
        //> 给「reportModal.hidden」赋值，更新其保存的状态
        reportModal.hidden = true;
        //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
        reportModal.innerHTML =
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '<div class="moe-report-panel" role="dialog" aria-modal="true" aria-labelledby="mrp-title">' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '  <div class="mrp-head"><strong id="mrp-title">🚩 举报这条评论喵</strong>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '    <button type="button" class="mrp-close" aria-label="关闭">✕</button></div>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '  <div class="mrp-reasons">' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '    <button type="button" class="mrp-reason" data-reason="垃圾广告">📢 垃圾广告</button>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '    <button type="button" class="mrp-reason" data-reason="引战辱骂">😾 引战辱骂</button>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '    <button type="button" class="mrp-reason" data-reason="违法违规">⚠️ 违法违规</button>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '    <button type="button" class="mrp-reason" data-reason="色情低俗">🔞 色情低俗</button>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '    <button type="button" class="mrp-reason" data-reason="其他">🌸 其他</button>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '  </div>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '  <textarea class="mrp-detail" rows="2" maxlength="300" placeholder="补充说明（选填，最多 300 字）"></textarea>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '  <div class="mrp-bar">' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '    <button type="button" class="btn-sm mrp-cancel">再想想</button>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '    <button type="button" class="btn-primary btn-sm mrp-submit" disabled>提交举报</button>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '  </div>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '</div>';
        //> 把子节点追加到当前元素内部末尾
        document.body.appendChild(reportModal);
        //> 返回结果并结束当前函数
        return reportModal;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    //> 声明变量「reportState」（report state），用于保存对应数据
    var reportState = { url: '', reason: '' };
    // =========================================================
    // 【函数】openReport
    // 功能：打开「report」相关逻辑（open report）
    // 参数：
    //   - url：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function openReport(url) {
        //> 声明变量「m」（m），用于保存对应数据
        var m = ensureReportModal();
        //> 给「reportState」赋值，更新其保存的状态
        reportState = { url: url, reason: '' };
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        m.querySelectorAll('.mrp-reason').forEach(function (b) { b.classList.remove('active'); });
        //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
        m.querySelector('.mrp-detail').value = '';
        //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
        m.querySelector('.mrp-submit').disabled = true;
        //> 给「m.hidden」赋值，更新其保存的状态
        m.hidden = false;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // =========================================================
    // 【函数】closeReport
    // 功能：关闭「report」相关逻辑（close report）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function closeReport() { if (reportModal) reportModal.hidden = true; }
    //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    document.addEventListener('click', function (e) {
        //> 声明变量「btn」（btn），用于保存对应数据
        var btn = e.target.closest('[data-report-url]');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!btn) return;
        //> 阻止事件的默认行为（如表单提交、链接跳转）
        e.preventDefault();
        //> 读取元素的 HTML 属性值
        openReport(btn.getAttribute('data-report-url'));
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
    //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    document.addEventListener('click', function (e) {
        //> 条件判断：满足括号内条件时执行对应分支
        if (!reportModal || reportModal.hidden) return;
        //> 条件判断：满足括号内条件时执行对应分支
        if (e.target.classList.contains('mrp-reason')) {
            //> 读取元素的 HTML 属性值
            reportState.reason = e.target.getAttribute('data-reason');
            //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
            reportModal.querySelectorAll('.mrp-reason').forEach(function (b) { b.classList.remove('active'); });
            //> 为元素添加一个或多个样式类
            e.target.classList.add('active');
            //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
            reportModal.querySelector('.mrp-submit').disabled = false;
        //> 否则若满足该条件则进入此分支
        } else if (e.target.classList.contains('mrp-close') || e.target.classList.contains('mrp-cancel')) {
            //> 调用函数「closeReport」并传入参数执行对应逻辑
            closeReport();
        //> 否则若满足该条件则进入此分支
        } else if (e.target === reportModal) {
            //> 调用函数「closeReport」并传入参数执行对应逻辑
            closeReport();
        //> 否则若满足该条件则进入此分支
        } else if (e.target.classList.contains('mrp-submit')) {
            //> 声明变量「detail」（detail），用于保存对应数据
            var detail = reportModal.querySelector('.mrp-detail').value.trim();
            //> 声明变量「submitBtn」（submit btn），用于保存对应数据
            var submitBtn = e.target;
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            submitBtn.disabled = true; submitBtn.textContent = '提交中…';
            //> 调用函数「post」并传入参数执行对应逻辑
            post(reportState.url, 'POST', { reason: reportState.reason, detail: detail })
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                .then(function (d) {
                    //> 调用函数「closeReport」并传入参数执行对应逻辑
                    closeReport();
                    // 兼容两种响应包：扁平 {success:true} 与统一信封 {code:0,data:{success:true}}
                    //> 声明变量「ok」（ok），用于保存对应数据
                    var ok = d && (d.success === true ||
                        //> 该行执行对应的脚本逻辑（结合上下文理解）
                        (d.data && d.data.success === true) || d.code === 0);
                    //> 调用函数「toast」并传入参数执行对应逻辑
                    toast(ok ? '举报已提交，感谢守护~' : '提交失败，稍后再试');
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                })
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                .catch(function () { toast('提交失败，稍后再试'); })
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                .then(function () { submitBtn.textContent = '提交举报'; });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
    //> 绑定「keydown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    document.addEventListener('keydown', function (e) {
        //> 条件判断：满足括号内条件时执行对应分支
        if (e.key === 'Escape' && reportModal && !reportModal.hidden) closeReport();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- C6 图片评论上传 ---------- */
    //> 声明变量「imgInput」（img input），用于保存对应数据，保存 DOM/窗口相关对象
    var imgInput = document.querySelector('[data-comment-image-input]');
    //> 条件判断：满足括号内条件时执行对应分支
    if (imgInput) {
        //> 绑定「change」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        imgInput.addEventListener('change', function () {
            //> 声明变量「file」（file），用于保存对应数据
            var file = imgInput.files[0];
            //> 条件判断：满足括号内条件时执行对应分支
            if (!file) return;
            //> 声明变量「fd」（fd），用于保存对应数据
            var fd = new FormData(); fd.append('image', file);
            //> 读取元素的 HTML 属性值
            fetch(imgInput.getAttribute('data-upload-url') || '/api/comment/image/upload/', {
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                method: 'POST',
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                headers: { 'X-CSRFToken': cookie('csrftoken') },
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                body: fd, credentials: 'same-origin'
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }).then(function (r) { return r.json(); }).then(function (d) {
                // Bug4：兼容统一信封 {code,data:{url}} 与扁平 {url} 两种返回结构
                //> 声明变量「payload」（payload），用于保存对应数据
                var payload = d && d.data ? d.data : d;
                //> 声明变量「ta」（ta），用于保存对应数据，保存 DOM/窗口相关对象
                var ta = document.querySelector('#comment-input, textarea[name="content"]');
                // 直接插入 <img> 标签（bleach 已放行 img），提交后即可真正显示图片
                //> 条件判断：满足括号内条件时执行对应分支
                if (ta && payload.url) {
                    //> 操作「ta」的相关方法/属性
                    ta.value += '\n<img src="' + payload.url + '" alt="评论图片">\n';
                    //> 操作「ta」的相关方法/属性
                    ta.focus();
                    //> 创建并派发自定义事件，实现模块间解耦通信
                    ta.dispatchEvent(new Event('input', { bubbles: true }));
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
                //> 调用函数「toast」并传入参数执行对应逻辑
                toast('图片已插入~');
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }).catch(function () { toast('图片上传失败'); });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- C7 楼层跳转 ---------- */
    //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
    document.querySelectorAll('.comment-floor').forEach(function (fl) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        fl.addEventListener('click', function () {
            //> 声明变量「target」（target），用于保存对应数据，保存 DOM/窗口相关对象
            var target = document.getElementById('comment-' + fl.getAttribute('data-floor'));
            //> 条件判断：满足括号内条件时执行对应分支
            if (target) target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- C8 只看楼主（工单7：绑定 #only-author 复选框） ---------- */
    //> 声明变量「opBtn」（op btn），用于保存对应数据，保存 DOM/窗口相关对象
    var opBtn = document.getElementById('only-author') ||
               //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
               document.querySelector('[data-op-only]');
    //> 声明变量「opList」（op list），用于保存对应数据，保存 DOM/窗口相关对象
    var opList = document.getElementById('comment-flat-list') ||
                 //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
                 document.querySelector('.comment-list') || document.getElementById('comments');
    // =========================================================
    // 【函数】applyOpOnly
    // 功能：应用「op only」相关逻辑（apply op only）
    // 参数：
    //   - on：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function applyOpOnly(on) {
        //> 声明变量「shown」（shown），用于保存对应数据
        var shown = 0;
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        document.querySelectorAll('.comment-item').forEach(function (it) {
            //> 声明变量「hide」（hide），用于保存对应数据
            var hide = on && !it.classList.contains('is-op');
            //> 切换样式类（有则移除、无则添加），可传第二参强制状态
            it.classList.toggle('op-only-hidden', hide);
            //> 条件判断：满足括号内条件时执行对应分支
            if (!hide) shown++;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        //> 切换样式类（有则移除、无则添加），可传第二参强制状态
        document.body.classList.toggle('op-only-on', on);
        // 工单7：楼主一条评论都没有时给出萌系空状态，避免勾选后一片空白
        //> 声明变量「note」（note），用于保存对应数据，保存 DOM/窗口相关对象
        var note = document.getElementById('op-only-empty');
        //> 条件判断：满足括号内条件时执行对应分支
        if (on && shown === 0) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (!note) {
                //> 创建新的 DOM 元素节点，后续需挂载到文档才显示
                note = document.createElement('div');
                //> 给「note.id」赋值，更新其保存的状态
                note.id = 'op-only-empty';
                //> 给「note.className」赋值，更新其保存的状态
                note.className = 'op-only-empty';
                //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
                note.innerHTML = '🐣 <span>楼主还没有回复评论喵，去抢沙发吧~</span>';
                //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
                (opList || document.querySelector('.comments-section') || document.body).appendChild(note);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 给「note.style.display」赋值，更新其保存的状态
            note.style.display = '';
        //> 否则若满足该条件则进入此分支
        } else if (note) {
            //> 给「note.style.display」赋值，更新其保存的状态
            note.style.display = 'none';
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    //> 条件判断：满足括号内条件时执行对应分支
    if (opBtn) {
        //> 绑定「change」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        opBtn.addEventListener('change', function () {
            //> 调用函数「applyOpOnly」并传入参数执行对应逻辑
            applyOpOnly(opBtn.checked);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        // 新评论（AJAX 插入）后若过滤开启，自动重新应用，避免非楼主评论漏出
        //> 声明变量「flatList」（flat list），用于保存对应数据，保存 DOM/窗口相关对象
        var flatList = document.getElementById('comment-flat-list') ||
                      //> 按 id 获取单个元素，不存在时返回 null
                      document.getElementById('comments');
        //> 条件判断：满足括号内条件时执行对应分支
        if (flatList && 'MutationObserver' in window) {
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            new MutationObserver(function () {
                //> 条件判断：满足括号内条件时执行对应分支
                if (opBtn.checked) applyOpOnly(true);
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }).observe(flatList, { childList: true });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- C10 收藏夹切换 ---------- */
    //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
    document.querySelectorAll('.favorite-folder').forEach(function (f) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        f.addEventListener('click', function () {
            //> 声明变量「name」（name），用于保存对应数据
            var name = f.getAttribute('data-folder');
            //> 声明变量「url」（url），用于保存对应数据，初始为字符串
            var url = '/api/favorites/?folder=' + encodeURIComponent(name);
            //> 通过赋值跳转页面
            location.href = url;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- C11/C12 评论字数 + 草稿自动保存 ---------- */
    //> 声明变量「ta」（ta），用于保存对应数据，保存 DOM/窗口相关对象
    var ta = document.querySelector('.comment-input, #id_content_comment, textarea[name="comment"]');
    //> 条件判断：满足括号内条件时执行对应分支
    if (ta) {
        //> 声明变量「draftKey」（draft key），用于保存对应数据，初始为字符串
        var draftKey = 'blog_comment_draft_' + (location.pathname);
        //> 尝试执行可能出错的代码，出错则进入 catch
        try { var saved = localStorage.getItem(draftKey); if (saved) ta.value = saved; } catch (e) {}
        //> 声明变量「wc」（wc），用于保存对应数据，保存 DOM/窗口相关对象
        var wc = document.querySelector('.comment-wc');
        //> 声明变量「timer」（timer），用于保存对应数据
        var timer = null;
        //> 绑定「input」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        ta.addEventListener('input', function () {
            //> 条件判断：满足括号内条件时执行对应分支
            if (wc) wc.textContent = (ta.value || '').length + ' 字';
            //> 清除对应的定时器，防止其继续执行
            clearTimeout(timer);
            //> 设置延时执行的定时器，返回可清除的定时器 id
            timer = setTimeout(function () {
                //> 尝试执行可能出错的代码，出错则进入 catch
                try { localStorage.setItem(draftKey, ta.value || ''); } catch (e) {}
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }, 800);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        //> 绑定「submit」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        ta.form && ta.form.addEventListener('submit', function () {
            //> 尝试执行可能出错的代码，出错则进入 catch
            try { localStorage.removeItem(draftKey); } catch (e) {}
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- C13 评论撤回（5分钟内，Bug8：站内萌系确认） ----------
       //> 该行执行对应的脚本逻辑（结合上下文理解）
       事件委托到 document：AJAX 新插入的评论节点同样可撤回（直接绑定会漏掉动态节点） */
    //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    document.addEventListener('click', function (e) {
        //> 声明变量「btn」（btn），用于保存对应数据
        var btn = e.target.closest('[data-recall-url]');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!btn) return;
        //> 调用函数「moeConfirm」并传入参数执行对应逻辑
        moeConfirm({ message: '确定撤回这条评论吗？', danger: true, confirmText: '撤回' })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .then(function (ok) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (!ok) return;
                //> 读取元素的 HTML 属性值
                post(btn.getAttribute('data-recall-url'), 'DELETE').then(function () {
                    //> 声明变量「item」（item），用于保存对应数据
                    var item = btn.closest('.comment-item'); if (item) item.remove();
                    // 撤回后同步减评论数（与后端重算结果一致；下一个整页刷新时以服务端为准）
                    //> 声明变量「cc」（cc），用于保存对应数据，保存 DOM/窗口相关对象
                    var cc = document.getElementById('comments-count');
                    //> 条件判断：满足括号内条件时执行对应分支
                    if (cc) {
                        //> 声明变量「n」（n），用于保存对应数据
                        var n = parseInt(cc.textContent, 10);
                        //> 条件判断：满足括号内条件时执行对应分支
                        if (!isNaN(n) && n > 0) cc.textContent = n - 1;
                    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                    }
                    //> 调用函数「toast」并传入参数执行对应逻辑
                    toast('已撤回~');
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                }).catch(function () { toast('撤回失败（可能超过时限）'); });
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- C14 点赞爱心爆炸 ---------- */
    //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    document.addEventListener('click', function (e) {
        //> 声明变量「like」（like），用于保存对应数据
        var like = e.target.closest('.like-btn, [data-like-success]');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!like) return;
        //> 声明变量「cx」（cx），用于保存对应数据
        var cx = e.clientX, cy = e.clientY;
        //> 循环：按条件重复执行循环体
        for (var i = 0; i < 8; i++) {
            //> 声明变量「h」（h），用于保存对应数据，保存 DOM/窗口相关对象
            var h = document.createElement('span');
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            h.className = 'heart-burst'; h.textContent = '💗';
            //> 给「h.style.left」赋值，更新其保存的状态
            h.style.left = cx + 'px'; h.style.top = cy + 'px';
            //> 操作「h.style」的相关方法/属性
            h.style.setProperty('--dx', (Math.random() * 80 - 40) + 'px');
            //> 操作「h.style」的相关方法/属性
            h.style.setProperty('--dy', (-Math.random() * 80 - 20) + 'px');
            //> 把子节点追加到当前元素内部末尾
            document.body.appendChild(h);
            //> 把元素从 DOM 中移除
            setTimeout(function (el) { if (el && el.remove) el.remove(); }, 900, h);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- C15 分享感谢弹窗 ---------- */
    //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    document.addEventListener('click', function (e) {
        //> 声明变量「sh」（sh），用于保存对应数据
        var sh = e.target.closest('[data-share-thanks]');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!sh) return;
        //> 声明变量「mask」（mask），用于保存对应数据，保存 DOM/窗口相关对象
        var mask = document.createElement('div');
        //> 给「mask.className」赋值，更新其保存的状态
        mask.className = 'thanks-modal-mask';
        //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
        mask.innerHTML = '<div class="thanks-modal"><div class="thanks-icon">🎉</div>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '<h4>感谢分享！</h4><p>你的分享是对作者最大的鼓励~</p></div>';
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        mask.addEventListener('click', function () { mask.remove(); });
        //> 把子节点追加到当前元素内部末尾
        document.body.appendChild(mask);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- C16 右栏热门文章 周/月/总榜切换（AJAX 拉取片段，带本地缓存） ---------- */
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    (function () {
        //> 声明变量「tabsBox」（tabs box），用于保存对应数据，保存 DOM/窗口相关对象
        var tabsBox = document.querySelector('.hot-rank-tabs');
        //> 声明变量「list」（list），用于保存对应数据，保存 DOM/窗口相关对象
        var list = document.querySelector('.widget .hot-list');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!tabsBox || !list) return;
        //> 声明变量「mem」（mem），用于保存对应数据
        var mem = {};   // 本次会话内已加载片段缓存，避免重复请求
        // =========================================================
        // 【函数】setActive
        // 功能：设置「active」相关逻辑（set active）
        // 参数：
        //   - range：传入的参数（含义结合调用处与函数体）
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function setActive(range) {
            //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
            tabsBox.querySelectorAll('.hot-rank-tab').forEach(function (t) {
                //> 切换样式类（有则移除、无则添加），可传第二参强制状态
                t.classList.toggle('active', t.getAttribute('data-range') === range);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // =========================================================
        // 【函数】load
        // 功能：加载相关逻辑（load）
        // 参数：
        //   - range：传入的参数（含义结合调用处与函数体）
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function load(range) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (mem[range]) { list.innerHTML = mem[range]; setActive(range); return; }
            //> 为元素添加一个或多个样式类
            list.classList.add('hot-loading');
            //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
            fetch('/api/hot-articles/?range=' + encodeURIComponent(range), {
                //> 使用 XHR 发起传统异步请求
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                credentials: 'same-origin'
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }).then(function (r) { if (!r.ok) throw new Error('bad'); return r.text(); })
              //> 该行执行对应的脚本逻辑（结合上下文理解）
              .then(function (html) {
                  //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
                  mem[range] = html; list.innerHTML = html; setActive(range);
              //> 该行执行对应的脚本逻辑（结合上下文理解）
              }).catch(function () {
                  //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
                  list.innerHTML = '<li class="muted">榜单加载失败喵，稍后再试~</li>';
              //> 移除元素的一个或多个样式类
              }).then(function () { list.classList.remove('hot-loading'); });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        tabsBox.addEventListener('click', function (e) {
            //> 声明变量「tab」（tab），用于保存对应数据
            var tab = e.target.closest('.hot-rank-tab');
            //> 条件判断：满足括号内条件时执行对应分支
            if (tab) load(tab.getAttribute('data-range'));
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    })();
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

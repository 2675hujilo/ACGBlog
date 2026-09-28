/* Bug11 文件头注释
 * 全站公共脚本：页面通用工具与初始化，所有页面加载。
 * 主要逻辑：①工具提示 initTooltip（Bug9 已改浅色系）；②moeToast 右下角轻提示并暴露到 window；
 * ③相对时间格式化；④通用 fetch/CSRF 封装；⑤主题、菜单等公共交互的初始化。
 */
//> 该行执行对应的脚本逻辑（结合上下文理解）
﻿/**
 * common.js —— 全站通用前端交互脚本（瘦身版）
 *
 * 功能：
 *   1. 顶部阅读进度条：随滚动实时更新宽度
 *   2. 回到顶部按钮：滚动超过 400px 显示，带环形进度
 *   3. Flash 消息自动淡出
 *   4. 骨架屏隐藏：DOM 就绪后渐隐
 *   5. 数字滚动动画：[data-count] 从 0 滚动到目标值
 *   6. 入场动画：IntersectionObserver 观察 .animate-in
 *   7. 按钮涟漪效果（事件委托）
 *   8. 搜索自动补全：debounce 300ms，键盘上下选择
 *   9. 快捷键盘导航：j/k 移动文章，/ 聚焦搜索，gg 回顶，? 帮助
 *  10. 图片加载失败占位：粉紫蓝渐变 SVG
 *  11. 全局自定义 tooltip：hover 300ms 淡入
 *
 * 依赖：无（纯原生 JS）
 * 注：暗黑模式切换由 theme.js 独立负责，本文件不再重复绑定 #theme-toggle
 */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';

    /* ====== 阅读进度 / 回到顶部 / Flash 淡出 ====== */
    //> 声明变量「progress」（progress），用于保存对应数据，保存 DOM/窗口相关对象
    var progress = document.getElementById('reading-progress');
    //> 声明变量「topBtn」（top btn），用于保存对应数据，保存 DOM/窗口相关对象
    var topBtn = document.getElementById('back-to-top');
    //> 声明变量「header」（header），用于保存对应数据，保存 DOM/窗口相关对象
    var header = document.querySelector('.site-header');
    //> 声明变量「ringFg」（ring fg），用于保存对应数据
    var ringFg = topBtn ? topBtn.querySelector('.btt-ring-fg') : null;
    //> 声明变量「RING_LEN」（ring len），用于保存对应数据
    var RING_LEN = 2 * Math.PI * 22;

    // =========================================================
    // 【函数】onScroll
    // 功能：处理……事件「scroll」相关逻辑（on scroll）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function onScroll() {
        //> 声明变量「doc」（doc），用于保存对应数据，保存 DOM/窗口相关对象
        var doc = document.documentElement;
        //> 声明变量「total」（total），用于保存对应数据
        var total = doc.scrollHeight - doc.clientHeight;
        //> 声明变量「ratio」（ratio），用于保存对应数据
        var ratio = total > 0 ? (doc.scrollTop || document.body.scrollTop) / total : 0;
        //> 条件判断：满足括号内条件时执行对应分支
        if (progress) progress.style.width = Math.round(ratio * 100) + '%';
        //> 条件判断：满足括号内条件时执行对应分支
        if (topBtn) topBtn.classList.toggle('show', doc.scrollTop > 400);
        //> 条件判断：满足括号内条件时执行对应分支
        if (ringFg) {
            //> 给「ringFg.style.strokeDasharray」赋值，更新其保存的状态
            ringFg.style.strokeDasharray = RING_LEN;
            //> 给「ringFg.style.strokeDashoffset」赋值，更新其保存的状态
            ringFg.style.strokeDashoffset = RING_LEN * (1 - ratio);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 条件判断：满足括号内条件时执行对应分支
        if (header) header.classList.toggle('scrolled', doc.scrollTop > 50);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    //> 绑定「scroll」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    window.addEventListener('scroll', onScroll, { passive: true });
    //> 调用函数「onScroll」并传入参数执行对应逻辑
    onScroll();

    //> 条件判断：满足括号内条件时执行对应分支
    if (topBtn) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        topBtn.addEventListener('click', function () {
            //> 程序化滚动窗口到指定位置
            window.scrollTo({ top: 0, behavior: 'smooth' });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
    document.querySelectorAll('.flash').forEach(function (el) {
        // =========================================================
        // 【函数】setTimeout
        // 功能：设置「timeout」相关逻辑（set timeout）
        // 参数：
        //   - function：传入的参数（含义结合调用处与函数体）
        //   - (：传入的参数（含义结合调用处与函数体）
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：含定时器，注意在适当时机清除，避免泄漏与重复触发
        // =========================================================
        setTimeout(function () {
            //> 给「el.style.transition」赋值，更新其保存的状态
            el.style.transition = 'opacity .6s';
            //> 给「el.style.opacity」赋值，更新其保存的状态
            el.style.opacity = '0';
            //> 把元素从 DOM 中移除
            setTimeout(function () { el.remove(); }, 700);
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }, 4000);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ====== 骨架屏隐藏 ====== */
    // =========================================================
    // 【函数】hideSkeleton
    // 功能：隐藏「skeleton」相关逻辑（hide skeleton）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function hideSkeleton() {
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        document.querySelectorAll('.skeleton-wrap').forEach(function (w) {
            //> 为元素添加一个或多个样式类
            w.classList.add('hidden');
            //> 把元素从 DOM 中移除
            setTimeout(function () { w.remove(); }, 450);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    //> 条件判断：满足括号内条件时执行对应分支
    if (document.readyState === 'loading') {
        //> 绑定「DOMContentLoaded」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('DOMContentLoaded', hideSkeleton);
    //> 以上条件都不满足时执行的兜底分支
    } else {
        //> 调用函数「hideSkeleton」并传入参数执行对应逻辑
        hideSkeleton();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ====== 数字滚动动画 ====== */
    // =========================================================
    // 【函数】animateNumber
    // 功能：执行动画「number」相关逻辑（animate number）
    // 参数：
    //   - el：传入的参数（含义结合调用处与函数体）
    //   - target：传入的参数（含义结合调用处与函数体）
    //   - duration：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function animateNumber(el, target, duration) {
        //> 声明变量「start」（start），用于保存对应数据
        var start = null;
        // =========================================================
        // 【函数】step
        // 功能：处理「step」相关逻辑（common）
        // 参数：
        //   - ts：传入的参数（含义结合调用处与函数体）
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function step(ts) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (start === null) start = ts;
            //> 声明变量「ratio」（ratio），用于保存对应数据
            var ratio = Math.min((ts - start) / duration, 1);
            //> 声明变量「eased」（eased），用于保存对应数据
            var eased = 1 - Math.pow(1 - ratio, 3);
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            el.textContent = Math.round(target * eased).toLocaleString('en-US');
            //> 条件判断：满足括号内条件时执行对应分支
            if (ratio < 1) requestAnimationFrame(step);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 在下一帧重绘前执行回调，是流畅动画的标准做法
        requestAnimationFrame(step);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // =========================================================
    // 【函数】initAnimatedNumbers
    // 功能：初始化「animated numbers」相关逻辑（init animated numbers）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function initAnimatedNumbers() {
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        document.querySelectorAll('[data-count]').forEach(function (el) {
            //> 读取元素的 HTML 属性值
            animateNumber(el, parseInt(el.getAttribute('data-count'), 10) || 0, 1200);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ====== 入场动画 IntersectionObserver ====== */
    // =========================================================
    // 【函数】initEntranceObserver
    // 功能：初始化「entrance observer」相关逻辑（init entrance observer）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function initEntranceObserver() {
        //> 声明变量「items」（items），用于保存对应数据，保存 DOM/窗口相关对象
        var items = document.querySelectorAll('.animate-in, .scroll-fade-in');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!items.length) return;
        //> 条件判断：满足括号内条件时执行对应分支
        if (!('IntersectionObserver' in window)) {
            //> 为元素添加一个或多个样式类
            items.forEach(function (el) { el.classList.add('visible'); });
            //> 提前结束函数，无返回值
            return;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 声明变量「io」（io），用于保存对应数据
        var io = new IntersectionObserver(function (entries) {
            //> 遍历数组/类数组中的每一项并执行回调
            entries.forEach(function (entry) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (entry.isIntersecting) {
                    //> 为元素添加一个或多个样式类
                    entry.target.classList.add('visible');
                    //> 操作「io」的相关方法/属性
                    io.unobserve(entry.target);
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }, { threshold: 0.05 });
        //> 遍历数组/类数组中的每一项并执行回调
        items.forEach(function (el) { io.observe(el); });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ====== 按钮涟漪效果 ====== */
    // =========================================================
    // 【函数】initRipple
    // 功能：初始化「ripple」相关逻辑（init ripple）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function initRipple() {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('click', function (e) {
            //> 声明变量「target」（target），用于保存对应数据
            var target = e.target.closest('button, .btn-primary, .page-link, .like-btn, .fav-btn, .btn-sm');
            //> 条件判断：满足括号内条件时执行对应分支
            if (!target) return;
            //> 声明变量「rect」（rect），用于保存对应数据
            var rect = target.getBoundingClientRect();
            //> 声明变量「size」（size），用于保存对应数据
            var size = Math.max(rect.width, rect.height);
            //> 声明变量「span」（span），用于保存对应数据，保存 DOM/窗口相关对象
            var span = document.createElement('span');
            //> 给「span.className」赋值，更新其保存的状态
            span.className = 'ripple';
            //> 给「span.style.width」赋值，更新其保存的状态
            span.style.width = span.style.height = size + 'px';
            //> 给「span.style.left」赋值，更新其保存的状态
            span.style.left = ((e.clientX ? e.clientX - rect.left : rect.width / 2) - size / 2) + 'px';
            //> 给「span.style.top」赋值，更新其保存的状态
            span.style.top = ((e.clientY ? e.clientY - rect.top : rect.height / 2) - size / 2) + 'px';
            //> 把子节点追加到当前元素内部末尾
            target.appendChild(span);
            //> 绑定「animationend」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            span.addEventListener('animationend', function () { span.remove(); });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ====== 搜索自动补全 ====== */
    // =========================================================
    // 【函数】initSearchSuggest
    // 功能：初始化「search suggest」相关逻辑（init search suggest）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function initSearchSuggest() {
        //> 声明变量「form」（form），用于保存对应数据，保存 DOM/窗口相关对象
        var form = document.querySelector('.nav-search');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!form) return;
        //> 声明变量「input」（input），用于保存对应数据
        var input = form.querySelector('input[name="q"]');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!input) return;
        //> 声明变量「list」（list），用于保存对应数据，保存 DOM/窗口相关对象
        var list = document.createElement('ul');
        //> 给「list.className」赋值，更新其保存的状态
        list.className = 'search-suggestions';
        //> 把子节点追加到当前元素内部末尾
        form.appendChild(list);
        //> 声明变量「debounceTimer」（debounce timer），用于保存对应数据
        var debounceTimer = null, activeIndex = -1;

        // =========================================================
        // 【函数】renderItems
        // 功能：渲染「items」相关逻辑（render items）
        // 参数：
        //   - items：传入的参数（含义结合调用处与函数体）
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function renderItems(items) {
            //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
            list.innerHTML = '';
            //> 条件判断：满足括号内条件时执行对应分支
            if (!items.length) { list.classList.remove('show'); return; }
            //> 遍历数组/类数组中的每一项并执行回调
            items.forEach(function (text) {
                //> 声明变量「li」（li），用于保存对应数据，保存 DOM/窗口相关对象
                var li = document.createElement('li');
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                li.textContent = text;
                //> 绑定「mousedown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
                li.addEventListener('mousedown', function (e) {
                    //> 阻止事件的默认行为（如表单提交、链接跳转）
                    e.preventDefault();
                    //> 给「input.value」赋值，更新其保存的状态
                    input.value = text;
                    //> 移除元素的一个或多个样式类
                    list.classList.remove('show');
                    //> 操作「form」的相关方法/属性
                    form.submit();
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                });
                //> 把子节点追加到当前元素内部末尾
                list.appendChild(li);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            //> 为元素添加一个或多个样式类
            list.classList.add('show');
            //> 给「activeIndex」赋值，更新其保存的状态
            activeIndex = -1;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // =========================================================
        // 【函数】fetchSuggest
        // 功能：请求并获取「suggest」相关逻辑（fetch suggest）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function fetchSuggest() {
            //> 声明变量「q」（q），用于保存对应数据
            var q = input.value.trim();
            //> 条件判断：满足括号内条件时执行对应分支
            if (!q) { list.classList.remove('show'); return; }
            //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
            fetch('/api/search/suggest/?q=' + encodeURIComponent(q))
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                .then(function (r) { return r.json(); })
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                .then(function (data) { renderItems(data.suggestions || []); })
                //> 移除元素的一个或多个样式类
                .catch(function () { list.classList.remove('show'); });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 绑定「input」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        input.addEventListener('input', function () {
            //> 清除对应的定时器，防止其继续执行
            clearTimeout(debounceTimer);
            //> 设置延时执行的定时器，返回可清除的定时器 id
            debounceTimer = setTimeout(fetchSuggest, 300);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        //> 绑定「keydown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        input.addEventListener('keydown', function (e) {
            //> 声明变量「items」（items），用于保存对应数据
            var items = list.querySelectorAll('li');
            //> 条件判断：满足括号内条件时执行对应分支
            if (e.key === 'ArrowDown' && items.length) {
                //> 阻止事件的默认行为（如表单提交、链接跳转）
                e.preventDefault(); activeIndex = (activeIndex + 1) % items.length;
            //> 否则若满足该条件则进入此分支
            } else if (e.key === 'ArrowUp' && items.length) {
                //> 阻止事件的默认行为（如表单提交、链接跳转）
                e.preventDefault(); activeIndex = (activeIndex - 1 + items.length) % items.length;
            //> 否则若满足该条件则进入此分支
            } else if (e.key === 'Enter') {
                //> 条件判断：满足括号内条件时执行对应分支
                if (activeIndex >= 0 && items[activeIndex]) {
                    //> 读写纯文本内容，不解析 HTML，可防 XSS
                    input.value = items[activeIndex].textContent;
                    //> 移除元素的一个或多个样式类
                    list.classList.remove('show');
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
                //> 提前结束函数，无返回值
                return;
            //> 否则若满足该条件则进入此分支
            } else if (e.key === 'Escape') {
                //> 移除元素的一个或多个样式类
                list.classList.remove('show');
            //> 以上条件都不满足时执行的兜底分支
            } else { return; }
            //> 切换样式类（有则移除、无则添加），可传第二参强制状态
            items.forEach(function (li, i) { li.classList.toggle('active', i === activeIndex); });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('click', function (e) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (!form.contains(e.target)) list.classList.remove('show');
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ====== 快捷键盘导航 ====== */

    /* ====== 键盘快捷键帮助面板（? 键与导航栏 ⌨ 按钮共用，全局单例） ====== */
    //> 声明变量「kbdHelpEl」（kbd help el），用于保存对应数据
    var kbdHelpEl = null;
    // =========================================================
    // 【函数】getKbdHelp
    // 功能：获取「kbd help」相关逻辑（get kbd help）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function getKbdHelp() {
        //> 条件判断：满足括号内条件时执行对应分支
        if (kbdHelpEl) return kbdHelpEl;
        //> 创建新的 DOM 元素节点，后续需挂载到文档才显示
        kbdHelpEl = document.createElement('div');
        //> 给「kbdHelpEl.className」赋值，更新其保存的状态
        kbdHelpEl.className = 'kbd-help';
        //> 设置元素的 HTML 属性
        kbdHelpEl.setAttribute('role', 'dialog');
        //> 设置元素的 HTML 属性
        kbdHelpEl.setAttribute('aria-label', '键盘快捷键');
        //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
        kbdHelpEl.innerHTML =
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '<div class="kbd-help-card">' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '<div class="kbd-help-head"><strong>⌨️ 键盘快捷键喵</strong><button type="button" class="kbd-help-close" aria-label="关闭">×</button></div>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '<div class="kbd-help-grid">' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '<div class="kbd-row"><kbd>j</kbd><kbd>k</kbd><span>下移 / 上移文章</span></div>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '<div class="kbd-row"><kbd>Enter</kbd><span>打开高亮文章</span></div>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '<div class="kbd-row"><kbd>/</kbd><span>聚焦搜索框</span></div>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '<div class="kbd-row"><kbd>g</kbd><kbd>g</kbd><span>回到顶部</span></div>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '<div class="kbd-row"><kbd>?</kbd><span>显示 / 隐藏本面板</span></div>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '<div class="kbd-row"><kbd>Esc</kbd><span>关闭弹窗 / 取消输入</span></div>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '</div></div>';
        //> 把子节点追加到当前元素内部末尾
        document.body.appendChild(kbdHelpEl);
        // 点击遮罩或关闭按钮收起
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        kbdHelpEl.addEventListener('click', function (e) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (e.target === kbdHelpEl || e.target.closest('.kbd-help-close')) {
                //> 移除元素的一个或多个样式类
                kbdHelpEl.classList.remove('show');
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        //> 返回结果并结束当前函数
        return kbdHelpEl;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // =========================================================
    // 【函数】toggleKbdHelp
    // 功能：切换「kbd help」相关逻辑（toggle kbd help）
    // 参数：
    //   - force：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function toggleKbdHelp(force) {
        //> 声明变量「h」（h），用于保存对应数据
        var h = getKbdHelp();
        //> 声明变量「show」（show），用于保存对应数据，值为一个函数
        var show = (typeof force === 'boolean') ? force : !h.classList.contains('show');
        //> 切换样式类（有则移除、无则添加），可传第二参强制状态
        h.classList.toggle('show', show);
        //> 条件判断：满足括号内条件时执行对应分支
        if (show) { var b = h.querySelector('.kbd-help-close'); if (b) b.focus(); }
        //> 返回结果并结束当前函数
        return show;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // =========================================================
    // 【函数】initKeyboardNav
    // 功能：初始化「keyboard nav」相关逻辑（init keyboard nav）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function initKeyboardNav() {
        //> 声明变量「focusedIndex」（focused index），用于保存对应数据
        var focusedIndex = -1, gPressedAt = 0;
        // =========================================================
        // 【函数】isTyping
        // 功能：判断是否为「typing」相关逻辑（is typing）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function isTyping() {
            //> 声明变量「el」（el），用于保存对应数据，保存 DOM/窗口相关对象
            var el = document.activeElement;
            //> 返回结果并结束当前函数
            return el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // =========================================================
        // 【函数】getCards
        // 功能：获取「cards」相关逻辑（get cards）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function getCards() {
            //> 返回结果并结束当前函数
            return Array.prototype.slice.call(document.querySelectorAll('.article-card'));
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // =========================================================
        // 【函数】moveFocus
        // 功能：处理「move focus」相关逻辑（common）
        // 参数：
        //   - dir：传入的参数（含义结合调用处与函数体）
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function moveFocus(dir) {
            //> 声明变量「cards」（cards），用于保存对应数据
            var cards = getCards();
            //> 条件判断：满足括号内条件时执行对应分支
            if (!cards.length) return;
            //> 移除元素的一个或多个样式类
            cards.forEach(function (c) { c.classList.remove('keyboard-focus'); });
            //> 给「focusedIndex」赋值，更新其保存的状态
            focusedIndex = Math.max(0, Math.min(focusedIndex + dir, cards.length - 1));
            //> 声明变量「card」（card），用于保存对应数据
            var card = cards[focusedIndex];
            //> 为元素添加一个或多个样式类
            card.classList.add('keyboard-focus');
            //> 滚动页面使元素进入可视区域
            card.scrollIntoView({ block: 'center', behavior: 'smooth' });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 绑定「keydown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('keydown', function (e) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (isTyping()) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (e.key === 'Escape') {
                    //> 操作「document.activeElement」的相关方法/属性
                    document.activeElement.blur();
                    //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
                    document.querySelectorAll('.search-suggestions.show').forEach(function (l) { l.classList.remove('show'); });
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
                //> 提前结束函数，无返回值
                return;
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 声明变量「key」（key），用于保存对应数据
            var key = e.key;
            //> 条件判断：满足括号内条件时执行对应分支
            if (key === 'j') { e.preventDefault(); moveFocus(1); }
            //> 否则若满足该条件则进入此分支
            else if (key === 'k') { e.preventDefault(); moveFocus(-1); }
            //> 否则若满足该条件则进入此分支
            else if (key === '/') {
                //> 阻止事件的默认行为（如表单提交、链接跳转）
                e.preventDefault();
                //> 声明变量「s」（s），用于保存对应数据，保存 DOM/窗口相关对象
                var s = document.querySelector('.nav-search input[name="q"]');
                //> 条件判断：满足括号内条件时执行对应分支
                if (s) s.focus();
            //> 否则若满足该条件则进入此分支
            } else if (key === 'g') {
                //> 声明变量「now」（now），用于保存对应数据
                var now = Date.now();
                //> 条件判断：满足括号内条件时执行对应分支
                if (now - gPressedAt < 500) window.scrollTo({ top: 0, behavior: 'smooth' });
                //> 给「gPressedAt」赋值，更新其保存的状态
                gPressedAt = now;
            //> 否则若满足该条件则进入此分支
            } else if (key === 'Enter' && focusedIndex >= 0) {
                //> 声明变量「card」（card），用于保存对应数据
                var card = getCards()[focusedIndex];
                //> 声明变量「link」（link），用于保存对应数据
                var link = card && card.querySelector('a[href]');
                //> 条件判断：满足括号内条件时执行对应分支
                if (link) { e.preventDefault(); window.location.href = link.href; }
            //> 否则若满足该条件则进入此分支
            } else if (key === '?') {
                //> 阻止事件的默认行为（如表单提交、链接跳转）
                e.preventDefault(); toggleKbdHelp();
            //> 否则若满足该条件则进入此分支
            } else if (key === 'Escape') {
                //> 声明变量「h」（h），用于保存对应数据，保存 DOM/窗口相关对象
                var h = document.querySelector('.kbd-help.show');
                //> 条件判断：满足括号内条件时执行对应分支
                if (h) h.classList.remove('show');
                //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
                document.querySelectorAll('.search-suggestions.show').forEach(function (l) { l.classList.remove('show'); });
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ====== 图片加载失败占位 ====== */
    // =========================================================
    // 【函数】initImageFallback
    // 功能：初始化「image fallback」相关逻辑（init image fallback）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function initImageFallback() {
        // =========================================================
        // 【函数】svg
        // 功能：处理「svg」相关逻辑（common）
        // 参数：
        //   - w：传入的参数（含义结合调用处与函数体）
        //   - h：传入的参数（含义结合调用处与函数体）
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        var svg = function (w, h) {
            //> 返回结果并结束当前函数
            return 'data:image/svg+xml;utf8,' + encodeURIComponent(
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                '<svg xmlns="http://www.w3.org/2000/svg" width="' + (w || 300) +
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                '" height="' + (h || 200) + '">' +
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">' +
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                '<stop offset="0" stop-color="#ff8fb1"/><stop offset=".5" stop-color="#a06cd5"/>' +
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                '<stop offset="1" stop-color="#6ea8fe"/></linearGradient></defs>' +
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                '<rect width="100%" height="100%" fill="url(#g)"/>' +
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                '<text x="50%" y="46%" font-size="28" text-anchor="middle" fill="#fff">\ud83d\uddbc\ufe0f</text>' +
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                '<text x="50%" y="62%" font-size="13" text-anchor="middle" fill="#fff">\u56fe\u7247\u52a0\u8f7d\u5931\u8d25</text>' +
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                '</svg>');
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        };
        //> 绑定「error」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('error', function (e) {
            //> 声明变量「t」（t），用于保存对应数据
            var t = e.target;
            //> 条件判断：满足括号内条件时执行对应分支
            if (t && t.tagName === 'IMG' && !t.dataset.fbDone) {
                //> 读写元素的 data-* 自定义数据属性
                t.dataset.fbDone = '1';
                //> 给「t.src」赋值，更新其保存的状态
                t.src = svg(t.naturalWidth || t.width, t.naturalHeight || t.height);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }, true);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ====== 全局自定义 tooltip ====== */
    // =========================================================
    // 【函数】initTooltip
    // 功能：初始化「tooltip」相关逻辑（init tooltip）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function initTooltip() {        var tip = null;
        // =========================================================
        // 【函数】ensure
        // 功能：处理「ensure」相关逻辑（common）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function ensure() {
            //> 条件判断：满足括号内条件时执行对应分支
            if (tip) return tip;
            //> 创建新的 DOM 元素节点，后续需挂载到文档才显示
            tip = document.createElement('div');
            //> 给「tip.className」赋值，更新其保存的状态
            tip.className = 'ui-tooltip';
            // Bug9：兜底气泡改为浅色系（近白→浅薰衣草，深紫字），与 moe-tooltip 看板娘配色统一
            //> 给「tip.style.cssText」赋值，更新其保存的状态
            tip.style.cssText = 'position:fixed;z-index:9999;pointer-events:none;opacity:0;' +
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                'transition:opacity .2s;background:linear-gradient(135deg,rgba(255,255,255,.98),rgba(253,244,255,.98));' +
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                'color:#6b21a8;border:1px solid #e9d5ff;padding:6px 12px;' +
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                'border-radius:999px;font-size:12px;white-space:max-content;box-shadow:0 6px 20px rgba(168,85,247,.22);';
            //> 把子节点追加到当前元素内部末尾
            document.body.appendChild(tip);
            //> 返回结果并结束当前函数
            return tip;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // =========================================================
        // 【函数】show
        // 功能：显示相关逻辑（show）
        // 参数：
        //   - el：传入的参数（含义结合调用处与函数体）
        //   - text：传入的参数（含义结合调用处与函数体）
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function show(el, text) {
            //> 声明变量「t」（t），用于保存对应数据
            var t = ensure();
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            t.textContent = text;
            //> 给「t.style.opacity」赋值，更新其保存的状态
            t.style.opacity = '1';
            //> 声明变量「r」（r），用于保存对应数据
            var r = el.getBoundingClientRect();
            //> 给「t.style.left」赋值，更新其保存的状态
            t.style.left = (r.left + r.width / 2 - t.offsetWidth / 2) + 'px';
            //> 给「t.style.top」赋值，更新其保存的状态
            t.style.top = (r.top - t.offsetHeight - 8) + 'px';
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 绑定「mouseover」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('mouseover', function (e) {
            //> 声明变量「el」（el），用于保存对应数据
            var el = e.target.closest('[title]');
            //> 条件判断：满足括号内条件时执行对应分支
            if (el && el.title) {
                //> 调用函数「show」并传入参数执行对应逻辑
                show(el, el.title);
                //> 读写元素的 data-* 自定义数据属性
                el.dataset._tt = el.title;
                //> 操作「el」的相关方法/属性
                el.removeAttribute('title');
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        //> 绑定「mouseout」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('mouseout', function (e) {
            //> 声明变量「el」（el），用于保存对应数据
            var el = e.target.closest('[data-_tt]');
            //> 条件判断：满足括号内条件时执行对应分支
            if (el) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (tip) tip.style.opacity = '0';
                //> 设置元素的 HTML 属性
                el.setAttribute('title', el.dataset._tt);
                //> 读写元素的 data-* 自定义数据属性
                delete el.dataset._tt;
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ====== 双击空白区域回顶（第3轮新增） ====== */
    // =========================================================
    // 【函数】initDoubleClickTop
    // 功能：初始化「double click top」相关逻辑（init double click top）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function initDoubleClickTop() {
        // =========================================================
        // 【函数】showToast
        // 功能：显示「toast」相关逻辑（show toast）
        // 参数：
        //   - msg：传入的参数（含义结合调用处与函数体）
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function showToast(msg) {
            //> 声明变量「t」（t），用于保存对应数据，保存 DOM/窗口相关对象
            var t = document.getElementById('global-toast');
            //> 条件判断：满足括号内条件时执行对应分支
            if (!t) {
                //> 创建新的 DOM 元素节点，后续需挂载到文档才显示
                t = document.createElement('div');
                //> 给「t.id」赋值，更新其保存的状态
                t.id = 'global-toast';
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
            t._timer = setTimeout(function () { t.classList.remove('show'); }, 1500);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 绑定「dblclick」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('dblclick', function (e) {
            // 忽略交互元素 / 弹窗 / 灯箱 / 卡片内的双击
            //> 条件判断：满足括号内条件时执行对应分支
            if (e.target.closest('a, button, input, textarea, select, [contenteditable], ' +
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                '.modal, .lightbox-overlay, .read-progress-bar, .kbd-help, .article-card, ' +
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                '.comment-item, .preview-modal, .nav-bar, .site-header')) return;
            // 有选中文本时不干扰（如双击选词）
            //> 声明变量「sel」（sel），用于保存对应数据，保存 DOM/窗口相关对象
            var sel = window.getSelection && window.getSelection();
            //> 条件判断：满足括号内条件时执行对应分支
            if (sel && sel.toString().length) return;
            // 页面较顶部无需回顶
            //> 条件判断：满足括号内条件时执行对应分支
            if (window.scrollY < 300) return;
            //> 程序化滚动窗口到指定位置
            window.scrollTo({ top: 0, behavior: 'smooth' });
            //> 调用函数「showToast」并传入参数执行对应逻辑
            showToast('双击回到顶部喵~ 🐾');
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }


    /* ====== 通用折叠面板：点击 [data-collapse-target] 切换目标面板（按钮始终保留，不会把自身隐藏） ====== */
    // =========================================================
    // 【函数】initCollapse
    // 功能：初始化「collapse」相关逻辑（init collapse）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function initCollapse() {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('click', function (e) {
            //> 声明变量「btn」（btn），用于保存对应数据
            var btn = e.target.closest('[data-collapse-target]');
            //> 条件判断：满足括号内条件时执行对应分支
            if (!btn) return;
            //> 条件判断：满足括号内条件时执行对应分支
            if (btn.getAttribute('data-busy') === '1') return;
            //> 声明变量「id」（id），用于保存对应数据
            var id = btn.getAttribute('data-collapse-target');
            //> 声明变量「panel」（panel），用于保存对应数据，保存 DOM/窗口相关对象
            var panel = document.getElementById(id);
            //> 条件判断：满足括号内条件时执行对应分支
            if (!panel) return;
            //> 阻止事件的默认行为（如表单提交、链接跳转）
            e.preventDefault();
            //> 声明变量「willOpen」（will open），用于保存对应数据
            var willOpen = panel.hasAttribute('hidden');
            //> 条件判断：满足括号内条件时执行对应分支
            if (willOpen) { panel.removeAttribute('hidden'); } else { panel.setAttribute('hidden', ''); }
            //> 设置元素的 HTML 属性
            btn.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
            // 切换 caret 文案（若提供 data-text-open / data-text-closed）
            //> 声明变量「caret」（caret），用于保存对应数据
            var caret = btn.querySelector('[data-text-open]');
            //> 条件判断：满足括号内条件时执行对应分支
            if (caret) { caret.textContent = willOpen ? caret.getAttribute('data-text-open') : caret.getAttribute('data-text-closed'); }
            //> 切换样式类（有则移除、无则添加），可传第二参强制状态
            btn.classList.toggle('is-open', willOpen);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }


    /* ====== 导航栏辅助开关：交互音效 / 高对比度 / 快捷键面板按钮 ====== */
    // =========================================================
    // 【函数】initNavToggles
    // 功能：初始化「nav toggles」相关逻辑（init nav toggles）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function initNavToggles() {
        /* ---------- Bug6 交互音效（Web Audio，localStorage 持久化） ---------- */
        //> 声明变量「soundBtn」（sound btn），用于保存对应数据，保存 DOM/窗口相关对象
        var soundBtn = document.getElementById('sound-toggle');
        //> 声明变量「soundOn」（sound on），用于保存对应数据
        var soundOn = true;
        //> 尝试执行可能出错的代码，出错则进入 catch
        try { soundOn = localStorage.getItem('moe_sound') !== '0'; } catch (e) {}
        //> 声明变量「actx」（actx），用于保存对应数据
        var actx = null;
        // =========================================================
        // 【函数】playTone
        // 功能：播放「tone」相关逻辑（play tone）
        // 参数：
        //   - freq：传入的参数（含义结合调用处与函数体）
        //   - dur：传入的参数（含义结合调用处与函数体）
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function playTone(freq, dur) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (!soundOn) return;
            //> 尝试执行可能出错的代码，出错则进入 catch
            try {
                //> 给「actx」赋值，更新其保存的状态
                actx = actx || new (window.AudioContext || window.webkitAudioContext)();
                //> 条件判断：满足括号内条件时执行对应分支
                if (actx.state === 'suspended') actx.resume();
                //> 声明变量「o」（o），用于保存对应数据
                var o = actx.createOscillator(), g = actx.createGain();
                //> 给「o.type」赋值，更新其保存的状态
                o.type = 'sine'; o.frequency.value = freq;
                //> 操作「o」的相关方法/属性
                o.connect(g); g.connect(actx.destination);
                //> 声明变量「t」（t），用于保存对应数据
                var t = actx.currentTime;
                //> 操作「g.gain」的相关方法/属性
                g.gain.setValueAtTime(0.0001, t);
                //> 操作「g.gain」的相关方法/属性
                g.gain.exponentialRampToValueAtTime(0.05, t + 0.01);
                //> 操作「g.gain」的相关方法/属性
                g.gain.exponentialRampToValueAtTime(0.0001, t + (dur || 0.09));
                //> 操作「o」的相关方法/属性
                o.start(t); o.stop(t + (dur || 0.1));
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            } catch (e) {}
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 给「window.moePlayTone」赋值，更新其保存的状态
        window.moePlayTone = playTone;   // 暴露给其他脚本复用
        // =========================================================
        // 【函数】syncSound
        // 功能：同步「sound」相关逻辑（sync sound）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function syncSound() {
            //> 条件判断：满足括号内条件时执行对应分支
            if (!soundBtn) return;
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            soundBtn.textContent = soundOn ? '\uD83D\uDD0A' : '\uD83D\uDD07';
            //> 切换样式类（有则移除、无则添加），可传第二参强制状态
            soundBtn.classList.toggle('off', !soundOn);
            //> 设置元素的 HTML 属性
            soundBtn.setAttribute('aria-pressed', soundOn ? 'false' : 'true');
            //> 给「soundBtn.title」赋值，更新其保存的状态
            soundBtn.title = soundOn ? '交互音效：开（点击关闭）喵' : '交互音效：关（点击开启）喵';
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 条件判断：满足括号内条件时执行对应分支
        if (soundBtn) {
            //> 调用函数「syncSound」并传入参数执行对应逻辑
            syncSound();
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            soundBtn.addEventListener('click', function () {
                //> 给「soundOn」赋值，更新其保存的状态
                soundOn = !soundOn;
                //> 尝试执行可能出错的代码，出错则进入 catch
                try { localStorage.setItem('moe_sound', soundOn ? '1' : '0'); } catch (e) {}
                //> 调用函数「syncSound」并传入参数执行对应逻辑
                syncSound();
                //> 条件判断：满足括号内条件时执行对应分支
                if (soundOn) playTone(660, 0.1);   // 开启时给一声提示
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            // 全局轻量点击音（按钮 / 链接 / 可点击元素）
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            document.addEventListener('click', function (e) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (!soundOn) return;
                //> 条件判断：满足括号内条件时执行对应分支
                if (e.target.closest && e.target.closest('button, a, [role="button"], .clickable, .chip, .corner-badge')) {
                    //> 调用函数「playTone」并传入参数执行对应逻辑
                    playTone(500 + Math.random() * 90, 0.05);
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            // 输入打字音
            //> 绑定「keydown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            document.addEventListener('keydown', function (e) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (!soundOn) return;
                //> 声明变量「el」（el），用于保存对应数据，保存 DOM/窗口相关对象
                var el = document.activeElement;
                //> 条件判断：满足括号内条件时执行对应分支
                if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable) && e.key.length === 1) {
                    //> 调用函数「playTone」并传入参数执行对应逻辑
                    playTone(860 + Math.random() * 140, 0.03);
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }

        /* ---------- Bug8 高对比度模式 ---------- */
        //> 声明变量「contrastBtn」（contrast btn），用于保存对应数据，保存 DOM/窗口相关对象
        var contrastBtn = document.getElementById('contrast-toggle');
        //> 声明变量「contrastOn」（contrast on），用于保存对应数据
        var contrastOn = false;
        //> 尝试执行可能出错的代码，出错则进入 catch
        try { contrastOn = localStorage.getItem('moe_contrast') === '1'; } catch (e) {}
        // =========================================================
        // 【函数】syncContrast
        // 功能：同步「contrast」相关逻辑（sync contrast）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function syncContrast() {
//> 切换样式类（有则移除、无则添加），可传第二参强制状态
document.documentElement.classList.toggle('high-contrast', contrastOn);
            //> 条件判断：满足括号内条件时执行对应分支
            if (document.body) document.body.classList.toggle('high-contrast', contrastOn);
            //> 条件判断：满足括号内条件时执行对应分支
            if (contrastBtn) {
                //> 切换样式类（有则移除、无则添加），可传第二参强制状态
                contrastBtn.classList.toggle('active', contrastOn);
                //> 设置元素的 HTML 属性
                contrastBtn.setAttribute('aria-pressed', contrastOn ? 'true' : 'false');
                //> 给「contrastBtn.title」赋值，更新其保存的状态
                contrastBtn.title = contrastOn ? '高对比度：开（点击关闭）' : '高对比度：关（点击开启）';
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 条件判断：满足括号内条件时执行对应分支
        if (contrastBtn) {
            //> 调用函数「syncContrast」并传入参数执行对应逻辑
            syncContrast();
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            contrastBtn.addEventListener('click', function () {
                //> 给「contrastOn」赋值，更新其保存的状态
                contrastOn = !contrastOn;
                //> 尝试执行可能出错的代码，出错则进入 catch
                try { localStorage.setItem('moe_contrast', contrastOn ? '1' : '0'); } catch (e) {}
                //> 调用函数「syncContrast」并传入参数执行对应逻辑
                syncContrast();
                //> 条件判断：满足括号内条件时执行对应分支
                if (window.moePlayTone) window.moePlayTone(contrastOn ? 720 : 480, 0.08);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }

        /* ---------- Bug9 快捷键帮助面板按钮 ---------- */
        //> 声明变量「scBtn」（sc btn），用于保存对应数据，保存 DOM/窗口相关对象
        var scBtn = document.getElementById('shortcut-help-toggle');
        //> 条件判断：满足括号内条件时执行对应分支
        if (scBtn) {
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            scBtn.addEventListener('click', function () { toggleKbdHelp(); });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // Esc 统一关闭快捷键面板
        //> 绑定「keydown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('keydown', function (e) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (e.key === 'Escape') {
                //> 声明变量「h」（h），用于保存对应数据，保存 DOM/窗口相关对象
                var h = document.querySelector('.kbd-help.show');
                //> 条件判断：满足括号内条件时执行对应分支
                if (h) h.classList.remove('show');
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* 工单选中态：已废弃 bakeActiveStates「先置 transparent 再两帧后重绘」hack。
       //> 该行执行对应的脚本逻辑（结合上下文理解）
       该 hack 正是三处选中态问题的根因——首页紫色选中态闪烁、我的文章选中白字、
       //> 该行执行对应的脚本逻辑（结合上下文理解）
       内容审核先白后紫；现代 Chrome/Edge 已无入场合成首帧冻结问题，直接移除。 */
    // =========================================================
    // 【函数】bakeActiveStates
    // 功能：处理「bake active states」相关逻辑（common）
    // 参数：
    //   - root：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function bakeActiveStates(root) { /* 空操作，仅为兼容保留 */ }

    /* ====== Bug8：全站统一「轻提示 toast」与「确认弹窗 modal」，替代原生 alert / confirm ======
       //> 该行执行对应的脚本逻辑（结合上下文理解）
       - moeToast(msg, type)：右下角（移动端底部）轻提示，1.8s 自动消失，不打断操作；
         //> 该行执行对应的脚本逻辑（结合上下文理解）
         type 可选 'info'（默认）/ 'success' / 'error'。
       //> 该行执行对应的脚本逻辑（结合上下文理解）
       - moeConfirm({title,message,confirmText,cancelText,danger})：返回 Promise<bool>，
         //> 该行执行对应的脚本逻辑（结合上下文理解）
         柔和粉紫萌系对话框，Esc / 遮罩 = 取消；danger=true 时确认按钮为珊瑚红。
       //> 该行执行对应的脚本逻辑（结合上下文理解）
       - 声明式用法（推荐模板使用）：
           //> 该行执行对应的脚本逻辑（结合上下文理解）
           <form data-confirm="真的要收进回收站吗？" data-confirm-danger> ...
           //> 该行执行对应的脚本逻辑（结合上下文理解）
           <a data-confirm="..."> ... </a>
         //> 该行执行对应的脚本逻辑（结合上下文理解）
         全局事件委托自动拦截，确认后才继续提交 / 跳转。 */
    // =========================================================
    // 【函数】ensureToast
    // 功能：处理「ensure toast」相关逻辑（common）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function ensureToast() {
        //> 声明变量「t」（t），用于保存对应数据，保存 DOM/窗口相关对象
        var t = document.getElementById('global-toast');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!t) {
            //> 创建新的 DOM 元素节点，后续需挂载到文档才显示
            t = document.createElement('div');
            //> 给「t.id」赋值，更新其保存的状态
            t.id = 'global-toast';
            //> 设置元素的 HTML 属性
            t.setAttribute('role', 'status');
            //> 把子节点追加到当前元素内部末尾
            document.body.appendChild(t);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 返回结果并结束当前函数
        return t;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // =========================================================
    // 【函数】moeToast
    // 功能：处理「moe toast」相关逻辑（common）
    // 参数：
    //   - msg：传入的参数（含义结合调用处与函数体）
    //   - type：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function moeToast(msg, type) {
        //> 声明变量「t」（t），用于保存对应数据
        var t = ensureToast();
        //> 读写纯文本内容，不解析 HTML，可防 XSS
        t.textContent = msg;
        //> 给「t.className」赋值，更新其保存的状态
        t.className = 'show' + (type ? ' toast-' + type : '');
        //> 清除对应的定时器，防止其继续执行
        clearTimeout(t._timer);
        //> 设置延时执行的定时器，返回可清除的定时器 id
        t._timer = setTimeout(function () { t.className = t.className.replace('show', '').trim(); }, 1900);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    //> 给「window.moeToast」赋值，更新其保存的状态
    window.moeToast = moeToast;

    // =========================================================
    // 【函数】moeConfirm
    // 功能：处理「moe confirm」相关逻辑（common）
    // 参数：
    //   - opts：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function moeConfirm(opts) {
        //> 给「opts」赋值，更新其保存的状态
        opts = opts || {};
        // Bug9 任务2：默认弹窗文案改从后端下发的文案包取（window.moeMsg），
        // 取不到时回退到脚本内默认值，保证独立可用
        // =========================================================
        // 【函数】moeMsg
        // 功能：处理「moe msg」相关逻辑（common）
        // 参数：
        //   - k：传入的参数（含义结合调用处与函数体）
        //   - d：传入的参数（含义结合调用处与函数体）
        // 返回：函数体内有 return，返回对应结果
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        var T = (typeof window.moeMsg === 'function') ? window.moeMsg : function (k, d) { return d || k; };
        //> 返回结果并结束当前函数
        return new Promise(function (resolve) {
            //> 声明变量「modal」（modal），用于保存对应数据，保存 DOM/窗口相关对象
            var modal = document.getElementById('globalConfirmModal');
            // 极端兜底：页面缺少预置弹窗时不阻塞流程（正常 base.html 一定包含）
            //> 条件判断：满足括号内条件时执行对应分支
            if (!modal) { resolve(true); return; }
            //> 调用函数「ensureModalCss」并传入参数执行对应逻辑
            ensureModalCss();
            //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
            modal.querySelector('#gcmTitle').textContent = opts.title || T('confirm_default');
            //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
            modal.querySelector('#gcmMsg').textContent = opts.message || '';
            //> 声明变量「cancel」（cancel），用于保存对应数据
            var cancel = modal.querySelector('#gcmCancel');
            //> 声明变量「ok」（ok），用于保存对应数据
            var ok = modal.querySelector('#gcmOk');
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            cancel.textContent = opts.cancelText || T('confirm_cancel');
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            ok.textContent = opts.confirmText || T('confirm_ok');
            //> 给「ok.style.background」赋值，更新其保存的状态
            ok.style.background = opts.danger
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                ? 'linear-gradient(135deg,#ff7a8a,#ff5d73)'
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                : 'linear-gradient(135deg,#ff8fb1,#a06cd5)';
            // =========================================================
            // 【函数】cleanup
            // 功能：处理「cleanup」相关逻辑（common）
            // 参数：无
            // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
            // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
            // =========================================================
            var cleanup = function () {
                //> 移除元素的一个或多个样式类
                modal.classList.remove('show');
                //> 解绑「keydown」事件监听器，避免重复绑定或内存泄漏
                document.removeEventListener('keydown', onKey, true);
                //> 给「cancel.onclick」赋值，更新其保存的状态
                cancel.onclick = null; ok.onclick = null; modal.onclick = null;
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            };
            // =========================================================
            // 【函数】onKey
            // 功能：处理……事件「key」相关逻辑（on key）
            // 参数：
            //   - e：传入的参数（含义结合调用处与函数体）
            // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
            // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
            // =========================================================
            function onKey(e) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (e.key === 'Escape') { e.stopPropagation(); cleanup(); resolve(false); }
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            // =========================================================
            // 【函数】onclick
            // 功能：处理「onclick」相关逻辑（common）
            // 参数：无
            // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
            // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
            // =========================================================
            cancel.onclick = function () { cleanup(); resolve(false); };
            //> 给「ok.onclick」赋值，更新其保存的状态
            ok.onclick = function () { cleanup(); resolve(true); };
            //> 给「modal.onclick」赋值，更新其保存的状态
            modal.onclick = function (e) { if (e.target === modal) { cleanup(); resolve(false); } };
            //> 绑定「keydown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            document.addEventListener('keydown', onKey, true);
            // 预置在初始 DOM 中的弹窗，直接加 .show（display:none→flex），可靠绘制
            //> 为元素添加一个或多个样式类
            modal.classList.add('show');
            //> 设置延时执行的定时器，返回可清除的定时器 id
            setTimeout(function () { ok.focus(); }, 30);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    //> 给「window.moeConfirm」赋值，更新其保存的状态
    window.moeConfirm = moeConfirm;

    // 弹窗 / toast 所需样式（仅注入一次，内联自包含，跟随站点圆角与粉紫基调）
    // 注意：#global-toast 必须显式 top:auto/left:auto/width:auto/height:auto，
    // 否则 round6.css 的 top:76px/left:50% 会与这里的 bottom:24px 同时生效，
    // 固定定位元素被纵向拉伸成贯穿屏幕的巨型框（bug7 怪框复发根因）
    //> 声明变量「_tipCssAdded」（tip css added），用于保存对应数据
    var _tipCssAdded = false;
    // =========================================================
    // 【函数】tipCss
    // 功能：处理「tip css」相关逻辑（common）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function tipCss() {
        //> 声明变量「st」（st），用于保存对应数据，保存 DOM/窗口相关对象
        var st = document.createElement('style');
        //> 设置元素的 HTML 属性
        st.setAttribute('data-moe-modal-css', '1');
        //> 读写纯文本内容，不解析 HTML，可防 XSS
        st.textContent = [
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '#global-toast{position:fixed;top:84px;left:50%;right:auto;bottom:auto;width:auto;height:auto;z-index:10000;max-width:90vw;',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            'background:var(--c-card,#fff);color:var(--c-text,#3a2f55);padding:10px 18px;',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            'border:1.5px solid #7a5fc0;border-radius:14px;font-size:13px;font-weight:600;',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            'box-shadow:0 12px 30px rgba(80,60,120,.22);opacity:0;transform:translate(-50%,-14px);',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            'transition:opacity .25s,transform .25s;pointer-events:none;}',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '#global-toast.show{opacity:1;transform:translate(-50%,0);}',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '#global-toast.toast-info{border-color:#7a5fc0;color:#6a4fb0;}',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '#global-toast.toast-success{border-color:#3aa77a;color:#2a8a63;background:#f2fbf7;}',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '#global-toast.toast-error{border-color:#ef5d6b;color:#d84454;background:#fff1f2;}',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '.moe-modal-overlay{position:fixed;inset:0;z-index:10001;display:none;align-items:center;justify-content:center;',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            'padding:20px;background:rgba(60,45,90,.34);backdrop-filter:blur(4px);}',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '.moe-modal-overlay.show{display:flex;}',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '.moe-modal-card{width:min(420px,92vw);background:var(--c-surface,#fff);border-radius:20px;',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            'padding:24px 24px 20px;box-shadow:0 24px 60px rgba(80,60,120,.32);}',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '.moe-modal-title{font-size:17px;font-weight:700;color:var(--c-text,#333);margin-bottom:8px;}',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '.moe-modal-msg{font-size:14px;line-height:1.7;color:var(--c-text-sub,#666);white-space:pre-wrap;word-break:break-word;}',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '.moe-modal-actions{display:flex;justify-content:flex-end;gap:10px;margin-top:20px;}',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '.moe-btn{border:none;cursor:pointer;border-radius:12px;padding:9px 18px;font-size:14px;font-weight:600;}',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '.moe-btn-cancel{background:var(--c-card,#f1eef8);color:var(--c-text-sub,#777);}',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '.moe-btn-ok{color:#fff;box-shadow:0 8px 18px rgba(160,108,213,.32);}',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '.notification-item{display:flex;gap:9px;cursor:pointer;align-items:flex-start;}',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '.notification-item .ni-icon{font-size:15px;line-height:1.3;}',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '.notification-item .ni-body{display:flex;flex-direction:column;gap:2px;min-width:0;flex:1;}',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '.notification-item .ni-title{font-size:.84rem;line-height:1.4;color:var(--c-text,#333);}',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '.notification-item .ni-time{font-size:.72rem;color:var(--c-text-sub,#999);}',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '.notification-item.unread{background:linear-gradient(90deg,rgba(255,143,177,.14),transparent);}',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '.notification-item.unread .ni-title{font-weight:700;}',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '.notification-item.unread .ni-title::after{content:"";display:inline-block;width:7px;height:7px;border-radius:50%;background:#ff5d73;margin-left:6px;vertical-align:middle;}',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '.notification-item.muted{justify-content:center;color:var(--c-text-sub,#999);cursor:default;}',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '@media (max-width:560px){#global-toast{top:76px;left:16px;right:16px;max-width:none;transform:translateY(-14px);text-align:center;}#global-toast.show{transform:translateY(0);}}'
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        ].join('');
        //> 返回结果并结束当前函数
        return st;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // =========================================================
    // 【函数】ensureModalCss
    // 功能：处理「ensure modal css」相关逻辑（common）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function ensureModalCss() {
        //> 条件判断：满足括号内条件时执行对应分支
        if (_tipCssAdded || document.querySelector('[data-moe-modal-css]')) { _tipCssAdded = true; return; }
        //> 把子节点追加到当前元素内部末尾
        document.body.appendChild(tipCss());
        //> 给「_tipCssAdded」赋值，更新其保存的状态
        _tipCssAdded = true;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // 声明式 data-confirm：拦截表单提交
    //> 绑定「submit」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    document.addEventListener('submit', function (e) {
        //> 声明变量「form」（form），用于保存对应数据
        var form = e.target;
        //> 条件判断：满足括号内条件时执行对应分支
        if (form && form.hasAttribute && form.hasAttribute('data-confirm') && !form.dataset.confirmed) {
            //> 阻止事件的默认行为（如表单提交、链接跳转）
            e.preventDefault();
            //> 调用函数「ensureModalCss」并传入参数执行对应逻辑
            ensureModalCss();
            //> 调用函数「moeConfirm」并传入参数执行对应逻辑
            moeConfirm({
                //> 读取元素的 HTML 属性值
                message: form.getAttribute('data-confirm'),
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                danger: form.hasAttribute('data-confirm-danger'),
                //> 读取元素的 HTML 属性值
                confirmText: form.getAttribute('data-confirm-ok') || '确定喵'
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }).then(function (ok) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (ok) { form.dataset.confirmed = '1'; form.submit(); }
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    }, true);
    // 声明式 data-confirm：拦截链接 / 按钮点击
    //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    document.addEventListener('click', function (e) {
        //> 声明变量「el」（el），用于保存对应数据
        var el = e.target.closest && e.target.closest('[data-confirm]');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!el || el.tagName === 'FORM' || el.dataset.confirmed) return;
        //> 阻止事件的默认行为（如表单提交、链接跳转）
        e.preventDefault();
        //> 调用函数「ensureModalCss」并传入参数执行对应逻辑
        ensureModalCss();
        //> 调用函数「moeConfirm」并传入参数执行对应逻辑
        moeConfirm({
            //> 读取元素的 HTML 属性值
            message: el.getAttribute('data-confirm'),
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            danger: el.hasAttribute('data-confirm-danger'),
            //> 读取元素的 HTML 属性值
            confirmText: el.getAttribute('data-confirm-ok') || '确定喵'
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }).then(function (ok) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (!ok) return;
            //> 读写元素的 data-* 自定义数据属性
            el.dataset.confirmed = '1';
            //> 条件判断：满足括号内条件时执行对应分支
            if (el.tagName === 'A' && el.href) { window.location.href = el.href; }
            //> 以上条件都不满足时执行的兜底分支
            else { el.click(); }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    }, true);

    /* ====== Bug9：导航铃铛下拉，接入真实通知数据 ====== */
    // =========================================================
    // 【函数】initNotificationBell
    // 功能：初始化「notification bell」相关逻辑（init notification bell）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function initNotificationBell() {
        //> 声明变量「bell」（bell），用于保存对应数据，保存 DOM/窗口相关对象
        var bell = document.getElementById('notification-bell');
        //> 声明变量「panel」（panel），用于保存对应数据，保存 DOM/窗口相关对象
        var panel = document.getElementById('notification-panel');
        //> 声明变量「list」（list），用于保存对应数据，保存 DOM/窗口相关对象
        var list = document.getElementById('notification-list');
        //> 声明变量「markAll」（mark all），用于保存对应数据，保存 DOM/窗口相关对象
        var markAll = document.getElementById('notification-mark-all');
        //> 声明变量「badge」（badge），用于保存对应数据，保存 DOM/窗口相关对象
        var badge = document.getElementById('notification-badge');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!bell || !panel || !list) return;
        //> 声明变量「loaded」（loaded），用于保存对应数据
        var loaded = false;
        //> 声明变量「mainEl」（main el），用于保存对应数据，保存 DOM/窗口相关对象
        var mainEl = document.getElementById('main-content') || document.querySelector('.site-main');
        // header 合成面不会重绘“加载后才出现”的子元素（首帧冻结），故把下拉移入
        // <main> 合成面并改为 fixed，按铃铛坐标定位，确保可靠绘制。
        //> 条件判断：满足括号内条件时执行对应分支
        if (mainEl) {
            //> 把子节点追加到当前元素内部末尾
            mainEl.appendChild(panel);
            //> 给「panel.style.position」赋值，更新其保存的状态
            panel.style.position = 'fixed';
            //> 给「panel.style.right」赋值，更新其保存的状态
            panel.style.right = 'auto';
            //> 给「panel.style.top」赋值，更新其保存的状态
            panel.style.top = 'auto';
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // =========================================================
        // 【函数】place
        // 功能：处理「place」相关逻辑（common）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function place() {
            //> 条件判断：满足括号内条件时执行对应分支
            if (!mainEl) return;
            //> 声明变量「r」（r），用于保存对应数据
            var r = bell.getBoundingClientRect();
            //> 声明变量「w」（w），用于保存对应数据
            var w = 320;
            //> 声明变量「wantLeft」（want left），用于保存对应数据
            var wantLeft = Math.min(r.right - w, innerWidth - w - 12);
            //> 给「wantLeft」赋值，更新其保存的状态
            wantLeft = Math.max(12, wantLeft);
            // 工单16：main 残留 identity transform 成为 fixed 包含块，
            // 求包含块原点并扣除，保证面板稳定落在铃铛正下方（视口坐标）。
            //> 声明变量「ox」（ox），用于保存对应数据
            var ox = 0, oy = 0, node = panel.parentElement;
            //> 当条件为真时反复执行循环体
            while (node && node.nodeType === 1) {
                //> 声明变量「cs」（cs），用于保存对应数据
                var cs = getComputedStyle(node);
                //> 条件判断：满足括号内条件时执行对应分支
                if ((cs.transform && cs.transform !== 'none') ||
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    (cs.filter && cs.filter !== 'none') ||
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    (cs.perspective && cs.perspective !== 'none')) {
                    //> 声明变量「br」（br），用于保存对应数据
                    var br = node.getBoundingClientRect();
                    //> 给「ox」赋值，更新其保存的状态
                    ox = br.left; oy = br.top; break;
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
                //> 给「node」赋值，更新其保存的状态
                node = node.parentElement;
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 给「panel.style.left」赋值，更新其保存的状态
            panel.style.left = (wantLeft - ox) + 'px';
            //> 给「panel.style.top」赋值，更新其保存的状态
            panel.style.top = (r.bottom + 8 - oy) + 'px';
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }

        // =========================================================
        // 【函数】csrf
        // 功能：处理「csrf」相关逻辑（common）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function csrf() {
            //> 声明变量「m」（m），用于保存对应数据，保存 DOM/窗口相关对象
            var m = document.cookie.match(/csrftoken=([^;]+)/);
            //> 返回结果并结束当前函数
            return m ? m[1] : '';
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // =========================================================
        // 【函数】iconFor
        // 功能：处理「icon for」相关逻辑（common）
        // 参数：
        //   - t：传入的参数（含义结合调用处与函数体）
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function iconFor(t) {
            //> 返回结果并结束当前函数
            return t === 'reply' ? '💬' : t === 'mention' ? '🏷'
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                : t === 'like' ? '👍' : t === 'article' ? '📄' : '🔔';
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // =========================================================
        // 【函数】relTime
        // 功能：处理「rel time」相关逻辑（common）
        // 参数：
        //   - iso：传入的参数（含义结合调用处与函数体）
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function relTime(iso) {
            //> 声明变量「d」（d），用于保存对应数据
            var d = new Date(iso), diff = (Date.now() - d.getTime()) / 1000;
            //> 条件判断：满足括号内条件时执行对应分支
            if (diff < 60) return '刚刚';
            //> 条件判断：满足括号内条件时执行对应分支
            if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前';
            //> 条件判断：满足括号内条件时执行对应分支
            if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前';
            //> 条件判断：满足括号内条件时执行对应分支
            if (diff < 2592000) return Math.floor(diff / 86400) + ' 天前';
            //> 返回结果并结束当前函数
            return d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // =========================================================
        // 【函数】setBadge
        // 功能：设置「badge」相关逻辑（set badge）
        // 参数：
        //   - n：传入的参数（含义结合调用处与函数体）
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function setBadge(n) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (!badge) return;
            //> 条件判断：满足括号内条件时执行对应分支
            if (n > 0) { badge.textContent = n > 99 ? '99+' : n; badge.style.display = ''; }
            //> 以上条件都不满足时执行的兜底分支
            else { badge.style.display = 'none'; }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // =========================================================
        // 【函数】render
        // 功能：渲染相关逻辑（render）
        // 参数：
        //   - results：传入的参数（含义结合调用处与函数体）
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function render(results) {
            //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
            list.innerHTML = '';
            //> 条件判断：满足括号内条件时执行对应分支
            if (!results || !results.length) {
                //> 声明变量「li」（li），用于保存对应数据，保存 DOM/窗口相关对象
                var li = document.createElement('li');
                //> 给「li.className」赋值，更新其保存的状态
                li.className = 'notification-item muted';
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                li.textContent = '这里还没有通知喵~';
                //> 把子节点追加到当前元素内部末尾
                list.appendChild(li);
                //> 提前结束函数，无返回值
                return;
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 遍历数组/类数组中的每一项并执行回调
            results.forEach(function (n) {
                //> 声明变量「li」（li），用于保存对应数据，保存 DOM/窗口相关对象
                var li = document.createElement('li');
                //> 给「li.className」赋值，更新其保存的状态
                li.className = 'notification-item' + (n.is_read ? '' : ' unread');
                //> 设置元素的 HTML 属性
                li.setAttribute('data-id', n.id);
                //> 设置元素的 HTML 属性
                li.setAttribute('data-url', n.related_url || '');
                //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
                li.innerHTML =
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    '<span class="ni-icon">' + iconFor(n.type) + '</span>' +
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    '<span class="ni-body"><span class="ni-title"></span>' +
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    '<span class="ni-time">' + relTime(n.created_at) + '</span></span>';
                //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
                li.querySelector('.ni-title').textContent = n.title;
                //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
                li.addEventListener('click', function () {
                    // =========================================================
                    // 【函数】go
                    // 功能：处理「go」相关逻辑（common）
                    // 参数：无
                    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
                    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
                    // =========================================================
                    var go = function () {
                        //> 声明变量「u」（u），用于保存对应数据
                        var u = li.getAttribute('data-url');
                        //> 条件判断：满足括号内条件时执行对应分支
                        if (u) window.location.href = u; else window.location.href = '/notifications/';
                    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                    };
                    //> 条件判断：满足括号内条件时执行对应分支
                    if (!n.is_read) {
                        //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
                        fetch('/api/notifications/' + n.id + '/read/', {
                            //> 该行执行对应的脚本逻辑（结合上下文理解）
                            method: 'POST', headers: { 'X-CSRFToken': csrf() }, credentials: 'same-origin'
                        //> 该行执行对应的脚本逻辑（结合上下文理解）
                        }).then(go).catch(go);
                    //> 以上条件都不满足时执行的兜底分支
                    } else { go(); }
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                });
                //> 把子节点追加到当前元素内部末尾
                list.appendChild(li);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // =========================================================
        // 【函数】load
        // 功能：加载相关逻辑（load）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function load() {
            //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
            fetch('/api/notifications/?page_size=6', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                .then(function (r) {
                    //> 条件判断：满足括号内条件时执行对应分支
                    if (r.status === 401) { window.location.href = '/notifications/'; return null; }
                    //> 返回结果并结束当前函数
                    return r.json();
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                })
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                .then(function (d) {
                    //> 条件判断：满足括号内条件时执行对应分支
                    if (!d) return;
                    //> 声明变量「res」（res），用于保存对应数据
                    var res = d.results || (d.data && d.data.results) || [];
                    //> 调用函数「render」并传入参数执行对应逻辑
                    render(res);
                    //> 声明变量「unread」（unread），用于保存对应数据
                    var unread = res.filter(function (x) { return !x.is_read; }).length;
                    //> 调用函数「setBadge」并传入参数执行对应逻辑
                    setBadge(unread);
                    //> 给「loaded」赋值，更新其保存的状态
                    loaded = true;
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                })
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                .catch(function () {
                    //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
                    list.innerHTML = '';
                    //> 声明变量「li」（li），用于保存对应数据，保存 DOM/窗口相关对象
                    var li = document.createElement('li');
                    //> 给「li.className」赋值，更新其保存的状态
                    li.className = 'notification-item muted';
                    //> 读写纯文本内容，不解析 HTML，可防 XSS
                    li.textContent = '通知加载失败，点底部查看全部~';
                    //> 把子节点追加到当前元素内部末尾
                    list.appendChild(li);
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // =========================================================
        // 【函数】openPanel
        // 功能：打开「panel」相关逻辑（open panel）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function openPanel() {
            //> 调用函数「place」并传入参数执行对应逻辑
            place();
            //> 给「panel.hidden」赋值，更新其保存的状态
            panel.hidden = false;
            //> 设置元素的 HTML 属性
            bell.setAttribute('aria-expanded', 'true');
            //> 条件判断：满足括号内条件时执行对应分支
            if (!loaded) load();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // =========================================================
        // 【函数】closePanel
        // 功能：关闭「panel」相关逻辑（close panel）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function closePanel() {
            //> 给「panel.hidden」赋值，更新其保存的状态
            panel.hidden = true;
            //> 设置元素的 HTML 属性
            bell.setAttribute('aria-expanded', 'false');
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // =========================================================
        // 【函数】togglePanel
        // 功能：切换「panel」相关逻辑（toggle panel）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function togglePanel() {
            //> 条件判断：满足括号内条件时执行对应分支
            if (panel.hidden) openPanel(); else closePanel();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        bell.addEventListener('click', function (e) { e.stopPropagation(); togglePanel(); });
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        panel.addEventListener('click', function (e) { e.stopPropagation(); });
        //> 条件判断：满足括号内条件时执行对应分支
        if (markAll) {
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            markAll.addEventListener('click', function () {
                //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
                fetch('/api/notifications/read_all/', {
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    method: 'POST', headers: { 'X-CSRFToken': csrf() }, credentials: 'same-origin'
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                }).then(function () {
                    //> 调用函数「setBadge」并传入参数执行对应逻辑
                    setBadge(0);
                    //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
                    list.querySelectorAll('.notification-item.unread').forEach(function (x) {
                        //> 移除元素的一个或多个样式类
                        x.classList.remove('unread');
                    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                    });
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                });
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 绑定「resize」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        window.addEventListener('resize', function () { if (!panel.hidden) place(); });
        //> 绑定「scroll」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        window.addEventListener('scroll', function () { if (!panel.hidden) place(); }, true);
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('click', function () { if (!panel.hidden) closePanel(); });
        //> 绑定「keydown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('keydown', function (e) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (e.key === 'Escape' && !panel.hidden) closePanel();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ====== 初始化 ====== */
    // =========================================================
    // 【函数】init
    // 功能：初始化相关逻辑（init）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function init() {
        //> 调用函数「ensureModalCss」并传入参数执行对应逻辑
        ensureModalCss();   // 预置弹窗在初始 DOM，需先有样式才会 display:none
        //> 调用函数「initNotificationBell」并传入参数执行对应逻辑
        initNotificationBell();
        //> 调用函数「initAnimatedNumbers」并传入参数执行对应逻辑
        initAnimatedNumbers();
        //> 调用函数「initEntranceObserver」并传入参数执行对应逻辑
        initEntranceObserver();
        //> 调用函数「initRipple」并传入参数执行对应逻辑
        initRipple();
        //> 调用函数「initSearchSuggest」并传入参数执行对应逻辑
        initSearchSuggest();
        //> 调用函数「initKeyboardNav」并传入参数执行对应逻辑
        initKeyboardNav();
        //> 调用函数「initImageFallback」并传入参数执行对应逻辑
        initImageFallback();
        //> 调用函数「initTooltip」并传入参数执行对应逻辑
        initTooltip();
        //> 调用函数「initDoubleClickTop」并传入参数执行对应逻辑
        initDoubleClickTop();
        //> 调用函数「initCollapse」并传入参数执行对应逻辑
        initCollapse();
        //> 调用函数「initNavToggles」并传入参数执行对应逻辑
        initNavToggles();
        // 工单选中态：不再做「透明→重绘」烘焙（消除闪烁/白字/延迟）
        // =========================================================
        // 【函数】moeBakeActive
        // 功能：处理「moe bake active」相关逻辑（common）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        window.moeBakeActive = function () {};  // 兼容旧脚本调用，空操作
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    //> 条件判断：满足括号内条件时执行对应分支
    if (document.readyState === 'loading') {
        //> 绑定「DOMContentLoaded」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('DOMContentLoaded', init);
    //> 以上条件都不满足时执行的兜底分支
    } else {
        //> 调用函数「init」并传入参数执行对应逻辑
        init();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

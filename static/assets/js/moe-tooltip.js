/* ============================================================
 * moe-tooltip.js  ·  萌语博客全站通用「萌系气泡提示」逻辑
 * ------------------------------------------------------------
 * 功能：
 *  1. 自动为带 data-tip 的元素，以及顶部导航 .theme-toggle
 *     等带 title 的按钮启用自定义气泡（同时移除原生 title，
 *     避免原生提示与自定义气泡重复弹出，保留 aria-label 无障碍）；
 *  2. 气泡默认显示在目标元素「右侧」垂直居中；右侧空间不足
 *     时自动翻转到左侧；也可用 data-tip-pos="top|bottom|left|right"
 *     显式指定方向；
 *  3. 支持鼠标悬停与键盘聚焦触发；滚动、点击、离开时隐藏；
 *  4. 通过 MutationObserver 监听后续动态插入的节点
 *     （例如异步加载的评论 / 举报弹窗），新节点自动生效。
 * 说明：本文件为「源文件」，部署前由构建脚本压缩为 .min.js。
 * ============================================================ */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';

    /* 全站所有「带原生 title 的可见元素」统一升级为萌系气泡；
       //> 该行执行对应的脚本逻辑（结合上下文理解）
       排除 head 内 link/meta 等非渲染元素（其 title 有 RSS/语义用途）。 */
    //> 声明变量「TITLE_SELECTOR」（title selector），用于保存对应数据，初始为字符串
    var TITLE_SELECTOR = '[title]:not(link):not(meta):not(script):not(style):not(template)';

    //> 声明变量「tipEl」（tip el），用于保存对应数据
    var tipEl = null;      /* 气泡单例 DOM */
    //> 声明变量「current」（current），用于保存对应数据
    var current = null;    /* 当前触发气泡的目标元素 */
    //> 声明变量「hideTimer」（hide timer），用于保存对应数据
    var hideTimer = null;  /* 延迟隐藏计时器（鼠标在相邻元素间移动时更顺滑） */

    /* 创建气泡单例并挂到 body 末尾（脱离 overflow:hidden 容器，避免被裁切） */
    // =========================================================
    // 【函数】ensureTip
    // 功能：处理「ensure tip」相关逻辑（moe-tooltip）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function ensureTip() {
        //> 条件判断：满足括号内条件时执行对应分支
        if (tipEl) return tipEl;
        //> 创建新的 DOM 元素节点，后续需挂载到文档才显示
        tipEl = document.createElement('div');
        //> 给「tipEl.id」赋值，更新其保存的状态
        tipEl.id = 'moe-tooltip';
        //> 设置元素的 HTML 属性
        tipEl.setAttribute('role', 'tooltip');
        //> 设置元素的 HTML 属性
        tipEl.setAttribute('aria-hidden', 'true');
        //> 给「tipEl.hidden」赋值，更新其保存的状态
        tipEl.hidden = true;
        //> 把子节点追加到当前元素内部末尾
        document.body.appendChild(tipEl);
        //> 返回结果并结束当前函数
        return tipEl;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* 把元素的原生 title 迁移到 data-tip，并移除 title 抑制原生黑色提示 */
    // =========================================================
    // 【函数】promoteTitle
    // 功能：处理「promote title」相关逻辑（moe-tooltip）
    // 参数：
    //   - el：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function promoteTitle(el) {
        //> 条件判断：满足括号内条件时执行对应分支
        if (el.__moeTitlePromoted) return;
        /* 跳过 head 内 feed link / meta 等非渲染元素（其 title 有语义用途，不可移除） */
        //> 声明变量「tag」（tag），用于保存对应数据
        var tag = el.tagName;
        //> 条件判断：满足括号内条件时执行对应分支
        if (tag === 'LINK' || tag === 'META' || tag === 'SCRIPT' ||
            //> 给「tag」赋值，更新其保存的状态
            tag === 'STYLE' || tag === 'TEMPLATE' || tag === 'TITLE') {
            //> 给「el.__moeTitlePromoted」赋值，更新其保存的状态
            el.__moeTitlePromoted = true;
            //> 提前结束函数，无返回值
            return;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 声明变量「t」（t），用于保存对应数据
        var t = el.getAttribute('title');
        //> 条件判断：满足括号内条件时执行对应分支
        if (t && !el.getAttribute('data-tip')) {
            //> 设置元素的 HTML 属性
            el.setAttribute('data-tip', t);
            //> 设置元素的 HTML 属性
            el.setAttribute('data-native-title', t);
            //> 操作「el」的相关方法/属性
            el.removeAttribute('title');
            /* 横向「统计 / 徽章」行的气泡默认显示在元素上方，避免遮挡相邻项；
               //> 该行执行对应的脚本逻辑（结合上下文理解）
               其余元素默认在右侧。显式 data-tip-pos 优先。 */
            //> 条件判断：满足括号内条件时执行对应分支
            if (!el.getAttribute('data-tip-pos') && el.classList &&
                //> 判断元素是否含有指定样式类，返回布尔值
                (el.classList.contains('stat-item') ||
                 //> 判断元素是否含有指定样式类，返回布尔值
                 el.classList.contains('corner-badge') ||
                 //> 判断元素是否含有指定样式类，返回布尔值
                 el.classList.contains('arch-badge'))) {
                //> 设置元素的 HTML 属性
                el.setAttribute('data-tip-pos', 'top');
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 给「el.__moeTitlePromoted」赋值，更新其保存的状态
        el.__moeTitlePromoted = true;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* 根据方向把气泡定位到目标元素旁，并做视口边界翻转/夹紧 */
    // =========================================================
    // 【函数】position
    // 功能：处理「position」相关逻辑（moe-tooltip）
    // 参数：
    //   - target：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function position(target) {
        //> 声明变量「rect」（rect），用于保存对应数据
        var rect = target.getBoundingClientRect();
        //> 声明变量「text」（text），用于保存对应数据
        var text = target.getAttribute('data-tip') || '';
        //> 读写纯文本内容，不解析 HTML，可防 XSS
        tipEl.textContent = text;
        //> 给「tipEl.hidden」赋值，更新其保存的状态
        tipEl.hidden = false;
        //> 设置元素的 HTML 属性
        tipEl.setAttribute('aria-hidden', 'false');

        /* 先显示以测量气泡自身尺寸 */
        //> 声明变量「tw」（tw），用于保存对应数据
        var tw = tipEl.offsetWidth;
        //> 声明变量「th」（th），用于保存对应数据
        var th = tipEl.offsetHeight;
        //> 声明变量「gap」（gap），用于保存对应数据
        var gap = 10;  /* 气泡与元素的间距 */
        //> 声明变量「vw」（vw），用于保存对应数据，保存 DOM/窗口相关对象
        var vw = window.innerWidth;
        //> 声明变量「vh」（vh），用于保存对应数据，保存 DOM/窗口相关对象
        var vh = window.innerHeight;

        /* 清除方向 class */
        //> 移除元素的一个或多个样式类
        tipEl.classList.remove('tip-left', 'tip-top', 'tip-bottom');

        /* 确定期望方向（默认右侧） */
        //> 声明变量「want」（want），用于保存对应数据
        var want = target.getAttribute('data-tip-pos') || 'right';

        /* 计算各方向是否放得下 */
        //> 声明变量「roomRight」（room right），用于保存对应数据，值为一个函数
        var roomRight = (vw - rect.right) >= tw + gap;
        //> 声明变量「roomLeft」（room left），用于保存对应数据
        var roomLeft = rect.left >= tw + gap;

        //> 声明变量「side」（side），用于保存对应数据
        var side = want;
        //> 条件判断：满足括号内条件时执行对应分支
        if (want === 'right' && !roomRight) side = roomLeft ? 'left' : 'right';
        //> 条件判断：满足括号内条件时执行对应分支
        if (want === 'left' && !roomLeft) side = roomRight ? 'right' : 'left';

        //> 声明变量「x」，稍后赋值使用
        var x, y;
        //> 条件判断：满足括号内条件时执行对应分支
        if (side === 'right') {
            //> 给「x」赋值，更新其保存的状态
            x = rect.right + gap;
            //> 给「y」赋值，更新其保存的状态
            y = rect.top + rect.height / 2 - th / 2;
        //> 否则若满足该条件则进入此分支
        } else if (side === 'left') {
            //> 给「x」赋值，更新其保存的状态
            x = rect.left - gap - tw;
            //> 给「y」赋值，更新其保存的状态
            y = rect.top + rect.height / 2 - th / 2;
            //> 为元素添加一个或多个样式类
            tipEl.classList.add('tip-left');
        //> 否则若满足该条件则进入此分支
        } else if (side === 'top') {
            //> 给「x」赋值，更新其保存的状态
            x = rect.left + rect.width / 2 - tw / 2;
            //> 给「y」赋值，更新其保存的状态
            y = rect.top - gap - th;
            //> 为元素添加一个或多个样式类
            tipEl.classList.add('tip-top');
        //> 以上条件都不满足时执行的兜底分支
        } else { /* bottom */
            //> 给「x」赋值，更新其保存的状态
            x = rect.left + rect.width / 2 - tw / 2;
            //> 给「y」赋值，更新其保存的状态
            y = rect.bottom + gap;
            //> 为元素添加一个或多个样式类
            tipEl.classList.add('tip-bottom');
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }

        /* 水平 / 垂直方向夹紧到视口内，留出 8px 安全边距 */
        //> 给「x」赋值，更新其保存的状态
        x = Math.max(8, Math.min(x, vw - tw - 8));
        //> 给「y」赋值，更新其保存的状态
        y = Math.max(8, Math.min(y, vh - th - 8));

        //> 给「tipEl.style.left」赋值，更新其保存的状态
        tipEl.style.left = x + 'px';
        //> 给「tipEl.style.top」赋值，更新其保存的状态
        tipEl.style.top = y + 'px';
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* 显示气泡 */
    // =========================================================
    // 【函数】show
    // 功能：显示相关逻辑（show）
    // 参数：
    //   - target：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function show(target) {
      //> 条件判断：满足括号内条件时执行对应分支
      if (!target || !target.getAttribute) return;
      /* 带 data-tip-local 的元素**自带本地气泡**，全站气泡必须让位，
         //> 该行执行对应的脚本逻辑（结合上下文理解）
         否则同一个按钮会同时弹出两个提示（看板娘工具栏曾出现「换模型」左右各一个）。
         //> 该行执行对应的脚本逻辑（结合上下文理解）
         判定覆盖祖先：标记在按钮上、子节点触发 mouseover 时也能正确跳过。 */
      //> 条件判断：满足括号内条件时执行对应分支
      if (target.closest && target.closest('[data-tip-local]')) return;
      //> 声明变量「text」（text），用于保存对应数据
      var text = target.getAttribute('data-tip');
      //> 条件判断：满足括号内条件时执行对应分支
      if (!text) return;
      //> 条件判断：满足括号内条件时执行对应分支
      if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
      //> 调用函数「ensureTip」并传入参数执行对应逻辑
      ensureTip();
      //> 给「current」赋值，更新其保存的状态
      current = target;
      //> 调用函数「position」并传入参数执行对应逻辑
      position(target);
      /* 下一帧再加 show，保证过渡动画触发 */
      //> 为元素添加一个或多个样式类
      tipEl.classList.add('show');
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* 隐藏气泡 */
    // =========================================================
    // 【函数】hide
    // 功能：隐藏相关逻辑（hide）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function hide() {
        //> 条件判断：满足括号内条件时执行对应分支
        if (!tipEl) return;
        //> 条件判断：满足括号内条件时执行对应分支
        if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
        //> 移除元素的一个或多个样式类
        tipEl.classList.remove('show');
        //> 设置元素的 HTML 属性
        tipEl.setAttribute('aria-hidden', 'true');
        //> 给「current」赋值，更新其保存的状态
        current = null;
        /* 等收起动画结束后再 hidden，避免闪烁 */
        //> 设置延时执行的定时器，返回可清除的定时器 id
        hideTimer = setTimeout(function () { if (tipEl) tipEl.hidden = true; }, 160);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* 事件委托：统一在 document 上处理悬停 / 聚焦 / 触摸，
       //> 该行执行对应的脚本逻辑（结合上下文理解）
       这样对动态插入的节点同样有效，无需逐个绑定。 */
    // =========================================================
    // 【函数】bindEvents
    // 功能：绑定「events」相关逻辑（bind events）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function bindEvents() {
        /* 鼠标移入：找到最近的带 data-tip 祖先并显示 */
        //> 绑定「mouseover」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('mouseover', function (e) {
            //> 声明变量「t」（t），用于保存对应数据
            var t = e.target.closest ? e.target.closest('[data-tip]') : null;
            //> 条件判断：满足括号内条件时执行对应分支
            if (t && t !== current) show(t);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        /* 鼠标移出：离开触发元素时隐藏 */
        //> 绑定「mouseout」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('mouseout', function (e) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (!current) return;
            //> 声明变量「related」（related），用于保存对应数据
            var related = e.relatedTarget;
            //> 条件判断：满足括号内条件时执行对应分支
            if (related && current.contains(related)) return;
            //> 条件判断：满足括号内条件时执行对应分支
            if (related && related.closest && related.closest('[data-tip]') === current) return;
            //> 调用函数「hide」并传入参数执行对应逻辑
            hide();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        /* 键盘聚焦也弹出（无障碍） */
        //> 绑定「focusin」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('focusin', function (e) {
            //> 声明变量「t」（t），用于保存对应数据
            var t = e.target.closest ? e.target.closest('[data-tip]') : null;
            //> 条件判断：满足括号内条件时执行对应分支
            if (t) show(t);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        //> 绑定「focusout」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('focusout', function () { hide(); });
        /* 点击 / 滚动 / 窗口尺寸变化时隐藏，避免气泡停留在错误位置 */
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('click', function () { hide(); });
        //> 绑定「scroll」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        window.addEventListener('scroll', function () { hide(); }, true);
        //> 绑定「resize」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        window.addEventListener('resize', function () { hide(); });
        /* Esc 关闭 */
        //> 绑定「keydown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('keydown', function (e) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (e.key === 'Escape') hide();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* 扫描并升级当前文档内的 title 按钮 */
    // =========================================================
    // 【函数】scan
    // 功能：处理「scan」相关逻辑（moe-tooltip）
    // 参数：
    //   - root：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function scan(root) {
        //> 声明变量「scope」（scope），用于保存对应数据
        var scope = root || document;
        //> 声明变量「nodes」（nodes），用于保存对应数据
        var nodes = scope.querySelectorAll ? scope.querySelectorAll(TITLE_SELECTOR) : [];
        //> 循环：按条件重复执行循环体
        for (var i = 0; i < nodes.length; i++) promoteTitle(nodes[i]);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* 初始化 */
    // =========================================================
    // 【函数】init
    // 功能：初始化相关逻辑（init）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function init() {
        //> 调用函数「ensureTip」并传入参数执行对应逻辑
        ensureTip();
        //> 调用函数「bindEvents」并传入参数执行对应逻辑
        bindEvents();
        //> 调用函数「scan」并传入参数执行对应逻辑
        scan(document);

        /* 监听动态插入节点（异步评论、弹窗等），自动升级其 title */
        //> 条件判断：满足括号内条件时执行对应分支
        if (window.MutationObserver) {
            //> 声明变量「mo」（mo），用于保存对应数据
            var mo = new MutationObserver(function (mutations) {
                //> 遍历数组/类数组中的每一项并执行回调
                mutations.forEach(function (m) {
                    //> 遍历数组/类数组中的每一项并执行回调
                    m.addedNodes.forEach(function (node) {
                        //> 条件判断：满足括号内条件时执行对应分支
                        if (node.nodeType === 1) scan(node);
                    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                    });
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                });
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            //> 操作「mo」的相关方法/属性
            mo.observe(document.body, { childList: true, subtree: true });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }

        /* 视觉走查钩子：URL 带 tip_demo=1 时，持续让「视口中线附近」的收藏
           //> 该行执行对应的脚本逻辑（结合上下文理解）
           统计气泡保持显示（滚动后也会自动重新定位），便于截图验收；
           //> 该行执行对应的脚本逻辑（结合上下文理解）
           普通访问不会触发，也不影响交互。 */
        //> 条件判断：满足括号内条件时执行对应分支
        if (/[?&]tip_demo=1/.test(location.search)) {
            // =========================================================
            // 【函数】setInterval
            // 功能：设置「interval」相关逻辑（set interval）
            // 参数：
            //   - function：传入的参数（含义结合调用处与函数体）
            //   - (：传入的参数（含义结合调用处与函数体）
            // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
            // 注意：含定时器，注意在适当时机清除，避免泄漏与重复触发
            // =========================================================
            setInterval(function () {
                //> 声明变量「nodes」（nodes），用于保存对应数据，保存 DOM/窗口相关对象
                var nodes = document.querySelectorAll('.article-card-stats .stat-item');
                //> 声明变量「fav」（fav），用于保存对应数据
                var fav = null, nearest = null, bd = 1e9, cy = innerHeight / 2;
                //> 循环：按条件重复执行循环体
                for (var i = 0; i < nodes.length; i++) {
                    //> 声明变量「r」（r），用于保存对应数据
                    var r = nodes[i].getBoundingClientRect();
                    //> 条件判断：满足括号内条件时执行对应分支
                    if (r.bottom <= 0 || r.top >= innerHeight) continue;
                    //> 声明变量「d」（d），用于保存对应数据
                    var d = Math.abs(r.top + r.height / 2 - cy);
                    //> 条件判断：满足括号内条件时执行对应分支
                    if (d < bd) { bd = d; nearest = nodes[i]; }
                    //> 条件判断：满足括号内条件时执行对应分支
                    if ((nodes[i].getAttribute('data-tip') || '').indexOf('收藏') !== -1 &&
                        //> 该行执行对应的脚本逻辑（结合上下文理解）
                        (!fav || d < fav.d)) { fav = { el: nodes[i], d: d }; }
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
                //> 声明变量「pick」（pick），用于保存对应数据
                var pick = fav ? fav.el : nearest;
                //> 条件判断：满足括号内条件时执行对应分支
                if (pick && pick !== current) show(pick);
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }, 500);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
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

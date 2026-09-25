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
(function () {
    'use strict';

    /* 全站所有「带原生 title 的可见元素」统一升级为萌系气泡；
       排除 head 内 link/meta 等非渲染元素（其 title 有 RSS/语义用途）。 */
    var TITLE_SELECTOR = '[title]:not(link):not(meta):not(script):not(style):not(template)';

    var tipEl = null;      /* 气泡单例 DOM */
    var current = null;    /* 当前触发气泡的目标元素 */
    var hideTimer = null;  /* 延迟隐藏计时器（鼠标在相邻元素间移动时更顺滑） */

    /* 创建气泡单例并挂到 body 末尾（脱离 overflow:hidden 容器，避免被裁切） */
    function ensureTip() {
        if (tipEl) return tipEl;
        tipEl = document.createElement('div');
        tipEl.id = 'moe-tooltip';
        tipEl.setAttribute('role', 'tooltip');
        tipEl.setAttribute('aria-hidden', 'true');
        tipEl.hidden = true;
        document.body.appendChild(tipEl);
        return tipEl;
    }

    /* 把元素的原生 title 迁移到 data-tip，并移除 title 抑制原生黑色提示 */
    function promoteTitle(el) {
        if (el.__moeTitlePromoted) return;
        /* 跳过 head 内 feed link / meta 等非渲染元素（其 title 有语义用途，不可移除） */
        var tag = el.tagName;
        if (tag === 'LINK' || tag === 'META' || tag === 'SCRIPT' ||
            tag === 'STYLE' || tag === 'TEMPLATE' || tag === 'TITLE') {
            el.__moeTitlePromoted = true;
            return;
        }
        var t = el.getAttribute('title');
        if (t && !el.getAttribute('data-tip')) {
            el.setAttribute('data-tip', t);
            el.setAttribute('data-native-title', t);
            el.removeAttribute('title');
            /* 横向「统计 / 徽章」行的气泡默认显示在元素上方，避免遮挡相邻项；
               其余元素默认在右侧。显式 data-tip-pos 优先。 */
            if (!el.getAttribute('data-tip-pos') && el.classList &&
                (el.classList.contains('stat-item') ||
                 el.classList.contains('corner-badge') ||
                 el.classList.contains('arch-badge'))) {
                el.setAttribute('data-tip-pos', 'top');
            }
        }
        el.__moeTitlePromoted = true;
    }

    /* 根据方向把气泡定位到目标元素旁，并做视口边界翻转/夹紧 */
    function position(target) {
        var rect = target.getBoundingClientRect();
        var text = target.getAttribute('data-tip') || '';
        tipEl.textContent = text;
        tipEl.hidden = false;
        tipEl.setAttribute('aria-hidden', 'false');

        /* 先显示以测量气泡自身尺寸 */
        var tw = tipEl.offsetWidth;
        var th = tipEl.offsetHeight;
        var gap = 10;  /* 气泡与元素的间距 */
        var vw = window.innerWidth;
        var vh = window.innerHeight;

        /* 清除方向 class */
        tipEl.classList.remove('tip-left', 'tip-top', 'tip-bottom');

        /* 确定期望方向（默认右侧） */
        var want = target.getAttribute('data-tip-pos') || 'right';

        /* 计算各方向是否放得下 */
        var roomRight = (vw - rect.right) >= tw + gap;
        var roomLeft = rect.left >= tw + gap;

        var side = want;
        if (want === 'right' && !roomRight) side = roomLeft ? 'left' : 'right';
        if (want === 'left' && !roomLeft) side = roomRight ? 'right' : 'left';

        var x, y;
        if (side === 'right') {
            x = rect.right + gap;
            y = rect.top + rect.height / 2 - th / 2;
        } else if (side === 'left') {
            x = rect.left - gap - tw;
            y = rect.top + rect.height / 2 - th / 2;
            tipEl.classList.add('tip-left');
        } else if (side === 'top') {
            x = rect.left + rect.width / 2 - tw / 2;
            y = rect.top - gap - th;
            tipEl.classList.add('tip-top');
        } else { /* bottom */
            x = rect.left + rect.width / 2 - tw / 2;
            y = rect.bottom + gap;
            tipEl.classList.add('tip-bottom');
        }

        /* 水平 / 垂直方向夹紧到视口内，留出 8px 安全边距 */
        x = Math.max(8, Math.min(x, vw - tw - 8));
        y = Math.max(8, Math.min(y, vh - th - 8));

        tipEl.style.left = x + 'px';
        tipEl.style.top = y + 'px';
    }

    /* 显示气泡 */
    function show(target) {
      if (!target || !target.getAttribute) return;
      var text = target.getAttribute('data-tip');
      if (!text) return;
      if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
      ensureTip();
      current = target;
      position(target);
      /* 下一帧再加 show，保证过渡动画触发 */
      tipEl.classList.add('show');
    }

    /* 隐藏气泡 */
    function hide() {
        if (!tipEl) return;
        if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
        tipEl.classList.remove('show');
        tipEl.setAttribute('aria-hidden', 'true');
        current = null;
        /* 等收起动画结束后再 hidden，避免闪烁 */
        hideTimer = setTimeout(function () { if (tipEl) tipEl.hidden = true; }, 160);
    }

    /* 事件委托：统一在 document 上处理悬停 / 聚焦 / 触摸，
       这样对动态插入的节点同样有效，无需逐个绑定。 */
    function bindEvents() {
        /* 鼠标移入：找到最近的带 data-tip 祖先并显示 */
        document.addEventListener('mouseover', function (e) {
            var t = e.target.closest ? e.target.closest('[data-tip]') : null;
            if (t && t !== current) show(t);
        });
        /* 鼠标移出：离开触发元素时隐藏 */
        document.addEventListener('mouseout', function (e) {
            if (!current) return;
            var related = e.relatedTarget;
            if (related && current.contains(related)) return;
            if (related && related.closest && related.closest('[data-tip]') === current) return;
            hide();
        });
        /* 键盘聚焦也弹出（无障碍） */
        document.addEventListener('focusin', function (e) {
            var t = e.target.closest ? e.target.closest('[data-tip]') : null;
            if (t) show(t);
        });
        document.addEventListener('focusout', function () { hide(); });
        /* 点击 / 滚动 / 窗口尺寸变化时隐藏，避免气泡停留在错误位置 */
        document.addEventListener('click', function () { hide(); });
        window.addEventListener('scroll', function () { hide(); }, true);
        window.addEventListener('resize', function () { hide(); });
        /* Esc 关闭 */
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') hide();
        });
    }

    /* 扫描并升级当前文档内的 title 按钮 */
    function scan(root) {
        var scope = root || document;
        var nodes = scope.querySelectorAll ? scope.querySelectorAll(TITLE_SELECTOR) : [];
        for (var i = 0; i < nodes.length; i++) promoteTitle(nodes[i]);
    }

    /* 初始化 */
    function init() {
        ensureTip();
        bindEvents();
        scan(document);

        /* 监听动态插入节点（异步评论、弹窗等），自动升级其 title */
        if (window.MutationObserver) {
            var mo = new MutationObserver(function (mutations) {
                mutations.forEach(function (m) {
                    m.addedNodes.forEach(function (node) {
                        if (node.nodeType === 1) scan(node);
                    });
                });
            });
            mo.observe(document.body, { childList: true, subtree: true });
        }

        /* 视觉走查钩子：URL 带 tip_demo=1 时，持续让「视口中线附近」的收藏
           统计气泡保持显示（滚动后也会自动重新定位），便于截图验收；
           普通访问不会触发，也不影响交互。 */
        if (/[?&]tip_demo=1/.test(location.search)) {
            setInterval(function () {
                var nodes = document.querySelectorAll('.article-card-stats .stat-item');
                var fav = null, nearest = null, bd = 1e9, cy = innerHeight / 2;
                for (var i = 0; i < nodes.length; i++) {
                    var r = nodes[i].getBoundingClientRect();
                    if (r.bottom <= 0 || r.top >= innerHeight) continue;
                    var d = Math.abs(r.top + r.height / 2 - cy);
                    if (d < bd) { bd = d; nearest = nodes[i]; }
                    if ((nodes[i].getAttribute('data-tip') || '').indexOf('收藏') !== -1 &&
                        (!fav || d < fav.d)) { fav = { el: nodes[i], d: d }; }
                }
                var pick = fav ? fav.el : nearest;
                if (pick && pick !== current) show(pick);
            }, 500);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

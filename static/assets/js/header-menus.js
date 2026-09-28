/* ============================================================
 * header-menus.js —— 顶部「工具箱 / 用户头像」下拉菜单逻辑（工单 16）
 *
 * 与通知铃铛一致：header 合成面存在「首帧冻结」，下拉面板若留在 header 中
 * 可能不绘制，故初始化时把面板移入 <main id="main-content"> 并改为 fixed，
 * 按触发器坐标实时定位；支持点击切换、外部点击 / Esc 关闭、滚动与缩放跟随。
 * 工单16：<main> 的入场动画会残留 identity transform
 * （matrix(1,0,0,1,0,0)，非 none），它仍会成为 fixed 的包含块，使面板整体下移
 * 约一个 header 高度。这里在定位时主动检测最近的「transform/filter/perspective
 * 祖先」（即 fixed 的真实包含块），用「目标视口坐标 − 包含块原点」换算，
 * 无论 header 高度 / 动画状态如何，面板都能稳定落在触发器正下方。
 * ============================================================ */
(function () {
    'use strict';

    var mainEl = document.getElementById('main-content') ||
                 document.querySelector('.site-main');

    /* 求 fixed 元素真实包含块的视口原点：
       从父节点向上找第一个带 transform/filter/perspective（非 none）的祖先，
       它就是 fixed 的包含块；没有则相对视口（原点 0,0）。 */
    function containingOrigin(el) {
        var node = el.parentElement;
        while (node && node.nodeType === 1) {
            var cs = getComputedStyle(node);
            if ((cs.transform && cs.transform !== 'none') ||
                (cs.filter && cs.filter !== 'none') ||
                (cs.perspective && cs.perspective !== 'none')) {
                var r = node.getBoundingClientRect();
                return [r.left, r.top];
            }
            node = node.parentElement;
        }
        return [0, 0];
    }

    /* 统一构造一个下拉控制器 */
    function createMenu(btnId, panelId, align) {
        var btn = document.getElementById(btnId);
        var panel = document.getElementById(panelId);
        if (!btn || !panel) return null;

        // 面板移入 main 合成面并 fixed 定位，确保可靠绘制
        if (mainEl && panel.parentElement !== mainEl) {
            mainEl.appendChild(panel);
        }
        panel.style.position = 'fixed';

        function place() {
            var r = btn.getBoundingClientRect();
            var w = panel.offsetWidth || 220;
            var wantLeft;
            if (align === 'left') {
                wantLeft = Math.max(12, Math.min(r.left, innerWidth - w - 12));
            } else {
                wantLeft = Math.max(12, Math.min(r.right - w, innerWidth - w - 12));
            }
            // 期望的视口坐标
            var wantTop = r.bottom + 8;
            // 扣除 fixed 真实包含块（transform 祖先）的原点，得到应设置的 top/left
            var origin = containingOrigin(panel);
            panel.style.left = (wantLeft - origin[0]) + 'px';
            panel.style.top = (wantTop - origin[1]) + 'px';
        }
        function openPanel() {
            place();
            panel.hidden = false;
            btn.classList.add('is-open');
            btn.setAttribute('aria-expanded', 'true');
        }
        function closePanel() {
            panel.hidden = true;
            btn.classList.remove('is-open');
            btn.setAttribute('aria-expanded', 'false');
        }
        function togglePanel() {
            if (panel.hidden) openPanel(); else closePanel();
        }

        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            // 关闭其它已打开的菜单
            document.querySelectorAll('.header-menu-btn.is-open').forEach(function (b) {
                if (b !== btn) b.click();
            });
            togglePanel();
        });
        panel.addEventListener('click', function (e) {
            e.stopPropagation();
        });
        window.addEventListener('resize', function () {
            if (!panel.hidden) place();
        });
        window.addEventListener('scroll', function () {
            if (!panel.hidden) place();
        }, true);

        return { close: closePanel, btn: btn, panel: panel };
    }

    var toolsMenu = createMenu('tools-menu-btn', 'tools-menu-panel', 'right');
    var userMenu = createMenu('user-menu-btn', 'user-menu-panel', 'right');
    var allMenus = [toolsMenu, userMenu].filter(Boolean);

    /* 点击页面任意空白处关闭所有菜单 */
    document.addEventListener('click', function () {
        allMenus.forEach(function (m) { if (!m.panel.hidden) m.close(); });
    });
    /* Esc 关闭 */
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            allMenus.forEach(function (m) { if (!m.panel.hidden) m.close(); });
        }
    });

    /* 工具箱：点击整行（图标按钮之外的区域）等价于点击开关按钮 */
    var toolsPanel = document.getElementById('tools-menu-panel');
    if (toolsPanel) {
        toolsPanel.querySelectorAll('.tool-row').forEach(function (row) {
            row.addEventListener('click', function (e) {
                if (e.target.closest('.theme-toggle')) return; // 点按钮本身，不重复触发
                var b = row.querySelector('.theme-toggle');
                if (b) b.click();
            });
        });
    }
})();

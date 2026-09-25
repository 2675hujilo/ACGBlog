/**
 * focus_mode.js —— 专注阅读模式（第4轮新增）
 * 功能：
 *   1. 点击 .focus-toggle 切换 body.focus-mode-active；
 *   2. 激活后隐藏左右侧栏、文章区居中加宽、导航栏折叠；
 *   3. 状态存入 localStorage('focus_mode')，刷新后恢复；
 *   4. 按钮文字在「专注喵」/「退出专注喵」之间切换。
 * 依赖：无。仅详情页存在 .focus-toggle 时生效。
 */
(function () {
    'use strict';

    var BTN_TEXT_ON = '退出专注喵';
    var BTN_TEXT_OFF = '专注喵';

    function apply(on) {
        document.body.classList.toggle('focus-mode-active', on);
        var btn = document.querySelector('.focus-toggle');
        if (btn) {
            /* 只更新文字 span，保留前置图标 img（Bug23） */
            var txt = btn.querySelector('.focus-text');
            if (txt) txt.textContent = on ? BTN_TEXT_ON : BTN_TEXT_OFF;
            else btn.textContent = on ? BTN_TEXT_ON : BTN_TEXT_OFF;
            btn.setAttribute('aria-pressed', on ? 'true' : 'false');
        }
        try { localStorage.setItem('focus_mode', on ? 'true' : 'false'); } catch (e) {}
    }

    function init() {
        var btn = document.querySelector('.focus-toggle');
        if (!btn) return;

        /* 恢复上次状态 */
        var saved = false;
        try { saved = localStorage.getItem('focus_mode') === 'true'; } catch (e) {}
        apply(saved);

        btn.addEventListener('click', function () {
            apply(!document.body.classList.contains('focus-mode-active'));
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

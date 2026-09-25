/**
 * theme.js —— 明暗主题切换脚本（第3轮增强：自动跟随系统）
 * 功能：
 *   1. 点击导航栏主题按钮在亮色 / 暗色之间切换；
 *   2. 通过 <html data-theme="dark"> 切换，样式由 base.css 变量覆盖实现；
 *   3. 偏好持久化到 localStorage；
 *   4. 【新增】未手动设置过主题时，自动跟随系统 prefers-color-scheme；
 *      一旦用户手动点击切换，标记 theme_manual=1，不再自动跟随；
 *   5. 按钮图标随主题切换（暗色显示 ☀️，亮色显示 🌙）。
 * 防闪烁：base.html <head> 内联脚本在首帧已设置 data-theme。
 * 依赖：无。
 */
(function () {
    'use strict';

    var btn = document.getElementById('theme-toggle');

    function current() {
        return document.documentElement.getAttribute('data-theme') || 'light';
    }

    /** 设置主题并持久化 */
    function setTheme(t) {
        document.documentElement.setAttribute('data-theme', t);
        try { localStorage.setItem('theme', t); } catch (e) {}
        if (btn) btn.textContent = t === 'dark' ? '☀️' : '🌙';
    }

    /* ---------- URL 参数指定主题（?theme=dark|light） ----------
       实用特性：可通过链接直接分享指定主题（如 /?theme=dark），打开即应用并记住；
       同时便于多主题自动化实测。非法值忽略，不影响正常逻辑。 */
    (function applyThemeFromUrl() {
        try {
            var m = new RegExp('[?&]theme=(dark|light)\\b').exec(location.search);
            if (m) {
                setTheme(m[1]);
                // 显式通过链接指定，视为手动选择，停止跟随系统
                try { localStorage.setItem('theme_manual', '1'); } catch (e) {}
            }
        } catch (e) {}
    }());

    /* ---------- 自动跟随系统（仅未手动时） ---------- */
    var mq = window.matchMedia('(prefers-color-scheme: dark)');
    function followSystem() {
        // 已手动设置过则不跟随
        try { if (localStorage.getItem('theme_manual')) return; } catch (e) {}
        setTheme(mq.matches ? 'dark' : 'light');
    }
    // 旧版 Safari 用 addListener
    if (mq.addEventListener) mq.addEventListener('change', followSystem);
    else if (mq.addListener) mq.addListener(followSystem);

    /* ---------- 手动点击切换 ---------- */
    if (btn) {
        btn.addEventListener('click', function () {
            var next = current() === 'dark' ? 'light' : 'dark';
            setTheme(next);
            // 标记为手动模式，停止跟随系统
            try { localStorage.setItem('theme_manual', '1'); } catch (e) {}
        });
        btn.textContent = current() === 'dark' ? '☀️' : '🌙';
    }
})();

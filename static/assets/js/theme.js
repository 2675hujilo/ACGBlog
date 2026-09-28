/* ============================================================================
 * theme.js —— 明暗主题切换（第 3 轮增强：自动跟随系统 + URL 指定）
 * ----------------------------------------------------------------------------
 * 切换机制：在 <html> 上设置 data-theme="dark|light"，base.css 通过
 *          [data-theme='dark'] 覆盖一套 CSS 变量实现整体换色。
 *
 * 三条主题来源（优先级从高到低）：
 *   1. 用户手动点击切换（写入 localStorage 'theme'，并标记 'theme_manual'=1）；
 *   2. URL 参数 ?theme=dark|light（视为手动选择，会被记住，也便于自动化实测）；
 *   3. 自动跟随系统 prefers-color-scheme（仅当用户从未手动设置过时生效）。
 *
 * 持久化：localStorage 'theme' 存当前主题，'theme_manual' 标记是否手动。
 * 防闪烁：base.html <head> 内联脚本已在首帧设置 data-theme，本脚本只负责交互。
 * 按钮图标：暗色显示 ☀️（提示可切到亮色），亮色显示 🌙。
 * ----------------------------------------------------------------------------
 * 排错与联动速查：
 *   · 存储键：'theme'（dark|light）、'theme_manual'（存在即表示用户手动选择）；
 *   · 首帧防闪烁由 base.html <head> 内联脚本完成，本脚本只处理交互与跟随系统；
 *   · 想「恢复跟随系统」：清掉 localStorage 的 theme_manual 后刷新即可；
 *   · ?theme= 参数同时服务于多主题自动化实测，属刻意保留的便利特性；
 *   · 暗黑配色全部来自 base.css 的 [data-theme='dark'] 变量，改色请改变量而非
 *     逐元素覆盖；AMOLED 纯黑由 body.amoled-dark 在此基础上进一步压暗。
 * ============================================================================ */
(function () {
    'use strict';

    // 导航栏主题切换按钮
    var btn = document.getElementById('theme-toggle');

    /** 读取当前主题（默认亮色）。 */
    function current() {
        return document.documentElement.getAttribute('data-theme') || 'light';
    }

    /**
     * 设置主题、持久化并更新按钮图标。
     * @param {string} t - 'dark' 或 'light'。
     */
    function setTheme(t) {
        // 写到文档根元素，触发 CSS 变量切换
        document.documentElement.setAttribute('data-theme', t);
        // 记住选择；存储不可用时忽略
        try { localStorage.setItem('theme', t); } catch (err) {}
        // 更新按钮图标：暗色下显示太阳，亮色下显示月亮
        if (btn) btn.textContent = t === 'dark' ? '☀️' : '🌙';
    }

    /* ---------- 来源②：URL 参数 ?theme=dark|light ---------- */
    (function applyThemeFromUrl() {
        try {
            // 正则从查询串提取 theme 值（仅接受 dark / light）
            var m = new RegExp('[?&]theme=(dark|light)\\b').exec(location.search);
            if (m) {
                // 应用该主题
                setTheme(m[1]);
                // 显式链接指定视为手动，停止跟随系统
                try { localStorage.setItem('theme_manual', '1'); } catch (err) {}
            }
        } catch (err) {}
    }());

    /* ---------- 来源③：自动跟随系统（仅未手动时） ---------- */
    // 监听系统明暗偏好
    var mq = window.matchMedia('(prefers-color-scheme: dark)');

    /** 跟随系统设置主题；若用户已手动选择则直接返回。 */
    function followSystem() {
        // 已手动标记过则不再跟随
        try {
            if (localStorage.getItem('theme_manual')) return;
        } catch (err) {}
        // 按系统偏好在暗 / 亮间设置
        setTheme(mq.matches ? 'dark' : 'light');
    }

    // 绑定系统主题变化（现代浏览器用 addEventListener，旧 Safari 用 addListener）
    if (mq.addEventListener) {
        mq.addEventListener('change', followSystem);
    } else if (mq.addListener) {
        mq.addListener(followSystem);
    }

    /* ---------- 来源①：手动点击切换 ---------- */
    if (btn) {
        btn.addEventListener('click', function () {
            // 在当前主题基础上取反
            var next = current() === 'dark' ? 'light' : 'dark';
            setTheme(next);
            // 标记手动，从此停止跟随系统
            try { localStorage.setItem('theme_manual', '1'); } catch (err) {}
        });
        // 初始化按钮图标
        btn.textContent = current() === 'dark' ? '☀️' : '🌙';
    }
})();

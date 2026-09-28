/* ============================================================================
 * error_theme_fix.js —— 错误页的主题防闪烁 + 返回按钮
 * ----------------------------------------------------------------------------
 * 错误页（404/500 等）可能不加载完整的 base 脚本，因此在此独立完成两件事：
 *
 * 1) 主题防闪烁（与 base_theme_fix.js 同逻辑）：
 *    在首帧前按 localStorage / 系统偏好设置 data-theme，保证错误页配色与全站
 *    一致、暗色用户不会看到刺眼白屏；异常时兜底亮色。
 *
 * 2) 返回按钮（第三轮迁移）：
 *    原 500.html 内联 onclick="history.back()" 外移为事件委托；
 *    有浏览历史则 history.back() 返回上一页，无历史（如直接打开错误页）
 *    则回首页 '/' 兜底。
 *
 * 注意：用事件委托监听点击，错误页只要有 .btn-back 即可生效，无需内联脚本。
 * ----------------------------------------------------------------------------
 * 排错速查：
 *   · 错误页可能不加载完整 base 脚本，故主题逻辑在此独立实现，勿假设 base
 *     主题脚本一定运行；
 *   · .btn-back 采用事件委托：按钮是静态还是动态插入都能响应；
 *   · history.length 在某些浏览器对「新开标签直接进入错误页」也可能 >1，
 *     因此回退后若仍异常，用户可再用页面上的首页链接（双保险）；
 *   · 相关文件：base_theme_fix.js（正常页主题）、各 error*.html 模板与
 *     cute_error_pages 中间件（决定错误页渲染内容）。
 * ============================================================================ */
/* ---- 第一部分：错误页主题设定 ---- */
(function () {
    'use strict';
    try {
        var stored = localStorage.getItem('theme');
        var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        var theme = stored || (prefersDark ? 'dark' : 'light');
        document.documentElement.setAttribute('data-theme', theme);
    } catch (err) {
        document.documentElement.setAttribute('data-theme', 'light');
    }
})();

/* ---- 第二部分：返回上一页 / 回首页 ---- */
(function () {
    'use strict';
    document.addEventListener('click', function (event) {
        // closest 兼容点击到按钮内图标 / 文字的情况
        var btn = event.target.closest('.btn-back');
        if (!btn) return;
        event.preventDefault();
        // 有历史则返回，否则回首页
        if (window.history.length > 1) {
            history.back();
        } else {
            window.location.href = '/';
        }
    });
})();

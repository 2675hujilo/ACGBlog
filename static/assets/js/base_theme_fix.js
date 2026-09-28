/* ============================================================================
 * base_theme_fix.js —— 明暗主题「渲染前」防闪烁设定
 * ----------------------------------------------------------------------------
 * 引入位置：base.html 的 <head> 最早期、绘制前同步执行。
 *
 * 解决的问题：
 *   若等普通脚本在 DOMContentLoaded 后再设置 data-theme，浏览器会先用默认
 *   （亮色）绘制一帧，暗色用户会看到明显的「白屏一闪」。本脚本在首帧前
 *   就把 data-theme 写到 <html> 上，CSS 据此第一时间给出正确配色。
 *
 * 主题判定优先级：
 *   1. localStorage 的 'theme' 键（用户在站内手动切换后的选择，最优先）；
 *   2. 系统偏好 prefers-color-scheme: dark（跟随操作系统）；
 *   3. 兜底为亮色 light。
 *
 * 注意点：localStorage 不可用（隐私模式等）时 try/catch 兜底为亮色，
 * 绝不阻断 <head> 解析。
 * ============================================================================ */
(function () {
    'use strict';
    try {
        // 读取本地保存的主题；未保存则读取系统明暗偏好
        var stored = localStorage.getItem('theme');
        var prefersDark = window.matchMedia('(prefers-color-scheme: dark').matches;
        var theme = stored || (prefersDark ? 'dark' : 'light');

        // 写到文档根元素：全站 CSS 通过 [data-theme='dark'] 切换暗色变量
        document.documentElement.setAttribute('data-theme', theme);
    } catch (err) {
        // 存储 / matchMedia 异常时兜底亮色，保证页面可读
        document.documentElement.setAttribute('data-theme', 'light');
    }
})();

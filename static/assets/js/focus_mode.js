/* ============================================================================
 * focus_mode.js —— 专注阅读模式（第 4 轮新增）
 * ----------------------------------------------------------------------------
 * 适用页面：文章详情页（仅当页面存在 .focus-toggle 按钮时生效）。
 *
 * 功能总览：
 *   1. 点击 .focus-toggle 切换 <body> 上的 .focus-mode-active 类；
 *   2. 激活后由 CSS 隐藏左右侧栏、文章主体居中并加宽、折叠导航，
 *      让读者只聚焦正文，减少干扰；
 *   3. 状态写入 localStorage('focus_mode')，刷新 / 下次访问自动恢复；
 *   4. 按钮文案在「专注喵」/「退出专注喵」之间切换，并同步 aria-pressed
 *      以保证可访问性（屏幕阅读器可感知开关状态）。
 *
 * 依赖：无第三方库。
 * 注意点：只更新按钮内 .focus-text 文字节点，保留前置图标（修复过的 Bug23），
 *        避免整按钮 textContent 覆盖把图标也删掉。
 * ----------------------------------------------------------------------------
 * 排错速查：
 *   · 状态类在 body（focus-mode-active），布局变化全部由 CSS 完成，本脚本只
 *     切换类名 / 文案 / aria-pressed；
 *   · 存储键 'focus_mode' 的值是字符串 'true'/'false'，比较时注意类型；
 *   · 只改 .focus-text 保留图标（Bug23）；若模板没有 .focus-text 才整按钮兜底；
 *   · 专注模式与暗黑 / 护眼 / 字号等偏好正交，可叠加使用；
 *   · 相关文件：详情页模板（按钮）、reading.css 或正文相关 CSS（专注态排版）。
 * ============================================================================ */
(function () {
    'use strict';

    // 按钮两种文案：激活态显示「退出」，未激活显示「进入」
    var BTN_TEXT_ON = '退出专注喵';
    var BTN_TEXT_OFF = '专注喵';

    /**
     * 应用专注模式状态。
     * @param {boolean} on - true 进入专注，false 退出。
     */
    function apply(on) {
        // 切换 body 类：CSS 据此隐藏侧栏、重排版心
        document.body.classList.toggle('focus-mode-active', on);

        var btn = document.querySelector('.focus-toggle');
        if (btn) {
            // 只改文字 span，保留按钮里的图标 img（Bug23）
            var txt = btn.querySelector('.focus-text');
            if (txt) {
                txt.textContent = on ? BTN_TEXT_ON : BTN_TEXT_OFF;
            } else {
                btn.textContent = on ? BTN_TEXT_ON : BTN_TEXT_OFF;
            }
            // 同步无障碍「按下」状态
            btn.setAttribute('aria-pressed', on ? 'true' : 'false');
        }

        // 持久化到 localStorage；存储不可用时静默忽略
        try {
            localStorage.setItem('focus_mode', on ? 'true' : 'false');
        } catch (err) {}
    }

    /** 初始化：恢复状态并绑定点击。 */
    function init() {
        var btn = document.querySelector('.focus-toggle');
        // 详情页以外没有该按钮，直接退出
        if (!btn) return;

        // 恢复上次的专注状态（默认关闭）
        var saved = false;
        try {
            saved = localStorage.getItem('focus_mode') === 'true';
        } catch (err) {}
        apply(saved);

        // 点击按钮：在当前状态基础上取反
        btn.addEventListener('click', function () {
            var active = document.body.classList.contains('focus-mode-active');
            apply(!active);
        });
    }

    // DOM 未就绪则等待，否则直接初始化（兼容脚本在底部加载的情况）
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

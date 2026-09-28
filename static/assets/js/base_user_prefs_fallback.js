/* ============================================================================
 * base_user_prefs_fallback.js —— 用户个性化偏好的「渲染前」早期兜底
 * ----------------------------------------------------------------------------
 * 引入位置：base.html 的 <head> 内、CSS 之后尽早执行（必须在首屏绘制前）。
 *
 * 解决的问题（防闪烁 / FOUC）：
 *   用户在个人设置里可关闭动效、开启护眼底色、开启 AMOLED 纯黑暗黑。
 *   这些偏好若等到 DOMContentLoaded 后再由普通脚本加类，首屏会先用默认样式
 *   绘制一帧、随后「跳变」成用户偏好（明显闪烁）。本脚本在解析到此处时就
 *   同步读取偏好并把对应类名挂到 <html>/<body> 上，使首屏第一帧即正确。
 *
 * 数据来源（两处，按场景取并集）：
 *   · window.USER_PREFERENCES —— 已登录用户由后端 context_processors 注入的偏好；
 *   · localStorage            —— 未登录访客或前端本地保存的设置（键见下）。
 *
 * 会挂载的类名：
 *   · <html>.motion-off      关闭入场 / 跟随等动效（对应「关闭特效」）；
 *   · <body>.eye-protection  护眼模式（柔和米黄底色）；
 *   · <body>.amoled-dark     AMOLED 纯黑暗黑（在暗黑基础上把背景压成纯黑）。
 *
 * 注意点：
 *   · 整段包在 try/catch 中：localStorage 在隐私模式 / 被禁用时会抛错，
 *     绝不能因为偏好读取失败而阻断 <head> 解析；
 *   · 本文件刻意保持零依赖、零网络请求，执行耗时可忽略。
 * ============================================================================ */
(function () {
    'use strict';
    try {
        // 后端注入的登录用户偏好；未登录时为 undefined，用 {} 兜底
        var prefs = window.USER_PREFERENCES || {};

        // ---- 动效开关：优先读本地手动开关 moe_motion，否则看后端 effects_enabled ----
        var motionLocal = localStorage.getItem('moe_motion');
        // 本地显式设过 '0'，或后端偏好里 effects_enabled === false → 关闭动效
        var motionOff = (motionLocal !== null ? motionLocal === '0'
                                              : prefs.effects_enabled === false);
        if (motionOff) {
            // 挂到文档根元素：全站 CSS 据此停用动画 / 过渡
            document.documentElement.classList.add('motion-off');
        }

        // ---- 护眼 / AMOLED：先以后端偏好为初值，再用本地阅读偏好覆盖 ----
        var eye = prefs.eye_protection;     // 护眼模式
        var amoled = prefs.amoled_dark;     // AMOLED 纯黑

        // 前端阅读设置面板把偏好存在 blog_reading_prefs（JSON 字符串）
        var readingLocal = localStorage.getItem('blog_reading_prefs');
        if (readingLocal) {
            try {
                var readingPrefs = JSON.parse(readingLocal);
                // 本地勾选过护眼 / 纯黑则置真（与后端取并集，任一为真即生效）
                if (readingPrefs.eyeProtection) eye = true;
                if (readingPrefs.amoled) amoled = true;
            } catch (parseErr) {
                // 本地数据损坏时忽略，沿用后端偏好
            }
        }

        // 护眼：给 body 加类，由 CSS 叠加米黄底色
        if (eye) document.body.classList.add('eye-protection');
        // AMOLED：给 body 加类，由 CSS 把暗黑背景进一步压成纯黑
        if (amoled) document.body.classList.add('amoled-dark');
    } catch (outerErr) {
        // 任何意外（存储不可用等）都静默忽略，绝不影响页面加载
    }
})();

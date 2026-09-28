/* ============================================================================
 * waifu-footer-avoid.js —— 看板娘避让页脚统计带
 * ----------------------------------------------------------------------------
 * 场景：页脚有一条「统计带」.footer-stats-band，滚动进入视口时，看板娘若
 *      停在右下角会遮挡统计数字。本脚本在统计带进入视口时把看板娘淡出 /
 *      下移并禁用其指针事件，离开视口后再恢复。
 *
 * 实现：使用 IntersectionObserver 观察统计带，threshold 0.08 表示露出约 8%
 *      即触发（比 0 更稳，避免一两个像素抖动反复触发）。
 *
 * 时序：看板娘由 waifu-init-new.js 动态创建，故用轮询（每 300ms，最多约
 *      15 秒）等待 #waifu 出现。
 *
 * 联动：恢复 transform 时需保留移动端缩放（601~760 为 scale(.65)，
 *      与 waifu-mobile.js 约定一致），否则平板上看板娘会突然变大。
 * ----------------------------------------------------------------------------
 * 排错速查：
 *   · 观察目标 .footer-stats-band，threshold 0.08（露出约 8% 才触发），可减少
 *     边界像素抖动导致的反复淡入淡出；
 *   · 隐藏时同时禁用 pointerEvents，避免看板娘虽透明仍拦截点击；
 *   · 恢复 transform 必须保留 601~760 的 scale(.65)，与 waifu-mobile.js 约定
 *     一致，否则平板上看板娘会突然变大；
 *   · 不支持 IntersectionObserver 时直接停止轮询、不做避让（优雅降级）；
 *   · 相关文件：waifu-mobile.js、页脚模板（统计带）。
 * ============================================================================ */
(function () {
    'use strict';

    /** 尝试启动观察；元素就绪则绑定并返回 true。 */
    function start() {
        var band = document.querySelector('.footer-stats-band');
        var waifu = document.getElementById('waifu');

        // 不支持 IntersectionObserver 时直接返回 true（停止轮询，不做避让）
        if (!band || !waifu || !('IntersectionObserver' in window)) return true;

        // 给看板娘加透明 / 位移过渡，使淡入淡出更柔和
        waifu.style.transition = 'opacity .28s ease, transform .28s ease';

        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    // 统计带进入视口：淡出、下移、禁用点击
                    waifu.style.setProperty('opacity', '0', 'important');
                    waifu.style.setProperty('transform', 'translateY(24px)', 'important');
                    waifu.style.pointerEvents = 'none';
                } else {
                    // 离开：恢复显示
                    waifu.style.setProperty('opacity', '1', 'important');
                    // 恢复时保留移动端缩放（601~760 为 .65，否则 none）
                    var restoreTransform =
                        (window.innerWidth <= 760 && window.innerWidth > 600)
                        ? 'scale(.65)' : 'none';
                    waifu.style.setProperty('transform', restoreTransform, 'important');
                    waifu.style.pointerEvents = '';
                }
            });
        }, { threshold: 0.08 });

        // 开始观察统计带
        io.observe(band);
        return true;
    }

    // 轮询等待元素就绪：成功或超过 50 次（约 15 秒）后停止
    var tries = 0;
    var timer = setInterval(function () {
        tries++;
        if (start() || tries > 50) clearInterval(timer);
    }, 300);
})();

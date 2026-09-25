/**
 * waifu-footer-avoid.js —— 看板娘避让页脚
 * 页脚统计带滚动进入视口时淡出看板娘，避免遮挡统计；离开后恢复。
 * 看板娘由 waifu-init-new.js 动态创建（#waifu），本脚本用轮询等待其出现。
 */
(function () {
    'use strict';

    function start() {
        var band = document.querySelector('.footer-stats-band');
        var w = document.getElementById('waifu');
        if (!band || !w || !('IntersectionObserver' in window)) return true;

        w.style.transition = 'opacity .28s ease, transform .28s ease';
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (en) {
                if (en.isIntersecting) {
                    w.style.setProperty('opacity', '0', 'important');
                    w.style.setProperty('transform', 'translateY(24px)', 'important');
                    w.style.pointerEvents = 'none';
                } else {
                    w.style.setProperty('opacity', '1', 'important');
                    // 恢复时保留移动端缩放（waifu-mobile.js 约定 601~760 为 .65）
                    var restoreT = (window.innerWidth <= 760 && window.innerWidth > 600)
                        ? 'scale(.65)' : 'none';
                    w.style.setProperty('transform', restoreT, 'important');
                    w.style.pointerEvents = '';
                }
            });
        }, { threshold: 0.08 });
        io.observe(band);
        return true;
    }

    // 等待 #waifu / 页脚就绪（最多约 15 秒）
    var tries = 0;
    var timer = setInterval(function () {
        tries++;
        if (start() || tries > 50) clearInterval(timer);
    }, 300);
})();

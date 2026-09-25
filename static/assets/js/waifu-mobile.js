/**
 * waifu-mobile.js —— 看板娘移动端适配
 *
 * waifu-init-new.js 会给 #waifu 写入 display:block !important、
 * transform:none !important 等内联样式，普通样式表无法覆盖；
 * 因此窄屏下由本脚本直接改写内联样式：
 *   ≤600px   隐藏（避免遮挡评论按钮等可点区域）；
 *   601~760px 缩小到 65%，贴右下角；
 *   >760px   恢复默认。
 * 看板娘为动态创建，脚本用轮询等待 #waifu 出现。
 */
(function () {
    'use strict';

    function apply(w) {
        var vw = window.innerWidth;
        if (vw <= 600) {
            w.style.setProperty('display', 'none', 'important');
        } else {
            w.style.setProperty('display', 'block', 'important');
            if (vw <= 760) {
                w.style.setProperty('transform', 'scale(.65)', 'important');
                w.style.transformOrigin = 'right bottom';
            } else {
                w.style.setProperty('transform', 'none', 'important');
                w.style.transformOrigin = '';
            }
        }
    }

    function start() {
        var w = document.getElementById('waifu');
        if (!w) return false;
        apply(w);
        window.addEventListener('resize', function () { apply(w); }, { passive: true });
        // 避让页脚脚本在离开页脚时会重写 transform，滚动时按当前宽度校正
        window.addEventListener('scroll', function () {
            if (window.innerWidth <= 760 && window.innerWidth > 600) apply(w);
        }, { passive: true });
        return true;
    }

    // 等待 #waifu 就绪（最多约 18 秒）
    var tries = 0;
    var timer = setInterval(function () {
        tries++;
        if (start() || tries > 60) clearInterval(timer);
    }, 300);
})();

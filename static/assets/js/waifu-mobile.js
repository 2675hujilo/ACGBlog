/* ============================================================================
 * waifu-mobile.js —— 看板娘（Live2D）移动端 / 窄屏适配
 * ----------------------------------------------------------------------------
 * 背景（为何要用 JS 而不是媒体查询）：
 *   waifu-init-new.js 初始化时会给 #waifu 写入 display:block !important、
 *   transform:none !important 等内联样式。内联 + !important 优先级最高，
 *   普通样式表 / @media 无法覆盖，只能由本脚本直接改写内联样式。
 *
 * 三档宽度策略：
 *   · 视口宽 ≤ 600px   ：隐藏看板娘（避免遮挡评论 / 点赞等可点区域）；
 *   · 601 ~ 760px      ：缩小到 65%，贴右下角，保留趣味又不挡内容；
 *   · > 760px          ：恢复默认尺寸与位置。
 *
 * 时序：看板娘是运行时动态创建的，#waifu 一开始不存在，因此用轮询
 *      （每 300ms 一次，最多约 18 秒）等其出现后再绑定。
 *
 * 联动：waifu-footer-avoid.js 在离开页脚时会重写 transform，故本脚本
 *      额外监听 scroll，在 601~760 区间把 transform 校正回 .65。
 * ----------------------------------------------------------------------------
 * 排错速查：
 *   · 必须用 setProperty(..., 'important') 才能压过初始化脚本写入的内联
 *     !important；普通赋值 / 媒体查询都不生效；
 *   · 三档分界 600 / 760 与 waifu-footer-avoid.js 的恢复逻辑共用，改动需同步；
 *   · 轮询上限约 18 秒：若看板娘脚本异常未创建 #waifu，本脚本会自动停止；
 *   · 相关文件：waifu-footer-avoid.js（避让页脚）、live2d 初始化脚本、
 *     blog/live2d.py（看板娘相关后端端点）。
 * ============================================================================ */
(function () {
    'use strict';

    /**
     * 按当前视口宽度设置看板娘的显隐与缩放。
     * @param {HTMLElement} waifu - #waifu 元素。
     */
    function apply(waifu) {
        var vw = window.innerWidth;

        if (vw <= 600) {
            // 窄屏：强制隐藏，腾出可点区域
            waifu.style.setProperty('display', 'none', 'important');
        } else {
            // 非窄屏先恢复显示
            waifu.style.setProperty('display', 'block', 'important');
            if (vw <= 760) {
                // 平板 / 大屏手机：缩小并以右下角为缩放原点
                waifu.style.setProperty('transform', 'scale(.65)', 'important');
                waifu.style.transformOrigin = 'right bottom';
            } else {
                // 桌面：恢复原始变换
                waifu.style.setProperty('transform', 'none', 'important');
                waifu.style.transformOrigin = '';
            }
        }
    }

    /** 尝试启动：找到 #waifu 则应用并绑定 resize/scroll，返回是否成功。 */
    function start() {
        var waifu = document.getElementById('waifu');
        if (!waifu) return false;

        apply(waifu);

        // 窗口尺寸变化时重新应用（passive 表示不阻止滚动，性能更好）
        window.addEventListener('resize', function () {
            apply(waifu);
        }, { passive: true });

        // 滚动时校正 601~760 区间的缩放（避让页脚脚本可能改写 transform）
        window.addEventListener('scroll', function () {
            if (window.innerWidth <= 760 && window.innerWidth > 600) {
                apply(waifu);
            }
        }, { passive: true });

        return true;
    }

    // 轮询等待看板娘就绪：成功或超过 60 次（约 18 秒）后停止
    var tries = 0;
    var timer = setInterval(function () {
        tries++;
        if (start() || tries > 60) clearInterval(timer);
    }, 300);
})();

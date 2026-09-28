/* ============================================================================
 * base_page_progress.js —— 顶部页面加载进度条
 * ----------------------------------------------------------------------------
 * 引入位置：base.html 顶部，进度条元素 #page-loader 在 <body> 最前面。
 *
 * 视觉与时间线：
 *   · 初始（HTML 解析中）进度条停在很小的宽度，提示「正在加载」；
 *   · DOMContentLoaded（DOM 结构就绪）→ 宽度推进到 60%；
 *   · window load（图片等全部资源加载完）→ 冲到 100%，加 .done 类淡出；
 *   · 淡出后把宽度归零，方便下次进入时重新播放。
 *
 * 兜底机制（重要）：
 *   个别资源一直 pending 时 load 事件可能迟迟不触发，因此设 2.5 秒定时器，
 *   若进度条还没 .done 就强制完成，避免进度条永久挂在顶部。
 *
 * 注意：这是「体感」进度条（不反映真实字节进度），仅用于加载反馈。
 * ============================================================================ */
(function () {
    'use strict';

    // 取顶部进度条元素；页面没有该元素时直接退出（如特殊精简页）
    var bar = document.getElementById('page-loader');
    if (!bar) return;

    // 设置进度条宽度的小工具：w 为 0~100
    function setWidth(w) {
        bar.style.width = w + '%';
    }

    // DOM 结构就绪 → 60%
    document.addEventListener('DOMContentLoaded', function () {
        setWidth(60);
    });

    // 全部资源加载完成 → 100% 并淡出、归零
    window.addEventListener('load', function () {
        setWidth(100);
        // 稍作停留让用户看到满格，再加 done 类触发淡出动画
        setTimeout(function () { bar.classList.add('done'); }, 300);
        // 淡出动画结束后归零，便于下次进入重新播放
        setTimeout(function () { bar.style.width = '0'; }, 900);
    });

    // 兜底：2.5 秒仍未完成则强制满格并淡出，防止进度条卡死
    setTimeout(function () {
        if (!bar.classList.contains('done')) {
            setWidth(100);
            bar.classList.add('done');
        }
    }, 2500);
})();

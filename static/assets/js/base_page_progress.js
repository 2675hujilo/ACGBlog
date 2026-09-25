/* 页面加载进度条：DOMContentLoaded 起步到 60%，load 事件冲到 100% 后淡出 */
(function () {
    var bar = document.getElementById('page-loader');
    if (!bar) return;
    function setWidth(w) { bar.style.width = w + '%'; }
    document.addEventListener('DOMContentLoaded', function () { setWidth(60); });
    window.addEventListener('load', function () {
        setWidth(100);
        setTimeout(function () { bar.classList.add('done'); }, 300);
        // 动画结束后再彻底归零，方便下次跳转（SPA 不适用时也无害）
        setTimeout(function () { bar.style.width = '0'; }, 900);
    });
    // 兜底：若 load 未触发（极端情况），2.5 秒后强制完成
    setTimeout(function () { if (!bar.classList.contains('done')) { setWidth(100); bar.classList.add('done'); } }, 2500);
})();
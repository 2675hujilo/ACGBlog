(function () {
    try {
        var t = localStorage.getItem('theme') ||
            (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
        document.documentElement.setAttribute('data-theme', t);
    } catch (e) { document.documentElement.setAttribute('data-theme', 'light'); }
})();

/* 错误页返回按钮（第三轮迁移：原 500.html 内联 onclick="history.back()" 外移）。
   500 页才有 .btn-back；无历史时回首页兜底。 */
(function () {
    'use strict';
    document.addEventListener('click', function (e) {
        var b = e.target.closest('.btn-back');
        if (!b) return;
        e.preventDefault();
        if (window.history.length > 1) history.back();
        else window.location.href = '/';
    });
})();
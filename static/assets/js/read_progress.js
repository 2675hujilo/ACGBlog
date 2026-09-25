/**
 * read_progress.js —— 阅读进度记忆（第3轮新增）
 * 记录每篇文章滚动位置到 localStorage（read_progress_{id}）；
 * 有记录时底部提示"上次读到这里啦，要继续吗？"，点击平滑滚动恢复；
 * 滚动 500ms 节流保存；滚到 80% 视为读完清除记录。
 * 依赖：无。仅文章详情页生效。
 */
(function () {
    'use strict';
    var m = window.location.pathname.match(/\/article\/(\d+)/);
    if (!m) return;
    var KEY = 'read_progress_' + m[1];
    var doc = document.documentElement;
    var saved = 0;
    try { saved = parseInt(localStorage.getItem(KEY) || '0', 10); } catch (e) {}

    function maxScroll() { return Math.max(doc.scrollHeight, document.body.scrollHeight) - window.innerHeight; }
    function curY() { return window.scrollY || doc.scrollTop || 0; }

    function showPrompt() {
        var bar = document.createElement('div');
        bar.className = 'read-progress-bar';
        bar.innerHTML =
            '<span>\u{1F43E} 上次读到这里啦，要继续吗？</span><span class="rp-actions">' +
            '<button class="rp-resume" type="button">\u7EE7\u7EED</button>' +
            '<button class="rp-dismiss" type="button">\u4E0D\u4E86</button></span>';
        document.body.appendChild(bar);
        bar.querySelector('.rp-resume').addEventListener('click', function () {
            window.scrollTo({ top: saved, behavior: 'smooth' }); bar.remove();
        });
        bar.querySelector('.rp-dismiss').addEventListener('click', function () { bar.remove(); });
        setTimeout(function () { if (bar.parentNode) bar.remove(); }, 8000);
    }

    if (saved > 200 && saved < maxScroll() - 100) setTimeout(showPrompt, 600);

    var timer = null, done = false;
    window.addEventListener('scroll', function () {
        var y = curY(), max = maxScroll();
        if (!done && max > 0 && y / max >= 0.8) {
            done = true;
            try { localStorage.removeItem(KEY); } catch (e) {}
            return;
        }
        if (timer) return;
        timer = setTimeout(function () {
            timer = null;
            try {
                if (y > 200) localStorage.setItem(KEY, String(Math.round(y)));
                else localStorage.removeItem(KEY);
            } catch (e) {}
        }, 500);
    }, { passive: true });
})();

/**
 * image_lightbox.js —— 文章正文图片灯箱（第3轮新增）
 * 功能：
 *   1. .article-body 内图片点击后全屏遮罩放大；
 *   2. 遮罩半透明，图片居中最大 90vw/90vh；
 *   3. 点遮罩 / 关闭按钮 / ESC 关闭；
 *   4. 多图时左右箭头切换上一张/下一张；
 *   5. 加载时显示旋转动画。
 * 依赖：无。样式在 ui_polish.css（.lightbox-*）。
 */
(function () {
    'use strict';

    var body = document.querySelector('.article-body');
    if (!body) return;
    var imgs = Array.prototype.slice.call(body.querySelectorAll('img'));
    if (!imgs.length) return;

    var overlay = null, current = 0;

    function build() {
        overlay = document.createElement('div');
        overlay.className = 'lightbox-overlay';
        overlay.innerHTML =
            '<div class="lightbox-loading"></div>' +
            '<img class="lightbox-img" alt="">' +
            '<button class="lightbox-btn lightbox-close" type="button" aria-label="\u5173\u95ed">\u00d7</button>' +
            '<button class="lightbox-btn lightbox-prev" type="button" aria-label="\u4e0a\u4e00\u5f20">\u2039</button>' +
            '<button class="lightbox-btn lightbox-next" type="button" aria-label="\u4e0b\u4e00\u5f20">\u203a</button>';
        document.body.appendChild(overlay);

        overlay.querySelector('.lightbox-close').addEventListener('click', close);
        overlay.querySelector('.lightbox-prev').addEventListener('click', function (e) { e.stopPropagation(); go(-1); });
        overlay.querySelector('.lightbox-next').addEventListener('click', function (e) { e.stopPropagation(); go(1); });
        overlay.addEventListener('click', function (e) { if (e.target === overlay) close(); });
        document.addEventListener('keydown', onKey);
    }

    function show(i) {
        if (!overlay) build();
        current = (i + imgs.length) % imgs.length;
        var img = overlay.querySelector('.lightbox-img');
        var loading = overlay.querySelector('.lightbox-loading');
        loading.style.display = 'block';
        img.style.opacity = '0';
        img.onload = function () {
            loading.style.display = 'none';
            img.style.opacity = '1';
        };
        img.src = imgs[current].src;
        overlay.style.display = 'flex';
        // 多图才显示左右箭头
        var multi = imgs.length > 1;
        overlay.querySelector('.lightbox-prev').style.display = multi ? '' : 'none';
        overlay.querySelector('.lightbox-next').style.display = multi ? '' : 'none';
    }

    function go(dir) { show(current + dir); }

    function onKey(e) {
        if (!overlay || overlay.style.display !== 'flex') return;
        if (e.key === 'Escape') close();
        else if (e.key === 'ArrowLeft') go(-1);
        else if (e.key === 'ArrowRight') go(1);
    }

    function close() {
        if (overlay) overlay.style.display = 'none';
    }

    // 绑定正文图片点击
    imgs.forEach(function (img, i) {
        img.addEventListener('click', function () { show(i); });
    });
})();

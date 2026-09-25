/* ============================================================
 * article_card_fallback.js —— 封面图加载失败兜底（第三轮迁移）
 * 原为 _article_card.html 内联 onerror 属性，现外移为全局委托：
 *  - 图片加载失败（error 事件不冒泡，需捕获阶段监听）；
 *  - 移除失效的 .article-card-thumb 容器；
 *  - 给 .article-card 加 .no-cover 类（无封面布局降级）。
 * 依赖：无。base.html 全局加载。
 * ============================================================ */
(function () {
    'use strict';
    document.addEventListener('error', function (e) {
        var t = e.target;
        if (!t || t.tagName !== 'IMG') return;
        var thumb = t.closest('.article-card-thumb');
        if (!thumb) return;
        var card = thumb.closest('.article-card');
        if (card) card.classList.add('no-cover');
        thumb.remove();
    }, true);
})();

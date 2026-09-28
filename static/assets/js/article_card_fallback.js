/* ============================================================================
 * article_card_fallback.js —— 文章卡片封面图加载失败的全局兜底
 * ----------------------------------------------------------------------------
 * 来源（第三轮迁移）：原为 _article_card.html 内联的 onerror 属性，
 * 现外移为全局事件委托，便于统一维护并避免内联 JS / CSP 问题。
 *
 * 触发场景：
 *   文章卡片封面图 URL 失效、文件缺失或网络错误，<img> 触发 error 事件。
 *
 * 关键技术点（务必注意）：
 *   · 图片 / 脚本等资源的 error 事件**不冒泡**，普通 addEventListener('error')
 *     在 document 上根本收不到；必须把第三个参数设为 **true（捕获阶段）**，
 *     在事件从 window 向下捕获的途中拦截；
 *   · 处理动作分两步：
 *       1) 移除 .article-card-thumb 缩略图容器（避免留下裂图图标）；
 *       2) 给 .article-card 加 .no-cover 类，卡片降级为「纯文字」布局
 *          （标题 / 摘要占满，CSS 据此重排）。
 *
 * 依赖：无第三方库；base.html 全局加载，对所有列表页生效。
 * ============================================================================ */
(function () {
    'use strict';

    // 在捕获阶段监听全局 error 事件（资源错误不冒泡，只能捕获）
    document.addEventListener('error', function (event) {
        var target = event.target;

        // 只处理图片元素的错误，其它资源（脚本等）忽略
        if (!target || target.tagName !== 'IMG') return;

        // 向上找到卡片缩略图容器；不在封面容器内的图片错误不处理
        var thumb = target.closest('.article-card-thumb');
        if (!thumb) return;

        // 找到所属文章卡片，加无封面类，触发纯文字降级布局
        var card = thumb.closest('.article-card');
        if (card) card.classList.add('no-cover');

        // 移除缩略图容器，消除裂图 / 占位空白
        thumb.remove();
    }, true);   // true = 捕获阶段，这是本脚本生效的前提
})();

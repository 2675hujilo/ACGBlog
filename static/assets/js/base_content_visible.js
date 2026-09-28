/* ============================================================================
 * base_content_visible.js —— 入场动画异常时的「内容可见」兜底
 * ----------------------------------------------------------------------------
 * 背景：
 *   全站大量区块使用滚动入场动画（.scroll-fade-in / .animate-in / .fade-scroll），
 *   正常情况下由滚动监听 / IntersectionObserver 在元素进入视口时加 .visible
 *   类使其淡入。但若相关观察脚本加载失败、或用户关闭 JS 动画时序异常，元素
 *   可能一直停在透明初始态，导致页面「空白」。
 *
 * 本脚本的兜底策略：
 *   · DOMContentLoaded 时（或脚本已在 DOM 就绪后执行时立即）给所有入场元素
 *     强制加 .visible，并给 body 加 .page-enter-done，确保内容立即可见；
 *   · 再设 500ms 二次保险，覆盖晚插入的内容。
 *
 * 取舍：宁可放弃部分入场动画，也绝不让正文内容不可见（可读性优先）。
 * ============================================================================ */
(function () {
    'use strict';

    // 强制让所有带入场类的元素变为可见
    function showAll() {
        var nodes = document.querySelectorAll(
            '.scroll-fade-in, .animate-in, .fade-scroll'
        );
        nodes.forEach(function (el) {
            el.classList.add('visible');
        });
        // body 标记入场完成，部分 CSS 据此解除初始隐藏
        document.body.classList.add('page-enter-done');
    }

    // DOM 还在加载则等 DOMContentLoaded；否则立即执行
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', showAll);
    } else {
        showAll();
    }

    // 500ms 二次兜底，覆盖延迟插入的节点
    setTimeout(showAll, 500);
})();

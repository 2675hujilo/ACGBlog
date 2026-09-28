/**
 * toc.js —— 详情页右侧自动目录（Table of Contents）生成与滚动高亮（增强版）
 * 功能：
 *   1. 扫描 .article-body 内的 h1~h5 标题，自动为缺少 id 的标题生成锚点；
 *   2. 依据标题层级（h1~h5）生成带缩进的目录树，写入右侧 #toc-list；
 *   3. 点击目录项平滑滚动到对应标题（预留导航栏高度偏移），并同步地址栏 hash；
 *   4. 滚动页面时实时高亮当前阅读章节（添加 .toc-active 类）；
 *   5. TOC 标题可折叠：点击 #toc-toggle 展开 / 收起目录列表（.collapsed 类）；
 *   6. 正文没有任何标题时，给侧栏加 .hidden 类隐藏目录卡片。
 * 依赖：无（纯原生 JS，无外部库）
 * 配套样式：blog.css 中 .toc-sidebar / .toc-list / .toc-item / .toc-level-* / .toc-toggle
 */
(function () {
    'use strict';

    // 正文容器 / 目录卡片 / 目录列表 / 折叠开关；任一缺失说明当前页不是文章详情页，直接退出
    var body = document.querySelector('.article-body');
    var sidebar = document.getElementById('toc-sidebar');
    var list = document.getElementById('toc-list');
    var toggle = document.getElementById('toc-toggle');
    if (!body || !sidebar || !list) return;

    // 收集正文内所有一级到五级标题（h1~h5）
    var headings = body.querySelectorAll('h1, h2, h3, h4, h5');
    // 无标题文章：隐藏目录卡片，正文自然占满宽度
    if (!headings.length) {
        sidebar.classList.add('hidden');
        return;
    }

    /**
     * 目录生成算法：遍历标题列表
     *  - 若标题没有 id，则按序号 sec-1 / sec-2 ... 自动分配，作为锚点目标；
     *  - 解析标签名得到层级数字（h1 -> 1, h2 -> 2 ... h5 -> 5），用于 CSS 缩进类名；
     *  - 创建 <li class="toc-item toc-level-N"><a href="#id">标题文字</a></li>；
     *  - 绑定点击事件：阻止默认锚点跳转，改用平滑滚动并减去导航栏高度偏移。
     */
    headings.forEach(function (h, i) {
        // 自动补全标题锚点 id
        if (!h.id) h.id = 'sec-' + (i + 1);
        // 从标签名解析层级（取 "H2" 的第二位并转数字）
        var level = parseInt(h.tagName.substring(1), 10);
        // 构建目录项 DOM
        var li = document.createElement('li');
        li.className = 'toc-item toc-level-' + level;
        var a = document.createElement('a');
        a.href = '#' + h.id;
        a.textContent = h.textContent.trim();
        // 点击目录项：平滑滚动到对应标题（顶部预留 72px 避开 sticky 导航栏）
        a.addEventListener('click', function (e) {
            e.preventDefault();
            // 当前标题相对视口的位置 + 已滚动距离 - 导航栏偏移 = 目标滚动值
            window.scrollTo({ top: h.getBoundingClientRect().top + window.pageYOffset - 72, behavior: 'smooth' });
            // 同步地址栏 hash，便于刷新/分享时定位
            history.replaceState(null, '', '#' + h.id);
        });
        li.appendChild(a);
        list.appendChild(li);
    });

    // 缓存所有目录链接，供滚动高亮使用
    var links = list.querySelectorAll('a');

    /**
     * 折叠功能：点击目录标题切换 .collapsed 类，控制列表显隐与箭头方向
     */
    if (toggle) {
        toggle.addEventListener('click', function () {
            sidebar.classList.toggle('collapsed');
        });
    }

    /**
     * 滚动高亮逻辑
     * 思路：取当前视口上方 90px 处（≈ 导航栏底边）作为判定线，
     *       向下遍历所有标题，凡是 offsetTop <= 该位置的都视为"已经过"，
     *       最后一个命中的即为当前阅读章节，给它的目录链接加 .toc-active。
     */
    function highlight() {
        var pos = window.pageYOffset + 90;  // 判定线位置（相对文档顶部）
        var currentId = '';
        // 找到最后一个位于判定线之上的标题
        headings.forEach(function (h) {
            if (h.offsetTop <= pos) currentId = h.id;
        });
        // 依据命中结果切换高亮类
        links.forEach(function (a) {
            var li = a.parentElement;
            li.classList.toggle('toc-active', a.getAttribute('href') === '#' + currentId);
        });
    }
    // passive: true 优化滚动性能；首次立即执行一次定位当前章节
    window.addEventListener('scroll', highlight, { passive: true });
    highlight();
})();

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
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';

    // 正文容器 / 目录卡片 / 目录列表 / 折叠开关；任一缺失说明当前页不是文章详情页，直接退出
    //> 声明变量「body」（body），用于保存对应数据，保存 DOM/窗口相关对象
    var body = document.querySelector('.article-body');
    //> 声明变量「sidebar」（sidebar），用于保存对应数据，保存 DOM/窗口相关对象
    var sidebar = document.getElementById('toc-sidebar');
    //> 声明变量「list」（list），用于保存对应数据，保存 DOM/窗口相关对象
    var list = document.getElementById('toc-list');
    //> 声明变量「toggle」（toggle），用于保存对应数据，保存 DOM/窗口相关对象
    var toggle = document.getElementById('toc-toggle');
    //> 条件判断：满足括号内条件时执行对应分支
    if (!body || !sidebar || !list) return;

    // 收集正文内所有一级到五级标题（h1~h5）
    //> 声明变量「headings」（headings），用于保存对应数据
    var headings = body.querySelectorAll('h1, h2, h3, h4, h5');
    // 无标题文章：隐藏目录卡片，正文自然占满宽度
    //> 条件判断：满足括号内条件时执行对应分支
    if (!headings.length) {
        //> 为元素添加一个或多个样式类
        sidebar.classList.add('hidden');
        //> 提前结束函数，无返回值
        return;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /**
     * 目录生成算法：遍历标题列表
     *  - 若标题没有 id，则按序号 sec-1 / sec-2 ... 自动分配，作为锚点目标；
     *  - 解析标签名得到层级数字（h1 -> 1, h2 -> 2 ... h5 -> 5），用于 CSS 缩进类名；
     *  - 创建 <li class="toc-item toc-level-N"><a href="#id">标题文字</a></li>；
     *  - 绑定点击事件：阻止默认锚点跳转，改用平滑滚动并减去导航栏高度偏移。
     */
    //> 遍历数组/类数组中的每一项并执行回调
    headings.forEach(function (h, i) {
        // 自动补全标题锚点 id
        //> 条件判断：满足括号内条件时执行对应分支
        if (!h.id) h.id = 'sec-' + (i + 1);
        // 从标签名解析层级（取 "H2" 的第二位并转数字）
        //> 声明变量「level」（level），用于保存对应数据
        var level = parseInt(h.tagName.substring(1), 10);
        // 构建目录项 DOM
        //> 声明变量「li」（li），用于保存对应数据，保存 DOM/窗口相关对象
        var li = document.createElement('li');
        //> 给「li.className」赋值，更新其保存的状态
        li.className = 'toc-item toc-level-' + level;
        //> 声明变量「a」（a），用于保存对应数据，保存 DOM/窗口相关对象
        var a = document.createElement('a');
        //> 给「a.href」赋值，更新其保存的状态
        a.href = '#' + h.id;
        //> 读写纯文本内容，不解析 HTML，可防 XSS
        a.textContent = h.textContent.trim();
        // 点击目录项：平滑滚动到对应标题（顶部预留 72px 避开 sticky 导航栏）
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        a.addEventListener('click', function (e) {
            //> 阻止事件的默认行为（如表单提交、链接跳转）
            e.preventDefault();
            // 当前标题相对视口的位置 + 已滚动距离 - 导航栏偏移 = 目标滚动值
            //> 程序化滚动窗口到指定位置
            window.scrollTo({ top: h.getBoundingClientRect().top + window.pageYOffset - 72, behavior: 'smooth' });
            // 同步地址栏 hash，便于刷新/分享时定位
            //> 操作浏览器历史记录，实现无刷新导航
            history.replaceState(null, '', '#' + h.id);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        //> 把子节点追加到当前元素内部末尾
        li.appendChild(a);
        //> 把子节点追加到当前元素内部末尾
        list.appendChild(li);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    // 缓存所有目录链接，供滚动高亮使用
    //> 声明变量「links」（links），用于保存对应数据
    var links = list.querySelectorAll('a');

    /**
     * 折叠功能：点击目录标题切换 .collapsed 类，控制列表显隐与箭头方向
     */
    //> 条件判断：满足括号内条件时执行对应分支
    if (toggle) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        toggle.addEventListener('click', function () {
            //> 切换样式类（有则移除、无则添加），可传第二参强制状态
            sidebar.classList.toggle('collapsed');
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /**
     * 滚动高亮逻辑
     * 思路：取当前视口上方 90px 处（≈ 导航栏底边）作为判定线，
     *       向下遍历所有标题，凡是 offsetTop <= 该位置的都视为"已经过"，
     *       最后一个命中的即为当前阅读章节，给它的目录链接加 .toc-active。
     */
    // =========================================================
    // 【函数】highlight
    // 功能：高亮相关逻辑（highlight）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function highlight() {
        //> 声明变量「pos」（pos），用于保存对应数据，保存 DOM/窗口相关对象
        var pos = window.pageYOffset + 90;  // 判定线位置（相对文档顶部）
        //> 声明变量「currentId」（current id），用于保存对应数据，初始为字符串
        var currentId = '';
        // 找到最后一个位于判定线之上的标题
        //> 遍历数组/类数组中的每一项并执行回调
        headings.forEach(function (h) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (h.offsetTop <= pos) currentId = h.id;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        // 依据命中结果切换高亮类
        //> 遍历数组/类数组中的每一项并执行回调
        links.forEach(function (a) {
            //> 声明变量「li」（li），用于保存对应数据
            var li = a.parentElement;
            //> 切换样式类（有则移除、无则添加），可传第二参强制状态
            li.classList.toggle('toc-active', a.getAttribute('href') === '#' + currentId);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // passive: true 优化滚动性能；首次立即执行一次定位当前章节
    //> 绑定「scroll」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    window.addEventListener('scroll', highlight, { passive: true });
    //> 调用函数「highlight」并传入参数执行对应逻辑
    highlight();
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

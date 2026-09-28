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
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';

    //> 声明变量「body」（body），用于保存对应数据，保存 DOM/窗口相关对象
    var body = document.querySelector('.article-body');
    //> 条件判断：满足括号内条件时执行对应分支
    if (!body) return;
    //> 声明变量「imgs」（imgs），用于保存对应数据
    var imgs = Array.prototype.slice.call(body.querySelectorAll('img'));
    //> 条件判断：满足括号内条件时执行对应分支
    if (!imgs.length) return;

    //> 声明变量「overlay」（overlay），用于保存对应数据
    var overlay = null, current = 0;

    // =========================================================
    // 【函数】build
    // 功能：构建相关逻辑（build）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function build() {
        //> 创建新的 DOM 元素节点，后续需挂载到文档才显示
        overlay = document.createElement('div');
        //> 给「overlay.className」赋值，更新其保存的状态
        overlay.className = 'lightbox-overlay';
        //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
        overlay.innerHTML =
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '<div class="lightbox-loading"></div>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '<img class="lightbox-img" alt="">' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '<button class="lightbox-btn lightbox-close" type="button" aria-label="\u5173\u95ed">\u00d7</button>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '<button class="lightbox-btn lightbox-prev" type="button" aria-label="\u4e0a\u4e00\u5f20">\u2039</button>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '<button class="lightbox-btn lightbox-next" type="button" aria-label="\u4e0b\u4e00\u5f20">\u203a</button>';
        //> 把子节点追加到当前元素内部末尾
        document.body.appendChild(overlay);

        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        overlay.querySelector('.lightbox-close').addEventListener('click', close);
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        overlay.querySelector('.lightbox-prev').addEventListener('click', function (e) { e.stopPropagation(); go(-1); });
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        overlay.querySelector('.lightbox-next').addEventListener('click', function (e) { e.stopPropagation(); go(1); });
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        overlay.addEventListener('click', function (e) { if (e.target === overlay) close(); });
        //> 绑定「keydown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('keydown', onKey);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // =========================================================
    // 【函数】show
    // 功能：显示相关逻辑（show）
    // 参数：
    //   - i：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function show(i) {
        //> 条件判断：满足括号内条件时执行对应分支
        if (!overlay) build();
        //> 给「current」赋值，更新其保存的状态
        current = (i + imgs.length) % imgs.length;
        //> 声明变量「img」（img），用于保存对应数据
        var img = overlay.querySelector('.lightbox-img');
        //> 声明变量「loading」（loading），用于保存对应数据
        var loading = overlay.querySelector('.lightbox-loading');
        //> 给「loading.style.display」赋值，更新其保存的状态
        loading.style.display = 'block';
        //> 给「img.style.opacity」赋值，更新其保存的状态
        img.style.opacity = '0';
        // =========================================================
        // 【函数】onload
        // 功能：处理「onload」相关逻辑（image_lightbox）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        img.onload = function () {
            //> 给「loading.style.display」赋值，更新其保存的状态
            loading.style.display = 'none';
            //> 给「img.style.opacity」赋值，更新其保存的状态
            img.style.opacity = '1';
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        };
        //> 给「img.src」赋值，更新其保存的状态
        img.src = imgs[current].src;
        //> 给「overlay.style.display」赋值，更新其保存的状态
        overlay.style.display = 'flex';
        // 多图才显示左右箭头
        //> 声明变量「multi」（multi），用于保存对应数据
        var multi = imgs.length > 1;
        //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
        overlay.querySelector('.lightbox-prev').style.display = multi ? '' : 'none';
        //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
        overlay.querySelector('.lightbox-next').style.display = multi ? '' : 'none';
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // =========================================================
    // 【函数】go
    // 功能：处理「go」相关逻辑（image_lightbox）
    // 参数：
    //   - dir：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function go(dir) { show(current + dir); }

    // =========================================================
    // 【函数】onKey
    // 功能：处理……事件「key」相关逻辑（on key）
    // 参数：
    //   - e：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function onKey(e) {
        //> 条件判断：满足括号内条件时执行对应分支
        if (!overlay || overlay.style.display !== 'flex') return;
        //> 条件判断：满足括号内条件时执行对应分支
        if (e.key === 'Escape') close();
        //> 否则若满足该条件则进入此分支
        else if (e.key === 'ArrowLeft') go(-1);
        //> 否则若满足该条件则进入此分支
        else if (e.key === 'ArrowRight') go(1);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // =========================================================
    // 【函数】close
    // 功能：关闭相关逻辑（close）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function close() {
        //> 条件判断：满足括号内条件时执行对应分支
        if (overlay) overlay.style.display = 'none';
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // 绑定正文图片点击
    //> 遍历数组/类数组中的每一项并执行回调
    imgs.forEach(function (img, i) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        img.addEventListener('click', function () { show(i); });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

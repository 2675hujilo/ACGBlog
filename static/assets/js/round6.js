/* ============================================================
 * round6.js · 萌语博客「第六轮」Bug 修复与体验增强脚本
 * ------------------------------------------------------------
 * 功能：
 *  1. 左下角 FAB 快捷操作菜单（bug2）：展开/收起、点击动作、
 *     外部点击 / Esc 自动关闭；
 *  2. 标签云防拖拽（bug22）：标签只响应点击跳转，不被拖起；
 *  3. 热门文章周 / 月 / 总榜切换（配合模板渲染的三组列表）；
 *  4. 侧栏在窄屏下的折叠辅助；
 *  全部逻辑带 UTF-8 中文注释，压缩后由 refresh_assets 生成 .min.js。
 * ============================================================ */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';

    /* ----------------------------------------------------------
     * 1. FAB 快捷菜单（bug2）
     * -------------------------------------------------------- */
    // =========================================================
    // 【函数】initQuickMenu
    // 功能：初始化「quick menu」相关逻辑（init quick menu）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function initQuickMenu() {
        //> 声明变量「fab」（fab），用于保存对应数据，保存 DOM/窗口相关对象
        var fab = document.getElementById('sidebar-toggle');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!fab) return;

        /* 若菜单 DOM 尚未由模板输出，则动态构建一份，保证可用 */
        //> 声明变量「menu」（menu），用于保存对应数据，保存 DOM/窗口相关对象
        var menu = document.getElementById('quick-menu');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!menu) {
            //> 创建新的 DOM 元素节点，后续需挂载到文档才显示
            menu = document.createElement('div');
            //> 给「menu.id」赋值，更新其保存的状态
            menu.id = 'quick-menu';
            //> 给「menu.className」赋值，更新其保存的状态
            menu.className = 'quick-menu';
            //> 给「menu.hidden」赋值，更新其保存的状态
            menu.hidden = true;
            //> 声明变量「items」（items），用于保存对应数据
            var items = [
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                { ico: '🔝', text: '回到顶部', action: 'top' },
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                { ico: '✍', text: '写文章', action: 'write', auth: true },
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                { ico: '🌓', text: '明暗切换', action: 'theme' },
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                { ico: '🔍', text: '聚焦搜索', action: 'search' },
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                { ico: '🎲', text: '随机一篇', action: 'random' },
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                { ico: '🎛', text: '运营看板', action: 'console', staff: true },
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                { ico: '🔄', text: '刷新页面', action: 'reload' }
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            ];
            //> 遍历数组/类数组中的每一项并执行回调
            items.forEach(function (it) {
                //> 声明变量「a」（a），用于保存对应数据，保存 DOM/窗口相关对象
                var a = document.createElement('a');
                //> 给「a.className」赋值，更新其保存的状态
                a.className = 'quick-item' + (it.action === 'reload' ? ' qi-danger' : '');
                //> 设置元素的 HTML 属性
                a.setAttribute('role', 'menuitem');
                //> 读写元素的 data-* 自定义数据属性
                a.dataset.action = it.action;
                //> 条件判断：满足括号内条件时执行对应分支
                if (it.auth) a.dataset.auth = '1';
                //> 条件判断：满足括号内条件时执行对应分支
                if (it.staff) a.dataset.staff = '1';
                //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
                a.innerHTML = '<span class="qi-ico">' + it.ico + '</span><span>' + it.text + '</span>';
                //> 把子节点追加到当前元素内部末尾
                menu.appendChild(a);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            //> 把子节点追加到当前元素内部末尾
            document.body.appendChild(menu);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }

        /* 根据登录 / 员工身份显隐对应菜单项。
           //> 该行执行对应的脚本逻辑（结合上下文理解）
           工单12：原先限定的 .nav-user 容器类已失效，改为直接探测全页可靠信号——
           //> 该行执行对应的脚本逻辑（结合上下文理解）
           登录看“退出表单 / 用户菜单按钮”，员工看“运营看板链接”。 */
        //> 声明变量「loggedIn」（logged in），用于保存对应数据
        var loggedIn = !!document.querySelector('form[action$="logout/"]') ||
                       //> 按 id 获取单个元素，不存在时返回 null
                       !!document.getElementById('user-menu-btn');
        //> 声明变量「isStaff」（is staff），用于保存对应数据
        var isStaff = !!document.querySelector('a[href$="/console/"]');
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        menu.querySelectorAll('[data-auth="1"]').forEach(function (el) {
            //> 给「el.style.display」赋值，更新其保存的状态
            el.style.display = loggedIn ? '' : 'none';
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        menu.querySelectorAll('[data-staff="1"]').forEach(function (el) {
            //> 给「el.style.display」赋值，更新其保存的状态
            el.style.display = isStaff ? '' : 'none';
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });

        /* 展开 / 收起 */
        // =========================================================
        // 【函数】setOpen
        // 功能：设置「open」相关逻辑（set open）
        // 参数：
        //   - open：传入的参数（含义结合调用处与函数体）
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function setOpen(open) {
            //> 给「menu.hidden」赋值，更新其保存的状态
            menu.hidden = !open;
            // 下一帧切换 open class，触发过渡
            // =========================================================
            // 【函数】requestAnimationFrame
            // 功能：处理「request animation frame」相关逻辑（round6）
            // 参数：
            //   - function：传入的参数（含义结合调用处与函数体）
            //   - (：传入的参数（含义结合调用处与函数体）
            // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
            // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
            // =========================================================
            requestAnimationFrame(function () {
                //> 切换样式类（有则移除、无则添加），可传第二参强制状态
                menu.classList.toggle('open', open);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            //> 设置元素的 HTML 属性
            fab.setAttribute('aria-expanded', open ? 'true' : 'false');
            // 工单12：钉住（点击展开）态视觉反馈——高亮环 + aria-pressed
            //> 切换样式类（有则移除、无则添加），可传第二参强制状态
            fab.classList.toggle('is-pinned', open && pinned);
            //> 设置元素的 HTML 属性
            fab.setAttribute('aria-pressed', (open && pinned) ? 'true' : 'false');
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // =========================================================
        // 【函数】isOpen
        // 功能：判断是否为「open」相关逻辑（is open）
        // 参数：无
        // 返回：函数体内有 return，返回对应结果
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function isOpen() { return !menu.hidden; }

        /* bug1：悬停与点击都有交互。
           //> 给「pinned」赋值，更新其保存的状态
           pinned=点击“钉住”，鼠标移出也不收起；再次点击 / 外部点击 / Esc 才关闭。 */
        //> 声明变量「pinned」（pinned），用于保存对应数据
        var pinned = false;
        //> 声明变量「hoverTimer」（hover timer），用于保存对应数据
        var hoverTimer = null;
        // =========================================================
        // 【函数】clearHover
        // 功能：清空「hover」相关逻辑（clear hover）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function clearHover() { if (hoverTimer) { clearTimeout(hoverTimer); hoverTimer = null; } }
        // =========================================================
        // 【函数】openByHover
        // 功能：打开「by hover」相关逻辑（open by hover）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function openByHover() { clearHover(); if (!isOpen()) setOpen(true); }
        // =========================================================
        // 【函数】scheduleClose
        // 功能：处理「schedule close」相关逻辑（round6）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function scheduleClose() {
            //> 调用函数「clearHover」并传入参数执行对应逻辑
            clearHover();
            //> 设置延时执行的定时器，返回可清除的定时器 id
            hoverTimer = setTimeout(function () { if (!pinned) setOpen(false); }, 240);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }

        /* 悬停 FAB 或菜单即展开；移出给予 240ms 缓冲，避免中途抖动 */
        //> 绑定「mouseenter」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        fab.addEventListener('mouseenter', openByHover);
        //> 绑定「mouseleave」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        fab.addEventListener('mouseleave', scheduleClose);
        //> 绑定「mouseenter」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        menu.addEventListener('mouseenter', openByHover);
        //> 绑定「mouseleave」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        menu.addEventListener('mouseleave', scheduleClose);

        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        fab.addEventListener('click', function (e) {
            //> 阻止事件的默认行为（如表单提交、链接跳转）
            e.preventDefault();
            //> 阻止事件继续向上冒泡
            e.stopPropagation();
            //> 调用函数「clearHover」并传入参数执行对应逻辑
            clearHover();
            //> 条件判断：满足括号内条件时执行对应分支
            if (isOpen() && pinned) { pinned = false; setOpen(false); }
            //> 以上条件都不满足时执行的兜底分支
            else { pinned = true; setOpen(true); }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });

        /* 点击具体动作 */
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        menu.addEventListener('click', function (e) {
            //> 声明变量「item」（item），用于保存对应数据
            var item = e.target.closest('.quick-item');
            //> 条件判断：满足括号内条件时执行对应分支
            if (!item) return;
            //> 声明变量「act」（act），用于保存对应数据
            var act = item.dataset.action;
            //> 给「pinned」赋值，更新其保存的状态
            pinned = false;
            //> 调用函数「setOpen」并传入参数执行对应逻辑
            setOpen(false);
            //> 多分支选择：按表达式值匹配对应 case
            switch (act) {
                //> 匹配该值时执行的分支
                case 'top':
                    //> 程序化滚动窗口到指定位置
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                    //> 跳出当前循环或 switch
                    break;
                //> 匹配该值时执行的分支
                case 'write':
                    //> 通过赋值跳转页面
                    window.location.href = '/new/';
                    //> 跳出当前循环或 switch
                    break;
                //> 匹配该值时执行的分支
                case 'theme':
                    //> 声明变量「t」（t），用于保存对应数据，保存 DOM/窗口相关对象
                    var t = document.getElementById('theme-toggle');
                    //> 条件判断：满足括号内条件时执行对应分支
                    if (t) t.click();
                    //> 跳出当前循环或 switch
                    break;
                //> 匹配该值时执行的分支
                case 'search':
                    //> 声明变量「s」（s），用于保存对应数据，保存 DOM/窗口相关对象
                    var s = document.getElementById('nav-search-input');
                    //> 条件判断：满足括号内条件时执行对应分支
                    if (s) { s.focus(); s.select(); }
                    //> 跳出当前循环或 switch
                    break;
                //> 匹配该值时执行的分支
                case 'random':
                    //> 通过赋值跳转页面
                    window.location.href = '/random/';
                    //> 跳出当前循环或 switch
                    break;
                //> 匹配该值时执行的分支
                case 'console':
                    //> 通过赋值跳转页面
                    window.location.href = '/console/';
                    //> 跳出当前循环或 switch
                    break;
                //> 匹配该值时执行的分支
                case 'reload':
                    //> 重新加载当前页面
                    window.location.reload();
                    //> 跳出当前循环或 switch
                    break;
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });

                /* 外部点击关闭 */
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('click', function (e) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (!isOpen()) return;
            //> 条件判断：满足括号内条件时执行对应分支
            if (menu.contains(e.target) || fab.contains(e.target)) return;
            //> 给「pinned」赋值，更新其保存的状态
            pinned = false;
            //> 调用函数「setOpen」并传入参数执行对应逻辑
            setOpen(false);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        /* Esc 关闭 */
        //> 绑定「keydown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('keydown', function (e) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (e.key === 'Escape' && isOpen()) { pinned = false; setOpen(false); }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ----------------------------------------------------------
     * 2. 标签云防拖拽（bug22）
     *    模板已设 draggable=false，这里再加 JS 兜底：阻止 dragstart
     * -------------------------------------------------------- */
    // =========================================================
    // 【函数】initTagNoDrag
    // 功能：初始化「tag no drag」相关逻辑（init tag no drag）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function initTagNoDrag() {
        //> 绑定「dragstart」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('dragstart', function (e) {
            //> 声明变量「t」（t），用于保存对应数据
            var t = e.target.closest ? e.target.closest('.tag-cloud a, #home-tag-cloud a') : null;
            //> 条件判断：满足括号内条件时执行对应分支
            if (t) e.preventDefault();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ----------------------------------------------------------
     * 3. 热门文章周 / 月 / 总榜切换
     *    期望右栏存在 <ol data-range="week|month|total">；
     *    若只有一个列表（后端未渲染三组），则不做处理。
     * -------------------------------------------------------- */
    // =========================================================
    // 【函数】initHotRankTabs
    // 功能：初始化「hot rank tabs」相关逻辑（init hot rank tabs）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function initHotRankTabs() {
        //> 声明变量「tabs」（tabs），用于保存对应数据，保存 DOM/窗口相关对象
        var tabs = document.querySelectorAll('.hot-rank-tab');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!tabs.length) return;
        //> 声明变量「lists」（lists），用于保存对应数据，保存 DOM/窗口相关对象
        var lists = document.querySelectorAll('.hot-list[data-range]');
        //> 遍历数组/类数组中的每一项并执行回调
        tabs.forEach(function (tab) {
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            tab.addEventListener('click', function () {
                //> 声明变量「range」（range），用于保存对应数据
                var range = tab.dataset.range;
                //> 遍历数组/类数组中的每一项并执行回调
                tabs.forEach(function (x) {
                    //> 切换样式类（有则移除、无则添加），可传第二参强制状态
                    x.classList.toggle('active', x === tab);
                    //> 设置元素的 HTML 属性
                    x.setAttribute('aria-selected', x === tab ? 'true' : 'false');
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                });
                //> 条件判断：满足括号内条件时执行对应分支
                if (lists.length) {
                    //> 遍历数组/类数组中的每一项并执行回调
                    lists.forEach(function (ol) {
                        //> 读写元素的 data-* 自定义数据属性
                        ol.style.display = ol.dataset.range === range ? '' : 'none';
                    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                    });
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ----------------------------------------------------------
     * 4. 正文图片加载失败兜底（bug9）
     *    error 不冒泡，需在捕获阶段监听；把裂图替换为萌系占位卡
     * -------------------------------------------------------- */
    // =========================================================
    // 【函数】initBrokenImageFallback
    // 功能：初始化「broken image fallback」相关逻辑（init broken image fallback）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function initBrokenImageFallback() {
        //> 绑定「error」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('error', function (e) {
            //> 声明变量「img」（img），用于保存对应数据
            var img = e.target;
            //> 条件判断：满足括号内条件时执行对应分支
            if (!img || img.tagName !== 'IMG') return;
            // 仅处理正文 / 评论内容中的图片（跳过头像、图标等小图）
            //> 声明变量「inBody」（in body），用于保存对应数据
            var inBody = img.closest('#article-body, .comment-content, .comment-body');
            //> 条件判断：满足括号内条件时执行对应分支
            if (!inBody || img.dataset.moeFallback === '1') return;
            //> 读写元素的 data-* 自定义数据属性
            img.dataset.moeFallback = '1';
            //> 声明变量「box」（box），用于保存对应数据，保存 DOM/窗口相关对象
            var box = document.createElement('div');
            //> 给「box.className」赋值，更新其保存的状态
            box.className = 'moe-img-fallback';
            //> 设置元素的 HTML 属性
            box.setAttribute('role', 'img');
            //> 设置元素的 HTML 属性
            box.setAttribute('aria-label', '图片加载失败');
            //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
            box.innerHTML = '<span class="mif-emoji">🖋️</span>' +
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                '<span class="mif-text">图片走丢了喵~</span>' +
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                '<span class="mif-sub">可能链接失效或网络不好</span>';
            //> 给「img.style.display」赋值，更新其保存的状态
            img.style.display = 'none';
            //> 在参考子节点之前插入新子节点
            img.parentNode.insertBefore(box, img.nextSibling);
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }, true);   // true = 捕获阶段
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ----------------------------------------------------------
     * 5. 通用「封面选择器」文件名回显（Bug2：创建系列页等）
     *    任意 .cover-picker 内的隐藏文件框，选中文件后把文件名显示
     *    在萌系标签上并加 has-file 高亮；取消选择则还原占位文案。
     *    写文章页 id_cover_image 已由 edit_inline.js 专门处理，这里跳过。
     * -------------------------------------------------------- */
    // =========================================================
    // 【函数】initCoverPicker
    // 功能：初始化「cover picker」相关逻辑（init cover picker）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function initCoverPicker() {
        //> 绑定「change」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('change', function (e) {
            //> 声明变量「fi」（fi），用于保存对应数据
            var fi = e.target;
            //> 条件判断：满足括号内条件时执行对应分支
            if (!fi || fi.tagName !== 'INPUT' || fi.type !== 'file') return;
            //> 条件判断：满足括号内条件时执行对应分支
            if (fi.id === 'id_cover_image') return;   // 写文章页交给 edit_inline.js
            //> 声明变量「box」（box），用于保存对应数据
            var box = fi.closest('.cover-picker');
            //> 条件判断：满足括号内条件时执行对应分支
            if (!box) return;
            // 标签内的文字节点（.cp-text），没有则退化为整个 label
            //> 声明变量「label」（label），用于保存对应数据
            var label = box.querySelector('.cover-picker-label .cp-text') ||
                        //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
                        box.querySelector('.cp-text');
            //> 条件判断：满足括号内条件时执行对应分支
            if (!label) return;
            // 首次记录默认占位文案，便于还原
            //> 条件判断：满足括号内条件时执行对应分支
            if (!label.dataset.defaultText) label.dataset.defaultText = label.textContent;
            //> 条件判断：满足括号内条件时执行对应分支
            if (fi.files && fi.files.length) {
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                label.textContent = '已选择：' + fi.files[0].name;
                //> 为元素添加一个或多个样式类
                box.classList.add('has-file');
            //> 以上条件都不满足时执行的兜底分支
            } else {
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                label.textContent = label.dataset.defaultText;
                //> 移除元素的一个或多个样式类
                box.classList.remove('has-file');
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ----------------------------------------------------------
     * 6. 楼中楼回复「折叠 / 展开」（Bug3）
     *    点击 .comment-replies-toggle：切换线程 replies-open 类，
     *    被折叠的 .comment-reply-row.is-extra 随之显隐；按钮文案在
     *    「展开其余 N 条回复」与「收起回复」之间切换。
     * -------------------------------------------------------- */
    // =========================================================
    // 【函数】initReplyCollapse
    // 功能：初始化「reply collapse」相关逻辑（init reply collapse）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function initReplyCollapse() {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('click', function (e) {
            //> 声明变量「btn」（btn），用于保存对应数据
            var btn = e.target.closest('.comment-replies-toggle');
            //> 条件判断：满足括号内条件时执行对应分支
            if (!btn) return;
            //> 声明变量「thread」（thread），用于保存对应数据
            var thread = btn.closest('.comment-thread');
            //> 条件判断：满足括号内条件时执行对应分支
            if (!thread) return;
            // 记录展开前的原始文案（含 N），收起时还原
            //> 条件判断：满足括号内条件时执行对应分支
            if (!btn.dataset.openText) btn.dataset.openText = btn.textContent;
            //> 声明变量「collapsed」（collapsed），用于保存对应数据
            var collapsed = btn.dataset.collapsed === 'true';
            //> 条件判断：满足括号内条件时执行对应分支
            if (collapsed) {
                //> 为元素添加一个或多个样式类
                thread.classList.add('replies-open');
                //> 读写元素的 data-* 自定义数据属性
                btn.dataset.collapsed = 'false';
                //> 设置元素的 HTML 属性
                btn.setAttribute('aria-expanded', 'true');
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                btn.textContent = '🫧 收起回复';
            //> 以上条件都不满足时执行的兜底分支
            } else {
                //> 移除元素的一个或多个样式类
                thread.classList.remove('replies-open');
                //> 读写元素的 data-* 自定义数据属性
                btn.dataset.collapsed = 'true';
                //> 设置元素的 HTML 属性
                btn.setAttribute('aria-expanded', 'false');
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                btn.textContent = btn.dataset.openText;
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ----------------------------------------------------------
     * 7. 置顶 / 精华 / 热门（Bug1）
     *    - 管理员点 .promo-toggle：直接切换（带 promo-on 表示当前已设置）；
     *    - 作者点 .promo-apply-btn：打开理由弹窗，提交后生成推广申请。
     * -------------------------------------------------------- */
    /* 读取 csrftoken cookie，供 POST 防 CSRF 校验 */
    // =========================================================
    // 【函数】getCsrfToken
    // 功能：获取「csrf token」相关逻辑（get csrf token）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function getCsrfToken() {
        //> 声明变量「m」（m），用于保存对应数据，保存 DOM/窗口相关对象
        var m = document.cookie.match(/csrftoken=([^;]+)/);
        //> 返回结果并结束当前函数
        return m ? m[1] : '';
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    /* 以表单编码 POST 到指定 URL，返回解析后的 JSON；失败给出轻提示 */
    // =========================================================
    // 【函数】postForm
    // 功能：处理「post form」相关逻辑（round6）
    // 参数：
    //   - url：传入的参数（含义结合调用处与函数体）
    //   - data：传入的参数（含义结合调用处与函数体）
    //   - cb：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function postForm(url, data, cb) {
        //> 声明变量「body」（body），用于保存对应数据
        var body = new URLSearchParams();
        //> 遍历数组/类数组中的每一项并执行回调
        Object.keys(data).forEach(function (k) { body.append(k, data[k]); });
        //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
        fetch(url, {
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            method: 'POST',
            //> 使用 XHR 发起传统异步请求
            headers: { 'X-CSRFToken': getCsrfToken(), 'X-Requested-With': 'XMLHttpRequest' },
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            body: body,
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            credentials: 'same-origin'
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }).then(function (r) { return r.json(); }).then(function (j) {
            //> 调用函数「cb」并传入参数执行对应逻辑
            cb(j);
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }).catch(function () {
            //> 条件判断：满足括号内条件时执行对应分支
            if (window.moeToast) moeToast('网络开小差了，稍后再试喵~', 'error');
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // =========================================================
    // 【函数】initPromotion
    // 功能：初始化「promotion」相关逻辑（init promotion）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function initPromotion() {
        /* ---- 管理员直接切换置顶/精华/热门 ---- */
        //> 声明变量「manage」（manage），用于保存对应数据，保存 DOM/窗口相关对象
        var manage = document.querySelector('.promo-manage');
        //> 条件判断：满足括号内条件时执行对应分支
        if (manage) {
            //> 声明变量「toggleUrl」（toggle url），用于保存对应数据
            var toggleUrl = manage.dataset.toggleUrl;
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            manage.addEventListener('click', function (e) {
                //> 声明变量「btn」（btn），用于保存对应数据
                var btn = e.target.closest('.promo-toggle');
                //> 条件判断：满足括号内条件时执行对应分支
                if (!btn) return;
                //> 声明变量「isOn」（is on），用于保存对应数据
                var isOn = btn.classList.contains('promo-on');
                // 当前已设置则执行「取消」动作，否则执行「设置」动作
                //> 声明变量「action」（action），用于保存对应数据
                var action = isOn ? btn.dataset.actionOff : btn.dataset.actionOn;
                //> 调用函数「postForm」并传入参数执行对应逻辑
                postForm(toggleUrl, { action: action }, function (j) {
                    //> 条件判断：满足括号内条件时执行对应分支
                    if (j.code === 0) {
                        //> 切换样式类（有则移除、无则添加），可传第二参强制状态
                        btn.classList.toggle('promo-on', !isOn);
                        //> 条件判断：满足括号内条件时执行对应分支
                        if (window.moeToast) moeToast(j.msg || '操作成功~', 'success');
                    //> 否则若满足该条件则进入此分支
                    } else if (window.moeToast) {
                        //> 调用函数「moeToast」并传入参数执行对应逻辑
                        moeToast(j.msg || '操作失败~', 'error');
                    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                    }
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                });
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }

        /* ---- 作者申请：理由弹窗 ---- */
        //> 声明变量「apply」（apply），用于保存对应数据，保存 DOM/窗口相关对象
        var apply = document.querySelector('.promo-apply');
        //> 声明变量「modal」（modal），用于保存对应数据，保存 DOM/窗口相关对象
        var modal = document.getElementById('promo-modal');
        //> 条件判断：满足括号内条件时执行对应分支
        if (apply && modal) {
            //> 声明变量「requestUrl」（request url），用于保存对应数据
            var requestUrl = apply.dataset.requestUrl;
            //> 声明变量「statusUrl」（status url），用于保存对应数据
            var statusUrl = apply.dataset.statusUrl;
            //> 声明变量「kindInput」（kind input），用于保存对应数据，保存 DOM/窗口相关对象
            var kindInput = document.getElementById('promo-modal-kind');
            //> 声明变量「reasonInput」（reason input），用于保存对应数据，保存 DOM/窗口相关对象
            var reasonInput = document.getElementById('promo-modal-reason');
            //> 声明变量「submitBtn」（submit btn），用于保存对应数据，保存 DOM/窗口相关对象
            var submitBtn = document.getElementById('promo-modal-submit');
            //> 声明变量「currentKind」（current kind），用于保存对应数据，初始为字符串
            var currentKind = '';
            //> 声明变量「currentBtn」（current btn），用于保存对应数据
            var currentBtn = null;

            /* Bug8：把 data-state / 文案 / 禁用态同步到按钮上（服务端与前端共用一套状态） */
            // =========================================================
            // 【函数】paintButton
            // 功能：处理「paint button」相关逻辑（round6）
            // 参数：
            //   - btn：传入的参数（含义结合调用处与函数体）
            //   - state：传入的参数（含义结合调用处与函数体）
            //   - kindLabel：传入的参数（含义结合调用处与函数体）
            // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
            // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
            // =========================================================
            function paintButton(btn, state, kindLabel) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (!btn) return;
                //> 读写元素的 data-* 自定义数据属性
                btn.dataset.state = state;
                //> 移除元素的一个或多个样式类
                btn.classList.remove('promo-state-open', 'promo-state-applied', 'promo-state-pending');
                //> 为元素添加一个或多个样式类
                btn.classList.add('promo-state-' + state);
                //> 条件判断：满足括号内条件时执行对应分支
                if (state === 'applied') {
                    //> 读写纯文本内容，不解析 HTML，可防 XSS
                    btn.textContent = '已经' + kindLabel;
                    //> 给「btn.disabled」赋值，更新其保存的状态
                    btn.disabled = true;
                    //> 设置元素的 HTML 属性
                    btn.setAttribute('aria-disabled', 'true');
                    //> 给「btn.title」赋值，更新其保存的状态
                    btn.title = '这篇文章已经' + kindLabel + '啦，无需再次申请';
                //> 否则若满足该条件则进入此分支
                } else if (state === 'pending') {
                    //> 读写纯文本内容，不解析 HTML，可防 XSS
                    btn.textContent = '⏳ ' + kindLabel + '审核中';
                    //> 给「btn.disabled」赋值，更新其保存的状态
                    btn.disabled = true;
                    //> 设置元素的 HTML 属性
                    btn.setAttribute('aria-disabled', 'true');
                    //> 给「btn.title」赋值，更新其保存的状态
                    btn.title = kindLabel + '申请正在审核中，请耐心等待';
                //> 以上条件都不满足时执行的兜底分支
                } else {
                    //> 读写纯文本内容，不解析 HTML，可防 XSS
                    btn.textContent = '申请' + kindLabel;
                    //> 给「btn.disabled」赋值，更新其保存的状态
                    btn.disabled = false;
                    //> 操作「btn」的相关方法/属性
                    btn.removeAttribute('aria-disabled');
                    //> 给「btn.title」赋值，更新其保存的状态
                    btn.title = '点这里申请把文章' + (kindLabel === '精华' ? '加精' : kindLabel === '热门' ? '加入热门' : kindLabel) ;
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }

            /* Bug8：提交后按服务端真实状态回填三个按钮（防止前端状态与服务端漂移） */
            // =========================================================
            // 【函数】refreshStates
            // 功能：刷新「states」相关逻辑（refresh states）
            // 参数：
            //   - cb：传入的参数（含义结合调用处与函数体）
            // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
            // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
            // =========================================================
            function refreshStates(cb) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (!statusUrl || !window.fetch) { if (cb) cb(); return; }
                //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
                fetch(statusUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' },
                                   //> 该行执行对应的脚本逻辑（结合上下文理解）
                                   credentials: 'same-origin' })
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    .then(function (r) { return r.json(); })
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    .then(function (j) {
                        //> 声明变量「st」（st），用于保存对应数据，值为一个函数
                        var st = (j && j.data && j.data.states) || null;
                        //> 条件判断：满足括号内条件时执行对应分支
                        if (!st) { if (cb) cb(); return; }
                        //> 遍历数组/类数组中的每一项并执行回调
                        Object.keys(st).forEach(function (kind) {
                            //> 声明变量「btn」（btn），用于保存对应数据
                            var btn = apply.querySelector('.promo-apply-btn[data-kind="' + kind + '"]');
                            //> 调用函数「paintButton」并传入参数执行对应逻辑
                            paintButton(btn, st[kind].state, st[kind].label);
                        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                        });
                        //> 条件判断：满足括号内条件时执行对应分支
                        if (cb) cb();
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    }).catch(function () { if (cb) cb(); });
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }

            // =========================================================
            // 【函数】openModal
            // 功能：打开「modal」相关逻辑（open modal）
            // 参数：
            //   - kind：传入的参数（含义结合调用处与函数体）
            //   - label：传入的参数（含义结合调用处与函数体）
            // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
            // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
            // =========================================================
            function openModal(kind, label) {
                //> 给「currentKind」赋值，更新其保存的状态
                currentKind = kind;
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                kindInput.textContent = label;
                //> 给「reasonInput.value」赋值，更新其保存的状态
                reasonInput.value = '';
                //> 给「modal.hidden」赋值，更新其保存的状态
                modal.hidden = false;
                //> 为元素添加一个或多个样式类
                document.body.classList.add('modal-open');
                //> 设置延时执行的定时器，返回可清除的定时器 id
                setTimeout(function () { reasonInput.focus(); }, 50);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            // =========================================================
            // 【函数】closeModal
            // 功能：关闭「modal」相关逻辑（close modal）
            // 参数：无
            // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
            // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
            // =========================================================
            function closeModal() {
                //> 给「modal.hidden」赋值，更新其保存的状态
                modal.hidden = true;
                //> 移除元素的一个或多个样式类
                document.body.classList.remove('modal-open');
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            apply.addEventListener('click', function (e) {
                //> 声明变量「btn」（btn），用于保存对应数据
                var btn = e.target.closest('.promo-apply-btn');
                //> 条件判断：满足括号内条件时执行对应分支
                if (!btn) return;
                // Bug8：已生效 / 审核中的按钮不可再点（disabled 已拦截，这里再兜底一次）
                //> 条件判断：满足括号内条件时执行对应分支
                if (btn.disabled || btn.dataset.state === 'applied' || btn.dataset.state === 'pending') {
                    //> 条件判断：满足括号内条件时执行对应分支
                    if (window.moeToast) {
                        //> 读写元素的 data-* 自定义数据属性
                        moeToast(btn.dataset.state === 'applied'
                            //> 读写元素的 data-* 自定义数据属性
                            ? '这篇文章已经' + btn.dataset.label + '啦，不用再申请喵~'
                            //> 读写元素的 data-* 自定义数据属性
                            : btn.dataset.label + '申请正在审核中，请耐心等待喵~', 'info');
                    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                    }
                    //> 提前结束函数，无返回值
                    return;
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
                //> 给「currentBtn」赋值，更新其保存的状态
                currentBtn = btn;
                //> 读写元素的 data-* 自定义数据属性
                openModal(btn.dataset.kind, btn.dataset.label);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            // 点遮罩 / 取消按钮关闭
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            modal.addEventListener('click', function (e) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (e.target.closest('[data-promo-close]')) closeModal();
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            // Esc 关闭
            //> 绑定「keydown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            document.addEventListener('keydown', function (e) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (e.key === 'Escape' && !modal.hidden) closeModal();
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            submitBtn.addEventListener('click', function () {
                //> 声明变量「reason」（reason），用于保存对应数据
                var reason = reasonInput.value.trim();
                //> 条件判断：满足括号内条件时执行对应分支
                if (!reason) {
                    //> 条件判断：满足括号内条件时执行对应分支
                    if (window.moeToast) moeToast('请先填写申请理由喵~', 'info');
                    //> 操作「reasonInput」的相关方法/属性
                    reasonInput.focus();
                    //> 提前结束函数，无返回值
                    return;
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
                //> 调用函数「postForm」并传入参数执行对应逻辑
                postForm(requestUrl, { kind: currentKind, reason: reason }, function (j) {
                    //> 条件判断：满足括号内条件时执行对应分支
                    if (j.code === 0) {
                        //> 调用函数「closeModal」并传入参数执行对应逻辑
                        closeModal();
                        // Bug8：申请成功后立刻把按钮改为「审核中」并禁用，避免重复提交
                        //> 调用函数「paintButton」并传入参数执行对应逻辑
                        paintButton(currentBtn, 'pending',
                            //> 读写元素的 data-* 自定义数据属性
                            (currentBtn && currentBtn.dataset.label) || '');
                        //> 条件判断：满足括号内条件时执行对应分支
                        if (window.moeToast) moeToast(j.msg || '申请已提交~', j.notice ? 'info' : 'success');
                        //> 调用函数「refreshStates」并传入参数执行对应逻辑
                        refreshStates();
                    //> 以上条件都不满足时执行的兜底分支
                    } else {
                        // 409（已生效 / 已在审核中）时同步服务端真实状态
                        //> 条件判断：满足括号内条件时执行对应分支
                        if (j.code === 409) refreshStates();
                        //> 条件判断：满足括号内条件时执行对应分支
                        if (window.moeToast) moeToast(j.msg || '提交失败~', 'error');
                    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                    }
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                });
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            // 首次进页面自检一次，确保按钮状态与服务端一致
            //> 调用函数「refreshStates」并传入参数执行对应逻辑
            refreshStates();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ----------------------------------------------------------
     * 初始化
     * -------------------------------------------------------- */
    // =========================================================
    // 【函数】ready
    // 功能：处理「ready」相关逻辑（round6）
    // 参数：
    //   - fn：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function ready(fn) {
        //> 条件判断：满足括号内条件时执行对应分支
        if (document.readyState === 'loading') {
            //> 绑定「DOMContentLoaded」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            document.addEventListener('DOMContentLoaded', fn);
        //> 以上条件都不满足时执行的兜底分支
        } else { fn(); }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    //> 调用函数「ready」并传入参数执行对应逻辑
    ready(function () {
        //> 调用函数「initQuickMenu」并传入参数执行对应逻辑
        initQuickMenu();
        //> 调用函数「initTagNoDrag」并传入参数执行对应逻辑
        initTagNoDrag();
        //> 调用函数「initHotRankTabs」并传入参数执行对应逻辑
        initHotRankTabs();
        //> 调用函数「initBrokenImageFallback」并传入参数执行对应逻辑
        initBrokenImageFallback();
        //> 调用函数「initCoverPicker」并传入参数执行对应逻辑
        initCoverPicker();
        //> 调用函数「initReplyCollapse」并传入参数执行对应逻辑
        initReplyCollapse();
        //> 调用函数「initPromotion」并传入参数执行对应逻辑
        initPromotion();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

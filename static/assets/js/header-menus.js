/* ============================================================
 * header-menus.js —— 顶部「工具箱 / 用户头像」下拉菜单逻辑（工单 16）
 *
 * 与通知铃铛一致：header 合成面存在「首帧冻结」，下拉面板若留在 header 中
 * 可能不绘制，故初始化时把面板移入 <main id="main-content"> 并改为 fixed，
 * 按触发器坐标实时定位；支持点击切换、外部点击 / Esc 关闭、滚动与缩放跟随。
 * 工单16：<main> 的入场动画会残留 identity transform
 * （matrix(1,0,0,1,0,0)，非 none），它仍会成为 fixed 的包含块，使面板整体下移
 * 约一个 header 高度。这里在定位时主动检测最近的「transform/filter/perspective
 * 祖先」（即 fixed 的真实包含块），用「目标视口坐标 − 包含块原点」换算，
 * 无论 header 高度 / 动画状态如何，面板都能稳定落在触发器正下方。
 * ============================================================ */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';

    //> 声明变量「mainEl」（main el），用于保存对应数据，保存 DOM/窗口相关对象
    var mainEl = document.getElementById('main-content') ||
                 //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
                 document.querySelector('.site-main');

    /* 求 fixed 元素真实包含块的视口原点：
       //> 该行执行对应的脚本逻辑（结合上下文理解）
       从父节点向上找第一个带 transform/filter/perspective（非 none）的祖先，
       //> 该行执行对应的脚本逻辑（结合上下文理解）
       它就是 fixed 的包含块；没有则相对视口（原点 0,0）。 */
    // =========================================================
    // 【函数】containingOrigin
    // 功能：处理「containing origin」相关逻辑（header-menus）
    // 参数：
    //   - el：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function containingOrigin(el) {
        //> 声明变量「node」（node），用于保存对应数据
        var node = el.parentElement;
        //> 当条件为真时反复执行循环体
        while (node && node.nodeType === 1) {
            //> 声明变量「cs」（cs），用于保存对应数据
            var cs = getComputedStyle(node);
            //> 条件判断：满足括号内条件时执行对应分支
            if ((cs.transform && cs.transform !== 'none') ||
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                (cs.filter && cs.filter !== 'none') ||
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                (cs.perspective && cs.perspective !== 'none')) {
                //> 声明变量「r」（r），用于保存对应数据
                var r = node.getBoundingClientRect();
                //> 返回结果并结束当前函数
                return [r.left, r.top];
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 给「node」赋值，更新其保存的状态
            node = node.parentElement;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 返回结果并结束当前函数
        return [0, 0];
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* 统一构造一个下拉控制器 */
    // =========================================================
    // 【函数】createMenu
    // 功能：创建「menu」相关逻辑（create menu）
    // 参数：
    //   - btnId：传入的参数（含义结合调用处与函数体）
    //   - panelId：传入的参数（含义结合调用处与函数体）
    //   - align：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function createMenu(btnId, panelId, align) {
        //> 声明变量「btn」（btn），用于保存对应数据，保存 DOM/窗口相关对象
        var btn = document.getElementById(btnId);
        //> 声明变量「panel」（panel），用于保存对应数据，保存 DOM/窗口相关对象
        var panel = document.getElementById(panelId);
        //> 条件判断：满足括号内条件时执行对应分支
        if (!btn || !panel) return null;

        // 面板移入 main 合成面并 fixed 定位，确保可靠绘制
        //> 条件判断：满足括号内条件时执行对应分支
        if (mainEl && panel.parentElement !== mainEl) {
            //> 把子节点追加到当前元素内部末尾
            mainEl.appendChild(panel);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 给「panel.style.position」赋值，更新其保存的状态
        panel.style.position = 'fixed';

        // =========================================================
        // 【函数】place
        // 功能：处理「place」相关逻辑（header-menus）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function place() {
            //> 声明变量「r」（r），用于保存对应数据
            var r = btn.getBoundingClientRect();
            //> 声明变量「w」（w），用于保存对应数据
            var w = panel.offsetWidth || 220;
            //> 声明变量「wantLeft」，稍后赋值使用
            var wantLeft;
            //> 条件判断：满足括号内条件时执行对应分支
            if (align === 'left') {
                //> 给「wantLeft」赋值，更新其保存的状态
                wantLeft = Math.max(12, Math.min(r.left, innerWidth - w - 12));
            //> 以上条件都不满足时执行的兜底分支
            } else {
                //> 给「wantLeft」赋值，更新其保存的状态
                wantLeft = Math.max(12, Math.min(r.right - w, innerWidth - w - 12));
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            // 期望的视口坐标
            //> 声明变量「wantTop」（want top），用于保存对应数据
            var wantTop = r.bottom + 8;
            // 扣除 fixed 真实包含块（transform 祖先）的原点，得到应设置的 top/left
            //> 声明变量「origin」（origin），用于保存对应数据
            var origin = containingOrigin(panel);
            //> 给「panel.style.left」赋值，更新其保存的状态
            panel.style.left = (wantLeft - origin[0]) + 'px';
            //> 给「panel.style.top」赋值，更新其保存的状态
            panel.style.top = (wantTop - origin[1]) + 'px';
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // =========================================================
        // 【函数】openPanel
        // 功能：打开「panel」相关逻辑（open panel）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function openPanel() {
            //> 调用函数「place」并传入参数执行对应逻辑
            place();
            //> 给「panel.hidden」赋值，更新其保存的状态
            panel.hidden = false;
            //> 为元素添加一个或多个样式类
            btn.classList.add('is-open');
            //> 设置元素的 HTML 属性
            btn.setAttribute('aria-expanded', 'true');
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // =========================================================
        // 【函数】closePanel
        // 功能：关闭「panel」相关逻辑（close panel）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function closePanel() {
            //> 给「panel.hidden」赋值，更新其保存的状态
            panel.hidden = true;
            //> 移除元素的一个或多个样式类
            btn.classList.remove('is-open');
            //> 设置元素的 HTML 属性
            btn.setAttribute('aria-expanded', 'false');
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // =========================================================
        // 【函数】togglePanel
        // 功能：切换「panel」相关逻辑（toggle panel）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function togglePanel() {
            //> 条件判断：满足括号内条件时执行对应分支
            if (panel.hidden) openPanel(); else closePanel();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }

        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        btn.addEventListener('click', function (e) {
            //> 阻止事件继续向上冒泡
            e.stopPropagation();
            // 关闭其它已打开的菜单
            //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
            document.querySelectorAll('.header-menu-btn.is-open').forEach(function (b) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (b !== btn) b.click();
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            //> 调用函数「togglePanel」并传入参数执行对应逻辑
            togglePanel();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        panel.addEventListener('click', function (e) {
            //> 阻止事件继续向上冒泡
            e.stopPropagation();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        //> 绑定「resize」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        window.addEventListener('resize', function () {
            //> 条件判断：满足括号内条件时执行对应分支
            if (!panel.hidden) place();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        //> 绑定「scroll」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        window.addEventListener('scroll', function () {
            //> 条件判断：满足括号内条件时执行对应分支
            if (!panel.hidden) place();
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }, true);

        //> 返回结果并结束当前函数
        return { close: closePanel, btn: btn, panel: panel };
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    //> 声明变量「toolsMenu」（tools menu），用于保存对应数据
    var toolsMenu = createMenu('tools-menu-btn', 'tools-menu-panel', 'right');
    //> 声明变量「userMenu」（user menu），用于保存对应数据
    var userMenu = createMenu('user-menu-btn', 'user-menu-panel', 'right');
    //> 声明变量「allMenus」（all menus），用于保存对应数据
    var allMenus = [toolsMenu, userMenu].filter(Boolean);

    /* 点击页面任意空白处关闭所有菜单 */
    //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    document.addEventListener('click', function () {
        //> 遍历数组/类数组中的每一项并执行回调
        allMenus.forEach(function (m) { if (!m.panel.hidden) m.close(); });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
    /* Esc 关闭 */
    //> 绑定「keydown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    document.addEventListener('keydown', function (e) {
        //> 条件判断：满足括号内条件时执行对应分支
        if (e.key === 'Escape') {
            //> 遍历数组/类数组中的每一项并执行回调
            allMenus.forEach(function (m) { if (!m.panel.hidden) m.close(); });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* 工具箱：点击整行（图标按钮之外的区域）等价于点击开关按钮 */
    //> 声明变量「toolsPanel」（tools panel），用于保存对应数据，保存 DOM/窗口相关对象
    var toolsPanel = document.getElementById('tools-menu-panel');
    //> 条件判断：满足括号内条件时执行对应分支
    if (toolsPanel) {
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        toolsPanel.querySelectorAll('.tool-row').forEach(function (row) {
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            row.addEventListener('click', function (e) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (e.target.closest('.theme-toggle')) return; // 点按钮本身，不重复触发
                //> 声明变量「b」（b），用于保存对应数据
                var b = row.querySelector('.theme-toggle');
                //> 条件判断：满足括号内条件时执行对应分支
                if (b) b.click();
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

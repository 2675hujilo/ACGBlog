/* ============================================================================
 * focus_mode.js —— 专注阅读模式（第 4 轮新增）
 * ----------------------------------------------------------------------------
 * 适用页面：文章详情页（仅当页面存在 .focus-toggle 按钮时生效）。
 *
 * 功能总览：
 *   1. 点击 .focus-toggle 切换 <body> 上的 .focus-mode-active 类；
 *   2. 激活后由 CSS 隐藏左右侧栏、文章主体居中并加宽、折叠导航，
 *      让读者只聚焦正文，减少干扰；
 *   3. 状态写入 localStorage('focus_mode')，刷新 / 下次访问自动恢复；
 *   4. 按钮文案在「专注喵」/「退出专注喵」之间切换，并同步 aria-pressed
 *      以保证可访问性（屏幕阅读器可感知开关状态）。
 *
 * 依赖：无第三方库。
 * 注意点：只更新按钮内 .focus-text 文字节点，保留前置图标（修复过的 Bug23），
 *        避免整按钮 textContent 覆盖把图标也删掉。
 * ----------------------------------------------------------------------------
 * 排错速查：
 *   · 状态类在 body（focus-mode-active），布局变化全部由 CSS 完成，本脚本只
 *     切换类名 / 文案 / aria-pressed；
 *   · 存储键 'focus_mode' 的值是字符串 'true'/'false'，比较时注意类型；
 *   · 只改 .focus-text 保留图标（Bug23）；若模板没有 .focus-text 才整按钮兜底；
 *   · 专注模式与暗黑 / 护眼 / 字号等偏好正交，可叠加使用；
 *   · 相关文件：详情页模板（按钮）、reading.css 或正文相关 CSS（专注态排版）。
 * ============================================================================ */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';

    // 按钮两种文案：激活态显示「退出」，未激活显示「进入」
    //> 声明变量「BTN_TEXT_ON」（btn text on），用于保存对应数据，初始为字符串
    var BTN_TEXT_ON = '退出专注喵';
    //> 声明变量「BTN_TEXT_OFF」（btn text off），用于保存对应数据，初始为字符串
    var BTN_TEXT_OFF = '专注喵';

    /**
     * 应用专注模式状态。
     * @param {boolean} on - true 进入专注，false 退出。
     */
    // =========================================================
    // 【函数】apply
    // 功能：应用相关逻辑（apply）
    // 参数：
    //   - on：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function apply(on) {
        // 切换 body 类：CSS 据此隐藏侧栏、重排版心
        //> 切换样式类（有则移除、无则添加），可传第二参强制状态
        document.body.classList.toggle('focus-mode-active', on);

        //> 声明变量「btn」（btn），用于保存对应数据，保存 DOM/窗口相关对象
        var btn = document.querySelector('.focus-toggle');
        //> 条件判断：满足括号内条件时执行对应分支
        if (btn) {
            // 只改文字 span，保留按钮里的图标 img（Bug23）
            //> 声明变量「txt」（txt），用于保存对应数据
            var txt = btn.querySelector('.focus-text');
            //> 条件判断：满足括号内条件时执行对应分支
            if (txt) {
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                txt.textContent = on ? BTN_TEXT_ON : BTN_TEXT_OFF;
            //> 以上条件都不满足时执行的兜底分支
            } else {
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                btn.textContent = on ? BTN_TEXT_ON : BTN_TEXT_OFF;
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            // 同步无障碍「按下」状态
            //> 设置元素的 HTML 属性
            btn.setAttribute('aria-pressed', on ? 'true' : 'false');
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }

        // 持久化到 localStorage；存储不可用时静默忽略
        //> 尝试执行可能出错的代码，出错则进入 catch
        try {
            //> 操作 localStorage（持久化本地存储），注意容量与解析异常
            localStorage.setItem('focus_mode', on ? 'true' : 'false');
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        } catch (err) {}
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /** 初始化：恢复状态并绑定点击。 */
    // =========================================================
    // 【函数】init
    // 功能：初始化相关逻辑（init）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function init() {
        //> 声明变量「btn」（btn），用于保存对应数据，保存 DOM/窗口相关对象
        var btn = document.querySelector('.focus-toggle');
        // 详情页以外没有该按钮，直接退出
        //> 条件判断：满足括号内条件时执行对应分支
        if (!btn) return;

        // 恢复上次的专注状态（默认关闭）
        //> 声明变量「saved」（saved），用于保存对应数据
        var saved = false;
        //> 尝试执行可能出错的代码，出错则进入 catch
        try {
            //> 操作 localStorage（持久化本地存储），注意容量与解析异常
            saved = localStorage.getItem('focus_mode') === 'true';
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        } catch (err) {}
        //> 调用函数「apply」并传入参数执行对应逻辑
        apply(saved);

        // 点击按钮：在当前状态基础上取反
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        btn.addEventListener('click', function () {
            //> 声明变量「active」（active），用于保存对应数据，保存 DOM/窗口相关对象
            var active = document.body.classList.contains('focus-mode-active');
            //> 调用函数「apply」并传入参数执行对应逻辑
            apply(!active);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // DOM 未就绪则等待，否则直接初始化（兼容脚本在底部加载的情况）
    //> 条件判断：满足括号内条件时执行对应分支
    if (document.readyState === 'loading') {
        //> 绑定「DOMContentLoaded」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('DOMContentLoaded', init);
    //> 以上条件都不满足时执行的兜底分支
    } else {
        //> 调用函数「init」并传入参数执行对应逻辑
        init();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

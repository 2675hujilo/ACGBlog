/* Bug11 文件头注释
 * 表情面板脚本：动态在 body 生成 .emoji-panel，含颜文字与 Emoji，点击插入光标处。
 * 支持点击外部/Esc 关闭，并定位到触发按钮附近。
 */
/**
 * emoji_panel.js —— 评论表情包面板（第4轮新增）
 * 点击 .emoji-trigger 弹出颜文字+emoji面板，点击插入textarea光标处；外部点击/ESC关闭。
 */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';
    //> 声明变量「KAOMOJI」（kaomoji），用于保存对应数据
    var KAOMOJI = ['(≧▽≦)','(=^･ω･^=)','(ノ´ヮ`)ノ*:・゚✧','(；ω；)','( ´_ゝ`)','ヽ(✿ﾟ▽ﾟ)ノ','(╯°□°）╯︵ ┻━┻','(｡•́︿•̀｡)','(*≧ω≦)','(¬‿¬)','(◕ᴗ◕✿)','(つ✧ω✧)つ'];
    //> 声明变量「EMOJI」（emoji），用于保存对应数据
    var EMOJI = ['😀','😍','🥰','😢','😡','👍','👏','🎉','💖','✨','🌸','🍰','🐱','🌙','🔥','💡'];

    // =========================================================
    // 【函数】buildPanel
    // 功能：构建「panel」相关逻辑（build panel）
    // 参数：
    //   - trigger：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function buildPanel(trigger) {
        //> 声明变量「panel」（panel），用于保存对应数据，保存 DOM/窗口相关对象
        var panel = document.createElement('div');
        //> 给「panel.className」赋值，更新其保存的状态
        panel.className = 'emoji-panel';
        //> 设置元素的 HTML 属性
        panel.setAttribute('role', 'dialog');
        //> 声明变量「html」（html），用于保存对应数据，初始为字符串
        var html = '<div class="emoji-section"><div class="emoji-section-title">颜文字</div><div class="emoji-grid">';
        //> 遍历数组/类数组中的每一项并执行回调
        KAOMOJI.forEach(function (k) { html += '<button type="button" class="emoji-item emoji-kaomoji" data-text="' + k + '">' + k + '</button>'; });
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        html += '</div></div><div class="emoji-section"><div class="emoji-section-title">Emoji</div><div class="emoji-grid">';
        //> 遍历数组/类数组中的每一项并执行回调
        EMOJI.forEach(function (e) { html += '<button type="button" class="emoji-item" data-text="' + e + '">' + e + '</button>'; });
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        html += '</div></div>';
        //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
        panel.innerHTML = html;
        //> 把子节点追加到当前元素内部末尾
        document.body.appendChild(panel);
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        panel.addEventListener('click', function (e) {
            //> 声明变量「item」（item），用于保存对应数据
            var item = e.target.closest('.emoji-item');
            //> 条件判断：满足括号内条件时执行对应分支
            if (!item) return;
            //> 声明变量「text」（text），用于保存对应数据
            var text = item.getAttribute('data-text');
            //> 声明变量「form」（form），用于保存对应数据
            var form = trigger.closest('form') || document;
            //> 声明变量「ta」（ta），用于保存对应数据
            var ta = form.querySelector('textarea') || document.querySelector('.comment-form textarea, textarea[name="content"]');
            //> 条件判断：满足括号内条件时执行对应分支
            if (ta) {
                //> 声明变量「s」（s），用于保存对应数据
                var s = ta.selectionStart || ta.value.length;
                //> 声明变量「en」（en），用于保存对应数据
                var en = ta.selectionEnd || s;
                //> 给「ta.value」赋值，更新其保存的状态
                ta.value = ta.value.slice(0, s) + text + ta.value.slice(en);
                //> 给「ta.selectionStart」赋值，更新其保存的状态
                ta.selectionStart = ta.selectionEnd = s + text.length;
                //> 操作「ta」的相关方法/属性
                ta.focus();
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 调用函数「closePanel」并传入参数执行对应逻辑
            closePanel();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        //> 返回结果并结束当前函数
        return panel;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    //> 声明变量「currentPanel」（current panel），用于保存对应数据
    var currentPanel = null;
    // =========================================================
    // 【函数】closePanel
    // 功能：关闭「panel」相关逻辑（close panel）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function closePanel() {
        //> 条件判断：满足括号内条件时执行对应分支
        if (currentPanel) { currentPanel.remove(); currentPanel = null; }
        //> 移除元素的一个或多个样式类
        document.body.classList.remove('emoji-panel-open');
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // =========================================================
    // 【函数】openPanel
    // 功能：打开「panel」相关逻辑（open panel）
    // 参数：
    //   - trigger：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function openPanel(trigger) {
        //> 条件判断：满足括号内条件时执行对应分支
        if (currentPanel) { closePanel(); return; }
        //> 给「currentPanel」赋值，更新其保存的状态
        currentPanel = buildPanel(trigger);
        //> 为元素添加一个或多个样式类
        document.body.classList.add('emoji-panel-open');
        //> 声明变量「r」（r），用于保存对应数据
        var r = trigger.getBoundingClientRect();
        //> 给「currentPanel.style.top」赋值，更新其保存的状态
        currentPanel.style.top = (r.bottom + window.scrollY + 6) + 'px';
        //> 给「currentPanel.style.left」赋值，更新其保存的状态
        currentPanel.style.left = Math.max(8, r.left + window.scrollX - 20) + 'px';
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // =========================================================
    // 【函数】init
    // 功能：初始化相关逻辑（init）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function init() {
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        document.querySelectorAll('.emoji-trigger').forEach(function (t) {
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            t.addEventListener('click', function (e) {
                //> 阻止事件的默认行为（如表单提交、链接跳转）
                e.preventDefault(); e.stopPropagation();
                //> 调用函数「openPanel」并传入参数执行对应逻辑
                openPanel(t);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('click', function (e) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (currentPanel && !currentPanel.contains(e.target) && !e.target.closest('.emoji-trigger')) closePanel();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        //> 绑定「keydown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('keydown', function (e) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (e.key === 'Escape' && currentPanel) closePanel();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    //> 条件判断：满足括号内条件时执行对应分支
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    else init();
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

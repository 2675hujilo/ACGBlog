/* ============================================================
 * features/settings_prefs.js —— Bug22: 账号设置页「阅读偏好」
 * 主题色 / 字号 / 护眼 / AMOLED纯黑 / 交互音效 / 页面动效
 * 任一控件变化：即时在当前页面生效 + 写入账号偏好(后端) +
 *              同步本地 localStorage（详情页阅读设置保持一致）
 * ============================================================ */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';
    //> 声明变量「form」（form），用于保存对应数据，保存 DOM/窗口相关对象
    var form = document.getElementById('preferences-form');
    //> 条件判断：满足括号内条件时执行对应分支
    if (!form) return;

    // =========================================================
    // 【函数】$
    // 功能：处理「$」相关逻辑（settings_prefs）
    // 参数：
    //   - id：传入的参数（含义结合调用处与函数体）
    // 返回：函数体内有 return，返回对应结果
    // 注意：操作 DOM，取值后先判空再使用，避免 null 报错
    // =========================================================
    function $(id) { return document.getElementById(id); }
    //> 声明变量「themeSel」（theme sel），用于保存对应数据
    var themeSel = $('pref-theme-color'),
        //> 给「sizeSel」赋值，更新其保存的状态
        sizeSel = $('pref-font-size'),
        //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
        eyeChk = form.querySelector('[name="eye_protection"]'),
        //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
        amoledChk = form.querySelector('[name="amoled_dark"]'),
        //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
        soundChk = form.querySelector('[name="sound_enabled"]'),
        //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
        effectsChk = form.querySelector('[name="effects_enabled"]');

    /* 读取 cookie（用于 CSRF） */
    // =========================================================
    // 【函数】cookie
    // 功能：处理「cookie」相关逻辑（settings_prefs）
    // 参数：
    //   - name：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function cookie(name) {
        //> 声明变量「m」（m），用于保存对应数据，保存 DOM/窗口相关对象
        var m = document.cookie.match(new RegExp('\\b' + name + '=([^;]*)'));
        //> 返回结果并结束当前函数
        return m ? decodeURIComponent(m[1]) : '';
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    /* 轻量 toast 提示（复用全站 #global-toast，不存在则临时创建） */
    // =========================================================
    // 【函数】toast
    // 功能：处理「toast」相关逻辑（settings_prefs）
    // 参数：
    //   - msg：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function toast(msg) {
        //> 声明变量「t」（t），用于保存对应数据，保存 DOM/窗口相关对象
        var t = document.getElementById('global-toast');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!t) {
            //> 创建新的 DOM 元素节点，后续需挂载到文档才显示
            t = document.createElement('div');
            //> 给「t.id」赋值，更新其保存的状态
            t.id = 'global-toast';
            //> 给「t.style.cssText」赋值，更新其保存的状态
            t.style.cssText = 'position:fixed;left:50%;bottom:32px;transform:translateX(-50%);background:rgba(43,35,64,.92);color:#fff;padding:10px 20px;border-radius:999px;font-size:.9rem;z-index:9999;opacity:0;transition:opacity .25s;pointer-events:none;';
            //> 把子节点追加到当前元素内部末尾
            document.body.appendChild(t);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 读写纯文本内容，不解析 HTML，可防 XSS
        t.textContent = msg;
        //> 为元素添加一个或多个样式类
        t.classList.add('show');
        //> 给「t.style.opacity」赋值，更新其保存的状态
        t.style.opacity = '1';
        //> 清除对应的定时器，防止其继续执行
        clearTimeout(t._timer);
        //> 移除元素的一个或多个样式类
        t._timer = setTimeout(function () { t.style.opacity = '0'; t.classList.remove('show'); }, 1800);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    //> 声明变量「P」（p），用于保存对应数据，保存 DOM/窗口相关对象
    var P = window.USER_PREFERENCES || {};
    /* 字号档位 → 详情页正文 --read-font-scale 映射 */
    //> 声明变量「FONT_SCALE」（font scale），用于保存对应数据
    var FONT_SCALE = { small: 0.92, medium: 1.0, large: 1.15, xlarge: 1.3 };

    /* 收集控件当前值（字段名与后端偏好一致） */
    // =========================================================
    // 【函数】collect
    // 功能：收集相关逻辑（collect）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function collect() {
        //> 返回结果并结束当前函数
        return {
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            theme_color: themeSel.value,
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            font_size: sizeSel.value,
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            eye_protection: eyeChk.checked,
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            amoled_dark: amoledChk.checked,
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            sound_enabled: soundChk.checked,
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            effects_enabled: effectsChk.checked
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        };
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* 即时应用到当前页面（无需刷新即可看到效果） */
    // =========================================================
    // 【函数】apply
    // 功能：应用相关逻辑（apply）
    // 参数：
    //   - p：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function apply(p) {
        //> 设置元素的 HTML 属性
        document.body.setAttribute('data-theme-color', p.theme_color || 'purple_pink');
        //> 设置元素的 HTML 属性
        document.body.setAttribute('data-font-size', p.font_size || 'medium');
        //> 切换样式类（有则移除、无则添加），可传第二参强制状态
        document.body.classList.toggle('eye-protection', !!p.eye_protection);
        //> 切换样式类（有则移除、无则添加），可传第二参强制状态
        document.body.classList.toggle('amoled-dark', !!p.amoled_dark);
        //> 切换样式类（有则移除、无则添加），可传第二参强制状态
        document.documentElement.classList.toggle('motion-off', !p.effects_enabled);
        //> 尝试执行可能出错的代码，出错则进入 catch
        try { localStorage.setItem('moe_motion', p.effects_enabled ? '1' : '0'); } catch (e) {}

        /* 音效：与导航栏音效按钮（common.js 维护 moe_sound）状态对齐 */
        //> 尝试执行可能出错的代码，出错则进入 catch
        try {
            //> 声明变量「curSound」（cur sound），用于保存对应数据
            var curSound = localStorage.getItem('moe_sound') !== '0';
            //> 条件判断：满足括号内条件时执行对应分支
            if (curSound !== p.sound_enabled) {
                //> 操作 localStorage（持久化本地存储），注意容量与解析异常
                localStorage.setItem('moe_sound', p.sound_enabled ? '1' : '0');
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 声明变量「sb」（sb），用于保存对应数据，保存 DOM/窗口相关对象
            var sb = document.getElementById('sound-toggle');
            //> 条件判断：满足括号内条件时执行对应分支
            if (sb) {
                //> 声明变量「sbOn」（sb on），用于保存对应数据
                var sbOn = sb.textContent.indexOf('\uD83D\uDD0A') >= 0;  // 🔊 表示开
                //> 条件判断：满足括号内条件时执行对应分支
                if (sbOn !== p.sound_enabled) sb.click();  // 翻转 common.js 内部状态
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        } catch (e) {}

        /* 同步详情页阅读偏好（reading.js 读取 blog_reading_prefs） */
        //> 尝试执行可能出错的代码，出错则进入 catch
        try {
            //> 声明变量「rp」（rp），用于保存对应数据
            var rp = JSON.parse(localStorage.getItem('blog_reading_prefs') || '{}');
            //> 给「rp.themeColor」赋值，更新其保存的状态
            rp.themeColor = (p.theme_color === 'purple_pink') ? '' : p.theme_color;
            //> 给「rp.fontScale」赋值，更新其保存的状态
            rp.fontScale = FONT_SCALE[p.font_size] || 1;
            //> 给「rp.eyeProtection」赋值，更新其保存的状态
            rp.eyeProtection = !!p.eye_protection;
            //> 给「rp.amoled」赋值，更新其保存的状态
            rp.amoled = !!p.amoled_dark;
            //> 操作 localStorage（持久化本地存储），注意容量与解析异常
            localStorage.setItem('blog_reading_prefs', JSON.stringify(rp));
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        } catch (e) {}
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* 持久化到账号（PUT /api/user/preferences/） */
    //> 声明变量「saveTimer」（save timer），用于保存对应数据
    var saveTimer = null;
    // =========================================================
    // 【函数】persist
    // 功能：处理「persist」相关逻辑（settings_prefs）
    // 参数：
    //   - p：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function persist(p) {
        //> 清除对应的定时器，防止其继续执行
        clearTimeout(saveTimer);
        //> 设置延时执行的定时器，返回可清除的定时器 id
        saveTimer = setTimeout(function () {
            //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
            fetch('/api/user/preferences/', {
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                method: 'PUT',
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                headers: {
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    'Content-Type': 'application/json',
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    'X-CSRFToken': cookie('csrftoken') || window.csrftoken,
                    //> 使用 XHR 发起传统异步请求
                    'X-Requested-With': 'XMLHttpRequest'
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                },
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                credentials: 'same-origin',
                //> 把 JS 数据序列化为 JSON 字符串
                body: JSON.stringify(p)
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }).then(function (r) { return r.json(); })
              //> 该行执行对应的脚本逻辑（结合上下文理解）
              .then(function () { toast('阅读偏好已保存喵~✨'); })
              //> 该行执行对应的脚本逻辑（结合上下文理解）
              .catch(function () { toast('偏好已在本设备生效喵~'); });
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }, 250);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* 用账号偏好 + 本地开关初始化控件 */
    // =========================================================
    // 【函数】init
    // 功能：初始化相关逻辑（init）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function init() {
        //> 条件判断：满足括号内条件时执行对应分支
        if (P.theme_color) themeSel.value = P.theme_color;
        //> 条件判断：满足括号内条件时执行对应分支
        if (P.font_size) sizeSel.value = P.font_size;
        //> 给「eyeChk.checked」赋值，更新其保存的状态
        eyeChk.checked = !!P.eye_protection;
        //> 给「amoledChk.checked」赋值，更新其保存的状态
        amoledChk.checked = !!P.amoled_dark;
        //> 声明变量「lsSound」（ls sound），用于保存对应数据
        var lsSound = localStorage.getItem('moe_sound');
        // 无本地记录时与导航音效按钮(common.js)默认行为一致：音效默认开
        //> 给「soundChk.checked」赋值，更新其保存的状态
        soundChk.checked = lsSound !== null ? lsSound !== '0' : true;
        //> 声明变量「lsMotion」（ls motion），用于保存对应数据
        var lsMotion = localStorage.getItem('moe_motion');
        //> 给「effectsChk.checked」赋值，更新其保存的状态
        effectsChk.checked = lsMotion !== null ? lsMotion !== '0' : (P.effects_enabled !== false);
        //> 调用函数「apply」并传入参数执行对应逻辑
        apply(collect());
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* 任一控件变化：实时生效并保存 */
    //> 遍历数组/类数组中的每一项并执行回调
    [themeSel, sizeSel, eyeChk, amoledChk, soundChk, effectsChk].forEach(function (el) {
        //> 条件判断：满足括号内条件时执行对应分支
        if (!el) return;
        //> 绑定「change」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        el.addEventListener('change', function () {
            //> 声明变量「p」（p），用于保存对应数据
            var p = collect();
            //> 调用函数「apply」并传入参数执行对应逻辑
            apply(p);
            //> 调用函数「persist」并传入参数执行对应逻辑
            persist(p);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
    /* 拦截表单传统提交（已实时保存，避免整页刷新） */
    //> 绑定「submit」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    form.addEventListener('submit', function (e) {
        //> 阻止事件的默认行为（如表单提交、链接跳转）
        e.preventDefault();
        //> 声明变量「p」（p），用于保存对应数据
        var p = collect();
        //> 调用函数「apply」并传入参数执行对应逻辑
        apply(p);
        //> 调用函数「persist」并传入参数执行对应逻辑
        persist(p);
        //> 调用函数「toast」并传入参数执行对应逻辑
        toast('阅读偏好已保存喵~✨');
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    //> 调用函数「init」并传入参数执行对应逻辑
    init();
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

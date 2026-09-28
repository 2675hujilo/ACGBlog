/**
 * features/reading.js —— 阅读体验增强（B类）
 *
 * 功能：
 *   B1 字体大小调节（A-/A/A+，写 --read-font-scale）
 *   B2 行高调节（slider，写 --read-line-height）
 *   B3 字体切换（sans/song/mono，body[data-font-family]）
 *   B4 主题色切换（紫粉/蓝绿/橙黄/玫瑰，body[data-theme-color]）
 *   B5 护眼模式（body.eye-protection）
 *   B6 AMOLED 纯黑（body.amoled-dark）
 *   B7 纸张纹理（body.paper-texture）
 *   B9 选中文字划线笔记（localStorage，可再点清除）
 *   B10 段落书签（段落旁按钮，localStorage 记录滚动位置）
 *   B11 选中文字翻译（弹出按钮，调免费翻译接口）
 *   B12 TTS 语音朗读（Web Speech API，播放/暂停/语速）
 *   B14 编辑页字数实时统计
 *   B15 字号同步评论区（body[data-font-scale-sync]）
 *
 * 偏好来源：window.USER_PREFERENCES；修改后写 localStorage 并尝试 PUT
 *           /api/user/preferences/（未登录则静默失败，不影响使用）
 * 防御式：仅在相关 DOM 存在时初始化，无依赖，纯原生。
 */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';

    //> 声明变量「PREF」（pref），用于保存对应数据，保存 DOM/窗口相关对象
    var PREF = window.USER_PREFERENCES || {};
    //> 声明变量「LS_KEY」（ls key），用于保存对应数据，初始为字符串
    var LS_KEY = 'blog_reading_prefs';

    /* ---------- 偏好读写 ---------- */
    // =========================================================
    // 【函数】loadPrefs
    // 功能：加载「prefs」相关逻辑（load prefs）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function loadPrefs() {
        //> 尝试执行可能出错的代码，出错则进入 catch
        try { return JSON.parse(localStorage.getItem(LS_KEY)) || {}; }
        //> 捕获并处理 try 中抛出的异常，避免程序中断
        catch (e) { return {}; }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // =========================================================
    // 【函数】savePrefs
    // 功能：保存「prefs」相关逻辑（save prefs）
    // 参数：
    //   - p：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function savePrefs(p) {
        //> 尝试执行可能出错的代码，出错则进入 catch
        try { localStorage.setItem(LS_KEY, JSON.stringify(p)); } catch (e) {}
        // 尽力同步到后端偏好（未登录会 403/重定向，静默忽略）
        //> 条件判断：满足括号内条件时执行对应分支
        if (window.csrftoken) {
            //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
            fetch('/api/user/preferences/', {
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                method: 'PUT',
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                headers: {
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    'Content-Type': 'application/json',
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    'X-CSRFToken': window.csrftoken,
                    //> 使用 XHR 发起传统异步请求
                    'X-Requested-With': 'XMLHttpRequest'
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                },
                //> 把 JS 数据序列化为 JSON 字符串
                body: JSON.stringify(p),
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                credentials: 'same-origin'
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }).catch(function () {});
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    //> 声明变量「prefs」（prefs），用于保存对应数据
    var prefs = loadPrefs();

    // =========================================================
    // 【函数】setVar
    // 功能：设置「var」相关逻辑（set var）
    // 参数：
    //   - name：传入的参数（含义结合调用处与函数体）
    //   - val：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function setVar(name, val) { document.documentElement.style.setProperty(name, val); }

    /* ---------- B1/B2/B3 应用偏好到页面 ---------- */
    // =========================================================
    // 【函数】applyReadingPrefs
    // 功能：应用「reading prefs」相关逻辑（apply reading prefs）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function applyReadingPrefs() {
        //> 条件判断：满足括号内条件时执行对应分支
        if (prefs.fontScale) setVar('--read-font-scale', prefs.fontScale);
        //> 条件判断：满足括号内条件时执行对应分支
        if (prefs.lineHeight) setVar('--read-line-height', prefs.lineHeight);
        //> 条件判断：满足括号内条件时执行对应分支
        if (prefs.fontFamily) document.body.setAttribute('data-font-family', prefs.fontFamily);
        //> 条件判断：满足括号内条件时执行对应分支
        if (prefs.themeColor) document.body.setAttribute('data-theme-color', prefs.themeColor);
        //> 切换样式类（有则移除、无则添加），可传第二参强制状态
        document.body.classList.toggle('eye-protection', !!prefs.eyeProtection);
        //> 切换样式类（有则移除、无则添加），可传第二参强制状态
        document.body.classList.toggle('amoled-dark', !!prefs.amoled);
        //> 切换样式类（有则移除、无则添加），可传第二参强制状态
        document.body.classList.toggle('paper-texture', !!prefs.paper);
        //> 设置元素的 HTML 属性
        document.body.setAttribute('data-font-scale-sync', '1');
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    //> 调用函数「applyReadingPrefs」并传入参数执行对应逻辑
    applyReadingPrefs();

    /* ---------- B1/B2/B3/B4 工具条按钮绑定 ---------- */
    // =========================================================
    // 【函数】on
    // 功能：处理……事件相关逻辑（on）
    // 参数：
    //   - sel：传入的参数（含义结合调用处与函数体）
    //   - evt：传入的参数（含义结合调用处与函数体）
    //   - fn：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function on(sel, evt, fn) {
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        document.querySelectorAll(sel).forEach(function (el) { el.addEventListener(evt, fn); });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // 字号
    //> 调用函数「on」并传入参数执行对应逻辑
    on('[data-act="font-dec"]', 'click', function () {
        //> 给「prefs.fontScale」赋值，更新其保存的状态
        prefs.fontScale = Math.max(.8, (parseFloat(prefs.fontScale || 1) - .1).toFixed(2));
        //> 调用函数「setVar」并传入参数执行对应逻辑
        setVar('--read-font-scale', prefs.fontScale); savePrefs(prefs); syncLabel();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
    //> 调用函数「on」并传入参数执行对应逻辑
    on('[data-act="font-inc"]', 'click', function () {
        //> 给「prefs.fontScale」赋值，更新其保存的状态
        prefs.fontScale = Math.min(1.8, (parseFloat(prefs.fontScale || 1) + .1).toFixed(2));
        //> 调用函数「setVar」并传入参数执行对应逻辑
        setVar('--read-font-scale', prefs.fontScale); savePrefs(prefs); syncLabel();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
    // =========================================================
    // 【函数】syncLabel
    // 功能：同步「label」相关逻辑（sync label）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function syncLabel() {
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        document.querySelectorAll('.fs-value').forEach(function (el) {
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            el.textContent = Math.round((parseFloat(prefs.fontScale || 1)) * 100) + '%';
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    //> 调用函数「syncLabel」并传入参数执行对应逻辑
    syncLabel();
    // 行高
    //> 声明变量「lh」（lh），用于保存对应数据，保存 DOM/窗口相关对象
    var lh = document.querySelector('.line-height-slider');
    //> 条件判断：满足括号内条件时执行对应分支
    if (lh) {
        //> 给「lh.value」赋值，更新其保存的状态
        lh.value = prefs.lineHeight || 1.8;
        //> 绑定「input」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        lh.addEventListener('input', function () {
            //> 给「prefs.lineHeight」赋值，更新其保存的状态
            prefs.lineHeight = lh.value; setVar('--read-line-height', lh.value); savePrefs(prefs);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // 字体
    //> 调用函数「on」并传入参数执行对应逻辑
    on('[data-font]', 'click', function () {
        //> 读取元素的 HTML 属性值
        prefs.fontFamily = this.getAttribute('data-font');
        //> 设置元素的 HTML 属性
        document.body.setAttribute('data-font-family', prefs.fontFamily);
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        document.querySelectorAll('[data-font]').forEach(function (b) { b.classList.toggle('active', b === this); }, this);
        //> 调用函数「savePrefs」并传入参数执行对应逻辑
        savePrefs(prefs);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
    // 主题色
    //> 调用函数「on」并传入参数执行对应逻辑
    on('[data-theme-color]', 'click', function () {
        //> 读取元素的 HTML 属性值
        prefs.themeColor = this.getAttribute('data-theme-color') || '';
        //> 条件判断：满足括号内条件时执行对应分支
        if (prefs.themeColor) document.body.setAttribute('data-theme-color', prefs.themeColor);
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        else document.body.removeAttribute('data-theme-color');
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        document.querySelectorAll('[data-theme-color].swatch').forEach(function (s) {
            //> 切换样式类（有则移除、无则添加），可传第二参强制状态
            s.classList.toggle('active', s === this);
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }, this);
        //> 调用函数「savePrefs」并传入参数执行对应逻辑
        savePrefs(prefs);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
    // 模式开关
    //> 调用函数「on」并传入参数执行对应逻辑
    on('[data-act="eye"]', 'click', function () {
        //> 给「prefs.eyeProtection」赋值，更新其保存的状态
        prefs.eyeProtection = !prefs.eyeProtection;
        //> 切换样式类（有则移除、无则添加），可传第二参强制状态
        document.body.classList.toggle('eye-protection', prefs.eyeProtection);
        //> 切换样式类（有则移除、无则添加），可传第二参强制状态
        this.classList.toggle('active', prefs.eyeProtection); savePrefs(prefs);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
    //> 调用函数「on」并传入参数执行对应逻辑
    on('[data-act="amoled"]', 'click', function () {
        //> 给「prefs.amoled」赋值，更新其保存的状态
        prefs.amoled = !prefs.amoled;
        //> 切换样式类（有则移除、无则添加），可传第二参强制状态
        document.body.classList.toggle('amoled-dark', prefs.amoled);
        //> 切换样式类（有则移除、无则添加），可传第二参强制状态
        this.classList.toggle('active', prefs.amoled); savePrefs(prefs);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
    //> 调用函数「on」并传入参数执行对应逻辑
    on('[data-act="paper"]', 'click', function () {
        //> 给「prefs.paper」赋值，更新其保存的状态
        prefs.paper = !prefs.paper;
        //> 切换样式类（有则移除、无则添加），可传第二参强制状态
        document.body.classList.toggle('paper-texture', prefs.paper);
        //> 切换样式类（有则移除、无则添加），可传第二参强制状态
        this.classList.toggle('active', prefs.paper); savePrefs(prefs);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- B10 段落书签：给正文段落加书签按钮 ---------- */
    //> 声明变量「body」（body），用于保存对应数据，保存 DOM/窗口相关对象
    var body = document.getElementById('article-body');
    //> 条件判断：满足括号内条件时执行对应分支
    if (body) {
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        body.querySelectorAll('p, h2, h3').forEach(function (p) {
            //> 给「p.style.position」赋值，更新其保存的状态
            p.style.position = p.style.position || 'relative';
            //> 声明变量「bm」（bm），用于保存对应数据，保存 DOM/窗口相关对象
            var bm = document.createElement('span');
            //> 给「bm.className」赋值，更新其保存的状态
            bm.className = 'paragraph-bookmark';
            //> 给「bm.title」赋值，更新其保存的状态
            bm.title = '在此处添加书签';
            //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
            bm.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12v18l-6-4-6 4z"/></svg>';
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            bm.addEventListener('click', function (e) {
                //> 阻止事件继续向上冒泡
                e.stopPropagation();
                //> 声明变量「id」（id），用于保存对应数据
                var id = p.id || ('p_' + Math.random().toString(36).slice(2, 8));
                //> 条件判断：满足括号内条件时执行对应分支
                if (!p.id) p.id = id;
                //> 声明变量「marks」（marks），用于保存对应数据
                var marks = JSON.parse(localStorage.getItem('blog_bookmarks') || '{}');
                //> 条件判断：满足括号内条件时执行对应分支
                if (bm.classList.contains('marked')) {
                    //> 移除元素的一个或多个样式类
                    delete marks[id]; bm.classList.remove('marked');
                //> 以上条件都不满足时执行的兜底分支
                } else {
                    //> 读写纯文本内容，不解析 HTML，可防 XSS
                    marks[id] = { top: window.scrollY, text: (p.textContent || '').slice(0, 40) };
                    //> 为元素添加一个或多个样式类
                    bm.classList.add('marked');
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
                //> 操作 localStorage（持久化本地存储），注意容量与解析异常
                localStorage.setItem('blog_bookmarks', JSON.stringify(marks));
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            //> 把子节点追加到当前元素内部末尾
            p.appendChild(bm);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });

        /* ---------- B9/B11 选中文字：笔记 / 翻译 弹出按钮 ---------- */
        //> 绑定「mouseup」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('mouseup', function () {
            // =========================================================
            // 【函数】setTimeout
            // 功能：设置「timeout」相关逻辑（set timeout）
            // 参数：
            //   - function：传入的参数（含义结合调用处与函数体）
            //   - (：传入的参数（含义结合调用处与函数体）
            // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
            // 注意：含定时器，注意在适当时机清除，避免泄漏与重复触发
            // =========================================================
            setTimeout(function () {
                //> 声明变量「sel」（sel），用于保存对应数据，保存 DOM/窗口相关对象
                var sel = window.getSelection();
                //> 声明变量「text」（text），用于保存对应数据
                var text = sel ? sel.toString().trim() : '';
                //> 声明变量「old」（old），用于保存对应数据，保存 DOM/窗口相关对象
                var old = document.querySelector('.note-popup');
                //> 条件判断：满足括号内条件时执行对应分支
                if (old) old.remove();
                //> 条件判断：满足括号内条件时执行对应分支
                if (!text || text.length < 2 || !body.contains(sel.anchorNode)) return;
                //> 声明变量「rect」（rect），用于保存对应数据
                var rect = sel.getRangeAt(0).getBoundingClientRect();
                //> 声明变量「pop」（pop），用于保存对应数据，保存 DOM/窗口相关对象
                var pop = document.createElement('div');
                //> 给「pop.className」赋值，更新其保存的状态
                pop.className = 'note-popup';
                //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
                pop.innerHTML = '<button data-note>✏️ 笔记</button><button data-trans>🌐 翻译</button>';
                //> 给「pop.style.left」赋值，更新其保存的状态
                pop.style.left = (rect.left + window.scrollX) + 'px';
                //> 给「pop.style.top」赋值，更新其保存的状态
                pop.style.top = (rect.bottom + window.scrollY + 8) + 'px';
                //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
                pop.querySelector('[data-note]').addEventListener('click', function () {
                    //> 声明变量「range」（range），用于保存对应数据
                    var range = sel.getRangeAt(0);
                    //> 声明变量「mark」（mark），用于保存对应数据，保存 DOM/窗口相关对象
                    var mark = document.createElement('mark');
                    //> 读写纯文本内容，不解析 HTML，可防 XSS
                    mark.className = 'text-note'; mark.textContent = text;
                    //> 操作「range」的相关方法/属性
                    range.deleteContents(); range.insertNode(mark);
                    //> 把元素从 DOM 中移除
                    pop.remove();
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                });
                //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
                pop.querySelector('[data-trans]').addEventListener('click', function () {
                    //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
                    translate(text, pop.querySelector('[data-trans]'));
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                });
                //> 把子节点追加到当前元素内部末尾
                document.body.appendChild(pop);
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }, 10);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- B11 翻译：调用免费公开接口（失败给出提示，不报错） ---------- */
    // =========================================================
    // 【函数】translate
    // 功能：处理「translate」相关逻辑（reading）
    // 参数：
    //   - text：传入的参数（含义结合调用处与函数体）
    //   - btn：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function translate(text, btn) {
        //> 读写纯文本内容，不解析 HTML，可防 XSS
        btn.textContent = '翻译中…';
        //> 声明变量「url」（url），用于保存对应数据，初始为字符串
        var url = 'https://api.mymemory.translated.net/get?q=' + encodeURIComponent(text) +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '&langpair=zh-CN|en';
        //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
        fetch(url).then(function (r) { return r.json(); }).then(function (data) {
            //> 声明变量「out」（out），用于保存对应数据
            var out = data && data.responseData && data.responseData.translatedText;
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            btn.textContent = out ? out.slice(0, 80) : '翻译失败';
        //> 读写纯文本内容，不解析 HTML，可防 XSS
        }).catch(function () { btn.textContent = '翻译服务不可用'; });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- B12 TTS 语音朗读 ---------- */
    //> 声明变量「ttsBar」（tts bar），用于保存对应数据，保存 DOM/窗口相关对象
    var ttsBar = document.querySelector('.tts-bar');
    //> 条件判断：满足括号内条件时执行对应分支
    if (ttsBar && 'speechSynthesis' in window) {
        //> 声明变量「playing」（playing），用于保存对应数据
        var playing = false;
        //> 声明变量「playBtn」（play btn），用于保存对应数据
        var playBtn = ttsBar.querySelector('[data-tts="play"]');
        //> 声明变量「stopBtn」（stop btn），用于保存对应数据
        var stopBtn = ttsBar.querySelector('[data-tts="stop"]');
        //> 声明变量「speed」（speed），用于保存对应数据
        var speed = ttsBar.querySelector('.tts-speed');
        //> 声明变量「status」（status），用于保存对应数据
        var status = ttsBar.querySelector('.tts-status');
        // =========================================================
        // 【函数】text
        // 功能：处理「text」相关逻辑（reading）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function text() {
            //> 返回结果并结束当前函数
            return (document.getElementById('article-body') || document.body).innerText.slice(0, 3000);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 条件判断：满足括号内条件时执行对应分支
        if (playBtn) playBtn.addEventListener('click', function () {
            //> 条件判断：满足括号内条件时执行对应分支
            if (playing) { window.speechSynthesis.pause(); playing = false; status.textContent = '已暂停'; return; }
            //> 声明变量「u」（u），用于保存对应数据
            var u = new SpeechSynthesisUtterance(text());
            //> 给「u.lang」赋值，更新其保存的状态
            u.lang = 'zh-CN';
            //> 条件判断：满足括号内条件时执行对应分支
            if (speed) u.rate = parseFloat(speed.value) || 1;
            // =========================================================
            // 【函数】onend
            // 功能：处理「onend」相关逻辑（reading）
            // 参数：无
            // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
            // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
            // =========================================================
            u.onend = function () { playing = false; status.textContent = '朗读结束'; };
            //> 操作「window.speechSynthesis」的相关方法/属性
            window.speechSynthesis.cancel();
            //> 操作「window.speechSynthesis」的相关方法/属性
            window.speechSynthesis.speak(u);
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            playing = true; status.textContent = '朗读中…';
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        //> 条件判断：满足括号内条件时执行对应分支
        if (stopBtn) stopBtn.addEventListener('click', function () {
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            window.speechSynthesis.cancel(); playing = false; status.textContent = '已停止';
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        /* Bug23: 操作栏「朗读喵」快捷按钮，等同播放/暂停 */
        //> 声明变量「ttsQuick」（tts quick），用于保存对应数据，保存 DOM/窗口相关对象
        var ttsQuick = document.getElementById('tts-toggle-btn');
        //> 条件判断：满足括号内条件时执行对应分支
        if (ttsQuick && playBtn) ttsQuick.addEventListener('click', function () { playBtn.click(); });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- Bug23: 阅读设置面板开合 ---------- */
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    (function () {
        //> 声明变量「btn」（btn），用于保存对应数据，保存 DOM/窗口相关对象
        var btn = document.getElementById('reading-settings-btn');
        //> 声明变量「mask」（mask），用于保存对应数据，保存 DOM/窗口相关对象
        var mask = document.getElementById('reading-settings-mask');
        //> 声明变量「close」（close），用于保存对应数据，保存 DOM/窗口相关对象
        var close = document.getElementById('rs-close');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!btn || !mask) return;
        // =========================================================
        // 【函数】openPanel
        // 功能：打开「panel」相关逻辑（open panel）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function openPanel() { mask.hidden = false; btn.setAttribute('aria-expanded', 'true'); }
        // =========================================================
        // 【函数】hidePanel
        // 功能：隐藏「panel」相关逻辑（hide panel）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function hidePanel() { mask.hidden = true; btn.setAttribute('aria-expanded', 'false'); }
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        btn.addEventListener('click', function () { mask.hidden ? openPanel() : hidePanel(); });
        //> 条件判断：满足括号内条件时执行对应分支
        if (close) close.addEventListener('click', hidePanel);
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        mask.addEventListener('click', function (e) { if (e.target === mask) hidePanel(); });
        //> 绑定「keydown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('keydown', function (e) { if (e.key === 'Escape') hidePanel(); });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    })();

    /* ---------- B14 编辑页字数实时统计 ---------- */
    //> 声明变量「editor」（editor），用于保存对应数据，保存 DOM/窗口相关对象
    var editor = document.querySelector('#id_content, .editor-input, textarea.editor-area');
    //> 条件判断：满足括号内条件时执行对应分支
    if (editor) {
        //> 声明变量「wc」（wc），用于保存对应数据，保存 DOM/窗口相关对象
        var wc = document.querySelector('.editor-word-count');
        //> 条件判断：满足括号内条件时执行对应分支
        if (wc) {
            // =========================================================
            // 【函数】upd
            // 功能：处理「upd」相关逻辑（reading）
            // 参数：无
            // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
            // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
            // =========================================================
            var upd = function () {
                //> 声明变量「n」（n），用于保存对应数据，值为一个函数
                var n = (editor.value || '').length;
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                wc.textContent = n + ' 字';
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            };
            //> 绑定「input」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            editor.addEventListener('input', upd); upd();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

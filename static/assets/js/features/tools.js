/* Bug11 文件头注释
 * 工具箱功能脚本：顶部「🧰」菜单内各小工具（如返回、复制、刷新等）的注册与执行。
 * 采用事件委托，按 data-action 分发对应操作，并给出 moeToast 反馈。
 */
/**
 * features/tools.js —— 效率工具（G类）
 *
 * 功能：
 *   G1 代码行号显示
 *   G2 代码块折叠/展开
 *   G3 文章导出 PDF（前端 jsPDF + html2canvas，中文像素渲染无乱码）
 *   G4 文章导出 Markdown（调 /api/article/<pk>/export/md/）
 *   G5 分享卡片生成（Canvas）
 *   G6 文章二维码生成
 *   G7 短链接生成
 *   G8 全文复制
 *   G9 目录导出大纲（TOC -> Markdown）
 *   G10 正文图片批量下载
 *
 * 防御式：按 data-* 存在初始化，纯原生，无外部库。
 */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';
    // =========================================================
    // 【函数】toast
    // 功能：处理「toast」相关逻辑（tools）
    // 参数：
    //   - msg：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function toast(msg) {
        //> 声明变量「t」（t），用于保存对应数据，保存 DOM/窗口相关对象
        var t = document.getElementById('global-toast');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!t) { t = document.createElement('div'); t.id = 'global-toast'; document.body.appendChild(t); }
        //> 读写纯文本内容，不解析 HTML，可防 XSS
        t.textContent = msg; t.classList.add('show');
        //> 移除元素的一个或多个样式类
        clearTimeout(t._t); t._t = setTimeout(function () { t.classList.remove('show'); }, 1600);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // =========================================================
    // 【函数】download
    // 功能：处理「download」相关逻辑（tools）
    // 参数：
    //   - url：传入的参数（含义结合调用处与函数体）
    //   - name：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function download(url, name) {
        //> 声明变量「a」（a），用于保存对应数据，保存 DOM/窗口相关对象
        var a = document.createElement('a'); a.href = url; a.download = name || '';
        //> 把子节点追加到当前元素内部末尾
        document.body.appendChild(a); a.click(); a.remove();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    //> 声明变量「body」（body），用于保存对应数据，保存 DOM/窗口相关对象
    var body = document.getElementById('article-body');

    /* ---------- G1 代码行号 / G2 折叠 ---------- */
    //> 条件判断：满足括号内条件时执行对应分支
    if (body) {
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        body.querySelectorAll('pre').forEach(function (pre) {
            //> 声明变量「wrap」（wrap），用于保存对应数据，保存 DOM/窗口相关对象
            var wrap = document.createElement('div');
            //> 给「wrap.className」赋值，更新其保存的状态
            wrap.className = 'code-block-wrap';
            //> 把子节点追加到当前元素内部末尾
            pre.parentNode.insertBefore(wrap, pre); wrap.appendChild(pre);
            // 行号
            //> 声明变量「code」（code），用于保存对应数据
            var code = pre.querySelector('code');
            //> 声明变量「lines」（lines），用于保存对应数据
            var lines = code ? code.textContent.split('\n').length : pre.textContent.split('\n').length;
            //> 条件判断：满足括号内条件时执行对应分支
            if (lines > 3) {
                //> 为元素添加一个或多个样式类
                pre.classList.add('has-line-numbers');
                //> 声明变量「num」（num），用于保存对应数据，保存 DOM/窗口相关对象
                var num = document.createElement('span');
                //> 给「num.className」赋值，更新其保存的状态
                num.className = 'line-num';
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                num.textContent = Array.from({ length: lines }, function (_, i) { return i + 1; }).join('\n');
                //> 把子节点追加到当前元素内部末尾
                pre.appendChild(num);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            // 折叠按钮
            //> 声明变量「fold」（fold），用于保存对应数据，保存 DOM/窗口相关对象
            var fold = document.createElement('button');
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            fold.className = 'code-fold-toggle'; fold.textContent = '折叠 ▴';
            // =========================================================
            // 【函数】setFolded
            // 功能：设置「folded」相关逻辑（set folded）
            // 参数：
            //   - folded：传入的参数（含义结合调用处与函数体）
            // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
            // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
            // =========================================================
            function setFolded(folded) {
                //> 切换样式类（有则移除、无则添加），可传第二参强制状态
                wrap.classList.toggle('folded', folded);
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                fold.textContent = folded ? '展开 ▾' : '折叠 ▴';
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            fold.addEventListener('click', function (e) {
                //> 阻止事件继续向上冒泡
                e.stopPropagation();
                //> 判断元素是否含有指定样式类，返回布尔值
                setFolded(!wrap.classList.contains('folded'));
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            // 工单9：折叠状态下点击代码预览区（含“点击展开”提示）也可直接展开
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            pre.addEventListener('click', function () {
                //> 条件判断：满足括号内条件时执行对应分支
                if (wrap.classList.contains('folded')) setFolded(false);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            //> 把子节点追加到当前元素内部末尾
            wrap.appendChild(fold);
            // 语法高亮
            // if (code) { highlightCode(code, pre); }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- 轻量级语法高亮（支持 Python/JS/HTML/CSS/Bash） ---------- */
    // =========================================================
    // 【函数】highlightCode
    // 功能：高亮「code」相关逻辑（highlight code）
    // 参数：
    //   - codeEl：传入的参数（含义结合调用处与函数体）
    //   - preEl：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function highlightCode(codeEl, preEl) {
        //> 声明变量「text」（text），用于保存对应数据
        var text = codeEl.textContent;
        //> 声明变量「lang」（lang），用于保存对应数据，初始为字符串
        var lang = '';
        //> 声明变量「cls」（cls），用于保存对应数据，值为一个函数
        var cls = (codeEl.className || '') + ' ' + (preEl.className || '');
        //> 条件判断：满足括号内条件时执行对应分支
        if (/language-(\w+)/.test(cls)) lang = RegExp.$1.toLowerCase();
        //> 否则若满足该条件则进入此分支
        else if (/python|py/.test(cls)) lang = 'python';
        //> 否则若满足该条件则进入此分支
        else if (/javascript|js/.test(cls)) lang = 'javascript';
        //> 否则若满足该条件则进入此分支
        else if (/html|xml/.test(cls)) lang = 'html';
        //> 否则若满足该条件则进入此分支
        else if (/css/.test(cls)) lang = 'css';
        //> 否则若满足该条件则进入此分支
        else if (/bash|shell|sh/.test(cls)) lang = 'bash';
        //> 以上条件都不满足时执行的兜底分支
        else {
            //> 条件判断：满足括号内条件时执行对应分支
            if (/^\s*(import |from |def |class |print\()/m.test(text)) lang = 'python';
            //> 否则若满足该条件则进入此分支
            else if (/^\s*(const |let |var |function |=>)/m.test(text)) lang = 'javascript';
            //> 否则若满足该条件则进入此分支
            else if (/^\s*</m.test(text)) lang = 'html';
            //> 否则若满足该条件则进入此分支
            else if (/^\s*(\.|#|@media|@keyframes)/m.test(text)) lang = 'css';
            //> 否则若满足该条件则进入此分支
            else if (/^\s*(#!|echo |cd |ls |grep )/m.test(text)) lang = 'bash';
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 声明变量「highlighted」（highlighted），用于保存对应数据，初始为字符串
        var highlighted = '';
        //> 条件判断：满足括号内条件时执行对应分支
        if (lang === 'python') highlighted = hlPython(text);
        //> 否则若满足该条件则进入此分支
        else if (lang === 'javascript') highlighted = hlJS(text);
        //> 否则若满足该条件则进入此分支
        else if (lang === 'html') highlighted = hlHTML(text);
        //> 否则若满足该条件则进入此分支
        else if (lang === 'css') highlighted = hlCSS(text);
        //> 否则若满足该条件则进入此分支
        else if (lang === 'bash') highlighted = hlBash(text);
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        else highlighted = hlGeneric(text);
        //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
        codeEl.innerHTML = highlighted;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // =========================================================
    // 【函数】esc
    // 功能：处理「esc」相关逻辑（tools）
    // 参数：
    //   - s：传入的参数（含义结合调用处与函数体）
    // 返回：函数体内有 return，返回对应结果
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function esc(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
    // =========================================================
    // 【函数】wrapTok
    // 功能：处理「wrap tok」相关逻辑（tools）
    // 参数：
    //   - cls：传入的参数（含义结合调用处与函数体）
    //   - text：传入的参数（含义结合调用处与函数体）
    // 返回：函数体内有 return，返回对应结果
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function wrapTok(cls, text) { return '<span class="tok-' + cls + '">' + text + '</span>'; }
    // =========================================================
    // 【函数】hlPython
    // 功能：处理「hl python」相关逻辑（tools）
    // 参数：
    //   - text：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function hlPython(text) {
        //> 声明变量「kws」（kws），用于保存对应数据，初始为字符串
        var kws = '\\b(import|from|def|class|return|if|elif|else|for|while|in|not|and|or|is|None|True|False|try|except|finally|with|as|lambda|yield|global|nonlocal|pass|break|continue|raise|assert|del|async|await)\\b';
        //> 声明变量「builtins」（builtins），用于保存对应数据，初始为字符串
        var builtins = '\\b(print|len|range|str|int|float|list|dict|set|tuple|bool|type|isinstance|hasattr|getattr|setattr|open|input|enumerate|zip|map|filter|sorted|reversed|sum|min|max|abs|round|format|super|self|cls)\\b';
        //> 返回结果并结束当前函数
        return esc(text)
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/("""[\s\S]*?"""|'''[\s\S]*?'''|"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')/g, function(m){ return wrapTok('string', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/(#[^\n]*)/g, function(m){ return wrapTok('comment', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/(@\w+)/g, function(m){ return wrapTok('decorator', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(new RegExp(kws, 'g'), function(m){ return wrapTok('keyword', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(new RegExp(builtins, 'g'), function(m){ return wrapTok('builtin', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/\b(\d+\.?\d*)\b/g, function(m){ return wrapTok('number', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/\b([A-Z]\w*)\b/g, function(m){ return wrapTok('class', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/(\w+)(?=\()/g, function(m){ return wrapTok('function', m); });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // =========================================================
    // 【函数】hlJS
    // 功能：处理「hl js」相关逻辑（tools）
    // 参数：
    //   - text：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function hlJS(text) {
        //> 声明变量「kws」（kws），用于保存对应数据，初始为字符串
        var kws = '\\b(const|let|var|function|return|if|else|for|while|do|switch|case|break|continue|new|class|extends|super|this|import|export|from|default|try|catch|finally|throw|typeof|instanceof|in|of|async|await|yield|void|delete|true|false|null|undefined)\\b';
        //> 声明变量「builtins」（builtins），用于保存对应数据，初始为字符串
        var builtins = '\\b(console|document|window|Math|JSON|Array|Object|String|Number|Boolean|Promise|Map|Set|Date|RegExp|Error|fetch|setTimeout|setInterval|addEventListener|querySelector|querySelectorAll|getElementById)\\b';
        //> 返回结果并结束当前函数
        return esc(text)
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|`(?:[^`\\]|\\.)*`)/g, function(m){ return wrapTok('string', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/(\/\/[^\n]*|\/\*[\s\S]*?\*\/)/g, function(m){ return wrapTok('comment', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(new RegExp(kws, 'g'), function(m){ return wrapTok('keyword', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(new RegExp(builtins, 'g'), function(m){ return wrapTok('builtin', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/\b(\d+\.?\d*)\b/g, function(m){ return wrapTok('number', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/(\w+)(?=\()/g, function(m){ return wrapTok('function', m); });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // =========================================================
    // 【函数】hlHTML
    // 功能：处理「hl html」相关逻辑（tools）
    // 参数：
    //   - text：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function hlHTML(text) {
        //> 返回结果并结束当前函数
        return esc(text)
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/(&lt;!--[\s\S]*?--&gt;)/g, function(m){ return wrapTok('comment', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/(&lt;\/?[\w-]+)/g, function(m){ return wrapTok('tag', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/(\w+)=("[^"]*"|'[^']*')/g, function(m, attr, val){ return wrapTok('attr', attr) + '=' + wrapTok('string', val); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/(&gt;)/g, function(m){ return wrapTok('tag', m); });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // =========================================================
    // 【函数】hlCSS
    // 功能：处理「hl css」相关逻辑（tools）
    // 参数：
    //   - text：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function hlCSS(text) {
        //> 返回结果并结束当前函数
        return esc(text)
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/(\/\*[\s\S]*?\*\/)/g, function(m){ return wrapTok('comment', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/(@[\w-]+)/g, function(m){ return wrapTok('keyword', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/([.#]?[\w-]+)(?=\s*\{)/g, function(m){ return wrapTok('selector', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/([\w-]+)(?=\s*:)/g, function(m){ return wrapTok('attr', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/(#[0-9a-fA-F]{3,8}|\d+\.?\d*(?:px|em|rem|%|vh|vw|s|ms|deg)?)/g, function(m){ return wrapTok('number', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')/g, function(m){ return wrapTok('string', m); });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // =========================================================
    // 【函数】hlBash
    // 功能：处理「hl bash」相关逻辑（tools）
    // 参数：
    //   - text：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function hlBash(text) {
        //> 声明变量「kws」（kws），用于保存对应数据，初始为字符串
        var kws = '\\b(echo|cd|ls|grep|sed|awk|cat|touch|mkdir|rm|cp|mv|chmod|chown|sudo|apt|pip|python|node|npm|git|curl|wget|tar|zip|unzip|find|xargs|export|source|alias|if|then|else|fi|for|do|done|while|case|esac|function)\\b';
        //> 返回结果并结束当前函数
        return esc(text)
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')/g, function(m){ return wrapTok('string', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/(#[^\n]*)/g, function(m){ return wrapTok('comment', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/(\$\w+|\$\{[^}]+\})/g, function(m){ return wrapTok('variable', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(new RegExp(kws, 'g'), function(m){ return wrapTok('keyword', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/\b(\d+\.?\d*)\b/g, function(m){ return wrapTok('number', m); });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // =========================================================
    // 【函数】hlGeneric
    // 功能：处理「hl generic」相关逻辑（tools）
    // 参数：
    //   - text：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function hlGeneric(text) {
        //> 返回结果并结束当前函数
        return esc(text)
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')/g, function(m){ return wrapTok('string', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/(\/\/[^\n]*|#[^\n]*|\/\*[\s\S]*?\*\/)/g, function(m){ return wrapTok('comment', m); })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .replace(/\b(\d+\.?\d*)\b/g, function(m){ return wrapTok('number', m); });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- G3 导出 PDF（前端 jsPDF + html2canvas，彻底解决中文乱码） ----------
     * 第6轮重构：原方案调后端 xhtml2pdf 接口，中文字形缺失导致 PDF 乱码；
     * 改为前端 html2canvas 截图正文 → jsPDF 嵌入图片，中文以像素渲染，100% 还原。
     * 同时兼容 [data-export-pdf] 属性按钮和详情页 #export-pdf-btn（无 data 属性）。
     */
    // =========================================================
    // 【函数】exportArticlePDF
    // 功能：导出「article pdf」相关逻辑（export article pdf）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function exportArticlePDF() {
        //> 声明变量「target」（target），用于保存对应数据
        var target = body || document.getElementById('article-body') || document.querySelector('.article-body');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!target) { toast('未找到文章正文喵~'); return; }
        //> 条件判断：满足括号内条件时执行对应分支
        if (typeof html2canvas === 'undefined' || typeof jspdf === 'undefined') {
            //> 调用函数「toast」并传入参数执行对应逻辑
            toast('PDF 组件加载中，请稍后再试喵~'); return;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 调用函数「toast」并传入参数执行对应逻辑
        toast('正在生成 PDF，请稍候喵~');
        //> 声明变量「title」（title），用于保存对应数据，值为一个函数
        var title = (document.title || 'article').replace(/[^\w\u4e00-\u9fff-]+/g, '_').slice(0, 60);
        /* 克隆正文到屏外，固定宽度 720px 便于 A4 排版 */
        //> 声明变量「clone」（clone），用于保存对应数据
        var clone = target.cloneNode(true);
        //> 给「clone.style.cssText」赋值，更新其保存的状态
        clone.style.cssText = 'width:720px;padding:24px;background:#fff;color:#2b2340;'
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            + 'position:absolute;left:-9999px;top:0;z-index:-1;line-height:1.7;';
        //> 把子节点追加到当前元素内部末尾
        document.body.appendChild(clone);
        //> 调用函数「html2canvas」并传入参数执行对应逻辑
        html2canvas(clone, { scale: 2, useCORS: true, backgroundColor: '#ffffff', logging: false })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .then(function (canvas) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (clone.parentNode) document.body.removeChild(clone);
                //> 声明变量「jsPDF」（js pdf），用于保存对应数据
                var jsPDF = jspdf.jsPDF;
                //> 声明变量「pdf」（pdf），用于保存对应数据
                var pdf = new jsPDF('p', 'mm', 'a4');
                //> 声明变量「pageW」（page w），用于保存对应数据
                var pageW = 210, pageH = 297, margin = 10;
                //> 声明变量「imgW」（img w），用于保存对应数据
                var imgW = pageW - margin * 2;
                //> 声明变量「imgH」（img h），用于保存对应数据
                var imgH = canvas.height * imgW / canvas.width;
                //> 声明变量「imgData」（img data），用于保存对应数据
                var imgData = canvas.toDataURL('image/png');
                //> 声明变量「heightLeft」（height left），用于保存对应数据
                var heightLeft = imgH, pos = margin;
                //> 操作「pdf」的相关方法/属性
                pdf.addImage(imgData, 'PNG', margin, pos, imgW, imgH);
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                heightLeft -= (pageH - margin * 2);
                //> 当条件为真时反复执行循环体
                while (heightLeft > 0) {
                    //> 给「pos」赋值，更新其保存的状态
                    pos = margin - (imgH - heightLeft);
                    //> 操作「pdf」的相关方法/属性
                    pdf.addPage();
                    //> 操作「pdf」的相关方法/属性
                    pdf.addImage(imgData, 'PNG', margin, pos, imgW, imgH);
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    heightLeft -= (pageH - margin * 2);
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
                //> 操作「pdf」的相关方法/属性
                pdf.save(title + '.pdf');
                //> 调用函数「toast」并传入参数执行对应逻辑
                toast('PDF 导出成功喵~');
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .catch(function (err) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (clone.parentNode) document.body.removeChild(clone);
                //> 向控制台输出调试信息（生产环境应精简）
                console.error('PDF export error:', err);
                //> 调用函数「toast」并传入参数执行对应逻辑
                toast('PDF 导出失败喵~，请重试');
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
    document.querySelectorAll('[data-export-pdf]').forEach(function (btn) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        btn.addEventListener('click', exportArticlePDF);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
    //> 声明变量「_pdfBtn」（pdf btn），用于保存对应数据，保存 DOM/窗口相关对象
    var _pdfBtn = document.getElementById('export-pdf-btn');
    //> 条件判断：满足括号内条件时执行对应分支
    if (_pdfBtn) _pdfBtn.addEventListener('click', exportArticlePDF);

    /* ---------- G4 导出 Markdown ---------- */
    //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
    document.querySelectorAll('[data-export-md]').forEach(function (btn) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        btn.addEventListener('click', function () {
            //> 声明变量「md」（md），用于保存对应数据
            var md = body ? body.innerText : document.body.innerText;
            //> 声明变量「blob」（blob），用于保存对应数据
            var blob = new Blob(['# ' + (document.title || '') + '\n\n' + md], { type: 'text/markdown' });
            //> 声明变量「url」（url），用于保存对应数据
            var url = URL.createObjectURL(blob);
            //> 调用函数「download」并传入参数执行对应逻辑
            download(url, 'article.md'); URL.revokeObjectURL(url);
            //> 调用函数「toast」并传入参数执行对应逻辑
            toast('已导出 Markdown~');
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- G5 分享卡片 Canvas ---------- */
    //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
    document.querySelectorAll('[data-share-card]').forEach(function (btn) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        btn.addEventListener('click', function () {
            //> 声明变量「c」（c），用于保存对应数据，保存 DOM/窗口相关对象
            var c = document.createElement('canvas'); c.width = 600; c.height = 800;
            //> 声明变量「ctx」（ctx），用于保存对应数据
            var ctx = c.getContext('2d');
            //> 给「ctx.fillStyle」赋值，更新其保存的状态
            ctx.fillStyle = '#f4f2fb'; ctx.fillRect(0, 0, 600, 800);
            //> 声明变量「grad」（grad），用于保存对应数据
            var grad = ctx.createLinearGradient(0, 0, 600, 200);
            //> 操作「grad」的相关方法/属性
            grad.addColorStop(0, '#ff8fb1'); grad.addColorStop(.5, '#a06cd5'); grad.addColorStop(1, '#6ea8fe');
            //> 给「ctx.fillStyle」赋值，更新其保存的状态
            ctx.fillStyle = grad; ctx.fillRect(0, 0, 600, 220);
            //> 给「ctx.fillStyle」赋值，更新其保存的状态
            ctx.fillStyle = '#fff'; ctx.font = 'bold 34px sans-serif';
            //> 操作「ctx」的相关方法/属性
            ctx.fillText(document.title.slice(0, 20), 40, 130);
            //> 给「ctx.fillStyle」赋值，更新其保存的状态
            ctx.fillStyle = '#2b2340'; ctx.font = '18px sans-serif';
            //> 操作「ctx」的相关方法/属性
            ctx.fillText((body ? body.innerText : '').slice(0, 120), 40, 300);
            //> 操作「ctx」的相关方法/属性
            ctx.fillText('长按保存图片分享~', 40, 740);
            //> 声明变量「mask」（mask），用于保存对应数据，保存 DOM/窗口相关对象
            var mask = document.createElement('div'); mask.className = 'share-card-modal-mask';
            //> 声明变量「img」（img），用于保存对应数据
            var img = new Image(); img.src = c.toDataURL('image/png');
            //> 给「img.className」赋值，更新其保存的状态
            img.className = 'share-card-canvas';
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            mask.appendChild(img); mask.addEventListener('click', function () { mask.remove(); });
            //> 把子节点追加到当前元素内部末尾
            document.body.appendChild(mask);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- G6 二维码 ---------- */
    //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
    document.querySelectorAll('[data-qrcode-url]').forEach(function (btn) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        btn.addEventListener('click', function () {
            //> 声明变量「url」（url），用于保存对应数据，初始为字符串
            var url = 'https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=' +
                //> 读取元素的 HTML 属性值
                encodeURIComponent(btn.getAttribute('data-qrcode-url') || location.href);
            //> 声明变量「mask」（mask），用于保存对应数据，保存 DOM/窗口相关对象
            var mask = document.createElement('div'); mask.className = 'share-card-modal-mask';
            //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
            mask.innerHTML = '<div class="qrcode-box"><img src="' + url + '" alt="qrcode"><p>扫描二维码访问</p></div>';
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            mask.addEventListener('click', function () { mask.remove(); });
            //> 把子节点追加到当前元素内部末尾
            document.body.appendChild(mask);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- G7 短链接 ---------- */
    //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
    document.querySelectorAll('[data-shorten]').forEach(function (btn) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        btn.addEventListener('click', function () {
            //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
            fetch('/api/short_link/', {
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                method: 'POST',
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
                //> 把 JS 数据序列化为 JSON 字符串
                body: JSON.stringify({ url: location.href }), credentials: 'same-origin'
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }).then(function (r) { return r.json(); }).then(function (d) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (d.short_url) { toast('短链接已复制~'); navigator.clipboard && navigator.clipboard.writeText(d.short_url); }
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }).catch(function () { toast('短链接生成失败'); });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
    // =========================================================
    // 【函数】getCookie
    // 功能：获取「cookie」相关逻辑（get cookie）
    // 参数：
    //   - n：传入的参数（含义结合调用处与函数体）
    // 返回：函数体内有 return，返回对应结果
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function getCookie(n) { var m = document.cookie.match(new RegExp('(^| )' + n + '=([^;]*)(;|$)')); return m ? decodeURIComponent(m[2]) : null; }

    /* ---------- G8 全文复制 ---------- */
    //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
    document.querySelectorAll('[data-copy-all]').forEach(function (btn) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        btn.addEventListener('click', function () {
            //> 声明变量「text」（text），用于保存对应数据
            var text = body ? body.innerText : document.body.innerText;
            //> 读取浏览器/设备信息（如 userAgent、剪贴板、地理）
            (navigator.clipboard ? navigator.clipboard.writeText(text) :
                //> 操作「Promise」的相关方法/属性
                Promise.reject()).then(function () { toast('全文已复制~'); })
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                .catch(function () {
                    //> 声明变量「ta」（ta），用于保存对应数据，保存 DOM/窗口相关对象
                    var ta = document.createElement('textarea'); ta.value = text;
                    //> 把子节点追加到当前元素内部末尾
                    document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove();
                    //> 调用函数「toast」并传入参数执行对应逻辑
                    toast('全文已复制~');
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- G9 目录导出大纲 ---------- */
    //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
    document.querySelectorAll('[data-export-outline]').forEach(function (btn) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        btn.addEventListener('click', function () {
            //> 声明变量「hs」（hs），用于保存对应数据，保存 DOM/窗口相关对象
            var hs = document.querySelectorAll('#article-body h2, #article-body h3');
            //> 声明变量「lines」（lines），用于保存对应数据
            var lines = ['# 文章大纲'];
            //> 遍历数组/类数组中的每一项并执行回调
            hs.forEach(function (h) {
                //> 声明变量「prefix」（prefix），用于保存对应数据
                var prefix = h.tagName === 'H2' ? '## ' : '### ';
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                lines.push(prefix + h.textContent);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            //> 声明变量「blob」（blob），用于保存对应数据
            var blob = new Blob([lines.join('\n')], { type: 'text/markdown' });
            //> 声明变量「url」（url），用于保存对应数据
            var url = URL.createObjectURL(blob); download(url, 'outline.md'); URL.revokeObjectURL(url);
            //> 调用函数「toast」并传入参数执行对应逻辑
            toast('大纲已导出~');
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- G10 正文图片批量下载 ---------- */
    //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
    document.querySelectorAll('[data-download-images]').forEach(function (btn) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        btn.addEventListener('click', function () {
            //> 声明变量「imgs」（imgs），用于保存对应数据
            var imgs = body ? body.querySelectorAll('img') : [];
            //> 条件判断：满足括号内条件时执行对应分支
            if (!imgs.length) { toast('没有图片~'); return; }
            //> 声明变量「bar」（bar），用于保存对应数据，保存 DOM/窗口相关对象
            var bar = document.createElement('div'); bar.className = 'download-progress';
            //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
            bar.innerHTML = '下载图片 <span class="dp-n">0/' + imgs.length + '</span><div class="dp-bar"><div class="dp-fill"></div></div>';
            //> 把子节点追加到当前元素内部末尾
            document.body.appendChild(bar);
            //> 操作「Array.prototype.forEach」的相关方法/属性
            Array.prototype.forEach.call(imgs, function (img, i) {
                //> 声明变量「a」（a），用于保存对应数据，保存 DOM/窗口相关对象
                var a = document.createElement('a');
                //> 给「a.href」赋值，更新其保存的状态
                a.href = img.src; a.download = 'img_' + (i + 1) + '.jpg';
                //> 把子节点追加到当前元素内部末尾
                document.body.appendChild(a); a.click(); a.remove();
                //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
                bar.querySelector('.dp-n').textContent = (i + 1) + '/' + imgs.length;
                //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
                bar.querySelector('.dp-fill').style.width = ((i + 1) / imgs.length * 100) + '%';
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            //> 把元素从 DOM 中移除
            setTimeout(function () { bar.remove(); }, 2500);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- Bug7: 导出/更多 下拉菜单开合 ---------- */
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    (function () {
        //> 声明变量「wrap」（wrap），用于保存对应数据，保存 DOM/窗口相关对象
        var wrap = document.getElementById('export-dropdown');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!wrap) return;
        //> 声明变量「toggle」（toggle），用于保存对应数据
        var toggle = wrap.querySelector('.export-toggle');
        //> 声明变量「menu」（menu），用于保存对应数据
        var menu = wrap.querySelector('.export-menu');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!toggle || !menu) return;
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
            //> 设置元素的 HTML 属性
            toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        toggle.addEventListener('click', function (e) { e.stopPropagation(); setOpen(menu.hidden); });
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        menu.addEventListener('click', function () { setOpen(false); });
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('click', function (e) { if (!wrap.contains(e.target)) setOpen(false); });
        //> 绑定「keydown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setOpen(false); });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    })();

    /* ---------- 记录最近浏览（供 D8/F4 使用） ---------- */
    //> 尝试执行可能出错的代码，出错则进入 catch
    try {
        //> 声明变量「views」（views），用于保存对应数据
        var views = JSON.parse(localStorage.getItem('recent_views') || '[]');
        //> 声明变量「entry」（entry），用于保存对应数据
        var entry = { url: location.href, title: document.title, time: new Date().toLocaleString() };
        //> 按条件筛选元素，返回满足条件的新数组
        views = views.filter(function (v) { return v.url !== entry.url; });
        //> 操作「views」的相关方法/属性
        views.unshift(entry); views = views.slice(0, 30);
        //> 操作 localStorage（持久化本地存储），注意容量与解析异常
        localStorage.setItem('recent_views', JSON.stringify(views));
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    } catch (e) {}
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

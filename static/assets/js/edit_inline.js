/* Bug11 文件头注释
 * 编辑页内联脚本：封面选择、标签辅助、字数统计与表单校验的前端逻辑。
 * 配合系列封面选择器 initCoverPicker，提升发文/编辑体验。
 */
/* ===== 4. 编辑页实时字数统计 + 5. 实时预览弹窗 ===== */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';
    //> 声明变量「titleInput」（title input），用于保存对应数据，保存 DOM/窗口相关对象
    var titleInput = document.getElementById('id_title');
    //> 声明变量「contentTA」（content ta），用于保存对应数据，保存 DOM/窗口相关对象
    var contentTA = document.getElementById('id_content');
    //> 声明变量「titleNum」（title num），用于保存对应数据，保存 DOM/窗口相关对象
    var titleNum = document.getElementById('title-wc-num');
    //> 声明变量「titleWc」（title wc），用于保存对应数据，保存 DOM/窗口相关对象
    var titleWc = document.getElementById('title-wc');
    //> 声明变量「contentNum」（content num），用于保存对应数据，保存 DOM/窗口相关对象
    var contentNum = document.getElementById('content-wc-num');
    //> 声明变量「contentMin」（content min），用于保存对应数据，保存 DOM/窗口相关对象
    var contentMin = document.getElementById('content-wc-min');
    /* 统计正文字数：中文字符按 1，英文单词按 1（与后端 word_count 口径一致） */
    // =========================================================
    // 【函数】countWords
    // 功能：处理「count words」相关逻辑（edit_inline）
    // 参数：
    //   - html：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function countWords(html) {
        //> 声明变量「tmp」（tmp），用于保存对应数据，保存 DOM/窗口相关对象
        var tmp = document.createElement('div');
        //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
        tmp.innerHTML = html || '';
        //> 声明变量「text」（text），用于保存对应数据，值为一个函数
        var text = (tmp.textContent || '').replace(/\s+/g, ' ').trim();
        //> 声明变量「cn」（cn），用于保存对应数据，值为一个函数
        var cn = (text.match(/[\u4e00-\u9fff]/g) || []).length;
        //> 声明变量「en」（en），用于保存对应数据，值为一个函数
        var en = (text.match(/[a-zA-Z0-9]+/g) || []).length;
        //> 返回结果并结束当前函数
        return cn + en;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    /* 更新标题字数（>200 变红） */
    // =========================================================
    // 【函数】updateTitle
    // 功能：更新「title」相关逻辑（update title）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function updateTitle() {
        //> 声明变量「n」（n），用于保存对应数据，值为一个函数
        var n = (titleInput.value || '').length;
        //> 读写纯文本内容，不解析 HTML，可防 XSS
        titleNum.textContent = n;
        //> 条件判断：满足括号内条件时执行对应分支
        if (n > 200) { titleWc.classList.add('wc-over'); } else { titleWc.classList.remove('wc-over'); }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    /* 更新正文字数与预计阅读时长（300字/分） */
    // =========================================================
    // 【函数】updateContent
    // 功能：更新「content」相关逻辑（update content）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function updateContent() {
        //> 声明变量「html」（html），用于保存对应数据，初始为字符串
        var html = '';
        // 优先取 CKEditor 实例内容（编辑器替换 textarea 后），兜底取 textarea 值
        //> 条件判断：满足括号内条件时执行对应分支
        if (window.CKEDITOR && CKEDITOR.instances.id_content) {
            //> 给「html」赋值，更新其保存的状态
            html = CKEDITOR.instances.id_content.getData();
        //> 以上条件都不满足时执行的兜底分支
        } else {
            //> 给「html」赋值，更新其保存的状态
            html = contentTA.value;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 声明变量「wc」（wc），用于保存对应数据
        var wc = countWords(html);
        //> 读写纯文本内容，不解析 HTML，可防 XSS
        contentNum.textContent = wc;
        //> 读写纯文本内容，不解析 HTML，可防 XSS
        contentMin.textContent = Math.max(1, Math.round(wc / 300));
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    //> 条件判断：满足括号内条件时执行对应分支
    if (titleInput) titleInput.addEventListener('input', updateTitle);
    /* CKEditor 内容变化：监听 change 事件；兜底用定时器每 2 秒刷新一次 */
    // =========================================================
    // 【函数】bindEditor
    // 功能：绑定「editor」相关逻辑（bind editor）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function bindEditor() {
        //> 条件判断：满足括号内条件时执行对应分支
        if (window.CKEDITOR && CKEDITOR.instances.id_content) {
            //> 操作「CKEDITOR.instances.id_content」的相关方法/属性
            CKEDITOR.instances.id_content.on('change', updateContent);
            //> 调用函数「updateContent」并传入参数执行对应逻辑
            updateContent();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    //> 条件判断：满足括号内条件时执行对应分支
    if (window.CKEDITOR) {
        //> 操作「CKEDITOR」的相关方法/属性
        CKEDITOR.on('instanceReady', function () { bindEditor(); });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    //> 设置按间隔重复执行的定时器，记得 clearInterval 停止
    setInterval(updateContent, 2000);   // 兜底定时刷新
    //> 调用函数「updateTitle」并传入参数执行对应逻辑
    updateTitle();
    /* ===== 5. 预览弹窗：读取当前表单值动态渲染 ===== */
    //> 声明变量「mask」（mask），用于保存对应数据，保存 DOM/窗口相关对象
    var mask = document.getElementById('preview-modal');
    //> 声明变量「openBtn」（open btn），用于保存对应数据，保存 DOM/窗口相关对象
    var openBtn = document.getElementById('preview-btn');
    //> 声明变量「closeBtn」（close btn），用于保存对应数据，保存 DOM/窗口相关对象
    var closeBtn = document.getElementById('preview-close');
    //> 声明变量「pvTitle」（pv title），用于保存对应数据，保存 DOM/窗口相关对象
    var pvTitle = document.getElementById('preview-title');
    //> 声明变量「pvContent」（pv content），用于保存对应数据，保存 DOM/窗口相关对象
    var pvContent = document.getElementById('preview-content');
    // =========================================================
    // 【函数】openPreview
    // 功能：打开「preview」相关逻辑（open preview）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function openPreview() {
        //> 读写纯文本内容，不解析 HTML，可防 XSS
        pvTitle.textContent = titleInput.value.trim() || '（未输入标题）';
        //> 声明变量「html」（html），用于保存对应数据，初始为字符串
        var html = '';
        //> 条件判断：满足括号内条件时执行对应分支
        if (window.CKEDITOR && CKEDITOR.instances.id_content) {
            //> 给「html」赋值，更新其保存的状态
            html = CKEDITOR.instances.id_content.getData();
        //> 以上条件都不满足时执行的兜底分支
        } else {
            //> 给「html」赋值，更新其保存的状态
            html = contentTA.value;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
        pvContent.innerHTML = html || '<p class="muted">还没有内容呢~</p>';
        //> 给「mask.hidden」赋值，更新其保存的状态
        mask.hidden = false;
        //> 给「document.body.style.overflow」赋值，更新其保存的状态
        document.body.style.overflow = 'hidden';
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // =========================================================
    // 【函数】closePreview
    // 功能：关闭「preview」相关逻辑（close preview）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function closePreview() { mask.hidden = true; document.body.style.overflow = ''; }
    //> 条件判断：满足括号内条件时执行对应分支
    if (openBtn) openBtn.addEventListener('click', openPreview);
    //> 条件判断：满足括号内条件时执行对应分支
    if (closeBtn) closeBtn.addEventListener('click', closePreview);
    //> 条件判断：满足括号内条件时执行对应分支
    if (mask) mask.addEventListener('click', function (e) { if (e.target === mask) closePreview(); });
    //> 绑定「keydown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    document.addEventListener('keydown', function (e) {
        //> 条件判断：满足括号内条件时执行对应分支
        if (e.key === 'Escape' && !mask.hidden) closePreview();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

/* 工单4：封面选择器——选中文件后把文件名显示在萌系选择器上 */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 声明变量「fi」（fi），用于保存对应数据，保存 DOM/窗口相关对象
    var fi = document.getElementById('id_cover_image');
    //> 声明变量「box」（box），用于保存对应数据，保存 DOM/窗口相关对象
    var box = document.querySelector('.cover-picker');
    //> 声明变量「txt」（txt），用于保存对应数据，保存 DOM/窗口相关对象
    var txt = document.getElementById('cover-picker-text');
    //> 条件判断：满足括号内条件时执行对应分支
    if (fi && txt) {
        //> 绑定「change」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        fi.addEventListener('change', function () {
            //> 条件判断：满足括号内条件时执行对应分支
            if (fi.files && fi.files.length) {
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                txt.textContent = '已选封面：' + fi.files[0].name;
                //> 条件判断：满足括号内条件时执行对应分支
                if (box) box.classList.add('has-file');
            //> 以上条件都不满足时执行的兜底分支
            } else {
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                txt.textContent = '点击选择封面图喵（可选，建议宽幅横图）';
                //> 条件判断：满足括号内条件时执行对应分支
                if (box) box.classList.remove('has-file');
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

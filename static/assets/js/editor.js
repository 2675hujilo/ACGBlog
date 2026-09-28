/* ============================================================================
 * editor.js —— 全站统一富文本编辑器（CKEditor 4 本地构建）
 * ----------------------------------------------------------------------------
 * 能力：图片上传、图文混排（image2）、表格编辑（table + tabletools）、
 *      拖拽调整表格列宽（tableresize）、代码块高亮、源码编辑、从 Word 粘贴。
 *
 * 自动初始化：页面上所有 <textarea class="rich-editor"> 都会被替换为同一套
 *            编辑器，文章 / 笔记 / 独立页面共用配置，保证体验一致。
 *
 * 依赖：全局对象 CKEDITOR（base.html 引入本地 ckeditor.js，不走 CDN）；
 *      编辑区样式由 contentsCss 指向 editor-content.css，做到「编辑即所见」。
 *
 * 注意：图片上传走 /api/upload-image/（需登录 + CSRF）；allowedContent=true
 *      关闭了 CKEditor 自带的内容过滤，真正的净化由后端 html_safety 统一负责。
 * ============================================================================ */
(function () {
    'use strict';

    // CKEditor 核心未加载时直接报错退出，避免后续访问 CKEDITOR.xxx 抛错
    if (typeof CKEDITOR === 'undefined') {
        console.error('CKEditor 静态资源未加载');
        return;
    }

    /* ---------------- 全局默认配置（三类内容共用） ---------------- */

    // 编辑器界面语言：简体中文
    CKEDITOR.config.language = 'zh-cn';
    // 编辑区高度（像素）
    CKEDITOR.config.height = 480;
    // 宽度自适应父容器
    CKEDITOR.config.width = 'auto';

    // 启用的额外插件：图片上传 / 图文混排 / 表格列宽拖拽 / 表格选中 /
    // 代码块 / 源码对话框 / 从 Word 粘贴
    CKEDITOR.config.extraPlugins =
        'uploadimage,image2,tableresize,tabletools,tableselection,' +
        'codesnippet,sourcedialog,pastefromword';

    // 移除依赖云端或不需要的插件：easyimage / 云服务 / 导出 PDF / 拼写检查
    CKEDITOR.config.removePlugins =
        'easyimage,cloudservices,exportpdf,scayt,wsc';

    // 关闭编辑器自带 ACF 过滤，允许全部标签 / 属性（净化交给后端）
    CKEDITOR.config.allowedContent = true;

    // 图片上传地址：工具栏与拖拽 / 粘贴图片都 POST 到这里，返回图片 URL
    CKEDITOR.config.filebrowserImageUploadUrl = '/api/upload-image/';
    CKEDITOR.config.uploadUrl = '/api/upload-image/';

    // 编辑区样式表：让编辑时的排版与前台文章一致
    CKEDITOR.config.contentsCss = '/static/assets/css/editor-content.css';
    // 代码块高亮主题（Monokai Sublime 配色）
    CKEDITOR.config.codeSnippet_theme = 'monokai_sublime';

    /*
     * 工具栏分组定义：每个对象是一组，items 为按钮，'-' 为分隔符，
     * 单独的 '/' 表示换行到下一排。
     */
    CKEDITOR.config.toolbar = [
        // 源码编辑 / 预览
        { name: 'document', items: ['Sourcedialog', '-', 'Preview'] },
        // 撤销重做 / 剪切复制 / 纯文本粘贴 / 从 Word 粘贴
        { name: 'clipboard', items: ['Undo', 'Redo', '-', 'Cut', 'Copy',
            'PasteText', 'PasteFromWord'] },
        // 查找替换 / 全选
        { name: 'editing', items: ['Find', 'Replace', '-', 'SelectAll'] },
        // 文字基础样式 / 上下标 / 清除格式
        { name: 'basicstyles', items: ['Bold', 'Italic', 'Underline',
            'Strike', 'Subscript', 'Superscript', '-', 'RemoveFormat'] },
        // 列表 / 缩进 / 引用 / 对齐
        { name: 'paragraph', items: ['NumberedList', 'BulletedList', '-',
            'Outdent', 'Indent', '-', 'Blockquote', '-', 'JustifyLeft',
            'JustifyCenter', 'JustifyRight', 'JustifyBlock'] },
        // 插入：图片 / 表格 / 分隔线 / 表情 / 特殊字符 / 链接 / 代码块
        { name: 'insert', items: ['Image', 'Table', 'HorizontalRule',
            'Smiley', 'SpecialChar', 'Link', 'Unlink', 'CodeSnippet'] },
        // 换行
        '/',
        // 样式 / 格式 / 字体字号 / 文字与背景色
        { name: 'styles', items: ['Styles', 'Format', 'Font', 'FontSize',
            'TextColor', 'BGColor'] },
        // 全屏 / 显示区块
        { name: 'tools', items: ['Maximize', 'ShowBlocks'] }
    ];

    /*
     * 表格对话框默认值：把默认行列设为 3×3，新手插入即可见完整网格。
     * 通过 dialogDefinition 事件改写对话框字段默认值。
     */
    CKEDITOR.on('dialogDefinition', function (ev) {
        // 只处理表格对话框
        if (ev.data.name !== 'table') return;
        // 取 info 标签页
        var info = ev.data.definition.getContents('info');
        // 取行数、列数字段
        var rows = info.get('txtRows');
        var cols = info.get('txtCols');
        // 改写默认值为 3
        if (rows) rows['default'] = '3';
        if (cols) cols['default'] = '3';
    });

    /**
     * 初始化单个 textarea 为 CKEditor 实例。
     * @param {HTMLTextAreaElement} textarea - 待替换的原始文本框。
     */
    function init(textarea) {
        // 防止重复初始化（同一 textarea 多次 replace 会报错）
        if (textarea.dataset.ckInited) return;
        // 打标记
        textarea.dataset.ckInited = '1';
        // 替换为编辑器
        CKEDITOR.replace(textarea, {});
    }

    // 保留 instanceReady 钩子，便于后续按实例做扩展（当前为空）
    CKEDITOR.on('instanceReady', function () {});

    // 替换页面上全部富文本输入框
    document.querySelectorAll('textarea.rich-editor').forEach(init);
})();

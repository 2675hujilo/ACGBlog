/**
 * editor.js —— 全站统一富文本编辑器（CKEditor 4 本地构建）
 * 能力：图片上传 / 图文混排（image2）/ 表格编辑（table+tabletools）/
 *       拖拽调整表格列宽（tableresize）/ 代码块 / 源码编辑。
 * 自动初始化：页面上所有 <textarea class="rich-editor"> 都会被替换为同一套编辑器。
 * 依赖：CKEDITOR 全局对象（由 base.html 引入的本地 ckeditor.js 提供）；
 *       编辑区样式通过 contentsCss 指向 editor-content.css。
 */
(function () {
    'use strict';

    // CKEditor 核心脚本未加载时直接报错退出，避免后续调用报错
    if (typeof CKEDITOR === 'undefined') {
        console.error('CKEditor 静态资源未加载');
        return;
    }

    // ---------- 全局默认配置（文章 / 笔记 / 独立页面共用同一套） ----------
    CKEDITOR.config.language = 'zh-cn';           // 编辑器界面语言：简体中文
    CKEDITOR.config.height = 480;                // 编辑区高度（px）
    CKEDITOR.config.width = 'auto';               // 宽度自适应父容器
    // 额外插件：图片上传/图文混排/表格拖拽列宽/表格选中/代码块/源码编辑/从 Word 粘贴
    CKEDITOR.config.extraPlugins =
        'uploadimage,image2,tableresize,tabletools,tableselection,codesnippet,sourcedialog,pastefromword';
    // easyimage / exportpdf 依赖 CKEditor 云端服务，本地构建中禁用；同时关闭拼写检查
    CKEDITOR.config.removePlugins = 'easyimage,cloudservices,exportpdf,scayt,wsc';
    CKEDITOR.config.allowedContent = true;        // 关闭 ACF 过滤，允许全部 HTML 标签/属性
    // 图片上传接口：拖拽/粘贴图片时 POST 到该地址，返回上传后的图片 URL
    CKEDITOR.config.filebrowserImageUploadUrl = '/api/upload-image/';
    CKEDITOR.config.uploadUrl = '/api/upload-image/';
    // 编辑区内的样式表：让编辑时所见即所得样式与前台文章展示一致（见 editor-content.css）
    CKEDITOR.config.contentsCss = '/static/assets/css/editor-content.css';
    CKEDITOR.config.codeSnippet_theme = 'monokai_sublime';  // 代码块高亮配色主题

    // 工具栏定义：分组排列，"/" 表示换行
    CKEDITOR.config.toolbar = [
        { name: 'document', items: ['Sourcedialog', '-', 'Preview'] },           // 源码编辑 / 预览
        { name: 'clipboard', items: ['Undo', 'Redo', '-', 'Cut', 'Copy', 'PasteText', 'PasteFromWord'] },  // 剪贴板与撤销
        { name: 'editing', items: ['Find', 'Replace', '-', 'SelectAll'] },       // 查找替换
        { name: 'basicstyles', items: ['Bold', 'Italic', 'Underline', 'Strike', 'Subscript', 'Superscript', '-', 'RemoveFormat'] },  // 文字基础样式
        { name: 'paragraph', items: ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-',
            'Blockquote', '-', 'JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock'] },  // 列表/缩进/对齐
        { name: 'insert', items: ['Image', 'Table', 'HorizontalRule', 'Smiley', 'SpecialChar', 'Link', 'Unlink', 'CodeSnippet'] },  // 插入元素
        '/',
        { name: 'styles', items: ['Styles', 'Format', 'Font', 'FontSize', 'TextColor', 'BGColor'] },  // 样式/字体/颜色
        { name: 'tools', items: ['Maximize', 'ShowBlocks'] }                     // 全屏/显示区块
    ];

    // 表格默认属性：插入表格对话框默认 3 行 3 列（表头自带边框，插入即可见网格）
    CKEDITOR.on('dialogDefinition', function (ev) {
        if (ev.data.name !== 'table') return;
        var info = ev.data.definition.getContents('info');
        var rows = info.get('txtRows');
        var cols = info.get('txtCols');
        if (rows) rows['default'] = '3';
        if (cols) cols['default'] = '3';
    });

    /**
     * 初始化单个 textarea 为 CKEditor 实例
     * @param {HTMLTextAreaElement} textarea 待替换的原输入框
     */
    function init(textarea) {
        // 防止重复初始化（同一 textarea 被 replace 多次会报错）
        if (textarea.dataset.ckInited) return;
        textarea.dataset.ckInited = '1';
        CKEDITOR.replace(textarea, {});
    }

    // 占位回调：保留 instanceReady 钩子，便于后续扩展
    CKEDITOR.on('instanceReady', function () {});
    // 替换页面上所有富文本输入框
    document.querySelectorAll('textarea.rich-editor').forEach(init);
})();

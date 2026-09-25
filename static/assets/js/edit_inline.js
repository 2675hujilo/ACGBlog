/* Bug11 文件头注释
 * 编辑页内联脚本：封面选择、标签辅助、字数统计与表单校验的前端逻辑。
 * 配合系列封面选择器 initCoverPicker，提升发文/编辑体验。
 */
/* ===== 4. 编辑页实时字数统计 + 5. 实时预览弹窗 ===== */
(function () {
    'use strict';
    var titleInput = document.getElementById('id_title');
    var contentTA = document.getElementById('id_content');
    var titleNum = document.getElementById('title-wc-num');
    var titleWc = document.getElementById('title-wc');
    var contentNum = document.getElementById('content-wc-num');
    var contentMin = document.getElementById('content-wc-min');
    /* 统计正文字数：中文字符按 1，英文单词按 1（与后端 word_count 口径一致） */
    function countWords(html) {
        var tmp = document.createElement('div');
        tmp.innerHTML = html || '';
        var text = (tmp.textContent || '').replace(/\s+/g, ' ').trim();
        var cn = (text.match(/[\u4e00-\u9fff]/g) || []).length;
        var en = (text.match(/[a-zA-Z0-9]+/g) || []).length;
        return cn + en;
    }
    /* 更新标题字数（>200 变红） */
    function updateTitle() {
        var n = (titleInput.value || '').length;
        titleNum.textContent = n;
        if (n > 200) { titleWc.classList.add('wc-over'); } else { titleWc.classList.remove('wc-over'); }
    }
    /* 更新正文字数与预计阅读时长（300字/分） */
    function updateContent() {
        var html = '';
        // 优先取 CKEditor 实例内容（编辑器替换 textarea 后），兜底取 textarea 值
        if (window.CKEDITOR && CKEDITOR.instances.id_content) {
            html = CKEDITOR.instances.id_content.getData();
        } else {
            html = contentTA.value;
        }
        var wc = countWords(html);
        contentNum.textContent = wc;
        contentMin.textContent = Math.max(1, Math.round(wc / 300));
    }
    if (titleInput) titleInput.addEventListener('input', updateTitle);
    /* CKEditor 内容变化：监听 change 事件；兜底用定时器每 2 秒刷新一次 */
    function bindEditor() {
        if (window.CKEDITOR && CKEDITOR.instances.id_content) {
            CKEDITOR.instances.id_content.on('change', updateContent);
            updateContent();
        }
    }
    if (window.CKEDITOR) {
        CKEDITOR.on('instanceReady', function () { bindEditor(); });
    }
    setInterval(updateContent, 2000);   // 兜底定时刷新
    updateTitle();
    /* ===== 5. 预览弹窗：读取当前表单值动态渲染 ===== */
    var mask = document.getElementById('preview-modal');
    var openBtn = document.getElementById('preview-btn');
    var closeBtn = document.getElementById('preview-close');
    var pvTitle = document.getElementById('preview-title');
    var pvContent = document.getElementById('preview-content');
    function openPreview() {
        pvTitle.textContent = titleInput.value.trim() || '（未输入标题）';
        var html = '';
        if (window.CKEDITOR && CKEDITOR.instances.id_content) {
            html = CKEDITOR.instances.id_content.getData();
        } else {
            html = contentTA.value;
        }
        pvContent.innerHTML = html || '<p class="muted">还没有内容呢~</p>';
        mask.hidden = false;
        document.body.style.overflow = 'hidden';
    }
    function closePreview() { mask.hidden = true; document.body.style.overflow = ''; }
    if (openBtn) openBtn.addEventListener('click', openPreview);
    if (closeBtn) closeBtn.addEventListener('click', closePreview);
    if (mask) mask.addEventListener('click', function (e) { if (e.target === mask) closePreview(); });
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && !mask.hidden) closePreview();
    });
})();

/* 工单4：封面选择器——选中文件后把文件名显示在萌系选择器上 */
(function () {
    var fi = document.getElementById('id_cover_image');
    var box = document.querySelector('.cover-picker');
    var txt = document.getElementById('cover-picker-text');
    if (fi && txt) {
        fi.addEventListener('change', function () {
            if (fi.files && fi.files.length) {
                txt.textContent = '已选封面：' + fi.files[0].name;
                if (box) box.classList.add('has-file');
            } else {
                txt.textContent = '点击选择封面图喵（可选，建议宽幅横图）';
                if (box) box.classList.remove('has-file');
            }
        });
    }
})();

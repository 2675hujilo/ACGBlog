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
(function () {
    'use strict';
    function toast(msg) {
        var t = document.getElementById('global-toast');
        if (!t) { t = document.createElement('div'); t.id = 'global-toast'; document.body.appendChild(t); }
        t.textContent = msg; t.classList.add('show');
        clearTimeout(t._t); t._t = setTimeout(function () { t.classList.remove('show'); }, 1600);
    }
    function download(url, name) {
        var a = document.createElement('a'); a.href = url; a.download = name || '';
        document.body.appendChild(a); a.click(); a.remove();
    }
    var body = document.getElementById('article-body');

    /* ---------- G1 代码行号 / G2 折叠 ---------- */
    if (body) {
        body.querySelectorAll('pre').forEach(function (pre) {
            var wrap = document.createElement('div');
            wrap.className = 'code-block-wrap';
            pre.parentNode.insertBefore(wrap, pre); wrap.appendChild(pre);
            // 行号
            var code = pre.querySelector('code');
            var lines = code ? code.textContent.split('\n').length : pre.textContent.split('\n').length;
            if (lines > 3) {
                pre.classList.add('has-line-numbers');
                var num = document.createElement('span');
                num.className = 'line-num';
                num.textContent = Array.from({ length: lines }, function (_, i) { return i + 1; }).join('\n');
                pre.appendChild(num);
            }
            // 折叠按钮
            var fold = document.createElement('button');
            fold.className = 'code-fold-toggle'; fold.textContent = '折叠 ▴';
            function setFolded(folded) {
                wrap.classList.toggle('folded', folded);
                fold.textContent = folded ? '展开 ▾' : '折叠 ▴';
            }
            fold.addEventListener('click', function (e) {
                e.stopPropagation();
                setFolded(!wrap.classList.contains('folded'));
            });
            // 工单9：折叠状态下点击代码预览区（含“点击展开”提示）也可直接展开
            pre.addEventListener('click', function () {
                if (wrap.classList.contains('folded')) setFolded(false);
            });
            wrap.appendChild(fold);
            // 语法高亮
            // if (code) { highlightCode(code, pre); }
        });
    }

    /* ---------- 轻量级语法高亮（支持 Python/JS/HTML/CSS/Bash） ---------- */
    function highlightCode(codeEl, preEl) {
        var text = codeEl.textContent;
        var lang = '';
        var cls = (codeEl.className || '') + ' ' + (preEl.className || '');
        if (/language-(\w+)/.test(cls)) lang = RegExp.$1.toLowerCase();
        else if (/python|py/.test(cls)) lang = 'python';
        else if (/javascript|js/.test(cls)) lang = 'javascript';
        else if (/html|xml/.test(cls)) lang = 'html';
        else if (/css/.test(cls)) lang = 'css';
        else if (/bash|shell|sh/.test(cls)) lang = 'bash';
        else {
            if (/^\s*(import |from |def |class |print\()/m.test(text)) lang = 'python';
            else if (/^\s*(const |let |var |function |=>)/m.test(text)) lang = 'javascript';
            else if (/^\s*</m.test(text)) lang = 'html';
            else if (/^\s*(\.|#|@media|@keyframes)/m.test(text)) lang = 'css';
            else if (/^\s*(#!|echo |cd |ls |grep )/m.test(text)) lang = 'bash';
        }
        var highlighted = '';
        if (lang === 'python') highlighted = hlPython(text);
        else if (lang === 'javascript') highlighted = hlJS(text);
        else if (lang === 'html') highlighted = hlHTML(text);
        else if (lang === 'css') highlighted = hlCSS(text);
        else if (lang === 'bash') highlighted = hlBash(text);
        else highlighted = hlGeneric(text);
        codeEl.innerHTML = highlighted;
    }
    function esc(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
    function wrapTok(cls, text) { return '<span class="tok-' + cls + '">' + text + '</span>'; }
    function hlPython(text) {
        var kws = '\\b(import|from|def|class|return|if|elif|else|for|while|in|not|and|or|is|None|True|False|try|except|finally|with|as|lambda|yield|global|nonlocal|pass|break|continue|raise|assert|del|async|await)\\b';
        var builtins = '\\b(print|len|range|str|int|float|list|dict|set|tuple|bool|type|isinstance|hasattr|getattr|setattr|open|input|enumerate|zip|map|filter|sorted|reversed|sum|min|max|abs|round|format|super|self|cls)\\b';
        return esc(text)
            .replace(/("""[\s\S]*?"""|'''[\s\S]*?'''|"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')/g, function(m){ return wrapTok('string', m); })
            .replace(/(#[^\n]*)/g, function(m){ return wrapTok('comment', m); })
            .replace(/(@\w+)/g, function(m){ return wrapTok('decorator', m); })
            .replace(new RegExp(kws, 'g'), function(m){ return wrapTok('keyword', m); })
            .replace(new RegExp(builtins, 'g'), function(m){ return wrapTok('builtin', m); })
            .replace(/\b(\d+\.?\d*)\b/g, function(m){ return wrapTok('number', m); })
            .replace(/\b([A-Z]\w*)\b/g, function(m){ return wrapTok('class', m); })
            .replace(/(\w+)(?=\()/g, function(m){ return wrapTok('function', m); });
    }
    function hlJS(text) {
        var kws = '\\b(const|let|var|function|return|if|else|for|while|do|switch|case|break|continue|new|class|extends|super|this|import|export|from|default|try|catch|finally|throw|typeof|instanceof|in|of|async|await|yield|void|delete|true|false|null|undefined)\\b';
        var builtins = '\\b(console|document|window|Math|JSON|Array|Object|String|Number|Boolean|Promise|Map|Set|Date|RegExp|Error|fetch|setTimeout|setInterval|addEventListener|querySelector|querySelectorAll|getElementById)\\b';
        return esc(text)
            .replace(/("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|`(?:[^`\\]|\\.)*`)/g, function(m){ return wrapTok('string', m); })
            .replace(/(\/\/[^\n]*|\/\*[\s\S]*?\*\/)/g, function(m){ return wrapTok('comment', m); })
            .replace(new RegExp(kws, 'g'), function(m){ return wrapTok('keyword', m); })
            .replace(new RegExp(builtins, 'g'), function(m){ return wrapTok('builtin', m); })
            .replace(/\b(\d+\.?\d*)\b/g, function(m){ return wrapTok('number', m); })
            .replace(/(\w+)(?=\()/g, function(m){ return wrapTok('function', m); });
    }
    function hlHTML(text) {
        return esc(text)
            .replace(/(&lt;!--[\s\S]*?--&gt;)/g, function(m){ return wrapTok('comment', m); })
            .replace(/(&lt;\/?[\w-]+)/g, function(m){ return wrapTok('tag', m); })
            .replace(/(\w+)=("[^"]*"|'[^']*')/g, function(m, attr, val){ return wrapTok('attr', attr) + '=' + wrapTok('string', val); })
            .replace(/(&gt;)/g, function(m){ return wrapTok('tag', m); });
    }
    function hlCSS(text) {
        return esc(text)
            .replace(/(\/\*[\s\S]*?\*\/)/g, function(m){ return wrapTok('comment', m); })
            .replace(/(@[\w-]+)/g, function(m){ return wrapTok('keyword', m); })
            .replace(/([.#]?[\w-]+)(?=\s*\{)/g, function(m){ return wrapTok('selector', m); })
            .replace(/([\w-]+)(?=\s*:)/g, function(m){ return wrapTok('attr', m); })
            .replace(/(#[0-9a-fA-F]{3,8}|\d+\.?\d*(?:px|em|rem|%|vh|vw|s|ms|deg)?)/g, function(m){ return wrapTok('number', m); })
            .replace(/("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')/g, function(m){ return wrapTok('string', m); });
    }
    function hlBash(text) {
        var kws = '\\b(echo|cd|ls|grep|sed|awk|cat|touch|mkdir|rm|cp|mv|chmod|chown|sudo|apt|pip|python|node|npm|git|curl|wget|tar|zip|unzip|find|xargs|export|source|alias|if|then|else|fi|for|do|done|while|case|esac|function)\\b';
        return esc(text)
            .replace(/("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')/g, function(m){ return wrapTok('string', m); })
            .replace(/(#[^\n]*)/g, function(m){ return wrapTok('comment', m); })
            .replace(/(\$\w+|\$\{[^}]+\})/g, function(m){ return wrapTok('variable', m); })
            .replace(new RegExp(kws, 'g'), function(m){ return wrapTok('keyword', m); })
            .replace(/\b(\d+\.?\d*)\b/g, function(m){ return wrapTok('number', m); });
    }
    function hlGeneric(text) {
        return esc(text)
            .replace(/("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')/g, function(m){ return wrapTok('string', m); })
            .replace(/(\/\/[^\n]*|#[^\n]*|\/\*[\s\S]*?\*\/)/g, function(m){ return wrapTok('comment', m); })
            .replace(/\b(\d+\.?\d*)\b/g, function(m){ return wrapTok('number', m); });
    }

    /* ---------- G3 导出 PDF（前端 jsPDF + html2canvas，彻底解决中文乱码） ----------
     * 第6轮重构：原方案调后端 xhtml2pdf 接口，中文字形缺失导致 PDF 乱码；
     * 改为前端 html2canvas 截图正文 → jsPDF 嵌入图片，中文以像素渲染，100% 还原。
     * 同时兼容 [data-export-pdf] 属性按钮和详情页 #export-pdf-btn（无 data 属性）。
     */
    function exportArticlePDF() {
        var target = body || document.getElementById('article-body') || document.querySelector('.article-body');
        if (!target) { toast('未找到文章正文喵~'); return; }
        if (typeof html2canvas === 'undefined' || typeof jspdf === 'undefined') {
            toast('PDF 组件加载中，请稍后再试喵~'); return;
        }
        toast('正在生成 PDF，请稍候喵~');
        var title = (document.title || 'article').replace(/[^\w\u4e00-\u9fff-]+/g, '_').slice(0, 60);
        /* 克隆正文到屏外，固定宽度 720px 便于 A4 排版 */
        var clone = target.cloneNode(true);
        clone.style.cssText = 'width:720px;padding:24px;background:#fff;color:#2b2340;'
            + 'position:absolute;left:-9999px;top:0;z-index:-1;line-height:1.7;';
        document.body.appendChild(clone);
        html2canvas(clone, { scale: 2, useCORS: true, backgroundColor: '#ffffff', logging: false })
            .then(function (canvas) {
                if (clone.parentNode) document.body.removeChild(clone);
                var jsPDF = jspdf.jsPDF;
                var pdf = new jsPDF('p', 'mm', 'a4');
                var pageW = 210, pageH = 297, margin = 10;
                var imgW = pageW - margin * 2;
                var imgH = canvas.height * imgW / canvas.width;
                var imgData = canvas.toDataURL('image/png');
                var heightLeft = imgH, pos = margin;
                pdf.addImage(imgData, 'PNG', margin, pos, imgW, imgH);
                heightLeft -= (pageH - margin * 2);
                while (heightLeft > 0) {
                    pos = margin - (imgH - heightLeft);
                    pdf.addPage();
                    pdf.addImage(imgData, 'PNG', margin, pos, imgW, imgH);
                    heightLeft -= (pageH - margin * 2);
                }
                pdf.save(title + '.pdf');
                toast('PDF 导出成功喵~');
            })
            .catch(function (err) {
                if (clone.parentNode) document.body.removeChild(clone);
                console.error('PDF export error:', err);
                toast('PDF 导出失败喵~，请重试');
            });
    }
    document.querySelectorAll('[data-export-pdf]').forEach(function (btn) {
        btn.addEventListener('click', exportArticlePDF);
    });
    var _pdfBtn = document.getElementById('export-pdf-btn');
    if (_pdfBtn) _pdfBtn.addEventListener('click', exportArticlePDF);

    /* ---------- G4 导出 Markdown ---------- */
    document.querySelectorAll('[data-export-md]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var md = body ? body.innerText : document.body.innerText;
            var blob = new Blob(['# ' + (document.title || '') + '\n\n' + md], { type: 'text/markdown' });
            var url = URL.createObjectURL(blob);
            download(url, 'article.md'); URL.revokeObjectURL(url);
            toast('已导出 Markdown~');
        });
    });

    /* ---------- G5 分享卡片 Canvas ---------- */
    document.querySelectorAll('[data-share-card]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var c = document.createElement('canvas'); c.width = 600; c.height = 800;
            var ctx = c.getContext('2d');
            ctx.fillStyle = '#f4f2fb'; ctx.fillRect(0, 0, 600, 800);
            var grad = ctx.createLinearGradient(0, 0, 600, 200);
            grad.addColorStop(0, '#ff8fb1'); grad.addColorStop(.5, '#a06cd5'); grad.addColorStop(1, '#6ea8fe');
            ctx.fillStyle = grad; ctx.fillRect(0, 0, 600, 220);
            ctx.fillStyle = '#fff'; ctx.font = 'bold 34px sans-serif';
            ctx.fillText(document.title.slice(0, 20), 40, 130);
            ctx.fillStyle = '#2b2340'; ctx.font = '18px sans-serif';
            ctx.fillText((body ? body.innerText : '').slice(0, 120), 40, 300);
            ctx.fillText('长按保存图片分享~', 40, 740);
            var mask = document.createElement('div'); mask.className = 'share-card-modal-mask';
            var img = new Image(); img.src = c.toDataURL('image/png');
            img.className = 'share-card-canvas';
            mask.appendChild(img); mask.addEventListener('click', function () { mask.remove(); });
            document.body.appendChild(mask);
        });
    });

    /* ---------- G6 二维码 ---------- */
    document.querySelectorAll('[data-qrcode-url]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var url = 'https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=' +
                encodeURIComponent(btn.getAttribute('data-qrcode-url') || location.href);
            var mask = document.createElement('div'); mask.className = 'share-card-modal-mask';
            mask.innerHTML = '<div class="qrcode-box"><img src="' + url + '" alt="qrcode"><p>扫描二维码访问</p></div>';
            mask.addEventListener('click', function () { mask.remove(); });
            document.body.appendChild(mask);
        });
    });

    /* ---------- G7 短链接 ---------- */
    document.querySelectorAll('[data-shorten]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            fetch('/api/short_link/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
                body: JSON.stringify({ url: location.href }), credentials: 'same-origin'
            }).then(function (r) { return r.json(); }).then(function (d) {
                if (d.short_url) { toast('短链接已复制~'); navigator.clipboard && navigator.clipboard.writeText(d.short_url); }
            }).catch(function () { toast('短链接生成失败'); });
        });
    });
    function getCookie(n) { var m = document.cookie.match(new RegExp('(^| )' + n + '=([^;]*)(;|$)')); return m ? decodeURIComponent(m[2]) : null; }

    /* ---------- G8 全文复制 ---------- */
    document.querySelectorAll('[data-copy-all]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var text = body ? body.innerText : document.body.innerText;
            (navigator.clipboard ? navigator.clipboard.writeText(text) :
                Promise.reject()).then(function () { toast('全文已复制~'); })
                .catch(function () {
                    var ta = document.createElement('textarea'); ta.value = text;
                    document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove();
                    toast('全文已复制~');
                });
        });
    });

    /* ---------- G9 目录导出大纲 ---------- */
    document.querySelectorAll('[data-export-outline]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var hs = document.querySelectorAll('#article-body h2, #article-body h3');
            var lines = ['# 文章大纲'];
            hs.forEach(function (h) {
                var prefix = h.tagName === 'H2' ? '## ' : '### ';
                lines.push(prefix + h.textContent);
            });
            var blob = new Blob([lines.join('\n')], { type: 'text/markdown' });
            var url = URL.createObjectURL(blob); download(url, 'outline.md'); URL.revokeObjectURL(url);
            toast('大纲已导出~');
        });
    });

    /* ---------- G10 正文图片批量下载 ---------- */
    document.querySelectorAll('[data-download-images]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var imgs = body ? body.querySelectorAll('img') : [];
            if (!imgs.length) { toast('没有图片~'); return; }
            var bar = document.createElement('div'); bar.className = 'download-progress';
            bar.innerHTML = '下载图片 <span class="dp-n">0/' + imgs.length + '</span><div class="dp-bar"><div class="dp-fill"></div></div>';
            document.body.appendChild(bar);
            Array.prototype.forEach.call(imgs, function (img, i) {
                var a = document.createElement('a');
                a.href = img.src; a.download = 'img_' + (i + 1) + '.jpg';
                document.body.appendChild(a); a.click(); a.remove();
                bar.querySelector('.dp-n').textContent = (i + 1) + '/' + imgs.length;
                bar.querySelector('.dp-fill').style.width = ((i + 1) / imgs.length * 100) + '%';
            });
            setTimeout(function () { bar.remove(); }, 2500);
        });
    });

    /* ---------- Bug7: 导出/更多 下拉菜单开合 ---------- */
    (function () {
        var wrap = document.getElementById('export-dropdown');
        if (!wrap) return;
        var toggle = wrap.querySelector('.export-toggle');
        var menu = wrap.querySelector('.export-menu');
        if (!toggle || !menu) return;
        function setOpen(open) {
            menu.hidden = !open;
            toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        }
        toggle.addEventListener('click', function (e) { e.stopPropagation(); setOpen(menu.hidden); });
        menu.addEventListener('click', function () { setOpen(false); });
        document.addEventListener('click', function (e) { if (!wrap.contains(e.target)) setOpen(false); });
        document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setOpen(false); });
    })();

    /* ---------- 记录最近浏览（供 D8/F4 使用） ---------- */
    try {
        var views = JSON.parse(localStorage.getItem('recent_views') || '[]');
        var entry = { url: location.href, title: document.title, time: new Date().toLocaleString() };
        views = views.filter(function (v) { return v.url !== entry.url; });
        views.unshift(entry); views = views.slice(0, 30);
        localStorage.setItem('recent_views', JSON.stringify(views));
    } catch (e) {}
})();

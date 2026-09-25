/* Bug11 文件头注释
 * 文章功能脚本：详情页点赞、收藏、分享、复制链接等按钮的异步行为与状态切换。
 * 用 session 防重复，结果通过 moeToast 与计数更新反馈。
 */
/* article_features.js —— 详情页增强：
 *   63. 星级评分（点击提交 /api/articles/<pk>/rate/）
 *   55. 版本快照弹窗（查看快照按钮 → 左右对比）
 *   60. 打印本文按钮（window.print()）
 *   65. 复制 Markdown 目录到剪贴板
 * 本脚本通过 <script data-article-id=...> 属性传入当前文章信息。
 */
(function () {
    'use strict';
    var self = document.currentScript || document.querySelector('script[data-article-id]');
    var ARTICLE_ID = self ? self.dataset.articleId : null;
    var ARTICLE_TITLE = self ? self.dataset.articleTitle : '';
    var ARTICLE_VIEWS = self ? self.dataset.articleViews : '0';
    var ARTICLE_COVER = (self && self.dataset.articleCover) || '';

    /* ---------- 63. 星级评分 ---------- */
    var widget = document.getElementById('rating-widget');
    if (widget) {
        var stars = widget.querySelectorAll('.star');
        var my = widget.dataset.my;
        // 初始高亮已评分
        paintStars(parseInt(my, 10) || 0);
        function paintStars(n) {
            stars.forEach(function (s) {
                s.classList.toggle('on', parseInt(s.dataset.value, 10) <= n);
            });
        }
        stars.forEach(function (s) {
            var val = parseInt(s.dataset.value, 10);
            s.addEventListener('mouseenter', function () { paintStars(val); });
            s.addEventListener('click', function () {
                submitRate(val);
            });
        });
        widget.addEventListener('mouseleave', function () { paintStars(parseInt(my, 10) || 0); });

        function submitRate(val) {
            var fd = new FormData();
            fd.append('score', val);
            fetch(widget.dataset.url, {
                method: 'POST',
                body: fd,
                headers: { 'X-CSRFToken': csrftoken() },
                credentials: 'same-origin'
            }).then(function (r) { return r.json(); }).then(function (data) {
                if (data.success) {
                    my = data.my;
                    paintStars(my);
                    var avg = widget.querySelector('.rating-avg');
                    if (avg) avg.textContent = '⭐ ' + data.avg + '（' + data.count + '人）';
                    toast('评分成功喵~ ' + my + '⭐');
                } else {
                    toast(data.error || '评分失败喵~');
                }
            }).catch(function () { toast('网络开小差了喵~'); });
        }
    }

    /* ---------- 55. 版本快照弹窗 ---------- */
    var modal = document.getElementById('snapshot-modal');
    if (modal) {
        var beforeEl = document.getElementById('snapshot-before');
        var afterEl = document.getElementById('snapshot-after');
        var titleEl = document.getElementById('snapshot-modal-title');
        document.querySelectorAll('.snapshot-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                titleEl.textContent = btn.dataset.title || '版本快照对比';
                beforeEl.textContent = btn.dataset.before || '（无内容）';
                afterEl.textContent = btn.dataset.after || '（无内容）';
                modal.hidden = false;
            });
        });
        var closeBtn = document.getElementById('snapshot-close');
        if (closeBtn) closeBtn.addEventListener('click', function () { modal.hidden = true; });
        modal.addEventListener('click', function (e) { if (e.target === modal) modal.hidden = true; });
    }

    /* ---------- 60. 打印本文 ---------- */
    var printBtn = document.getElementById('print-btn');
    if (printBtn) printBtn.addEventListener('click', function () { window.print(); });

    /* ---------- 65. 复制 Markdown 目录 ---------- */
    var tocCopy = document.getElementById('toc-copy-btn');
    if (tocCopy) {
        tocCopy.addEventListener('click', function () {
            var body = document.querySelector('.article-body');
            if (!body) return;
            var headings = body.querySelectorAll('h1, h2, h3, h4, h5');
            var lines = ['## 目录'];
            headings.forEach(function (h) {
                var level = parseInt(h.tagName.substring(1), 10);
                var indent = new Array(level).join('  ');  // 按层级缩进
                var text = h.textContent.trim();
                lines.push(indent + '- [' + text + '](#' + (h.id || '') + ')');
            });
            var md = lines.join('\n');
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(md).then(function () {
                    toast('目录已复制喵~📋');
                }).catch(function () { fallbackCopy(md); });
            } else {
                fallbackCopy(md);
            }
        });
    }
    function fallbackCopy(text) {
        var ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand('copy'); toast('目录已复制喵~📋'); }
        catch (e) { toast('复制失败喵~'); }
        document.body.removeChild(ta);
    }

    /* ---------- 64. 记录阅读历史 ---------- */
    if (ARTICLE_ID) {
        try {
            var key = 'reading_history';
            var list = JSON.parse(localStorage.getItem(key) || '[]');
            // 去重：移除同 id 的旧记录
            list = list.filter(function (it) { return String(it.id) !== String(ARTICLE_ID); });
            list.unshift({
                id: ARTICLE_ID,
                title: ARTICLE_TITLE,
                cover: ARTICLE_COVER,
                views: ARTICLE_VIEWS,
                time: Date.now()
            });
            if (list.length > 10) list = list.slice(0, 10);  // 最多保留 10 篇
            localStorage.setItem(key, JSON.stringify(list));
        } catch (e) {}
    }

    /* ---------- 工具：读取 CSRF token ---------- */
    function csrftoken() {
        var m = document.cookie.match(/csrftoken=([^;]+)/);
        return m ? decodeURIComponent(m[1]) : '';
    }
    /* ---------- 工具：轻量 toast 提示 ---------- */
    function toast(msg) {
        var t = document.getElementById('global-toast');
        if (!t) {
            t = document.createElement('div');
            t.id = 'global-toast';
            t.className = 'global-toast';
            document.body.appendChild(t);
        }
        t.textContent = msg;
        t.classList.add('show');
        clearTimeout(t._timer);
        t._timer = setTimeout(function () { t.classList.remove('show'); }, 2200);
    }
})();

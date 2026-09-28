/* Bug11 文件头注释
 * 交互功能脚本：图片上传、异步提交、悬浮/拖拽等通用交互的接线。
 * Bug4 起评论图片上传成功后插入 <img>，并兼容统一信封 {code,data:{url}} 与扁平 {url}。
 */
/**
 * features/interaction.js —— 互动增强（C类）
 *
 * 功能：
 *   C1 文章踩（POST data-dislike-url）
 *   C2 评论排序（最新/最热，前端重排）
 *   C3 长评论自动折叠（超阈值字数）
 *   C4 评论区搜索（前端过滤高亮）
 *   C5 评论举报（POST data-report-url）
 *   C6 图片评论（评论框图片上传按钮）
 *   C7 评论楼层跳转（点楼层号滚动定位）
 *   C8 只看楼主（过滤非楼主评论）
 *   C9 评论热度🔥标记（点赞数超阈值）
 *   C10 收藏夹管理（前端展示+切换）
 *   C11 评论字数统计（增强样式）
 *   C12 评论草稿自动保存（localStorage）
 *   C13 评论撤回（5分钟内，DELETE data-recall-url）
 *   C14 点赞爱心爆炸粒子（监听 like 成功）
 *   C15 分享后感谢弹窗
 *
 * 防御式：按 data-* 属性 / 类名存在才绑定，纯原生，无依赖。
 */
(function () {
    'use strict';

    function cookie(name) {
        var m = document.cookie.match(new RegExp('(^| )' + name + '=([^;]*)(;|$)'));
        return m ? decodeURIComponent(m[2]) : null;
    }
    function post(url, method, body) {
        return fetch(url, {
            method: method || 'POST',
            headers: {
                'X-CSRFToken': cookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin',
            body: body ? JSON.stringify(body) : undefined
        }).then(function (r) { return r.json(); });
    }
    function toast(msg) {
        var t = document.getElementById('global-toast');
        if (!t) { t = document.createElement('div'); t.id = 'global-toast'; document.body.appendChild(t); }
        t.textContent = msg; t.classList.add('show');
        clearTimeout(t._timer); t._timer = setTimeout(function () { t.classList.remove('show'); }, 1600);
    }

    /* ---------- C1 文章踩（D2修复：计数读 dislike_count、文字/标题随状态切换） ---------- */
    var dislikeBtn = document.querySelector('[data-dislike-url]');
    if (dislikeBtn) {
        var dislikeText = dislikeBtn.querySelector('.like-text');
        dislikeBtn.addEventListener('click', function () {
            post(dislikeBtn.getAttribute('data-dislike-url'), 'POST').then(function (d) {
                var disliked = d.disliked !== false;
                dislikeBtn.classList.toggle('disliked', disliked);
                // 后端返回 dislike_count；兼容旧字段名 count
                var n = (typeof d.dislike_count === 'number') ? d.dislike_count : d.count;
                if (typeof n === 'number') {
                    var c = document.querySelector('[data-dislike-count]');
                    if (c) c.textContent = n;
                }
                if (dislikeText) dislikeText.textContent = disliked ? '已踩喵' : '踩一下喵';
                dislikeBtn.title = disliked ? '再点一下取消踩喵~' : '踩一下这篇文章';
                toast(disliked ? '已踩~' : '取消踩~');
            }).catch(function () { toast('操作失败'); });
        });
    }

    /* ---------- C2 评论排序 ---------- */
    var sortBtns = document.querySelectorAll('.comment-sort button');
    sortBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            sortBtns.forEach(function (b) { b.classList.remove('active'); });
            btn.classList.add('active');
            var wrap = document.querySelector('.comment-list') || document.body;
            var items = Array.prototype.slice.call(wrap.querySelectorAll('.comment-item'));
            var mode = btn.getAttribute('data-sort');
            items.sort(function (a, b) {
                if (mode === 'hot') {
                    return (+(b.getAttribute('data-likes') || 0)) - (+(a.getAttribute('data-likes') || 0));
                }
                return (+(b.getAttribute('data-time') || 0)) - (+(a.getAttribute('data-time') || 0));
            });
            items.forEach(function (it) { wrap.appendChild(it); });
        });
    });

    /* ---------- C3 长评论折叠 / C9 热度标记 ---------- */
    document.querySelectorAll('.comment-item').forEach(function (item) {
        var text = item.querySelector('.comment-text');
        var likes = +(item.getAttribute('data-likes') || 0);
        if (likes >= 20) item.classList.add('comment-hot');
        if (text && text.textContent.length > 120) {
            item.classList.add('comment-folded');
            var btn = document.createElement('button');
            btn.className = 'fold-toggle'; btn.textContent = '展开全文 ▾';
            btn.addEventListener('click', function () {
                var folded = item.classList.toggle('comment-folded');
                btn.textContent = folded ? '展开全文 ▾' : '收起 ▴';
            });
            text.parentNode.insertBefore(btn, text.nextSibling);
        }
    });

    /* ---------- C4 评论区搜索 ---------- */
    var cSearch = document.querySelector('.comment-search-box input');
    if (cSearch) {
        cSearch.addEventListener('input', function () {
            var q = cSearch.value.trim().toLowerCase();
            document.querySelectorAll('.comment-item').forEach(function (it) {
                var hit = !q || (it.textContent || '').toLowerCase().indexOf(q) >= 0;
                it.style.display = hit ? '' : 'none';
                it.classList.toggle('highlight', !!q && hit);
            });
        });
    }

    /* ---------- C5 评论举报（bug11：萌系原因弹窗，事件委托兼容动态评论） ---------- */
    var reportModal = null;
    function ensureReportModal() {
        if (reportModal) return reportModal;
        reportModal = document.createElement('div');
        reportModal.className = 'moe-report-mask';
        reportModal.hidden = true;
        reportModal.innerHTML =
            '<div class="moe-report-panel" role="dialog" aria-modal="true" aria-labelledby="mrp-title">' +
            '  <div class="mrp-head"><strong id="mrp-title">🚩 举报这条评论喵</strong>' +
            '    <button type="button" class="mrp-close" aria-label="关闭">✕</button></div>' +
            '  <div class="mrp-reasons">' +
            '    <button type="button" class="mrp-reason" data-reason="垃圾广告">📢 垃圾广告</button>' +
            '    <button type="button" class="mrp-reason" data-reason="引战辱骂">😾 引战辱骂</button>' +
            '    <button type="button" class="mrp-reason" data-reason="违法违规">⚠️ 违法违规</button>' +
            '    <button type="button" class="mrp-reason" data-reason="色情低俗">🔞 色情低俗</button>' +
            '    <button type="button" class="mrp-reason" data-reason="其他">🌸 其他</button>' +
            '  </div>' +
            '  <textarea class="mrp-detail" rows="2" maxlength="300" placeholder="补充说明（选填，最多 300 字）"></textarea>' +
            '  <div class="mrp-bar">' +
            '    <button type="button" class="btn-sm mrp-cancel">再想想</button>' +
            '    <button type="button" class="btn-primary btn-sm mrp-submit" disabled>提交举报</button>' +
            '  </div>' +
            '</div>';
        document.body.appendChild(reportModal);
        return reportModal;
    }
    var reportState = { url: '', reason: '' };
    function openReport(url) {
        var m = ensureReportModal();
        reportState = { url: url, reason: '' };
        m.querySelectorAll('.mrp-reason').forEach(function (b) { b.classList.remove('active'); });
        m.querySelector('.mrp-detail').value = '';
        m.querySelector('.mrp-submit').disabled = true;
        m.hidden = false;
    }
    function closeReport() { if (reportModal) reportModal.hidden = true; }
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('[data-report-url]');
        if (!btn) return;
        e.preventDefault();
        openReport(btn.getAttribute('data-report-url'));
    });
    document.addEventListener('click', function (e) {
        if (!reportModal || reportModal.hidden) return;
        if (e.target.classList.contains('mrp-reason')) {
            reportState.reason = e.target.getAttribute('data-reason');
            reportModal.querySelectorAll('.mrp-reason').forEach(function (b) { b.classList.remove('active'); });
            e.target.classList.add('active');
            reportModal.querySelector('.mrp-submit').disabled = false;
        } else if (e.target.classList.contains('mrp-close') || e.target.classList.contains('mrp-cancel')) {
            closeReport();
        } else if (e.target === reportModal) {
            closeReport();
        } else if (e.target.classList.contains('mrp-submit')) {
            var detail = reportModal.querySelector('.mrp-detail').value.trim();
            var submitBtn = e.target;
            submitBtn.disabled = true; submitBtn.textContent = '提交中…';
            post(reportState.url, 'POST', { reason: reportState.reason, detail: detail })
                .then(function (d) {
                    closeReport();
                    // 兼容两种响应包：扁平 {success:true} 与统一信封 {code:0,data:{success:true}}
                    var ok = d && (d.success === true ||
                        (d.data && d.data.success === true) || d.code === 0);
                    toast(ok ? '举报已提交，感谢守护~' : '提交失败，稍后再试');
                })
                .catch(function () { toast('提交失败，稍后再试'); })
                .then(function () { submitBtn.textContent = '提交举报'; });
        }
    });
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && reportModal && !reportModal.hidden) closeReport();
    });

    /* ---------- C6 图片评论上传 ---------- */
    var imgInput = document.querySelector('[data-comment-image-input]');
    if (imgInput) {
        imgInput.addEventListener('change', function () {
            var file = imgInput.files[0];
            if (!file) return;
            var fd = new FormData(); fd.append('image', file);
            fetch(imgInput.getAttribute('data-upload-url') || '/api/comment/image/upload/', {
                method: 'POST',
                headers: { 'X-CSRFToken': cookie('csrftoken') },
                body: fd, credentials: 'same-origin'
            }).then(function (r) { return r.json(); }).then(function (d) {
                // Bug4：兼容统一信封 {code,data:{url}} 与扁平 {url} 两种返回结构
                var payload = d && d.data ? d.data : d;
                var ta = document.querySelector('#comment-input, textarea[name="content"]');
                // 直接插入 <img> 标签（bleach 已放行 img），提交后即可真正显示图片
                if (ta && payload.url) {
                    ta.value += '\n<img src="' + payload.url + '" alt="评论图片">\n';
                    ta.focus();
                    ta.dispatchEvent(new Event('input', { bubbles: true }));
                }
                toast('图片已插入~');
            }).catch(function () { toast('图片上传失败'); });
        });
    }

    /* ---------- C7 楼层跳转 ---------- */
    document.querySelectorAll('.comment-floor').forEach(function (fl) {
        fl.addEventListener('click', function () {
            var target = document.getElementById('comment-' + fl.getAttribute('data-floor'));
            if (target) target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        });
    });

    /* ---------- C8 只看楼主（工单7：绑定 #only-author 复选框） ---------- */
    var opBtn = document.getElementById('only-author') ||
               document.querySelector('[data-op-only]');
    var opList = document.getElementById('comment-flat-list') ||
                 document.querySelector('.comment-list') || document.getElementById('comments');
    function applyOpOnly(on) {
        var shown = 0;
        document.querySelectorAll('.comment-item').forEach(function (it) {
            var hide = on && !it.classList.contains('is-op');
            it.classList.toggle('op-only-hidden', hide);
            if (!hide) shown++;
        });
        document.body.classList.toggle('op-only-on', on);
        // 工单7：楼主一条评论都没有时给出萌系空状态，避免勾选后一片空白
        var note = document.getElementById('op-only-empty');
        if (on && shown === 0) {
            if (!note) {
                note = document.createElement('div');
                note.id = 'op-only-empty';
                note.className = 'op-only-empty';
                note.innerHTML = '🐣 <span>楼主还没有回复评论喵，去抢沙发吧~</span>';
                (opList || document.querySelector('.comments-section') || document.body).appendChild(note);
            }
            note.style.display = '';
        } else if (note) {
            note.style.display = 'none';
        }
    }
    if (opBtn) {
        opBtn.addEventListener('change', function () {
            applyOpOnly(opBtn.checked);
        });
        // 新评论（AJAX 插入）后若过滤开启，自动重新应用，避免非楼主评论漏出
        var flatList = document.getElementById('comment-flat-list') ||
                      document.getElementById('comments');
        if (flatList && 'MutationObserver' in window) {
            new MutationObserver(function () {
                if (opBtn.checked) applyOpOnly(true);
            }).observe(flatList, { childList: true });
        }
    }

    /* ---------- C10 收藏夹切换 ---------- */
    document.querySelectorAll('.favorite-folder').forEach(function (f) {
        f.addEventListener('click', function () {
            var name = f.getAttribute('data-folder');
            var url = '/api/favorites/?folder=' + encodeURIComponent(name);
            location.href = url;
        });
    });

    /* ---------- C11/C12 评论字数 + 草稿自动保存 ---------- */
    var ta = document.querySelector('.comment-input, #id_content_comment, textarea[name="comment"]');
    if (ta) {
        var draftKey = 'blog_comment_draft_' + (location.pathname);
        try { var saved = localStorage.getItem(draftKey); if (saved) ta.value = saved; } catch (e) {}
        var wc = document.querySelector('.comment-wc');
        var timer = null;
        ta.addEventListener('input', function () {
            if (wc) wc.textContent = (ta.value || '').length + ' 字';
            clearTimeout(timer);
            timer = setTimeout(function () {
                try { localStorage.setItem(draftKey, ta.value || ''); } catch (e) {}
            }, 800);
        });
        ta.form && ta.form.addEventListener('submit', function () {
            try { localStorage.removeItem(draftKey); } catch (e) {}
        });
    }

    /* ---------- C13 评论撤回（5分钟内，Bug8：站内萌系确认） ----------
       事件委托到 document：AJAX 新插入的评论节点同样可撤回（直接绑定会漏掉动态节点） */
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('[data-recall-url]');
        if (!btn) return;
        moeConfirm({ message: '确定撤回这条评论吗？', danger: true, confirmText: '撤回' })
            .then(function (ok) {
                if (!ok) return;
                post(btn.getAttribute('data-recall-url'), 'DELETE').then(function () {
                    var item = btn.closest('.comment-item'); if (item) item.remove();
                    // 撤回后同步减评论数（与后端重算结果一致；下一个整页刷新时以服务端为准）
                    var cc = document.getElementById('comments-count');
                    if (cc) {
                        var n = parseInt(cc.textContent, 10);
                        if (!isNaN(n) && n > 0) cc.textContent = n - 1;
                    }
                    toast('已撤回~');
                }).catch(function () { toast('撤回失败（可能超过时限）'); });
            });
    });

    /* ---------- C14 点赞爱心爆炸 ---------- */
    document.addEventListener('click', function (e) {
        var like = e.target.closest('.like-btn, [data-like-success]');
        if (!like) return;
        var cx = e.clientX, cy = e.clientY;
        for (var i = 0; i < 8; i++) {
            var h = document.createElement('span');
            h.className = 'heart-burst'; h.textContent = '💗';
            h.style.left = cx + 'px'; h.style.top = cy + 'px';
            h.style.setProperty('--dx', (Math.random() * 80 - 40) + 'px');
            h.style.setProperty('--dy', (-Math.random() * 80 - 20) + 'px');
            document.body.appendChild(h);
            setTimeout(function (el) { if (el && el.remove) el.remove(); }, 900, h);
        }
    });

    /* ---------- C15 分享感谢弹窗 ---------- */
    document.addEventListener('click', function (e) {
        var sh = e.target.closest('[data-share-thanks]');
        if (!sh) return;
        var mask = document.createElement('div');
        mask.className = 'thanks-modal-mask';
        mask.innerHTML = '<div class="thanks-modal"><div class="thanks-icon">🎉</div>' +
            '<h4>感谢分享！</h4><p>你的分享是对作者最大的鼓励~</p></div>';
        mask.addEventListener('click', function () { mask.remove(); });
        document.body.appendChild(mask);
    });

    /* ---------- C16 右栏热门文章 周/月/总榜切换（AJAX 拉取片段，带本地缓存） ---------- */
    (function () {
        var tabsBox = document.querySelector('.hot-rank-tabs');
        var list = document.querySelector('.widget .hot-list');
        if (!tabsBox || !list) return;
        var mem = {};   // 本次会话内已加载片段缓存，避免重复请求
        function setActive(range) {
            tabsBox.querySelectorAll('.hot-rank-tab').forEach(function (t) {
                t.classList.toggle('active', t.getAttribute('data-range') === range);
            });
        }
        function load(range) {
            if (mem[range]) { list.innerHTML = mem[range]; setActive(range); return; }
            list.classList.add('hot-loading');
            fetch('/api/hot-articles/?range=' + encodeURIComponent(range), {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                credentials: 'same-origin'
            }).then(function (r) { if (!r.ok) throw new Error('bad'); return r.text(); })
              .then(function (html) {
                  mem[range] = html; list.innerHTML = html; setActive(range);
              }).catch(function () {
                  list.innerHTML = '<li class="muted">榜单加载失败喵，稍后再试~</li>';
              }).then(function () { list.classList.remove('hot-loading'); });
        }
        tabsBox.addEventListener('click', function (e) {
            var tab = e.target.closest('.hot-rank-tab');
            if (tab) load(tab.getAttribute('data-range'));
        });
    })();
})();

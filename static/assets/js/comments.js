/**
 * comments.js —— 文章详情页评论区交互
 * 功能：
 *   1. 相对时间格式化：把 .comment-time[data-ts] 渲染为"X分钟前/X小时前/X天前"；
 *   2. 发表评论：主表单 AJAX 提交，成功后把新评论 HTML 插入列表顶部 / 对应回复槽，
 *      并更新评论总数；失败则在提示区显示后端返回的错误文案；
 *   3. 楼中楼回复：点击"回复"按钮展开内联表单，提交后把回复 HTML 追加到父评论下；
 *   4. 评论点赞：AJAX POST 到 /api/comments/<pk>/like/，成功后更新数字并禁用按钮。
 * 依赖：无（纯原生 JS）。执行方式：IIFE，DOM 就绪后自动初始化。
 */
(function () {
    'use strict';

    /* ============================ 工具函数 ============================ */

    /**
     * 轻量 toast 提示（替代 alert，更萌）
     */
    function toast(msg) {
        var t = document.getElementById('global-toast');
        if (!t) {
            t = document.createElement('div');
            t.id = 'global-toast';
            document.body.appendChild(t);
        }
        t.textContent = msg;
        t.classList.add('show');
        clearTimeout(t._timer);
        t._timer = setTimeout(function () { t.classList.remove('show'); }, 2200);
    }

    /**
     * 读取指定名称的 cookie（用于 csrftoken）。
     * @param {string} name cookie 名
     * @returns {string|null}
     */
    function getCookie(name) {
        var arr = document.cookie.match(new RegExp('(^| )' + name + '=([^;]*)(;|$)'));
        return arr ? decodeURIComponent(arr[2]) : null;
    }

    /**
     * 把 Unix 时间戳(秒)格式化为相对时间字符串。
     * @param {number} ts 秒级时间戳
     * @returns {string} 形如"刚刚 / X分钟前 / X小时前 / X天前 / 日期"
     */
    function relTime(ts) {
        var diff = Math.floor(Date.now() / 1000) - Number(ts);
        if (diff < 60) return '刚刚';
        if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前';
        if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前';
        if (diff < 86400 * 30) return Math.floor(diff / 86400) + ' 天前';
        // 超过 30 天回退为 YYYY-MM-DD
        var d = new Date(ts * 1000);
        return d.getFullYear() + '-' +
            String(d.getMonth() + 1).padStart(2, '0') + '-' +
            String(d.getDate()).padStart(2, '0');
    }

    /**
     * 把页面上所有 .comment-time[data-ts] 替换为相对时间。
     */
    function refreshRelativeTimes() {
        document.querySelectorAll('.comment-time[data-ts]').forEach(function (el) {
            var ts = el.getAttribute('data-ts');
            if (ts) el.textContent = relTime(ts);
        });
    }

    /**
     * 通用 fetch 包装：POST JSON 表单，自动带 CSRF。
     * @param {string} url 提交地址
     * @param {FormData} formData 表单数据
     * @returns {Promise<object>} 解析后的 JSON
     */
    function postForm(url, formData) {
        return fetch(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            credentials: 'same-origin',
            body: formData
        }).then(function (resp) {
            return resp.json().then(function (data) {
                data._status = resp.status;
                return data;
            });
        });
    }

    /* ============================ 1. 发表主评论 ============================ */
    var commentForm = document.getElementById('comment-form');
    if (commentForm) {
        commentForm.addEventListener('submit', function (e) {
            e.preventDefault();
            var input = document.getElementById('comment-input');
            var submitBtn = document.getElementById('comment-submit');
            var url = commentForm.getAttribute('data-url');
            var content = (input.value || '').trim();
            if (!content) {
                toast('评论内容不能为空喵~ 📝');
                return;
            }
            var oldText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = '发送中...';
            var fd = new FormData();
            fd.append('content', content);
            postForm(url, fd).then(function (data) {
                if (data.success) {
                    // 清空输入框
                    input.value = '';
                    // 移除空状态提示（若存在）
                    var empty = document.querySelector('.comment-empty');
                    if (empty) empty.remove();
                    // Bug3：顶级评论需先包进 .comment-thread（父子同框的「一个框」）再插到列表最前
                    var list = document.getElementById('comment-list');
                    var wrap = document.createElement('div');
                    wrap.innerHTML = data.html.trim();
                    var node = wrap.firstElementChild;
                    // Bug1：评论需审核时作者本人看到半透明「审核中」态
                    if (data.moderation_pending && node) node.classList.add('comment-pending');
                    var newThread = document.createElement('div');
                    newThread.className = 'comment-thread';
                    newThread.setAttribute('data-thread', '');
                    newThread.appendChild(node);
                    list.insertBefore(newThread, list.firstChild);
                    // 更新评论总数
                    updateCount(data.comment_count);
                    // 新插入节点的相对时间格式化
                    refreshRelativeTimes();
                    toast('评论成功喵~ ✨');
                } else {
                    toast(data.error || '发表失败了喵~再试一次吧');
                }
            }).catch(function () {
                toast('网络开小差了喵~再试一次吧');
            }).finally(function () {
                submitBtn.disabled = false;
                submitBtn.textContent = oldText;
            });
        });
    }

    /* ============================ 2. 回复（事件委托） ============================ */
    var commentList = document.getElementById('comment-list');
    if (commentList) {
        // 展开 / 收起内联回复表单
        commentList.addEventListener('click', function (e) {
            var replyBtn = e.target.closest('.comment-reply-btn');
            if (replyBtn) {
                var item = replyBtn.closest('.comment-item');
                var form = item.querySelector('.comment-reply-form');
                // 只展开当前这条，收起其它已展开的
                document.querySelectorAll('.comment-reply-form:not([hidden])').forEach(function (f) {
                    if (f !== form) f.hidden = true;
                });
                form.hidden = !form.hidden;
                if (!form.hidden) {
                    var ta = form.querySelector('textarea');
                    if (ta) ta.focus();
                }
                return;
            }
            // 取消回复
            if (e.target.closest('.comment-reply-cancel')) {
                var f = e.target.closest('.comment-reply-form');
                if (f) f.hidden = true;
                return;
            }
            // 提交回复
            var submitReply = e.target.closest('.comment-reply-submit');
            if (submitReply) {
                var item = submitReply.closest('.comment-item');
                var form = item.querySelector('.comment-reply-form');
                var ta = form.querySelector('textarea');
                var content = (ta.value || '').trim();
                if (!content) { toast('回复内容不能为空喵~'); return; }
                var parentPk = submitReply.getAttribute('data-pk');
                var fd = new FormData();
                fd.append('content', content);
                fd.append('parent_comment_id', parentPk);
                var url = commentForm
                    ? commentForm.getAttribute('data-url')
                    : document.querySelector('.comments-section').getAttribute('data-post-url');
                var oldReplyText = submitReply.textContent;
                submitReply.disabled = true;
                submitReply.textContent = '发送中...';
                postForm(url, fd).then(function (data) {
                    if (data.success) {
                        // 扁平化插入（bug10）：与服务端渲染保持一致，把新回复直接放进
                        // #comment-list 并紧跟在被回复评论之后；不再塞进父评论的
                        // .comment-reply-slot，避免逐层嵌套累积左外边距、越回复越靠右。
                        var wrap = document.createElement('div');
                        wrap.innerHTML = data.html.trim();
                        var node = wrap.firstElementChild;
                        // Bug1：回复需审核时同样标记为待审核态
                        if (data.moderation_pending && node) node.classList.add('comment-pending');
                        // Bug3：定位被回复评论所在线程，把回复放进其 .comment-replies 容器
                        var targetThread = item.closest('.comment-thread');
                        var repliesBox = targetThread ? targetThread.querySelector('.comment-replies') : null;
                        if (!repliesBox && targetThread) {
                            // 该线程此前没有回复：新建回复容器并加到线程末尾
                            repliesBox = document.createElement('div');
                            repliesBox.className = 'comment-replies';
                            targetThread.appendChild(repliesBox);
                        }
                        // 单条回复用 .comment-reply-row 包裹（与服务端渲染结构一致）
                        var replyRow = document.createElement('div');
                        replyRow.className = 'comment-reply-row';
                        replyRow.appendChild(node);
                        if (repliesBox) {
                            repliesBox.appendChild(replyRow);
                            updateThreadToggle(targetThread);   // 重新计算折叠行与按钮文案
                        } else {
                            // 极端兜底：找不到线程容器时直接追加到评论列表末尾
                            document.getElementById('comment-list').appendChild(replyRow);
                        }
                        ta.value = '';
                        form.hidden = true;
                        updateCount(data.comment_count);
                        refreshRelativeTimes();
                        toast('回复成功喵~ 💬');
                    } else {
                        toast(data.error || '回复失败了喵~');
                    }
                }).catch(function () {
                    toast('网络开小差了喵~');
                }).finally(function () {
                    submitReply.disabled = false;
                    submitReply.textContent = oldReplyText;
                });
            }
        });
    }

    /* ============================ 3. 评论点赞（事件委托） ============================ */
    if (commentList) {
        commentList.addEventListener('click', function (e) {
            var likeBtn = e.target.closest('.comment-like-btn');
            if (!likeBtn || likeBtn.disabled) return;
            var url = likeBtn.getAttribute('data-url');
            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            }).then(function (r) { return r.json(); })
              .then(function (data) {
                  if (typeof data.likes === 'number') {
                      var n = likeBtn.querySelector('.n');
                      if (n) n.textContent = data.likes;
                  }
                  likeBtn.disabled = false;  // 请求期间已临时禁用，响应后恢复（toggle 取消/再赞）
                  if (data.liked) {
                      likeBtn.classList.add('liked');
                      likeBtn.title = '再点一下取消赞喵~';
                      var txt = likeBtn.querySelector('.txt');
                      if (txt) txt.textContent = '已赞';
                  } else {
                      likeBtn.classList.remove('liked');
                      likeBtn.title = '赞喵';
                      var txt = likeBtn.querySelector('.txt');
                      if (txt) txt.textContent = '赞';
                  }
              }).catch(function () {
                  toast('点赞失败了喵~再试一次吧');
              });
        });
    }

    /* ============================ Bug3：维护线程「展开/收起回复」按钮 ============================ */
    function updateThreadToggle(thread) {
        if (!thread) return;
        var repliesBox = thread.querySelector('.comment-replies');
        if (!repliesBox) return;
        var SHOWN = 3;   // 默认可见回复条数，与后端 REPLY_DEFAULT_SHOWN 一致
        var rows = repliesBox.querySelectorAll('.comment-reply-row');
        var toggle = repliesBox.querySelector('.comment-replies-toggle');
        var isOpen = thread.classList.contains('replies-open');
        // 按当前是否展开，重新给超出 SHOWN 的行加 / 去 is-extra
        rows.forEach(function (r, i) {
            r.classList.toggle('is-extra', i >= SHOWN && !isOpen);
        });
        var extra = Math.max(0, rows.length - SHOWN);
        if (extra > 0) {
            if (!toggle) {
                toggle = document.createElement('button');
                toggle.type = 'button';
                toggle.className = 'comment-replies-toggle';
                repliesBox.appendChild(toggle);
            }
            if (isOpen) {
                toggle.dataset.collapsed = 'false';
                toggle.setAttribute('aria-expanded', 'true');
                toggle.textContent = '🫧 收起回复';
            } else {
                toggle.dataset.collapsed = 'true';
                toggle.setAttribute('aria-expanded', 'false');
                toggle.textContent = '💬 展开其余 ' + extra + ' 条回复';
            }
        } else if (toggle) {
            toggle.remove();   // 回复数回到阈值内，移除折叠按钮
        }
    }

    /* ============================ 工具：更新评论总数 ============================ */
    function updateCount(n) {
        var el = document.getElementById('comments-count');
        if (typeof n === 'number' && el) el.textContent = n;
    }

    /* ============================ 27. 评论字数统计（接近上限变黄，超限变红） ============================ */
    var commentInput = document.getElementById('comment-input');
    var wcNum = document.getElementById('comment-wc-num');
    var wcBox = document.getElementById('comment-wc');
    if (commentInput && wcNum) {
        function updateWc() {
            var n = (commentInput.value || '').length;
            wcNum.textContent = n;
            if (n >= 10000) { wcBox.classList.add('wc-over'); wcBox.classList.remove('wc-warn'); }
            else if (n >= 8000) { wcBox.classList.add('wc-warn'); wcBox.classList.remove('wc-over'); }
            else { wcBox.classList.remove('wc-warn', 'wc-over'); }
        }
        commentInput.addEventListener('input', updateWc);
        updateWc();
    }

    /* ============================ Bug4：主评论轻量富文本工具栏（仅主评论） ============================ */
    /**
     * 用指定标签包裹 textarea 当前选中文字；没有选中时插入占位文字并选中它。
     * @param {HTMLTextAreaElement} ta 主评论输入框
     * @param {string} before 起始标签
     * @param {string} after 结束标签
     * @param {string} ph 无选中时的占位文字
     */
    function wrapSelection(ta, before, after, ph) {
        var s = ta.selectionStart != null ? ta.selectionStart : ta.value.length;
        var e = ta.selectionEnd != null ? ta.selectionEnd : s;
        var sel = ta.value.slice(s, e) || ph;
        ta.value = ta.value.slice(0, s) + before + sel + after + ta.value.slice(e);
        ta.selectionStart = s + before.length;
        ta.selectionEnd = s + before.length + sel.length;
        ta.focus();
        ta.dispatchEvent(new Event('input', { bubbles: true }));   // 触发字数统计更新
    }

    var rtToolbar = document.querySelector('.comment-rt-toolbar');
    if (rtToolbar) {
        rtToolbar.addEventListener('click', function (e) {
            var btn = e.target.closest('.crt-btn');
            if (!btn) return;
            var ta = document.getElementById('comment-input');
            if (!ta) return;
            var fmt = btn.getAttribute('data-fmt');
            if (fmt === 'strong') {
                wrapSelection(ta, '<strong>', '</strong>', '加粗文字');
            } else if (fmt === 'em') {
                wrapSelection(ta, '<em>', '</em>', '斜体文字');
            } else if (fmt === 'code') {
                wrapSelection(ta, '<code>', '</code>', 'code');
            } else if (fmt === 'link') {
                var url = window.prompt('请输入链接地址喵 (https://...)', 'https://');
                if (!url) return;
                var s = ta.selectionStart != null ? ta.selectionStart : ta.value.length;
                var en = ta.selectionEnd != null ? ta.selectionEnd : s;
                var sel = ta.value.slice(s, en) || '萌系链接';
                var html = '<a href="' + url + '">' + sel + '</a>';
                ta.value = ta.value.slice(0, s) + html + ta.value.slice(en);
                ta.selectionStart = ta.selectionEnd = s + html.length;
                ta.focus();
                ta.dispatchEvent(new Event('input', { bubbles: true }));
            }
        });
    }

    /* Bug4：图片喵按钮 → 打开文件选择框（上传成功后由 interaction.js 插入 <img>） */
    var commentImageBtn = document.getElementById('comment-image-btn');
    var commentImageInput = document.getElementById('comment-image-input');
    if (commentImageBtn && commentImageInput) {
        commentImageBtn.addEventListener('click', function () { commentImageInput.click(); });
    }

    /* ============================ 初始化：相对时间 ============================ */
    refreshRelativeTimes();
})();

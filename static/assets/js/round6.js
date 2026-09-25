/* ============================================================
 * round6.js · 萌语博客「第六轮」Bug 修复与体验增强脚本
 * ------------------------------------------------------------
 * 功能：
 *  1. 左下角 FAB 快捷操作菜单（bug2）：展开/收起、点击动作、
 *     外部点击 / Esc 自动关闭；
 *  2. 标签云防拖拽（bug22）：标签只响应点击跳转，不被拖起；
 *  3. 热门文章周 / 月 / 总榜切换（配合模板渲染的三组列表）；
 *  4. 侧栏在窄屏下的折叠辅助；
 *  全部逻辑带 UTF-8 中文注释，压缩后由 refresh_assets 生成 .min.js。
 * ============================================================ */
(function () {
    'use strict';

    /* ----------------------------------------------------------
     * 1. FAB 快捷菜单（bug2）
     * -------------------------------------------------------- */
    function initQuickMenu() {
        var fab = document.getElementById('sidebar-toggle');
        if (!fab) return;

        /* 若菜单 DOM 尚未由模板输出，则动态构建一份，保证可用 */
        var menu = document.getElementById('quick-menu');
        if (!menu) {
            menu = document.createElement('div');
            menu.id = 'quick-menu';
            menu.className = 'quick-menu';
            menu.hidden = true;
            var items = [
                { ico: '🔝', text: '回到顶部', action: 'top' },
                { ico: '✍', text: '写文章', action: 'write', auth: true },
                { ico: '🌓', text: '明暗切换', action: 'theme' },
                { ico: '🔍', text: '聚焦搜索', action: 'search' },
                { ico: '🎲', text: '随机一篇', action: 'random' },
                { ico: '🎛', text: '运营看板', action: 'console', staff: true },
                { ico: '🔄', text: '刷新页面', action: 'reload' }
            ];
            items.forEach(function (it) {
                var a = document.createElement('a');
                a.className = 'quick-item' + (it.action === 'reload' ? ' qi-danger' : '');
                a.setAttribute('role', 'menuitem');
                a.dataset.action = it.action;
                if (it.auth) a.dataset.auth = '1';
                if (it.staff) a.dataset.staff = '1';
                a.innerHTML = '<span class="qi-ico">' + it.ico + '</span><span>' + it.text + '</span>';
                menu.appendChild(a);
            });
            document.body.appendChild(menu);
        }

        /* 根据登录 / 员工身份显隐对应菜单项。
           工单12：原先限定的 .nav-user 容器类已失效，改为直接探测全页可靠信号——
           登录看“退出表单 / 用户菜单按钮”，员工看“运营看板链接”。 */
        var loggedIn = !!document.querySelector('form[action$="logout/"]') ||
                       !!document.getElementById('user-menu-btn');
        var isStaff = !!document.querySelector('a[href$="/console/"]');
        menu.querySelectorAll('[data-auth="1"]').forEach(function (el) {
            el.style.display = loggedIn ? '' : 'none';
        });
        menu.querySelectorAll('[data-staff="1"]').forEach(function (el) {
            el.style.display = isStaff ? '' : 'none';
        });

        /* 展开 / 收起 */
        function setOpen(open) {
            menu.hidden = !open;
            // 下一帧切换 open class，触发过渡
            requestAnimationFrame(function () {
                menu.classList.toggle('open', open);
            });
            fab.setAttribute('aria-expanded', open ? 'true' : 'false');
            // 工单12：钉住（点击展开）态视觉反馈——高亮环 + aria-pressed
            fab.classList.toggle('is-pinned', open && pinned);
            fab.setAttribute('aria-pressed', (open && pinned) ? 'true' : 'false');
        }
        function isOpen() { return !menu.hidden; }

        /* bug1：悬停与点击都有交互。
           pinned=点击“钉住”，鼠标移出也不收起；再次点击 / 外部点击 / Esc 才关闭。 */
        var pinned = false;
        var hoverTimer = null;
        function clearHover() { if (hoverTimer) { clearTimeout(hoverTimer); hoverTimer = null; } }
        function openByHover() { clearHover(); if (!isOpen()) setOpen(true); }
        function scheduleClose() {
            clearHover();
            hoverTimer = setTimeout(function () { if (!pinned) setOpen(false); }, 240);
        }

        /* 悬停 FAB 或菜单即展开；移出给予 240ms 缓冲，避免中途抖动 */
        fab.addEventListener('mouseenter', openByHover);
        fab.addEventListener('mouseleave', scheduleClose);
        menu.addEventListener('mouseenter', openByHover);
        menu.addEventListener('mouseleave', scheduleClose);

        fab.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            clearHover();
            if (isOpen() && pinned) { pinned = false; setOpen(false); }
            else { pinned = true; setOpen(true); }
        });

        /* 点击具体动作 */
        menu.addEventListener('click', function (e) {
            var item = e.target.closest('.quick-item');
            if (!item) return;
            var act = item.dataset.action;
            pinned = false;
            setOpen(false);
            switch (act) {
                case 'top':
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                    break;
                case 'write':
                    window.location.href = '/new/';
                    break;
                case 'theme':
                    var t = document.getElementById('theme-toggle');
                    if (t) t.click();
                    break;
                case 'search':
                    var s = document.getElementById('nav-search-input');
                    if (s) { s.focus(); s.select(); }
                    break;
                case 'random':
                    window.location.href = '/random/';
                    break;
                case 'console':
                    window.location.href = '/console/';
                    break;
                case 'reload':
                    window.location.reload();
                    break;
            }
        });

                /* 外部点击关闭 */
        document.addEventListener('click', function (e) {
            if (!isOpen()) return;
            if (menu.contains(e.target) || fab.contains(e.target)) return;
            pinned = false;
            setOpen(false);
        });
        /* Esc 关闭 */
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && isOpen()) { pinned = false; setOpen(false); }
        });
    }

    /* ----------------------------------------------------------
     * 2. 标签云防拖拽（bug22）
     *    模板已设 draggable=false，这里再加 JS 兜底：阻止 dragstart
     * -------------------------------------------------------- */
    function initTagNoDrag() {
        document.addEventListener('dragstart', function (e) {
            var t = e.target.closest ? e.target.closest('.tag-cloud a, #home-tag-cloud a') : null;
            if (t) e.preventDefault();
        });
    }

    /* ----------------------------------------------------------
     * 3. 热门文章周 / 月 / 总榜切换
     *    期望右栏存在 <ol data-range="week|month|total">；
     *    若只有一个列表（后端未渲染三组），则不做处理。
     * -------------------------------------------------------- */
    function initHotRankTabs() {
        var tabs = document.querySelectorAll('.hot-rank-tab');
        if (!tabs.length) return;
        var lists = document.querySelectorAll('.hot-list[data-range]');
        tabs.forEach(function (tab) {
            tab.addEventListener('click', function () {
                var range = tab.dataset.range;
                tabs.forEach(function (x) {
                    x.classList.toggle('active', x === tab);
                    x.setAttribute('aria-selected', x === tab ? 'true' : 'false');
                });
                if (lists.length) {
                    lists.forEach(function (ol) {
                        ol.style.display = ol.dataset.range === range ? '' : 'none';
                    });
                }
            });
        });
    }

    /* ----------------------------------------------------------
     * 4. 正文图片加载失败兜底（bug9）
     *    error 不冒泡，需在捕获阶段监听；把裂图替换为萌系占位卡
     * -------------------------------------------------------- */
    function initBrokenImageFallback() {
        document.addEventListener('error', function (e) {
            var img = e.target;
            if (!img || img.tagName !== 'IMG') return;
            // 仅处理正文 / 评论内容中的图片（跳过头像、图标等小图）
            var inBody = img.closest('#article-body, .comment-content, .comment-body');
            if (!inBody || img.dataset.moeFallback === '1') return;
            img.dataset.moeFallback = '1';
            var box = document.createElement('div');
            box.className = 'moe-img-fallback';
            box.setAttribute('role', 'img');
            box.setAttribute('aria-label', '图片加载失败');
            box.innerHTML = '<span class="mif-emoji">🖋️</span>' +
                '<span class="mif-text">图片走丢了喵~</span>' +
                '<span class="mif-sub">可能链接失效或网络不好</span>';
            img.style.display = 'none';
            img.parentNode.insertBefore(box, img.nextSibling);
        }, true);   // true = 捕获阶段
    }

    /* ----------------------------------------------------------
     * 5. 通用「封面选择器」文件名回显（Bug2：创建系列页等）
     *    任意 .cover-picker 内的隐藏文件框，选中文件后把文件名显示
     *    在萌系标签上并加 has-file 高亮；取消选择则还原占位文案。
     *    写文章页 id_cover_image 已由 edit_inline.js 专门处理，这里跳过。
     * -------------------------------------------------------- */
    function initCoverPicker() {
        document.addEventListener('change', function (e) {
            var fi = e.target;
            if (!fi || fi.tagName !== 'INPUT' || fi.type !== 'file') return;
            if (fi.id === 'id_cover_image') return;   // 写文章页交给 edit_inline.js
            var box = fi.closest('.cover-picker');
            if (!box) return;
            // 标签内的文字节点（.cp-text），没有则退化为整个 label
            var label = box.querySelector('.cover-picker-label .cp-text') ||
                        box.querySelector('.cp-text');
            if (!label) return;
            // 首次记录默认占位文案，便于还原
            if (!label.dataset.defaultText) label.dataset.defaultText = label.textContent;
            if (fi.files && fi.files.length) {
                label.textContent = '已选择：' + fi.files[0].name;
                box.classList.add('has-file');
            } else {
                label.textContent = label.dataset.defaultText;
                box.classList.remove('has-file');
            }
        });
    }

    /* ----------------------------------------------------------
     * 6. 楼中楼回复「折叠 / 展开」（Bug3）
     *    点击 .comment-replies-toggle：切换线程 replies-open 类，
     *    被折叠的 .comment-reply-row.is-extra 随之显隐；按钮文案在
     *    「展开其余 N 条回复」与「收起回复」之间切换。
     * -------------------------------------------------------- */
    function initReplyCollapse() {
        document.addEventListener('click', function (e) {
            var btn = e.target.closest('.comment-replies-toggle');
            if (!btn) return;
            var thread = btn.closest('.comment-thread');
            if (!thread) return;
            // 记录展开前的原始文案（含 N），收起时还原
            if (!btn.dataset.openText) btn.dataset.openText = btn.textContent;
            var collapsed = btn.dataset.collapsed === 'true';
            if (collapsed) {
                thread.classList.add('replies-open');
                btn.dataset.collapsed = 'false';
                btn.setAttribute('aria-expanded', 'true');
                btn.textContent = '🫧 收起回复';
            } else {
                thread.classList.remove('replies-open');
                btn.dataset.collapsed = 'true';
                btn.setAttribute('aria-expanded', 'false');
                btn.textContent = btn.dataset.openText;
            }
        });
    }

    /* ----------------------------------------------------------
     * 7. 置顶 / 精华 / 热门（Bug1）
     *    - 管理员点 .promo-toggle：直接切换（带 promo-on 表示当前已设置）；
     *    - 作者点 .promo-apply-btn：打开理由弹窗，提交后生成推广申请。
     * -------------------------------------------------------- */
    /* 读取 csrftoken cookie，供 POST 防 CSRF 校验 */
    function getCsrfToken() {
        var m = document.cookie.match(/csrftoken=([^;]+)/);
        return m ? m[1] : '';
    }
    /* 以表单编码 POST 到指定 URL，返回解析后的 JSON；失败给出轻提示 */
    function postForm(url, data, cb) {
        var body = new URLSearchParams();
        Object.keys(data).forEach(function (k) { body.append(k, data[k]); });
        fetch(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken(), 'X-Requested-With': 'XMLHttpRequest' },
            body: body,
            credentials: 'same-origin'
        }).then(function (r) { return r.json(); }).then(function (j) {
            cb(j);
        }).catch(function () {
            if (window.moeToast) moeToast('网络开小差了，稍后再试喵~', 'error');
        });
    }
    function initPromotion() {
        /* ---- 管理员直接切换置顶/精华/热门 ---- */
        var manage = document.querySelector('.promo-manage');
        if (manage) {
            var toggleUrl = manage.dataset.toggleUrl;
            manage.addEventListener('click', function (e) {
                var btn = e.target.closest('.promo-toggle');
                if (!btn) return;
                var isOn = btn.classList.contains('promo-on');
                // 当前已设置则执行「取消」动作，否则执行「设置」动作
                var action = isOn ? btn.dataset.actionOff : btn.dataset.actionOn;
                postForm(toggleUrl, { action: action }, function (j) {
                    if (j.code === 0) {
                        btn.classList.toggle('promo-on', !isOn);
                        if (window.moeToast) moeToast(j.msg || '操作成功~', 'success');
                    } else if (window.moeToast) {
                        moeToast(j.msg || '操作失败~', 'error');
                    }
                });
            });
        }

        /* ---- 作者申请：理由弹窗 ---- */
        var apply = document.querySelector('.promo-apply');
        var modal = document.getElementById('promo-modal');
        if (apply && modal) {
            var requestUrl = apply.dataset.requestUrl;
            var statusUrl = apply.dataset.statusUrl;
            var kindInput = document.getElementById('promo-modal-kind');
            var reasonInput = document.getElementById('promo-modal-reason');
            var submitBtn = document.getElementById('promo-modal-submit');
            var currentKind = '';
            var currentBtn = null;

            /* Bug8：把 data-state / 文案 / 禁用态同步到按钮上（服务端与前端共用一套状态） */
            function paintButton(btn, state, kindLabel) {
                if (!btn) return;
                btn.dataset.state = state;
                btn.classList.remove('promo-state-open', 'promo-state-applied', 'promo-state-pending');
                btn.classList.add('promo-state-' + state);
                if (state === 'applied') {
                    btn.textContent = '已经' + kindLabel;
                    btn.disabled = true;
                    btn.setAttribute('aria-disabled', 'true');
                    btn.title = '这篇文章已经' + kindLabel + '啦，无需再次申请';
                } else if (state === 'pending') {
                    btn.textContent = '⏳ ' + kindLabel + '审核中';
                    btn.disabled = true;
                    btn.setAttribute('aria-disabled', 'true');
                    btn.title = kindLabel + '申请正在审核中，请耐心等待';
                } else {
                    btn.textContent = '申请' + kindLabel;
                    btn.disabled = false;
                    btn.removeAttribute('aria-disabled');
                    btn.title = '点这里申请把文章' + (kindLabel === '精华' ? '加精' : kindLabel === '热门' ? '加入热门' : kindLabel) ;
                }
            }

            /* Bug8：提交后按服务端真实状态回填三个按钮（防止前端状态与服务端漂移） */
            function refreshStates(cb) {
                if (!statusUrl || !window.fetch) { if (cb) cb(); return; }
                fetch(statusUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' },
                                   credentials: 'same-origin' })
                    .then(function (r) { return r.json(); })
                    .then(function (j) {
                        var st = (j && j.data && j.data.states) || null;
                        if (!st) { if (cb) cb(); return; }
                        Object.keys(st).forEach(function (kind) {
                            var btn = apply.querySelector('.promo-apply-btn[data-kind="' + kind + '"]');
                            paintButton(btn, st[kind].state, st[kind].label);
                        });
                        if (cb) cb();
                    }).catch(function () { if (cb) cb(); });
            }

            function openModal(kind, label) {
                currentKind = kind;
                kindInput.textContent = label;
                reasonInput.value = '';
                modal.hidden = false;
                document.body.classList.add('modal-open');
                setTimeout(function () { reasonInput.focus(); }, 50);
            }
            function closeModal() {
                modal.hidden = true;
                document.body.classList.remove('modal-open');
            }
            apply.addEventListener('click', function (e) {
                var btn = e.target.closest('.promo-apply-btn');
                if (!btn) return;
                // Bug8：已生效 / 审核中的按钮不可再点（disabled 已拦截，这里再兜底一次）
                if (btn.disabled || btn.dataset.state === 'applied' || btn.dataset.state === 'pending') {
                    if (window.moeToast) {
                        moeToast(btn.dataset.state === 'applied'
                            ? '这篇文章已经' + btn.dataset.label + '啦，不用再申请喵~'
                            : btn.dataset.label + '申请正在审核中，请耐心等待喵~', 'info');
                    }
                    return;
                }
                currentBtn = btn;
                openModal(btn.dataset.kind, btn.dataset.label);
            });
            // 点遮罩 / 取消按钮关闭
            modal.addEventListener('click', function (e) {
                if (e.target.closest('[data-promo-close]')) closeModal();
            });
            // Esc 关闭
            document.addEventListener('keydown', function (e) {
                if (e.key === 'Escape' && !modal.hidden) closeModal();
            });
            submitBtn.addEventListener('click', function () {
                var reason = reasonInput.value.trim();
                if (!reason) {
                    if (window.moeToast) moeToast('请先填写申请理由喵~', 'info');
                    reasonInput.focus();
                    return;
                }
                postForm(requestUrl, { kind: currentKind, reason: reason }, function (j) {
                    if (j.code === 0) {
                        closeModal();
                        // Bug8：申请成功后立刻把按钮改为「审核中」并禁用，避免重复提交
                        paintButton(currentBtn, 'pending',
                            (currentBtn && currentBtn.dataset.label) || '');
                        if (window.moeToast) moeToast(j.msg || '申请已提交~', j.notice ? 'info' : 'success');
                        refreshStates();
                    } else {
                        // 409（已生效 / 已在审核中）时同步服务端真实状态
                        if (j.code === 409) refreshStates();
                        if (window.moeToast) moeToast(j.msg || '提交失败~', 'error');
                    }
                });
            });
            // 首次进页面自检一次，确保按钮状态与服务端一致
            refreshStates();
        }
    }

    /* ----------------------------------------------------------
     * 初始化
     * -------------------------------------------------------- */
    function ready(fn) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn);
        } else { fn(); }
    }
    ready(function () {
        initQuickMenu();
        initTagNoDrag();
        initHotRankTabs();
        initBrokenImageFallback();
        initCoverPicker();
        initReplyCollapse();
        initPromotion();
    });
})();

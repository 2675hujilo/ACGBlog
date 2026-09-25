/* Bug11 文件头注释
 * 全站公共脚本：页面通用工具与初始化，所有页面加载。
 * 主要逻辑：①工具提示 initTooltip（Bug9 已改浅色系）；②moeToast 右下角轻提示并暴露到 window；
 * ③相对时间格式化；④通用 fetch/CSRF 封装；⑤主题、菜单等公共交互的初始化。
 */
﻿/**
 * common.js —— 全站通用前端交互脚本（瘦身版）
 *
 * 功能：
 *   1. 顶部阅读进度条：随滚动实时更新宽度
 *   2. 回到顶部按钮：滚动超过 400px 显示，带环形进度
 *   3. Flash 消息自动淡出
 *   4. 骨架屏隐藏：DOM 就绪后渐隐
 *   5. 数字滚动动画：[data-count] 从 0 滚动到目标值
 *   6. 入场动画：IntersectionObserver 观察 .animate-in
 *   7. 按钮涟漪效果（事件委托）
 *   8. 搜索自动补全：debounce 300ms，键盘上下选择
 *   9. 快捷键盘导航：j/k 移动文章，/ 聚焦搜索，gg 回顶，? 帮助
 *  10. 图片加载失败占位：粉紫蓝渐变 SVG
 *  11. 全局自定义 tooltip：hover 300ms 淡入
 *
 * 依赖：无（纯原生 JS）
 * 注：暗黑模式切换由 theme.js 独立负责，本文件不再重复绑定 #theme-toggle
 */
(function () {
    'use strict';

    /* ====== 阅读进度 / 回到顶部 / Flash 淡出 ====== */
    var progress = document.getElementById('reading-progress');
    var topBtn = document.getElementById('back-to-top');
    var header = document.querySelector('.site-header');
    var ringFg = topBtn ? topBtn.querySelector('.btt-ring-fg') : null;
    var RING_LEN = 2 * Math.PI * 22;

    function onScroll() {
        var doc = document.documentElement;
        var total = doc.scrollHeight - doc.clientHeight;
        var ratio = total > 0 ? (doc.scrollTop || document.body.scrollTop) / total : 0;
        if (progress) progress.style.width = Math.round(ratio * 100) + '%';
        if (topBtn) topBtn.classList.toggle('show', doc.scrollTop > 400);
        if (ringFg) {
            ringFg.style.strokeDasharray = RING_LEN;
            ringFg.style.strokeDashoffset = RING_LEN * (1 - ratio);
        }
        if (header) header.classList.toggle('scrolled', doc.scrollTop > 50);
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    if (topBtn) {
        topBtn.addEventListener('click', function () {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    document.querySelectorAll('.flash').forEach(function (el) {
        setTimeout(function () {
            el.style.transition = 'opacity .6s';
            el.style.opacity = '0';
            setTimeout(function () { el.remove(); }, 700);
        }, 4000);
    });

    /* ====== 骨架屏隐藏 ====== */
    function hideSkeleton() {
        document.querySelectorAll('.skeleton-wrap').forEach(function (w) {
            w.classList.add('hidden');
            setTimeout(function () { w.remove(); }, 450);
        });
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', hideSkeleton);
    } else {
        hideSkeleton();
    }

    /* ====== 数字滚动动画 ====== */
    function animateNumber(el, target, duration) {
        var start = null;
        function step(ts) {
            if (start === null) start = ts;
            var ratio = Math.min((ts - start) / duration, 1);
            var eased = 1 - Math.pow(1 - ratio, 3);
            el.textContent = Math.round(target * eased).toLocaleString('en-US');
            if (ratio < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
    }
    function initAnimatedNumbers() {
        document.querySelectorAll('[data-count]').forEach(function (el) {
            animateNumber(el, parseInt(el.getAttribute('data-count'), 10) || 0, 1200);
        });
    }

    /* ====== 入场动画 IntersectionObserver ====== */
    function initEntranceObserver() {
        var items = document.querySelectorAll('.animate-in, .scroll-fade-in');
        if (!items.length) return;
        if (!('IntersectionObserver' in window)) {
            items.forEach(function (el) { el.classList.add('visible'); });
            return;
        }
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    io.unobserve(entry.target);
                }
            });
        }, { threshold: 0.05 });
        items.forEach(function (el) { io.observe(el); });
    }

    /* ====== 按钮涟漪效果 ====== */
    function initRipple() {
        document.addEventListener('click', function (e) {
            var target = e.target.closest('button, .btn-primary, .page-link, .like-btn, .fav-btn, .btn-sm');
            if (!target) return;
            var rect = target.getBoundingClientRect();
            var size = Math.max(rect.width, rect.height);
            var span = document.createElement('span');
            span.className = 'ripple';
            span.style.width = span.style.height = size + 'px';
            span.style.left = ((e.clientX ? e.clientX - rect.left : rect.width / 2) - size / 2) + 'px';
            span.style.top = ((e.clientY ? e.clientY - rect.top : rect.height / 2) - size / 2) + 'px';
            target.appendChild(span);
            span.addEventListener('animationend', function () { span.remove(); });
        });
    }

    /* ====== 搜索自动补全 ====== */
    function initSearchSuggest() {
        var form = document.querySelector('.nav-search');
        if (!form) return;
        var input = form.querySelector('input[name="q"]');
        if (!input) return;
        var list = document.createElement('ul');
        list.className = 'search-suggestions';
        form.appendChild(list);
        var debounceTimer = null, activeIndex = -1;

        function renderItems(items) {
            list.innerHTML = '';
            if (!items.length) { list.classList.remove('show'); return; }
            items.forEach(function (text) {
                var li = document.createElement('li');
                li.textContent = text;
                li.addEventListener('mousedown', function (e) {
                    e.preventDefault();
                    input.value = text;
                    list.classList.remove('show');
                    form.submit();
                });
                list.appendChild(li);
            });
            list.classList.add('show');
            activeIndex = -1;
        }
        function fetchSuggest() {
            var q = input.value.trim();
            if (!q) { list.classList.remove('show'); return; }
            fetch('/api/search/suggest/?q=' + encodeURIComponent(q))
                .then(function (r) { return r.json(); })
                .then(function (data) { renderItems(data.suggestions || []); })
                .catch(function () { list.classList.remove('show'); });
        }
        input.addEventListener('input', function () {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(fetchSuggest, 300);
        });
        input.addEventListener('keydown', function (e) {
            var items = list.querySelectorAll('li');
            if (e.key === 'ArrowDown' && items.length) {
                e.preventDefault(); activeIndex = (activeIndex + 1) % items.length;
            } else if (e.key === 'ArrowUp' && items.length) {
                e.preventDefault(); activeIndex = (activeIndex - 1 + items.length) % items.length;
            } else if (e.key === 'Enter') {
                if (activeIndex >= 0 && items[activeIndex]) {
                    input.value = items[activeIndex].textContent;
                    list.classList.remove('show');
                }
                return;
            } else if (e.key === 'Escape') {
                list.classList.remove('show');
            } else { return; }
            items.forEach(function (li, i) { li.classList.toggle('active', i === activeIndex); });
        });
        document.addEventListener('click', function (e) {
            if (!form.contains(e.target)) list.classList.remove('show');
        });
    }

    /* ====== 快捷键盘导航 ====== */

    /* ====== 键盘快捷键帮助面板（? 键与导航栏 ⌨ 按钮共用，全局单例） ====== */
    var kbdHelpEl = null;
    function getKbdHelp() {
        if (kbdHelpEl) return kbdHelpEl;
        kbdHelpEl = document.createElement('div');
        kbdHelpEl.className = 'kbd-help';
        kbdHelpEl.setAttribute('role', 'dialog');
        kbdHelpEl.setAttribute('aria-label', '键盘快捷键');
        kbdHelpEl.innerHTML =
            '<div class="kbd-help-card">' +
            '<div class="kbd-help-head"><strong>⌨️ 键盘快捷键喵</strong><button type="button" class="kbd-help-close" aria-label="关闭">×</button></div>' +
            '<div class="kbd-help-grid">' +
            '<div class="kbd-row"><kbd>j</kbd><kbd>k</kbd><span>下移 / 上移文章</span></div>' +
            '<div class="kbd-row"><kbd>Enter</kbd><span>打开高亮文章</span></div>' +
            '<div class="kbd-row"><kbd>/</kbd><span>聚焦搜索框</span></div>' +
            '<div class="kbd-row"><kbd>g</kbd><kbd>g</kbd><span>回到顶部</span></div>' +
            '<div class="kbd-row"><kbd>?</kbd><span>显示 / 隐藏本面板</span></div>' +
            '<div class="kbd-row"><kbd>Esc</kbd><span>关闭弹窗 / 取消输入</span></div>' +
            '</div></div>';
        document.body.appendChild(kbdHelpEl);
        // 点击遮罩或关闭按钮收起
        kbdHelpEl.addEventListener('click', function (e) {
            if (e.target === kbdHelpEl || e.target.closest('.kbd-help-close')) {
                kbdHelpEl.classList.remove('show');
            }
        });
        return kbdHelpEl;
    }
    function toggleKbdHelp(force) {
        var h = getKbdHelp();
        var show = (typeof force === 'boolean') ? force : !h.classList.contains('show');
        h.classList.toggle('show', show);
        if (show) { var b = h.querySelector('.kbd-help-close'); if (b) b.focus(); }
        return show;
    }

    function initKeyboardNav() {
        var focusedIndex = -1, gPressedAt = 0;
        function isTyping() {
            var el = document.activeElement;
            return el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable);
        }
        function getCards() {
            return Array.prototype.slice.call(document.querySelectorAll('.article-card'));
        }
        function moveFocus(dir) {
            var cards = getCards();
            if (!cards.length) return;
            cards.forEach(function (c) { c.classList.remove('keyboard-focus'); });
            focusedIndex = Math.max(0, Math.min(focusedIndex + dir, cards.length - 1));
            var card = cards[focusedIndex];
            card.classList.add('keyboard-focus');
            card.scrollIntoView({ block: 'center', behavior: 'smooth' });
        }
        document.addEventListener('keydown', function (e) {
            if (isTyping()) {
                if (e.key === 'Escape') {
                    document.activeElement.blur();
                    document.querySelectorAll('.search-suggestions.show').forEach(function (l) { l.classList.remove('show'); });
                }
                return;
            }
            var key = e.key;
            if (key === 'j') { e.preventDefault(); moveFocus(1); }
            else if (key === 'k') { e.preventDefault(); moveFocus(-1); }
            else if (key === '/') {
                e.preventDefault();
                var s = document.querySelector('.nav-search input[name="q"]');
                if (s) s.focus();
            } else if (key === 'g') {
                var now = Date.now();
                if (now - gPressedAt < 500) window.scrollTo({ top: 0, behavior: 'smooth' });
                gPressedAt = now;
            } else if (key === 'Enter' && focusedIndex >= 0) {
                var card = getCards()[focusedIndex];
                var link = card && card.querySelector('a[href]');
                if (link) { e.preventDefault(); window.location.href = link.href; }
            } else if (key === '?') {
                e.preventDefault(); toggleKbdHelp();
            } else if (key === 'Escape') {
                var h = document.querySelector('.kbd-help.show');
                if (h) h.classList.remove('show');
                document.querySelectorAll('.search-suggestions.show').forEach(function (l) { l.classList.remove('show'); });
            }
        });
    }

    /* ====== 图片加载失败占位 ====== */
    function initImageFallback() {
        var svg = function (w, h) {
            return 'data:image/svg+xml;utf8,' + encodeURIComponent(
                '<svg xmlns="http://www.w3.org/2000/svg" width="' + (w || 300) +
                '" height="' + (h || 200) + '">' +
                '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">' +
                '<stop offset="0" stop-color="#ff8fb1"/><stop offset=".5" stop-color="#a06cd5"/>' +
                '<stop offset="1" stop-color="#6ea8fe"/></linearGradient></defs>' +
                '<rect width="100%" height="100%" fill="url(#g)"/>' +
                '<text x="50%" y="46%" font-size="28" text-anchor="middle" fill="#fff">\ud83d\uddbc\ufe0f</text>' +
                '<text x="50%" y="62%" font-size="13" text-anchor="middle" fill="#fff">\u56fe\u7247\u52a0\u8f7d\u5931\u8d25</text>' +
                '</svg>');
        };
        document.addEventListener('error', function (e) {
            var t = e.target;
            if (t && t.tagName === 'IMG' && !t.dataset.fbDone) {
                t.dataset.fbDone = '1';
                t.src = svg(t.naturalWidth || t.width, t.naturalHeight || t.height);
            }
        }, true);
    }

    /* ====== 全局自定义 tooltip ====== */
    function initTooltip() {        var tip = null;
        function ensure() {
            if (tip) return tip;
            tip = document.createElement('div');
            tip.className = 'ui-tooltip';
            // Bug9：兜底气泡改为浅色系（近白→浅薰衣草，深紫字），与 moe-tooltip 看板娘配色统一
            tip.style.cssText = 'position:fixed;z-index:9999;pointer-events:none;opacity:0;' +
                'transition:opacity .2s;background:linear-gradient(135deg,rgba(255,255,255,.98),rgba(253,244,255,.98));' +
                'color:#6b21a8;border:1px solid #e9d5ff;padding:6px 12px;' +
                'border-radius:999px;font-size:12px;white-space:max-content;box-shadow:0 6px 20px rgba(168,85,247,.22);';
            document.body.appendChild(tip);
            return tip;
        }
        function show(el, text) {
            var t = ensure();
            t.textContent = text;
            t.style.opacity = '1';
            var r = el.getBoundingClientRect();
            t.style.left = (r.left + r.width / 2 - t.offsetWidth / 2) + 'px';
            t.style.top = (r.top - t.offsetHeight - 8) + 'px';
        }
        document.addEventListener('mouseover', function (e) {
            var el = e.target.closest('[title]');
            if (el && el.title) {
                show(el, el.title);
                el.dataset._tt = el.title;
                el.removeAttribute('title');
            }
        });
        document.addEventListener('mouseout', function (e) {
            var el = e.target.closest('[data-_tt]');
            if (el) {
                if (tip) tip.style.opacity = '0';
                el.setAttribute('title', el.dataset._tt);
                delete el.dataset._tt;
            }
        });
    }

    /* ====== 双击空白区域回顶（第3轮新增） ====== */
    function initDoubleClickTop() {
        function showToast(msg) {
            var t = document.getElementById('global-toast');
            if (!t) {
                t = document.createElement('div');
                t.id = 'global-toast';
                document.body.appendChild(t);
            }
            t.textContent = msg;
            t.classList.add('show');
            clearTimeout(t._timer);
            t._timer = setTimeout(function () { t.classList.remove('show'); }, 1500);
        }
        document.addEventListener('dblclick', function (e) {
            // 忽略交互元素 / 弹窗 / 灯箱 / 卡片内的双击
            if (e.target.closest('a, button, input, textarea, select, [contenteditable], ' +
                '.modal, .lightbox-overlay, .read-progress-bar, .kbd-help, .article-card, ' +
                '.comment-item, .preview-modal, .nav-bar, .site-header')) return;
            // 有选中文本时不干扰（如双击选词）
            var sel = window.getSelection && window.getSelection();
            if (sel && sel.toString().length) return;
            // 页面较顶部无需回顶
            if (window.scrollY < 300) return;
            window.scrollTo({ top: 0, behavior: 'smooth' });
            showToast('双击回到顶部喵~ 🐾');
        });
    }


    /* ====== 通用折叠面板：点击 [data-collapse-target] 切换目标面板（按钮始终保留，不会把自身隐藏） ====== */
    function initCollapse() {
        document.addEventListener('click', function (e) {
            var btn = e.target.closest('[data-collapse-target]');
            if (!btn) return;
            if (btn.getAttribute('data-busy') === '1') return;
            var id = btn.getAttribute('data-collapse-target');
            var panel = document.getElementById(id);
            if (!panel) return;
            e.preventDefault();
            var willOpen = panel.hasAttribute('hidden');
            if (willOpen) { panel.removeAttribute('hidden'); } else { panel.setAttribute('hidden', ''); }
            btn.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
            // 切换 caret 文案（若提供 data-text-open / data-text-closed）
            var caret = btn.querySelector('[data-text-open]');
            if (caret) { caret.textContent = willOpen ? caret.getAttribute('data-text-open') : caret.getAttribute('data-text-closed'); }
            btn.classList.toggle('is-open', willOpen);
        });
    }


    /* ====== 导航栏辅助开关：交互音效 / 高对比度 / 快捷键面板按钮 ====== */
    function initNavToggles() {
        /* ---------- Bug6 交互音效（Web Audio，localStorage 持久化） ---------- */
        var soundBtn = document.getElementById('sound-toggle');
        var soundOn = true;
        try { soundOn = localStorage.getItem('moe_sound') !== '0'; } catch (e) {}
        var actx = null;
        function playTone(freq, dur) {
            if (!soundOn) return;
            try {
                actx = actx || new (window.AudioContext || window.webkitAudioContext)();
                if (actx.state === 'suspended') actx.resume();
                var o = actx.createOscillator(), g = actx.createGain();
                o.type = 'sine'; o.frequency.value = freq;
                o.connect(g); g.connect(actx.destination);
                var t = actx.currentTime;
                g.gain.setValueAtTime(0.0001, t);
                g.gain.exponentialRampToValueAtTime(0.05, t + 0.01);
                g.gain.exponentialRampToValueAtTime(0.0001, t + (dur || 0.09));
                o.start(t); o.stop(t + (dur || 0.1));
            } catch (e) {}
        }
        window.moePlayTone = playTone;   // 暴露给其他脚本复用
        function syncSound() {
            if (!soundBtn) return;
            soundBtn.textContent = soundOn ? '\uD83D\uDD0A' : '\uD83D\uDD07';
            soundBtn.classList.toggle('off', !soundOn);
            soundBtn.setAttribute('aria-pressed', soundOn ? 'false' : 'true');
            soundBtn.title = soundOn ? '交互音效：开（点击关闭）喵' : '交互音效：关（点击开启）喵';
        }
        if (soundBtn) {
            syncSound();
            soundBtn.addEventListener('click', function () {
                soundOn = !soundOn;
                try { localStorage.setItem('moe_sound', soundOn ? '1' : '0'); } catch (e) {}
                syncSound();
                if (soundOn) playTone(660, 0.1);   // 开启时给一声提示
            });
            // 全局轻量点击音（按钮 / 链接 / 可点击元素）
            document.addEventListener('click', function (e) {
                if (!soundOn) return;
                if (e.target.closest && e.target.closest('button, a, [role="button"], .clickable, .chip, .corner-badge')) {
                    playTone(500 + Math.random() * 90, 0.05);
                }
            });
            // 输入打字音
            document.addEventListener('keydown', function (e) {
                if (!soundOn) return;
                var el = document.activeElement;
                if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable) && e.key.length === 1) {
                    playTone(860 + Math.random() * 140, 0.03);
                }
            });
        }

        /* ---------- Bug8 高对比度模式 ---------- */
        var contrastBtn = document.getElementById('contrast-toggle');
        var contrastOn = false;
        try { contrastOn = localStorage.getItem('moe_contrast') === '1'; } catch (e) {}
        function syncContrast() {
document.documentElement.classList.toggle('high-contrast', contrastOn);
            if (document.body) document.body.classList.toggle('high-contrast', contrastOn);
            if (contrastBtn) {
                contrastBtn.classList.toggle('active', contrastOn);
                contrastBtn.setAttribute('aria-pressed', contrastOn ? 'true' : 'false');
                contrastBtn.title = contrastOn ? '高对比度：开（点击关闭）' : '高对比度：关（点击开启）';
            }
        }
        if (contrastBtn) {
            syncContrast();
            contrastBtn.addEventListener('click', function () {
                contrastOn = !contrastOn;
                try { localStorage.setItem('moe_contrast', contrastOn ? '1' : '0'); } catch (e) {}
                syncContrast();
                if (window.moePlayTone) window.moePlayTone(contrastOn ? 720 : 480, 0.08);
            });
        }

        /* ---------- Bug9 快捷键帮助面板按钮 ---------- */
        var scBtn = document.getElementById('shortcut-help-toggle');
        if (scBtn) {
            scBtn.addEventListener('click', function () { toggleKbdHelp(); });
        }
        // Esc 统一关闭快捷键面板
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                var h = document.querySelector('.kbd-help.show');
                if (h) h.classList.remove('show');
            }
        });
    }

    /* 工单选中态：已废弃 bakeActiveStates「先置 transparent 再两帧后重绘」hack。
       该 hack 正是三处选中态问题的根因——首页紫色选中态闪烁、我的文章选中白字、
       内容审核先白后紫；现代 Chrome/Edge 已无入场合成首帧冻结问题，直接移除。 */
    function bakeActiveStates(root) { /* 空操作，仅为兼容保留 */ }

    /* ====== Bug8：全站统一「轻提示 toast」与「确认弹窗 modal」，替代原生 alert / confirm ======
       - moeToast(msg, type)：右下角（移动端底部）轻提示，1.8s 自动消失，不打断操作；
         type 可选 'info'（默认）/ 'success' / 'error'。
       - moeConfirm({title,message,confirmText,cancelText,danger})：返回 Promise<bool>，
         柔和粉紫萌系对话框，Esc / 遮罩 = 取消；danger=true 时确认按钮为珊瑚红。
       - 声明式用法（推荐模板使用）：
           <form data-confirm="真的要收进回收站吗？" data-confirm-danger> ...
           <a data-confirm="..."> ... </a>
         全局事件委托自动拦截，确认后才继续提交 / 跳转。 */
    function ensureToast() {
        var t = document.getElementById('global-toast');
        if (!t) {
            t = document.createElement('div');
            t.id = 'global-toast';
            t.setAttribute('role', 'status');
            document.body.appendChild(t);
        }
        return t;
    }
    function moeToast(msg, type) {
        var t = ensureToast();
        t.textContent = msg;
        t.className = 'show' + (type ? ' toast-' + type : '');
        clearTimeout(t._timer);
        t._timer = setTimeout(function () { t.className = t.className.replace('show', '').trim(); }, 1900);
    }
    window.moeToast = moeToast;

    function moeConfirm(opts) {
        opts = opts || {};
        return new Promise(function (resolve) {
            var modal = document.getElementById('globalConfirmModal');
            // 极端兜底：页面缺少预置弹窗时不阻塞流程（正常 base.html 一定包含）
            if (!modal) { resolve(true); return; }
            ensureModalCss();
            modal.querySelector('#gcmTitle').textContent = opts.title || '请确认喵~';
            modal.querySelector('#gcmMsg').textContent = opts.message || '';
            var cancel = modal.querySelector('#gcmCancel');
            var ok = modal.querySelector('#gcmOk');
            cancel.textContent = opts.cancelText || '再想想';
            ok.textContent = opts.confirmText || '确定喵';
            ok.style.background = opts.danger
                ? 'linear-gradient(135deg,#ff7a8a,#ff5d73)'
                : 'linear-gradient(135deg,#ff8fb1,#a06cd5)';
            var cleanup = function () {
                modal.classList.remove('show');
                document.removeEventListener('keydown', onKey, true);
                cancel.onclick = null; ok.onclick = null; modal.onclick = null;
            };
            function onKey(e) {
                if (e.key === 'Escape') { e.stopPropagation(); cleanup(); resolve(false); }
            }
            cancel.onclick = function () { cleanup(); resolve(false); };
            ok.onclick = function () { cleanup(); resolve(true); };
            modal.onclick = function (e) { if (e.target === modal) { cleanup(); resolve(false); } };
            document.addEventListener('keydown', onKey, true);
            // 预置在初始 DOM 中的弹窗，直接加 .show（display:none→flex），可靠绘制
            modal.classList.add('show');
            setTimeout(function () { ok.focus(); }, 30);
        });
    }
    window.moeConfirm = moeConfirm;

    // 弹窗 / toast 所需样式（仅注入一次，内联自包含，跟随站点圆角与粉紫基调）
    // 注意：#global-toast 必须显式 top:auto/left:auto/width:auto/height:auto，
    // 否则 round6.css 的 top:76px/left:50% 会与这里的 bottom:24px 同时生效，
    // 固定定位元素被纵向拉伸成贯穿屏幕的巨型框（bug7 怪框复发根因）
    var _tipCssAdded = false;
    function tipCss() {
        var st = document.createElement('style');
        st.setAttribute('data-moe-modal-css', '1');
        st.textContent = [
            '#global-toast{position:fixed;top:84px;left:50%;right:auto;bottom:auto;width:auto;height:auto;z-index:10000;max-width:90vw;',
            'background:var(--c-card,#fff);color:var(--c-text,#3a2f55);padding:10px 18px;',
            'border:1.5px solid #7a5fc0;border-radius:14px;font-size:13px;font-weight:600;',
            'box-shadow:0 12px 30px rgba(80,60,120,.22);opacity:0;transform:translate(-50%,-14px);',
            'transition:opacity .25s,transform .25s;pointer-events:none;}',
            '#global-toast.show{opacity:1;transform:translate(-50%,0);}',
            '#global-toast.toast-info{border-color:#7a5fc0;color:#6a4fb0;}',
            '#global-toast.toast-success{border-color:#3aa77a;color:#2a8a63;background:#f2fbf7;}',
            '#global-toast.toast-error{border-color:#ef5d6b;color:#d84454;background:#fff1f2;}',
            '.moe-modal-overlay{position:fixed;inset:0;z-index:10001;display:none;align-items:center;justify-content:center;',
            'padding:20px;background:rgba(60,45,90,.34);backdrop-filter:blur(4px);}',
            '.moe-modal-overlay.show{display:flex;}',
            '.moe-modal-card{width:min(420px,92vw);background:var(--c-surface,#fff);border-radius:20px;',
            'padding:24px 24px 20px;box-shadow:0 24px 60px rgba(80,60,120,.32);}',
            '.moe-modal-title{font-size:17px;font-weight:700;color:var(--c-text,#333);margin-bottom:8px;}',
            '.moe-modal-msg{font-size:14px;line-height:1.7;color:var(--c-text-sub,#666);white-space:pre-wrap;word-break:break-word;}',
            '.moe-modal-actions{display:flex;justify-content:flex-end;gap:10px;margin-top:20px;}',
            '.moe-btn{border:none;cursor:pointer;border-radius:12px;padding:9px 18px;font-size:14px;font-weight:600;}',
            '.moe-btn-cancel{background:var(--c-card,#f1eef8);color:var(--c-text-sub,#777);}',
            '.moe-btn-ok{color:#fff;box-shadow:0 8px 18px rgba(160,108,213,.32);}',
            '.notification-item{display:flex;gap:9px;cursor:pointer;align-items:flex-start;}',
            '.notification-item .ni-icon{font-size:15px;line-height:1.3;}',
            '.notification-item .ni-body{display:flex;flex-direction:column;gap:2px;min-width:0;flex:1;}',
            '.notification-item .ni-title{font-size:.84rem;line-height:1.4;color:var(--c-text,#333);}',
            '.notification-item .ni-time{font-size:.72rem;color:var(--c-text-sub,#999);}',
            '.notification-item.unread{background:linear-gradient(90deg,rgba(255,143,177,.14),transparent);}',
            '.notification-item.unread .ni-title{font-weight:700;}',
            '.notification-item.unread .ni-title::after{content:"";display:inline-block;width:7px;height:7px;border-radius:50%;background:#ff5d73;margin-left:6px;vertical-align:middle;}',
            '.notification-item.muted{justify-content:center;color:var(--c-text-sub,#999);cursor:default;}',
            '@media (max-width:560px){#global-toast{top:76px;left:16px;right:16px;max-width:none;transform:translateY(-14px);text-align:center;}#global-toast.show{transform:translateY(0);}}'
        ].join('');
        return st;
    }
    function ensureModalCss() {
        if (_tipCssAdded || document.querySelector('[data-moe-modal-css]')) { _tipCssAdded = true; return; }
        document.body.appendChild(tipCss());
        _tipCssAdded = true;
    }

    // 声明式 data-confirm：拦截表单提交
    document.addEventListener('submit', function (e) {
        var form = e.target;
        if (form && form.hasAttribute && form.hasAttribute('data-confirm') && !form.dataset.confirmed) {
            e.preventDefault();
            ensureModalCss();
            moeConfirm({
                message: form.getAttribute('data-confirm'),
                danger: form.hasAttribute('data-confirm-danger'),
                confirmText: form.getAttribute('data-confirm-ok') || '确定喵'
            }).then(function (ok) {
                if (ok) { form.dataset.confirmed = '1'; form.submit(); }
            });
        }
    }, true);
    // 声明式 data-confirm：拦截链接 / 按钮点击
    document.addEventListener('click', function (e) {
        var el = e.target.closest && e.target.closest('[data-confirm]');
        if (!el || el.tagName === 'FORM' || el.dataset.confirmed) return;
        e.preventDefault();
        ensureModalCss();
        moeConfirm({
            message: el.getAttribute('data-confirm'),
            danger: el.hasAttribute('data-confirm-danger'),
            confirmText: el.getAttribute('data-confirm-ok') || '确定喵'
        }).then(function (ok) {
            if (!ok) return;
            el.dataset.confirmed = '1';
            if (el.tagName === 'A' && el.href) { window.location.href = el.href; }
            else { el.click(); }
        });
    }, true);

    /* ====== Bug9：导航铃铛下拉，接入真实通知数据 ====== */
    function initNotificationBell() {
        var bell = document.getElementById('notification-bell');
        var panel = document.getElementById('notification-panel');
        var list = document.getElementById('notification-list');
        var markAll = document.getElementById('notification-mark-all');
        var badge = document.getElementById('notification-badge');
        if (!bell || !panel || !list) return;
        var loaded = false;
        var mainEl = document.getElementById('main-content') || document.querySelector('.site-main');
        // header 合成面不会重绘“加载后才出现”的子元素（首帧冻结），故把下拉移入
        // <main> 合成面并改为 fixed，按铃铛坐标定位，确保可靠绘制。
        if (mainEl) {
            mainEl.appendChild(panel);
            panel.style.position = 'fixed';
            panel.style.right = 'auto';
            panel.style.top = 'auto';
        }
        function place() {
            if (!mainEl) return;
            var r = bell.getBoundingClientRect();
            var w = 320;
            var wantLeft = Math.min(r.right - w, innerWidth - w - 12);
            wantLeft = Math.max(12, wantLeft);
            // 工单16：main 残留 identity transform 成为 fixed 包含块，
            // 求包含块原点并扣除，保证面板稳定落在铃铛正下方（视口坐标）。
            var ox = 0, oy = 0, node = panel.parentElement;
            while (node && node.nodeType === 1) {
                var cs = getComputedStyle(node);
                if ((cs.transform && cs.transform !== 'none') ||
                    (cs.filter && cs.filter !== 'none') ||
                    (cs.perspective && cs.perspective !== 'none')) {
                    var br = node.getBoundingClientRect();
                    ox = br.left; oy = br.top; break;
                }
                node = node.parentElement;
            }
            panel.style.left = (wantLeft - ox) + 'px';
            panel.style.top = (r.bottom + 8 - oy) + 'px';
        }

        function csrf() {
            var m = document.cookie.match(/csrftoken=([^;]+)/);
            return m ? m[1] : '';
        }
        function iconFor(t) {
            return t === 'reply' ? '💬' : t === 'mention' ? '🏷'
                : t === 'like' ? '👍' : t === 'article' ? '📄' : '🔔';
        }
        function relTime(iso) {
            var d = new Date(iso), diff = (Date.now() - d.getTime()) / 1000;
            if (diff < 60) return '刚刚';
            if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前';
            if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前';
            if (diff < 2592000) return Math.floor(diff / 86400) + ' 天前';
            return d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate();
        }
        function setBadge(n) {
            if (!badge) return;
            if (n > 0) { badge.textContent = n > 99 ? '99+' : n; badge.style.display = ''; }
            else { badge.style.display = 'none'; }
        }
        function render(results) {
            list.innerHTML = '';
            if (!results || !results.length) {
                var li = document.createElement('li');
                li.className = 'notification-item muted';
                li.textContent = '这里还没有通知喵~';
                list.appendChild(li);
                return;
            }
            results.forEach(function (n) {
                var li = document.createElement('li');
                li.className = 'notification-item' + (n.is_read ? '' : ' unread');
                li.setAttribute('data-id', n.id);
                li.setAttribute('data-url', n.related_url || '');
                li.innerHTML =
                    '<span class="ni-icon">' + iconFor(n.type) + '</span>' +
                    '<span class="ni-body"><span class="ni-title"></span>' +
                    '<span class="ni-time">' + relTime(n.created_at) + '</span></span>';
                li.querySelector('.ni-title').textContent = n.title;
                li.addEventListener('click', function () {
                    var go = function () {
                        var u = li.getAttribute('data-url');
                        if (u) window.location.href = u; else window.location.href = '/notifications/';
                    };
                    if (!n.is_read) {
                        fetch('/api/notifications/' + n.id + '/read/', {
                            method: 'POST', headers: { 'X-CSRFToken': csrf() }, credentials: 'same-origin'
                        }).then(go).catch(go);
                    } else { go(); }
                });
                list.appendChild(li);
            });
        }
        function load() {
            fetch('/api/notifications/?page_size=6', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(function (r) {
                    if (r.status === 401) { window.location.href = '/notifications/'; return null; }
                    return r.json();
                })
                .then(function (d) {
                    if (!d) return;
                    var res = d.results || (d.data && d.data.results) || [];
                    render(res);
                    var unread = res.filter(function (x) { return !x.is_read; }).length;
                    setBadge(unread);
                    loaded = true;
                })
                .catch(function () {
                    list.innerHTML = '';
                    var li = document.createElement('li');
                    li.className = 'notification-item muted';
                    li.textContent = '通知加载失败，点底部查看全部~';
                    list.appendChild(li);
                });
        }
        function openPanel() {
            place();
            panel.hidden = false;
            bell.setAttribute('aria-expanded', 'true');
            if (!loaded) load();
        }
        function closePanel() {
            panel.hidden = true;
            bell.setAttribute('aria-expanded', 'false');
        }
        function togglePanel() {
            if (panel.hidden) openPanel(); else closePanel();
        }
        bell.addEventListener('click', function (e) { e.stopPropagation(); togglePanel(); });
        panel.addEventListener('click', function (e) { e.stopPropagation(); });
        if (markAll) {
            markAll.addEventListener('click', function () {
                fetch('/api/notifications/read_all/', {
                    method: 'POST', headers: { 'X-CSRFToken': csrf() }, credentials: 'same-origin'
                }).then(function () {
                    setBadge(0);
                    list.querySelectorAll('.notification-item.unread').forEach(function (x) {
                        x.classList.remove('unread');
                    });
                });
            });
        }
        window.addEventListener('resize', function () { if (!panel.hidden) place(); });
        window.addEventListener('scroll', function () { if (!panel.hidden) place(); }, true);
        document.addEventListener('click', function () { if (!panel.hidden) closePanel(); });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && !panel.hidden) closePanel();
        });
    }

    /* ====== 初始化 ====== */
    function init() {
        ensureModalCss();   // 预置弹窗在初始 DOM，需先有样式才会 display:none
        initNotificationBell();
        initAnimatedNumbers();
        initEntranceObserver();
        initRipple();
        initSearchSuggest();
        initKeyboardNav();
        initImageFallback();
        initTooltip();
        initDoubleClickTop();
        initCollapse();
        initNavToggles();
        // 工单选中态：不再做「透明→重绘」烘焙（消除闪烁/白字/延迟）
        window.moeBakeActive = function () {};  // 兼容旧脚本调用，空操作
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

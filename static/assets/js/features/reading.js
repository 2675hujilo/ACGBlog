/**
 * features/reading.js —— 阅读体验增强（B类）
 *
 * 功能：
 *   B1 字体大小调节（A-/A/A+，写 --read-font-scale）
 *   B2 行高调节（slider，写 --read-line-height）
 *   B3 字体切换（sans/song/mono，body[data-font-family]）
 *   B4 主题色切换（紫粉/蓝绿/橙黄/玫瑰，body[data-theme-color]）
 *   B5 护眼模式（body.eye-protection）
 *   B6 AMOLED 纯黑（body.amoled-dark）
 *   B7 纸张纹理（body.paper-texture）
 *   B9 选中文字划线笔记（localStorage，可再点清除）
 *   B10 段落书签（段落旁按钮，localStorage 记录滚动位置）
 *   B11 选中文字翻译（弹出按钮，调免费翻译接口）
 *   B12 TTS 语音朗读（Web Speech API，播放/暂停/语速）
 *   B14 编辑页字数实时统计
 *   B15 字号同步评论区（body[data-font-scale-sync]）
 *
 * 偏好来源：window.USER_PREFERENCES；修改后写 localStorage 并尝试 PUT
 *           /api/user/preferences/（未登录则静默失败，不影响使用）
 * 防御式：仅在相关 DOM 存在时初始化，无依赖，纯原生。
 */
(function () {
    'use strict';

    var PREF = window.USER_PREFERENCES || {};
    var LS_KEY = 'blog_reading_prefs';

    /* ---------- 偏好读写 ---------- */
    function loadPrefs() {
        try { return JSON.parse(localStorage.getItem(LS_KEY)) || {}; }
        catch (e) { return {}; }
    }
    function savePrefs(p) {
        try { localStorage.setItem(LS_KEY, JSON.stringify(p)); } catch (e) {}
        // 尽力同步到后端偏好（未登录会 403/重定向，静默忽略）
        if (window.csrftoken) {
            fetch('/api/user/preferences/', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrftoken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(p),
                credentials: 'same-origin'
            }).catch(function () {});
        }
    }
    var prefs = loadPrefs();

    function setVar(name, val) { document.documentElement.style.setProperty(name, val); }

    /* ---------- B1/B2/B3 应用偏好到页面 ---------- */
    function applyReadingPrefs() {
        if (prefs.fontScale) setVar('--read-font-scale', prefs.fontScale);
        if (prefs.lineHeight) setVar('--read-line-height', prefs.lineHeight);
        if (prefs.fontFamily) document.body.setAttribute('data-font-family', prefs.fontFamily);
        if (prefs.themeColor) document.body.setAttribute('data-theme-color', prefs.themeColor);
        document.body.classList.toggle('eye-protection', !!prefs.eyeProtection);
        document.body.classList.toggle('amoled-dark', !!prefs.amoled);
        document.body.classList.toggle('paper-texture', !!prefs.paper);
        document.body.setAttribute('data-font-scale-sync', '1');
    }
    applyReadingPrefs();

    /* ---------- B1/B2/B3/B4 工具条按钮绑定 ---------- */
    function on(sel, evt, fn) {
        document.querySelectorAll(sel).forEach(function (el) { el.addEventListener(evt, fn); });
    }
    // 字号
    on('[data-act="font-dec"]', 'click', function () {
        prefs.fontScale = Math.max(.8, (parseFloat(prefs.fontScale || 1) - .1).toFixed(2));
        setVar('--read-font-scale', prefs.fontScale); savePrefs(prefs); syncLabel();
    });
    on('[data-act="font-inc"]', 'click', function () {
        prefs.fontScale = Math.min(1.8, (parseFloat(prefs.fontScale || 1) + .1).toFixed(2));
        setVar('--read-font-scale', prefs.fontScale); savePrefs(prefs); syncLabel();
    });
    function syncLabel() {
        document.querySelectorAll('.fs-value').forEach(function (el) {
            el.textContent = Math.round((parseFloat(prefs.fontScale || 1)) * 100) + '%';
        });
    }
    syncLabel();
    // 行高
    var lh = document.querySelector('.line-height-slider');
    if (lh) {
        lh.value = prefs.lineHeight || 1.8;
        lh.addEventListener('input', function () {
            prefs.lineHeight = lh.value; setVar('--read-line-height', lh.value); savePrefs(prefs);
        });
    }
    // 字体
    on('[data-font]', 'click', function () {
        prefs.fontFamily = this.getAttribute('data-font');
        document.body.setAttribute('data-font-family', prefs.fontFamily);
        document.querySelectorAll('[data-font]').forEach(function (b) { b.classList.toggle('active', b === this); }, this);
        savePrefs(prefs);
    });
    // 主题色
    on('[data-theme-color]', 'click', function () {
        prefs.themeColor = this.getAttribute('data-theme-color') || '';
        if (prefs.themeColor) document.body.setAttribute('data-theme-color', prefs.themeColor);
        else document.body.removeAttribute('data-theme-color');
        document.querySelectorAll('[data-theme-color].swatch').forEach(function (s) {
            s.classList.toggle('active', s === this);
        }, this);
        savePrefs(prefs);
    });
    // 模式开关
    on('[data-act="eye"]', 'click', function () {
        prefs.eyeProtection = !prefs.eyeProtection;
        document.body.classList.toggle('eye-protection', prefs.eyeProtection);
        this.classList.toggle('active', prefs.eyeProtection); savePrefs(prefs);
    });
    on('[data-act="amoled"]', 'click', function () {
        prefs.amoled = !prefs.amoled;
        document.body.classList.toggle('amoled-dark', prefs.amoled);
        this.classList.toggle('active', prefs.amoled); savePrefs(prefs);
    });
    on('[data-act="paper"]', 'click', function () {
        prefs.paper = !prefs.paper;
        document.body.classList.toggle('paper-texture', prefs.paper);
        this.classList.toggle('active', prefs.paper); savePrefs(prefs);
    });

    /* ---------- B10 段落书签：给正文段落加书签按钮 ---------- */
    var body = document.getElementById('article-body');
    if (body) {
        body.querySelectorAll('p, h2, h3').forEach(function (p) {
            p.style.position = p.style.position || 'relative';
            var bm = document.createElement('span');
            bm.className = 'paragraph-bookmark';
            bm.title = '在此处添加书签';
            bm.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12v18l-6-4-6 4z"/></svg>';
            bm.addEventListener('click', function (e) {
                e.stopPropagation();
                var id = p.id || ('p_' + Math.random().toString(36).slice(2, 8));
                if (!p.id) p.id = id;
                var marks = JSON.parse(localStorage.getItem('blog_bookmarks') || '{}');
                if (bm.classList.contains('marked')) {
                    delete marks[id]; bm.classList.remove('marked');
                } else {
                    marks[id] = { top: window.scrollY, text: (p.textContent || '').slice(0, 40) };
                    bm.classList.add('marked');
                }
                localStorage.setItem('blog_bookmarks', JSON.stringify(marks));
            });
            p.appendChild(bm);
        });

        /* ---------- B9/B11 选中文字：笔记 / 翻译 弹出按钮 ---------- */
        document.addEventListener('mouseup', function () {
            setTimeout(function () {
                var sel = window.getSelection();
                var text = sel ? sel.toString().trim() : '';
                var old = document.querySelector('.note-popup');
                if (old) old.remove();
                if (!text || text.length < 2 || !body.contains(sel.anchorNode)) return;
                var rect = sel.getRangeAt(0).getBoundingClientRect();
                var pop = document.createElement('div');
                pop.className = 'note-popup';
                pop.innerHTML = '<button data-note>✏️ 笔记</button><button data-trans>🌐 翻译</button>';
                pop.style.left = (rect.left + window.scrollX) + 'px';
                pop.style.top = (rect.bottom + window.scrollY + 8) + 'px';
                pop.querySelector('[data-note]').addEventListener('click', function () {
                    var range = sel.getRangeAt(0);
                    var mark = document.createElement('mark');
                    mark.className = 'text-note'; mark.textContent = text;
                    range.deleteContents(); range.insertNode(mark);
                    pop.remove();
                });
                pop.querySelector('[data-trans]').addEventListener('click', function () {
                    translate(text, pop.querySelector('[data-trans]'));
                });
                document.body.appendChild(pop);
            }, 10);
        });
    }

    /* ---------- B11 翻译：调用免费公开接口（失败给出提示，不报错） ---------- */
    function translate(text, btn) {
        btn.textContent = '翻译中…';
        var url = 'https://api.mymemory.translated.net/get?q=' + encodeURIComponent(text) +
            '&langpair=zh-CN|en';
        fetch(url).then(function (r) { return r.json(); }).then(function (data) {
            var out = data && data.responseData && data.responseData.translatedText;
            btn.textContent = out ? out.slice(0, 80) : '翻译失败';
        }).catch(function () { btn.textContent = '翻译服务不可用'; });
    }

    /* ---------- B12 TTS 语音朗读 ---------- */
    var ttsBar = document.querySelector('.tts-bar');
    if (ttsBar && 'speechSynthesis' in window) {
        var playing = false;
        var playBtn = ttsBar.querySelector('[data-tts="play"]');
        var stopBtn = ttsBar.querySelector('[data-tts="stop"]');
        var speed = ttsBar.querySelector('.tts-speed');
        var status = ttsBar.querySelector('.tts-status');
        function text() {
            return (document.getElementById('article-body') || document.body).innerText.slice(0, 3000);
        }
        if (playBtn) playBtn.addEventListener('click', function () {
            if (playing) { window.speechSynthesis.pause(); playing = false; status.textContent = '已暂停'; return; }
            var u = new SpeechSynthesisUtterance(text());
            u.lang = 'zh-CN';
            if (speed) u.rate = parseFloat(speed.value) || 1;
            u.onend = function () { playing = false; status.textContent = '朗读结束'; };
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(u);
            playing = true; status.textContent = '朗读中…';
        });
        if (stopBtn) stopBtn.addEventListener('click', function () {
            window.speechSynthesis.cancel(); playing = false; status.textContent = '已停止';
        });
        /* Bug23: 操作栏「朗读喵」快捷按钮，等同播放/暂停 */
        var ttsQuick = document.getElementById('tts-toggle-btn');
        if (ttsQuick && playBtn) ttsQuick.addEventListener('click', function () { playBtn.click(); });
    }

    /* ---------- Bug23: 阅读设置面板开合 ---------- */
    (function () {
        var btn = document.getElementById('reading-settings-btn');
        var mask = document.getElementById('reading-settings-mask');
        var close = document.getElementById('rs-close');
        if (!btn || !mask) return;
        function openPanel() { mask.hidden = false; btn.setAttribute('aria-expanded', 'true'); }
        function hidePanel() { mask.hidden = true; btn.setAttribute('aria-expanded', 'false'); }
        btn.addEventListener('click', function () { mask.hidden ? openPanel() : hidePanel(); });
        if (close) close.addEventListener('click', hidePanel);
        mask.addEventListener('click', function (e) { if (e.target === mask) hidePanel(); });
        document.addEventListener('keydown', function (e) { if (e.key === 'Escape') hidePanel(); });
    })();

    /* ---------- B14 编辑页字数实时统计 ---------- */
    var editor = document.querySelector('#id_content, .editor-input, textarea.editor-area');
    if (editor) {
        var wc = document.querySelector('.editor-word-count');
        if (wc) {
            var upd = function () {
                var n = (editor.value || '').length;
                wc.textContent = n + ' 字';
            };
            editor.addEventListener('input', upd); upd();
        }
    }
})();

/* ============================================================
 * features/settings_prefs.js —— Bug22: 账号设置页「阅读偏好」
 * 主题色 / 字号 / 护眼 / AMOLED纯黑 / 交互音效 / 页面动效
 * 任一控件变化：即时在当前页面生效 + 写入账号偏好(后端) +
 *              同步本地 localStorage（详情页阅读设置保持一致）
 * ============================================================ */
(function () {
    'use strict';
    var form = document.getElementById('preferences-form');
    if (!form) return;

    function $(id) { return document.getElementById(id); }
    var themeSel = $('pref-theme-color'),
        sizeSel = $('pref-font-size'),
        eyeChk = form.querySelector('[name="eye_protection"]'),
        amoledChk = form.querySelector('[name="amoled_dark"]'),
        soundChk = form.querySelector('[name="sound_enabled"]'),
        effectsChk = form.querySelector('[name="effects_enabled"]');

    /* 读取 cookie（用于 CSRF） */
    function cookie(name) {
        var m = document.cookie.match(new RegExp('\\b' + name + '=([^;]*)'));
        return m ? decodeURIComponent(m[1]) : '';
    }
    /* 轻量 toast 提示（复用全站 #global-toast，不存在则临时创建） */
    function toast(msg) {
        var t = document.getElementById('global-toast');
        if (!t) {
            t = document.createElement('div');
            t.id = 'global-toast';
            t.style.cssText = 'position:fixed;left:50%;bottom:32px;transform:translateX(-50%);background:rgba(43,35,64,.92);color:#fff;padding:10px 20px;border-radius:999px;font-size:.9rem;z-index:9999;opacity:0;transition:opacity .25s;pointer-events:none;';
            document.body.appendChild(t);
        }
        t.textContent = msg;
        t.classList.add('show');
        t.style.opacity = '1';
        clearTimeout(t._timer);
        t._timer = setTimeout(function () { t.style.opacity = '0'; t.classList.remove('show'); }, 1800);
    }

    var P = window.USER_PREFERENCES || {};
    /* 字号档位 → 详情页正文 --read-font-scale 映射 */
    var FONT_SCALE = { small: 0.92, medium: 1.0, large: 1.15, xlarge: 1.3 };

    /* 收集控件当前值（字段名与后端偏好一致） */
    function collect() {
        return {
            theme_color: themeSel.value,
            font_size: sizeSel.value,
            eye_protection: eyeChk.checked,
            amoled_dark: amoledChk.checked,
            sound_enabled: soundChk.checked,
            effects_enabled: effectsChk.checked
        };
    }

    /* 即时应用到当前页面（无需刷新即可看到效果） */
    function apply(p) {
        document.body.setAttribute('data-theme-color', p.theme_color || 'purple_pink');
        document.body.setAttribute('data-font-size', p.font_size || 'medium');
        document.body.classList.toggle('eye-protection', !!p.eye_protection);
        document.body.classList.toggle('amoled-dark', !!p.amoled_dark);
        document.documentElement.classList.toggle('motion-off', !p.effects_enabled);
        try { localStorage.setItem('moe_motion', p.effects_enabled ? '1' : '0'); } catch (e) {}

        /* 音效：与导航栏音效按钮（common.js 维护 moe_sound）状态对齐 */
        try {
            var curSound = localStorage.getItem('moe_sound') !== '0';
            if (curSound !== p.sound_enabled) {
                localStorage.setItem('moe_sound', p.sound_enabled ? '1' : '0');
            }
            var sb = document.getElementById('sound-toggle');
            if (sb) {
                var sbOn = sb.textContent.indexOf('\uD83D\uDD0A') >= 0;  // 🔊 表示开
                if (sbOn !== p.sound_enabled) sb.click();  // 翻转 common.js 内部状态
            }
        } catch (e) {}

        /* 同步详情页阅读偏好（reading.js 读取 blog_reading_prefs） */
        try {
            var rp = JSON.parse(localStorage.getItem('blog_reading_prefs') || '{}');
            rp.themeColor = (p.theme_color === 'purple_pink') ? '' : p.theme_color;
            rp.fontScale = FONT_SCALE[p.font_size] || 1;
            rp.eyeProtection = !!p.eye_protection;
            rp.amoled = !!p.amoled_dark;
            localStorage.setItem('blog_reading_prefs', JSON.stringify(rp));
        } catch (e) {}
    }

    /* 持久化到账号（PUT /api/user/preferences/） */
    var saveTimer = null;
    function persist(p) {
        clearTimeout(saveTimer);
        saveTimer = setTimeout(function () {
            fetch('/api/user/preferences/', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': cookie('csrftoken') || window.csrftoken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin',
                body: JSON.stringify(p)
            }).then(function (r) { return r.json(); })
              .then(function () { toast('阅读偏好已保存喵~✨'); })
              .catch(function () { toast('偏好已在本设备生效喵~'); });
        }, 250);
    }

    /* 用账号偏好 + 本地开关初始化控件 */
    function init() {
        if (P.theme_color) themeSel.value = P.theme_color;
        if (P.font_size) sizeSel.value = P.font_size;
        eyeChk.checked = !!P.eye_protection;
        amoledChk.checked = !!P.amoled_dark;
        var lsSound = localStorage.getItem('moe_sound');
        // 无本地记录时与导航音效按钮(common.js)默认行为一致：音效默认开
        soundChk.checked = lsSound !== null ? lsSound !== '0' : true;
        var lsMotion = localStorage.getItem('moe_motion');
        effectsChk.checked = lsMotion !== null ? lsMotion !== '0' : (P.effects_enabled !== false);
        apply(collect());
    }

    /* 任一控件变化：实时生效并保存 */
    [themeSel, sizeSel, eyeChk, amoledChk, soundChk, effectsChk].forEach(function (el) {
        if (!el) return;
        el.addEventListener('change', function () {
            var p = collect();
            apply(p);
            persist(p);
        });
    });
    /* 拦截表单传统提交（已实时保存，避免整页刷新） */
    form.addEventListener('submit', function (e) {
        e.preventDefault();
        var p = collect();
        apply(p);
        persist(p);
        toast('阅读偏好已保存喵~✨');
    });

    init();
})();

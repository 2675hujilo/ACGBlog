/**
 * sakura-mode.js —— 24. 樱花模式三档开关
 *
 * 三档循环：off（关闭） → light（淡，5 朵） → dense（浓，15 朵，更大更快） → off
 * 状态存于 localStorage('sakura_mode')，刷新保持。
 * 已有的 5 个 .sakura-deco 花瓣在 base.html 中静态写死；浓模式时动态追加 10 个。
 */
(function () {
    'use strict';
    var btn = document.getElementById('sakura-mode-toggle');
    if (!btn) return;

    var STATES = ['off', 'light', 'dense'];
    var LABELS = { off: '🌺', light: '🌸', dense: '🌺' };
    var TITLES = {
        off: '樱花模式：关闭（点击开启淡模式）',
        light: '樱花模式：淡（点击开启浓模式）',
        dense: '樱花模式：浓（点击关闭）'
    };

    // 基础 5 个花瓣（base.html 静态存在）
    var basePetals = Array.prototype.slice.call(document.querySelectorAll('.sakura-deco'));
    // 浓模式动态追加的花瓣容器
    var densePetals = [];

    /* 读取当前状态，兜底 off */
    function getState() {
        var s = 'off';
        try { s = localStorage.getItem('sakura_mode') || 'off'; } catch (e) {}
        return STATES.indexOf(s) >= 0 ? s : 'off';
    }
    /* 保存状态 */
    function save(s) {
        try { localStorage.setItem('sakura_mode', s); } catch (e) {}
    }

    /* 创建一个动态花瓣（浓模式用） */
    function makePetal(i) {
        var span = document.createElement('span');
        span.className = 'sakura-deco sakura-dense';
        span.style.left = (Math.random() * 96) + '%';
        span.style.animationDuration = (8 + Math.random() * 6) + 's';   // 下落更快
        span.style.animationDelay = (Math.random() * 5) + 's';
        span.style.transform = 'scale(' + (1.2 + Math.random() * 0.8) + ')';  // 更大
        document.body.appendChild(span);
        return span;
    }

    /* 应用状态：显示/隐藏花瓣 */
    function apply(s) {
        // off 全部隐藏；light/dense 显示基础花瓣
        var showBase = (s !== 'off');
        basePetals.forEach(function (p) { p.style.display = showBase ? '' : 'none'; });
        // dense 时确保动态花瓣存在；否则移除
        if (s === 'dense') {
            while (densePetals.length < 10) densePetals.push(makePetal(densePetals.length));
            densePetals.forEach(function (p) { p.style.display = ''; });
        } else {
            densePetals.forEach(function (p) { p.style.display = 'none'; });
        }
        // 按钮外观提示当前档
        btn.textContent = LABELS[s];
        btn.title = TITLES[s];
    }

    /* 点击循环到下一档 */
    btn.addEventListener('click', function () {
        var cur = getState();
        var next = STATES[(STATES.indexOf(cur) + 1) % STATES.length];
        save(next);
        apply(next);
    });

    // 页面加载时恢复状态
    apply(getState());
})();

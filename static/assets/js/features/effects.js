/**
 * features/effects.js —— 视觉动效（E类）+ 彩蛋个性化（H类）
 *
 * 功能：
 *   E3 粒子背景（Canvas，可开关，50~100 粒子）
 *   E4 视差滚动背景
 *   E8 打字机效果（.typewriter-target）
 *   E15 滚动触发淡入（IntersectionObserver，.fade-scroll）
 *   H1 节日主题自动切换（按日期）
 *   H2 用户生日彩蛋（读 window.USER_PREFERENCES.birthday）
 *   H3 任意点击爱心粒子
 *   H4 控制台萌系彩蛋
 *   H8 交互音效开关（Web Audio）
 *   H9 打字音效
 *   H10 Konami 代码彩蛋（↑↑↓↓←→←→BA）
 *   H6/H7 自定义主题色与背景面板
 *   A7/A9 移动端底部导航与浮动按钮
 *
 * 防御式：按 DOM 存在初始化；动效总开关 body.motion-off 关闭一切。
 */
(function () {
    'use strict';
    var motionOn = document.body.classList.contains('motion-off') ? false : true;

    /* ---------- E3 粒子背景 ---------- */
    var particleBtn = document.querySelector('[data-act="particles"]');
    function initParticles() {
        var cv = document.getElementById('particle-canvas');
        if (!cv) return;
        var ctx = cv.getContext('2d');
        var pts = [], N = 70;
        function resize() { cv.width = innerWidth; cv.height = innerHeight; }
        resize(); addEventListener('resize', resize);
        for (var i = 0; i < N; i++) {
            pts.push({
                x: Math.random() * innerWidth, y: Math.random() * innerHeight,
                r: Math.random() * 2 + 1,
                vx: (Math.random() - .5) * .4, vy: (Math.random() - .5) * .4,
                c: ['#ff8fb1', '#a06cd5', '#6ea8fe'][i % 3]
            });
        }
        function loop() {
            ctx.clearRect(0, 0, cv.width, cv.height);
            pts.forEach(function (p) {
                p.x += p.vx; p.y += p.vy;
                if (p.x < 0 || p.x > cv.width) p.vx *= -1;
                if (p.y < 0 || p.y > cv.height) p.vy *= -1;
                ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
                ctx.fillStyle = p.c; ctx.globalAlpha = .6; ctx.fill();
            });
            requestAnimationFrame(loop);
        }
        loop();
    }
    if (particleBtn) {
        particleBtn.addEventListener('click', function () {
            var on = document.body.classList.toggle('has-particle');
            particleBtn.classList.toggle('active', on);
            if (on) { document.body.insertAdjacentHTML('beforeend', '<canvas id="particle-canvas"></canvas>'); initParticles(); }
            else { var cv = document.getElementById('particle-canvas'); if (cv) cv.remove(); }
        });
    }

    /* ---------- E4 视差背景 ---------- */
    var pbg = document.querySelector('.parallax-bg');
    if (pbg) {
        addEventListener('scroll', function () {
            pbg.style.transform = 'translateY(' + (window.scrollY * 0.3) + 'px)';
        }, { passive: true });
    }

    /* ---------- E8 打字机 ---------- */
    document.querySelectorAll('.typewriter-target').forEach(function (el) {
        var full = el.textContent; el.textContent = '';
        var i = 0;
        (function type() {
            if (i <= full.length) { el.textContent = full.slice(0, i++); setTimeout(type, 80); }
        })();
    });

    /* ---------- E15 滚动淡入 ---------- */
    /* .scroll-fade-in 仅用于 main 主内容区，总在视口顶部，用 rAF 立即渐显，
       不依赖 IntersectionObserver（避免 defer 脚本执行时布局未完成导致不触发）；
       .fade-scroll 用于文章卡片等滚动触发元素，仍用 IntersectionObserver。 */
    requestAnimationFrame(function () {
        document.querySelectorAll('.scroll-fade-in').forEach(function (el) { el.classList.add('visible'); });
    });
    if ('IntersectionObserver' in window) {
        var io = new IntersectionObserver(function (es) {
            es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('visible'); io.unobserve(e.target); } });
        }, { threshold: .12 });
        document.querySelectorAll('.fade-scroll').forEach(function (el) { io.observe(el); });
    } else {
        document.querySelectorAll('.fade-scroll').forEach(function (el) { el.classList.add('visible'); });
    }

    /* ---------- H1 节日主题 ---------- */
    (function festival() {
        var d = new Date(), m = d.getMonth() + 1, day = d.getDate();
        if ((m === 2 && day >= 1 && day <= 15) || (m === 1 && day === 1)) document.body.classList.add('festival-spring');
        if (m === 12 && day >= 20) document.body.classList.add('festival-xmas');
        if (m === 10 && day === 31) document.body.classList.add('festival-halloween');
    })();

    /* ---------- H2 生日彩蛋 ---------- */
    (function birthday() {
        var bd = (window.USER_PREFERENCES || {}).birthday;
        if (!bd) return;
        var d = new Date(bd); var now = new Date();
        if (d.getMonth() === now.getMonth() && d.getDate() === now.getDate()) {
            var deco = document.createElement('div');
            deco.className = 'festival-deco'; deco.textContent = '🎂🎉🎈 生日快乐！';
            deco.style.textAlign = 'center'; deco.style.padding = '8px';
            document.body.insertBefore(deco, document.body.firstChild);
        }
    })();

    /* ---------- H3 任意点击爱心 ---------- */
    document.addEventListener('click', function (e) {
        if (!motionOn) return;
        if (e.target.closest('a, button, input, textarea, .modal')) return;
        var h = document.createElement('span');
        h.className = 'click-heart'; h.textContent = '💗';
        h.style.left = e.clientX + 'px'; h.style.top = e.clientY + 'px';
        document.body.appendChild(h);
        setTimeout(function () { h.remove(); }, 1000);
    });

    /* ---------- H4 控制台彩蛋 ---------- */
    console.log('%c🐾 欢迎来到萌系博客喵~', 'font-size:20px;color:#a06cd5;font-weight:bold');
    console.log('%c(◕ᴗ◕)ﾉ 发现你了！记得常来玩哦~', 'color:#ff8fb1');

    /* H8/H9 交互音效已统一迁移到 common.js 的 initNavToggles()，由导航栏 #sound-toggle 控制（含 localStorage 持久化、点击音、打字音），此处不再重复绑定。 */

    /* ---------- H10 Konami 彩蛋 ---------- */
    var seq = [38, 38, 40, 40, 37, 39, 37, 39, 66, 65], idx = 0;
    document.addEventListener('keydown', function (e) {
        idx = (e.keyCode === seq[idx]) ? idx + 1 : 0;
        if (idx === seq.length) {
            document.body.classList.toggle('konami-mode');
            if (window.moeToast) moeToast('🐾 樱花暴雨模式开启！再输一次关闭喵~');
            idx = 0;
        }
    });

    /* ---------- H7 自定义背景面板 ---------- */
    var bgPanel = document.querySelector('.custom-bg-panel');
    if (bgPanel) {
        bgPanel.querySelectorAll('.bg-thumb').forEach(function (t) {
            t.addEventListener('click', function () {
                var url = t.getAttribute('data-bg');
                if (url) document.body.style.backgroundImage = 'url(' + url + ')';
                else document.body.style.backgroundImage = '';
            });
        });
    }

    /* ---------- A7 页面入场淡入 ---------- */
    document.body.classList.add('page-enter');
})();

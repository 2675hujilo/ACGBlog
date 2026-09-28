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
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';
    //> 声明变量「motionOn」（motion on），用于保存对应数据，保存 DOM/窗口相关对象
    var motionOn = document.body.classList.contains('motion-off') ? false : true;

    /* ---------- E3 粒子背景 ---------- */
    //> 声明变量「particleBtn」（particle btn），用于保存对应数据，保存 DOM/窗口相关对象
    var particleBtn = document.querySelector('[data-act="particles"]');
    // =========================================================
    // 【函数】initParticles
    // 功能：初始化「particles」相关逻辑（init particles）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function initParticles() {
        //> 声明变量「cv」（cv），用于保存对应数据，保存 DOM/窗口相关对象
        var cv = document.getElementById('particle-canvas');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!cv) return;
        //> 声明变量「ctx」（ctx），用于保存对应数据
        var ctx = cv.getContext('2d');
        //> 声明变量「pts」（pts），用于保存对应数据
        var pts = [], N = 70;
        // =========================================================
        // 【函数】resize
        // 功能：处理「resize」相关逻辑（effects）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function resize() { cv.width = innerWidth; cv.height = innerHeight; }
        //> 绑定「resize」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        resize(); addEventListener('resize', resize);
        //> 循环：按条件重复执行循环体
        for (var i = 0; i < N; i++) {
            //> 操作「pts」的相关方法/属性
            pts.push({
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                x: Math.random() * innerWidth, y: Math.random() * innerHeight,
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                r: Math.random() * 2 + 1,
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                vx: (Math.random() - .5) * .4, vy: (Math.random() - .5) * .4,
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                c: ['#ff8fb1', '#a06cd5', '#6ea8fe'][i % 3]
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // =========================================================
        // 【函数】loop
        // 功能：处理「loop」相关逻辑（effects）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function loop() {
            //> 操作「ctx」的相关方法/属性
            ctx.clearRect(0, 0, cv.width, cv.height);
            //> 遍历数组/类数组中的每一项并执行回调
            pts.forEach(function (p) {
                //> 操作「p」的相关方法/属性
                p.x += p.vx; p.y += p.vy;
                //> 条件判断：满足括号内条件时执行对应分支
                if (p.x < 0 || p.x > cv.width) p.vx *= -1;
                //> 条件判断：满足括号内条件时执行对应分支
                if (p.y < 0 || p.y > cv.height) p.vy *= -1;
                //> 操作「ctx」的相关方法/属性
                ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
                //> 给「ctx.fillStyle」赋值，更新其保存的状态
                ctx.fillStyle = p.c; ctx.globalAlpha = .6; ctx.fill();
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            //> 在下一帧重绘前执行回调，是流畅动画的标准做法
            requestAnimationFrame(loop);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 调用函数「loop」并传入参数执行对应逻辑
        loop();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    //> 条件判断：满足括号内条件时执行对应分支
    if (particleBtn) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        particleBtn.addEventListener('click', function () {
            //> 声明变量「on」（on），用于保存对应数据，保存 DOM/窗口相关对象
            var on = document.body.classList.toggle('has-particle');
            //> 切换样式类（有则移除、无则添加），可传第二参强制状态
            particleBtn.classList.toggle('active', on);
            //> 条件判断：满足括号内条件时执行对应分支
            if (on) { document.body.insertAdjacentHTML('beforeend', '<canvas id="particle-canvas"></canvas>'); initParticles(); }
            //> 以上条件都不满足时执行的兜底分支
            else { var cv = document.getElementById('particle-canvas'); if (cv) cv.remove(); }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- E4 视差背景 ---------- */
    //> 声明变量「pbg」（pbg），用于保存对应数据，保存 DOM/窗口相关对象
    var pbg = document.querySelector('.parallax-bg');
    //> 条件判断：满足括号内条件时执行对应分支
    if (pbg) {
        // =========================================================
        // 【函数】addEventListener
        // 功能：添加「event listener」相关逻辑（add event listener）
        // 参数：
        //   - 'scroll'：传入的参数（含义结合调用处与函数体）
        //   - function：传入的参数（含义结合调用处与函数体）
        //   - (：传入的参数（含义结合调用处与函数体）
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：体内绑定事件监听，注意回调中的 this 与解绑时机
        // =========================================================
        addEventListener('scroll', function () {
            //> 给「pbg.style.transform」赋值，更新其保存的状态
            pbg.style.transform = 'translateY(' + (window.scrollY * 0.3) + 'px)';
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }, { passive: true });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- E8 打字机 ---------- */
    //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
    document.querySelectorAll('.typewriter-target').forEach(function (el) {
        //> 声明变量「full」（full），用于保存对应数据
        var full = el.textContent; el.textContent = '';
        //> 声明变量「i」（i），用于保存对应数据
        var i = 0;
        // =========================================================
        // 【函数】type
        // 功能：处理「type」相关逻辑（effects）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        (function type() {
            //> 条件判断：满足括号内条件时执行对应分支
            if (i <= full.length) { el.textContent = full.slice(0, i++); setTimeout(type, 80); }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        })();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- E15 滚动淡入 ---------- */
    /* .scroll-fade-in 仅用于 main 主内容区，总在视口顶部，用 rAF 立即渐显，
       //> 该行执行对应的脚本逻辑（结合上下文理解）
       不依赖 IntersectionObserver（避免 defer 脚本执行时布局未完成导致不触发）；
       //> 该行执行对应的脚本逻辑（结合上下文理解）
       .fade-scroll 用于文章卡片等滚动触发元素，仍用 IntersectionObserver。 */
    // =========================================================
    // 【函数】requestAnimationFrame
    // 功能：处理「request animation frame」相关逻辑（effects）
    // 参数：
    //   - function：传入的参数（含义结合调用处与函数体）
    //   - (：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    requestAnimationFrame(function () {
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        document.querySelectorAll('.scroll-fade-in').forEach(function (el) { el.classList.add('visible'); });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
    //> 条件判断：满足括号内条件时执行对应分支
    if ('IntersectionObserver' in window) {
        //> 声明变量「io」（io），用于保存对应数据
        var io = new IntersectionObserver(function (es) {
            //> 为元素添加一个或多个样式类
            es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('visible'); io.unobserve(e.target); } });
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }, { threshold: .12 });
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        document.querySelectorAll('.fade-scroll').forEach(function (el) { io.observe(el); });
    //> 以上条件都不满足时执行的兜底分支
    } else {
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        document.querySelectorAll('.fade-scroll').forEach(function (el) { el.classList.add('visible'); });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- H1 节日主题 ---------- */
    // =========================================================
    // 【函数】festival
    // 功能：处理「festival」相关逻辑（effects）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    (function festival() {
        //> 声明变量「d」（d），用于保存对应数据
        var d = new Date(), m = d.getMonth() + 1, day = d.getDate();
        //> 条件判断：满足括号内条件时执行对应分支
        if ((m === 2 && day >= 1 && day <= 15) || (m === 1 && day === 1)) document.body.classList.add('festival-spring');
        //> 条件判断：满足括号内条件时执行对应分支
        if (m === 12 && day >= 20) document.body.classList.add('festival-xmas');
        //> 条件判断：满足括号内条件时执行对应分支
        if (m === 10 && day === 31) document.body.classList.add('festival-halloween');
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    })();

    /* ---------- H2 生日彩蛋 ---------- */
    // =========================================================
    // 【函数】birthday
    // 功能：处理「birthday」相关逻辑（effects）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    (function birthday() {
        //> 声明变量「bd」（bd），用于保存对应数据，值为一个函数
        var bd = (window.USER_PREFERENCES || {}).birthday;
        //> 条件判断：满足括号内条件时执行对应分支
        if (!bd) return;
        //> 声明变量「d」（d），用于保存对应数据
        var d = new Date(bd); var now = new Date();
        //> 条件判断：满足括号内条件时执行对应分支
        if (d.getMonth() === now.getMonth() && d.getDate() === now.getDate()) {
            //> 声明变量「deco」（deco），用于保存对应数据，保存 DOM/窗口相关对象
            var deco = document.createElement('div');
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            deco.className = 'festival-deco'; deco.textContent = '🎂🎉🎈 生日快乐！';
            //> 给「deco.style.textAlign」赋值，更新其保存的状态
            deco.style.textAlign = 'center'; deco.style.padding = '8px';
            //> 在参考子节点之前插入新子节点
            document.body.insertBefore(deco, document.body.firstChild);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    })();

    /* ---------- H3 任意点击爱心 ---------- */
    //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    document.addEventListener('click', function (e) {
        //> 条件判断：满足括号内条件时执行对应分支
        if (!motionOn) return;
        //> 条件判断：满足括号内条件时执行对应分支
        if (e.target.closest('a, button, input, textarea, .modal')) return;
        //> 声明变量「h」（h），用于保存对应数据，保存 DOM/窗口相关对象
        var h = document.createElement('span');
        //> 读写纯文本内容，不解析 HTML，可防 XSS
        h.className = 'click-heart'; h.textContent = '💗';
        //> 给「h.style.left」赋值，更新其保存的状态
        h.style.left = e.clientX + 'px'; h.style.top = e.clientY + 'px';
        //> 把子节点追加到当前元素内部末尾
        document.body.appendChild(h);
        //> 把元素从 DOM 中移除
        setTimeout(function () { h.remove(); }, 1000);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- H4 控制台彩蛋 ---------- */
    //> 向控制台输出调试信息（生产环境应精简）
    console.log('%c🐾 欢迎来到萌系博客喵~', 'font-size:20px;color:#a06cd5;font-weight:bold');
    //> 向控制台输出调试信息（生产环境应精简）
    console.log('%c(◕ᴗ◕)ﾉ 发现你了！记得常来玩哦~', 'color:#ff8fb1');

    /* H8/H9 交互音效已统一迁移到 common.js 的 initNavToggles()，由导航栏 #sound-toggle 控制（含 localStorage 持久化、点击音、打字音），此处不再重复绑定。 */

    /* ---------- H10 Konami 彩蛋 ---------- */
    //> 声明变量「seq」（seq），用于保存对应数据
    var seq = [38, 38, 40, 40, 37, 39, 37, 39, 66, 65], idx = 0;
    //> 绑定「keydown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    document.addEventListener('keydown', function (e) {
        //> 给「idx」赋值，更新其保存的状态
        idx = (e.keyCode === seq[idx]) ? idx + 1 : 0;
        //> 条件判断：满足括号内条件时执行对应分支
        if (idx === seq.length) {
            //> 切换样式类（有则移除、无则添加），可传第二参强制状态
            document.body.classList.toggle('konami-mode');
            //> 条件判断：满足括号内条件时执行对应分支
            if (window.moeToast) moeToast('🐾 樱花暴雨模式开启！再输一次关闭喵~');
            //> 给「idx」赋值，更新其保存的状态
            idx = 0;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- H7 自定义背景面板 ---------- */
    //> 声明变量「bgPanel」（bg panel），用于保存对应数据，保存 DOM/窗口相关对象
    var bgPanel = document.querySelector('.custom-bg-panel');
    //> 条件判断：满足括号内条件时执行对应分支
    if (bgPanel) {
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        bgPanel.querySelectorAll('.bg-thumb').forEach(function (t) {
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            t.addEventListener('click', function () {
                //> 声明变量「url」（url），用于保存对应数据
                var url = t.getAttribute('data-bg');
                //> 条件判断：满足括号内条件时执行对应分支
                if (url) document.body.style.backgroundImage = 'url(' + url + ')';
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                else document.body.style.backgroundImage = '';
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- A7 页面入场淡入 ---------- */
    //> 为元素添加一个或多个样式类
    document.body.classList.add('page-enter');
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

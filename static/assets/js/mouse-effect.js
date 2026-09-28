/* ============================================================
 * mouse-effect.js —— 鼠标跟随粒子特效
 * 鼠标移动时在指针位置生成樱花花瓣 / 星星粒子，带重力下落与旋转。
 * 性能友好：粒子总数上限 60 个，页面不可见时暂停 rAF，Canvas 不拦截事件。
 * ============================================================ */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';

    // ---------- 开关状态：读取 localStorage，默认开启 ----------
    //> 声明变量「STORAGE_KEY」（storage key），用于保存对应数据，初始为字符串
    var STORAGE_KEY = 'mouse_effect_enabled';
    //> 声明变量「enabled」（enabled），用于保存对应数据，值为一个函数
    var enabled = (function () {
        //> 尝试执行可能出错的代码，出错则进入 catch
        try {
            // 未设置时默认开启；仅当显式存为 'false' 时关闭
            //> 返回结果并结束当前函数
            return localStorage.getItem(STORAGE_KEY) !== 'false';
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        } catch (e) {
            //> 返回结果并结束当前函数
            return true;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    })();

    // ---------- 配置项 ----------
    //> 声明变量「MAX_PARTICLES」（max particles），用于保存对应数据
    var MAX_PARTICLES = 60;          // 粒子数量上限，超出时移除最老的
    //> 声明变量「GRAVITY」（gravity），用于保存对应数据
    var GRAVITY = 0.08;              // 向下的重力加速度
    //> 声明变量「PARTICLE_SIZE_MIN」（particle size min），用于保存对应数据
    var PARTICLE_SIZE_MIN = 6;        // 粒子最小尺寸（px）
    //> 声明变量「PARTICLE_SIZE_MAX」（particle size max），用于保存对应数据
    var PARTICLE_SIZE_MAX = 12;       // 粒子最大尺寸（px）
    //> 声明变量「SPAWN_PER_MOVE」（spawn per move），用于保存对应数据
    var SPAWN_PER_MOVE = 2;          // 每次 mousemove 生成的粒子数（节流用）

    // ---------- 全屏 Canvas（按需创建，默认开启时才挂载） ----------
    //> 声明变量「canvas」（canvas），用于保存对应数据
    var canvas = null;
    //> 声明变量「ctx」（ctx），用于保存对应数据
    var ctx = null;
    //> 声明变量「mounted」（mounted），用于保存对应数据
    var mounted = false;             // Canvas 是否已挂载到 body
    //> 声明变量「eventsBound」（events bound），用于保存对应数据
    var eventsBound = false;         // 事件是否已绑定（避免重复绑定）
    //> 声明变量「running」（running），用于保存对应数据
    var running = false;             // 动画循环是否在运行

    // =========================================================
    // 【函数】ensureCanvas
    // 功能：处理「ensure canvas」相关逻辑（mouse-effect）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function ensureCanvas() {
        //> 条件判断：满足括号内条件时执行对应分支
        if (canvas) return;
        //> 创建新的 DOM 元素节点，后续需挂载到文档才显示
        canvas = document.createElement('canvas');
        //> 设置元素的 HTML 属性
        canvas.setAttribute('aria-hidden', 'true');
        //> 给「ctx」赋值，更新其保存的状态
        ctx = canvas.getContext('2d');
        // 关键样式：fixed 全屏、不拦截鼠标事件、最高层级
        //> 给「canvas.style.cssText」赋值，更新其保存的状态
        canvas.style.cssText =
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            'position:fixed;top:0;left:0;width:100vw;height:100vh;' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            'pointer-events:none;z-index:9999;';
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // 启动特效：挂载 Canvas、绑定事件、开启动画循环
    // =========================================================
    // 【函数】startEffect
    // 功能：处理「start effect」相关逻辑（mouse-effect）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function startEffect() {
        //> 条件判断：满足括号内条件时执行对应分支
        if (mounted) return;
        //> 调用函数「ensureCanvas」并传入参数执行对应逻辑
        ensureCanvas();
        //> 把子节点追加到当前元素内部末尾
        document.body.appendChild(canvas);
        //> 调用函数「resize」并传入参数执行对应逻辑
        resize();
        //> 调用函数「bindEvents」并传入参数执行对应逻辑
        bindEvents();
        //> 给「running」赋值，更新其保存的状态
        running = true;
        //> 给「mounted」赋值，更新其保存的状态
        mounted = true;
        //> 调用函数「loop」并传入参数执行对应逻辑
        loop();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // 停止特效：清空粒子、移除 Canvas、停止动画循环
    // =========================================================
    // 【函数】stopEffect
    // 功能：处理「stop effect」相关逻辑（mouse-effect）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function stopEffect() {
        //> 给「running」赋值，更新其保存的状态
        running = false;
        //> 给「particles」赋值，更新其保存的状态
        particles = [];
        //> 条件判断：满足括号内条件时执行对应分支
        if (canvas && canvas.parentNode) {
            //> 操作「canvas.parentNode」的相关方法/属性
            canvas.parentNode.removeChild(canvas);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 给「mounted」赋值，更新其保存的状态
        mounted = false;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // 全局切换函数：切换开关状态并持久化到 localStorage
    // =========================================================
    // 【函数】toggleMouseEffect
    // 功能：切换「mouse effect」相关逻辑（toggle mouse effect）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function toggleMouseEffect() {
        //> 给「enabled」赋值，更新其保存的状态
        enabled = !enabled;
        //> 尝试执行可能出错的代码，出错则进入 catch
        try {
            //> 操作 localStorage（持久化本地存储），注意容量与解析异常
            localStorage.setItem(STORAGE_KEY, enabled ? 'true' : 'false');
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        } catch (e) { /* 隐私模式等场景下忽略写入失败 */ }
        //> 条件判断：满足括号内条件时执行对应分支
        if (enabled) {
            //> 调用函数「startEffect」并传入参数执行对应逻辑
            startEffect();
        //> 以上条件都不满足时执行的兜底分支
        } else {
            //> 调用函数「stopEffect」并传入参数执行对应逻辑
            stopEffect();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 调用函数「updateToggleButton」并传入参数执行对应逻辑
        updateToggleButton();
        //> 返回结果并结束当前函数
        return enabled;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // 暴露到全局，供 base.html 中的按钮调用
    //> 给「window.toggleMouseEffect」赋值，更新其保存的状态
    window.toggleMouseEffect = toggleMouseEffect;

    // ---------- 尺寸自适应 ----------
    // =========================================================
    // 【函数】resize
    // 功能：处理「resize」相关逻辑（mouse-effect）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function resize() {
        // 用 devicePixelRatio 保证高分屏清晰，同时限制上限避免过大开销
        //> 声明变量「dpr」（dpr），用于保存对应数据
        var dpr = Math.min(window.devicePixelRatio || 1, 2);
        //> 给「canvas.width」赋值，更新其保存的状态
        canvas.width = Math.floor(window.innerWidth * dpr);
        //> 给「canvas.height」赋值，更新其保存的状态
        canvas.height = Math.floor(window.innerHeight * dpr);
        //> 操作「ctx」的相关方法/属性
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // ---------- 粒子池 ----------
    //> 声明变量「particles」（particles），用于保存对应数据
    var particles = [];

    /**
     * 在指定位置生成一个粒子
     * @param {number} x 水平坐标（CSS 像素）
     * @param {number} y 垂直坐标（CSS 像素）
     */
    // =========================================================
    // 【函数】spawn
    // 功能：处理「spawn」相关逻辑（mouse-effect）
    // 参数：
    //   - x：传入的参数（含义结合调用处与函数体）
    //   - y：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function spawn(x, y) {
        // 随机选择形状：0 = 樱花花瓣，1 = 星星
        //> 声明变量「type」（type），用于保存对应数据
        var type = Math.random() < 0.5 ? 'petal' : 'star';
        //> 声明变量「size」（size），用于保存对应数据
        var size = PARTICLE_SIZE_MIN + Math.random() * (PARTICLE_SIZE_MAX - PARTICLE_SIZE_MIN);
        //> 操作「particles」的相关方法/属性
        particles.push({
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            x: x,
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            y: y,
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            vx: (Math.random() - 0.5) * 2,          // 水平速度 -1 ~ 1
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            vy: Math.random() * 0.5,                // 初始向上/微向下
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            size: size,
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            rotation: Math.random() * Math.PI * 2, // 初始旋转角
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            rotationSpeed: (Math.random() - 0.5) * 0.1, // 旋转速度
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            life: 1,                                // 剩余生命值 1 -> 0
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            decay: 0.008 + Math.random() * 0.012,   // 每帧衰减
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            type: type,
            // 樱花粉 / 星星紫蓝，随机取色
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            color: type === 'petal'
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                ? 'rgba(255, 143, 177,'
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                : 'rgba(160, 108, 213,'
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });

        // 超出上限时移除最老的粒子（数组头部）
        //> 当条件为真时反复执行循环体
        while (particles.length > MAX_PARTICLES) {
            //> 操作「particles」的相关方法/属性
            particles.shift();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // ---------- 绘制单个粒子 ----------
    // =========================================================
    // 【函数】drawParticle
    // 功能：绘制「particle」相关逻辑（draw particle）
    // 参数：
    //   - p：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function drawParticle(p) {
        //> 操作「ctx」的相关方法/属性
        ctx.save();
        //> 操作「ctx」的相关方法/属性
        ctx.translate(p.x, p.y);
        //> 操作「ctx」的相关方法/属性
        ctx.rotate(p.rotation);
        //> 给「ctx.globalAlpha」赋值，更新其保存的状态
        ctx.globalAlpha = Math.max(p.life, 0);

        //> 条件判断：满足括号内条件时执行对应分支
        if (p.type === 'petal') {
            // 樱花花瓣：用一个粉色椭圆旋转模拟
            //> 给「ctx.fillStyle」赋值，更新其保存的状态
            ctx.fillStyle = p.color + '0.9)';
            //> 操作「ctx」的相关方法/属性
            ctx.beginPath();
            //> 操作「ctx」的相关方法/属性
            ctx.ellipse(0, 0, p.size, p.size * 0.55, 0, 0, Math.PI * 2);
            //> 操作「ctx」的相关方法/属性
            ctx.fill();
        //> 以上条件都不满足时执行的兜底分支
        } else {
            // 星星：四角星
            //> 给「ctx.fillStyle」赋值，更新其保存的状态
            ctx.fillStyle = p.color + '0.95)';
            //> 声明变量「r」（r），用于保存对应数据
            var r = p.size;
            //> 操作「ctx」的相关方法/属性
            ctx.beginPath();
            //> 循环：按条件重复执行循环体
            for (var i = 0; i < 8; i++) {
                //> 声明变量「angle」（angle），用于保存对应数据，值为一个函数
                var angle = (Math.PI / 4) * i;
                //> 声明变量「radius」（radius），用于保存对应数据，值为一个函数
                var radius = (i % 2 === 0) ? r : r * 0.4;
                //> 声明变量「px」（px），用于保存对应数据
                var px = Math.cos(angle) * radius;
                //> 声明变量「py」（py），用于保存对应数据
                var py = Math.sin(angle) * radius;
                //> 条件判断：满足括号内条件时执行对应分支
                if (i === 0) ctx.moveTo(px, py);
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                else ctx.lineTo(px, py);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 操作「ctx」的相关方法/属性
            ctx.closePath();
            //> 操作「ctx」的相关方法/属性
            ctx.fill();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 操作「ctx」的相关方法/属性
        ctx.restore();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // ---------- 每帧更新 ----------
    // =========================================================
    // 【函数】update
    // 功能：更新相关逻辑（update）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function update() {
        //> 循环：按条件重复执行循环体
        for (var i = particles.length - 1; i >= 0; i--) {
            //> 声明变量「p」（p），用于保存对应数据
            var p = particles[i];
            //> 操作「p」的相关方法/属性
            p.vy += GRAVITY;        // 重力加速
            //> 操作「p」的相关方法/属性
            p.x += p.vx;
            //> 操作「p」的相关方法/属性
            p.y += p.vy;
            //> 操作「p」的相关方法/属性
            p.rotation += p.rotationSpeed;
            //> 操作「p」的相关方法/属性
            p.life -= p.decay;

            // 生命结束或飘出屏幕底部则移除
            //> 条件判断：满足括号内条件时执行对应分支
            if (p.life <= 0 || p.y > window.innerHeight + 20) {
                //> 操作「particles」的相关方法/属性
                particles.splice(i, 1);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // =========================================================
    // 【函数】render
    // 功能：渲染相关逻辑（render）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function render() {
        //> 操作「ctx」的相关方法/属性
        ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
        //> 循环：按条件重复执行循环体
        for (var i = 0; i < particles.length; i++) {
            //> 调用函数「drawParticle」并传入参数执行对应逻辑
            drawParticle(particles[i]);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // ---------- 动画循环（页面不可见时暂停；running 由 start/stop 控制） ----------
    // =========================================================
    // 【函数】loop
    // 功能：处理「loop」相关逻辑（mouse-effect）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function loop() {
        //> 条件判断：满足括号内条件时执行对应分支
        if (!running) return;
        //> 条件判断：满足括号内条件时执行对应分支
        if (!document.hidden) {
            //> 调用函数「update」并传入参数执行对应逻辑
            update();
            //> 调用函数「render」并传入参数执行对应逻辑
            render();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 在下一帧重绘前执行回调，是流畅动画的标准做法
        requestAnimationFrame(loop);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // ---------- 事件绑定 ----------
    // =========================================================
    // 【函数】bindEvents
    // 功能：绑定「events」相关逻辑（bind events）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function bindEvents() {
        //> 条件判断：满足括号内条件时执行对应分支
        if (eventsBound) return;   // 重复挂载时只绑定一次，避免事件叠加
        //> 给「eventsBound」赋值，更新其保存的状态
        eventsBound = true;
        //> 绑定「resize」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        window.addEventListener('resize', resize);

        // 鼠标移动：节流生成粒子（特效关闭时不生成）
        //> 声明变量「lastSpawn」（last spawn），用于保存对应数据
        var lastSpawn = 0;
        //> 绑定「mousemove」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        window.addEventListener('mousemove', function (e) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (!running) return;
            //> 声明变量「now」（now），用于保存对应数据
            var now = performance.now();
            // 约每 16ms 生成一次，避免快速移动时粒子爆炸
            //> 条件判断：满足括号内条件时执行对应分支
            if (now - lastSpawn < 16) return;
            //> 给「lastSpawn」赋值，更新其保存的状态
            lastSpawn = now;
            //> 循环：按条件重复执行循环体
            for (var i = 0; i < SPAWN_PER_MOVE; i++) {
                //> 调用函数「spawn」并传入参数执行对应逻辑
                spawn(e.clientX + (Math.random() - 0.5) * 6,
                      //> 操作「e」的相关方法/属性
                      e.clientY + (Math.random() - 0.5) * 6);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }, { passive: true });

        // 触摸支持（移动端）
        //> 绑定「touchmove」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        window.addEventListener('touchmove', function (e) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (!running) return;
            //> 条件判断：满足括号内条件时执行对应分支
            if (!e.touches || e.touches.length === 0) return;
            //> 声明变量「t」（t），用于保存对应数据
            var t = e.touches[0];
            //> 循环：按条件重复执行循环体
            for (var i = 0; i < SPAWN_PER_MOVE; i++) {
                //> 调用函数「spawn」并传入参数执行对应逻辑
                spawn(t.clientX + (Math.random() - 0.5) * 6,
                      //> 操作「t」的相关方法/属性
                      t.clientY + (Math.random() - 0.5) * 6);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }, { passive: true });

        // 页面可见性变化时暂停 / 恢复动画
        //> 绑定「visibilitychange」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('visibilitychange', function () {
            //> 条件判断：满足括号内条件时执行对应分支
            if (document.hidden) {
                //> 给「running」赋值，更新其保存的状态
                running = false;
            //> 否则若满足该条件则进入此分支
            } else if (!running && mounted) {
                //> 给「running」赋值，更新其保存的状态
                running = true;
                //> 调用函数「loop」并传入参数执行对应逻辑
                loop();
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // 同步开关按钮的视觉状态：关闭时置灰
    // =========================================================
    // 【函数】updateToggleButton
    // 功能：更新「toggle button」相关逻辑（update toggle button）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function updateToggleButton() {
        //> 声明变量「btn」（btn），用于保存对应数据，保存 DOM/窗口相关对象
        var btn = document.getElementById('mouse-effect-toggle');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!btn) return;
        //> 给「btn.style.opacity」赋值，更新其保存的状态
        btn.style.opacity = enabled ? '1' : '.45';
        //> 给「btn.title」赋值，更新其保存的状态
        btn.title = enabled ? '切换鼠标特效（当前开启）' : '切换鼠标特效（当前关闭）';
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // 绑定开关按钮点击事件
    // =========================================================
    // 【函数】bindToggleButton
    // 功能：绑定「toggle button」相关逻辑（bind toggle button）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function bindToggleButton() {
        //> 声明变量「btn」（btn），用于保存对应数据，保存 DOM/窗口相关对象
        var btn = document.getElementById('mouse-effect-toggle');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!btn) return;
        //> 调用函数「updateToggleButton」并传入参数执行对应逻辑
        updateToggleButton();
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        btn.addEventListener('click', function () {
            //> 调用函数「toggleMouseEffect」并传入参数执行对应逻辑
            toggleMouseEffect();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // ---------- 启动：默认开启时才挂载；关闭则仅暴露 toggleMouseEffect ----------
    // =========================================================
    // 【函数】boot
    // 功能：处理「boot」相关逻辑（mouse-effect）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function boot() {
        //> 条件判断：满足括号内条件时执行对应分支
        if (enabled) {
            //> 调用函数「startEffect」并传入参数执行对应逻辑
            startEffect();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 调用函数「bindToggleButton」并传入参数执行对应逻辑
        bindToggleButton();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    //> 条件判断：满足括号内条件时执行对应分支
    if (document.readyState === 'loading') {
        //> 绑定「DOMContentLoaded」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('DOMContentLoaded', boot);
    //> 以上条件都不满足时执行的兜底分支
    } else {
        //> 调用函数「boot」并传入参数执行对应逻辑
        boot();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

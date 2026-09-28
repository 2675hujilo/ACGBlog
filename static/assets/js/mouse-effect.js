/* ============================================================
 * mouse-effect.js —— 鼠标跟随粒子特效
 * 鼠标移动时在指针位置生成樱花花瓣 / 星星粒子，带重力下落与旋转。
 * 性能友好：粒子总数上限 60 个，页面不可见时暂停 rAF，Canvas 不拦截事件。
 * ============================================================ */
(function () {
    'use strict';

    // ---------- 开关状态：读取 localStorage，默认开启 ----------
    var STORAGE_KEY = 'mouse_effect_enabled';
    var enabled = (function () {
        try {
            // 未设置时默认开启；仅当显式存为 'false' 时关闭
            return localStorage.getItem(STORAGE_KEY) !== 'false';
        } catch (e) {
            return true;
        }
    })();

    // ---------- 配置项 ----------
    var MAX_PARTICLES = 60;          // 粒子数量上限，超出时移除最老的
    var GRAVITY = 0.08;              // 向下的重力加速度
    var PARTICLE_SIZE_MIN = 6;        // 粒子最小尺寸（px）
    var PARTICLE_SIZE_MAX = 12;       // 粒子最大尺寸（px）
    var SPAWN_PER_MOVE = 2;          // 每次 mousemove 生成的粒子数（节流用）

    // ---------- 全屏 Canvas（按需创建，默认开启时才挂载） ----------
    var canvas = null;
    var ctx = null;
    var mounted = false;             // Canvas 是否已挂载到 body
    var eventsBound = false;         // 事件是否已绑定（避免重复绑定）
    var running = false;             // 动画循环是否在运行

    function ensureCanvas() {
        if (canvas) return;
        canvas = document.createElement('canvas');
        canvas.setAttribute('aria-hidden', 'true');
        ctx = canvas.getContext('2d');
        // 关键样式：fixed 全屏、不拦截鼠标事件、最高层级
        canvas.style.cssText =
            'position:fixed;top:0;left:0;width:100vw;height:100vh;' +
            'pointer-events:none;z-index:9999;';
    }

    // 启动特效：挂载 Canvas、绑定事件、开启动画循环
    function startEffect() {
        if (mounted) return;
        ensureCanvas();
        document.body.appendChild(canvas);
        resize();
        bindEvents();
        running = true;
        mounted = true;
        loop();
    }

    // 停止特效：清空粒子、移除 Canvas、停止动画循环
    function stopEffect() {
        running = false;
        particles = [];
        if (canvas && canvas.parentNode) {
            canvas.parentNode.removeChild(canvas);
        }
        mounted = false;
    }

    // 全局切换函数：切换开关状态并持久化到 localStorage
    function toggleMouseEffect() {
        enabled = !enabled;
        try {
            localStorage.setItem(STORAGE_KEY, enabled ? 'true' : 'false');
        } catch (e) { /* 隐私模式等场景下忽略写入失败 */ }
        if (enabled) {
            startEffect();
        } else {
            stopEffect();
        }
        updateToggleButton();
        return enabled;
    }
    // 暴露到全局，供 base.html 中的按钮调用
    window.toggleMouseEffect = toggleMouseEffect;

    // ---------- 尺寸自适应 ----------
    function resize() {
        // 用 devicePixelRatio 保证高分屏清晰，同时限制上限避免过大开销
        var dpr = Math.min(window.devicePixelRatio || 1, 2);
        canvas.width = Math.floor(window.innerWidth * dpr);
        canvas.height = Math.floor(window.innerHeight * dpr);
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    // ---------- 粒子池 ----------
    var particles = [];

    /**
     * 在指定位置生成一个粒子
     * @param {number} x 水平坐标（CSS 像素）
     * @param {number} y 垂直坐标（CSS 像素）
     */
    function spawn(x, y) {
        // 随机选择形状：0 = 樱花花瓣，1 = 星星
        var type = Math.random() < 0.5 ? 'petal' : 'star';
        var size = PARTICLE_SIZE_MIN + Math.random() * (PARTICLE_SIZE_MAX - PARTICLE_SIZE_MIN);
        particles.push({
            x: x,
            y: y,
            vx: (Math.random() - 0.5) * 2,          // 水平速度 -1 ~ 1
            vy: Math.random() * 0.5,                // 初始向上/微向下
            size: size,
            rotation: Math.random() * Math.PI * 2, // 初始旋转角
            rotationSpeed: (Math.random() - 0.5) * 0.1, // 旋转速度
            life: 1,                                // 剩余生命值 1 -> 0
            decay: 0.008 + Math.random() * 0.012,   // 每帧衰减
            type: type,
            // 樱花粉 / 星星紫蓝，随机取色
            color: type === 'petal'
                ? 'rgba(255, 143, 177,'
                : 'rgba(160, 108, 213,'
        });

        // 超出上限时移除最老的粒子（数组头部）
        while (particles.length > MAX_PARTICLES) {
            particles.shift();
        }
    }

    // ---------- 绘制单个粒子 ----------
    function drawParticle(p) {
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rotation);
        ctx.globalAlpha = Math.max(p.life, 0);

        if (p.type === 'petal') {
            // 樱花花瓣：用一个粉色椭圆旋转模拟
            ctx.fillStyle = p.color + '0.9)';
            ctx.beginPath();
            ctx.ellipse(0, 0, p.size, p.size * 0.55, 0, 0, Math.PI * 2);
            ctx.fill();
        } else {
            // 星星：四角星
            ctx.fillStyle = p.color + '0.95)';
            var r = p.size;
            ctx.beginPath();
            for (var i = 0; i < 8; i++) {
                var angle = (Math.PI / 4) * i;
                var radius = (i % 2 === 0) ? r : r * 0.4;
                var px = Math.cos(angle) * radius;
                var py = Math.sin(angle) * radius;
                if (i === 0) ctx.moveTo(px, py);
                else ctx.lineTo(px, py);
            }
            ctx.closePath();
            ctx.fill();
        }
        ctx.restore();
    }

    // ---------- 每帧更新 ----------
    function update() {
        for (var i = particles.length - 1; i >= 0; i--) {
            var p = particles[i];
            p.vy += GRAVITY;        // 重力加速
            p.x += p.vx;
            p.y += p.vy;
            p.rotation += p.rotationSpeed;
            p.life -= p.decay;

            // 生命结束或飘出屏幕底部则移除
            if (p.life <= 0 || p.y > window.innerHeight + 20) {
                particles.splice(i, 1);
            }
        }
    }

    function render() {
        ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
        for (var i = 0; i < particles.length; i++) {
            drawParticle(particles[i]);
        }
    }

    // ---------- 动画循环（页面不可见时暂停；running 由 start/stop 控制） ----------
    function loop() {
        if (!running) return;
        if (!document.hidden) {
            update();
            render();
        }
        requestAnimationFrame(loop);
    }

    // ---------- 事件绑定 ----------
    function bindEvents() {
        if (eventsBound) return;   // 重复挂载时只绑定一次，避免事件叠加
        eventsBound = true;
        window.addEventListener('resize', resize);

        // 鼠标移动：节流生成粒子（特效关闭时不生成）
        var lastSpawn = 0;
        window.addEventListener('mousemove', function (e) {
            if (!running) return;
            var now = performance.now();
            // 约每 16ms 生成一次，避免快速移动时粒子爆炸
            if (now - lastSpawn < 16) return;
            lastSpawn = now;
            for (var i = 0; i < SPAWN_PER_MOVE; i++) {
                spawn(e.clientX + (Math.random() - 0.5) * 6,
                      e.clientY + (Math.random() - 0.5) * 6);
            }
        }, { passive: true });

        // 触摸支持（移动端）
        window.addEventListener('touchmove', function (e) {
            if (!running) return;
            if (!e.touches || e.touches.length === 0) return;
            var t = e.touches[0];
            for (var i = 0; i < SPAWN_PER_MOVE; i++) {
                spawn(t.clientX + (Math.random() - 0.5) * 6,
                      t.clientY + (Math.random() - 0.5) * 6);
            }
        }, { passive: true });

        // 页面可见性变化时暂停 / 恢复动画
        document.addEventListener('visibilitychange', function () {
            if (document.hidden) {
                running = false;
            } else if (!running && mounted) {
                running = true;
                loop();
            }
        });
    }

    // 同步开关按钮的视觉状态：关闭时置灰
    function updateToggleButton() {
        var btn = document.getElementById('mouse-effect-toggle');
        if (!btn) return;
        btn.style.opacity = enabled ? '1' : '.45';
        btn.title = enabled ? '切换鼠标特效（当前开启）' : '切换鼠标特效（当前关闭）';
    }

    // 绑定开关按钮点击事件
    function bindToggleButton() {
        var btn = document.getElementById('mouse-effect-toggle');
        if (!btn) return;
        updateToggleButton();
        btn.addEventListener('click', function () {
            toggleMouseEffect();
        });
    }

    // ---------- 启动：默认开启时才挂载；关闭则仅暴露 toggleMouseEffect ----------
    function boot() {
        if (enabled) {
            startEffect();
        }
        bindToggleButton();
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();

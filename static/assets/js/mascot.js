/* Bug11 文件头注释
 * 看板娘交互脚本：提示语轮播、点击换装/隐藏、工具栏按钮与舞台显隐逻辑。
 * 与 Live2D 引擎协作驱动吉祥物的动作与对话，增强陪伴感。
 */
﻿/* ============================================================
   看板娘 Mascot 交互逻辑
   功能：5热区交互 / 换皮肤 / 拖动 / 最小化 / 随机说话 / 阅读提示
   ============================================================ */
(function () {
    'use strict';

    // ========== 配置 ==========
    var SKINS = [
        { id: 'purple', name: '紫发魔法喵', img: 'mascot_purple.svg' },
        { id: 'pink', name: '粉发猫耳喵', img: 'mascot_pink.svg' },
        { id: 'blue', name: '蓝发机械喵', img: 'mascot_blue.svg' },
        { id: 'white', name: '银发狐耳喵', img: 'mascot_white.svg' }
    ];

    var STATIC_BASE = '/static/assets/img/mascot/';

    // ========== 吐槽文案库 ==========
    var DIALOGUES = {
        head: [
            '喵~好舒服喵~再摸摸嘛',
            '哼哼，本喵的头可不是随便摸的哦',
            '唔...头发都被弄乱啦！',
            '喵呜~摸头会变聪明的喵',
            '再摸我就要打瞌睡了喵~'
        ],
        forehead: [
            '唔！戳额头会变笨的啦！',
            '别戳啦！额头会凹进去的！',
            '哼！再戳我就生气了哦',
            '喵？你在做什么喵',
            '额头是弱点啦笨蛋！'
        ],
        belly: [
            '呀！肚子是禁区啦笨蛋！',
            '呜哇~不要碰肚子啦！',
            '变态！往哪摸呢！',
            '喵~肚子软软的对吧',
            '再碰肚子我就咬你哦！'
        ],
        legs: [
            '变态！往哪摸呢！',
            '不要碰腿啦！好痒！',
            '哼！本喵的腿才不给你摸',
            '喵呜~腿腿会害羞的啦',
            '再摸腿我就踢你哦！'
        ],
        feet: [
            '哈哈哈好痒！别碰脚啦！',
            '喵~脚脚好痒的喵！',
            '不要挠脚心啦！哈哈哈',
            '脚脚是最敏感的地方喵',
            '再碰脚我就跳起来了哦！'
        ],
        random: [
            '欢迎回来喵~今天也要加油哦',
            '喵？你在看什么呢',
            '本喵可是最可爱的看板娘喵',
            '要不要喝杯茶再走喵~',
            '文章写得不错嘛，本喵认可了',
            '喵呜~有点无聊了，陪我玩嘛',
            '记得早点休息哦，熬夜对身体不好',
            '今天的你也很努力呢喵~',
            '喵~本喵饿了，有小鱼干吗',
            '点击不同的地方会有不同反应哦喵'
        ],
        scroll: [
            '慢慢看喵~不着急',
            '已经读了这么多啦，好厉害喵',
            '喵~这篇文章好长啊',
            '加油加油，快看完了喵',
            '本喵陪你一起看~'
        ]
    };

    // ========== 状态 ==========
    var currentSkin = localStorage.getItem('mascot_skin') || 'purple';
    var isMinimized = localStorage.getItem('mascot_minimized') === 'true';
    var bubbleTimer = null;
    var randomTimer = null;
    var lastScrollSay = 0;

    // ========== 初始化 ==========
    function init() {
        // DOM已在base.html中静态创建，直接获取
        var container = document.getElementById('mascot-container');
        if (!container) return;

        // 恢复位置
        var savedPos = localStorage.getItem('mascot_position');
        if (savedPos) {
            try {
                var pos = JSON.parse(savedPos);
                container.style.right = 'auto';
                container.style.bottom = 'auto';
                container.style.left = pos.left + 'px';
                container.style.top = pos.top + 'px';
            } catch (e) {}
        }

        // 设置皮肤
        setSkin(currentSkin);

        // 最小化状态
        if (isMinimized) {
            container.classList.add('minimized');
        }

        // 绑定事件
        bindEvents(container);

        // 构建皮肤列表
        buildSkinList();

        // 启动随机说话
        startRandomTalk();

        // 欢迎语
        setTimeout(function () {
            say(randomPick(DIALOGUES.random));
        }, 1500);
    }

    // ========== 绑定事件 ==========
    function bindEvents(container) {
        var img = document.getElementById('mascot-image');
        var bubble = document.getElementById('mascot-bubble');
        var skinPanel = document.getElementById('mascot-skin-panel');

        // 热区点击
        container.querySelectorAll('.mascot-hitarea').forEach(function (area) {
            area.addEventListener('click', function (e) {
                e.stopPropagation();
                var type = this.dataset.area;
                handleHit(type, img);
            });
        });

        // 点击图片（非热区）随机说话
        img.addEventListener('click', function () {
            say(randomPick(DIALOGUES.random));
            playAnim(img, 'bounce');
        });

        // 换肤按钮
        document.getElementById('mascot-skin-btn').addEventListener('click', function (e) {
            e.stopPropagation();
            skinPanel.classList.toggle('show');
        });

        // 最小化按钮
        document.getElementById('mascot-min-btn').addEventListener('click', function (e) {
            e.stopPropagation();
            toggleMinimize(container);
        });

        // 点击外部关闭皮肤面板
        document.addEventListener('click', function (e) {
            if (!container.contains(e.target)) {
                skinPanel.classList.remove('show');
            }
        });

        // 拖动
        enableDrag(container);

        // 滚动阅读提示
        window.addEventListener('scroll', function () {
            var now = Date.now();
            if (now - lastScrollSay > 15000 && Math.random() < 0.3) {
                lastScrollSay = now;
                say(randomPick(DIALOGUES.scroll));
            }
        });
    }

    // ========== 热区处理 ==========
    function handleHit(type, img) {
        var lines = DIALOGUES[type] || DIALOGUES.random;
        say(randomPick(lines));

        // SVG分体动画：触发对应部位的动画
        var svg = img.contentDocument || img.getSVGDocument();
        var animMap = {
            head: { selector: '.mascot-head', cls: 'pat-head' },
            forehead: { selector: '.mascot-head', cls: 'shy-forehead' },
            belly: { selector: '.mascot-body', cls: 'tickle-belly' },
            legs: { selector: '.mascot-legs', cls: 'kick-legs' },
            feet: { selector: '.mascot-legs', cls: 'jump-feet' }
        };
        var cfg = animMap[type];
        if (svg && cfg) {
            var part = svg.querySelector(cfg.selector);
            if (part) {
                part.classList.remove(cfg.cls);
                void part.getBoundingClientRect();
                part.classList.add(cfg.cls);
                setTimeout(function(){ part.classList.remove(cfg.cls); }, 800);
            }
        } else {
            // 降级：整体动画
            playAnim(img, 'bounce');
        }
        // 挥手特效（右手臂）
        if (svg && type === 'head') {
            var arm = svg.querySelector('.mascot-arm-right');
            if (arm) {
                arm.classList.remove('wave');
                void arm.getBoundingClientRect();
                arm.classList.add('wave');
                setTimeout(function(){ arm.classList.remove('wave'); }, 900);
            }
        }
    }

    // ========== 说话 ==========
    function say(text) {
        var bubble = document.getElementById('mascot-bubble');
        if (!bubble) return;
        bubble.textContent = text;
        bubble.classList.add('show');
        if (bubbleTimer) clearTimeout(bubbleTimer);
        bubbleTimer = setTimeout(function () {
            bubble.classList.remove('show');
        }, 3500);
    }

    // ========== 播放动画 ==========
    function playAnim(img, anim) {
        img.classList.remove('bounce', 'shy', 'angry', 'happy');
        void img.offsetWidth; // 触发重绘
        img.classList.add(anim);
        setTimeout(function () {
            img.classList.remove(anim);
        }, 700);
    }

    // ========== 换皮肤 ==========
    function setSkin(skinId) {
        var skin = SKINS.find(function (s) { return s.id === skinId; });
        if (!skin) skin = SKINS[0];
        currentSkin = skin.id;
        localStorage.setItem('mascot_skin', skin.id);
        var img = document.getElementById('mascot-image');
        if (img) {
            img.src = STATIC_BASE + skin.img;
        }
        // 更新皮肤列表选中状态
        document.querySelectorAll('.mascot-skin-item').forEach(function (item) {
            item.classList.toggle('active', item.dataset.skin === skin.id);
        });
    }

    function buildSkinList() {
        var list = document.getElementById('mascot-skin-list');
        if (!list) return;
        list.innerHTML = '';
        SKINS.forEach(function (skin) {
            var item = document.createElement('div');
            item.className = 'mascot-skin-item' + (skin.id === currentSkin ? ' active' : '');
            item.dataset.skin = skin.id;
            item.title = skin.name;
            item.innerHTML = '<img src="' + STATIC_BASE + skin.img + '" alt="' + skin.name + '">' +
                '<div class="mascot-skin-name">' + skin.name + '</div>';
            item.addEventListener('click', function (e) {
                e.stopPropagation();
                setSkin(skin.id);
                say('换好新衣服啦喵~好看吗？');
            });
            list.appendChild(item);
        });
    }

    // ========== 最小化 ==========
    function toggleMinimize(container) {
        isMinimized = !isMinimized;
        container.classList.toggle('minimized', isMinimized);
        localStorage.setItem('mascot_minimized', isMinimized);
        var btn = document.getElementById('mascot-min-btn');
        if (btn) btn.textContent = isMinimized ? '+' : '_';
        if (isMinimized) {
            // 最小化时点击展开
            container.onclick = function () {
                if (isMinimized) toggleMinimize(container);
            };
        } else {
            container.onclick = null;
        }
    }

    // ========== 拖动 ==========
    function enableDrag(container) {
        var isDragging = false;
        var startX, startY, startLeft, startTop;
        var hasMoved = false;

        container.addEventListener('mousedown', function (e) {
            if (e.target.closest('.mascot-toolbar') || e.target.closest('.mascot-skin-panel') || e.target.closest('.mascot-hitarea')) {
                return;
            }
            isDragging = true;
            hasMoved = false;
            var rect = container.getBoundingClientRect();
            startX = e.clientX;
            startY = e.clientY;
            startLeft = rect.left;
            startTop = rect.top;
            container.style.right = 'auto';
            container.style.bottom = 'auto';
            e.preventDefault();
        });

        document.addEventListener('mousemove', function (e) {
            if (!isDragging) return;
            var dx = e.clientX - startX;
            var dy = e.clientY - startY;
            if (Math.abs(dx) > 3 || Math.abs(dy) > 3) hasMoved = true;
            var newLeft = Math.max(0, Math.min(window.innerWidth - container.offsetWidth, startLeft + dx));
            var newTop = Math.max(0, Math.min(window.innerHeight - container.offsetHeight, startTop + dy));
            container.style.left = newLeft + 'px';
            container.style.top = newTop + 'px';
        });

        document.addEventListener('mouseup', function () {
            if (isDragging && hasMoved) {
                var rect = container.getBoundingClientRect();
                localStorage.setItem('mascot_position', JSON.stringify({
                    left: rect.left,
                    top: rect.top
                }));
            }
            isDragging = false;
        });

        // 触摸支持
        container.addEventListener('touchstart', function (e) {
            if (e.target.closest('.mascot-toolbar') || e.target.closest('.mascot-skin-panel') || e.target.closest('.mascot-hitarea')) {
                return;
            }
            var touch = e.touches[0];
            isDragging = true;
            hasMoved = false;
            var rect = container.getBoundingClientRect();
            startX = touch.clientX;
            startY = touch.clientY;
            startLeft = rect.left;
            startTop = rect.top;
            container.style.right = 'auto';
            container.style.bottom = 'auto';
        }, { passive: true });

        container.addEventListener('touchmove', function (e) {
            if (!isDragging) return;
            var touch = e.touches[0];
            var dx = touch.clientX - startX;
            var dy = touch.clientY - startY;
            if (Math.abs(dx) > 3 || Math.abs(dy) > 3) hasMoved = true;
            var newLeft = Math.max(0, Math.min(window.innerWidth - container.offsetWidth, startLeft + dx));
            var newTop = Math.max(0, Math.min(window.innerHeight - container.offsetHeight, startTop + dy));
            container.style.left = newLeft + 'px';
            container.style.top = newTop + 'px';
            e.preventDefault();
        }, { passive: false });

        container.addEventListener('touchend', function () {
            if (isDragging && hasMoved) {
                var rect = container.getBoundingClientRect();
                localStorage.setItem('mascot_position', JSON.stringify({ left: rect.left, top: rect.top }));
            }
            isDragging = false;
        });
    }

    // ========== 随机说话 ==========
    function startRandomTalk() {
        if (randomTimer) clearInterval(randomTimer);
        randomTimer = setInterval(function () {
            if (document.hidden) return;
            if (Math.random() < 0.4) {
                say(randomPick(DIALOGUES.random));
            }
        }, 25000);
    }

    // ========== 工具函数 ==========
    function randomPick(arr) {
        return arr[Math.floor(Math.random() * arr.length)];
    }

    // ========== 启动 ==========
    function safeInit() {
        try {
            init();
            window.__mascotLoaded = true;
        } catch (e) {
            console.error('看板娘初始化失败:', e);
            window.__mascotError = e.message;
        }
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', safeInit);
    } else {
        safeInit();
    }
})();

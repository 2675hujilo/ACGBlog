/* Bug11 文件头注释
 * 看板娘交互脚本：提示语轮播、点击换装/隐藏、工具栏按钮与舞台显隐逻辑。
 * 与 Live2D 引擎协作驱动吉祥物的动作与对话，增强陪伴感。
 */
//> 该行执行对应的脚本逻辑（结合上下文理解）
﻿/* ============================================================
   //> 该行执行对应的脚本逻辑（结合上下文理解）
   看板娘 Mascot 交互逻辑
   //> 该行执行对应的脚本逻辑（结合上下文理解）
   功能：5热区交互 / 换皮肤 / 拖动 / 最小化 / 随机说话 / 阅读提示
   //> 该行执行对应的脚本逻辑（结合上下文理解）
   ============================================================ */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';

    // ========== 配置 ==========
    //> 声明变量「SKINS」（skins），用于保存对应数据
    var SKINS = [
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        { id: 'purple', name: '紫发魔法喵', img: 'mascot_purple.svg' },
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        { id: 'pink', name: '粉发猫耳喵', img: 'mascot_pink.svg' },
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        { id: 'blue', name: '蓝发机械喵', img: 'mascot_blue.svg' },
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        { id: 'white', name: '银发狐耳喵', img: 'mascot_white.svg' }
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    ];

    //> 声明变量「STATIC_BASE」（static base），用于保存对应数据，初始为字符串
    var STATIC_BASE = '/static/assets/img/mascot/';

    // ========== 吐槽文案库 ==========
    //> 声明变量「DIALOGUES」（dialogues），用于保存对应数据
    var DIALOGUES = {
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        head: [
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '喵~好舒服喵~再摸摸嘛',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '哼哼，本喵的头可不是随便摸的哦',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '唔...头发都被弄乱啦！',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '喵呜~摸头会变聪明的喵',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '再摸我就要打瞌睡了喵~'
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        ],
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        forehead: [
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '唔！戳额头会变笨的啦！',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '别戳啦！额头会凹进去的！',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '哼！再戳我就生气了哦',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '喵？你在做什么喵',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '额头是弱点啦笨蛋！'
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        ],
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        belly: [
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '呀！肚子是禁区啦笨蛋！',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '呜哇~不要碰肚子啦！',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '变态！往哪摸呢！',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '喵~肚子软软的对吧',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '再碰肚子我就咬你哦！'
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        ],
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        legs: [
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '变态！往哪摸呢！',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '不要碰腿啦！好痒！',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '哼！本喵的腿才不给你摸',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '喵呜~腿腿会害羞的啦',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '再摸腿我就踢你哦！'
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        ],
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        feet: [
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '哈哈哈好痒！别碰脚啦！',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '喵~脚脚好痒的喵！',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '不要挠脚心啦！哈哈哈',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '脚脚是最敏感的地方喵',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '再碰脚我就跳起来了哦！'
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        ],
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        random: [
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '欢迎回来喵~今天也要加油哦',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '喵？你在看什么呢',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '本喵可是最可爱的看板娘喵',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '要不要喝杯茶再走喵~',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '文章写得不错嘛，本喵认可了',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '喵呜~有点无聊了，陪我玩嘛',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '记得早点休息哦，熬夜对身体不好',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '今天的你也很努力呢喵~',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '喵~本喵饿了，有小鱼干吗',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '点击不同的地方会有不同反应哦喵'
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        ],
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        scroll: [
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '慢慢看喵~不着急',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '已经读了这么多啦，好厉害喵',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '喵~这篇文章好长啊',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '加油加油，快看完了喵',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '本喵陪你一起看~'
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        ]
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    };

    // ========== 状态 ==========
    //> 声明变量「currentSkin」（current skin），用于保存对应数据
    var currentSkin = localStorage.getItem('mascot_skin') || 'purple';
    //> 声明变量「isMinimized」（is minimized），用于保存对应数据
    var isMinimized = localStorage.getItem('mascot_minimized') === 'true';
    //> 声明变量「bubbleTimer」（bubble timer），用于保存对应数据
    var bubbleTimer = null;
    //> 声明变量「randomTimer」（random timer），用于保存对应数据
    var randomTimer = null;
    //> 声明变量「lastScrollSay」（last scroll say），用于保存对应数据
    var lastScrollSay = 0;

    // ========== 初始化 ==========
    // =========================================================
    // 【函数】init
    // 功能：初始化相关逻辑（init）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function init() {
        // DOM已在base.html中静态创建，直接获取
        //> 声明变量「container」（container），用于保存对应数据，保存 DOM/窗口相关对象
        var container = document.getElementById('mascot-container');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!container) return;

        // 恢复位置
        //> 声明变量「savedPos」（saved pos），用于保存对应数据
        var savedPos = localStorage.getItem('mascot_position');
        //> 条件判断：满足括号内条件时执行对应分支
        if (savedPos) {
            //> 尝试执行可能出错的代码，出错则进入 catch
            try {
                //> 声明变量「pos」（pos），用于保存对应数据
                var pos = JSON.parse(savedPos);
                //> 给「container.style.right」赋值，更新其保存的状态
                container.style.right = 'auto';
                //> 给「container.style.bottom」赋值，更新其保存的状态
                container.style.bottom = 'auto';
                //> 给「container.style.left」赋值，更新其保存的状态
                container.style.left = pos.left + 'px';
                //> 给「container.style.top」赋值，更新其保存的状态
                container.style.top = pos.top + 'px';
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            } catch (e) {}
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }

        // 设置皮肤
        //> 调用函数「setSkin」并传入参数执行对应逻辑
        setSkin(currentSkin);

        // 最小化状态
        //> 条件判断：满足括号内条件时执行对应分支
        if (isMinimized) {
            //> 为元素添加一个或多个样式类
            container.classList.add('minimized');
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }

        // 绑定事件
        //> 调用函数「bindEvents」并传入参数执行对应逻辑
        bindEvents(container);

        // 构建皮肤列表
        //> 调用函数「buildSkinList」并传入参数执行对应逻辑
        buildSkinList();

        // 启动随机说话
        //> 调用函数「startRandomTalk」并传入参数执行对应逻辑
        startRandomTalk();

        // 欢迎语
        // =========================================================
        // 【函数】setTimeout
        // 功能：设置「timeout」相关逻辑（set timeout）
        // 参数：
        //   - function：传入的参数（含义结合调用处与函数体）
        //   - (：传入的参数（含义结合调用处与函数体）
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：含定时器，注意在适当时机清除，避免泄漏与重复触发
        // =========================================================
        setTimeout(function () {
            //> 调用函数「say」并传入参数执行对应逻辑
            say(randomPick(DIALOGUES.random));
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }, 1500);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // ========== 绑定事件 ==========
    // =========================================================
    // 【函数】bindEvents
    // 功能：绑定「events」相关逻辑（bind events）
    // 参数：
    //   - container：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function bindEvents(container) {
        //> 声明变量「img」（img），用于保存对应数据，保存 DOM/窗口相关对象
        var img = document.getElementById('mascot-image');
        //> 声明变量「bubble」（bubble），用于保存对应数据，保存 DOM/窗口相关对象
        var bubble = document.getElementById('mascot-bubble');
        //> 声明变量「skinPanel」（skin panel），用于保存对应数据，保存 DOM/窗口相关对象
        var skinPanel = document.getElementById('mascot-skin-panel');

        // 热区点击
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        container.querySelectorAll('.mascot-hitarea').forEach(function (area) {
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            area.addEventListener('click', function (e) {
                //> 阻止事件继续向上冒泡
                e.stopPropagation();
                //> 声明变量「type」（type），用于保存对应数据
                var type = this.dataset.area;
                //> 调用函数「handleHit」并传入参数执行对应逻辑
                handleHit(type, img);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });

        // 点击图片（非热区）随机说话
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        img.addEventListener('click', function () {
            //> 调用函数「say」并传入参数执行对应逻辑
            say(randomPick(DIALOGUES.random));
            //> 调用函数「playAnim」并传入参数执行对应逻辑
            playAnim(img, 'bounce');
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });

        // 换肤按钮
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.getElementById('mascot-skin-btn').addEventListener('click', function (e) {
            //> 阻止事件继续向上冒泡
            e.stopPropagation();
            //> 切换样式类（有则移除、无则添加），可传第二参强制状态
            skinPanel.classList.toggle('show');
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });

        // 最小化按钮
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.getElementById('mascot-min-btn').addEventListener('click', function (e) {
            //> 阻止事件继续向上冒泡
            e.stopPropagation();
            //> 调用函数「toggleMinimize」并传入参数执行对应逻辑
            toggleMinimize(container);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });

        // 点击外部关闭皮肤面板
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('click', function (e) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (!container.contains(e.target)) {
                //> 移除元素的一个或多个样式类
                skinPanel.classList.remove('show');
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });

        // 拖动
        //> 调用函数「enableDrag」并传入参数执行对应逻辑
        enableDrag(container);

        // 滚动阅读提示
        //> 绑定「scroll」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        window.addEventListener('scroll', function () {
            //> 声明变量「now」（now），用于保存对应数据
            var now = Date.now();
            //> 条件判断：满足括号内条件时执行对应分支
            if (now - lastScrollSay > 15000 && Math.random() < 0.3) {
                //> 给「lastScrollSay」赋值，更新其保存的状态
                lastScrollSay = now;
                //> 调用函数「say」并传入参数执行对应逻辑
                say(randomPick(DIALOGUES.scroll));
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // ========== 热区处理 ==========
    // =========================================================
    // 【函数】handleHit
    // 功能：处理「hit」相关逻辑（handle hit）
    // 参数：
    //   - type：传入的参数（含义结合调用处与函数体）
    //   - img：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function handleHit(type, img) {
        //> 声明变量「lines」（lines），用于保存对应数据
        var lines = DIALOGUES[type] || DIALOGUES.random;
        //> 调用函数「say」并传入参数执行对应逻辑
        say(randomPick(lines));

        // SVG分体动画：触发对应部位的动画
        //> 声明变量「svg」（svg），用于保存对应数据
        var svg = img.contentDocument || img.getSVGDocument();
        //> 声明变量「animMap」（anim map），用于保存对应数据
        var animMap = {
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            head: { selector: '.mascot-head', cls: 'pat-head' },
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            forehead: { selector: '.mascot-head', cls: 'shy-forehead' },
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            belly: { selector: '.mascot-body', cls: 'tickle-belly' },
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            legs: { selector: '.mascot-legs', cls: 'kick-legs' },
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            feet: { selector: '.mascot-legs', cls: 'jump-feet' }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        };
        //> 声明变量「cfg」（cfg），用于保存对应数据
        var cfg = animMap[type];
        //> 条件判断：满足括号内条件时执行对应分支
        if (svg && cfg) {
            //> 声明变量「part」（part），用于保存对应数据
            var part = svg.querySelector(cfg.selector);
            //> 条件判断：满足括号内条件时执行对应分支
            if (part) {
                //> 移除元素的一个或多个样式类
                part.classList.remove(cfg.cls);
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                void part.getBoundingClientRect();
                //> 为元素添加一个或多个样式类
                part.classList.add(cfg.cls);
                //> 移除元素的一个或多个样式类
                setTimeout(function(){ part.classList.remove(cfg.cls); }, 800);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 以上条件都不满足时执行的兜底分支
        } else {
            // 降级：整体动画
            //> 调用函数「playAnim」并传入参数执行对应逻辑
            playAnim(img, 'bounce');
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // 挥手特效（右手臂）
        //> 条件判断：满足括号内条件时执行对应分支
        if (svg && type === 'head') {
            //> 声明变量「arm」（arm），用于保存对应数据
            var arm = svg.querySelector('.mascot-arm-right');
            //> 条件判断：满足括号内条件时执行对应分支
            if (arm) {
                //> 移除元素的一个或多个样式类
                arm.classList.remove('wave');
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                void arm.getBoundingClientRect();
                //> 为元素添加一个或多个样式类
                arm.classList.add('wave');
                //> 移除元素的一个或多个样式类
                setTimeout(function(){ arm.classList.remove('wave'); }, 900);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // ========== 说话 ==========
    // =========================================================
    // 【函数】say
    // 功能：处理「say」相关逻辑（mascot）
    // 参数：
    //   - text：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function say(text) {
        //> 声明变量「bubble」（bubble），用于保存对应数据，保存 DOM/窗口相关对象
        var bubble = document.getElementById('mascot-bubble');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!bubble) return;
        //> 读写纯文本内容，不解析 HTML，可防 XSS
        bubble.textContent = text;
        //> 为元素添加一个或多个样式类
        bubble.classList.add('show');
        //> 条件判断：满足括号内条件时执行对应分支
        if (bubbleTimer) clearTimeout(bubbleTimer);
        //> 设置延时执行的定时器，返回可清除的定时器 id
        bubbleTimer = setTimeout(function () {
            //> 移除元素的一个或多个样式类
            bubble.classList.remove('show');
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }, 3500);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // ========== 播放动画 ==========
    // =========================================================
    // 【函数】playAnim
    // 功能：播放「anim」相关逻辑（play anim）
    // 参数：
    //   - img：传入的参数（含义结合调用处与函数体）
    //   - anim：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function playAnim(img, anim) {
        //> 移除元素的一个或多个样式类
        img.classList.remove('bounce', 'shy', 'angry', 'happy');
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        void img.offsetWidth; // 触发重绘
        //> 为元素添加一个或多个样式类
        img.classList.add(anim);
        //> 设置延时执行的定时器，返回可清除的定时器 id
        setTimeout(function () {
            //> 移除元素的一个或多个样式类
            img.classList.remove(anim);
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }, 700);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // ========== 换皮肤 ==========
    // =========================================================
    // 【函数】setSkin
    // 功能：设置「skin」相关逻辑（set skin）
    // 参数：
    //   - skinId：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function setSkin(skinId) {
        //> 声明变量「skin」（skin），用于保存对应数据
        var skin = SKINS.find(function (s) { return s.id === skinId; });
        //> 条件判断：满足括号内条件时执行对应分支
        if (!skin) skin = SKINS[0];
        //> 给「currentSkin」赋值，更新其保存的状态
        currentSkin = skin.id;
        //> 操作 localStorage（持久化本地存储），注意容量与解析异常
        localStorage.setItem('mascot_skin', skin.id);
        //> 声明变量「img」（img），用于保存对应数据，保存 DOM/窗口相关对象
        var img = document.getElementById('mascot-image');
        //> 条件判断：满足括号内条件时执行对应分支
        if (img) {
            //> 给「img.src」赋值，更新其保存的状态
            img.src = STATIC_BASE + skin.img;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // 更新皮肤列表选中状态
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        document.querySelectorAll('.mascot-skin-item').forEach(function (item) {
            //> 切换样式类（有则移除、无则添加），可传第二参强制状态
            item.classList.toggle('active', item.dataset.skin === skin.id);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // =========================================================
    // 【函数】buildSkinList
    // 功能：构建「skin list」相关逻辑（build skin list）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function buildSkinList() {
        //> 声明变量「list」（list），用于保存对应数据，保存 DOM/窗口相关对象
        var list = document.getElementById('mascot-skin-list');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!list) return;
        //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
        list.innerHTML = '';
        //> 遍历数组/类数组中的每一项并执行回调
        SKINS.forEach(function (skin) {
            //> 声明变量「item」（item），用于保存对应数据，保存 DOM/窗口相关对象
            var item = document.createElement('div');
            //> 给「item.className」赋值，更新其保存的状态
            item.className = 'mascot-skin-item' + (skin.id === currentSkin ? ' active' : '');
            //> 读写元素的 data-* 自定义数据属性
            item.dataset.skin = skin.id;
            //> 给「item.title」赋值，更新其保存的状态
            item.title = skin.name;
            //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
            item.innerHTML = '<img src="' + STATIC_BASE + skin.img + '" alt="' + skin.name + '">' +
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                '<div class="mascot-skin-name">' + skin.name + '</div>';
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            item.addEventListener('click', function (e) {
                //> 阻止事件继续向上冒泡
                e.stopPropagation();
                //> 调用函数「setSkin」并传入参数执行对应逻辑
                setSkin(skin.id);
                //> 调用函数「say」并传入参数执行对应逻辑
                say('换好新衣服啦喵~好看吗？');
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            //> 把子节点追加到当前元素内部末尾
            list.appendChild(item);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // ========== 最小化 ==========
    // =========================================================
    // 【函数】toggleMinimize
    // 功能：切换「minimize」相关逻辑（toggle minimize）
    // 参数：
    //   - container：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function toggleMinimize(container) {
        //> 给「isMinimized」赋值，更新其保存的状态
        isMinimized = !isMinimized;
        //> 切换样式类（有则移除、无则添加），可传第二参强制状态
        container.classList.toggle('minimized', isMinimized);
        //> 操作 localStorage（持久化本地存储），注意容量与解析异常
        localStorage.setItem('mascot_minimized', isMinimized);
        //> 声明变量「btn」（btn），用于保存对应数据，保存 DOM/窗口相关对象
        var btn = document.getElementById('mascot-min-btn');
        //> 条件判断：满足括号内条件时执行对应分支
        if (btn) btn.textContent = isMinimized ? '+' : '_';
        //> 条件判断：满足括号内条件时执行对应分支
        if (isMinimized) {
            // 最小化时点击展开
            // =========================================================
            // 【函数】onclick
            // 功能：处理「onclick」相关逻辑（mascot）
            // 参数：无
            // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
            // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
            // =========================================================
            container.onclick = function () {
                //> 条件判断：满足括号内条件时执行对应分支
                if (isMinimized) toggleMinimize(container);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            };
        //> 以上条件都不满足时执行的兜底分支
        } else {
            //> 给「container.onclick」赋值，更新其保存的状态
            container.onclick = null;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // ========== 拖动 ==========
    // =========================================================
    // 【函数】enableDrag
    // 功能：处理「enable drag」相关逻辑（mascot）
    // 参数：
    //   - container：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function enableDrag(container) {
        //> 声明变量「isDragging」（is dragging），用于保存对应数据
        var isDragging = false;
        //> 声明变量「startX」，稍后赋值使用
        var startX, startY, startLeft, startTop;
        //> 声明变量「hasMoved」（has moved），用于保存对应数据
        var hasMoved = false;

        //> 绑定「mousedown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        container.addEventListener('mousedown', function (e) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (e.target.closest('.mascot-toolbar') || e.target.closest('.mascot-skin-panel') || e.target.closest('.mascot-hitarea')) {
                //> 提前结束函数，无返回值
                return;
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 给「isDragging」赋值，更新其保存的状态
            isDragging = true;
            //> 给「hasMoved」赋值，更新其保存的状态
            hasMoved = false;
            //> 声明变量「rect」（rect），用于保存对应数据
            var rect = container.getBoundingClientRect();
            //> 给「startX」赋值，更新其保存的状态
            startX = e.clientX;
            //> 给「startY」赋值，更新其保存的状态
            startY = e.clientY;
            //> 给「startLeft」赋值，更新其保存的状态
            startLeft = rect.left;
            //> 给「startTop」赋值，更新其保存的状态
            startTop = rect.top;
            //> 给「container.style.right」赋值，更新其保存的状态
            container.style.right = 'auto';
            //> 给「container.style.bottom」赋值，更新其保存的状态
            container.style.bottom = 'auto';
            //> 阻止事件的默认行为（如表单提交、链接跳转）
            e.preventDefault();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });

        //> 绑定「mousemove」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('mousemove', function (e) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (!isDragging) return;
            //> 声明变量「dx」（dx），用于保存对应数据
            var dx = e.clientX - startX;
            //> 声明变量「dy」（dy），用于保存对应数据
            var dy = e.clientY - startY;
            //> 条件判断：满足括号内条件时执行对应分支
            if (Math.abs(dx) > 3 || Math.abs(dy) > 3) hasMoved = true;
            //> 声明变量「newLeft」（new left），用于保存对应数据
            var newLeft = Math.max(0, Math.min(window.innerWidth - container.offsetWidth, startLeft + dx));
            //> 声明变量「newTop」（new top），用于保存对应数据
            var newTop = Math.max(0, Math.min(window.innerHeight - container.offsetHeight, startTop + dy));
            //> 给「container.style.left」赋值，更新其保存的状态
            container.style.left = newLeft + 'px';
            //> 给「container.style.top」赋值，更新其保存的状态
            container.style.top = newTop + 'px';
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });

        //> 绑定「mouseup」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('mouseup', function () {
            //> 条件判断：满足括号内条件时执行对应分支
            if (isDragging && hasMoved) {
                //> 声明变量「rect」（rect），用于保存对应数据
                var rect = container.getBoundingClientRect();
                //> 操作 localStorage（持久化本地存储），注意容量与解析异常
                localStorage.setItem('mascot_position', JSON.stringify({
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    left: rect.left,
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    top: rect.top
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }));
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 给「isDragging」赋值，更新其保存的状态
            isDragging = false;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });

        // 触摸支持
        //> 绑定「touchstart」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        container.addEventListener('touchstart', function (e) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (e.target.closest('.mascot-toolbar') || e.target.closest('.mascot-skin-panel') || e.target.closest('.mascot-hitarea')) {
                //> 提前结束函数，无返回值
                return;
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 声明变量「touch」（touch），用于保存对应数据
            var touch = e.touches[0];
            //> 给「isDragging」赋值，更新其保存的状态
            isDragging = true;
            //> 给「hasMoved」赋值，更新其保存的状态
            hasMoved = false;
            //> 声明变量「rect」（rect），用于保存对应数据
            var rect = container.getBoundingClientRect();
            //> 给「startX」赋值，更新其保存的状态
            startX = touch.clientX;
            //> 给「startY」赋值，更新其保存的状态
            startY = touch.clientY;
            //> 给「startLeft」赋值，更新其保存的状态
            startLeft = rect.left;
            //> 给「startTop」赋值，更新其保存的状态
            startTop = rect.top;
            //> 给「container.style.right」赋值，更新其保存的状态
            container.style.right = 'auto';
            //> 给「container.style.bottom」赋值，更新其保存的状态
            container.style.bottom = 'auto';
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }, { passive: true });

        //> 绑定「touchmove」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        container.addEventListener('touchmove', function (e) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (!isDragging) return;
            //> 声明变量「touch」（touch），用于保存对应数据
            var touch = e.touches[0];
            //> 声明变量「dx」（dx），用于保存对应数据
            var dx = touch.clientX - startX;
            //> 声明变量「dy」（dy），用于保存对应数据
            var dy = touch.clientY - startY;
            //> 条件判断：满足括号内条件时执行对应分支
            if (Math.abs(dx) > 3 || Math.abs(dy) > 3) hasMoved = true;
            //> 声明变量「newLeft」（new left），用于保存对应数据
            var newLeft = Math.max(0, Math.min(window.innerWidth - container.offsetWidth, startLeft + dx));
            //> 声明变量「newTop」（new top），用于保存对应数据
            var newTop = Math.max(0, Math.min(window.innerHeight - container.offsetHeight, startTop + dy));
            //> 给「container.style.left」赋值，更新其保存的状态
            container.style.left = newLeft + 'px';
            //> 给「container.style.top」赋值，更新其保存的状态
            container.style.top = newTop + 'px';
            //> 阻止事件的默认行为（如表单提交、链接跳转）
            e.preventDefault();
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }, { passive: false });

        //> 绑定「touchend」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        container.addEventListener('touchend', function () {
            //> 条件判断：满足括号内条件时执行对应分支
            if (isDragging && hasMoved) {
                //> 声明变量「rect」（rect），用于保存对应数据
                var rect = container.getBoundingClientRect();
                //> 操作 localStorage（持久化本地存储），注意容量与解析异常
                localStorage.setItem('mascot_position', JSON.stringify({ left: rect.left, top: rect.top }));
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 给「isDragging」赋值，更新其保存的状态
            isDragging = false;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // ========== 随机说话 ==========
    // =========================================================
    // 【函数】startRandomTalk
    // 功能：处理「start random talk」相关逻辑（mascot）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function startRandomTalk() {
        //> 条件判断：满足括号内条件时执行对应分支
        if (randomTimer) clearInterval(randomTimer);
        //> 设置按间隔重复执行的定时器，记得 clearInterval 停止
        randomTimer = setInterval(function () {
            //> 条件判断：满足括号内条件时执行对应分支
            if (document.hidden) return;
            //> 条件判断：满足括号内条件时执行对应分支
            if (Math.random() < 0.4) {
                //> 调用函数「say」并传入参数执行对应逻辑
                say(randomPick(DIALOGUES.random));
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }, 25000);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // ========== 工具函数 ==========
    // =========================================================
    // 【函数】randomPick
    // 功能：处理「random pick」相关逻辑（mascot）
    // 参数：
    //   - arr：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function randomPick(arr) {
        //> 返回结果并结束当前函数
        return arr[Math.floor(Math.random() * arr.length)];
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // ========== 启动 ==========
    // =========================================================
    // 【函数】safeInit
    // 功能：处理「safe init」相关逻辑（mascot）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function safeInit() {
        //> 尝试执行可能出错的代码，出错则进入 catch
        try {
            //> 调用函数「init」并传入参数执行对应逻辑
            init();
            //> 给「window.__mascotLoaded」赋值，更新其保存的状态
            window.__mascotLoaded = true;
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        } catch (e) {
            //> 向控制台输出调试信息（生产环境应精简）
            console.error('看板娘初始化失败:', e);
            //> 给「window.__mascotError」赋值，更新其保存的状态
            window.__mascotError = e.message;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    //> 条件判断：满足括号内条件时执行对应分支
    if (document.readyState === 'loading') {
        //> 绑定「DOMContentLoaded」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('DOMContentLoaded', safeInit);
    //> 以上条件都不满足时执行的兜底分支
    } else {
        //> 调用函数「safeInit」并传入参数执行对应逻辑
        safeInit();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

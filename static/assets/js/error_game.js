/* ============================================================================
 * error_game.js —— 404 页「接樱花」小游戏（Bug11）
 * ----------------------------------------------------------------------------
 * 目的：用一个轻量小游戏化解用户落到错误页的挫败感，契合二次元萌系调性。
 *
 * 玩法：
 *   · 点击开始 → 显示画布，樱花花瓣从顶部随机位置落下；
 *   · 移动 / 键盘左右方向键控制底部的「小篮子」横移；
 *   · 接住花瓣得分，每 10 分下落速度加快，60 秒倒计时结束；
 *   · 漏接（花瓣落出画布）不扣分，直接移除。
 *
 * 重要约定（踩过的坑）：
 *   「得分：」这类中文前缀由模板从文案注册表渲染（#game-score 前置标签），
 *   JS 只把数字写进 #game-score-num，绝不在 JS 里硬拼中文，否则运营改文案
 *   会被覆盖。
 *
 * 依赖：Canvas 2D API、requestAnimationFrame（现代浏览器均支持）。
 * ----------------------------------------------------------------------------
 * 排错速查：
 *   · 中文「得分：」前缀由模板从文案表渲染，JS 只写 #game-score-num 数字，
 *     切勿在 JS 拼中文（运营改文案会被覆盖，已踩坑）；
 *   · 主循环用 requestAnimationFrame；碰撞判定用「高度区间 + 水平区间」的
 *     简化 AABB，篮子高约在 y=180、宽 40；
 *   · 花瓣数组倒序遍历以便安全 splice；漏接（y 超画布）直接移除不扣分；
 *   · 难度递增：每 10 分 fallSpeed += 0.5，新花瓣速度 = fallSpeed + 随机量；
 *   · 鼠标坐标需按 getBoundingClientRect 与画布宽高比换算，CSS 缩放也能对准；
 *   · 相关文件：404 模板（画布 / 按钮 / 文案）、error404.css。
 *   · 扩展提示：如需倒计时结束 / 最高分，可在 playing 切换处加计时与
 *     localStorage 记录，注意结束时停止 RAF 循环避免空转。
 * ============================================================================ */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';

    // 开始按钮、画布、分数容器
    //> 声明变量「btn」（btn），用于保存对应数据，保存 DOM/窗口相关对象
    var btn = document.getElementById('game-start-btn');
    //> 声明变量「canvas」（canvas），用于保存对应数据，保存 DOM/窗口相关对象
    var canvas = document.getElementById('game-canvas');
    //> 声明变量「scoreEl」（score el），用于保存对应数据，保存 DOM/窗口相关对象
    var scoreEl = document.getElementById('game-score');
    // 分数数字节点（优先专用节点，兜底整体分数容器）
    //> 声明变量「scoreNumEl」（score num el），用于保存对应数据，保存 DOM/窗口相关对象
    var scoreNumEl = document.getElementById('game-score-num') || scoreEl;
    // 画布 2D 上下文
    //> 声明变量「ctx」（ctx），用于保存对应数据
    var ctx = canvas.getContext('2d');

    // 游戏状态：是否进行中、得分、篮子横坐标、花瓣数组、下落速度
    //> 声明变量「playing」（playing），用于保存对应数据
    var playing = false;
    //> 声明变量「score」（score），用于保存对应数据
    var score = 0;
    //> 声明变量「playerX」（player x），用于保存对应数据
    var playerX = 140;
    //> 声明变量「petals」（petals），用于保存对应数据
    var petals = [];
    //> 声明变量「fallSpeed」（fall speed），用于保存对应数据
    var fallSpeed = 2;

    // 点击开始：显示画布与分数、隐藏开始按钮，重置状态并启动主循环
    //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    btn.addEventListener('click', function () {
        //> 给「canvas.style.display」赋值，更新其保存的状态
        canvas.style.display = 'block';
        //> 给「scoreEl.style.display」赋值，更新其保存的状态
        scoreEl.style.display = 'block';
        //> 给「btn.style.display」赋值，更新其保存的状态
        btn.style.display = 'none';
        //> 给「playing」赋值，更新其保存的状态
        playing = true;
        //> 给「score」赋值，更新其保存的状态
        score = 0;
        //> 给「petals」赋值，更新其保存的状态
        petals = [];
        //> 调用函数「gameLoop」并传入参数执行对应逻辑
        gameLoop();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    // 键盘控制：左右方向键移动篮子（限制在画布范围内）
    //> 绑定「keydown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    document.addEventListener('keydown', function (e) {
        //> 条件判断：满足括号内条件时执行对应分支
        if (!playing) return;
        //> 条件判断：满足括号内条件时执行对应分支
        if (e.key === 'ArrowLeft') {
            //> 给「playerX」赋值，更新其保存的状态
            playerX = Math.max(0, playerX - 30);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 条件判断：满足括号内条件时执行对应分支
        if (e.key === 'ArrowRight') {
            //> 给「playerX」赋值，更新其保存的状态
            playerX = Math.min(canvas.width - 40, playerX + 30);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    // 鼠标控制：鼠标在画布上的水平位置映射为篮子位置
    //> 绑定「mousemove」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    canvas.addEventListener('mousemove', function (e) {
        //> 条件判断：满足括号内条件时执行对应分支
        if (!playing) return;
        //> 声明变量「rect」（rect），用于保存对应数据
        var rect = canvas.getBoundingClientRect();
        // 把 CSS 像素坐标换算成画布内坐标，并减去篮子半宽使指针居中
        //> 给「playerX」赋值，更新其保存的状态
        playerX = (e.clientX - rect.left) * (canvas.width / rect.width) - 20;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /** 生成一片花瓣：随机水平位置、位于画布顶部外、随机半径与速度。 */
    // =========================================================
    // 【函数】spawnPetal
    // 功能：处理「spawn petal」相关逻辑（error_game）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function spawnPetal() {
        //> 操作「petals」的相关方法/属性
        petals.push({
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            x: Math.random() * (canvas.width - 20),
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            y: -10,
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            r: 6,
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            speed: fallSpeed + Math.random() * 1.5
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /** 游戏主循环：清屏 → 概率生成花瓣 → 绘制篮子 → 更新并绘制花瓣。 */
    // =========================================================
    // 【函数】gameLoop
    // 功能：处理「game loop」相关逻辑（error_game）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function gameLoop() {
        //> 条件判断：满足括号内条件时执行对应分支
        if (!playing) return;

        // 清空整块画布
        //> 操作「ctx」的相关方法/属性
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // 每帧约 3% 概率生成一片新花瓣
        //> 条件判断：满足括号内条件时执行对应分支
        if (Math.random() < 0.03) spawnPetal();

        // 绘制底部篮子（紫色圆角矩形）
        //> 给「ctx.fillStyle」赋值，更新其保存的状态
        ctx.fillStyle = '#a06cd5';
        //> 操作「ctx」的相关方法/属性
        ctx.beginPath();
        //> 操作「ctx」的相关方法/属性
        ctx.roundRect(playerX, 180, 40, 12, 6);
        //> 操作「ctx」的相关方法/属性
        ctx.fill();

        // 倒序遍历花瓣（倒序便于安全 splice 删除）
        //> 循环：按条件重复执行循环体
        for (var i = petals.length - 1; i >= 0; i--) {
            //> 声明变量「p」（p），用于保存对应数据
            var p = petals[i];
            // 花瓣下移
            //> 操作「p」的相关方法/属性
            p.y += p.speed;

            // 绘制花瓣（粉色圆形）
            //> 给「ctx.fillStyle」赋值，更新其保存的状态
            ctx.fillStyle = '#ff8fb1';
            //> 操作「ctx」的相关方法/属性
            ctx.beginPath();
            //> 操作「ctx」的相关方法/属性
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            //> 操作「ctx」的相关方法/属性
            ctx.fill();

            // 碰撞判定：花瓣进入篮子高度与水平区间
            //> 条件判断：满足括号内条件时执行对应分支
            if (p.y > 175 && p.y < 195
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                && p.x > playerX - 5 && p.x < playerX + 45) {
                // 得分 +1，更新数字，移除该花瓣
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                score++;
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                scoreNumEl.textContent = score;
                //> 操作「petals」的相关方法/属性
                petals.splice(i, 1);
                // 每 10 分加快下落速度，提升难度
                //> 条件判断：满足括号内条件时执行对应分支
                if (score % 10 === 0) fallSpeed += 0.5;
            //> 否则若满足该条件则进入此分支
            } else if (p.y > canvas.height) {
                // 落出画布：移除（漏接）
                //> 操作「petals」的相关方法/属性
                petals.splice(i, 1);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }

        // 请求下一帧，形成动画循环
        //> 在下一帧重绘前执行回调，是流畅动画的标准做法
        requestAnimationFrame(gameLoop);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

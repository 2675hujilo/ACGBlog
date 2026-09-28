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
(function () {
    'use strict';

    // 开始按钮、画布、分数容器
    var btn = document.getElementById('game-start-btn');
    var canvas = document.getElementById('game-canvas');
    var scoreEl = document.getElementById('game-score');
    // 分数数字节点（优先专用节点，兜底整体分数容器）
    var scoreNumEl = document.getElementById('game-score-num') || scoreEl;
    // 画布 2D 上下文
    var ctx = canvas.getContext('2d');

    // 游戏状态：是否进行中、得分、篮子横坐标、花瓣数组、下落速度
    var playing = false;
    var score = 0;
    var playerX = 140;
    var petals = [];
    var fallSpeed = 2;

    // 点击开始：显示画布与分数、隐藏开始按钮，重置状态并启动主循环
    btn.addEventListener('click', function () {
        canvas.style.display = 'block';
        scoreEl.style.display = 'block';
        btn.style.display = 'none';
        playing = true;
        score = 0;
        petals = [];
        gameLoop();
    });

    // 键盘控制：左右方向键移动篮子（限制在画布范围内）
    document.addEventListener('keydown', function (e) {
        if (!playing) return;
        if (e.key === 'ArrowLeft') {
            playerX = Math.max(0, playerX - 30);
        }
        if (e.key === 'ArrowRight') {
            playerX = Math.min(canvas.width - 40, playerX + 30);
        }
    });

    // 鼠标控制：鼠标在画布上的水平位置映射为篮子位置
    canvas.addEventListener('mousemove', function (e) {
        if (!playing) return;
        var rect = canvas.getBoundingClientRect();
        // 把 CSS 像素坐标换算成画布内坐标，并减去篮子半宽使指针居中
        playerX = (e.clientX - rect.left) * (canvas.width / rect.width) - 20;
    });

    /** 生成一片花瓣：随机水平位置、位于画布顶部外、随机半径与速度。 */
    function spawnPetal() {
        petals.push({
            x: Math.random() * (canvas.width - 20),
            y: -10,
            r: 6,
            speed: fallSpeed + Math.random() * 1.5
        });
    }

    /** 游戏主循环：清屏 → 概率生成花瓣 → 绘制篮子 → 更新并绘制花瓣。 */
    function gameLoop() {
        if (!playing) return;

        // 清空整块画布
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // 每帧约 3% 概率生成一片新花瓣
        if (Math.random() < 0.03) spawnPetal();

        // 绘制底部篮子（紫色圆角矩形）
        ctx.fillStyle = '#a06cd5';
        ctx.beginPath();
        ctx.roundRect(playerX, 180, 40, 12, 6);
        ctx.fill();

        // 倒序遍历花瓣（倒序便于安全 splice 删除）
        for (var i = petals.length - 1; i >= 0; i--) {
            var p = petals[i];
            // 花瓣下移
            p.y += p.speed;

            // 绘制花瓣（粉色圆形）
            ctx.fillStyle = '#ff8fb1';
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fill();

            // 碰撞判定：花瓣进入篮子高度与水平区间
            if (p.y > 175 && p.y < 195
                && p.x > playerX - 5 && p.x < playerX + 45) {
                // 得分 +1，更新数字，移除该花瓣
                score++;
                scoreNumEl.textContent = score;
                petals.splice(i, 1);
                // 每 10 分加快下落速度，提升难度
                if (score % 10 === 0) fallSpeed += 0.5;
            } else if (p.y > canvas.height) {
                // 落出画布：移除（漏接）
                petals.splice(i, 1);
            }
        }

        // 请求下一帧，形成动画循环
        requestAnimationFrame(gameLoop);
    }
})();

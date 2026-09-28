/**
 * 标签云词云布局脚本 v3.0（确定性布局，修复"标签云抖动"）
 * 特性：
 * 1. 固定种子的伪随机数（mulberry32），种子由「全部标签名 + 容器宽度档位」派生，
 *    同一组标签在同一宽度下【每次刷新布局完全一致】，不再随机抖动；
 * 2. 正态分布布局（中心密集，周围稀疏），大标签不强制在中心，可略微偏移；
 * 3. 智能重叠策略：标签少时不重叠，标签多时允许重叠；碰撞检测；
 * 4. 标签可拖动（鼠标/触摸）；
 * 5. 布局前隐藏容器、布局完成再淡入，且只布局一次，避免肉眼可见的二次重排。
 */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function() {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';

    /**
     * 字符串 -> 32 位无符号整数哈希（用于派生随机种子）
     * @param {string} str 原始字符串
     * @returns {number} 32 位无符号整数
     */
    // =========================================================
    // 【函数】hashString
    // 功能：处理「hash string」相关逻辑（tag-cloud-layout）
    // 参数：
    //   - str：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function hashString(str) {
        //> 声明块级变量「h」（h），用于保存对应数据
        let h = 1779033703 ^ str.length;
        //> 循环：按条件重复执行循环体
        for (let i = 0; i < str.length; i++) {
            //> 给「h」赋值，更新其保存的状态
            h = Math.imul(h ^ str.charCodeAt(i), 3432918353);
            //> 给「h」赋值，更新其保存的状态
            h = (h << 13) | (h >>> 19);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 返回结果并结束当前函数
        return (h ^ (h >>> 16)) >>> 0;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /**
     * mulberry32 确定性伪随机数发生器：相同种子产生完全相同的随机序列
     * @param {number} seed 32 位整数种子
     * @returns {function():number} 返回 [0,1) 随机数的函数
     */
    // =========================================================
    // 【函数】mulberry32
    // 功能：处理「mulberry32」相关逻辑（tag-cloud-layout）
    // 参数：
    //   - seed：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function mulberry32(seed) {
        //> 声明块级变量「a」（a），用于保存对应数据
        let a = seed >>> 0;
        //> 返回结果并结束当前函数
        return function() {
            //> 给「a」赋值，更新其保存的状态
            a = (a + 0x6D2B79F5) | 0;
            //> 声明块级变量「t」（t），用于保存对应数据
            let t = Math.imul(a ^ (a >>> 15), 1 | a);
            //> 给「t」赋值，更新其保存的状态
            t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
            //> 返回结果并结束当前函数
            return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        };
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /**
     * Box-Muller 变换生成正态分布随机数（使用传入的确定性 rng）
     * @param {number} mean 均值
     * @param {number} stdDev 标准差
     * @param {function():number} rng 确定性随机数函数
     * @returns {number} 正态分布随机数
     */
    // =========================================================
    // 【函数】normalRandom
    // 功能：处理「normal random」相关逻辑（tag-cloud-layout）
    // 参数：
    //   - mean：传入的参数（含义结合调用处与函数体）
    //   - stdDev：传入的参数（含义结合调用处与函数体）
    //   - rng：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function normalRandom(mean, stdDev, rng) {
        //> 声明常量「u1」（u1），用于保存对应数据
        const u1 = rng();
        //> 声明常量「u2」（u2），用于保存对应数据
        const u2 = rng();
        //> 声明常量「z」（z），用于保存对应数据
        const z = Math.sqrt(-2 * Math.log(Math.max(u1, 0.0001))) * Math.cos(2 * Math.PI * u2);
        //> 返回结果并结束当前函数
        return mean + z * stdDev;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /**
     * 检测两个矩形是否重叠
     */
    // =========================================================
    // 【函数】rectsOverlap
    // 功能：处理「rects overlap」相关逻辑（tag-cloud-layout）
    // 参数：
    //   - a：传入的参数（含义结合调用处与函数体）
    //   - b：传入的参数（含义结合调用处与函数体）
    //   - padding：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function rectsOverlap(a, b, padding) {
        //> 给「padding」赋值，更新其保存的状态
        padding = padding || 2;
        //> 返回结果并结束当前函数
        return !(a.x + a.width + padding < b.x ||
                 //> 操作「b」的相关方法/属性
                 b.x + b.width + padding < a.x ||
                 //> 操作「a」的相关方法/属性
                 a.y + a.height + padding < b.y ||
                 //> 操作「b」的相关方法/属性
                 b.y + b.height + padding < a.y);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /**
     * 使元素可拖动
     */
    // =========================================================
    // 【函数】makeDraggable
    // 功能：处理「make draggable」相关逻辑（tag-cloud-layout）
    // 参数：
    //   - el：传入的参数（含义结合调用处与函数体）
    //   - container：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function makeDraggable(el, container) {
        //> 声明块级变量「isDragging」（is dragging），用于保存对应数据
        let isDragging = false;
        //> 声明块级变量「startX」，稍后赋值使用
        let startX, startY, initialLeft, initialTop;
        //> 声明块级变量「hasMoved」（has moved），用于保存对应数据
        let hasMoved = false;

        // =========================================================
        // 【函数】onStart
        // 功能：处理……事件「start」相关逻辑（on start）
        // 参数：
        //   - e：传入的参数（含义结合调用处与函数体）
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function onStart(e) {
            //> 给「isDragging」赋值，更新其保存的状态
            isDragging = true;
            //> 给「hasMoved」赋值，更新其保存的状态
            hasMoved = false;
            //> 给「el._suppressClick」赋值，更新其保存的状态
            el._suppressClick = false;
            //> 声明常量「point」（point），用于保存对应数据
            const point = e.touches ? e.touches[0] : e;
            //> 给「startX」赋值，更新其保存的状态
            startX = point.clientX;
            //> 给「startY」赋值，更新其保存的状态
            startY = point.clientY;
            //> 给「initialLeft」赋值，更新其保存的状态
            initialLeft = parseFloat(el.style.left) || 0;
            //> 给「initialTop」赋值，更新其保存的状态
            initialTop = parseFloat(el.style.top) || 0;
            //> 给「el.style.zIndex」赋值，更新其保存的状态
            el.style.zIndex = '999';
            //> 给「el.style.cursor」赋值，更新其保存的状态
            el.style.cursor = 'grabbing';
            //> 给「el.style.transition」赋值，更新其保存的状态
            el.style.transition = 'none';
            //> 阻止事件的默认行为（如表单提交、链接跳转）
            e.preventDefault();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }

        // =========================================================
        // 【函数】onMove
        // 功能：处理……事件「move」相关逻辑（on move）
        // 参数：
        //   - e：传入的参数（含义结合调用处与函数体）
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function onMove(e) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (!isDragging) return;
            //> 声明常量「point」（point），用于保存对应数据
            const point = e.touches ? e.touches[0] : e;
            //> 声明常量「dx」（dx），用于保存对应数据
            const dx = point.clientX - startX;
            //> 声明常量「dy」（dy），用于保存对应数据
            const dy = point.clientY - startY;
            // 移动超过 4px 即判定为“拖动”而非“点击”
            //> 条件判断：满足括号内条件时执行对应分支
            if (Math.abs(dx) > 4 || Math.abs(dy) > 4) {
                //> 给「hasMoved」赋值，更新其保存的状态
                hasMoved = true;
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 声明块级变量「newLeft」（new left），用于保存对应数据
            let newLeft = initialLeft + dx;
            //> 声明块级变量「newTop」（new top），用于保存对应数据
            let newTop = initialTop + dy;
            // 边界限制
            //> 声明常量「maxLeft」（max left），用于保存对应数据
            const maxLeft = container.offsetWidth - el.offsetWidth - 4;
            //> 声明常量「maxTop」（max top），用于保存对应数据
            const maxTop = container.offsetHeight - el.offsetHeight - 4;
            //> 给「newLeft」赋值，更新其保存的状态
            newLeft = Math.max(4, Math.min(maxLeft, newLeft));
            //> 给「newTop」赋值，更新其保存的状态
            newTop = Math.max(4, Math.min(maxTop, newTop));
            //> 给「el.style.left」赋值，更新其保存的状态
            el.style.left = newLeft + 'px';
            //> 给「el.style.top」赋值，更新其保存的状态
            el.style.top = newTop + 'px';
            //> 阻止事件的默认行为（如表单提交、链接跳转）
            e.preventDefault();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }

        // =========================================================
        // 【函数】onEnd
        // 功能：处理……事件「end」相关逻辑（on end）
        // 参数：
        //   - e：传入的参数（含义结合调用处与函数体）
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function onEnd(e) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (!isDragging) return;
            //> 给「isDragging」赋值，更新其保存的状态
            isDragging = false;
            //> 给「el.style.zIndex」赋值，更新其保存的状态
            el.style.zIndex = '';
            //> 给「el.style.cursor」赋值，更新其保存的状态
            el.style.cursor = 'grab';
            //> 给「el.style.transition」赋值，更新其保存的状态
            el.style.transition = '';
            // 只要发生了拖动，就标记“拦截下一次 click”。链接跳转发生在 mouseup
            // 之后派发的 click 事件上，仅对 mouseup preventDefault 无法阻止导航。
            //> 条件判断：满足括号内条件时执行对应分支
            if (hasMoved) {
                //> 给「el._suppressClick」赋值，更新其保存的状态
                el._suppressClick = true;
                //> 阻止事件的默认行为（如表单提交、链接跳转）
                e.preventDefault();
                //> 阻止事件继续向上冒泡
                e.stopPropagation();
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }

        // 捕获阶段拦截“拖动后的那一次 click”，阻止默认跳转与冒泡，随后复位。
        //> 条件判断：满足括号内条件时执行对应分支
        if (!el._clickGuardBound) {
            //> 给「el._clickGuardBound」赋值，更新其保存的状态
            el._clickGuardBound = true;
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            el.addEventListener('click', function (ev) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (el._suppressClick) {
                    //> 阻止事件的默认行为（如表单提交、链接跳转）
                    ev.preventDefault();
                    //> 阻止事件继续向上冒泡
                    ev.stopPropagation();
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
                //> 给「el._suppressClick」赋值，更新其保存的状态
                el._suppressClick = false;
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }, true);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }

        //> 给「el.style.cursor」赋值，更新其保存的状态
        el.style.cursor = 'grab';
        // 防重复绑定：重排会再次调用 makeDraggable，加标志位避免堆叠监听
        //> 条件判断：满足括号内条件时执行对应分支
        if (el._dragBound) return;
        //> 给「el._dragBound」赋值，更新其保存的状态
        el._dragBound = true;
        //> 绑定「mousedown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        el.addEventListener('mousedown', onStart);
        //> 绑定「touchstart」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        el.addEventListener('touchstart', onStart, { passive: false });
        //> 绑定「mousemove」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('mousemove', onMove);
        //> 绑定「touchmove」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('touchmove', onMove, { passive: false });
        //> 绑定「mouseup」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('mouseup', onEnd);
        //> 绑定「touchend」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        document.addEventListener('touchend', onEnd);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /**
     * 词云布局主函数（确定性）。重复调用会按相同种子重建布局。
     */
    // =========================================================
    // 【函数】layoutTagCloud
    // 功能：处理「layout tag cloud」相关逻辑（tag-cloud-layout）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function layoutTagCloud() {
        //> 声明常量「container」（container），用于保存对应数据，保存 DOM/窗口相关对象
        const container = document.querySelector('.tags-cloud-wordcloud');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!container) return;

        //> 声明常量「tags」（tags），用于保存对应数据
        const tags = Array.from(container.querySelectorAll('.chip'));
        //> 条件判断：满足括号内条件时执行对应分支
        if (tags.length === 0) return;

        // 布局前先隐藏容器（不影响 offsetWidth/Height 测量），避免旧布局/贴边 flex 闪现
        //> 给「container.style.opacity」赋值，更新其保存的状态
        container.style.opacity = '0';

        // 按字体大小排序（大的在前，方便布局）
        //> 操作「tags」的相关方法/属性
        tags.sort(function(a, b) {
            //> 声明常量「sizeA」（size a），用于保存对应数据
            const sizeA = parseFloat(a.style.fontSize) || 1;
            //> 声明常量「sizeB」（size b），用于保存对应数据
            const sizeB = parseFloat(b.style.fontSize) || 1;
            //> 返回结果并结束当前函数
            return sizeB - sizeA;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });

        // 容器尺寸
        //> 声明常量「containerWidth」（container width），用于保存对应数据
        const containerWidth = container.offsetWidth;
        //> 声明常量「containerHeight」（container height），用于保存对应数据
        const containerHeight = Math.max(380, Math.min(520, containerWidth * 0.45));
        //> 给「container.style.height」赋值，更新其保存的状态
        container.style.height = containerHeight + 'px';
        //> 给「container.style.position」赋值，更新其保存的状态
        container.style.position = 'relative';
        //> 给「container.style.overflow」赋值，更新其保存的状态
        container.style.overflow = 'hidden';

        // 确定性随机种子：标签名集合 + 宽度档位（宽度按 50px 取整，缩放/拖动窗口时
        // 同一宽度档位内布局保持一致，跨档位才切换到另一个固定布局，绝不随机抖动）
        //> 声明常量「widthBucket」（width bucket），用于保存对应数据
        const widthBucket = Math.round(containerWidth / 50) * 50;
        //> 声明常量「seedText」（seed text），用于保存对应数据
        const seedText = tags.map(function(t) { return t.textContent; })
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            .sort().join('|') + '#' + widthBucket;
        //> 声明常量「rng」（rng），用于保存对应数据
        const rng = mulberry32(hashString(seedText));

        //> 声明常量「centerX」（center x），用于保存对应数据
        const centerX = containerWidth / 2;
        //> 声明常量「centerY」（center y），用于保存对应数据
        const centerY = containerHeight / 2;

        // 计算所有标签的总面积
        //> 声明块级变量「totalTagArea」（total tag area），用于保存对应数据
        let totalTagArea = 0;
        //> 遍历数组/类数组中的每一项并执行回调
        tags.forEach(function(tag) {
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            totalTagArea += tag.offsetWidth * tag.offsetHeight;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        //> 声明常量「containerArea」（container area），用于保存对应数据
        const containerArea = containerWidth * containerHeight;
        //> 声明常量「coverageRatio」（coverage ratio），用于保存对应数据
        const coverageRatio = totalTagArea / containerArea;

        // 智能重叠策略：覆盖率<40%时严格不重叠，>=40%时允许重叠
        //> 声明常量「allowOverlap」（allow overlap），用于保存对应数据
        const allowOverlap = coverageRatio >= 0.4;
        //> 声明常量「maxAttempts」（max attempts），用于保存对应数据
        const maxAttempts = allowOverlap ? 40 : 120;  // 居中：提高尝试，优先挤向中部
        //> 声明常量「collisionPadding」（collision padding），用于保存对应数据
        const collisionPadding = allowOverlap ? -8 : 4;

        //> 声明常量「placed」（placed），用于保存对应数据
        const placed = [];

        //> 遍历数组/类数组中的每一项并执行回调
        tags.forEach(function(tag, index) {
            //> 给「tag.style.position」赋值，更新其保存的状态
            tag.style.position = 'absolute';
            //> 给「tag.style.margin」赋值，更新其保存的状态
            tag.style.margin = '0';

            //> 声明常量「tagWidth」（tag width），用于保存对应数据
            const tagWidth = tag.offsetWidth;
            //> 声明常量「tagHeight」（tag height），用于保存对应数据
            const tagHeight = tag.offsetHeight;

            //> 声明块级变量「x」，稍后赋值使用
            let x, y;
            //> 声明块级变量「attempts」（attempts），用于保存对应数据
            let attempts = 0;

            // 居中：标准差收紧到容器尺寸的 1/6.2（原 1/3 偏散），向中部聚拢
            //> 声明常量「stdDevX」（std dev x），用于保存对应数据
            const stdDevX = containerWidth / 6.2;
            //> 声明常量「stdDevY」（std dev y），用于保存对应数据
            const stdDevY = containerHeight / 6.2;

            //> 当条件为真时反复执行循环体
            while (attempts < maxAttempts) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (index === 0) {
                    // 最大标签：中心附近确定性偏移（偏移范围为容器的 16%）
                    //> 给「x」赋值，更新其保存的状态
                    x = centerX + (rng() - 0.5) * containerWidth * 0.16;
                    //> 给「y」赋值，更新其保存的状态
                    y = centerY + (rng() - 0.5) * containerHeight * 0.16;
                //> 以上条件都不满足时执行的兜底分支
                } else {
                    // 正态分布确定性位置
                    //> 给「x」赋值，更新其保存的状态
                    x = normalRandom(centerX, stdDevX, rng);
                    //> 给「y」赋值，更新其保存的状态
                    y = normalRandom(centerY, stdDevY, rng);
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }

                // 越界位置不做贴边钳制（否则标签堆积在边缘），直接重试
                //> 条件判断：满足括号内条件时执行对应分支
                if (x < tagWidth / 2 + 6 || x > containerWidth - tagWidth / 2 - 6 ||
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    y < tagHeight / 2 + 6 || y > containerHeight - tagHeight / 2 - 6) {
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    attempts++;
                    //> 跳过本次循环剩余部分，进入下一次迭代
                    continue;
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }

                // 碰撞检测（允许重叠时前半程仍做宽松检测）
                //> 条件判断：满足括号内条件时执行对应分支
                if (!allowOverlap || attempts < maxAttempts / 2) {
                    //> 声明常量「tagRect」（tag rect），用于保存对应数据
                    const tagRect = {
                        //> 该行执行对应的脚本逻辑（结合上下文理解）
                        x: x - tagWidth / 2,
                        //> 该行执行对应的脚本逻辑（结合上下文理解）
                        y: y - tagHeight / 2,
                        //> 该行执行对应的脚本逻辑（结合上下文理解）
                        width: tagWidth,
                        //> 该行执行对应的脚本逻辑（结合上下文理解）
                        height: tagHeight
                    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                    };

                    //> 声明块级变量「overlap」（overlap），用于保存对应数据
                    let overlap = false;
                    //> 循环：按条件重复执行循环体
                    for (let i = 0; i < placed.length; i++) {
                        //> 条件判断：满足括号内条件时执行对应分支
                        if (rectsOverlap(tagRect, placed[i], collisionPadding)) {
                            //> 给「overlap」赋值，更新其保存的状态
                            overlap = true;
                            //> 跳出当前循环或 switch
                            break;
                        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                        }
                    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                    }

                    //> 条件判断：满足括号内条件时执行对应分支
                    if (!overlap) break;
                //> 以上条件都不满足时执行的兜底分支
                } else {
                    //> 跳出当前循环或 switch
                    break;
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }

                //> 该行执行对应的脚本逻辑（结合上下文理解）
                attempts++;
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }

            // 尝试耗尽则兜底放在中心附近小范围（允许重叠），避免甩到边角
            //> 条件判断：满足括号内条件时执行对应分支
            if (attempts >= maxAttempts) {
                //> 给「x」赋值，更新其保存的状态
                x = centerX + (rng() - 0.5) * tagWidth * 0.8;
                //> 给「y」赋值，更新其保存的状态
                y = centerY + (rng() - 0.5) * tagHeight * 0.8;
                //> 给「x」赋值，更新其保存的状态
                x = Math.max(tagWidth / 2 + 6, Math.min(containerWidth - tagWidth / 2 - 6, x));
                //> 给「y」赋值，更新其保存的状态
                y = Math.max(tagHeight / 2 + 6, Math.min(containerHeight - tagHeight / 2 - 6, y));
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }

            // 设置位置
            //> 给「tag.style.left」赋值，更新其保存的状态
            tag.style.left = (x - tagWidth / 2) + 'px';
            //> 给「tag.style.top」赋值，更新其保存的状态
            tag.style.top = (y - tagHeight / 2) + 'px';

            // 记录已放置位置
            //> 操作「placed」的相关方法/属性
            placed.push({
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                x: x - tagWidth / 2,
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                y: y - tagHeight / 2,
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                width: tagWidth,
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                height: tagHeight
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });

            // 使标签可拖动
            //> 调用函数「makeDraggable」并传入参数执行对应逻辑
            makeDraggable(tag, container);

            // 直接显示（容器统一淡入，不再逐个 scale，避免与容器淡入叠加）
            //> 给「tag.style.opacity」赋值，更新其保存的状态
            tag.style.opacity = '1';
            //> 给「tag.style.transform」赋值，更新其保存的状态
            tag.style.transform = 'none';
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });

        // 布局完成：强制一次重绘后淡入容器
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        void container.offsetWidth;
        //> 给「container.style.transition」赋值，更新其保存的状态
        container.style.transition = 'opacity 0.35s ease';
        //> 给「container.style.opacity」赋值，更新其保存的状态
        container.style.opacity = '1';
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // 响应式：窗口大小变化时重新布局（防抖）。同宽度档位下种子相同 → 布局不变。
    //> 声明块级变量「resizeTimer」，稍后赋值使用
    let resizeTimer;
    //> 绑定「resize」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    window.addEventListener('resize', function() {
        //> 清除对应的定时器，防止其继续执行
        clearTimeout(resizeTimer);
        //> 设置延时执行的定时器，返回可清除的定时器 id
        resizeTimer = setTimeout(layoutTagCloud, 300);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /**
     * 启动：轮询等待标签就绪，并尽量等网页字体就绪（保证尺寸准确），
     * 然后【只布局一次】。window load 仅作为兜底，不再无条件二次重排。
     */
    //> 声明块级变量「didLayout」（did layout），用于保存对应数据
    let didLayout = false;
    // =========================================================
    // 【函数】runOnce
    // 功能：处理「run once」相关逻辑（tag-cloud-layout）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function runOnce() {
        //> 条件判断：满足括号内条件时执行对应分支
        if (didLayout) return;
        //> 给「didLayout」赋值，更新其保存的状态
        didLayout = true;
        //> 调用函数「layoutTagCloud」并传入参数执行对应逻辑
        layoutTagCloud();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // =========================================================
    // 【函数】boot
    // 功能：处理「boot」相关逻辑（tag-cloud-layout）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function boot() {
        //> 声明常量「c」（c），用于保存对应数据，保存 DOM/窗口相关对象
        const c = document.querySelector('.tags-cloud-wordcloud');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!c || c.querySelectorAll('.chip').length === 0) {
            // 标签尚未就绪，120ms 后重试（设上限避免异常时无限轮询）
            //> 给「boot._tries」赋值，更新其保存的状态
            boot._tries = (boot._tries || 0) + 1;
            //> 条件判断：满足括号内条件时执行对应分支
            if (boot._tries < 40) setTimeout(boot, 120);
            //> 提前结束函数，无返回值
            return;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // 等字体加载完成再布局，尺寸更准、无需二次重排
        //> 条件判断：满足括号内条件时执行对应分支
        if (document.fonts && document.fonts.ready) {
            //> 操作「document.fonts.ready」的相关方法/属性
            document.fonts.ready.then(runOnce);
            // 兜底：字体 API 异常时 600ms 后照常布局
            //> 设置延时执行的定时器，返回可清除的定时器 id
            setTimeout(runOnce, 600);
        //> 以上条件都不满足时执行的兜底分支
        } else {
            //> 调用函数「runOnce」并传入参数执行对应逻辑
            runOnce();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
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
    // window load 仅兜底：若此前未布局才布局，不再无条件重排（消除肉眼可见抖动）
    //> 绑定「load」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    window.addEventListener('load', runOnce);

    // 暴露给全局，方便手动触发
    //> 给「window.layoutTagCloud」赋值，更新其保存的状态
    window.layoutTagCloud = layoutTagCloud;
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

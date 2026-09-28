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
(function() {
    'use strict';

    /**
     * 字符串 -> 32 位无符号整数哈希（用于派生随机种子）
     * @param {string} str 原始字符串
     * @returns {number} 32 位无符号整数
     */
    function hashString(str) {
        let h = 1779033703 ^ str.length;
        for (let i = 0; i < str.length; i++) {
            h = Math.imul(h ^ str.charCodeAt(i), 3432918353);
            h = (h << 13) | (h >>> 19);
        }
        return (h ^ (h >>> 16)) >>> 0;
    }

    /**
     * mulberry32 确定性伪随机数发生器：相同种子产生完全相同的随机序列
     * @param {number} seed 32 位整数种子
     * @returns {function():number} 返回 [0,1) 随机数的函数
     */
    function mulberry32(seed) {
        let a = seed >>> 0;
        return function() {
            a = (a + 0x6D2B79F5) | 0;
            let t = Math.imul(a ^ (a >>> 15), 1 | a);
            t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
            return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
        };
    }

    /**
     * Box-Muller 变换生成正态分布随机数（使用传入的确定性 rng）
     * @param {number} mean 均值
     * @param {number} stdDev 标准差
     * @param {function():number} rng 确定性随机数函数
     * @returns {number} 正态分布随机数
     */
    function normalRandom(mean, stdDev, rng) {
        const u1 = rng();
        const u2 = rng();
        const z = Math.sqrt(-2 * Math.log(Math.max(u1, 0.0001))) * Math.cos(2 * Math.PI * u2);
        return mean + z * stdDev;
    }

    /**
     * 检测两个矩形是否重叠
     */
    function rectsOverlap(a, b, padding) {
        padding = padding || 2;
        return !(a.x + a.width + padding < b.x ||
                 b.x + b.width + padding < a.x ||
                 a.y + a.height + padding < b.y ||
                 b.y + b.height + padding < a.y);
    }

    /**
     * 使元素可拖动
     */
    function makeDraggable(el, container) {
        let isDragging = false;
        let startX, startY, initialLeft, initialTop;
        let hasMoved = false;

        function onStart(e) {
            isDragging = true;
            hasMoved = false;
            el._suppressClick = false;
            const point = e.touches ? e.touches[0] : e;
            startX = point.clientX;
            startY = point.clientY;
            initialLeft = parseFloat(el.style.left) || 0;
            initialTop = parseFloat(el.style.top) || 0;
            el.style.zIndex = '999';
            el.style.cursor = 'grabbing';
            el.style.transition = 'none';
            e.preventDefault();
        }

        function onMove(e) {
            if (!isDragging) return;
            const point = e.touches ? e.touches[0] : e;
            const dx = point.clientX - startX;
            const dy = point.clientY - startY;
            // 移动超过 4px 即判定为“拖动”而非“点击”
            if (Math.abs(dx) > 4 || Math.abs(dy) > 4) {
                hasMoved = true;
            }
            let newLeft = initialLeft + dx;
            let newTop = initialTop + dy;
            // 边界限制
            const maxLeft = container.offsetWidth - el.offsetWidth - 4;
            const maxTop = container.offsetHeight - el.offsetHeight - 4;
            newLeft = Math.max(4, Math.min(maxLeft, newLeft));
            newTop = Math.max(4, Math.min(maxTop, newTop));
            el.style.left = newLeft + 'px';
            el.style.top = newTop + 'px';
            e.preventDefault();
        }

        function onEnd(e) {
            if (!isDragging) return;
            isDragging = false;
            el.style.zIndex = '';
            el.style.cursor = 'grab';
            el.style.transition = '';
            // 只要发生了拖动，就标记“拦截下一次 click”。链接跳转发生在 mouseup
            // 之后派发的 click 事件上，仅对 mouseup preventDefault 无法阻止导航。
            if (hasMoved) {
                el._suppressClick = true;
                e.preventDefault();
                e.stopPropagation();
            }
        }

        // 捕获阶段拦截“拖动后的那一次 click”，阻止默认跳转与冒泡，随后复位。
        if (!el._clickGuardBound) {
            el._clickGuardBound = true;
            el.addEventListener('click', function (ev) {
                if (el._suppressClick) {
                    ev.preventDefault();
                    ev.stopPropagation();
                }
                el._suppressClick = false;
            }, true);
        }

        el.style.cursor = 'grab';
        // 防重复绑定：重排会再次调用 makeDraggable，加标志位避免堆叠监听
        if (el._dragBound) return;
        el._dragBound = true;
        el.addEventListener('mousedown', onStart);
        el.addEventListener('touchstart', onStart, { passive: false });
        document.addEventListener('mousemove', onMove);
        document.addEventListener('touchmove', onMove, { passive: false });
        document.addEventListener('mouseup', onEnd);
        document.addEventListener('touchend', onEnd);
    }

    /**
     * 词云布局主函数（确定性）。重复调用会按相同种子重建布局。
     */
    function layoutTagCloud() {
        const container = document.querySelector('.tags-cloud-wordcloud');
        if (!container) return;

        const tags = Array.from(container.querySelectorAll('.chip'));
        if (tags.length === 0) return;

        // 布局前先隐藏容器（不影响 offsetWidth/Height 测量），避免旧布局/贴边 flex 闪现
        container.style.opacity = '0';

        // 按字体大小排序（大的在前，方便布局）
        tags.sort(function(a, b) {
            const sizeA = parseFloat(a.style.fontSize) || 1;
            const sizeB = parseFloat(b.style.fontSize) || 1;
            return sizeB - sizeA;
        });

        // 容器尺寸
        const containerWidth = container.offsetWidth;
        const containerHeight = Math.max(380, Math.min(520, containerWidth * 0.45));
        container.style.height = containerHeight + 'px';
        container.style.position = 'relative';
        container.style.overflow = 'hidden';

        // 确定性随机种子：标签名集合 + 宽度档位（宽度按 50px 取整，缩放/拖动窗口时
        // 同一宽度档位内布局保持一致，跨档位才切换到另一个固定布局，绝不随机抖动）
        const widthBucket = Math.round(containerWidth / 50) * 50;
        const seedText = tags.map(function(t) { return t.textContent; })
            .sort().join('|') + '#' + widthBucket;
        const rng = mulberry32(hashString(seedText));

        const centerX = containerWidth / 2;
        const centerY = containerHeight / 2;

        // 计算所有标签的总面积
        let totalTagArea = 0;
        tags.forEach(function(tag) {
            totalTagArea += tag.offsetWidth * tag.offsetHeight;
        });
        const containerArea = containerWidth * containerHeight;
        const coverageRatio = totalTagArea / containerArea;

        // 智能重叠策略：覆盖率<40%时严格不重叠，>=40%时允许重叠
        const allowOverlap = coverageRatio >= 0.4;
        const maxAttempts = allowOverlap ? 40 : 120;  // 居中：提高尝试，优先挤向中部
        const collisionPadding = allowOverlap ? -8 : 4;

        const placed = [];

        tags.forEach(function(tag, index) {
            tag.style.position = 'absolute';
            tag.style.margin = '0';

            const tagWidth = tag.offsetWidth;
            const tagHeight = tag.offsetHeight;

            let x, y;
            let attempts = 0;

            // 居中：标准差收紧到容器尺寸的 1/6.2（原 1/3 偏散），向中部聚拢
            const stdDevX = containerWidth / 6.2;
            const stdDevY = containerHeight / 6.2;

            while (attempts < maxAttempts) {
                if (index === 0) {
                    // 最大标签：中心附近确定性偏移（偏移范围为容器的 16%）
                    x = centerX + (rng() - 0.5) * containerWidth * 0.16;
                    y = centerY + (rng() - 0.5) * containerHeight * 0.16;
                } else {
                    // 正态分布确定性位置
                    x = normalRandom(centerX, stdDevX, rng);
                    y = normalRandom(centerY, stdDevY, rng);
                }

                // 越界位置不做贴边钳制（否则标签堆积在边缘），直接重试
                if (x < tagWidth / 2 + 6 || x > containerWidth - tagWidth / 2 - 6 ||
                    y < tagHeight / 2 + 6 || y > containerHeight - tagHeight / 2 - 6) {
                    attempts++;
                    continue;
                }

                // 碰撞检测（允许重叠时前半程仍做宽松检测）
                if (!allowOverlap || attempts < maxAttempts / 2) {
                    const tagRect = {
                        x: x - tagWidth / 2,
                        y: y - tagHeight / 2,
                        width: tagWidth,
                        height: tagHeight
                    };

                    let overlap = false;
                    for (let i = 0; i < placed.length; i++) {
                        if (rectsOverlap(tagRect, placed[i], collisionPadding)) {
                            overlap = true;
                            break;
                        }
                    }

                    if (!overlap) break;
                } else {
                    break;
                }

                attempts++;
            }

            // 尝试耗尽则兜底放在中心附近小范围（允许重叠），避免甩到边角
            if (attempts >= maxAttempts) {
                x = centerX + (rng() - 0.5) * tagWidth * 0.8;
                y = centerY + (rng() - 0.5) * tagHeight * 0.8;
                x = Math.max(tagWidth / 2 + 6, Math.min(containerWidth - tagWidth / 2 - 6, x));
                y = Math.max(tagHeight / 2 + 6, Math.min(containerHeight - tagHeight / 2 - 6, y));
            }

            // 设置位置
            tag.style.left = (x - tagWidth / 2) + 'px';
            tag.style.top = (y - tagHeight / 2) + 'px';

            // 记录已放置位置
            placed.push({
                x: x - tagWidth / 2,
                y: y - tagHeight / 2,
                width: tagWidth,
                height: tagHeight
            });

            // 使标签可拖动
            makeDraggable(tag, container);

            // 直接显示（容器统一淡入，不再逐个 scale，避免与容器淡入叠加）
            tag.style.opacity = '1';
            tag.style.transform = 'none';
        });

        // 布局完成：强制一次重绘后淡入容器
        void container.offsetWidth;
        container.style.transition = 'opacity 0.35s ease';
        container.style.opacity = '1';
    }

    // 响应式：窗口大小变化时重新布局（防抖）。同宽度档位下种子相同 → 布局不变。
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(layoutTagCloud, 300);
    });

    /**
     * 启动：轮询等待标签就绪，并尽量等网页字体就绪（保证尺寸准确），
     * 然后【只布局一次】。window load 仅作为兜底，不再无条件二次重排。
     */
    let didLayout = false;
    function runOnce() {
        if (didLayout) return;
        didLayout = true;
        layoutTagCloud();
    }
    function boot() {
        const c = document.querySelector('.tags-cloud-wordcloud');
        if (!c || c.querySelectorAll('.chip').length === 0) {
            // 标签尚未就绪，120ms 后重试（设上限避免异常时无限轮询）
            boot._tries = (boot._tries || 0) + 1;
            if (boot._tries < 40) setTimeout(boot, 120);
            return;
        }
        // 等字体加载完成再布局，尺寸更准、无需二次重排
        if (document.fonts && document.fonts.ready) {
            document.fonts.ready.then(runOnce);
            // 兜底：字体 API 异常时 600ms 后照常布局
            setTimeout(runOnce, 600);
        } else {
            runOnce();
        }
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
    // window load 仅兜底：若此前未布局才布局，不再无条件重排（消除肉眼可见抖动）
    window.addEventListener('load', runOnce);

    // 暴露给全局，方便手动触发
    window.layoutTagCloud = layoutTagCloud;
})();

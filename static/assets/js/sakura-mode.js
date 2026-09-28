/* ============================================================================
 * sakura-mode.js —— 樱花飘落氛围「三档开关」
 * ----------------------------------------------------------------------------
 * 三档循环：off（关闭）→ light（淡，5 朵）→ dense（浓，15 朵，更大更快）→ off。
 *
 * 花瓣来源：
 *   · 基础 5 个 .sakura-deco 花瓣在 base.html 中静态写死，淡 / 浓模式都用；
 *   · 浓模式额外动态追加 10 个 .sakura-dense 花瓣（随机位置、时长、延迟、缩放）。
 *
 * 持久化：当前档位存 localStorage('sakura_mode')，刷新后保持。
 * 按钮：#sakura-mode-toggle，图标与 title 随档位变化，提示当前档与下一档。
 * ----------------------------------------------------------------------------
 * 排错速查：
 *   · 三档 off/light/dense，循环顺序与按钮 title 文案需保持一致；
 *   · 基础 5 个 .sakura-deco 由 base.html 静态提供；浓模式动态花瓣缓存于
 *     densePetals，只创建一次、之后切显隐，避免反复增删节点；
 *   · 动态花瓣的位置 / 时长 / 延迟 / 缩放均随机，范围见 makePetal，调整浓淡
 *     改这些随机区间即可；
 *   · 存储键 'sakura_mode' 存档位字符串，非法值兜底 off；
 *   · 相关文件：base.html（基础花瓣与动画 keyframes）、effects.css 或
 *     effects.js（其它氛围效果）。
 *   · 注意：尊重 prefers-reduced-motion / 全站「关闭特效」：当用户关闭动效时
 *     应停止飘落（与 motion-off 偏好联动），避免违背减弱动效的意愿。
 * ============================================================================ */
(function () {
    'use strict';

    // 切换按钮；页面没有则退出
    var btn = document.getElementById('sakura-mode-toggle');
    if (!btn) return;

    // 三档标识（顺序即循环顺序）
    var STATES = ['off', 'light', 'dense'];
    // 各档按钮图标
    var LABELS = { off: '🌺', light: '🌸', dense: '🌺' };
    // 各档按钮悬停提示
    var TITLES = {
        off: '樱花模式：关闭（点击开启淡模式）',
        light: '樱花模式：淡（点击开启浓模式）',
        dense: '樱花模式：浓（点击关闭）'
    };

    // 基础花瓣（base.html 静态写死的 5 个）
    var basePetals = Array.prototype.slice.call(
        document.querySelectorAll('.sakura-deco')
    );
    // 浓模式动态追加的花瓣缓存（避免重复创建）
    var densePetals = [];

    /** 读取当前档位，非法 / 未设置时兜底为 off。 */
    function getState() {
        var s = 'off';
        try {
            s = localStorage.getItem('sakura_mode') || 'off';
        } catch (err) {}
        // 仅接受合法档位
        return STATES.indexOf(s) >= 0 ? s : 'off';
    }

    /** 保存当前档位（存储不可用时忽略）。 */
    function save(s) {
        try { localStorage.setItem('sakura_mode', s); } catch (err) {}
    }

    /** 创建一个动态花瓣（浓模式追加用），随机位置 / 时长 / 延迟 / 缩放。 */
    function makePetal() {
        var span = document.createElement('span');
        span.className = 'sakura-deco sakura-dense';
        // 随机水平起始位置（留出两侧边距）
        span.style.left = (Math.random() * 96) + '%';
        // 随机动画时长（8~14 秒，浓模式下落更快）
        span.style.animationDuration = (8 + Math.random() * 6) + 's';
        // 随机动画延迟，错开飘落节奏
        span.style.animationDelay = (Math.random() * 5) + 's';
        // 随机放大 1.2~2.0 倍，浓模式花瓣更大
        span.style.transform =
            'scale(' + (1.2 + Math.random() * 0.8) + ')';
        document.body.appendChild(span);
        return span;
    }

    /** 应用档位：显隐基础与动态花瓣、更新按钮外观。 */
    function apply(s) {
        // 非关闭档显示基础花瓣，关闭档隐藏
        var showBase = (s !== 'off');
        basePetals.forEach(function (p) {
            p.style.display = showBase ? '' : 'none';
        });

        if (s === 'dense') {
            // 浓模式：不足 10 个动态花瓣则补齐
            while (densePetals.length < 10) {
                densePetals.push(makePetal());
            }
            // 显示全部动态花瓣
            densePetals.forEach(function (p) {
                p.style.display = '';
            });
        } else {
            // 淡 / 关：隐藏动态花瓣（保留节点以便再切回）
            densePetals.forEach(function (p) {
                p.style.display = 'none';
            });
        }

        // 更新按钮图标与提示
        btn.textContent = LABELS[s];
        btn.title = TITLES[s];
    }

    // 点击按钮：循环到下一档并保存、应用
    btn.addEventListener('click', function () {
        var cur = getState();
        var next = STATES[(STATES.indexOf(cur) + 1) % STATES.length];
        save(next);
        apply(next);
    });

    // 页面加载时恢复档位
    apply(getState());
})();

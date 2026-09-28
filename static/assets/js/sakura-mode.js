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
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';

    // 切换按钮；页面没有则退出
    //> 声明变量「btn」（btn），用于保存对应数据，保存 DOM/窗口相关对象
    var btn = document.getElementById('sakura-mode-toggle');
    //> 条件判断：满足括号内条件时执行对应分支
    if (!btn) return;

    // 三档标识（顺序即循环顺序）
    //> 声明变量「STATES」（states），用于保存对应数据
    var STATES = ['off', 'light', 'dense'];
    // 各档按钮图标
    //> 声明变量「LABELS」（labels），用于保存对应数据
    var LABELS = { off: '🌺', light: '🌸', dense: '🌺' };
    // 各档按钮悬停提示
    //> 声明变量「TITLES」（titles），用于保存对应数据
    var TITLES = {
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        off: '樱花模式：关闭（点击开启淡模式）',
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        light: '樱花模式：淡（点击开启浓模式）',
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        dense: '樱花模式：浓（点击关闭）'
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    };

    // 基础花瓣（base.html 静态写死的 5 个）
    //> 声明变量「basePetals」（base petals），用于保存对应数据
    var basePetals = Array.prototype.slice.call(
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        document.querySelectorAll('.sakura-deco')
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    );
    // 浓模式动态追加的花瓣缓存（避免重复创建）
    //> 声明变量「densePetals」（dense petals），用于保存对应数据
    var densePetals = [];

    /** 读取当前档位，非法 / 未设置时兜底为 off。 */
    // =========================================================
    // 【函数】getState
    // 功能：获取「state」相关逻辑（get state）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function getState() {
        //> 声明变量「s」（s），用于保存对应数据，初始为字符串
        var s = 'off';
        //> 尝试执行可能出错的代码，出错则进入 catch
        try {
            //> 操作 localStorage（持久化本地存储），注意容量与解析异常
            s = localStorage.getItem('sakura_mode') || 'off';
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        } catch (err) {}
        // 仅接受合法档位
        //> 返回结果并结束当前函数
        return STATES.indexOf(s) >= 0 ? s : 'off';
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /** 保存当前档位（存储不可用时忽略）。 */
    // =========================================================
    // 【函数】save
    // 功能：保存相关逻辑（save）
    // 参数：
    //   - s：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function save(s) {
        //> 尝试执行可能出错的代码，出错则进入 catch
        try { localStorage.setItem('sakura_mode', s); } catch (err) {}
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /** 创建一个动态花瓣（浓模式追加用），随机位置 / 时长 / 延迟 / 缩放。 */
    // =========================================================
    // 【函数】makePetal
    // 功能：处理「make petal」相关逻辑（sakura-mode）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function makePetal() {
        //> 声明变量「span」（span），用于保存对应数据，保存 DOM/窗口相关对象
        var span = document.createElement('span');
        //> 给「span.className」赋值，更新其保存的状态
        span.className = 'sakura-deco sakura-dense';
        // 随机水平起始位置（留出两侧边距）
        //> 给「span.style.left」赋值，更新其保存的状态
        span.style.left = (Math.random() * 96) + '%';
        // 随机动画时长（8~14 秒，浓模式下落更快）
        //> 给「span.style.animationDuration」赋值，更新其保存的状态
        span.style.animationDuration = (8 + Math.random() * 6) + 's';
        // 随机动画延迟，错开飘落节奏
        //> 给「span.style.animationDelay」赋值，更新其保存的状态
        span.style.animationDelay = (Math.random() * 5) + 's';
        // 随机放大 1.2~2.0 倍，浓模式花瓣更大
        //> 给「span.style.transform」赋值，更新其保存的状态
        span.style.transform =
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            'scale(' + (1.2 + Math.random() * 0.8) + ')';
        //> 把子节点追加到当前元素内部末尾
        document.body.appendChild(span);
        //> 返回结果并结束当前函数
        return span;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /** 应用档位：显隐基础与动态花瓣、更新按钮外观。 */
    // =========================================================
    // 【函数】apply
    // 功能：应用相关逻辑（apply）
    // 参数：
    //   - s：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function apply(s) {
        // 非关闭档显示基础花瓣，关闭档隐藏
        //> 声明变量「showBase」（show base），用于保存对应数据，值为一个函数
        var showBase = (s !== 'off');
        //> 遍历数组/类数组中的每一项并执行回调
        basePetals.forEach(function (p) {
            //> 给「p.style.display」赋值，更新其保存的状态
            p.style.display = showBase ? '' : 'none';
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });

        //> 条件判断：满足括号内条件时执行对应分支
        if (s === 'dense') {
            // 浓模式：不足 10 个动态花瓣则补齐
            //> 当条件为真时反复执行循环体
            while (densePetals.length < 10) {
                //> 操作「densePetals」的相关方法/属性
                densePetals.push(makePetal());
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            // 显示全部动态花瓣
            //> 遍历数组/类数组中的每一项并执行回调
            densePetals.forEach(function (p) {
                //> 给「p.style.display」赋值，更新其保存的状态
                p.style.display = '';
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 以上条件都不满足时执行的兜底分支
        } else {
            // 淡 / 关：隐藏动态花瓣（保留节点以便再切回）
            //> 遍历数组/类数组中的每一项并执行回调
            densePetals.forEach(function (p) {
                //> 给「p.style.display」赋值，更新其保存的状态
                p.style.display = 'none';
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }

        // 更新按钮图标与提示
        //> 读写纯文本内容，不解析 HTML，可防 XSS
        btn.textContent = LABELS[s];
        //> 给「btn.title」赋值，更新其保存的状态
        btn.title = TITLES[s];
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // 点击按钮：循环到下一档并保存、应用
    //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    btn.addEventListener('click', function () {
        //> 声明变量「cur」（cur），用于保存对应数据
        var cur = getState();
        //> 声明变量「next」（next），用于保存对应数据
        var next = STATES[(STATES.indexOf(cur) + 1) % STATES.length];
        //> 调用函数「save」并传入参数执行对应逻辑
        save(next);
        //> 调用函数「apply」并传入参数执行对应逻辑
        apply(next);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    // 页面加载时恢复档位
    //> 调用函数「apply」并传入参数执行对应逻辑
    apply(getState());
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

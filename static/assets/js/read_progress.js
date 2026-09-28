/* ============================================================================
 * read_progress.js —— 阅读进度 / 位置记忆（第 3 轮新增）
 * ----------------------------------------------------------------------------
 * 适用页面：文章详情页（URL 形如 /article/<id>/）。
 *
 * 功能：
 *   1. 滚动时（500ms 节流）把当前滚动位置存到 localStorage 'read_progress_<id>'；
 *   2. 再次打开同一篇文章、且上次读到中部时，底部弹出「上次读到这里，要继续吗？」
 *      可一键平滑滚动恢复，或关闭提示；
 *   3. 滚动到全文约 80% 视为读完，清除该文章的位置记录。
 *
 * 依赖：无第三方库。
 * 注意：位置小于 200px 不保存（基本在开头，没必要提示）；提示条 8 秒自动消失。
 * ----------------------------------------------------------------------------
 * 排错速查：
 *   · 存储键 'read_progress_<id>' 与浏览历史 'reading_history' 不同，勿混淆；
 *   · 弹提示条件：saved > 200 且 saved < maxScroll()-100，避免「在开头」或
 *     「已到结尾」也弹无意义提示；
 *   · 保存采用 500ms 节流（timer 占位），到达 80% 置 done 并清除记录；
 *   · 提示条 8 秒自动移除；「继续」用 scrollTo smooth，旧浏览器降级可改瞬时；
 *   · 最大滚动距离取 documentElement 与 body 的 scrollHeight 较大者，兼容模式；
 *   · 相关文件：reading_history.js / reading_history_inline.js（历史列表）、
 *     详情页模板。
 *   · 注意：本数据仅存本地，换设备 / 清缓存后不保留，属预期。
 * ============================================================================ */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';

    // 从路径提取文章 id；非详情页直接退出
    //> 声明变量「match」（match），用于保存对应数据，保存 DOM/窗口相关对象
    var match = window.location.pathname.match(/\/article\/(\d+)/);
    //> 条件判断：满足括号内条件时执行对应分支
    if (!match) return;

    // 本文进度的 localStorage 键
    //> 声明变量「KEY」（key），用于保存对应数据，初始为字符串
    var KEY = 'read_progress_' + match[1];
    // 文档根元素，用于计算滚动尺寸
    //> 声明变量「doc」（doc），用于保存对应数据，保存 DOM/窗口相关对象
    var doc = document.documentElement;

    // 读取上次保存的位置（默认 0）
    //> 声明变量「saved」（saved），用于保存对应数据
    var saved = 0;
    //> 尝试执行可能出错的代码，出错则进入 catch
    try {
        //> 操作 localStorage（持久化本地存储），注意容量与解析异常
        saved = parseInt(localStorage.getItem(KEY) || '0', 10);
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    } catch (err) {}

    /** 计算页面最大可滚动距离（内容高 - 视口高）。 */
    // =========================================================
    // 【函数】maxScroll
    // 功能：处理「max scroll」相关逻辑（read_progress）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function maxScroll() {
        //> 返回结果并结束当前函数
        return Math.max(doc.scrollHeight, document.body.scrollHeight)
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            - window.innerHeight;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /** 读取当前垂直滚动位置（兼容多种写法）。 */
    // =========================================================
    // 【函数】curY
    // 功能：处理「cur y」相关逻辑（read_progress）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function curY() {
        //> 返回结果并结束当前函数
        return window.scrollY || doc.scrollTop || 0;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /** 弹出「是否继续阅读」提示条。 */
    // =========================================================
    // 【函数】showPrompt
    // 功能：显示「prompt」相关逻辑（show prompt）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function showPrompt() {
        // 创建提示条容器
        //> 声明变量「bar」（bar），用于保存对应数据，保存 DOM/窗口相关对象
        var bar = document.createElement('div');
        //> 给「bar.className」赋值，更新其保存的状态
        bar.className = 'read-progress-bar';
        // 结构：提示文案 + 两个按钮（继续 / 不了）
        //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
        bar.innerHTML =
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '<span>🐾 上次读到这里啦，要继续吗？</span>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '<span class="rp-actions">' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '<button class="rp-resume" type="button">继续</button>' +
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            '<button class="rp-dismiss" type="button">不了</button></span>';
        //> 把子节点追加到当前元素内部末尾
        document.body.appendChild(bar);

        // 「继续」：平滑滚动到上次位置并移除提示条
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        bar.querySelector('.rp-resume').addEventListener('click', function () {
            //> 程序化滚动窗口到指定位置
            window.scrollTo({ top: saved, behavior: 'smooth' });
            //> 把元素从 DOM 中移除
            bar.remove();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        // 「不了」：仅移除提示条
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        bar.querySelector('.rp-dismiss').addEventListener('click', function () {
            //> 把元素从 DOM 中移除
            bar.remove();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        // 8 秒后若还在页面上则自动移除
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
            //> 条件判断：满足括号内条件时执行对应分支
            if (bar.parentNode) bar.remove();
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }, 8000);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // 上次位置在 200px 以上、且未接近文末时，延迟 600ms 弹出提示
    //> 条件判断：满足括号内条件时执行对应分支
    if (saved > 200 && saved < maxScroll() - 100) {
        //> 设置延时执行的定时器，返回可清除的定时器 id
        setTimeout(showPrompt, 600);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // 滚动监听：节流保存 + 读完判定
    //> 声明变量「timer」（timer），用于保存对应数据
    var timer = null;     // 节流计时器
    //> 声明变量「done」（done），用于保存对应数据
    var done = false;     // 是否已判定读完
    //> 绑定「scroll」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    window.addEventListener('scroll', function () {
        //> 声明变量「y」（y），用于保存对应数据
        var y = curY();
        //> 声明变量「max」（max），用于保存对应数据
        var max = maxScroll();

        // 到达约 80% → 标记读完并清除记录
        //> 条件判断：满足括号内条件时执行对应分支
        if (!done && max > 0 && y / max >= 0.8) {
            //> 给「done」赋值，更新其保存的状态
            done = true;
            //> 尝试执行可能出错的代码，出错则进入 catch
            try { localStorage.removeItem(KEY); } catch (err) {}
            //> 提前结束函数，无返回值
            return;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }

        // 已有计时任务则跳过（节流）
        //> 条件判断：满足括号内条件时执行对应分支
        if (timer) return;
        // 500ms 后保存一次
        //> 设置延时执行的定时器，返回可清除的定时器 id
        timer = setTimeout(function () {
            //> 给「timer」赋值，更新其保存的状态
            timer = null;
            //> 尝试执行可能出错的代码，出错则进入 catch
            try {
                //> 条件判断：满足括号内条件时执行对应分支
                if (y > 200) {
                    // 位置有效则保存（四舍五入成整数）
                    //> 操作 localStorage（持久化本地存储），注意容量与解析异常
                    localStorage.setItem(KEY, String(Math.round(y)));
                //> 以上条件都不满足时执行的兜底分支
                } else {
                    // 太靠顶部则清除，避免下次弹提示
                    //> 操作 localStorage（持久化本地存储），注意容量与解析异常
                    localStorage.removeItem(KEY);
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            } catch (err) {}
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }, 500);
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    }, { passive: true });   // passive 提升滚动性能
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

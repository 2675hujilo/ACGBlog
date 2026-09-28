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
(function () {
    'use strict';

    // 从路径提取文章 id；非详情页直接退出
    var match = window.location.pathname.match(/\/article\/(\d+)/);
    if (!match) return;

    // 本文进度的 localStorage 键
    var KEY = 'read_progress_' + match[1];
    // 文档根元素，用于计算滚动尺寸
    var doc = document.documentElement;

    // 读取上次保存的位置（默认 0）
    var saved = 0;
    try {
        saved = parseInt(localStorage.getItem(KEY) || '0', 10);
    } catch (err) {}

    /** 计算页面最大可滚动距离（内容高 - 视口高）。 */
    function maxScroll() {
        return Math.max(doc.scrollHeight, document.body.scrollHeight)
            - window.innerHeight;
    }

    /** 读取当前垂直滚动位置（兼容多种写法）。 */
    function curY() {
        return window.scrollY || doc.scrollTop || 0;
    }

    /** 弹出「是否继续阅读」提示条。 */
    function showPrompt() {
        // 创建提示条容器
        var bar = document.createElement('div');
        bar.className = 'read-progress-bar';
        // 结构：提示文案 + 两个按钮（继续 / 不了）
        bar.innerHTML =
            '<span>🐾 上次读到这里啦，要继续吗？</span>' +
            '<span class="rp-actions">' +
            '<button class="rp-resume" type="button">继续</button>' +
            '<button class="rp-dismiss" type="button">不了</button></span>';
        document.body.appendChild(bar);

        // 「继续」：平滑滚动到上次位置并移除提示条
        bar.querySelector('.rp-resume').addEventListener('click', function () {
            window.scrollTo({ top: saved, behavior: 'smooth' });
            bar.remove();
        });
        // 「不了」：仅移除提示条
        bar.querySelector('.rp-dismiss').addEventListener('click', function () {
            bar.remove();
        });
        // 8 秒后若还在页面上则自动移除
        setTimeout(function () {
            if (bar.parentNode) bar.remove();
        }, 8000);
    }

    // 上次位置在 200px 以上、且未接近文末时，延迟 600ms 弹出提示
    if (saved > 200 && saved < maxScroll() - 100) {
        setTimeout(showPrompt, 600);
    }

    // 滚动监听：节流保存 + 读完判定
    var timer = null;     // 节流计时器
    var done = false;     // 是否已判定读完
    window.addEventListener('scroll', function () {
        var y = curY();
        var max = maxScroll();

        // 到达约 80% → 标记读完并清除记录
        if (!done && max > 0 && y / max >= 0.8) {
            done = true;
            try { localStorage.removeItem(KEY); } catch (err) {}
            return;
        }

        // 已有计时任务则跳过（节流）
        if (timer) return;
        // 500ms 后保存一次
        timer = setTimeout(function () {
            timer = null;
            try {
                if (y > 200) {
                    // 位置有效则保存（四舍五入成整数）
                    localStorage.setItem(KEY, String(Math.round(y)));
                } else {
                    // 太靠顶部则清除，避免下次弹提示
                    localStorage.removeItem(KEY);
                }
            } catch (err) {}
        }, 500);
    }, { passive: true });   // passive 提升滚动性能
})();

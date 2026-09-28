/* ============================================================================
 * announcement.js —— 可关闭的公告横幅（第 4 轮新增，cookie 记忆版）
 * ----------------------------------------------------------------------------
 * 与 base_announcement_banner.js 的区别：
 *   · base_announcement_banner.js 用 localStorage 记忆关闭状态；
 *   · 本文件用 cookie（notice_dismissed_{id}）记忆，服务端也能读到该 cookie，
 *     从而可在渲染阶段就决定是否输出横幅（两者按页面实际加载情况生效）。
 *
 * 功能：
 *   1. 点击 .announcement-close → 横幅先加 .closing 做淡出动画，再 .hidden；
 *   2. 写入 cookie notice_dismissed_{id}=1，max-age=86400（24 小时内不再显示）；
 *   3. 初始化时若该 cookie 已存在则直接隐藏。
 *
 * 依赖：无第三方库；横幅由模板渲染，本脚本只负责关闭与记忆。
 * ----------------------------------------------------------------------------
 * 排错速查：
 *   · cookie 名 'notice_dismissed_<id>'，max-age=86400 即 24 小时；改时长调整
 *     max-age 即可；
 *   · 关闭是「先 .closing 淡出(300ms) 再 .hidden」两段，删除动画需同步调整
 *     setTimeout 的 300ms，否则可能在动画未结束时就隐藏；
 *   · SameSite=Lax：正常同站导航会携带，跨站跳转不带，符合公告场景；
 *   · 与 base_announcement_banner.js 的差异是记忆载体（cookie vs localStorage），
 *     cookie 版服务端可读、可在渲染期决定是否输出；
 *   · 相关文件：后端公告模型 / 视图、site_messages（文案）。
 * ============================================================================ */
(function () {
    'use strict';

    /**
     * 读取指定名称的 cookie 值。
     * @param {string} name - cookie 名。
     * @returns {string|null} 解码后的 cookie 值，不存在返回 null。
     */
    function getCookie(name) {
        // 正则匹配「开头或空格后 name=值，直到分号或结尾」
        var match = document.cookie.match(
            new RegExp('(^| )' + name + '=([^;]*)(;|$)')
        );
        return match ? decodeURIComponent(match[2]) : null;
    }

    /** 初始化公告横幅的关闭逻辑。 */
    function init() {
        var banner = document.getElementById('announcementBanner');
        if (!banner) return;

        // 公告 id：拼出对应的 cookie 名；缺失时用 default 兜底
        var id = banner.getAttribute('data-notice-id') || 'default';
        var cookieName = 'notice_dismissed_' + id;

        // 已关闭过（cookie 为 1）→ 直接隐藏，不再播放动画
        if (getCookie(cookieName) === '1') {
            banner.classList.add('hidden');
            return;
        }

        var closeBtn = banner.querySelector('.announcement-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function () {
                // 先加 closing 触发 300ms 淡出动画
                banner.classList.add('closing');
                // 写 cookie：24 小时有效、path=/、SameSite=Lax 防跨站携带
                document.cookie =
                    cookieName + '=1; max-age=86400; path=/; SameSite=Lax';
                // 动画结束后再彻底隐藏，并移除 closing 类
                setTimeout(function () {
                    banner.classList.add('hidden');
                    banner.classList.remove('closing');
                }, 300);
            });
        }
    }

    // DOM 未就绪则等待，否则直接初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

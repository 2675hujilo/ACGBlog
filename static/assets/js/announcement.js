/**
 * announcement.js —— 可关闭公告横幅（第4轮新增）
 * 功能：
 *   1. 点击 .announcement-close 关闭 .announcement-banner，淡出隐藏；
 *   2. 写入 cookie notice_dismissed_{id}=1，max-age=86400（24小时）；
 *   3. 页面加载时若 cookie 已存在则直接隐藏横幅。
 * 依赖：无。横幅由模板渲染，本脚本只负责关闭逻辑。
 */
(function () {
    'use strict';

    function getCookie(name) {
        var m = document.cookie.match(new RegExp('(^| )' + name + '=([^;]*)(;|$)'));
        return m ? decodeURIComponent(m[2]) : null;
    }

    function init() {
        var banner = document.getElementById('announcementBanner');
        if (!banner) return;
        var id = banner.getAttribute('data-notice-id') || 'default';
        var cookieName = 'notice_dismissed_' + id;

        /* 已关闭过则直接隐藏 */
        if (getCookie(cookieName) === '1') {
            banner.classList.add('hidden');
            return;
        }

        var closeBtn = banner.querySelector('.announcement-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function () {
                banner.classList.add('closing');
                /* 24 小时内不再显示 */
                document.cookie = cookieName + '=1; max-age=86400; path=/; SameSite=Lax';
                setTimeout(function () {
                    banner.classList.add('hidden');
                    banner.classList.remove('closing');
                }, 300);
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

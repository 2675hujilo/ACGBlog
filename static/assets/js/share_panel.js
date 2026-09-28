/* Bug11 文件头注释
 * 分享面板脚本：微博/Twitter/复制链接等分享方式的弹窗与链接拼装。
 * 调用分享计数接口 F() 原子自增，并处理复制到剪贴板的降级。
 */
/**
 * share_panel.js —— 分享增强（第4轮新增）
 * 注入QQ空间分享按钮；任意分享动作 POST data-share-url 自增计数；toast提示。
 * 基础微博/Twitter/复制链接由 features.js 负责，本文件仅增强不冲突。
 */
(function () {
    'use strict';
    function getCookie(name) {
        var m = document.cookie.match(new RegExp('(^| )' + name + '=([^;]*)(;|$)'));
        return m ? decodeURIComponent(m[2]) : null;
    }
    function toast(msg) {
        var t = document.getElementById('global-toast');
        if (!t) {
            t = document.createElement('div');
            t.id = 'global-toast';
            document.body.appendChild(t);
        }
        t.textContent = msg;
        t.classList.add('show');
        clearTimeout(t._timer);
        t._timer = setTimeout(function () { t.classList.remove('show'); }, 1800);
    }
    function bump(apiUrl) {
        if (!apiUrl) return;
        fetch(apiUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken'), 'X-Requested-With': 'XMLHttpRequest' },
            credentials: 'same-origin'
        }).catch(function () {});
    }
    function init() {
        var group = document.getElementById('share-group');
        if (!group) return;
        var shareUrl = group.getAttribute('data-url') || location.href;
        var shareTitle = group.getAttribute('data-title') || document.title;
        var apiUrl = group.getAttribute('data-share-url') || group.getAttribute('data-api');
        if (!document.getElementById('share-qzone')) {
            var qz = document.createElement('button');
            qz.type = 'button';
            qz.id = 'share-qzone';
            qz.className = 'share-btn share-qzone';
            qz.textContent = 'QQ空间';
            qz.addEventListener('click', function (e) {
                e.preventDefault();
                bump(apiUrl);
                window.open('https://sns.qzone.qq.com/cgi-bin/qzshare/cgi_qzshare_onekey?url=' +
                    encodeURIComponent(shareUrl) + '&title=' + encodeURIComponent(shareTitle),
                    '_blank', 'noopener,width=640,height=520');
                toast('分享到QQ空间喵~ ✨');
            });
            group.appendChild(qz);
        }
        group.addEventListener('click', function (e) {
            var btn = e.target.closest('.share-btn');
            if (!btn || btn.id === 'share-qzone') return;
            bump(apiUrl);
        });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
})();

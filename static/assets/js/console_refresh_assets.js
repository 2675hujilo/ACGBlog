/* ============================================================================
 * console_refresh_assets.js —— 管理看板「一键刷新静态打包与缓存」（Bug14）
 * ----------------------------------------------------------------------------
 * 适用页面：管理员看板（存在按钮 #btn-refresh-assets，data-url 指向刷新接口）。
 *
 * 功能流程：
 *   1. 点击按钮先弹确认框（moeConfirm），说明会重新压缩 CSS/JS、写新版本号、
 *      清空服务端缓存；
 *   2. 确认后禁用按钮、改文案，POST 到 data-url（带 CSRF token）；
 *   3. 成功 → toast 提示并在约 750ms 后重载页面，让新资源生效；
 *      失败 → toast 报错并恢复按钮可点；
 *      网络异常 → 同样恢复按钮，避免按钮永久禁用。
 *
 * 依赖：moeToast / moeConfirm（萌系弹窗，缺失时降级直接执行）。
 * 安全：POST 必须带 X-CSRFToken，且接口要求管理员权限（后端校验）。
 * ----------------------------------------------------------------------------
 * 排错速查：
 *   · 接口为按钮 data-url 指向的看板刷新端点（POST，管理员 + CSRF），后端会
 *     重新压缩静态资源、写缓存版本号、清空服务端缓存；
 *   · 成功后约 750ms 才 reload，留出 toast 展示与后端写盘时间；
 *   · 失败 / 网络异常都要恢复 disabled 与原文案，否则按钮会永久不可点；
 *   · moeConfirm / moeToast 缺失时分别降级为「直接执行 / 无提示」，保证主流程；
 *   · 该操作会让全站静态缓存版本变化、所有用户下次加载取新资源，属预期；
 *   · 相关文件：refresh_assets 管理命令（同一套打包逻辑的命令行入口）、
 *     cache_bump（缓存版本号）、看板模板与后端刷新视图。
 *   · 注意：频繁执行会增加一次性 CPU（压缩）开销，建议发布静态资源后再使用。
 * ============================================================================ */
(function () {
    'use strict';

    var btn = document.getElementById('btn-refresh-assets');
    if (!btn) return;

    /** 从 cookie 读取 CSRF token（Django 约定名 csrftoken）。 */
    function csrf() {
        var m = document.cookie.match(/csrftoken=([^;]+)/);
        return m ? m[1] : '';
    }

    /** 执行刷新请求。 */
    function run() {
        // 禁用按钮并缓存原文案，便于失败时还原
        btn.disabled = true;
        var oldText = btn.textContent;
        btn.textContent = '♻️ 正在打包刷新…';

        if (window.moeToast) {
            moeToast('正在重新压缩静态资源并清空缓存，请稍候喵~', 'info');
        }

        // 发起 POST：带 CSRF 头、同源凭证（cookie）
        fetch(btn.dataset.url, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrf() },
            credentials: 'same-origin'
        })
        .then(function (resp) { return resp.json(); })
        .then(function (data) {
            if (data.ok) {
                // 成功：提示后重载页面
                if (window.moeToast) {
                    moeToast('静态资源已刷新，正在重载页面喵~', 'success');
                }
                setTimeout(function () { location.reload(); }, 750);
            } else {
                // 业务失败：报错并恢复按钮
                if (window.moeToast) {
                    moeToast('刷新失败：' + (data.error || ''), 'error');
                }
                btn.disabled = false;
                btn.textContent = oldText;
            }
        })
        .catch(function () {
            // 网络异常：提示并恢复按钮
            if (window.moeToast) moeToast('刷新请求失败喵~', 'error');
            btn.disabled = false;
            btn.textContent = oldText;
        });
    }

    // 点击：有确认框则先确认，没有则直接执行
    btn.addEventListener('click', function () {
        if (window.moeConfirm) {
            moeConfirm({
                title: '一键刷新静态与缓存？',
                message: '将重新压缩全部 CSS/JS、写入新版本号并清空服务端缓存，' +
                         '完成后页面自动重载喵~',
                confirmText: '开始刷新'
            }).then(function (ok) {
                if (ok) run();
            });
        } else {
            run();
        }
    });
})();

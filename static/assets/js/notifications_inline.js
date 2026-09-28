/* ============================================================================
 * notifications_inline.js —— 通知中心列表项点击与「全部已读」
 * ----------------------------------------------------------------------------
 * 适用页面：通知中心页（.notif-center-item 列表 + #notif-mark-all 按钮）。
 *
 * 行为：
 *   · 点击单条通知：
 *       - 若该通知未读（data-read='false'），先 POST 标记已读接口，
 *         成功或失败都继续跳转（失败也不能把用户卡住）；
 *       - 然后跳转到通知关联地址 data-url；没有地址则刷新页面。
 *   · 支持键盘：Enter / 空格触发同样动作（可访问性，列表项可能不是 <a>）。
 *   · 点击「全部已读」：POST read_all 接口后刷新页面。
 *
 * 安全：所有 POST 都带 X-CSRFToken 与同源凭证。
 * 注意：通知项的 id / url / read 状态由模板通过 data-* 注入。
 * ----------------------------------------------------------------------------
 * 排错速查：
 *   · 接口：POST /api/notifications/<id>/read/（单条）、POST
 *     /api/notifications/read_all/（全部），均需 CSRF + 登录；
 *   · 未读标记失败也继续跳转（.then(done).catch(done)）：不能因标记接口抖动
 *     把用户挡在目标内容之外，未读计数可在下次进入时再修正；
 *   · 列表项若非天然可聚焦元素，需有 tabindex 才能键盘触发，模板需配合；
 *   · data-id / data-url / data-read 全部由模板注入，前端不猜测；
 *   · 相关文件：通知模型与信号（谁产生通知）、通知中心模板、后端通知 API。
 *   · 注意：通知已读后图标 / 字重样式由模板按 data-read 渲染，标记后整页
 *     刷新或跳转再回来即可看到已读样式（本页不做局部样式切换）。
 * ============================================================================ */
(function () {
    'use strict';

    /** 从 cookie 读取 CSRF token。 */
    function csrfToken() {
        var m = document.cookie.match(/csrftoken=([^;]+)/);
        return m ? m[1] : '';
    }

    /**
     * 标记单条通知为已读（返回 fetch Promise）。
     * @param {string} id - 通知 id。
     */
    function markRead(id) {
        return fetch('/api/notifications/' + id + '/read/', {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken() },
            credentials: 'same-origin'
        });
    }

    // 为每条通知绑定点击 / 键盘事件
    document.querySelectorAll('.notif-center-item').forEach(function (item) {
        /** 激活一条通知：必要时标记已读，然后跳转 / 刷新。 */
        function activate() {
            var url = item.dataset.url;
            // 跳转目标：有 url 走 url，无 url 刷新当前页
            var done = function () {
                if (url) window.location.href = url;
                else window.location.reload();
            };

            if (item.dataset.read === 'false') {
                // 未读：先标记已读，无论成败都执行跳转
                markRead(item.dataset.id).then(done).catch(done);
            } else {
                // 已读：直接跳转
                done();
            }
        }

        // 鼠标点击
        item.addEventListener('click', activate);
        // 键盘可达：Enter 或空格触发
        item.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                activate();
            }
        });
    });

    // 「全部已读」按钮：调用批量接口后刷新
    var markAll = document.getElementById('notif-mark-all');
    if (markAll) {
        markAll.addEventListener('click', function () {
            fetch('/api/notifications/read_all/', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken() },
                credentials: 'same-origin'
            }).then(function () {
                window.location.reload();
            });
        });
    }
})();

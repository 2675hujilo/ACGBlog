/**
 * features/profile.js —— 个人中心（F类）
 *
 * 功能：
 *   F1 头像上传 Canvas 裁剪预览
 *   F2 资料编辑表单提交
 *   F3 密码修改（前端校验一致性）
 *   F4 阅读历史（读取 localStorage recent_views 渲染）
 *   F5 收藏夹管理（前端切换/删除）
 *   F6 点赞记录（由模板渲染，此处加交互）
 *   F7 评论管理（删除确认）
 *   F8 通知中心（已读标记/未读红点）
 *   F9 偏好设置开关（写入 preferences）
 *   F10 成就徽章展示（解锁态交互）
 *   F11 个人主页签名编辑
 *   F12 在线状态（头像呼吸点）
 *
 * 防御式：按 DOM 存在初始化，纯原生。
 */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';
    // =========================================================
    // 【函数】cookie
    // 功能：处理「cookie」相关逻辑（profile）
    // 参数：
    //   - n：传入的参数（含义结合调用处与函数体）
    // 返回：函数体内有 return，返回对应结果
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function cookie(n) { var m = document.cookie.match(new RegExp('(^| )' + n + '=([^;]*)(;|$)')); return m ? decodeURIComponent(m[2]) : null; }
    // =========================================================
    // 【函数】toast
    // 功能：处理「toast」相关逻辑（profile）
    // 参数：
    //   - msg：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function toast(msg) {
        //> 声明变量「t」（t），用于保存对应数据，保存 DOM/窗口相关对象
        var t = document.getElementById('global-toast');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!t) { t = document.createElement('div'); t.id = 'global-toast'; document.body.appendChild(t); }
        //> 读写纯文本内容，不解析 HTML，可防 XSS
        t.textContent = msg; t.classList.add('show');
        //> 移除元素的一个或多个样式类
        clearTimeout(t._t); t._t = setTimeout(function () { t.classList.remove('show'); }, 1600);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- F1 头像裁剪预览 ---------- */
    //> 声明变量「avatarInput」（avatar input），用于保存对应数据，保存 DOM/窗口相关对象
    var avatarInput = document.getElementById('id_avatar');
    //> 声明变量「cropWrap」（crop wrap），用于保存对应数据，保存 DOM/窗口相关对象
    var cropWrap = document.querySelector('.avatar-crop-wrap');
    //> 条件判断：满足括号内条件时执行对应分支
    if (avatarInput && cropWrap) {
        //> 绑定「change」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        avatarInput.addEventListener('change', function () {
            //> 声明变量「file」（file），用于保存对应数据
            var file = avatarInput.files[0]; if (!file) return;
            //> 声明变量「url」（url），用于保存对应数据
            var url = URL.createObjectURL(file);
            //> 声明变量「img」（img），用于保存对应数据
            var img = cropWrap.querySelector('img') || document.createElement('img');
            //> 把子节点追加到当前元素内部末尾
            img.src = url; cropWrap.appendChild(img);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- F3 密码一致性 ---------- */
    //> 声明变量「p1」（p1），用于保存对应数据，保存 DOM/窗口相关对象
    var p1 = document.getElementById('id_new_password'), p2 = document.getElementById('id_confirm_password');
    //> 条件判断：满足括号内条件时执行对应分支
    if (p1 && p2) {
        //> 绑定「input」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        p2.addEventListener('input', function () {
            //> 条件判断：满足括号内条件时执行对应分支
            if (p1.value !== p2.value) { p2.setCustomValidity('两次密码不一致'); }
            //> 以上条件都不满足时执行的兜底分支
            else { p2.setCustomValidity(''); }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- F4 阅读历史渲染 ---------- */
    //> 声明变量「histBox」（hist box），用于保存对应数据，保存 DOM/窗口相关对象
    var histBox = document.querySelector('.reading-history-list');
    //> 条件判断：满足括号内条件时执行对应分支
    if (histBox) {
        //> 尝试执行可能出错的代码，出错则进入 catch
        try {
            //> 声明变量「views」（views），用于保存对应数据
            var views = JSON.parse(localStorage.getItem('recent_views') || '[]').slice(0, 30);
            //> 遍历数组/类数组中的每一项并执行回调
            views.forEach(function (v) {
                //> 声明变量「div」（div），用于保存对应数据，保存 DOM/窗口相关对象
                var div = document.createElement('div');
                //> 给「div.className」赋值，更新其保存的状态
                div.className = 'profile-list-item';
                //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
                div.innerHTML = '<div><a href="' + v.url + '">' + v.title + '</a>' +
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    '<div class="pli-meta">' + (v.time || '') + '</div></div>';
                //> 把子节点追加到当前元素内部末尾
                histBox.appendChild(div);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        } catch (e) {}
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---------- F7 评论管理删除（Bug8：软删除 + 站内萌系确认） ---------- */
    //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
    document.querySelectorAll('[data-delete-comment-url]').forEach(function (btn) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        btn.addEventListener('click', function () {
            //> 调用函数「moeConfirm」并传入参数执行对应逻辑
            moeConfirm({ message: '确定要把这条评论收进回收站吗？', danger: true, confirmText: '收进回收站' })
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                .then(function (ok) {
                    //> 条件判断：满足括号内条件时执行对应分支
                    if (!ok) return;
                    //> 返回结果并结束当前函数
                    return fetch(btn.getAttribute('data-delete-comment-url'), {
                        //> 该行执行对应的脚本逻辑（结合上下文理解）
                        method: 'DELETE', headers: { 'X-CSRFToken': cookie('csrftoken') }, credentials: 'same-origin'
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    }).then(function () {
                        //> 声明变量「item」（item），用于保存对应数据
                        var item = btn.closest('.profile-list-item, .comment-item'); if (item) item.remove();
                        //> 条件判断：满足括号内条件时执行对应分支
                        if (window.moeToast) moeToast('已收进回收站~');
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    }).catch(function () { if (window.moeToast) moeToast('删除失败', 'error'); });
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- F8 通知中心：点击标记已读 ---------- */
    //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
    document.querySelectorAll('.notification-item').forEach(function (item) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        item.addEventListener('click', function () {
            //> 移除元素的一个或多个样式类
            item.classList.remove('unread');
            //> 声明变量「url」（url），用于保存对应数据
            var url = item.getAttribute('data-read-url');
            //> 条件判断：满足括号内条件时执行对应分支
            if (url) fetch(url, { headers: { 'X-CSRFToken': cookie('csrftoken') }, credentials: 'same-origin' }).catch(function () {});
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
    // 未读红点计数
    //> 声明变量「unread」（unread），用于保存对应数据，保存 DOM/窗口相关对象
    var unread = document.querySelectorAll('.notification-item.unread').length;
    //> 声明变量「badge」（badge），用于保存对应数据，保存 DOM/窗口相关对象
    var badge = document.querySelector('.notification-badge');
    //> 条件判断：满足括号内条件时执行对应分支
    if (badge) { if (unread > 0) badge.textContent = unread; else badge.style.display = 'none'; }

    /* ---------- F9 偏好设置开关同步 ---------- */
    //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
    document.querySelectorAll('.preference-row .switch input').forEach(function (sw) {
        //> 绑定「change」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        sw.addEventListener('change', function () {
            //> 声明变量「key」（key），用于保存对应数据
            var key = sw.getAttribute('data-pref');
            //> 声明变量「val」（val），用于保存对应数据
            var val = sw.checked;
            //> 条件判断：满足括号内条件时执行对应分支
            if (window.csrftoken) {
                //> 声明变量「body」（body），用于保存对应数据
                var body = {}; body[key] = val;
                //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
                fetch('/api/user/preferences/', {
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    method: 'PUT',
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.csrftoken },
                    //> 把 JS 数据序列化为 JSON 字符串
                    body: JSON.stringify(body), credentials: 'same-origin'
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                }).then(function () { toast('偏好已保存~'); }).catch(function () {});
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- F10 徽章点击提示 ---------- */
    //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
    document.querySelectorAll('.badge-cell.locked').forEach(function (b) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        b.addEventListener('click', function () { toast('继续加油解锁这个徽章吧~'); });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* ---------- F11 签名就地编辑 ---------- */
    //> 声明变量「sig」（sig），用于保存对应数据，保存 DOM/窗口相关对象
    var sig = document.querySelector('.profile-signature[data-editable]');
    //> 条件判断：满足括号内条件时执行对应分支
    if (sig) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        sig.addEventListener('click', function () {
            //> 声明变量「v」（v），用于保存对应数据
            var v = prompt('编辑你的签名：', sig.textContent);
            //> 条件判断：满足括号内条件时执行对应分支
            if (v !== null) {
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                sig.textContent = v;
                //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
                fetch('/api/user/preferences/', {
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    method: 'PUT',
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.csrftoken },
                    //> 把 JS 数据序列化为 JSON 字符串
                    body: JSON.stringify({ signature: v }), credentials: 'same-origin'
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                }).catch(function () {});
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

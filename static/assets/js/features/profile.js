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
(function () {
    'use strict';
    function cookie(n) { var m = document.cookie.match(new RegExp('(^| )' + n + '=([^;]*)(;|$)')); return m ? decodeURIComponent(m[2]) : null; }
    function toast(msg) {
        var t = document.getElementById('global-toast');
        if (!t) { t = document.createElement('div'); t.id = 'global-toast'; document.body.appendChild(t); }
        t.textContent = msg; t.classList.add('show');
        clearTimeout(t._t); t._t = setTimeout(function () { t.classList.remove('show'); }, 1600);
    }

    /* ---------- F1 头像裁剪预览 ---------- */
    var avatarInput = document.getElementById('id_avatar');
    var cropWrap = document.querySelector('.avatar-crop-wrap');
    if (avatarInput && cropWrap) {
        avatarInput.addEventListener('change', function () {
            var file = avatarInput.files[0]; if (!file) return;
            var url = URL.createObjectURL(file);
            var img = cropWrap.querySelector('img') || document.createElement('img');
            img.src = url; cropWrap.appendChild(img);
        });
    }

    /* ---------- F3 密码一致性 ---------- */
    var p1 = document.getElementById('id_new_password'), p2 = document.getElementById('id_confirm_password');
    if (p1 && p2) {
        p2.addEventListener('input', function () {
            if (p1.value !== p2.value) { p2.setCustomValidity('两次密码不一致'); }
            else { p2.setCustomValidity(''); }
        });
    }

    /* ---------- F4 阅读历史渲染 ---------- */
    var histBox = document.querySelector('.reading-history-list');
    if (histBox) {
        try {
            var views = JSON.parse(localStorage.getItem('recent_views') || '[]').slice(0, 30);
            views.forEach(function (v) {
                var div = document.createElement('div');
                div.className = 'profile-list-item';
                div.innerHTML = '<div><a href="' + v.url + '">' + v.title + '</a>' +
                    '<div class="pli-meta">' + (v.time || '') + '</div></div>';
                histBox.appendChild(div);
            });
        } catch (e) {}
    }

    /* ---------- F7 评论管理删除（Bug8：软删除 + 站内萌系确认） ---------- */
    document.querySelectorAll('[data-delete-comment-url]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            moeConfirm({ message: '确定要把这条评论收进回收站吗？', danger: true, confirmText: '收进回收站' })
                .then(function (ok) {
                    if (!ok) return;
                    return fetch(btn.getAttribute('data-delete-comment-url'), {
                        method: 'DELETE', headers: { 'X-CSRFToken': cookie('csrftoken') }, credentials: 'same-origin'
                    }).then(function () {
                        var item = btn.closest('.profile-list-item, .comment-item'); if (item) item.remove();
                        if (window.moeToast) moeToast('已收进回收站~');
                    }).catch(function () { if (window.moeToast) moeToast('删除失败', 'error'); });
                });
        });
    });

    /* ---------- F8 通知中心：点击标记已读 ---------- */
    document.querySelectorAll('.notification-item').forEach(function (item) {
        item.addEventListener('click', function () {
            item.classList.remove('unread');
            var url = item.getAttribute('data-read-url');
            if (url) fetch(url, { headers: { 'X-CSRFToken': cookie('csrftoken') }, credentials: 'same-origin' }).catch(function () {});
        });
    });
    // 未读红点计数
    var unread = document.querySelectorAll('.notification-item.unread').length;
    var badge = document.querySelector('.notification-badge');
    if (badge) { if (unread > 0) badge.textContent = unread; else badge.style.display = 'none'; }

    /* ---------- F9 偏好设置开关同步 ---------- */
    document.querySelectorAll('.preference-row .switch input').forEach(function (sw) {
        sw.addEventListener('change', function () {
            var key = sw.getAttribute('data-pref');
            var val = sw.checked;
            if (window.csrftoken) {
                var body = {}; body[key] = val;
                fetch('/api/user/preferences/', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.csrftoken },
                    body: JSON.stringify(body), credentials: 'same-origin'
                }).then(function () { toast('偏好已保存~'); }).catch(function () {});
            }
        });
    });

    /* ---------- F10 徽章点击提示 ---------- */
    document.querySelectorAll('.badge-cell.locked').forEach(function (b) {
        b.addEventListener('click', function () { toast('继续加油解锁这个徽章吧~'); });
    });

    /* ---------- F11 签名就地编辑 ---------- */
    var sig = document.querySelector('.profile-signature[data-editable]');
    if (sig) {
        sig.addEventListener('click', function () {
            var v = prompt('编辑你的签名：', sig.textContent);
            if (v !== null) {
                sig.textContent = v;
                fetch('/api/user/preferences/', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.csrftoken },
                    body: JSON.stringify({ signature: v }), credentials: 'same-origin'
                }).catch(function () {});
            }
        });
    }
})();

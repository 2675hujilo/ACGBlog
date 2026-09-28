/* Bug11 文件头注释
 * 点赞脚本：文章/评论点赞的轻量异步封装（session 防重、toggle 语义）。
 * 成功后局部更新计数与激活样式，失败给出提示。
 */
/**
 * like.js —— 文章点赞前端（第3轮新增）
 * 功能：
 *   1. 为 .like-btn 绑定点击，POST 到 /api/article/<id>/like/；
 *   2. 请求中按钮 loading（图标旋转），成功后点赞数+1、心形实心+粉色、弹跳动画；
 *   3. 失败 toast 提示；请求期间防重复点击。
 * 依赖：无。按钮由模板 Agent 添加 .like-btn 与 data-article-id。
 */
(function () {
    'use strict';

    function getCookie(name) {
        var m = document.cookie.match(new RegExp('(^| )' + name + '=([^;]*)'));
        return m ? decodeURIComponent(m[2]) : '';
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
        t._timer = setTimeout(function () { t.classList.remove('show'); }, 2000);
    }

    document.addEventListener('click', function (e) {
        var btn = e.target.closest('.like-btn');
        if (!btn || btn.disabled) return;
        var id = btn.getAttribute('data-article-id') ||
            (window.location.pathname.match(/\/article\/(\d+)/) || [])[1];
        if (!id) return;
        e.preventDefault();

        btn.disabled = true;
        btn.classList.add('loading');

        fetch('/api/article/' + id + '/like/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        }).then(function (r) { return r.json(); })
          .then(function (data) {
              btn.classList.remove('loading');
              if (data.success || data.liked) {
                  btn.classList.add('liked', 'pop');
                  var n = btn.querySelector('.n, .like-count');
                  if (n) n.textContent = (parseInt(n.textContent, 10) || 0) + (data.inc || 1);
                  setTimeout(function () { btn.classList.remove('pop'); }, 500);
              } else {
                  btn.disabled = false;
                  toast(data.error || '\u70b9\u8d5e\u6210\u529f\u5566~');
              }
          })
          .catch(function () {
              btn.classList.remove('loading');
              btn.disabled = false;
              toast('\u70b9\u8d5e\u5931\u8d25\u5566\uff0c\u8bf7\u7a0d\u540e\u518d\u8bd5');
          });
    });
})();

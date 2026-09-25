/* Bug14：看板一键刷新静态打包与缓存 */
(function () {
  var btn = document.getElementById('btn-refresh-assets');
  if (!btn) return;
  function csrf() { var m = document.cookie.match(/csrftoken=([^;]+)/); return m ? m[1] : ''; }
  function run() {
    btn.disabled = true; var old = btn.textContent; btn.textContent = '♻️ 正在打包刷新…';
    if (window.moeToast) moeToast('正在重新压缩静态资源并清空缓存，请稍候喵~', 'info');
    fetch(btn.dataset.url, {
      method: 'POST', headers: { 'X-CSRFToken': csrf() }, credentials: 'same-origin'
    }).then(function (r) { return r.json(); }).then(function (d) {
      if (d.ok) {
        if (window.moeToast) moeToast('静态资源已刷新，正在重载页面喵~', 'success');
        setTimeout(function () { location.reload(); }, 750);
      } else {
        if (window.moeToast) moeToast('刷新失败：' + (d.error || ''), 'error');
        btn.disabled = false; btn.textContent = old;
      }
    }).catch(function () {
      if (window.moeToast) moeToast('刷新请求失败喵~', 'error');
      btn.disabled = false; btn.textContent = old;
    });
  }
  btn.addEventListener('click', function () {
    if (window.moeConfirm) {
      moeConfirm({ title: '一键刷新静态与缓存？',
        message: '将重新压缩全部 CSS/JS、写入新版本号并清空服务端缓存，完成后页面自动重载喵~',
        confirmText: '开始刷新' }).then(function (ok) { if (ok) run(); });
    } else { run(); }
  });
})();
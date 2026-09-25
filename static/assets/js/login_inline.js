/* ============================================================
 * 免刷新登录（bug8）：
 *  - 拦截表单提交，用 fetch 以 redirect:'manual' 发送；
 *  - 成功（302 重定向）→ 直接跳转到 next 或首页；
 *  - 失败（200 重渲染）→ 显示红色内联提示并抖动，不整页刷新。
 * ============================================================ */
(function () {
    var form = document.getElementById('login-form');
    if (!form) return;
    var errBox = document.getElementById('login-error');
    var errText = document.getElementById('login-error-text');
    var btn = document.getElementById('login-submit');

    function showError(msg) {
        errText.textContent = msg || '用户名或密码不对呢~再试试喵';
        errBox.hidden = false;
        // 重新触发抖动动画
        errBox.style.animation = 'none';
        // 强制重排后恢复动画
        void errBox.offsetWidth;
        errBox.style.animation = '';
    }

    form.addEventListener('submit', function (e) {
        // 禁用 JS 或异常时回退普通提交
        e.preventDefault();
        var data = new FormData(form);
        btn.classList.add('is-loading');
        btn.textContent = '登录中喵…';
        // 表单 action 保留当前 URL（含 ?next=）
        fetch(form.action || window.location.href, {
            method: 'POST',
            body: data,
            redirect: 'manual',           // 成功的 302 以 opaqueredirect 返回
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        }).then(function (resp) {
            if (resp.type === 'opaqueredirect' || resp.status === 0) {
                // 登录成功：回跳 next 或首页
                var params = new URLSearchParams(window.location.search);
                window.location.href = params.get('next') || '/';
                return;
            }
            if (resp.ok) {
                // 登录失败：后端重渲染登录页，展示固定红色提示
                btn.classList.remove('is-loading');
                btn.textContent = '登录喵';
                showError();
            } else {
                throw new Error('bad status');
            }
        }).catch(function () {
            btn.classList.remove('is-loading');
            btn.textContent = '登录喵';
            showError('网络开小差了，稍后再试喵~');
        });
    });
})();
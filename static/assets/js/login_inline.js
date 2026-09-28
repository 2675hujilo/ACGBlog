/* ============================================================================
 * login_inline.js —— 免刷新登录（修复 Bug8）
 * ----------------------------------------------------------------------------
 * 适用页面：登录页（表单 #login-form，错误提示 #login-error / #login-error-text，
 *          提交按钮 #login-submit）。
 *
 * 核心思路（为何用 redirect:'manual'）：
 *   Django 的登录视图在「登录成功」时返回 302 重定向，「登录失败」时返回 200
 *   并重新渲染登录页。fetch 默认会自动跟随 302，我们就无法区分成功与失败。
 *   设置 redirect:'manual' 后：
 *     · 成功的 302 → 响应类型为 opaqueredirect、status 为 0；
 *     · 失败的 200 → 正常可读响应（resp.ok 为 true）。
 *
 * 行为：
 *   · 成功 → 读取 URL 上的 next 参数跳转，没有则回首页；
 *   · 失败 → 在 #login-error 内联显示红色提示并播放抖动动画，不整页刷新；
 *   · 网络异常 → 提示「网络开小差」。
 *
 * 降级：若 JS 被禁用，表单仍是普通提交，后端流程不受影响（渐进增强）。
 * ----------------------------------------------------------------------------
 * 排错速查：
 *   · 判定成功的关键是 redirect:'manual'：成功 302 → opaqueredirect/status 0，
 *     失败 200 → resp.ok；若改成默认跟随重定向将无法区分，务必保留；
 *   · 抖动动画重置依赖「设 none → 强制重排(void offsetWidth) → 恢复」三步，
 *     缺少重排步骤动画不会重播；
 *   · 本增强不改变后端登录视图契约，JS 禁用时表单普通提交依旧可用；
 *   · 登录成功后的 next 已由后端做白名单校验（防开放重定向），前端只读取；
 *   · 相关文件：auth_inline.js（注册 / 其它认证交互）、后端认证视图与信号
 *     （登录历史、在线状态、访问日志均由后端 / 中间件完成，不在本脚本）。
 * ============================================================================ */
(function () {
    'use strict';

    // 取登录表单；页面没有则直接退出
    var form = document.getElementById('login-form');
    if (!form) return;

    // 错误提示容器、文字节点、提交按钮
    var errBox = document.getElementById('login-error');
    var errText = document.getElementById('login-error-text');
    var btn = document.getElementById('login-submit');

    /**
     * 显示错误提示并重新触发抖动动画。
     * @param {string} msg - 提示文案（不传则用默认的「用户名或密码不对」）。
     */
    function showError(msg) {
        // 写入提示文字（textContent 防注入）
        errText.textContent = msg || '用户名或密码不对呢~再试试喵';
        // 显示错误框
        errBox.hidden = false;
        // 先清掉动画，使其可以重新触发
        errBox.style.animation = 'none';
        // 读取一次布局宽度，强制浏览器重排（重置动画的关键技巧）
        void errBox.offsetWidth;
        // 恢复动画（CSS 中定义的抖动）
        errBox.style.animation = '';
    }

    // 拦截表单提交
    form.addEventListener('submit', function (e) {
        // 阻止默认的整页提交，改由 fetch 发送
        e.preventDefault();

        // 收集表单数据（含用户名、密码、CSRF、next 等）
        var data = new FormData(form);

        // 按钮进入加载态，防止重复提交
        btn.classList.add('is-loading');
        btn.textContent = '登录中喵…';

        // 发送请求：manual 模式不自动跟随 302
        fetch(form.action || window.location.href, {
            method: 'POST',
            body: data,
            redirect: 'manual',
            // 标记为 AJAX：后端可据此返回不同内容
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(function (resp) {
            // 302 被 manual 拦截 → opaqueredirect / status 0 表示登录成功
            if (resp.type === 'opaqueredirect' || resp.status === 0) {
                // 解析查询串里的 next，决定登录后去向
                var params = new URLSearchParams(window.location.search);
                window.location.href = params.get('next') || '/';
                return;
            }
            if (resp.ok) {
                // 200：登录失败、后端重渲染了登录页，恢复按钮并显示固定提示
                btn.classList.remove('is-loading');
                btn.textContent = '登录喵';
                showError();
            } else {
                // 其它非预期状态码，抛错进入 catch
                throw new Error('bad status');
            }
        })
        .catch(function () {
            // 网络异常等：恢复按钮并提示
            btn.classList.remove('is-loading');
            btn.textContent = '登录喵';
            showError('网络开小差了，稍后再试喵~');
        });
    });
})();

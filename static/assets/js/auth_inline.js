/* ============================================================
 * 认证表单免刷新（bug8 / Bug8 工单修正）：
 *  - 登录页（#login-form）与注册页（#register-form）共用同一套逻辑；
 *  - 拦截提交，用 fetch 以 redirect:'manual' 发送；
 *  - 成功（302 重定向）→ 直接跳转到 next 或首页；
 *  - 失败（200 重渲染）→ 解析服务端返回的校验提示，渲染成
 *    「输入框下方的红色内联提示」，同时高亮出错字段并抖动，绝不整页刷新；
 *  - 无 JS / 网络异常时自动回退普通表单提交，功能不降级。
 * ============================================================ */
(function () {
    'use strict';

    /** 取 CSRF token：先读表单隐藏域，再回退 cookie。 */
    function readCsrf(form) {
        var input = form.querySelector('input[name=csrfmiddlewaretoken]');
        if (input && input.value) return input.value;
        var m = document.cookie.match(/csrftoken=([^;]+)/);
        return m ? m[1] : '';
    }

    /** 顶部汇总红条（认证表单通用）：不存在时按需创建，保证服务端模板可预置。 */
    function ensureAlert(box) {
        if (!box) return null;
        var alert = box.querySelector('.auth-form-alert');
        if (!alert) {
            alert = document.createElement('div');
            alert.className = 'auth-form-alert';
            alert.setAttribute('role', 'alert');
            var title = box.querySelector('.auth-title');
            if (title && title.nextSibling) {
                box.insertBefore(alert, title.nextSibling);
            } else {
                box.insertBefore(alert, box.firstChild);
            }
        }
        return alert;
    }

    /** 清空一次提交遗留的所有错误态。 */
    function clearErrors(form, box) {
        form.querySelectorAll('.is-invalid').forEach(function (el) {
            el.classList.remove('is-invalid');
            el.removeAttribute('aria-invalid');
        });
        // 复用模板预置的 #err-<field> 占位（清空 + 隐藏）；仅移除本脚本动态插入的节点
        form.querySelectorAll('.field-error').forEach(function (el) {
            el.textContent = '';
            el.hidden = true;
            if (el.dataset.jsInline === '1') el.remove();
        });
        var alert = box && box.querySelector('.auth-form-alert');
        if (alert) alert.remove();
    }

    /** 在指定输入框下方渲染红色内联错误；fieldKey 为空时渲染到顶部汇总。 */
    function showFieldError(form, box, fieldKey, message) {
        if (!fieldKey) {
            // ---- 整块提示：优先复用页面预置的错误容器（如 #login-error / .auth-form-alert），
            //      并把其中的专用文本节点 #login-error-text 一并更新，
            //      同时显式移除 hidden 属性 + 打上 .is-visible（双通道，避免样式/脚本冲突导致不可见）
            var container = (box && box.querySelector('.login-error'))
                || (box && box.querySelector('.auth-form-alert'))
                || ensureAlert(box);
            if (container) {
                var textNode = container.querySelector('#login-error-text');
                if (textNode) {
                    textNode.textContent = message;
                } else if (container.classList.contains('login-error')
                           || container.classList.contains('form-error-text')) {
                    // 没有专用文本节点时，保留装饰性 emoji，仅替换正文
                    container.textContent = message;
                    container.insertAdjacentHTML('afterbegin', '<span aria-hidden="true">😿</span>');
                } else {
                    container.textContent = message;
                }
                container.hidden = false;
                container.removeAttribute('hidden');
                container.classList.add('is-visible');
                container.style.display = '';
            }
            return;
        }
        var input = form.querySelector('[name="' + fieldKey + '"]');
        if (!input) {
            showFieldError(form, box, '', message);   // 无对应输入框时降级为整块提示
            return;
        }
        input.classList.add('is-invalid');
        input.setAttribute('aria-invalid', 'true');
        var errId = 'err-' + fieldKey;
        var node = form.querySelector('#' + errId);
        if (!node) {
            node = document.createElement('span');
            node.id = errId;
            node.className = 'field-error form-error-text';
            node.setAttribute('role', 'alert');
            node.dataset.jsInline = '1';
            input.insertAdjacentElement('afterend', node);
        }
        node.textContent = message;
        node.hidden = false;
        node.removeAttribute('hidden');
        node.classList.add('is-visible');
    }

    /** 解析服务端重渲染页面里的校验提示（.field-error / .auth-form-alert / flash）。 */
    function parseServerErrors(html) {
        var doc = new DOMParser().parseFromString(html, 'text/html');
        var out = [];
        // 1) 认证卡片内的整块错误提示：优先读专用文本节点 #login-error-text，
        //    避免把装饰 emoji（😿）当成提示内容一起带出来
        doc.querySelectorAll('.login-error, .auth-form-alert').forEach(function (el) {
            var textNode = el.querySelector('#login-error-text');
            var text = ((textNode ? textNode.textContent : el.textContent) || '');
            // 去掉开头的装饰性 emoji / 符号与空白
            text = text.replace(/^[\s\u2600-\u27bf\ud83c-\udbff\udc00-\udfff\u2000-\u2bff]+/, '').trim();
            if (text) out.push({ field: '', message: text });
        });
        // 2) 字段级错误
        doc.querySelectorAll('.field-error').forEach(function (el) {
            var text = (el.textContent || '').trim();
            if (!text) return;
            var field = '';
            var described = el.getAttribute('aria-describedby') || '';
            var target = el.previousElementSibling;
            if (el.id) {
                var forName = doc.querySelector('[aria-describedby~="' + el.id + '"]');
                if (forName && forName.name) field = forName.name;
                // 后端预置的占位 id 形如 err-<field>，可直接解析出字段名
                if (!field && el.id.indexOf('err-') === 0) field = el.id.slice(4);
            }
            if (!field && target && target.name) field = target.name;
            if (!field && described) field = described;
            out.push({ field: field, message: text });
        });
        // 3) 兜底：模板未渲染内联错误时，使用顶部 flash 消息
        if (!out.length) {
            doc.querySelectorAll('.flash').forEach(function (el) {
                var text = (el.textContent || '').trim();
                if (text) out.push({ field: '', message: text });
            });
        }
        return out;
    }

    /** 把服务端返回的错误列表渲染到表单上，并聚焦首个出错字段。 */
    function renderErrors(form, box, errors) {
        clearErrors(form, box);
        if (!errors.length) {
            errors = [{ field: '', message: '提交失败，请检查填写内容后重试喵~' }];
        }
        errors.forEach(function (e) { showFieldError(form, box, e.field, e.message); });
        var firstBad = form.querySelector('.is-invalid');
        if (firstBad) {
            firstBad.focus();
            var card = box || form;
            card.classList.remove('reg-shake');
            void card.offsetWidth;   // 强制重排后重放动画
            card.classList.add('reg-shake');
        }
    }

    /** 给单个表单绑定免刷新提交。 */
    function bindForm(form, opts) {
        var box = form.closest('.auth-card') || form.parentElement;
        var btn = form.querySelector('button[type="submit"]');
        var idleText = btn ? btn.textContent : '';
        var busyText = opts.busyText || '提交中喵…';

        function resetBtn() {
            if (!btn) return;
            btn.classList.remove('is-loading');
            btn.disabled = false;
            btn.textContent = idleText;
        }

        // 原生校验失败时也给出内联红字提示（而不是只靠浏览器气泡）
        form.addEventListener('invalid', function (ev) {
            var el = ev.target;
            if (!el.name) return;
            var msg = el.validationMessage || '这一项填写不正确喵~';
            showFieldError(form, box, el.name, msg);
        }, true);
        form.addEventListener('input', function (ev) {
            var el = ev.target;
            if (!el.name) return;
            el.classList.remove('is-invalid');
            el.removeAttribute('aria-invalid');
            var node = form.querySelector('#err-' + el.name);
            if (node) {
                if (node.dataset.jsInline === '1') node.remove();
                else { node.textContent = ''; node.hidden = true; }
            }
        });

        form.addEventListener('submit', function (e) {
            // 原生校验不通过：交给浏览器 + invalid 事件渲染内联提示
            if (typeof form.checkValidity === 'function' && !form.checkValidity()) {
                e.preventDefault();
                form.reportValidity();
                return;
            }
            e.preventDefault();
            if (btn) {
                btn.classList.add('is-loading');
                btn.disabled = true;
                btn.textContent = busyText;
            }
            var headers = { 'X-Requested-With': 'XMLHttpRequest' };
            var csrf = readCsrf(form);
            if (csrf) headers['X-CSRFToken'] = csrf;

            fetch(form.action || window.location.href, {
                method: 'POST',
                body: new FormData(form),
                redirect: 'manual',            // 成功的 302 以 opaqueredirect 返回
                credentials: 'same-origin',
                headers: headers
            }).then(function (resp) {
                if (resp.type === 'opaqueredirect' || resp.status === 0) {
                    // 成功：跳转 next 或首页
                    var params = new URLSearchParams(window.location.search);
                    window.location.href = params.get('next') || opts.successUrl || '/';
                    return null;
                }
                if (resp.ok) return resp.text();
                throw new Error('bad status ' + resp.status);
            }).then(function (html) {
                if (html === null) return;      // 已跳转
                resetBtn();
                renderErrors(form, box, parseServerErrors(html));
            }).catch(function () {
                resetBtn();
                renderErrors(form, box, [{ field: '', message: '网络开小差了，稍后再试喵~' }]);
            });
        });
    }

    var loginForm = document.getElementById('login-form');
    if (loginForm) bindForm(loginForm, { busyText: '登录中喵…' });

    var registerForm = document.getElementById('register-form');
    if (registerForm) bindForm(registerForm, { busyText: '注册中喵…' });

    /* ---- 注册页密码一致性实时提示：两次不一致时即时红字，无需等提交 ---- */
    if (registerForm) {
        var pw1 = registerForm.querySelector('[name=password]');
        var pw2 = registerForm.querySelector('[name=password2]');
        var box = registerForm.closest('.auth-card') || registerForm.parentElement;
        function checkMatch() {
            if (!pw1 || !pw2 || !pw2.value) return;
            if (pw1.value === pw2.value) {
                pw2.classList.remove('is-invalid');
                var n = registerForm.querySelector('#err-password2');
                if (n) {
                    if (n.dataset.jsInline === '1') n.remove();
                    else { n.textContent = ''; n.hidden = true; }
                }
                return;
            }
            showFieldError(registerForm, box, 'password2', '两次密码不一样呢~再确认一下喵🔍');
        }
        if (pw2) pw2.addEventListener('input', checkMatch);
        if (pw1) pw1.addEventListener('input', checkMatch);
    }

    /* ---- 注册页：把服务端整页重渲染留下的 flash 错误转成内联红字（兜底） ---- */
    if (registerForm) {
        var box2 = registerForm.closest('.auth-card') || registerForm.parentElement;
        var flashes = document.querySelectorAll('.flash-error, .flash-danger');
        if (flashes.length) {
            var errs = [];
            flashes.forEach(function (f) {
                var text = (f.textContent || '').trim();
                if (text) errs.push({ field: '', message: text });
            });
            renderErrors(registerForm, box2, errs);
        }
    }
})();

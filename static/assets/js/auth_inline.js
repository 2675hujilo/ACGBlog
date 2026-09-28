/* ============================================================
 * 认证表单免刷新（bug8 / Bug8 工单修正）：
 *  - 登录页（#login-form）与注册页（#register-form）共用同一套逻辑；
 *  - 拦截提交，用 fetch 以 redirect:'manual' 发送；
 *  - 成功（302 重定向）→ 直接跳转到 next 或首页；
 *  - 失败（200 重渲染）→ 解析服务端返回的校验提示，渲染成
 *    「输入框下方的红色内联提示」，同时高亮出错字段并抖动，绝不整页刷新；
 *  - 无 JS / 网络异常时自动回退普通表单提交，功能不降级。
 * ============================================================ */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';

    /** 取 CSRF token：先读表单隐藏域，再回退 cookie。 */
    // =========================================================
    // 【函数】readCsrf
    // 功能：处理「read csrf」相关逻辑（auth_inline）
    // 参数：
    //   - form：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function readCsrf(form) {
        //> 声明变量「input」（input），用于保存对应数据
        var input = form.querySelector('input[name=csrfmiddlewaretoken]');
        //> 条件判断：满足括号内条件时执行对应分支
        if (input && input.value) return input.value;
        //> 声明变量「m」（m），用于保存对应数据，保存 DOM/窗口相关对象
        var m = document.cookie.match(/csrftoken=([^;]+)/);
        //> 返回结果并结束当前函数
        return m ? m[1] : '';
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /** 顶部汇总红条（认证表单通用）：不存在时按需创建，保证服务端模板可预置。 */
    // =========================================================
    // 【函数】ensureAlert
    // 功能：处理「ensure alert」相关逻辑（auth_inline）
    // 参数：
    //   - box：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function ensureAlert(box) {
        //> 条件判断：满足括号内条件时执行对应分支
        if (!box) return null;
        //> 声明变量「alert」（alert），用于保存对应数据
        var alert = box.querySelector('.auth-form-alert');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!alert) {
            //> 创建新的 DOM 元素节点，后续需挂载到文档才显示
            alert = document.createElement('div');
            //> 给「alert.className」赋值，更新其保存的状态
            alert.className = 'auth-form-alert';
            //> 设置元素的 HTML 属性
            alert.setAttribute('role', 'alert');
            //> 声明变量「title」（title），用于保存对应数据
            var title = box.querySelector('.auth-title');
            //> 条件判断：满足括号内条件时执行对应分支
            if (title && title.nextSibling) {
                //> 在参考子节点之前插入新子节点
                box.insertBefore(alert, title.nextSibling);
            //> 以上条件都不满足时执行的兜底分支
            } else {
                //> 在参考子节点之前插入新子节点
                box.insertBefore(alert, box.firstChild);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 返回结果并结束当前函数
        return alert;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /** 清空一次提交遗留的所有错误态。 */
    // =========================================================
    // 【函数】clearErrors
    // 功能：清空「errors」相关逻辑（clear errors）
    // 参数：
    //   - form：传入的参数（含义结合调用处与函数体）
    //   - box：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function clearErrors(form, box) {
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        form.querySelectorAll('.is-invalid').forEach(function (el) {
            //> 移除元素的一个或多个样式类
            el.classList.remove('is-invalid');
            //> 操作「el」的相关方法/属性
            el.removeAttribute('aria-invalid');
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        // 复用模板预置的 #err-<field> 占位（清空 + 隐藏）；仅移除本脚本动态插入的节点
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        form.querySelectorAll('.field-error').forEach(function (el) {
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            el.textContent = '';
            //> 给「el.hidden」赋值，更新其保存的状态
            el.hidden = true;
            //> 条件判断：满足括号内条件时执行对应分支
            if (el.dataset.jsInline === '1') el.remove();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        //> 声明变量「alert」（alert），用于保存对应数据
        var alert = box && box.querySelector('.auth-form-alert');
        //> 条件判断：满足括号内条件时执行对应分支
        if (alert) alert.remove();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /** 在指定输入框下方渲染红色内联错误；fieldKey 为空时渲染到顶部汇总。 */
    // =========================================================
    // 【函数】showFieldError
    // 功能：显示「field error」相关逻辑（show field error）
    // 参数：
    //   - form：传入的参数（含义结合调用处与函数体）
    //   - box：传入的参数（含义结合调用处与函数体）
    //   - fieldKey：传入的参数（含义结合调用处与函数体）
    //   - message：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function showFieldError(form, box, fieldKey, message) {
        //> 条件判断：满足括号内条件时执行对应分支
        if (!fieldKey) {
            // ---- 整块提示：优先复用页面预置的错误容器（如 #login-error / .auth-form-alert），
            //      并把其中的专用文本节点 #login-error-text 一并更新，
            //      同时显式移除 hidden 属性 + 打上 .is-visible（双通道，避免样式/脚本冲突导致不可见）
            //> 声明变量「container」（container），用于保存对应数据，值为一个函数
            var container = (box && box.querySelector('.login-error'))
                //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
                || (box && box.querySelector('.auth-form-alert'))
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                || ensureAlert(box);
            //> 条件判断：满足括号内条件时执行对应分支
            if (container) {
                //> 声明变量「textNode」（text node），用于保存对应数据
                var textNode = container.querySelector('#login-error-text');
                //> 条件判断：满足括号内条件时执行对应分支
                if (textNode) {
                    //> 读写纯文本内容，不解析 HTML，可防 XSS
                    textNode.textContent = message;
                //> 否则若满足该条件则进入此分支
                } else if (container.classList.contains('login-error')
                           //> 判断元素是否含有指定样式类，返回布尔值
                           || container.classList.contains('form-error-text')) {
                    // 没有专用文本节点时，保留装饰性 emoji，仅替换正文
                    //> 读写纯文本内容，不解析 HTML，可防 XSS
                    container.textContent = message;
                    //> 操作「container」的相关方法/属性
                    container.insertAdjacentHTML('afterbegin', '<span aria-hidden="true">😿</span>');
                //> 以上条件都不满足时执行的兜底分支
                } else {
                    //> 读写纯文本内容，不解析 HTML，可防 XSS
                    container.textContent = message;
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
                //> 给「container.hidden」赋值，更新其保存的状态
                container.hidden = false;
                //> 操作「container」的相关方法/属性
                container.removeAttribute('hidden');
                //> 为元素添加一个或多个样式类
                container.classList.add('is-visible');
                //> 给「container.style.display」赋值，更新其保存的状态
                container.style.display = '';
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 提前结束函数，无返回值
            return;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 声明变量「input」（input），用于保存对应数据
        var input = form.querySelector('[name="' + fieldKey + '"]');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!input) {
            //> 调用函数「showFieldError」并传入参数执行对应逻辑
            showFieldError(form, box, '', message);   // 无对应输入框时降级为整块提示
            //> 提前结束函数，无返回值
            return;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 为元素添加一个或多个样式类
        input.classList.add('is-invalid');
        //> 设置元素的 HTML 属性
        input.setAttribute('aria-invalid', 'true');
        //> 声明变量「errId」（err id），用于保存对应数据，初始为字符串
        var errId = 'err-' + fieldKey;
        //> 声明变量「node」（node），用于保存对应数据
        var node = form.querySelector('#' + errId);
        //> 条件判断：满足括号内条件时执行对应分支
        if (!node) {
            //> 创建新的 DOM 元素节点，后续需挂载到文档才显示
            node = document.createElement('span');
            //> 给「node.id」赋值，更新其保存的状态
            node.id = errId;
            //> 给「node.className」赋值，更新其保存的状态
            node.className = 'field-error form-error-text';
            //> 设置元素的 HTML 属性
            node.setAttribute('role', 'alert');
            //> 读写元素的 data-* 自定义数据属性
            node.dataset.jsInline = '1';
            //> 操作「input」的相关方法/属性
            input.insertAdjacentElement('afterend', node);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 读写纯文本内容，不解析 HTML，可防 XSS
        node.textContent = message;
        //> 给「node.hidden」赋值，更新其保存的状态
        node.hidden = false;
        //> 操作「node」的相关方法/属性
        node.removeAttribute('hidden');
        //> 为元素添加一个或多个样式类
        node.classList.add('is-visible');
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /** 解析服务端重渲染页面里的校验提示（.field-error / .auth-form-alert / flash）。 */
    // =========================================================
    // 【函数】parseServerErrors
    // 功能：解析「server errors」相关逻辑（parse server errors）
    // 参数：
    //   - html：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function parseServerErrors(html) {
        //> 声明变量「doc」（doc），用于保存对应数据
        var doc = new DOMParser().parseFromString(html, 'text/html');
        //> 声明变量「out」（out），用于保存对应数据
        var out = [];
        // 1) 认证卡片内的整块错误提示：优先读专用文本节点 #login-error-text，
        //    避免把装饰 emoji（😿）当成提示内容一起带出来
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        doc.querySelectorAll('.login-error, .auth-form-alert').forEach(function (el) {
            //> 声明变量「textNode」（text node），用于保存对应数据
            var textNode = el.querySelector('#login-error-text');
            //> 声明变量「text」（text），用于保存对应数据，值为一个函数
            var text = ((textNode ? textNode.textContent : el.textContent) || '');
            // 去掉开头的装饰性 emoji / 符号与空白
            //> 给「text」赋值，更新其保存的状态
            text = text.replace(/^[\s\u2600-\u27bf\ud83c-\udbff\udc00-\udfff\u2000-\u2bff]+/, '').trim();
            //> 条件判断：满足括号内条件时执行对应分支
            if (text) out.push({ field: '', message: text });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        // 2) 字段级错误
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        doc.querySelectorAll('.field-error').forEach(function (el) {
            //> 声明变量「text」（text），用于保存对应数据，值为一个函数
            var text = (el.textContent || '').trim();
            //> 条件判断：满足括号内条件时执行对应分支
            if (!text) return;
            //> 声明变量「field」（field），用于保存对应数据，初始为字符串
            var field = '';
            //> 声明变量「described」（described），用于保存对应数据
            var described = el.getAttribute('aria-describedby') || '';
            //> 声明变量「target」（target），用于保存对应数据
            var target = el.previousElementSibling;
            //> 条件判断：满足括号内条件时执行对应分支
            if (el.id) {
                //> 声明变量「forName」（for name），用于保存对应数据
                var forName = doc.querySelector('[aria-describedby~="' + el.id + '"]');
                //> 条件判断：满足括号内条件时执行对应分支
                if (forName && forName.name) field = forName.name;
                // 后端预置的占位 id 形如 err-<field>，可直接解析出字段名
                //> 条件判断：满足括号内条件时执行对应分支
                if (!field && el.id.indexOf('err-') === 0) field = el.id.slice(4);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 条件判断：满足括号内条件时执行对应分支
            if (!field && target && target.name) field = target.name;
            //> 条件判断：满足括号内条件时执行对应分支
            if (!field && described) field = described;
            //> 操作「out」的相关方法/属性
            out.push({ field: field, message: text });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        // 3) 兜底：模板未渲染内联错误时，使用顶部 flash 消息
        //> 条件判断：满足括号内条件时执行对应分支
        if (!out.length) {
            //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
            doc.querySelectorAll('.flash').forEach(function (el) {
                //> 声明变量「text」（text），用于保存对应数据，值为一个函数
                var text = (el.textContent || '').trim();
                //> 条件判断：满足括号内条件时执行对应分支
                if (text) out.push({ field: '', message: text });
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 返回结果并结束当前函数
        return out;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /** 把服务端返回的错误列表渲染到表单上，并聚焦首个出错字段。 */
    // =========================================================
    // 【函数】renderErrors
    // 功能：渲染「errors」相关逻辑（render errors）
    // 参数：
    //   - form：传入的参数（含义结合调用处与函数体）
    //   - box：传入的参数（含义结合调用处与函数体）
    //   - errors：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function renderErrors(form, box, errors) {
        //> 调用函数「clearErrors」并传入参数执行对应逻辑
        clearErrors(form, box);
        //> 条件判断：满足括号内条件时执行对应分支
        if (!errors.length) {
            //> 给「errors」赋值，更新其保存的状态
            errors = [{ field: '', message: '提交失败，请检查填写内容后重试喵~' }];
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 遍历数组/类数组中的每一项并执行回调
        errors.forEach(function (e) { showFieldError(form, box, e.field, e.message); });
        //> 声明变量「firstBad」（first bad），用于保存对应数据
        var firstBad = form.querySelector('.is-invalid');
        //> 条件判断：满足括号内条件时执行对应分支
        if (firstBad) {
            //> 操作「firstBad」的相关方法/属性
            firstBad.focus();
            //> 声明变量「card」（card），用于保存对应数据
            var card = box || form;
            //> 移除元素的一个或多个样式类
            card.classList.remove('reg-shake');
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            void card.offsetWidth;   // 强制重排后重放动画
            //> 为元素添加一个或多个样式类
            card.classList.add('reg-shake');
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /** 给单个表单绑定免刷新提交。 */
    // =========================================================
    // 【函数】bindForm
    // 功能：绑定「form」相关逻辑（bind form）
    // 参数：
    //   - form：传入的参数（含义结合调用处与函数体）
    //   - opts：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function bindForm(form, opts) {
        //> 声明变量「box」（box），用于保存对应数据
        var box = form.closest('.auth-card') || form.parentElement;
        //> 声明变量「btn」（btn），用于保存对应数据
        var btn = form.querySelector('button[type="submit"]');
        //> 声明变量「idleText」（idle text），用于保存对应数据
        var idleText = btn ? btn.textContent : '';
        //> 声明变量「busyText」（busy text），用于保存对应数据
        var busyText = opts.busyText || '提交中喵…';

        // =========================================================
        // 【函数】resetBtn
        // 功能：重置「btn」相关逻辑（reset btn）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function resetBtn() {
            //> 条件判断：满足括号内条件时执行对应分支
            if (!btn) return;
            //> 移除元素的一个或多个样式类
            btn.classList.remove('is-loading');
            //> 给「btn.disabled」赋值，更新其保存的状态
            btn.disabled = false;
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            btn.textContent = idleText;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }

        // 原生校验失败时也给出内联红字提示（而不是只靠浏览器气泡）
        //> 绑定「invalid」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        form.addEventListener('invalid', function (ev) {
            //> 声明变量「el」（el），用于保存对应数据
            var el = ev.target;
            //> 条件判断：满足括号内条件时执行对应分支
            if (!el.name) return;
            //> 声明变量「msg」（msg），用于保存对应数据
            var msg = el.validationMessage || '这一项填写不正确喵~';
            //> 调用函数「showFieldError」并传入参数执行对应逻辑
            showFieldError(form, box, el.name, msg);
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }, true);
        //> 绑定「input」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        form.addEventListener('input', function (ev) {
            //> 声明变量「el」（el），用于保存对应数据
            var el = ev.target;
            //> 条件判断：满足括号内条件时执行对应分支
            if (!el.name) return;
            //> 移除元素的一个或多个样式类
            el.classList.remove('is-invalid');
            //> 操作「el」的相关方法/属性
            el.removeAttribute('aria-invalid');
            //> 声明变量「node」（node），用于保存对应数据
            var node = form.querySelector('#err-' + el.name);
            //> 条件判断：满足括号内条件时执行对应分支
            if (node) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (node.dataset.jsInline === '1') node.remove();
                //> 以上条件都不满足时执行的兜底分支
                else { node.textContent = ''; node.hidden = true; }
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });

        //> 绑定「submit」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        form.addEventListener('submit', function (e) {
            // 原生校验不通过：交给浏览器 + invalid 事件渲染内联提示
            //> 条件判断：满足括号内条件时执行对应分支
            if (typeof form.checkValidity === 'function' && !form.checkValidity()) {
                //> 阻止事件的默认行为（如表单提交、链接跳转）
                e.preventDefault();
                //> 操作「form」的相关方法/属性
                form.reportValidity();
                //> 提前结束函数，无返回值
                return;
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 阻止事件的默认行为（如表单提交、链接跳转）
            e.preventDefault();
            //> 条件判断：满足括号内条件时执行对应分支
            if (btn) {
                //> 为元素添加一个或多个样式类
                btn.classList.add('is-loading');
                //> 给「btn.disabled」赋值，更新其保存的状态
                btn.disabled = true;
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                btn.textContent = busyText;
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 声明变量「headers」（headers），用于保存对应数据
            var headers = { 'X-Requested-With': 'XMLHttpRequest' };
            //> 声明变量「csrf」（csrf），用于保存对应数据
            var csrf = readCsrf(form);
            //> 条件判断：满足括号内条件时执行对应分支
            if (csrf) headers['X-CSRFToken'] = csrf;

            //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
            fetch(form.action || window.location.href, {
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                method: 'POST',
                //> 构造表单数据对象，常用于异步提交（含文件）
                body: new FormData(form),
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                redirect: 'manual',            // 成功的 302 以 opaqueredirect 返回
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                credentials: 'same-origin',
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                headers: headers
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }).then(function (resp) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (resp.type === 'opaqueredirect' || resp.status === 0) {
                    // 成功：跳转 next 或首页
                    //> 声明变量「params」（params），用于保存对应数据
                    var params = new URLSearchParams(window.location.search);
                    //> 通过赋值跳转页面
                    window.location.href = params.get('next') || opts.successUrl || '/';
                    //> 返回结果并结束当前函数
                    return null;
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
                //> 条件判断：满足括号内条件时执行对应分支
                if (resp.ok) return resp.text();
                //> 主动抛出异常，交由上层捕获处理
                throw new Error('bad status ' + resp.status);
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }).then(function (html) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (html === null) return;      // 已跳转
                //> 调用函数「resetBtn」并传入参数执行对应逻辑
                resetBtn();
                //> 调用函数「renderErrors」并传入参数执行对应逻辑
                renderErrors(form, box, parseServerErrors(html));
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }).catch(function () {
                //> 调用函数「resetBtn」并传入参数执行对应逻辑
                resetBtn();
                //> 调用函数「renderErrors」并传入参数执行对应逻辑
                renderErrors(form, box, [{ field: '', message: '网络开小差了，稍后再试喵~' }]);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    //> 声明变量「loginForm」（login form），用于保存对应数据，保存 DOM/窗口相关对象
    var loginForm = document.getElementById('login-form');
    //> 条件判断：满足括号内条件时执行对应分支
    if (loginForm) bindForm(loginForm, { busyText: '登录中喵…' });

    //> 声明变量「registerForm」（register form），用于保存对应数据，保存 DOM/窗口相关对象
    var registerForm = document.getElementById('register-form');
    //> 条件判断：满足括号内条件时执行对应分支
    if (registerForm) bindForm(registerForm, { busyText: '注册中喵…' });

    /* ---- 注册页密码一致性实时提示：两次不一致时即时红字，无需等提交 ---- */
    //> 条件判断：满足括号内条件时执行对应分支
    if (registerForm) {
        //> 声明变量「pw1」（pw1），用于保存对应数据
        var pw1 = registerForm.querySelector('[name=password]');
        //> 声明变量「pw2」（pw2），用于保存对应数据
        var pw2 = registerForm.querySelector('[name=password2]');
        //> 声明变量「box」（box），用于保存对应数据
        var box = registerForm.closest('.auth-card') || registerForm.parentElement;
        // =========================================================
        // 【函数】checkMatch
        // 功能：检查/校验「match」相关逻辑（check match）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function checkMatch() {
            //> 条件判断：满足括号内条件时执行对应分支
            if (!pw1 || !pw2 || !pw2.value) return;
            //> 条件判断：满足括号内条件时执行对应分支
            if (pw1.value === pw2.value) {
                //> 移除元素的一个或多个样式类
                pw2.classList.remove('is-invalid');
                //> 声明变量「n」（n），用于保存对应数据
                var n = registerForm.querySelector('#err-password2');
                //> 条件判断：满足括号内条件时执行对应分支
                if (n) {
                    //> 条件判断：满足括号内条件时执行对应分支
                    if (n.dataset.jsInline === '1') n.remove();
                    //> 以上条件都不满足时执行的兜底分支
                    else { n.textContent = ''; n.hidden = true; }
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
                //> 提前结束函数，无返回值
                return;
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 调用函数「showFieldError」并传入参数执行对应逻辑
            showFieldError(registerForm, box, 'password2', '两次密码不一样呢~再确认一下喵🔍');
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 条件判断：满足括号内条件时执行对应分支
        if (pw2) pw2.addEventListener('input', checkMatch);
        //> 条件判断：满足括号内条件时执行对应分支
        if (pw1) pw1.addEventListener('input', checkMatch);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ---- 注册页：把服务端整页重渲染留下的 flash 错误转成内联红字（兜底） ---- */
    //> 条件判断：满足括号内条件时执行对应分支
    if (registerForm) {
        //> 声明变量「box2」（box2），用于保存对应数据
        var box2 = registerForm.closest('.auth-card') || registerForm.parentElement;
        //> 声明变量「flashes」（flashes），用于保存对应数据，保存 DOM/窗口相关对象
        var flashes = document.querySelectorAll('.flash-error, .flash-danger');
        //> 条件判断：满足括号内条件时执行对应分支
        if (flashes.length) {
            //> 声明变量「errs」（errs），用于保存对应数据
            var errs = [];
            //> 遍历数组/类数组中的每一项并执行回调
            flashes.forEach(function (f) {
                //> 声明变量「text」（text），用于保存对应数据，值为一个函数
                var text = (f.textContent || '').trim();
                //> 条件判断：满足括号内条件时执行对应分支
                if (text) errs.push({ field: '', message: text });
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            //> 调用函数「renderErrors」并传入参数执行对应逻辑
            renderErrors(registerForm, box2, errs);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

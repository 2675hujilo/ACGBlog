/**
 * comments.js —— 文章详情页评论区交互
 * 功能：
 *   1. 相对时间格式化：把 .comment-time[data-ts] 渲染为"X分钟前/X小时前/X天前"；
 *   2. 发表评论：主表单 AJAX 提交，成功后把新评论 HTML 插入列表顶部 / 对应回复槽，
 *      并更新评论总数；失败则在提示区显示后端返回的错误文案；
 *   3. 楼中楼回复：点击"回复"按钮展开内联表单，提交后把回复 HTML 追加到父评论下；
 *   4. 评论点赞：AJAX POST 到 /api/comments/<pk>/like/，成功后更新数字并禁用按钮。
 * 依赖：无（纯原生 JS）。执行方式：IIFE，DOM 就绪后自动初始化。
 */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';

    /* ============================ 工具函数 ============================ */

    /**
     * 轻量 toast 提示（替代 alert，更萌）
     */
    // =========================================================
    // 【函数】toast
    // 功能：处理「toast」相关逻辑（comments）
    // 参数：
    //   - msg：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function toast(msg) {
        //> 声明变量「t」（t），用于保存对应数据，保存 DOM/窗口相关对象
        var t = document.getElementById('global-toast');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!t) {
            //> 创建新的 DOM 元素节点，后续需挂载到文档才显示
            t = document.createElement('div');
            //> 给「t.id」赋值，更新其保存的状态
            t.id = 'global-toast';
            //> 把子节点追加到当前元素内部末尾
            document.body.appendChild(t);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 读写纯文本内容，不解析 HTML，可防 XSS
        t.textContent = msg;
        //> 为元素添加一个或多个样式类
        t.classList.add('show');
        //> 清除对应的定时器，防止其继续执行
        clearTimeout(t._timer);
        //> 移除元素的一个或多个样式类
        t._timer = setTimeout(function () { t.classList.remove('show'); }, 2200);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /**
     * 读取指定名称的 cookie（用于 csrftoken）。
     * @param {string} name cookie 名
     * @returns {string|null}
     */
    // =========================================================
    // 【函数】getCookie
    // 功能：获取「cookie」相关逻辑（get cookie）
    // 参数：
    //   - name：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function getCookie(name) {
        //> 声明变量「arr」（arr），用于保存对应数据，保存 DOM/窗口相关对象
        var arr = document.cookie.match(new RegExp('(^| )' + name + '=([^;]*)(;|$)'));
        //> 返回结果并结束当前函数
        return arr ? decodeURIComponent(arr[2]) : null;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /**
     * 把 Unix 时间戳(秒)格式化为相对时间字符串。
     * @param {number} ts 秒级时间戳
     * @returns {string} 形如"刚刚 / X分钟前 / X小时前 / X天前 / 日期"
     */
    // =========================================================
    // 【函数】relTime
    // 功能：处理「rel time」相关逻辑（comments）
    // 参数：
    //   - ts：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function relTime(ts) {
        //> 声明变量「diff」（diff），用于保存对应数据
        var diff = Math.floor(Date.now() / 1000) - Number(ts);
        //> 条件判断：满足括号内条件时执行对应分支
        if (diff < 60) return '刚刚';
        //> 条件判断：满足括号内条件时执行对应分支
        if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前';
        //> 条件判断：满足括号内条件时执行对应分支
        if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前';
        //> 条件判断：满足括号内条件时执行对应分支
        if (diff < 86400 * 30) return Math.floor(diff / 86400) + ' 天前';
        // 超过 30 天回退为 YYYY-MM-DD
        //> 声明变量「d」（d），用于保存对应数据
        var d = new Date(ts * 1000);
        //> 返回结果并结束当前函数
        return d.getFullYear() + '-' +
            //> 调用函数「String」并传入参数执行对应逻辑
            String(d.getMonth() + 1).padStart(2, '0') + '-' +
            //> 调用函数「String」并传入参数执行对应逻辑
            String(d.getDate()).padStart(2, '0');
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /**
     * 把页面上所有 .comment-time[data-ts] 替换为相对时间。
     */
    // =========================================================
    // 【函数】refreshRelativeTimes
    // 功能：刷新「relative times」相关逻辑（refresh relative times）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function refreshRelativeTimes() {
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        document.querySelectorAll('.comment-time[data-ts]').forEach(function (el) {
            //> 声明变量「ts」（ts），用于保存对应数据
            var ts = el.getAttribute('data-ts');
            //> 条件判断：满足括号内条件时执行对应分支
            if (ts) el.textContent = relTime(ts);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /**
     * 通用 fetch 包装：POST JSON 表单，自动带 CSRF。
     * @param {string} url 提交地址
     * @param {FormData} formData 表单数据
     * @returns {Promise<object>} 解析后的 JSON
     */
    // =========================================================
    // 【函数】postForm
    // 功能：处理「post form」相关逻辑（comments）
    // 参数：
    //   - url：传入的参数（含义结合调用处与函数体）
    //   - formData：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function postForm(url, formData) {
        //> 返回结果并结束当前函数
        return fetch(url, {
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            method: 'POST',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            credentials: 'same-origin',
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            body: formData
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }).then(function (resp) {
            //> 返回结果并结束当前函数
            return resp.json().then(function (data) {
                //> 给「data._status」赋值，更新其保存的状态
                data._status = resp.status;
                //> 返回结果并结束当前函数
                return data;
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ============================ 1. 发表主评论 ============================ */
    //> 声明变量「commentForm」（comment form），用于保存对应数据，保存 DOM/窗口相关对象
    var commentForm = document.getElementById('comment-form');
    //> 条件判断：满足括号内条件时执行对应分支
    if (commentForm) {
        //> 绑定「submit」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        commentForm.addEventListener('submit', function (e) {
            //> 阻止事件的默认行为（如表单提交、链接跳转）
            e.preventDefault();
            //> 声明变量「input」（input），用于保存对应数据，保存 DOM/窗口相关对象
            var input = document.getElementById('comment-input');
            //> 声明变量「submitBtn」（submit btn），用于保存对应数据，保存 DOM/窗口相关对象
            var submitBtn = document.getElementById('comment-submit');
            //> 声明变量「url」（url），用于保存对应数据
            var url = commentForm.getAttribute('data-url');
            //> 声明变量「content」（content），用于保存对应数据，值为一个函数
            var content = (input.value || '').trim();
            //> 条件判断：满足括号内条件时执行对应分支
            if (!content) {
                //> 调用函数「toast」并传入参数执行对应逻辑
                toast('评论内容不能为空喵~ 📝');
                //> 提前结束函数，无返回值
                return;
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 声明变量「oldText」（old text），用于保存对应数据
            var oldText = submitBtn.textContent;
            //> 给「submitBtn.disabled」赋值，更新其保存的状态
            submitBtn.disabled = true;
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            submitBtn.textContent = '发送中...';
            //> 声明变量「fd」（fd），用于保存对应数据
            var fd = new FormData();
            //> 操作「fd」的相关方法/属性
            fd.append('content', content);
            //> 调用函数「postForm」并传入参数执行对应逻辑
            postForm(url, fd).then(function (data) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (data.success) {
                    // 清空输入框
                    //> 给「input.value」赋值，更新其保存的状态
                    input.value = '';
                    // 移除空状态提示（若存在）
                    //> 声明变量「empty」（empty），用于保存对应数据，保存 DOM/窗口相关对象
                    var empty = document.querySelector('.comment-empty');
                    //> 条件判断：满足括号内条件时执行对应分支
                    if (empty) empty.remove();
                    // Bug3：顶级评论需先包进 .comment-thread（父子同框的「一个框」）再插到列表最前
                    //> 声明变量「list」（list），用于保存对应数据，保存 DOM/窗口相关对象
                    var list = document.getElementById('comment-list');
                    //> 声明变量「wrap」（wrap），用于保存对应数据，保存 DOM/窗口相关对象
                    var wrap = document.createElement('div');
                    //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
                    wrap.innerHTML = data.html.trim();
                    //> 声明变量「node」（node），用于保存对应数据
                    var node = wrap.firstElementChild;
                    // Bug1：评论需审核时作者本人看到半透明「审核中」态
                    //> 条件判断：满足括号内条件时执行对应分支
                    if (data.moderation_pending && node) node.classList.add('comment-pending');
                    //> 声明变量「newThread」（new thread），用于保存对应数据，保存 DOM/窗口相关对象
                    var newThread = document.createElement('div');
                    //> 给「newThread.className」赋值，更新其保存的状态
                    newThread.className = 'comment-thread';
                    //> 设置元素的 HTML 属性
                    newThread.setAttribute('data-thread', '');
                    //> 把子节点追加到当前元素内部末尾
                    newThread.appendChild(node);
                    //> 在参考子节点之前插入新子节点
                    list.insertBefore(newThread, list.firstChild);
                    // 更新评论总数
                    //> 调用函数「updateCount」并传入参数执行对应逻辑
                    updateCount(data.comment_count);
                    // 新插入节点的相对时间格式化
                    //> 调用函数「refreshRelativeTimes」并传入参数执行对应逻辑
                    refreshRelativeTimes();
                    //> 调用函数「toast」并传入参数执行对应逻辑
                    toast('评论成功喵~ ✨');
                //> 以上条件都不满足时执行的兜底分支
                } else {
                    //> 调用函数「toast」并传入参数执行对应逻辑
                    toast(data.error || '发表失败了喵~再试一次吧');
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }).catch(function () {
                //> 调用函数「toast」并传入参数执行对应逻辑
                toast('网络开小差了喵~再试一次吧');
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }).finally(function () {
                //> 给「submitBtn.disabled」赋值，更新其保存的状态
                submitBtn.disabled = false;
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                submitBtn.textContent = oldText;
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ============================ 2. 回复（事件委托） ============================ */
    //> 声明变量「commentList」（comment list），用于保存对应数据，保存 DOM/窗口相关对象
    var commentList = document.getElementById('comment-list');
    //> 条件判断：满足括号内条件时执行对应分支
    if (commentList) {
        // 展开 / 收起内联回复表单
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        commentList.addEventListener('click', function (e) {
            //> 声明变量「replyBtn」（reply btn），用于保存对应数据
            var replyBtn = e.target.closest('.comment-reply-btn');
            //> 条件判断：满足括号内条件时执行对应分支
            if (replyBtn) {
                //> 声明变量「item」（item），用于保存对应数据
                var item = replyBtn.closest('.comment-item');
                //> 声明变量「form」（form），用于保存对应数据
                var form = item.querySelector('.comment-reply-form');
                // 只展开当前这条，收起其它已展开的
                //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
                document.querySelectorAll('.comment-reply-form:not([hidden])').forEach(function (f) {
                    //> 条件判断：满足括号内条件时执行对应分支
                    if (f !== form) f.hidden = true;
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                });
                //> 操作「form」的相关方法/属性
                form.hidden = !form.hidden;
                //> 条件判断：满足括号内条件时执行对应分支
                if (!form.hidden) {
                    //> 声明变量「ta」（ta），用于保存对应数据
                    var ta = form.querySelector('textarea');
                    //> 条件判断：满足括号内条件时执行对应分支
                    if (ta) ta.focus();
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
                //> 提前结束函数，无返回值
                return;
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            // 取消回复
            //> 条件判断：满足括号内条件时执行对应分支
            if (e.target.closest('.comment-reply-cancel')) {
                //> 声明变量「f」（f），用于保存对应数据
                var f = e.target.closest('.comment-reply-form');
                //> 条件判断：满足括号内条件时执行对应分支
                if (f) f.hidden = true;
                //> 提前结束函数，无返回值
                return;
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            // 提交回复
            //> 声明变量「submitReply」（submit reply），用于保存对应数据
            var submitReply = e.target.closest('.comment-reply-submit');
            //> 条件判断：满足括号内条件时执行对应分支
            if (submitReply) {
                //> 声明变量「item」（item），用于保存对应数据
                var item = submitReply.closest('.comment-item');
                //> 声明变量「form」（form），用于保存对应数据
                var form = item.querySelector('.comment-reply-form');
                //> 声明变量「ta」（ta），用于保存对应数据
                var ta = form.querySelector('textarea');
                //> 声明变量「content」（content），用于保存对应数据，值为一个函数
                var content = (ta.value || '').trim();
                //> 条件判断：满足括号内条件时执行对应分支
                if (!content) { toast('回复内容不能为空喵~'); return; }
                //> 声明变量「parentPk」（parent pk），用于保存对应数据
                var parentPk = submitReply.getAttribute('data-pk');
                //> 声明变量「fd」（fd），用于保存对应数据
                var fd = new FormData();
                //> 操作「fd」的相关方法/属性
                fd.append('content', content);
                //> 操作「fd」的相关方法/属性
                fd.append('parent_comment_id', parentPk);
                //> 声明变量「url」（url），用于保存对应数据
                var url = commentForm
                    //> 读取元素的 HTML 属性值
                    ? commentForm.getAttribute('data-url')
                    //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
                    : document.querySelector('.comments-section').getAttribute('data-post-url');
                //> 声明变量「oldReplyText」（old reply text），用于保存对应数据
                var oldReplyText = submitReply.textContent;
                //> 给「submitReply.disabled」赋值，更新其保存的状态
                submitReply.disabled = true;
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                submitReply.textContent = '发送中...';
                //> 调用函数「postForm」并传入参数执行对应逻辑
                postForm(url, fd).then(function (data) {
                    //> 条件判断：满足括号内条件时执行对应分支
                    if (data.success) {
                        // 扁平化插入（bug10）：与服务端渲染保持一致，把新回复直接放进
                        // #comment-list 并紧跟在被回复评论之后；不再塞进父评论的
                        // .comment-reply-slot，避免逐层嵌套累积左外边距、越回复越靠右。
                        //> 声明变量「wrap」（wrap），用于保存对应数据，保存 DOM/窗口相关对象
                        var wrap = document.createElement('div');
                        //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
                        wrap.innerHTML = data.html.trim();
                        //> 声明变量「node」（node），用于保存对应数据
                        var node = wrap.firstElementChild;
                        // Bug1：回复需审核时同样标记为待审核态
                        //> 条件判断：满足括号内条件时执行对应分支
                        if (data.moderation_pending && node) node.classList.add('comment-pending');
                        // Bug3：定位被回复评论所在线程，把回复放进其 .comment-replies 容器
                        //> 声明变量「targetThread」（target thread），用于保存对应数据
                        var targetThread = item.closest('.comment-thread');
                        //> 声明变量「repliesBox」（replies box），用于保存对应数据
                        var repliesBox = targetThread ? targetThread.querySelector('.comment-replies') : null;
                        //> 条件判断：满足括号内条件时执行对应分支
                        if (!repliesBox && targetThread) {
                            // 该线程此前没有回复：新建回复容器并加到线程末尾
                            //> 创建新的 DOM 元素节点，后续需挂载到文档才显示
                            repliesBox = document.createElement('div');
                            //> 给「repliesBox.className」赋值，更新其保存的状态
                            repliesBox.className = 'comment-replies';
                            //> 把子节点追加到当前元素内部末尾
                            targetThread.appendChild(repliesBox);
                        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                        }
                        // 单条回复用 .comment-reply-row 包裹（与服务端渲染结构一致）
                        //> 声明变量「replyRow」（reply row），用于保存对应数据，保存 DOM/窗口相关对象
                        var replyRow = document.createElement('div');
                        //> 给「replyRow.className」赋值，更新其保存的状态
                        replyRow.className = 'comment-reply-row';
                        //> 把子节点追加到当前元素内部末尾
                        replyRow.appendChild(node);
                        //> 条件判断：满足括号内条件时执行对应分支
                        if (repliesBox) {
                            //> 把子节点追加到当前元素内部末尾
                            repliesBox.appendChild(replyRow);
                            //> 调用函数「updateThreadToggle」并传入参数执行对应逻辑
                            updateThreadToggle(targetThread);   // 重新计算折叠行与按钮文案
                        //> 以上条件都不满足时执行的兜底分支
                        } else {
                            // 极端兜底：找不到线程容器时直接追加到评论列表末尾
                            //> 按 id 获取单个元素，不存在时返回 null
                            document.getElementById('comment-list').appendChild(replyRow);
                        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                        }
                        //> 给「ta.value」赋值，更新其保存的状态
                        ta.value = '';
                        //> 操作「form」的相关方法/属性
                        form.hidden = true;
                        //> 调用函数「updateCount」并传入参数执行对应逻辑
                        updateCount(data.comment_count);
                        //> 调用函数「refreshRelativeTimes」并传入参数执行对应逻辑
                        refreshRelativeTimes();
                        //> 调用函数「toast」并传入参数执行对应逻辑
                        toast('回复成功喵~ 💬');
                    //> 以上条件都不满足时执行的兜底分支
                    } else {
                        //> 调用函数「toast」并传入参数执行对应逻辑
                        toast(data.error || '回复失败了喵~');
                    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                    }
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                }).catch(function () {
                    //> 调用函数「toast」并传入参数执行对应逻辑
                    toast('网络开小差了喵~');
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                }).finally(function () {
                    //> 给「submitReply.disabled」赋值，更新其保存的状态
                    submitReply.disabled = false;
                    //> 读写纯文本内容，不解析 HTML，可防 XSS
                    submitReply.textContent = oldReplyText;
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                });
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ============================ 3. 评论点赞（事件委托） ============================ */
    //> 条件判断：满足括号内条件时执行对应分支
    if (commentList) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        commentList.addEventListener('click', function (e) {
            //> 声明变量「likeBtn」（like btn），用于保存对应数据
            var likeBtn = e.target.closest('.comment-like-btn');
            //> 条件判断：满足括号内条件时执行对应分支
            if (!likeBtn || likeBtn.disabled) return;
            //> 声明变量「url」（url），用于保存对应数据
            var url = likeBtn.getAttribute('data-url');
            //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
            fetch(url, {
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                method: 'POST',
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                headers: {
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    'X-CSRFToken': getCookie('csrftoken'),
                    //> 使用 XHR 发起传统异步请求
                    'X-Requested-With': 'XMLHttpRequest'
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                },
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                credentials: 'same-origin'
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }).then(function (r) { return r.json(); })
              //> 该行执行对应的脚本逻辑（结合上下文理解）
              .then(function (data) {
                  //> 条件判断：满足括号内条件时执行对应分支
                  if (typeof data.likes === 'number') {
                      //> 声明变量「n」（n），用于保存对应数据
                      var n = likeBtn.querySelector('.n');
                      //> 条件判断：满足括号内条件时执行对应分支
                      if (n) n.textContent = data.likes;
                  //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                  }
                  //> 给「likeBtn.disabled」赋值，更新其保存的状态
                  likeBtn.disabled = false;  // 请求期间已临时禁用，响应后恢复（toggle 取消/再赞）
                  //> 条件判断：满足括号内条件时执行对应分支
                  if (data.liked) {
                      //> 为元素添加一个或多个样式类
                      likeBtn.classList.add('liked');
                      //> 给「likeBtn.title」赋值，更新其保存的状态
                      likeBtn.title = '再点一下取消赞喵~';
                      //> 声明变量「txt」（txt），用于保存对应数据
                      var txt = likeBtn.querySelector('.txt');
                      //> 条件判断：满足括号内条件时执行对应分支
                      if (txt) txt.textContent = '已赞';
                  //> 以上条件都不满足时执行的兜底分支
                  } else {
                      //> 移除元素的一个或多个样式类
                      likeBtn.classList.remove('liked');
                      //> 给「likeBtn.title」赋值，更新其保存的状态
                      likeBtn.title = '赞喵';
                      //> 声明变量「txt」（txt），用于保存对应数据
                      var txt = likeBtn.querySelector('.txt');
                      //> 条件判断：满足括号内条件时执行对应分支
                      if (txt) txt.textContent = '赞';
                  //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                  }
              //> 该行执行对应的脚本逻辑（结合上下文理解）
              }).catch(function () {
                  //> 调用函数「toast」并传入参数执行对应逻辑
                  toast('点赞失败了喵~再试一次吧');
              //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
              });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ============================ Bug3：维护线程「展开/收起回复」按钮 ============================ */
    // =========================================================
    // 【函数】updateThreadToggle
    // 功能：更新「thread toggle」相关逻辑（update thread toggle）
    // 参数：
    //   - thread：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function updateThreadToggle(thread) {
        //> 条件判断：满足括号内条件时执行对应分支
        if (!thread) return;
        //> 声明变量「repliesBox」（replies box），用于保存对应数据
        var repliesBox = thread.querySelector('.comment-replies');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!repliesBox) return;
        //> 声明变量「SHOWN」（shown），用于保存对应数据
        var SHOWN = 3;   // 默认可见回复条数，与后端 REPLY_DEFAULT_SHOWN 一致
        //> 声明变量「rows」（rows），用于保存对应数据
        var rows = repliesBox.querySelectorAll('.comment-reply-row');
        //> 声明变量「toggle」（toggle），用于保存对应数据
        var toggle = repliesBox.querySelector('.comment-replies-toggle');
        //> 声明变量「isOpen」（is open），用于保存对应数据
        var isOpen = thread.classList.contains('replies-open');
        // 按当前是否展开，重新给超出 SHOWN 的行加 / 去 is-extra
        //> 遍历数组/类数组中的每一项并执行回调
        rows.forEach(function (r, i) {
            //> 切换样式类（有则移除、无则添加），可传第二参强制状态
            r.classList.toggle('is-extra', i >= SHOWN && !isOpen);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
        //> 声明变量「extra」（extra），用于保存对应数据
        var extra = Math.max(0, rows.length - SHOWN);
        //> 条件判断：满足括号内条件时执行对应分支
        if (extra > 0) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (!toggle) {
                //> 创建新的 DOM 元素节点，后续需挂载到文档才显示
                toggle = document.createElement('button');
                //> 给「toggle.type」赋值，更新其保存的状态
                toggle.type = 'button';
                //> 给「toggle.className」赋值，更新其保存的状态
                toggle.className = 'comment-replies-toggle';
                //> 把子节点追加到当前元素内部末尾
                repliesBox.appendChild(toggle);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 条件判断：满足括号内条件时执行对应分支
            if (isOpen) {
                //> 读写元素的 data-* 自定义数据属性
                toggle.dataset.collapsed = 'false';
                //> 设置元素的 HTML 属性
                toggle.setAttribute('aria-expanded', 'true');
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                toggle.textContent = '🫧 收起回复';
            //> 以上条件都不满足时执行的兜底分支
            } else {
                //> 读写元素的 data-* 自定义数据属性
                toggle.dataset.collapsed = 'true';
                //> 设置元素的 HTML 属性
                toggle.setAttribute('aria-expanded', 'false');
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                toggle.textContent = '💬 展开其余 ' + extra + ' 条回复';
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 否则若满足该条件则进入此分支
        } else if (toggle) {
            //> 把元素从 DOM 中移除
            toggle.remove();   // 回复数回到阈值内，移除折叠按钮
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ============================ 工具：更新评论总数 ============================ */
    // =========================================================
    // 【函数】updateCount
    // 功能：更新「count」相关逻辑（update count）
    // 参数：
    //   - n：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function updateCount(n) {
        //> 声明变量「el」（el），用于保存对应数据，保存 DOM/窗口相关对象
        var el = document.getElementById('comments-count');
        //> 条件判断：满足括号内条件时执行对应分支
        if (typeof n === 'number' && el) el.textContent = n;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ============================ 27. 评论字数统计（接近上限变黄，超限变红） ============================ */
    //> 声明变量「commentInput」（comment input），用于保存对应数据，保存 DOM/窗口相关对象
    var commentInput = document.getElementById('comment-input');
    //> 声明变量「wcNum」（wc num），用于保存对应数据，保存 DOM/窗口相关对象
    var wcNum = document.getElementById('comment-wc-num');
    //> 声明变量「wcBox」（wc box），用于保存对应数据，保存 DOM/窗口相关对象
    var wcBox = document.getElementById('comment-wc');
    //> 条件判断：满足括号内条件时执行对应分支
    if (commentInput && wcNum) {
        // =========================================================
        // 【函数】updateWc
        // 功能：更新「wc」相关逻辑（update wc）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        function updateWc() {
            //> 声明变量「n」（n），用于保存对应数据，值为一个函数
            var n = (commentInput.value || '').length;
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            wcNum.textContent = n;
            //> 条件判断：满足括号内条件时执行对应分支
            if (n >= 10000) { wcBox.classList.add('wc-over'); wcBox.classList.remove('wc-warn'); }
            //> 否则若满足该条件则进入此分支
            else if (n >= 8000) { wcBox.classList.add('wc-warn'); wcBox.classList.remove('wc-over'); }
            //> 以上条件都不满足时执行的兜底分支
            else { wcBox.classList.remove('wc-warn', 'wc-over'); }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 绑定「input」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        commentInput.addEventListener('input', updateWc);
        //> 调用函数「updateWc」并传入参数执行对应逻辑
        updateWc();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ============================ Bug4：主评论轻量富文本工具栏（仅主评论） ============================ */
    /**
     * 用指定标签包裹 textarea 当前选中文字；没有选中时插入占位文字并选中它。
     * @param {HTMLTextAreaElement} ta 主评论输入框
     * @param {string} before 起始标签
     * @param {string} after 结束标签
     * @param {string} ph 无选中时的占位文字
     */
    // =========================================================
    // 【函数】wrapSelection
    // 功能：处理「wrap selection」相关逻辑（comments）
    // 参数：
    //   - ta：传入的参数（含义结合调用处与函数体）
    //   - before：传入的参数（含义结合调用处与函数体）
    //   - after：传入的参数（含义结合调用处与函数体）
    //   - ph：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function wrapSelection(ta, before, after, ph) {
        //> 声明变量「s」（s），用于保存对应数据
        var s = ta.selectionStart != null ? ta.selectionStart : ta.value.length;
        //> 声明变量「e」（e），用于保存对应数据
        var e = ta.selectionEnd != null ? ta.selectionEnd : s;
        //> 声明变量「sel」（sel），用于保存对应数据
        var sel = ta.value.slice(s, e) || ph;
        //> 给「ta.value」赋值，更新其保存的状态
        ta.value = ta.value.slice(0, s) + before + sel + after + ta.value.slice(e);
        //> 给「ta.selectionStart」赋值，更新其保存的状态
        ta.selectionStart = s + before.length;
        //> 给「ta.selectionEnd」赋值，更新其保存的状态
        ta.selectionEnd = s + before.length + sel.length;
        //> 操作「ta」的相关方法/属性
        ta.focus();
        //> 创建并派发自定义事件，实现模块间解耦通信
        ta.dispatchEvent(new Event('input', { bubbles: true }));   // 触发字数统计更新
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    //> 声明变量「rtToolbar」（rt toolbar），用于保存对应数据，保存 DOM/窗口相关对象
    var rtToolbar = document.querySelector('.comment-rt-toolbar');
    //> 条件判断：满足括号内条件时执行对应分支
    if (rtToolbar) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        rtToolbar.addEventListener('click', function (e) {
            //> 声明变量「btn」（btn），用于保存对应数据
            var btn = e.target.closest('.crt-btn');
            //> 条件判断：满足括号内条件时执行对应分支
            if (!btn) return;
            //> 声明变量「ta」（ta），用于保存对应数据，保存 DOM/窗口相关对象
            var ta = document.getElementById('comment-input');
            //> 条件判断：满足括号内条件时执行对应分支
            if (!ta) return;
            //> 声明变量「fmt」（fmt），用于保存对应数据
            var fmt = btn.getAttribute('data-fmt');
            //> 条件判断：满足括号内条件时执行对应分支
            if (fmt === 'strong') {
                //> 调用函数「wrapSelection」并传入参数执行对应逻辑
                wrapSelection(ta, '<strong>', '</strong>', '加粗文字');
            //> 否则若满足该条件则进入此分支
            } else if (fmt === 'em') {
                //> 调用函数「wrapSelection」并传入参数执行对应逻辑
                wrapSelection(ta, '<em>', '</em>', '斜体文字');
            //> 否则若满足该条件则进入此分支
            } else if (fmt === 'code') {
                //> 调用函数「wrapSelection」并传入参数执行对应逻辑
                wrapSelection(ta, '<code>', '</code>', 'code');
            //> 否则若满足该条件则进入此分支
            } else if (fmt === 'link') {
                //> 声明变量「url」（url），用于保存对应数据，保存 DOM/窗口相关对象
                var url = window.prompt('请输入链接地址喵 (https://...)', 'https://');
                //> 条件判断：满足括号内条件时执行对应分支
                if (!url) return;
                //> 声明变量「s」（s），用于保存对应数据
                var s = ta.selectionStart != null ? ta.selectionStart : ta.value.length;
                //> 声明变量「en」（en），用于保存对应数据
                var en = ta.selectionEnd != null ? ta.selectionEnd : s;
                //> 声明变量「sel」（sel），用于保存对应数据
                var sel = ta.value.slice(s, en) || '萌系链接';
                //> 声明变量「html」（html），用于保存对应数据，初始为字符串
                var html = '<a href="' + url + '">' + sel + '</a>';
                //> 给「ta.value」赋值，更新其保存的状态
                ta.value = ta.value.slice(0, s) + html + ta.value.slice(en);
                //> 给「ta.selectionStart」赋值，更新其保存的状态
                ta.selectionStart = ta.selectionEnd = s + html.length;
                //> 操作「ta」的相关方法/属性
                ta.focus();
                //> 创建并派发自定义事件，实现模块间解耦通信
                ta.dispatchEvent(new Event('input', { bubbles: true }));
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* Bug4：图片喵按钮 → 打开文件选择框（上传成功后由 interaction.js 插入 <img>） */
    //> 声明变量「commentImageBtn」（comment image btn），用于保存对应数据，保存 DOM/窗口相关对象
    var commentImageBtn = document.getElementById('comment-image-btn');
    //> 声明变量「commentImageInput」（comment image input），用于保存对应数据，保存 DOM/窗口相关对象
    var commentImageInput = document.getElementById('comment-image-input');
    //> 条件判断：满足括号内条件时执行对应分支
    if (commentImageBtn && commentImageInput) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        commentImageBtn.addEventListener('click', function () { commentImageInput.click(); });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ============================ 初始化：相对时间 ============================ */
    //> 调用函数「refreshRelativeTimes」并传入参数执行对应逻辑
    refreshRelativeTimes();
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

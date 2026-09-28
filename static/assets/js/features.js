/**
 * features.js —— 详情页增强交互（点赞 / 分享 / 代码块复制）
 * 功能：
 *   1. 点赞按钮：点击 AJAX POST 到 /api/articles/<pk>/like/，
 *      成功后刷新点赞数字、按钮置为"已赞"态；
 *   2. 分享按钮组：
 *      - 微博：拼装 service.weibo.com/share/share.php 链接并新窗口打开；
 *      - Twitter(X)：拼装 twitter.com/intent/tweet 链接并新窗口打开；
 *      - 复制链接：navigator.clipboard.writeText 复制当前地址，成功提示"已复制喵~"；
 *   3. 代码块复制：遍历正文所有 pre / pre code，在右上角插入"复制"按钮，
 *      点击复制代码到剪贴板，按钮文字变"已复制✓"，2 秒后恢复。
 * 依赖：无（纯原生 JS，无外部库）
 * 执行方式：IIFE 立即执行函数，DOM 就绪后自动初始化
 */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';

    /* ============================ 1. 点赞按钮 ============================ */
    //> 声明变量「likeBtn」（like btn），用于保存对应数据，保存 DOM/窗口相关对象
    var likeBtn = document.getElementById('like-btn');
    //> 声明变量「likeCount」（like count），用于保存对应数据，保存 DOM/窗口相关对象
    var likeCount = document.getElementById('like-count');
    //> 条件判断：满足括号内条件时执行对应分支
    if (likeBtn && likeCount) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        likeBtn.addEventListener('click', function () {
            // 请求进行中临时禁用，防止重复提交；结束后恢复可点击（toggle 取消/再赞，D2修复）
            //> 条件判断：满足括号内条件时执行对应分支
            if (likeBtn.disabled) return;
            //> 声明变量「url」（url），用于保存对应数据
            var url = likeBtn.getAttribute('data-url');
            //> 给「likeBtn.disabled」赋值，更新其保存的状态
            likeBtn.disabled = true;
            // 带 CSRF token 的 fetch POST（Django 默认在 cookie 中存 csrftoken）
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
            }).then(function (resp) { return resp.json(); })
              //> 该行执行对应的脚本逻辑（结合上下文理解）
              .then(function (data) {
                  // 更新点赞数字
                  //> 条件判断：满足括号内条件时执行对应分支
                  if (typeof data.likes === 'number') {
                      //> 读写纯文本内容，不解析 HTML，可防 XSS
                      likeCount.textContent = data.likes;
                  //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                  }
                  // 按钮按后端返回切换已赞 / 取消态
                  //> 声明变量「text」（text），用于保存对应数据
                  var text = likeBtn.querySelector('.like-text');
                  //> 条件判断：满足括号内条件时执行对应分支
                  if (data.liked) {
                      //> 为元素添加一个或多个样式类
                      likeBtn.classList.add('liked');
                      //> 给「likeBtn.title」赋值，更新其保存的状态
                      likeBtn.title = '再点一下取消赞喵~';
                      //> 条件判断：满足括号内条件时执行对应分支
                      if (text) text.textContent = '已赞喵';
                  //> 以上条件都不满足时执行的兜底分支
                  } else {
                      //> 移除元素的一个或多个样式类
                      likeBtn.classList.remove('liked');
                      //> 给「likeBtn.title」赋值，更新其保存的状态
                      likeBtn.title = '点赞这篇文章';
                      //> 条件判断：满足括号内条件时执行对应分支
                      if (text) text.textContent = '点赞喵';
                  //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                  }
                  //> 给「likeBtn.disabled」赋值，更新其保存的状态
                  likeBtn.disabled = false;
              //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
              })
              //> 该行执行对应的脚本逻辑（结合上下文理解）
              .catch(function () {
                  //> 给「likeBtn.disabled」赋值，更新其保存的状态
                  likeBtn.disabled = false;
                  //> 条件判断：满足括号内条件时执行对应分支
                  if (window.moeToast) moeToast('点赞失败了喵~再试一次吧', 'error');
              //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
              });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ============================ 1.5 收藏按钮 ============================ */
    //> 声明变量「favBtn」（fav btn），用于保存对应数据，保存 DOM/窗口相关对象
    var favBtn = document.getElementById('fav-btn');
    //> 声明变量「favCount」（fav count），用于保存对应数据，保存 DOM/窗口相关对象
    var favCount = document.getElementById('fav-count');
    //> 条件判断：满足括号内条件时执行对应分支
    if (favBtn) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        favBtn.addEventListener('click', function () {
            //> 声明变量「url」（url），用于保存对应数据
            var url = favBtn.getAttribute('data-url');
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
            }).then(function (resp) {
                // 302 重定向说明未登录，跳转登录页
                //> 条件判断：满足括号内条件时执行对应分支
                if (resp.redirected) {
                    //> 通过赋值跳转页面
                    window.location.href = resp.url;
                    //> 返回结果并结束当前函数
                    return null;
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
                //> 返回结果并结束当前函数
                return resp.json();
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }).then(function (data) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (!data) return;
                // 更新按钮状态
                //> 条件判断：满足括号内条件时执行对应分支
                if (data.favorited) {
                    //> 为元素添加一个或多个样式类
                    favBtn.classList.add('favorited');
                    //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
                    favBtn.querySelector('.fav-icon').textContent = '⭐';
                    //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
                    favBtn.querySelector('.fav-text').textContent = '已收藏';
                //> 以上条件都不满足时执行的兜底分支
                } else {
                    //> 移除元素的一个或多个样式类
                    favBtn.classList.remove('favorited');
                    //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
                    favBtn.querySelector('.fav-icon').textContent = '☆';
                    //> 查询第一个匹配选择器的元素，结果可能为 null，使用前需判空
                    favBtn.querySelector('.fav-text').textContent = '收藏';
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
                // 更新收藏数
                //> 条件判断：满足括号内条件时执行对应分支
                if (typeof data.count === 'number' && favCount) {
                    //> 读写纯文本内容，不解析 HTML，可防 XSS
                    favCount.textContent = data.count;
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }).catch(function () {
                //> 条件判断：满足括号内条件时执行对应分支
                if (window.moeToast) moeToast('收藏失败了喵~再试一次吧', 'error');
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ============================ 2. 分享按钮组 ============================ */
    //> 声明变量「shareGroup」（share group），用于保存对应数据，保存 DOM/窗口相关对象
    var shareGroup = document.getElementById('share-group');
    //> 条件判断：满足括号内条件时执行对应分支
    if (shareGroup) {
        //> 声明变量「shareUrl」（share url），用于保存对应数据
        var shareUrl = shareGroup.getAttribute('data-url') || location.href;
        //> 声明变量「shareTitle」（share title），用于保存对应数据
        var shareTitle = shareGroup.getAttribute('data-title') || document.title;

        // 微博分享：拼装分享链接，新窗口打开
        //> 声明变量「weibo」（weibo），用于保存对应数据，保存 DOM/窗口相关对象
        var weibo = document.getElementById('share-weibo');
        //> 条件判断：满足括号内条件时执行对应分支
        if (weibo) {
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            weibo.addEventListener('click', function (e) {
                //> 阻止事件的默认行为（如表单提交、链接跳转）
                e.preventDefault();
                //> 声明变量「url」（url），用于保存对应数据，初始为字符串
                var url = 'https://service.weibo.com/share/share.php?url=' +
                    //> 对 URL 参数做编码，防止特殊字符破坏链接或被注入
                    encodeURIComponent(shareUrl) + '&title=' + encodeURIComponent(shareTitle);
                //> 操作「window」的相关方法/属性
                window.open(url, '_blank', 'noopener');
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // Twitter(X) 分享：拼装 intent/tweet 链接，新窗口打开
        //> 声明变量「twitter」（twitter），用于保存对应数据，保存 DOM/窗口相关对象
        var twitter = document.getElementById('share-twitter');
        //> 条件判断：满足括号内条件时执行对应分支
        if (twitter) {
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            twitter.addEventListener('click', function (e) {
                //> 阻止事件的默认行为（如表单提交、链接跳转）
                e.preventDefault();
                //> 声明变量「url」（url），用于保存对应数据，初始为字符串
                var url = 'https://twitter.com/intent/tweet?url=' +
                    //> 对 URL 参数做编码，防止特殊字符破坏链接或被注入
                    encodeURIComponent(shareUrl) + '&text=' + encodeURIComponent(shareTitle);
                //> 操作「window」的相关方法/属性
                window.open(url, '_blank', 'noopener');
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // 复制链接：navigator.clipboard 复制当前文章地址
        //> 声明变量「copyBtn」（copy btn），用于保存对应数据，保存 DOM/窗口相关对象
        var copyBtn = document.getElementById('share-copy');
        //> 条件判断：满足括号内条件时执行对应分支
        if (copyBtn) {
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            copyBtn.addEventListener('click', function () {
                //> 调用函数「copyText」并传入参数执行对应逻辑
                copyText(shareUrl).then(function () {
                    // 成功提示：按钮文字临时变为"已复制喵~"，2 秒后恢复
                    //> 声明变量「original」（original），用于保存对应数据
                    var original = copyBtn.textContent;
                    //> 读写纯文本内容，不解析 HTML，可防 XSS
                    copyBtn.textContent = '✅ 已复制喵~';
                    //> 读写纯文本内容，不解析 HTML，可防 XSS
                    setTimeout(function () { copyBtn.textContent = original; }, 2000);
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                }).catch(function () {
                    //> 条件判断：满足括号内条件时执行对应分支
                    if (window.moeToast) moeToast('复制失败了喵~请手动复制地址栏链接', 'error');
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                });
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ============================ 3. 代码块复制按钮 ============================ */
    //> 声明变量「articleBody」（article body），用于保存对应数据，保存 DOM/窗口相关对象
    var articleBody = document.getElementById('article-body');
    //> 条件判断：满足括号内条件时执行对应分支
    if (articleBody) {
        // 遍历所有 pre 代码块，在右上角插入复制按钮
        //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
        articleBody.querySelectorAll('pre').forEach(function (pre) {
            // 跳过已经加过按钮的（防止重复初始化）
            //> 条件判断：满足括号内条件时执行对应分支
            if (pre.querySelector('.code-copy-btn')) return;
            //> 声明变量「btn」（btn），用于保存对应数据，保存 DOM/窗口相关对象
            var btn = document.createElement('button');
            //> 给「btn.type」赋值，更新其保存的状态
            btn.type = 'button';
            //> 给「btn.className」赋值，更新其保存的状态
            btn.className = 'code-copy-btn';
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            btn.textContent = '复制';
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            btn.addEventListener('click', function () {
                // 优先取 pre 内 code 的文本，否则直接取 pre 的文本
                //> 声明变量「codeEl」（code el），用于保存对应数据
                var codeEl = pre.querySelector('code');
                //> 声明变量「text」（text），用于保存对应数据
                var text = codeEl ? codeEl.textContent : pre.textContent;
                //> 调用函数「copyText」并传入参数执行对应逻辑
                copyText(text).then(function () {
                    //> 读写纯文本内容，不解析 HTML，可防 XSS
                    btn.textContent = '已复制✓';
                    //> 为元素添加一个或多个样式类
                    btn.classList.add('copied');
                    // 2 秒后恢复按钮文字与样式
                    // =========================================================
                    // 【函数】setTimeout
                    // 功能：设置「timeout」相关逻辑（set timeout）
                    // 参数：
                    //   - function：传入的参数（含义结合调用处与函数体）
                    //   - (：传入的参数（含义结合调用处与函数体）
                    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
                    // 注意：含定时器，注意在适当时机清除，避免泄漏与重复触发
                    // =========================================================
                    setTimeout(function () {
                        //> 读写纯文本内容，不解析 HTML，可防 XSS
                        btn.textContent = '复制';
                        //> 移除元素的一个或多个样式类
                        btn.classList.remove('copied');
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    }, 2000);
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                }).catch(function () {
                    //> 读写纯文本内容，不解析 HTML，可防 XSS
                    btn.textContent = '失败';
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                });
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            //> 把子节点追加到当前元素内部末尾
            pre.appendChild(btn);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* ============================ 工具函数 ============================ */

    /**
     * 设置页：头像上传即时预览。
     * 选择文件后用 FileReader 读取，替换圆形预览区的图片。
     */
    //> 声明变量「avatarInput」（avatar input），用于保存对应数据，保存 DOM/窗口相关对象
    var avatarInput = document.getElementById('id_avatar');
    //> 条件判断：满足括号内条件时执行对应分支
    if (avatarInput) {
        //> 绑定「change」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        avatarInput.addEventListener('change', function () {
            //> 声明变量「file」（file），用于保存对应数据
            var file = avatarInput.files[0];
            //> 条件判断：满足括号内条件时执行对应分支
            if (!file) return;
            //> 声明变量「reader」（reader），用于保存对应数据
            var reader = new FileReader();
            // =========================================================
            // 【函数】onload
            // 功能：处理「onload」相关逻辑（features）
            // 参数：
            //   - e：传入的参数（含义结合调用处与函数体）
            // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
            // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
            // =========================================================
            reader.onload = function (e) {
                //> 声明变量「previewImg」（preview img），用于保存对应数据，保存 DOM/窗口相关对象
                var previewImg = document.getElementById('avatar-preview-img');
                //> 声明变量「initial」（initial），用于保存对应数据，保存 DOM/窗口相关对象
                var initial = document.getElementById('avatar-preview-initial');
                //> 条件判断：满足括号内条件时执行对应分支
                if (previewImg) {
                    //> 给「previewImg.src」赋值，更新其保存的状态
                    previewImg.src = e.target.result;
                    //> 给「previewImg.style.display」赋值，更新其保存的状态
                    previewImg.style.display = 'block';
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
                //> 条件判断：满足括号内条件时执行对应分支
                if (initial) {
                    //> 给「initial.style.display」赋值，更新其保存的状态
                    initial.style.display = 'none';
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            };
            //> 操作「reader」的相关方法/属性
            reader.readAsDataURL(file);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /**
     * 设置页：密码强度指示器。
     * 根据密码长度、字符种类实时计算弱/中/强。
     */
    //> 声明变量「newPwd」（new pwd），用于保存对应数据，保存 DOM/窗口相关对象
    var newPwd = document.getElementById('id_new_password');
    //> 声明变量「strengthFill」（strength fill），用于保存对应数据，保存 DOM/窗口相关对象
    var strengthFill = document.getElementById('strength-fill');
    //> 声明变量「strengthText」（strength text），用于保存对应数据，保存 DOM/窗口相关对象
    var strengthText = document.getElementById('strength-text');
    //> 声明变量「strengthWrap」（strength wrap），用于保存对应数据，保存 DOM/窗口相关对象
    var strengthWrap = document.querySelector('.password-strength');
    //> 条件判断：满足括号内条件时执行对应分支
    if (newPwd && strengthFill && strengthText && strengthWrap) {
        //> 绑定「input」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        newPwd.addEventListener('input', function () {
            //> 声明变量「pwd」（pwd），用于保存对应数据
            var pwd = newPwd.value;
            //> 声明变量「score」（score），用于保存对应数据
            var score = 0;
            //> 条件判断：满足括号内条件时执行对应分支
            if (pwd.length >= 8) score++;
            //> 条件判断：满足括号内条件时执行对应分支
            if (pwd.length >= 12) score++;
            //> 条件判断：满足括号内条件时执行对应分支
            if (/[A-Z]/.test(pwd) && /[a-z]/.test(pwd)) score++;
            //> 条件判断：满足括号内条件时执行对应分支
            if (/\d/.test(pwd)) score++;
            //> 条件判断：满足括号内条件时执行对应分支
            if (/[^A-Za-z0-9]/.test(pwd)) score++;

            // 移除旧的强度 class
            //> 移除元素的一个或多个样式类
            strengthWrap.classList.remove('strength-weak', 'strength-medium', 'strength-strong');
            //> 条件判断：满足括号内条件时执行对应分支
            if (!pwd) {
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                strengthText.textContent = '输入密码查看强度';
                //> 提前结束函数，无返回值
                return;
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 条件判断：满足括号内条件时执行对应分支
            if (score <= 2) {
                //> 为元素添加一个或多个样式类
                strengthWrap.classList.add('strength-weak');
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                strengthText.textContent = '弱';
            //> 否则若满足该条件则进入此分支
            } else if (score <= 3) {
                //> 为元素添加一个或多个样式类
                strengthWrap.classList.add('strength-medium');
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                strengthText.textContent = '中';
            //> 以上条件都不满足时执行的兜底分支
            } else {
                //> 为元素添加一个或多个样式类
                strengthWrap.classList.add('strength-strong');
                //> 读写纯文本内容，不解析 HTML，可防 XSS
                strengthText.textContent = '强';
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /**
     * 我的文章页：删除确认弹窗。
     * 所有带 .js-delete-confirm 的表单提交前弹出 confirm。
     */
    //> 查询所有匹配选择器的元素，返回可遍历的 NodeList
    document.querySelectorAll('form.js-delete-confirm').forEach(function (form) {
        //> 绑定「submit」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        form.addEventListener('submit', function (e) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (form.dataset.confirmed) return;
            //> 阻止事件的默认行为（如表单提交、链接跳转）
            e.preventDefault();
            // Bug8：改为站内萌系确认弹窗；删除现为软删除，可在回收站恢复
            //> 调用函数「moeConfirm」并传入参数执行对应逻辑
            moeConfirm({
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                message: '确定要把这篇内容收进回收站吗？之后可在审核后台的回收站恢复喵~',
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                danger: true, confirmText: '收进回收站'
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }).then(function (ok) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (ok) { form.dataset.confirmed = '1'; form.submit(); }
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /**
     * 读取指定名称的 cookie（用于获取 csrftoken）。
     * @param {string} name cookie 名
     * @returns {string|null} cookie 值
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
     * 兼容地复制文本到剪贴板。
     * 优先使用 navigator.clipboard（现代浏览器），失败时回退到 execCommand 方案。
     * @param {string} text 待复制文本
     * @returns {Promise<void>}
     */
    // =========================================================
    // 【函数】copyText
    // 功能：处理「copy text」相关逻辑（features）
    // 参数：
    //   - text：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function copyText(text) {
        //> 条件判断：满足括号内条件时执行对应分支
        if (navigator.clipboard && navigator.clipboard.writeText) {
            //> 返回结果并结束当前函数
            return navigator.clipboard.writeText(text);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        // 旧浏览器回退方案：创建临时 textarea 选中后执行 copy
        //> 返回结果并结束当前函数
        return new Promise(function (resolve, reject) {
            //> 声明变量「ta」（ta），用于保存对应数据，保存 DOM/窗口相关对象
            var ta = document.createElement('textarea');
            //> 给「ta.value」赋值，更新其保存的状态
            ta.value = text;
            //> 给「ta.style.position」赋值，更新其保存的状态
            ta.style.position = 'fixed';
            //> 给「ta.style.opacity」赋值，更新其保存的状态
            ta.style.opacity = '0';
            //> 把子节点追加到当前元素内部末尾
            document.body.appendChild(ta);
            //> 操作「ta」的相关方法/属性
            ta.select();
            //> 尝试执行可能出错的代码，出错则进入 catch
            try {
                //> 操作「document」的相关方法/属性
                document.execCommand('copy');
                //> 调用函数「resolve」并传入参数执行对应逻辑
                resolve();
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            } catch (e) {
                //> 调用函数「reject」并传入参数执行对应逻辑
                reject(e);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 操作「document.body」的相关方法/属性
            document.body.removeChild(ta);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

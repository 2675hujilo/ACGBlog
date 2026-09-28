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
(function () {
    'use strict';

    /* ============================ 1. 点赞按钮 ============================ */
    var likeBtn = document.getElementById('like-btn');
    var likeCount = document.getElementById('like-count');
    if (likeBtn && likeCount) {
        likeBtn.addEventListener('click', function () {
            // 请求进行中临时禁用，防止重复提交；结束后恢复可点击（toggle 取消/再赞，D2修复）
            if (likeBtn.disabled) return;
            var url = likeBtn.getAttribute('data-url');
            likeBtn.disabled = true;
            // 带 CSRF token 的 fetch POST（Django 默认在 cookie 中存 csrftoken）
            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            }).then(function (resp) { return resp.json(); })
              .then(function (data) {
                  // 更新点赞数字
                  if (typeof data.likes === 'number') {
                      likeCount.textContent = data.likes;
                  }
                  // 按钮按后端返回切换已赞 / 取消态
                  var text = likeBtn.querySelector('.like-text');
                  if (data.liked) {
                      likeBtn.classList.add('liked');
                      likeBtn.title = '再点一下取消赞喵~';
                      if (text) text.textContent = '已赞喵';
                  } else {
                      likeBtn.classList.remove('liked');
                      likeBtn.title = '点赞这篇文章';
                      if (text) text.textContent = '点赞喵';
                  }
                  likeBtn.disabled = false;
              })
              .catch(function () {
                  likeBtn.disabled = false;
                  if (window.moeToast) moeToast('点赞失败了喵~再试一次吧', 'error');
              });
        });
    }

    /* ============================ 1.5 收藏按钮 ============================ */
    var favBtn = document.getElementById('fav-btn');
    var favCount = document.getElementById('fav-count');
    if (favBtn) {
        favBtn.addEventListener('click', function () {
            var url = favBtn.getAttribute('data-url');
            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            }).then(function (resp) {
                // 302 重定向说明未登录，跳转登录页
                if (resp.redirected) {
                    window.location.href = resp.url;
                    return null;
                }
                return resp.json();
            }).then(function (data) {
                if (!data) return;
                // 更新按钮状态
                if (data.favorited) {
                    favBtn.classList.add('favorited');
                    favBtn.querySelector('.fav-icon').textContent = '⭐';
                    favBtn.querySelector('.fav-text').textContent = '已收藏';
                } else {
                    favBtn.classList.remove('favorited');
                    favBtn.querySelector('.fav-icon').textContent = '☆';
                    favBtn.querySelector('.fav-text').textContent = '收藏';
                }
                // 更新收藏数
                if (typeof data.count === 'number' && favCount) {
                    favCount.textContent = data.count;
                }
            }).catch(function () {
                if (window.moeToast) moeToast('收藏失败了喵~再试一次吧', 'error');
            });
        });
    }

    /* ============================ 2. 分享按钮组 ============================ */
    var shareGroup = document.getElementById('share-group');
    if (shareGroup) {
        var shareUrl = shareGroup.getAttribute('data-url') || location.href;
        var shareTitle = shareGroup.getAttribute('data-title') || document.title;

        // 微博分享：拼装分享链接，新窗口打开
        var weibo = document.getElementById('share-weibo');
        if (weibo) {
            weibo.addEventListener('click', function (e) {
                e.preventDefault();
                var url = 'https://service.weibo.com/share/share.php?url=' +
                    encodeURIComponent(shareUrl) + '&title=' + encodeURIComponent(shareTitle);
                window.open(url, '_blank', 'noopener');
            });
        }
        // Twitter(X) 分享：拼装 intent/tweet 链接，新窗口打开
        var twitter = document.getElementById('share-twitter');
        if (twitter) {
            twitter.addEventListener('click', function (e) {
                e.preventDefault();
                var url = 'https://twitter.com/intent/tweet?url=' +
                    encodeURIComponent(shareUrl) + '&text=' + encodeURIComponent(shareTitle);
                window.open(url, '_blank', 'noopener');
            });
        }
        // 复制链接：navigator.clipboard 复制当前文章地址
        var copyBtn = document.getElementById('share-copy');
        if (copyBtn) {
            copyBtn.addEventListener('click', function () {
                copyText(shareUrl).then(function () {
                    // 成功提示：按钮文字临时变为"已复制喵~"，2 秒后恢复
                    var original = copyBtn.textContent;
                    copyBtn.textContent = '✅ 已复制喵~';
                    setTimeout(function () { copyBtn.textContent = original; }, 2000);
                }).catch(function () {
                    if (window.moeToast) moeToast('复制失败了喵~请手动复制地址栏链接', 'error');
                });
            });
        }
    }

    /* ============================ 3. 代码块复制按钮 ============================ */
    var articleBody = document.getElementById('article-body');
    if (articleBody) {
        // 遍历所有 pre 代码块，在右上角插入复制按钮
        articleBody.querySelectorAll('pre').forEach(function (pre) {
            // 跳过已经加过按钮的（防止重复初始化）
            if (pre.querySelector('.code-copy-btn')) return;
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'code-copy-btn';
            btn.textContent = '复制';
            btn.addEventListener('click', function () {
                // 优先取 pre 内 code 的文本，否则直接取 pre 的文本
                var codeEl = pre.querySelector('code');
                var text = codeEl ? codeEl.textContent : pre.textContent;
                copyText(text).then(function () {
                    btn.textContent = '已复制✓';
                    btn.classList.add('copied');
                    // 2 秒后恢复按钮文字与样式
                    setTimeout(function () {
                        btn.textContent = '复制';
                        btn.classList.remove('copied');
                    }, 2000);
                }).catch(function () {
                    btn.textContent = '失败';
                });
            });
            pre.appendChild(btn);
        });
    }

    /* ============================ 工具函数 ============================ */

    /**
     * 设置页：头像上传即时预览。
     * 选择文件后用 FileReader 读取，替换圆形预览区的图片。
     */
    var avatarInput = document.getElementById('id_avatar');
    if (avatarInput) {
        avatarInput.addEventListener('change', function () {
            var file = avatarInput.files[0];
            if (!file) return;
            var reader = new FileReader();
            reader.onload = function (e) {
                var previewImg = document.getElementById('avatar-preview-img');
                var initial = document.getElementById('avatar-preview-initial');
                if (previewImg) {
                    previewImg.src = e.target.result;
                    previewImg.style.display = 'block';
                }
                if (initial) {
                    initial.style.display = 'none';
                }
            };
            reader.readAsDataURL(file);
        });
    }

    /**
     * 设置页：密码强度指示器。
     * 根据密码长度、字符种类实时计算弱/中/强。
     */
    var newPwd = document.getElementById('id_new_password');
    var strengthFill = document.getElementById('strength-fill');
    var strengthText = document.getElementById('strength-text');
    var strengthWrap = document.querySelector('.password-strength');
    if (newPwd && strengthFill && strengthText && strengthWrap) {
        newPwd.addEventListener('input', function () {
            var pwd = newPwd.value;
            var score = 0;
            if (pwd.length >= 8) score++;
            if (pwd.length >= 12) score++;
            if (/[A-Z]/.test(pwd) && /[a-z]/.test(pwd)) score++;
            if (/\d/.test(pwd)) score++;
            if (/[^A-Za-z0-9]/.test(pwd)) score++;

            // 移除旧的强度 class
            strengthWrap.classList.remove('strength-weak', 'strength-medium', 'strength-strong');
            if (!pwd) {
                strengthText.textContent = '输入密码查看强度';
                return;
            }
            if (score <= 2) {
                strengthWrap.classList.add('strength-weak');
                strengthText.textContent = '弱';
            } else if (score <= 3) {
                strengthWrap.classList.add('strength-medium');
                strengthText.textContent = '中';
            } else {
                strengthWrap.classList.add('strength-strong');
                strengthText.textContent = '强';
            }
        });
    }

    /**
     * 我的文章页：删除确认弹窗。
     * 所有带 .js-delete-confirm 的表单提交前弹出 confirm。
     */
    document.querySelectorAll('form.js-delete-confirm').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            if (form.dataset.confirmed) return;
            e.preventDefault();
            // Bug8：改为站内萌系确认弹窗；删除现为软删除，可在回收站恢复
            moeConfirm({
                message: '确定要把这篇内容收进回收站吗？之后可在审核后台的回收站恢复喵~',
                danger: true, confirmText: '收进回收站'
            }).then(function (ok) {
                if (ok) { form.dataset.confirmed = '1'; form.submit(); }
            });
        });
    });

    /**
     * 读取指定名称的 cookie（用于获取 csrftoken）。
     * @param {string} name cookie 名
     * @returns {string|null} cookie 值
     */
    function getCookie(name) {
        var arr = document.cookie.match(new RegExp('(^| )' + name + '=([^;]*)(;|$)'));
        return arr ? decodeURIComponent(arr[2]) : null;
    }

    /**
     * 兼容地复制文本到剪贴板。
     * 优先使用 navigator.clipboard（现代浏览器），失败时回退到 execCommand 方案。
     * @param {string} text 待复制文本
     * @returns {Promise<void>}
     */
    function copyText(text) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            return navigator.clipboard.writeText(text);
        }
        // 旧浏览器回退方案：创建临时 textarea 选中后执行 copy
        return new Promise(function (resolve, reject) {
            var ta = document.createElement('textarea');
            ta.value = text;
            ta.style.position = 'fixed';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            try {
                document.execCommand('copy');
                resolve();
            } catch (e) {
                reject(e);
            }
            document.body.removeChild(ta);
        });
    }
})();

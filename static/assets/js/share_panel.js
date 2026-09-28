/* Bug11 文件头注释
 * 分享面板脚本：微博/Twitter/复制链接等分享方式的弹窗与链接拼装。
 * 调用分享计数接口 F() 原子自增，并处理复制到剪贴板的降级。
 */
/**
 * share_panel.js —— 分享增强（第4轮新增）
 * 注入QQ空间分享按钮；任意分享动作 POST data-share-url 自增计数；toast提示。
 * 基础微博/Twitter/复制链接由 features.js 负责，本文件仅增强不冲突。
 */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';
    // =========================================================
    // 【函数】getCookie
    // 功能：获取「cookie」相关逻辑（get cookie）
    // 参数：
    //   - name：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function getCookie(name) {
        //> 声明变量「m」（m），用于保存对应数据，保存 DOM/窗口相关对象
        var m = document.cookie.match(new RegExp('(^| )' + name + '=([^;]*)(;|$)'));
        //> 返回结果并结束当前函数
        return m ? decodeURIComponent(m[2]) : null;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // =========================================================
    // 【函数】toast
    // 功能：处理「toast」相关逻辑（share_panel）
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
        t._timer = setTimeout(function () { t.classList.remove('show'); }, 1800);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // =========================================================
    // 【函数】bump
    // 功能：处理「bump」相关逻辑（share_panel）
    // 参数：
    //   - apiUrl：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function bump(apiUrl) {
        //> 条件判断：满足括号内条件时执行对应分支
        if (!apiUrl) return;
        //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
        fetch(apiUrl, {
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            method: 'POST',
            //> 使用 XHR 发起传统异步请求
            headers: { 'X-CSRFToken': getCookie('csrftoken'), 'X-Requested-With': 'XMLHttpRequest' },
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            credentials: 'same-origin'
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }).catch(function () {});
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    // =========================================================
    // 【函数】init
    // 功能：初始化相关逻辑（init）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function init() {
        //> 声明变量「group」（group），用于保存对应数据，保存 DOM/窗口相关对象
        var group = document.getElementById('share-group');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!group) return;
        //> 声明变量「shareUrl」（share url），用于保存对应数据
        var shareUrl = group.getAttribute('data-url') || location.href;
        //> 声明变量「shareTitle」（share title），用于保存对应数据
        var shareTitle = group.getAttribute('data-title') || document.title;
        //> 声明变量「apiUrl」（api url），用于保存对应数据
        var apiUrl = group.getAttribute('data-share-url') || group.getAttribute('data-api');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!document.getElementById('share-qzone')) {
            //> 声明变量「qz」（qz），用于保存对应数据，保存 DOM/窗口相关对象
            var qz = document.createElement('button');
            //> 给「qz.type」赋值，更新其保存的状态
            qz.type = 'button';
            //> 给「qz.id」赋值，更新其保存的状态
            qz.id = 'share-qzone';
            //> 给「qz.className」赋值，更新其保存的状态
            qz.className = 'share-btn share-qzone';
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            qz.textContent = 'QQ空间';
            //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
            qz.addEventListener('click', function (e) {
                //> 阻止事件的默认行为（如表单提交、链接跳转）
                e.preventDefault();
                //> 调用函数「bump」并传入参数执行对应逻辑
                bump(apiUrl);
                //> 操作「window」的相关方法/属性
                window.open('https://sns.qzone.qq.com/cgi-bin/qzshare/cgi_qzshare_onekey?url=' +
                    //> 对 URL 参数做编码，防止特殊字符破坏链接或被注入
                    encodeURIComponent(shareUrl) + '&title=' + encodeURIComponent(shareTitle),
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    '_blank', 'noopener,width=640,height=520');
                //> 调用函数「toast」并传入参数执行对应逻辑
                toast('分享到QQ空间喵~ ✨');
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
            //> 把子节点追加到当前元素内部末尾
            group.appendChild(qz);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        group.addEventListener('click', function (e) {
            //> 声明变量「btn」（btn），用于保存对应数据
            var btn = e.target.closest('.share-btn');
            //> 条件判断：满足括号内条件时执行对应分支
            if (!btn || btn.id === 'share-qzone') return;
            //> 调用函数「bump」并传入参数执行对应逻辑
            bump(apiUrl);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    //> 条件判断：满足括号内条件时执行对应分支
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    else init();
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

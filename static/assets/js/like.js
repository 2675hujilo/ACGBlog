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
        var m = document.cookie.match(new RegExp('(^| )' + name + '=([^;]*)'));
        //> 返回结果并结束当前函数
        return m ? decodeURIComponent(m[2]) : '';
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // =========================================================
    // 【函数】toast
    // 功能：处理「toast」相关逻辑（like）
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
        t._timer = setTimeout(function () { t.classList.remove('show'); }, 2000);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    document.addEventListener('click', function (e) {
        //> 声明变量「btn」（btn），用于保存对应数据
        var btn = e.target.closest('.like-btn');
        //> 条件判断：满足括号内条件时执行对应分支
        if (!btn || btn.disabled) return;
        //> 声明变量「id」（id），用于保存对应数据
        var id = btn.getAttribute('data-article-id') ||
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            (window.location.pathname.match(/\/article\/(\d+)/) || [])[1];
        //> 条件判断：满足括号内条件时执行对应分支
        if (!id) return;
        //> 阻止事件的默认行为（如表单提交、链接跳转）
        e.preventDefault();

        //> 给「btn.disabled」赋值，更新其保存的状态
        btn.disabled = true;
        //> 为元素添加一个或多个样式类
        btn.classList.add('loading');

        //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
        fetch('/api/article/' + id + '/like/', {
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
              //> 移除元素的一个或多个样式类
              btn.classList.remove('loading');
              //> 条件判断：满足括号内条件时执行对应分支
              if (data.success || data.liked) {
                  //> 为元素添加一个或多个样式类
                  btn.classList.add('liked', 'pop');
                  //> 声明变量「n」（n），用于保存对应数据
                  var n = btn.querySelector('.n, .like-count');
                  //> 条件判断：满足括号内条件时执行对应分支
                  if (n) n.textContent = (parseInt(n.textContent, 10) || 0) + (data.inc || 1);
                  //> 移除元素的一个或多个样式类
                  setTimeout(function () { btn.classList.remove('pop'); }, 500);
              //> 以上条件都不满足时执行的兜底分支
              } else {
                  //> 给「btn.disabled」赋值，更新其保存的状态
                  btn.disabled = false;
                  //> 调用函数「toast」并传入参数执行对应逻辑
                  toast(data.error || '\u70b9\u8d5e\u6210\u529f\u5566~');
              //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
              }
          //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
          })
          //> 该行执行对应的脚本逻辑（结合上下文理解）
          .catch(function () {
              //> 移除元素的一个或多个样式类
              btn.classList.remove('loading');
              //> 给「btn.disabled」赋值，更新其保存的状态
              btn.disabled = false;
              //> 调用函数「toast」并传入参数执行对应逻辑
              toast('\u70b9\u8d5e\u5931\u8d25\u5566\uff0c\u8bf7\u7a0d\u540e\u518d\u8bd5');
          //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
          });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

/* ============================================================================
 * reading_history_inline.js —— 浏览历史「完整列表」页渲染与清空
 * ----------------------------------------------------------------------------
 * 适用页面：浏览历史完整列表页（#rh-full-list 列表、#rh-empty 空状态、
 *          #rh-clear-all 清空按钮）。
 *
 * 数据来源：localStorage 键 'reading_history'，由前台阅读脚本写入，
 *          结构为数组，每项含 {id, title, time}（time 为毫秒时间戳）。
 *
 * 渲染：
 *   · 无历史 → 显示空状态 #rh-empty；
 *   · 有历史 → 逐条生成 <li>：标题链接到 /article/<id>/，并把时间戳格式化为
 *     相对时间（刚刚 / N 分钟前 / N 小时前 / 月-日）。
 *
 * 清空：点击 #rh-clear-all 移除 localStorage 数据后重新渲染（列表变空）。
 *
 * 安全注意：标题用 textContent 写入（而非 innerHTML），避免历史标题中的
 *          特殊字符造成 HTML 注入。
 * ----------------------------------------------------------------------------
 * 排错速查：
 *   · 数据结构固定为 [{id, title, time}]，写入端（前台阅读脚本）改动需同步本
 *     文件，否则字段缺失会渲染异常；
 *   · 标题一律 textContent 写入，杜绝历史标题中的 < 等字符造成 HTML 注入；
 *   · 相对时间分四档（刚刚 / 分钟 / 小时 / 月-日），跨月不显示年份是刻意
 *     精简，需要更精确可扩展格式；
 *   · 清空只移除本地键，不影响任何服务端数据；
 *   · 相关文件：reading_history.js（侧边栏简版，最近 5 篇）、历史完整页模板。
 * ============================================================================ */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';

    //> 声明变量「listEl」（list el），用于保存对应数据，保存 DOM/窗口相关对象
    var listEl = document.getElementById('rh-full-list');
    //> 声明变量「emptyEl」（empty el），用于保存对应数据，保存 DOM/窗口相关对象
    var emptyEl = document.getElementById('rh-empty');

    /** 读取并渲染完整浏览历史。 */
    // =========================================================
    // 【函数】load
    // 功能：加载相关逻辑（load）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function load() {
        //> 声明变量「list」（list），用于保存对应数据
        var list = [];
        //> 尝试执行可能出错的代码，出错则进入 catch
        try {
            //> 操作 localStorage（持久化本地存储），注意容量与解析异常
            list = JSON.parse(localStorage.getItem('reading_history') || '[]');
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        } catch (err) {
            // 数据损坏时按空列表处理
            //> 给「list」赋值，更新其保存的状态
            list = [];
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }

        // 每次重绘前清空列表
        //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
        listEl.innerHTML = '';

        // 无历史：显示空状态并结束
        //> 条件判断：满足括号内条件时执行对应分支
        if (!list.length) {
            //> 给「emptyEl.hidden」赋值，更新其保存的状态
            emptyEl.hidden = false;
            //> 提前结束函数，无返回值
            return;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
        //> 给「emptyEl.hidden」赋值，更新其保存的状态
        emptyEl.hidden = true;

        // 逐条渲染
        //> 遍历数组/类数组中的每一项并执行回调
        list.forEach(function (item) {
            //> 声明变量「li」（li），用于保存对应数据，保存 DOM/窗口相关对象
            var li = document.createElement('li');
            //> 给「li.className」赋值，更新其保存的状态
            li.className = 'rh-full-item';

            // 标题链接
            //> 声明变量「a」（a），用于保存对应数据，保存 DOM/窗口相关对象
            var a = document.createElement('a');
            //> 给「a.href」赋值，更新其保存的状态
            a.href = '/article/' + item.id + '/';
            //> 给「a.className」赋值，更新其保存的状态
            a.className = 'rh-full-title';
            // textContent 防注入
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            a.textContent = item.title;

            // 相对时间
            //> 声明变量「meta」（meta），用于保存对应数据，保存 DOM/窗口相关对象
            var meta = document.createElement('span');
            //> 给「meta.className」赋值，更新其保存的状态
            meta.className = 'rh-full-time muted';
            //> 声明变量「date」（date），用于保存对应数据
            var date = new Date(item.time);
            //> 声明变量「diffSec」（diff sec），用于保存对应数据，值为一个函数
            var diffSec = (Date.now() - date.getTime()) / 1000;
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            meta.textContent =
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                diffSec < 60 ? '刚刚'
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                : diffSec < 3600 ? Math.floor(diffSec / 60) + ' 分钟前'
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                : diffSec < 86400 ? Math.floor(diffSec / 3600) + ' 小时前'
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                : (date.getMonth() + 1) + '-' + date.getDate();

            //> 把子节点追加到当前元素内部末尾
            li.appendChild(a);
            //> 把子节点追加到当前元素内部末尾
            li.appendChild(meta);
            //> 把子节点追加到当前元素内部末尾
            listEl.appendChild(li);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // 清空全部历史：移除存储后重新渲染（显示空状态）
    //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    document.getElementById('rh-clear-all').addEventListener('click', function () {
        //> 操作 localStorage（持久化本地存储），注意容量与解析异常
        localStorage.removeItem('reading_history');
        //> 调用函数「load」并传入参数执行对应逻辑
        load();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    // 首次进入立即渲染
    //> 调用函数「load」并传入参数执行对应逻辑
    load();
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

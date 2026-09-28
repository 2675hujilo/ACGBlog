/* ============================================================================
 * reading_history.js —— 侧边栏「最近阅读」小组件
 * ----------------------------------------------------------------------------
 * 数据来源：localStorage 键 'reading_history'（由前台脚本在访问文章时写入），
 *          数组结构，每项 {id, title, time}，按时间倒序、已做去重与上限裁剪。
 *
 * 本组件职责（侧边栏简版，只显示最近 5 篇）：
 *   · 读取历史并渲染到 #rh-list；
 *   · 无历史时显示空状态「还没有阅读记录，去逛逛吧~」；
 *   · 每条显示标题链接与相对时间；
 *   · 点击 #rh-clear 一键清空并重新渲染。
 *
 * 完整列表页（更多条 / 相对时间）由 reading_history_inline.js 负责。
 * 安全：标题统一用 textContent 写入，防止历史标题中的字符造成注入。
 * ----------------------------------------------------------------------------
 * 排错速查：
 *   · 本组件是侧边栏「简版」，固定显示最近 5 篇；需要看更多用完整列表页
 *     （reading_history_inline.js）；
 *   · 历史写入（去重、上限裁剪、时间戳）由前台阅读相关脚本负责，本文件只读，
 *     若历史不更新应排查写入端而非本文件；
 *   · 标题用 textContent 防注入；空状态是动态 <li>，清空后会重新出现；
 *   · 清空仅删本地 'reading_history'，不涉及服务端；
 *   · 相关文件：reading_history_inline.js（完整页）、read_progress.js（位置
 *     记忆，注意两者存储键不同：reading_history vs read_progress_<id>）。
 * ============================================================================ */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';

    // 列表容器与清空按钮
    //> 声明变量「listEl」（list el），用于保存对应数据，保存 DOM/窗口相关对象
    var listEl = document.getElementById('rh-list');
    //> 声明变量「clearBtn」（clear btn），用于保存对应数据，保存 DOM/窗口相关对象
    var clearBtn = document.getElementById('rh-clear');
    // 侧边栏没有该组件则直接退出
    //> 条件判断：满足括号内条件时执行对应分支
    if (!listEl) return;

    /**
     * 把时间戳格式化为相对时间。
     * @param {Date} d - 历史记录时间。
     * @returns {string} 刚刚 / N 分钟前 / N 小时前 / 月-日。
     */
    // =========================================================
    // 【函数】formatTime
    // 功能：格式化「time」相关逻辑（format time）
    // 参数：
    //   - d：传入的参数（含义结合调用处与函数体）
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function formatTime(d) {
        //> 声明变量「now」（now），用于保存对应数据
        var now = new Date();
        // 相差秒数
        //> 声明变量「diff」（diff），用于保存对应数据，值为一个函数
        var diff = (now - d) / 1000;
        //> 条件判断：满足括号内条件时执行对应分支
        if (diff < 60) return '刚刚';
        //> 条件判断：满足括号内条件时执行对应分支
        if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前';
        //> 条件判断：满足括号内条件时执行对应分支
        if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前';
        // 超过一天显示「月-日」
        //> 返回结果并结束当前函数
        return (d.getMonth() + 1) + '-' + d.getDate();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /** 读取历史并渲染列表（最近 5 篇）。 */
    // =========================================================
    // 【函数】render
    // 功能：渲染相关逻辑（render）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function render() {
        //> 声明变量「list」（list），用于保存对应数据
        var list = [];
        //> 尝试执行可能出错的代码，出错则进入 catch
        try {
            //> 操作 localStorage（持久化本地存储），注意容量与解析异常
            list = JSON.parse(localStorage.getItem('reading_history') || '[]');
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        } catch (err) {
            // 数据损坏按空列表处理
            //> 给「list」赋值，更新其保存的状态
            list = [];
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }

        // 侧边栏只取最近 5 篇
        //> 声明变量「show」（show），用于保存对应数据
        var show = list.slice(0, 5);
        // 清空旧内容
        //> 读写元素内部 HTML；插入外部内容时有 XSS 风险，优先用 textContent
        listEl.innerHTML = '';

        // 无历史：渲染空状态并结束
        //> 条件判断：满足括号内条件时执行对应分支
        if (!show.length) {
            //> 声明变量「empty」（empty），用于保存对应数据，保存 DOM/窗口相关对象
            var empty = document.createElement('li');
            //> 给「empty.className」赋值，更新其保存的状态
            empty.className = 'muted rh-empty';
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            empty.textContent = '还没有阅读记录，去逛逛吧~';
            //> 把子节点追加到当前元素内部末尾
            listEl.appendChild(empty);
            //> 提前结束函数，无返回值
            return;
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }

        // 逐条渲染
        //> 遍历数组/类数组中的每一项并执行回调
        show.forEach(function (item) {
            //> 声明变量「li」（li），用于保存对应数据，保存 DOM/窗口相关对象
            var li = document.createElement('li');

            // 标题链接
            //> 声明变量「a」（a），用于保存对应数据，保存 DOM/窗口相关对象
            var a = document.createElement('a');
            //> 给「a.href」赋值，更新其保存的状态
            a.href = '/article/' + item.id + '/';
            // textContent 防注入
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            a.textContent = item.title;
            //> 把子节点追加到当前元素内部末尾
            li.appendChild(a);

            // 相对时间
            //> 声明变量「meta」（meta），用于保存对应数据，保存 DOM/窗口相关对象
            var meta = document.createElement('div');
            //> 给「meta.className」赋值，更新其保存的状态
            meta.className = 'rh-meta muted';
            //> 读写纯文本内容，不解析 HTML，可防 XSS
            meta.textContent = formatTime(new Date(item.time));
            //> 把子节点追加到当前元素内部末尾
            li.appendChild(meta);

            //> 把子节点追加到当前元素内部末尾
            listEl.appendChild(li);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // 绑定清空按钮：移除存储后重新渲染（显示空状态）
    //> 条件判断：满足括号内条件时执行对应分支
    if (clearBtn) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        clearBtn.addEventListener('click', function () {
            //> 操作 localStorage（持久化本地存储），注意容量与解析异常
            localStorage.removeItem('reading_history');
            //> 调用函数「render」并传入参数执行对应逻辑
            render();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // 首次进入立即渲染
    //> 调用函数「render」并传入参数执行对应逻辑
    render();
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

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
(function () {
    'use strict';

    // 列表容器与清空按钮
    var listEl = document.getElementById('rh-list');
    var clearBtn = document.getElementById('rh-clear');
    // 侧边栏没有该组件则直接退出
    if (!listEl) return;

    /**
     * 把时间戳格式化为相对时间。
     * @param {Date} d - 历史记录时间。
     * @returns {string} 刚刚 / N 分钟前 / N 小时前 / 月-日。
     */
    function formatTime(d) {
        var now = new Date();
        // 相差秒数
        var diff = (now - d) / 1000;
        if (diff < 60) return '刚刚';
        if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前';
        if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前';
        // 超过一天显示「月-日」
        return (d.getMonth() + 1) + '-' + d.getDate();
    }

    /** 读取历史并渲染列表（最近 5 篇）。 */
    function render() {
        var list = [];
        try {
            list = JSON.parse(localStorage.getItem('reading_history') || '[]');
        } catch (err) {
            // 数据损坏按空列表处理
            list = [];
        }

        // 侧边栏只取最近 5 篇
        var show = list.slice(0, 5);
        // 清空旧内容
        listEl.innerHTML = '';

        // 无历史：渲染空状态并结束
        if (!show.length) {
            var empty = document.createElement('li');
            empty.className = 'muted rh-empty';
            empty.textContent = '还没有阅读记录，去逛逛吧~';
            listEl.appendChild(empty);
            return;
        }

        // 逐条渲染
        show.forEach(function (item) {
            var li = document.createElement('li');

            // 标题链接
            var a = document.createElement('a');
            a.href = '/article/' + item.id + '/';
            // textContent 防注入
            a.textContent = item.title;
            li.appendChild(a);

            // 相对时间
            var meta = document.createElement('div');
            meta.className = 'rh-meta muted';
            meta.textContent = formatTime(new Date(item.time));
            li.appendChild(meta);

            listEl.appendChild(li);
        });
    }

    // 绑定清空按钮：移除存储后重新渲染（显示空状态）
    if (clearBtn) {
        clearBtn.addEventListener('click', function () {
            localStorage.removeItem('reading_history');
            render();
        });
    }

    // 首次进入立即渲染
    render();
})();

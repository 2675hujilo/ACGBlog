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
(function () {
    'use strict';

    var listEl = document.getElementById('rh-full-list');
    var emptyEl = document.getElementById('rh-empty');

    /** 读取并渲染完整浏览历史。 */
    function load() {
        var list = [];
        try {
            list = JSON.parse(localStorage.getItem('reading_history') || '[]');
        } catch (err) {
            // 数据损坏时按空列表处理
            list = [];
        }

        // 每次重绘前清空列表
        listEl.innerHTML = '';

        // 无历史：显示空状态并结束
        if (!list.length) {
            emptyEl.hidden = false;
            return;
        }
        emptyEl.hidden = true;

        // 逐条渲染
        list.forEach(function (item) {
            var li = document.createElement('li');
            li.className = 'rh-full-item';

            // 标题链接
            var a = document.createElement('a');
            a.href = '/article/' + item.id + '/';
            a.className = 'rh-full-title';
            // textContent 防注入
            a.textContent = item.title;

            // 相对时间
            var meta = document.createElement('span');
            meta.className = 'rh-full-time muted';
            var date = new Date(item.time);
            var diffSec = (Date.now() - date.getTime()) / 1000;
            meta.textContent =
                diffSec < 60 ? '刚刚'
                : diffSec < 3600 ? Math.floor(diffSec / 60) + ' 分钟前'
                : diffSec < 86400 ? Math.floor(diffSec / 3600) + ' 小时前'
                : (date.getMonth() + 1) + '-' + date.getDate();

            li.appendChild(a);
            li.appendChild(meta);
            listEl.appendChild(li);
        });
    }

    // 清空全部历史：移除存储后重新渲染（显示空状态）
    document.getElementById('rh-clear-all').addEventListener('click', function () {
        localStorage.removeItem('reading_history');
        load();
    });

    // 首次进入立即渲染
    load();
})();

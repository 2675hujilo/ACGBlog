/* ============================================================================
 * base_announcement_banner.js —— 顶部公告条的关闭与记忆
 * ----------------------------------------------------------------------------
 * 对应需求（Round4-C9）：公告条可被用户手动关闭，并用 localStorage 记住
 * 已关闭的公告 id，避免同一公告每次刷新都重新弹出打扰。
 *
 * 元素约定：
 *   · 容器 #announcementBanner，带 data-notice-id（公告唯一标识）；
 *   · 关闭按钮 #announcementClose。
 *
 * 存储约定：
 *   · localStorage 键 'closed_notices'，值为已关闭公告 id 的 JSON 数组。
 *
 * 逻辑：
 *   · 初始化时若当前公告 id 在已关闭列表中 → 直接隐藏；
 *   · 点击关闭 → 隐藏并把 id 追加进列表（去重）后写回。
 *
 * 注意点：JSON 解析 / 写入均包 try/catch，存储不可用时降级为「本次关闭」。
 * ----------------------------------------------------------------------------
 * 接口与存储约定（排错速查）：
 *   · localStorage 键：'closed_notices'，值为公告 id 的 JSON 字符串数组；
 *   · 公告 id 来源：容器的 data-notice-id，由后端按公告记录主键渲染；
 *   · 降级行为：localStorage 不可用时仅「本次关闭」，刷新后可能重现，属预期；
 *   · 相关文件：announcement.js（cookie 版，服务端可感知）、后端公告模型与
 *     context_processors（决定是否输出公告条）。
 *   · 注意：清空站点数据 / 换浏览器 / 换设备后关闭状态不互通（本地存储特性）。
 * ============================================================================ */
(function () {
    'use strict';

    // 取公告条与关闭按钮；任一缺失则页面无公告，直接退出
    var bar = document.getElementById('announcementBanner');
    var close = document.getElementById('announcementClose');
    if (!bar || !close) return;

    // 读取已关闭公告 id 数组（损坏 / 不存在时返回空数组）
    function readClosed() {
        try {
            return JSON.parse(localStorage.getItem('closed_notices') || '[]');
        } catch (err) {
            return [];
        }
    }

    // 初始化：当前公告已被关闭过则直接隐藏
    var closed = readClosed();
    if (closed.indexOf(bar.dataset.noticeId) >= 0) {
        bar.style.display = 'none';
    }

    // 点击关闭：隐藏并记忆
    close.addEventListener('click', function () {
        bar.style.display = 'none';
        try {
            var list = readClosed();
            // 去重后再追加当前公告 id
            if (list.indexOf(bar.dataset.noticeId) < 0) {
                list.push(bar.dataset.noticeId);
            }
            localStorage.setItem('closed_notices', JSON.stringify(list));
        } catch (err) {
            // 存储不可用时仅本次隐藏，刷新后可能重现（可接受降级）
        }
    });
})();

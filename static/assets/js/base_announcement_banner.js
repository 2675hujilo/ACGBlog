/* 62. 公告条关闭：localStorage 记录已关闭的公告 id（Round4-C9: 选择器迁移为 announcementBanner/announcementClose） */
(function () {
    var bar = document.getElementById('announcementBanner');
    var close = document.getElementById('announcementClose');
    if (!bar || !close) return;
    try {
        var closed = JSON.parse(localStorage.getItem('closed_notices') || '[]');
        if (closed.indexOf(bar.dataset.noticeId) >= 0) bar.style.display = 'none';
    } catch (e) {}
    close.addEventListener('click', function () {
        bar.style.display = 'none';
        try {
            var closed = JSON.parse(localStorage.getItem('closed_notices') || '[]');
            if (closed.indexOf(bar.dataset.noticeId) < 0) closed.push(bar.dataset.noticeId);
            localStorage.setItem('closed_notices', JSON.stringify(closed));
        } catch (e) {}
    });
})();
(function () {
    var listEl = document.getElementById('rh-full-list');
    var emptyEl = document.getElementById('rh-empty');
    function load() {
        var list = [];
        try { list = JSON.parse(localStorage.getItem('reading_history') || '[]'); }
        catch (e) { list = []; }
        listEl.innerHTML = '';
        if (!list.length) { emptyEl.hidden = false; return; }
        emptyEl.hidden = true;
        list.forEach(function (it) {
            var li = document.createElement('li');
            li.className = 'rh-full-item';
            var a = document.createElement('a');
            a.href = '/article/' + it.id + '/';
            a.className = 'rh-full-title';
            a.textContent = it.title;
            var meta = document.createElement('span');
            meta.className = 'rh-full-time muted';
            var d = new Date(it.time);
            var diff = (Date.now() - d.getTime()) / 1000;
            meta.textContent = diff < 60 ? '刚刚'
                : diff < 3600 ? Math.floor(diff / 60) + ' 分钟前'
                : diff < 86400 ? Math.floor(diff / 3600) + ' 小时前'
                : (d.getMonth() + 1) + '-' + d.getDate();
            li.appendChild(a); li.appendChild(meta);
            listEl.appendChild(li);
        });
    }
    document.getElementById('rh-clear-all').addEventListener('click', function () {
        localStorage.removeItem('reading_history');
        load();
    });
    load();
})();
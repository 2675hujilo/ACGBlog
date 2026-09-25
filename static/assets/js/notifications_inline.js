(function () {
    function csrfToken() {
        var m = document.cookie.match(/csrftoken=([^;]+)/);
        return m ? m[1] : '';
    }
    function markRead(id) {
        return fetch('/api/notifications/' + id + '/read/', {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken() },
            credentials: 'same-origin'
        });
    }
    document.querySelectorAll('.notif-center-item').forEach(function (item) {
        function activate() {
            var url = item.dataset.url;
            var done = function () { if (url) window.location.href = url; else window.location.reload(); };
            if (item.dataset.read === 'false') {
                markRead(item.dataset.id).then(done).catch(done);
            } else { done(); }
        }
        item.addEventListener('click', activate);
        item.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); activate(); }
        });
    });
    var all = document.getElementById('notif-mark-all');
    if (all) {
        all.addEventListener('click', function () {
            fetch('/api/notifications/read_all/', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken() },
                credentials: 'same-origin'
            }).then(function () { window.location.reload(); });
        });
    }
})();
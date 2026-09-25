if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
        navigator.serviceWorker.register('/static/sw.js').then(function (reg) {
            // 主动检查 sw.js 更新；发现新版本（waiting）立即激活并刷新一次
            reg.update();
            function applyWaiting(w) { if (w) w.postMessage({ type: 'SKIP_WAITING' }); }
            applyWaiting(reg.waiting);
            reg.addEventListener('updatefound', function () {
                var nw = reg.installing;
                if (nw) nw.addEventListener('statechange', function () {
                    if (nw.state === 'installed') applyWaiting(nw);
                });
            });
            var reloaded = false;
            navigator.serviceWorker.addEventListener('controllerchange', function () {
                if (!reloaded) { reloaded = true; window.location.reload(); }
            });
        }).catch(function (e) {
            console.warn('SW 注册失败：', e);
        });
    });
}
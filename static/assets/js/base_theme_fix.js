/* 防闪烁：渲染前确定明暗主题 */
    (function () {
        try {
            var t = localStorage.getItem('theme') ||
                (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
            document.documentElement.setAttribute('data-theme', t);
        } catch (e) { document.documentElement.setAttribute('data-theme', 'light'); }
    })();
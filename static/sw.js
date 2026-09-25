/* sw.js —— 萌语博客 Service Worker
 * 策略（v2 修复版）：
 *   - install 时预缓存核心静态资源；
 *   - activate 时清理旧版本缓存（v1 等全部删除）；
 *   - fetch 时：静态资源走"stale-while-revalidate"（立即返回缓存，后台更新），
 *     确保用户总能拿到最新版本；HTML / API 走"网络优先"。
 * v2 变更：缓存名升级 mengyu-v2，静态策略从 cache-first 改为 stale-while-revalidate，
 *   修复静态资源更新后浏览器仍加载旧缓存导致页面空白的问题。
 * v3 变更：缓存名升级 mengyu-v3，支持页面 postMessage('SKIP_WAITING') 即时激活，
 *   HTML 导航请求严格网络优先（带查询参数的页面也不命中旧缓存），杜绝模板更新不生效。
 */
var CACHE_NAME = 'mengyu-v3';
var CORE_ASSETS = [
    '/static/assets/css/base.css',
    '/static/assets/css/components.css',
    '/static/assets/css/blog.css',
    '/static/assets/css/enhance.css',
    '/static/assets/js/common.js',
    '/static/assets/js/theme.js',
    '/static/manifest.json'
];

/* 安装：预缓存核心静态资源，立即接管 */
self.addEventListener('install', function (event) {
    event.waitUntil(
        caches.open(CACHE_NAME).then(function (cache) {
            return cache.addAll(CORE_ASSETS).catch(function () {
                /* 预缓存失败不阻断安装（某些资源可能暂时不可用） */
            });
        }).then(function () {
            return self.skipWaiting();
        })
    );
});

/* 激活：删除所有旧版本缓存（只保留当前 CACHE_NAME） */
self.addEventListener('activate', function (event) {
    event.waitUntil(
        caches.keys().then(function (keys) {
            return Promise.all(keys.map(function (key) {
                if (key !== CACHE_NAME) return caches.delete(key);
            }));
        }).then(function () {
            return self.clients.claim();
        })
    );
});

/* 接收页面指令：SKIP_WAITING 时立即激活新版本（配合 base.html 的更新提示） */
self.addEventListener('message', function (event) {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

/* 拦截请求 */
self.addEventListener('fetch', function (event) {
    var url = new URL(event.request.url);
    /* 仅处理同源 GET 请求；跨域（CDN/字体）与非 GET 不干预 */
    if (event.request.method !== 'GET' || url.origin !== self.location.origin) return;

    var isStatic = url.pathname.startsWith('/static/');
    var isApi = url.pathname.startsWith('/api/');

    if (isApi) {
        /* API：网络优先，失败则返回空 JSON */
        event.respondWith(fetch(event.request).catch(function () {
            return new Response('{}', { headers: { 'Content-Type': 'application/json' } });
        }));
    } else if (isStatic) {
        /* 静态资源：stale-while-revalidate
         * 立即返回缓存（如果有），同时后台 fetch 最新版本并更新缓存。
         * 这样用户既能秒开，又能在下次访问拿到最新版本。
         */
        event.respondWith(
            caches.open(CACHE_NAME).then(function (cache) {
                return cache.match(event.request).then(function (cached) {
                    var networkFetch = fetch(event.request).then(function (resp) {
                        if (resp && resp.status === 200) {
                            cache.put(event.request, resp.clone());
                        }
                        return resp;
                    }).catch(function () {
                        return cached;
                    });
                    return cached || networkFetch;
                });
            })
        );
    } else {
        /* HTML 页面：网络优先，离线回退缓存 */
        event.respondWith(
            fetch(event.request).then(function (resp) {
                var copy = resp.clone();
                caches.open(CACHE_NAME).then(function (cache) {
                    cache.put(event.request, copy);
                });
                return resp;
            }).catch(function () {
                return caches.match(event.request);
            })
        );
    }
});

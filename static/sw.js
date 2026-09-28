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
//> 声明变量「CACHE_NAME」（cache name），用于保存对应数据，初始为字符串
var CACHE_NAME = 'mengyu-v3';
//> 声明变量「CORE_ASSETS」（core assets），用于保存对应数据
var CORE_ASSETS = [
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    '/static/assets/css/base.css',
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    '/static/assets/css/components.css',
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    '/static/assets/css/blog.css',
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    '/static/assets/css/enhance.css',
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    '/static/assets/js/common.js',
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    '/static/assets/js/theme.js',
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    '/static/manifest.json'
//> 该行执行对应的脚本逻辑（结合上下文理解）
];

/* 安装：预缓存核心静态资源，立即接管 */
//> 绑定「install」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
self.addEventListener('install', function (event) {
    //> 操作「event」的相关方法/属性
    event.waitUntil(
        //> 操作「caches」的相关方法/属性
        caches.open(CACHE_NAME).then(function (cache) {
            //> 返回结果并结束当前函数
            return cache.addAll(CORE_ASSETS).catch(function () {
                /* 预缓存失败不阻断安装（某些资源可能暂时不可用） */
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            });
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }).then(function () {
            //> 返回结果并结束当前函数
            return self.skipWaiting();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        })
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    );
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
});

/* 激活：删除所有旧版本缓存（只保留当前 CACHE_NAME） */
//> 绑定「activate」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
self.addEventListener('activate', function (event) {
    //> 操作「event」的相关方法/属性
    event.waitUntil(
        //> 操作「caches」的相关方法/属性
        caches.keys().then(function (keys) {
            //> 返回结果并结束当前函数
            return Promise.all(keys.map(function (key) {
                //> 条件判断：满足括号内条件时执行对应分支
                if (key !== CACHE_NAME) return caches.delete(key);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }));
        //> 该行执行对应的脚本逻辑（结合上下文理解）
        }).then(function () {
            //> 返回结果并结束当前函数
            return self.clients.claim();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        })
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    );
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
});

/* 接收页面指令：SKIP_WAITING 时立即激活新版本（配合 base.html 的更新提示） */
//> 绑定「message」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
self.addEventListener('message', function (event) {
    //> 条件判断：满足括号内条件时执行对应分支
    if (event.data && event.data.type === 'SKIP_WAITING') {
        //> 操作「self」的相关方法/属性
        self.skipWaiting();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
});

/* 拦截请求 */
//> 绑定「fetch」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
self.addEventListener('fetch', function (event) {
    //> 声明变量「url」（url），用于保存对应数据
    var url = new URL(event.request.url);
    /* 仅处理同源 GET 请求；跨域（CDN/字体）与非 GET 不干预 */
    //> 条件判断：满足括号内条件时执行对应分支
    if (event.request.method !== 'GET' || url.origin !== self.location.origin) return;

    //> 声明变量「isStatic」（is static），用于保存对应数据
    var isStatic = url.pathname.startsWith('/static/');
    //> 声明变量「isApi」（is api），用于保存对应数据
    var isApi = url.pathname.startsWith('/api/');

    //> 条件判断：满足括号内条件时执行对应分支
    if (isApi) {
        /* API：网络优先，失败则返回空 JSON */
        //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
        event.respondWith(fetch(event.request).catch(function () {
            //> 返回结果并结束当前函数
            return new Response('{}', { headers: { 'Content-Type': 'application/json' } });
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }));
    //> 否则若满足该条件则进入此分支
    } else if (isStatic) {
        /* 静态资源：stale-while-revalidate
         * 立即返回缓存（如果有），同时后台 fetch 最新版本并更新缓存。
         * 这样用户既能秒开，又能在下次访问拿到最新版本。
         */
        //> 操作「event」的相关方法/属性
        event.respondWith(
            //> 操作「caches」的相关方法/属性
            caches.open(CACHE_NAME).then(function (cache) {
                //> 返回结果并结束当前函数
                return cache.match(event.request).then(function (cached) {
                    //> 声明变量「networkFetch」（network fetch），用于保存对应数据
                    var networkFetch = fetch(event.request).then(function (resp) {
                        //> 条件判断：满足括号内条件时执行对应分支
                        if (resp && resp.status === 200) {
                            //> 操作「cache」的相关方法/属性
                            cache.put(event.request, resp.clone());
                        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                        }
                        //> 返回结果并结束当前函数
                        return resp;
                    //> 该行执行对应的脚本逻辑（结合上下文理解）
                    }).catch(function () {
                        //> 返回结果并结束当前函数
                        return cached;
                    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                    });
                    //> 返回结果并结束当前函数
                    return cached || networkFetch;
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                });
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            })
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        );
    //> 以上条件都不满足时执行的兜底分支
    } else {
        /* HTML 页面：网络优先，离线回退缓存 */
        //> 操作「event」的相关方法/属性
        event.respondWith(
            //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
            fetch(event.request).then(function (resp) {
                //> 声明变量「copy」（copy），用于保存对应数据
                var copy = resp.clone();
                //> 操作「caches」的相关方法/属性
                caches.open(CACHE_NAME).then(function (cache) {
                    //> 操作「cache」的相关方法/属性
                    cache.put(event.request, copy);
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                });
                //> 返回结果并结束当前函数
                return resp;
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }).catch(function () {
                //> 返回结果并结束当前函数
                return caches.match(event.request);
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            })
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        );
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
});

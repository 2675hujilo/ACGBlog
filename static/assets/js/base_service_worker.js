/* ============================================================================
 * base_service_worker.js —— Service Worker 注册与「即时更新」
 * ----------------------------------------------------------------------------
 * 作用：在页面 load 后注册 /static/sw.js（PWA 离线缓存、资源预缓存）。
 *
 * 更新策略（重点，避免老用户卡在旧缓存）：
 *   · 注册后立即 reg.update() 主动拉取一次 sw.js，检查是否有新版本；
 *   · 监听 updatefound：新 SW 安装完成（installed / waiting）后，
 *     通过 postMessage({type:'SKIP_WAITING'}) 让其跳过等待、立即激活；
 *   · 监听 controllerchange：新 SW 接管后自动 reload 一次，让页面用上新缓存；
 *     用 reloaded 标志保证只刷新一次，避免刷新循环。
 *
 * 注意点：
 *   · 仅在 navigator.serviceWorker 存在时执行（现代浏览器 / 安全上下文 https
 *     或 localhost；旧浏览器自动跳过）；
 *   · 放在 load 事件里注册，避免与首屏关键资源竞争；
 *   · 注册失败只 console.warn，不影响正常浏览。
 * ----------------------------------------------------------------------------
 * 排错速查：
 *   · SW 仅在安全上下文（https 或 localhost/127.0.0.1）可用，http 局域网 IP
 *     下注册失败属正常，代码已用能力检测与 catch 兜底；
 *   · 更新闭环：update → updatefound → worker installed → postMessage
 *     SKIP_WAITING → controllerchange → reload；reloaded 标志防止刷新死循环；
 *   · 真正的缓存清单与 SKIP_WAITING 响应逻辑在 /static/sw.js，不在本文件；
 *   · 调试可用浏览器 Application/Service Workers 面板，或 self.registration；
 *   · 改了 sw.js 后老客户端也会在下次 load 时 update 并自动接管，无需手动卸载。
 * ============================================================================ */
// 能力检测：不支持 SW 的浏览器直接跳过整段
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
        navigator.serviceWorker.register('/static/sw.js').then(function (reg) {
            // 主动检查 sw.js 更新
            reg.update();

            // 让处于 waiting 的新 SW 立即跳过等待、进入激活
            function applyWaiting(worker) {
                if (worker) worker.postMessage({ type: 'SKIP_WAITING' });
            }
            applyWaiting(reg.waiting);

            // 发现新 SW 正在安装：等其 installed 后通知跳过等待
            reg.addEventListener('updatefound', function () {
                var newWorker = reg.installing;
                if (newWorker) {
                    newWorker.addEventListener('statechange', function () {
                        if (newWorker.state === 'installed') {
                            applyWaiting(newWorker);
                        }
                    });
                }
            });

            // 新 SW 接管页面 → 刷新一次以加载新缓存（仅一次）
            var reloaded = false;
            navigator.serviceWorker.addEventListener('controllerchange', function () {
                if (!reloaded) {
                    reloaded = true;
                    window.location.reload();
                }
            });
        }).catch(function (err) {
            // 注册失败（如安全上下文限制）仅告警，不影响站点功能
            console.warn('SW 注册失败：', err);
        });
    });
}

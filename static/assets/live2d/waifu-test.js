/* 简化测试版本 - 直接执行 */
(function () {
    try {
        console.log('[Waifu Test] JS loaded, executing directly');
        var w = document.createElement('div');
        w.id = 'waifu-test';
        w.style.cssText = 'position:fixed;right:20px;bottom:20px;z-index:2147483647;width:200px;height:200px;background:linear-gradient(135deg,#f0abfc,#e879f9);border-radius:20px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:20px;';
        w.textContent = '看板娘测试';
        document.body.appendChild(w);
        console.log('[Waifu Test] element added successfully');
    } catch (e) {
        console.error('[Waifu Test] error:', e);
    }
})();
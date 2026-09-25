/* Bug11 文件头注释
 * Live2D 初始化入口：加载 PIXI 与 Live2D 运行时、拉取模型资源并挂载舞台。
 */
/* ============================================================
   Live2D 看板娘初始化脚本
   基于 stevenjoezhang/live2d-widget，加载本地模型
   ============================================================ */
(function () {
    'use strict';

    // 调试：把错误写到页面上
    window.addEventListener('error', function (e) {
        var debug = document.getElementById('waifu-debug');
        if (!debug) {
            debug = document.createElement('div');
            debug.id = 'waifu-debug';
            debug.style.cssText = 'position:fixed;top:10px;left:10px;background:#fff;color:#f00;padding:10px;z-index:999999;font-size:12px;max-width:400px;word-break:break-all;';
            document.body.appendChild(debug);
        }
        debug.innerHTML += '<br>ERROR: ' + e.message + ' @ ' + e.filename + ':' + e.lineno;
    });

    var MODEL_PATH = '/static/assets/live2d/models/shizuku/shizuku.model.json';
    var tipsTimer = null;

    console.log('[Live2D] init script loaded');
    console.log('[Live2D] loadlive2d exists:', typeof loadlive2d);

    var DIALOGUES = {
        click: ['喵~你摸到人家了啦~', '唔！不要随便摸啦！', '哼哼，本喵可是很可爱的哦~', '再摸我就要生气了哦！', '喵呜~好舒服喵~'],
        welcome: ['欢迎回来喵~今天也要开心哦！', '喵呜~你来啦！人家等你好久了~'],
        idle: ['喵~有点无聊呢，陪人家玩嘛~', '你在看什么呢？人家也想看~']
    };

    function randomPick(arr) { return arr[Math.floor(Math.random() * arr.length)]; }

    function showTips(text, duration) {
        var tips = document.getElementById('waifu-tips');
        if (!tips) return;
        tips.innerHTML = text;
        tips.classList.add('waifu-tips-active');
        if (tipsTimer) clearTimeout(tipsTimer);
        tipsTimer = setTimeout(function () { tips.classList.remove('waifu-tips-active'); }, duration || 4000);
    }

    function initWidget() {
        console.log('[Live2D] initWidget called');
        try {
            var waifu = document.createElement('div');
            waifu.id = 'waifu';
            waifu.innerHTML =
                '<div id="waifu-tips"></div>' +
                '<canvas id="live2d" width="800" height="800"></canvas>' +
                '<div id="waifu-tool">' +
                    '<span id="waifu-tool-quit" title="隐藏">✕</span>' +
                '</div>';
            document.body.appendChild(waifu);
            console.log('[Live2D] waifu element created');

            setTimeout(function () { waifu.style.bottom = '0'; }, 100);

            if (typeof loadlive2d === 'function') {
                console.log('[Live2D] loading model: ' + MODEL_PATH);
                loadlive2d('live2d', MODEL_PATH);
            } else {
                console.error('[Live2D] loadlive2d not found');
                showTips('模型加载失败喵...', 3000);
            }

            setTimeout(function () { showTips(randomPick(DIALOGUES.welcome), 5000); }, 2000);

            var canvas = document.getElementById('live2d');
            if (canvas) {
                canvas.addEventListener('click', function () { showTips(randomPick(DIALOGUES.click), 3000); });
            }

            var quitBtn = document.getElementById('waifu-tool-quit');
            if (quitBtn) {
                quitBtn.addEventListener('click', function () {
                    waifu.style.bottom = '-500px';
                    setTimeout(function () { waifu.style.display = 'none'; }, 500);
                });
            }
        } catch (e) {
            console.error('[Live2D] init error:', e);
            var debug = document.getElementById('waifu-debug');
            if (debug) debug.innerHTML += '<br>INIT ERROR: ' + e.message;
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initWidget);
    } else {
        initWidget();
    }
})();

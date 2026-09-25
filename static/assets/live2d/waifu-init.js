/* Bug11 文件头注释
 * 看板娘初始化（旧版）：模型加载、提示语与工具栏事件绑定。
 */
/* ============================================================
   Live2D 看板娘初始化脚本
   参考 fghrsh/live2d_api 接口规范 + stevenjoezhang/live2d-widget
   功能：模型切换、皮肤切换、猜拳小游戏、拍照、对话
   ============================================================ */
(function () {
    'use strict';

    // API基础路径
    var API_BASE = '/api/live2d';

    // 当前状态
    var state = {
        modelId: 'shizuku',
        modelName: '雫',
        skin: 0,
        skinCount: 6
    };

    // 从localStorage恢复状态
    try {
        var saved = localStorage.getItem('live2d_state');
        if (saved) {
            var s = JSON.parse(saved);
            state.modelId = s.modelId || 'shizuku';
            state.skin = s.skin || 0;
        }
    } catch (e) {}

    var tipsTimer = null;
    var welcomeTimer = null;
    var gameModal = null;

    // 对话文案
    var DIALOGUES = {
        click: ['喵~你摸到人家了啦~', '唔！不要随便摸啦！', '哼哼，本喵可是很可爱的哦~', '再摸我就要生气了哦！', '喵呜~好舒服喵~'],
        welcome: ['欢迎回来喵~今天也要开心哦！', '喵呜~你来啦！人家等你好久了~'],
        photo: ['咔嚓~拍好啦！', '人家今天也很可爱呢~', '拍照要记得微笑哦~'],
        game: ['来玩猜拳吧喵~', '人家可是猜拳高手哦！', '敢和人家比试比试吗？']
    };

    function rp(a) { return a[Math.floor(Math.random() * a.length)]; }

    function saveState() {
        try {
            localStorage.setItem('live2d_state', JSON.stringify({
                modelId: state.modelId,
                skin: state.skin
            }));
        } catch (e) {}
    }

    function st(t, d) {
        var el = document.getElementById('waifu-tips');
        if (!el) return;
        el.innerHTML = t;
        el.style.opacity = '1';
        if (tipsTimer) clearTimeout(tipsTimer);
        tipsTimer = setTimeout(function () { el.style.opacity = '0'; }, d || 4000);
    }

    // 加载模型（重建canvas确保旧模型完全清理）
    function loadModel(modelUrl, callback) {
        if (typeof loadlive2d !== 'function') {
            st('Live2D引擎未加载喵~', 3000);
            return;
        }
        try {
            console.log('[Waifu] loadModel:', modelUrl);
            var oldCanvas = document.getElementById('live2d');
            if (oldCanvas && oldCanvas.parentNode) {
                var parent = oldCanvas.parentNode;
                var width = oldCanvas.width || 800;
                var height = oldCanvas.height || 800;
                var styleText = oldCanvas.style.cssText || 'width:220px;height:250px;position:absolute;bottom:0;left:0;cursor:pointer;';
                parent.removeChild(oldCanvas);
                var newCanvas = document.createElement('canvas');
                newCanvas.id = 'live2d';
                newCanvas.width = width;
                newCanvas.height = height;
                newCanvas.style.cssText = styleText;
                parent.appendChild(newCanvas);
            }
            loadlive2d('live2d', modelUrl);
            if (callback) callback();
        } catch (e) {
            console.error('[Waifu] loadlive2d error:', e);
            st('模型加载出错: ' + e.message, 5000);
        }
    }

    // 切换模型（顺序）
    function switchModel() {
        var staticPaths = {
            'shizuku': { path: '/static/assets/live2d/models/shizuku/shizuku.model.json', name: '雫', skins: 6 },
            'shizuku_talk': { path: '/static/assets/live2d/models/shizuku_talk/shizuku-48/index.json', name: '雫Talk', skins: 2 },
            'koharu': { path: '/static/assets/live2d/models/koharu/koharu.model.json', name: '小春', skins: 1 },
            'haru': { path: '/static/assets/live2d/models/haru/haru01.model.json', name: '春', skins: 3 },
            'hijiki': { path: '/static/assets/live2d/models/hijiki/hijiki.model.json', name: '黑猫', skins: 1 },
            'tororo': { path: '/static/assets/live2d/models/tororo/tororo.model.json', name: '白猫', skins: 1 },
            'wanko': { path: '/static/assets/live2d/models/wanko/wanko.model.json', name: '狗狗', skins: 1 },
            'hibiki': { path: '/static/assets/live2d/models/hibiki/hibiki.model.json', name: '响', skins: 1 },
            'izumi': { path: '/static/assets/live2d/models/izumi/izumi.model.json', name: '泉', skins: 1 },
            'tsumiki': { path: '/static/assets/live2d/models/tsumiki/tsumiki.model.json', name: '积木', skins: 1 },
            'chitose': { path: '/static/assets/live2d/models/chitose/chitose.model.json', name: '千岁', skins: 1 },
            'haruto': { path: '/static/assets/live2d/models/haruto/haruto.model.json', name: '春人', skins: 1 },
            'miku': { path: '/static/assets/live2d/models/miku/miku.model.json', name: '初音', skins: 1 },
            'ni-j': { path: '/static/assets/live2d/models/ni-j/ni-j.model.json', name: '仁藤', skins: 1 },
            'nico': { path: '/static/assets/live2d/models/nico/nico.model.json', name: '妮可', skins: 1 },
            'nipsilon': { path: '/static/assets/live2d/models/nipsilon/nipsilon.model.json', name: '尼普西隆', skins: 1 },
            'nito': { path: '/static/assets/live2d/models/nito/nito.model.json', name: '仁斗', skins: 1 },
            'unitychan': { path: '/static/assets/live2d/models/unitychan/unitychan.model.json', name: 'Unity娘', skins: 1 },
            'z16': { path: '/static/assets/live2d/models/z16/z16.model.json', name: '小可爱', skins: 1 },
        };
        var ids = ['shizuku', 'shizuku_talk', 'koharu', 'haru', 'hijiki', 'tororo', 'wanko', 'hibiki', 'izumi', 'tsumiki', 'chitose', 'haruto', 'miku', 'ni-j', 'nico', 'nipsilon', 'nito', 'unitychan', 'z16'];
        var currentIdx = ids.indexOf(state.modelId);
        var nextIdx = (currentIdx + 1) % ids.length;
        var nextId = ids[nextIdx];
        var next = staticPaths[nextId];
        state.modelId = nextId;
        state.modelName = next.name;
        state.skin = 0;
        state.skinCount = next.skins;
        saveState();
        loadModel(next.path);
        st(next.name + '~ 换好新造型啦~', 4000);
    }

    // 随机切换模型
    function randModel() {
        var staticPaths = {
            'shizuku': { path: '/static/assets/live2d/models/shizuku/shizuku.model.json', name: '雫', skins: 6 },
            'shizuku_talk': { path: '/static/assets/live2d/models/shizuku_talk/shizuku-48/index.json', name: '雫Talk', skins: 2 },
            'koharu': { path: '/static/assets/live2d/models/koharu/koharu.model.json', name: '小春', skins: 1 },
            'haru': { path: '/static/assets/live2d/models/haru/haru01.model.json', name: '春', skins: 3 },
            'hijiki': { path: '/static/assets/live2d/models/hijiki/hijiki.model.json', name: '黑猫', skins: 1 },
            'tororo': { path: '/static/assets/live2d/models/tororo/tororo.model.json', name: '白猫', skins: 1 },
            'wanko': { path: '/static/assets/live2d/models/wanko/wanko.model.json', name: '狗狗', skins: 1 },
            'hibiki': { path: '/static/assets/live2d/models/hibiki/hibiki.model.json', name: '响', skins: 1 },
            'izumi': { path: '/static/assets/live2d/models/izumi/izumi.model.json', name: '泉', skins: 1 },
            'tsumiki': { path: '/static/assets/live2d/models/tsumiki/tsumiki.model.json', name: '积木', skins: 1 },
            'chitose': { path: '/static/assets/live2d/models/chitose/chitose.model.json', name: '千岁', skins: 1 },
            'haruto': { path: '/static/assets/live2d/models/haruto/haruto.model.json', name: '春人', skins: 1 },
            'miku': { path: '/static/assets/live2d/models/miku/miku.model.json', name: '初音', skins: 1 },
            'ni-j': { path: '/static/assets/live2d/models/ni-j/ni-j.model.json', name: '仁藤', skins: 1 },
            'nico': { path: '/static/assets/live2d/models/nico/nico.model.json', name: '妮可', skins: 1 },
            'nipsilon': { path: '/static/assets/live2d/models/nipsilon/nipsilon.model.json', name: '尼普西隆', skins: 1 },
            'nito': { path: '/static/assets/live2d/models/nito/nito.model.json', name: '仁斗', skins: 1 },
            'unitychan': { path: '/static/assets/live2d/models/unitychan/unitychan.model.json', name: 'Unity娘', skins: 1 },
            'z16': { path: '/static/assets/live2d/models/z16/z16.model.json', name: '小可爱', skins: 1 },
        };
        var ids = ['shizuku', 'shizuku_talk', 'koharu', 'haru', 'hijiki', 'tororo', 'wanko', 'hibiki', 'izumi', 'tsumiki', 'chitose', 'haruto', 'miku', 'ni-j', 'nico', 'nipsilon', 'nito', 'unitychan', 'z16'];
        var available = ids.filter(function(id) { return id !== state.modelId; });
        var nextId = available[Math.floor(Math.random() * available.length)];
        var next = staticPaths[nextId];
        state.modelId = nextId;
        state.modelName = next.name;
        state.skin = 0;
        state.skinCount = next.skins;
        saveState();
        loadModel(next.path);
        st(next.name + '~ 惊喜！换了个新朋友~', 4000);
    }

    // 切换皮肤（顺序）
    function switchSkin() {
        // 皮肤配置：模型ID -> 皮肤JSON路径和数量
        var skinConfigs = {
            'shizuku': { count: 6, base: '/static/assets/live2d/models/shizuku/shizuku_skin_' },
            'shizuku_talk': { count: 2, skins: [
                '/static/assets/live2d/models/shizuku_talk/shizuku-48/index.json',
                '/static/assets/live2d/models/shizuku_talk/shizuku-pajama/index.json'
            ]},
            'koharu': { count: 1 },
            'haru': { count: 3, base: '/static/assets/live2d/models/haru/haru_skin_' },
            'hijiki': { count: 1 },
            'tororo': { count: 1 },
            'wanko': { count: 1 },
            'hibiki': { count: 1 },
            'izumi': { count: 1 },
            'tsumiki': { count: 1 },
            'chitose': { count: 1 },
            'haruto': { count: 1 },
            'miku': { count: 1 },
            'ni-j': { count: 1 },
            'nico': { count: 1 },
            'nipsilon': { count: 1 },
            'nito': { count: 1 },
            'unitychan': { count: 1 },
            'z16': { count: 1 },
        };
        var cfg = skinConfigs[state.modelId];
        if (!cfg || cfg.count <= 1) {
            st('这个角色只有一套衣服喵~', 3000);
            return;
        }
        state.skin = (state.skin + 1) % cfg.count;
        saveState();
        var skinUrl = cfg.skins ? cfg.skins[state.skin] : (cfg.base + state.skin + '.json');
        console.log('[Waifu] switchSkin:', state.modelId, 'skin:', state.skin, 'url:', skinUrl);
        loadModel(skinUrl);
        var skinNames = {
            'shizuku_talk': ['日常服', '睡衣']
        };
        var skinName = (skinNames[state.modelId] && skinNames[state.modelId][state.skin]) || ('皮肤' + (state.skin + 1));
        st('新衣服：' + skinName + '喵~（' + (state.skin + 1) + '/' + cfg.count + '）', 4000);
    }

    // 随机切换皮肤
    function randSkin() {
        var skinConfigs = {
            'shizuku': { count: 6, base: '/static/assets/live2d/models/shizuku/shizuku_skin_' },
            'shizuku_talk': { count: 2, skins: [
                '/static/assets/live2d/models/shizuku_talk/shizuku-48/index.json',
                '/static/assets/live2d/models/shizuku_talk/shizuku-pajama/index.json'
            ]},
            'koharu': { count: 1 },
            'haru': { count: 3, base: '/static/assets/live2d/models/haru/haru_skin_' },
            'hijiki': { count: 1 },
            'tororo': { count: 1 },
            'wanko': { count: 1 },
            'hibiki': { count: 1 },
            'izumi': { count: 1 },
            'tsumiki': { count: 1 },
            'chitose': { count: 1 },
            'haruto': { count: 1 },
            'miku': { count: 1 },
            'ni-j': { count: 1 },
            'nico': { count: 1 },
            'nipsilon': { count: 1 },
            'nito': { count: 1 },
            'unitychan': { count: 1 },
            'z16': { count: 1 },
        };
        var cfg = skinConfigs[state.modelId];
        if (!cfg || cfg.count <= 1) {
            st('这个角色只有一套衣服喵~', 3000);
            return;
        }
        var available = [];
        for (var i = 0; i < cfg.count; i++) {
            if (i !== state.skin) available.push(i);
        }
        state.skin = available[Math.floor(Math.random() * available.length)];
        saveState();
        var skinUrl = cfg.skins ? cfg.skins[state.skin] : (cfg.base + state.skin + '.json');
        loadModel(skinUrl);
        st('惊喜！新衣服~（皮肤' + (state.skin + 1) + '/' + cfg.count + '）', 4000);
    }

    // 猜拳小游戏
    function playGame() {
        if (gameModal) {
            gameModal.remove();
            gameModal = null;
            return;
        }

        // 创建游戏弹窗
        gameModal = document.createElement('div');
        gameModal.id = 'waifu-game-modal';
        gameModal.style.cssText = 'position:fixed;right:260px;bottom:280px;z-index:2147483647;background:linear-gradient(135deg,#fff,#fdf4ff);border:2px solid #e9d5ff;border-radius:20px;padding:20px;box-shadow:0 8px 30px rgba(168,85,247,0.3);width:240px;text-align:center;animation:waifuFadeIn 0.3s ease;';
        gameModal.innerHTML =
            '<div style="font-size:16px;font-weight:bold;color:#6b21a8;margin-bottom:12px;">🎮 猜拳大作战</div>' +
            '<div id="waifu-game-result" style="font-size:14px;color:#8b5cf6;margin-bottom:15px;min-height:40px;">选择你的出招喵~</div>' +
            '<div style="display:flex;justify-content:center;gap:12px;">' +
                '<button data-choice="石头" style="width:56px;height:56px;border-radius:50%;border:2px solid #e9d5ff;background:#fff;font-size:24px;cursor:pointer;transition:all 0.2s;">✊</button>' +
                '<button data-choice="剪刀" style="width:56px;height:56px;border-radius:50%;border:2px solid #e9d5ff;background:#fff;font-size:24px;cursor:pointer;transition:all 0.2s;">✌️</button>' +
                '<button data-choice="布" style="width:56px;height:56px;border-radius:50%;border:2px solid #e9d5ff;background:#fff;font-size:24px;cursor:pointer;transition:all 0.2s;">🖐️</button>' +
            '</div>' +
            '<button id="waifu-game-close" style="margin-top:12px;background:none;border:none;color:#a855f7;cursor:pointer;font-size:12px;">关闭</button>';

        document.body.appendChild(gameModal);

        // 按钮hover效果
        var btns = gameModal.querySelectorAll('button[data-choice]');
        for (var i = 0; i < btns.length; i++) {
            btns[i].addEventListener('mouseenter', function () {
                this.style.transform = 'scale(1.15)';
                this.style.borderColor = '#a855f7';
                this.style.background = '#faf5ff';
            });
            btns[i].addEventListener('mouseleave', function () {
                this.style.transform = 'scale(1)';
                this.style.borderColor = '#e9d5ff';
                this.style.background = '#fff';
            });
            btns[i].addEventListener('click', function () {
                var choice = this.dataset.choice;
                var resultEl = document.getElementById('waifu-game-result');
                resultEl.innerHTML = '出招中...';

                fetch(API_BASE + '/game/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
                    body: JSON.stringify({ choice: choice })
                })
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        var emoji = { '石头': '✊', '剪刀': '✌️', '布': '🖐️' };
                        var resultColor = data.result === '胜利' ? '#22c55e' : (data.result === '失败' ? '#ef4444' : '#f59e0b');
                        resultEl.innerHTML =
                            '你：' + emoji[data.user_choice] + ' vs ' + emoji[data.waifu_choice] + '：看板娘<br>' +
                            '<span style="color:' + resultColor + ';font-weight:bold;">' + data.result + '！</span> ' + data.message;
                        st(data.message, 3000);
                    })
                    .catch(function (e) {
                        resultEl.innerHTML = '游戏出错了喵~';
                    });
            });
        }

        document.getElementById('waifu-game-close').addEventListener('click', function () {
            if (gameModal) {
                gameModal.remove();
                gameModal = null;
            }
        });
    }

    // 获取CSRF token
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // 拍照功能
    function takePhoto() {
        var canvas = document.getElementById('live2d');
        if (!canvas) {
            st('找不到画布喵~', 3000);
            return;
        }
        try {
            // 创建下载链接
            var link = document.createElement('a');
            link.download = '看板娘_' + Date.now() + '.png';
            link.href = canvas.toDataURL('image/png');
            link.click();
            st(rp(DIALOGUES.photo), 3000);
        } catch (e) {
            console.error('[Waifu] photo error:', e);
            st('拍照失败喵~可能是跨域限制', 4000);
        }
    }

    function init() {
        console.log('[Waifu] init start');

        // 创建看板娘容器
        var w = document.createElement('div');
        w.id = 'waifu';
        w.style.cssText = 'position:fixed !important;right:20px !important;bottom:20px !important;z-index:2147483647 !important;width:220px !important;height:280px !important;pointer-events:auto !important;display:block !important;';
        w.style.setProperty('right', '20px', 'important');
        w.style.setProperty('bottom', '20px', 'important');
        w.style.setProperty('left', 'auto', 'important');
        w.style.setProperty('top', 'auto', 'important');

        w.innerHTML =
            '<div id="waifu-tips" style="position:absolute;top:-60px;left:-20px;right:-20px;background:linear-gradient(135deg,#fff,#fdf4ff);border:2px solid #e9d5ff;border-radius:16px;padding:10px 14px;font-size:13px;color:#6b21a8;box-shadow:0 4px 15px rgba(168,85,247,0.3);z-index:2147483646;min-height:36px;line-height:1.5;text-align:center;opacity:0;transition:opacity 0.3s;pointer-events:none;">加载中喵~</div>' +
            '<canvas id="live2d" width="800" height="800" style="width:220px;height:250px;position:absolute;bottom:0;left:0;cursor:pointer;"></canvas>' +
            '<div id="waifu-tool" style="position:absolute;top:-20px;left:-48px;display:flex;flex-direction:column;gap:8px;opacity:0;transition:opacity 0.4s ease,transform 0.4s ease;transform:translateX(10px);z-index:2147483646;">' +
                '<span class="waifu-btn" data-action="text" data-tip="说句话" data-hover-border="#a855f7" data-hover-bg="rgba(168,85,247,0.15)" style="width:34px;height:34px;background:rgba(255,255,255,0.95);backdrop-filter:blur(8px);border:2px solid transparent;border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:15px;box-shadow:0 2px 12px rgba(0,0,0,0.1);transition:all 0.3s ease;user-select:none;position:relative;">💬</span>' +
                '<span class="waifu-btn" data-action="game" data-tip="猜拳游戏" data-hover-border="#3b82f6" data-hover-bg="rgba(59,130,246,0.15)" style="width:34px;height:34px;background:rgba(255,255,255,0.95);backdrop-filter:blur(8px);border:2px solid transparent;border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:15px;box-shadow:0 2px 12px rgba(0,0,0,0.1);transition:all 0.3s ease;user-select:none;position:relative;">🎮</span>' +
                '<span class="waifu-btn" data-action="model" data-tip="换模型" data-hover-border="#f59e0b" data-hover-bg="rgba(245,158,11,0.15)" style="width:34px;height:34px;background:rgba(255,255,255,0.95);backdrop-filter:blur(8px);border:2px solid transparent;border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:15px;box-shadow:0 2px 12px rgba(0,0,0,0.1);transition:all 0.3s ease;user-select:none;position:relative;">🔄</span>' +
                '<span class="waifu-btn" data-action="skin" data-tip="换皮肤" data-hover-border="#ec4899" data-hover-bg="rgba(236,72,153,0.15)" style="width:34px;height:34px;background:rgba(255,255,255,0.95);backdrop-filter:blur(8px);border:2px solid transparent;border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:15px;box-shadow:0 2px 12px rgba(0,0,0,0.1);transition:all 0.3s ease;user-select:none;position:relative;">👗</span>' +
                '<span class="waifu-btn" data-action="photo" data-tip="拍照" data-hover-border="#22c55e" data-hover-bg="rgba(34,197,94,0.15)" style="width:34px;height:34px;background:rgba(255,255,255,0.95);backdrop-filter:blur(8px);border:2px solid transparent;border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:15px;box-shadow:0 2px 12px rgba(0,0,0,0.1);transition:all 0.3s ease;user-select:none;position:relative;">📷</span>' +
                '<span class="waifu-btn" data-action="close" data-tip="关闭" data-hover-border="#ef4444" data-hover-bg="rgba(239,68,68,0.15)" style="width:34px;height:34px;background:rgba(255,255,255,0.95);backdrop-filter:blur(8px);border:2px solid transparent;border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:15px;box-shadow:0 2px 12px rgba(0,0,0,0.1);transition:all 0.3s ease;user-select:none;position:relative;">✕</span>' +
            '</div>';

        document.body.appendChild(w);

        // hover显示菜单
        w.addEventListener('mouseenter', function () {
            var tool = document.getElementById('waifu-tool');
            if (tool) {
                tool.style.opacity = '1';
                tool.style.transform = 'translateX(0)';
            }
        });
        w.addEventListener('mouseleave', function () {
            var tool = document.getElementById('waifu-tool');
            if (tool) {
                tool.style.opacity = '0';
                tool.style.transform = 'translateX(10px)';
            }
        });

        // 按钮事件
        var btns = w.querySelectorAll('.waifu-btn');
        for (var i = 0; i < btns.length; i++) {
            btns[i].addEventListener('mouseenter', function () {
                var hoverBorder = this.dataset.hoverBorder || '#a855f7';
                var hoverBg = this.dataset.hoverBg || 'rgba(168,85,247,0.15)';
                this.style.borderColor = hoverBorder;
                this.style.background = hoverBg;
                this.style.transform = 'scale(1.15)';
                // 自定义tooltip
                var tip = this.dataset.tip;
                if (tip) {
                    var tipEl = document.getElementById('waifu-btn-tip');
                    if (!tipEl) {
                        tipEl = document.createElement('div');
                        tipEl.id = 'waifu-btn-tip';
                        tipEl.style.cssText = 'position:fixed;background:linear-gradient(135deg,#fff,#fdf4ff);border:2px solid #e9d5ff;border-radius:10px;padding:4px 10px;font-size:12px;color:#6b21a8;box-shadow:0 2px 10px rgba(168,85,247,0.3);z-index:2147483647;pointer-events:none;white-space:nowrap;opacity:0;transition:opacity 0.2s;';
                        document.body.appendChild(tipEl);
                    }
                    tipEl.textContent = tip;
                    var rect = this.getBoundingClientRect();
                    tipEl.style.left = (rect.left - 80) + 'px';
                    tipEl.style.top = (rect.top + rect.height / 2 - 12) + 'px';
                    tipEl.style.opacity = '1';
                }
            });
            btns[i].addEventListener('mouseleave', function () {
                this.style.borderColor = 'transparent';
                this.style.background = 'rgba(255,255,255,0.95)';
                this.style.transform = 'scale(1)';
                var tipEl = document.getElementById('waifu-btn-tip');
                if (tipEl) tipEl.style.opacity = '0';
            });
            btns[i].addEventListener('click', function (e) {
                e.stopPropagation();
                e.preventDefault();
                var action = this.dataset.action;
                if (action === 'text') { st(rp(DIALOGUES.click), 4000); }
                else if (action === 'game') { playGame(); }
                else if (action === 'model') { switchModel(); }
                else if (action === 'skin') { switchSkin(); }
                else if (action === 'photo') { takePhoto(); }
                else if (action === 'close') {
                    w.style.transition = 'all 0.5s';
                    w.style.opacity = '0';
                    w.style.transform = 'translateY(100px)';
                    setTimeout(function () { w.style.display = 'none'; }, 500);
                }
            });
        }

        // 加载初始模型（使用静态模型路径，确保稳定显示）
        var staticModels = {
            'shizuku': '/static/assets/live2d/models/shizuku/shizuku.model.json',
            'shizuku_talk': '/static/assets/live2d/models/shizuku_talk/shizuku-48/index.json',
            'koharu': '/static/assets/live2d/models/koharu/koharu.model.json',
            'haru': '/static/assets/live2d/models/haru/haru01.model.json',
            'hijiki': '/static/assets/live2d/models/hijiki/hijiki.model.json',
            'tororo': '/static/assets/live2d/models/tororo/tororo.model.json',
            'wanko': '/static/assets/live2d/models/wanko/wanko.model.json',
            'hibiki': '/static/assets/live2d/models/hibiki/hibiki.model.json',
            'izumi': '/static/assets/live2d/models/izumi/izumi.model.json',
            'tsumiki': '/static/assets/live2d/models/tsumiki/tsumiki.model.json',
            'chitose': '/static/assets/live2d/models/chitose/chitose.model.json',
            'haruto': '/static/assets/live2d/models/haruto/haruto.model.json',
            'miku': '/static/assets/live2d/models/miku/miku.model.json',
            'ni-j': '/static/assets/live2d/models/ni-j/ni-j.model.json',
            'nico': '/static/assets/live2d/models/nico/nico.model.json',
            'nipsilon': '/static/assets/live2d/models/nipsilon/nipsilon.model.json',
            'nito': '/static/assets/live2d/models/nito/nito.model.json',
            'unitychan': '/static/assets/live2d/models/unitychan/unitychan.model.json',
            'z16': '/static/assets/live2d/models/z16/z16.model.json',
        };
        var initUrl = staticModels[state.modelId] || staticModels['shizuku'];
        console.log('[Waifu] init modelId:', state.modelId, 'skin:', state.skin, 'url:', initUrl);
        loadModel(initUrl, function () {
            console.log('[Waifu] initial model loaded');
        });

        // 欢迎语
        welcomeTimer = setTimeout(function () { st(rp(DIALOGUES.welcome), 5000); }, 2000);

        // 点击交互
        var c = document.getElementById('live2d');
        if (c) {
            c.addEventListener('click', function () {
                if (welcomeTimer) clearTimeout(welcomeTimer);
                st(rp(DIALOGUES.click), 3000);
            });
        }

        // 窗口大小变化时重新定位
        window.addEventListener('resize', function () {
            var wEl = document.getElementById('waifu');
            if (wEl) {
                wEl.style.setProperty('right', '20px', 'important');
                wEl.style.setProperty('bottom', '20px', 'important');
                wEl.style.setProperty('left', 'auto', 'important');
                wEl.style.setProperty('top', 'auto', 'important');
            }
        });
    }

    // 添加动画样式
    var style = document.createElement('style');
    style.textContent = '@keyframes waifuFadeIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }';
    document.head.appendChild(style);

    // 启动
    if (document.body) {
        init();
    } else {
        document.addEventListener('DOMContentLoaded', init);
    }
})();

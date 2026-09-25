/* ============================================================
   Live2D 全格式渲染器（基于 pixi-live2d-display）
   支持 Cubism 2.1 / 3 / 4 / 5 所有格式模型
   ============================================================ */
(function () {
    'use strict';

    var PIXI = null;
    var Live2DModel = null;
    var app = null;
    var currentModel = null;
    var container = null;
    var canvasEl = null;
    var isReady = false;

    // 初始化PIXI应用
    function initApp(canvasId) {
        if (app) return app;

        canvasEl = document.getElementById(canvasId);
        if (!canvasEl) {
            console.error('[Live2D] Canvas not found:', canvasId);
            return null;
        }

        PIXI = window.PIXI;
        Live2DModel = window.PIXI.live2d.Live2DModel;

        app = new PIXI.Application({
            view: canvasEl,
            autoStart: true,
            resizeTo: canvasEl.parentElement,
            transparent: true,
            backgroundAlpha: 0,
            antialias: true
        });

        container = new PIXI.Container();
        app.stage.addChild(container);

        isReady = true;
        console.log('[Live2D] PIXI app initialized');
        return app;
    }

    // 加载模型（自动识别格式）
    function loadModel(canvasId, modelUrl, callback) {
        if (!isReady) {
            initApp(canvasId);
        }

        // 清除旧模型
        if (currentModel) {
            container.removeChild(currentModel);
            currentModel.destroy();
            currentModel = null;
        }

        Live2DModel.from(modelUrl).then(function (model) {
            currentModel = model;

            // 调试信息
            console.log('[Live2D] Model size:', model.width, 'x', model.height);
            console.log('[Live2D] Canvas size:', canvasEl.parentElement.clientWidth, 'x', canvasEl.parentElement.clientHeight);

            // 自动缩放适配
            var modelW = model.width || 1000;
            var modelH = model.height || 1000;
            var scale = Math.min(
                (canvasEl.parentElement.clientWidth - 20) / modelW,
                (canvasEl.parentElement.clientHeight - 20) / modelH
            );
            if (!scale || scale <= 0 || scale > 10) scale = 0.5;
            model.scale.set(scale * 0.9);

            console.log('[Live2D] Scale:', scale * 0.9);

            // 居中底部
            model.anchor.set(0.5, 1);
            model.x = app.renderer.width / 2;
            model.y = app.renderer.height;

            container.addChild(model);

            // 自动呼吸和眨眼
            if (model.motion) {
                try { model.motion('idle'); } catch(e) { console.log('[Live2D] idle motion not available'); }
            }

            console.log('[Live2D] Model loaded:', modelUrl);
            console.log('[Live2D] Model position:', model.x, model.y);
            if (callback) callback(null, model);
        }).catch(function (err) {
            console.error('[Live2D] Load model error:', err);
            if (callback) callback(err);
        });
    }

    // 切换皮肤（Cubism 2格式）
    function changeTexture(textureIndex) {
        if (!currentModel || !currentModel.textures) return;
        if (textureIndex >= 0 && textureIndex < currentModel.textures.length) {
            currentModel.textures.forEach(function (t, i) {
                t.visible = (i === textureIndex);
            });
        }
    }

    // 触发动作
    function motion(group, index) {
        if (currentModel && currentModel.motion) {
            currentModel.motion(group, index || 0);
        }
    }

    // 暴露全局API
    window.Live2DRenderer = {
        init: initApp,
        loadModel: loadModel,
        changeTexture: changeTexture,
        motion: motion,
        getModel: function () { return currentModel; },
        getApp: function () { return app; },
        isReady: function () { return isReady; }
    };

    console.log('[Live2D] Renderer loaded (supports Cubism 2/3/4/5)');
})();

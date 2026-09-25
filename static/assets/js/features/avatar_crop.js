/* ============================================================
 * features/avatar_crop.js —— 头像上传裁剪（bug13 增强）
 * 两种适配模式：
 *   「完整显示 contain」整图一次看全，圆形盖不到的区域用
 *      同图高斯模糊铺底，头像永不出现空白角；
 *   「填满圆形 cover」经典短边铺满，拖动选择裁切区域。
 * 选图后可在圆形视窗内拖动定位、滑块/滚轮缩放；
 * 提交表单前用 canvas 按视窗所见裁剪为 400×400 正方形 PNG
 * （含模糊铺底），再写回 <input type=file name=avatar>，后端无需改动。
 * ============================================================ */
(function () {
    'use strict';
    var fileInput = document.getElementById('id_avatar');
    var cropArea = document.getElementById('avatar-crop-area');
    if (!fileInput || !cropArea) return;

    var pickBtn = document.getElementById('avatar-pick-btn');
    var fileName = document.getElementById('avatar-file-name');
    var viewport = document.getElementById('avatar-crop-viewport');
    var bgImg = document.getElementById('avatar-crop-bg');       // 模糊铺底
    var cropImg = document.getElementById('avatar-crop-img');   // 可拖动主图
    var zoom = document.getElementById('avatar-crop-zoom');
    var fitBtns = document.querySelectorAll('.avatar-fit-btn'); // 模式切换
    var form = fileInput.closest('form');
    var OUT = 400;            // 输出边长 px
    // mode：contain 完整显示（默认，满足 bug13 整图可见）；cover 填满圆形
    var state = { mode: 'contain', scale: 1, x: 0, y: 0,
                  naturalW: 0, naturalH: 0, base: 0, ready: false };

    /* 萌系「选择图片喵」按钮触发隐藏的原生文件框 */
    if (pickBtn) {
        pickBtn.addEventListener('click', function () { fileInput.click(); });
    }

    function clamp(v, min, max) { return Math.max(min, Math.min(max, v)); }

    /* 依据模式与缩放计算图片显示尺寸、位移上限并应用变换 */
    function render() {
        if (!state.ready) return;
        var V = viewport.clientWidth || 240;
        var contain = Math.min(V / state.naturalW, V / state.naturalH); // 长边贴边→整图可见
        var cover = Math.max(V / state.naturalW, state.naturalH ? V / state.naturalH : contain);
        state.base = state.mode === 'cover' ? cover : contain;
        var w = state.naturalW * state.base * state.scale;
        var h = state.naturalH * state.base * state.scale;
        var maxX = Math.max(0, (w - V) / 2);
        var maxY = Math.max(0, (h - V) / 2);
        state.x = clamp(state.x, -maxX, maxX);
        state.y = clamp(state.y, -maxY, maxY);
        cropImg.style.width = w + 'px';
        cropImg.style.height = h + 'px';
        cropImg.style.transform =
            'translate(-50%,-50%) translate(' + state.x + 'px,' + state.y + 'px)';
        // contain 模式整图小于视窗时显示模糊铺底；cover 模式主图已铺满则隐藏
        viewport.classList.toggle('is-contain', state.mode === 'contain');
        bgImg.style.opacity = (state.mode === 'contain' && (w < V - 1 || h < V - 1)) ? '1' : '0';
    }

    /* 切换完整显示 / 填满圆形，重置缩放与位移 */
    fitBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            state.mode = btn.dataset.fit;
            state.scale = 1; state.x = 0; state.y = 0;
            if (zoom) zoom.value = 1;
            fitBtns.forEach(function (b) { b.classList.toggle('is-active', b === btn); });
            render();
        });
    });

    /* 选择文件：读入裁剪视窗 */
    fileInput.addEventListener('change', function () {
        var file = fileInput.files[0];
        if (!file) return;
        if (fileName) fileName.textContent = file.name;
        var url = URL.createObjectURL(file);
        cropImg.onload = function () {
            state.naturalW = cropImg.naturalWidth;
            state.naturalH = cropImg.naturalHeight;
            state.scale = 1; state.x = 0; state.y = 0;
            if (zoom) zoom.value = 1;
            state.ready = true;
            cropArea.hidden = false;
            render();
            URL.revokeObjectURL(url);
        };
        cropImg.src = url;
        if (bgImg) bgImg.src = url; // 模糊铺底同源
        // 同步顶部圆形预览
        var prevImg = document.getElementById('avatar-preview-img');
        var prevInitial = document.getElementById('avatar-preview-initial');
        if (prevImg) { prevImg.src = url; prevImg.style.display = 'block'; }
        if (prevInitial) prevInitial.style.display = 'none';
    });

    /* 滑块缩放 */
    if (zoom) {
        zoom.addEventListener('input', function () { state.scale = parseFloat(zoom.value); render(); });
    }
    /* 滚轮缩放（视窗内） */
    viewport.addEventListener('wheel', function (e) {
        if (!state.ready) return;
        e.preventDefault();
        state.scale = clamp(state.scale + (e.deltaY < 0 ? 0.08 : -0.08), 1, 3);
        if (zoom) zoom.value = state.scale;
        render();
    }, { passive: false });

    /* 指针拖动（鼠标 + 触摸） */
    var dragging = false, sx = 0, sy = 0, ox = 0, oy = 0;
    viewport.addEventListener('pointerdown', function (e) {
        if (!state.ready) return;
        dragging = true; sx = e.clientX; sy = e.clientY; ox = state.x; oy = state.y;
        viewport.setPointerCapture(e.pointerId);
    });
    viewport.addEventListener('pointermove', function (e) {
        if (!dragging) return;
        state.x = ox + (e.clientX - sx);
        state.y = oy + (e.clientY - sy);
        render();
    });
    function endDrag() { dragging = false; }
    viewport.addEventListener('pointerup', endDrag);
    viewport.addEventListener('pointercancel', endDrag);

    /* 提交前：按圆形视窗所见裁剪为正方形 PNG（含模糊铺底），写回文件框 */
    if (form) {
        form.addEventListener('submit', function (e) {
            if (!state.ready || !fileInput.files[0]) return; // 未选新图则走原流程
            e.preventDefault();
            var V = viewport.clientWidth || 240;
            var disp = state.base * state.scale;
            var w = state.naturalW * disp, h = state.naturalH * disp;
            // 主图在视窗内的显示区间（居中 + 位移），与 [0,V] 求交
            function span(dim, off) {
                var c0 = V / 2 - dim / 2 + off, c1 = c0 + dim;
                var d0 = clamp(c0, 0, V), d1 = clamp(c1, 0, V);
                return { d0: d0, d1: d1, s0: (d0 - c0) / disp, s1: (d1 - c0) / disp };
            }
            var xs = span(w, state.x), ys = span(h, state.y);

            var canvas = document.createElement('canvas');
            canvas.width = OUT; canvas.height = OUT;
            var ctx = canvas.getContext('2d');
            ctx.imageSmoothingQuality = 'high';

            /* ① 模糊同图铺底：cover 铺满并放大少许，盖住模糊边缘的透明缝 */
            ctx.fillStyle = '#f3ecff';
            ctx.fillRect(0, 0, OUT, OUT);
            var bg = OUT * 1.2, bs = Math.max(bg / state.naturalW, bg / state.naturalH);
            var bdW = state.naturalW * bs, bdH = state.naturalH * bs;
            ctx.filter = 'blur(22px)';
            ctx.drawImage(cropImg, (OUT - bdW) / 2, (OUT - bdH) / 2, bdW, bdH);
            ctx.filter = 'none';
            ctx.fillStyle = 'rgba(255,255,255,.18)';
            ctx.fillRect(0, 0, OUT, OUT);

            /* ② 按视窗所见绘制主图（整图或填满），映射到输出坐标 */
            ctx.drawImage(
                cropImg,
                xs.s0, ys.s0, xs.s1 - xs.s0, ys.s1 - ys.s0,
                xs.d0 / V * OUT, ys.d0 / V * OUT,
                (xs.d1 - xs.d0) / V * OUT, (ys.d1 - ys.d0) / V * OUT
            );

            canvas.toBlob(function (blob) {
                var out = new File([blob], 'avatar_crop.png', { type: 'image/png' });
                try {
                    var dt = new DataTransfer();
                    dt.items.add(out);
                    fileInput.files = dt.files;
                } catch (err) {
                    // 个别浏览器不允许赋值 files，则直接用 FormData 提交裁剪结果
                    var fd = new FormData(form);
                    fd.set('avatar', out, 'avatar_crop.png');
                    fd.set('avatar_form', '1');
                    fetch(form.action, { method: 'POST', body: fd, credentials: 'same-origin' })
                        .then(function () { window.location.reload(); });
                    return;
                }
                form.submit();
            }, 'image/png');
        });
    }
})();

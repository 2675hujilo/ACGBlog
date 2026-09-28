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
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';
    //> 声明变量「fileInput」（file input），用于保存对应数据，保存 DOM/窗口相关对象
    var fileInput = document.getElementById('id_avatar');
    //> 声明变量「cropArea」（crop area），用于保存对应数据，保存 DOM/窗口相关对象
    var cropArea = document.getElementById('avatar-crop-area');
    //> 条件判断：满足括号内条件时执行对应分支
    if (!fileInput || !cropArea) return;

    //> 声明变量「pickBtn」（pick btn），用于保存对应数据，保存 DOM/窗口相关对象
    var pickBtn = document.getElementById('avatar-pick-btn');
    //> 声明变量「fileName」（file name），用于保存对应数据，保存 DOM/窗口相关对象
    var fileName = document.getElementById('avatar-file-name');
    //> 声明变量「viewport」（viewport），用于保存对应数据，保存 DOM/窗口相关对象
    var viewport = document.getElementById('avatar-crop-viewport');
    //> 声明变量「bgImg」（bg img），用于保存对应数据，保存 DOM/窗口相关对象
    var bgImg = document.getElementById('avatar-crop-bg');       // 模糊铺底
    //> 声明变量「cropImg」（crop img），用于保存对应数据，保存 DOM/窗口相关对象
    var cropImg = document.getElementById('avatar-crop-img');   // 可拖动主图
    //> 声明变量「zoom」（zoom），用于保存对应数据，保存 DOM/窗口相关对象
    var zoom = document.getElementById('avatar-crop-zoom');
    //> 声明变量「fitBtns」（fit btns），用于保存对应数据，保存 DOM/窗口相关对象
    var fitBtns = document.querySelectorAll('.avatar-fit-btn'); // 模式切换
    //> 声明变量「form」（form），用于保存对应数据
    var form = fileInput.closest('form');
    //> 声明变量「OUT」（out），用于保存对应数据
    var OUT = 400;            // 输出边长 px
    // mode：contain 完整显示（默认，满足 bug13 整图可见）；cover 填满圆形
    //> 声明变量「state」（state），用于保存对应数据
    var state = { mode: 'contain', scale: 1, x: 0, y: 0,
                  //> 该行执行对应的脚本逻辑（结合上下文理解）
                  naturalW: 0, naturalH: 0, base: 0, ready: false };

    /* 萌系「选择图片喵」按钮触发隐藏的原生文件框 */
    //> 条件判断：满足括号内条件时执行对应分支
    if (pickBtn) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        pickBtn.addEventListener('click', function () { fileInput.click(); });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    // =========================================================
    // 【函数】clamp
    // 功能：处理「clamp」相关逻辑（avatar_crop）
    // 参数：
    //   - v：传入的参数（含义结合调用处与函数体）
    //   - min：传入的参数（含义结合调用处与函数体）
    //   - max：传入的参数（含义结合调用处与函数体）
    // 返回：函数体内有 return，返回对应结果
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function clamp(v, min, max) { return Math.max(min, Math.min(max, v)); }

    /* 依据模式与缩放计算图片显示尺寸、位移上限并应用变换 */
    // =========================================================
    // 【函数】render
    // 功能：渲染相关逻辑（render）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function render() {
        //> 条件判断：满足括号内条件时执行对应分支
        if (!state.ready) return;
        //> 声明变量「V」（v），用于保存对应数据
        var V = viewport.clientWidth || 240;
        //> 声明变量「contain」（contain），用于保存对应数据
        var contain = Math.min(V / state.naturalW, V / state.naturalH); // 长边贴边→整图可见
        //> 声明变量「cover」（cover），用于保存对应数据
        var cover = Math.max(V / state.naturalW, state.naturalH ? V / state.naturalH : contain);
        //> 给「state.base」赋值，更新其保存的状态
        state.base = state.mode === 'cover' ? cover : contain;
        //> 声明变量「w」（w），用于保存对应数据
        var w = state.naturalW * state.base * state.scale;
        //> 声明变量「h」（h），用于保存对应数据
        var h = state.naturalH * state.base * state.scale;
        //> 声明变量「maxX」（max x），用于保存对应数据
        var maxX = Math.max(0, (w - V) / 2);
        //> 声明变量「maxY」（max y），用于保存对应数据
        var maxY = Math.max(0, (h - V) / 2);
        //> 给「state.x」赋值，更新其保存的状态
        state.x = clamp(state.x, -maxX, maxX);
        //> 给「state.y」赋值，更新其保存的状态
        state.y = clamp(state.y, -maxY, maxY);
        //> 给「cropImg.style.width」赋值，更新其保存的状态
        cropImg.style.width = w + 'px';
        //> 给「cropImg.style.height」赋值，更新其保存的状态
        cropImg.style.height = h + 'px';
        //> 给「cropImg.style.transform」赋值，更新其保存的状态
        cropImg.style.transform =
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            'translate(-50%,-50%) translate(' + state.x + 'px,' + state.y + 'px)';
        // contain 模式整图小于视窗时显示模糊铺底；cover 模式主图已铺满则隐藏
        //> 切换样式类（有则移除、无则添加），可传第二参强制状态
        viewport.classList.toggle('is-contain', state.mode === 'contain');
        //> 给「bgImg.style.opacity」赋值，更新其保存的状态
        bgImg.style.opacity = (state.mode === 'contain' && (w < V - 1 || h < V - 1)) ? '1' : '0';
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }

    /* 切换完整显示 / 填满圆形，重置缩放与位移 */
    //> 遍历数组/类数组中的每一项并执行回调
    fitBtns.forEach(function (btn) {
        //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        btn.addEventListener('click', function () {
            //> 读写元素的 data-* 自定义数据属性
            state.mode = btn.dataset.fit;
            //> 给「state.scale」赋值，更新其保存的状态
            state.scale = 1; state.x = 0; state.y = 0;
            //> 条件判断：满足括号内条件时执行对应分支
            if (zoom) zoom.value = 1;
            //> 切换样式类（有则移除、无则添加），可传第二参强制状态
            fitBtns.forEach(function (b) { b.classList.toggle('is-active', b === btn); });
            //> 调用函数「render」并传入参数执行对应逻辑
            render();
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* 选择文件：读入裁剪视窗 */
    //> 绑定「change」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    fileInput.addEventListener('change', function () {
        //> 声明变量「file」（file），用于保存对应数据
        var file = fileInput.files[0];
        //> 条件判断：满足括号内条件时执行对应分支
        if (!file) return;
        //> 条件判断：满足括号内条件时执行对应分支
        if (fileName) fileName.textContent = file.name;
        //> 声明变量「url」（url），用于保存对应数据
        var url = URL.createObjectURL(file);
        // =========================================================
        // 【函数】onload
        // 功能：处理「onload」相关逻辑（avatar_crop）
        // 参数：无
        // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
        // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
        // =========================================================
        cropImg.onload = function () {
            //> 给「state.naturalW」赋值，更新其保存的状态
            state.naturalW = cropImg.naturalWidth;
            //> 给「state.naturalH」赋值，更新其保存的状态
            state.naturalH = cropImg.naturalHeight;
            //> 给「state.scale」赋值，更新其保存的状态
            state.scale = 1; state.x = 0; state.y = 0;
            //> 条件判断：满足括号内条件时执行对应分支
            if (zoom) zoom.value = 1;
            //> 给「state.ready」赋值，更新其保存的状态
            state.ready = true;
            //> 给「cropArea.hidden」赋值，更新其保存的状态
            cropArea.hidden = false;
            //> 调用函数「render」并传入参数执行对应逻辑
            render();
            //> 操作「URL」的相关方法/属性
            URL.revokeObjectURL(url);
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        };
        //> 给「cropImg.src」赋值，更新其保存的状态
        cropImg.src = url;
        //> 条件判断：满足括号内条件时执行对应分支
        if (bgImg) bgImg.src = url; // 模糊铺底同源
        // 同步顶部圆形预览
        //> 声明变量「prevImg」（prev img），用于保存对应数据，保存 DOM/窗口相关对象
        var prevImg = document.getElementById('avatar-preview-img');
        //> 声明变量「prevInitial」（prev initial），用于保存对应数据，保存 DOM/窗口相关对象
        var prevInitial = document.getElementById('avatar-preview-initial');
        //> 条件判断：满足括号内条件时执行对应分支
        if (prevImg) { prevImg.src = url; prevImg.style.display = 'block'; }
        //> 条件判断：满足括号内条件时执行对应分支
        if (prevInitial) prevInitial.style.display = 'none';
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    /* 滑块缩放 */
    //> 条件判断：满足括号内条件时执行对应分支
    if (zoom) {
        //> 绑定「input」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        zoom.addEventListener('input', function () { state.scale = parseFloat(zoom.value); render(); });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    /* 滚轮缩放（视窗内） */
    //> 绑定「wheel」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    viewport.addEventListener('wheel', function (e) {
        //> 条件判断：满足括号内条件时执行对应分支
        if (!state.ready) return;
        //> 阻止事件的默认行为（如表单提交、链接跳转）
        e.preventDefault();
        //> 给「state.scale」赋值，更新其保存的状态
        state.scale = clamp(state.scale + (e.deltaY < 0 ? 0.08 : -0.08), 1, 3);
        //> 条件判断：满足括号内条件时执行对应分支
        if (zoom) zoom.value = state.scale;
        //> 调用函数「render」并传入参数执行对应逻辑
        render();
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    }, { passive: false });

    /* 指针拖动（鼠标 + 触摸） */
    //> 声明变量「dragging」（dragging），用于保存对应数据
    var dragging = false, sx = 0, sy = 0, ox = 0, oy = 0;
    //> 绑定「pointerdown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    viewport.addEventListener('pointerdown', function (e) {
        //> 条件判断：满足括号内条件时执行对应分支
        if (!state.ready) return;
        //> 给「dragging」赋值，更新其保存的状态
        dragging = true; sx = e.clientX; sy = e.clientY; ox = state.x; oy = state.y;
        //> 操作「viewport」的相关方法/属性
        viewport.setPointerCapture(e.pointerId);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
    //> 绑定「pointermove」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    viewport.addEventListener('pointermove', function (e) {
        //> 条件判断：满足括号内条件时执行对应分支
        if (!dragging) return;
        //> 给「state.x」赋值，更新其保存的状态
        state.x = ox + (e.clientX - sx);
        //> 给「state.y」赋值，更新其保存的状态
        state.y = oy + (e.clientY - sy);
        //> 调用函数「render」并传入参数执行对应逻辑
        render();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
    // =========================================================
    // 【函数】endDrag
    // 功能：处理「end drag」相关逻辑（avatar_crop）
    // 参数：无
    // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
    // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
    // =========================================================
    function endDrag() { dragging = false; }
    //> 绑定「pointerup」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    viewport.addEventListener('pointerup', endDrag);
    //> 绑定「pointercancel」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    viewport.addEventListener('pointercancel', endDrag);

    /* 提交前：按圆形视窗所见裁剪为正方形 PNG（含模糊铺底），写回文件框 */
    //> 条件判断：满足括号内条件时执行对应分支
    if (form) {
        //> 绑定「submit」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
        form.addEventListener('submit', function (e) {
            //> 条件判断：满足括号内条件时执行对应分支
            if (!state.ready || !fileInput.files[0]) return; // 未选新图则走原流程
            //> 阻止事件的默认行为（如表单提交、链接跳转）
            e.preventDefault();
            //> 声明变量「V」（v），用于保存对应数据
            var V = viewport.clientWidth || 240;
            //> 声明变量「disp」（disp），用于保存对应数据
            var disp = state.base * state.scale;
            //> 声明变量「w」（w），用于保存对应数据
            var w = state.naturalW * disp, h = state.naturalH * disp;
            // 主图在视窗内的显示区间（居中 + 位移），与 [0,V] 求交
            // =========================================================
            // 【函数】span
            // 功能：处理「span」相关逻辑（avatar_crop）
            // 参数：
            //   - dim：传入的参数（含义结合调用处与函数体）
            //   - off：传入的参数（含义结合调用处与函数体）
            // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
            // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
            // =========================================================
            function span(dim, off) {
                //> 声明变量「c0」（c0），用于保存对应数据
                var c0 = V / 2 - dim / 2 + off, c1 = c0 + dim;
                //> 声明变量「d0」（d0），用于保存对应数据
                var d0 = clamp(c0, 0, V), d1 = clamp(c1, 0, V);
                //> 返回结果并结束当前函数
                return { d0: d0, d1: d1, s0: (d0 - c0) / disp, s1: (d1 - c0) / disp };
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
            //> 声明变量「xs」（xs），用于保存对应数据
            var xs = span(w, state.x), ys = span(h, state.y);

            //> 声明变量「canvas」（canvas），用于保存对应数据，保存 DOM/窗口相关对象
            var canvas = document.createElement('canvas');
            //> 给「canvas.width」赋值，更新其保存的状态
            canvas.width = OUT; canvas.height = OUT;
            //> 声明变量「ctx」（ctx），用于保存对应数据
            var ctx = canvas.getContext('2d');
            //> 给「ctx.imageSmoothingQuality」赋值，更新其保存的状态
            ctx.imageSmoothingQuality = 'high';

            /* ① 模糊同图铺底：cover 铺满并放大少许，盖住模糊边缘的透明缝 */
            //> 给「ctx.fillStyle」赋值，更新其保存的状态
            ctx.fillStyle = '#f3ecff';
            //> 操作「ctx」的相关方法/属性
            ctx.fillRect(0, 0, OUT, OUT);
            //> 声明变量「bg」（bg），用于保存对应数据
            var bg = OUT * 1.2, bs = Math.max(bg / state.naturalW, bg / state.naturalH);
            //> 声明变量「bdW」（bd w），用于保存对应数据
            var bdW = state.naturalW * bs, bdH = state.naturalH * bs;
            //> 给「ctx.filter」赋值，更新其保存的状态
            ctx.filter = 'blur(22px)';
            //> 操作「ctx」的相关方法/属性
            ctx.drawImage(cropImg, (OUT - bdW) / 2, (OUT - bdH) / 2, bdW, bdH);
            //> 给「ctx.filter」赋值，更新其保存的状态
            ctx.filter = 'none';
            //> 给「ctx.fillStyle」赋值，更新其保存的状态
            ctx.fillStyle = 'rgba(255,255,255,.18)';
            //> 操作「ctx」的相关方法/属性
            ctx.fillRect(0, 0, OUT, OUT);

            /* ② 按视窗所见绘制主图（整图或填满），映射到输出坐标 */
            //> 操作「ctx」的相关方法/属性
            ctx.drawImage(
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                cropImg,
                //> 操作「xs」的相关方法/属性
                xs.s0, ys.s0, xs.s1 - xs.s0, ys.s1 - ys.s0,
                //> 操作「xs」的相关方法/属性
                xs.d0 / V * OUT, ys.d0 / V * OUT,
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                (xs.d1 - xs.d0) / V * OUT, (ys.d1 - ys.d0) / V * OUT
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            );

            //> 操作「canvas」的相关方法/属性
            canvas.toBlob(function (blob) {
                //> 声明变量「out」（out），用于保存对应数据
                var out = new File([blob], 'avatar_crop.png', { type: 'image/png' });
                //> 尝试执行可能出错的代码，出错则进入 catch
                try {
                    //> 声明变量「dt」（dt），用于保存对应数据
                    var dt = new DataTransfer();
                    //> 操作「dt.items」的相关方法/属性
                    dt.items.add(out);
                    //> 给「fileInput.files」赋值，更新其保存的状态
                    fileInput.files = dt.files;
                //> 该行执行对应的脚本逻辑（结合上下文理解）
                } catch (err) {
                    // 个别浏览器不允许赋值 files，则直接用 FormData 提交裁剪结果
                    //> 声明变量「fd」（fd），用于保存对应数据
                    var fd = new FormData(form);
                    //> 操作「fd」的相关方法/属性
                    fd.set('avatar', out, 'avatar_crop.png');
                    //> 操作「fd」的相关方法/属性
                    fd.set('avatar_form', '1');
                    //> 发起网络请求，返回 Promise；需处理响应与异常，并携带 CSRF
                    fetch(form.action, { method: 'POST', body: fd, credentials: 'same-origin' })
                        //> 重新加载当前页面
                        .then(function () { window.location.reload(); });
                    //> 提前结束函数，无返回值
                    return;
                //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
                }
                //> 操作「form」的相关方法/属性
                form.submit();
            //> 该行执行对应的脚本逻辑（结合上下文理解）
            }, 'image/png');
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

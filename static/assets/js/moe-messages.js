/* ============================================================
 * moe-messages.js —— 全站文案访问层（Bug9 任务「2」前端部分）
 * ------------------------------------------------------------
 * 作用：
 *   把后端下发的文案包（base.html 中 <script id="site-messages-data"
 *   type="application/json"> 由 Django |json_script 安全序列化）挂到
 *   window.SITE_MSG，并暴露 window.moeMsg(key, ...args) 取词函数，
 *   从此前端脚本不再硬编码中文提示语。
 *
 * 设计要点：
 *   1. **同步可用**：脚本以普通 <script> 引入（非 defer 依赖顺序），
 *      在 DOM 解析到 body 后立即可用，不需要等待网络请求；
 *   2. **离线兜底**：读取失败时用内置 FALLBACK 文案，保证 toast 等提示
 *      永远不会是空白；
 *   3. **占位符**：支持 {0} {1} 位置占位与 {name} 具名占位，
 *      与后端 str.format 语义保持一致（JS 侧用简单替换实现）；
 *   4. **零依赖**：不依赖 jQuery / 任何框架，可在任意页面单独引入。
 * ============================================================ */
(function () {
    'use strict';

    /* 内置兜底文案：与后端 blog/site_messages.py 的 js.* 键一一对应，
       仅在页面未渲染文案包（极少数异常）时生效。 */
    var FALLBACK = {
        network_error: '网络开小差了，稍后再试喵~',
        confirm_default: '请确认喵~',
        confirm_ok: '确定喵',
        confirm_cancel: '再想想',
        loading: '加载中喵…',
        load_more: '加载更多喵~',
        no_more: '没有更多了喵~',
        copied: '已复制喵~ 📋',
        offline: '当前处于离线状态喵~',
        online_again: '网络恢复啦~ 🔄',
        unsaved_leave: '有内容还没保存，真的要离开吗喵？',
        delete_confirm: '确定要删除吗？删除后可以在回收站找回喵~',
        generic_error: '出了点小问题喵，稍后再试~'
    };

    /**
     * 读取页面内嵌的文案包。
     * @returns {Object} 形如 { network_error: '...', btn_confirm: '...' }
     */
    function readPayload() {
        var el = document.getElementById('site-messages-data');
        if (!el) return {};
        try {
            // json_script 输出的是应用 JSON 类型脚本，textContent 即安全 JSON 文本
            var parsed = JSON.parse(el.textContent || '{}');
            return (parsed && typeof parsed === 'object') ? parsed : {};
        } catch (e) {
            // 解析失败（极端情况）时返回空对象，由 FALLBACK 兜底
            return {};
        }
    }

    /**
     * 把 {0} / {name} 占位替换为实参。
     * 位置参数从 args 依次取，具名参数从最后一个对象参数里取。
     */
    function interpolate(text, args) {
        if (!args || !args.length) return text;
        var named = (args.length && typeof args[args.length - 1] === 'object') ? args[args.length - 1] : null;
        return String(text).replace(/\{(\w+)\}/g, function (all, key) {
            // 具名占位优先；否则当作位置下标
            if (named && Object.prototype.hasOwnProperty.call(named, key)) return named[key];
            var idx = parseInt(key, 10);
            if (!isNaN(idx) && idx < args.length) return args[idx];
            return all;   // 找不到对应实参时保留占位，便于发现遗漏
        });
    }

    var payload = readPayload();

    /**
     * 取文案：优先取后端下发，其次取内置兜底，最后回退为 key 本身。
     * @param {string} key 文案键（如 'network_error'、'btn_confirm'）
     * @param {...*} args 占位符实参
     * @returns {string}
     */
    function moeMsg(key) {
        var args = Array.prototype.slice.call(arguments, 1);
        var text = payload[key];
        if (text === undefined || text === null || text === '') text = FALLBACK[key];
        if (text === undefined || text === null) text = key;
        return interpolate(text, args);
    }

    // 暴露到全局：window.SITE_MSG 供直接读取，window.moeMsg 供带占位符取词
    window.SITE_MSG = payload;
    window.moeMsg = moeMsg;

    /* ----------------------------------------------------------
     * 结构化文案命名空间：window.MOE_MSG.<域>.<键>
     * 与后端 MSG.<域>.<键> 命名保持一致，便于前后端对照阅读。
     * -------------------------------------------------------- */
    window.MOE_MSG = {
        js: FALLBACK,
        /** 泛化取词（等价于 moeMsg，语义更明确） */
        get: moeMsg,
        /** 当前是否成功拿到后端下发的文案包（自动化测试可用） */
        ready: Object.keys(payload).length > 0
    };

    /**
     * 异步补齐文案：从 /api/site-messages/ 拉取并合并（用于 SW 离线页等
     * 未渲染模板的场景）。失败静默，因为兜底文案已可用。
     */
    window.moeMsgRefresh = function () {
        if (typeof fetch !== 'function') return Promise.resolve(false);
        return fetch('/api/site-messages/', { credentials: 'same-origin' })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (j) {
                if (!j || !j.data) return false;
                Object.keys(j.data).forEach(function (k) { window.SITE_MSG[k] = j.data[k]; });
                window.MOE_MSG.ready = true;
                return true;
            })
            .catch(function () { return false; });
    };
})();

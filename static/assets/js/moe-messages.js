/* ============================================================================
 * moe-messages.js —— 全站文案访问层（Bug9 前端部分）
 * ----------------------------------------------------------------------------
 * 目标：让前端脚本不再硬编码中文提示，统一从后端下发的文案包取词。
 *
 * 文案包来源：
 *   base.html 中 <script id="site-messages-data" type="application/json">，
 *   由 Django 的 json_script 过滤器安全序列化（自动转义 <，杜绝脚本注入）。
 *
 * 对外暴露：
 *   · window.SITE_MSG            文案包对象（直接读取）；
 *   · window.moeMsg(key, ...args) 取词函数，支持占位符；
 *   · window.MOE_MSG             结构化命名空间（与后端 MSG 对照）；
 *   · window.moeMsgRefresh()     从 /api/site-messages/ 异步补文案（离线页用）。
 *
 * 设计要点：
 *   1. 同步可用：普通 <script> 顺序引入，解析到即可用，无需等待网络；
 *   2. 离线兜底：读取失败用内置 FALLBACK，提示永不为空；
 *   3. 占位符：支持 {0}{1} 位置占位与 {name} 具名占位，对齐后端 str.format；
 *   4. 零依赖：不依赖 jQuery / 任何框架，可单独引入任意页面。
 * ----------------------------------------------------------------------------
 * 排错速查：
 *   · 文案包节点 id 固定为 'site-messages-data'（json_script 生成），后端模板
 *     必须输出该节点，否则前端只用 FALLBACK；
 *   · 占位符找不到实参时「保留原样」（如 {name}），这是刻意的，便于在界面上
 *     直接暴露漏传参数，而不是悄悄替换成 undefined；
 *   · 离线 / SW 页面未渲染模板时调用 moeMsgRefresh() 从 /api/site-messages/
 *     补文案，失败静默因为 FALLBACK 已保证不空；
 *   · 新增前端文案优先在后端文案表登记，避免再次散落硬编码；
 *   · 相关文件：后端 services/site_messages.py、site_messages_admin.js（后台
 *     覆盖管理）、site_messages.css（后台样式）。
 * ============================================================================ */
(function () {
    'use strict';

    /*
     * 内置兜底文案：与后端 site_messages 的 js.* 键一一对应，
     * 仅在页面未渲染文案包（极少数异常）时生效。
     */
    var FALLBACK = {
        network_error: '网络开小差了，稍后再试喵~',     // 网络请求失败
        confirm_default: '请确认喵~',                   // 通用确认标题
        confirm_ok: '确定喵',                           // 确认按钮
        confirm_cancel: '再想想',                       // 取消按钮
        loading: '加载中喵…',                           // 加载中
        load_more: '加载更多喵~',                       // 加载更多
        no_more: '没有更多了喵~',                       // 列表到底
        copied: '已复制喵~ 📋',                         // 复制成功
        offline: '当前处于离线状态喵~',                 // 离线提示
        online_again: '网络恢复啦~ 🔄',                 // 恢复联网
        unsaved_leave: '有内容还没保存，真的要离开吗喵？', // 离开未保存页
        delete_confirm: '确定要删除吗？删除后可以在回收站找回喵~', // 删除确认
        generic_error: '出了点小问题喵，稍后再试~'       // 通用错误
    };

    /**
     * 读取页面内嵌文案包。
     * @returns {Object} 文案键值对象；读取失败返回 {}。
     */
    function readPayload() {
        // 取 json_script 输出的脚本节点
        var el = document.getElementById('site-messages-data');
        if (!el) return {};
        try {
            // textContent 即安全 JSON 文本，解析之
            var parsed = JSON.parse(el.textContent || '{}');
            // 确认是对象再返回
            return (parsed && typeof parsed === 'object') ? parsed : {};
        } catch (err) {
            // 解析失败返回空对象，交由 FALLBACK 兜底
            return {};
        }
    }

    /**
     * 替换文案中的 {0} / {name} 占位符。
     * @param {string} text - 含占位符的原文。
     * @param {Array} args  - 实参数组（最后一个若为对象则兼作具名参数来源）。
     * @returns {string} 替换后的文案。
     */
    function interpolate(text, args) {
        // 无实参直接返回原文
        if (!args || !args.length) return text;
        // 末位是普通对象时作为具名参数表（null 不算）
        var named = (args.length &&
            typeof args[args.length - 1] === 'object')
            ? args[args.length - 1] : null;
        // 逐个替换 {xxx}
        return String(text).replace(/\{(\w+)\}/g, function (all, key) {
            // 具名参数优先
            if (named &&
                Object.prototype.hasOwnProperty.call(named, key)) {
                return named[key];
            }
            // 否则当作位置下标
            var idx = parseInt(key, 10);
            if (!isNaN(idx) && idx < args.length) return args[idx];
            // 找不到实参则保留占位，便于暴露遗漏
            return all;
        });
    }

    // 启动时读取一次文案包
    var payload = readPayload();

    /**
     * 取文案：后端下发 → 内置兜底 → key 本身。
     * @param {string} key - 文案键。
     * @returns {string} 最终文案（其余参数作为占位符实参）。
     */
    function moeMsg(key) {
        // 取占位符实参
        var args = Array.prototype.slice.call(arguments, 1);
        // 优先用后端下发文案
        var text = payload[key];
        // 后端没有则用兜底
        if (text === undefined || text === null || text === '') {
            text = FALLBACK[key];
        }
        // 兜底也没有则直接显示 key，避免空白
        if (text === undefined || text === null) text = key;
        // 替换占位符后返回
        return interpolate(text, args);
    }

    // 暴露文案包与取词函数到全局
    window.SITE_MSG = payload;
    window.moeMsg = moeMsg;

    /*
     * 结构化命名空间：window.MOE_MSG.<域>.<键>，
     * 与后端 MSG.<域>.<键> 命名保持一致，方便前后端对照。
     */
    window.MOE_MSG = {
        js: FALLBACK,                 // js 域直接引用兜底表
        get: moeMsg,                  // 泛化取词
        // 是否成功拿到后端文案（自动化测试可据此判断）
        ready: Object.keys(payload).length > 0
    };

    /**
     * 异步补齐文案：拉取 /api/site-messages/ 并合并进 SITE_MSG。
     * 用于 Service Worker 离线页等没有渲染模板的场景；失败静默（兜底已可用）。
     * @returns {Promise<boolean>} 是否成功合并。
     */
    window.moeMsgRefresh = function () {
        // 不支持 fetch 时直接返回失败
        if (typeof fetch !== 'function') {
            return Promise.resolve(false);
        }
        // 请求文案接口（带同源凭证）
        return fetch('/api/site-messages/', {credentials: 'same-origin'})
            .then(function (r) {
                // 仅在响应正常时解析 JSON
                return r.ok ? r.json() : null;
            })
            .then(function (j) {
                // 接口结构为 {data: {...}}；缺失则失败
                if (!j || !j.data) return false;
                // 逐个合并到全局文案包
                Object.keys(j.data).forEach(function (k) {
                    window.SITE_MSG[k] = j.data[k];
                });
                // 标记就绪
                window.MOE_MSG.ready = true;
                return true;
            })
            .catch(function () {
                // 任何异常都返回失败，不抛出
                return false;
            });
    };
})();

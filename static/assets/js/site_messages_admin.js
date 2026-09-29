/* ============================================================
 * site_messages_admin.js —— 文案总表管理页交互
 * ------------------------------------------------------------
 * 只做三件「纯前端、不影响数据」的事，编辑与保存完全依赖原生表单
 * （即使脚本加载失败，页面依然可正常编辑与提交）：
 *   1. 全部展开 / 全部折叠（近 300 条时快速定位域）；
 *   2. 实时标出「本次被改过」的行并统计数量（防误改、防漏改）；
 *   3. 有未保存改动时，离开页面前提示（beforeunload）。
 *
 * 两个「改过」的口径必须区分（踩过坑）：
 *   · 服务端口径 `is-changed`：该 key 在数据库里有覆盖记录（进页面时就有）；
 *   · 前端口径 `is-dirty`  ：输入框当前值与「进页面时的值」（data-original）不同。
 * 若混用，用户只是把值改回原样也会被误标为「待保存」，或被 beforeunload 误拦。
 * ============================================================ */
(function () {
    'use strict';

    var form = document.getElementById('msgs-form');
    if (!form) return;

    var rows = Array.prototype.slice.call(form.querySelectorAll('.msgs-row'));
    var bar = form.querySelector('.msgs-savebar');
    var meter = bar ? bar.querySelector('.muted') : null;

    /** 采集每行的输入框与「进页面时的值」，供脏检查使用。 */
    var states = rows.map(function (row) {
        var input = row.querySelector('.msgs-input');
        return {
            row: row,
            input: input,
            original: row.getAttribute('data-original') || '',
            dirtyChip: row.querySelector('.msgs-chip--dirty'),
        };
    });

    /** 依据输入框当前值刷新「待保存」标记与统计，返回脏行数。 */
    function refresh() {
        var dirty = 0;
        states.forEach(function (s) {
            if (!s.input) return;
            var isDirty = s.input.value !== s.original;
            if (isDirty) dirty++;
            s.row.classList.toggle('is-dirty', isDirty);
            if (s.dirtyChip) s.dirtyChip.hidden = !isDirty;
        });
        if (meter) {
            meter.textContent = dirty
                ? ('有 ' + dirty + ' 条改动待保存')
                : ('共 ' + states.length + ' 条，暂无改动');
        }
        return dirty;
    }

    /* ---- 1. 输入即刷新（事件委托：近 300 个输入框只绑一次） ---- */
    form.addEventListener('input', function (e) {
        if (e.target && e.target.classList && e.target.classList.contains('msgs-input')) {
            refresh();
        }
    });

    /* ---- 2. 全部展开 / 折叠 + 搜索框快捷键 ---- */
    if (bar) {
        var toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.className = 'btn-sm';
        toggle.textContent = '展开全部域';
        toggle.addEventListener('click', function () {
            var blocks = form.querySelectorAll('details.msgs-domain');
            var anyClosed = Array.prototype.some.call(blocks, function (d) { return !d.open; });
            Array.prototype.forEach.call(blocks, function (d) { d.open = anyClosed; });
            toggle.textContent = anyClosed ? '折叠全部域' : '展开全部域';
        });
        bar.appendChild(toggle);
    }
    var search = document.querySelector('.msgs-toolbar input[type="search"]');
    if (search) {
        document.addEventListener('keydown', function (e) {
            var tag = (e.target && e.target.tagName) || '';
            if (e.key === '/' && tag !== 'INPUT' && tag !== 'TEXTAREA') {
                e.preventDefault();
                search.focus();
                search.select();
            }
        });
    }

    /* ---- 3. 有未保存改动时离开提示 ---- */
    var submitting = false;
    form.addEventListener('submit', function () { submitting = true; });
    window.addEventListener('beforeunload', function (e) {
        if (submitting) return undefined;
        if (refresh() > 0) {
            e.preventDefault();
            e.returnValue = '';   // 兼容旧实现：部分浏览器需要设置该值才弹确认
            return '';
        }
        return undefined;
    });

    refresh();
})();

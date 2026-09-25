/* Bug11 文件头注释
 * 审核页脚本：自定义确认弹窗（替代原生 confirm）、理由填写、标签切换与异步审核。
 * js-confirm 按钮统一走弹窗，可带 data-need-reason 收集理由随表单提交。
 */
/* Bug8：站内统一确认弹窗，取代 window.confirm / alert。
   触发方式：在 <form> 内放置 .js-confirm 按钮（type=button），
   通过 data-* 描述标题/正文/图标/确认按钮文案，需要理由时 data-need-reason=1。 */
(function () {
  var mask = document.getElementById('modModal');
  if (!mask) return;
  var titleEl = document.getElementById('modModalTitle'),
      bodyEl = document.getElementById('modModalBody'),
      iconEl = document.getElementById('modModalIcon'),
      reasonWrap = document.getElementById('modModalReasonWrap'),
      reasonEl = document.getElementById('modModalReason'),
      okBtn = document.getElementById('modModalOk'),
      cancelBtn = document.getElementById('modModalCancel');
  var ctx = {form: null, needReason: false, reasonField: 'reason'};

  function open(btn) {
    ctx.form = btn.closest('form');
    ctx.needReason = btn.dataset.needReason === '1';
    ctx.reasonField = btn.dataset.reasonField || 'reason';
    titleEl.textContent = btn.dataset.title || '确认操作';
    bodyEl.textContent = btn.dataset.body || '';
    iconEl.textContent = btn.dataset.icon || '⚠️';
    okBtn.textContent = btn.dataset.okText || '确认';
    okBtn.className = 'mod-btn ' + (btn.dataset.okClass || 'btn-danger');
    okBtn.disabled = false;
    reasonWrap.hidden = !ctx.needReason;
    reasonEl.value = '';
    mask.hidden = false;
    document.body.classList.add('modal-lock');
    if (ctx.needReason) setTimeout(function () { reasonEl.focus(); }, 80);
  }
  function close() {
    mask.hidden = true;
    document.body.classList.remove('modal-lock');
    ctx.form = null;
  }
  function confirm() {
    if (ctx.needReason) {
      var v = reasonEl.value.trim();
      var existing = ctx.form.querySelector('input[name="' + ctx.reasonField + '"]');
      if (!existing) {
        existing = document.createElement('input');
        existing.type = 'hidden';
        existing.name = ctx.reasonField;
        ctx.form.appendChild(existing);
      }
      existing.value = v;
    }
    okBtn.disabled = true;
    if (ctx.form) ctx.form.submit(); else close();
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.js-confirm');
    if (b) { e.preventDefault(); open(b); }
  });
  okBtn.addEventListener('click', confirm);
  cancelBtn.addEventListener('click', close);
  mask.addEventListener('click', function (e) { if (e.target === mask) close(); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !mask.hidden) close();
  });
})();

/* 审核历史动作筛选（第三轮迁移：原 moderation.html 内联 onchange 外移）。
   下拉框 change 时跳转 ?tab=history&act=<value>，与模板分页链接口径一致。 */
(function () {
  'use strict';
  document.addEventListener('change', function (e) {
    if (e.target && e.target.id === 'history-act-filter') {
      window.location.href = '?tab=history&act=' + encodeURIComponent(e.target.value);
    }
  });
})();
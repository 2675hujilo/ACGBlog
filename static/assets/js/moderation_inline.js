/* Bug11 文件头注释
 * 审核页脚本：自定义确认弹窗（替代原生 confirm）、理由填写、标签切换与异步审核。
 * js-confirm 按钮统一走弹窗，可带 data-need-reason 收集理由随表单提交。
 */
/* Bug8：站内统一确认弹窗，取代 window.confirm / alert。
   //> 该行执行对应的脚本逻辑（结合上下文理解）
   触发方式：在 <form> 内放置 .js-confirm 按钮（type=button），
   //> 该行执行对应的脚本逻辑（结合上下文理解）
   通过 data-* 描述标题/正文/图标/确认按钮文案，需要理由时 data-need-reason=1。 */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
  //> 声明变量「mask」（mask），用于保存对应数据，保存 DOM/窗口相关对象
  var mask = document.getElementById('modModal');
  //> 条件判断：满足括号内条件时执行对应分支
  if (!mask) return;
  //> 声明变量「titleEl」（title el），用于保存对应数据，保存 DOM/窗口相关对象
  var titleEl = document.getElementById('modModalTitle'),
      //> 按 id 获取单个元素，不存在时返回 null
      bodyEl = document.getElementById('modModalBody'),
      //> 按 id 获取单个元素，不存在时返回 null
      iconEl = document.getElementById('modModalIcon'),
      //> 按 id 获取单个元素，不存在时返回 null
      reasonWrap = document.getElementById('modModalReasonWrap'),
      //> 按 id 获取单个元素，不存在时返回 null
      reasonEl = document.getElementById('modModalReason'),
      //> 按 id 获取单个元素，不存在时返回 null
      okBtn = document.getElementById('modModalOk'),
      //> 按 id 获取单个元素，不存在时返回 null
      cancelBtn = document.getElementById('modModalCancel');
  //> 声明变量「ctx」（ctx），用于保存对应数据
  var ctx = {form: null, needReason: false, reasonField: 'reason'};

  // =========================================================
  // 【函数】open
  // 功能：打开相关逻辑（open）
  // 参数：
  //   - btn：传入的参数（含义结合调用处与函数体）
  // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
  // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
  // =========================================================
  function open(btn) {
    //> 沿 DOM 向上查找最近的匹配祖先（含自身），常用于事件委托
    ctx.form = btn.closest('form');
    //> 读写元素的 data-* 自定义数据属性
    ctx.needReason = btn.dataset.needReason === '1';
    //> 读写元素的 data-* 自定义数据属性
    ctx.reasonField = btn.dataset.reasonField || 'reason';
    //> 读写纯文本内容，不解析 HTML，可防 XSS
    titleEl.textContent = btn.dataset.title || '确认操作';
    //> 读写纯文本内容，不解析 HTML，可防 XSS
    bodyEl.textContent = btn.dataset.body || '';
    //> 读写纯文本内容，不解析 HTML，可防 XSS
    iconEl.textContent = btn.dataset.icon || '⚠️';
    //> 读写纯文本内容，不解析 HTML，可防 XSS
    okBtn.textContent = btn.dataset.okText || '确认';
    //> 读写元素的 data-* 自定义数据属性
    okBtn.className = 'mod-btn ' + (btn.dataset.okClass || 'btn-danger');
    //> 给「okBtn.disabled」赋值，更新其保存的状态
    okBtn.disabled = false;
    //> 给「reasonWrap.hidden」赋值，更新其保存的状态
    reasonWrap.hidden = !ctx.needReason;
    //> 给「reasonEl.value」赋值，更新其保存的状态
    reasonEl.value = '';
    //> 给「mask.hidden」赋值，更新其保存的状态
    mask.hidden = false;
    //> 为元素添加一个或多个样式类
    document.body.classList.add('modal-lock');
    //> 条件判断：满足括号内条件时执行对应分支
    if (ctx.needReason) setTimeout(function () { reasonEl.focus(); }, 80);
  //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
  }
  // =========================================================
  // 【函数】close
  // 功能：关闭相关逻辑（close）
  // 参数：无
  // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
  // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
  // =========================================================
  function close() {
    //> 给「mask.hidden」赋值，更新其保存的状态
    mask.hidden = true;
    //> 移除元素的一个或多个样式类
    document.body.classList.remove('modal-lock');
    //> 给「ctx.form」赋值，更新其保存的状态
    ctx.form = null;
  //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
  }
  // =========================================================
  // 【函数】confirm
  // 功能：处理「confirm」相关逻辑（moderation_inline）
  // 参数：无
  // 返回：无显式返回值（undefined），多以副作用（DOM/事件）为主
  // 注意：保持纯原生实现；修改时勿影响其它已初始化逻辑
  // =========================================================
  function confirm() {
    //> 条件判断：满足括号内条件时执行对应分支
    if (ctx.needReason) {
      //> 声明变量「v」（v），用于保存对应数据
      var v = reasonEl.value.trim();
      //> 声明变量「existing」（existing），用于保存对应数据
      var existing = ctx.form.querySelector('input[name="' + ctx.reasonField + '"]');
      //> 条件判断：满足括号内条件时执行对应分支
      if (!existing) {
        //> 创建新的 DOM 元素节点，后续需挂载到文档才显示
        existing = document.createElement('input');
        //> 给「existing.type」赋值，更新其保存的状态
        existing.type = 'hidden';
        //> 给「existing.name」赋值，更新其保存的状态
        existing.name = ctx.reasonField;
        //> 把子节点追加到当前元素内部末尾
        ctx.form.appendChild(existing);
      //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
      }
      //> 给「existing.value」赋值，更新其保存的状态
      existing.value = v;
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
    //> 给「okBtn.disabled」赋值，更新其保存的状态
    okBtn.disabled = true;
    //> 条件判断：满足括号内条件时执行对应分支
    if (ctx.form) ctx.form.submit(); else close();
  //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
  }
  //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
  document.addEventListener('click', function (e) {
    //> 声明变量「b」（b），用于保存对应数据
    var b = e.target.closest('.js-confirm');
    //> 条件判断：满足括号内条件时执行对应分支
    if (b) { e.preventDefault(); open(b); }
  //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
  });
  //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
  okBtn.addEventListener('click', confirm);
  //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
  cancelBtn.addEventListener('click', close);
  //> 绑定「click」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
  mask.addEventListener('click', function (e) { if (e.target === mask) close(); });
  //> 绑定「keydown」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
  document.addEventListener('keydown', function (e) {
    //> 条件判断：满足括号内条件时执行对应分支
    if (e.key === 'Escape' && !mask.hidden) close();
  //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
  });
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

/* 审核历史动作筛选（第三轮迁移：原 moderation.html 内联 onchange 外移）。
   //> 该行执行对应的脚本逻辑（结合上下文理解）
   下拉框 change 时跳转 ?tab=history&act=<value>，与模板分页链接口径一致。 */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
  //> 该行执行对应的脚本逻辑（结合上下文理解）
  'use strict';
  //> 绑定「change」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
  document.addEventListener('change', function (e) {
    //> 条件判断：满足括号内条件时执行对应分支
    if (e.target && e.target.id === 'history-act-filter') {
      //> 对 URL 参数做编码，防止特殊字符破坏链接或被注入
      window.location.href = '?tab=history&act=' + encodeURIComponent(e.target.value);
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    }
  //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
  });
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();
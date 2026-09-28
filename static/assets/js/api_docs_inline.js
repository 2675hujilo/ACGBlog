/* 70. 文档页搜索过滤：按 data-key 实时过滤端点卡片 */
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 声明变量「input」（input），用于保存对应数据，保存 DOM/窗口相关对象
    var input = document.getElementById('apidocs-search');
    //> 声明变量「cards」（cards），用于保存对应数据，保存 DOM/窗口相关对象
    var cards = document.querySelectorAll('.api-card');
    //> 条件判断：满足括号内条件时执行对应分支
    if (!input) return;
    //> 绑定「input」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    input.addEventListener('input', function () {
        //> 声明变量「q」（q），用于保存对应数据
        var q = input.value.trim().toLowerCase();
        //> 遍历数组/类数组中的每一项并执行回调
        cards.forEach(function (c) {
            //> 读写元素的 data-* 自定义数据属性
            c.style.display = c.dataset.key.toLowerCase().indexOf(q) >= 0 ? '' : 'none';
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        });
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();
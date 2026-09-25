/* 70. 文档页搜索过滤：按 data-key 实时过滤端点卡片 */
(function () {
    var input = document.getElementById('apidocs-search');
    var cards = document.querySelectorAll('.api-card');
    if (!input) return;
    input.addEventListener('input', function () {
        var q = input.value.trim().toLowerCase();
        cards.forEach(function (c) {
            c.style.display = c.dataset.key.toLowerCase().indexOf(q) >= 0 ? '' : 'none';
        });
    });
})();
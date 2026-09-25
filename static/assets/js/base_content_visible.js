/* 兜底：确保页面内容立即可见，防止入场动画异常导致空白 */
(function(){
    function showAll(){
        document.querySelectorAll('.scroll-fade-in, .animate-in, .fade-scroll').forEach(function(el){
            el.classList.add('visible');
        });
        document.body.classList.add('page-enter-done');
    }
    if(document.readyState === 'loading'){
        document.addEventListener('DOMContentLoaded', showAll);
    } else {
        showAll();
    }
    setTimeout(showAll, 500);
})();
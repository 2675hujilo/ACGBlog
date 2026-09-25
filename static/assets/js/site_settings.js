/* ============================================================
 * site_settings.js —— 站点设置页交互（工单 15）
 * 1) 品牌区实时预览（Logo / 名称 / 副标题随输入更新）；
 * 2) 前端基础校验：网站名必填，给出萌系提示，不做空提交。
 * ============================================================ */
(function () {
    'use strict';

    var form = document.getElementById('site-settings-form');
    if (!form) return;

    var logoInput = document.getElementById('id_logo_emoji');
    var nameInput = document.getElementById('id_site_name');
    var taglineInput = document.getElementById('id_tagline');
    var pvLogo = document.getElementById('pv-logo');
    var pvName = document.getElementById('pv-name');
    var pvTagline = document.getElementById('pv-tagline');

    /* ---- 实时预览：输入即更新 ---- */
    logoInput.addEventListener('input', function () {
        pvLogo.textContent = logoInput.value.trim() || '🌸';
    });
    nameInput.addEventListener('input', function () {
        pvName.textContent = nameInput.value.trim() || '萌语博客';
    });
    taglineInput.addEventListener('input', function () {
        pvTagline.textContent = taglineInput.value.trim();
    });

    /* ---- 提交前校验：网站名不能为空 ---- */
    form.addEventListener('submit', function (e) {
        if (!nameInput.value.trim()) {
            e.preventDefault();
            nameInput.focus();
            if (window.moeToast) {
                window.moeToast('网站名称不能为空喵~ (｡•́︿•̀｡)');
            } else {
                nameInput.setCustomValidity('网站名称不能为空喵~');
                nameInput.reportValidity();
            }
        }
    });
})();

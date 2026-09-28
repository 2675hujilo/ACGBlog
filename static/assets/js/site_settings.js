/* ============================================================================
 * site_settings.js —— 站点设置页交互（工单 15，管理员）
 * ----------------------------------------------------------------------------
 * 适用页面：站点设置表单 #site-settings-form。
 *
 * 功能：
 *   1) 品牌区实时预览：Logo emoji / 站点名称 / 副标题随输入即时更新到预览区
 *      （#pv-logo / #pv-name / #pv-tagline），所见即所得；
 *   2) 提交前前端基础校验：网站名称必填，为空时阻止提交、聚焦输入框并给出
 *      萌系提示，避免无意义的空提交（后端仍会再次校验，前端仅为体验）。
 *
 * 依赖：moeToast（缺失时降级为浏览器原生 setCustomValidity 提示）。
 * ----------------------------------------------------------------------------
 * 排错速查：
 *   · 预览节点 #pv-logo / #pv-name / #pv-tagline 必须与表单字段一一对应，模板
 *     缺失预览节点会报错，新增字段时同步补预览；
 *   · 空值兜底（🌸 / 萌语博客）仅用于预览，不会写回表单或提交；
 *   · 前端必填校验只是体验层，后端站点设置视图仍会再次校验，不可省略后端；
 *   · moeToast 缺失时降级为 setCustomValidity 原生气泡，两条路径都要可用；
 *   · 相关文件：站点设置模板、后端站点设置视图（SiteInfo 单例）、
 *     site_settings.css（本页样式）。
 * ============================================================================ */
(function () {
    'use strict';

    var form = document.getElementById('site-settings-form');
    if (!form) return;

    // 表单输入元素
    var logoInput = document.getElementById('id_logo_emoji');
    var nameInput = document.getElementById('id_site_name');
    var taglineInput = document.getElementById('id_tagline');

    // 预览区元素
    var pvLogo = document.getElementById('pv-logo');
    var pvName = document.getElementById('pv-name');
    var pvTagline = document.getElementById('pv-tagline');

    // ---- 实时预览：输入即更新（空值时给默认占位）----
    logoInput.addEventListener('input', function () {
        pvLogo.textContent = logoInput.value.trim() || '🌸';
    });
    nameInput.addEventListener('input', function () {
        pvName.textContent = nameInput.value.trim() || '萌语博客';
    });
    taglineInput.addEventListener('input', function () {
        pvTagline.textContent = taglineInput.value.trim();
    });

    // ---- 提交前校验：网站名不能为空 ----
    form.addEventListener('submit', function (e) {
        if (!nameInput.value.trim()) {
            // 阻止空提交并聚焦到名称输入框
            e.preventDefault();
            nameInput.focus();
            if (window.moeToast) {
                // 萌系 toast 提示
                window.moeToast('网站名称不能为空喵~ (｡•́︿•̀｡)');
            } else {
                // 降级：原生校验气泡
                nameInput.setCustomValidity('网站名称不能为空喵~');
                nameInput.reportValidity();
            }
        }
    });
})();

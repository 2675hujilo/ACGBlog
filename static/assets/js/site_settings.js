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
//> 该行执行对应的脚本逻辑（结合上下文理解）
(function () {
    //> 该行执行对应的脚本逻辑（结合上下文理解）
    'use strict';

    //> 声明变量「form」（form），用于保存对应数据，保存 DOM/窗口相关对象
    var form = document.getElementById('site-settings-form');
    //> 条件判断：满足括号内条件时执行对应分支
    if (!form) return;

    // 表单输入元素
    //> 声明变量「logoInput」（logo input），用于保存对应数据，保存 DOM/窗口相关对象
    var logoInput = document.getElementById('id_logo_emoji');
    //> 声明变量「nameInput」（name input），用于保存对应数据，保存 DOM/窗口相关对象
    var nameInput = document.getElementById('id_site_name');
    //> 声明变量「taglineInput」（tagline input），用于保存对应数据，保存 DOM/窗口相关对象
    var taglineInput = document.getElementById('id_tagline');

    // 预览区元素
    //> 声明变量「pvLogo」（pv logo），用于保存对应数据，保存 DOM/窗口相关对象
    var pvLogo = document.getElementById('pv-logo');
    //> 声明变量「pvName」（pv name），用于保存对应数据，保存 DOM/窗口相关对象
    var pvName = document.getElementById('pv-name');
    //> 声明变量「pvTagline」（pv tagline），用于保存对应数据，保存 DOM/窗口相关对象
    var pvTagline = document.getElementById('pv-tagline');

    // ---- 实时预览：输入即更新（空值时给默认占位）----
    //> 绑定「input」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    logoInput.addEventListener('input', function () {
        //> 读写纯文本内容，不解析 HTML，可防 XSS
        pvLogo.textContent = logoInput.value.trim() || '🌸';
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
    //> 绑定「input」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    nameInput.addEventListener('input', function () {
        //> 读写纯文本内容，不解析 HTML，可防 XSS
        pvName.textContent = nameInput.value.trim() || '萌语博客';
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
    //> 绑定「input」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    taglineInput.addEventListener('input', function () {
        //> 读写纯文本内容，不解析 HTML，可防 XSS
        pvTagline.textContent = taglineInput.value.trim();
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });

    // ---- 提交前校验：网站名不能为空 ----
    //> 绑定「submit」事件监听器，事件触发时执行回调（passive 可提升滚动性能）
    form.addEventListener('submit', function (e) {
        //> 条件判断：满足括号内条件时执行对应分支
        if (!nameInput.value.trim()) {
            // 阻止空提交并聚焦到名称输入框
            //> 阻止事件的默认行为（如表单提交、链接跳转）
            e.preventDefault();
            //> 操作「nameInput」的相关方法/属性
            nameInput.focus();
            //> 条件判断：满足括号内条件时执行对应分支
            if (window.moeToast) {
                // 萌系 toast 提示
                //> 操作「window」的相关方法/属性
                window.moeToast('网站名称不能为空喵~ (｡•́︿•̀｡)');
            //> 以上条件都不满足时执行的兜底分支
            } else {
                // 降级：原生校验气泡
                //> 操作「nameInput」的相关方法/属性
                nameInput.setCustomValidity('网站名称不能为空喵~');
                //> 操作「nameInput」的相关方法/属性
                nameInput.reportValidity();
            //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
            }
        //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
        }
    //> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
    });
//> 闭合/分隔符：结束当前代码块或回调作用域，需与开头括号正确配对
})();

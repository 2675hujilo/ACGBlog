# -*- coding: utf-8 -*-
"""HTML 安全净化共享组件。

集中维护 bleach 的 CSS 净化策略（``CSSSanitizer``），供正文净化
（``blog.views.sanitize_html``）与 DRF 序列化器（``blog.serializers``）复用，
避免各处重复配置，同时消除 bleach 6 在允许 ``style`` 属性却未设置
``css_sanitizer`` 时抛出的 ``NoCssSanitizerWarning``。

``CSSSanitizer`` 基于 tinycss2 解析内联样式，仅保留白名单内的安全属性，
默认即会剥离 ``expression()``、``url(javascript:...)`` 等危险 CSS。
"""
from bleach.css_sanitizer import CSSSanitizer

# 允许出现在元素 style="" 中的安全 CSS 属性白名单。
# 覆盖 CKEditor 常用的排版 / 对齐 / 尺寸 / 颜色 / 边距 / 圆角等需求；
# 任何不在列表内的属性（含 expression、behavior、-moz-binding 等）一律移除。
ALLOWED_CSS_PROPERTIES = [
    # 尺寸
    'width', 'height', 'max-width', 'max-height', 'min-width', 'min-height',
    # 文本排版
    'text-align', 'vertical-align', 'line-height', 'text-indent',
    'letter-spacing', 'white-space', 'word-break', 'overflow-wrap',
    # 颜色 / 背景
    'color', 'background', 'background-color',
    # 边框 / 圆角
    'border', 'border-width', 'border-style', 'border-color',
    'border-radius', 'border-collapse',
    # 内 / 外边距
    'padding', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
    'margin', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
    # 字体
    'font', 'font-weight', 'font-style', 'font-size', 'font-family',
    'text-decoration', 'text-transform',
    # 布局（基础）
    'float', 'clear', 'display', 'object-fit', 'table-layout',
]

# 共享的萌系博客 CSS 净化器实例（线程安全，可全局复用）
MoeCSSSanitizer = CSSSanitizer(allowed_css_properties=ALLOWED_CSS_PROPERTIES)

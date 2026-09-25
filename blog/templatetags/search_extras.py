"""搜索关键词高亮模板标签库（第4轮 C3）。

提供过滤器 ``highlight(value, keyword)``：把搜索结果标题 / 摘要中的
关键词包裹为 ``<mark class="search-highlight">关键词</mark>``，
供模板 ``{% load search_extras %}`` 后使用 ``{{ value|highlight:keyword }}``。

安全要点：
    先对原文与关键词分别做 ``django.utils.html.escape`` HTML 转义，
    再用不区分大小写的正则替换，最后 ``mark_safe`` 输出。
    即使用户输入 ``<script>`` 等内容也会被转义为纯文本，杜绝 XSS。
"""
import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name='highlight')
def highlight(value, keyword):
    """把 ``value`` 中出现的 ``keyword`` 关键词高亮为 ``<mark class="search-highlight">``。

    Args:
        value: 待高亮的原始文本（如文章标题 / 摘要）。
        keyword: 搜索关键词；为空或 None 时仅返回转义后的原文。

    Returns:
        SafeString: 转义后并把命中关键词包上 ``<mark class="search-highlight">``
        的安全 HTML 字符串。
    """
    # None 兜底为空字符串
    if value is None:
        value = ''
    text = str(value)
    keyword = '' if keyword is None else str(keyword).strip()

    # 先整体转义原文，确保正文里的 < > & 等都变成实体，杜绝 XSS
    escaped = escape(text)
    if not keyword:
        return mark_safe(escaped)

    # 关键词同样转义；re.escape 兜住正则元字符，避免关键词带 . * ? 等导致正则错误
    pattern = re.compile(re.escape(escape(keyword)), re.IGNORECASE)
    # 用我们自己可控的 <mark class="search-highlight"> 包裹命中片段
    result = pattern.sub(
        lambda m: '<mark class="search-highlight">' + m.group(0) + '</mark>',
        escaped)
    return mark_safe(result)

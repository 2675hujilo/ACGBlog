"""blog 自定义模板标签库。

目前提供：
- ``highlight`` 过滤器：在搜索结果中把关键词包一层 ``<mark>`` 标签用于高亮。

安全要点：
    过滤器内部先对【原文】和【关键词】分别做 ``escape`` HTML 转义，
    再用不区分大小写的正则替换，最后才 ``mark_safe``。
    这样即使用户输入 ``<script>`` 之类的内容，也会被转义为纯文本，
    绝不会把关键词当成 HTML 注入到页面里。
"""
import re
from pathlib import Path
from urllib.parse import unquote

from django import template
from django.conf import settings
from django.core.cache import cache
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils import timezone

register = template.Library()


# 迭代#247: is_new过滤器docstring完善
@register.filter(name='is_new')
def is_new(created_at):
    """12. 判断文章是否为"新"：发布时间在最近 24 小时内。

    Args:
        created_at: 文章的 created_at  datetime。

    Returns:
        bool: 24 小时内为 True。
    """
    if not created_at:
        return False
    return (timezone.now() - created_at).total_seconds() < 86400


# 迭代#248: time_ago过滤器docstring完善
@register.filter(name='time_ago')
def time_ago(dt):
    """把 datetime 格式化为相对时间字符串（如"3天前"/"2小时前"）。

    Args:
        dt: 待格式化的 datetime（应带时区）。

    Returns:
        str: 中文相对时间描述。
    """
    if not dt:
        return ''
    diff = timezone.now() - dt
    secs = diff.total_seconds()
    if secs < 60:
        return '刚刚'
    if secs < 3600:
        return f'{int(secs // 60)}分钟前'
    if secs < 86400:
        return f'{int(secs // 3600)}小时前'
    if secs < 86400 * 30:
        return f'{int(secs // 86400)}天前'
    if secs < 86400 * 365:
        return f'{int(secs // 86400 // 30)}个月前'
    return f'{int(secs // 86400 // 365)}年前'


# 迭代#249: highlight过滤器docstring完善
@register.filter(name='highlight')
def highlight(text, query):
    """把 ``text`` 中出现的 ``query`` 关键词高亮为 ``<mark>关键词</mark>``。

    Args:
        text: 待高亮的原始文本（如文章标题 / 摘要）。
        query: 搜索关键词，空串或 None 时原样返回转义后的文本。

    Returns:
        SafeString: 转义后并把关键词包上 <mark> 的安全 HTML 字符串。
    """
    # None 兜底为空字符串
    if text is None:
        text = ''
    text = str(text)
    query = '' if query is None else str(query).strip()

    # 先整体转义原文，确保正文里的 < > & 等都变成实体，杜绝 XSS
    escaped = escape(text)
    if not query:
        return mark_safe(escaped)

    # 关键词同样转义（转义不会改变中英文 / 数字等普通字符），
    # re.escape 再兜住正则元字符，避免关键词里带 . * ? 等导致正则错误
    pattern = re.compile(re.escape(escape(query)), re.IGNORECASE)
    # 用转义后的 <mark> 替换命中片段；因为 escaped 已是纯文本安全态，
    # 这里主动写入的 <mark> 标签是我们自己可控的，最后 mark_safe 渲染
    result = pattern.sub(lambda m: '<mark class="search-highlight">' + m.group(0) + '</mark>', escaped)
    return mark_safe(result)


# 迭代#250: lazy_images过滤器docstring完善
@register.filter(name='lazy_images', is_safe=True)
def lazy_images(html):
    """给富文本正文中所有 <img> 标签注入 loading="lazy"。

    正文经 bleach 净化后由模板 |safe 输出，这里再用正则给每个尚未带
    loading 属性的 <img> 补上懒加载，避免首屏外的图片阻塞首屏渲染。
    已显式带 loading 的图片（如首屏封面）不重复添加。
    """
    import re
    def _add(m):
        tag = m.group(0)
        if 'loading=' in tag:
            return tag
        return tag[:-1].rstrip('>') + ' loading="lazy">'
    return re.sub(r'<img\b[^>]*>', _add, html)


@register.filter(name='file_url')
def file_url(fieldfile):
    """安全返回 FileField/ImageField 的 url；未关联文件时返回空串。

    模板里直接写 ``article.cover_image.url``，当没有上传文件时
    FieldFile.url 会抛 ValueError 导致整页 500，故用本过滤器兜底。
    """
    try:
        return fieldfile.url
    except (ValueError, AttributeError):
        return ''


# 命中这些路径 / 文件名片段的图片，基本是编辑器 UI 图标而非正文配图（bug4）
_BAD_IMG_SRC = re.compile(
    r'(placeholder|empty[-_]?state|/blank|/static/|ckeditor|/plugins?/|smilie?y|'
    r'sprite|/icons?/|[-_/]icon|loader|spinner|toolbar|/button|emoji|/gfx/|[-_]logo\.)',
    re.IGNORECASE)
_IMG_TAG_RE = re.compile(r'<img\b[^>]*>', re.IGNORECASE | re.DOTALL)
_IMG_SRC_RE = re.compile(r'\bsrc=["\']([^"\']+)["\']', re.IGNORECASE)
_IMG_W_RE = re.compile(r'\bwidth=["\']?(\d+)', re.IGNORECASE)
_IMG_H_RE = re.compile(r'\bheight=["\']?(\d+)', re.IGNORECASE)
_IMG_CLS_RE = re.compile(r'\bclass=["\']([^"\']+)', re.IGNORECASE)


def _local_media_path(src):
    """把图片 URL 映射为本地 MEDIA_ROOT 下的文件路径；非本站 media 资源返回 None。"""
    media_url = settings.MEDIA_URL or '/media/'
    rel = None
    if src.startswith(media_url):
        rel = src[len(media_url):]
    else:
        marker = '/' + media_url.strip('/') + '/'
        i = src.find(marker)
        if i >= 0:
            rel = src[i + len(marker):]
    if rel is None:
        return None
    rel = rel.split('?', 1)[0].split('#', 1)[0]
    return Path(settings.MEDIA_ROOT) / unquote(rel)


def _image_pixel_size(src):
    """用 Pillow 读取本地 media 图片的真实像素尺寸，结果按 src 缓存 24h。

    用于剔除“宽但极矮”的编辑器工具条截图等伪配图。无法判定时返回 None。
    """
    cache_key = 'blog:imgdim:' + src
    cached = cache.get(cache_key)
    if cached is not None:
        return tuple(cached) if cached else None
    size = None
    path = _local_media_path(src)
    if path is not None and path.is_file():
        try:
            from PIL import Image
            with Image.open(path) as im:
                size = im.size
        except Exception:
            size = None
    cache.set(cache_key, list(size) if size else False, 86400)
    return size


def _portable_media_src(src):
    """把指向任意 host:port 的本站 media 绝对 URL 改写为相对路径。

    历史正文里图片是“创建时端口”的绝对地址（如 http://127.0.0.1:8032/media/..），
    一旦换端口 / 换域名图片就会全部失效。统一改成 /media/.. 相对地址即可随当前
    host 访问。外部非 media 的 URL 原样返回。
    """
    media_seg = (settings.MEDIA_URL or '/media/').strip('/')
    pattern = re.compile(
        r'https?://[^\s"\'<>]*?/(' + re.escape(media_seg) + r'/[^\s"\'<>]+)',
        re.IGNORECASE)
    return pattern.sub(lambda m: '/' + m.group(1), src)


@register.filter(name='portable_media')
def portable_media(html):
    """对整段正文 HTML 执行 media 绝对 URL 相对化（详情页渲染前使用，bug4 增强）。"""
    if not html:
        return ''
    media_seg = (settings.MEDIA_URL or '/media/').strip('/')
    pattern = re.compile(
        r'https?://[^\s"\'<>]*?/(' + re.escape(media_seg) + r'/[^\s"\'<>]+)',
        re.IGNORECASE)
    return pattern.sub(lambda m: '/' + m.group(1), str(html))


@register.filter(name='body_first_image')
def body_first_image(html):
    """提取富文本正文中第一张“真实配图”的 src（bug4）。

    列表缩略图优先级：文章封面 → 正文首图 → 无图则隐藏。
    取图时会智能跳过：
      1. data: 内联图、编辑器 / 插件 / 图标 / 表情 / 工具条等路径；
      2. 显式声明宽或高小于 80px 的图片；
      3. class 含 icon/smiley/emoji/sprite 的图片；
      4. 本站 media 图中真实像素宽<160 或 高<100 的“工具条细条”（Pillow 判定）。
    按文档顺序返回第一张通过全部检查的图片，找不到返回空字符串。
    """
    if not html:
        return ''
    for tag_match in _IMG_TAG_RE.finditer(str(html)):
        tag = tag_match.group(0)
        src_match = _IMG_SRC_RE.search(tag)
        if not src_match:
            continue
        src = src_match.group(1)
        if not src or src.startswith('data:'):
            continue
        # 历史绝对 URL（带旧端口/域名）先相对化，保证换端口后仍可加载
        src = _portable_media_src(src)
        low = src.split('?', 1)[0].split('#', 1)[0]
        if _BAD_IMG_SRC.search(low):
            continue
        # 显式声明的小尺寸
        wm, hm = _IMG_W_RE.search(tag), _IMG_H_RE.search(tag)
        if (wm and int(wm.group(1)) < 80) or (hm and int(hm.group(1)) < 80):
            continue
        # class 上的图标 / 表情信号
        cm = _IMG_CLS_RE.search(tag)
        if cm and re.search(r'smilie?y|icon|emoji|sprite', cm.group(1), re.IGNORECASE):
            continue
        # 本站 media：用真实像素尺寸剔除编辑器工具条 / 细长截图
        if _local_media_path(src) is not None:
            size = _image_pixel_size(src)
            if size is not None:
                w, h = size
                ratio = w / h if h else 99
                # 太小、过宽（工具条 w/h>2.6）、过窄（h/w>4）都不算正文配图
                if w < 160 or h < 100 or ratio > 2.6 or (1 / ratio if ratio else 0) > 4:
                    continue
        return src
    return ''


@register.simple_tag(name='smart_page_range')
def smart_page_range(current, total, span=3):
    """智能页码窗口（bug6）。

    始终包含【首页 1】【尾页 total】以及【当前页左右各 span 页】；
    相邻不连续处用整数 ``0`` 作为省略号占位，模板遇到 0 渲染不可点击
    的「…」。

    示例（total=207, current=100, span=3）::

        [1, 0, 97, 98, 99, 100, 101, 102, 103, 0, 207]
    """
    try:
        current = int(current)
        total = int(total)
        span = int(span)
    except (TypeError, ValueError):
        return []
    if total <= 1:
        return []
    # 收集必须展示的页码（集合自动去重）
    pages = {1, total}
    for n in range(current - span, current + span + 1):
        if 1 <= n <= total:
            pages.add(n)
    ordered = sorted(pages)
    # 在缺口处插入省略号标记 0
    result = []
    prev = None
    for n in ordered:
        if prev is not None and n - prev > 1:
            result.append(0)
        result.append(n)
        prev = n
    return result

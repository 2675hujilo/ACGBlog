"""blog 自定义模板标签库。

目前提供：
- ``highlight`` 过滤器：在搜索结果中把关键词包一层 ``<mark>`` 标签用于高亮。
- ``format`` 过滤器：给文案注册表（``MSG``）里带占位符的文案填参。

安全要点：
    过滤器内部先对【原文】和【关键词】分别做 ``escape`` HTML 转义，
    再用不区分大小写的正则替换，最后才 ``mark_safe``。
    这样即使用户输入 ``<script>`` 之类的内容，也会被转义为纯文本，
    绝不会把关键词当成 HTML 注入到页面里。
"""
#: 导入模块「re」，供本文件后续使用
import re
#: 从模块「pathlib」导入所需对象
from pathlib import Path
#: 从模块「urllib.parse」导入所需对象
from urllib.parse import unquote

#: 从模块「django」导入所需对象
from django import template
#: 从模块「django.conf」导入所需对象
from django.conf import settings
#: 从模块「django.core.cache」导入所需对象
from django.core.cache import cache
#: 从模块「django.utils.html」导入所需对象
from django.utils.html import escape
#: 从模块「django.utils.safestring」导入所需对象
from django.utils.safestring import mark_safe
#: 从模块「django.utils」导入所需对象
from django.utils import timezone

#: 定义变量「register」，保存对应数据
register = template.Library()


# 迭代#247: is_new过滤器docstring完善
#: 装饰器：为下一个定义附加「register.filter(name='is_new')」行为（权限、缓存、注册信号等）
@register.filter(name='is_new')
def is_new(created_at):
    """12. 判断文章是否为"新"：发布时间在最近 24 小时内。

    Args:
        created_at: 文章的 created_at  datetime。

    Returns:
        bool: 24 小时内为 True。
    """
    #: 条件判断：条件成立时执行该分支
    if not created_at:
        #: 返回结果并结束当前函数
        return False
    #: 返回结果并结束当前函数
    return (timezone.now() - created_at).total_seconds() < 86400


# 迭代#248: time_ago过滤器docstring完善
#: 装饰器：为下一个定义附加「register.filter(name='time_ago')」行为（权限、缓存、注册信号等）
@register.filter(name='time_ago')
def time_ago(dt):
    """把 datetime 格式化为相对时间字符串（如"3天前"/"2小时前"）。

    Args:
        dt: 待格式化的 datetime（应带时区）。

    Returns:
        str: 中文相对时间描述。
    """
    #: 条件判断：条件成立时执行该分支
    if not dt:
        #: 返回结果并结束当前函数
        return ''
    #: 获取当前时间（时区感知），统一时间口径
    diff = timezone.now() - dt
    #: 定义变量「secs」，保存对应数据
    secs = diff.total_seconds()
    #: 条件判断：条件成立时执行该分支
    if secs < 60:
        #: 返回结果并结束当前函数
        return '刚刚'
    #: 条件判断：条件成立时执行该分支
    if secs < 3600:
        #: 返回结果并结束当前函数
        return f'{int(secs // 60)}分钟前'
    #: 条件判断：条件成立时执行该分支
    if secs < 86400:
        #: 返回结果并结束当前函数
        return f'{int(secs // 3600)}小时前'
    #: 条件判断：条件成立时执行该分支
    if secs < 86400 * 30:
        #: 返回结果并结束当前函数
        return f'{int(secs // 86400)}天前'
    #: 条件判断：条件成立时执行该分支
    if secs < 86400 * 365:
        #: 返回结果并结束当前函数
        return f'{int(secs // 86400 // 30)}个月前'
    #: 返回结果并结束当前函数
    return f'{int(secs // 86400 // 365)}年前'


#: 装饰器：为下一个定义附加「register.filter(name='time_until')」行为（权限、缓存、注册信号等）
@register.filter(name='time_until')
def time_until(delta):
    """把 timedelta 格式化为「还有多久」的中文倒计时文案（Bug9 定时投稿提示用）。

    与 ``time_ago`` 互为反向：``time_ago`` 描述过去，``time_until`` 描述未来。

    Args:
        delta: ``datetime.timedelta``（通常为 ``published_at - now``）。

    Returns:
        str: 形如「3 分钟」「2 小时 15 分」「1 天 3 小时」的简洁倒计时；
             已过时（<=0）返回「即将」。
    """
    #: 条件判断：条件成立时执行该分支
    if delta is None:
        #: 返回结果并结束当前函数
        return ''
    #: 定义变量「secs」，保存对应数据
    secs = int(delta.total_seconds())
    #: 条件判断：条件成立时执行该分支
    if secs <= 0:
        #: 返回结果并结束当前函数
        return '即将'
    #: 该行执行对应逻辑（结合上下文理解）
    days, rem = divmod(secs, 86400)
    #: 该行执行对应逻辑（结合上下文理解）
    hours, rem = divmod(rem, 3600)
    #: 定义变量「minutes」，保存对应数据
    minutes = rem // 60
    #: 条件判断：条件成立时执行该分支
    if days:
        #: 返回结果并结束当前函数
        return f'{days} 天 {hours} 小时' if hours else f'{days} 天'
    #: 条件判断：条件成立时执行该分支
    if hours:
        #: 返回结果并结束当前函数
        return f'{hours} 小时 {minutes} 分' if minutes else f'{hours} 小时'
    #: 条件判断：条件成立时执行该分支
    if minutes:
        #: 返回结果并结束当前函数
        return f'{minutes} 分钟'
    #: 返回结果并结束当前函数
    return f'{secs} 秒'


#: 装饰器：为下一个定义附加「register.filter(name='msgfmt', is_safe=True)」行为（权限、缓存、注册信号等）
@register.filter(name='msgfmt', is_safe=True)
def msgfmt(template_text, a1=None, a2=None, a3=None):
    """给带占位符的文案填参（供 ``MSG`` 命名空间在模板侧使用）。

    背景与命名
    ----------
    Django **自带一个名为 ``format`` 的内置过滤器**（``date|format:"Y-m-d"`` 那种），
    自定义同名过滤器会触发 ``TemplateSyntaxError``。实测踩过两次坑，务必记住：

      1. 名字不能叫 ``format``（与内置冲突）；
      2. **不能用 ``*args`` 收集参数**。Django 的 ``FilterExpression.args_check`` 用
         ``inspect.getfullargspec`` 校验参数个数，而 ``*args`` 不计入 ``args`` 列表：
         写成 ``def f(text, *args)`` 会被算成「只接受 1 个参数」，
         于是 ``{{ x|msgfmt:y }}``（2 个）直接报
         ``msgfmt requires 1 arguments, 2 provided`` —— 整页 500。
         因此这里显式声明 3 个可选位置参数（``a1/a2/a3``），
         既满足校验，也覆盖了本项目的实际用法（最多 3 个占位符）。

    用法::

        {{ MSG.a11y.notification_unread|msgfmt:unread_count }}
        {{ MSG.brand.about_title|msgfmt:site_name }}
        {{ MSG.moderation.page_of|msgfmt:'pending_page.number|pending_page.paginator.num_pages' }}

    多参数怎么办
    ------------
    Django 模板过滤器语法 ``{{ v|filter:arg }}`` **只接受一个参数**，
    写 ``|msgfmt:a:b`` 会抛 ``TemplateSyntaxError``。因此多参数场景把值用 ``|``
    拼成一个字符串传入，本过滤器内部按 ``|`` 拆分（见下方实现）。

    设计要点：
      · **容错优先**：占位符与实参不匹配时返回原文而不是抛异常 ——
        文案问题绝不能让页面 500（与 ``site_messages.msg()`` 口径一致）；
      · 只做纯文本格式化，不 ``mark_safe``：含 HTML 的文案由调用方自行决定
        是否加 ``|safe``，避免默认放开转义扩大 XSS 面。

    Args:
        template_text: 文案原文（``{{ MSG.x }}`` 取到的值）。
        a1: 单个参数，或形如 ``'值1|值2'`` 的多值字符串。
        a2, a3: 兼容直接传多个参数的调用（模板里通常用不到，见上）。

    Returns:
        str: 格式化后的文案；不匹配时原样返回。
    """
    #: 条件判断：条件成立时执行该分支
    if template_text is None:
        #: 返回结果并结束当前函数
        return ''
    #: 定义变量「provided」，保存对应数据（集合/元组）
    provided = [a for a in (a1, a2, a3) if a is not None]
    #: 条件判断：条件成立时执行该分支
    if not provided:
        #: 返回结果并结束当前函数
        return template_text
    # 单参数且含分隔符 → 拆分（多参数的正确写法，绕开过滤器只收一个参数的限制）
    #: 条件判断：条件成立时执行该分支
    if len(provided) == 1 and isinstance(provided[0], str) and '|' in provided[0]:
        #: 定义变量「provided」，保存对应数据
        provided = provided[0].split('|')
    #: 尝试执行可能出错的代码
    try:
        #: 返回结果并结束当前函数
        return str(template_text).format(*provided)
    #: 捕获并处理异常，避免程序中断
    except (IndexError, KeyError, ValueError):
        #: 返回结果并结束当前函数
        return template_text


#: 兼容别名：模板里也可以写 ``|fmt``（更短，日常书写更方便）
register.filter('fmt', msgfmt)


# 迭代#249: highlight过滤器docstring完善
#: 装饰器：为下一个定义附加「register.filter(name='highlight')」行为（权限、缓存、注册信号等）
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
    #: 条件判断：条件成立时执行该分支
    if text is None:
        #: 定义变量「text」，保存对应数据
        text = ''
    #: 定义变量「text」，保存对应数据
    text = str(text)
    #: 定义变量「query」，保存对应数据
    query = '' if query is None else str(query).strip()

    # 先整体转义原文，确保正文里的 < > & 等都变成实体，杜绝 XSS
    #: 定义变量「escaped」，保存对应数据
    escaped = escape(text)
    #: 条件判断：条件成立时执行该分支
    if not query:
        #: 返回结果并结束当前函数
        return mark_safe(escaped)

    # 关键词同样转义（转义不会改变中英文 / 数字等普通字符），
    # re.escape 再兜住正则元字符，避免关键词里带 . * ? 等导致正则错误
    #: 定义变量「pattern」，保存对应数据
    pattern = re.compile(re.escape(escape(query)), re.IGNORECASE)
    # 用转义后的 <mark> 替换命中片段；因为 escaped 已是纯文本安全态，
    # 这里主动写入的 <mark> 标签是我们自己可控的，最后 mark_safe 渲染
    #: 定义变量「result」，保存对应数据
    result = pattern.sub(lambda m: '<mark class="search-highlight">' + m.group(0) + '</mark>', escaped)
    #: 返回结果并结束当前函数
    return mark_safe(result)


# 迭代#250: lazy_images过滤器docstring完善
#: 装饰器：为下一个定义附加「register.filter(name='lazy_images', is_safe=True)」行为（权限、缓存、注册信号等）
@register.filter(name='lazy_images', is_safe=True)
def lazy_images(html):
    """给富文本正文中所有 <img> 标签注入 loading="lazy"。

    正文经 bleach 净化后由模板 |safe 输出，这里再用正则给每个尚未带
    loading 属性的 <img> 补上懒加载，避免首屏外的图片阻塞首屏渲染。
    已显式带 loading 的图片（如首屏封面）不重复添加。
    """
    #: 导入模块「re」，供本文件后续使用
    import re
    def _add(m):
        """
        功能：添加「add」。

        参数：
          - m：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 定义变量「tag」，保存对应数据
        tag = m.group(0)
        #: 条件判断：条件成立时执行该分支
        if 'loading=' in tag:
            #: 返回结果并结束当前函数
            return tag
        #: 返回结果并结束当前函数
        return tag[:-1].rstrip('>') + ' loading="lazy">'
    #: 返回结果并结束当前函数
    return re.sub(r'<img\b[^>]*>', _add, html)


#: 装饰器：为下一个定义附加「register.filter(name='file_url')」行为（权限、缓存、注册信号等）
@register.filter(name='file_url')
def file_url(fieldfile):
    """安全返回 FileField/ImageField 的 url；未关联文件时返回空串。

    模板里直接写 ``article.cover_image.url``，当没有上传文件时
    FieldFile.url 会抛 ValueError 导致整页 500，故用本过滤器兜底。
    """
    #: 尝试执行可能出错的代码
    try:
        #: 返回结果并结束当前函数
        return fieldfile.url
    #: 捕获并处理异常，避免程序中断
    except (ValueError, AttributeError):
        #: 返回结果并结束当前函数
        return ''


# 命中这些路径 / 文件名片段的图片，基本是编辑器 UI 图标而非正文配图（bug4）
#: 定义变量「_BAD_IMG_SRC」，保存对应数据
_BAD_IMG_SRC = re.compile(
    #: 该行执行对应逻辑（结合上下文理解）
    r'(placeholder|empty[-_]?state|/blank|/static/|ckeditor|/plugins?/|smilie?y|'
    #: 该行执行对应逻辑（结合上下文理解）
    r'sprite|/icons?/|[-_/]icon|loader|spinner|toolbar|/button|emoji|/gfx/|[-_]logo\.)',
    #: 操作「re」的属性或方法
    re.IGNORECASE)
#: 定义变量「_IMG_TAG_RE」，保存对应数据
_IMG_TAG_RE = re.compile(r'<img\b[^>]*>', re.IGNORECASE | re.DOTALL)
#: 定义变量「_IMG_SRC_RE」，保存对应数据
_IMG_SRC_RE = re.compile(r'\bsrc=["\']([^"\']+)["\']', re.IGNORECASE)
#: 定义变量「_IMG_W_RE」，保存对应数据
_IMG_W_RE = re.compile(r'\bwidth=["\']?(\d+)', re.IGNORECASE)
#: 定义变量「_IMG_H_RE」，保存对应数据
_IMG_H_RE = re.compile(r'\bheight=["\']?(\d+)', re.IGNORECASE)
#: 定义变量「_IMG_CLS_RE」，保存对应数据
_IMG_CLS_RE = re.compile(r'\bclass=["\']([^"\']+)', re.IGNORECASE)


def _local_media_path(src):
    """把图片 URL 映射为本地 MEDIA_ROOT 下的文件路径；非本站 media 资源返回 None。"""
    #: 定义变量「media_url」，保存对应数据
    media_url = settings.MEDIA_URL or '/media/'
    #: 定义变量「rel」，保存对应数据
    rel = None
    #: 条件判断：条件成立时执行该分支
    if src.startswith(media_url):
        #: 定义变量「rel」，保存对应数据
        rel = src[len(media_url):]
    #: 以上条件均不成立时的兜底分支
    else:
        #: 定义变量「marker」，保存对应数据
        marker = '/' + media_url.strip('/') + '/'
        #: 定义变量「i」，保存对应数据
        i = src.find(marker)
        #: 条件判断：条件成立时执行该分支
        if i >= 0:
            #: 定义变量「rel」，保存对应数据
            rel = src[i + len(marker):]
    #: 条件判断：条件成立时执行该分支
    if rel is None:
        #: 返回结果并结束当前函数
        return None
    #: 定义变量「rel」，保存对应数据
    rel = rel.split('?', 1)[0].split('#', 1)[0]
    #: 返回结果并结束当前函数
    return Path(settings.MEDIA_ROOT) / unquote(rel)


def _image_pixel_size(src):
    """用 Pillow 读取本地 media 图片的真实像素尺寸，结果按 src 缓存 24h。

    用于剔除“宽但极矮”的编辑器工具条截图等伪配图。无法判定时返回 None。
    """
    #: 定义变量「cache_key」，保存对应数据
    cache_key = 'blog:imgdim:' + src
    #: 读写缓存，减轻数据库压力，注意键与过期时间
    cached = cache.get(cache_key)
    #: 条件判断：条件成立时执行该分支
    if cached is not None:
        #: 返回结果并结束当前函数
        return tuple(cached) if cached else None
    #: 定义变量「size」，保存对应数据
    size = None
    #: 定义变量「path」，保存对应数据
    path = _local_media_path(src)
    #: 条件判断：条件成立时执行该分支
    if path is not None and path.is_file():
        #: 尝试执行可能出错的代码
        try:
            #: 从模块「PIL」导入所需对象
            from PIL import Image
            #: 上下文管理：进入时获取资源、退出时自动释放
            with Image.open(path) as im:
                #: 定义变量「size」，保存对应数据
                size = im.size
        #: 捕获并处理异常，避免程序中断
        except Exception:
            #: 定义变量「size」，保存对应数据
            size = None
    #: 读写缓存，减轻数据库压力，注意键与过期时间
    cache.set(cache_key, list(size) if size else False, 86400)
    #: 返回结果并结束当前函数
    return size


def _portable_media_src(src):
    """把指向任意 host:port 的本站 media 绝对 URL 改写为相对路径。

    历史正文里图片是“创建时端口”的绝对地址（如 http://127.0.0.1:8032/media/..），
    一旦换端口 / 换域名图片就会全部失效。统一改成 /media/.. 相对地址即可随当前
    host 访问。外部非 media 的 URL 原样返回。
    """
    #: 定义变量「media_seg」，保存对应数据（集合/元组）
    media_seg = (settings.MEDIA_URL or '/media/').strip('/')
    #: 定义变量「pattern」，保存对应数据
    pattern = re.compile(
        #: 该行执行对应逻辑（结合上下文理解）
        r'https?://[^\s"\'<>]*?/(' + re.escape(media_seg) + r'/[^\s"\'<>]+)',
        #: 操作「re」的属性或方法
        re.IGNORECASE)
    #: 返回结果并结束当前函数
    return pattern.sub(lambda m: '/' + m.group(1), src)


#: 装饰器：为下一个定义附加「register.filter(name='portable_media')」行为（权限、缓存、注册信号等）
@register.filter(name='portable_media')
def portable_media(html):
    """对整段正文 HTML 执行 media 绝对 URL 相对化（详情页渲染前使用，bug4 增强）。"""
    #: 条件判断：条件成立时执行该分支
    if not html:
        #: 返回结果并结束当前函数
        return ''
    #: 定义变量「media_seg」，保存对应数据（集合/元组）
    media_seg = (settings.MEDIA_URL or '/media/').strip('/')
    #: 定义变量「pattern」，保存对应数据
    pattern = re.compile(
        #: 该行执行对应逻辑（结合上下文理解）
        r'https?://[^\s"\'<>]*?/(' + re.escape(media_seg) + r'/[^\s"\'<>]+)',
        #: 操作「re」的属性或方法
        re.IGNORECASE)
    #: 返回结果并结束当前函数
    return pattern.sub(lambda m: '/' + m.group(1), str(html))


#: 装饰器：为下一个定义附加「register.filter(name='body_first_image')」行为（权限、缓存、注册信号等）
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
    #: 条件判断：条件成立时执行该分支
    if not html:
        #: 返回结果并结束当前函数
        return ''
    #: 循环遍历，逐个处理元素
    for tag_match in _IMG_TAG_RE.finditer(str(html)):
        #: 定义变量「tag」，保存对应数据
        tag = tag_match.group(0)
        #: 定义变量「src_match」，保存对应数据
        src_match = _IMG_SRC_RE.search(tag)
        #: 条件判断：条件成立时执行该分支
        if not src_match:
            #: 跳过本次进入下一次迭代
            continue
        #: 定义变量「src」，保存对应数据
        src = src_match.group(1)
        #: 条件判断：条件成立时执行该分支
        if not src or src.startswith('data:'):
            #: 跳过本次进入下一次迭代
            continue
        # 历史绝对 URL（带旧端口/域名）先相对化，保证换端口后仍可加载
        #: 定义变量「src」，保存对应数据
        src = _portable_media_src(src)
        #: 定义变量「low」，保存对应数据
        low = src.split('?', 1)[0].split('#', 1)[0]
        #: 条件判断：条件成立时执行该分支
        if _BAD_IMG_SRC.search(low):
            #: 跳过本次进入下一次迭代
            continue
        # 显式声明的小尺寸
        #: 该行执行对应逻辑（结合上下文理解）
        wm, hm = _IMG_W_RE.search(tag), _IMG_H_RE.search(tag)
        #: 条件判断：条件成立时执行该分支
        if (wm and int(wm.group(1)) < 80) or (hm and int(hm.group(1)) < 80):
            #: 跳过本次进入下一次迭代
            continue
        # class 上的图标 / 表情信号
        #: 定义变量「cm」，保存对应数据
        cm = _IMG_CLS_RE.search(tag)
        #: 条件判断：条件成立时执行该分支
        if cm and re.search(r'smilie?y|icon|emoji|sprite', cm.group(1), re.IGNORECASE):
            #: 跳过本次进入下一次迭代
            continue
        # 本站 media：用真实像素尺寸剔除编辑器工具条 / 细长截图
        #: 条件判断：条件成立时执行该分支
        if _local_media_path(src) is not None:
            #: 定义变量「size」，保存对应数据
            size = _image_pixel_size(src)
            #: 条件判断：条件成立时执行该分支
            if size is not None:
                #: 该行执行对应逻辑（结合上下文理解）
                w, h = size
                #: 定义变量「ratio」，保存对应数据
                ratio = w / h if h else 99
                # 太小、过宽（工具条 w/h>2.6）、过窄（h/w>4）都不算正文配图
                #: 条件判断：条件成立时执行该分支
                if w < 160 or h < 100 or ratio > 2.6 or (1 / ratio if ratio else 0) > 4:
                    #: 跳过本次进入下一次迭代
                    continue
        #: 返回结果并结束当前函数
        return src
    #: 返回结果并结束当前函数
    return ''


#: 装饰器：为下一个定义附加「register.simple_tag(name='smart_page_range')」行为（权限、缓存、注册信号等）
@register.simple_tag(name='smart_page_range')
def smart_page_range(current, total, span=3):
    """智能页码窗口（bug6）。

    始终包含【首页 1】【尾页 total】以及【当前页左右各 span 页】；
    相邻不连续处用整数 ``0`` 作为省略号占位，模板遇到 0 渲染不可点击
    的「…」。

    示例（total=207, current=100, span=3）::

        [1, 0, 97, 98, 99, 100, 101, 102, 103, 0, 207]
    """
    #: 尝试执行可能出错的代码
    try:
        #: 定义变量「current」，保存对应数据
        current = int(current)
        #: 定义变量「total」，保存对应数据
        total = int(total)
        #: 定义变量「span」，保存对应数据
        span = int(span)
    #: 捕获并处理异常，避免程序中断
    except (TypeError, ValueError):
        #: 返回结果并结束当前函数
        return []
    #: 条件判断：条件成立时执行该分支
    if total <= 1:
        #: 返回结果并结束当前函数
        return []
    # 收集必须展示的页码（集合自动去重）
    #: 定义变量「pages」，保存对应数据
    pages = {1, total}
    #: 循环遍历，逐个处理元素
    for n in range(current - span, current + span + 1):
        #: 条件判断：条件成立时执行该分支
        if 1 <= n <= total:
            #: 调用「pages.add」执行相应逻辑
            pages.add(n)
    #: 定义变量「ordered」，保存对应数据
    ordered = sorted(pages)
    # 在缺口处插入省略号标记 0
    #: 定义变量「result」，保存对应数据（集合/元组）
    result = []
    #: 定义变量「prev」，保存对应数据
    prev = None
    #: 循环遍历，逐个处理元素
    for n in ordered:
        #: 条件判断：条件成立时执行该分支
        if prev is not None and n - prev > 1:
            #: 调用「result.append」执行相应逻辑
            result.append(0)
        #: 调用「result.append」执行相应逻辑
        result.append(n)
        #: 定义变量「prev」，保存对应数据
        prev = n
    #: 返回结果并结束当前函数
    return result

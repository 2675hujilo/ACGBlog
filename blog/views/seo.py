# -*- coding: utf-8 -*-

"""SEO：网站 JSON-LD、sitemap、RSS 与 robots.txt。"""

#: 导入模块「logging」，供本文件后续使用
import logging
#: 从模块「datetime」导入所需对象
from datetime import datetime, timedelta
#: 从模块「django.conf」导入所需对象
from django.conf import settings
#: 从模块「django.db」导入所需对象
from django.db import DatabaseError, IntegrityError, OperationalError
#: 从模块「django.http」导入所需对象
from django.http import (
    #: 抛出 404 异常（渲染萌系 404 页）
    FileResponse, Http404, HttpRequest, HttpResponse,
    #: 该行执行对应逻辑（结合上下文理解）
    HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound,
    #: 该行执行对应逻辑（结合上下文理解）
    HttpResponseNotModified, HttpResponsePermanentRedirect,
    #: 构造 HTTP 响应返回给客户端
    HttpResponseRedirect, JsonResponse, StreamingHttpResponse,
#: 该行执行对应逻辑（结合上下文理解）
)
#: 从模块「django.shortcuts」导入所需对象
from django.shortcuts import get_object_or_404, redirect, render
#: 从模块「..models」导入所需对象
from ..models import (
    #: 该行执行对应逻辑（结合上下文理解）
    AccessLog, Article, Badge, Category, Comment, CommentReport,
    #: 该行执行对应逻辑（结合上下文理解）
    EditLog, Favorite, FavoriteFolder, ModerationLog, Notification,
    #: 该行执行对应逻辑（结合上下文理解）
    PromotionRequest, ModerationSettings, Rating, Series, ShortLink,
    #: 该行执行对应逻辑（结合上下文理解）
    SiteNotice, Tag, User, UserBadge,
#: 该行执行对应逻辑（结合上下文理解）
)

#: 从模块「.common」导入所需对象
from .common import _safe_jsonld, logger


#: 定义变量「logger」，保存对应数据
logger = logging.getLogger('blog.views')

# 迭代#110: _build_website_jsonld函数docstring完善
def _build_website_jsonld(request):
    """构造首页 Website + SearchAction 结构化数据（Schema.org）。

    让搜索引擎结果中可直接展示站内搜索框（Sitelinks Searchbox）。

    Args:
        request: 当前 HttpRequest，用于拼绝对 URL。

    Returns:
        str: 已安全转义的 JSON-LD 字符串。
    """
    #: 返回结果并结束当前函数
    return _safe_jsonld({
        #: 该行执行对应逻辑（结合上下文理解）
        '@context': 'https://schema.org',
        #: 该行执行对应逻辑（结合上下文理解）
        '@type': 'WebSite',
        #: 配置项「name」：字典/模型的该键设置为对应值
        'name': settings.SITE_NAME,
        #: 配置项「url」：字典/模型的该键设置为对应值
        'url': request.build_absolute_uri('/'),
        #: 配置项「potentialAction」：字典/模型的该键设置为对应值
        'potentialAction': {
            #: 该行执行对应逻辑（结合上下文理解）
            '@type': 'SearchAction',
            #: 配置项「target」：字典/模型的该键设置为对应值
            'target': {
                #: 该行执行对应逻辑（结合上下文理解）
                '@type': 'EntryPoint',
                #: 配置项「urlTemplate」：字典/模型的该键设置为对应值
                'urlTemplate': request.build_absolute_uri('/search/?q={search_term_string}'),
            #: 该行执行对应逻辑（结合上下文理解）
            },
            #: 该行执行对应逻辑（结合上下文理解）
            'query-input': 'required name=search_term_string',
        #: 该行执行对应逻辑（结合上下文理解）
        },
    #: 该行执行对应逻辑（结合上下文理解）
    })

# 迭代#226: sitemap视图docstring
# 迭代#227: sitemap(request) -> HttpResponse 类型提示
def sitemap(request: HttpRequest) -> HttpResponse:
    """生成 sitemap.xml：搜索引擎站点地图。

    列出所有已发布文章、全部分类页、全部标签页、首页与归档页。
    - 文章用轻量 ``values('pk','updated_at')`` 查询，只取需要的字段；
    - 每条 <url> 含 <loc> / <lastmod>(文章更新时间) / <changefreq> / <priority>；
    - 优先级：首页 1.0 > 文章 0.8 > 归档 0.7 > 分类 0.6 > 标签 0.5。

    Args:
        request: 当前 HttpRequest，用于拼绝对 URL。

    Returns:
        HttpResponse: Content-Type 为 text/xml 的站点地图。
    """
    # host 去掉结尾斜杠，模板中再按需拼接带前导斜杠的路径
    #: 定义变量「host」，保存对应数据
    host = request.build_absolute_uri('/').rstrip('/')
    # 已发布文章：轻量查询，仅取主键与更新时间，避免拉取整行富文本
    # 迭代#228: sitemap中文章查询异常处理
    #: 尝试执行可能出错的代码
    try:
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        articles = (Article.objects.filter(status=Article.Status.PUBLISHED)
                    #: 对查询结果按字段排序
                    .order_by('-updated_at').values('pk', 'updated_at'))
    #: 捕获并处理异常，避免程序中断
    except DatabaseError as db_exc:
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.error('sitemap查询失败: %s', db_exc)
        #: 定义变量「articles」，保存对应数据
        articles = Article.objects.none()
    #: 定义变量「ctx」，保存对应数据
    ctx = {
        #: 配置项「host」：字典/模型的该键设置为对应值
        'host': host,
        #: 配置项「articles」：字典/模型的该键设置为对应值
        'articles': articles,
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        'categories': Category.objects.all().values('pk'),
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        'tags': Tag.objects.all().values('pk'),
    #: 该行执行对应逻辑（结合上下文理解）
    }
    #: 返回结果并结束当前函数
    return render(request, 'sitemap.xml', ctx, content_type='text/xml')

# 迭代#229: rss_feed视图docstring
# 迭代#230: rss_feed(request) -> HttpResponse 类型提示
def rss_feed(request: HttpRequest) -> HttpResponse:
    """生成 RSS 2.0 订阅源：最近 20 篇已发布文章。

    每个 <item> 含 title / link / description(摘要) / pubDate(RFC 2822) /
    category(分类名) / guid。日期格式按东八区输出。

    Args:
        request: 当前 HttpRequest，用于拼绝对 URL。

    Returns:
        HttpResponse: Content-Type 为 application/rss+xml 的 RSS 源。
    """
    #: 定义变量「host」，保存对应数据
    host = request.build_absolute_uri('/').rstrip('/')
    # 最近 20 篇已发布文章，预加载分类/作者避免 N+1
    # 迭代#231: rss_feed中文章查询异常处理
    #: 尝试执行可能出错的代码
    try:
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        article_list = (Article.objects.filter(status=Article.Status.PUBLISHED)
                    #: ORM 预加载关联，减少 N+1 查询提升性能
                    .select_related('category', 'author')
                    #: 对查询结果按字段排序
                    .order_by('-created_at')[:20])
    #: 捕获并处理异常，避免程序中断
    except DatabaseError as db_exc:
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.error('RSS查询失败: %s', db_exc)
        #: 定义变量「article_list」，保存对应数据（集合/元组）
        article_list = []
    #: 定义变量「items」，保存对应数据（集合/元组）
    items = []
    #: 循环遍历，逐个处理元素
    for a in article_list:
        #: 调用「items.append」执行相应逻辑
        items.append({
            #: 配置项「title」：字典/模型的该键设置为对应值
            'title': a.title,
            # 绝对链接：host + 详情页路径
            #: 配置项「link」：字典/模型的该键设置为对应值
            'link': host + a.get_absolute_url(),
            #: 配置项「description」：字典/模型的该键设置为对应值
            'description': a.excerpt,
            # RFC 2822 格式发布时间（东八区）
            #: 配置项「pub_date」：字典/模型的该键设置为对应值
            'pub_date': a.created_at.strftime('%a, %d %b %Y %H:%M:%S +0800'),
            #: 配置项「category」：字典/模型的该键设置为对应值
            'category': a.category.name if a.category else '',
            #: 配置项「guid」：字典/模型的该键设置为对应值
            'guid': host + a.get_absolute_url(),
        #: 该行执行对应逻辑（结合上下文理解）
        })
    #: 定义变量「ctx」，保存对应数据
    ctx = {
        #: 配置项「host」：字典/模型的该键设置为对应值
        'host': host,
        #: 配置项「items」：字典/模型的该键设置为对应值
        'items': items,
        #: 配置项「build_date」：字典/模型的该键设置为对应值
        'build_date': datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0800'),
    #: 该行执行对应逻辑（结合上下文理解）
    }
    #: 返回结果并结束当前函数
    return render(request, 'rss.xml', ctx, content_type='application/rss+xml')

# 迭代#232: robots_txt视图docstring
# 迭代#233: robots_txt(request) -> HttpResponse 类型提示
def robots_txt(request: HttpRequest) -> HttpResponse:
    """返回 robots.txt：允许抓取前台、禁止抓取后台与需登录的管理页。

    直接用 HttpResponse 返回纯文本字符串，无需模板。

    Args:
        request: 当前 HttpRequest，用于拼 Sitemap 绝对 URL。

    Returns:
        HttpResponse: Content-Type 为 text/plain 的 robots 规则。
    """
    #: 定义变量「lines」，保存对应数据（集合/元组）
    lines = [
        #: 该行执行对应逻辑（结合上下文理解）
        'User-agent: *',
        #: 该行执行对应逻辑（结合上下文理解）
        'Allow: /',
        #: 该行执行对应逻辑（结合上下文理解）
        'Disallow: /admin/',
        #: 该行执行对应逻辑（结合上下文理解）
        'Disallow: /new/',
        #: 该行执行对应逻辑（结合上下文理解）
        'Disallow: /edit/',
        #: 该行执行对应逻辑（结合上下文理解）
        'Disallow: /delete/',
        #: 该行执行对应逻辑（结合上下文理解）
        'Disallow: /settings/',
        #: 该行执行对应逻辑（结合上下文理解）
        'Disallow: /my-articles/',
        # Sitemap 必须是绝对 URL
        #: 该行执行对应逻辑（结合上下文理解）
        f'Sitemap: {request.build_absolute_uri("/sitemap.xml")}',
    #: 该行执行对应逻辑（结合上下文理解）
    ]
    #: 返回结果并结束当前函数
    return HttpResponse('\n'.join(lines), content_type='text/plain')

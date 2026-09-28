# -*- coding: utf-8 -*-

"""SEO：网站 JSON-LD、sitemap、RSS 与 robots.txt。"""

import logging
from datetime import datetime

from django.conf import settings
from django.db import DatabaseError
from django.http import (
    HttpRequest, HttpResponse,
)
from django.shortcuts import render

from .common import _safe_jsonld, logger
from ..models import (
    Article, Category, Tag, )

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
    return _safe_jsonld({
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        'name': settings.SITE_NAME,
        'url': request.build_absolute_uri('/'),
        'potentialAction': {
            '@type': 'SearchAction',
            'target': {
                '@type': 'EntryPoint',
                'urlTemplate': request.build_absolute_uri('/search/?q={search_term_string}'),
            },
            'query-input': 'required name=search_term_string',
        },
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
    host = request.build_absolute_uri('/').rstrip('/')
    # 已发布文章：轻量查询，仅取主键与更新时间，避免拉取整行富文本
    # 迭代#228: sitemap中文章查询异常处理
    try:
        articles = (Article.objects.filter(status=Article.Status.PUBLISHED)
                    .order_by('-updated_at').values('pk', 'updated_at'))
    except DatabaseError as db_exc:
        logger.error('sitemap查询失败: %s', db_exc)
        articles = Article.objects.none()
    ctx = {
        'host': host,
        'articles': articles,
        'categories': Category.objects.all().values('pk'),
        'tags': Tag.objects.all().values('pk'),
    }
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
    host = request.build_absolute_uri('/').rstrip('/')
    # 最近 20 篇已发布文章，预加载分类/作者避免 N+1
    # 迭代#231: rss_feed中文章查询异常处理
    try:
        article_list = (Article.objects.filter(status=Article.Status.PUBLISHED)
                    .select_related('category', 'author')
                    .order_by('-created_at')[:20])
    except DatabaseError as db_exc:
        logger.error('RSS查询失败: %s', db_exc)
        article_list = []
    items = []
    for a in article_list:
        items.append({
            'title': a.title,
            # 绝对链接：host + 详情页路径
            'link': host + a.get_absolute_url(),
            'description': a.excerpt,
            # RFC 2822 格式发布时间（东八区）
            'pub_date': a.created_at.strftime('%a, %d %b %Y %H:%M:%S +0800'),
            'category': a.category.name if a.category else '',
            'guid': host + a.get_absolute_url(),
        })
    ctx = {
        'host': host,
        'items': items,
        'build_date': datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0800'),
    }
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
    lines = [
        'User-agent: *',
        'Allow: /',
        'Disallow: /admin/',
        'Disallow: /new/',
        'Disallow: /edit/',
        'Disallow: /delete/',
        'Disallow: /settings/',
        'Disallow: /my-articles/',
        # Sitemap 必须是绝对 URL
        f'Sitemap: {request.build_absolute_uri("/sitemap.xml")}',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain')

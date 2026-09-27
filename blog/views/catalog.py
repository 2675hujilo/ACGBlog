# -*- coding: utf-8 -*-

"""内容目录：侧边栏、分类、标签、归档与标签云。"""

import logging
from itertools import groupby
from django.conf import settings
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Avg, Count, F, Min, Q, Sum
from django.http import (
    FileResponse, Http404, HttpRequest, HttpResponse,
    HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound,
    HttpResponseNotModified, HttpResponsePermanentRedirect,
    HttpResponseRedirect, JsonResponse, StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page
from ..models import (
    AccessLog, Article, Badge, Category, Comment, CommentReport,
    EditLog, Favorite, FavoriteFolder, ModerationLog, Notification,
    PromotionRequest, ModerationSettings, Rating, Series, ShortLink,
    SiteNotice, Tag, User, UserBadge,
)

from .common import SIDEBAR_CACHE_KEY, SIDEBAR_CACHE_TIMEOUT, TAG_CLOUD_KEY, _base_qs, _filter_articles


logger = logging.getLogger('blog.views')

# 迭代#119: _sidebar聚合查询注释
def _build_sidebar():
    """真正计算侧边栏数据（含聚合查询）。queryset 统一物化为 list 以便缓存序列化。

    第4轮 A4: 统计部分复用 ``context_processors.get_sidebar_stats()``
    （key=sidebar_stats, TTL 300s），避免与侧边栏统计缓存重复跑聚合 SQL。
    """
    # 仅统计已发布文章，草稿不计入侧边栏公开数据
    published = Article.objects.filter(status=Article.Status.PUBLISHED)
    # 第4轮 A4: 统计走统一缓存（文章数/总浏览/标签数/分类数/今日访问/独立访客）
    from ..context_processors import get_sidebar_stats
    stats = get_sidebar_stats()
    return {
        'stats': stats,
        # 物化为 list：LocMemCache 需 pickle，lazy queryset 不可直接缓存
        'hot_articles': list(published.order_by('-views')[:10]),
        'cloud_tags': list(Tag.objects.annotate(
            n=Count('articles', filter=Q(articles__status='published', articles__is_deleted=False)))
            .filter(n__gt=0).order_by('-n')[:30]),
        'nav_categories': list(Category.objects.annotate(
            n=Count('articles', filter=Q(articles__status='published', articles__is_deleted=False)))
            .order_by('-n', 'name')),
    }

# 迭代#120: _sidebar函数docstring
# 迭代#121: _sidebar() -> dict 类型提示
def _sidebar() -> dict:
    """聚合侧边栏数据并缓存 5 分钟。

    公共只读数据（统计 / 热门 / 标签云 / 分类导航）不随登录用户变化，
    用 ``cache.get_or_set`` 命中缓存后直接返回，避免每次请求都跑聚合查询。
    文章新增 / 编辑 / 删除时在对应视图调用 ``cache.delete(SIDEBAR_CACHE_KEY)
            cache.delete('footer_stats')`` 失效。
    """
    return cache.get_or_set(SIDEBAR_CACHE_KEY, _build_sidebar, SIDEBAR_CACHE_TIMEOUT)

def _tag_cloud_cached(limit=30, timeout=600):
    # 第2轮迭代#64: 标签云缓存——带文章数注解并缓存
    # 第3轮迭代#3: 缓存键统一为 TAG_CLOUD_KEY，与信号失效键对齐
    key = TAG_CLOUD_KEY
    return cache.get_or_set(key, lambda: list(
        Tag.objects.annotate(n=Count('articles', filter=Q(
            articles__status='published', articles__is_deleted=False)))
        .filter(n__gt=0).order_by('-n')[:limit]), timeout)

def _archive_cached(timeout=600):
    # 第2轮迭代#65: 归档缓存——按年月分组的时间轴数据短 TTL 缓存
    key = 'archive_data'
    def _build():
        rows = (Article.objects.filter(status=Article.Status.PUBLISHED)
                .order_by('-created_at'))
        return list(rows.values('id', 'title', 'created_at')[:500])
    return cache.get_or_set(key, _build, timeout)

# 迭代#155: categories视图docstring
# 迭代#156: categories(request) -> HttpResponse 类型提示
def categories(request: HttpRequest) -> HttpResponse:
    """分类导航页：展示全部分类及其下文章数量。

    Args:
        request: 当前 HttpRequest 对象。

    Returns:
        HttpResponse: 渲染分类列表页 ``blog/categories.html``。
    """
    # 分类文章数仅统计已发布且未删除的文章（旧逻辑把草稿/待审/软删文章计入，数量虚高）
    ctx = {'categories': Category.objects.annotate(
        n=Count('articles', filter=Q(articles__status='published', articles__is_deleted=False))
        ).order_by('-n', 'name'), 'active_nav': 'categories',
        # ---- SEO ----
        'meta_title': f'全部分类 - {settings.SITE_NAME}',
        'meta_description': f'{settings.SITE_NAME} 文章分类导航。'}
    return render(request, 'blog/categories.html', ctx)

# 迭代#157: category_detail视图docstring
# 迭代#158: category_detail(request, pk) -> HttpResponse 类型提示
def category_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """单个分类下的文章列表页：复用首页模板，叠加分类筛选。

    按主键取出分类，在 ``_base_qs`` 基础上额外过滤 ``category=该分类``，
    再走统一的筛选 / 排序 / 分页流程。

    Args:
        request: 当前 HttpRequest 对象。
        pk: 分类主键。

    Returns:
        HttpResponse: 渲染后的文章列表 HTML（复用 ``blog/index.html``）。
    """
    category = get_object_or_404(Category, pk=pk)
    # 在权限过滤之上叠加"仅该分类"的条件，再走统一筛选
    qs, sort, q = _filter_articles(
        request, _base_qs(request).filter(category=category))
    paginator = Paginator(qs, settings.PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))
    ctx = {'page_obj': page_obj, 'page_range': list(paginator.page_range),
           'sort': sort, 'q': q, 'current_category': category,
           'active_kind': request.GET.get('kind', ''), 'active_nav': 'categories',
           # ---- SEO / Open Graph ----
           'meta_title': f'{category.name} - {settings.SITE_NAME}',
           'meta_description': (category.description or f'{category.name} 分类下的文章').strip(),
           'og_type': 'website',
           'og_url': request.build_absolute_uri()}
    ctx.update(_sidebar())
    return render(request, 'blog/index.html', ctx)

# 迭代#159: tags视图docstring
# 迭代#160: tags(request) -> HttpResponse 类型提示
def tags(request: HttpRequest) -> HttpResponse:
    """标签页：排行页（默认）+ 标签索引分页。

    页面模式：
        - rank: 排行页（默认），上半部分标签云 + 下半部分排名列表
        - index: 标签索引分页，显示全部标签，分页展示

    排序方式：
        - count: 文章数（默认）
        - views: 总浏览量
        - likes: 总点赞数
        - comments: 总评论数
        - latest: 最新文章
        - name: 名称

    排序方向：
        - desc: 降序（默认）
        - asc: 升序

    标签云字体大小：根据排名动态调整，排名越靠前字体越大，设定最大最小值。

    Args:
        request: 当前 HttpRequest 对象，读取 GET 参数 ``mode``/``sort``/``order``/``page``。

    Returns:
        HttpResponse: 渲染标签页 ``blog/tags.html``。
    """
    from django.db.models import Sum, Max

    # 页面模式
    mode = request.GET.get('mode', 'rank')

    # 排序映射
    sort_map = {
        'count': 'n',
        'views': 'total_views',
        'likes': 'total_likes',
        'comments': 'total_comments',
        'latest': 'latest_article',
        'name': 'name',
    }
    sort = request.GET.get('sort', 'count')
    order = request.GET.get('order', 'desc')  # desc/asc
    sort_field = sort_map.get(sort, 'n')
    order_by = f'-{sort_field}' if order == 'desc' else sort_field

    # 标签查询：仅聚合「已发布且未删除」文章的数量 / 总浏览 / 总点赞 / 总评论 / 最新时间
    # （旧逻辑未过滤状态与软删，把草稿、待审、回收站文章全部计入，导致数量虚高）
    pub_cond = Q(articles__status='published', articles__is_deleted=False)
    all_tags = (
        Tag.objects
        .annotate(
            n=Count('articles', filter=pub_cond),
            total_views=Sum('articles__views', filter=pub_cond),
            total_likes=Sum('articles__likes', filter=pub_cond),
            total_comments=Sum('articles__comment_count', filter=pub_cond),
            latest_article=Max('articles__created_at', filter=pub_cond),
        )
        .filter(n__gt=0)
        .order_by(order_by)
    )

    # 全站统计：直接按「已发布未删除」的唯一文章聚合，
    # 避免一篇多标签文章在各标签下被重复累加（文章总数应等于实际已发布篇数）。
    total_tags = all_tags.count()
    _pub_articles = Article.objects.filter(status='published', is_deleted=False)
    _site = _pub_articles.aggregate(
        total_views=Sum('views'), total_likes=Sum('likes'),
        total_comments=Sum('comment_count'))
    total_articles = _pub_articles.count()
    total_views = _site['total_views'] or 0
    total_likes = _site['total_likes'] or 0
    total_comments = _site['total_comments'] or 0

    # 标签云字体大小：根据排名动态调整（排名从1开始）
    # 最大字体 1.6rem，最小字体 0.75rem
    max_font = 1.6
    min_font = 0.75
    cloud_tags_with_size = []
    for idx, tag in enumerate(all_tags):
        rank = idx + 1
        # 排名越靠前字体越大：线性插值
        if total_tags > 1:
            font_size = max_font - (max_font - min_font) * (rank - 1) / (total_tags - 1)
        else:
            font_size = max_font
        tag.font_size = round(font_size, 2)
        tag.rank = rank
        cloud_tags_with_size.append(tag)

    ctx = {
        'cloud_tags': cloud_tags_with_size,
        'all_tags': all_tags,
        'current_mode': mode,
        'current_sort': sort,
        'current_order': order,
        'active_nav': 'tags',
        # 全站统计
        'stat_total_tags': total_tags,
        'stat_total_articles': total_articles,
        'stat_total_views': total_views,
        'stat_total_likes': total_likes,
        'stat_total_comments': total_comments,
        # 标签索引分页
        'page_obj': None,
        # ---- SEO ----
        'meta_title': f'全部标签 - {settings.SITE_NAME}',
        'meta_description': f'{settings.SITE_NAME} 文章标签云，共 {total_tags} 个标签，{total_articles} 篇文章。',
    }

    # 标签索引分页模式
    if mode == 'index':
        paginator = Paginator(all_tags, 30)  # 每页30个标签
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        ctx['page_obj'] = page_obj
        ctx['page_range'] = list(paginator.page_range)

    return render(request, 'blog/tags.html', ctx)

# 迭代#161: tag_detail视图docstring
# 迭代#162: tag_detail(request, pk) -> HttpResponse 类型提示
def tag_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """单个标签下的文章列表页：复用首页模板，叠加标签筛选。

    按主键取出标签，在 ``_base_qs`` 基础上额外过滤 ``tags=该标签``，
    再走统一的筛选 / 排序 / 分页流程。

    Args:
        request: 当前 HttpRequest 对象。
        pk: 标签主键。

    Returns:
        HttpResponse: 渲染后的文章列表 HTML（复用 ``blog/index.html``）。
    """
    from django.db.models import Sum, Avg

    tag = get_object_or_404(Tag, pk=pk)
    # 多对多过滤：tags=tag 会自动去重（_filter_articles 内也再调了 distinct）
    qs, sort, q = _filter_articles(request, _base_qs(request).filter(tags=tag))
    paginator = Paginator(qs, settings.PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))

    # 标签统计数据
    tag_articles = Article.objects.filter(status=Article.Status.PUBLISHED, tags=tag)
    tag_stats = tag_articles.aggregate(
        total_views=Sum('views'),
        total_likes=Sum('likes'),
        total_comments=Sum('comment_count'),
        avg_rating=Avg('rating_avg'),
    )

    ctx = {'page_obj': page_obj, 'page_range': list(paginator.page_range),
           'sort': sort, 'q': q, 'current_tag': tag,
           'active_kind': request.GET.get('kind', ''), 'active_nav': 'tags',
           # 标签统计
           'tag_stat_articles': tag_articles.count(),
           'tag_stat_views': tag_stats['total_views'] or 0,
           'tag_stat_likes': tag_stats['total_likes'] or 0,
           'tag_stat_comments': tag_stats['total_comments'] or 0,
           'tag_stat_avg_rating': round(tag_stats['avg_rating'] or 0, 1),
           # ---- SEO / Open Graph ----
           'meta_title': f'{tag.name} - {settings.SITE_NAME}',
           'meta_description': f'标签「{tag.name}」下的全部文章，共 {tag_articles.count()} 篇。',
           'og_type': 'website',
           'og_url': request.build_absolute_uri()}
    ctx.update(_sidebar())
    return render(request, 'blog/index.html', ctx)

@cache_page(60 * 5)
# 迭代#169: archive视图docstring
# 迭代#170: archive(request) -> HttpResponse 类型提示
# 迭代#171: archive年月分组算法注释
def archive(request: HttpRequest) -> HttpResponse:
    """文章归档页：把所有已发布文章按「年-月」分组，时间轴样式展示。

    流程：
    1. 查询全部已发布文章（按创建时间倒序），预加载分类；
    2. 用 itertools.groupby 按 ``YYYY年MM月`` 字符串分组（倒序排列自然就是最新月份在前）；
    3. 每个月组装成 ``{'year_month': ..., 'count': N, 'articles': [...]}``；
    4. 合并侧边栏数据后渲染 ``blog/archive.html``。

    Args:
        request: 当前 HttpRequest 对象。

    Returns:
        HttpResponse: 归档页 HTML。
    """
    # 仅已发布文章，按创建时间倒序（groupby 要求同组相邻，这里排序已满足）
    articles = (Article.objects.filter(status=Article.Status.PUBLISHED)
                .select_related('category').order_by('-created_at', '-id'))
    archives = []
    # groupby 依据「年-月」键分组；键相同的文章归到同一月
    for key, group in groupby(articles, key=lambda a: a.created_at.strftime('%Y年%m月')):
        month_articles = list(group)
        archives.append({
            'year_month': key,
            'count': len(month_articles),
            'articles': month_articles,
        })
    ctx = {
        'archives': archives,
        'active_nav': 'archive',   # 顶栏高亮「归档」
        # ---- SEO ----
        'meta_title': f'文章归档 - {settings.SITE_NAME}',
        'meta_description': f'{settings.SITE_NAME} 全部已发布文章按年月时间轴归档。',
        'og_type': 'website',
    }
    ctx.update(_sidebar())
    return render(request, 'blog/archive.html', ctx)

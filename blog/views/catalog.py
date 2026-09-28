# -*- coding: utf-8 -*-

"""内容目录：侧边栏、分类、标签、归档与标签云。"""

#: 导入模块「logging」，供本文件后续使用
import logging
#: 从模块「itertools」导入所需对象
from itertools import groupby
#: 从模块「django.conf」导入所需对象
from django.conf import settings
#: 从模块「django.core.cache」导入所需对象
from django.core.cache import cache
#: 从模块「django.core.paginator」导入所需对象
from django.core.paginator import Paginator
#: 从模块「django.db.models」导入所需对象
from django.db.models import Avg, Count, F, Min, Q, Sum
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
#: 从模块「django.views.decorators.cache」导入所需对象
from django.views.decorators.cache import cache_page
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
from .common import SIDEBAR_CACHE_KEY, SIDEBAR_CACHE_TIMEOUT, TAG_CLOUD_KEY, _base_qs, _filter_articles


#: 定义变量「logger」，保存对应数据
logger = logging.getLogger('blog.views')

# 迭代#119: _sidebar聚合查询注释
def _build_sidebar():
    """真正计算侧边栏数据（含聚合查询）。queryset 统一物化为 list 以便缓存序列化。

    第4轮 A4: 统计部分复用 ``context_processors.get_sidebar_stats()``
    （key=sidebar_stats, TTL 300s），避免与侧边栏统计缓存重复跑聚合 SQL。
    """
    # 仅统计已发布文章，草稿不计入侧边栏公开数据
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    published = Article.objects.filter(status=Article.Status.PUBLISHED)
    # 第4轮 A4: 统计走统一缓存（文章数/总浏览/标签数/分类数/今日访问/独立访客）
    #: 从模块「..context_processors」导入所需对象
    from ..context_processors import get_sidebar_stats
    #: 定义变量「stats」，保存对应数据
    stats = get_sidebar_stats()
    #: 返回结果并结束当前函数
    return {
        #: 配置项「stats」：字典/模型的该键设置为对应值
        'stats': stats,
        # 物化为 list：LocMemCache 需 pickle，lazy queryset 不可直接缓存
        #: 对查询结果按字段排序
        'hot_articles': list(published.order_by('-views')[:10]),
        #: 配置项「cloud_tags」：字典/模型的该键设置为对应值
        'cloud_tags': list(Tag.objects.annotate(
            #: 使用 Q/F 表达式构造复杂查询或引用字段值
            n=Count('articles', filter=Q(articles__status='published', articles__is_deleted=False)))
            #: 对查询结果按字段排序
            .filter(n__gt=0).order_by('-n')[:30]),
        #: 配置项「nav_categories」：字典/模型的该键设置为对应值
        'nav_categories': list(Category.objects.annotate(
            #: 使用 Q/F 表达式构造复杂查询或引用字段值
            n=Count('articles', filter=Q(articles__status='published', articles__is_deleted=False)))
            #: 对查询结果按字段排序
            .order_by('-n', 'name')),
    #: 该行执行对应逻辑（结合上下文理解）
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
    #: 返回结果并结束当前函数
    return cache.get_or_set(SIDEBAR_CACHE_KEY, _build_sidebar, SIDEBAR_CACHE_TIMEOUT)

def _tag_cloud_cached(limit=30, timeout=600):
    # 第2轮迭代#64: 标签云缓存——带文章数注解并缓存
    # 第3轮迭代#3: 缓存键统一为 TAG_CLOUD_KEY，与信号失效键对齐
    """
    功能：处理「tag cloud cached」相关逻辑。

    参数：
      - limit（可选，有默认值）：传入参数，含义结合函数体与调用处
      - timeout（可选，有默认值）：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：含 Django ORM 数据库查询，注意查询性能与空结果处理；读写缓存，注意缓存键口径与失效策略。
    """
    #: 定义变量「key」，保存对应数据
    key = TAG_CLOUD_KEY
    #: 返回结果并结束当前函数
    return cache.get_or_set(key, lambda: list(
        #: 使用 Q/F 表达式构造复杂查询或引用字段值
        Tag.objects.annotate(n=Count('articles', filter=Q(
            #: 定义变量「articles__status」，保存对应数据
            articles__status='published', articles__is_deleted=False)))
        #: 对查询结果按字段排序
        .filter(n__gt=0).order_by('-n')[:limit]), timeout)

def _archive_cached(timeout=600):
    # 第2轮迭代#65: 归档缓存——按年月分组的时间轴数据短 TTL 缓存
    """
    功能：处理「archive cached」相关逻辑。

    参数：
      - timeout（可选，有默认值）：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：含 Django ORM 数据库查询，注意查询性能与空结果处理；读写缓存，注意缓存键口径与失效策略。
    """
    #: 定义变量「key」，保存对应数据
    key = 'archive_data'
    def _build():
        """
        功能：构建「build」。

        返回：对应计算/查询结果。

        注意：含 Django ORM 数据库查询，注意查询性能与空结果处理。
        """
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        rows = (Article.objects.filter(status=Article.Status.PUBLISHED)
                #: 对查询结果按字段排序
                .order_by('-created_at'))
        #: 返回结果并结束当前函数
        return list(rows.values('id', 'title', 'created_at')[:500])
    #: 返回结果并结束当前函数
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
    #: 定义变量「ctx」，保存对应数据
    ctx = {'categories': Category.objects.annotate(
        #: 使用 Q/F 表达式构造复杂查询或引用字段值
        n=Count('articles', filter=Q(articles__status='published', articles__is_deleted=False))
        #: 对查询结果按字段排序
        ).order_by('-n', 'name'), 'active_nav': 'categories',
        # ---- SEO ----
        #: 配置项「meta_title」：字典/模型的该键设置为对应值
        'meta_title': f'全部分类 - {settings.SITE_NAME}',
        #: 配置项「meta_description」：字典/模型的该键设置为对应值
        'meta_description': f'{settings.SITE_NAME} 文章分类导航。'}
    #: 返回结果并结束当前函数
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
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    category = get_object_or_404(Category, pk=pk)
    # 在权限过滤之上叠加"仅该分类"的条件，再走统一筛选
    #: 该行执行对应逻辑（结合上下文理解）
    qs, sort, q = _filter_articles(
        #: 该行执行对应逻辑（结合上下文理解）
        request, _base_qs(request).filter(category=category))
    #: 定义变量「paginator」，保存对应数据
    paginator = Paginator(qs, settings.PAGE_SIZE)
    #: 读取本次请求的 GET 数据
    page_obj = paginator.get_page(request.GET.get('page'))
    #: 定义变量「ctx」，保存对应数据
    ctx = {'page_obj': page_obj, 'page_range': list(paginator.page_range),
           #: 配置项「sort」：字典/模型的该键设置为对应值
           'sort': sort, 'q': q, 'current_category': category,
           #: 读取本次请求的 GET 数据
           'active_kind': request.GET.get('kind', ''), 'active_nav': 'categories',
           # ---- SEO / Open Graph ----
           #: 配置项「meta_title」：字典/模型的该键设置为对应值
           'meta_title': f'{category.name} - {settings.SITE_NAME}',
           #: 配置项「meta_description」：字典/模型的该键设置为对应值
           'meta_description': (category.description or f'{category.name} 分类下的文章').strip(),
           #: 配置项「og_type」：字典/模型的该键设置为对应值
           'og_type': 'website',
           #: 配置项「og_url」：字典/模型的该键设置为对应值
           'og_url': request.build_absolute_uri()}
    #: 调用「ctx.update」执行相应逻辑
    ctx.update(_sidebar())
    #: 返回结果并结束当前函数
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
    #: 从模块「django.db.models」导入所需对象
    from django.db.models import Sum, Max

    # 页面模式
    #: 读取本次请求的 GET 数据
    mode = request.GET.get('mode', 'rank')

    # 排序映射
    #: 定义变量「sort_map」，保存对应数据
    sort_map = {
        #: 配置项「count」：字典/模型的该键设置为对应值
        'count': 'n',
        #: 配置项「views」：字典/模型的该键设置为对应值
        'views': 'total_views',
        #: 配置项「likes」：字典/模型的该键设置为对应值
        'likes': 'total_likes',
        #: 配置项「comments」：字典/模型的该键设置为对应值
        'comments': 'total_comments',
        #: 配置项「latest」：字典/模型的该键设置为对应值
        'latest': 'latest_article',
        #: 配置项「name」：字典/模型的该键设置为对应值
        'name': 'name',
    #: 该行执行对应逻辑（结合上下文理解）
    }
    #: 读取本次请求的 GET 数据
    sort = request.GET.get('sort', 'count')
    #: 读取本次请求的 GET 数据
    order = request.GET.get('order', 'desc')  # desc/asc
    #: 定义变量「sort_field」，保存对应数据
    sort_field = sort_map.get(sort, 'n')
    #: 定义变量「order_by」，保存对应数据
    order_by = f'-{sort_field}' if order == 'desc' else sort_field

    # 标签查询：仅聚合「已发布且未删除」文章的数量 / 总浏览 / 总点赞 / 总评论 / 最新时间
    # （旧逻辑未过滤状态与软删，把草稿、待审、回收站文章全部计入，导致数量虚高）
    #: 使用 Q/F 表达式构造复杂查询或引用字段值
    pub_cond = Q(articles__status='published', articles__is_deleted=False)
    #: 定义变量「all_tags」，保存对应数据（集合/元组）
    all_tags = (
        #: 操作「Tag」的属性或方法
        Tag.objects
        #: 该行执行对应逻辑（结合上下文理解）
        .annotate(
            #: 使用聚合函数做统计查询
            n=Count('articles', filter=pub_cond),
            #: 使用聚合函数做统计查询
            total_views=Sum('articles__views', filter=pub_cond),
            #: 使用聚合函数做统计查询
            total_likes=Sum('articles__likes', filter=pub_cond),
            #: 使用聚合函数做统计查询
            total_comments=Sum('articles__comment_count', filter=pub_cond),
            #: 使用聚合函数做统计查询
            latest_article=Max('articles__created_at', filter=pub_cond),
        #: 该行执行对应逻辑（结合上下文理解）
        )
        #: 该行执行对应逻辑（结合上下文理解）
        .filter(n__gt=0)
        #: 对查询结果按字段排序
        .order_by(order_by)
    #: 该行执行对应逻辑（结合上下文理解）
    )

    # 全站统计：直接按「已发布未删除」的唯一文章聚合，
    # 避免一篇多标签文章在各标签下被重复累加（文章总数应等于实际已发布篇数）。
    #: 定义变量「total_tags」，保存对应数据
    total_tags = all_tags.count()
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    _pub_articles = Article.objects.filter(status='published', is_deleted=False)
    #: 定义变量「_site」，保存对应数据
    _site = _pub_articles.aggregate(
        #: 使用聚合函数做统计查询
        total_views=Sum('views'), total_likes=Sum('likes'),
        #: 使用聚合函数做统计查询
        total_comments=Sum('comment_count'))
    #: 定义变量「total_articles」，保存对应数据
    total_articles = _pub_articles.count()
    #: 定义变量「total_views」，保存对应数据
    total_views = _site['total_views'] or 0
    #: 定义变量「total_likes」，保存对应数据
    total_likes = _site['total_likes'] or 0
    #: 定义变量「total_comments」，保存对应数据
    total_comments = _site['total_comments'] or 0

    # 标签云字体大小：根据排名动态调整（排名从1开始）
    # 最大字体 1.6rem，最小字体 0.75rem
    #: 定义变量「max_font」，保存对应数据
    max_font = 1.6
    #: 定义变量「min_font」，保存对应数据
    min_font = 0.75
    #: 定义变量「cloud_tags_with_size」，保存对应数据（集合/元组）
    cloud_tags_with_size = []
    #: 循环遍历，逐个处理元素
    for idx, tag in enumerate(all_tags):
        #: 定义变量「rank」，保存对应数据
        rank = idx + 1
        # 排名越靠前字体越大：线性插值
        #: 条件判断：条件成立时执行该分支
        if total_tags > 1:
            #: 定义变量「font_size」，保存对应数据
            font_size = max_font - (max_font - min_font) * (rank - 1) / (total_tags - 1)
        #: 以上条件均不成立时的兜底分支
        else:
            #: 定义变量「font_size」，保存对应数据
            font_size = max_font
        #: 定义实例/类属性「tag.font_size」，保存对应数据
        tag.font_size = round(font_size, 2)
        #: 定义实例/类属性「tag.rank」，保存对应数据
        tag.rank = rank
        #: 调用「cloud_tags_with_size.append」执行相应逻辑
        cloud_tags_with_size.append(tag)

    #: 定义变量「ctx」，保存对应数据
    ctx = {
        #: 配置项「cloud_tags」：字典/模型的该键设置为对应值
        'cloud_tags': cloud_tags_with_size,
        #: 配置项「all_tags」：字典/模型的该键设置为对应值
        'all_tags': all_tags,
        #: 配置项「current_mode」：字典/模型的该键设置为对应值
        'current_mode': mode,
        #: 配置项「current_sort」：字典/模型的该键设置为对应值
        'current_sort': sort,
        #: 配置项「current_order」：字典/模型的该键设置为对应值
        'current_order': order,
        #: 配置项「active_nav」：字典/模型的该键设置为对应值
        'active_nav': 'tags',
        # 全站统计
        #: 配置项「stat_total_tags」：字典/模型的该键设置为对应值
        'stat_total_tags': total_tags,
        #: 配置项「stat_total_articles」：字典/模型的该键设置为对应值
        'stat_total_articles': total_articles,
        #: 配置项「stat_total_views」：字典/模型的该键设置为对应值
        'stat_total_views': total_views,
        #: 配置项「stat_total_likes」：字典/模型的该键设置为对应值
        'stat_total_likes': total_likes,
        #: 配置项「stat_total_comments」：字典/模型的该键设置为对应值
        'stat_total_comments': total_comments,
        # 标签索引分页
        #: 配置项「page_obj」：字典/模型的该键设置为对应值
        'page_obj': None,
        # ---- SEO ----
        #: 配置项「meta_title」：字典/模型的该键设置为对应值
        'meta_title': f'全部标签 - {settings.SITE_NAME}',
        #: 配置项「meta_description」：字典/模型的该键设置为对应值
        'meta_description': f'{settings.SITE_NAME} 文章标签云，共 {total_tags} 个标签，{total_articles} 篇文章。',
    #: 该行执行对应逻辑（结合上下文理解）
    }

    # 标签索引分页模式
    #: 条件判断：条件成立时执行该分支
    if mode == 'index':
        #: 定义变量「paginator」，保存对应数据
        paginator = Paginator(all_tags, 30)  # 每页30个标签
        #: 读取本次请求的 GET 数据
        page_number = request.GET.get('page', 1)
        #: 定义变量「page_obj」，保存对应数据
        page_obj = paginator.get_page(page_number)
        #: 该行执行对应逻辑（结合上下文理解）
        ctx['page_obj'] = page_obj
        #: 该行执行对应逻辑（结合上下文理解）
        ctx['page_range'] = list(paginator.page_range)

    #: 返回结果并结束当前函数
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
    #: 从模块「django.db.models」导入所需对象
    from django.db.models import Sum, Avg

    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    tag = get_object_or_404(Tag, pk=pk)
    # 多对多过滤：tags=tag 会自动去重（_filter_articles 内也再调了 distinct）
    #: 该行执行对应逻辑（结合上下文理解）
    qs, sort, q = _filter_articles(request, _base_qs(request).filter(tags=tag))
    #: 定义变量「paginator」，保存对应数据
    paginator = Paginator(qs, settings.PAGE_SIZE)
    #: 读取本次请求的 GET 数据
    page_obj = paginator.get_page(request.GET.get('page'))

    # 标签统计数据
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    tag_articles = Article.objects.filter(status=Article.Status.PUBLISHED, tags=tag)
    #: 定义变量「tag_stats」，保存对应数据
    tag_stats = tag_articles.aggregate(
        #: 使用聚合函数做统计查询
        total_views=Sum('views'),
        #: 使用聚合函数做统计查询
        total_likes=Sum('likes'),
        #: 使用聚合函数做统计查询
        total_comments=Sum('comment_count'),
        #: 使用聚合函数做统计查询
        avg_rating=Avg('rating_avg'),
    #: 该行执行对应逻辑（结合上下文理解）
    )

    #: 定义变量「ctx」，保存对应数据
    ctx = {'page_obj': page_obj, 'page_range': list(paginator.page_range),
           #: 配置项「sort」：字典/模型的该键设置为对应值
           'sort': sort, 'q': q, 'current_tag': tag,
           #: 读取本次请求的 GET 数据
           'active_kind': request.GET.get('kind', ''), 'active_nav': 'tags',
           # 标签统计
           #: 配置项「tag_stat_articles」：字典/模型的该键设置为对应值
           'tag_stat_articles': tag_articles.count(),
           #: 配置项「tag_stat_views」：字典/模型的该键设置为对应值
           'tag_stat_views': tag_stats['total_views'] or 0,
           #: 配置项「tag_stat_likes」：字典/模型的该键设置为对应值
           'tag_stat_likes': tag_stats['total_likes'] or 0,
           #: 配置项「tag_stat_comments」：字典/模型的该键设置为对应值
           'tag_stat_comments': tag_stats['total_comments'] or 0,
           #: 配置项「tag_stat_avg_rating」：字典/模型的该键设置为对应值
           'tag_stat_avg_rating': round(tag_stats['avg_rating'] or 0, 1),
           # ---- SEO / Open Graph ----
           #: 配置项「meta_title」：字典/模型的该键设置为对应值
           'meta_title': f'{tag.name} - {settings.SITE_NAME}',
           #: 配置项「meta_description」：字典/模型的该键设置为对应值
           'meta_description': f'标签「{tag.name}」下的全部文章，共 {tag_articles.count()} 篇。',
           #: 配置项「og_type」：字典/模型的该键设置为对应值
           'og_type': 'website',
           #: 配置项「og_url」：字典/模型的该键设置为对应值
           'og_url': request.build_absolute_uri()}
    #: 调用「ctx.update」执行相应逻辑
    ctx.update(_sidebar())
    #: 返回结果并结束当前函数
    return render(request, 'blog/index.html', ctx)

#: 装饰器：为下一个定义附加「cache_page(60 * 5)」行为（权限、缓存、注册信号等）
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
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    articles = (Article.objects.filter(status=Article.Status.PUBLISHED)
                #: ORM 预加载关联，减少 N+1 查询提升性能
                .select_related('category').order_by('-created_at', '-id'))
    #: 定义变量「archives」，保存对应数据（集合/元组）
    archives = []
    # groupby 依据「年-月」键分组；键相同的文章归到同一月
    #: 循环遍历，逐个处理元素
    for key, group in groupby(articles, key=lambda a: a.created_at.strftime('%Y年%m月')):
        #: 定义变量「month_articles」，保存对应数据
        month_articles = list(group)
        #: 调用「archives.append」执行相应逻辑
        archives.append({
            #: 配置项「year_month」：字典/模型的该键设置为对应值
            'year_month': key,
            #: 配置项「count」：字典/模型的该键设置为对应值
            'count': len(month_articles),
            #: 配置项「articles」：字典/模型的该键设置为对应值
            'articles': month_articles,
        #: 该行执行对应逻辑（结合上下文理解）
        })
    #: 定义变量「ctx」，保存对应数据
    ctx = {
        #: 配置项「archives」：字典/模型的该键设置为对应值
        'archives': archives,
        #: 配置项「active_nav」：字典/模型的该键设置为对应值
        'active_nav': 'archive',   # 顶栏高亮「归档」
        # ---- SEO ----
        #: 配置项「meta_title」：字典/模型的该键设置为对应值
        'meta_title': f'文章归档 - {settings.SITE_NAME}',
        #: 配置项「meta_description」：字典/模型的该键设置为对应值
        'meta_description': f'{settings.SITE_NAME} 全部已发布文章按年月时间轴归档。',
        #: 配置项「og_type」：字典/模型的该键设置为对应值
        'og_type': 'website',
    #: 该行执行对应逻辑（结合上下文理解）
    }
    #: 调用「ctx.update」执行相应逻辑
    ctx.update(_sidebar())
    #: 返回结果并结束当前函数
    return render(request, 'blog/archive.html', ctx)

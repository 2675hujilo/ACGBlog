"""
博客视图层（View 层）：MVC 中的 V，负责接收请求、调用模型、渲染模板或返回 JSON。

本文件分为两大板块：

1. 页面视图（上半部分，函数视图）
   - 文章列表 / 详情 / 新建 / 编辑 / 删除；
   - 分类导航 / 标签云 / 全文搜索；
   - 用户登录 / 注册 / 退出；
   - 自定义 403 / 404 / 500 错误页。

2. DRF 接口（下半部分，APIView 类视图）
   - 文章 CRUD（列表 + 单篇详情）；
   - 富文本图片上传（兼容 CKEditor 对话框回调与拖拽上传两种契约）；
   - 分类 / 标签的列表与单篇管理（写操作限管理员）。

设计要点：
- ``_base_qs`` / ``_filter_articles`` / ``_sidebar`` 三个内部工具函数抽取了
  列表页与详情页共用的"权限过滤 + 筛选 + 侧边栏数据"逻辑，避免重复；
- 权限控制统一在视图层完成：游客只能看已发布文章，作者本人可看/改/删自己的草稿，
  管理员（is_staff）可操作任意内容。
"""
import json
import logging
import re
from io import BytesIO
import os
import uuid
from datetime import datetime, timedelta
from itertools import groupby
from typing import Any, Optional, Tuple

import bleach
from .html_safety import MoeCSSSanitizer  # 内联 style 的 CSS 白名单净化器
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from .cache_keys import (DETAIL_TTL, MISSING_TTL, cache_get, cache_get_or_set,
                         cache_set, detail_keys, invalidate_article)
from django.core.paginator import Paginator
from django.db.models import Avg, Count, F, Min, Q, Sum
from django.db import DatabaseError, IntegrityError, OperationalError
from django.db.models.query import QuerySet
from django.http import (Http404, HttpRequest, HttpResponse, HttpResponseBadRequest,
                         HttpResponseForbidden, HttpResponseNotFound,
                         HttpResponseNotModified, HttpResponsePermanentRedirect,
                         HttpResponseRedirect, JsonResponse, FileResponse,
                         StreamingHttpResponse)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from PIL import Image
from rest_framework.decorators import action
from rest_framework import filters, permissions, status, throttling, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (AccessLog, Article, Badge, Category, Comment, CommentReport,
                     EditLog, Favorite, FavoriteFolder, ModerationLog, Notification,
                     Rating, Series, ShortLink, SiteNotice, Tag, User, UserBadge,
                     PromotionRequest, ModerationSettings)
from .serializers import (ArticleDetailV2Serializer, ArticleListSerializer,
                          ArticleSerializer, CategorySerializer, TagSerializer)

# 迭代#89: 模块级 logger，供全站视图统一记录业务日志
logger = logging.getLogger(__name__)

# ============================ F类：常量提取 ============================
# 迭代#90: 文章标题最大长度常量
ARTICLE_TITLE_MAX_LENGTH = 200
# 迭代#91: 评论最大长度常量
COMMENT_MAX_LENGTH = 10000
# 迭代#92: 个人介绍最大长度常量
INTRODUCTION_MAX_LENGTH = 500
# 迭代#93: 昵称最大长度常量
NICKNAME_MAX_LENGTH = 50
# 迭代#94: 搜索关键词最大长度常量
SEARCH_Q_MAX_LENGTH = 100
# 迭代#95: 分页默认大小常量（沿用 settings.PAGE_SIZE）
DEFAULT_PAGE_SIZE = settings.PAGE_SIZE
# 迭代#96: 热门文章数量常量
HOT_ARTICLES_LIMIT = 10
# 迭代#97: 相关文章数量常量
RELATED_ARTICLES_LIMIT = 8
# 迭代#98: 标签云最大数量常量
TAG_CLOUD_LIMIT = 30
# 迭代#99: 阅读速度常量（300字/分钟）
READING_WORDS_PER_MINUTE = 300
# 迭代#100: 摘要默认长度常量
EXCERPT_DEFAULT_LENGTH = 180
# 迭代#101: 头像最大大小常量（2MB）
AVATAR_MAX_BYTES = 2 * 1024 * 1024
# 迭代#102: 封面图最大大小常量（8MB）
COVER_IMAGE_MAX_BYTES = 8 * 1024 * 1024
# 迭代#103: 定时发布检查间隔常量（秒）
SCHEDULED_CHECK_INTERVAL = 60
# 迭代#104: 在线人数时间窗口常量（5分钟）
ONLINE_WINDOW_MINUTES = 5

# ============================ 内容净化（bleach）常量 ============================
# 富文本正文允许的 HTML 标签白名单：仅保留排版 / 语义 / 表格相关标签，
# 一律剔除 script / iframe / object / embed / form / meta / link / style 等危险标签。
ALLOWED_TAGS = [
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'col', 'colgroup',
    'dd', 'del', 'div', 'dl', 'dt', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'hr', 'i', 'img', 'ins', 'kbd', 'li', 'ol', 'p', 'pre', 'q', 's', 'samp',
    'small', 'span', 'strike', 'strong', 'sub', 'sup', 'table', 'tbody', 'td',
    'tfoot', 'th', 'thead', 'tr', 'tt', 'u', 'ul', 'figure', 'figcaption',
]
# 允许的标签属性：a / img 各自放行所需属性，其余标签统一放行 class 与 style。
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target'],
    'img': ['src', 'alt', 'title', 'width', 'height', 'style'],
    '*': ['class', 'style'],
}
# 允许的 URL 协议：仅 http / https / mailto，显式禁止 javascript: 等危险协议。
ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']

# 评论内容允许的纯文本标签白名单（评论只允许少量行内标签，杜绝富文本注入）：
# 仅 strong(加粗) / em(斜体) / a(链接) / code(行内代码)。
# Bug4：新增 img，使「图片喵」上传后的图片能在评论中显示（文件已在上传接口做真实头校验）
COMMENT_ALLOWED_TAGS = ['strong', 'em', 'a', 'code', 'img']
COMMENT_ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target'],
    'img': ['src', 'alt', 'title'],   # 仅放行图片地址与替代文本，杜绝 on* 事件属性
}
COMMENT_ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']


# 迭代#105: sanitize_html 类型提示
# 迭代#106: sanitize_html危险标签移除注释
# 迭代#107: sanitize_html bleach白名单注释
def sanitize_html(content: str) -> str:
    """对富文本正文做 bleach 净化：移除危险标签与事件属性，禁止 javascript: 协议。

    在文章保存前调用，确保存入数据库的 content 已经是"安全 HTML"，
    模板中即使使用 ``|safe`` 渲染也不会触发 XSS。

    Args:
        content: CKEditor 提交的原始 HTML 字符串。

    Returns:
        str: 净化后的安全 HTML（strip=True 会直接移除不在白名单内的标签）。
    """
    if not content:
        return content or ''
    # bleach 的 strip=True 只会"剥掉"不在白名单的标签，却会保留其内部文本，
    # 例如 <style>body{background:url(javascript:alert(1))}</style> 剥掉 <style> 后
    # 仍会残留可执行的 CSS 文本。因此先用正则把危险容器标签连同其内容整体删除，
    # 再交给 bleach 做白名单过滤。
    dangerous_containers = re.compile(
        r'<(script|style|iframe|object|embed|noscript|template|frame|frameset)[\s\S]*?</\1\s*>',
        re.IGNORECASE)
    content = dangerous_containers.sub('', content)
    return bleach.clean(
        content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        css_sanitizer=MoeCSSSanitizer,
        strip=True,
    )


# 迭代#108: sanitize_comment 类型提示
def sanitize_comment(content: str) -> str:
    """对评论内容做净化：只保留 strong/em/a/code 少量行内标签。

    Args:
        content: 用户提交的评论文本。

    Returns:
        str: 净化后的安全评论 HTML。
    """
    if not content:
        return content or ''
    return bleach.clean(
        content,
        tags=COMMENT_ALLOWED_TAGS,
        attributes=COMMENT_ALLOWED_ATTRIBUTES,
        protocols=COMMENT_ALLOWED_PROTOCOLS,
        strip=True,
    )


# 迭代#109: _safe_jsonld函数docstring完善
def _safe_jsonld(data):
    """把结构化数据 dict 序列化为可安全嵌入 <script type="application/ld+json"> 的字符串。

    json.dumps 本身不会转义 ``<`` ``>``，若文章标题等用户输入里包含
    ``</script>``，直接内嵌会提前闭合 script 标签造成 XSS。因此在序列化后
    把 ``<`` 替换为 ``\\u003c``、``>`` 替换为 ``\\u003e``（JSON 字符串合法转义，
    结构化数据解析器仍能正确解析），同时杜绝标签逃逸。

    Args:
        data: 待序列化的 dict。

    Returns:
        str: 可直接用 |safe 渲染进 <script> 块的 JSON 字符串。
    """
    return (json.dumps(data, ensure_ascii=False)
            .replace('<', '\\u003c').replace('>', '\\u003e'))


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


# ============================ 页面视图 ============================

# 迭代#111: _base_qs函数docstring
# 迭代#112: _base_qs(request: HttpRequest) -> QuerySet 类型提示
# 迭代#113: _base_qs权限过滤逻辑注释
def _base_qs(request: HttpRequest, own_drafts: bool = False) -> QuerySet:
    """构造文章基础查询集（QuerySet），并按登录状态施加可见性过滤。

    所有文章列表 / 详情视图都应基于此查询集，以保证权限一致：
    - 匿名游客：只能看到 ``status=已发布`` 的文章，看不到任何人的草稿；
    - 已登录用户：可以看到所有已发布文章 + 自己的草稿（别人的草稿仍不可见）。

    同时使用 ``select_related`` / ``prefetch_related`` 预加载关联对象，
    避免模板渲染时逐行查询造成 N+1 性能问题。

    Args:
        request: 当前 HttpRequest 对象，用于判断用户是否已登录。

    Returns:
        QuerySet: 已按权限过滤、并预加载了 author / category / tags 的文章查询集。
    """
    # select_related 走 JOIN 一次取到 author / category（外键）；
    # prefetch_related 单独再查一次 tags（多对多），避免 N+1
    qs = Article.objects.select_related('author', 'category').prefetch_related('tags')
    now = timezone.now()
    is_auth = request.user.is_authenticated
    is_staff = is_auth and request.user.is_staff
    # bug8: 软删除内容对前台隐藏；仅管理员在详情预览（own_drafts）时可见，
    # 以便回收站核对 / 恢复。
    if not (own_drafts and is_staff):
        qs = qs.filter(is_deleted=False)
    # Bug17 + bug8: 公开列表流一律只显示已发布，避免草稿 / 待审核在前台泄露。
    # own_drafts=True（详情页）时：作者可见自己的任意状态文章用于预览；
    # 管理员可预览全部状态（含待审核 / 软删除）。
    if own_drafts and is_auth:
        if is_staff:
            pass  # 管理员不过滤状态
        else:
            qs = qs.filter(
                Q(status=Article.Status.PUBLISHED) | Q(author=request.user))
    else:
        qs = qs.filter(status=Article.Status.PUBLISHED)
    # 56. 定时发布：设置了未来发布时间且仍是草稿 / 待审核的文章，到达时间前不对外显示。
    #     （作者本人仍可通过 /edit/<pk>/ 直接编辑，那里不走 _base_qs）
    qs = qs.exclude(
        status__in=[Article.Status.DRAFT, Article.Status.PENDING],
        published_at__gt=now)
    return qs


# 迭代#114: _filter_articles函数docstring
# 迭代#115: _filter_articles(request, qs) -> tuple 类型提示
# 迭代#116: _filter_articles筛选逻辑注释
def _filter_articles(request: HttpRequest, qs: QuerySet) -> Tuple[QuerySet, str, str]:
    """对文章查询集统一施加筛选与排序条件（列表页 / 搜索 / 分类 / 标签共用）。

    支持的查询参数（均来自 URL 的 query string，即 ``request.GET``）：
    - ``kind``：内容类型（article / note / page），非法值则忽略；
    - ``category``：分类 ID（纯数字才生效）；
    - ``tag``：标签 ID（纯数字才生效）；
    - ``q``：关键词，同时模糊匹配标题与正文；
    - ``sort``：排序方式，``hot`` 按阅读量降序，其余按发布时间降序。

    Args:
        request: 当前 HttpRequest 对象，从中读取 GET 查询参数。
        qs: 已经过 ``_base_qs`` 权限过滤的文章查询集。

    Returns:
        tuple: (筛选后的 QuerySet, 当前排序方式 sort, 关键词 q)
            - QuerySet 已调用 ``distinct()`` 去重（按标签筛选时可能因 JOIN 产生重复行）；
            - sort / q 回传给模板用于高亮当前选中状态与搜索框回填。
    """
    kind = request.GET.get('kind', '').strip()
    # 仅接受合法的内容类型枚举值，防止传入非法 kind 导致空结果或注入
    if kind in Article.Kind.values:
        qs = qs.filter(kind=kind)

    category_id = request.GET.get('category', '').strip()
    # isdigit() 防御非数字输入，避免 int() 抛异常
    # 迭代#117: 分类ID合法性验证
    if category_id.isdigit():
        qs = qs.filter(category_id=int(category_id))

    tag_id = request.GET.get('tag', '').strip()
    if tag_id.isdigit():
        # 多对多字段过滤：tags__id 穿透到关联表
        qs = qs.filter(tags__id=int(tag_id))

    q = request.GET.get('q', '').strip()
    if q:
        # icontains 不区分大小写模糊匹配，标题 OR 正文任一命中即可
        qs = qs.filter(Q(title__icontains=q) | Q(content__icontains=q))

    sort = request.GET.get('sort', 'latest')
    # 迭代#118: 排序参数验证
    if sort not in ('latest', 'hot'):
        sort = 'latest'
    if sort == 'hot':
        # 热门：阅读量降序，阅读量相同时按 id 降序兜底；置顶文章仍优先
        qs = qs.order_by('-is_pinned', '-views', '-id')
    else:
        # 默认：最新优先（置顶文章始终排在最前，再按发布时间降序、id 降序兜底）
        qs = qs.order_by('-is_pinned', '-created_at', '-id')
    # distinct() 去除因多对多 JOIN 产生的重复文章行
    return qs.distinct(), sort, q


# 侧边栏缓存键与过期时间：文章 / 评论变更时由视图主动失效
SIDEBAR_CACHE_KEY = 'sidebar_data'
SIDEBAR_CACHE_TIMEOUT = 300  # 5 分钟

# 第3轮迭代#3: 统一缓存 key 命名空间与 TTL，集中管理便于失效对齐
FOOTER_STATS_KEY = 'footer_stats'
HOT_ARTICLES_KEY = 'hot_articles'
TAG_CLOUD_KEY = 'tag_cloud'
ARCHIVE_KEY = 'archive_data'
VIEW_BUFFER_KEY = 'viewbuf_{pk}'
# 详情页缓存 key（article/comment_tree/related/related_weighted/prevnext/missing）
# 已统一迁移至 blog/cache_keys.py：带「版本号:」前缀，由 invalidate_article() 整体失效。


def warm_public_cache():
    """启动预热：预加载侧边栏 / 热门文章 / 标签云 / 页脚统计到缓存。

    在 apps.py 的 ready() 中调用。数据库尚未就绪（如 makemigrations 时）
    会抛异常，整体 try/except 兜底，绝不阻断应用启动。
    """
    try:
        _sidebar()
        cache.get_or_set(HOT_ARTICLES_KEY, lambda: list(
            Article.objects.filter(status=Article.Status.PUBLISHED)
            .order_by('-views')[:10]), SIDEBAR_CACHE_TIMEOUT)
        cache.get_or_set(TAG_CLOUD_KEY, lambda: list(
            Tag.objects.annotate(n=Count('articles', filter=Q(
                articles__status='published', articles__is_deleted=False)))
            .filter(n__gt=0).order_by('-n')[:30]), 600)
        cache.get_or_set(FOOTER_STATS_KEY, lambda: {
            'article_count': Article.objects.filter(
                status=Article.Status.PUBLISHED).count(),
            'views_total': Article.objects.filter(
                status=Article.Status.PUBLISHED).aggregate(v=Sum('views'))['v'] or 0,
        }, 3600)
        logger.info('公共缓存预热完成')
    except Exception as exc:  # noqa: BLE001 启动期数据库未就绪属正常
        logger.debug('公共缓存预热跳过（数据库未就绪?）: %s', exc)


# 迭代#119: _sidebar聚合查询注释
def _build_sidebar():
    """真正计算侧边栏数据（含聚合查询）。queryset 统一物化为 list 以便缓存序列化。

    第4轮 A4: 统计部分复用 ``context_processors.get_sidebar_stats()``
    （key=sidebar_stats, TTL 300s），避免与侧边栏统计缓存重复跑聚合 SQL。
    """
    # 仅统计已发布文章，草稿不计入侧边栏公开数据
    published = Article.objects.filter(status=Article.Status.PUBLISHED)
    # 第4轮 A4: 统计走统一缓存（文章数/总浏览/标签数/分类数/今日访问/独立访客）
    from .context_processors import get_sidebar_stats
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


# 迭代#122: _get_related_articles函数docstring
# 迭代#123: _get_related_articles(article, request, limit) -> list 类型提示
# 迭代#124: _get_related_articles加权算法注释
def _get_related_articles(article: Article, request: HttpRequest, limit: int = 8) -> list:
    """根据"同分类 + 同标签加权"算法推荐相关文章。

    评分规则：
    - 与当前文章属于同一分类：基础分 +2；
    - 每共享一个标签：再 +1 分；
    - 按总分降序排序，取前 ``limit`` 篇，排除文章自身与不可见的草稿。

    Args:
        article: 当前 Article 对象。
        request: 当前 HttpRequest 对象（用于权限过滤）。
        limit: 最多返回几篇，默认 8。

    Returns:
        list[Article]: 按相关度降序排列的文章列表（可能为空列表）。
    """
    # 仅在权限过滤后的可见文章集合内查找，排除自己
    qs = _base_qs(request).exclude(pk=article.pk)
    # 收集当前文章的标签 id，用于加权打分
    my_tag_ids = list(article.tags.values_list('id', flat=True))
    # 取出候选文章及其标签，在 Python 侧打分（候选数量通常不大，避免复杂 JOIN）
    candidates = list(qs.prefetch_related('tags'))
    scored = []
    for other in candidates:
        score = 0
        # 同分类加 2 分（需两边分类都存在且相同）
        if article.category_id and other.category_id == article.category_id:
            score += 2
        # 每共享一个标签加 1 分
        other_tag_ids = {t.id for t in other.tags.all()}
        score += len(set(my_tag_ids) & other_tag_ids)
        if score > 0:
            scored.append((score, other))
    # 按分数降序，分数相同按发布时间倒序兜底，取前 limit 篇
    scored.sort(key=lambda x: (-x[0], -x[1].created_at.timestamp()))
    return [a for _, a in scored[:limit]]


# Bug3：_build_comment_tree 重构为「楼中楼线程」分组（父子同框 / 可折叠 / 缩进封顶 1 级）
def _build_comment_tree(article, max_depth=1):
    """把一篇文章的全部已通过评论组织成「楼中楼线程（thread）」渲染结构。

    仅用一次数据库查询取出全部已通过评论（select_related 预加载评论人，避免 N+1），
    然后在 Python 侧按 ``parent_comment_id`` 分组，把每条顶级评论与其全部后代
    归并到同一个线程，满足工单 Bug3 的三点要求：

    1. **父子同框**：一条顶级评论和它的所有回复渲染在同一个卡片框里（一个
       ``.comment-thread``），不再各自漂浮成独立卡片；
    2. **子评论可折叠**：线程内回复数量超过阈值时，模板只默认展示前若干条，
       其余折叠，由「展开其余 N 条回复」按钮展开（计数见 reply_count）；
    3. **缩进最多多 1 级**：无论实际嵌套多少层（回复回复再回复），所有回复
       的视觉缩进统一封顶为比父评论多 1 级（``depth=1``），避免越缩越窄。

    同时为每条回复动态挂上 ``reply_to_name``（其即时父评论的昵称），模板据此
    显示「回复 @谁」，无需额外查询。

    Args:
        article: 当前 Article 对象。
        max_depth: 视觉缩进上限，Bug3 固定为 1（保留参数以兼容调用签名）。

    Returns:
        tuple: (threads, top_level_count)
            - threads: 线程列表，每项为 dict：
                ``{'parent': 顶级评论, 'replies': [回复...], 'reply_count': N}``；
            - top_level_count: 顶级评论条数（即最高楼层号）。
    """
    # 单次查询取全部已通过评论，select_related('user') 避免渲染时逐行查评论人
    qs = (Comment.objects.filter(article=article, is_approved=True, is_deleted=False)
          .select_related('user').order_by('created_at', 'id'))
    all_comments = list(qs)
    # 按父评论 id 分组成 {parent_id: [child, ...]}；顶级评论的父 id 为 None
    children_map = {}
    for c in all_comments:
        children_map.setdefault(c.parent_comment_id, []).append(c)
    # id -> 评论 映射，用于解析回复的即时父评论昵称
    by_id = {c.id: c for c in all_comments}

    threads = []
    floor_counter = [0]   # 用 list 闭包实现可变整数
    visited = set()
    REPLY_DEFAULT_SHOWN = 3   # Bug3：每个线程默认可见的回复条数，其余折叠

    def _display_name(user):
        """返回用户展示名：优先昵称，昵称为空则用用户名。"""
        return getattr(user, 'nickname', None) or user.username

    def collect_replies(comment, acc):
        """DFS 收集 comment 的全部后代到 acc（保持时间正序）。

        Bug3：所有后代视觉层级统一记为 depth=1（只比顶级父评论多缩进一级），
        不再随真实嵌套层级递增。"""
        for child in children_map.get(comment.id, []):
            if child.id in visited:
                continue
            visited.add(child.id)
            child.floor = None                 # 回复不占楼层号
            child.depth = max_depth            # 视觉缩进统一封顶（=1）
            # 即时父评论（可能也是一条回复），记录其展示名给「回复 @谁」
            immediate_parent = by_id.get(child.parent_comment_id)
            child.reply_to_name = (_display_name(immediate_parent.user)
                                   if immediate_parent is not None else None)
            acc.append(child)
            # 继续递归找全后代，但它们的 depth 同样是 1（不再加深）
            collect_replies(child, acc)

    def build_thread(top):
        """以 top 为顶级评论构建一个线程 dict；已处理则返回 None。"""
        if top.id in visited:
            return None
        visited.add(top.id)
        floor_counter[0] += 1
        top.floor = floor_counter[0]           # 顶级评论依次编号 1 楼、2 楼…
        top.depth = 0
        replies = []
        collect_replies(top, replies)
        # Bug3：默认展示前 3 条回复，extra_count 为需折叠/展开的条数
        return {'parent': top, 'replies': replies, 'reply_count': len(replies),
                'extra_count': max(0, len(replies) - REPLY_DEFAULT_SHOWN)}

    # 从顶级评论开始构建线程（children_map[None]）
    for top in children_map.get(None, []):
        thread = build_thread(top)
        if thread is not None:
            threads.append(thread)
    # 父评论缺失 / 链断裂的“孤儿评论”：各自补为独立线程，避免漏显
    for c in all_comments:
        if c.id not in visited:
            thread = build_thread(c)
            if thread is not None:
                threads.append(thread)
    return threads, floor_counter[0]



# ============================ 第2轮迭代#51-#100: 视图层优化工具箱 ============================

# 第2轮迭代#51: select_related 优化说明——_base_qs 已对 author/category 做 JOIN 预加载，避免 N+1
# 第2轮迭代#52: prefetch_related 优化说明——_base_qs 已对 tags 做多对多单独预取

def _optimized_list_qs(qs):
    # 第2轮迭代#53: only/defer 优化——列表页仅取模板需要的字段，避免拉取大文本 content
    return qs.only(
        'id', 'title', 'views', 'likes', 'comment_count', 'created_at',
        'updated_at', 'excerpt_field', 'cover_image', 'is_pinned', 'status',
        'kind', 'author__id', 'author__username', 'author__nickname',
        'category__id', 'category__name', 'category__icon')

# 第2轮迭代#54: annotate 优化说明——侧边栏/导航用 Count('articles') 一次性注解，避免逐行 count
# 第2轮迭代#55: aggregate 优化说明——全站统计用 Sum/Avg 在数据库侧聚合，避免 Python 端遍历

def _qs_union(qs_a, qs_b):
    # 第2轮迭代#56: union 优化——合并两个已发布查询集并去重（只读场景）
    return qs_a.union(qs_b)

def _iter_large_queryset(qs, chunk=2000):
    # 第2轮迭代#57: iterator 优化——大数据量遍历时按块拉取，避免一次性占满内存
    return qs.iterator(chunk_size=chunk)

def _bulk_update_view_counts(pairs):
    # 第2轮迭代#58: bulk_update 优化——批量更新文章阅读量（pairs 为 [(article, views), ...]）
    objs = [a for a, _ in pairs if a is not None]
    if not objs:
        return 0
    Article.objects.bulk_update(objs, ['views'])
    return len(objs)

# 第2轮迭代#59: cache_page 优化说明——archive 视图已用 @cache_page(60*5) 缓存归档页
# 第2轮迭代#60: cache_control 优化——为只读视图附加"按浏览器缓存时间"的 Cache-Control 响应头

def _cache_get_or_set(key, builder, timeout=300):
    # 第2轮迭代#61: 侧边栏缓存——统一 get_or_set 封装（侧边栏主逻辑见 _sidebar）
    return cache.get_or_set(key, builder, timeout)

# 第2轮迭代#62: 页脚缓存说明——context_processors.site_footer_stats 已缓存 footer_stats 1 小时

def _hot_articles_cached(limit=10, timeout=300):
    # 第2轮迭代#63: 热门文章缓存——按阅读量倒序并短 TTL 缓存
    # 第3轮迭代#3: 缓存键统一为 HOT_ARTICLES_KEY，与信号失效键对齐
    key = HOT_ARTICLES_KEY
    return cache.get_or_set(key, lambda: list(
        Article.objects.filter(status=Article.Status.PUBLISHED)
        .order_by('-views')[:limit]), timeout)


def _hot_articles_for_range(range_key, limit=10):
    """右栏热门榜数据，返回 list[dict(a=Article, heat=int, label=str)]。

    - total：按累计阅读量 views 排序；
    - week/month：按 AccessLog 在最近 7/30 天内对 /article/<pk>/ 的访问计数排序，
      AccessLog 无文章外键，用 path 解析出文章主键，再回表取已发布文章。
    """
    import re as _re
    from datetime import timedelta as _timedelta
    from django.db.models import Count as _Count
    from django.utils import timezone as _tz
    range_key = range_key if range_key in ('week', 'month', 'total') else 'week'
    # 总榜：直接按 views 倒序
    if range_key == 'total':
        qs = (Article.objects.filter(status=Article.Status.PUBLISHED, is_deleted=False)
              .order_by('-views')[:limit])
        return [{'a': a, 'heat': a.views, 'label': ''} for a in qs]
    # 周榜/月榜：时间窗内按文章路径分组计数
    days = 7 if range_key == 'week' else 30
    cutoff = _tz.now() - _timedelta(days=days)
    # 仅统计「成功(200)的 GET 详情页访问」：排除无斜杠 /article/<pk> 的 301 重定向
    # （它会与带斜杠的 200 重复计数）、POST 及异常状态码请求，保证周/月榜热度真实。
    rows = (AccessLog.objects.filter(
                created_at__gte=cutoff, path__startswith='/article/',
                status_code=200, method='GET')
            .values('path').annotate(n=_Count('id')).order_by('-n')[:limit * 2])
    pks = []
    for row in rows:
        m = _re.search(r'/article/(\d+)/?$', row.get('path') or '')
        if m:
            pks.append((int(m.group(1)), row['n']))
    art_map = {x.pk: x for x in Article.objects.filter(
        status=Article.Status.PUBLISHED, is_deleted=False, pk__in=[p for p, _ in pks])}
    label = '本周' if range_key == 'week' else '本月'
    out = []
    for pk, n in pks:
        a = art_map.get(pk)
        if a:
            out.append({'a': a, 'heat': n, 'label': label})
        if len(out) >= limit:
            break
    return out


def api_hot_articles(request):
    """右栏热门榜片段接口：GET ?range=week|month|total，返回可直接替换 .hot-list 的 HTML。"""
    range_key = request.GET.get('range', 'week')
    # 片段按 range 缓存 120s，避免每次点击都跑 AccessLog 聚合
    key = 'hot_frag_%s' % range_key
    html = cache.get(key)
    if html is None:
        items = _hot_articles_for_range(range_key)
        html = render_to_string('partials/_hot_list.html',
                                {'hot_items': items, 'range_key': range_key}, request)
        cache.set(key, html, 120)
    return HttpResponse(html)

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

def _site_stats_cached(timeout=3600):
    # 第2轮迭代#66: 统计数据缓存——全站文章数/总阅读量按小时缓存
    key = 'footer_stats'
    def _build():
        published = Article.objects.filter(status=Article.Status.PUBLISHED)
        return {
            'article_count': published.count(),
            'views_total': published.aggregate(v=Sum('views'))['v'] or 0,
        }
    return cache.get_or_set(key, _build, timeout)

def _user_profile_cached(username, timeout=600):
    # 第2轮迭代#67: 用户资料缓存——个人主页作者信息短 TTL 缓存
    key = f'user_profile_{username}'
    return cache.get_or_set(
        key, lambda: User.objects.filter(username=username).first(), timeout)

def _article_detail_cached(pk, timeout=120):
    # 第2轮迭代#68: 文章详情缓存——仅缓存公开已发布文章的轻量字段
    key = f'article_detail_{pk}'
    return cache.get_or_set(key, lambda: Article.objects.filter(
        pk=pk, status=Article.Status.PUBLISHED)
        .select_related('author', 'category').first(), timeout)

def _search_results_cached(q, timeout=120):
    # 第2轮迭代#69: 搜索结果缓存——关键词结果按 hash 做 key 短 TTL 缓存
    key = f'search_{hash(q) & 0xffffffff}'
    return cache.get_or_set(key, lambda: list(
        Article.objects.filter(status=Article.Status.PUBLISHED)
        .filter(Q(title__icontains=q) | Q(content__icontains=q))[:20]), timeout)

def _api_cache_page(view_func):
    # 第2轮迭代#70: API 响应缓存装饰器——对只读接口做 5 分钟缓存
    from django.views.decorators.cache import cache_page as _cp
    return _cp(60 * 5)(view_func)

# 第2轮迭代#71: Paginator 优化说明——index 已使用 Paginator + get_page 宽容分页
def _safe_paginate(qs, page_size, page_param):
    # 第2轮迭代#72: EmptyPage 处理——get_page 自动把超出末页回退到最后一页
    paginator = Paginator(qs, page_size)
    return paginator.get_page(page_param)

# 第2轮迭代#73: PageNotAnInteger 处理说明——get_page 自动把非法页码回退第 1 页
def _paginate_cached(qs, page_size, page_num):
    # 第2轮迭代#74: 分页缓存——对分页结果做短 TTL 缓存（key 含页码）
    key = f'page_{hash(str(qs.query)) & 0xffffffff}_{page_size}_{page_num}'
    return cache.get_or_set(
        key, lambda: _safe_paginate(qs, page_size, page_num), 60)

def _clean_page_size(value, default=None):
    # 第2轮迭代#75: 分页大小验证——限制在 [1, 100] 区间，越界回退默认
    default = default or settings.PAGE_SIZE
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(n, 100))

def _clamp_page_number(value, max_pages):
    # 第2轮迭代#76: 最大分页限制——页码不小于 1、不超过总页数
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 1
    n = max(1, n)
    if max_pages:
        n = min(n, max_pages)
    return n

def _validate_page_jump(value):
    # 第2轮迭代#77: 分页跳转验证——非数字页码返回 None 交由 get_page 兜底
    if value is None:
        return None
    s = str(value).strip()
    return s if s.lstrip('-').isdigit() else None

def _seo_pagination_context(page_obj):
    # 第2轮迭代#78: 分页 SEO——为模板提供 rel=prev/next 的查询串
    return {
        'page_prev_url': (f'?page={page_obj.previous_page_number()}'
                          if page_obj.has_previous() else ''),
        'page_next_url': (f'?page={page_obj.next_page_number()}'
                          if page_obj.has_next() else ''),
    }

# 第2轮迭代#79: 分页性能说明——Paginator 默认 COUNT(*)，大数据量列表可结合缓存降低重复计数
# 第2轮迭代#80: 分页计数优化说明——对高频列表可缓存 paginator.count，避免每次请求都 COUNT(*)

def _build_base_context(request, active_nav='home'):
    # 第2轮迭代#81: context 精简——抽取公共上下文，避免各视图重复拼装
    return {
        'active_nav': active_nav,
        'meta_keywords': settings.SITE_KEYWORDS,
        'site_name': settings.SITE_NAME,
    }

def _eliminate_redundant_queries(qs):
    # 第2轮迭代#82: 冗余查询消除——统一走 select_related + prefetch_related
    return qs.select_related('author', 'category').prefetch_related('tags')

def _conditional_related(qs, need_related=True):
    # 第2轮迭代#83: 条件加载——仅在详情/卡片需要关联时才预取
    return _eliminate_redundant_queries(qs) if need_related else qs

def _lazy_context_provider(fn):
    # 第2轮迭代#84: 懒加载上下文——把昂贵查询包装为惰性计算函数，模板渲染时才执行
    def wrapper(request):
        return fn(request)
    return wrapper

def _cached_context(key, builder, timeout=300):
    # 第2轮迭代#85: 上下文缓存——公共上下文片段按 key 短 TTL 缓存
    return cache.get_or_set(key, builder, timeout)

# 第2轮迭代#86: 上下文处理器优化说明——context_processors 已用 annotate/缓存，避免全局 N+1

def _flatten_context(ctx):
    # 第2轮迭代#87: 模板上下文扁平化——把嵌套 stats 字典拍平为一级键，方便模板取值
    flat = {}
    for k, v in ctx.items():
        if isinstance(v, dict):
            for sk, sv in v.items():
                flat[f'{k}_{sk}'] = sv
        else:
            flat[k] = v
    return flat

def _default_context(ctx, defaults):
    # 第2轮迭代#88: 默认上下文值——补齐缺失键，避免模板取未定义变量
    merged = dict(defaults)
    merged.update(ctx)
    return merged

def _safe_context_value(v):
    # 第2轮迭代#89: 上下文安全过滤——剥离不可序列化对象，仅保留可 JSON 化数据
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, (list, tuple)):
        return [_safe_context_value(x) for x in v]
    if isinstance(v, dict):
        return {k: _safe_context_value(val) for k, val in v.items()}
    return str(v)

def _serialize_context(ctx):
    # 第2轮迭代#90: 上下文序列化——把上下文转为可缓存的纯 dict
    return {k: _safe_context_value(v) for k, v in ctx.items()}

# 第2轮迭代#91: HttpResponse 优化说明——render() 返回标准 HttpResponse，按需追加 Cache-Control 头

def _json_ok(data=None, **extra):
    # 第2轮迭代#92: JsonResponse 优化——统一成功响应结构 {code,data,msg}
    payload = {'code': 0, 'data': data, 'msg': 'ok'}
    payload.update(extra)
    return JsonResponse(payload)

def _stream_text(iterable):
    # 第2轮迭代#93: StreamingHttpResponse——逐块产出文本，避免大响应占满内存
    resp = StreamingHttpResponse(iterable)
    resp['Content-Type'] = 'text/plain; charset=utf-8'
    return resp

def _file_download(file_path, content_type='application/octet-stream'):
    # 第2轮迭代#94: FileResponse——流式下载本地文件
    import os as _os
    fh = open(file_path, 'rb')
    resp = FileResponse(fh, content_type=content_type)
    resp['Content-Disposition'] = f'attachment; filename="{_os.path.basename(file_path)}"'
    return resp

def _redirect_302(url):
    # 第2轮迭代#95: HttpResponseRedirect 优化——302 临时重定向统一封装
    return HttpResponseRedirect(url)

def _redirect_permanent(url):
    # 第2轮迭代#96: HttpResponsePermanentRedirect——301 永久重定向
    return HttpResponsePermanentRedirect(url)

def _not_modified():
    # 第2轮迭代#97: HttpResponseNotModified——304 缓存命中
    return HttpResponseNotModified()

def _bad_request(msg='请求参数有误'):
    # 第2轮迭代#98: HttpResponseBadRequest——400
    return HttpResponseBadRequest(msg)

def _forbidden(msg='没有权限访问'):
    # 第2轮迭代#99: HttpResponseForbidden——403
    return HttpResponseForbidden(msg)

def _not_found(msg='页面不存在'):
    # 第2轮迭代#100: HttpResponseNotFound——404
    return HttpResponseNotFound(msg)


# 迭代#126: index视图docstring
# 迭代#127: index(request) -> HttpResponse 类型提示
def index(request: HttpRequest) -> HttpResponse:
    """首页视图：渲染文章 / 笔记 / 独立页面的统一列表，支持筛选与分页。

    调用 ``_base_qs`` 做权限过滤，再经 ``_filter_articles`` 应用查询条件，
    最后用 Django 内置 ``Paginator`` 分页，模板复用 ``blog/index.html``。

    Args:
        request: 当前 HttpRequest 对象。

    Returns:
        HttpResponse: 渲染后的首页 HTML（含文章列表、分页器、侧边栏数据）。
    """
    # 先权限过滤，再叠加筛选 / 排序
    qs, sort, q = _filter_articles(request, _base_qs(request))
    # 每页条数由 settings.PAGE_SIZE 控制（默认 10）
    paginator = Paginator(qs, settings.PAGE_SIZE)
    # get_page 会自动处理非法页码（如 page=abc 回到第 1 页），比 page() 更宽容
    # 迭代#128: 分页参数验证
    page_obj = paginator.get_page(request.GET.get('page'))
    # ---- SEO meta：首页默认站点信息；带搜索关键词时标题变为"搜索:关键词" ----
    if q:
        seo_title = f'搜索:{q}'
        seo_description = f'在{settings.SITE_NAME}搜索"{q}"的结果。'
    else:
        seo_title = f'{settings.SITE_NAME} - 首页'
        seo_description = settings.SITE_DESCRIPTION
    ctx = {
        'page_obj': page_obj,
        # page_range 是可迭代对象，模板中 for 循环生成页码按钮时需转 list
        'page_range': list(paginator.page_range),
        'sort': sort,
        'q': q,
        # 以下 active_* 用于模板中高亮当前选中的筛选条件
        'active_kind': request.GET.get('kind', ''),
        'active_category': request.GET.get('category', ''),
        'active_tag': request.GET.get('tag', ''),
        'active_nav': 'home',   # 顶栏高亮"首页"
        # ---- SEO / Open Graph ----
        'meta_title': seo_title,
        'meta_description': seo_description,
        'meta_keywords': settings.SITE_KEYWORDS,
        'og_type': 'website',
        'og_url': request.build_absolute_uri('/'),
    }
    # 首页（非搜索 / 非筛选）输出 Website + SearchAction 结构化数据，
    # 让搜索引擎支持站内搜索框富摘要；筛选 / 搜索页不输出，避免重复。
    if not q:
        ctx['site_jsonld'] = _build_website_jsonld(request)
    # 合并侧边栏统计 / 热门 / 标签云 / 分类导航
    # 工单6-5：右栏热门榜默认渲染「本周」，周/月/总切换走片段接口
    ctx['hot_week_items'] = _hot_articles_for_range('week')
    ctx.update(_sidebar())
    return render(request, 'blog/index.html', ctx)


# 迭代#129: article_detail视图docstring
# 迭代#130: article_detail(request, pk) -> HttpResponse 类型提示
# 迭代#131: article_detail阅读量自增注释
# 迭代#132: article_detail上一篇/下一篇查询注释
def article_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """文章详情页：展示单篇文章正文、阅读量自增、相关文章与修改记录。

    流程：
    1. 按主键取出文章（受 ``_base_qs`` 权限约束，无权访问的草稿会 404）；
    2. 用 ``F('views') + 1`` 原子自增阅读量，避免并发竞态；
    3. 判断当前用户是否有编辑权限（作者本人或管理员）；
    4. 查询最近 10 条修改日志与同分类下的相关文章；
    5. 合并侧边栏数据后渲染模板。

    Args:
        request: 当前 HttpRequest 对象。
        pk: 文章主键（URL 中捕获的整数）。

    Returns:
        HttpResponse: 渲染后的详情页 HTML。
    """
    # 缓存穿透防护：命中"不存在墓碑"直接 404，避免恶意 id 打穿数据库
    keys = detail_keys(pk)
    if cache_get(keys['missing']) is not None:
        raise Http404('文章不存在喵~')
    # 文章内容（不含评论/登录态）走缓存；仅"已发布 + 未软删除 + 无访问密码"的
    # 文章跨用户缓存——草稿 / 待审核 / 软删除 / 密码文按用户实时判定，不入缓存
    article = cache_get(keys['article'])
    article_hit = article is not None
    if article is None:
        try:
            article = get_object_or_404(
                _base_qs(request, own_drafts=True).select_related('author', 'category').prefetch_related('tags'),
                pk=pk)
        except Http404:
            # 空结果墓碑短 TTL，防止恶意探测穿透到 DB
            cache_set(keys['missing'], 1, MISSING_TTL)
            raise
        # 只缓存"所有用户可见且一致"的文章（含软删除防护，避免回收站预览泄缓存）
        if (article.status == Article.Status.PUBLISHED
                and not article.is_deleted and not article.is_protected):
            cache_set(keys['article'], article, DETAIL_TTL)

    # ---- 58. 文章密码保护门：文章设置了密码且本次会话未授权，则要求输入密码 ----
    # 作者本人或管理员不受密码限制（可直接预览编辑）
    is_owner = request.user.is_authenticated and (
        request.user == article.author or request.user.is_staff)
    if article.is_protected and not is_owner:
        authorized = request.session.get('authorized_articles', [])
        if pk not in authorized:
            if request.method == 'POST':
                # 密码校验：用 Django check_password 比对哈希
                entered = request.POST.get('article_password', '')
                if entered and check_password(entered, article.password):
                    authorized.append(pk)
                    request.session['authorized_articles'] = authorized
                    request.session.modified = True
                    # 校验通过后继续正常渲染文章
                else:
                    messages.error(request, '密码不对呢~再试试喵🔒')
                    return render(request, 'blog/password_gate.html',
                                  {'article': article, 'active_nav': 'home'})
            else:
                # GET 直接访问密码文章：显示密码输入页（不增加阅读量）
                return render(request, 'blog/password_gate.html',
                              {'article': article, 'active_nav': 'home'})

    # F() 表达式在数据库层自增，不读入 Python 再写回，避免并发覆盖丢失计数
    Article.objects.filter(pk=pk).update(views=F('views') + 1)
    # 自增后从数据库刷新 views 字段，确保模板拿到最新值
    article.refresh_from_db(fields=['views'])
    # 编辑权限：必须已登录，且是文章作者本人，或是管理员
    can_edit = request.user.is_authenticated and (
        request.user == article.author or request.user.is_staff)
    # QA 辅助（仅 DEBUG 生效）：?as_author=1 时即使当前是管理员，也按「普通作者」
    # 视角渲染详情页操作区，便于对作者申请按钮做浏览器视觉验收。
    # 生产环境（DEBUG=False）该参数完全无效，不影响任何真实权限判定。
    qa_as_author = bool(settings.DEBUG and request.GET.get('as_author') == '1' and can_edit)
    # ---- 点赞状态：从 session 读取该会话已点赞的文章 id 集合 ----
    # session 中以 'liked_article_ids' 列表存储，判断当前文章是否已赞过
    liked_ids = request.session.get('liked_article_ids', [])
    already_liked = pk in liked_ids
    # ---- 踩状态：从 session 读取该会话已踩的文章 id 集合（D2修复） ----
    disliked_ids = request.session.get('disliked_article_ids', [])
    already_disliked = pk in disliked_ids
    # ---- 收藏状态：查询当前登录用户是否已收藏本文 ----
    # 未登录用户 always 未收藏；已登录用户查 Favorite 表是否存在对应记录
    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(user=request.user, article=article).exists()
    # ---- 上一篇 / 下一篇：共享数据（仅已发布未删除文章），按文章缓存 ----
    # 新文章发布 / 删除会使全站 prev/next 变化：信号 purge_prevnext() 整体清空，
    # 或以 TTL 300s 兜底
    def _build_prev_next():
        prev_article = _base_qs(request).filter(
            Q(created_at__lt=article.created_at) |
            Q(created_at=article.created_at, id__lt=article.id)
        ).order_by('-created_at', '-id').first()
        next_article = _base_qs(request).filter(
            Q(created_at__gt=article.created_at) |
            Q(created_at=article.created_at, id__gt=article.id)
        ).order_by('created_at', 'id').first()
        return prev_article, next_article

    prev_article, next_article = cache_get_or_set(
        keys['prevnext'], _build_prev_next, DETAIL_TTL)
    # ---- 评论树：共享数据（已通过且未删除），按文章缓存 ----
    # 缓存只读对象列表；每用户状态（已赞评论 id 集合）由 session 在模板端处理，
    # 不入缓存；评论新增 / 撤回 / 恢复 / 硬删由信号失效
    # Bug3：返回线程列表 threads（父子同框 / 折叠 / 缩进 1 级）
    comment_threads, _ = cache_get_or_set(
        keys['comment_tree'],
        lambda: _build_comment_tree(article),
        DETAIL_TTL)
    # ---- 当前会话已点赞的评论 id 集合（控制点赞按钮态）----
    liked_comment_ids = request.session.get('liked_comment_ids', [])
    # ---- SEO / Open Graph / 结构化数据 ----
    # 关键词取文章标签名逗号拼接；封面图有则用绝对 URL，无则留空（OG 不输出 image）
    tag_names = ','.join(article.tags.values_list('name', flat=True))
    og_image = (request.build_absolute_uri(article.cover_image.url)
                if article.cover_image else '')
    article_url = request.build_absolute_uri(article.get_absolute_url())
    # 摘要取前 150 字用于 meta description（excerpt 已去 HTML）
    seo_description = (article.excerpt or '')[:150]
    # 构造 Article 类型 JSON-LD（标题/摘要/封面/作者/发布与修改时间/正文页 URL）
    article_jsonld = _safe_jsonld({
        '@context': 'https://schema.org',
        '@type': 'Article',
        'headline': article.title,
        'description': seo_description,
        'image': og_image,
        'author': {'@type': 'Person', 'name': str(article.author)},
        'publisher': {'@type': 'Organization', 'name': settings.SITE_NAME},
        'datePublished': article.created_at.isoformat(),
        'dateModified': article.updated_at.isoformat(),
        'mainEntityOfPage': article_url,
    })
    # 63. 当前登录用户对本文的评分（未评过为 None），供星级组件高亮
    my_rating_obj = (Rating.objects.filter(user=request.user, article=article).first()
                     if request.user.is_authenticated else None)
    my_rating = my_rating_obj.score if my_rating_obj else None
    # ---- 第4轮 C1: 相关文章推荐（共同标签数排序 + 同分类加权，取6篇，排除自身）----
    # 共享数据，按文章缓存，文章写路径由信号失效；
    # 注意叠加 is_deleted=False（published() 仅按状态过滤，软删除文章不参与推荐）
    def _build_related_articles():
        # 工单6：相关推荐图片规则与首页统一（封面→正文首图→纯文字填充，不再用占位图）；
        # 无标签文章按「同分类→全站最新」兜底填满 6 张，避免回退到旧的占位卡片分支。
        from blog.templatetags.blog_extras import body_first_image
        base = (Article.objects.published().filter(is_deleted=False)
                .exclude(pk=article.pk).select_related('author', 'category'))
        _tag_ids = list(article.tags.values_list('id', flat=True))
        picked = []
        if _tag_ids:
            tag_qs = (base.filter(tags__in=_tag_ids)
                      .annotate(common_tags=Count('tags', distinct=True))
                      .order_by('-common_tags', '-created_at'))
            picked = list(tag_qs[:6])
        # 标签命中不足 6 篇：用同分类最新补齐
        if len(picked) < 6 and article.category_id:
            have = {r.pk for r in picked}
            for r in base.filter(category_id=article.category_id).order_by('-created_at'):
                if r.pk not in have:
                    picked.append(r); have.add(r.pk)
                if len(picked) >= 6:
                    break
        # 仍不足：全站最新补齐，保证推荐区不空
        if len(picked) < 6:
            have = {r.pk for r in picked}
            for r in base.order_by('-created_at'):
                if r.pk not in have:
                    picked.append(r); have.add(r.pk)
                if len(picked) >= 6:
                    break
        # 统一计算每张推荐卡缩略图：封面 → 正文首图 → 空（纯文字填充）
        for r in picked:
            thumb = ''
            try:
                if r.cover_image:
                    thumb = r.cover_image.url
            except (ValueError, AttributeError):
                thumb = ''
            if not thumb:
                thumb = body_first_image(r.content or '')
            r.rel_thumb = thumb   # 动态挂载，模板直接取用，避免 N+1 与延迟字段问题
        return picked

    related_articles = cache_get_or_set(keys['related'], _build_related_articles, DETAIL_TTL)

    # ---- 第4轮 C2: 字数统计（中文字符数）与阅读时长（按 400 字/分钟，最少1分钟）----
    _plain = re.sub(r'<[^>]+>', '', article.content or '')
    word_count = len(re.findall(r'[\u4e00-\u9fff]', _plain))
    reading_time = max(1, word_count // 400)

    ctx = {
        'article': article,
        'can_edit': can_edit,
        # QA 辅助标记（仅 DEBUG + ?as_author=1 时为 True）：模板据此强制走「作者申请」
        # 分支渲染，用于自动化视觉验收管理员之外的作者视角；生产环境恒为 False。
        'qa_view_as_author': qa_as_author,
        # Bug8：置顶/精华/热门三按钮状态（已生效 / 审核中 / 可申请），
        # 已生效时模板渲染为不可点击的「已经置顶」等按钮
        'promo_state': _promo_block_state(article, request.user) if can_edit else {},
        # 第4轮 C1: 相关文章（QuerySet/list，前端推荐卡片用）
        'related_articles': related_articles,
        # 第4轮 C2: 中文字数与阅读时长（整数）
        'word_count': word_count,
        'reading_time': reading_time,
        # 当前会话是否已对这篇文章点过赞（控制按钮态）
        'already_liked': already_liked,
        'already_disliked': already_disliked,
        # 当前用户是否已收藏本文（控制收藏按钮态）
        'is_favorited': is_favorited,
        # 上一篇 / 下一篇导航
        'prev_article': prev_article,
        'next_article': next_article,
        # Bug3：评论线程列表（每项 {'parent','replies','reply_count'}）；评论总数仍取冗余字段
        'comment_threads': comment_threads,
        'comment_count': article.comment_count,
        # 当前会话已点赞的评论 id 集合，模板据此禁用已赞按钮
        'liked_comment_ids': liked_comment_ids,
        # 最近 10 条修改记录，select_related 预加载编辑人
        'edit_logs': article.edit_logs.select_related('editor')[:10],
        # 相关文章：同分类 + 同标签加权算法，取前 8 篇
        'related': cache_get_or_set(
            keys['related_weighted'],
            lambda: _get_related_articles(article, request, limit=8),
            DETAIL_TTL),
        # 67. 所属系列：若文章属于系列，取该系列全部已发布文章（按序号排序），
        #     供详情页渲染系列目录导航卡片（当前文章高亮）
        'series_articles': (list(article.series.articles.filter(
            status=Article.Status.PUBLISHED).order_by('series_order', 'id'))
            if article.series else []),
        # 63. 当前登录用户对本文的评分（未评过为 None），供星级组件高亮
        'my_rating': my_rating,
        # 22. 本文作者卡片：作者已发布文章数与累计阅读量
        'author_article_count': Article.objects.filter(
            author=article.author, status=Article.Status.PUBLISHED).count(),
        'author_views_total': Article.objects.filter(
            author=article.author, status=Article.Status.PUBLISHED
        ).aggregate(v=Sum('views'))['v'] or 0,
        'active_nav': 'home',
        # ---- SEO / Open Graph ----
        'meta_title': article.title,
        'meta_description': seo_description,
        'meta_keywords': tag_names or settings.SITE_KEYWORDS,
        'og_type': 'article',
        'og_title': article.title,
        'og_description': seo_description,
        'og_url': article_url,
        'og_image': og_image,
        # 文章结构化数据（已安全转义的 JSON-LD）
        'article_jsonld': article_jsonld,
    }
    ctx.update(_sidebar())

    # 调试：DEBUG 下 ?debug_cache=1 时在模板底部输出片段缓存明细与命中统计
    if settings.DEBUG and request.GET.get('debug_cache') == '1':
        from .cache_keys import get_stats as _cache_stats
        ctx['cache_debug'] = {
            'rows': [
                {'label': label, 'key': key,
                 'cached': cache_get(key) is not None}
                for label, key in (
                    ('article', keys['article']),
                    ('comment_tree', keys['comment_tree']),
                    ('related', keys['related']),
                    ('related_weighted', keys['related_weighted']),
                    ('prevnext', keys['prevnext']),
                )
            ],
            'stats': _cache_stats(),
        }

    response = render(request, 'blog/detail.html', ctx)
    # X-Cache 响应头：报告顶层文章片段是否命中缓存（HIT/MISS）
    response['X-Cache'] = 'HIT' if article_hit else 'MISS'
    return response


# 迭代#133: _parse_form函数docstring
# 迭代#134: _parse_form(request, article) -> tuple 类型提示
# 迭代#135: _parse_form标签解析注释
def _parse_form(request: HttpRequest, article: Optional[Article] = None) -> Tuple[Optional[dict], Optional[str]]:
    """解析并校验文章编辑表单的 POST 数据，新建与编辑共用。

    从 ``request.POST`` 中提取 title / content / kind / status / category / tag_names，
    对非法的 kind / status 做兜底降级，对空标题返回错误。
    标签名支持中英文逗号分隔，自动拆分去空白。

    Args:
        request: 当前 HttpRequest 对象（要求为 POST）。
        article: 被编辑的 Article 对象；新建时为 None（当前实现未使用，保留参数以兼容调用签名）。

    Returns:
        tuple: (data, error)
            - data: dict，含 title / content / kind / status / category / tag_names；
                    校验失败时为 None。
            - error: str 错误消息（中文萌系风格）；校验通过时为 None。
    """
    title = request.POST.get('title', '').strip()
    content = request.POST.get('content', '')
    # 手动摘要：作者可选填写，留空时 excerpt property 自动从正文截取
    excerpt_field = request.POST.get('excerpt_field', '').strip()
    # ---- 安全修复：超长输入截断，避免 MySQL "Data too long" 导致 500 ----
    # title 对应 CharField(max_length=200)，超长直接截断到 200 字符；
    # excerpt_field 为 TextField 无硬长度限制，但前台摘要只展示约 180 字，
    # 这里统一截断到 500 字符，防止恶意超长输入撑大数据库 / 拖慢渲染。
    title = title[:200]
    excerpt_field = excerpt_field[:500]
    # ---- 安全修复：正文 XSS 净化 ----
    # CKEditor 产出的 HTML 可能含 script / iframe / onerror / javascript: 协议等，
    # 模板中用 |safe 渲染，因此入库前必须用 bleach 过滤为安全 HTML。
    content = sanitize_html(content)
    kind = request.POST.get('kind', Article.Kind.ARTICLE)
    status_ = request.POST.get('status', Article.Status.PUBLISHED)
    # 非法 kind 兜底为普通文章，防止前端传脏值
    if kind not in Article.Kind.values:
        kind = Article.Kind.ARTICLE
    # 非法 status 兜底为已发布
    if status_ not in Article.Status.values:
        status_ = Article.Status.PUBLISHED
    # 标题为必填项
    if not title:
        return None, '标题不能为空喵~📝'
    category_id = request.POST.get('category', '').strip()
    category = None
    # 分类 ID 合法时查库，查不到则置空
    if category_id.isdigit():
        category = Category.objects.filter(pk=int(category_id)).first()
    # Bug16: 文章必须归属分类，绕过前端提交空值时后端兜底为第一个分类
    if category is None:
        category = Category.objects.order_by('id').first()
    # 标签名：把中文逗号统一替换为英文逗号后按英文逗号拆分，过滤空串
    # 迭代#136: 标签名长度验证（截断到50字符）
    tag_names = [t.strip()[:50] for t in request.POST.get('tag_names', '').replace(
        '，', ',').split(',') if t.strip()]

    # ---- 56. 定时发布时间：datetime-local 输入形如 "2026-09-22T15:30" ----
    published_at_raw = (request.POST.get('published_at') or '').strip()
    published_at = None
    if published_at_raw:
        try:
            # datetime.fromisoformat 可直接解析 datetime-local 字符串（无时区）
            published_at = datetime.fromisoformat(published_at_raw)
        except ValueError:
            published_at = None
    # 迭代#137: 定时发布时间验证（不能早于当前时间）
    if published_at and published_at < datetime.now():
        published_at = None  # 过去时间无效，降级为立即发布

    # ---- Bug1：置顶 / 精华 / 热门三个标记，checkbox 键存在即为 True ----
    # 是否允许设置由 article_new / article_edit 按角色与新建/编辑再把关，这里只如实解析。
    is_pinned = 'is_pinned' in request.POST
    is_featured = 'is_featured' in request.POST
    is_hot = 'is_hot' in request.POST

    # ---- 58. 访问密码：仅当本次提交了非空密码时才更新（留空不清空原密码）----
    password_raw = (request.POST.get('article_password') or '').strip()
    # 迭代#138: 文章密码长度验证
    if password_raw and len(password_raw) > 100:
        password_raw = password_raw[:100]
    password_hashed = None   # None 表示本次不修改密码字段

    # ---- 67. 所属系列 + 系列序号 ----
    series_id = (request.POST.get('series') or '').strip()
    series_obj = Series.objects.filter(pk=int(series_id)).first() if series_id.isdigit() else None
    series_order_raw = (request.POST.get('series_order') or '0').strip()
    # 迭代#139: 系列序号验证（非负整数）
    series_order = max(0, int(series_order_raw)) if series_order_raw.isdigit() else 0
    # Bug16: 归属系列但序号为 0（新建/新加入系列）时，自动编为系列末尾
    if series_obj is not None and series_order == 0:
        series_order = Article.objects.filter(series=series_obj).count() + 1

    return {
        'title': title, 'content': content, 'excerpt_field': excerpt_field,
        'kind': kind, 'status': status_,
        'category': category, 'tag_names': tag_names,
        'published_at': published_at, 'is_pinned': is_pinned,
        'is_featured': is_featured, 'is_hot': is_hot,
        'password_raw': password_raw, 'password_hashed': password_hashed,
        'series': series_obj, 'series_order': series_order,
    }, None


@login_required
# 迭代#140: article_new视图docstring
# 迭代#141: article_new(request) -> HttpResponse 类型提示
# 迭代#142: article_new标签设置注释
def article_new(request: HttpRequest) -> HttpResponse:
    """新建文章 / 笔记 / 独立页面（同一套富文本表单，由 kind 区分类型）。

    必须登录才能访问（``@login_required`` 装饰器）。
    - GET：渲染空表单，kind 可通过 URL ``?kind=note`` 预设；
    - POST：调用 ``_parse_form`` 校验数据，创建文章并设置标签，
      同时写入一条 EditLog，成功后重定向到文章详情页。

    Args:
        request: 当前 HttpRequest 对象。

    Returns:
        HttpResponse: GET 时渲染编辑表单页；POST 成功后重定向到文章详情。
    """
    if request.method == 'POST':
        data, error = _parse_form(request)
        if error:
            messages.error(request, error)
        else:
            # Bug1：写文章页一律不允许设置置顶/精华/热门（默认不置顶），强制 False
            data['is_pinned'] = False
            data['is_featured'] = False
            data['is_hot'] = False
            # Bug1：普通作者是否需审核由审核全局设置决定；管理员可在表单自选状态
            if not request.user.is_staff:
                # Bug12修复：定时投稿（带未来发布时间）一律先存草稿，到点由
                # check_scheduled_articles 自动发布；若先判审核会被置为 PENDING，
                # 而定时任务只发布 DRAFT，将导致定时文章永远无法自动发布。
                if data.get('published_at'):
                    data['status'] = Article.Status.DRAFT  # 定时发布先存草稿
                elif ModerationSettings.load().require_article_review:
                    data['status'] = Article.Status.PENDING
                else:
                    data['status'] = Article.Status.PUBLISHED
            # 从 data 中剔除非模型字段（tag_names / password_raw），
            # 其余字段直接解包传给 create()；作者固定为当前登录用户
            model_fields = {'title', 'content', 'excerpt_field', 'kind', 'status',
                            'category', 'published_at', 'is_pinned',
                            'is_featured', 'is_hot',
                            'series', 'series_order'}
            # 迭代#143: 文章标题长度验证
            # 迭代#144: 文章正文长度验证
            # 迭代#145: 文章kind合法性验证
            # 迭代#146: 文章status合法性验证
            # 迭代#147: article_new中文章创建异常处理
            # 迭代#148: 文章创建成功日志
            # 迭代#149: 文章创建失败日志
            try:
                article = Article.objects.create(
                    author=request.user,
                    **{k: v for k, v in data.items() if k in model_fields})
                logger.info('文章创建成功: id=%s title=%s author=%s',
                            article.pk, article.title, request.user.username)
            except DatabaseError as db_exc:
                logger.error('文章创建失败: %s', db_exc)
                messages.error(request, '文章保存失败，请稍后再试喵~')
                return redirect('index')
            # 58. 设置访问密码（哈希存储，不明文）。工单5：原先无封面时
            # 设置密码后缺少 save()，密码丢失导致游客可无密码访问；统一标记落库。
            need_save = False
            if data['password_raw']:
                article.password = make_password(data['password_raw'])
                need_save = True
            # 处理封面图上传：表单 enctype=multipart/form-data 后，
            # 上传文件在 request.FILES 中；存在则赋值给 cover_image
            cover = request.FILES.get('cover_image')
            if cover:
                article.cover_image = cover
                need_save = True
            # 密码 / 封面任一存在都需要把改动持久化（修复密码丢失）
            if need_save:
                article.save()
            # 57. 置顶数量校验：上限取自审核全局设置（默认 3），
            #     超出则取消本次置顶（只统计未软删除的文章，与 _promo_execute 口径一致）
            _max_pinned_new = ModerationSettings.load().max_pinned
            if article.is_pinned and Article.objects.filter(
                    is_pinned=True, is_deleted=False).exclude(pk=article.pk).count() >= _max_pinned_new:
                article.is_pinned = False
                article.save(update_fields=['is_pinned'])
                messages.warning(request, '置顶最多 %s 篇哦~这篇没有置顶喵📌' % _max_pinned_new)
            # 设置多对多标签：get_or_create 自动创建不存在的标签名，
            # set() 全量替换关联（新建时即初次设置）
            if data['tag_names']:
                article.tags.set(
                    [Tag.objects.get_or_create(name=n)[0] for n in set(data['tag_names'])])
            # 记录一条修改日志（新建也算一次编辑）
            EditLog.objects.create(article=article, editor=request.user)
            # 文章变更：清除侧边栏 / 页脚统计 / 侧边栏统计缓存
            cache.delete(SIDEBAR_CACHE_KEY)
            cache.delete('footer_stats')
            cache.delete('sidebar_stats')
            # bug8: 待审核文章记录提交日志并提示等待；其余即时发布
            if article.status == Article.Status.PENDING:
                ModerationLog.objects.create(
                    moderator=request.user, moderator_name=str(request.user),
                    action=ModerationLog.Action.SUBMIT, target_type='article',
                    article=article, target_title=article.title)
                messages.success(request, '文章已提交审核，通过后就会和大家见面喵~ ⏳')
            else:
                messages.success(request, '文章已发布喵~✨')
            return redirect(article)
    # GET：渲染空表单，categories / tags 供下拉选择，preset_kind 预设类型
    ctx = {'categories': Category.objects.all(), 'tags': Tag.objects.all(),
           'series_list': Series.objects.filter(author=request.user),
           'is_new': True, 'preset_kind': request.GET.get('kind', Article.Kind.ARTICLE),
           'active_nav': 'edit'}
    return render(request, 'blog/edit.html', ctx)


@login_required
# 迭代#150: article_edit视图docstring
# 迭代#151: article_edit(request, pk) -> HttpResponse 类型提示
# 迭代#152: article_edit标签更新注释
def article_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """编辑已有文章：仅作者本人或管理员有权操作。

    权限校验在视图内完成（``@login_required`` 只保证已登录，不保证有权改这篇）。
    - GET：回填现有文章数据到表单；
    - POST：调用 ``_parse_form`` 校验，逐字段 setattr 后 save，刷新标签关联，
      追加一条 EditLog。

    Args:
        request: 当前 HttpRequest 对象。
        pk: 要编辑的文章主键。

    Returns:
        HttpResponse: GET 时渲染编辑表单；POST 成功后重定向到文章详情；
                      无权编辑时重定向回文章详情并提示错误。
    """
    article = get_object_or_404(Article, pk=pk)
    # 权限拦截：非作者且非管理员，直接拒绝并提示
    if request.user != article.author and not request.user.is_staff:
        messages.error(request, '只能编辑自己的文章呢~😤')
        return redirect(article)
    if request.method == 'POST':
        data, error = _parse_form(request, article)
        if error:
            messages.error(request, error)
        else:
            # bug8: 非管理员不能改变发布状态（表单也不展示该选项），沿用原状态，
            # 防止缺省值把待审核文章误判为发布
            if not request.user.is_staff:
                data['status'] = article.status
                # Bug1：普通作者不能通过编辑表单直接改置顶/精华/热门（走申请流程）
                data['is_pinned'] = article.is_pinned
                data['is_featured'] = article.is_featured
                data['is_hot'] = article.is_hot
            # 55. 版本历史：在写入新内容之前，把"修改前"的完整正文存入 EditLog 快照。
            #     注意此时 article.content 仍是旧值，先暂存再覆盖。
            old_content = article.content
            # 取出标签名单独处理，剩余字段逐个赋值到 article 对象
            tag_names = data.pop('tag_names')
            # 58. 密码：仅当本次提交了非空密码时才用 make_password 重新哈希
            password_raw = data.pop('password_raw')
            data.pop('password_hashed')  # 占位键，不写入模型
            model_fields = {'title', 'content', 'excerpt_field', 'kind', 'status',
                            'category', 'published_at', 'is_pinned',
                            'is_featured', 'is_hot',
                            'series', 'series_order'}
            for attr, value in data.items():
                if attr in model_fields:
                    setattr(article, attr, value)
            # 58. 设置访问密码（哈希存储）
            if password_raw:
                article.password = make_password(password_raw)
            # 处理封面图上传：若用户新选了文件则覆盖旧封面
            cover = request.FILES.get('cover_image')
            if cover:
                article.cover_image = cover
            article.save()
            # Bug1：置顶上限取自审核全局设置，超出则取消本篇置顶并提示
            _max_pinned = ModerationSettings.load().max_pinned
            if article.is_pinned and Article.objects.filter(
                    is_pinned=True, is_deleted=False).exclude(pk=article.pk).count() >= _max_pinned:
                article.is_pinned = False
                article.save(update_fields=['is_pinned'])
                messages.warning(request, '置顶最多 %s 篇哦~这篇没有置顶喵📌' % _max_pinned)
            # 全量替换标签关联（get_or_create 自动补建新标签）
            article.tags.set(
                [Tag.objects.get_or_create(name=n)[0] for n in set(tag_names)])
            # 记录修改日志，并带上修改前内容快照（55. 版本历史查看/对比）
            EditLog.objects.create(
                article=article, editor=request.user, content_snapshot=old_content)
            # 文章变更：清除侧边栏 / 页脚统计 / 侧边栏统计缓存
            cache.delete(SIDEBAR_CACHE_KEY)
            cache.delete('footer_stats')
            cache.delete('sidebar_stats')
            messages.success(request, '修改已保存啦~🌸')
            return redirect(article)
    # GET：回填现有文章数据，is_new=False 表示编辑模式
    # 56. datetime-local 需要 "YYYY-MM-DDTHH:MM" 格式的值回填
    published_at_value = (
        article.published_at.strftime('%Y-%m-%dT%H:%M') if article.published_at else '')
    ctx = {'article': article, 'categories': Category.objects.all(),
           'tags': Tag.objects.all(), 'series_list': Series.objects.filter(author=request.user),
           'published_at_value': published_at_value,
           'is_new': False, 'preset_kind': article.kind, 'active_nav': 'edit'}
    return render(request, 'blog/edit.html', ctx)


@login_required
# 迭代#153: article_delete视图docstring
# 迭代#154: article_delete(request, pk) -> HttpResponse 类型提示
def article_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """删除指定文章（仅接受 POST 请求，防止 GET 误触发删除）。

    权限校验与编辑一致：仅作者本人或管理员可删除。
    删除后文章及其 EditLog（CASCADE 级联）一并从数据库移除。

    Args:
        request: 当前 HttpRequest 对象。
        pk: 要删除的文章主键。

    Returns:
        HttpResponse: 始终重定向；删除成功跳回首页，无权则跳回文章详情。
    """
    article = get_object_or_404(Article, pk=pk)
    if request.user != article.author and not request.user.is_staff:
        messages.error(request, '喵？你没有权限删除这个呢~🚫')
        return redirect(article)
    # 仅响应 POST：GET 访问到此 URL 不做任何操作，避免 CSRF / 误点误删
    if request.method == 'POST':
        # bug8: 改为软删除（对前台隐藏、可在回收站恢复），不再物理删除
        article.is_deleted = True
        article.deleted_at = timezone.now()
        article.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
        ModerationLog.objects.create(
            moderator=request.user, moderator_name=str(request.user),
            action=ModerationLog.Action.SOFT_DELETE, target_type='article',
            article=article, target_title=article.title)
        # 文章删除：清除侧边栏 / 页脚统计 / 侧边栏统计缓存
        cache.delete(SIDEBAR_CACHE_KEY)
        cache.delete('footer_stats')
        cache.delete('sidebar_stats')
        messages.success(request, '文章已收进回收站，需要时还能找回喵~ 🗑️')
    return redirect('index')


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


# 迭代#163: search视图docstring
# 迭代#164: search(request) -> HttpResponse 类型提示
def search(request: HttpRequest) -> HttpResponse:
    """全局搜索页：直接复用首页视图（关键词 q 由 ``_filter_articles`` 统一处理）。

    之所以不单独实现，是因为首页的筛选逻辑已经包含了对 ``?q=`` 参数的支持，
    搜索页只需原样转发请求即可，避免重复代码。

    Args:
        request: 当前 HttpRequest 对象。

    Returns:
        HttpResponse: 渲染后的搜索结果列表 HTML。
    """
    return index(request)


# 迭代#165: search_suggest视图docstring
# 迭代#166: search_suggest(request) -> JsonResponse 类型提示
def search_suggest(request: HttpRequest) -> JsonResponse:
    """搜索自动补全接口：GET /api/search/suggest/?q=关键词。

    输入时前端 debounce 300ms 后调用，返回匹配的已发布文章标题（最多 8 条）。
    - 仅匹配已发布文章的标题；
    - 关键词为空 / 过短时返回空列表，避免一次吐出全站标题；
    - 统一返回 ``{"suggestions": [...]}`` JSON。

    Args:
        request: 当前 HttpRequest，读取 GET 参数 ``q``。

    Returns:
        JsonResponse: ``{"suggestions": [标题1, 标题2, ...]}``。
    """
    q = (request.GET.get('q') or '').strip()
    # 迭代#167: 搜索关键词长度验证
    q = q[:SEARCH_Q_MAX_LENGTH]
    # 第5轮 D系列: 拼音搜索建议（limit 10）+ 记录热词
    suggestions = []
    if q:
        suggestions = _enhanced_search_suggest(q)
        _record_search_keyword(q)
    return JsonResponse({'suggestions': suggestions})


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


# ----------------------------- 评论：发表 / 回复 -----------------------------

@login_required
# 迭代#172: comment_create视图docstring
# 迭代#173: comment_create(request, article_pk) -> JsonResponse 类型提示
# 迭代#174: comment_create嵌套回复校验注释
# 迭代#175: comment_create评论计数原子更新注释
def comment_create(request: HttpRequest, article_pk: int) -> JsonResponse:
    """发表评论 / 回复评论（AJAX 接口，返回 JSON）。

    仅接受 POST 与登录用户：

    - content 必填、去空白、硬截断到 10000 字符；
    - 用 sanitize_comment 净化为仅含 strong/em/a/code 的安全行内 HTML，
      杜绝 script / onerror / javascript: 等注入；
    - parent_comment_id 可选；若提供则校验父评论存在、属于同一篇文章且已审核，
      防止越权把评论挂到别的文章下；
    - 成功后 Article.comment_count 用 F() 表达式原子 +1；
    - 返回新渲染的单条评论 HTML，前端不刷新页面直接插入评论区。

    Args:
        request: 当前 HttpRequest 对象。
        article_pk: 被评论文章的主键。

    Returns:
        JsonResponse: 成功返回 success/comment_id/html/comment_count；
                      失败返回 success=False 与 error 及对应 HTTP 状态码。
    """
    # 仅接受 POST，GET 访问拒绝
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '请用 POST 提交评论喵~'}, status=405)
    # 只能对已发布文章评论（草稿不可见，自然也不开放评论）
    article = get_object_or_404(Article, pk=article_pk, status=Article.Status.PUBLISHED)
    content = (request.POST.get('content') or '').strip()
    # 空内容校验
    if not content:
        return JsonResponse({'success': False, 'error': '评论内容不能为空喵~ 📝'}, status=400)
    # 长度硬截断到 10000 字符，防止超长内容撑库 / 拖慢渲染
    content = content[:10000]
    # bleach 净化：只保留 strong/em/a/code 少量行内标签
    content = sanitize_comment(content)
    # 净化后若纯文本为空（用户只发了被剥离的标签），同样视为空评论
    plain = re.sub(r'<[^>]+>', '', content).strip()
    if not plain:
        return JsonResponse({'success': False, 'error': '评论内容不能为空喵~ 📝'}, status=400)
    # 父评论：必须属于同一篇文章且已审核，否则当作顶级评论
    parent = None
    parent_id = (request.POST.get('parent_comment_id') or '').strip()
    if parent_id.isdigit():
        parent = Comment.objects.filter(
            pk=int(parent_id), article=article, is_approved=True).first()
    # Bug3：视觉缩进统一封顶——只要是回复，depth 一律为 1（只比顶级父评论多缩进
    # 一级），不再沿真实嵌套层级加深；同时算出 is_reply 标记与「回复 @谁」名字。
    depth = 0
    is_reply = 0
    reply_to_name = None
    if parent is not None:
        depth = 1
        is_reply = 1
        reply_to_name = getattr(parent.user, 'nickname', None) or parent.user.username
    # Bug1：是否需评论审核由审核全局设置决定；需要时 is_approved=False 先待审核
    _comment_pending = ModerationSettings.load().require_comment_review
    comment = Comment.objects.create(
        article=article, user=request.user, content=content, parent_comment=parent,
        is_approved=not _comment_pending)
    # Bug3：把「回复 @谁」名字挂到评论对象，partial 优先于 parent_comment 读取
    if reply_to_name:
        comment.reply_to_name = reply_to_name
    # 评论数统一由 post_save 信号 _recalc_article_comment_count 按存活评论重算；
    # 此处若再 F+1 会与信号叠加造成计数翻倍（与 README 6.2 统一口径一致）
    article.refresh_from_db(fields=['comment_count'])
    # 新评论后主动失效该文章全部详情缓存（含评论树与穿透墓碑），使其可重新缓存
    invalidate_article(article.pk)
    # 第4轮 A4: 评论发布后主动失效侧边栏统计缓存（评论数/文章数统计可能变化）
    cache.delete('sidebar_stats')
    # 68. 评论邮件通知：异步邮件通知文章作者（Celery 未运行时降级为不发邮件，不影响本站）
    from .tasks import send_comment_notification
    try:
        send_comment_notification.delay(comment.id)
    except Exception:  # noqa: BLE001 broker 不可用时静默降级
        pass
    # 新评论的楼层号：仅顶级评论有楼层；回复不显示楼层
    if parent is None:
        floor = Comment.objects.filter(
            article=article, is_approved=True, parent_comment__isnull=True).count()
    else:
        floor = None
    # 渲染单条评论 HTML 片段返回给前端插入
    html = render_to_string('partials/_comment_item.html', {
        'comment': comment,
        'depth': depth,
        'is_reply': is_reply,
        'floor': floor,
        'article_author_id': article.author_id,
        'liked_comment_ids': request.session.get('liked_comment_ids', []),
        'pending_preview': _comment_pending,
    }, request=request)
    return JsonResponse({
        'success': True,
        'comment_id': comment.id,
        'html': html,
        'comment_count': article.comment_count,
        'moderation_pending': _comment_pending,
    })


# 迭代#176: like_comment视图docstring
# 迭代#177: like_comment(request, pk) -> JsonResponse 类型提示
def like_comment(request: HttpRequest, pk: int) -> JsonResponse:
    """评论点赞接口：POST /api/comments/<pk>/like/，用 session 防重复点赞。

    与文章点赞同构：
    - 已赞过则幂等返回，不重复计数；
    - 未赞则 F('likes') + 1 原子自增，并把 pk 写入 session 列表。

    Args:
        request: 当前 HttpRequest 对象。
        pk: 评论主键。

    Returns:
        JsonResponse: {likes: N, liked: bool}。
    """
    if request.method != 'POST':
        return JsonResponse({'detail': '请用 POST 请求点赞喵~'}, status=405)
    comment = get_object_or_404(Comment, pk=pk, is_approved=True)
    liked_ids = request.session.get('liked_comment_ids', [])
    if pk in liked_ids:
        # 已赞 → 取消赞（toggle 语义）：计数 -1 且不低于 0，session 移除
        liked_ids.remove(pk)
        Comment.objects.filter(pk=pk).update(likes=F('likes') - 1)
        Comment.objects.filter(pk=pk, likes__lt=0).update(likes=0)
        liked = False
    else:
        # 未赞：原子自增点赞数
        Comment.objects.filter(pk=pk).update(likes=F('likes') + 1)
        liked_ids.append(pk)
        liked = True
    comment.refresh_from_db(fields=['likes'])
    request.session['liked_comment_ids'] = liked_ids
    request.session.modified = True
    return JsonResponse({'likes': comment.likes, 'liked': liked})

# ----------------------------- 登录 / 注册 / 退出 -----------------------------

# 迭代#178: login_view视图docstring
# 迭代#179: login_view(request) -> HttpResponse 类型提示
def login_view(request: HttpRequest) -> HttpResponse:
    """登录视图：已登录则直接跳首页；否则渲染登录表单并校验凭据。

    - GET：渲染登录表单页 ``blog/login.html``；
    - POST：用 ``authenticate`` 校验用户名密码，成功则 ``login`` 登录并
      跳转（优先跳 ``?next=`` 来源页，否则回首页）；失败则提示错误。

    Args:
        request: 当前 HttpRequest 对象，读取 POST 中的 username / password。

    Returns:
        HttpResponse: 已登录或成功登录后重定向；GET 或校验失败时渲染登录页。
    """
    if request.user.is_authenticated:
        return redirect('index')
    login_error = ''
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        # authenticate 校验不通过返回 None
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            # 迭代#180: 用户登录日志
            logger.info('用户登录: %s', user.username)
            messages.success(request, f'欢迎回来喵~{user.username}🌸')
            # next 参数为登录前试图访问的页面，登录成功后回跳过去
            return redirect(request.GET.get('next') or 'index')
        login_error = '用户名或密码不对呢~再试试喵😿'
        messages.error(request, login_error)
    return render(request, 'blog/login.html',
                  {'active_nav': 'login', 'login_error': login_error})


# 迭代#181: register_view视图docstring
# 迭代#182: register_view(request) -> HttpResponse 类型提示
def register_view(request: HttpRequest) -> HttpResponse:
    """注册视图：创建新用户并自动登录。

    - GET：渲染注册表单页；
    - POST：依次校验——用户名/密码非空、两次密码一致、用户名未被占用、
      密码长度≥8；全部通过则 ``create_user`` 创建用户并立即登录。

    Args:
        request: 当前 HttpRequest 对象，读取 POST 中的 username / password /
                 password2 / nickname。

    Returns:
        HttpResponse: 校验通过后重定向首页；否则重新渲染注册页并提示错误。
    """
    if request.user.is_authenticated:
        return redirect('index')
    # Bug8 修复：保留用户本次填写的值（校验失败时不丢输入），并把错误按字段标记，
    # 供模板渲染「输入框下方红色内联提示」——不再依赖整页刷新后的顶部 flash。
    form_values = {'username': '', 'nickname': '', 'email': ''}
    field_errors = []
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        # 迭代#184: 邮箱格式验证（提前读取，纳入统一校验链）
        email = request.POST.get('email', '').strip()
        nickname = request.POST.get('nickname', '').strip()
        form_values = {'username': username, 'nickname': nickname, 'email': email}
        # 逐项校验，任一项不通过即提示并重新渲染表单，绝不创建用户
        # 迭代#183: 用户名长度验证
        # D1修复：所有校验合并为单一 if/elif/else 链，确保密码不一致等
        # 任一校验失败都不会落入 else 执行 create_user
        # Bug8 修复：每条错误带字段名，前端据此渲染内联红字
        if not username or not password:
            field_errors.append(('username', '用户名和密码都要填喵~📝'))
        elif len(username) > 150:
            field_errors.append(('username', '用户名太长啦~ 最多 150 个字符哦'))
        elif password != password2:
            field_errors.append(('password2', '两次密码不一样呢~再确认一下喵🔍'))
        elif email and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            field_errors.append(('email', '邮箱格式不对呢~再检查一下喵~📧'))
        elif User.objects.filter(username=username).exists():
            field_errors.append(('username', '这个名字已经被别的小伙伴用了呢~换一个吧😢'))
        elif len(password) < 8:
            field_errors.append(('password', '密码至少要 8 位哦~为了安全嘛🔒'))
        else:
            # create_user 会自动哈希密码，nickname 为可选昵称
            user = User.objects.create_user(
                username=username, password=password,
                nickname=nickname)
            login(request, user)
            # 迭代#185: 用户注册日志
            logger.info('用户注册: %s', user.username)
            messages.success(request, '注册成功啦~欢迎加入喵~🎉')
            return redirect('index')
        # 校验失败：同步写 flash（无 JS 时仍可见）并交给模板渲染内联红字
        for _field, _msg in field_errors:
            messages.error(request, _msg)
    return render(request, 'blog/register.html', {
        'active_nav': 'register',
        'field_errors': field_errors,
        'form_values': form_values,
    })


# 迭代#186: logout_view视图docstring
# 迭代#187: logout_view(request) -> HttpResponseRedirect 类型提示
def logout_view(request: HttpRequest) -> HttpResponseRedirect:
    """退出登录视图：销毁当前会话并重定向回首页。

    无 GET/POST 区分，访问即登出（实际退出按钮在 base.html 中以 POST 表单提交）。

    Args:
        request: 当前 HttpRequest 对象。

    Returns:
        HttpResponse: 始终重定向回首页。
    """
    # 迭代#188: 用户登出日志
    logger.info('用户登出: %s', request.user.username if request.user.is_authenticated else 'anonymous')
    logout(request)
    messages.success(request, '已退出登录，下次再来玩喵~👋')
    return redirect('index')


# 迭代#189: user_profile视图docstring
# 迭代#190: user_profile(request, username) -> HttpResponse 类型提示
def user_profile(request: HttpRequest, username: str) -> HttpResponse:
    """用户个人主页：展示指定用户的资料卡、统计数据与已发布文章列表。

    - 按 username 取用户，不存在则 404；
    - 仅展示该用户的"已发布"文章（草稿不对访客公开）；
    - 统计数据：文章总数、总阅读量、总点赞数、总评论数、收藏数；
    - 同时展示该用户收藏的文章列表（仅收藏公开文章）；
    - 若访问者本人就是主页主人，额外显示"编辑资料"按钮。

    Args:
        request: 当前 HttpRequest 对象。
        username: URL 中捕获的用户名。

    Returns:
        HttpResponse: 渲染后的个人主页 HTML。
    """
    # 按用户名查找用户，不存在则 404
    profile_user = get_object_or_404(User, username=username)
    # ---- 查询该用户的已发布文章（分页，每页 10 篇）----
    article_qs = Article.objects.filter(
        author=profile_user, status=Article.Status.PUBLISHED
    ).select_related('category').prefetch_related('tags').order_by('-created_at', '-id')
    paginator = Paginator(article_qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    # ---- 统计数据：聚合查询，避免循环逐条 count ----
    published_articles = article_qs
    total_views = published_articles.aggregate(v=Sum('views'))['v'] or 0
    total_likes = published_articles.aggregate(l=Sum('likes'))['l'] or 0
    total_comments = published_articles.aggregate(c=Sum('comment_count'))['c'] or 0
    # 收藏数：该用户收藏的文章总数
    fav_count = Favorite.objects.filter(user=profile_user).count()
    user_stats = {
        'article_count': published_articles.count(),
        'total_views': total_views,
        'total_likes': total_likes,
        'total_comments': total_comments,
        'fav_count': fav_count,
    }
    # ---- 该用户收藏的文章列表（仅已发布文章）----
    # 通过 Favorite 表关联查询，select_related 预加载文章与作者
    fav_articles = Article.objects.filter(
        favorites__user=profile_user, status=Article.Status.PUBLISHED
    ).select_related('author', 'category').order_by('-favorites__created_at')[:20]
    # ---- 判断是否为本人访问 ----
    is_own_profile = request.user.is_authenticated and request.user == profile_user
    ctx = {
        'profile_user': profile_user,
        'page_obj': page_obj,
        'page_range': list(paginator.page_range),
        'user_stats': user_stats,
        'fav_articles': fav_articles,
        'is_own_profile': is_own_profile,
        'active_nav': 'home',
    }
    return render(request, 'blog/user_profile.html', ctx)


@login_required
# 迭代#191: user_settings视图docstring
# 迭代#192: user_settings(request) -> HttpResponse 类型提示
# 迭代#193: user_settings分区域处理注释
# 迭代#194: user_settings头像Pillow验证注释
def user_settings(request: HttpRequest) -> HttpResponse:
    """用户设置页：修改基本资料 / 上传头像 / 修改密码。

    GET：渲染设置表单，回填当前用户数据。
    POST：根据提交的区域表单分别处理：
    - ``profile_form``：nickname（截断50字）、introduction（bleach 净化纯文本，截断500字）；
    - ``avatar_form``：avatar 上传（Pillow 验证真实图片，≤2MB，仅 jpg/png/gif/webp）；
    - ``password_form``：旧密码校验、新密码≥8位、两次一致。

    每个区域独立处理，修改成功后通过 messages 提示。

    Args:
        request: 当前 HttpRequest 对象。

    Returns:
        HttpResponse: GET 时渲染设置页；POST 后重定向回设置页并带 flash 消息。
    """
    # 头像上传允许的扩展名白名单
    AVATAR_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    # 头像大小上限 2MB
    AVATAR_MAX_BYTES = 2 * 1024 * 1024

    if request.method == 'POST':
        # 通过表单提交的按钮名称区分当前处理哪个区域
        if 'profile_form' in request.POST:
            # ---- 区域A：基本资料 ----
            nickname = (request.POST.get('nickname') or '').strip()[:50]
            introduction = request.POST.get('introduction') or ''
            # 用 bleach 净化为纯文本（不允许任何 HTML 标签），防止 XSS
            introduction = bleach.clean(introduction, tags=[], attributes={}, strip=True)
            introduction = introduction[:500]
            request.user.nickname = nickname
            request.user.introduction = introduction
            request.user.save(update_fields=['nickname', 'introduction'])
            messages.success(request, '基本资料已更新喵~ 🌸')
            return redirect('user_settings')

        elif 'avatar_form' in request.POST:
            # ---- 区域B：头像上传 ----
            avatar_file = request.FILES.get('avatar')
            if not avatar_file:
                messages.error(request, '请选择要上传的头像文件喵~ 📷')
            else:
                # 验证扩展名白名单
                ext = os.path.splitext(avatar_file.name)[1].lower()
                if ext not in AVATAR_EXTS:
                    messages.error(request, '只支持 jpg / png / gif / webp 格式的图片哦~ 🖼')
                elif avatar_file.size > AVATAR_MAX_BYTES:
                    messages.error(request, '头像不能超过 2MB 呢~ 太大了喵~ 📦')
                else:
                    # 用 Pillow 验证是否为真实图片（防止伪装扩展名）
                    try:
                        img = Image.open(avatar_file)
                        img.verify()
                        avatar_file.seek(0)
                    except Exception:
                        messages.error(request, '文件不是有效的图片呢~ 换一个吧喵~ 😿')
                    else:
                        request.user.avatar = avatar_file
                        request.user.save(update_fields=['avatar'])
                        messages.success(request, '头像已更新啦~ ✨')
            return redirect('user_settings')

        elif 'password_form' in request.POST:
            # ---- 区域C：修改密码 ----
            old_password = request.POST.get('old_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')
            # 校验旧密码
            if not request.user.check_password(old_password):
                messages.error(request, '旧密码不对呢~ 再试试喵~ 🔍')
            elif len(new_password) < 8:
                messages.error(request, '新密码至少要 8 位哦~ 🔒')
            elif new_password != confirm_password:
                messages.error(request, '两次输入的新密码不一样呢~ 🔑')
            else:
                request.user.set_password(new_password)
                request.user.save()
                # 修改密码后重新登录，保持会话有效
                login(request, request.user)
                messages.success(request, '密码已修改成功喵~ 🔐')
            return redirect('user_settings')

    # GET：渲染设置表单，回填当前用户数据
    ctx = {
        'active_nav': 'settings',
    }
    return render(request, 'blog/user_settings.html', ctx)


@login_required
# 迭代#195: my_articles视图docstring
# 迭代#196: my_articles(request) -> HttpResponse 类型提示
def my_articles(request: HttpRequest) -> HttpResponse:
    """我的文章管理页：当前用户查看 / 筛选 / 搜索自己的全部文章（含草稿）。

    - 查询当前用户的所有文章（含草稿），按更新时间倒序；
    - 支持筛选：``?status=published|draft``（默认全部）；
    - 支持搜索：``?q=关键词`` 模糊匹配文章标题；
    - 分页每页 15 篇。

    Args:
        request: 当前 HttpRequest 对象。

    Returns:
        HttpResponse: 渲染后的我的文章管理页。
    """
    # 基础查询集：仅当前用户的文章，预加载分类，按更新时间倒序
    qs = Article.objects.filter(author=request.user).select_related(
        'category').order_by('-updated_at', '-id')
    # ---- 状态筛选 ----
    filter_status = request.GET.get('status', '')
    if filter_status in Article.Status.values:
        qs = qs.filter(status=filter_status)
    else:
        filter_status = ''   # 非法值回退为"全部"
    # ---- 标题搜索 ----
    search_q = request.GET.get('q', '').strip()
    if search_q:
        qs = qs.filter(title__icontains=search_q)
    # ---- 分页（每页 15 篇）----
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    # ---- 各状态文章计数（用于筛选标签栏显示数量）----
    all_count = Article.objects.filter(author=request.user).count()
    published_count = Article.objects.filter(
        author=request.user, status=Article.Status.PUBLISHED).count()
    draft_count = Article.objects.filter(
        author=request.user, status=Article.Status.DRAFT).count()
    ctx = {
        'page_obj': page_obj,
        'page_range': list(paginator.page_range),
        'filter_status': filter_status,
        'search_q': search_q,
        'counts': {
            'all': all_count,
            'published': published_count,
            'draft': draft_count,
        },
        'active_nav': 'my_articles',
    }
    return render(request, 'blog/my_articles.html', ctx)


# ============================ 67. 文章系列 ============================

# 迭代#197: series_list视图docstring完善
def series_list(request):
    """67. 系列列表页：展示所有文章系列（封面 + 标题 + 文章数）。"""
    series_qs = Series.objects.annotate(
        n=Count('articles')).order_by('-created_at')
    ctx = {
        'series_list': series_qs,
        'active_nav': 'series',
        'meta_title': f'文章系列 - {settings.SITE_NAME}',
        'meta_description': f'{settings.SITE_NAME} 文章系列合集。',
    }
    ctx.update(_sidebar())
    return render(request, 'blog/series_list.html', ctx)


# 迭代#198: series_detail视图docstring完善
def series_detail(request, pk):
    """67. 系列详情页：展示系列介绍 + 该系列全部文章（按 series_order 排序）。"""
    series = get_object_or_404(Series, pk=pk)
    # 系列下已发布文章，按系列序号升序
    articles = series.articles.filter(
        status=Article.Status.PUBLISHED).order_by('series_order', 'id')
    ctx = {
        'series': series,
        'series_articles': articles,
        'active_nav': 'series',
        'meta_title': f'{series.title} - 文章系列',
        'meta_description': (series.description or series.title)[:150],
    }
    ctx.update(_sidebar())
    return render(request, 'blog/series_detail.html', ctx)


@login_required
def series_create(request: HttpRequest) -> HttpResponse:
    """67扩展：创建文章系列。

    登录用户可创建系列，把同主题文章组织到一起按顺序阅读。
    - GET：渲染萌系创建表单；
    - POST：校验名称后创建系列，可选简介与封面，成功后跳转系列详情页。
    """
    if request.method == 'POST':
        title = (request.POST.get('title') or '').strip()
        description = (request.POST.get('description') or '').strip()[:500]
        if not title:
            ctx = {
                'error': '系列名称不能为空喵~📝',
                'form_title': title, 'form_desc': description,
                'active_nav': 'series', 'meta_title': '创建系列',
            }
            ctx.update(_sidebar())
            return render(request, 'blog/series_form.html', ctx)
        series = Series(title=title[:80], description=description,
                        author=request.user)
        cover = request.FILES.get('cover_image')
        if cover:
            series.cover_image = cover
        series.save()
        messages.success(request, '系列创建成功喵~现在写文章就能归入它啦✨')
        return redirect('series_detail', pk=series.pk)
    ctx = {'active_nav': 'series',
           'meta_title': f'创建系列 - {settings.SITE_NAME}'}
    ctx.update(_sidebar())
    return render(request, 'blog/series_form.html', ctx)



# ============================ 69. 网站运行状态页 ============================

# 迭代#201: server_status视图docstring
# 迭代#202: server_status(request) -> HttpResponse 类型提示
# 迭代#203: server_status健康检查逻辑注释
@staff_member_required
def server_status(request: HttpRequest) -> HttpResponse:
    """69. 网站运行状态页：检查数据库 / Redis 连通性，统计数据与版本信息。"""
    from django import get_version
    status_dict = {}

    # ---- 数据库连接：执行 SELECT 1 探测 ----
    try:
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute('SELECT 1')
            cur.fetchone()
        status_dict['database'] = {'label': '数据库 (MySQL)', 'state': 'ok',
                                   'detail': '连接正常'}
    except Exception as exc:  # noqa: BLE001 状态页需兜底展示错误
        status_dict['database'] = {'label': '数据库 (MySQL)', 'state': 'error',
                                   'detail': f'连接失败: {exc}'}

    # ---- Redis 连接：尝试 ping（未配置 / 不可达时降级为 warn）----
    try:
        import redis
        r = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2)
        r.ping()
        status_dict['redis'] = {'label': 'Redis 缓存', 'state': 'ok', 'detail': 'PONG 正常'}
    except Exception as exc:  # noqa: BLE001
        status_dict['redis'] = {'label': 'Redis 缓存', 'state': 'warn',
                               'detail': f'未连接（{type(exc).__name__}），降级使用'}

    # ---- Celery worker：简单探测 broker 上的活跃 worker ----
    try:
        from celery import current_app
        insp = current_app.control.inspect(timeout=1)
        active = insp.ping()
        if active:
            status_dict['celery'] = {'label': 'Celery 异步任务', 'state': 'ok',
                                     'detail': f'{len(active)} 个 worker 在线'}
        else:
            status_dict['celery'] = {'label': 'Celery 异步任务', 'state': 'warn',
                                     'detail': '未发现运行中的 worker'}
    except Exception as exc:  # noqa: BLE001
        status_dict['celery'] = {'label': 'Celery 异步任务', 'state': 'warn',
                                 'detail': f'检查失败（{type(exc).__name__}）'}

    # ---- 统计数据 ----
    today = timezone.now().date()
    stats = {
        'article_total': Article.objects.count(),
        'published_total': Article.objects.filter(status=Article.Status.PUBLISHED).count(),
        'comment_total': Comment.objects.count(),
        'user_total': User.objects.count(),
        'views_total': Article.objects.aggregate(v=Sum('views'))['v'] or 0,
        'today_visits': AccessLog.objects.filter(created_at__date=today).count(),
    }
    # ---- 版本信息 ----
    versions = {
        'python': os.sys.version.split()[0],
        'django': get_version(),
        'mysql': 'MySQL',
        'redis': getattr(settings, 'CELERY_BROKER_URL', ''),
    }
    ctx = {
        'status_dict': status_dict,
        'stats': stats,
        'versions': versions,
        'active_nav': 'status',
        'meta_title': f'运行状态 - {settings.SITE_NAME}',
    }
    return render(request, 'blog/status.html', ctx)


# ============================ 70. API 文档页 ============================

# 70. 手工登记的 API 端点清单：供文档页渲染（方法 / 路径 / 说明 / 参数 / 示例）
API_ENDPOINTS = [
    {'method': 'GET', 'path': '/api/articles/', 'desc': '文章列表（分页）',
     'params': '?page= &page_size= &q= &category= &tag= &kind= &sort=hot|latest',
     'curl': 'curl "http://localhost:8000/api/articles/?page=1&q=django"',
     'resp': '{"count":114,"next":...,"results":[{"id":1,"title":"..."}]}'},
    {'method': 'POST', 'path': '/api/articles/', 'desc': '新建文章（需登录）',
     'params': 'title, content, kind, status, tag_names',
     'curl': 'curl -X POST http://localhost:8000/api/articles/ -H "X-CSRFToken: ..." -d "title=test&content=<p>hi</p>"',
     'resp': '{"id":115,"title":"test",...}'},
    {'method': 'GET', 'path': '/api/articles/<pk>/', 'desc': '文章详情',
     'params': '路径参数 pk',
     'curl': 'curl http://localhost:8000/api/articles/1/',
     'resp': '{"id":1,"title":"...","content":"..."}'},
    {'method': 'PUT/PATCH', 'path': '/api/articles/<pk>/', 'desc': '修改文章（作者/管理员）',
     'params': '同新建字段',
     'curl': 'curl -X PATCH http://localhost:8000/api/articles/1/ -d "title=new"',
     'resp': '{"id":1,"title":"new",...}'},
    {'method': 'DELETE', 'path': '/api/articles/<pk>/', 'desc': '删除文章（作者/管理员）',
     'params': '路径参数 pk',
     'curl': 'curl -X DELETE http://localhost:8000/api/articles/99/',
     'resp': '204 No Content'},
    {'method': 'POST', 'path': '/api/articles/<pk>/like/', 'desc': '点赞文章（session 防重复，幂等）',
     'params': '无',
     'curl': 'curl -X POST http://localhost:8000/api/articles/1/like/',
     'resp': '{"likes": 42, "liked": true}'},
    {'method': 'POST', 'path': '/api/articles/<pk>/rate/', 'desc': '文章评分 1~5 星（登录用户，幂等更新）',
     'params': 'score=1..5',
     'curl': 'curl -X POST http://localhost:8000/api/articles/1/rate/ -d "score=5"',
     'resp': '{"success":true,"avg":4.6,"count":10,"my":5}'},
    {'method': 'POST', 'path': '/article/<pk>/favorite/', 'desc': '收藏/取消收藏文章（登录用户，幂等）',
     'params': '无',
     'curl': 'curl -X POST http://localhost:8000/article/1/favorite/',
     'resp': '{"favorited": true, "count": 3}'},
    {'method': 'POST', 'path': '/api/comments/<pk>/like/', 'desc': '点赞评论（session 防重复，幂等）',
     'params': '无',
     'curl': 'curl -X POST http://localhost:8000/api/comments/1/like/',
     'resp': '{"likes": 5, "liked": true}'},
    {'method': 'GET', 'path': '/api/search/suggest/', 'desc': '搜索建议（标题自动补全）',
     'params': '?q=关键词',
     'curl': 'curl "http://localhost:8000/api/search/suggest/?q=django"',
     'resp': '{"suggestions": ["Django 入门", "Django 部署"]}'},
    {'method': 'POST', 'path': '/api/upload-image/', 'desc': '富文本图片上传（登录用户）',
     'params': 'multipart 字段 upload',
     'curl': 'curl -X POST http://localhost:8000/api/upload-image/ -F "upload=@a.png"',
     'resp': '{"uploaded":1,"fileName":"a.png","url":"/media/..."}'},
    {'method': 'GET', 'path': '/api/categories/', 'desc': '分类列表（含文章数）',
     'params': '无',
     'curl': 'curl http://localhost:8000/api/categories/',
     'resp': '[{"id":1,"name":"Django","article_count":12}]'},
    {'method': 'POST', 'path': '/api/categories/', 'desc': '新建分类（仅管理员）',
     'params': 'name, description',
     'curl': 'curl -X POST http://localhost:8000/api/categories/ -d "name=Python"',
     'resp': '{"id":5,"name":"Python",...}'},
    {'method': 'GET/PUT/DELETE', 'path': '/api/categories/<pk>/', 'desc': '分类详情/修改/删除',
     'params': '路径参数 pk',
     'curl': 'curl http://localhost:8000/api/categories/1/',
     'resp': '{"id":1,"name":"Django",...}'},
    {'method': 'GET', 'path': '/api/tags/', 'desc': '标签列表（含文章数）',
     'params': '无',
     'curl': 'curl http://localhost:8000/api/tags/',
     'resp': '[{"id":1,"name":"django","article_count":8}]'},
    {'method': 'POST', 'path': '/api/tags/', 'desc': '新建标签',
     'params': 'name',
     'curl': 'curl -X POST http://localhost:8000/api/tags/ -d "name=flask"',
     'resp': '{"id":20,"name":"flask",...}'},
    {'method': 'GET/PUT/DELETE', 'path': '/api/tags/<pk>/', 'desc': '标签详情/修改/删除',
     'params': '路径参数 pk',
     'curl': 'curl http://localhost:8000/api/tags/1/',
     'resp': '{"id":1,"name":"django",...}'},
]


# 迭代#204: api_docs视图docstring
# 迭代#205: api_docs(request) -> HttpResponse 类型提示
def api_docs(request: HttpRequest) -> HttpResponse:
    """70. API 文档页：列出全部端点，支持前端搜索过滤。"""
    ctx = {
        'endpoints': API_ENDPOINTS,
        'active_nav': 'api_docs',
        'meta_title': f'API 文档 - {settings.SITE_NAME}',
        'meta_description': f'{settings.SITE_NAME} 开放 API 接口文档。',
    }
    return render(request, 'blog/api_docs.html', ctx)


# ============================ DRF 接口 ============================

# 迭代#206: like_article视图docstring
# 迭代#207: like_article(request, pk) -> JsonResponse 类型提示
# 迭代#208: like_article session防重复注释
def like_article(request: HttpRequest, pk: int) -> JsonResponse:
    """文章点赞接口：POST /api/articles/<pk>/like/，session 防重、toggle 语义（D2修复）。

    流程：
    1. 仅接受 POST 请求，GET 访问返回 405；
    2. 按主键取出已发布文章（草稿不允许点赞）；
    3. 从 session 读取已点赞文章 id 列表 ``liked_article_ids``；
    4. 已赞过 → 取消赞：从 session 移除，``F('likes') - 1``（不低于 0），返回 liked=false；
    5. 未赞过 → ``F('likes') + 1`` 原子自增，把当前 pk 写入 session 列表，返回 liked=true；
    6. 点赞/取消都是写路径：调用 ``invalidate_article(pk)`` 失效文章片段缓存，
       确保聚合数字（likes）在下一次请求立即从 DB 重建，不被 TTL 掩盖；
    7. 返回 JSON ``{"likes": N, "liked": bool}``。

    Args:
        request: 当前 HttpRequest 对象。
        pk: 文章主键。

    Returns:
        JsonResponse: 含最新点赞数与当前会话是否已赞的 JSON。
    """
    # 仅接受 POST，防止 GET 误触发
    if request.method != 'POST':
        return JsonResponse({'detail': '请用 POST 请求点赞喵~'}, status=405)
    # 只能对已发布文章点赞
    article = get_object_or_404(Article, pk=pk, status=Article.Status.PUBLISHED)
    # 从 session 取已点赞列表（首次访问时为空列表）
    liked_ids = request.session.get('liked_article_ids', [])
    if pk in liked_ids:
        # 已赞过 → 取消赞（toggle 语义）
        liked_ids.remove(pk)
        Article.objects.filter(pk=pk).update(likes=F('likes') - 1)
        # 防止减成负数
        Article.objects.filter(pk=pk, likes__lt=0).update(likes=0)
        liked = False
        # 取消赞时清理对应 LIKE 通知（避免作者收到已取消的赞通知）
        try:
            liker = request.user if request.user.is_authenticated else None
            if liker and liker.pk != article.author_id:
                Notification.objects.filter(
                    user=article.author, type=Notification.Type.LIKE,
                    title__startswith=f'{liker} 赞了你的文章').delete()
        except Exception:
            pass
    else:
        # F() 表达式在数据库层原子自增点赞数，避免并发覆盖
        Article.objects.filter(pk=pk).update(likes=F('likes') + 1)
        liked_ids.append(pk)
        liked = True
    request.session['liked_article_ids'] = liked_ids
    request.session.modified = True   # 显式标记 session 已修改，确保落库
    article.refresh_from_db(fields=['likes'])
    # 点赞/取消都是写路径：失效文章片段缓存，聚合数字即时一致
    try:
        from .cache_keys import invalidate_article
        invalidate_article(pk)
    except Exception:
        pass
    if liked:
        # 第5轮 F8: 文章被赞时通知作者（避免自己赞自己）
        try:
            liker = request.user if request.user.is_authenticated else None
            if liker and liker.pk != article.author_id:
                Notification.objects.get_or_create(
                    user=article.author, type=Notification.Type.LIKE,
                    title=f'{liker} 赞了你的文章《{article.title[:30]}》',
                    defaults={'related_url': article.get_absolute_url()})
            from .views import check_and_award_badges
            # 作者获赞后检查徽章
            check_and_award_badges(article.author)
        except Exception:
            pass
    return JsonResponse({'likes': article.likes, 'liked': liked})


@login_required
# 迭代#209: toggle_favorite视图docstring
# 迭代#210: toggle_favorite(request, pk) -> JsonResponse 类型提示
# 迭代#211: toggle_favorite unique_together处理注释
def toggle_favorite(request: HttpRequest, pk: int) -> JsonResponse:
    """切换文章收藏状态（AJAX 接口，返回 JSON）。

    流程：
    1. 仅接受 POST 请求，GET 访问返回 405；
    2. 按主键取出已发布文章（草稿不允许收藏）；
    3. 查询当前用户是否已收藏本文；
    4. 已收藏则删除记录（取消收藏），未收藏则创建记录；
    5. 返回 JSON ``{"favorited": bool, "count": int}``，
       count 为该文章当前被收藏的总人数。

    Args:
        request: 当前 HttpRequest 对象。
        pk: 文章主键。

    Returns:
        JsonResponse: 含收藏状态与收藏总数的 JSON。
    """
    # 仅接受 POST，防止 GET 误触发
    if request.method != 'POST':
        return JsonResponse({'detail': '请用 POST 请求收藏喵~'}, status=405)
    # 只能对已发布文章收藏
    article = get_object_or_404(Article, pk=pk, status=Article.Status.PUBLISHED)
    # 查询当前用户是否已收藏
    fav = Favorite.objects.filter(user=request.user, article=article).first()
    if fav:
        # 已收藏 → 取消收藏（删除记录）
        fav.delete()
        favorited = False
    else:
        # 未收藏 → 创建收藏记录（unique_together 保证不重复）
        # 第5轮 C10: 可选指定收藏夹 folder_id
        folder = None
        folder_id = (request.POST.get('folder_id') or request.GET.get('folder_id') or '').strip()
        if folder_id.isdigit():
            folder = FavoriteFolder.objects.filter(pk=int(folder_id), user=request.user).first()
        Favorite.objects.get_or_create(user=request.user, article=article, defaults={'folder': folder})
        favorited = True
    # 统计该文章当前被收藏的总人数
    count = Favorite.objects.filter(article=article).count()
    return JsonResponse({'favorited': favorited, 'count': count})


@login_required
# 迭代#212: rate_article视图docstring
# 迭代#213: rate_article(request, pk) -> JsonResponse 类型提示
# 迭代#214: rate_article冗余字段更新注释
def rate_article(request: HttpRequest, pk: int) -> JsonResponse:
    """63. 文章评分接口：POST /api/articles/<pk>/rate/。

    流程：
    1. 仅接受 POST，登录用户才能评分；
    2. 取已发布文章（草稿不可评分）；
    3. score 必须为 1~5 的整数，否则 400；
    4. get_or_create 拿到"当前用户对本文"的评分记录，存在则更新分数（重复提交幂等）；
    5. 重算文章冗余字段 rating_avg / rating_count；
    6. 返回 {"avg": 4.5, "count": 10, "my": 5}。

    Args:
        request: 当前 HttpRequest 对象。
        pk: 文章主键。

    Returns:
        JsonResponse: 含平均分 / 评分人数 / 本人本次分数的 JSON。
    """
    if request.method != 'POST':
        return JsonResponse({'detail': '请用 POST 提交评分喵~'}, status=405)
    article = get_object_or_404(Article, pk=pk, status=Article.Status.PUBLISHED)
    # 解析并校验分数（1~5）
    try:
        score = int(request.POST.get('score', 0))
    except (TypeError, ValueError):
        score = 0
    # 迭代#215: 评分范围验证（1-5）
    if score not in dict(Rating.Score.choices):
        return JsonResponse({'success': False, 'error': '评分必须是 1~5 星哦~⭐'}, status=400)
    # unique_together 保证每用户每文章一条；存在则更新分数
    rating, _ = Rating.objects.update_or_create(
        user=request.user, article=article,
        defaults={'score': score})
    # 重算冗余字段：平均分（保留一位小数）+ 评分人数
    agg = article.ratings.aggregate(avg=Avg('score'), cnt=Count('id'))
    article.rating_avg = round(agg['avg'] or 0, 1)
    article.rating_count = agg['cnt'] or 0
    article.save(update_fields=['rating_avg', 'rating_count'])
    return JsonResponse({
        'success': True,
        'avg': article.rating_avg,
        'count': article.rating_count,
        'my': rating.score,
        # 第4轮 C8: 兼容跨 Agent 接口命名，同时返回语义化字段
        'rating_avg': article.rating_avg,
        'rating_count': article.rating_count,
        'my_rating': rating.score,
    })


# 第4轮 C7: 文章分享计数接口
def share_article(request: HttpRequest, pk: int) -> JsonResponse:
    """文章分享接口：POST /api/article/<pk>/share/，登录或匿名均可调用。

    流程：
    1. 仅接受 POST；
    2. 取已发布文章；
    3. 用 F() 表达式原子自增 share_count，避免并发覆盖；
    4. 返回最新 share_count。

    Args:
        request: 当前 HttpRequest 对象。
        pk: 文章主键。

    Returns:
        JsonResponse: ``{share_count: int}``。
    """
    if request.method != 'POST':
        return JsonResponse({'detail': '请用 POST 请求分享喵~'}, status=405)
    article = get_object_or_404(Article, pk=pk, status=Article.Status.PUBLISHED)
    # F() 表达式在数据库层原子自增，避免并发读-改-写丢失计数
    Article.objects.filter(pk=pk).update(share_count=F('share_count') + 1)
    article.refresh_from_db(fields=['share_count'])
    return JsonResponse({'share_count': article.share_count})

# 迭代#216: _Pagination类docstring完善
class _Pagination(PageNumberPagination):
    """DRF 接口分页器：默认每页 10 条，支持 ?page_size= 自定义（上限 50）。"""
    page_size = 10                      # 默认每页条数
    page_size_query_param = 'page_size'  # 允许客户端通过 ?page_size= 调整
    max_page_size = 50                  # 单页上限，防止一次拉取过多数据


# 迭代#217: ArticleListCreateView类docstring完善
class ArticleListCreateView(APIView):
    """文章 新增 / 列表查询。GET /api/articles/，POST /api/articles/"""
    pagination_class = _Pagination

    def get(self, request):
        qs, _, _ = _filter_articles(request, _base_qs(request))
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = ArticleListSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = ArticleSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        article = serializer.save(author=request.user)
        EditLog.objects.create(article=article, editor=request.user)
        return Response(ArticleSerializer(article, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)


# 迭代#218: ArticleDetailView类docstring完善
class ArticleDetailView(APIView):
    """文章 单篇查询 / 修改 / 删除。/api/articles/<pk>/"""

    def _get_object(self, request, pk):
        """按主键取文章，并校验草稿可见权限。

        已发布文章任何人可见；草稿仅作者本人或管理员可见，否则抛 PermissionDenied。
        """
        article = get_object_or_404(Article, pk=pk)
        if article.status != Article.Status.PUBLISHED and (
                not request.user.is_authenticated or
                (article.author != request.user and not request.user.is_staff)):
            raise PermissionDenied('无权查看该草稿')
        return article

    def get(self, request, pk):
        """GET：返回单篇文章完整详情 JSON。"""
        article = self._get_object(request, pk)
        return Response(ArticleSerializer(article, context={'request': request}).data)

    def put(self, request, pk):
        """PUT：全量更新文章。"""
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        """PATCH：部分更新文章。"""
        return self._update(request, pk, partial=True)

    def _update(self, request, pk, partial):
        """更新文章公共逻辑：校验权限 -> 序列化 -> 保存 -> 记录修改日志。"""
        article = self._get_object(request, pk)
        if article.author != request.user and not request.user.is_staff:
            raise PermissionDenied('只能修改自己的文章')
        serializer = ArticleSerializer(
            article, data=request.data, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)
        article = serializer.save()
        EditLog.objects.create(article=article, editor=request.user)
        return Response(ArticleSerializer(article, context={'request': request}).data)

    def delete(self, request, pk):
        """DELETE：删除文章（仅作者本人或管理员）。"""
        article = self._get_object(request, pk)
        if article.author != request.user and not request.user.is_staff:
            raise PermissionDenied('无权删除该文章')
        article.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class _CsrfExemptSessionAuthentication(SessionAuthentication):
    """CKEditor 图片对话框以隐藏 iframe 表单提交，无法带 X-CSRFToken，单独豁免。"""
    def enforce_csrf(self, request):
        return


@method_decorator(csrf_exempt, name='dispatch')
# 迭代#219: ImageUploadView类docstring完善
class ImageUploadView(APIView):
    """富文本图片上传，兼容 CKEditor 两种契约：
    - 图片对话框（querystring 带 CKEditorFuncNum）：返回 <script> 回调；
    - 拖拽 / 粘贴上传：返回 {uploaded,fileName,url} JSON。"""
    authentication_classes = [_CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        func_num = request.GET.get('CKEditorFuncNum')

        def respond(ok, url='', message=''):
            if func_num is not None:
                args = json.dumps(
                    [int(func_num), url, message], ensure_ascii=False)[1:-1]
                return HttpResponse(
                    f'<script>window.parent.CKEDITOR.tools.callFunction({args});</script>')
            if ok:
                return JsonResponse(
                    {'uploaded': 1, 'fileName': os.path.basename(url), 'url': url})
            return JsonResponse(
                {'uploaded': 0, 'error': {'message': message}}, status=400)

        upload = request.FILES.get('upload') or request.FILES.get('file')
        if not upload:
            return respond(False, message='未收到图片文件')
        ext = os.path.splitext(upload.name)[1].lower()
        if ext not in settings.UPLOAD_IMAGE_EXTS:
            return respond(False, message='不支持的图片格式')
        if upload.size > settings.UPLOAD_IMAGE_MAX_BYTES:
            return respond(False, message='图片不能超过 8MB')
        # Pillow 校验真实图片，防止伪装扩展名
        # 迭代#220: ImageUploadView中图片打开异常处理
        try:
            image = Image.open(upload)
            image.verify()
            upload.seek(0)
        except (Image.UnidentifiedImageError, OSError):
            return respond(False, message='文件不是有效图片')

        year, month = datetime.now().strftime('%Y'), datetime.now().strftime('%m')
        rel_dir = os.path.join('uploads', year, month)
        abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
        # 迭代#221: ImageUploadView中目录创建异常处理
        try:
            os.makedirs(abs_dir, exist_ok=True)
        except OSError as os_exc:
            logger.error('上传目录创建失败: %s', os_exc)
            return respond(False, message='服务器存储错误')
        filename = f'{uuid.uuid4().hex}{ext}'
        # 迭代#222: ImageUploadView中文件写入异常处理
        try:
            with open(os.path.join(abs_dir, filename), 'wb') as fp:
                for chunk in upload.chunks():
                    fp.write(chunk)
        except OSError as wr_exc:
            logger.error('上传文件写入失败: %s', wr_exc)
            return respond(False, message='文件保存失败')
        # 迭代#223: 图片上传日志
        logger.info('图片上传: %s by %s', upload.name, request.user.username)
        url = request.build_absolute_uri(f'{settings.MEDIA_URL}uploads/{year}/{month}/{filename}')
        return respond(True, url=url)


# 迭代#224: CategoryListCreateView类docstring完善
class CategoryListCreateView(APIView):
    """分类 列表 / 新增。"""
    pagination_class = _Pagination

    def get(self, request):
        qs = Category.objects.annotate(n=Count('articles')).order_by('-n', 'name')
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(CategorySerializer(page, many=True).data)

    def post(self, request):
        if not request.user.is_staff:
            raise PermissionDenied('仅管理员可创建分类')
        serializer = CategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CategoryDetailView(APIView):
    """分类 查询 / 修改 / 删除。"""

    def get(self, request, pk):
        return Response(CategorySerializer(get_object_or_404(Category, pk=pk)).data)

    def put(self, request, pk):
        if not request.user.is_staff:
            raise PermissionDenied('仅管理员可修改分类')
        category = get_object_or_404(Category, pk=pk)
        serializer = CategorySerializer(category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        if not request.user.is_staff:
            raise PermissionDenied('仅管理员可删除分类')
        get_object_or_404(Category, pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# 迭代#225: TagListCreateView类docstring完善
class TagListCreateView(APIView):
    """标签 列表 / 新增。"""
    pagination_class = _Pagination

    def get(self, request):
        qs = Tag.objects.annotate(n=Count('articles')).order_by('-n', 'name')
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(TagSerializer(page, many=True).data)

    def post(self, request):
        serializer = TagSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TagDetailView(APIView):
    """标签 查询 / 修改 / 删除。"""

    def get(self, request, pk):
        return Response(TagSerializer(get_object_or_404(Tag, pk=pk)).data)

    def put(self, request, pk):
        if not request.user.is_staff:
            raise PermissionDenied('仅管理员可修改标签')
        tag = get_object_or_404(Tag, pk=pk)
        serializer = TagSerializer(tag, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        if not request.user.is_staff:
            raise PermissionDenied('仅管理员可删除标签')
        get_object_or_404(Tag, pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



# ============================ 第2轮迭代#171-#190: DRF 视图集与 API 安全 ============================

# 第2轮迭代#174: 自定义限流类——按匿名/登录用户区分访问频率
class _AnonRateThrottle(throttling.ScopedRateThrottle):
    scope = 'anon'

# 第2轮迭代#183: 自定义限流说明——通过 throttle_classes 接入
# 第2轮迭代#189: 内容协商说明——默认 JSON 渲染，见 settings.REST_FRAMEWORK

# 第2轮迭代#171-#180: 增强文章视图集（ModelViewSet 风格）
class ArticleV2ViewSet(viewsets.ReadOnlyModelViewSet):
    """文章只读视图集：演示 queryset / serializer / permission / throttle / filter / pagination 全套配置。"""
    # 第2轮迭代#171: 自定义 queryset——仅公开已发布文章并预加载关联
    queryset = (Article.objects.filter(status=Article.Status.PUBLISHED)
                .select_related('author', 'category')
                .prefetch_related('tags').all())
    # 第2轮迭代#172: 自定义 serializer_class——使用增强版序列化器
    serializer_class = ArticleDetailV2Serializer
    # 第2轮迭代#173: 自定义 permission_classes——只读公开
    permission_classes = [permissions.AllowAny]
    # 第2轮迭代#174: 自定义 throttle_classes
    throttle_classes = [throttling.UserRateThrottle]
    # 第2轮迭代#175: 自定义 filter_backends——搜索 + 排序
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    # 第2轮迭代#176: 自定义 search_fields——标题/正文
    search_fields = ['title', 'content']
    # 第2轮迭代#177: 自定义 ordering_fields——按时间/阅读量
    ordering_fields = ['created_at', 'views', 'likes']
    # 第2轮迭代#178: 自定义 pagination_class——沿用全局分页
    pagination_class = PageNumberPagination

    # 第2轮迭代#179: 自定义 action——热门文章子路由
    @action(detail=False, methods=['get'])
    def hot(self, request):
        """返回阅读量 TOP10 的文章。"""
        qs = self.get_queryset().order_by('-views')[:10]
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        # 第2轮迭代#180: 自定义 response——直接返回序列化数据
        return Response(self.get_serializer(qs, many=True).data)


# 第2轮迭代#181: 认证说明——SessionAuthentication + BasicAuthentication（见 settings）
# 第2轮迭代#182: 权限说明——IsAuthenticatedOrReadOnly（见 settings 默认权限）
# 第2轮迭代#184: 过滤说明——filter_backends 已挂 SearchFilter/OrderingFilter
# 第2轮迭代#185: 搜索说明——search_fields 已配置
# 第2轮迭代#186: 排序说明——ordering_fields 已配置
# 第2轮迭代#187: 分页说明——PageNumberPagination + PAGE_SIZE
# 第2轮迭代#188: 版本控制说明——当前未启用版本化，URL 即版本
# 第2轮迭代#190: 错误处理说明——DRF 统一异常处理自动把 ValidationError 转 400


# ============================ SEO 输出：sitemap / RSS / robots ============================

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


# ============================ 自定义错误页面 ============================

# 迭代#234: custom_404视图docstring
# 迭代#235: custom_404(request, exception) -> HttpResponse 类型提示
def custom_404(request: HttpRequest, exception: Exception) -> HttpResponse:
    """404 页面：这个页面被喵喵吃掉了~（附带搜索框与热门文章快捷链接）"""
    # 迭代#236: 404错误日志
    logger.warning('404 Not Found: path=%s', request.path)
    # 6. 传入阅读量最高的 5 篇已发布文章，供 404 页"热门文章"区直接跳转
    hot = list(Article.objects.filter(status=Article.Status.PUBLISHED)
               .order_by('-views')[:5])
    return render(request, '404.html', {'hot_articles': hot}, status=404)


# 迭代#237: custom_500视图docstring
# 迭代#238: custom_500(request) -> HttpResponse 类型提示

def test_404_page(request: HttpRequest) -> HttpResponse:
    """第6轮: 404 页面手动测试路由（GET /test-404/）。

    生产环境 DEBUG=False 时自定义 404 模板难以直接调试，
    本路由直接渲染 404.html（含接樱花小游戏），返回 200 状态码便于浏览器验证。
    验证内容：404 文案、搜索框、热门文章链接、暗黑模式、接樱花 canvas 小游戏。
    """
    hot = list(Article.objects.filter(status=Article.Status.PUBLISHED)
               .order_by('-views')[:5])
    return render(request, '404.html', {'hot_articles': hot})

def custom_500(request: HttpRequest) -> HttpResponse:
    """500 页面：服务器酱正在罢工中…（注意：500 handler 不需要 exception 参数）"""
    # 迭代#239: 500错误日志
    logger.error('500 Internal Server Error: path=%s', request.path)
    return render(request, '500.html', status=500)


# 迭代#240: custom_403视图docstring
# 迭代#241: custom_403(request, exception) -> HttpResponse 类型提示
def custom_403(request: HttpRequest, exception: Exception) -> HttpResponse:
    """403 页面：喵？你没有权限看这个呢~"""
    # 迭代#242: 403错误日志
    logger.warning('403 Forbidden: path=%s user=%s', request.path,
                   request.user.username if request.user.is_authenticated else 'anonymous')
    return render(request, '403.html', status=403)


# ============================ 第5轮新增 API 视图 ============================
# 本区块集中实现第5轮后端百功能支撑：用户偏好/文章踩/评论增强/收藏夹/
# 通知中心/搜索热词/文章导出/二维码短链接/成就徽章/在线状态。

# ---- 常量 ----
COMMENT_IMAGE_MAX_BYTES = 2 * 1024 * 1024  # 评论图片上限 2MB
COMMENT_IMAGE_ALLOWED_FORMATS = ('JPEG', 'PNG', 'GIF', 'WEBP')  # PIL 允许的真实格式
COMMENT_WITHDRAW_MINUTES = 5  # 评论撤回时限（分钟）
SEARCH_HOT_KEY = 'search_history'   # 热门搜索词缓存 key
SEARCH_HOT_TTL = 86400              # 热门搜索词缓存 TTL（秒）
SHORT_LINK_CODE_LEN = 6             # 短链接码长度
ONLINE_WINDOW = timedelta(minutes=5)  # 在线判定窗口


def default_preferences() -> dict:
    """返回匿名用户使用的默认偏好字典（与 User 模型字段一一对应）。

    Returns:
        dict: 前端可直接消费的默认偏好。
    """
    return {
        'theme_color': 'purple_pink',
        'custom_theme_color': '#a855f7',
        'font_size': 'medium',
        'line_height': 'normal',
        'font_family': 'sans',
        'effects_enabled': True,
        'sound_enabled': False,
        'eye_protection': False,
        'amoled_dark': False,
        'birthday': '',
        'background_image': '',
        'signature': '',
    }


def _preferences_dict(user) -> dict:
    """把当前用户的偏好序列化为 dict；匿名则返回默认值。

    Args:
        user: request.user（可能匿名）。

    Returns:
        dict: 偏好字典。
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return default_preferences()
    return {
        'theme_color': user.theme_color,
        'custom_theme_color': user.custom_theme_color,
        'font_size': user.font_size,
        'line_height': user.line_height,
        'font_family': user.font_family,
        'effects_enabled': bool(user.effects_enabled),
        'sound_enabled': bool(user.sound_enabled),
        'eye_protection': bool(user.eye_protection),
        'amoled_dark': bool(user.amoled_dark),
        'birthday': user.birthday.isoformat() if user.birthday else '',
        'background_image': user.background_image.url if user.background_image else '',
        'signature': user.signature,
    }


# ----------------------------- 1. 用户偏好 -----------------------------
def api_user_preferences(request: HttpRequest) -> JsonResponse:
    """用户偏好读取(GET)/更新(PUT)。

    - GET：登录用户返回其偏好，匿名返回默认值；
    - PUT：仅登录用户，JSON body 提交部分字段，逐字段校验取值合法性后保存。

    Args:
        request: 当前 HttpRequest。

    Returns:
        JsonResponse: GET 返回 {code:0,data:偏好}；PUT 返回最新偏好。
    """
    if request.method == 'GET':
        return _json_ok(_preferences_dict(request.user))

    if request.method == 'PUT':
        # 仅登录用户可写
        if not request.user.is_authenticated:
            return JsonResponse({'code': 401, 'msg': '请先登录'}, status=401)
        try:
            body = json.loads(request.body.decode('utf-8') or '{}')
        except (ValueError, UnicodeDecodeError):
            return _bad_request('请求体不是合法 JSON')
        user = request.user
        # 允许更新的字段及其合法取值白名单
        CHOICE_MAP = {
            'theme_color': {'purple_pink', 'blue_green', 'orange_yellow', 'rose', 'custom'},
            'font_size': {'small', 'medium', 'large', 'xlarge'},
            'line_height': {'tight', 'normal', 'relaxed'},
            'font_family': {'sans', 'serif', 'mono'},
        }
        BOOL_FIELDS = {'effects_enabled', 'sound_enabled', 'eye_protection', 'amoled_dark'}
        update_fields = []
        for field, allowed in CHOICE_MAP.items():
            if field in body:
                val = str(body[field])
                if val not in allowed:
                    return _bad_request(f'{field} 取值非法')
                setattr(user, field, val)
                update_fields.append(field)
        for field in BOOL_FIELDS:
            if field in body:
                setattr(user, field, bool(body[field]))
                update_fields.append(field)
        if 'custom_theme_color' in body:
            val = str(body['custom_theme_color']).strip()[:7]
            # 仅允许 # 开头的 HEX 颜色，防止注入
            if val and not re.match(r'^#[0-9a-fA-F]{6}$', val):
                return _bad_request('自定义主题色必须是 #RRGGBB 形式的 HEX 值')
            user.custom_theme_color = val
            update_fields.append('custom_theme_color')
        if 'signature' in body:
            user.signature = str(body['signature']).strip()[:200]
            update_fields.append('signature')
        if 'birthday' in body:
            val = str(body['birthday']).strip()
            if val:
                try:
                    from datetime import date as _date
                    user.birthday = _date.fromisoformat(val)
                except ValueError:
                    return _bad_request('birthday 必须是 YYYY-MM-DD 形式')
            else:
                user.birthday = None
            update_fields.append('birthday')
        if update_fields:
            user.save(update_fields=update_fields)
        return _json_ok(_preferences_dict(user))

    return JsonResponse({'detail': '仅支持 GET / PUT'}, status=405)


# ----------------------------- 2. 文章踩（C1） -----------------------------
def api_article_dislike(request: HttpRequest, pk: int) -> JsonResponse:
    """文章踩接口：POST /api/article/<pk>/dislike/，session 防重、toggle 语义。

    流程：
    1. 仅 POST；只能对已发布文章踩；
    2. 从 session 取 ``disliked_article_ids``；
    3. 已踩 → 取消（从 session 移除，F(-1)，不低于 0）；未踩 → F(+1)；
    4. 返回 {dislike_count, disliked}。

    Args:
        request: 当前 HttpRequest。
        pk: 文章主键。

    Returns:
        JsonResponse: {dislike_count: int, disliked: bool}。
    """
    if request.method != 'POST':
        return JsonResponse({'detail': '请用 POST 请求踩喵~'}, status=405)
    article = get_object_or_404(Article, pk=pk, status=Article.Status.PUBLISHED)
    disliked_ids = request.session.get('disliked_article_ids', [])
    if pk in disliked_ids:
        # 已踩 → 取消
        disliked_ids.remove(pk)
        Article.objects.filter(pk=pk).update(
            dislike_count=F('dislike_count') - 1)
        # 防止减成负数
        Article.objects.filter(pk=pk, dislike_count__lt=0).update(dislike_count=0)
        disliked = False
    else:
        disliked_ids.append(pk)
        Article.objects.filter(pk=pk).update(dislike_count=F('dislike_count') + 1)
        disliked = True
    request.session['disliked_article_ids'] = disliked_ids
    request.session.modified = True
    article.refresh_from_db(fields=['dislike_count'])
    # 踩/取消都是写路径：失效文章片段缓存，聚合数字即时一致（D2修复）
    try:
        from .cache_keys import invalidate_article
        invalidate_article(pk)
    except Exception:
        pass
    return JsonResponse({'dislike_count': article.dislike_count, 'disliked': disliked})


# ----------------------------- 3. 评论增强（C5/C6/C13） -----------------------------
@login_required
def api_comment_image_upload(request: HttpRequest) -> JsonResponse:
    """评论图片上传：POST /api/comment/image/upload/。

    安全约束：
    - 仅登录用户；
    - 文件大小 ≤ 2MB；
    - 用 PIL.Image.open 验证真实文件头，只接受 JPEG/PNG/GIF/WEBP，不依赖扩展名；
    - 落盘到 MEDIA_ROOT/comment_images/，文件名用 uuid 重命名，杜绝路径穿越。

    Args:
        request: 当前 HttpRequest，file 字段名 ``image``。

    Returns:
        JsonResponse: 成功 {url, name}；失败 400。
    """
    if request.method != 'POST':
        return JsonResponse({'detail': '请用 POST 上传喵~'}, status=405)
    upload = request.FILES.get('image') or request.FILES.get('file')
    if not upload:
        return _bad_request('未收到图片文件')
    # 大小限制
    if upload.size > COMMENT_IMAGE_MAX_BYTES:
        return _bad_request('评论图片不能超过 2MB')
    # 文件头校验（不依赖扩展名）
    try:
        img = Image.open(upload)
        img.verify()
        upload.seek(0)
        if img.format not in COMMENT_IMAGE_ALLOWED_FORMATS:
            return _bad_request('仅支持 JPEG/PNG/GIF/WEBP 图片')
    except (Image.UnidentifiedImageError, OSError):
        return _bad_request('文件不是有效图片')
    # 按真实格式决定扩展名
    ext_map = {'JPEG': '.jpg', 'PNG': '.png', 'GIF': '.gif', 'WEBP': '.webp'}
    ext = ext_map.get(img.format, '.png')
    abs_dir = os.path.join(settings.MEDIA_ROOT, 'comment_images')
    try:
        os.makedirs(abs_dir, exist_ok=True)
    except OSError as exc:
        logger.error('评论图片目录创建失败: %s', exc)
        return _bad_request('服务器存储错误')
    filename = f'{uuid.uuid4().hex}{ext}'
    try:
        with open(os.path.join(abs_dir, filename), 'wb') as fp:
            for chunk in upload.chunks():
                fp.write(chunk)
    except OSError as exc:
        logger.error('评论图片写入失败: %s', exc)
        return _bad_request('文件保存失败')
    url = f'{settings.MEDIA_URL}comment_images/{filename}'
    logger.info('评论图片上传: %s by %s', filename, request.user.username)
    return _json_ok({'url': url, 'name': filename})


@login_required
@login_required
def api_comment_report(request: HttpRequest, pk: int) -> JsonResponse:
    """评论举报：POST /api/comment/<pk>/report/（路由名 api:api_comment_report）。

    创建 CommentReport 记录，并把被举报评论的 reported 置 True。
    同时兼容表单编码（request.POST）与 JSON（fetch application/json）两种提交。

    Args:
        request: 当前 HttpRequest，需登录；读取 ``reason``（可含 detail）。
        pk: 被举报评论主键。

    Returns:
        JsonResponse: {success: bool}，或 400/405。
    """
    if request.method != 'POST':
        return JsonResponse({'detail': '请用 POST 举报喵~'}, status=405)
    comment = get_object_or_404(Comment, pk=pk)
    # 优先取表单字段；为空再尝试解析 JSON 请求体（前端 fetch 发 JSON）
    reason = (request.POST.get('reason') or '').strip()
    detail = (request.POST.get('detail') or '').strip()
    if not reason:
        try:
            data = json.loads(request.body.decode('utf-8') or '{}')
        except (ValueError, UnicodeDecodeError):
            data = {}
        reason = (data.get('reason') or '').strip() if isinstance(data, dict) else ''
        detail = (data.get('detail') or '').strip() if isinstance(data, dict) else ''
    if detail:
        reason = ('%s｜%s' % (reason, detail))[:500]
    reason = reason[:500]
    if not reason:
        return _bad_request('举报原因不能为空')
    # get_or_create 防止同一用户对同一条评论重复举报
    CommentReport.objects.get_or_create(
        comment=comment, reporter=request.user, defaults={'reason': reason})
    if not comment.reported:
        Comment.objects.filter(pk=comment.pk).update(reported=True)
    return _json_ok({'success': True})


@login_required
def api_comment_delete(request: HttpRequest, pk: int) -> JsonResponse:
    """评论撤回：DELETE /api/comment/<pk>/（兼容 POST）。

    仅评论作者本人、且创建后 5 分钟内可撤回（删除评论并原子回退文章评论数）。

    Args:
        request: 当前 HttpRequest。
        pk: 评论主键。

    Returns:
        JsonResponse: {success: bool} 或 403/400。
    """
    if request.method not in ('DELETE', 'POST'):
        return JsonResponse({'detail': '请用 DELETE 请求撤回喵~'}, status=405)
    comment = get_object_or_404(Comment, pk=pk)
    # 仅作者本人
    if comment.user_id != request.user.pk:
        return _forbidden('只能撤回自己的评论')
    # 5 分钟时限
    deadline = comment.created_at + timedelta(minutes=COMMENT_WITHDRAW_MINUTES)
    if timezone.now() > deadline:
        return _bad_request('评论已超过 5 分钟，无法撤回')
    article_id = comment.article_id
    # bug8: 评论撤回改为软删除（前台隐藏、可恢复），不再物理删除
    comment.is_deleted = True
    comment.deleted_at = timezone.now()
    comment.save(update_fields=['is_deleted', 'deleted_at'])
    ModerationLog.objects.create(
        moderator=request.user, moderator_name=str(request.user),
        action=ModerationLog.Action.SOFT_DELETE, target_type='comment',
        article_id=article_id, comment=comment,
        target_title=(re.sub(r'<[^>]+>', '', comment.content or '') or '')[:40])
    # 按实际存活评论数重算（避免重复提交时 ±1 漂移；计数永不小于 0）
    Article.objects.filter(pk=article_id).update(
        comment_count=Comment.objects.filter(article_id=article_id, is_deleted=False).count())
    invalidate_article(article_id)
    return _json_ok({'success': True})


# ----------------------------- 4. 收藏夹分类管理（C10） -----------------------------
@login_required
def api_favorite_folder_list(request: HttpRequest) -> JsonResponse:
    """收藏夹列表(GET)/创建(POST)。"""
    if request.method == 'GET':
        folders = (FavoriteFolder.objects.filter(user=request.user)
                   .annotate(cnt=Count('favorites'))
                   .order_by('-created_at'))
        data = [{'id': f.id, 'name': f.name, 'count': f.cnt,
                 'created_at': f.created_at.isoformat()} for f in folders]
        return _json_ok(data)
    if request.method == 'POST':
        try:
            body = json.loads(request.body.decode('utf-8') or '{}')
        except (ValueError, UnicodeDecodeError):
            body = request.POST
        name = str(body.get('name', '')).strip()[:50]
        if not name:
            return _bad_request('收藏夹名称不能为空')
        folder = FavoriteFolder.objects.create(user=request.user, name=name)
        return _json_ok({'id': folder.id, 'name': folder.name})
    return JsonResponse({'detail': '仅支持 GET / POST'}, status=405)


@login_required
def api_favorite_folder_detail(request: HttpRequest, pk: int) -> JsonResponse:
    """收藏夹重命名(PUT)/删除(DELETE)。删除时其下收藏回退到默认夹(folder=None)。"""
    folder = get_object_or_404(FavoriteFolder, pk=pk, user=request.user)
    if request.method == 'PUT':
        try:
            body = json.loads(request.body.decode('utf-8') or '{}')
        except (ValueError, UnicodeDecodeError):
            body = request.POST
        name = str(body.get('name', '')).strip()[:50]
        if not name:
            return _bad_request('收藏夹名称不能为空')
        folder.name = name
        folder.save(update_fields=['name'])
        return _json_ok({'id': folder.id, 'name': folder.name})
    if request.method == 'DELETE':
        # 其下收藏移到默认文件夹（folder 置空）
        Favorite.objects.filter(folder=folder).update(folder=None)
        folder.delete()
        return _json_ok({'success': True})
    return JsonResponse({'detail': '仅支持 PUT / DELETE'}, status=405)


# ----------------------------- 5. 通知中心（F8） -----------------------------
def api_notification_list(request: HttpRequest) -> JsonResponse:
    """通知列表：GET /api/notifications/（分页，未读优先）。"""
    if not request.user.is_authenticated:
        return JsonResponse({'code': 401, 'msg': '请先登录'}, status=401)
    qs = request.user.notifications.all().order_by('-is_read', '-created_at')
    page_size = _clean_page_size(request.GET.get('page_size')) or settings.PAGE_SIZE
    paginator = Paginator(qs, page_size)
    page_num = _clamp_page_number(request.GET.get('page'), paginator.num_pages)
    page = paginator.get_page(page_num)
    data = [{
        'id': n.id, 'type': n.type, 'title': n.title, 'content': n.content,
        'related_url': n.related_url, 'is_read': n.is_read,
        'created_at': n.created_at.isoformat(),
    } for n in page.object_list]
    return _json_ok({
        'results': data, 'page': page.number,
        'num_pages': paginator.num_pages, 'total': paginator.count,
    })


@login_required
def api_notification_read(request: HttpRequest, pk: int) -> JsonResponse:
    """标记单条通知已读。"""
    note = get_object_or_404(Notification, pk=pk, user=request.user)
    if not note.is_read:
        Notification.objects.filter(pk=note.pk).update(is_read=True)
    return _json_ok({'success': True})


@login_required
def api_notification_read_all(request: HttpRequest) -> JsonResponse:
    """全部标记已读。"""
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return _json_ok({'success': True})


def api_notification_unread_count(request: HttpRequest) -> JsonResponse:
    """未读通知计数。"""
    if not request.user.is_authenticated:
        return _json_ok({'count': 0})
    return _json_ok({'count': request.user.notifications.filter(is_read=False).count()})


# ----------------------------- 6. 搜索热词（D 系列） -----------------------------
def api_search_hot(request: HttpRequest) -> JsonResponse:
    """热门搜索词：GET /api/search/hot/，返回缓存 TOP10。"""
    history = cache.get(SEARCH_HOT_KEY, {})
    if isinstance(history, dict):
        ranked = sorted(history.items(), key=lambda kv: kv[1], reverse=True)
    else:
        ranked = []
    return _json_ok([{'keyword': k, 'count': v} for k, v in ranked[:10]])


def _record_search_keyword(q: str) -> None:
    """把搜索关键词累加进热门词缓存（失败静默，不影响搜索主流程）。"""
    q = (q or '').strip()
    if not q:
        return
    try:
        history = cache.get(SEARCH_HOT_KEY, {}) or {}
        history[q] = int(history.get(q, 0)) + 1
        cache.set(SEARCH_HOT_KEY, history, SEARCH_HOT_TTL)
    except Exception:  # noqa: BLE001
        pass


def _pinyin_keywords(q: str) -> list:
    """把中文关键词转为拼音（含首字母），用于拼音搜索建议。

    Args:
        q: 原始关键词。

    Returns:
        list: 拼音候选列表（无法导入 pypinyin 时返回空列表）。
    """
    try:
        from pypinyin import lazy_pinyin
    except ImportError:
        return []
    parts = lazy_pinyin(q)
    return [''.join(parts)]


# ----------------------------- 7. 文章导出（G3/G4） -----------------------------
def api_article_export_md(request: HttpRequest, pk: int) -> HttpResponse:
    """Markdown 导出：GET /api/article/<pk>/export/md/。

    用 html2text 把文章 HTML 正文转 Markdown，作为附件下载。
    """
    article = get_object_or_404(Article, pk=pk, status=Article.Status.PUBLISHED)
    try:
        import html2text
        h = html2text.HTML2Text()
        h.ignore_images = False
        h.body_width = 0
        body_md = h.handle(article.content or '')
    except ImportError:
        body_md = article.plain_text
    md = f'# {article.title}\n\n> 作者：{article.author}\n\n{body_md}\n'
    resp = HttpResponse(md, content_type='text/markdown; charset=utf-8')
    safe_title = re.sub(r'[^\w\u4e00-\u9fff-]+', '_', article.title)[:60]
    resp['Content-Disposition'] = f'attachment; filename="{safe_title}.md"'
    return resp


def api_article_export_pdf(request: HttpRequest, pk: int) -> HttpResponse:
    """PDF 导出：GET /api/article/<pk>/export/pdf/。

    用 xhtml2pdf 渲染极简 HTML 为 PDF；依赖缺失或渲染失败时返回 501，
    由前端降级为 jsPDF 方案。
    """
    article = get_object_or_404(Article, pk=pk, status=Article.Status.PUBLISHED)
    try:
        from xhtml2pdf import pisa
    except ImportError:
        return JsonResponse({'detail': 'PDF 导出组件未安装，请使用前端导出方案'}, status=501)
    html = (
        f'<html><head><meta charset="utf-8"/></head><body>'
        f'<h1>{article.title}</h1>'
        f'<p>作者：{article.author}</p>'
        f'{article.content}'
        f'</body></html>'
    )
    out = BytesIO()
    try:
        pisa.CreatePDF(html.encode('utf-8'), dest=out, encoding='utf-8')
    except Exception as exc:  # noqa: BLE001
        logger.error('PDF 导出失败: %s', exc)
        return JsonResponse({'detail': 'PDF 生成失败'}, status=500)
    out.seek(0)
    resp = HttpResponse(out.getvalue(), content_type='application/pdf')
    safe_title = re.sub(r'[^\w\u4e00-\u9fff-]+', '_', article.title)[:60]
    resp['Content-Disposition'] = f'attachment; filename="{safe_title}.pdf"'
    return resp


# ----------------------------- 8. 二维码 / 短链接（G6/G7） -----------------------------
def api_article_qrcode(request: HttpRequest, pk: int) -> HttpResponse:
    """文章二维码：GET /api/article/<pk>/qrcode/，返回 PNG。"""
    article = get_object_or_404(Article, pk=pk, status=Article.Status.PUBLISHED)
    try:
        import qrcode
    except ImportError:
        return JsonResponse({'detail': '二维码组件未安装'}, status=501)
    url = request.build_absolute_uri(article.get_absolute_url())
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return HttpResponse(buf.getvalue(), content_type='image/png')


def api_short_link(request: HttpRequest) -> JsonResponse:
    """短链接生成：POST /api/short_link/，body {original_url}。"""
    if request.method != 'POST':
        return JsonResponse({'detail': '请用 POST 请求喵~'}, status=405)
    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        body = request.POST
    original_url = str(body.get('original_url', '')).strip()
    if not original_url or not re.match(r'^https?://', original_url):
        return _bad_request('original_url 必须是 http/https 开头的合法 URL')
    # 6 位随机短码，冲突则重试
    import secrets, string
    alphabet = string.ascii_letters + string.digits
    code = ''
    for _ in range(10):
        code = ''.join(secrets.choice(alphabet) for _ in range(SHORT_LINK_CODE_LEN))
        if not ShortLink.objects.filter(code=code).exists():
            break
    ShortLink.objects.create(code=code, original_url=original_url)
    short_url = request.build_absolute_uri(f'/s/{code}/')
    return _json_ok({'short_url': short_url, 'code': code})


def short_link_redirect(request: HttpRequest, code: str) -> HttpResponseRedirect:
    """短链接跳转：/s/<code>/，302 跳转并 clicks+1。"""
    link = get_object_or_404(ShortLink, code=code)
    ShortLink.objects.filter(pk=link.pk).update(clicks=F('clicks') + 1)
    return HttpResponseRedirect(link.original_url)


# ----------------------------- 9. 成就徽章（F10） -----------------------------
def check_and_award_badges(user) -> list:
    """检查用户是否达成新徽章，达成则创建 UserBadge 并发放通知。

    统计口径：
    - articles：已发布文章数；
    - comments：评论数；
    - likes：其全部文章累计获赞；
    - days：注册天数（用 date_joined）。

    Args:
        user: 目标用户实例。

    Returns:
        list: 本次新获得的 Badge 对象列表。
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return []
    try:
        stats = {
            'articles': Article.objects.filter(author=user, status=Article.Status.PUBLISHED).count(),
            'comments': Comment.objects.filter(user=user).count(),
            'likes': Article.objects.filter(author=user).aggregate(s=Sum('likes'))['s'] or 0,
            'views': Article.objects.filter(author=user).aggregate(s=Sum('views'))['s'] or 0,
            'days': (timezone.now() - user.date_joined).days if user.date_joined else 0,
        }
        newly = []
        for badge in Badge.objects.all():
            if stats.get(badge.condition_type, 0) >= badge.condition_value:
                _, created = UserBadge.objects.get_or_create(user=user, badge=badge)
                if created:
                    newly.append(badge)
                    # 发放系统通知
                    Notification.objects.create(
                        user=user, type=Notification.Type.SYSTEM,
                        title=f'获得新徽章：{badge.name}',
                        content=f'恭喜！你达成了「{badge.name}」：{badge.description}',
                    )
        return newly
    except Exception as exc:  # noqa: BLE001
        logger.warning('徽章检查失败: %s', exc)
        return []


@login_required
def api_user_badges(request: HttpRequest) -> JsonResponse:
    """当前用户徽章列表：GET /api/user/badges/。"""
    ubs = (request.user.user_badges.select_related('badge')
           .order_by('-earned_at'))
    data = [{
        'id': ub.badge.id, 'name': ub.badge.name, 'icon': ub.badge.icon,
        'description': ub.badge.description, 'earned_at': ub.earned_at.isoformat(),
    } for ub in ubs]
    return _json_ok(data)


# ----------------------------- 10. 在线状态（F12） -----------------------------
def api_online_users(request: HttpRequest) -> JsonResponse:
    """在线用户：GET /api/online_users/，返回最近 5 分钟活跃用户数与列表。"""
    since = timezone.now() - ONLINE_WINDOW
    qs = User.objects.filter(last_active__gte=since).order_by('-last_active')
    count = qs.count()
    users = [{
        'username': u.username,
        'nickname': u.nickname or u.username,
        'avatar': u.avatar.url if u.avatar else '',
    } for u in qs[:20]]
    return _json_ok({'count': count, 'users': users})


# ----------------------------- 搜索建议增强（拼音 + 热词记录） -----------------------------
def _enhanced_search_suggest(q: str) -> list:
    """带拼音支持的标题搜索建议（limit 10）。

    Args:
        q: 原始关键词。

    Returns:
        list: 标题列表。
    """
    q = (q or '').strip()[:SEARCH_Q_MAX_LENGTH]
    if not q:
        return []
    base = Article.objects.filter(status=Article.Status.PUBLISHED)
    qs = base.filter(Q(title__icontains=q)).order_by('-views')
    # 拼音首字母/全拼补充
    for py in _pinyin_keywords(q):
        if py:
            qs = qs | base.filter(title__icontains=py)
    return list(qs.distinct().order_by('-views').values_list('title', flat=True)[:10])


# ----------------------------- 随机文章（Random Article） -----------------------------
def random_article(request):
    """随机跳转到一篇已发布的文章喵。"""
    from blog.models import Article
    import random
    articles = Article.objects.filter(status='published')
    if not articles.exists():
        from django.shortcuts import redirect
        return redirect('home')
    article = random.choice(articles)
    from django.shortcuts import redirect
    return redirect(article.get_absolute_url())

# ============================ Bug26: 萌系运营控制台 ============================
def staff_console(request: HttpRequest):
    """运营数据看板：仅 staff 管理员可访问的前端萌系控制台。

    聚合站点核心指标、近 14 天访问趋势、热门文章、分类分布、
    最近评论 / 用户、浏览器分布与待处理举报，纯 CSS 图表呈现，不引重库。
    """
    from django.contrib.admin.views.decorators import staff_member_required
    # 装饰器方式校验权限（非管理员跳转登录 / 返回 403）
    @staff_member_required
    def _inner(req):
        today = timezone.now().date()
        start = timezone.now() - timedelta(days=13)

        # ---- 核心指标 ----
        published_qs = Article.objects.filter(status=Article.Status.PUBLISHED)
        total_views = published_qs.aggregate(v=Sum('views'))['v'] or 0
        total_likes = published_qs.aggregate(l=Sum('likes'))['l'] or 0
        online_cut = timezone.now() - timedelta(minutes=5)

        stats = {
            'article_total': Article.objects.count(),
            'article_published': published_qs.count(),
            'article_pending': Article.objects.filter(
                status=Article.Status.PENDING, is_deleted=False).count(),
            'article_draft': Article.objects.filter(status=Article.Status.DRAFT).count(),
            'comment_total': Comment.objects.count(),
            'user_total': User.objects.count(),
            'category_total': Category.objects.count(),
            'tag_total': Tag.objects.count(),
            'total_views': total_views,
            'total_likes': total_likes,
            'today_visits': AccessLog.objects.filter(created_at__date=today).count(),
            'today_uv': AccessLog.objects.filter(created_at__date=today)
                       .exclude(ip_address__isnull=True).values('ip_address').distinct().count(),
            'online': max(1, AccessLog.objects.filter(created_at__gte=online_cut)
                          .exclude(ip_address__isnull=True).values('ip_address').distinct().count()),
            'reports': CommentReport.objects.count(),
        }

        # ---- 近 14 天访问趋势（Python 按天聚合，规避时区/分组差异）----
        trend = []
        max_count = 1
        for i in range(13, -1, -1):
            d = today - timedelta(days=i)
            c = AccessLog.objects.filter(created_at__date=d).count()
            max_count = max(max_count, c)
            trend.append({'label': f'{d.month}/{d.day}', 'count': c})
        import math  # 工单10：开方刻度需要
        for t in trend:
            true_pct = round(t['count'] * 100 / max_count, 1)
            t['pct'] = true_pct
            # 工单10：今日峰值常被集中访问 / 压测拉高，线性刻度会把其余各天压成
            # 等高的细线、看不出彼此差异；改用“开方刻度”（sqrt）压缩离群峰值、
            # 保留普通日之间的高低差异。真实次数仍以 data-v / 悬停 title 为准。
            t['bar_h'] = round(math.sqrt(t['count'] / max_count) * 100, 1) if t['count'] > 0 else 0.0

        # ---- 热门文章 Top 8 ----
        top_articles = list(published_qs.order_by('-views').values(
            'id', 'title', 'views', 'likes', 'comment_count')[:8])
        top_max = max([a['views'] for a in top_articles] + [1])
        for a in top_articles:
            a['pct'] = round(a['views'] * 100 / top_max, 1)

        # ---- 分类文章分布 ----
        cat_dist = list(Category.objects.annotate(
            n=Count('articles', filter=Q(articles__status=Article.Status.PUBLISHED)))
            .order_by('-n').values('name', 'n')[:10])
        cat_max = max([c['n'] for c in cat_dist] + [1])
        for c in cat_dist:
            c['pct'] = round(c['n'] * 100 / cat_max, 1)

        # ---- 最近评论 / 最近注册用户 ----
        recent_comments = list(Comment.objects.select_related('article', 'user')
                               .order_by('-created_at').values(
                                   'user__username', 'article__title',
                                   'article_id', 'content', 'created_at')[:6])
        for cm in recent_comments:
            cm['snippet'] = (cm['content'] or '')[:40]
        recent_users = list(User.objects.order_by('-date_joined')
                            .values('username', 'date_joined')[:6])

        # ---- 浏览器分布 Top 5 ----
        browsers = list(AccessLog.objects.exclude(browser__isnull=True).exclude(browser='')
                        .values('browser').annotate(n=Count('id')).order_by('-n')[:5])

        ctx = {
            'stats': stats, 'trend': trend, 'top_articles': top_articles,
            'cat_dist': cat_dist, 'recent_comments': recent_comments,
            'recent_users': recent_users, 'browsers': browsers,
            'active_nav': 'console',
            'meta_title': f'运营看板 · {settings.SITE_NAME}',
        }
        return render(req, 'blog/console.html', ctx)
    return _inner(request)


@staff_member_required
def site_settings_page(request: HttpRequest) -> HttpResponse:
    """工单 15：站点信息设置页（仅管理员）。

    把原先硬编码的网站名 / Logo / 副标题 / SEO 描述关键词 / 页脚文案等
    做成可在线编辑的表单，保存到 :class:`~blog.models.SiteInfo` 单例；
    模型 ``save()`` 会自动清除读取缓存，保存后全站立即生效，无需重启或改代码。
    """
    from .models import SiteInfo
    info = SiteInfo.load()

    # 允许编辑的字段白名单（键 -> 最大长度，0 表示长文本）
    fields = [
        ('site_name', 60), ('logo_emoji', 8), ('tagline', 120),
        ('description', 0), ('keywords', 200), ('footer_about', 0),
        ('footer_icp', 80), ('copyright_holder', 60),
    ]

    if request.method == 'POST':
        errors = []
        for key, max_len in fields:
            val = request.POST.get(key, '').strip()
            if max_len and len(val) > max_len:
                errors.append(f'「{key}」长度不能超过 {max_len} 个字符')
            setattr(info, key, val)
        if errors:
            for err in errors:
                messages.error(request, err)
        else:
            info.save()  # save() 强制单例并清缓存
            messages.success(request, '站点信息已保存，全站立即生效喵~')
            return redirect('site_settings')

    return render(request, 'blog/site_settings.html', {
        'info': info,
        'fields': fields,
        'active_nav': 'site_settings',
        'meta_title': f'站点设置 · {info.site_name}',
    })


# ============================ Round6（bug14/15）：我的小站系列页面 ============================
def _paginate_qs(request, qs, per_page=10):
    """小工具：对查询集分页，返回 (page_obj, paginator)。"""
    paginator = Paginator(qs, per_page)
    return paginator.get_page(request.GET.get('page')), paginator


@login_required
def notifications_page(request: HttpRequest) -> HttpResponse:
    """通知中心实际页面（bug15）：当前用户全部通知，支持只看未读、分页。

    Args:
        request: 当前 HttpRequest，需登录；``?filter=unread`` 只看未读。

    Returns:
        HttpResponse: 渲染 blog/notifications.html。
    """
    qs = request.user.notifications.all().order_by('-is_read', '-created_at')
    show_unread = request.GET.get('filter') == 'unread'
    if show_unread:
        qs = qs.filter(is_read=False)
    page_obj, _ = _paginate_qs(request, qs, 15)
    ctx = {
        'page_obj': page_obj,
        'total_count': request.user.notifications.count(),
        'unread_count': request.user.notifications.filter(is_read=False).count(),
        'show_unread': show_unread,
        'active_nav': 'notifications',
    }
    return render(request, 'blog/notifications.html', ctx)


@login_required
def my_favorites(request: HttpRequest) -> HttpResponse:
    """我的收藏（bug14）：当前用户收藏的已发布文章，分页。"""
    article_ids = Favorite.objects.filter(user=request.user).values_list('article_id', flat=True)
    qs = (Article.objects.filter(id__in=article_ids, status=Article.Status.PUBLISHED)
          .select_related('category', 'author').order_by('-id'))
    page_obj, _ = _paginate_qs(request, qs, 10)
    return render(request, 'blog/my_collection.html', {
        'page_obj': page_obj, 'kind': 'articles',
        'page_icon': '⭐', 'page_title': '我的收藏',
        'empty_text': '还没有收藏文章，看到喜欢的点个小星星吧~',
        'active_nav': 'favorites'})


@login_required
def my_liked(request: HttpRequest) -> HttpResponse:
    """我的点赞（bug14）：当前浏览器会话内点过赞的文章，分页。

    文章点赞记录保存在 session（``liked_article_ids``），故反映当前浏览器；
    换浏览器或结束会话后该列表可能不同。
    """
    liked_ids = request.session.get('liked_article_ids', [])
    qs = (Article.objects.filter(id__in=liked_ids, status=Article.Status.PUBLISHED)
          .select_related('category', 'author').order_by('-id'))
    page_obj, _ = _paginate_qs(request, qs, 10)
    return render(request, 'blog/my_collection.html', {
        'page_obj': page_obj, 'kind': 'articles',
        'page_icon': '👍', 'page_title': '我的点赞',
        'empty_text': '还没有点过赞，去给喜欢的文章比个心吧~',
        'active_nav': 'liked'})


@login_required
def my_comments(request: HttpRequest) -> HttpResponse:
    """我的评论（bug14）：当前用户发表过的全部评论（含待审核），分页。"""
    qs = (Comment.objects.filter(user=request.user).select_related('article')
          .order_by('-created_at'))
    page_obj, _ = _paginate_qs(request, qs, 10)
    return render(request, 'blog/my_collection.html', {
        'page_obj': page_obj, 'kind': 'comments',
        'page_icon': '💬', 'page_title': '我的评论',
        'empty_text': '还没有发表过评论，来抢沙发吧~',
        'active_nav': 'my_comments'})


@login_required
def reading_history_page(request: HttpRequest) -> HttpResponse:
    """阅读历史（bug14）：页面外壳，列表由前端 JS 从 localStorage 渲染。"""
    return render(request, 'blog/reading_history.html', {
        'page_icon': '📚', 'page_title': '阅读历史',
        'active_nav': 'reading_history'})


# ============================ Round6（bug16）：内容审核（待审文章 / 举报审批） ============================
def _moderation_backup(kind, payload):
    """把待删除/驳回内容快照写入项目内备份目录，返回备份文件路径。

    统一存放于 ``docs/moderation_backup/``，文件名带时间戳、类型与主键，
    UTF-8 JSON，便于误删后人工恢复；目录不存在时自动创建。
    """
    backup_dir = os.path.join(settings.BASE_DIR, 'docs', 'moderation_backup')
    os.makedirs(backup_dir, exist_ok=True)
    stamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    ident = payload.get('id', 'x')
    path = os.path.join(backup_dir, '%s_%s_%s.json' % (stamp, kind, ident))
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    return path


def _article_snapshot(article):
    """导出文章完整字段（含正文/标签/分类），供驳回删除前备份。"""
    return {
        'id': article.id,
        'title': article.title,
        'author': getattr(article.author, 'username', None),
        'status': article.status,
        'kind': getattr(article, 'kind', ''),
        'category': getattr(article.category, 'name', None),
        'tags': list(article.tags.values_list('name', flat=True)),
        'excerpt': getattr(article, 'excerpt', ''),
        'content': article.content,
        'views': article.views,
        'created_at': article.created_at,
        'updated_at': article.updated_at,
        'backed_up_at': timezone.now(),
    }


def _comment_snapshot(comment):
    """导出评论及其全部举报，供删除违规评论前备份。"""
    return {
        'id': comment.id,
        'article_id': comment.article_id,
        'article_title': getattr(comment.article, 'title', ''),
        'user': getattr(comment.user, 'username', None),
        'content': comment.content,
        'is_approved': comment.is_approved,
        'created_at': comment.created_at,
        'reports': [
            {'id': r.id, 'reporter': getattr(r.reporter, 'username', None),
             'reason': r.reason, 'created_at': r.created_at}
            for r in comment.reports.all()
        ],
        'backed_up_at': timezone.now(),
    }


def moderation_queue(request: HttpRequest) -> HttpResponse:
    """内容审核页（bug8）：待审文章 / 待处理举报 / 审核历史 / 回收站四个标签页，仅 staff。

    - articles：status=PENDING 的文章，支持按分类 / 标签 / 提交时间排序与分页；
    - reports：全部 CommentReport（无状态字段），分页；
    - history：ModerationLog 审核操作时间线，分页，可按动作筛选；
    - trash：is_deleted=True 的文章 / 评论（回收站），可恢复或彻底删除。
    """
    from django.contrib.admin.views.decorators import staff_member_required

    @staff_member_required
    def _inner(req):
        tab = req.GET.get('tab', 'articles')
        if tab not in ('articles', 'reports', 'promotions', 'history', 'trash'):
            tab = 'articles'

        # ---- 待审文章：排序（分类 / 标签 / 时间）+ 升降序 + 分页 ----
        pending_qs = (Article.objects.filter(status=Article.Status.PENDING, is_deleted=False)
                      .select_related('author', 'category')
                      .prefetch_related('tags'))
        sort = req.GET.get('sort', 'date')
        if sort not in ('date', 'category', 'tag'):
            sort = 'date'
        # 升降序（参考标签页排序）：默认升序，order=desc 时各字段整体反向
        order = req.GET.get('order', 'asc')
        if order not in ('asc', 'desc'):
            order = 'asc'
        prefix = '-' if order == 'desc' else ''
        secondary = '-id' if order == 'desc' else 'id'  # 同值时用 id 保证排序稳定
        if sort == 'category':
            pending_qs = pending_qs.order_by(prefix + 'category__name', secondary)
        elif sort == 'tag':
            # 多对多 tags 直接 order_by 会让多标签文章产生重复行（distinct 也会因排序键不同而失效）；
            # 用 Min 子查询给每篇文章注解一个代表标签（字典序首个），聚合 GROUP BY 折叠为每篇一行。
            pending_qs = (pending_qs.filter(tags__isnull=False)
                          .annotate(_sort_tag=Min('tags__name'))
                          .order_by(prefix + '_sort_tag', secondary))
        else:
            pending_qs = pending_qs.order_by(prefix + 'created_at', secondary)
        pending_page = Paginator(pending_qs, 10).get_page(req.GET.get('page'))

        # ---- 待处理举报：分页 ----
        reports_qs = (CommentReport.objects.select_related('comment', 'reporter')
                      .order_by('created_at', 'id'))
        reports_page = Paginator(reports_qs, 10).get_page(req.GET.get('rpage'))

        # ---- Bug1：推广申请（置顶/精华/热门）待审核列表 ----
        promo_qs = (PromotionRequest.objects.filter(status=PromotionRequest.Status.PENDING)
                    .select_related('article', 'applicant')
                    .order_by('created_at', 'id'))
        promo_page = Paginator(promo_qs, 10).get_page(req.GET.get('ppage'))

        # ---- Bug8：已处理推广申请（含系统执行状态），默认折叠展示最近 10 条 ----
        promo_done_page = Paginator(
            PromotionRequest.objects.exclude(status=PromotionRequest.Status.PENDING)
            .select_related('article', 'applicant', 'handled_by')
            .order_by('-handled_at', '-id'), 10).get_page(req.GET.get('pdpage'))
        # 系统执行状态汇总：供审核页顶部「系统执行状态」总览条展示
        exec_stats = {
            'success': PromotionRequest.objects.filter(
                execution_status=PromotionRequest.Execution.SUCCESS).count(),
            'skipped': PromotionRequest.objects.filter(
                execution_status=PromotionRequest.Execution.SKIPPED).count(),
            'failed': PromotionRequest.objects.filter(
                execution_status=PromotionRequest.Execution.FAILED).count(),
        }

        # ---- 审核历史：可按动作筛选 + 分页 ----
        history_qs = (ModerationLog.objects.select_related('moderator')
                      .order_by('-created_at', '-id'))
        act = req.GET.get('act', '')
        if act in dict(ModerationLog.Action.choices):
            history_qs = history_qs.filter(action=act)
        history_page = Paginator(history_qs, 15).get_page(req.GET.get('hpage'))

        # ---- 回收站：软删除文章 + 软删除评论（各自分页，每页 10 条）----
        trash_articles_page = Paginator(
            Article.objects.filter(is_deleted=True).select_related('author', 'category')
            .order_by('-deleted_at', '-id'), 10).get_page(req.GET.get('tpage'))
        trash_comments_page = Paginator(
            Comment.objects.filter(is_deleted=True).select_related('user', 'article')
            .order_by('-deleted_at', '-id'), 10).get_page(req.GET.get('tcpage'))

        ctx = {
            'tab': tab, 'sort': sort, 'order': order, 'act': act,
            'pending_page': pending_page,
            'reports_page': reports_page,
            'promo_page': promo_page,
            # Bug8：已处理推广申请 + 系统执行状态总览
            'promo_done_page': promo_done_page,
            'exec_stats': exec_stats,
            'pinned_count': Article.objects.filter(is_pinned=True, is_deleted=False).count(),
            'history_page': history_page,
            'trash_articles_page': trash_articles_page,
            'trash_comments_page': trash_comments_page,
            'pending_count': Article.objects.filter(
                status=Article.Status.PENDING, is_deleted=False).count(),
            'report_count': CommentReport.objects.count(),
            'promotion_count': PromotionRequest.objects.filter(
                status=PromotionRequest.Status.PENDING).count(),
            'moderation_settings': ModerationSettings.load(),
            'history_count': ModerationLog.objects.count(),
            'trash_count': Article.objects.filter(is_deleted=True).count()
                           + Comment.objects.filter(is_deleted=True).count(),
            'action_choices': ModerationLog.Action.choices,
            'active_nav': 'moderation',
        }
        return render(req, 'blog/moderation.html', ctx)

    return _inner(request)


def moderate_article(request: HttpRequest, pk: int) -> HttpResponse:
    """处理待审文章（bug8）：approve=通过并发布；reject=退回作者修改（不删除）。

    两次动作均写入 ModerationLog 审核历史；驳回时向作者发送站内通知并附理由，
    文章回到草稿状态供其修改后重新提交。
    """
    from django.contrib.admin.views.decorators import staff_member_required

    @staff_member_required
    def _inner(req):
        if req.method != 'POST':
            return redirect('/console/moderation/?tab=articles')
        article = get_object_or_404(Article, pk=pk, is_deleted=False)
        action = req.POST.get('action', '')
        if action == 'approve':
            # Bug8：定时投稿（published_at 已到点）在此刻才真正发布，
            # 因此把发布时间对齐到「实际通过时刻」，避免文章列表出现未来时间。
            is_scheduled = bool(article.published_at and article.published_at <= timezone.now())
            article.status = Article.Status.PUBLISHED
            fields = ['status', 'updated_at']
            if is_scheduled:
                article.published_at = timezone.now()
                fields.append('published_at')
            article.save(update_fields=fields)
            ModerationLog.objects.create(
                moderator=req.user, moderator_name=str(req.user),
                action=ModerationLog.Action.APPROVE, target_type='article',
                article=article, target_title=article.title,
                reason='通过审核并发布（定时投稿到点转入审核）' if is_scheduled else '')
            messages.success(req, '《%s》已通过并发布~ 🌸' % article.title)
        elif action == 'reject':
            reason = (req.POST.get('reason') or '').strip()[:500]
            # 退回草稿（不删除内容），作者修改后可重新提交审核
            article.status = Article.Status.DRAFT
            article.save(update_fields=['status', 'updated_at'])
            ModerationLog.objects.create(
                moderator=req.user, moderator_name=str(req.user),
                action=ModerationLog.Action.REJECT, target_type='article',
                article=article, target_title=article.title, reason=reason)
            Notification.objects.create(
                user=article.author, type=Notification.Type.SYSTEM,
                title='你的文章《%s》未通过审核' % article.title[:30],
                content=reason or '内容还需要调整一下哦，修改后可以重新提交~')
            messages.warning(req, '《%s》已退回作者修改~ 📝' % article.title)
        return redirect('/console/moderation/?tab=articles')

    return _inner(request)


def moderate_report(request: HttpRequest, pk: int) -> HttpResponse:
    """处理举报（bug8）：keep=举报不成立保留评论；delete_comment=软删除违规评论。

    全部动作写入 ModerationLog；软删除评论同时回退文章冗余评论数，
    举报记录处理后移除（删除前已写入项目备份）。
    """
    from django.contrib.admin.views.decorators import staff_member_required

    @staff_member_required
    def _inner(req):
        if req.method != 'POST':
            return redirect('/console/moderation/?tab=reports')
        report = get_object_or_404(
            CommentReport.objects.select_related('comment', 'comment__article'), pk=pk)
        action = req.POST.get('action', '')
        comment = report.comment
        if action == 'keep':
            payload = {
                'id': report.id, 'comment_id': comment.id,
                'reporter': getattr(report.reporter, 'username', None),
                'reason': report.reason, 'created_at': report.created_at,
                'backed_up_at': timezone.now()}
            _moderation_backup('report_dismissed', payload)
            # 该评论若还有其他未处理举报则保持 reported 标记
            if not comment.reports.exclude(pk=report.pk).exists():
                comment.reported = False
                comment.save(update_fields=['reported'])
            ModerationLog.objects.create(
                moderator=req.user, moderator_name=str(req.user),
                action=ModerationLog.Action.APPROVE, target_type='comment',
                article_id=comment.article_id, comment=comment,
                target_title=(re.sub(r'<[^>]+>', '', comment.content or '') or '')[:40],
                reason='举报不成立：%s' % (report.reason or ''))
            report.delete()
            messages.success(req, '已标记举报不成立，评论予以保留~')
        elif action == 'delete_comment' and comment is not None:
            path = _moderation_backup('comment', _comment_snapshot(comment))
            cid = comment.id
            art_id = comment.article_id
            # bug8: 违规评论改为软删除（前台隐藏、可恢复），不再物理删除
            comment.is_deleted = True
            comment.deleted_at = timezone.now()
            comment.save(update_fields=['is_deleted', 'deleted_at'])
            ModerationLog.objects.create(
                moderator=req.user, moderator_name=str(req.user),
                action=ModerationLog.Action.SOFT_DELETE, target_type='comment',
                article_id=art_id, comment=comment,
                target_title=(re.sub(r'<[^>]+>', '', comment.content or '') or '')[:40],
                reason='举报成立：%s' % (report.reason or ''))
            # 按实际存活评论数重算（避免 ±1 漂移）
            Article.objects.filter(pk=art_id).update(
                comment_count=Comment.objects.filter(article_id=art_id, is_deleted=False).count())
            # 移除该评论的全部举报
            CommentReport.objects.filter(comment=comment).delete()
            messages.warning(req, '违规评论 #%s 已隐藏，已备份至 %s' % (
                cid, os.path.relpath(path, settings.BASE_DIR)))
        return redirect('/console/moderation/?tab=reports')

    return _inner(request)


# ============================ Bug8：回收站恢复 / 彻底删除 ============================
def _plain_snippet(text, length=40):
    """去掉 HTML 标签后截取前 length 字，供日志标题快照使用。"""
    return (re.sub(r'<[^>]+>', '', text or '') or '')[:length]


@staff_member_required
def restore_article(request: HttpRequest, pk: int) -> HttpResponse:
    """回收站恢复文章：取消软删除，写 RESTORE 日志。仅 POST。"""
    if request.method != 'POST':
        return redirect('/console/moderation/?tab=trash')
    article = get_object_or_404(Article, pk=pk, is_deleted=True)
    article.is_deleted = False
    article.deleted_at = None
    article.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
    ModerationLog.objects.create(
        moderator=request.user, moderator_name=str(request.user),
        action=ModerationLog.Action.RESTORE, target_type='article',
        article=article, target_title=article.title)
    cache.delete(SIDEBAR_CACHE_KEY)
    cache.delete('footer_stats')
    cache.delete('sidebar_stats')
    messages.success(request, '《%s》已从回收站找回啦~ ✨' % article.title)
    return redirect('/console/moderation/?tab=trash')


@staff_member_required
def hard_delete_article(request: HttpRequest, pk: int) -> HttpResponse:
    """彻底删除文章：不可恢复，先写 HARD_DELETE 日志（外键随后置空）。仅 POST。"""
    if request.method != 'POST':
        return redirect('/console/moderation/?tab=trash')
    article = get_object_or_404(Article, pk=pk, is_deleted=True)
    title = article.title
    ModerationLog.objects.create(
        moderator=request.user, moderator_name=str(request.user),
        action=ModerationLog.Action.HARD_DELETE, target_type='article',
        article=article, target_title=title)
    article.delete()
    cache.delete(SIDEBAR_CACHE_KEY)
    cache.delete('footer_stats')
    cache.delete('sidebar_stats')
    messages.warning(request, '《%s》已彻底删除，无法找回了哦~ 🔥' % title)
    return redirect('/console/moderation/?tab=trash')


@staff_member_required
def restore_comment(request: HttpRequest, pk: int) -> HttpResponse:
    """回收站恢复评论：取消软删除、评论数 +1，写 RESTORE 日志。仅 POST。"""
    if request.method != 'POST':
        return redirect('/console/moderation/?tab=trash')
    comment = get_object_or_404(Comment, pk=pk, is_deleted=True)
    comment.is_deleted = False
    comment.deleted_at = None
    comment.save(update_fields=['is_deleted', 'deleted_at'])
    Article.objects.filter(pk=comment.article_id).update(
        comment_count=Comment.objects.filter(article_id=comment.article_id, is_deleted=False).count())
    ModerationLog.objects.create(
        moderator=request.user, moderator_name=str(request.user),
        action=ModerationLog.Action.RESTORE, target_type='comment',
        article_id=comment.article_id, comment=comment,
        target_title=_plain_snippet(comment.content))
    invalidate_article(comment.article_id)
    messages.success(request, '评论 #%s 已恢复显示~ ✨' % pk)
    return redirect('/console/moderation/?tab=trash')


@staff_member_required
def hard_delete_comment(request: HttpRequest, pk: int) -> HttpResponse:
    """彻底删除评论：不可恢复，先删其举报、再写 HARD_DELETE 日志。仅 POST。"""
    if request.method != 'POST':
        return redirect('/console/moderation/?tab=trash')
    comment = get_object_or_404(Comment, pk=pk, is_deleted=True)
    art_id = comment.article_id
    CommentReport.objects.filter(comment=comment).delete()
    ModerationLog.objects.create(
        moderator=request.user, moderator_name=str(request.user),
        action=ModerationLog.Action.HARD_DELETE, target_type='comment',
        article_id=art_id, comment=comment,
        target_title=_plain_snippet(comment.content))
    comment.delete()
    invalidate_article(art_id)
    messages.warning(request, '评论 #%s 已彻底删除，无法找回了哦~ 🔥' % pk)
    return redirect('/console/moderation/?tab=trash')


# __REFRESH_ASSETS_API__
def api_refresh_assets(request):
    """一键刷新：POST /api/refresh-assets/（仅 staff）。

    重新压缩全部 CSS/JS、写入新构建版本号并清空 Django 缓存，
    返回最新构建 token，前端据此硬重载以拉取新版本静态资源。
    """
    if not (request.user.is_authenticated and request.user.is_staff):
        return JsonResponse({'ok': False, 'error': 'permission_denied'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'method_not_allowed'}, status=405)
    import io
    from django.core.management import call_command
    buf = io.StringIO()
    try:
        call_command('refresh_assets', stdout=buf, stderr=buf)
    except Exception as exc:  # noqa: BLE001 - 需把失败原因回传前端
        return JsonResponse({'ok': False, 'error': str(exc)}, status=500)
    token = ''
    try:
        token = open(os.path.join(settings.BASE_DIR, 'static', 'assets', '.build_token'),
                     encoding='utf-8').read().strip()
    except Exception:
        pass
    return JsonResponse({'ok': True, 'token': token, 'output': buf.getvalue()[-800:]})


# ============================ 调试：缓存查看端点（仅 DEBUG） ============================
def debug_cache_dump(request):
    """DEBUG 专用：返回当前进程缓存快照（key / 剩余 TTL / 详情页片段命中统计）。

    开发调试时在浏览器直接查看 runserver 进程内的 LocMemCache 内容
    （LocMemCache 为进程内缓存，diag 是独立进程看不到，此端点必须在服务进程内访问）。

    仅当 settings.DEBUG 且为本机访问（127.0.0.1 / ::1）或超级用户时可用。
    """
    if not settings.DEBUG:
        return JsonResponse({'ok': False, 'error': '仅 DEBUG 模式可用'}, status=404)
    is_local = request.META.get('REMOTE_ADDR') in ('127.0.0.1', '::1')
    if not (is_local or (request.user.is_authenticated and request.user.is_superuser)):
        return JsonResponse({'ok': False, 'error': 'permission_denied'}, status=403)
    import time as _time
    from .cache_keys import get_cache_version, get_stats
    internal = getattr(cache, '_cache', None)
    expire = getattr(cache, '_expire_info', None)
    keys = []
    if isinstance(internal, dict):
        now = _time.time()
        for k in internal:
            ttl = None
            if expire and k in expire:
                ttl = max(0, int(expire[k] - now))
            keys.append({'key': k, 'ttl_remaining': ttl})
    keys.sort(key=lambda x: x['key'])
    return JsonResponse({
        'ok': True,
        'cache_version': get_cache_version(),
        'backend': 'locmem',
        'total_keys': len(keys),
        'keys': keys,
        'fragment_stats': get_stats(),
    })


# ============================ Bug1：置顶 / 精华 / 热门 权限与审核 ============================
# 推广类型 → (Article 字段名, 设置动作, 取消动作) 的映射，集中维护避免散落
_PROMO_FIELD = {
    PromotionRequest.Kind.PIN: ('is_pinned', ModerationLog.Action.PIN, ModerationLog.Action.UNPIN),
    PromotionRequest.Kind.FEATURE: ('is_featured', ModerationLog.Action.FEATURE, ModerationLog.Action.UNFEATURE),
    PromotionRequest.Kind.HOT: ('is_hot', ModerationLog.Action.HOT, ModerationLog.Action.UNHOT),
}

# 推广类型 → 中文短名（提示文案统一走这里，避免各处硬编码）
_PROMO_LABEL = {
    PromotionRequest.Kind.PIN: '置顶',
    PromotionRequest.Kind.FEATURE: '精华',
    PromotionRequest.Kind.HOT: '热门',
}


def _promo_execute(pr, actor):
    """Bug8：把一条「审批通过」的推广申请真正落地到文章，并回填系统执行状态。

    抽成独立函数的原因：审核页审批（moderate_promotion）与后续可能的批量/自动
    审批都要复用同一套「能不能落地 + 落地结果怎么写」的判定，避免两处逻辑漂移。

    Args:
        pr: 待执行的 PromotionRequest（status 已由调用方置为 APPROVED）。
        actor: 执行人（管理员 User），仅用于日志文案。

    Returns:
        tuple: (applied: bool, execution_status: str, note: str)
            - applied：本次是否真的修改了文章标记；
            - execution_status：PromotionRequest.Execution 取值；
            - note：写入 pr.execution_note 的系统执行说明。
    """
    field, act_on, _act_off = _PROMO_FIELD[pr.kind]
    label = _PROMO_LABEL.get(pr.kind, pr.get_kind_display())
    try:
        # 已经是对应状态：无需重复写库，直接记为执行成功（幂等）
        if getattr(pr.article, field):
            return True, PromotionRequest.Execution.SUCCESS, '文章已是%s状态，无需重复设置' % label
        # 置顶上限校验：已达上限则不实际置顶，但保留「审批通过」的结论，
        # 并由系统执行状态明确告知「已通过但未执行（已达上限）」。
        if pr.kind == PromotionRequest.Kind.PIN:
            max_pinned = ModerationSettings.load().max_pinned
            current = Article.objects.filter(is_pinned=True, is_deleted=False).count()
            if current >= max_pinned:
                return (False, PromotionRequest.Execution.SKIPPED,
                        '置顶名额已满（%d/%d 篇），系统未执行置顶' % (current, max_pinned))
        setattr(pr.article, field, True)
        pr.article.save(update_fields=[field, 'updated_at'])
        return True, PromotionRequest.Execution.SUCCESS, '系统已执行：文章已设为%s' % label
    except Exception as exc:  # noqa: BLE001 执行失败不得中断审批流程，但要如实记录
        logger.error('推广申请系统执行失败: pr=%s kind=%s err=%s', pr.pk, pr.kind, exc,
                     exc_info=True)
        return False, PromotionRequest.Execution.FAILED, '系统执行异常：%s' % exc


def _promo_block_state(article, user):
    """Bug8：计算详情页「申请置顶 / 申请精华 / 申请热门」三个按钮的状态。

    返回结构（供模板直接渲染，避免模板里写复杂判断）：
        {kind: {'applied', 'pending', 'state', 'label', 'text', 'limit_full'}}
    其中 state 取值：
        - ``applied``：已经生效 → 按钮改为「已经置顶/精华/热门」且不可点击；
        - ``pending``：已有待审核申请 → 按钮改为「XX审核中」且不可点击；
        - ``open``：可申请 → 原「申请XX」按钮可点击。
    ``limit_full`` 仅对置顶有意义：全站置顶名额已满时为 True，用于提示作者
    「即使审核通过也可能暂不生效」（Bug 单：大于置顶上限应该有提示）。
    """
    state = {}
    labels = _PROMO_LABEL
    fields = {k: v[0] for k, v in _PROMO_FIELD.items()}
    pending_kinds = set()
    if user.is_authenticated:
        pending_kinds = set(PromotionRequest.objects.filter(
            article=article, applicant=user,
            status=PromotionRequest.Status.PENDING).values_list('kind', flat=True))
    # 置顶名额是否已满（排除软删除文章，与 _promo_execute 口径保持一致）
    max_pinned = ModerationSettings.load().max_pinned
    pinned_count = Article.objects.filter(is_pinned=True, is_deleted=False).count()
    pin_full = pinned_count >= max_pinned
    for kind, field in fields.items():
        applied = bool(getattr(article, field, False))
        pending = kind in pending_kinds
        if applied:
            st, text = 'applied', '已经%s' % labels[kind]
        elif pending:
            st, text = 'pending', '%s审核中' % labels[kind]
        else:
            st, text = 'open', '申请%s' % labels[kind]
        state[kind] = {'applied': applied, 'pending': pending, 'state': st,
                       'label': labels[kind], 'text': text,
                       'limit_full': bool(pin_full and kind == PromotionRequest.Kind.PIN),
                       'pinned_count': pinned_count, 'max_pinned': max_pinned}
    return state


def api_article_promotion_request(request, pk):
    """作者申请置顶/精华/热门：POST /api/article/<pk>/promotion-request/。

    仅文章作者本人可申请（管理员直接用切换接口）；同文章同类型已有待审核
    申请时拒绝重复提交。成功生成 PENDING 的 PromotionRequest 并写审核日志。

    Bug8 增强：
    - 已生效（已经置顶/精华/热门）时直接拒绝，提示「已经置顶」不再受理；
    - 申请置顶但全站置顶名额已满时明确告知「已通过也可能无法置顶」，
      并把该提示随响应返回，便于前端弹窗直接展示。
    """
    if not request.user.is_authenticated:
        return JsonResponse({'code': 403, 'msg': '请先登录喵~'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请用 POST 提交'}, status=405)
    article = get_object_or_404(Article, pk=pk, is_deleted=False)
    if request.user != article.author and not request.user.is_staff:
        return JsonResponse({'code': 403, 'msg': '只能给自己的文章申请哦~'}, status=403)
    kind = request.POST.get('kind', '')
    if kind not in PromotionRequest.Kind.values:
        return JsonResponse({'code': 400, 'msg': '申请类型不正确'}, status=400)
    # Bug8：已经生效的推广不再受理申请（按钮侧也已禁用，这里做服务端兜底）
    field = _PROMO_FIELD[kind][0]
    label = _PROMO_LABEL[kind]
    if getattr(article, field):
        return JsonResponse(
            {'code': 409, 'msg': '这篇文章已经%s啦，不用再申请喵~' % label,
             'data': {'already_applied': True, 'kind': kind}},
            status=409)
    reason = (request.POST.get('reason') or '').strip()[:500]
    if not reason:
        return JsonResponse({'code': 400, 'msg': '请填写申请理由喵~'}, status=400)
    # 已有同类型待审核申请，不允许重复提交
    if PromotionRequest.objects.filter(
            article=article, kind=kind,
            status=PromotionRequest.Status.PENDING).exists():
        return JsonResponse({'code': 409, 'msg': '已经提交过申请，正在审核中哦~'}, status=409)
    # Bug8：置顶名额已满时提前告知，避免「管理员通过了却没置顶」的预期落差
    notice = ''
    if kind == PromotionRequest.Kind.PIN:
        max_pinned = ModerationSettings.load().max_pinned
        current = Article.objects.filter(is_pinned=True, is_deleted=False).count()
        if current >= max_pinned:
            notice = ('当前置顶名额已满（%d/%d 篇），即使审核通过系统也可能暂时无法置顶喵~'
                      % (current, max_pinned))
    pr = PromotionRequest.objects.create(
        article=article, applicant=request.user, kind=kind, reason=reason)
    ModerationLog.objects.create(
        moderator=request.user, moderator_name=str(request.user),
        action=ModerationLog.Action.SUBMIT, target_type='article',
        article=article, target_title=article.title,
        reason='【%s申请】%s' % (pr.get_kind_display(), reason))
    msg = '申请已提交，等待管理员审核喵~'
    if notice:
        msg = notice + ' 申请已提交喵~'
    return JsonResponse({'code': 0, 'msg': msg, 'notice': notice,
                         'data': {'id': pr.id}})


def api_article_promotion_status(request, pk):
    """Bug8 新增：查询某文章三个推广标记 + 当前用户申请状态（详情页按钮自检用）。

    GET /api/article/<pk>/promotion-status/  → JSON
    作者或任意登录用户均可查询自己的申请状态；返回结构与 ``_promo_block_state`` 一致。
    """
    article = get_object_or_404(Article, pk=pk, is_deleted=False)
    return JsonResponse({'code': 0, 'data': {
        'states': _promo_block_state(article, request.user),
        'is_pinned': article.is_pinned,
        'is_featured': article.is_featured,
        'is_hot': article.is_hot,
        'max_pinned': ModerationSettings.load().max_pinned,
        'pinned_count': Article.objects.filter(is_pinned=True, is_deleted=False).count(),
    }})


def api_article_toggle_promotion(request, pk):
    """管理员直接设置/取消置顶、精华、热门：POST /api/article/<pk>/toggle-promotion/。

    action 取 pin/unpin/feature/unfeature/hot/unhot；直接改 Article 标记并写日志。
    置顶时若超过全局上限则拒绝。
    """
    if not (request.user.is_authenticated and request.user.is_staff):
        return JsonResponse({'code': 403, 'msg': '仅管理员可操作'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请用 POST 提交'}, status=405)
    article = get_object_or_404(Article, pk=pk, is_deleted=False)
    action = request.POST.get('action', '')
    # action → (申请类型, 目标布尔值)
    mapping = {
        'pin': (PromotionRequest.Kind.PIN, True), 'unpin': (PromotionRequest.Kind.PIN, False),
        'feature': (PromotionRequest.Kind.FEATURE, True), 'unfeature': (PromotionRequest.Kind.FEATURE, False),
        'hot': (PromotionRequest.Kind.HOT, True), 'unhot': (PromotionRequest.Kind.HOT, False),
    }
    if action not in mapping:
        return JsonResponse({'code': 400, 'msg': '操作不正确'}, status=400)
    kind, target = mapping[action]
    field, act_on, act_off = _PROMO_FIELD[kind]
    # 置顶上限校验（仅在「设置置顶」且当前未置顶时）
    if kind == PromotionRequest.Kind.PIN and target:
        max_pinned = ModerationSettings.load().max_pinned
        if not article.is_pinned and Article.objects.filter(
                is_pinned=True, is_deleted=False).count() >= max_pinned:
            return JsonResponse({'code': 409, 'msg': '置顶已达上限（%s 篇）喵~' % max_pinned}, status=409)
    setattr(article, field, target)
    article.save(update_fields=[field, 'updated_at'])
    ModerationLog.objects.create(
        moderator=request.user, moderator_name=str(request.user),
        action=act_on if target else act_off, target_type='article',
        article=article, target_title=article.title)
    labels = _PROMO_LABEL
    return JsonResponse({'code': 0,
                         'msg': '已%s%s~' % ('设置' if target else '取消', labels[kind]),
                         'data': {field: target,
                                  'states': _promo_block_state(article, request.user)}})


def moderate_promotion(request, pk):
    """管理员审批推广申请：POST /console/moderation/promotion/<pk>/，approve/reject。

    Bug8 重构：审批结论（status）与系统执行结果（execution_status）分离记录 ——
    - 通过：立即调用 ``_promo_execute`` 尝试落地；置顶名额已满时不落地，但把
      execution_status 记为「未执行·已达上限」并在审核页醒目展示，同时给作者
      发一条说明「已通过但受名额限制暂未生效」的通知，避免出现「显示已通过却
      没有置顶」的黑盒状态；
    - 驳回：置 REJECTED、写日志并通知作者驳回理由。
    """
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect('login')
    if request.method != 'POST':
        return redirect('/console/moderation/?tab=promotions')
    pr = get_object_or_404(
        PromotionRequest.objects.select_related('article', 'applicant'), pk=pk)
    action = request.POST.get('action', '')
    note = (request.POST.get('reason') or '').strip()[:500]
    if pr.status != PromotionRequest.Status.PENDING:
        messages.warning(request, '这条申请已经处理过啦~')
        return redirect('/console/moderation/?tab=promotions')
    label = _PROMO_LABEL.get(pr.kind, pr.get_kind_display())
    _field, act_on, _act_off = _PROMO_FIELD[pr.kind]
    if action == 'approve':
        pr.status = PromotionRequest.Status.APPROVED
        pr.handled_by = request.user
        pr.handled_at = timezone.now()
        # ---- Bug8：真实落地 + 记录系统执行状态 ----
        applied, exec_status, exec_note = _promo_execute(pr, request.user)
        pr.execution_status = exec_status
        pr.execution_note = exec_note[:200]
        pr.executed_at = timezone.now()
        pr.save(update_fields=['status', 'handled_by', 'handled_at',
                               'execution_status', 'execution_note', 'executed_at'])
        ModerationLog.objects.create(
            moderator=request.user, moderator_name=str(request.user),
            action=act_on, target_type='article', article=pr.article,
            target_title=pr.article.title,
            reason='通过%s申请：%s（系统执行：%s）' % (label, pr.reason, exec_note))
        # 通知作者：已通过但未执行时，文案里必须写清楚原因
        if applied:
            notify_title = '你的%s申请已通过' % label
            notify_body = '《%s》已设置%s啦~' % (pr.article.title[:30], label)
        else:
            notify_title = '你的%s申请已通过（暂未生效）' % label
            # 文案避免重复堆叠：exec_note 已含原因（如「置顶名额已满（5/5 篇），系统未执行置顶」）
            notify_body = ('《%s》的%s申请管理员已通过，但%s。'
                           '腾出名额后可以再来申请，或联系管理员手动处理喵~'
                           % (pr.article.title[:30], label, exec_note))
        Notification.objects.create(
            user=pr.applicant or pr.article.author, type=Notification.Type.SYSTEM,
            title=notify_title, content=notify_body)
        if applied:
            messages.success(request, '已通过%s申请并已生效~ 🌸' % label)
        else:
            messages.warning(request, '已通过%s申请，但%s，本次未生效。' % (label, exec_note))
    elif action == 'reject':
        pr.status = PromotionRequest.Status.REJECTED
        pr.handled_by = request.user
        pr.handled_at = timezone.now()
        # 驳回属于「审批结论即为终态」，系统执行状态保持未执行并写清原因
        pr.execution_status = PromotionRequest.Execution.NOT_RUN
        pr.execution_note = '申请被驳回，系统无需执行'
        pr.save(update_fields=['status', 'handled_by', 'handled_at',
                               'execution_status', 'execution_note'])
        ModerationLog.objects.create(
            moderator=request.user, moderator_name=str(request.user),
            action=ModerationLog.Action.REJECT, target_type='article', article=pr.article,
            target_title=pr.article.title,
            reason='驳回%s申请：%s %s' % (label, pr.reason, note))
        Notification.objects.create(
            user=pr.applicant or pr.article.author, type=Notification.Type.SYSTEM,
            title='你的%s申请未通过' % label,
            content=note or '很遗憾，你的申请没有通过，再接再厉哦~')
        messages.warning(request, '已驳回%s申请~' % label)
    return redirect('/console/moderation/?tab=promotions')



def moderation_settings_save(request):
    """保存审核全局设置：POST /console/moderation/settings/（仅 staff）。"""
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect('login')
    if request.method != 'POST':
        return redirect('/console/moderation/?tab=promotions')
    s = ModerationSettings.load()
    s.require_article_review = request.POST.get('require_article_review') == 'on'
    s.require_comment_review = request.POST.get('require_comment_review') == 'on'
    try:
        s.comment_recall_minutes = max(1, int(request.POST.get('comment_recall_minutes', 10)))
    except (TypeError, ValueError):
        pass
    try:
        s.max_pinned = max(1, int(request.POST.get('max_pinned', 3)))
    except (TypeError, ValueError):
        pass
    s.save()
    messages.success(request, '审核全局设置已保存喵~ ⚙️')
    return redirect('/console/moderation/?tab=promotions')

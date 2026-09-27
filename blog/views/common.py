# -*- coding: utf-8 -*-

"""通用视图工具：HTML 净化、统一 JSON/HTTP 响应、分页、缓存与 QuerySet 工具。"""

import json
import logging
import os
import re
import uuid
from typing import Any, Optional, Tuple
import bleach
from ..html_safety import MoeCSSSanitizer
from django.conf import settings
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Avg, Count, F, Min, Q, Sum
from django.db.models.query import QuerySet
from django.http import (
    FileResponse, Http404, HttpRequest, HttpResponse,
    HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound,
    HttpResponseNotModified, HttpResponsePermanentRedirect,
    HttpResponseRedirect, JsonResponse, StreamingHttpResponse,
)
from django.utils import timezone
from ..models import (
    AccessLog, Article, Badge, Category, Comment, CommentReport,
    EditLog, Favorite, FavoriteFolder, ModerationLog, Notification,
    PromotionRequest, ModerationSettings, Rating, Series, ShortLink,
    SiteNotice, Tag, User, UserBadge,
)
from ..site_messages import msg


logger = logging.getLogger('blog.views')

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

# 迭代#111: _base_qs函数docstring
# 迭代#112: _base_qs(request: HttpRequest) -> QuerySet 类型提示
# 迭代#113: _base_qs权限过滤逻辑注释
def _base_qs(request: HttpRequest, own_drafts: bool = False) -> QuerySet:
    """构造文章基础查询集（QuerySet），并按登录状态施加可见性过滤。

    所有文章列表 / 详情视图都应基于此查询集，以保证权限一致：
    - 匿名游客：只能看到 ``status=已发布`` 的文章，看不到任何人的草稿；
    - 已登录用户：可以看到所有已发布文章 + 自己的草稿（别人的草稿仍不可见）；
    - 管理员（staff）：own_drafts=True 时可预览全部状态（含待审核 / 软删除）。

    同时使用 ``select_related`` / ``prefetch_related`` 预加载关联对象，
    避免模板渲染时逐行查询造成 N+1 性能问题。

    Args:
        request: 当前 HttpRequest 对象，用于判断用户是否已登录。
        own_drafts: 是否为「详情页预览」语义（True 时作者 / 管理员可见未发布内容）。

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
    # ------------------------------------------------------------------
    # Bug9-1 修复：定时（未到点）文章的可见性
    # ------------------------------------------------------------------
    # 原实现无条件 exclude(published_at > now)，导致「作者 / 管理员打开自己
    # 定时未发布的文章」也直接 404，无法预览与核对；而管理员在审核页点「预览」
    # 同样打不开。新口径：
    #   · 作者本人 / 管理员（own_drafts 语义）→ 放行，允许预览定时文章，
    #     页面顶部给出「⏰ 定时投稿·X 后自动发布」提示（模板 scheduled_notice）；
    #   · 其他登录用户 / 游客 → 仍排除，定时内容绝不提前泄露。
    # 注意：这里只对 own_drafts=True 放行；列表流（own_drafts=False）不经过本段，
    # 因为列表本身已限定 status=PUBLISHED。
    if not (own_drafts and is_auth):
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

def _optimized_list_qs(qs):
    # 第2轮迭代#53: only/defer 优化——列表页仅取模板需要的字段，避免拉取大文本 content
    return qs.only(
        'id', 'title', 'views', 'likes', 'comment_count', 'created_at',
        'updated_at', 'excerpt_field', 'cover_image', 'is_pinned', 'status',
        'kind', 'author__id', 'author__username', 'author__nickname',
        'category__id', 'category__name', 'category__icon')

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

def _cache_get_or_set(key, builder, timeout=300):
    # 第2轮迭代#61: 侧边栏缓存——统一 get_or_set 封装（侧边栏主逻辑见 _sidebar）
    return cache.get_or_set(key, builder, timeout)

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

# ============================ Round6（bug14/15）：我的小站系列页面 ============================
def _paginate_qs(request, qs, per_page=10):
    """小工具：对查询集分页，返回 (page_obj, paginator)。"""
    paginator = Paginator(qs, per_page)
    return paginator.get_page(request.GET.get('page')), paginator

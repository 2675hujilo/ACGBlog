# -*- coding: utf-8 -*-

"""通用视图工具：HTML 净化、统一 JSON/HTTP 响应、分页、缓存与 QuerySet 工具。"""

#: 导入模块「json」，供本文件后续使用
import json
#: 导入模块「logging」，供本文件后续使用
import logging
#: 导入模块「os」，供本文件后续使用
import os
#: 导入模块「re」，供本文件后续使用
import re
#: 导入模块「uuid」，供本文件后续使用
import uuid
#: 从模块「typing」导入所需对象
from typing import Any, Optional, Tuple
#: 导入模块「bleach」，供本文件后续使用
import bleach
#: 从模块「..utils.html_safety」导入所需对象
from ..utils.html_safety import MoeCSSSanitizer
#: 从模块「django.conf」导入所需对象
from django.conf import settings
#: 从模块「django.core.cache」导入所需对象
from django.core.cache import cache
#: 从模块「django.core.paginator」导入所需对象
from django.core.paginator import Paginator
#: 从模块「django.db.models」导入所需对象
from django.db.models import Avg, Count, F, Min, Q, Sum
#: 从模块「django.db.models.query」导入所需对象
from django.db.models.query import QuerySet
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
#: 从模块「django.utils」导入所需对象
from django.utils import timezone
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
#: 从模块「..services.site_messages」导入所需对象
from ..services.site_messages import msg


#: 定义变量「logger」，保存对应数据
logger = logging.getLogger('blog.views')

# ============================ F类：常量提取 ============================
# 迭代#90: 文章标题最大长度常量
#: 定义变量「ARTICLE_TITLE_MAX_LENGTH」，保存对应数据
ARTICLE_TITLE_MAX_LENGTH = 200

# 迭代#91: 评论最大长度常量
#: 定义变量「COMMENT_MAX_LENGTH」，保存对应数据
COMMENT_MAX_LENGTH = 10000

# 迭代#92: 个人介绍最大长度常量
#: 定义变量「INTRODUCTION_MAX_LENGTH」，保存对应数据
INTRODUCTION_MAX_LENGTH = 500

# 迭代#93: 昵称最大长度常量
#: 定义变量「NICKNAME_MAX_LENGTH」，保存对应数据
NICKNAME_MAX_LENGTH = 50

# 迭代#94: 搜索关键词最大长度常量
#: 定义变量「SEARCH_Q_MAX_LENGTH」，保存对应数据
SEARCH_Q_MAX_LENGTH = 100

# 迭代#95: 分页默认大小常量（沿用 settings.PAGE_SIZE）
#: 定义变量「DEFAULT_PAGE_SIZE」，保存对应数据
DEFAULT_PAGE_SIZE = settings.PAGE_SIZE

# 迭代#96: 热门文章数量常量
#: 定义变量「HOT_ARTICLES_LIMIT」，保存对应数据
HOT_ARTICLES_LIMIT = 10

# 迭代#97: 相关文章数量常量
#: 定义变量「RELATED_ARTICLES_LIMIT」，保存对应数据
RELATED_ARTICLES_LIMIT = 8

# 迭代#98: 标签云最大数量常量
#: 定义变量「TAG_CLOUD_LIMIT」，保存对应数据
TAG_CLOUD_LIMIT = 30

# 迭代#99: 阅读速度常量（300字/分钟）
#: 定义变量「READING_WORDS_PER_MINUTE」，保存对应数据
READING_WORDS_PER_MINUTE = 300

# 迭代#100: 摘要默认长度常量
#: 定义变量「EXCERPT_DEFAULT_LENGTH」，保存对应数据
EXCERPT_DEFAULT_LENGTH = 180

# 迭代#101: 头像最大大小常量（2MB）
#: 定义变量「AVATAR_MAX_BYTES」，保存对应数据
AVATAR_MAX_BYTES = 2 * 1024 * 1024

# 迭代#102: 封面图最大大小常量（8MB）
#: 定义变量「COVER_IMAGE_MAX_BYTES」，保存对应数据
COVER_IMAGE_MAX_BYTES = 8 * 1024 * 1024

# 迭代#103: 定时发布检查间隔常量（秒）
#: 定义变量「SCHEDULED_CHECK_INTERVAL」，保存对应数据
SCHEDULED_CHECK_INTERVAL = 60

# 迭代#104: 在线人数时间窗口常量（5分钟）
#: 定义变量「ONLINE_WINDOW_MINUTES」，保存对应数据
ONLINE_WINDOW_MINUTES = 5

# ============================ 内容净化（bleach）常量 ============================
# 富文本正文允许的 HTML 标签白名单：仅保留排版 / 语义 / 表格相关标签，
# 一律剔除 script / iframe / object / embed / form / meta / link / style 等危险标签。
#: 定义变量「ALLOWED_TAGS」，保存对应数据（集合/元组）
ALLOWED_TAGS = [
    #: 该行执行对应逻辑（结合上下文理解）
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'col', 'colgroup',
    #: 该行执行对应逻辑（结合上下文理解）
    'dd', 'del', 'div', 'dl', 'dt', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    #: 该行执行对应逻辑（结合上下文理解）
    'hr', 'i', 'img', 'ins', 'kbd', 'li', 'ol', 'p', 'pre', 'q', 's', 'samp',
    #: 该行执行对应逻辑（结合上下文理解）
    'small', 'span', 'strike', 'strong', 'sub', 'sup', 'table', 'tbody', 'td',
    #: 该行执行对应逻辑（结合上下文理解）
    'tfoot', 'th', 'thead', 'tr', 'tt', 'u', 'ul', 'figure', 'figcaption',
#: 该行执行对应逻辑（结合上下文理解）
]

# 允许的标签属性：a / img 各自放行所需属性，其余标签统一放行 class 与 style。
#: 定义变量「ALLOWED_ATTRIBUTES」，保存对应数据
ALLOWED_ATTRIBUTES = {
    #: 配置项「a」：字典/模型的该键设置为对应值
    'a': ['href', 'title', 'target'],
    #: 配置项「img」：字典/模型的该键设置为对应值
    'img': ['src', 'alt', 'title', 'width', 'height', 'style'],
    #: 该行执行对应逻辑（结合上下文理解）
    '*': ['class', 'style'],
#: 该行执行对应逻辑（结合上下文理解）
}

# 允许的 URL 协议：仅 http / https / mailto，显式禁止 javascript: 等危险协议。
#: 定义变量「ALLOWED_PROTOCOLS」，保存对应数据（集合/元组）
ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']

# 评论内容允许的纯文本标签白名单（评论只允许少量行内标签，杜绝富文本注入）：
# 仅 strong(加粗) / em(斜体) / a(链接) / code(行内代码)。
# Bug4：新增 img，使「图片喵」上传后的图片能在评论中显示（文件已在上传接口做真实头校验）
#: 定义变量「COMMENT_ALLOWED_TAGS」，保存对应数据（集合/元组）
COMMENT_ALLOWED_TAGS = ['strong', 'em', 'a', 'code', 'img']

#: 定义变量「COMMENT_ALLOWED_ATTRIBUTES」，保存对应数据
COMMENT_ALLOWED_ATTRIBUTES = {
    #: 配置项「a」：字典/模型的该键设置为对应值
    'a': ['href', 'title', 'target'],
    #: 配置项「img」：字典/模型的该键设置为对应值
    'img': ['src', 'alt', 'title'],   # 仅放行图片地址与替代文本，杜绝 on* 事件属性
#: 该行执行对应逻辑（结合上下文理解）
}

#: 定义变量「COMMENT_ALLOWED_PROTOCOLS」，保存对应数据（集合/元组）
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
    #: 条件判断：条件成立时执行该分支
    if not content:
        #: 返回结果并结束当前函数
        return content or ''
    # bleach 的 strip=True 只会"剥掉"不在白名单的标签，却会保留其内部文本，
    # 例如 <style>body{background:url(javascript:alert(1))}</style> 剥掉 <style> 后
    # 仍会残留可执行的 CSS 文本。因此先用正则把危险容器标签连同其内容整体删除，
    # 再交给 bleach 做白名单过滤。
    #: 定义变量「dangerous_containers」，保存对应数据
    dangerous_containers = re.compile(
        #: 该行执行对应逻辑（结合上下文理解）
        r'<(script|style|iframe|object|embed|noscript|template|frame|frameset)[\s\S]*?</\1\s*>',
        #: 操作「re」的属性或方法
        re.IGNORECASE)
    #: 定义变量「content」，保存对应数据
    content = dangerous_containers.sub('', content)
    #: 返回结果并结束当前函数
    return bleach.clean(
        #: 该行执行对应逻辑（结合上下文理解）
        content,
        #: 定义变量「tags」，保存对应数据
        tags=ALLOWED_TAGS,
        #: 定义变量「attributes」，保存对应数据
        attributes=ALLOWED_ATTRIBUTES,
        #: 定义变量「protocols」，保存对应数据
        protocols=ALLOWED_PROTOCOLS,
        #: 定义变量「css_sanitizer」，保存对应数据
        css_sanitizer=MoeCSSSanitizer,
        #: 定义变量「strip」，保存对应数据
        strip=True,
    #: 该行执行对应逻辑（结合上下文理解）
    )

# 迭代#108: sanitize_comment 类型提示
def sanitize_comment(content: str) -> str:
    """对评论内容做净化：只保留 strong/em/a/code 少量行内标签。

    Args:
        content: 用户提交的评论文本。

    Returns:
        str: 净化后的安全评论 HTML。
    """
    #: 条件判断：条件成立时执行该分支
    if not content:
        #: 返回结果并结束当前函数
        return content or ''
    #: 返回结果并结束当前函数
    return bleach.clean(
        #: 该行执行对应逻辑（结合上下文理解）
        content,
        #: 定义变量「tags」，保存对应数据
        tags=COMMENT_ALLOWED_TAGS,
        #: 定义变量「attributes」，保存对应数据
        attributes=COMMENT_ALLOWED_ATTRIBUTES,
        #: 定义变量「protocols」，保存对应数据
        protocols=COMMENT_ALLOWED_PROTOCOLS,
        #: 定义变量「strip」，保存对应数据
        strip=True,
    #: 该行执行对应逻辑（结合上下文理解）
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
    #: 返回结果并结束当前函数
    return (json.dumps(data, ensure_ascii=False)
            #: 该行执行对应逻辑（结合上下文理解）
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
    #: ORM 预加载关联，减少 N+1 查询提升性能
    qs = Article.objects.select_related('author', 'category').prefetch_related('tags')
    #: 获取当前时间（时区感知），统一时间口径
    now = timezone.now()
    #: 读取本次请求的 user 数据
    is_auth = request.user.is_authenticated
    #: 读取本次请求的 user 数据
    is_staff = is_auth and request.user.is_staff
    # bug8: 软删除内容对前台隐藏；仅管理员在详情预览（own_drafts）时可见，
    # 以便回收站核对 / 恢复。
    #: 条件判断：条件成立时执行该分支
    if not (own_drafts and is_staff):
        #: 定义变量「qs」，保存对应数据
        qs = qs.filter(is_deleted=False)
    # Bug17 + bug8: 公开列表流一律只显示已发布，避免草稿 / 待审核在前台泄露。
    # own_drafts=True（详情页）时：作者可见自己的任意状态文章用于预览；
    # 管理员可预览全部状态（含待审核 / 软删除）。
    #: 条件判断：条件成立时执行该分支
    if own_drafts and is_auth:
        #: 条件判断：条件成立时执行该分支
        if is_staff:
            #: 该行执行对应逻辑（结合上下文理解）
            pass  # 管理员不过滤状态
        #: 以上条件均不成立时的兜底分支
        else:
            #: 定义变量「qs」，保存对应数据
            qs = qs.filter(
                #: 使用 Q/F 表达式构造复杂查询或引用字段值
                Q(status=Article.Status.PUBLISHED) | Q(author=request.user))
    #: 以上条件均不成立时的兜底分支
    else:
        #: 定义变量「qs」，保存对应数据
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
    #: 条件判断：条件成立时执行该分支
    if not (own_drafts and is_auth):
        #: 定义变量「qs」，保存对应数据
        qs = qs.exclude(
            #: 定义变量「status__in」，保存对应数据（集合/元组）
            status__in=[Article.Status.DRAFT, Article.Status.PENDING],
            #: 定义变量「published_at__gt」，保存对应数据
            published_at__gt=now)
    #: 返回结果并结束当前函数
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
    #: 读取本次请求的 GET 数据
    kind = request.GET.get('kind', '').strip()
    # 仅接受合法的内容类型枚举值，防止传入非法 kind 导致空结果或注入
    #: 条件判断：条件成立时执行该分支
    if kind in Article.Kind.values:
        #: 定义变量「qs」，保存对应数据
        qs = qs.filter(kind=kind)

    #: 读取本次请求的 GET 数据
    category_id = request.GET.get('category', '').strip()
    # isdigit() 防御非数字输入，避免 int() 抛异常
    # 迭代#117: 分类ID合法性验证
    #: 条件判断：条件成立时执行该分支
    if category_id.isdigit():
        #: 定义变量「qs」，保存对应数据
        qs = qs.filter(category_id=int(category_id))

    #: 读取本次请求的 GET 数据
    tag_id = request.GET.get('tag', '').strip()
    #: 条件判断：条件成立时执行该分支
    if tag_id.isdigit():
        # 多对多字段过滤：tags__id 穿透到关联表
        #: 定义变量「qs」，保存对应数据
        qs = qs.filter(tags__id=int(tag_id))

    #: 读取本次请求的 GET 数据
    q = request.GET.get('q', '').strip()
    #: 条件判断：条件成立时执行该分支
    if q:
        # icontains 不区分大小写模糊匹配，标题 OR 正文任一命中即可
        #: 使用 Q/F 表达式构造复杂查询或引用字段值
        qs = qs.filter(Q(title__icontains=q) | Q(content__icontains=q))

    #: 读取本次请求的 GET 数据
    sort = request.GET.get('sort', 'latest')
    # 迭代#118: 排序参数验证
    #: 条件判断：条件成立时执行该分支
    if sort not in ('latest', 'hot'):
        #: 定义变量「sort」，保存对应数据
        sort = 'latest'
    #: 条件判断：条件成立时执行该分支
    if sort == 'hot':
        # 热门：阅读量降序，阅读量相同时按 id 降序兜底；置顶文章仍优先
        #: 对查询结果按字段排序
        qs = qs.order_by('-is_pinned', '-views', '-id')
    #: 以上条件均不成立时的兜底分支
    else:
        # 默认：最新优先（置顶文章始终排在最前，再按发布时间降序、id 降序兜底）
        #: 对查询结果按字段排序
        qs = qs.order_by('-is_pinned', '-created_at', '-id')
    # distinct() 去除因多对多 JOIN 产生的重复文章行
    #: 返回结果并结束当前函数
    return qs.distinct(), sort, q

# 侧边栏缓存键与过期时间：文章 / 评论变更时由视图主动失效
#: 定义变量「SIDEBAR_CACHE_KEY」，保存对应数据
SIDEBAR_CACHE_KEY = 'sidebar_data'

#: 定义变量「SIDEBAR_CACHE_TIMEOUT」，保存对应数据
SIDEBAR_CACHE_TIMEOUT = 300  # 5 分钟

# 第3轮迭代#3: 统一缓存 key 命名空间与 TTL，集中管理便于失效对齐
#: 定义变量「FOOTER_STATS_KEY」，保存对应数据
FOOTER_STATS_KEY = 'footer_stats'

#: 定义变量「HOT_ARTICLES_KEY」，保存对应数据
HOT_ARTICLES_KEY = 'hot_articles'

#: 定义变量「TAG_CLOUD_KEY」，保存对应数据
TAG_CLOUD_KEY = 'tag_cloud'

#: 定义变量「ARCHIVE_KEY」，保存对应数据
ARCHIVE_KEY = 'archive_data'

#: 定义变量「VIEW_BUFFER_KEY」，保存对应数据
VIEW_BUFFER_KEY = 'viewbuf_{pk}'

def _optimized_list_qs(qs):
    # 第2轮迭代#53: only/defer 优化——列表页仅取模板需要的字段，避免拉取大文本 content
    """
    功能：处理「optimized list qs」相关逻辑。

    参数：
      - qs：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 返回结果并结束当前函数
    return qs.only(
        #: 该行执行对应逻辑（结合上下文理解）
        'id', 'title', 'views', 'likes', 'comment_count', 'created_at',
        #: 该行执行对应逻辑（结合上下文理解）
        'updated_at', 'excerpt_field', 'cover_image', 'is_pinned', 'status',
        #: 该行执行对应逻辑（结合上下文理解）
        'kind', 'author__id', 'author__username', 'author__nickname',
        #: 该行执行对应逻辑（结合上下文理解）
        'category__id', 'category__name', 'category__icon')

def _qs_union(qs_a, qs_b):
    # 第2轮迭代#56: union 优化——合并两个已发布查询集并去重（只读场景）
    """
    功能：处理「qs union」相关逻辑。

    参数：
      - qs_a：传入参数，含义结合函数体与调用处
      - qs_b：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 返回结果并结束当前函数
    return qs_a.union(qs_b)

def _iter_large_queryset(qs, chunk=2000):
    # 第2轮迭代#57: iterator 优化——大数据量遍历时按块拉取，避免一次性占满内存
    """
    功能：处理「iter large queryset」相关逻辑。

    参数：
      - qs：传入参数，含义结合函数体与调用处
      - chunk（可选，有默认值）：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 返回结果并结束当前函数
    return qs.iterator(chunk_size=chunk)

def _bulk_update_view_counts(pairs):
    # 第2轮迭代#58: bulk_update 优化——批量更新文章阅读量（pairs 为 [(article, views), ...]）
    """
    功能：处理「bulk update view counts」相关逻辑。

    参数：
      - pairs：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：含 Django ORM 数据库查询，注意查询性能与空结果处理。
    """
    #: 定义变量「objs」，保存对应数据（集合/元组）
    objs = [a for a, _ in pairs if a is not None]
    #: 条件判断：条件成立时执行该分支
    if not objs:
        #: 返回结果并结束当前函数
        return 0
    #: 调用「Article.objects.bulk_update」执行相应逻辑
    Article.objects.bulk_update(objs, ['views'])
    #: 返回结果并结束当前函数
    return len(objs)

def _cache_get_or_set(key, builder, timeout=300):
    # 第2轮迭代#61: 侧边栏缓存——统一 get_or_set 封装（侧边栏主逻辑见 _sidebar）
    """
    功能：处理「cache get or set」相关逻辑。

    参数：
      - key：传入参数，含义结合函数体与调用处
      - builder：传入参数，含义结合函数体与调用处
      - timeout（可选，有默认值）：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：读写缓存，注意缓存键口径与失效策略。
    """
    #: 返回结果并结束当前函数
    return cache.get_or_set(key, builder, timeout)

def _api_cache_page(view_func):
    # 第2轮迭代#70: API 响应缓存装饰器——对只读接口做 5 分钟缓存
    """
    功能：处理「api cache page」相关逻辑。

    参数：
      - view_func：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 从模块「django.views.decorators.cache」导入所需对象
    from django.views.decorators.cache import cache_page as _cp
    #: 返回结果并结束当前函数
    return _cp(60 * 5)(view_func)

# 第2轮迭代#71: Paginator 优化说明——index 已使用 Paginator + get_page 宽容分页
def _safe_paginate(qs, page_size, page_param):
    # 第2轮迭代#72: EmptyPage 处理——get_page 自动把超出末页回退到最后一页
    """
    功能：处理「safe paginate」相关逻辑。

    参数：
      - qs：传入参数，含义结合函数体与调用处
      - page_size：传入参数，含义结合函数体与调用处
      - page_param：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 定义变量「paginator」，保存对应数据
    paginator = Paginator(qs, page_size)
    #: 返回结果并结束当前函数
    return paginator.get_page(page_param)

# 第2轮迭代#73: PageNotAnInteger 处理说明——get_page 自动把非法页码回退第 1 页
def _paginate_cached(qs, page_size, page_num):
    # 第2轮迭代#74: 分页缓存——对分页结果做短 TTL 缓存（key 含页码）
    """
    功能：处理「paginate cached」相关逻辑。

    参数：
      - qs：传入参数，含义结合函数体与调用处
      - page_size：传入参数，含义结合函数体与调用处
      - page_num：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：读写缓存，注意缓存键口径与失效策略。
    """
    #: 定义变量「key」，保存对应数据
    key = f'page_{hash(str(qs.query)) & 0xffffffff}_{page_size}_{page_num}'
    #: 返回结果并结束当前函数
    return cache.get_or_set(
        #: 该行执行对应逻辑（结合上下文理解）
        key, lambda: _safe_paginate(qs, page_size, page_num), 60)

def _clean_page_size(value, default=None):
    # 第2轮迭代#75: 分页大小验证——限制在 [1, 100] 区间，越界回退默认
    """
    功能：清理「page size」。

    参数：
      - value：传入参数，含义结合函数体与调用处
      - default（可选，有默认值）：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 定义变量「default」，保存对应数据
    default = default or settings.PAGE_SIZE
    #: 尝试执行可能出错的代码
    try:
        #: 定义变量「n」，保存对应数据
        n = int(value)
    #: 捕获并处理异常，避免程序中断
    except (TypeError, ValueError):
        #: 返回结果并结束当前函数
        return default
    #: 返回结果并结束当前函数
    return max(1, min(n, 100))

def _clamp_page_number(value, max_pages):
    # 第2轮迭代#76: 最大分页限制——页码不小于 1、不超过总页数
    """
    功能：处理「clamp page number」相关逻辑。

    参数：
      - value：传入参数，含义结合函数体与调用处
      - max_pages：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 尝试执行可能出错的代码
    try:
        #: 定义变量「n」，保存对应数据
        n = int(value)
    #: 捕获并处理异常，避免程序中断
    except (TypeError, ValueError):
        #: 返回结果并结束当前函数
        return 1
    #: 定义变量「n」，保存对应数据
    n = max(1, n)
    #: 条件判断：条件成立时执行该分支
    if max_pages:
        #: 定义变量「n」，保存对应数据
        n = min(n, max_pages)
    #: 返回结果并结束当前函数
    return n

def _validate_page_jump(value):
    # 第2轮迭代#77: 分页跳转验证——非数字页码返回 None 交由 get_page 兜底
    """
    功能：校验「page jump」。

    参数：
      - value：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 条件判断：条件成立时执行该分支
    if value is None:
        #: 返回结果并结束当前函数
        return None
    #: 定义变量「s」，保存对应数据
    s = str(value).strip()
    #: 返回结果并结束当前函数
    return s if s.lstrip('-').isdigit() else None

def _seo_pagination_context(page_obj):
    # 第2轮迭代#78: 分页 SEO——为模板提供 rel=prev/next 的查询串
    """
    功能：处理「seo pagination context」相关逻辑。

    参数：
      - page_obj：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 返回结果并结束当前函数
    return {
        #: 配置项「page_prev_url」：字典/模型的该键设置为对应值
        'page_prev_url': (f'?page={page_obj.previous_page_number()}'
                          #: 条件判断：条件成立时执行该分支
                          if page_obj.has_previous() else ''),
        #: 配置项「page_next_url」：字典/模型的该键设置为对应值
        'page_next_url': (f'?page={page_obj.next_page_number()}'
                          #: 条件判断：条件成立时执行该分支
                          if page_obj.has_next() else ''),
    #: 该行执行对应逻辑（结合上下文理解）
    }

def _build_base_context(request, active_nav='home'):
    # 第2轮迭代#81: context 精简——抽取公共上下文，避免各视图重复拼装
    """
    功能：构建「base context」。

    参数：
      - request：传入参数，含义结合函数体与调用处
      - active_nav（可选，有默认值）：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 返回结果并结束当前函数
    return {
        #: 配置项「active_nav」：字典/模型的该键设置为对应值
        'active_nav': active_nav,
        #: 配置项「meta_keywords」：字典/模型的该键设置为对应值
        'meta_keywords': settings.SITE_KEYWORDS,
        #: 配置项「site_name」：字典/模型的该键设置为对应值
        'site_name': settings.SITE_NAME,
    #: 该行执行对应逻辑（结合上下文理解）
    }

def _eliminate_redundant_queries(qs):
    # 第2轮迭代#82: 冗余查询消除——统一走 select_related + prefetch_related
    """
    功能：处理「eliminate redundant queries」相关逻辑。

    参数：
      - qs：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 返回结果并结束当前函数
    return qs.select_related('author', 'category').prefetch_related('tags')

def _conditional_related(qs, need_related=True):
    # 第2轮迭代#83: 条件加载——仅在详情/卡片需要关联时才预取
    """
    功能：处理「conditional related」相关逻辑。

    参数：
      - qs：传入参数，含义结合函数体与调用处
      - need_related（可选，有默认值）：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 返回结果并结束当前函数
    return _eliminate_redundant_queries(qs) if need_related else qs

def _lazy_context_provider(fn):
    # 第2轮迭代#84: 懒加载上下文——把昂贵查询包装为惰性计算函数，模板渲染时才执行
    """
    功能：处理「lazy context provider」相关逻辑。

    参数：
      - fn：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    def wrapper(request):
        """
        功能：处理「wrapper」相关逻辑。

        参数：
          - request：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 返回结果并结束当前函数
        return fn(request)
    #: 返回结果并结束当前函数
    return wrapper

def _cached_context(key, builder, timeout=300):
    # 第2轮迭代#85: 上下文缓存——公共上下文片段按 key 短 TTL 缓存
    """
    功能：处理「cached context」相关逻辑。

    参数：
      - key：传入参数，含义结合函数体与调用处
      - builder：传入参数，含义结合函数体与调用处
      - timeout（可选，有默认值）：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：读写缓存，注意缓存键口径与失效策略。
    """
    #: 返回结果并结束当前函数
    return cache.get_or_set(key, builder, timeout)

def _flatten_context(ctx):
    # 第2轮迭代#87: 模板上下文扁平化——把嵌套 stats 字典拍平为一级键，方便模板取值
    """
    功能：处理「flatten context」相关逻辑。

    参数：
      - ctx：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 定义变量「flat」，保存对应数据
    flat = {}
    #: 循环遍历，逐个处理元素
    for k, v in ctx.items():
        #: 条件判断：条件成立时执行该分支
        if isinstance(v, dict):
            #: 循环遍历，逐个处理元素
            for sk, sv in v.items():
                #: 该行执行对应逻辑（结合上下文理解）
                flat[f'{k}_{sk}'] = sv
        #: 以上条件均不成立时的兜底分支
        else:
            #: 该行执行对应逻辑（结合上下文理解）
            flat[k] = v
    #: 返回结果并结束当前函数
    return flat

def _default_context(ctx, defaults):
    # 第2轮迭代#88: 默认上下文值——补齐缺失键，避免模板取未定义变量
    """
    功能：处理「default context」相关逻辑。

    参数：
      - ctx：传入参数，含义结合函数体与调用处
      - defaults：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 定义变量「merged」，保存对应数据
    merged = dict(defaults)
    #: 调用「merged.update」执行相应逻辑
    merged.update(ctx)
    #: 返回结果并结束当前函数
    return merged

def _safe_context_value(v):
    # 第2轮迭代#89: 上下文安全过滤——剥离不可序列化对象，仅保留可 JSON 化数据
    """
    功能：处理「safe context value」相关逻辑。

    参数：
      - v：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 条件判断：条件成立时执行该分支
    if isinstance(v, (str, int, float, bool)) or v is None:
        #: 返回结果并结束当前函数
        return v
    #: 条件判断：条件成立时执行该分支
    if isinstance(v, (list, tuple)):
        #: 返回结果并结束当前函数
        return [_safe_context_value(x) for x in v]
    #: 条件判断：条件成立时执行该分支
    if isinstance(v, dict):
        #: 返回结果并结束当前函数
        return {k: _safe_context_value(val) for k, val in v.items()}
    #: 返回结果并结束当前函数
    return str(v)

def _serialize_context(ctx):
    # 第2轮迭代#90: 上下文序列化——把上下文转为可缓存的纯 dict
    """
    功能：处理「serialize context」相关逻辑。

    参数：
      - ctx：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 返回结果并结束当前函数
    return {k: _safe_context_value(v) for k, v in ctx.items()}

def _json_ok(data=None, **extra):
    # 第2轮迭代#92: JsonResponse 优化——统一成功响应结构 {code,data,msg}
    """
    功能：处理「json ok」相关逻辑。

    参数：
      - data（可选，有默认值）：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 定义变量「payload」，保存对应数据
    payload = {'code': 0, 'data': data, 'msg': 'ok'}
    #: 调用「payload.update」执行相应逻辑
    payload.update(extra)
    #: 返回结果并结束当前函数
    return JsonResponse(payload)

def _stream_text(iterable):
    # 第2轮迭代#93: StreamingHttpResponse——逐块产出文本，避免大响应占满内存
    """
    功能：处理「stream text」相关逻辑。

    参数：
      - iterable：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 构造 HTTP 响应返回给客户端
    resp = StreamingHttpResponse(iterable)
    #: 该行执行对应逻辑（结合上下文理解）
    resp['Content-Type'] = 'text/plain; charset=utf-8'
    #: 返回结果并结束当前函数
    return resp

def _file_download(file_path, content_type='application/octet-stream'):
    # 第2轮迭代#94: FileResponse——流式下载本地文件
    """
    功能：处理「file download」相关逻辑。

    参数：
      - file_path：传入参数，含义结合函数体与调用处
      - content_type（可选，有默认值）：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 导入模块「os」，供本文件后续使用
    import os as _os
    #: 定义变量「fh」，保存对应数据
    fh = open(file_path, 'rb')
    #: 定义变量「resp」，保存对应数据
    resp = FileResponse(fh, content_type=content_type)
    #: 该行执行对应逻辑（结合上下文理解）
    resp['Content-Disposition'] = f'attachment; filename="{_os.path.basename(file_path)}"'
    #: 返回结果并结束当前函数
    return resp

def _redirect_302(url):
    # 第2轮迭代#95: HttpResponseRedirect 优化——302 临时重定向统一封装
    """
    功能：处理「redirect 302」相关逻辑。

    参数：
      - url：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 返回结果并结束当前函数
    return HttpResponseRedirect(url)

def _redirect_permanent(url):
    # 第2轮迭代#96: HttpResponsePermanentRedirect——301 永久重定向
    """
    功能：处理「redirect permanent」相关逻辑。

    参数：
      - url：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 返回结果并结束当前函数
    return HttpResponsePermanentRedirect(url)

def _not_modified():
    # 第2轮迭代#97: HttpResponseNotModified——304 缓存命中
    """
    功能：处理「not modified」相关逻辑。

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 返回结果并结束当前函数
    return HttpResponseNotModified()

def _bad_request(msg='请求参数有误'):
    # 第2轮迭代#98: HttpResponseBadRequest——400
    """
    功能：处理「bad request」相关逻辑。

    参数：
      - msg（可选，有默认值）：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 返回结果并结束当前函数
    return HttpResponseBadRequest(msg)

def _forbidden(msg='没有权限访问'):
    # 第2轮迭代#99: HttpResponseForbidden——403
    """
    功能：处理「forbidden」相关逻辑。

    参数：
      - msg（可选，有默认值）：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 返回结果并结束当前函数
    return HttpResponseForbidden(msg)

def _not_found(msg='页面不存在'):
    # 第2轮迭代#100: HttpResponseNotFound——404
    """
    功能：处理「not found」相关逻辑。

    参数：
      - msg（可选，有默认值）：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：保持函数单一职责；修改时确认调用方不受影响。
    """
    #: 返回结果并结束当前函数
    return HttpResponseNotFound(msg)

# ============================ Round6（bug14/15）：我的小站系列页面 ============================
def _paginate_qs(request, qs, per_page=10):
    """小工具：对查询集分页，返回 (page_obj, paginator)。"""
    #: 定义变量「paginator」，保存对应数据
    paginator = Paginator(qs, per_page)
    #: 返回结果并结束当前函数
    return paginator.get_page(request.GET.get('page')), paginator

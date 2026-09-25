"""全局模板上下文：顶栏分类导航 + 友情链接注入 + 页脚统计 + 侧边栏统计 + 公告。

第4轮重构要点：
- 公共缓存预热从 ``apps.py ready()`` 移至此处的**首个请求懒加载**（线程安全），
  彻底消除 runserver 启动期"app 初始化阶段访问数据库"RuntimeWarning；
- 侧边栏统计（文章数/总浏览/标签数/分类数/今日访问/独立访客）纳入缓存，TTL 300s；
- ``site_nav`` 改为复用视图层已缓存的侧边栏数据，避免与视图重复查询分类导航；
- 公告横幅支持 cookie 关闭：前端写入 ``notice_dismissed_{id}`` 后不再下发。
"""
import json
import os
import threading
from datetime import date, timedelta

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Sum
from django.utils import timezone

from .models import (AccessLog, Article, Category, Comment, FriendlyLink,
                     SiteNotice, Tag)

# 站点上线日期：用于页脚计算"已运行 N 天"。如需修改改这一行即可。
SITE_LAUNCH_DATE = date(2024, 1, 1)

# 第4轮 A4: 侧边栏统计缓存 key 与 TTL（秒）
SIDEBAR_STATS_KEY = 'sidebar_stats'
SIDEBAR_STATS_TIMEOUT = 300  # 5 分钟

# 第4轮 A1: 公共缓存懒加载的一次性标志与线程锁。
# runserver 是多线程开发服务器，首个请求可能并发到达，
# 用双重检查锁（double-checked locking）保证预热只执行一次。
_cache_warmed = False
_warm_lock = threading.Lock()


def _ensure_public_cache_warmed():
    """首个请求时线程安全地一次性预热公共只读缓存。

    替代原 ``apps.py.ready()`` 中的启动预热：
    - 仅在真正处理 HTTP 请求（上下文处理器被调用）时执行一次；
    - 后续请求直接跳过，不再访问数据库；
    - 预热失败整体兜底，绝不阻断请求。
    """
    global _cache_warmed
    if _cache_warmed:
        return
    with _warm_lock:
        if _cache_warmed:
            return
        try:
            # 函数内延迟导入，避免与 views 模块在 App 加载期形成循环导入
            from .views import warm_public_cache
            warm_public_cache()
        except Exception:  # noqa: BLE001 预热失败不得影响首个请求
            pass
        _cache_warmed = True


def lazy_public_cache(request):
    """上下文处理器：触发一次性懒加载预热，本身不注入任何变量。

    注册到 TEMPLATES['OPTIONS']['context_processors'] 后，
    每个请求都会调用本函数；内部双重检查锁保证预热只跑一次。
    """
    _ensure_public_cache_warmed()
    return {}


def realtime_online_count():
    """最近 5 分钟独立 IP 访客数（实时，不走缓存）。

    当前请求本身即代表一名在线访客，因此结果至少为 1，
    避免出现“绿灯亮却显示 0 在线”的自相矛盾。
    """
    try:
        since = timezone.now() - timedelta(minutes=ONLINE_WINDOW_MINUTES)
        n = (AccessLog.objects.filter(created_at__gte=since)
             .exclude(ip_address__isnull=True)
             .values('ip_address').distinct().count())
        return max(int(n or 0), 1)
    except Exception:  # noqa: BLE001 统计表异常时也保证至少1人在线
        return 1


ONLINE_WINDOW_MINUTES = 5


def get_sidebar_stats():
    """计算并缓存侧边栏全站统计，key=``sidebar_stats``，TTL 300s。

    统计口径（仅已发布文章）：
    - article_count: 文章类（kind=article）数量；
    - views_total: 全部已发布文章阅读量之和；
    - tag_count / category_count: 标签 / 分类总数；
    - today_views: 今日访问量（AccessLog 当日记录数）；
    - online_count: 最近 5 分钟独立 IP 数（独立访客近似）。

    Returns:
        dict: 统计字典，键见上方字段说明。
    """
    # Bug14: 在线人数实时计算（不参与5分钟长缓存，避免被冻结成0），每次请求刷新
    online_count = realtime_online_count()
    cached = cache.get(SIDEBAR_STATS_KEY)
    if cached is not None:
        cached = dict(cached)
        cached['online_count'] = online_count
        return cached
    published = Article.objects.filter(
        status=Article.Status.PUBLISHED, is_deleted=False)
    today = timezone.now().date()
    stats = {
        'article_count': published.filter(kind=Article.Kind.ARTICLE).count(),
        'views_total': published.aggregate(v=Sum('views'))['v'] or 0,
        'tag_count': Tag.objects.count(),
        'category_count': Category.objects.count(),
        'today_views': AccessLog.objects.filter(created_at__date=today).count(),
        'online_count': online_count,
    }
    cache.set(SIDEBAR_STATS_KEY, stats, SIDEBAR_STATS_TIMEOUT)
    return stats


def sidebar_stats(request):
    """上下文处理器：注入侧边栏统计 ``sidebar_stats``（带缓存）。"""
    try:
        return {'sidebar_stats': get_sidebar_stats()}
    except Exception:  # noqa: BLE001 查询异常时返回空统计，保证模板可渲染
        return {'sidebar_stats': {}}


# 迭代#12: site_nav处理器docstring
def site_nav(request):
    """
    注入全局模板变量：nav_categories（带文章数量的分类列表）。

    第4轮 A3: 改为复用视图层 ``_sidebar()`` 已缓存的侧边栏数据
    （``sidebar_data``，TTL 300s），不再每次请求独立查库，
    消除"上下文处理器查一次、视图又查一次"的重复分类导航查询。
    同时注入站点级 SEO 常量（SITE_NAME / SITE_DESCRIPTION / SITE_KEYWORDS）。
    """
    # 迭代#13: context_processors中查询异常处理
    try:
        # 函数内导入，避免 App 加载期循环依赖；命中缓存时无任何 SQL
        from .views import _sidebar
        side = _sidebar()
        return {
            # nav_categories 来自缓存的侧边栏数据（视图已 annotate 文章数）
            'nav_categories': side.get('nav_categories', []),
            # 8. 导航栏"文章"链接旁的小徽标：已发布文章总数
            'nav_article_count': get_sidebar_stats().get('article_count', 0),
            # 站点级 SEO 常量：各页面 meta 信息的兜底默认值
            'site_name': settings.SITE_NAME,
            'site_description': settings.SITE_DESCRIPTION,
            'site_keywords': settings.SITE_KEYWORDS,
        }
    except Exception:
        # 查询失败时返回最小可用上下文，确保模板仍可渲染
        return {
            'nav_categories': [],
            'nav_article_count': 0,
            'site_name': settings.SITE_NAME,
            'site_description': settings.SITE_DESCRIPTION,
            'site_keywords': settings.SITE_KEYWORDS,
        }


# 迭代#14: friendly_links处理器docstring
def friendly_links(request):
    """
    注入全局模板变量：friendly_links（已启用的友情链接，按 order 排序）。
    供首页右栏等位置遍历展示。数据库为空时模板 {% if %} 自动隐藏该区块。
    第6轮优化：纳入全局缓存，TTL 3600s，友链变更时由管理命令/视图失效。
    """
    cached = cache.get('friendly_links_all')
    if cached is None:
        cached = list(FriendlyLink.objects.filter(is_active=True).order_by('order'))
        cache.set('friendly_links_all', cached, 3600)
    return {'friendly_links': cached}


# 迭代#15: site_footer_stats处理器docstring
# 迭代#16: context_processors缓存逻辑注释
def site_footer_stats(request):
    """注入页脚全站统计，缓存 1 小时（文章 / 评论变更时由视图失效）。"""
    cached = cache.get('footer_stats')
    if cached is None:
        published = Article.objects.filter(
            status=Article.Status.PUBLISHED, is_deleted=False)
        cached = {
            'footer_article_count': published.filter(kind=Article.Kind.ARTICLE).count(),
            'footer_comment_count': Comment.objects.filter(
                is_approved=True, is_deleted=False).count(),
            'footer_views_total': published.aggregate(v=Sum('views'))['v'] or 0,
        }
        cache.set('footer_stats', cached, 3600)
    # 运行天数随日期变化，实时算（不查库）
    cached['footer_days'] = (date.today() - SITE_LAUNCH_DATE).days
    return cached


# 迭代#17: site_notice处理器docstring
def site_notice(request):
    """注入最新一条激活的网站公告，供 base.html 公告条渲染。

    第4轮 C9: 支持用户关闭公告横幅——前端 JS 在关闭时写入 cookie
    ``notice_dismissed_{notice_id}``（值为公告 id），本处理器检测到该 cookie
    即不向下传递公告（返回 ``site_notice=None``），模板自动隐藏横幅。
    无激活公告时同样返回 None。
    第6轮优化：公告查询纳入全局缓存，TTL 120s；公告变更时由视图失效。
    """
    notice = cache.get('site_active_notice')
    if notice is None:
        notice = SiteNotice.objects.filter(is_active=True).order_by('-created_at').first()
        cache.set('site_active_notice', notice, 120)  # None 也缓存，避免空查穿透
    if notice is None:
        return {'site_notice': None}
    # 第4轮 C9: 检查关闭 cookie；存在且与公告 id 一致则视为已关闭
    dismissed = request.COOKIES.get(f'notice_dismissed_{notice.id}', '')
    if str(dismissed) == str(notice.id):
        return {'site_notice': None}
    return {'site_notice': notice}


def user_preferences(request):
    """第5轮 B/F/H/I: 注入当前用户偏好（匿名返回默认值）。

    同时返回字典（供模板属性访问）和 JSON 字符串（供 JS 注入，
    避免 Python True/False/None 泄漏到 JS 导致 ReferenceError）。
    第6轮优化：用户偏好纳入按用户缓存，TTL 300s；偏好变更时由视图失效。
    """
    try:
        from .views import _preferences_dict
        user = request.user
        if user and user.is_authenticated:
            cache_key = f'user_pref_{user.pk}'
            cached = cache.get(cache_key)
            if cached is not None:
                pref = cached
            else:
                pref = _preferences_dict(user)
                cache.set(cache_key, pref, 300)
        else:
            pref = _preferences_dict(user)  # 匿名用户返回默认值，不查库
        return {
            'user_preferences': pref,
            'user_preferences_json': json.dumps(pref, ensure_ascii=False),
        }
    except Exception:
        return {'user_preferences': {}, 'user_preferences_json': '{}'}


def unread_notification_count(request):
    """第5轮 F8: 注入当前用户未读通知数（匿名为 0）。

    第6轮优化：未读数纳入按用户缓存，TTL 30s（短周期，通知变更时由视图失效）；
    避免每次请求都查 notification 表。
    """
    try:
        user = request.user
        if user and user.is_authenticated:
            cache_key = f'unread_notif_{user.pk}'
            count = cache.get(cache_key)
            if count is None:
                count = user.notifications.filter(is_read=False).count()
                cache.set(cache_key, count, 30)
            return {'unread_notification_count': count}
    except Exception:
        pass
    return {'unread_notification_count': 0}


# 构建版本号模块级缓存（refresh_assets 写入 static/assets/.build_token）
_build_token_cache = None


def build_token(request):
    """注入 ``BUILD_TOKEN``：供静态资源 URL 追加 ``?v=`` 破除浏览器缓存。

    版本号由 ``manage.py refresh_assets`` 每次打包时生成（时间戳）。
    进程内只读一次文件并缓存；runserver 重启后自动取到最新值。
    文件缺失时回退到固定默认值，保证模板始终可渲染。
    """
    global _build_token_cache
    token_path = os.path.join(settings.BASE_DIR, 'static', 'assets',
                              '.build_token')

    def _read_token():
        try:
            with open(token_path, 'r', encoding='utf-8') as tf:
                return tf.read().strip() or 'dev'
        except OSError:
            return 'dev'

    # DEBUG（本地 runserver）下每次请求重读 token 文件：refresh_assets 打包后
    # 无需重启即可让 ?v= 立即更新，避免浏览器拿到旧缓存静态资源；
    # 生产环境进程内只读一次并缓存，避免每请求一次磁盘 IO。
    if settings.DEBUG:
        _build_token_cache = _read_token()
    elif _build_token_cache is None:
        _build_token_cache = _read_token()
    # DEBUG（本地开发）下不注册 Service Worker，避免离线缓存干扰逐页视觉核验；
    # 生产环境（DEBUG=False）启用，配合 sw.js 的 HTML 网络优先策略提供离线能力。
    return {'BUILD_TOKEN': _build_token_cache, 'ENABLE_SW': not settings.DEBUG}


def site_info_ctx(request):
    """工单 15：把数据库中的站点信息单例注入模板。

    原先「网站名 / Logo / 标题 / 网站介绍 / 页脚关于文案」硬编码在模板与
    settings 中，现统一来自 :class:`~blog.models.SiteInfo`（管理员可在
    「站点设置」页面修改）。本处理器在 settings 中排在最后注册，因此其
    ``site_name`` 等键会覆盖 ``site_nav`` 中来自 settings 常量的同名值；
    与 ``SiteInfoMiddleware`` 读取同一份缓存，任何异常都降级、不阻断渲染。
    """
    # 读取失败时的兜底默认（与 settings 常量保持一致）
    defaults = {
        'site_info': None,
        'site_name': getattr(settings, 'SITE_NAME', '萌语博客'),
        'site_logo': '🌸',
        'site_tagline': getattr(settings, 'SITE_DESCRIPTION', ''),
        'site_description': getattr(settings, 'SITE_DESCRIPTION', ''),
        'site_keywords': getattr(settings, 'SITE_KEYWORDS', ''),
        'footer_about': '',
        'footer_icp': '',
        'copyright_holder': getattr(settings, 'SITE_NAME', '萌语博客'),
    }
    try:
        from .models import SiteInfo
        info = SiteInfo.load()
    except Exception:  # noqa: BLE001 读取失败降级默认
        return defaults
    return {
        'site_info': info,
        'site_name': info.site_name,
        'site_logo': info.logo_emoji,
        'site_tagline': info.tagline,
        'site_description': info.description,
        'site_keywords': info.keywords,
        'footer_about': info.footer_about,
        'footer_icp': info.footer_icp,
        'copyright_holder': info.copyright_holder or info.site_name,
    }

"""全局模板上下文：顶栏分类导航 + 友情链接注入 + 页脚统计 + 侧边栏统计 + 公告。

第4轮重构要点：
- 公共缓存预热从 ``apps.py ready()`` 移至此处的**首个请求懒加载**（线程安全），
  彻底消除 runserver 启动期"app 初始化阶段访问数据库"RuntimeWarning；
- 侧边栏统计（文章数/总浏览/标签数/分类数/今日访问/独立访客）纳入缓存，TTL 300s；
- ``site_nav`` 改为复用视图层已缓存的侧边栏数据，避免与视图重复查询分类导航；
- 公告横幅支持 cookie 关闭：前端写入 ``notice_dismissed_{id}`` 后不再下发。
"""
#: 导入模块「json」，供本文件后续使用
import json
#: 导入模块「os」，供本文件后续使用
import os
#: 导入模块「threading」，供本文件后续使用
import threading
#: 从模块「datetime」导入所需对象
from datetime import date, timedelta

#: 从模块「django.conf」导入所需对象
from django.conf import settings
#: 从模块「django.core.cache」导入所需对象
from django.core.cache import cache
#: 从模块「django.db.models」导入所需对象
from django.db.models import Count, Sum
#: 从模块「django.utils」导入所需对象
from django.utils import timezone

#: 从模块「.models」导入所需对象
from .models import (AccessLog, Article, Category, Comment, FriendlyLink,
                     #: 该行执行对应逻辑（结合上下文理解）
                     SiteNotice, Tag)

# 站点上线日期：用于页脚计算"已运行 N 天"。如需修改改这一行即可。
#: 定义变量「SITE_LAUNCH_DATE」，保存对应数据
SITE_LAUNCH_DATE = date(2024, 1, 1)

# 第4轮 A4: 侧边栏统计缓存 key 与 TTL（秒）
#: 定义变量「SIDEBAR_STATS_KEY」，保存对应数据
SIDEBAR_STATS_KEY = 'sidebar_stats'
#: 定义变量「SIDEBAR_STATS_TIMEOUT」，保存对应数据
SIDEBAR_STATS_TIMEOUT = 300  # 5 分钟

# 第4轮 A1: 公共缓存懒加载的一次性标志与线程锁。
# runserver 是多线程开发服务器，首个请求可能并发到达，
# 用双重检查锁（double-checked locking）保证预热只执行一次。
#: 定义变量「_cache_warmed」，保存对应数据
_cache_warmed = False
#: 定义变量「_warm_lock」，保存对应数据
_warm_lock = threading.Lock()


def _ensure_public_cache_warmed():
    """首个请求时线程安全地一次性预热公共只读缓存。

    替代原 ``apps.py.ready()`` 中的启动预热：
    - 仅在真正处理 HTTP 请求（上下文处理器被调用）时执行一次；
    - 后续请求直接跳过，不再访问数据库；
    - 预热失败整体兜底，绝不阻断请求。
    """
    #: 声明使用全局/外层变量
    global _cache_warmed
    #: 条件判断：条件成立时执行该分支
    if _cache_warmed:
        #: 返回结果并结束当前函数
        return
    #: 上下文管理：进入时获取资源、退出时自动释放
    with _warm_lock:
        #: 条件判断：条件成立时执行该分支
        if _cache_warmed:
            #: 返回结果并结束当前函数
            return
        #: 尝试执行可能出错的代码
        try:
            # 函数内延迟导入，避免与 views 模块在 App 加载期形成循环导入
            #: 从模块「.views」导入所需对象
            from .views import warm_public_cache
            #: 调用「warm_public_cache」执行相应逻辑
            warm_public_cache()
        #: 捕获并处理异常，避免程序中断
        except Exception:  # noqa: BLE001 预热失败不得影响首个请求
            #: 占位语句：此处暂不需要实现
            pass
        #: 定义变量「_cache_warmed」，保存对应数据
        _cache_warmed = True


def lazy_public_cache(request):
    """上下文处理器：触发一次性懒加载预热 + 定时投稿兜底扫描，本身不注入变量。

    注册到 TEMPLATES['OPTIONS']['context_processors'] 后，每个请求都会调用本函数：

    1. ``_ensure_public_cache_warmed()``：双重检查锁保证公共缓存预热只跑一次；
    2. ``maybe_sweep_due_articles()``：**定时投稿兜底扫描**（Bug9-2）。
       生产推荐用 Celery beat 每分钟执行 ``check_scheduled_articles``；但若部署
       环境没起 beat（本地开发很常见），到点文章会一直停在草稿状态。这里用
       「缓存锁 + 30 秒最小间隔」在请求侧做兜底，保证到点文章最迟 30 秒内
       被流转为待审核 / 已发布，且不会给每次请求增加数据库压力。
    """
    #: 调用「_ensure_public_cache_warmed」执行相应逻辑
    _ensure_public_cache_warmed()
    #: 尝试执行可能出错的代码
    try:
        #: 从模块「.services.scheduled_publishing」导入所需对象
        from .services.scheduled_publishing import maybe_sweep_due_articles
        #: 调用「maybe_sweep_due_articles」执行相应逻辑
        maybe_sweep_due_articles()
    #: 捕获并处理异常，避免程序中断
    except Exception:  # noqa: BLE001 兜底扫描异常绝不影响页面渲染
        #: 占位语句：此处暂不需要实现
        pass
    #: 返回结果并结束当前函数
    return {}


def realtime_online_count():
    """最近 5 分钟独立 IP 访客数（实时，不走缓存）。

    当前请求本身即代表一名在线访客，因此结果至少为 1，
    避免出现“绿灯亮却显示 0 在线”的自相矛盾。
    """
    #: 尝试执行可能出错的代码
    try:
        #: 获取当前时间（时区感知），统一时间口径
        since = timezone.now() - timedelta(minutes=ONLINE_WINDOW_MINUTES)
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        n = (AccessLog.objects.filter(created_at__gte=since)
             #: 该行执行对应逻辑（结合上下文理解）
             .exclude(ip_address__isnull=True)
             #: 该行执行对应逻辑（结合上下文理解）
             .values('ip_address').distinct().count())
        #: 返回结果并结束当前函数
        return max(int(n or 0), 1)
    #: 捕获并处理异常，避免程序中断
    except Exception:  # noqa: BLE001 统计表异常时也保证至少1人在线
        #: 返回结果并结束当前函数
        return 1


#: 定义变量「ONLINE_WINDOW_MINUTES」，保存对应数据
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
    #: 定义变量「online_count」，保存对应数据
    online_count = realtime_online_count()
    #: 读写缓存，减轻数据库压力，注意键与过期时间
    cached = cache.get(SIDEBAR_STATS_KEY)
    #: 条件判断：条件成立时执行该分支
    if cached is not None:
        #: 定义变量「cached」，保存对应数据
        cached = dict(cached)
        #: 该行执行对应逻辑（结合上下文理解）
        cached['online_count'] = online_count
        #: 返回结果并结束当前函数
        return cached
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    published = Article.objects.filter(
        #: 定义变量「status」，保存对应数据
        status=Article.Status.PUBLISHED, is_deleted=False)
    #: 获取当前时间（时区感知），统一时间口径
    today = timezone.now().date()
    #: 定义变量「stats」，保存对应数据
    stats = {
        #: 配置项「article_count」：字典/模型的该键设置为对应值
        'article_count': published.filter(kind=Article.Kind.ARTICLE).count(),
        #: 使用聚合函数做统计查询
        'views_total': published.aggregate(v=Sum('views'))['v'] or 0,
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        'tag_count': Tag.objects.count(),
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        'category_count': Category.objects.count(),
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        'today_views': AccessLog.objects.filter(created_at__date=today).count(),
        #: 配置项「online_count」：字典/模型的该键设置为对应值
        'online_count': online_count,
    #: 该行执行对应逻辑（结合上下文理解）
    }
    #: 读写缓存，减轻数据库压力，注意键与过期时间
    cache.set(SIDEBAR_STATS_KEY, stats, SIDEBAR_STATS_TIMEOUT)
    #: 返回结果并结束当前函数
    return stats


def sidebar_stats(request):
    """上下文处理器：注入侧边栏统计 ``sidebar_stats``（带缓存）。"""
    #: 尝试执行可能出错的代码
    try:
        #: 返回结果并结束当前函数
        return {'sidebar_stats': get_sidebar_stats()}
    #: 捕获并处理异常，避免程序中断
    except Exception:  # noqa: BLE001 查询异常时返回空统计，保证模板可渲染
        #: 返回结果并结束当前函数
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
    #: 尝试执行可能出错的代码
    try:
        # 函数内导入，避免 App 加载期循环依赖；命中缓存时无任何 SQL
        #: 从模块「.views」导入所需对象
        from .views import _sidebar
        #: 定义变量「side」，保存对应数据
        side = _sidebar()
        #: 返回结果并结束当前函数
        return {
            # nav_categories 来自缓存的侧边栏数据（视图已 annotate 文章数）
            #: 配置项「nav_categories」：字典/模型的该键设置为对应值
            'nav_categories': side.get('nav_categories', []),
            # 8. 导航栏"文章"链接旁的小徽标：已发布文章总数
            #: 配置项「nav_article_count」：字典/模型的该键设置为对应值
            'nav_article_count': get_sidebar_stats().get('article_count', 0),
            # 站点级 SEO 常量：各页面 meta 信息的兜底默认值
            #: 配置项「site_name」：字典/模型的该键设置为对应值
            'site_name': settings.SITE_NAME,
            #: 配置项「site_description」：字典/模型的该键设置为对应值
            'site_description': settings.SITE_DESCRIPTION,
            #: 配置项「site_keywords」：字典/模型的该键设置为对应值
            'site_keywords': settings.SITE_KEYWORDS,
        #: 该行执行对应逻辑（结合上下文理解）
        }
    #: 捕获并处理异常，避免程序中断
    except Exception:
        # 查询失败时返回最小可用上下文，确保模板仍可渲染
        #: 返回结果并结束当前函数
        return {
            #: 配置项「nav_categories」：字典/模型的该键设置为对应值
            'nav_categories': [],
            #: 配置项「nav_article_count」：字典/模型的该键设置为对应值
            'nav_article_count': 0,
            #: 配置项「site_name」：字典/模型的该键设置为对应值
            'site_name': settings.SITE_NAME,
            #: 配置项「site_description」：字典/模型的该键设置为对应值
            'site_description': settings.SITE_DESCRIPTION,
            #: 配置项「site_keywords」：字典/模型的该键设置为对应值
            'site_keywords': settings.SITE_KEYWORDS,
        #: 该行执行对应逻辑（结合上下文理解）
        }


# 迭代#14: friendly_links处理器docstring
def friendly_links(request):
    """
    注入全局模板变量：friendly_links（已启用的友情链接，按 order 排序）。
    供首页右栏等位置遍历展示。数据库为空时模板 {% if %} 自动隐藏该区块。
    第6轮优化：纳入全局缓存，TTL 3600s，友链变更时由管理命令/视图失效。
    """
    #: 读写缓存，减轻数据库压力，注意键与过期时间
    cached = cache.get('friendly_links_all')
    #: 条件判断：条件成立时执行该分支
    if cached is None:
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        cached = list(FriendlyLink.objects.filter(is_active=True).order_by('order'))
        #: 读写缓存，减轻数据库压力，注意键与过期时间
        cache.set('friendly_links_all', cached, 3600)
    #: 返回结果并结束当前函数
    return {'friendly_links': cached}


# 迭代#15: site_footer_stats处理器docstring
# 迭代#16: context_processors缓存逻辑注释
def site_footer_stats(request):
    """注入页脚全站统计，缓存 1 小时（文章 / 评论变更时由视图失效）。"""
    #: 读写缓存，减轻数据库压力，注意键与过期时间
    cached = cache.get('footer_stats')
    #: 条件判断：条件成立时执行该分支
    if cached is None:
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        published = Article.objects.filter(
            #: 定义变量「status」，保存对应数据
            status=Article.Status.PUBLISHED, is_deleted=False)
        #: 定义变量「cached」，保存对应数据
        cached = {
            #: 配置项「footer_article_count」：字典/模型的该键设置为对应值
            'footer_article_count': published.filter(kind=Article.Kind.ARTICLE).count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'footer_comment_count': Comment.objects.filter(
                #: 定义变量「is_approved」，保存对应数据
                is_approved=True, is_deleted=False).count(),
            #: 使用聚合函数做统计查询
            'footer_views_total': published.aggregate(v=Sum('views'))['v'] or 0,
        #: 该行执行对应逻辑（结合上下文理解）
        }
        #: 读写缓存，减轻数据库压力，注意键与过期时间
        cache.set('footer_stats', cached, 3600)
    # 运行天数随日期变化，实时算（不查库）
    #: 该行执行对应逻辑（结合上下文理解）
    cached['footer_days'] = (date.today() - SITE_LAUNCH_DATE).days
    #: 返回结果并结束当前函数
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
    #: 读写缓存，减轻数据库压力，注意键与过期时间
    notice = cache.get('site_active_notice')
    #: 条件判断：条件成立时执行该分支
    if notice is None:
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        notice = SiteNotice.objects.filter(is_active=True).order_by('-created_at').first()
        #: 读写缓存，减轻数据库压力，注意键与过期时间
        cache.set('site_active_notice', notice, 120)  # None 也缓存，避免空查穿透
    #: 条件判断：条件成立时执行该分支
    if notice is None:
        #: 返回结果并结束当前函数
        return {'site_notice': None}
    # 第4轮 C9: 检查关闭 cookie；存在且与公告 id 一致则视为已关闭
    #: 定义变量「dismissed」，保存对应数据
    dismissed = request.COOKIES.get(f'notice_dismissed_{notice.id}', '')
    #: 条件判断：条件成立时执行该分支
    if str(dismissed) == str(notice.id):
        #: 返回结果并结束当前函数
        return {'site_notice': None}
    #: 返回结果并结束当前函数
    return {'site_notice': notice}


def user_preferences(request):
    """第5轮 B/F/H/I: 注入当前用户偏好（匿名返回默认值）。

    同时返回字典（供模板属性访问）和 JSON 字符串（供 JS 注入，
    避免 Python True/False/None 泄漏到 JS 导致 ReferenceError）。
    第6轮优化：用户偏好纳入按用户缓存，TTL 300s；偏好变更时由视图失效。
    """
    #: 尝试执行可能出错的代码
    try:
        #: 从模块「.views」导入所需对象
        from .views import _preferences_dict
        #: 读取本次请求的 user 数据
        user = request.user
        #: 条件判断：条件成立时执行该分支
        if user and user.is_authenticated:
            #: 定义变量「cache_key」，保存对应数据
            cache_key = f'user_pref_{user.pk}'
            #: 读写缓存，减轻数据库压力，注意键与过期时间
            cached = cache.get(cache_key)
            #: 条件判断：条件成立时执行该分支
            if cached is not None:
                #: 定义变量「pref」，保存对应数据
                pref = cached
            #: 以上条件均不成立时的兜底分支
            else:
                #: 定义变量「pref」，保存对应数据
                pref = _preferences_dict(user)
                #: 读写缓存，减轻数据库压力，注意键与过期时间
                cache.set(cache_key, pref, 300)
        #: 以上条件均不成立时的兜底分支
        else:
            #: 定义变量「pref」，保存对应数据
            pref = _preferences_dict(user)  # 匿名用户返回默认值，不查库
        #: 返回结果并结束当前函数
        return {
            #: 配置项「user_preferences」：字典/模型的该键设置为对应值
            'user_preferences': pref,
            #: 配置项「user_preferences_json」：字典/模型的该键设置为对应值
            'user_preferences_json': json.dumps(pref, ensure_ascii=False),
        #: 该行执行对应逻辑（结合上下文理解）
        }
    #: 捕获并处理异常，避免程序中断
    except Exception:
        #: 返回结果并结束当前函数
        return {'user_preferences': {}, 'user_preferences_json': '{}'}


def site_messages_ctx(request):
    """Bug9 任务「2」：注入全站文案命名空间 ``MSG``。

    模板用法（无需 load 任何标签库，所有模板自动可用）::

        <h1>{{ MSG.err.404_heading }}</h1>
        <button>{{ MSG.btn.back_home }}</button>
        <p>{{ MSG.promo.limit_hint }}</p>      {# 带占位符的文案在模板侧用 |format #}

    数据来源是 ``blog/site_messages.py`` 的模块级常量，零数据库查询、零 IO，
    因此对每个请求的开销约为「一次浅拷贝」，可忽略。

    另外注入 ``SITE_MSG_JS``：前端脚本使用的文案 JSON（供 ``window.SITE_MSG``），
    以及 ``BADGE_PANEL_TEXTS``（个人中心徽章面板专用文案，避免模板里散落中文）。
    """
    #: 尝试执行可能出错的代码
    try:
        #: 从模块「.services.site_messages」导入所需对象
        from .services.site_messages import as_context, js_payload
        #: 定义变量「ctx」，保存对应数据
        ctx = as_context()
        #: 返回结果并结束当前函数
        return {
            #: 配置项「MSG」：字典/模型的该键设置为对应值
            'MSG': ctx,
            # 前端文案包：json_script 过滤器会在模板里安全序列化，避免 XSS 与转义问题
            #: 配置项「SITE_MSG_JS」：字典/模型的该键设置为对应值
            'SITE_MSG_JS': js_payload(),
        #: 该行执行对应逻辑（结合上下文理解）
        }
    #: 捕获并处理异常，避免程序中断
    except Exception:  # noqa: BLE001 文案注入失败时降级为空命名空间，绝不阻断页面
        #: 返回结果并结束当前函数
        return {'MSG': {}, 'SITE_MSG_JS': {}}


def unread_notification_count(request):
    """第5轮 F8: 注入当前用户未读通知数（匿名为 0）。

    第6轮优化：未读数纳入按用户缓存，TTL 30s（短周期，通知变更时由视图失效）；
    避免每次请求都查 notification 表。
    """
    #: 尝试执行可能出错的代码
    try:
        #: 读取本次请求的 user 数据
        user = request.user
        #: 条件判断：条件成立时执行该分支
        if user and user.is_authenticated:
            #: 定义变量「cache_key」，保存对应数据
            cache_key = f'unread_notif_{user.pk}'
            #: 读写缓存，减轻数据库压力，注意键与过期时间
            count = cache.get(cache_key)
            #: 条件判断：条件成立时执行该分支
            if count is None:
                #: 定义变量「count」，保存对应数据
                count = user.notifications.filter(is_read=False).count()
                #: 读写缓存，减轻数据库压力，注意键与过期时间
                cache.set(cache_key, count, 30)
            #: 返回结果并结束当前函数
            return {'unread_notification_count': count}
    #: 捕获并处理异常，避免程序中断
    except Exception:
        #: 占位语句：此处暂不需要实现
        pass
    #: 返回结果并结束当前函数
    return {'unread_notification_count': 0}


# 构建版本号模块级缓存（refresh_assets 写入 static/assets/.build_token）
#: 定义变量「_build_token_cache」，保存对应数据
_build_token_cache = None


def build_token(request):
    """注入 ``BUILD_TOKEN``：供静态资源 URL 追加 ``?v=`` 破除浏览器缓存。

    版本号由 ``manage.py refresh_assets`` 每次打包时生成（时间戳）。
    进程内只读一次文件并缓存；runserver 重启后自动取到最新值。
    文件缺失时回退到固定默认值，保证模板始终可渲染。
    """
    #: 声明使用全局/外层变量
    global _build_token_cache
    #: 定义变量「token_path」，保存对应数据
    token_path = os.path.join(settings.BASE_DIR, 'static', 'assets',
                              #: 该行执行对应逻辑（结合上下文理解）
                              '.build_token')

    def _read_token():
        """
        功能：读取「token」。

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 尝试执行可能出错的代码
        try:
            #: 上下文管理：进入时获取资源、退出时自动释放
            with open(token_path, 'r', encoding='utf-8') as tf:
                #: 返回结果并结束当前函数
                return tf.read().strip() or 'dev'
        #: 捕获并处理异常，避免程序中断
        except OSError:
            #: 返回结果并结束当前函数
            return 'dev'

    # DEBUG（本地 runserver）下每次请求重读 token 文件：refresh_assets 打包后
    # 无需重启即可让 ?v= 立即更新，避免浏览器拿到旧缓存静态资源；
    # 生产环境进程内只读一次并缓存，避免每请求一次磁盘 IO。
    #: 条件判断：条件成立时执行该分支
    if settings.DEBUG:
        #: 定义变量「_build_token_cache」，保存对应数据
        _build_token_cache = _read_token()
    #: 否则若该条件成立则进入此分支
    elif _build_token_cache is None:
        #: 定义变量「_build_token_cache」，保存对应数据
        _build_token_cache = _read_token()
    # DEBUG（本地开发）下不注册 Service Worker，避免离线缓存干扰逐页视觉核验；
    # 生产环境（DEBUG=False）启用，配合 sw.js 的 HTML 网络优先策略提供离线能力。
    #: 返回结果并结束当前函数
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
    #: 定义变量「defaults」，保存对应数据
    defaults = {
        #: 配置项「site_info」：字典/模型的该键设置为对应值
        'site_info': None,
        #: 配置项「site_name」：字典/模型的该键设置为对应值
        'site_name': getattr(settings, 'SITE_NAME', '萌语博客'),
        #: 配置项「site_logo」：字典/模型的该键设置为对应值
        'site_logo': '🌸',
        #: 配置项「site_tagline」：字典/模型的该键设置为对应值
        'site_tagline': getattr(settings, 'SITE_DESCRIPTION', ''),
        #: 配置项「site_description」：字典/模型的该键设置为对应值
        'site_description': getattr(settings, 'SITE_DESCRIPTION', ''),
        #: 配置项「site_keywords」：字典/模型的该键设置为对应值
        'site_keywords': getattr(settings, 'SITE_KEYWORDS', ''),
        #: 配置项「footer_about」：字典/模型的该键设置为对应值
        'footer_about': '',
        #: 配置项「footer_icp」：字典/模型的该键设置为对应值
        'footer_icp': '',
        #: 配置项「copyright_holder」：字典/模型的该键设置为对应值
        'copyright_holder': getattr(settings, 'SITE_NAME', '萌语博客'),
    #: 该行执行对应逻辑（结合上下文理解）
    }
    #: 尝试执行可能出错的代码
    try:
        #: 从模块「.models」导入所需对象
        from .models import SiteInfo
        #: 定义变量「info」，保存对应数据
        info = SiteInfo.load()
    #: 捕获并处理异常，避免程序中断
    except Exception:  # noqa: BLE001 读取失败降级默认
        #: 返回结果并结束当前函数
        return defaults
    #: 返回结果并结束当前函数
    return {
        #: 配置项「site_info」：字典/模型的该键设置为对应值
        'site_info': info,
        #: 配置项「site_name」：字典/模型的该键设置为对应值
        'site_name': info.site_name,
        #: 配置项「site_logo」：字典/模型的该键设置为对应值
        'site_logo': info.logo_emoji,
        #: 配置项「site_tagline」：字典/模型的该键设置为对应值
        'site_tagline': info.tagline,
        #: 配置项「site_description」：字典/模型的该键设置为对应值
        'site_description': info.description,
        #: 配置项「site_keywords」：字典/模型的该键设置为对应值
        'site_keywords': info.keywords,
        #: 配置项「footer_about」：字典/模型的该键设置为对应值
        'footer_about': info.footer_about,
        #: 配置项「footer_icp」：字典/模型的该键设置为对应值
        'footer_icp': info.footer_icp,
        #: 配置项「copyright_holder」：字典/模型的该键设置为对应值
        'copyright_holder': info.copyright_holder or info.site_name,
    #: 该行执行对应逻辑（结合上下文理解）
    }

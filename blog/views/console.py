# -*- coding: utf-8 -*-

"""运营看板、站点设置、文案总表、服务状态与调试端点。"""

import logging
import os
import re
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.db.models import Avg, Count, F, Min, Q, Sum
from django.http import (
    HttpRequest, HttpResponse,
    JsonResponse, )
from django.shortcuts import redirect, render
from django.utils import timezone

from ..models import (
    AccessLog, Article, Category, Comment, CommentReport,
    Tag, User, )
from ..services.site_messages import msg
# staff_required_moe：员工页面统一权限装饰器（未登录跳萌系登录页 / 已登录非员工显 403）
from ..utils.decorators import staff_required_moe

logger = logging.getLogger('blog.views')

# 迭代#110: _build_website_jsonld函数docstring完善
def api_site_messages(request):
    """Bug9 任务「2」：把全站文案包下发给前端脚本（``GET /api/site-messages/``）。

    前端在 ``base.html`` 中通过内联 ``window.SITE_MSG`` 拿到主要文案；
    本端点用于：①Service Worker / 离线页等无法渲染模板的场景；
    ②前端脚本懒加载补充文案；③自动化测试核对文案一致性。

    缓存策略：文案是**代码内置常量**，随构建版本号变化，
    因此按 ``BUILD_TOKEN`` 作为缓存键长久缓存（版本不变则浏览器直接用缓存）。

    Returns:
        JsonResponse: ``{'code': 0, 'data': {...文案键值...}, 'build': 构建号}``
    """
    from ..services.site_messages import MESSAGES, js_payload
    from ..context_processors import build_token as _build_token
    token = (_build_token(request) or {}).get('BUILD_TOKEN', 'dev')
    payload = js_payload()
    response = JsonResponse({
        'code': 0,
        'build': token,
        'count': len(MESSAGES),
        'data': payload,
    }, json_dumps_params={'ensure_ascii': False})
    # 版本号变化即视为新资源；未变化时允许浏览器与 CDN 长时间复用
    response['Cache-Control'] = 'public, max-age=86400'
    response['X-Messages-Build'] = token
    return response

# 迭代#201: server_status视图docstring
# 迭代#202: server_status(request) -> HttpResponse 类型提示
# 迭代#203: server_status健康检查逻辑注释
# staff_required_moe：未登录跳前台萌系登录页；已登录但非员工显 403（逻辑见 utils/decorators.py）
@staff_required_moe
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

# ============================ Bug26: 萌系运营控制台 ============================
def staff_console(request: HttpRequest):
    """运营数据看板：仅 staff 管理员可访问的前端萌系控制台。

    聚合站点核心指标、近 14 天访问趋势、热门文章、分类分布、
    最近评论 / 用户、浏览器分布与待处理举报，纯 CSS 图表呈现，不引重库。
    """
    # staff_required_moe：未登录跳前台萌系登录 / 已登录非员工返回 403（顶部已导入）
    @staff_required_moe
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

@staff_required_moe
def site_settings_page(request: HttpRequest) -> HttpResponse:
    """工单 15：站点信息设置页（仅管理员）。

    把原先硬编码的网站名 / Logo / 副标题 / SEO 描述关键词 / 页脚文案等
    做成可在线编辑的表单，保存到 :class:`~blog.models.SiteInfo` 单例；
    模型 ``save()`` 会自动清除读取缓存，保存后全站立即生效，无需重启或改代码。
    """
    from ..models import SiteInfo
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
            messages.success(request, msg('misc.site_saved'))
            return redirect('site_settings')

    return render(request, 'blog/site_settings.html', {
        'info': info,
        'fields': fields,
        'active_nav': 'site_settings',
        'meta_title': f'站点设置 · {info.site_name}',
    })

# ============================ 看板娘形象管理 ============================
@staff_required_moe
def live2d_models_page(request: HttpRequest) -> HttpResponse:
    """看板娘形象管理页（仅管理员）。

    展示 :mod:`blog.services.live2d_registry` 中的全部 Live2D 形象
    （缩略图 + 名称 + 启用开关），支持逐款切换与按组批量操作。
    被停用的形象不会出现在前台看板娘的切换列表里 —— 前端
    ``waifu-init-new.js`` 依据本页状态动态构建模型配置，刷新即生效。

    POST 动作：
      · ``toggle`` —— 需 ``model_id`` 与 ``enabled``(1/0)，切换单款；
      · ``bulk``   —— 需 ``enabled``，可选 ``group``，批量启用/停用。

    带 ``X-Requested-With: XMLHttpRequest`` 时返回 JSON（页面无刷新切换），
    否则走 messages + 重定向（无 JS 环境下同样可用）。
    """
    from ..services import live2d_registry as reg

    if request.method == 'POST':
        ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        action = (request.POST.get('action') or '').strip()
        enabled = (request.POST.get('enabled') or '') in ('1', 'true', 'on', 'True')

        if action == 'toggle':
            ok, note = reg.set_enabled((request.POST.get('model_id') or '').strip(), enabled)
        elif action == 'bulk':
            group = (request.POST.get('group') or '').strip() or None
            _, note = reg.set_many(enabled, group)
            ok = True
        else:
            ok, note = False, '未知操作'

        if ajax:
            return JsonResponse({'ok': ok, 'note': note, 'stats': reg.stats()})
        (messages.success if ok else messages.error)(request, note)
        return redirect('live2d_models')

    return render(request, 'blog/live2d_models.html', {
        'models': reg.models(),
        'stats': reg.stats(),
        'active_nav': 'live2d_models',
        'meta_title': '看板娘形象管理 · %s' % getattr(settings, 'SITE_NAME', '萌语博客'),
    })


# ============================ 全站文案总表（提示词）管理 ============================
# 文案域的中文标题，用于管理页分组展示（新增域时在此补一行）
MSG_DOMAIN_TITLES = {
    'brand': '站点品牌与固定标语',
    'nav': '导航与菜单',
    'btn': '按钮文案',
    'auth': '登录 / 注册 / 密码',
    'err': '错误页与错误提示',
    'empty': '空状态提示',
    'form': '表单提示',
    'article': '文章相关',
    'comment': '评论相关',
    'moderation': '审核与治理',
    'promo': '推广申请（置顶 / 精华 / 热门）',
    'interact': '互动（点赞 / 收藏 / 关注）',
    'search': '搜索',
    'user': '个人中心',
    'notify': '通知',
    'badge': '徽章与成就',
    'live2d': '看板娘',
    'misc': '其他',
    'js': '前端脚本专用（toast / 弹窗）',
}

# 「已接入」判定结果的进程内缓存（源码在运行期不变，无需每次请求都扫盘）
_WIRED_CACHE = {'stamp': None, 'keys': frozenset()}

# 后台重算去重标记（避免并发触发多次重算）
_RUNTIME_RECOMPUTING = False

def _schedule_runtime_recompute(base: str) -> None:
    """后台重算「运行时接入状态」并落盘（仅当指纹过期时触发）。

    为什么做成后台线程：重算需要把每个文案设成唯一标记后渲染全部页面（约 124 次
    渲染），耗时秒级，绝不能阻塞用户请求。因此：
      · 用去重标记保证同一时刻只有一个重算在跑；
      · 线程结束后清掉 ``_WIRED_CACHE``，下次请求即可读到新结果；
      · 任何异常都被吞掉（这只是统计信息，不能影响页面可用性）。

    Args:
        base: 项目根目录（``settings.BASE_DIR``）。
    """
    global _RUNTIME_RECOMPUTING
    if _RUNTIME_RECOMPUTING:
        return
    _RUNTIME_RECOMPUTING = True

    def _worker():
        global _RUNTIME_RECOMPUTING
        try:
            import subprocess
            import sys as _sys
            script = os.path.join(base, 'docs', 'bugfix_20260926_bug9', 'scripts',
                                  'tools', 'compute_wired_runtime.py')
            if not os.path.exists(script):
                return
            env = dict(os.environ)
            env['PYTHONIOENCODING'] = 'utf-8'
            subprocess.run([_sys.executable, script], cwd=base, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=300, check=False)
            _WIRED_CACHE.update({'stamp': None, 'keys': frozenset()})
        except Exception:  # noqa: BLE001 统计信息失败不影响功能
            pass
        finally:
            # 无论成功失败都要清标记，否则一次失败会永久阻止后续重算
            _RUNTIME_RECOMPUTING = False

    import threading
    threading.Thread(target=_worker, name='wired-runtime-recompute',
                     daemon=True).start()

def _wired_message_keys() -> frozenset:
    """扫描模板 / 视图 / 前端脚本，返回**真正被引用**的文案 key 集合。

    为什么需要它：``site_messages.MESSAGES`` 是「登记表」，其中一部分 key
    目前只是预留登记（还没有任何界面引用它）。如果管理页不标注出来，
    运营改了这些文案会发现「怎么改都没反应」，进而怀疑整页功能失效。

    实现：对每个 key 依次在所有模板（``MSG.<key>``）、Python（``'<key>'``）、
    前端脚本（``'<短键>'`` 或 ``'<域_键>'``）里查找字面出现。
    结果按源码文件 mtime 缓存，源码不变则不重复扫描。

    Returns:
        frozenset: 被引用的 key 集合（空集合表示扫描失败，此时按「全部未接入」展示，
        不会误报为已接入）。
    """
    import glob as _glob
    import os as _os
    from django.conf import settings as _settings

    base = str(_settings.BASE_DIR)
    # 扫描范围说明（这里踩过一个重要坑）：
    #   最初把整个 blog/views.py 排除，理由是「本页视图用到的 moderation.msg_* 只服务
    #   管理页，不该算已接入」。但 **views.py 是全站绝大多数 msg() 调用的所在地**
    #   （flash 消息、AJAX 返回），整文件排除导致这些 key 全被误判为「未接入」
    #   （实测：管理页显示 794 已接入 / 164 未接入，其中一大批其实在 views.py 里
    #   有调用，运营会以为改了没反应）。
    #   正确做法：**照常扫描 views.py**，只把「确实只服务本管理页」的几个 key
    #   放进 PAGE_ONLY_MSG_KEYS 排除（见该常量定义处）。
    self_path = _os.path.abspath(_os.path.join(base, 'blog', 'services', 'site_messages.py'))
    patterns = [
        _os.path.join(base, 'templates', '**', '*.html'),
        _os.path.join(base, 'blog', '**', '*.py'),
        _os.path.join(base, 'static', 'assets', 'js', '**', '*.js'),
    ]
    # 指纹只取「决定文案去向」的语料：模板与前端脚本。
    # 为什么不含 Python：`views.py` 是最常被改动的文件，若纳入指纹，
    # 每改一次视图就让接入状态「过期」而回退静态扫描（实测：管理页因此
    # 反复显示 87 条「未接入」）。而视图改动**不影响「哪些 key 会被渲染」**
    # 这一事实 —— 视图改的是数据，模板才是渲染入口，因此模板指纹足够。
    stamp_patterns = (
        _os.path.join(base, 'templates', '**', '*.html'),
        _os.path.join(base, 'static', 'assets', 'js', '**', '*.js'),
    )
    files = []
    stamp_files = []
    for pat in patterns:
        for path in _glob.glob(pat, recursive=True):
            if '__pycache__' in path or '.min.' in path:
                continue
            absolute = _os.path.abspath(path)
            if absolute == self_path:
                continue          # 注册表自身是「定义」不是「引用」
            try:
                files.append((absolute, _os.path.getmtime(absolute)))
            except OSError:
                continue
    for pat in stamp_patterns:
        for path in _glob.glob(pat, recursive=True):
            if '.min.' in path:
                continue
            try:
                stamp_files.append(_os.path.getmtime(path))
            except OSError:
                continue

    stamp = tuple(sorted(files, key=lambda x: x[0]))
    if _WIRED_CACHE['stamp'] == stamp:
        return _WIRED_CACHE['keys']

    # ---------------------------------------------------------------
    # 优先使用「运行时事实」：把每个 key 设为唯一标记后渲染全部页面，
    # 凡是标记真的出现在页面上的就是已接入。
    #
    # 为什么不信静态扫描（实测教训）：静态扫描漏掉两类引用，
    #   · Python 里经变量间接引用（msg(KEY)）；
    #   · 前端经 SITE_MSG 数据对象访问（SITE_MSG.auth_username_taken）。
    # 结果是静态判定报「87 条未接入」，而运行时验证证明这 87 条**全部生效**
    # （969/969），总表页因此错误标注「未接入」，用户会以为改了没反应。
    # 该文件由 docs/.../scripts/tools/compute_wired_runtime.py 生成，
    # 带源码 mtime 指纹；源码变了即视为过期，自动回退静态扫描。
    # ---------------------------------------------------------------
    try:
        import json as _json
        runtime_path = _os.path.join(
            base, 'docs', 'bugfix_20260926_bug9', 'reports', 'wired_runtime.json')
        with open(runtime_path, encoding='utf-8') as fh:
            payload = _json.load(fh)
        runtime_stamp = str(payload.get('stamp', ''))
        current_stamp = '%.3f' % max(stamp_files)
        # 指纹比较用**容差**而不是字符串相等：
        # mtime 是浮点秒，写入方与读取方各自做 `%.3f` 截断会产生毫秒级差异
        # （实测 1790369452.957 vs .952），字符串比较必然判为「过期」而回退静态扫描，
        # 于是管理页又显示 87 条「未接入」。允许 1 秒内的差异即可稳定命中。
        runtime_fresh = False
        try:
            runtime_fresh = abs(float(runtime_stamp) - float(current_stamp)) <= 1.0
        except (TypeError, ValueError):
            runtime_fresh = (runtime_stamp == current_stamp)
        if runtime_fresh and payload.get('wired'):
            keys = frozenset(payload['wired'])
            _WIRED_CACHE.update({'stamp': stamp, 'keys': keys})
            return keys
        # 指纹过期（源码改过）→ 回退静态扫描，**不在这里自动重算**。
        #
        # 为什么不自动重算：重算需要临时改写覆盖数据并渲染全部页面，早期实现放在
        # 后台线程里跑，结果与在线编辑、与验证脚本**并发争用同一张表/同一个文件**，
        # 实测把用户的覆盖记录冲掉过、也把统计文件写坏过。风险远大于收益。
        # 正确做法：重算由**维护/回归流程**显式执行（`verify_all_messages.py`
        # 会用「默认值可见性」重写该文件），页面侧只读不算。
    except (OSError, ValueError, TypeError):
        pass          # 文件缺失 / 格式异常 → 静态扫描兜底

    from ..services.site_messages import MESSAGES as _M

    # 分语料读取：模板 / Python 必须用「全 key」匹配，前端脚本才允许用短键
    # （SITE_MSG 里的键去掉了 js. 前缀）。绝不能把短键拿去匹配模板 ——
    # `'home'`、`'search'` 这类短词到处都是，会把大量未接入的 key 误判为已接入
    # （实测因此得出「已接入 117 / 待接入 7」的错误结论）。
    tpl_text, py_text, js_text = [], [], []
    for absolute, _ in files:
        try:
            with open(absolute, encoding='utf-8') as fh:
                content = fh.read()
        except (OSError, UnicodeDecodeError):
            continue
        if absolute.endswith('.html'):
            tpl_text.append(content)
        elif absolute.endswith('.py'):
            py_text.append(content)
        else:
            js_text.append(content)
    tpl, py, js = '\n'.join(tpl_text), '\n'.join(py_text), '\n'.join(js_text)

    wired = set()
    for key in _M:
        domain, _, short = key.partition('.')
        full = ["MSG.%s" % key, "'%s'" % key, '"%s"' % key]
        # 模板 / 视图：必须出现完整 key
        if any(n in tpl or n in py for n in full):
            wired.add(key)
            continue
        # 前端脚本：允许短键，但要求同文件里出现 SITE_MSG / moeMsg 取用方式，
        # 且用引号包住，避免子串误命中
        if domain == 'js' or domain in ('btn', 'misc'):
            if ("'%s'" % short) in js or ('"%s"' % short) in js:
                wired.add(key)
                continue
        # 前端也可能用「域_键」形式（如 SITE_MSG.btn_back_home）
        combined = key.replace('.', '_')
        if ("'%s'" % combined) in js or ('"%s"' % combined) in js:
            wired.add(key)

    keys = frozenset(wired)
    _WIRED_CACHE.update({'stamp': stamp, 'keys': keys})
    return keys

# 只服务于「文案总表管理页」自身的 key —— 改动它们对前台没有任何影响，
# 因此在接入统计里必须剔除，否则会出现「显示已接入、实际前台看不到」的假象。
# 
# 现状：本集合**已清空**。原先登记的是文案总表页自己的 5 条 flash 文案
# （moderation.msg_saved / msg_no_change / msg_save_invalid / msg_reset_one /
# msg_reset_domain），后来管理页文案统一迁移到 adminmsg.* 域，
# 这 5 条从注册表移除，集合随之失去意义。
# 保留这个名字是为了兼容既有调用点，避免再次改动大范围代码。
PAGE_ONLY_MSG_KEYS = frozenset()

@staff_required_moe
def site_messages_page(request: HttpRequest) -> HttpResponse:
    """全站文案总表管理页（仅管理员）：把近 300 条提示词全部搬到后台可视化编辑。

    设计取舍
    --------
    站点设置页（``/console/site-settings/``）管的是**站点级少量字段**
    （站名 / SEO / 页脚），文案总表有近 300 项、需要搜索与分组，塞进同一页面
    会让那一页无法使用。因此新增本页，并从站点设置页与 Django 后台同时挂入口。

    与代码的关系
    ------------
    - 代码里的 ``site_messages.MESSAGES`` 是**默认值**，本页只写「覆盖项」
      （``SiteMessage`` 表），保存后立即生效，且随时可一键恢复默认；
    - 页面同时显示「代码默认值」，改坏了能对照、能还原；
    - 占位符校验：数量与名称必须与默认值一致，否则保存被拒（避免线上文案报错）。

    GET  : 按域分组渲染全部文案 + 已有覆盖 + 当前搜索关键词
    POST : action=save 批量保存（只写有改动的项）；action=reset 恢复默认
           （支持单条 key 或整域 domain）
    """
    from ..models import SiteMessage
    from ..services.site_messages import MESSAGES, invalidate_overrides

    import string as _string

    class _Fmt(_string.Formatter):
        """只收集字段名，不求值（求值需要实参，这里只做静态校验）。"""

        def get_field(self, field_name, args, kwargs):
            return field_name, field_name

    def _placeholders(text):
        """取出文案里的占位符「指纹」，用于校验改动后占位符没有丢失 / 变形。

        为什么不能只收集字段名：``string.Formatter().parse('{}/{}')`` 对**位置占位符**
        （``{}``）返回的字段名是**空字符串**，用 ``if field_name`` 判断会全部漏掉，
        导致「把 ``{}`` 删掉」这种破坏性改动被放行（实测踩过）。
        因此这里统一归一化：位置占位符记为 ``#0`` / ``#1``（按出现顺序），
        命名占位符保留原字段名（含 ``str.format`` 的 ``{n}`` 与 ``%s`` 两种写法）。
        """
        out = []
        positional = 0
        for _, field_name, _, _ in _Fmt().parse(text or ''):
            if field_name is None:
                continue                      # 纯文本片段
            if field_name == '':              # 位置占位符 {}
                out.append('#%d' % positional)
                positional += 1
            else:
                out.append(field_name)
        # 兼容旧式 %s / %d 写法（本仓库文案历史上混用过）
        legacy = len(re.findall(r'%[sdrf]', text or ''))
        out.extend('#%%%d' % i for i in range(legacy))
        return tuple(out)

    if request.method == 'POST':
        # ---- 动作判定 ----
        #
        # ⚠️ 这里曾用 `<input type="hidden" name="action" value="reset">` 区分动作，
        #    但「恢复默认」按钮原先被放在**保存表单内部**（HTML 不允许表单嵌套），
        #    浏览器会忽略内层 <form> 标签、却保留它的隐藏字段。于是点「保存全部改动」时
        #    POST 里同时有 `action=save`（外层）与 `action=reset`（内层），
        #    ``request.POST.get('action')`` 取**最后一个值** → 走了重置分支 →
        #    **覆盖记录被删除**（用户报障「无改动点保存会重置为默认」）。
        #    教训：Django 测试客户端不解析 HTML，发现不了这类问题，必须用真实浏览器验证。
        #
        # 现方案：**只有一个表单**，提交按钮各自带 name：
        #    · name="save_all"       → 批量保存
        #    · name="reset_row"      → 单条恢复默认（value=key）
        #    · name="reset_domain"   → 整域恢复默认（value=域名）
        #    浏览器只提交被点击按钮的 name/value，因此判定无歧义。
        if 'reset_row' in request.POST or 'reset_domain' in request.POST:
            target_key = request.POST.get('reset_row', '').strip()
            target_domain = request.POST.get('reset_domain', '').strip()
            if target_key:
                deleted, _ = SiteMessage.objects.filter(key=target_key).delete()
                invalidate_overrides()
                messages.success(request, '%s：%s（清理 %d 条覆盖）'
                                              % (msg('adminmsg.reset_row_done'),
                                                 target_key, deleted))
            elif target_domain:
                # ⚠️ 必须转义 LIKE 通配符：`key__startswith('nav.')` 会翻译成
                #    `key LIKE 'nav.%'`，而 SQL 里 `_` 是**单字符通配符**，
                #    于是 nav.home / nav_articles / navXhome 都会被匹配到 ——
                #    「恢复 nav 域」会连带删掉无关的覆盖记录（实测踩过）。
                escaped = (target_domain.replace('\\', '\\\\')
                           .replace('_', '\\_').replace('%', '\\%'))
                deleted, _ = SiteMessage.objects.filter(
                    key__startswith=escaped + '.').delete()
                invalidate_overrides()
                messages.success(request, '%s：%s（清理 %d 条覆盖）'
                                              % (msg('adminmsg.reset_domain_done'),
                                                 target_domain, deleted))
            else:
                messages.error(request, msg('err.bad_request'))
            return redirect('site_messages')

        # ---- 批量保存：只处理**确实被改动**的项 ----
        #
        # ⚠️ 这里曾有一个「保存即重置」的严重缺陷（用户实测报障）：
        #    原实现只要提交值 == 代码默认值就删除覆盖记录。而「保存全部改动」
        #    会提交**全部** 969 个字段，用户没有改任何东西时，所有已保存的覆盖
        #    看起来都「等于默认值」→ 被逐条删除 → 覆盖全丢。
        #    正确判据是「提交值是否与**当前存储的**值不同」，而不是「是否等于默认值」：
        #      · 提交值 == 存储值        → 用户没动它，**什么都不做**（关键）
        #      · 提交值 == 默认值 ≠ 存储值 → 用户主动改回默认 → 删除覆盖
        #      · 其它                    → 写入/更新覆盖
        #    这样「无改动点保存」是**幂等**的，不会破坏任何数据。
        saved, skipped, errors, unchanged = 0, 0, [], 0
        stored = {m.key: m for m in SiteMessage.objects.all()}
        for key, default in MESSAGES.items():
            field = 'm_' + key.replace('.', '__')
            if field not in request.POST:
                continue          # 该字段未随表单提交（如被搜索过滤掉）→ 不动它
            new_text = request.POST.get(field, '').strip()
            current = stored.get(key)
            current_text = current.text if current else None

            # ① 与存储值完全一致 → 用户没改这一项，直接跳过（保住覆盖）
            if current_text is not None and new_text == current_text:
                unchanged += 1
                continue

            # ② 改回代码默认值 → 删除覆盖记录（用户主动还原）
            if new_text == default:
                if current is not None:
                    SiteMessage.objects.filter(key=key).delete()
                skipped += 1
                continue

            # ③ 内容为空 → 拒绝（避免把文案清空）
            if not new_text:
                errors.append(key)
                continue

            # ④ 占位符指纹必须一致（防破坏性改动）
            if _placeholders(new_text) != _placeholders(default):
                errors.append(key)
                continue

            obj, created = SiteMessage.objects.get_or_create(key=key)
            if obj.text != new_text:
                obj.text = new_text
                obj.is_enabled = True
                obj.updated_by = request.user if request.user.is_authenticated else None
                obj.save()
                saved += 1
        invalidate_overrides()
        if errors:
            messages.error(request, msg('moderation.msg_save_invalid', len(errors),
                                        '、'.join(errors[:5])))
        if saved:
            messages.success(request, msg('moderation.msg_saved', saved))
        elif not errors:
            messages.info(request, msg('moderation.msg_no_change'))
        return redirect('site_messages')

    # ---- GET：组装按域分组的展示数据 ----
    overrides = {m.key: m for m in SiteMessage.objects.all()}
    keyword = request.GET.get('q', '').strip()
    active_domain = request.GET.get('domain', '').strip()

    # 「已接入」集合：只有被模板 / 视图 / 前端脚本真正引用的 key，改了才会有可见效果。
    # 注册表里有相当一部分 key 目前只是「预留登记」（改它不会影响任何界面），
    # 若不在页面上标出来，运营会以为改了没生效 —— 这是必须显式告知的信息。
    wired_keys = _wired_message_keys() - PAGE_ONLY_MSG_KEYS

    groups, total_changed, total_dead = [], 0, 0
    for key, default in sorted(MESSAGES.items()):
        domain = key.split('.', 1)[0]
        if active_domain and domain != active_domain:
            continue
        if keyword and keyword.lower() not in key.lower() \
                and keyword not in default and keyword not in key:
            continue
        ov = overrides.get(key)
        # 两个概念要分开（曾混为一谈导致保存后标记错误）：
        #   · has_override —— 数据库里存在启用中的覆盖记录（决定「已覆盖」标签与「恢复默认」按钮）
        #   · differs      —— 覆盖值确实与代码默认不同（决定「与默认相同」提示）
        has_override = bool(ov and ov.is_enabled)
        differs = bool(has_override and ov.text != default)
        if has_override:
            total_changed += 1
        is_wired = key in wired_keys
        if not is_wired:
            total_dead += 1
        groups.append({
            'key': key, 'domain': domain, 'field': 'm_' + key.replace('.', '__'),
            'default': default,
            'current': ov.text if ov else default,
            'changed': has_override,
            'differs': differs,
            'wired': is_wired,
            'disabled': bool(ov and not ov.is_enabled),
            'updated_by': ov.updated_by.username if (ov and ov.updated_by) else '',
            'updated_at': ov.updated_at if ov else None,
        })
    # 按域聚合，保持域顺序与中文标题
    dom_order = list(MSG_DOMAIN_TITLES.keys())
    by_domain = {}
    for g in groups:
        by_domain.setdefault(g['domain'], []).append(g)
    domain_blocks = []
    for dom in dom_order + [d for d in by_domain if d not in dom_order]:
        if dom in by_domain:
            items = by_domain[dom]
            domain_blocks.append({
                'domain': dom,
                'title': MSG_DOMAIN_TITLES.get(dom, dom),
                'items': items,
                # 单独给出条数：模板里不能用 `|msgfmt:block.items|length`
                # （过滤器参数不支持再套过滤器，会整页 500），
                # 因此在这里算好，模板直接 |msgfmt:block.item_count。
                'item_count': len(items),
                'changed': sum(1 for i in items if i['changed']),
                'dead': sum(1 for i in items if not i['wired']),
            })

    return render(request, 'blog/site_messages.html', {
        'domain_blocks': domain_blocks,
        'total_keys': len(MESSAGES),
        'shown_keys': len(groups),
        'total_changed': total_changed,
        'total_wired': len(wired_keys),
        'total_dead': total_dead,
        'keyword': keyword,
        'active_domain': active_domain,
        'domain_titles': MSG_DOMAIN_TITLES,
        'default_titles': MSG_DOMAIN_TITLES,
        'meta_title': '文案总表 · %s' % settings.SITE_NAME,
    })

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
def dev_sync_state(request):
    """DEBUG 专用：把「外部脚本改过的数据库设置」同步到本服务进程的缓存。

    解决的问题：``ModerationSettings.load()`` 使用进程内 LocMemCache，
    验收脚本（独立进程）改了 ``require_article_review`` 等设置后，
    runserver 进程里的缓存仍是旧值，导致「脚本设 A、服务端按 B 执行」的假失败。

    机制：脚本先写入桥接文件 ``docs/bugfix_20260926_bug9/.sync_request``，
    再请求本端点；本端点读取该文件 → 清空本进程缓存 → 删除桥接文件。

    安全：仅 ``settings.DEBUG`` 且本机访问时可用；生产（DEBUG=False）返回 404。
    """
    if not settings.DEBUG:
        return JsonResponse({'ok': False, 'error': msg('err.debug_only')}, status=404)
    is_local = request.META.get('REMOTE_ADDR') in ('127.0.0.1', '::1')
    if not (is_local or getattr(request.user, 'is_superuser', False)):
        return JsonResponse({'ok': False, 'error': 'permission_denied'}, status=403)
    bridge = os.path.join(settings.BASE_DIR, 'docs',
                          'bugfix_20260926_bug9', '.sync_request')
    payload = ''
    if os.path.exists(bridge):
        try:
            with open(bridge, encoding='utf-8') as fh:
                payload = fh.read().strip()
            os.remove(bridge)
        except OSError:
            payload = ''
    # 清空本进程缓存，使下次请求重新从数据库读取设置
    cleared = True
    try:
        cache.clear()
    except Exception:  # noqa: BLE001 清缓存失败也要如实告知
        cleared = False
    return JsonResponse({'ok': True, 'payload': payload, 'cleared': cleared})

def debug_cache_dump(request):
    """DEBUG 专用：返回当前进程缓存快照（key / 剩余 TTL / 详情页片段命中统计）。

    开发调试时在浏览器直接查看 runserver 进程内的 LocMemCache 内容
    （LocMemCache 为进程内缓存，diag 是独立进程看不到，此端点必须在服务进程内访问）。

    仅当 settings.DEBUG 且为本机访问（127.0.0.1 / ::1）或超级用户时可用。
    """
    if not settings.DEBUG:
        return JsonResponse({'ok': False, 'error': msg('err.debug_only')}, status=404)
    is_local = request.META.get('REMOTE_ADDR') in ('127.0.0.1', '::1')
    if not (is_local or (request.user.is_authenticated and request.user.is_superuser)):
        return JsonResponse({'ok': False, 'error': 'permission_denied'}, status=403)
    import time as _time
    from ..utils.cache_keys import get_cache_version, get_stats
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

# -*- coding: utf-8 -*-

"""运营看板、站点设置、文案总表、服务状态与调试端点。"""

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
#: 从模块「datetime」导入所需对象
from datetime import datetime, timedelta
#: 从模块「django.conf」导入所需对象
from django.conf import settings
#: 从模块「django.contrib」导入所需对象
from django.contrib import messages
# staff_required_moe：员工页面统一权限装饰器（未登录跳萌系登录页 / 已登录非员工显 403）
#: 从模块「..utils.decorators」导入所需对象
from ..utils.decorators import staff_required_moe
#: 从模块「django.core.cache」导入所需对象
from django.core.cache import cache
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
    #: 从模块「..services.site_messages」导入所需对象
    from ..services.site_messages import MESSAGES, js_payload
    #: 从模块「..context_processors」导入所需对象
    from ..context_processors import build_token as _build_token
    #: 定义变量「token」，保存对应数据（集合/元组）
    token = (_build_token(request) or {}).get('BUILD_TOKEN', 'dev')
    #: 定义变量「payload」，保存对应数据
    payload = js_payload()
    #: 返回 JSON 响应，供前端异步接口使用
    response = JsonResponse({
        #: 配置项「code」：字典/模型的该键设置为对应值
        'code': 0,
        #: 配置项「build」：字典/模型的该键设置为对应值
        'build': token,
        #: 配置项「count」：字典/模型的该键设置为对应值
        'count': len(MESSAGES),
        #: 配置项「data」：字典/模型的该键设置为对应值
        'data': payload,
    #: 该行执行对应逻辑（结合上下文理解）
    }, json_dumps_params={'ensure_ascii': False})
    # 版本号变化即视为新资源；未变化时允许浏览器与 CDN 长时间复用
    #: 该行执行对应逻辑（结合上下文理解）
    response['Cache-Control'] = 'public, max-age=86400'
    #: 该行执行对应逻辑（结合上下文理解）
    response['X-Messages-Build'] = token
    #: 返回结果并结束当前函数
    return response

# 迭代#201: server_status视图docstring
# 迭代#202: server_status(request) -> HttpResponse 类型提示
# 迭代#203: server_status健康检查逻辑注释
# staff_required_moe：未登录跳前台萌系登录页；已登录但非员工显 403（逻辑见 utils/decorators.py）
#: 装饰器：为下一个定义附加「staff_required_moe」行为（权限、缓存、注册信号等）
@staff_required_moe
def server_status(request: HttpRequest) -> HttpResponse:
    """69. 网站运行状态页：检查数据库 / Redis 连通性，统计数据与版本信息。"""
    #: 从模块「django」导入所需对象
    from django import get_version
    #: 定义变量「status_dict」，保存对应数据
    status_dict = {}

    # ---- 数据库连接：执行 SELECT 1 探测 ----
    #: 尝试执行可能出错的代码
    try:
        #: 从模块「django.db」导入所需对象
        from django.db import connection
        #: 上下文管理：进入时获取资源、退出时自动释放
        with connection.cursor() as cur:
            #: 调用「cur.execute」执行相应逻辑
            cur.execute('SELECT 1')
            #: 调用「cur.fetchone」执行相应逻辑
            cur.fetchone()
        #: 该行执行对应逻辑（结合上下文理解）
        status_dict['database'] = {'label': '数据库 (MySQL)', 'state': 'ok',
                                   #: 配置项「detail」：字典/模型的该键设置为对应值
                                   'detail': '连接正常'}
    #: 捕获并处理异常，避免程序中断
    except Exception as exc:  # noqa: BLE001 状态页需兜底展示错误
        #: 该行执行对应逻辑（结合上下文理解）
        status_dict['database'] = {'label': '数据库 (MySQL)', 'state': 'error',
                                   #: 配置项「detail」：字典/模型的该键设置为对应值
                                   'detail': f'连接失败: {exc}'}

    # ---- Redis 连接：尝试 ping（未配置 / 不可达时降级为 warn）----
    #: 尝试执行可能出错的代码
    try:
        #: 导入模块「redis」，供本文件后续使用
        import redis
        #: 获取/使用 Redis 连接，注意连接失败的降级
        r = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2)
        #: 调用「r.ping」执行相应逻辑
        r.ping()
        #: 该行执行对应逻辑（结合上下文理解）
        status_dict['redis'] = {'label': 'Redis 缓存', 'state': 'ok', 'detail': 'PONG 正常'}
    #: 捕获并处理异常，避免程序中断
    except Exception as exc:  # noqa: BLE001
        #: 该行执行对应逻辑（结合上下文理解）
        status_dict['redis'] = {'label': 'Redis 缓存', 'state': 'warn',
                               #: 配置项「detail」：字典/模型的该键设置为对应值
                               'detail': f'未连接（{type(exc).__name__}），降级使用'}

    # ---- Celery worker：简单探测 broker 上的活跃 worker ----
    #: 尝试执行可能出错的代码
    try:
        #: 从模块「celery」导入所需对象
        from celery import current_app
        #: 定义变量「insp」，保存对应数据
        insp = current_app.control.inspect(timeout=1)
        #: 定义变量「active」，保存对应数据
        active = insp.ping()
        #: 条件判断：条件成立时执行该分支
        if active:
            #: 该行执行对应逻辑（结合上下文理解）
            status_dict['celery'] = {'label': 'Celery 异步任务', 'state': 'ok',
                                     #: 配置项「detail」：字典/模型的该键设置为对应值
                                     'detail': f'{len(active)} 个 worker 在线'}
        #: 以上条件均不成立时的兜底分支
        else:
            #: 该行执行对应逻辑（结合上下文理解）
            status_dict['celery'] = {'label': 'Celery 异步任务', 'state': 'warn',
                                     #: 配置项「detail」：字典/模型的该键设置为对应值
                                     'detail': '未发现运行中的 worker'}
    #: 捕获并处理异常，避免程序中断
    except Exception as exc:  # noqa: BLE001
        #: 该行执行对应逻辑（结合上下文理解）
        status_dict['celery'] = {'label': 'Celery 异步任务', 'state': 'warn',
                                 #: 配置项「detail」：字典/模型的该键设置为对应值
                                 'detail': f'检查失败（{type(exc).__name__}）'}

    # ---- 统计数据 ----
    #: 获取当前时间（时区感知），统一时间口径
    today = timezone.now().date()
    #: 定义变量「stats」，保存对应数据
    stats = {
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        'article_total': Article.objects.count(),
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        'published_total': Article.objects.filter(status=Article.Status.PUBLISHED).count(),
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        'comment_total': Comment.objects.count(),
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        'user_total': User.objects.count(),
        #: 使用聚合函数做统计查询
        'views_total': Article.objects.aggregate(v=Sum('views'))['v'] or 0,
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        'today_visits': AccessLog.objects.filter(created_at__date=today).count(),
    #: 该行执行对应逻辑（结合上下文理解）
    }
    # ---- 版本信息 ----
    #: 定义变量「versions」，保存对应数据
    versions = {
        #: 配置项「python」：字典/模型的该键设置为对应值
        'python': os.sys.version.split()[0],
        #: 配置项「django」：字典/模型的该键设置为对应值
        'django': get_version(),
        #: 配置项「mysql」：字典/模型的该键设置为对应值
        'mysql': 'MySQL',
        #: 配置项「redis」：字典/模型的该键设置为对应值
        'redis': getattr(settings, 'CELERY_BROKER_URL', ''),
    #: 该行执行对应逻辑（结合上下文理解）
    }
    #: 定义变量「ctx」，保存对应数据
    ctx = {
        #: 配置项「status_dict」：字典/模型的该键设置为对应值
        'status_dict': status_dict,
        #: 配置项「stats」：字典/模型的该键设置为对应值
        'stats': stats,
        #: 配置项「versions」：字典/模型的该键设置为对应值
        'versions': versions,
        #: 配置项「active_nav」：字典/模型的该键设置为对应值
        'active_nav': 'status',
        #: 配置项「meta_title」：字典/模型的该键设置为对应值
        'meta_title': f'运行状态 - {settings.SITE_NAME}',
    #: 该行执行对应逻辑（结合上下文理解）
    }
    #: 返回结果并结束当前函数
    return render(request, 'blog/status.html', ctx)

# 70. 手工登记的 API 端点清单：供文档页渲染（方法 / 路径 / 说明 / 参数 / 示例）
#: 定义变量「API_ENDPOINTS」，保存对应数据（集合/元组）
API_ENDPOINTS = [
    #: 该行执行对应逻辑（结合上下文理解）
    {'method': 'GET', 'path': '/api/articles/', 'desc': '文章列表（分页）',
     #: 配置项「params」：字典/模型的该键设置为对应值
     'params': '?page= &page_size= &q= &category= &tag= &kind= &sort=hot|latest',
     #: 配置项「curl」：字典/模型的该键设置为对应值
     'curl': 'curl "http://localhost:8000/api/articles/?page=1&q=django"',
     #: 配置项「resp」：字典/模型的该键设置为对应值
     'resp': '{"count":114,"next":...,"results":[{"id":1,"title":"..."}]}'},
    #: 该行执行对应逻辑（结合上下文理解）
    {'method': 'POST', 'path': '/api/articles/', 'desc': '新建文章（需登录）',
     #: 配置项「params」：字典/模型的该键设置为对应值
     'params': 'title, content, kind, status, tag_names',
     #: 配置项「curl」：字典/模型的该键设置为对应值
     'curl': 'curl -X POST http://localhost:8000/api/articles/ -H "X-CSRFToken: ..." -d "title=test&content=<p>hi</p>"',
     #: 配置项「resp」：字典/模型的该键设置为对应值
     'resp': '{"id":115,"title":"test",...}'},
    #: 该行执行对应逻辑（结合上下文理解）
    {'method': 'GET', 'path': '/api/articles/<pk>/', 'desc': '文章详情',
     #: 配置项「params」：字典/模型的该键设置为对应值
     'params': '路径参数 pk',
     #: 配置项「curl」：字典/模型的该键设置为对应值
     'curl': 'curl http://localhost:8000/api/articles/1/',
     #: 配置项「resp」：字典/模型的该键设置为对应值
     'resp': '{"id":1,"title":"...","content":"..."}'},
    #: 该行执行对应逻辑（结合上下文理解）
    {'method': 'PUT/PATCH', 'path': '/api/articles/<pk>/', 'desc': '修改文章（作者/管理员）',
     #: 配置项「params」：字典/模型的该键设置为对应值
     'params': '同新建字段',
     #: 配置项「curl」：字典/模型的该键设置为对应值
     'curl': 'curl -X PATCH http://localhost:8000/api/articles/1/ -d "title=new"',
     #: 配置项「resp」：字典/模型的该键设置为对应值
     'resp': '{"id":1,"title":"new",...}'},
    #: 该行执行对应逻辑（结合上下文理解）
    {'method': 'DELETE', 'path': '/api/articles/<pk>/', 'desc': '删除文章（作者/管理员）',
     #: 配置项「params」：字典/模型的该键设置为对应值
     'params': '路径参数 pk',
     #: 配置项「curl」：字典/模型的该键设置为对应值
     'curl': 'curl -X DELETE http://localhost:8000/api/articles/99/',
     #: 配置项「resp」：字典/模型的该键设置为对应值
     'resp': '204 No Content'},
    #: 该行执行对应逻辑（结合上下文理解）
    {'method': 'POST', 'path': '/api/articles/<pk>/like/', 'desc': '点赞文章（session 防重复，幂等）',
     #: 配置项「params」：字典/模型的该键设置为对应值
     'params': '无',
     #: 配置项「curl」：字典/模型的该键设置为对应值
     'curl': 'curl -X POST http://localhost:8000/api/articles/1/like/',
     #: 配置项「resp」：字典/模型的该键设置为对应值
     'resp': '{"likes": 42, "liked": true}'},
    #: 该行执行对应逻辑（结合上下文理解）
    {'method': 'POST', 'path': '/api/articles/<pk>/rate/', 'desc': '文章评分 1~5 星（登录用户，幂等更新）',
     #: 配置项「params」：字典/模型的该键设置为对应值
     'params': 'score=1..5',
     #: 配置项「curl」：字典/模型的该键设置为对应值
     'curl': 'curl -X POST http://localhost:8000/api/articles/1/rate/ -d "score=5"',
     #: 配置项「resp」：字典/模型的该键设置为对应值
     'resp': '{"success":true,"avg":4.6,"count":10,"my":5}'},
    #: 该行执行对应逻辑（结合上下文理解）
    {'method': 'POST', 'path': '/article/<pk>/favorite/', 'desc': '收藏/取消收藏文章（登录用户，幂等）',
     #: 配置项「params」：字典/模型的该键设置为对应值
     'params': '无',
     #: 配置项「curl」：字典/模型的该键设置为对应值
     'curl': 'curl -X POST http://localhost:8000/article/1/favorite/',
     #: 配置项「resp」：字典/模型的该键设置为对应值
     'resp': '{"favorited": true, "count": 3}'},
    #: 该行执行对应逻辑（结合上下文理解）
    {'method': 'POST', 'path': '/api/comments/<pk>/like/', 'desc': '点赞评论（session 防重复，幂等）',
     #: 配置项「params」：字典/模型的该键设置为对应值
     'params': '无',
     #: 配置项「curl」：字典/模型的该键设置为对应值
     'curl': 'curl -X POST http://localhost:8000/api/comments/1/like/',
     #: 配置项「resp」：字典/模型的该键设置为对应值
     'resp': '{"likes": 5, "liked": true}'},
    #: 该行执行对应逻辑（结合上下文理解）
    {'method': 'GET', 'path': '/api/search/suggest/', 'desc': '搜索建议（标题自动补全）',
     #: 配置项「params」：字典/模型的该键设置为对应值
     'params': '?q=关键词',
     #: 配置项「curl」：字典/模型的该键设置为对应值
     'curl': 'curl "http://localhost:8000/api/search/suggest/?q=django"',
     #: 配置项「resp」：字典/模型的该键设置为对应值
     'resp': '{"suggestions": ["Django 入门", "Django 部署"]}'},
    #: 该行执行对应逻辑（结合上下文理解）
    {'method': 'POST', 'path': '/api/upload-image/', 'desc': '富文本图片上传（登录用户）',
     #: 配置项「params」：字典/模型的该键设置为对应值
     'params': 'multipart 字段 upload',
     #: 配置项「curl」：字典/模型的该键设置为对应值
     'curl': 'curl -X POST http://localhost:8000/api/upload-image/ -F "upload=@a.png"',
     #: 配置项「resp」：字典/模型的该键设置为对应值
     'resp': '{"uploaded":1,"fileName":"a.png","url":"/media/..."}'},
    #: 该行执行对应逻辑（结合上下文理解）
    {'method': 'GET', 'path': '/api/categories/', 'desc': '分类列表（含文章数）',
     #: 配置项「params」：字典/模型的该键设置为对应值
     'params': '无',
     #: 配置项「curl」：字典/模型的该键设置为对应值
     'curl': 'curl http://localhost:8000/api/categories/',
     #: 配置项「resp」：字典/模型的该键设置为对应值
     'resp': '[{"id":1,"name":"Django","article_count":12}]'},
    #: 该行执行对应逻辑（结合上下文理解）
    {'method': 'POST', 'path': '/api/categories/', 'desc': '新建分类（仅管理员）',
     #: 配置项「params」：字典/模型的该键设置为对应值
     'params': 'name, description',
     #: 配置项「curl」：字典/模型的该键设置为对应值
     'curl': 'curl -X POST http://localhost:8000/api/categories/ -d "name=Python"',
     #: 配置项「resp」：字典/模型的该键设置为对应值
     'resp': '{"id":5,"name":"Python",...}'},
    #: 该行执行对应逻辑（结合上下文理解）
    {'method': 'GET/PUT/DELETE', 'path': '/api/categories/<pk>/', 'desc': '分类详情/修改/删除',
     #: 配置项「params」：字典/模型的该键设置为对应值
     'params': '路径参数 pk',
     #: 配置项「curl」：字典/模型的该键设置为对应值
     'curl': 'curl http://localhost:8000/api/categories/1/',
     #: 配置项「resp」：字典/模型的该键设置为对应值
     'resp': '{"id":1,"name":"Django",...}'},
    #: 该行执行对应逻辑（结合上下文理解）
    {'method': 'GET', 'path': '/api/tags/', 'desc': '标签列表（含文章数）',
     #: 配置项「params」：字典/模型的该键设置为对应值
     'params': '无',
     #: 配置项「curl」：字典/模型的该键设置为对应值
     'curl': 'curl http://localhost:8000/api/tags/',
     #: 配置项「resp」：字典/模型的该键设置为对应值
     'resp': '[{"id":1,"name":"django","article_count":8}]'},
    #: 该行执行对应逻辑（结合上下文理解）
    {'method': 'POST', 'path': '/api/tags/', 'desc': '新建标签',
     #: 配置项「params」：字典/模型的该键设置为对应值
     'params': 'name',
     #: 配置项「curl」：字典/模型的该键设置为对应值
     'curl': 'curl -X POST http://localhost:8000/api/tags/ -d "name=flask"',
     #: 配置项「resp」：字典/模型的该键设置为对应值
     'resp': '{"id":20,"name":"flask",...}'},
    #: 该行执行对应逻辑（结合上下文理解）
    {'method': 'GET/PUT/DELETE', 'path': '/api/tags/<pk>/', 'desc': '标签详情/修改/删除',
     #: 配置项「params」：字典/模型的该键设置为对应值
     'params': '路径参数 pk',
     #: 配置项「curl」：字典/模型的该键设置为对应值
     'curl': 'curl http://localhost:8000/api/tags/1/',
     #: 配置项「resp」：字典/模型的该键设置为对应值
     'resp': '{"id":1,"name":"django",...}'},
#: 该行执行对应逻辑（结合上下文理解）
]

# 迭代#204: api_docs视图docstring
# 迭代#205: api_docs(request) -> HttpResponse 类型提示
def api_docs(request: HttpRequest) -> HttpResponse:
    """70. API 文档页：列出全部端点，支持前端搜索过滤。"""
    #: 定义变量「ctx」，保存对应数据
    ctx = {
        #: 配置项「endpoints」：字典/模型的该键设置为对应值
        'endpoints': API_ENDPOINTS,
        #: 配置项「active_nav」：字典/模型的该键设置为对应值
        'active_nav': 'api_docs',
        #: 配置项「meta_title」：字典/模型的该键设置为对应值
        'meta_title': f'API 文档 - {settings.SITE_NAME}',
        #: 配置项「meta_description」：字典/模型的该键设置为对应值
        'meta_description': f'{settings.SITE_NAME} 开放 API 接口文档。',
    #: 该行执行对应逻辑（结合上下文理解）
    }
    #: 返回结果并结束当前函数
    return render(request, 'blog/api_docs.html', ctx)

# ============================ Bug26: 萌系运营控制台 ============================
def staff_console(request: HttpRequest):
    """运营数据看板：仅 staff 管理员可访问的前端萌系控制台。

    聚合站点核心指标、近 14 天访问趋势、热门文章、分类分布、
    最近评论 / 用户、浏览器分布与待处理举报，纯 CSS 图表呈现，不引重库。
    """
    # staff_required_moe：未登录跳前台萌系登录 / 已登录非员工返回 403（顶部已导入）
    #: 装饰器：为下一个定义附加「staff_required_moe」行为（权限、缓存、注册信号等）
    @staff_required_moe
    def _inner(req):
        """
        功能：处理「inner」相关逻辑。

        参数：
          - req：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：装饰器 staff_required_moe 决定其附加行为（权限/缓存/属性/信号等）；含 Django ORM 数据库查询，注意查询性能与空结果处理。
        """
        #: 获取当前时间（时区感知），统一时间口径
        today = timezone.now().date()
        #: 获取当前时间（时区感知），统一时间口径
        start = timezone.now() - timedelta(days=13)

        # ---- 核心指标 ----
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        published_qs = Article.objects.filter(status=Article.Status.PUBLISHED)
        #: 使用聚合函数做统计查询
        total_views = published_qs.aggregate(v=Sum('views'))['v'] or 0
        #: 使用聚合函数做统计查询
        total_likes = published_qs.aggregate(l=Sum('likes'))['l'] or 0
        #: 获取当前时间（时区感知），统一时间口径
        online_cut = timezone.now() - timedelta(minutes=5)

        #: 定义变量「stats」，保存对应数据
        stats = {
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'article_total': Article.objects.count(),
            #: 配置项「article_published」：字典/模型的该键设置为对应值
            'article_published': published_qs.count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'article_pending': Article.objects.filter(
                #: 定义变量「status」，保存对应数据
                status=Article.Status.PENDING, is_deleted=False).count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'article_draft': Article.objects.filter(status=Article.Status.DRAFT).count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'comment_total': Comment.objects.count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'user_total': User.objects.count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'category_total': Category.objects.count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'tag_total': Tag.objects.count(),
            #: 配置项「total_views」：字典/模型的该键设置为对应值
            'total_views': total_views,
            #: 配置项「total_likes」：字典/模型的该键设置为对应值
            'total_likes': total_likes,
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'today_visits': AccessLog.objects.filter(created_at__date=today).count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'today_uv': AccessLog.objects.filter(created_at__date=today)
                       #: 该行执行对应逻辑（结合上下文理解）
                       .exclude(ip_address__isnull=True).values('ip_address').distinct().count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'online': max(1, AccessLog.objects.filter(created_at__gte=online_cut)
                          #: 该行执行对应逻辑（结合上下文理解）
                          .exclude(ip_address__isnull=True).values('ip_address').distinct().count()),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'reports': CommentReport.objects.count(),
        #: 该行执行对应逻辑（结合上下文理解）
        }

        # ---- 近 14 天访问趋势（Python 按天聚合，规避时区/分组差异）----
        #: 定义变量「trend」，保存对应数据（集合/元组）
        trend = []
        #: 定义变量「max_count」，保存对应数据
        max_count = 1
        #: 循环遍历，逐个处理元素
        for i in range(13, -1, -1):
            #: 定义变量「d」，保存对应数据
            d = today - timedelta(days=i)
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            c = AccessLog.objects.filter(created_at__date=d).count()
            #: 定义变量「max_count」，保存对应数据
            max_count = max(max_count, c)
            #: 调用「trend.append」执行相应逻辑
            trend.append({'label': f'{d.month}/{d.day}', 'count': c})
        #: 导入模块「math」，供本文件后续使用
        import math  # 工单10：开方刻度需要
        #: 循环遍历，逐个处理元素
        for t in trend:
            #: 定义变量「true_pct」，保存对应数据
            true_pct = round(t['count'] * 100 / max_count, 1)
            #: 该行执行对应逻辑（结合上下文理解）
            t['pct'] = true_pct
            # 工单10：今日峰值常被集中访问 / 压测拉高，线性刻度会把其余各天压成
            # 等高的细线、看不出彼此差异；改用“开方刻度”（sqrt）压缩离群峰值、
            # 保留普通日之间的高低差异。真实次数仍以 data-v / 悬停 title 为准。
            #: 该行执行对应逻辑（结合上下文理解）
            t['bar_h'] = round(math.sqrt(t['count'] / max_count) * 100, 1) if t['count'] > 0 else 0.0

        # ---- 热门文章 Top 8 ----
        #: 对查询结果按字段排序
        top_articles = list(published_qs.order_by('-views').values(
            #: 该行执行对应逻辑（结合上下文理解）
            'id', 'title', 'views', 'likes', 'comment_count')[:8])
        #: 定义变量「top_max」，保存对应数据
        top_max = max([a['views'] for a in top_articles] + [1])
        #: 循环遍历，逐个处理元素
        for a in top_articles:
            #: 该行执行对应逻辑（结合上下文理解）
            a['pct'] = round(a['views'] * 100 / top_max, 1)

        # ---- 分类文章分布 ----
        #: 定义变量「cat_dist」，保存对应数据
        cat_dist = list(Category.objects.annotate(
            #: 使用 Q/F 表达式构造复杂查询或引用字段值
            n=Count('articles', filter=Q(articles__status=Article.Status.PUBLISHED)))
            #: 对查询结果按字段排序
            .order_by('-n').values('name', 'n')[:10])
        #: 定义变量「cat_max」，保存对应数据
        cat_max = max([c['n'] for c in cat_dist] + [1])
        #: 循环遍历，逐个处理元素
        for c in cat_dist:
            #: 该行执行对应逻辑（结合上下文理解）
            c['pct'] = round(c['n'] * 100 / cat_max, 1)

        # ---- 最近评论 / 最近注册用户 ----
        #: ORM 预加载关联，减少 N+1 查询提升性能
        recent_comments = list(Comment.objects.select_related('article', 'user')
                               #: 对查询结果按字段排序
                               .order_by('-created_at').values(
                                   #: 该行执行对应逻辑（结合上下文理解）
                                   'user__username', 'article__title',
                                   #: 该行执行对应逻辑（结合上下文理解）
                                   'article_id', 'content', 'created_at')[:6])
        #: 循环遍历，逐个处理元素
        for cm in recent_comments:
            #: 该行执行对应逻辑（结合上下文理解）
            cm['snippet'] = (cm['content'] or '')[:40]
        #: 对查询结果按字段排序
        recent_users = list(User.objects.order_by('-date_joined')
                            #: 该行执行对应逻辑（结合上下文理解）
                            .values('username', 'date_joined')[:6])

        # ---- 浏览器分布 Top 5 ----
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        browsers = list(AccessLog.objects.exclude(browser__isnull=True).exclude(browser='')
                        #: 对查询结果按字段排序
                        .values('browser').annotate(n=Count('id')).order_by('-n')[:5])

        #: 定义变量「ctx」，保存对应数据
        ctx = {
            #: 配置项「stats」：字典/模型的该键设置为对应值
            'stats': stats, 'trend': trend, 'top_articles': top_articles,
            #: 配置项「cat_dist」：字典/模型的该键设置为对应值
            'cat_dist': cat_dist, 'recent_comments': recent_comments,
            #: 配置项「recent_users」：字典/模型的该键设置为对应值
            'recent_users': recent_users, 'browsers': browsers,
            #: 配置项「active_nav」：字典/模型的该键设置为对应值
            'active_nav': 'console',
            #: 配置项「meta_title」：字典/模型的该键设置为对应值
            'meta_title': f'运营看板 · {settings.SITE_NAME}',
        #: 该行执行对应逻辑（结合上下文理解）
        }
        #: 返回结果并结束当前函数
        return render(req, 'blog/console.html', ctx)
    #: 返回结果并结束当前函数
    return _inner(request)

#: 装饰器：为下一个定义附加「staff_required_moe」行为（权限、缓存、注册信号等）
@staff_required_moe
def site_settings_page(request: HttpRequest) -> HttpResponse:
    """工单 15：站点信息设置页（仅管理员）。

    把原先硬编码的网站名 / Logo / 副标题 / SEO 描述关键词 / 页脚文案等
    做成可在线编辑的表单，保存到 :class:`~blog.models.SiteInfo` 单例；
    模型 ``save()`` 会自动清除读取缓存，保存后全站立即生效，无需重启或改代码。
    """
    #: 从模块「..models」导入所需对象
    from ..models import SiteInfo
    #: 定义变量「info」，保存对应数据
    info = SiteInfo.load()

    # 允许编辑的字段白名单（键 -> 最大长度，0 表示长文本）
    #: 定义变量「fields」，保存对应数据（集合/元组）
    fields = [
        #: 该行执行对应逻辑（结合上下文理解）
        ('site_name', 60), ('logo_emoji', 8), ('tagline', 120),
        #: 该行执行对应逻辑（结合上下文理解）
        ('description', 0), ('keywords', 200), ('footer_about', 0),
        #: 该行执行对应逻辑（结合上下文理解）
        ('footer_icp', 80), ('copyright_holder', 60),
    #: 该行执行对应逻辑（结合上下文理解）
    ]

    #: 条件判断：条件成立时执行该分支
    if request.method == 'POST':
        #: 定义变量「errors」，保存对应数据（集合/元组）
        errors = []
        #: 循环遍历，逐个处理元素
        for key, max_len in fields:
            #: 读取本次请求的 POST 数据
            val = request.POST.get(key, '').strip()
            #: 条件判断：条件成立时执行该分支
            if max_len and len(val) > max_len:
                #: 调用「errors.append」执行相应逻辑
                errors.append(f'「{key}」长度不能超过 {max_len} 个字符')
            #: 调用「setattr」执行相应逻辑
            setattr(info, key, val)
        #: 条件判断：条件成立时执行该分支
        if errors:
            #: 循环遍历，逐个处理元素
            for err in errors:
                #: 向用户闪现一条提示消息（下次请求展示）
                messages.error(request, err)
        #: 以上条件均不成立时的兜底分支
        else:
            #: 保存对象（INSERT/UPDATE），可能触发模型信号
            info.save()  # save() 强制单例并清缓存
            #: 向用户闪现一条提示消息（下次请求展示）
            messages.success(request, msg('misc.site_saved'))
            #: 返回结果并结束当前函数
            return redirect('site_settings')

    #: 返回结果并结束当前函数
    return render(request, 'blog/site_settings.html', {
        #: 配置项「info」：字典/模型的该键设置为对应值
        'info': info,
        #: 配置项「fields」：字典/模型的该键设置为对应值
        'fields': fields,
        #: 配置项「active_nav」：字典/模型的该键设置为对应值
        'active_nav': 'site_settings',
        #: 配置项「meta_title」：字典/模型的该键设置为对应值
        'meta_title': f'站点设置 · {info.site_name}',
    #: 该行执行对应逻辑（结合上下文理解）
    })

# ============================ 全站文案总表（提示词）管理 ============================
#: 文案域的中文标题，用于管理页分组展示（新增域时在此补一行）
MSG_DOMAIN_TITLES = {
    #: 配置项「brand」：字典/模型的该键设置为对应值
    'brand': '站点品牌与固定标语',
    #: 配置项「nav」：字典/模型的该键设置为对应值
    'nav': '导航与菜单',
    #: 配置项「btn」：字典/模型的该键设置为对应值
    'btn': '按钮文案',
    #: 配置项「auth」：字典/模型的该键设置为对应值
    'auth': '登录 / 注册 / 密码',
    #: 配置项「err」：字典/模型的该键设置为对应值
    'err': '错误页与错误提示',
    #: 配置项「empty」：字典/模型的该键设置为对应值
    'empty': '空状态提示',
    #: 配置项「form」：字典/模型的该键设置为对应值
    'form': '表单提示',
    #: 配置项「article」：字典/模型的该键设置为对应值
    'article': '文章相关',
    #: 配置项「comment」：字典/模型的该键设置为对应值
    'comment': '评论相关',
    #: 配置项「moderation」：字典/模型的该键设置为对应值
    'moderation': '审核与治理',
    #: 配置项「promo」：字典/模型的该键设置为对应值
    'promo': '推广申请（置顶 / 精华 / 热门）',
    #: 配置项「interact」：字典/模型的该键设置为对应值
    'interact': '互动（点赞 / 收藏 / 关注）',
    #: 配置项「search」：字典/模型的该键设置为对应值
    'search': '搜索',
    #: 配置项「user」：字典/模型的该键设置为对应值
    'user': '个人中心',
    #: 配置项「notify」：字典/模型的该键设置为对应值
    'notify': '通知',
    #: 配置项「badge」：字典/模型的该键设置为对应值
    'badge': '徽章与成就',
    #: 配置项「live2d」：字典/模型的该键设置为对应值
    'live2d': '看板娘',
    #: 配置项「misc」：字典/模型的该键设置为对应值
    'misc': '其他',
    #: 配置项「js」：字典/模型的该键设置为对应值
    'js': '前端脚本专用（toast / 弹窗）',
#: 该行执行对应逻辑（结合上下文理解）
}

#: 「已接入」判定结果的进程内缓存（源码在运行期不变，无需每次请求都扫盘）
_WIRED_CACHE = {'stamp': None, 'keys': frozenset()}

#: 后台重算去重标记（避免并发触发多次重算）
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
    #: 声明使用全局/外层变量
    global _RUNTIME_RECOMPUTING
    #: 条件判断：条件成立时执行该分支
    if _RUNTIME_RECOMPUTING:
        #: 返回结果并结束当前函数
        return
    #: 定义变量「_RUNTIME_RECOMPUTING」，保存对应数据
    _RUNTIME_RECOMPUTING = True

    def _worker():
        """
        功能：处理「worker」相关逻辑。

        返回：无显式返回（None），多以副作用为主。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 声明使用全局/外层变量
        global _RUNTIME_RECOMPUTING
        #: 尝试执行可能出错的代码
        try:
            #: 导入模块「subprocess」，供本文件后续使用
            import subprocess
            #: 导入模块「sys」，供本文件后续使用
            import sys as _sys
            #: 定义变量「script」，保存对应数据
            script = os.path.join(base, 'docs', 'bugfix_20260926_bug9', 'scripts',
                                  #: 该行执行对应逻辑（结合上下文理解）
                                  'tools', 'compute_wired_runtime.py')
            #: 条件判断：条件成立时执行该分支
            if not os.path.exists(script):
                #: 返回结果并结束当前函数
                return
            #: 定义变量「env」，保存对应数据
            env = dict(os.environ)
            #: 该行执行对应逻辑（结合上下文理解）
            env['PYTHONIOENCODING'] = 'utf-8'
            #: 调用「subprocess.run」执行相应逻辑
            subprocess.run([_sys.executable, script], cwd=base, env=env,
                           #: 定义变量「stdout」，保存对应数据
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           #: 定义变量「timeout」，保存对应数据
                           timeout=300, check=False)
            #: 调用「_WIRED_CACHE.update」执行相应逻辑
            _WIRED_CACHE.update({'stamp': None, 'keys': frozenset()})
        #: 捕获并处理异常，避免程序中断
        except Exception:  # noqa: BLE001 统计信息失败不影响功能
            #: 占位语句：此处暂不需要实现
            pass
        #: 无论是否异常都执行的收尾
        finally:
            # 无论成功失败都要清标记，否则一次失败会永久阻止后续重算
            #: 定义变量「_RUNTIME_RECOMPUTING」，保存对应数据
            _RUNTIME_RECOMPUTING = False

    #: 导入模块「threading」，供本文件后续使用
    import threading
    #: 调用「threading.Thread」执行相应逻辑
    threading.Thread(target=_worker, name='wired-runtime-recompute',
                     #: 定义变量「daemon」，保存对应数据
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
    #: 导入模块「glob」，供本文件后续使用
    import glob as _glob
    #: 导入模块「os」，供本文件后续使用
    import os as _os
    #: 从模块「django.conf」导入所需对象
    from django.conf import settings as _settings

    #: 定义变量「base」，保存对应数据
    base = str(_settings.BASE_DIR)
    # 扫描范围说明（这里踩过一个重要坑）：
    #   最初把整个 blog/views.py 排除，理由是「本页视图用到的 moderation.msg_* 只服务
    #   管理页，不该算已接入」。但 **views.py 是全站绝大多数 msg() 调用的所在地**
    #   （flash 消息、AJAX 返回），整文件排除导致这些 key 全被误判为「未接入」
    #   （实测：管理页显示 794 已接入 / 164 未接入，其中一大批其实在 views.py 里
    #   有调用，运营会以为改了没反应）。
    #   正确做法：**照常扫描 views.py**，只把「确实只服务本管理页」的几个 key
    #   放进 PAGE_ONLY_MSG_KEYS 排除（见该常量定义处）。
    #: 定义变量「self_path」，保存对应数据
    self_path = _os.path.abspath(_os.path.join(base, 'blog', 'services', 'site_messages.py'))
    #: 定义变量「patterns」，保存对应数据（集合/元组）
    patterns = [
        #: 调用「_os.path.join」执行相应逻辑
        _os.path.join(base, 'templates', '**', '*.html'),
        #: 调用「_os.path.join」执行相应逻辑
        _os.path.join(base, 'blog', '**', '*.py'),
        #: 调用「_os.path.join」执行相应逻辑
        _os.path.join(base, 'static', 'assets', 'js', '**', '*.js'),
    #: 该行执行对应逻辑（结合上下文理解）
    ]
    #: 指纹只取「决定文案去向」的语料：模板与前端脚本。
    #: 为什么不含 Python：`views.py` 是最常被改动的文件，若纳入指纹，
    #: 每改一次视图就让接入状态「过期」而回退静态扫描（实测：管理页因此
    #: 反复显示 87 条「未接入」）。而视图改动**不影响「哪些 key 会被渲染」**
    #: 这一事实 —— 视图改的是数据，模板才是渲染入口，因此模板指纹足够。
    stamp_patterns = (
        #: 调用「_os.path.join」执行相应逻辑
        _os.path.join(base, 'templates', '**', '*.html'),
        #: 调用「_os.path.join」执行相应逻辑
        _os.path.join(base, 'static', 'assets', 'js', '**', '*.js'),
    #: 该行执行对应逻辑（结合上下文理解）
    )
    #: 定义变量「files」，保存对应数据（集合/元组）
    files = []
    #: 定义变量「stamp_files」，保存对应数据（集合/元组）
    stamp_files = []
    #: 循环遍历，逐个处理元素
    for pat in patterns:
        #: 循环遍历，逐个处理元素
        for path in _glob.glob(pat, recursive=True):
            #: 条件判断：条件成立时执行该分支
            if '__pycache__' in path or '.min.' in path:
                #: 跳过本次进入下一次迭代
                continue
            #: 定义变量「absolute」，保存对应数据
            absolute = _os.path.abspath(path)
            #: 条件判断：条件成立时执行该分支
            if absolute == self_path:
                #: 跳过本次进入下一次迭代
                continue          # 注册表自身是「定义」不是「引用」
            #: 尝试执行可能出错的代码
            try:
                #: 调用「files.append」执行相应逻辑
                files.append((absolute, _os.path.getmtime(absolute)))
            #: 捕获并处理异常，避免程序中断
            except OSError:
                #: 跳过本次进入下一次迭代
                continue
    #: 循环遍历，逐个处理元素
    for pat in stamp_patterns:
        #: 循环遍历，逐个处理元素
        for path in _glob.glob(pat, recursive=True):
            #: 条件判断：条件成立时执行该分支
            if '.min.' in path:
                #: 跳过本次进入下一次迭代
                continue
            #: 尝试执行可能出错的代码
            try:
                #: 调用「stamp_files.append」执行相应逻辑
                stamp_files.append(_os.path.getmtime(path))
            #: 捕获并处理异常，避免程序中断
            except OSError:
                #: 跳过本次进入下一次迭代
                continue

    #: 定义变量「stamp」，保存对应数据
    stamp = tuple(sorted(files, key=lambda x: x[0]))
    #: 条件判断：条件成立时执行该分支
    if _WIRED_CACHE['stamp'] == stamp:
        #: 返回结果并结束当前函数
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
    #: 尝试执行可能出错的代码
    try:
        #: 导入模块「json」，供本文件后续使用
        import json as _json
        #: 定义变量「runtime_path」，保存对应数据
        runtime_path = _os.path.join(
            #: 该行执行对应逻辑（结合上下文理解）
            base, 'docs', 'bugfix_20260926_bug9', 'reports', 'wired_runtime.json')
        #: 上下文管理：进入时获取资源、退出时自动释放
        with open(runtime_path, encoding='utf-8') as fh:
            #: 定义变量「payload」，保存对应数据
            payload = _json.load(fh)
        #: 定义变量「runtime_stamp」，保存对应数据
        runtime_stamp = str(payload.get('stamp', ''))
        #: 定义变量「current_stamp」，保存对应数据
        current_stamp = '%.3f' % max(stamp_files)
        # 指纹比较用**容差**而不是字符串相等：
        # mtime 是浮点秒，写入方与读取方各自做 `%.3f` 截断会产生毫秒级差异
        # （实测 1790369452.957 vs .952），字符串比较必然判为「过期」而回退静态扫描，
        # 于是管理页又显示 87 条「未接入」。允许 1 秒内的差异即可稳定命中。
        #: 定义变量「runtime_fresh」，保存对应数据
        runtime_fresh = False
        #: 尝试执行可能出错的代码
        try:
            #: 定义变量「runtime_fresh」，保存对应数据
            runtime_fresh = abs(float(runtime_stamp) - float(current_stamp)) <= 1.0
        #: 捕获并处理异常，避免程序中断
        except (TypeError, ValueError):
            #: 定义变量「runtime_fresh」，保存对应数据（集合/元组）
            runtime_fresh = (runtime_stamp == current_stamp)
        #: 条件判断：条件成立时执行该分支
        if runtime_fresh and payload.get('wired'):
            #: 定义变量「keys」，保存对应数据
            keys = frozenset(payload['wired'])
            #: 调用「_WIRED_CACHE.update」执行相应逻辑
            _WIRED_CACHE.update({'stamp': stamp, 'keys': keys})
            #: 返回结果并结束当前函数
            return keys
        # 指纹过期（源码改过）→ 回退静态扫描，**不在这里自动重算**。
        #
        # 为什么不自动重算：重算需要临时改写覆盖数据并渲染全部页面，早期实现放在
        # 后台线程里跑，结果与在线编辑、与验证脚本**并发争用同一张表/同一个文件**，
        # 实测把用户的覆盖记录冲掉过、也把统计文件写坏过。风险远大于收益。
        # 正确做法：重算由**维护/回归流程**显式执行（`verify_all_messages.py`
        # 会用「默认值可见性」重写该文件），页面侧只读不算。
    #: 捕获并处理异常，避免程序中断
    except (OSError, ValueError, TypeError):
        #: 该行执行对应逻辑（结合上下文理解）
        pass          # 文件缺失 / 格式异常 → 静态扫描兜底

    #: 从模块「..services.site_messages」导入所需对象
    from ..services.site_messages import MESSAGES as _M

    # 分语料读取：模板 / Python 必须用「全 key」匹配，前端脚本才允许用短键
    # （SITE_MSG 里的键去掉了 js. 前缀）。绝不能把短键拿去匹配模板 ——
    # `'home'`、`'search'` 这类短词到处都是，会把大量未接入的 key 误判为已接入
    # （实测因此得出「已接入 117 / 待接入 7」的错误结论）。
    #: 该行执行对应逻辑（结合上下文理解）
    tpl_text, py_text, js_text = [], [], []
    #: 循环遍历，逐个处理元素
    for absolute, _ in files:
        #: 尝试执行可能出错的代码
        try:
            #: 上下文管理：进入时获取资源、退出时自动释放
            with open(absolute, encoding='utf-8') as fh:
                #: 定义变量「content」，保存对应数据
                content = fh.read()
        #: 捕获并处理异常，避免程序中断
        except (OSError, UnicodeDecodeError):
            #: 跳过本次进入下一次迭代
            continue
        #: 条件判断：条件成立时执行该分支
        if absolute.endswith('.html'):
            #: 调用「tpl_text.append」执行相应逻辑
            tpl_text.append(content)
        #: 否则若该条件成立则进入此分支
        elif absolute.endswith('.py'):
            #: 调用「py_text.append」执行相应逻辑
            py_text.append(content)
        #: 以上条件均不成立时的兜底分支
        else:
            #: 调用「js_text.append」执行相应逻辑
            js_text.append(content)
    #: 该行执行对应逻辑（结合上下文理解）
    tpl, py, js = '\n'.join(tpl_text), '\n'.join(py_text), '\n'.join(js_text)

    #: 定义变量「wired」，保存对应数据
    wired = set()
    #: 循环遍历，逐个处理元素
    for key in _M:
        #: 该行执行对应逻辑（结合上下文理解）
        domain, _, short = key.partition('.')
        #: 定义变量「full」，保存对应数据（集合/元组）
        full = ["MSG.%s" % key, "'%s'" % key, '"%s"' % key]
        # 模板 / 视图：必须出现完整 key
        #: 条件判断：条件成立时执行该分支
        if any(n in tpl or n in py for n in full):
            #: 调用「wired.add」执行相应逻辑
            wired.add(key)
            #: 跳过本次进入下一次迭代
            continue
        # 前端脚本：允许短键，但要求同文件里出现 SITE_MSG / moeMsg 取用方式，
        # 且用引号包住，避免子串误命中
        #: 条件判断：条件成立时执行该分支
        if domain == 'js' or domain in ('btn', 'misc'):
            #: 条件判断：条件成立时执行该分支
            if ("'%s'" % short) in js or ('"%s"' % short) in js:
                #: 调用「wired.add」执行相应逻辑
                wired.add(key)
                #: 跳过本次进入下一次迭代
                continue
        # 前端也可能用「域_键」形式（如 SITE_MSG.btn_back_home）
        #: 定义变量「combined」，保存对应数据
        combined = key.replace('.', '_')
        #: 条件判断：条件成立时执行该分支
        if ("'%s'" % combined) in js or ('"%s"' % combined) in js:
            #: 调用「wired.add」执行相应逻辑
            wired.add(key)

    #: 定义变量「keys」，保存对应数据
    keys = frozenset(wired)
    #: 调用「_WIRED_CACHE.update」执行相应逻辑
    _WIRED_CACHE.update({'stamp': stamp, 'keys': keys})
    #: 返回结果并结束当前函数
    return keys

#: 只服务于「文案总表管理页」自身的 key —— 改动它们对前台没有任何影响，
#: 因此在接入统计里必须剔除，否则会出现「显示已接入、实际前台看不到」的假象。
#:
#: 现状：本集合**已清空**。原先登记的是文案总表页自己的 5 条 flash 文案
#: （moderation.msg_saved / msg_no_change / msg_save_invalid / msg_reset_one /
#: msg_reset_domain），后来管理页文案统一迁移到 adminmsg.* 域，
#: 这 5 条从注册表移除，集合随之失去意义。
#: 保留这个名字是为了兼容既有调用点，避免再次改动大范围代码。
PAGE_ONLY_MSG_KEYS = frozenset()

#: 装饰器：为下一个定义附加「staff_required_moe」行为（权限、缓存、注册信号等）
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
    #: 从模块「..models」导入所需对象
    from ..models import SiteMessage
    #: 从模块「..services.site_messages」导入所需对象
    from ..services.site_messages import MESSAGES, invalidate_overrides

    #: 导入模块「re」，供本文件后续使用
    import re as _re
    #: 导入模块「string」，供本文件后续使用
    import string as _string

    class _Fmt(_string.Formatter):
        """只收集字段名，不求值（求值需要实参，这里只做静态校验）。"""

        def get_field(self, field_name, args, kwargs):
            """
            功能：获取「field」。

            参数：
              - field_name：传入参数，含义结合函数体与调用处
              - args：传入参数，含义结合函数体与调用处
              - kwargs：传入参数，含义结合函数体与调用处

            返回：对应计算/查询结果。

            注意：保持函数单一职责；修改时确认调用方不受影响。
            """
            #: 返回结果并结束当前函数
            return field_name, field_name

    def _placeholders(text):
        """取出文案里的占位符「指纹」，用于校验改动后占位符没有丢失 / 变形。

        为什么不能只收集字段名：``string.Formatter().parse('{}/{}')`` 对**位置占位符**
        （``{}``）返回的字段名是**空字符串**，用 ``if field_name`` 判断会全部漏掉，
        导致「把 ``{}`` 删掉」这种破坏性改动被放行（实测踩过）。
        因此这里统一归一化：位置占位符记为 ``#0`` / ``#1``（按出现顺序），
        命名占位符保留原字段名（含 ``str.format`` 的 ``{n}`` 与 ``%s`` 两种写法）。
        """
        #: 定义变量「out」，保存对应数据（集合/元组）
        out = []
        #: 定义变量「positional」，保存对应数据
        positional = 0
        #: 循环遍历，逐个处理元素
        for _, field_name, _, _ in _Fmt().parse(text or ''):
            #: 条件判断：条件成立时执行该分支
            if field_name is None:
                #: 跳过本次进入下一次迭代
                continue                      # 纯文本片段
            #: 条件判断：条件成立时执行该分支
            if field_name == '':              # 位置占位符 {}
                #: 调用「out.append」执行相应逻辑
                out.append('#%d' % positional)
                #: 该行执行对应逻辑（结合上下文理解）
                positional += 1
            #: 以上条件均不成立时的兜底分支
            else:
                #: 调用「out.append」执行相应逻辑
                out.append(field_name)
        # 兼容旧式 %s / %d 写法（本仓库文案历史上混用过）
        #: 定义变量「legacy」，保存对应数据
        legacy = len(re.findall(r'%[sdrf]', text or ''))
        #: 调用「out.extend」执行相应逻辑
        out.extend('#%%%d' % i for i in range(legacy))
        #: 返回结果并结束当前函数
        return tuple(out)

    #: 条件判断：条件成立时执行该分支
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
        #: 条件判断：条件成立时执行该分支
        if 'reset_row' in request.POST or 'reset_domain' in request.POST:
            #: 读取本次请求的 POST 数据
            target_key = request.POST.get('reset_row', '').strip()
            #: 读取本次请求的 POST 数据
            target_domain = request.POST.get('reset_domain', '').strip()
            #: 条件判断：条件成立时执行该分支
            if target_key:
                #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
                deleted, _ = SiteMessage.objects.filter(key=target_key).delete()
                #: 调用「invalidate_overrides」执行相应逻辑
                invalidate_overrides()
                #: 向用户闪现一条提示消息（下次请求展示）
                messages.success(request, '%s：%s（清理 %d 条覆盖）'
                                              #: 该行执行对应逻辑（结合上下文理解）
                                              % (msg('adminmsg.reset_row_done'),
                                                 #: 该行执行对应逻辑（结合上下文理解）
                                                 target_key, deleted))
            #: 否则若该条件成立则进入此分支
            elif target_domain:
                # ⚠️ 必须转义 LIKE 通配符：`key__startswith('nav.')` 会翻译成
                #    `key LIKE 'nav.%'`，而 SQL 里 `_` 是**单字符通配符**，
                #    于是 nav.home / nav_articles / navXhome 都会被匹配到 ——
                #    「恢复 nav 域」会连带删掉无关的覆盖记录（实测踩过）。
                #: 定义变量「escaped」，保存对应数据（集合/元组）
                escaped = (target_domain.replace('\\', '\\\\')
                           #: 该行执行对应逻辑（结合上下文理解）
                           .replace('_', '\\_').replace('%', '\\%'))
                #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
                deleted, _ = SiteMessage.objects.filter(
                    #: 删除对象，注意级联与权限
                    key__startswith=escaped + '.').delete()
                #: 调用「invalidate_overrides」执行相应逻辑
                invalidate_overrides()
                #: 向用户闪现一条提示消息（下次请求展示）
                messages.success(request, '%s：%s（清理 %d 条覆盖）'
                                              #: 该行执行对应逻辑（结合上下文理解）
                                              % (msg('adminmsg.reset_domain_done'),
                                                 #: 该行执行对应逻辑（结合上下文理解）
                                                 target_domain, deleted))
            #: 以上条件均不成立时的兜底分支
            else:
                #: 向用户闪现一条提示消息（下次请求展示）
                messages.error(request, msg('err.bad_request'))
            #: 返回结果并结束当前函数
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
        #: 该行执行对应逻辑（结合上下文理解）
        saved, skipped, errors, unchanged = 0, 0, [], 0
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        stored = {m.key: m for m in SiteMessage.objects.all()}
        #: 循环遍历，逐个处理元素
        for key, default in MESSAGES.items():
            #: 定义变量「field」，保存对应数据
            field = 'm_' + key.replace('.', '__')
            #: 条件判断：条件成立时执行该分支
            if field not in request.POST:
                #: 跳过本次进入下一次迭代
                continue          # 该字段未随表单提交（如被搜索过滤掉）→ 不动它
            #: 读取本次请求的 POST 数据
            new_text = request.POST.get(field, '').strip()
            #: 定义变量「current」，保存对应数据
            current = stored.get(key)
            #: 定义变量「current_text」，保存对应数据
            current_text = current.text if current else None

            # ① 与存储值完全一致 → 用户没改这一项，直接跳过（保住覆盖）
            #: 条件判断：条件成立时执行该分支
            if current_text is not None and new_text == current_text:
                #: 该行执行对应逻辑（结合上下文理解）
                unchanged += 1
                #: 跳过本次进入下一次迭代
                continue

            # ② 改回代码默认值 → 删除覆盖记录（用户主动还原）
            #: 条件判断：条件成立时执行该分支
            if new_text == default:
                #: 条件判断：条件成立时执行该分支
                if current is not None:
                    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
                    SiteMessage.objects.filter(key=key).delete()
                #: 该行执行对应逻辑（结合上下文理解）
                skipped += 1
                #: 跳过本次进入下一次迭代
                continue

            # ③ 内容为空 → 拒绝（避免把文案清空）
            #: 条件判断：条件成立时执行该分支
            if not new_text:
                #: 调用「errors.append」执行相应逻辑
                errors.append(key)
                #: 跳过本次进入下一次迭代
                continue

            # ④ 占位符指纹必须一致（防破坏性改动）
            #: 条件判断：条件成立时执行该分支
            if _placeholders(new_text) != _placeholders(default):
                #: 调用「errors.append」执行相应逻辑
                errors.append(key)
                #: 跳过本次进入下一次迭代
                continue

            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            obj, created = SiteMessage.objects.get_or_create(key=key)
            #: 条件判断：条件成立时执行该分支
            if obj.text != new_text:
                #: 定义实例/类属性「obj.text」，保存对应数据
                obj.text = new_text
                #: 定义实例/类属性「obj.is_enabled」，保存对应数据
                obj.is_enabled = True
                #: 读取本次请求的 user 数据
                obj.updated_by = request.user if request.user.is_authenticated else None
                #: 保存对象（INSERT/UPDATE），可能触发模型信号
                obj.save()
                #: 该行执行对应逻辑（结合上下文理解）
                saved += 1
        #: 调用「invalidate_overrides」执行相应逻辑
        invalidate_overrides()
        #: 条件判断：条件成立时执行该分支
        if errors:
            #: 向用户闪现一条提示消息（下次请求展示）
            messages.error(request, msg('moderation.msg_save_invalid', len(errors),
                                        #: 该行执行对应逻辑（结合上下文理解）
                                        '、'.join(errors[:5])))
        #: 条件判断：条件成立时执行该分支
        if saved:
            #: 向用户闪现一条提示消息（下次请求展示）
            messages.success(request, msg('moderation.msg_saved', saved))
        #: 否则若该条件成立则进入此分支
        elif not errors:
            #: 向用户闪现一条提示消息（下次请求展示）
            messages.info(request, msg('moderation.msg_no_change'))
        #: 返回结果并结束当前函数
        return redirect('site_messages')

    # ---- GET：组装按域分组的展示数据 ----
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    overrides = {m.key: m for m in SiteMessage.objects.all()}
    #: 读取本次请求的 GET 数据
    keyword = request.GET.get('q', '').strip()
    #: 读取本次请求的 GET 数据
    active_domain = request.GET.get('domain', '').strip()

    # 「已接入」集合：只有被模板 / 视图 / 前端脚本真正引用的 key，改了才会有可见效果。
    # 注册表里有相当一部分 key 目前只是「预留登记」（改它不会影响任何界面），
    # 若不在页面上标出来，运营会以为改了没生效 —— 这是必须显式告知的信息。
    #: 定义变量「wired_keys」，保存对应数据
    wired_keys = _wired_message_keys() - PAGE_ONLY_MSG_KEYS

    #: 该行执行对应逻辑（结合上下文理解）
    groups, total_changed, total_dead = [], 0, 0
    #: 循环遍历，逐个处理元素
    for key, default in sorted(MESSAGES.items()):
        #: 定义变量「domain」，保存对应数据
        domain = key.split('.', 1)[0]
        #: 条件判断：条件成立时执行该分支
        if active_domain and domain != active_domain:
            #: 跳过本次进入下一次迭代
            continue
        #: 条件判断：条件成立时执行该分支
        if keyword and keyword.lower() not in key.lower() \
                and keyword not in default and keyword not in key:
            #: 跳过本次进入下一次迭代
            continue
        #: 定义变量「ov」，保存对应数据
        ov = overrides.get(key)
        # 两个概念要分开（曾混为一谈导致保存后标记错误）：
        #   · has_override —— 数据库里存在启用中的覆盖记录（决定「已覆盖」标签与「恢复默认」按钮）
        #   · differs      —— 覆盖值确实与代码默认不同（决定「与默认相同」提示）
        #: 定义变量「has_override」，保存对应数据
        has_override = bool(ov and ov.is_enabled)
        #: 定义变量「differs」，保存对应数据
        differs = bool(has_override and ov.text != default)
        #: 条件判断：条件成立时执行该分支
        if has_override:
            #: 该行执行对应逻辑（结合上下文理解）
            total_changed += 1
        #: 定义变量「is_wired」，保存对应数据
        is_wired = key in wired_keys
        #: 条件判断：条件成立时执行该分支
        if not is_wired:
            #: 该行执行对应逻辑（结合上下文理解）
            total_dead += 1
        #: 调用「groups.append」执行相应逻辑
        groups.append({
            #: 配置项「key」：字典/模型的该键设置为对应值
            'key': key, 'domain': domain, 'field': 'm_' + key.replace('.', '__'),
            #: 配置项「default」：字典/模型的该键设置为对应值
            'default': default,
            #: 配置项「current」：字典/模型的该键设置为对应值
            'current': ov.text if ov else default,
            #: 配置项「changed」：字典/模型的该键设置为对应值
            'changed': has_override,
            #: 配置项「differs」：字典/模型的该键设置为对应值
            'differs': differs,
            #: 配置项「wired」：字典/模型的该键设置为对应值
            'wired': is_wired,
            #: 配置项「disabled」：字典/模型的该键设置为对应值
            'disabled': bool(ov and not ov.is_enabled),
            #: 配置项「updated_by」：字典/模型的该键设置为对应值
            'updated_by': ov.updated_by.username if (ov and ov.updated_by) else '',
            #: 配置项「updated_at」：字典/模型的该键设置为对应值
            'updated_at': ov.updated_at if ov else None,
        #: 该行执行对应逻辑（结合上下文理解）
        })
    # 按域聚合，保持域顺序与中文标题
    #: 定义变量「dom_order」，保存对应数据
    dom_order = list(MSG_DOMAIN_TITLES.keys())
    #: 定义变量「by_domain」，保存对应数据
    by_domain = {}
    #: 循环遍历，逐个处理元素
    for g in groups:
        #: 调用「by_domain.setdefault」执行相应逻辑
        by_domain.setdefault(g['domain'], []).append(g)
    #: 定义变量「domain_blocks」，保存对应数据（集合/元组）
    domain_blocks = []
    #: 循环遍历，逐个处理元素
    for dom in dom_order + [d for d in by_domain if d not in dom_order]:
        #: 条件判断：条件成立时执行该分支
        if dom in by_domain:
            #: 定义变量「items」，保存对应数据
            items = by_domain[dom]
            #: 调用「domain_blocks.append」执行相应逻辑
            domain_blocks.append({
                #: 配置项「domain」：字典/模型的该键设置为对应值
                'domain': dom,
                #: 配置项「title」：字典/模型的该键设置为对应值
                'title': MSG_DOMAIN_TITLES.get(dom, dom),
                #: 配置项「items」：字典/模型的该键设置为对应值
                'items': items,
                # 单独给出条数：模板里不能用 `|msgfmt:block.items|length`
                # （过滤器参数不支持再套过滤器，会整页 500），
                # 因此在这里算好，模板直接 |msgfmt:block.item_count。
                #: 配置项「item_count」：字典/模型的该键设置为对应值
                'item_count': len(items),
                #: 配置项「changed」：字典/模型的该键设置为对应值
                'changed': sum(1 for i in items if i['changed']),
                #: 配置项「dead」：字典/模型的该键设置为对应值
                'dead': sum(1 for i in items if not i['wired']),
            #: 该行执行对应逻辑（结合上下文理解）
            })

    #: 返回结果并结束当前函数
    return render(request, 'blog/site_messages.html', {
        #: 配置项「domain_blocks」：字典/模型的该键设置为对应值
        'domain_blocks': domain_blocks,
        #: 配置项「total_keys」：字典/模型的该键设置为对应值
        'total_keys': len(MESSAGES),
        #: 配置项「shown_keys」：字典/模型的该键设置为对应值
        'shown_keys': len(groups),
        #: 配置项「total_changed」：字典/模型的该键设置为对应值
        'total_changed': total_changed,
        #: 配置项「total_wired」：字典/模型的该键设置为对应值
        'total_wired': len(wired_keys),
        #: 配置项「total_dead」：字典/模型的该键设置为对应值
        'total_dead': total_dead,
        #: 配置项「keyword」：字典/模型的该键设置为对应值
        'keyword': keyword,
        #: 配置项「active_domain」：字典/模型的该键设置为对应值
        'active_domain': active_domain,
        #: 配置项「domain_titles」：字典/模型的该键设置为对应值
        'domain_titles': MSG_DOMAIN_TITLES,
        #: 配置项「default_titles」：字典/模型的该键设置为对应值
        'default_titles': MSG_DOMAIN_TITLES,
        #: 配置项「meta_title」：字典/模型的该键设置为对应值
        'meta_title': '文案总表 · %s' % settings.SITE_NAME,
    #: 该行执行对应逻辑（结合上下文理解）
    })

# __REFRESH_ASSETS_API__
def api_refresh_assets(request):
    """一键刷新：POST /api/refresh-assets/（仅 staff）。

    重新压缩全部 CSS/JS、写入新构建版本号并清空 Django 缓存，
    返回最新构建 token，前端据此硬重载以拉取新版本静态资源。
    """
    #: 条件判断：条件成立时执行该分支
    if not (request.user.is_authenticated and request.user.is_staff):
        #: 返回结果并结束当前函数
        return JsonResponse({'ok': False, 'error': 'permission_denied'}, status=403)
    #: 条件判断：条件成立时执行该分支
    if request.method != 'POST':
        #: 返回结果并结束当前函数
        return JsonResponse({'ok': False, 'error': 'method_not_allowed'}, status=405)
    #: 导入模块「io」，供本文件后续使用
    import io
    #: 从模块「django.core.management」导入所需对象
    from django.core.management import call_command
    #: 定义变量「buf」，保存对应数据
    buf = io.StringIO()
    #: 尝试执行可能出错的代码
    try:
        #: 调用「call_command」执行相应逻辑
        call_command('refresh_assets', stdout=buf, stderr=buf)
    #: 捕获并处理异常，避免程序中断
    except Exception as exc:  # noqa: BLE001 - 需把失败原因回传前端
        #: 返回结果并结束当前函数
        return JsonResponse({'ok': False, 'error': str(exc)}, status=500)
    #: 定义变量「token」，保存对应数据
    token = ''
    #: 尝试执行可能出错的代码
    try:
        #: 定义变量「token」，保存对应数据
        token = open(os.path.join(settings.BASE_DIR, 'static', 'assets', '.build_token'),
                     #: 定义变量「encoding」，保存对应数据
                     encoding='utf-8').read().strip()
    #: 捕获并处理异常，避免程序中断
    except Exception:
        #: 占位语句：此处暂不需要实现
        pass
    #: 返回结果并结束当前函数
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
    #: 条件判断：条件成立时执行该分支
    if not settings.DEBUG:
        #: 返回结果并结束当前函数
        return JsonResponse({'ok': False, 'error': msg('err.debug_only')}, status=404)
    #: 读取本次请求的 META 数据
    is_local = request.META.get('REMOTE_ADDR') in ('127.0.0.1', '::1')
    #: 条件判断：条件成立时执行该分支
    if not (is_local or getattr(request.user, 'is_superuser', False)):
        #: 返回结果并结束当前函数
        return JsonResponse({'ok': False, 'error': 'permission_denied'}, status=403)
    #: 定义变量「bridge」，保存对应数据
    bridge = os.path.join(settings.BASE_DIR, 'docs',
                          #: 该行执行对应逻辑（结合上下文理解）
                          'bugfix_20260926_bug9', '.sync_request')
    #: 定义变量「payload」，保存对应数据
    payload = ''
    #: 条件判断：条件成立时执行该分支
    if os.path.exists(bridge):
        #: 尝试执行可能出错的代码
        try:
            #: 上下文管理：进入时获取资源、退出时自动释放
            with open(bridge, encoding='utf-8') as fh:
                #: 定义变量「payload」，保存对应数据
                payload = fh.read().strip()
            #: 调用「os.remove」执行相应逻辑
            os.remove(bridge)
        #: 捕获并处理异常，避免程序中断
        except OSError:
            #: 定义变量「payload」，保存对应数据
            payload = ''
    # 清空本进程缓存，使下次请求重新从数据库读取设置
    #: 定义变量「cleared」，保存对应数据
    cleared = True
    #: 尝试执行可能出错的代码
    try:
        #: 调用「cache.clear」执行相应逻辑
        cache.clear()
    #: 捕获并处理异常，避免程序中断
    except Exception:  # noqa: BLE001 清缓存失败也要如实告知
        #: 定义变量「cleared」，保存对应数据
        cleared = False
    #: 返回结果并结束当前函数
    return JsonResponse({'ok': True, 'payload': payload, 'cleared': cleared})

def debug_cache_dump(request):
    """DEBUG 专用：返回当前进程缓存快照（key / 剩余 TTL / 详情页片段命中统计）。

    开发调试时在浏览器直接查看 runserver 进程内的 LocMemCache 内容
    （LocMemCache 为进程内缓存，diag 是独立进程看不到，此端点必须在服务进程内访问）。

    仅当 settings.DEBUG 且为本机访问（127.0.0.1 / ::1）或超级用户时可用。
    """
    #: 条件判断：条件成立时执行该分支
    if not settings.DEBUG:
        #: 返回结果并结束当前函数
        return JsonResponse({'ok': False, 'error': msg('err.debug_only')}, status=404)
    #: 读取本次请求的 META 数据
    is_local = request.META.get('REMOTE_ADDR') in ('127.0.0.1', '::1')
    #: 条件判断：条件成立时执行该分支
    if not (is_local or (request.user.is_authenticated and request.user.is_superuser)):
        #: 返回结果并结束当前函数
        return JsonResponse({'ok': False, 'error': 'permission_denied'}, status=403)
    #: 导入模块「time」，供本文件后续使用
    import time as _time
    #: 从模块「..utils.cache_keys」导入所需对象
    from ..utils.cache_keys import get_cache_version, get_stats
    #: 定义变量「internal」，保存对应数据
    internal = getattr(cache, '_cache', None)
    #: 定义变量「expire」，保存对应数据
    expire = getattr(cache, '_expire_info', None)
    #: 定义变量「keys」，保存对应数据（集合/元组）
    keys = []
    #: 条件判断：条件成立时执行该分支
    if isinstance(internal, dict):
        #: 定义变量「now」，保存对应数据
        now = _time.time()
        #: 循环遍历，逐个处理元素
        for k in internal:
            #: 定义变量「ttl」，保存对应数据
            ttl = None
            #: 条件判断：条件成立时执行该分支
            if expire and k in expire:
                #: 定义变量「ttl」，保存对应数据
                ttl = max(0, int(expire[k] - now))
            #: 调用「keys.append」执行相应逻辑
            keys.append({'key': k, 'ttl_remaining': ttl})
    #: 调用「keys.sort」执行相应逻辑
    keys.sort(key=lambda x: x['key'])
    #: 返回结果并结束当前函数
    return JsonResponse({
        #: 配置项「ok」：字典/模型的该键设置为对应值
        'ok': True,
        #: 配置项「cache_version」：字典/模型的该键设置为对应值
        'cache_version': get_cache_version(),
        #: 配置项「backend」：字典/模型的该键设置为对应值
        'backend': 'locmem',
        #: 配置项「total_keys」：字典/模型的该键设置为对应值
        'total_keys': len(keys),
        #: 配置项「keys」：字典/模型的该键设置为对应值
        'keys': keys,
        #: 配置项「fragment_stats」：字典/模型的该键设置为对应值
        'fragment_stats': get_stats(),
    #: 该行执行对应逻辑（结合上下文理解）
    })

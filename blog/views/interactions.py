# -*- coding: utf-8 -*-

"""互动域：点赞、收藏、评分、分享、热门文章、导出与短链接。"""

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
#: 从模块「io」导入所需对象
from io import BytesIO
#: 从模块「django.contrib.auth.decorators」导入所需对象
from django.contrib.auth.decorators import login_required
#: 从模块「django.core.cache」导入所需对象
from django.core.cache import cache
#: 从模块「..utils.cache_keys」导入所需对象
from ..utils.cache_keys import (
    #: 该行执行对应逻辑（结合上下文理解）
    DETAIL_TTL, MISSING_TTL, cache_get, cache_get_or_set,
    #: 该行执行对应逻辑（结合上下文理解）
    cache_set, detail_keys, invalidate_article,
#: 该行执行对应逻辑（结合上下文理解）
)
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
#: 从模块「django.template.loader」导入所需对象
from django.template.loader import render_to_string
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

#: 从模块「.common」导入所需对象
from .common import HOT_ARTICLES_KEY, _bad_request, _json_ok, logger

#: 从模块「.users」导入所需对象
from .users import check_and_award_badges


#: 定义变量「logger」，保存对应数据
logger = logging.getLogger('blog.views')

def _hot_articles_cached(limit=10, timeout=300):
    # 第2轮迭代#63: 热门文章缓存——按阅读量倒序并短 TTL 缓存
    # 第3轮迭代#3: 缓存键统一为 HOT_ARTICLES_KEY，与信号失效键对齐
    """
    功能：处理「hot articles cached」相关逻辑。

    参数：
      - limit（可选，有默认值）：传入参数，含义结合函数体与调用处
      - timeout（可选，有默认值）：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：含 Django ORM 数据库查询，注意查询性能与空结果处理；读写缓存，注意缓存键口径与失效策略。
    """
    #: 定义变量「key」，保存对应数据
    key = HOT_ARTICLES_KEY
    #: 返回结果并结束当前函数
    return cache.get_or_set(key, lambda: list(
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        Article.objects.filter(status=Article.Status.PUBLISHED)
        #: 对查询结果按字段排序
        .order_by('-views')[:limit]), timeout)

def _hot_articles_for_range(range_key, limit=10):
    """右栏热门榜数据，返回 list[dict(a=Article, heat=int, label=str)]。

    - total：按累计阅读量 views 排序；
    - week/month：按 AccessLog 在最近 7/30 天内对 /article/<pk>/ 的访问计数排序，
      AccessLog 无文章外键，用 path 解析出文章主键，再回表取已发布文章。
    """
    #: 导入模块「re」，供本文件后续使用
    import re as _re
    #: 从模块「datetime」导入所需对象
    from datetime import timedelta as _timedelta
    #: 从模块「django.db.models」导入所需对象
    from django.db.models import Count as _Count
    #: 从模块「django.utils」导入所需对象
    from django.utils import timezone as _tz
    #: 定义变量「range_key」，保存对应数据
    range_key = range_key if range_key in ('week', 'month', 'total') else 'week'
    # 总榜：直接按 views 倒序
    #: 条件判断：条件成立时执行该分支
    if range_key == 'total':
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        qs = (Article.objects.filter(status=Article.Status.PUBLISHED, is_deleted=False)
              #: 对查询结果按字段排序
              .order_by('-views')[:limit])
        #: 返回结果并结束当前函数
        return [{'a': a, 'heat': a.views, 'label': ''} for a in qs]
    # 周榜/月榜：时间窗内按文章路径分组计数
    #: 定义变量「days」，保存对应数据
    days = 7 if range_key == 'week' else 30
    #: 定义变量「cutoff」，保存对应数据
    cutoff = _tz.now() - _timedelta(days=days)
    # 仅统计「成功(200)的 GET 详情页访问」：排除无斜杠 /article/<pk> 的 301 重定向
    # （它会与带斜杠的 200 重复计数）、POST 及异常状态码请求，保证周/月榜热度真实。
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    rows = (AccessLog.objects.filter(
                #: 定义变量「created_at__gte」，保存对应数据
                created_at__gte=cutoff, path__startswith='/article/',
                #: 定义变量「status_code」，保存对应数据
                status_code=200, method='GET')
            #: 对查询结果按字段排序
            .values('path').annotate(n=_Count('id')).order_by('-n')[:limit * 2])
    #: 定义变量「pks」，保存对应数据（集合/元组）
    pks = []
    #: 循环遍历，逐个处理元素
    for row in rows:
        #: 定义变量「m」，保存对应数据
        m = _re.search(r'/article/(\d+)/?$', row.get('path') or '')
        #: 条件判断：条件成立时执行该分支
        if m:
            #: 调用「pks.append」执行相应逻辑
            pks.append((int(m.group(1)), row['n']))
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    art_map = {x.pk: x for x in Article.objects.filter(
        #: 定义变量「status」，保存对应数据
        status=Article.Status.PUBLISHED, is_deleted=False, pk__in=[p for p, _ in pks])}
    #: 定义变量「label」，保存对应数据
    label = '本周' if range_key == 'week' else '本月'
    #: 定义变量「out」，保存对应数据（集合/元组）
    out = []
    #: 循环遍历，逐个处理元素
    for pk, n in pks:
        #: 定义变量「a」，保存对应数据
        a = art_map.get(pk)
        #: 条件判断：条件成立时执行该分支
        if a:
            #: 调用「out.append」执行相应逻辑
            out.append({'a': a, 'heat': n, 'label': label})
        #: 条件判断：条件成立时执行该分支
        if len(out) >= limit:
            #: 跳出当前循环
            break
    #: 返回结果并结束当前函数
    return out

def api_hot_articles(request):
    """右栏热门榜片段接口：GET ?range=week|month|total，返回可直接替换 .hot-list 的 HTML。"""
    #: 读取本次请求的 GET 数据
    range_key = request.GET.get('range', 'week')
    # 片段按 range 缓存 120s，避免每次点击都跑 AccessLog 聚合
    #: 定义变量「key」，保存对应数据
    key = 'hot_frag_%s' % range_key
    #: 读写缓存，减轻数据库压力，注意键与过期时间
    html = cache.get(key)
    #: 条件判断：条件成立时执行该分支
    if html is None:
        #: 定义变量「items」，保存对应数据
        items = _hot_articles_for_range(range_key)
        #: 定义变量「html」，保存对应数据
        html = render_to_string('partials/_hot_list.html',
                                #: 该行执行对应逻辑（结合上下文理解）
                                {'hot_items': items, 'range_key': range_key}, request)
        #: 读写缓存，减轻数据库压力，注意键与过期时间
        cache.set(key, html, 120)
    #: 返回结果并结束当前函数
    return HttpResponse(html)

def _site_stats_cached(timeout=3600):
    # 第2轮迭代#66: 统计数据缓存——全站文章数/总阅读量按小时缓存
    """
    功能：处理「site stats cached」相关逻辑。

    参数：
      - timeout（可选，有默认值）：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：含 Django ORM 数据库查询，注意查询性能与空结果处理；读写缓存，注意缓存键口径与失效策略。
    """
    #: 定义变量「key」，保存对应数据
    key = 'footer_stats'
    def _build():
        """
        功能：构建「build」。

        返回：对应计算/查询结果。

        注意：含 Django ORM 数据库查询，注意查询性能与空结果处理。
        """
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        published = Article.objects.filter(status=Article.Status.PUBLISHED)
        #: 返回结果并结束当前函数
        return {
            #: 配置项「article_count」：字典/模型的该键设置为对应值
            'article_count': published.count(),
            #: 使用聚合函数做统计查询
            'views_total': published.aggregate(v=Sum('views'))['v'] or 0,
        #: 该行执行对应逻辑（结合上下文理解）
        }
    #: 返回结果并结束当前函数
    return cache.get_or_set(key, _build, timeout)

def _article_detail_cached(pk, timeout=120):
    # 第2轮迭代#68: 文章详情缓存——仅缓存公开已发布文章的轻量字段
    """
    功能：处理「article detail cached」相关逻辑。

    参数：
      - pk：传入参数，含义结合函数体与调用处
      - timeout（可选，有默认值）：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：含 Django ORM 数据库查询，注意查询性能与空结果处理；读写缓存，注意缓存键口径与失效策略。
    """
    #: 定义变量「key」，保存对应数据
    key = f'article_detail_{pk}'
    #: 返回结果并结束当前函数
    return cache.get_or_set(key, lambda: Article.objects.filter(
        #: 定义变量「pk」，保存对应数据
        pk=pk, status=Article.Status.PUBLISHED)
        #: ORM 预加载关联，减少 N+1 查询提升性能
        .select_related('author', 'category').first(), timeout)

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
    #: 条件判断：条件成立时执行该分支
    if request.method != 'POST':
        #: 返回结果并结束当前函数
        return JsonResponse({'detail': '请用 POST 请求点赞喵~'}, status=405)
    # 只能对已发布文章点赞
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    article = get_object_or_404(Article, pk=pk, status=Article.Status.PUBLISHED)
    # 从 session 取已点赞列表（首次访问时为空列表）
    #: 定义变量「liked_ids」，保存对应数据
    liked_ids = request.session.get('liked_article_ids', [])
    #: 条件判断：条件成立时执行该分支
    if pk in liked_ids:
        # 已赞过 → 取消赞（toggle 语义）
        #: 调用「liked_ids.remove」执行相应逻辑
        liked_ids.remove(pk)
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        Article.objects.filter(pk=pk).update(likes=F('likes') - 1)
        # 防止减成负数
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        Article.objects.filter(pk=pk, likes__lt=0).update(likes=0)
        #: 定义变量「liked」，保存对应数据
        liked = False
        # 取消赞时清理对应 LIKE 通知（避免作者收到已取消的赞通知）
        #: 尝试执行可能出错的代码
        try:
            #: 读取本次请求的 user 数据
            liker = request.user if request.user.is_authenticated else None
            #: 条件判断：条件成立时执行该分支
            if liker and liker.pk != article.author_id:
                #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
                Notification.objects.filter(
                    #: 定义变量「user」，保存对应数据
                    user=article.author, type=Notification.Type.LIKE,
                    #: 删除对象，注意级联与权限
                    title__startswith=f'{liker} 赞了你的文章').delete()
        #: 捕获并处理异常，避免程序中断
        except Exception:
            #: 占位语句：此处暂不需要实现
            pass
    #: 以上条件均不成立时的兜底分支
    else:
        # F() 表达式在数据库层原子自增点赞数，避免并发覆盖
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        Article.objects.filter(pk=pk).update(likes=F('likes') + 1)
        #: 调用「liked_ids.append」执行相应逻辑
        liked_ids.append(pk)
        #: 定义变量「liked」，保存对应数据
        liked = True
    #: 操作「request」的属性或方法
    request.session['liked_article_ids'] = liked_ids
    #: 定义实例/类属性「request.session.modified」，保存对应数据
    request.session.modified = True   # 显式标记 session 已修改，确保落库
    #: 调用「article.refresh_from_db」执行相应逻辑
    article.refresh_from_db(fields=['likes'])
    # 点赞/取消都是写路径：失效文章片段缓存，聚合数字即时一致
    #: 尝试执行可能出错的代码
    try:
        #: 从模块「..utils.cache_keys」导入所需对象
        from ..utils.cache_keys import invalidate_article
        #: 调用「invalidate_article」执行相应逻辑
        invalidate_article(pk)
    #: 捕获并处理异常，避免程序中断
    except Exception:
        #: 占位语句：此处暂不需要实现
        pass
    #: 条件判断：条件成立时执行该分支
    if liked:
        # 第5轮 F8: 文章被赞时通知作者（避免自己赞自己）
        #: 尝试执行可能出错的代码
        try:
            #: 读取本次请求的 user 数据
            liker = request.user if request.user.is_authenticated else None
            #: 条件判断：条件成立时执行该分支
            if liker and liker.pk != article.author_id:
                #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
                Notification.objects.get_or_create(
                    #: 定义变量「user」，保存对应数据
                    user=article.author, type=Notification.Type.LIKE,
                    #: 定义变量「title」，保存对应数据
                    title=f'{liker} 赞了你的文章《{article.title[:30]}》',
                    #: 定义变量「defaults」，保存对应数据
                    defaults={'related_url': article.get_absolute_url()})
            #: 从模块「.users」导入所需对象
            from .users import check_and_award_badges
            # 作者获赞后检查徽章
            #: 调用「check_and_award_badges」执行相应逻辑
            check_and_award_badges(article.author)
        #: 捕获并处理异常，避免程序中断
        except Exception:
            #: 占位语句：此处暂不需要实现
            pass
    #: 返回结果并结束当前函数
    return JsonResponse({'likes': article.likes, 'liked': liked})

#: 装饰器：为下一个定义附加「login_required」行为（权限、缓存、注册信号等）
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
    #: 条件判断：条件成立时执行该分支
    if request.method != 'POST':
        #: 返回结果并结束当前函数
        return JsonResponse({'detail': '请用 POST 请求收藏喵~'}, status=405)
    # 只能对已发布文章收藏
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    article = get_object_or_404(Article, pk=pk, status=Article.Status.PUBLISHED)
    # 查询当前用户是否已收藏
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    fav = Favorite.objects.filter(user=request.user, article=article).first()
    #: 条件判断：条件成立时执行该分支
    if fav:
        # 已收藏 → 取消收藏（删除记录）
        #: 删除对象，注意级联与权限
        fav.delete()
        #: 定义变量「favorited」，保存对应数据
        favorited = False
    #: 以上条件均不成立时的兜底分支
    else:
        # 未收藏 → 创建收藏记录（unique_together 保证不重复）
        # 第5轮 C10: 可选指定收藏夹 folder_id
        #: 定义变量「folder」，保存对应数据
        folder = None
        #: 读取本次请求的 POST 数据
        folder_id = (request.POST.get('folder_id') or request.GET.get('folder_id') or '').strip()
        #: 条件判断：条件成立时执行该分支
        if folder_id.isdigit():
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            folder = FavoriteFolder.objects.filter(pk=int(folder_id), user=request.user).first()
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        Favorite.objects.get_or_create(user=request.user, article=article, defaults={'folder': folder})
        #: 定义变量「favorited」，保存对应数据
        favorited = True
    # 统计该文章当前被收藏的总人数
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    count = Favorite.objects.filter(article=article).count()
    #: 返回结果并结束当前函数
    return JsonResponse({'favorited': favorited, 'count': count})

#: 装饰器：为下一个定义附加「login_required」行为（权限、缓存、注册信号等）
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
    #: 条件判断：条件成立时执行该分支
    if request.method != 'POST':
        #: 返回结果并结束当前函数
        return JsonResponse({'detail': '请用 POST 提交评分喵~'}, status=405)
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    article = get_object_or_404(Article, pk=pk, status=Article.Status.PUBLISHED)
    # 解析并校验分数（1~5）
    #: 尝试执行可能出错的代码
    try:
        #: 读取本次请求的 POST 数据
        score = int(request.POST.get('score', 0))
    #: 捕获并处理异常，避免程序中断
    except (TypeError, ValueError):
        #: 定义变量「score」，保存对应数据
        score = 0
    # 迭代#215: 评分范围验证（1-5）
    #: 条件判断：条件成立时执行该分支
    if score not in dict(Rating.Score.choices):
        #: 返回结果并结束当前函数
        return JsonResponse({'success': False, 'error': msg('interact.rating_required')}, status=400)
    # unique_together 保证每用户每文章一条；存在则更新分数
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    rating, _ = Rating.objects.update_or_create(
        #: 读取本次请求的 user 数据
        user=request.user, article=article,
        #: 定义变量「defaults」，保存对应数据
        defaults={'score': score})
    # 重算冗余字段：平均分（保留一位小数）+ 评分人数
    #: 使用聚合函数做统计查询
    agg = article.ratings.aggregate(avg=Avg('score'), cnt=Count('id'))
    #: 定义实例/类属性「article.rating_avg」，保存对应数据
    article.rating_avg = round(agg['avg'] or 0, 1)
    #: 定义实例/类属性「article.rating_count」，保存对应数据
    article.rating_count = agg['cnt'] or 0
    #: 调用「article.save」执行相应逻辑
    article.save(update_fields=['rating_avg', 'rating_count'])
    #: 返回结果并结束当前函数
    return JsonResponse({
        #: 配置项「success」：字典/模型的该键设置为对应值
        'success': True,
        #: 配置项「avg」：字典/模型的该键设置为对应值
        'avg': article.rating_avg,
        #: 配置项「count」：字典/模型的该键设置为对应值
        'count': article.rating_count,
        #: 配置项「my」：字典/模型的该键设置为对应值
        'my': rating.score,
        # 第4轮 C8: 兼容跨 Agent 接口命名，同时返回语义化字段
        #: 配置项「rating_avg」：字典/模型的该键设置为对应值
        'rating_avg': article.rating_avg,
        #: 配置项「rating_count」：字典/模型的该键设置为对应值
        'rating_count': article.rating_count,
        #: 配置项「my_rating」：字典/模型的该键设置为对应值
        'my_rating': rating.score,
    #: 该行执行对应逻辑（结合上下文理解）
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
    #: 条件判断：条件成立时执行该分支
    if request.method != 'POST':
        #: 返回结果并结束当前函数
        return JsonResponse({'detail': '请用 POST 请求分享喵~'}, status=405)
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    article = get_object_or_404(Article, pk=pk, status=Article.Status.PUBLISHED)
    # F() 表达式在数据库层原子自增，避免并发读-改-写丢失计数
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    Article.objects.filter(pk=pk).update(share_count=F('share_count') + 1)
    #: 调用「article.refresh_from_db」执行相应逻辑
    article.refresh_from_db(fields=['share_count'])
    #: 返回结果并结束当前函数
    return JsonResponse({'share_count': article.share_count})

#: 定义变量「SHORT_LINK_CODE_LEN」，保存对应数据
SHORT_LINK_CODE_LEN = 6             # 短链接码长度

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
    #: 条件判断：条件成立时执行该分支
    if request.method != 'POST':
        #: 返回结果并结束当前函数
        return JsonResponse({'detail': '请用 POST 请求踩喵~'}, status=405)
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    article = get_object_or_404(Article, pk=pk, status=Article.Status.PUBLISHED)
    #: 定义变量「disliked_ids」，保存对应数据
    disliked_ids = request.session.get('disliked_article_ids', [])
    #: 条件判断：条件成立时执行该分支
    if pk in disliked_ids:
        # 已踩 → 取消
        #: 调用「disliked_ids.remove」执行相应逻辑
        disliked_ids.remove(pk)
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        Article.objects.filter(pk=pk).update(
            #: 使用 Q/F 表达式构造复杂查询或引用字段值
            dislike_count=F('dislike_count') - 1)
        # 防止减成负数
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        Article.objects.filter(pk=pk, dislike_count__lt=0).update(dislike_count=0)
        #: 定义变量「disliked」，保存对应数据
        disliked = False
    #: 以上条件均不成立时的兜底分支
    else:
        #: 调用「disliked_ids.append」执行相应逻辑
        disliked_ids.append(pk)
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        Article.objects.filter(pk=pk).update(dislike_count=F('dislike_count') + 1)
        #: 定义变量「disliked」，保存对应数据
        disliked = True
    #: 操作「request」的属性或方法
    request.session['disliked_article_ids'] = disliked_ids
    #: 定义实例/类属性「request.session.modified」，保存对应数据
    request.session.modified = True
    #: 调用「article.refresh_from_db」执行相应逻辑
    article.refresh_from_db(fields=['dislike_count'])
    # 踩/取消都是写路径：失效文章片段缓存，聚合数字即时一致（D2修复）
    #: 尝试执行可能出错的代码
    try:
        #: 从模块「..utils.cache_keys」导入所需对象
        from ..utils.cache_keys import invalidate_article
        #: 调用「invalidate_article」执行相应逻辑
        invalidate_article(pk)
    #: 捕获并处理异常，避免程序中断
    except Exception:
        #: 占位语句：此处暂不需要实现
        pass
    #: 返回结果并结束当前函数
    return JsonResponse({'dislike_count': article.dislike_count, 'disliked': disliked})

# ----------------------------- 7. 文章导出（G3/G4） -----------------------------
def api_article_export_md(request: HttpRequest, pk: int) -> HttpResponse:
    """Markdown 导出：GET /api/article/<pk>/export/md/。

    用 html2text 把文章 HTML 正文转 Markdown，作为附件下载。
    """
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    article = get_object_or_404(Article, pk=pk, status=Article.Status.PUBLISHED)
    #: 尝试执行可能出错的代码
    try:
        #: 导入模块「html2text」，供本文件后续使用
        import html2text
        #: 定义变量「h」，保存对应数据
        h = html2text.HTML2Text()
        #: 定义实例/类属性「h.ignore_images」，保存对应数据
        h.ignore_images = False
        #: 定义实例/类属性「h.body_width」，保存对应数据
        h.body_width = 0
        #: 定义变量「body_md」，保存对应数据
        body_md = h.handle(article.content or '')
    #: 捕获并处理异常，避免程序中断
    except ImportError:
        #: 定义变量「body_md」，保存对应数据
        body_md = article.plain_text
    #: 定义变量「md」，保存对应数据
    md = f'# {article.title}\n\n> 作者：{article.author}\n\n{body_md}\n'
    #: 构造 HTTP 响应返回给客户端
    resp = HttpResponse(md, content_type='text/markdown; charset=utf-8')
    #: 定义变量「safe_title」，保存对应数据
    safe_title = re.sub(r'[^\w\u4e00-\u9fff-]+', '_', article.title)[:60]
    #: 该行执行对应逻辑（结合上下文理解）
    resp['Content-Disposition'] = f'attachment; filename="{safe_title}.md"'
    #: 返回结果并结束当前函数
    return resp

def api_article_export_pdf(request: HttpRequest, pk: int) -> HttpResponse:
    """PDF 导出：GET /api/article/<pk>/export/pdf/。

    用 xhtml2pdf 渲染极简 HTML 为 PDF；依赖缺失或渲染失败时返回 501，
    由前端降级为 jsPDF 方案。
    """
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    article = get_object_or_404(Article, pk=pk, status=Article.Status.PUBLISHED)
    #: 尝试执行可能出错的代码
    try:
        #: 从模块「xhtml2pdf」导入所需对象
        from xhtml2pdf import pisa
    #: 捕获并处理异常，避免程序中断
    except ImportError:
        #: 返回结果并结束当前函数
        return JsonResponse({'detail': 'PDF 导出组件未安装，请使用前端导出方案'}, status=501)
    #: 定义变量「html」，保存对应数据（集合/元组）
    html = (
        #: 该行执行对应逻辑（结合上下文理解）
        f'<html><head><meta charset="utf-8"/></head><body>'
        #: 该行执行对应逻辑（结合上下文理解）
        f'<h1>{article.title}</h1>'
        #: 该行执行对应逻辑（结合上下文理解）
        f'<p>作者：{article.author}</p>'
        #: 该行执行对应逻辑（结合上下文理解）
        f'{article.content}'
        #: 该行执行对应逻辑（结合上下文理解）
        f'</body></html>'
    #: 该行执行对应逻辑（结合上下文理解）
    )
    #: 定义变量「out」，保存对应数据
    out = BytesIO()
    #: 尝试执行可能出错的代码
    try:
        #: 调用「pisa.CreatePDF」执行相应逻辑
        pisa.CreatePDF(html.encode('utf-8'), dest=out, encoding='utf-8')
    #: 捕获并处理异常，避免程序中断
    except Exception as exc:  # noqa: BLE001
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.error('PDF 导出失败: %s', exc)
        #: 返回结果并结束当前函数
        return JsonResponse({'detail': 'PDF 生成失败'}, status=500)
    #: 调用「out.seek」执行相应逻辑
    out.seek(0)
    #: 构造 HTTP 响应返回给客户端
    resp = HttpResponse(out.getvalue(), content_type='application/pdf')
    #: 定义变量「safe_title」，保存对应数据
    safe_title = re.sub(r'[^\w\u4e00-\u9fff-]+', '_', article.title)[:60]
    #: 该行执行对应逻辑（结合上下文理解）
    resp['Content-Disposition'] = f'attachment; filename="{safe_title}.pdf"'
    #: 返回结果并结束当前函数
    return resp

# ----------------------------- 8. 二维码 / 短链接（G6/G7） -----------------------------
def api_article_qrcode(request: HttpRequest, pk: int) -> HttpResponse:
    """文章二维码：GET /api/article/<pk>/qrcode/，返回 PNG。"""
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    article = get_object_or_404(Article, pk=pk, status=Article.Status.PUBLISHED)
    #: 尝试执行可能出错的代码
    try:
        #: 导入模块「qrcode」，供本文件后续使用
        import qrcode
    #: 捕获并处理异常，避免程序中断
    except ImportError:
        #: 返回结果并结束当前函数
        return JsonResponse({'detail': '二维码组件未安装'}, status=501)
    #: 定义变量「url」，保存对应数据
    url = request.build_absolute_uri(article.get_absolute_url())
    #: 定义变量「img」，保存对应数据
    img = qrcode.make(url)
    #: 定义变量「buf」，保存对应数据
    buf = BytesIO()
    #: 调用「img.save」执行相应逻辑
    img.save(buf, format='PNG')
    #: 调用「buf.seek」执行相应逻辑
    buf.seek(0)
    #: 返回结果并结束当前函数
    return HttpResponse(buf.getvalue(), content_type='image/png')

def api_short_link(request: HttpRequest) -> JsonResponse:
    """短链接生成：POST /api/short_link/，body {original_url}。"""
    #: 条件判断：条件成立时执行该分支
    if request.method != 'POST':
        #: 返回结果并结束当前函数
        return JsonResponse({'detail': '请用 POST 请求喵~'}, status=405)
    #: 尝试执行可能出错的代码
    try:
        #: 读取本次请求的 body 数据
        body = json.loads(request.body.decode('utf-8') or '{}')
    #: 捕获并处理异常，避免程序中断
    except (ValueError, UnicodeDecodeError):
        #: 读取本次请求的 POST 数据
        body = request.POST
    #: 定义变量「original_url」，保存对应数据
    original_url = str(body.get('original_url', '')).strip()
    #: 条件判断：条件成立时执行该分支
    if not original_url or not re.match(r'^https?://', original_url):
        #: 返回结果并结束当前函数
        return _bad_request('original_url 必须是 http/https 开头的合法 URL')
    # 6 位随机短码，冲突则重试
    #: 导入模块「secrets」，供本文件后续使用
    import secrets, string
    #: 定义变量「alphabet」，保存对应数据
    alphabet = string.ascii_letters + string.digits
    #: 定义变量「code」，保存对应数据
    code = ''
    #: 循环遍历，逐个处理元素
    for _ in range(10):
        #: 定义变量「code」，保存对应数据
        code = ''.join(secrets.choice(alphabet) for _ in range(SHORT_LINK_CODE_LEN))
        #: 条件判断：条件成立时执行该分支
        if not ShortLink.objects.filter(code=code).exists():
            #: 跳出当前循环
            break
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    ShortLink.objects.create(code=code, original_url=original_url)
    #: 定义变量「short_url」，保存对应数据
    short_url = request.build_absolute_uri(f'/s/{code}/')
    #: 返回结果并结束当前函数
    return _json_ok({'short_url': short_url, 'code': code})

def short_link_redirect(request: HttpRequest, code: str) -> HttpResponseRedirect:
    """短链接跳转：/s/<code>/，302 跳转并 clicks+1。"""
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    link = get_object_or_404(ShortLink, code=code)
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    ShortLink.objects.filter(pk=link.pk).update(clicks=F('clicks') + 1)
    #: 返回结果并结束当前函数
    return HttpResponseRedirect(link.original_url)

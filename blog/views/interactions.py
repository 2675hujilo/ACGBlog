# -*- coding: utf-8 -*-

"""互动域：点赞、收藏、评分、分享、热门文章、导出与短链接。"""

import json
import logging
import os
import re
import uuid
from io import BytesIO
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from ..utils.cache_keys import (
    DETAIL_TTL, MISSING_TTL, cache_get, cache_get_or_set,
    cache_set, detail_keys, invalidate_article,
)
from django.db.models import Avg, Count, F, Min, Q, Sum
from django.http import (
    FileResponse, Http404, HttpRequest, HttpResponse,
    HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound,
    HttpResponseNotModified, HttpResponsePermanentRedirect,
    HttpResponseRedirect, JsonResponse, StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from ..models import (
    AccessLog, Article, Badge, Category, Comment, CommentReport,
    EditLog, Favorite, FavoriteFolder, ModerationLog, Notification,
    PromotionRequest, ModerationSettings, Rating, Series, ShortLink,
    SiteNotice, Tag, User, UserBadge,
)
from ..services.site_messages import msg

from .common import HOT_ARTICLES_KEY, _bad_request, _json_ok, logger

from .users import check_and_award_badges


logger = logging.getLogger('blog.views')

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

def _article_detail_cached(pk, timeout=120):
    # 第2轮迭代#68: 文章详情缓存——仅缓存公开已发布文章的轻量字段
    key = f'article_detail_{pk}'
    return cache.get_or_set(key, lambda: Article.objects.filter(
        pk=pk, status=Article.Status.PUBLISHED)
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
        from ..utils.cache_keys import invalidate_article
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
            from .users import check_and_award_badges
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
        return JsonResponse({'success': False, 'error': msg('interact.rating_required')}, status=400)
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
        from ..utils.cache_keys import invalidate_article
        invalidate_article(pk)
    except Exception:
        pass
    return JsonResponse({'dislike_count': article.dislike_count, 'disliked': disliked})

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

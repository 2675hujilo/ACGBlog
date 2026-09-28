# -*- coding: utf-8 -*-

"""评论域：多级评论树、发表、点赞、图片上传、举报与撤回。"""

import json
import logging
import os
import re
import uuid
from datetime import datetime, timedelta
from django.conf import settings
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
from django.utils import timezone
from PIL import Image
from ..models import (
    AccessLog, Article, Badge, Category, Comment, CommentReport,
    EditLog, Favorite, FavoriteFolder, ModerationLog, Notification,
    PromotionRequest, ModerationSettings, Rating, Series, ShortLink,
    SiteNotice, Tag, User, UserBadge,
)
from ..services.site_messages import msg

from .common import _bad_request, _forbidden, _json_ok, logger, sanitize_comment


logger = logging.getLogger('blog.views')

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
        return JsonResponse({'success': False, 'error': msg('comment.post_failed')}, status=405)
    # 只能对已发布文章评论（草稿不可见，自然也不开放评论）
    article = get_object_or_404(Article, pk=article_pk, status=Article.Status.PUBLISHED)
    content = (request.POST.get('content') or '').strip()
    # 空内容校验
    if not content:
        return JsonResponse({'success': False, 'error': msg('comment.empty_content')}, status=400)
    # 长度硬截断到 10000 字符，防止超长内容撑库 / 拖慢渲染
    content = content[:10000]
    # bleach 净化：只保留 strong/em/a/code 少量行内标签
    content = sanitize_comment(content)
    # 净化后若纯文本为空（用户只发了被剥离的标签），同样视为空评论
    plain = re.sub(r'<[^>]+>', '', content).strip()
    if not plain:
        return JsonResponse({'success': False, 'error': msg('comment.empty_content')}, status=400)
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
    from ..tasks import send_comment_notification
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

# ---- 常量 ----
COMMENT_IMAGE_MAX_BYTES = 2 * 1024 * 1024  # 评论图片上限 2MB

COMMENT_IMAGE_ALLOWED_FORMATS = ('JPEG', 'PNG', 'GIF', 'WEBP')  # PIL 允许的真实格式

COMMENT_WITHDRAW_MINUTES = 5  # 评论撤回时限（分钟）

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

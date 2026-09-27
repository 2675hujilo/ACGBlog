# -*- coding: utf-8 -*-

"""内容审核：审核队列、审批、回收站与置顶/精华/热门推广。"""

import json
import logging
import os
import re
import uuid
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from ..cache_keys import (
    DETAIL_TTL, MISSING_TTL, cache_get, cache_get_or_set,
    cache_set, detail_keys, invalidate_article,
)
from django.core.paginator import Paginator
from django.db.models import Avg, Count, F, Min, Q, Sum
from django.http import (
    FileResponse, Http404, HttpRequest, HttpResponse,
    HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound,
    HttpResponseNotModified, HttpResponsePermanentRedirect,
    HttpResponseRedirect, JsonResponse, StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from rest_framework.decorators import action
from ..models import (
    AccessLog, Article, Badge, Category, Comment, CommentReport,
    EditLog, Favorite, FavoriteFolder, ModerationLog, Notification,
    PromotionRequest, ModerationSettings, Rating, Series, ShortLink,
    SiteNotice, Tag, User, UserBadge,
)
from ..site_messages import msg

from .common import SIDEBAR_CACHE_KEY, logger


logger = logging.getLogger('blog.views')

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
            messages.success(req, msg('article.approved', article.title))
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
            messages.warning(req, msg('article.rejected', article.title))
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
            messages.success(req, msg('comment.report_dismissed'))
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
            messages.warning(req, msg('comment.hidden_backup', 
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
    messages.success(request, msg('article.restored', article.title))
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
    messages.warning(request, msg('article.hard_deleted', title))
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
    messages.success(request, msg('comment.restored', pk))
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
    messages.warning(request, msg('comment.hard_deleted', pk))
    return redirect('/console/moderation/?tab=trash')

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
        return JsonResponse({'code': 403, 'msg': msg('auth.login_required')}, status=403)
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': msg('err.method_not_allowed')}, status=405)
    article = get_object_or_404(Article, pk=pk, is_deleted=False)
    if request.user != article.author and not request.user.is_staff:
        return JsonResponse({'code': 403, 'msg': msg('promo.only_own')}, status=403)
    kind = request.POST.get('kind', '')
    if kind not in PromotionRequest.Kind.values:
        return JsonResponse({'code': 400, 'msg': msg('promo.bad_kind')}, status=400)
    # Bug8：已经生效的推广不再受理申请（按钮侧也已禁用，这里做服务端兜底）
    field = _PROMO_FIELD[kind][0]
    label = _PROMO_LABEL[kind]
    if getattr(article, field):
        return JsonResponse(
            {'code': 409, 'msg': msg('promo.already_applied', label),
             'data': {'already_applied': True, 'kind': kind}},
            status=409)
    reason = (request.POST.get('reason') or '').strip()[:500]
    if not reason:
        return JsonResponse({'code': 400, 'msg': msg('promo.reason_required')}, status=400)
    # 已有同类型待审核申请，不允许重复提交
    if PromotionRequest.objects.filter(
            article=article, kind=kind,
            status=PromotionRequest.Status.PENDING).exists():
        return JsonResponse({'code': 409, 'msg': msg('promo.duplicate')}, status=409)
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
        return JsonResponse({'code': 403, 'msg': msg('err.admin_only')}, status=403)
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': msg('err.method_not_allowed')}, status=405)
    article = get_object_or_404(Article, pk=pk, is_deleted=False)
    action = request.POST.get('action', '')
    # action → (申请类型, 目标布尔值)
    mapping = {
        'pin': (PromotionRequest.Kind.PIN, True), 'unpin': (PromotionRequest.Kind.PIN, False),
        'feature': (PromotionRequest.Kind.FEATURE, True), 'unfeature': (PromotionRequest.Kind.FEATURE, False),
        'hot': (PromotionRequest.Kind.HOT, True), 'unhot': (PromotionRequest.Kind.HOT, False),
    }
    if action not in mapping:
        return JsonResponse({'code': 400, 'msg': msg('err.bad_request')}, status=400)
    kind, target = mapping[action]
    field, act_on, act_off = _PROMO_FIELD[kind]
    # 置顶上限校验（仅在「设置置顶」且当前未置顶时）
    if kind == PromotionRequest.Kind.PIN and target:
        max_pinned = ModerationSettings.load().max_pinned
        if not article.is_pinned and Article.objects.filter(
                is_pinned=True, is_deleted=False).count() >= max_pinned:
            return JsonResponse({'code': 409, 'msg': msg('promo.limit_reached', max_pinned)}, status=409)
    setattr(article, field, target)
    article.save(update_fields=[field, 'updated_at'])
    ModerationLog.objects.create(
        moderator=request.user, moderator_name=str(request.user),
        action=act_on if target else act_off, target_type='article',
        article=article, target_title=article.title)
    labels = _PROMO_LABEL
    return JsonResponse({'code': 0,
                         'msg': msg('promo.toggle_ok', '设置' if target else '取消', labels[kind]),
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
        messages.warning(request, msg('moderation.already_handled'))
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
            messages.success(request, msg('promo.approved_ok', label))
        else:
            messages.warning(request, msg('promo.approved_not_applied', label, exec_note))
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
        messages.warning(request, msg('promo.rejected', label))
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
    messages.success(request, msg('moderation.settings_saved'))
    return redirect('/console/moderation/?tab=promotions')

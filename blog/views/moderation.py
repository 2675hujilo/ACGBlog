# -*- coding: utf-8 -*-

"""内容审核：审核队列、审批、回收站与置顶/精华/热门推广。"""

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
#: 从模块「django.conf」导入所需对象
from django.conf import settings
#: 从模块「django.contrib」导入所需对象
from django.contrib import messages
#: 从模块「django.contrib.admin.views.decorators」导入所需对象
from blog.utils.decorators import staff_required_moe
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
#: 从模块「django.core.paginator」导入所需对象
from django.core.paginator import Paginator
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
#: 从模块「rest_framework.decorators」导入所需对象
from rest_framework.decorators import action
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
from .common import SIDEBAR_CACHE_KEY, logger


#: 定义变量「logger」，保存对应数据
logger = logging.getLogger('blog.views')

# ============================ Round6（bug16）：内容审核（待审文章 / 举报审批） ============================
def _moderation_backup(kind, payload):
    """把待删除/驳回内容快照写入项目内备份目录，返回备份文件路径。

    统一存放于 ``docs/moderation_backup/``，文件名带时间戳、类型与主键，
    UTF-8 JSON，便于误删后人工恢复；目录不存在时自动创建。
    """
    #: 定义变量「backup_dir」，保存对应数据
    backup_dir = os.path.join(settings.BASE_DIR, 'docs', 'moderation_backup')
    #: 调用「os.makedirs」执行相应逻辑
    os.makedirs(backup_dir, exist_ok=True)
    #: 获取当前时间（时区感知），统一时间口径
    stamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    #: 定义变量「ident」，保存对应数据
    ident = payload.get('id', 'x')
    #: 定义变量「path」，保存对应数据
    path = os.path.join(backup_dir, '%s_%s_%s.json' % (stamp, kind, ident))
    #: 上下文管理：进入时获取资源、退出时自动释放
    with open(path, 'w', encoding='utf-8') as f:
        #: 调用「json.dump」执行相应逻辑
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    #: 返回结果并结束当前函数
    return path

def _article_snapshot(article):
    """导出文章完整字段（含正文/标签/分类），供驳回删除前备份。"""
    #: 返回结果并结束当前函数
    return {
        #: 配置项「id」：字典/模型的该键设置为对应值
        'id': article.id,
        #: 配置项「title」：字典/模型的该键设置为对应值
        'title': article.title,
        #: 配置项「author」：字典/模型的该键设置为对应值
        'author': getattr(article.author, 'username', None),
        #: 配置项「status」：字典/模型的该键设置为对应值
        'status': article.status,
        #: 配置项「kind」：字典/模型的该键设置为对应值
        'kind': getattr(article, 'kind', ''),
        #: 配置项「category」：字典/模型的该键设置为对应值
        'category': getattr(article.category, 'name', None),
        #: 配置项「tags」：字典/模型的该键设置为对应值
        'tags': list(article.tags.values_list('name', flat=True)),
        #: 配置项「excerpt」：字典/模型的该键设置为对应值
        'excerpt': getattr(article, 'excerpt', ''),
        #: 配置项「content」：字典/模型的该键设置为对应值
        'content': article.content,
        #: 配置项「views」：字典/模型的该键设置为对应值
        'views': article.views,
        #: 配置项「created_at」：字典/模型的该键设置为对应值
        'created_at': article.created_at,
        #: 配置项「updated_at」：字典/模型的该键设置为对应值
        'updated_at': article.updated_at,
        #: 获取当前时间（时区感知），统一时间口径
        'backed_up_at': timezone.now(),
    #: 该行执行对应逻辑（结合上下文理解）
    }

def _comment_snapshot(comment):
    """导出评论及其全部举报，供删除违规评论前备份。"""
    #: 返回结果并结束当前函数
    return {
        #: 配置项「id」：字典/模型的该键设置为对应值
        'id': comment.id,
        #: 配置项「article_id」：字典/模型的该键设置为对应值
        'article_id': comment.article_id,
        #: 配置项「article_title」：字典/模型的该键设置为对应值
        'article_title': getattr(comment.article, 'title', ''),
        #: 配置项「user」：字典/模型的该键设置为对应值
        'user': getattr(comment.user, 'username', None),
        #: 配置项「content」：字典/模型的该键设置为对应值
        'content': comment.content,
        #: 配置项「is_approved」：字典/模型的该键设置为对应值
        'is_approved': comment.is_approved,
        #: 配置项「created_at」：字典/模型的该键设置为对应值
        'created_at': comment.created_at,
        #: 配置项「reports」：字典/模型的该键设置为对应值
        'reports': [
            #: 该行执行对应逻辑（结合上下文理解）
            {'id': r.id, 'reporter': getattr(r.reporter, 'username', None),
             #: 配置项「reason」：字典/模型的该键设置为对应值
             'reason': r.reason, 'created_at': r.created_at}
            #: 循环遍历，逐个处理元素
            for r in comment.reports.all()
        #: 该行执行对应逻辑（结合上下文理解）
        ],
        #: 获取当前时间（时区感知），统一时间口径
        'backed_up_at': timezone.now(),
    #: 该行执行对应逻辑（结合上下文理解）
    }

def moderation_queue(request: HttpRequest) -> HttpResponse:
    """内容审核页（bug8）：待审文章 / 待处理举报 / 审核历史 / 回收站四个标签页，仅 staff。

    - articles：status=PENDING 的文章，支持按分类 / 标签 / 提交时间排序与分页；
    - reports：全部 CommentReport（无状态字段），分页；
    - history：ModerationLog 审核操作时间线，分页，可按动作筛选；
    - trash：is_deleted=True 的文章 / 评论（回收站），可恢复或彻底删除。
    """
    #: 从模块「django.contrib.admin.views.decorators」导入所需对象
    from blog.utils.decorators import staff_required_moe

    #: 装饰器：为下一个定义附加「staff_member_required」行为（权限、缓存、注册信号等）
    @staff_required_moe
    def _inner(req):
        """
        功能：处理「inner」相关逻辑。

        参数：
          - req：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：装饰器 staff_member_required 决定其附加行为（权限/缓存/属性/信号等）；含 Django ORM 数据库查询，注意查询性能与空结果处理。
        """
        #: 定义变量「tab」，保存对应数据
        tab = req.GET.get('tab', 'articles')
        #: 条件判断：条件成立时执行该分支
        if tab not in ('articles', 'reports', 'promotions', 'history', 'trash'):
            #: 定义变量「tab」，保存对应数据
            tab = 'articles'

        # ---- 待审文章：排序（分类 / 标签 / 时间）+ 升降序 + 分页 ----
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        pending_qs = (Article.objects.filter(status=Article.Status.PENDING, is_deleted=False)
                      #: ORM 预加载关联，减少 N+1 查询提升性能
                      .select_related('author', 'category')
                      #: ORM 预加载关联，减少 N+1 查询提升性能
                      .prefetch_related('tags'))
        #: 定义变量「sort」，保存对应数据
        sort = req.GET.get('sort', 'date')
        #: 条件判断：条件成立时执行该分支
        if sort not in ('date', 'category', 'tag'):
            #: 定义变量「sort」，保存对应数据
            sort = 'date'
        # 升降序（参考标签页排序）：默认升序，order=desc 时各字段整体反向
        #: 定义变量「order」，保存对应数据
        order = req.GET.get('order', 'asc')
        #: 条件判断：条件成立时执行该分支
        if order not in ('asc', 'desc'):
            #: 定义变量「order」，保存对应数据
            order = 'asc'
        #: 定义变量「prefix」，保存对应数据
        prefix = '-' if order == 'desc' else ''
        #: 定义变量「secondary」，保存对应数据
        secondary = '-id' if order == 'desc' else 'id'  # 同值时用 id 保证排序稳定
        #: 条件判断：条件成立时执行该分支
        if sort == 'category':
            #: 对查询结果按字段排序
            pending_qs = pending_qs.order_by(prefix + 'category__name', secondary)
        #: 否则若该条件成立则进入此分支
        elif sort == 'tag':
            # 多对多 tags 直接 order_by 会让多标签文章产生重复行（distinct 也会因排序键不同而失效）；
            # 用 Min 子查询给每篇文章注解一个代表标签（字典序首个），聚合 GROUP BY 折叠为每篇一行。
            #: 定义变量「pending_qs」，保存对应数据（集合/元组）
            pending_qs = (pending_qs.filter(tags__isnull=False)
                          #: 使用聚合函数做统计查询
                          .annotate(_sort_tag=Min('tags__name'))
                          #: 对查询结果按字段排序
                          .order_by(prefix + '_sort_tag', secondary))
        #: 以上条件均不成立时的兜底分支
        else:
            #: 对查询结果按字段排序
            pending_qs = pending_qs.order_by(prefix + 'created_at', secondary)
        #: 定义变量「pending_page」，保存对应数据
        pending_page = Paginator(pending_qs, 10).get_page(req.GET.get('page'))

        # ---- 待处理举报：分页 ----
        #: ORM 预加载关联，减少 N+1 查询提升性能
        reports_qs = (CommentReport.objects.select_related('comment', 'reporter')
                      #: 对查询结果按字段排序
                      .order_by('created_at', 'id'))
        #: 定义变量「reports_page」，保存对应数据
        reports_page = Paginator(reports_qs, 10).get_page(req.GET.get('rpage'))

        # ---- Bug1：推广申请（置顶/精华/热门）待审核列表 ----
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        promo_qs = (PromotionRequest.objects.filter(status=PromotionRequest.Status.PENDING)
                    #: ORM 预加载关联，减少 N+1 查询提升性能
                    .select_related('article', 'applicant')
                    #: 对查询结果按字段排序
                    .order_by('created_at', 'id'))
        #: 定义变量「promo_page」，保存对应数据
        promo_page = Paginator(promo_qs, 10).get_page(req.GET.get('ppage'))

        # ---- Bug8：已处理推广申请（含系统执行状态），默认折叠展示最近 10 条 ----
        #: 定义变量「promo_done_page」，保存对应数据
        promo_done_page = Paginator(
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            PromotionRequest.objects.exclude(status=PromotionRequest.Status.PENDING)
            #: ORM 预加载关联，减少 N+1 查询提升性能
            .select_related('article', 'applicant', 'handled_by')
            #: 对查询结果按字段排序
            .order_by('-handled_at', '-id'), 10).get_page(req.GET.get('pdpage'))
        # 系统执行状态汇总：供审核页顶部「系统执行状态」总览条展示
        #: 定义变量「exec_stats」，保存对应数据
        exec_stats = {
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'success': PromotionRequest.objects.filter(
                #: 定义变量「execution_status」，保存对应数据
                execution_status=PromotionRequest.Execution.SUCCESS).count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'skipped': PromotionRequest.objects.filter(
                #: 定义变量「execution_status」，保存对应数据
                execution_status=PromotionRequest.Execution.SKIPPED).count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'failed': PromotionRequest.objects.filter(
                #: 定义变量「execution_status」，保存对应数据
                execution_status=PromotionRequest.Execution.FAILED).count(),
        #: 该行执行对应逻辑（结合上下文理解）
        }

        # ---- 审核历史：可按动作筛选 + 分页 ----
        #: ORM 预加载关联，减少 N+1 查询提升性能
        history_qs = (ModerationLog.objects.select_related('moderator')
                      #: 对查询结果按字段排序
                      .order_by('-created_at', '-id'))
        #: 定义变量「act」，保存对应数据
        act = req.GET.get('act', '')
        #: 条件判断：条件成立时执行该分支
        if act in dict(ModerationLog.Action.choices):
            #: 定义变量「history_qs」，保存对应数据
            history_qs = history_qs.filter(action=act)
        #: 定义变量「history_page」，保存对应数据
        history_page = Paginator(history_qs, 15).get_page(req.GET.get('hpage'))

        # ---- 回收站：软删除文章 + 软删除评论（各自分页，每页 10 条）----
        #: 定义变量「trash_articles_page」，保存对应数据
        trash_articles_page = Paginator(
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            Article.objects.filter(is_deleted=True).select_related('author', 'category')
            #: 对查询结果按字段排序
            .order_by('-deleted_at', '-id'), 10).get_page(req.GET.get('tpage'))
        #: 定义变量「trash_comments_page」，保存对应数据
        trash_comments_page = Paginator(
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            Comment.objects.filter(is_deleted=True).select_related('user', 'article')
            #: 对查询结果按字段排序
            .order_by('-deleted_at', '-id'), 10).get_page(req.GET.get('tcpage'))

        #: 定义变量「ctx」，保存对应数据
        ctx = {
            #: 配置项「tab」：字典/模型的该键设置为对应值
            'tab': tab, 'sort': sort, 'order': order, 'act': act,
            #: 配置项「pending_page」：字典/模型的该键设置为对应值
            'pending_page': pending_page,
            #: 配置项「reports_page」：字典/模型的该键设置为对应值
            'reports_page': reports_page,
            #: 配置项「promo_page」：字典/模型的该键设置为对应值
            'promo_page': promo_page,
            # Bug8：已处理推广申请 + 系统执行状态总览
            #: 配置项「promo_done_page」：字典/模型的该键设置为对应值
            'promo_done_page': promo_done_page,
            #: 配置项「exec_stats」：字典/模型的该键设置为对应值
            'exec_stats': exec_stats,
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'pinned_count': Article.objects.filter(is_pinned=True, is_deleted=False).count(),
            #: 配置项「history_page」：字典/模型的该键设置为对应值
            'history_page': history_page,
            #: 配置项「trash_articles_page」：字典/模型的该键设置为对应值
            'trash_articles_page': trash_articles_page,
            #: 配置项「trash_comments_page」：字典/模型的该键设置为对应值
            'trash_comments_page': trash_comments_page,
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'pending_count': Article.objects.filter(
                #: 定义变量「status」，保存对应数据
                status=Article.Status.PENDING, is_deleted=False).count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'report_count': CommentReport.objects.count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'promotion_count': PromotionRequest.objects.filter(
                #: 定义变量「status」，保存对应数据
                status=PromotionRequest.Status.PENDING).count(),
            #: 配置项「moderation_settings」：字典/模型的该键设置为对应值
            'moderation_settings': ModerationSettings.load(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'history_count': ModerationLog.objects.count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'trash_count': Article.objects.filter(is_deleted=True).count()
                           #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
                           + Comment.objects.filter(is_deleted=True).count(),
            #: 配置项「action_choices」：字典/模型的该键设置为对应值
            'action_choices': ModerationLog.Action.choices,
            #: 配置项「active_nav」：字典/模型的该键设置为对应值
            'active_nav': 'moderation',
        #: 该行执行对应逻辑（结合上下文理解）
        }
        #: 返回结果并结束当前函数
        return render(req, 'blog/moderation.html', ctx)

    #: 返回结果并结束当前函数
    return _inner(request)

def moderate_article(request: HttpRequest, pk: int) -> HttpResponse:
    """处理待审文章（bug8）：approve=通过并发布；reject=退回作者修改（不删除）。

    两次动作均写入 ModerationLog 审核历史；驳回时向作者发送站内通知并附理由，
    文章回到草稿状态供其修改后重新提交。
    """
    #: 从模块「django.contrib.admin.views.decorators」导入所需对象
    from blog.utils.decorators import staff_required_moe

    #: 装饰器：为下一个定义附加「staff_member_required」行为（权限、缓存、注册信号等）
    @staff_required_moe
    def _inner(req):
        """
        功能：处理「inner」相关逻辑。

        参数：
          - req：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：装饰器 staff_member_required 决定其附加行为（权限/缓存/属性/信号等）；含 Django ORM 数据库查询，注意查询性能与空结果处理。
        """
        #: 条件判断：条件成立时执行该分支
        if req.method != 'POST':
            #: 返回结果并结束当前函数
            return redirect('/console/moderation/?tab=articles')
        #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
        article = get_object_or_404(Article, pk=pk, is_deleted=False)
        #: 定义变量「action」，保存对应数据
        action = req.POST.get('action', '')
        #: 条件判断：条件成立时执行该分支
        if action == 'approve':
            # Bug8：定时投稿（published_at 已到点）在此刻才真正发布，
            # 因此把发布时间对齐到「实际通过时刻」，避免文章列表出现未来时间。
            #: 获取当前时间（时区感知），统一时间口径
            is_scheduled = bool(article.published_at and article.published_at <= timezone.now())
            #: 定义实例/类属性「article.status」，保存对应数据
            article.status = Article.Status.PUBLISHED
            #: 定义变量「fields」，保存对应数据（集合/元组）
            fields = ['status', 'updated_at']
            #: 条件判断：条件成立时执行该分支
            if is_scheduled:
                #: 获取当前时间（时区感知），统一时间口径
                article.published_at = timezone.now()
                #: 调用「fields.append」执行相应逻辑
                fields.append('published_at')
            #: 调用「article.save」执行相应逻辑
            article.save(update_fields=fields)
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            ModerationLog.objects.create(
                #: 定义变量「moderator」，保存对应数据
                moderator=req.user, moderator_name=str(req.user),
                #: 定义变量「action」，保存对应数据
                action=ModerationLog.Action.APPROVE, target_type='article',
                #: 定义变量「article」，保存对应数据
                article=article, target_title=article.title,
                #: 定义变量「reason」，保存对应数据
                reason='通过审核并发布（定时投稿到点转入审核）' if is_scheduled else '')
            #: 向用户闪现一条提示消息（下次请求展示）
            messages.success(req, msg('article.approved', article.title))
        #: 否则若该条件成立则进入此分支
        elif action == 'reject':
            #: 定义变量「reason」，保存对应数据（集合/元组）
            reason = (req.POST.get('reason') or '').strip()[:500]
            # 退回草稿（不删除内容），作者修改后可重新提交审核
            #: 定义实例/类属性「article.status」，保存对应数据
            article.status = Article.Status.DRAFT
            #: 调用「article.save」执行相应逻辑
            article.save(update_fields=['status', 'updated_at'])
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            ModerationLog.objects.create(
                #: 定义变量「moderator」，保存对应数据
                moderator=req.user, moderator_name=str(req.user),
                #: 定义变量「action」，保存对应数据
                action=ModerationLog.Action.REJECT, target_type='article',
                #: 定义变量「article」，保存对应数据
                article=article, target_title=article.title, reason=reason)
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            Notification.objects.create(
                #: 定义变量「user」，保存对应数据
                user=article.author, type=Notification.Type.SYSTEM,
                #: 定义变量「title」，保存对应数据
                title='你的文章《%s》未通过审核' % article.title[:30],
                #: 定义变量「content」，保存对应数据
                content=reason or '内容还需要调整一下哦，修改后可以重新提交~')
            #: 向用户闪现一条提示消息（下次请求展示）
            messages.warning(req, msg('article.rejected', article.title))
        #: 返回结果并结束当前函数
        return redirect('/console/moderation/?tab=articles')

    #: 返回结果并结束当前函数
    return _inner(request)

def moderate_report(request: HttpRequest, pk: int) -> HttpResponse:
    """处理举报（bug8）：keep=举报不成立保留评论；delete_comment=软删除违规评论。

    全部动作写入 ModerationLog；软删除评论同时回退文章冗余评论数，
    举报记录处理后移除（删除前已写入项目备份）。
    """
    #: 从模块「django.contrib.admin.views.decorators」导入所需对象
    from blog.utils.decorators import staff_required_moe

    #: 装饰器：为下一个定义附加「staff_member_required」行为（权限、缓存、注册信号等）
    @staff_required_moe
    def _inner(req):
        """
        功能：处理「inner」相关逻辑。

        参数：
          - req：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：装饰器 staff_member_required 决定其附加行为（权限/缓存/属性/信号等）；含 Django ORM 数据库查询，注意查询性能与空结果处理。
        """
        #: 条件判断：条件成立时执行该分支
        if req.method != 'POST':
            #: 返回结果并结束当前函数
            return redirect('/console/moderation/?tab=reports')
        #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
        report = get_object_or_404(
            #: ORM 预加载关联，减少 N+1 查询提升性能
            CommentReport.objects.select_related('comment', 'comment__article'), pk=pk)
        #: 定义变量「action」，保存对应数据
        action = req.POST.get('action', '')
        #: 定义变量「comment」，保存对应数据
        comment = report.comment
        #: 条件判断：条件成立时执行该分支
        if action == 'keep':
            #: 定义变量「payload」，保存对应数据
            payload = {
                #: 配置项「id」：字典/模型的该键设置为对应值
                'id': report.id, 'comment_id': comment.id,
                #: 配置项「reporter」：字典/模型的该键设置为对应值
                'reporter': getattr(report.reporter, 'username', None),
                #: 配置项「reason」：字典/模型的该键设置为对应值
                'reason': report.reason, 'created_at': report.created_at,
                #: 获取当前时间（时区感知），统一时间口径
                'backed_up_at': timezone.now()}
            #: 调用「_moderation_backup」执行相应逻辑
            _moderation_backup('report_dismissed', payload)
            # 该评论若还有其他未处理举报则保持 reported 标记
            #: 条件判断：条件成立时执行该分支
            if not comment.reports.exclude(pk=report.pk).exists():
                #: 定义实例/类属性「comment.reported」，保存对应数据
                comment.reported = False
                #: 调用「comment.save」执行相应逻辑
                comment.save(update_fields=['reported'])
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            ModerationLog.objects.create(
                #: 定义变量「moderator」，保存对应数据
                moderator=req.user, moderator_name=str(req.user),
                #: 定义变量「action」，保存对应数据
                action=ModerationLog.Action.APPROVE, target_type='comment',
                #: 定义变量「article_id」，保存对应数据
                article_id=comment.article_id, comment=comment,
                #: 定义变量「target_title」，保存对应数据（集合/元组）
                target_title=(re.sub(r'<[^>]+>', '', comment.content or '') or '')[:40],
                #: 定义变量「reason」，保存对应数据
                reason='举报不成立：%s' % (report.reason or ''))
            #: 删除对象，注意级联与权限
            report.delete()
            #: 向用户闪现一条提示消息（下次请求展示）
            messages.success(req, msg('comment.report_dismissed'))
        #: 否则若该条件成立则进入此分支
        elif action == 'delete_comment' and comment is not None:
            #: 定义变量「path」，保存对应数据
            path = _moderation_backup('comment', _comment_snapshot(comment))
            #: 定义变量「cid」，保存对应数据
            cid = comment.id
            #: 定义变量「art_id」，保存对应数据
            art_id = comment.article_id
            # bug8: 违规评论改为软删除（前台隐藏、可恢复），不再物理删除
            #: 定义实例/类属性「comment.is_deleted」，保存对应数据
            comment.is_deleted = True
            #: 获取当前时间（时区感知），统一时间口径
            comment.deleted_at = timezone.now()
            #: 调用「comment.save」执行相应逻辑
            comment.save(update_fields=['is_deleted', 'deleted_at'])
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            ModerationLog.objects.create(
                #: 定义变量「moderator」，保存对应数据
                moderator=req.user, moderator_name=str(req.user),
                #: 定义变量「action」，保存对应数据
                action=ModerationLog.Action.SOFT_DELETE, target_type='comment',
                #: 定义变量「article_id」，保存对应数据
                article_id=art_id, comment=comment,
                #: 定义变量「target_title」，保存对应数据（集合/元组）
                target_title=(re.sub(r'<[^>]+>', '', comment.content or '') or '')[:40],
                #: 定义变量「reason」，保存对应数据
                reason='举报成立：%s' % (report.reason or ''))
            # 按实际存活评论数重算（避免 ±1 漂移）
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            Article.objects.filter(pk=art_id).update(
                #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
                comment_count=Comment.objects.filter(article_id=art_id, is_deleted=False).count())
            # 移除该评论的全部举报
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            CommentReport.objects.filter(comment=comment).delete()
            #: 向用户闪现一条提示消息（下次请求展示）
            messages.warning(req, msg('comment.hidden_backup', 
                #: 该行执行对应逻辑（结合上下文理解）
                cid, os.path.relpath(path, settings.BASE_DIR)))
        #: 返回结果并结束当前函数
        return redirect('/console/moderation/?tab=reports')

    #: 返回结果并结束当前函数
    return _inner(request)

# ============================ Bug8：回收站恢复 / 彻底删除 ============================
def _plain_snippet(text, length=40):
    """去掉 HTML 标签后截取前 length 字，供日志标题快照使用。"""
    #: 返回结果并结束当前函数
    return (re.sub(r'<[^>]+>', '', text or '') or '')[:length]

#: 装饰器：为下一个定义附加「staff_member_required」行为（权限、缓存、注册信号等）
@staff_required_moe
def restore_article(request: HttpRequest, pk: int) -> HttpResponse:
    """回收站恢复文章：取消软删除，写 RESTORE 日志。仅 POST。"""
    #: 条件判断：条件成立时执行该分支
    if request.method != 'POST':
        #: 返回结果并结束当前函数
        return redirect('/console/moderation/?tab=trash')
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    article = get_object_or_404(Article, pk=pk, is_deleted=True)
    #: 定义实例/类属性「article.is_deleted」，保存对应数据
    article.is_deleted = False
    #: 定义实例/类属性「article.deleted_at」，保存对应数据
    article.deleted_at = None
    #: 调用「article.save」执行相应逻辑
    article.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    ModerationLog.objects.create(
        #: 读取本次请求的 user 数据
        moderator=request.user, moderator_name=str(request.user),
        #: 定义变量「action」，保存对应数据
        action=ModerationLog.Action.RESTORE, target_type='article',
        #: 定义变量「article」，保存对应数据
        article=article, target_title=article.title)
    #: 读写缓存，减轻数据库压力，注意键与过期时间
    cache.delete(SIDEBAR_CACHE_KEY)
    #: 读写缓存，减轻数据库压力，注意键与过期时间
    cache.delete('footer_stats')
    #: 读写缓存，减轻数据库压力，注意键与过期时间
    cache.delete('sidebar_stats')
    #: 向用户闪现一条提示消息（下次请求展示）
    messages.success(request, msg('article.restored', article.title))
    #: 返回结果并结束当前函数
    return redirect('/console/moderation/?tab=trash')

#: 装饰器：为下一个定义附加「staff_member_required」行为（权限、缓存、注册信号等）
@staff_required_moe
def hard_delete_article(request: HttpRequest, pk: int) -> HttpResponse:
    """彻底删除文章：不可恢复，先写 HARD_DELETE 日志（外键随后置空）。仅 POST。"""
    #: 条件判断：条件成立时执行该分支
    if request.method != 'POST':
        #: 返回结果并结束当前函数
        return redirect('/console/moderation/?tab=trash')
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    article = get_object_or_404(Article, pk=pk, is_deleted=True)
    #: 定义变量「title」，保存对应数据
    title = article.title
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    ModerationLog.objects.create(
        #: 读取本次请求的 user 数据
        moderator=request.user, moderator_name=str(request.user),
        #: 定义变量「action」，保存对应数据
        action=ModerationLog.Action.HARD_DELETE, target_type='article',
        #: 定义变量「article」，保存对应数据
        article=article, target_title=title)
    #: 删除对象，注意级联与权限
    article.delete()
    #: 读写缓存，减轻数据库压力，注意键与过期时间
    cache.delete(SIDEBAR_CACHE_KEY)
    #: 读写缓存，减轻数据库压力，注意键与过期时间
    cache.delete('footer_stats')
    #: 读写缓存，减轻数据库压力，注意键与过期时间
    cache.delete('sidebar_stats')
    #: 向用户闪现一条提示消息（下次请求展示）
    messages.warning(request, msg('article.hard_deleted', title))
    #: 返回结果并结束当前函数
    return redirect('/console/moderation/?tab=trash')

#: 装饰器：为下一个定义附加「staff_member_required」行为（权限、缓存、注册信号等）
@staff_required_moe
def restore_comment(request: HttpRequest, pk: int) -> HttpResponse:
    """回收站恢复评论：取消软删除、评论数 +1，写 RESTORE 日志。仅 POST。"""
    #: 条件判断：条件成立时执行该分支
    if request.method != 'POST':
        #: 返回结果并结束当前函数
        return redirect('/console/moderation/?tab=trash')
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    comment = get_object_or_404(Comment, pk=pk, is_deleted=True)
    #: 定义实例/类属性「comment.is_deleted」，保存对应数据
    comment.is_deleted = False
    #: 定义实例/类属性「comment.deleted_at」，保存对应数据
    comment.deleted_at = None
    #: 调用「comment.save」执行相应逻辑
    comment.save(update_fields=['is_deleted', 'deleted_at'])
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    Article.objects.filter(pk=comment.article_id).update(
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        comment_count=Comment.objects.filter(article_id=comment.article_id, is_deleted=False).count())
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    ModerationLog.objects.create(
        #: 读取本次请求的 user 数据
        moderator=request.user, moderator_name=str(request.user),
        #: 定义变量「action」，保存对应数据
        action=ModerationLog.Action.RESTORE, target_type='comment',
        #: 定义变量「article_id」，保存对应数据
        article_id=comment.article_id, comment=comment,
        #: 定义变量「target_title」，保存对应数据
        target_title=_plain_snippet(comment.content))
    #: 调用「invalidate_article」执行相应逻辑
    invalidate_article(comment.article_id)
    #: 向用户闪现一条提示消息（下次请求展示）
    messages.success(request, msg('comment.restored', pk))
    #: 返回结果并结束当前函数
    return redirect('/console/moderation/?tab=trash')

#: 装饰器：为下一个定义附加「staff_member_required」行为（权限、缓存、注册信号等）
@staff_required_moe
def hard_delete_comment(request: HttpRequest, pk: int) -> HttpResponse:
    """彻底删除评论：不可恢复，先删其举报、再写 HARD_DELETE 日志。仅 POST。"""
    #: 条件判断：条件成立时执行该分支
    if request.method != 'POST':
        #: 返回结果并结束当前函数
        return redirect('/console/moderation/?tab=trash')
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    comment = get_object_or_404(Comment, pk=pk, is_deleted=True)
    #: 定义变量「art_id」，保存对应数据
    art_id = comment.article_id
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    CommentReport.objects.filter(comment=comment).delete()
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    ModerationLog.objects.create(
        #: 读取本次请求的 user 数据
        moderator=request.user, moderator_name=str(request.user),
        #: 定义变量「action」，保存对应数据
        action=ModerationLog.Action.HARD_DELETE, target_type='comment',
        #: 定义变量「article_id」，保存对应数据
        article_id=art_id, comment=comment,
        #: 定义变量「target_title」，保存对应数据
        target_title=_plain_snippet(comment.content))
    #: 删除对象，注意级联与权限
    comment.delete()
    #: 调用「invalidate_article」执行相应逻辑
    invalidate_article(art_id)
    #: 向用户闪现一条提示消息（下次请求展示）
    messages.warning(request, msg('comment.hard_deleted', pk))
    #: 返回结果并结束当前函数
    return redirect('/console/moderation/?tab=trash')

# ============================ Bug1：置顶 / 精华 / 热门 权限与审核 ============================
# 推广类型 → (Article 字段名, 设置动作, 取消动作) 的映射，集中维护避免散落
#: 定义变量「_PROMO_FIELD」，保存对应数据
_PROMO_FIELD = {
    #: 操作「PromotionRequest.Kind」的属性或方法
    PromotionRequest.Kind.PIN: ('is_pinned', ModerationLog.Action.PIN, ModerationLog.Action.UNPIN),
    #: 操作「PromotionRequest.Kind」的属性或方法
    PromotionRequest.Kind.FEATURE: ('is_featured', ModerationLog.Action.FEATURE, ModerationLog.Action.UNFEATURE),
    #: 操作「PromotionRequest.Kind」的属性或方法
    PromotionRequest.Kind.HOT: ('is_hot', ModerationLog.Action.HOT, ModerationLog.Action.UNHOT),
#: 该行执行对应逻辑（结合上下文理解）
}

# 推广类型 → 中文短名（提示文案统一走这里，避免各处硬编码）
#: 定义变量「_PROMO_LABEL」，保存对应数据
_PROMO_LABEL = {
    #: 操作「PromotionRequest.Kind」的属性或方法
    PromotionRequest.Kind.PIN: '置顶',
    #: 操作「PromotionRequest.Kind」的属性或方法
    PromotionRequest.Kind.FEATURE: '精华',
    #: 操作「PromotionRequest.Kind」的属性或方法
    PromotionRequest.Kind.HOT: '热门',
#: 该行执行对应逻辑（结合上下文理解）
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
    #: 该行执行对应逻辑（结合上下文理解）
    field, act_on, _act_off = _PROMO_FIELD[pr.kind]
    #: 定义变量「label」，保存对应数据
    label = _PROMO_LABEL.get(pr.kind, pr.get_kind_display())
    #: 尝试执行可能出错的代码
    try:
        # 已经是对应状态：无需重复写库，直接记为执行成功（幂等）
        #: 条件判断：条件成立时执行该分支
        if getattr(pr.article, field):
            #: 返回结果并结束当前函数
            return True, PromotionRequest.Execution.SUCCESS, '文章已是%s状态，无需重复设置' % label
        # 置顶上限校验：已达上限则不实际置顶，但保留「审批通过」的结论，
        # 并由系统执行状态明确告知「已通过但未执行（已达上限）」。
        #: 条件判断：条件成立时执行该分支
        if pr.kind == PromotionRequest.Kind.PIN:
            #: 定义变量「max_pinned」，保存对应数据
            max_pinned = ModerationSettings.load().max_pinned
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            current = Article.objects.filter(is_pinned=True, is_deleted=False).count()
            #: 条件判断：条件成立时执行该分支
            if current >= max_pinned:
                #: 返回结果并结束当前函数
                return (False, PromotionRequest.Execution.SKIPPED,
                        #: 该行执行对应逻辑（结合上下文理解）
                        '置顶名额已满（%d/%d 篇），系统未执行置顶' % (current, max_pinned))
        #: 调用「setattr」执行相应逻辑
        setattr(pr.article, field, True)
        #: 调用「pr.article.save」执行相应逻辑
        pr.article.save(update_fields=[field, 'updated_at'])
        #: 返回结果并结束当前函数
        return True, PromotionRequest.Execution.SUCCESS, '系统已执行：文章已设为%s' % label
    #: 捕获并处理异常，避免程序中断
    except Exception as exc:  # noqa: BLE001 执行失败不得中断审批流程，但要如实记录
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.error('推广申请系统执行失败: pr=%s kind=%s err=%s', pr.pk, pr.kind, exc,
                     #: 定义变量「exc_info」，保存对应数据
                     exc_info=True)
        #: 返回结果并结束当前函数
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
    #: 定义变量「state」，保存对应数据
    state = {}
    #: 定义变量「labels」，保存对应数据
    labels = _PROMO_LABEL
    #: 定义变量「fields」，保存对应数据
    fields = {k: v[0] for k, v in _PROMO_FIELD.items()}
    #: 定义变量「pending_kinds」，保存对应数据
    pending_kinds = set()
    #: 条件判断：条件成立时执行该分支
    if user.is_authenticated:
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        pending_kinds = set(PromotionRequest.objects.filter(
            #: 定义变量「article」，保存对应数据
            article=article, applicant=user,
            #: 定义变量「status」，保存对应数据
            status=PromotionRequest.Status.PENDING).values_list('kind', flat=True))
    # 置顶名额是否已满（排除软删除文章，与 _promo_execute 口径保持一致）
    #: 定义变量「max_pinned」，保存对应数据
    max_pinned = ModerationSettings.load().max_pinned
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    pinned_count = Article.objects.filter(is_pinned=True, is_deleted=False).count()
    #: 定义变量「pin_full」，保存对应数据
    pin_full = pinned_count >= max_pinned
    #: 循环遍历，逐个处理元素
    for kind, field in fields.items():
        #: 定义变量「applied」，保存对应数据
        applied = bool(getattr(article, field, False))
        #: 定义变量「pending」，保存对应数据
        pending = kind in pending_kinds
        #: 条件判断：条件成立时执行该分支
        if applied:
            #: 该行执行对应逻辑（结合上下文理解）
            st, text = 'applied', '已经%s' % labels[kind]
        #: 否则若该条件成立则进入此分支
        elif pending:
            #: 该行执行对应逻辑（结合上下文理解）
            st, text = 'pending', '%s审核中' % labels[kind]
        #: 以上条件均不成立时的兜底分支
        else:
            #: 该行执行对应逻辑（结合上下文理解）
            st, text = 'open', '申请%s' % labels[kind]
        #: 该行执行对应逻辑（结合上下文理解）
        state[kind] = {'applied': applied, 'pending': pending, 'state': st,
                       #: 配置项「label」：字典/模型的该键设置为对应值
                       'label': labels[kind], 'text': text,
                       #: 配置项「limit_full」：字典/模型的该键设置为对应值
                       'limit_full': bool(pin_full and kind == PromotionRequest.Kind.PIN),
                       #: 配置项「pinned_count」：字典/模型的该键设置为对应值
                       'pinned_count': pinned_count, 'max_pinned': max_pinned}
    #: 返回结果并结束当前函数
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
    #: 条件判断：条件成立时执行该分支
    if not request.user.is_authenticated:
        #: 返回结果并结束当前函数
        return JsonResponse({'code': 403, 'msg': msg('auth.login_required')}, status=403)
    #: 条件判断：条件成立时执行该分支
    if request.method != 'POST':
        #: 返回结果并结束当前函数
        return JsonResponse({'code': 405, 'msg': msg('err.method_not_allowed')}, status=405)
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    article = get_object_or_404(Article, pk=pk, is_deleted=False)
    #: 条件判断：条件成立时执行该分支
    if request.user != article.author and not request.user.is_staff:
        #: 返回结果并结束当前函数
        return JsonResponse({'code': 403, 'msg': msg('promo.only_own')}, status=403)
    #: 读取本次请求的 POST 数据
    kind = request.POST.get('kind', '')
    #: 条件判断：条件成立时执行该分支
    if kind not in PromotionRequest.Kind.values:
        #: 返回结果并结束当前函数
        return JsonResponse({'code': 400, 'msg': msg('promo.bad_kind')}, status=400)
    # Bug8：已经生效的推广不再受理申请（按钮侧也已禁用，这里做服务端兜底）
    #: 定义变量「field」，保存对应数据
    field = _PROMO_FIELD[kind][0]
    #: 定义变量「label」，保存对应数据
    label = _PROMO_LABEL[kind]
    #: 条件判断：条件成立时执行该分支
    if getattr(article, field):
        #: 返回结果并结束当前函数
        return JsonResponse(
            #: 该行执行对应逻辑（结合上下文理解）
            {'code': 409, 'msg': msg('promo.already_applied', label),
             #: 配置项「data」：字典/模型的该键设置为对应值
             'data': {'already_applied': True, 'kind': kind}},
            #: 定义变量「status」，保存对应数据
            status=409)
    #: 读取本次请求的 POST 数据
    reason = (request.POST.get('reason') or '').strip()[:500]
    #: 条件判断：条件成立时执行该分支
    if not reason:
        #: 返回结果并结束当前函数
        return JsonResponse({'code': 400, 'msg': msg('promo.reason_required')}, status=400)
    # 已有同类型待审核申请，不允许重复提交
    #: 条件判断：条件成立时执行该分支
    if PromotionRequest.objects.filter(
            #: 定义变量「article」，保存对应数据
            article=article, kind=kind,
            #: 定义变量「status」，保存对应数据
            status=PromotionRequest.Status.PENDING).exists():
        #: 返回结果并结束当前函数
        return JsonResponse({'code': 409, 'msg': msg('promo.duplicate')}, status=409)
    # Bug8：置顶名额已满时提前告知，避免「管理员通过了却没置顶」的预期落差
    #: 定义变量「notice」，保存对应数据
    notice = ''
    #: 条件判断：条件成立时执行该分支
    if kind == PromotionRequest.Kind.PIN:
        #: 定义变量「max_pinned」，保存对应数据
        max_pinned = ModerationSettings.load().max_pinned
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        current = Article.objects.filter(is_pinned=True, is_deleted=False).count()
        #: 条件判断：条件成立时执行该分支
        if current >= max_pinned:
            #: 定义变量「notice」，保存对应数据（集合/元组）
            notice = ('当前置顶名额已满（%d/%d 篇），即使审核通过系统也可能暂时无法置顶喵~'
                      #: 该行执行对应逻辑（结合上下文理解）
                      % (current, max_pinned))
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    pr = PromotionRequest.objects.create(
        #: 读取本次请求的 user 数据
        article=article, applicant=request.user, kind=kind, reason=reason)
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    ModerationLog.objects.create(
        #: 读取本次请求的 user 数据
        moderator=request.user, moderator_name=str(request.user),
        #: 定义变量「action」，保存对应数据
        action=ModerationLog.Action.SUBMIT, target_type='article',
        #: 定义变量「article」，保存对应数据
        article=article, target_title=article.title,
        #: 定义变量「reason」，保存对应数据
        reason='【%s申请】%s' % (pr.get_kind_display(), reason))
    #: 定义变量「msg」，保存对应数据
    msg = '申请已提交，等待管理员审核喵~'
    #: 条件判断：条件成立时执行该分支
    if notice:
        #: 定义变量「msg」，保存对应数据
        msg = notice + ' 申请已提交喵~'
    #: 返回结果并结束当前函数
    return JsonResponse({'code': 0, 'msg': msg, 'notice': notice,
                         #: 配置项「data」：字典/模型的该键设置为对应值
                         'data': {'id': pr.id}})

def api_article_promotion_status(request, pk):
    """Bug8 新增：查询某文章三个推广标记 + 当前用户申请状态（详情页按钮自检用）。

    GET /api/article/<pk>/promotion-status/  → JSON
    作者或任意登录用户均可查询自己的申请状态；返回结构与 ``_promo_block_state`` 一致。
    """
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    article = get_object_or_404(Article, pk=pk, is_deleted=False)
    #: 返回结果并结束当前函数
    return JsonResponse({'code': 0, 'data': {
        #: 读取本次请求的 user 数据
        'states': _promo_block_state(article, request.user),
        #: 配置项「is_pinned」：字典/模型的该键设置为对应值
        'is_pinned': article.is_pinned,
        #: 配置项「is_featured」：字典/模型的该键设置为对应值
        'is_featured': article.is_featured,
        #: 配置项「is_hot」：字典/模型的该键设置为对应值
        'is_hot': article.is_hot,
        #: 配置项「max_pinned」：字典/模型的该键设置为对应值
        'max_pinned': ModerationSettings.load().max_pinned,
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        'pinned_count': Article.objects.filter(is_pinned=True, is_deleted=False).count(),
    #: 该行执行对应逻辑（结合上下文理解）
    }})

def api_article_toggle_promotion(request, pk):
    """管理员直接设置/取消置顶、精华、热门：POST /api/article/<pk>/toggle-promotion/。

    action 取 pin/unpin/feature/unfeature/hot/unhot；直接改 Article 标记并写日志。
    置顶时若超过全局上限则拒绝。
    """
    #: 条件判断：条件成立时执行该分支
    if not (request.user.is_authenticated and request.user.is_staff):
        #: 返回结果并结束当前函数
        return JsonResponse({'code': 403, 'msg': msg('err.admin_only')}, status=403)
    #: 条件判断：条件成立时执行该分支
    if request.method != 'POST':
        #: 返回结果并结束当前函数
        return JsonResponse({'code': 405, 'msg': msg('err.method_not_allowed')}, status=405)
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    article = get_object_or_404(Article, pk=pk, is_deleted=False)
    #: 读取本次请求的 POST 数据
    action = request.POST.get('action', '')
    # action → (申请类型, 目标布尔值)
    #: 定义变量「mapping」，保存对应数据
    mapping = {
        #: 配置项「pin」：字典/模型的该键设置为对应值
        'pin': (PromotionRequest.Kind.PIN, True), 'unpin': (PromotionRequest.Kind.PIN, False),
        #: 配置项「feature」：字典/模型的该键设置为对应值
        'feature': (PromotionRequest.Kind.FEATURE, True), 'unfeature': (PromotionRequest.Kind.FEATURE, False),
        #: 配置项「hot」：字典/模型的该键设置为对应值
        'hot': (PromotionRequest.Kind.HOT, True), 'unhot': (PromotionRequest.Kind.HOT, False),
    #: 该行执行对应逻辑（结合上下文理解）
    }
    #: 条件判断：条件成立时执行该分支
    if action not in mapping:
        #: 返回结果并结束当前函数
        return JsonResponse({'code': 400, 'msg': msg('err.bad_request')}, status=400)
    #: 该行执行对应逻辑（结合上下文理解）
    kind, target = mapping[action]
    #: 该行执行对应逻辑（结合上下文理解）
    field, act_on, act_off = _PROMO_FIELD[kind]
    # 置顶上限校验（仅在「设置置顶」且当前未置顶时）
    #: 条件判断：条件成立时执行该分支
    if kind == PromotionRequest.Kind.PIN and target:
        #: 定义变量「max_pinned」，保存对应数据
        max_pinned = ModerationSettings.load().max_pinned
        #: 条件判断：条件成立时执行该分支
        if not article.is_pinned and Article.objects.filter(
                #: 定义变量「is_pinned」，保存对应数据
                is_pinned=True, is_deleted=False).count() >= max_pinned:
            #: 返回结果并结束当前函数
            return JsonResponse({'code': 409, 'msg': msg('promo.limit_reached', max_pinned)}, status=409)
    #: 调用「setattr」执行相应逻辑
    setattr(article, field, target)
    #: 调用「article.save」执行相应逻辑
    article.save(update_fields=[field, 'updated_at'])
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    ModerationLog.objects.create(
        #: 读取本次请求的 user 数据
        moderator=request.user, moderator_name=str(request.user),
        #: 定义变量「action」，保存对应数据
        action=act_on if target else act_off, target_type='article',
        #: 定义变量「article」，保存对应数据
        article=article, target_title=article.title)
    #: 定义变量「labels」，保存对应数据
    labels = _PROMO_LABEL
    #: 返回结果并结束当前函数
    return JsonResponse({'code': 0,
                         #: 配置项「msg」：字典/模型的该键设置为对应值
                         'msg': msg('promo.toggle_ok', '设置' if target else '取消', labels[kind]),
                         #: 配置项「data」：字典/模型的该键设置为对应值
                         'data': {field: target,
                                  #: 读取本次请求的 user 数据
                                  'states': _promo_block_state(article, request.user)}})

@staff_required_moe
def moderate_promotion(request, pk):
    """管理员审批推广申请：POST /console/moderation/promotion/<pk>/，approve/reject。

    Bug8 重构：审批结论（status）与系统执行结果（execution_status）分离记录 ——
    - 通过：立即调用 ``_promo_execute`` 尝试落地；置顶名额已满时不落地，但把
      execution_status 记为「未执行·已达上限」并在审核页醒目展示，同时给作者
      发一条说明「已通过但受名额限制暂未生效」的通知，避免出现「显示已通过却
      没有置顶」的黑盒状态；
    - 驳回：置 REJECTED、写日志并通知作者驳回理由。
    """
    #: 条件判断：条件成立时执行该分支（权限已由模块级 @staff_required_moe 统一校验）
    if request.method != 'POST':
        #: 返回结果并结束当前函数
        return redirect('/console/moderation/?tab=promotions')
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    pr = get_object_or_404(
        #: ORM 预加载关联，减少 N+1 查询提升性能
        PromotionRequest.objects.select_related('article', 'applicant'), pk=pk)
    #: 读取本次请求的 POST 数据
    action = request.POST.get('action', '')
    #: 读取本次请求的 POST 数据
    note = (request.POST.get('reason') or '').strip()[:500]
    #: 条件判断：条件成立时执行该分支
    if pr.status != PromotionRequest.Status.PENDING:
        #: 向用户闪现一条提示消息（下次请求展示）
        messages.warning(request, msg('moderation.already_handled'))
        #: 返回结果并结束当前函数
        return redirect('/console/moderation/?tab=promotions')
    #: 定义变量「label」，保存对应数据
    label = _PROMO_LABEL.get(pr.kind, pr.get_kind_display())
    #: 该行执行对应逻辑（结合上下文理解）
    _field, act_on, _act_off = _PROMO_FIELD[pr.kind]
    #: 条件判断：条件成立时执行该分支
    if action == 'approve':
        #: 定义实例/类属性「pr.status」，保存对应数据
        pr.status = PromotionRequest.Status.APPROVED
        #: 读取本次请求的 user 数据
        pr.handled_by = request.user
        #: 获取当前时间（时区感知），统一时间口径
        pr.handled_at = timezone.now()
        # ---- Bug8：真实落地 + 记录系统执行状态 ----
        #: 读取本次请求的 user 数据
        applied, exec_status, exec_note = _promo_execute(pr, request.user)
        #: 定义实例/类属性「pr.execution_status」，保存对应数据
        pr.execution_status = exec_status
        #: 定义实例/类属性「pr.execution_note」，保存对应数据
        pr.execution_note = exec_note[:200]
        #: 获取当前时间（时区感知），统一时间口径
        pr.executed_at = timezone.now()
        #: 调用「pr.save」执行相应逻辑
        pr.save(update_fields=['status', 'handled_by', 'handled_at',
                               #: 该行执行对应逻辑（结合上下文理解）
                               'execution_status', 'execution_note', 'executed_at'])
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        ModerationLog.objects.create(
            #: 读取本次请求的 user 数据
            moderator=request.user, moderator_name=str(request.user),
            #: 定义变量「action」，保存对应数据
            action=act_on, target_type='article', article=pr.article,
            #: 定义变量「target_title」，保存对应数据
            target_title=pr.article.title,
            #: 定义变量「reason」，保存对应数据
            reason='通过%s申请：%s（系统执行：%s）' % (label, pr.reason, exec_note))
        # 通知作者：已通过但未执行时，文案里必须写清楚原因
        #: 条件判断：条件成立时执行该分支
        if applied:
            #: 定义变量「notify_title」，保存对应数据
            notify_title = '你的%s申请已通过' % label
            #: 定义变量「notify_body」，保存对应数据
            notify_body = '《%s》已设置%s啦~' % (pr.article.title[:30], label)
        #: 以上条件均不成立时的兜底分支
        else:
            #: 定义变量「notify_title」，保存对应数据
            notify_title = '你的%s申请已通过（暂未生效）' % label
            # 文案避免重复堆叠：exec_note 已含原因（如「置顶名额已满（5/5 篇），系统未执行置顶」）
            #: 定义变量「notify_body」，保存对应数据（集合/元组）
            notify_body = ('《%s》的%s申请管理员已通过，但%s。'
                           #: 该行执行对应逻辑（结合上下文理解）
                           '腾出名额后可以再来申请，或联系管理员手动处理喵~'
                           #: 该行执行对应逻辑（结合上下文理解）
                           % (pr.article.title[:30], label, exec_note))
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        Notification.objects.create(
            #: 定义变量「user」，保存对应数据
            user=pr.applicant or pr.article.author, type=Notification.Type.SYSTEM,
            #: 定义变量「title」，保存对应数据
            title=notify_title, content=notify_body)
        #: 条件判断：条件成立时执行该分支
        if applied:
            #: 向用户闪现一条提示消息（下次请求展示）
            messages.success(request, msg('promo.approved_ok', label))
        #: 以上条件均不成立时的兜底分支
        else:
            #: 向用户闪现一条提示消息（下次请求展示）
            messages.warning(request, msg('promo.approved_not_applied', label, exec_note))
    #: 否则若该条件成立则进入此分支
    elif action == 'reject':
        #: 定义实例/类属性「pr.status」，保存对应数据
        pr.status = PromotionRequest.Status.REJECTED
        #: 读取本次请求的 user 数据
        pr.handled_by = request.user
        #: 获取当前时间（时区感知），统一时间口径
        pr.handled_at = timezone.now()
        # 驳回属于「审批结论即为终态」，系统执行状态保持未执行并写清原因
        #: 定义实例/类属性「pr.execution_status」，保存对应数据
        pr.execution_status = PromotionRequest.Execution.NOT_RUN
        #: 定义实例/类属性「pr.execution_note」，保存对应数据
        pr.execution_note = '申请被驳回，系统无需执行'
        #: 调用「pr.save」执行相应逻辑
        pr.save(update_fields=['status', 'handled_by', 'handled_at',
                               #: 该行执行对应逻辑（结合上下文理解）
                               'execution_status', 'execution_note'])
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        ModerationLog.objects.create(
            #: 读取本次请求的 user 数据
            moderator=request.user, moderator_name=str(request.user),
            #: 定义变量「action」，保存对应数据
            action=ModerationLog.Action.REJECT, target_type='article', article=pr.article,
            #: 定义变量「target_title」，保存对应数据
            target_title=pr.article.title,
            #: 定义变量「reason」，保存对应数据
            reason='驳回%s申请：%s %s' % (label, pr.reason, note))
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        Notification.objects.create(
            #: 定义变量「user」，保存对应数据
            user=pr.applicant or pr.article.author, type=Notification.Type.SYSTEM,
            #: 定义变量「title」，保存对应数据
            title='你的%s申请未通过' % label,
            #: 定义变量「content」，保存对应数据
            content=note or '很遗憾，你的申请没有通过，再接再厉哦~')
        #: 向用户闪现一条提示消息（下次请求展示）
        messages.warning(request, msg('promo.rejected', label))
    #: 返回结果并结束当前函数
    return redirect('/console/moderation/?tab=promotions')

@staff_required_moe
def moderation_settings_save(request):
    """保存审核全局设置：POST /console/moderation/settings/（仅 staff）。"""
    #: 条件判断：条件成立时执行该分支（权限已由模块级 @staff_required_moe 统一校验）
    if request.method != 'POST':
        #: 返回结果并结束当前函数
        return redirect('/console/moderation/?tab=promotions')
    #: 定义变量「s」，保存对应数据
    s = ModerationSettings.load()
    #: 读取本次请求的 POST 数据
    s.require_article_review = request.POST.get('require_article_review') == 'on'
    #: 读取本次请求的 POST 数据
    s.require_comment_review = request.POST.get('require_comment_review') == 'on'
    #: 尝试执行可能出错的代码
    try:
        #: 读取本次请求的 POST 数据
        s.comment_recall_minutes = max(1, int(request.POST.get('comment_recall_minutes', 10)))
    #: 捕获并处理异常，避免程序中断
    except (TypeError, ValueError):
        #: 占位语句：此处暂不需要实现
        pass
    #: 尝试执行可能出错的代码
    try:
        #: 读取本次请求的 POST 数据
        s.max_pinned = max(1, int(request.POST.get('max_pinned', 3)))
    #: 捕获并处理异常，避免程序中断
    except (TypeError, ValueError):
        #: 占位语句：此处暂不需要实现
        pass
    #: 保存对象（INSERT/UPDATE），可能触发模型信号
    s.save()
    #: 向用户闪现一条提示消息（下次请求展示）
    messages.success(request, msg('moderation.settings_saved'))
    #: 返回结果并结束当前函数
    return redirect('/console/moderation/?tab=promotions')

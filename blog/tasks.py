"""
Celery 异步任务：
- save_access_log：异步保存访问日志；
- update_article_views：批量统计文章阅读量（定时任务）；
- clean_old_logs：定时清理过期访问日志；
- check_scheduled_articles：定时发布检查（56）；
- send_comment_notification：评论邮件通知文章作者（68）。
"""
import logging
from datetime import timedelta

from celery import shared_task

logger = logging.getLogger(__name__)
from django.db import models
from django.utils import timezone


# 迭代#75: save_access_log任务docstring
@shared_task
def save_access_log(log_data):
    """异步保存访问日志到数据库。

    由 ``AccessLogMiddleware`` 投递（``save_access_log.delay()``），经 Redis broker
    排队后被 worker 消费执行，请求线程不参与本次 INSERT。

    Args:
        log_data: dict，包含访问日志的所有字段。

    Returns:
        str: 简要执行结果描述（saved / error: ...）。
    """
    from django.core.exceptions import ValidationError
    from .models import AccessLog, User
    try:
        user_id = log_data.pop('user_id', None)
        user = User.objects.filter(pk=user_id).first() if user_id else None
        # 代理可能给出 GenericIPAddressField 无法接受的内容，先校验，失败则置空
        ip = log_data.get('ip_address') or None
        if ip:
            try:
                AccessLog._meta.get_field('ip_address').run_validators(ip)
            except ValidationError:
                ip = None
        log_data['ip_address'] = ip
        AccessLog.objects.create(user=user, **log_data)
        return 'saved'
    except Exception as exc:  # noqa: BLE001
        logger.error('访问日志异步入库失败: %s', exc, exc_info=True)
        return f'error: {exc}'


# 迭代#76: update_article_views任务docstring
@shared_task
def update_article_views():
    """批量统计任务：汇总文章阅读数据。

    Returns:
        str: 统计结果描述字符串。
    """
    # 迭代#77: tasks.py中阅读量统计异常处理
    # 迭代#78: 阅读量统计日志
    try:
        from .models import Article
        total = Article.objects.aggregate(total_views=models.Sum('views'))['total_views'] or 0
        article_count = Article.objects.count()
        logger.info('阅读量统计: %s 篇文章, 总量 %s', article_count, total)
        return f'已统计 {article_count} 篇文章，总阅读量 {total}'
    except Exception as exc:
        logger.error('阅读量统计失败: %s', exc)
        return f'统计失败: {exc}'


# 迭代#79: clean_old_logs任务docstring
@shared_task
def clean_old_logs(days=90):
    """定时清理任务：删除指定天数之前的访问日志。

    Args:
        days: 保留最近多少天的日志，默认90天。

    Returns:
        str: 清理结果描述。
    """
    from .models import AccessLog
    # 迭代#80: tasks.py中日志清理异常处理
    # 迭代#81: 日志清理执行日志
    try:
        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = AccessLog.objects.filter(created_at__lt=cutoff).delete()
        logger.info('日志清理: 删除 %s 条', deleted)
        return f'已清理 {deleted} 条 {days} 天前的访问日志'
    except Exception as exc:
        logger.error('日志清理失败: %s', exc)
        return f'日志清理失败: {exc}'


# ============================ 访问日志兜底队列自动补齐 ============================

@shared_task
def flush_access_log_queue(batch=500, max_batches=20):
    """访问日志「Redis 兜底队列」自动补齐任务（Broker 恢复后把积压日志批量入库）。

    背景：访问日志中间件的三层降级策略中，Broker 故障期间日志会先写入 Redis
    列表（``acgblog:access_log:fallback``）。本任务由 Celery beat 每 5 分钟触发，
    尝试批量消费该队列并落库；Broker 已恢复时队列为空，任务安全空转。

    与 ``blog.tasks.save_access_log`` 的区别：后者是「一条请求一条任务」的正常
    异步通道；本任务是「兜底队列补漏」通道，两者互不干扰。

    Returns:
        str: 简要执行结果描述。
    """
    from .access_log_service import drain_fallback
    try:
        result = drain_fallback(batch=batch, max_batches=max_batches)
        if result['error']:
            # Redis 仍不可用：不算任务失败，等下一轮再试（中间件此时走同步兜底）
            logger.warning('访问日志兜底队列消费失败（Redis 不可用）: %s', result['error'])
            return f'兜底队列消费跳过: {result["error"]}'
        if result['ok'] or result['bad']:
            logger.info('访问日志兜底队列补齐: 入库 %s 条，坏数据 %s 条，剩余 %s 条',
                        result['ok'], result['bad'], result['remaining'])
        return ('兜底队列补齐: ok=%s bad=%s remaining=%s'
                % (result['ok'], result['bad'], result['remaining']))
    except Exception as exc:  # noqa: BLE001
        logger.error('访问日志兜底队列任务异常: %s', exc)
        return f'兜底队列任务异常: {exc}'


# 迭代#82: check_scheduled_articles任务docstring
@shared_task
def check_scheduled_articles():
    """56 + Bug8. 定时发布检查任务（每分钟执行一次）。

    Bug8 修复要点（Bug 单原话：定时发布文章异常，若开启了审核定时发布后出现
    draft；如果关闭审核，会直接发布）：

    - 开启「普通作者新文章需审核」时：到点的定时文章 **不得直接发布**，而是
      流转为 ``PENDING``（待审核）并入队内容审核页；管理员通过后才真正发布。
      流转后 ``published_at`` 保持不变（保留作者预约的时间点，仅作为审核参考）。
    - 关闭审核时：按原设计自动置为 ``PUBLISHED``（直接发布）。
    - 每条文章改用 ``save()`` 逐个流转，确保 ``post_save`` 信号（缓存失效、
      搜索索引刷新等）照常触发，不再用 bulk ``update()`` 绕过信号。
    - 同时写入 ``ModerationLog`` 审核历史，管理员能看到「定时转入待审核」的动作。

    Returns:
        str: 简要执行结果描述。
    """
    from django.core.cache import cache
    from .cache_keys import invalidate_article, purge_prevnext
    from .models import Article, ModerationLog, ModerationSettings
    now = timezone.now()
    due = list(Article.objects.filter(
        status=Article.Status.DRAFT,
        is_deleted=False,
        published_at__isnull=False,
        published_at__lte=now,
    ).select_related('author')[:200])  # 单轮上限，避免异常堆积时一次处理过多
    if not due:
        return '已自动发布 0 篇定时文章'
    # 是否开启文章审核：决定「定时到点」后进入 PENDING 还是直接 PUBLISHED
    require_review = ModerationSettings.load().require_article_review
    target_status = (Article.Status.PENDING if require_review
                     else Article.Status.PUBLISHED)
    try:
        changed_pks, published_cnt, pending_cnt = [], 0, 0
        for article in due:
            # 管理员发文始终可直接发布（与 article_new 的角色规则保持一致）
            status = (Article.Status.PUBLISHED
                      if article.author.is_staff else target_status)
            article.status = status
            article.save(update_fields=['status', 'updated_at'])   # 触发 post_save 信号
            changed_pks.append(article.pk)
            if status == Article.Status.PENDING:
                pending_cnt += 1
                ModerationLog.objects.create(
                    moderator=None, moderator_name='系统·定时任务',
                    action=ModerationLog.Action.SUBMIT, target_type='article',
                    article=article, target_title=article.title,
                    reason='定时发布时间已到（%s），因开启文章审核转入待审核'
                           % article.published_at.strftime('%Y-%m-%d %H:%M'))
            else:
                published_cnt += 1
        # 逐条 save() 虽已触发 post_save 缓存失效，这里再按 pk 精确失效一次，
        # 覆盖详情页片段缓存中的 prev/next 与相关文章；新建发布不影响全站顺序
        for pk in changed_pks:
            invalidate_article(pk)
        purge_prevnext()
        cache.delete('sidebar_data')
        cache.delete('footer_stats')
        logger.info('定时发布: 直接发布 %s 篇，转入待审核 %s 篇（审核开关=%s）',
                    published_cnt, pending_cnt, require_review)
        return ('已处理定时文章 %d 篇：直接发布 %d 篇，转入待审核 %d 篇'
                % (len(changed_pks), published_cnt, pending_cnt))
    except Exception as exc:
        logger.error('定时发布检查失败: %s', exc)
        return f'定时发布检查失败: {exc}'


# 迭代#86: send_comment_notification任务docstring
@shared_task
def send_comment_notification(comment_id):
    """68. 评论邮件通知任务：评论创建后异步邮件通知文章作者。

    - 若评论者就是文章作者本人，则不发邮件（自己评论自己无需通知）；
    - 邮件为 HTML 格式，含评论者昵称、内容预览、文章标题与查看链接；
    - 开发环境使用 console 邮件后端，仅打印到控制台，不真正发信。
    """
    from django.core.mail import send_mail
    from django.urls import reverse
    from .models import Comment
    comment = Comment.objects.select_related('article', 'user').filter(pk=comment_id).first()
    if not comment:
        return '评论不存在，跳过通知'
    article = comment.article
    # 作者本人评论自己的文章：不发通知
    if comment.user_id == article.author_id:
        return '评论者即作者，无需通知'
    author_email = getattr(article.author, 'email', '') or ''
    if not author_email:
        return '作者未填邮箱，跳过通知'
    # 内容预览（去 HTML 后前 80 字）
    import re
    preview = re.sub(r'<[^>]+>', '', comment.content or '')
    preview = re.sub(r'\s+', ' ', preview).strip()[:80]
    detail_url = reverse('article_detail', args=[article.pk])
    html = (
        f'<h2 style="color:#a06cd5;">🌸 萌语博客新评论提醒</h2>'
        f'<p>作者 {article.author.nickname or article.author.username} 你好呀~</p>'
        f'<p><b>{comment.user.nickname or comment.user.username}</b> '
        f'评论了你的文章《{article.title}》：</p>'
        f'<blockquote style="border-left:3px solid #ff8fb1;padding:8px 12px;background:#fdf2f8;">'
        f'{preview}…</blockquote>'
        f'<p><a href="http://127.0.0.1:8000{detail_url}">👉 点击查看并回复</a></p>'
    )
    # 迭代#87: tasks.py中邮件发送异常处理
    # 迭代#88: 邮件发送日志
    try:
        send_mail(
            subject=f'【萌语博客】{comment.user.nickname or comment.user.username} 评论了《{article.title}》',
            message=preview,
            from_email='萌语博客 <noreply@mengyu.blog>',
            recipient_list=[author_email],
            html_message=html,
            fail_silently=True,
        )
        logger.info('评论通知邮件已发送: article=%s', article.pk)
        return f'已通知作者：{article.title}'
    except Exception as exc:
        logger.error('评论通知邮件发送失败: %s', exc)
        return f'邮件发送失败: {exc}'

# ============================ 第3轮迭代#4: 批量/缓冲任务 ============================

@shared_task
def send_comment_digest():
    """批量评论通知摘要：把一段时间内多条评论合并为一封邮件发给文章作者。

    与 ``send_comment_notification``（每条评论一封）互补：本任务由 Celery beat
    定时触发，按文章作者聚合"自上次发送以来"的新评论，每封作者只收到一封摘要，
    显著降低邮件数量。全程 try/except，任何异常只记录日志，不影响主流程。

    Returns:
        str: 简要执行结果描述。
    """
    from django.core.cache import cache
    try:
        from .models import Comment, Article
        from django.core.mail import send_mail
        from django.conf import settings
        from django.utils.html import strip_tags

        # 上次发送截止时间（缓存键），首次运行回退为最近 15 分钟
        last_key = 'digest_last_run'
        cutoff = cache.get(last_key)
        now = timezone.now()
        qs = (Comment.objects.filter(is_approved=True, parent_comment__isnull=True)
              .select_related('article', 'article__author', 'user'))
        if cutoff:
            qs = qs.filter(created_at__gt=cutoff)
        else:
            qs = qs.filter(created_at__gte=now - timedelta(minutes=15))

        # 按文章作者分组（作者本人评论不通知）
        groups = {}
        for c in qs:
            owner = c.article.author
            if owner == c.user or not owner.email:
                continue
            groups.setdefault(owner, []).append(c)

        sent = 0
        site_name = getattr(settings, 'SITE_NAME', '本站')
        for owner, comments in groups.items():
            lines = [f'您在 {site_name} 的文章收到 {len(comments)} 条新评论：', '']
            for c in comments:
                snippet = strip_tags(c.content)[:80]
                who = c.user.nickname or c.user.username if c.user else '访客'
                lines.append(f'- 《{c.article.title}》 {who}: {snippet}')
            try:
                send_mail(
                    subject=f'[{site_name}] 您的文章有 {len(comments)} 条新评论',
                    message='\n'.join(lines),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[owner.email],
                    fail_silently=False,
                )
                sent += 1
            except Exception as mail_exc:  # noqa: BLE001
                logger.error('摘要邮件发送失败 %s: %s', owner, mail_exc)

        cache.set(last_key, now, 86400)
        logger.info('评论摘要邮件任务完成，发送 %d 封', sent)
        return f'digest sent={sent}, groups={len(groups)}'
    except Exception as exc:  # noqa: BLE001
        logger.error('评论摘要邮件任务异常: %s', exc)
        return f'digest error: {exc}'


@shared_task
def flush_buffered_views():
    """把内存累计的阅读量缓冲批量落库：``F('views') + delta``。

    前台可把单次阅读量累计到缓存键 ``viewbuf_{pk}``，由本任务定时统一 flush，
    从而把多次前台写库合并为一次批量写。当前缓存后端为 LocMemCache（进程内），
    仅当配置共享缓存（如 Redis）时跨进程可见；未命中缓冲时本任务安全空转，
    不丢失任何计数。全程 try/except。

    Returns:
        str: 简要执行结果描述。
    """
    from django.core.cache import cache
    from django.db.models import F
    try:
        from .models import Article
        flushed = 0
        deltas = {}
        # LocMemCache 内部字典可遍历；其他后端无该属性时安全跳过
        internal = getattr(cache, '_cache', None)
        if isinstance(internal, dict):
            for key, value in internal.items():
                if key.startswith('viewbuf_'):
                    pk = key[len('viewbuf_'):]
                    if str(pk).isdigit() and isinstance(value, int) and value > 0:
                        deltas[int(pk)] = value
        for pk, delta in deltas.items():
            Article.objects.filter(pk=pk).update(views=F('views') + delta)
            cache.delete(f'viewbuf_{pk}')
            flushed += 1
        logger.info('阅读量缓冲 flush 完成，更新文章 %d 篇', flushed)
        return f'flushed={flushed}'
    except Exception as exc:  # noqa: BLE001
        logger.error('阅读量 flush 任务异常: %s', exc)
        return f'flush error: {exc}'


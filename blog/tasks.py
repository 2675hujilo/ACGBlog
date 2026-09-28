"""
Celery 异步任务：
- save_access_log：异步保存访问日志；
- update_article_views：批量统计文章阅读量（定时任务）；
- clean_old_logs：定时清理过期访问日志；
- check_scheduled_articles：定时发布检查（56）；
- send_comment_notification：评论邮件通知文章作者（68）。
"""
#: 导入模块「logging」，供本文件后续使用
import logging
#: 从模块「datetime」导入所需对象
from datetime import timedelta

#: 从模块「celery」导入所需对象
from celery import shared_task

#: 定义变量「logger」，保存对应数据
logger = logging.getLogger(__name__)
#: 从模块「django.db」导入所需对象
from django.db import models
#: 从模块「django.utils」导入所需对象
from django.utils import timezone


# 迭代#75: save_access_log任务docstring
#: 装饰器：为下一个定义附加「shared_task」行为（权限、缓存、注册信号等）
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
    #: 从模块「django.core.exceptions」导入所需对象
    from django.core.exceptions import ValidationError
    #: 从模块「.models」导入所需对象
    from .models import AccessLog, User
    #: 尝试执行可能出错的代码
    try:
        #: 定义变量「user_id」，保存对应数据
        user_id = log_data.pop('user_id', None)
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        user = User.objects.filter(pk=user_id).first() if user_id else None
        # 代理可能给出 GenericIPAddressField 无法接受的内容，先校验，失败则置空
        #: 定义变量「ip」，保存对应数据
        ip = log_data.get('ip_address') or None
        #: 条件判断：条件成立时执行该分支
        if ip:
            #: 尝试执行可能出错的代码
            try:
                #: 调用「AccessLog._meta.get_field」执行相应逻辑
                AccessLog._meta.get_field('ip_address').run_validators(ip)
            #: 捕获并处理异常，避免程序中断
            except ValidationError:
                #: 定义变量「ip」，保存对应数据
                ip = None
        #: 该行执行对应逻辑（结合上下文理解）
        log_data['ip_address'] = ip
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        AccessLog.objects.create(user=user, **log_data)
        #: 返回结果并结束当前函数
        return 'saved'
    #: 捕获并处理异常，避免程序中断
    except Exception as exc:  # noqa: BLE001
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.error('访问日志异步入库失败: %s', exc, exc_info=True)
        #: 返回结果并结束当前函数
        return f'error: {exc}'


# 迭代#76: update_article_views任务docstring
#: 装饰器：为下一个定义附加「shared_task」行为（权限、缓存、注册信号等）
@shared_task
def update_article_views():
    """批量统计任务：汇总文章阅读数据。

    Returns:
        str: 统计结果描述字符串。
    """
    # 迭代#77: tasks.py中阅读量统计异常处理
    # 迭代#78: 阅读量统计日志
    #: 尝试执行可能出错的代码
    try:
        #: 从模块「.models」导入所需对象
        from .models import Article
        #: 使用聚合函数做统计查询
        total = Article.objects.aggregate(total_views=models.Sum('views'))['total_views'] or 0
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        article_count = Article.objects.count()
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.info('阅读量统计: %s 篇文章, 总量 %s', article_count, total)
        #: 返回结果并结束当前函数
        return f'已统计 {article_count} 篇文章，总阅读量 {total}'
    #: 捕获并处理异常，避免程序中断
    except Exception as exc:
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.error('阅读量统计失败: %s', exc)
        #: 返回结果并结束当前函数
        return f'统计失败: {exc}'


# 迭代#79: clean_old_logs任务docstring
#: 装饰器：为下一个定义附加「shared_task」行为（权限、缓存、注册信号等）
@shared_task
def clean_old_logs(days=90):
    """定时清理任务：删除指定天数之前的访问日志。

    Args:
        days: 保留最近多少天的日志，默认90天。

    Returns:
        str: 清理结果描述。
    """
    #: 从模块「.models」导入所需对象
    from .models import AccessLog
    # 迭代#80: tasks.py中日志清理异常处理
    # 迭代#81: 日志清理执行日志
    #: 尝试执行可能出错的代码
    try:
        #: 获取当前时间（时区感知），统一时间口径
        cutoff = timezone.now() - timedelta(days=days)
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        deleted, _ = AccessLog.objects.filter(created_at__lt=cutoff).delete()
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.info('日志清理: 删除 %s 条', deleted)
        #: 返回结果并结束当前函数
        return f'已清理 {deleted} 条 {days} 天前的访问日志'
    #: 捕获并处理异常，避免程序中断
    except Exception as exc:
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.error('日志清理失败: %s', exc)
        #: 返回结果并结束当前函数
        return f'日志清理失败: {exc}'


# ============================ 访问日志兜底队列自动补齐 ============================

#: 装饰器：为下一个定义附加「shared_task」行为（权限、缓存、注册信号等）
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
    #: 从模块「.services.access_log_service」导入所需对象
    from .services.access_log_service import drain_fallback
    #: 尝试执行可能出错的代码
    try:
        #: 定义变量「result」，保存对应数据
        result = drain_fallback(batch=batch, max_batches=max_batches)
        #: 条件判断：条件成立时执行该分支
        if result['error']:
            # Redis 仍不可用：不算任务失败，等下一轮再试（中间件此时走同步兜底）
            #: 记录日志，便于排查（勿记录密码等敏感信息）
            logger.warning('访问日志兜底队列消费失败（Redis 不可用）: %s', result['error'])
            #: 返回结果并结束当前函数
            return f'兜底队列消费跳过: {result["error"]}'
        #: 条件判断：条件成立时执行该分支
        if result['ok'] or result['bad']:
            #: 记录日志，便于排查（勿记录密码等敏感信息）
            logger.info('访问日志兜底队列补齐: 入库 %s 条，坏数据 %s 条，剩余 %s 条',
                        #: 该行执行对应逻辑（结合上下文理解）
                        result['ok'], result['bad'], result['remaining'])
        #: 返回结果并结束当前函数
        return ('兜底队列补齐: ok=%s bad=%s remaining=%s'
                #: 该行执行对应逻辑（结合上下文理解）
                % (result['ok'], result['bad'], result['remaining']))
    #: 捕获并处理异常，避免程序中断
    except Exception as exc:  # noqa: BLE001
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.error('访问日志兜底队列任务异常: %s', exc)
        #: 返回结果并结束当前函数
        return f'兜底队列任务异常: {exc}'


# 迭代#82: check_scheduled_articles任务docstring
#: 装饰器：为下一个定义附加「shared_task」行为（权限、缓存、注册信号等）
@shared_task
def check_scheduled_articles():
    """56 + Bug8/Bug9. 定时发布检查任务（每分钟执行一次）。

    Bug8/Bug9 修复要点（Bug 单原话：定时发布文章异常，若开启了审核定时发布后出现
    draft；如果关闭审核，会直接发布；到时间后文章应该是待审核或者已发布，
    而不是草稿状态）：

    - 开启「普通作者新文章需审核」时：到点的定时文章 **不得直接发布**，而是
      流转为 ``PENDING``（待审核）并入队内容审核页；管理员通过后才真正发布；
    - 关闭审核时：自动置为 ``PUBLISHED``（直接发布）；
    - 管理员（staff）发文始终直接发布（与 article_new 的角色规则一致）；
    - 每条文章改用 ``save()`` 逐个流转，确保 ``post_save`` 信号（缓存失效、
      搜索索引刷新等）照常触发，不再用 bulk ``update()`` 绕过信号；
    - 同时写入 ``ModerationLog`` 审核历史。

    实际流转逻辑已收敛到 ``blog.scheduled_publishing.process_due_articles()``，
    与请求侧兜底扫描器 ``maybe_sweep_due_articles()`` 共用同一实现，避免逻辑漂移。

    Returns:
        str: 简要执行结果描述。
    """
    #: 从模块「.services.scheduled_publishing」导入所需对象
    from .services.scheduled_publishing import process_due_articles
    #: 尝试执行可能出错的代码
    try:
        #: 定义变量「result」，保存对应数据
        result = process_due_articles()
        #: 返回结果并结束当前函数
        return ('已处理定时文章 %d 篇：直接发布 %d 篇，转入待审核 %d 篇'
                #: 该行执行对应逻辑（结合上下文理解）
                % (len(result['pks']), result['published'], result['pending']))
    #: 捕获并处理异常，避免程序中断
    except Exception as exc:  # noqa: BLE001
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.error('定时发布检查失败: %s', exc)
        #: 返回结果并结束当前函数
        return f'定时发布检查失败: {exc}'


# 迭代#86: send_comment_notification任务docstring
#: 装饰器：为下一个定义附加「shared_task」行为（权限、缓存、注册信号等）
@shared_task
def send_comment_notification(comment_id):
    """68. 评论邮件通知任务：评论创建后异步邮件通知文章作者。

    - 若评论者就是文章作者本人，则不发邮件（自己评论自己无需通知）；
    - 邮件为 HTML 格式，含评论者昵称、内容预览、文章标题与查看链接；
    - 开发环境使用 console 邮件后端，仅打印到控制台，不真正发信。
    """
    #: 从模块「django.core.mail」导入所需对象
    from django.core.mail import send_mail
    #: 从模块「django.urls」导入所需对象
    from django.urls import reverse
    #: 从模块「.models」导入所需对象
    from .models import Comment
    #: ORM 预加载关联，减少 N+1 查询提升性能
    comment = Comment.objects.select_related('article', 'user').filter(pk=comment_id).first()
    #: 条件判断：条件成立时执行该分支
    if not comment:
        #: 返回结果并结束当前函数
        return '评论不存在，跳过通知'
    #: 定义变量「article」，保存对应数据
    article = comment.article
    # 作者本人评论自己的文章：不发通知
    #: 条件判断：条件成立时执行该分支
    if comment.user_id == article.author_id:
        #: 返回结果并结束当前函数
        return '评论者即作者，无需通知'
    #: 定义变量「author_email」，保存对应数据
    author_email = getattr(article.author, 'email', '') or ''
    #: 条件判断：条件成立时执行该分支
    if not author_email:
        #: 返回结果并结束当前函数
        return '作者未填邮箱，跳过通知'
    # 内容预览（去 HTML 后前 80 字）
    #: 导入模块「re」，供本文件后续使用
    import re
    #: 定义变量「preview」，保存对应数据
    preview = re.sub(r'<[^>]+>', '', comment.content or '')
    #: 定义变量「preview」，保存对应数据
    preview = re.sub(r'\s+', ' ', preview).strip()[:80]
    #: 根据路由名反查 URL，避免硬编码路径
    detail_url = reverse('article_detail', args=[article.pk])
    #: 定义变量「html」，保存对应数据（集合/元组）
    html = (
        #: 该行执行对应逻辑（结合上下文理解）
        f'<h2 style="color:#a06cd5;">🌸 萌语博客新评论提醒</h2>'
        #: 该行执行对应逻辑（结合上下文理解）
        f'<p>作者 {article.author.nickname or article.author.username} 你好呀~</p>'
        #: 该行执行对应逻辑（结合上下文理解）
        f'<p><b>{comment.user.nickname or comment.user.username}</b> '
        #: 该行执行对应逻辑（结合上下文理解）
        f'评论了你的文章《{article.title}》：</p>'
        #: 该行执行对应逻辑（结合上下文理解）
        f'<blockquote style="border-left:3px solid #ff8fb1;padding:8px 12px;background:#fdf2f8;">'
        #: 该行执行对应逻辑（结合上下文理解）
        f'{preview}…</blockquote>'
        #: 该行执行对应逻辑（结合上下文理解）
        f'<p><a href="http://127.0.0.1:8000{detail_url}">👉 点击查看并回复</a></p>'
    #: 该行执行对应逻辑（结合上下文理解）
    )
    # 迭代#87: tasks.py中邮件发送异常处理
    # 迭代#88: 邮件发送日志
    #: 尝试执行可能出错的代码
    try:
        #: 调用「send_mail」执行相应逻辑
        send_mail(
            #: 定义变量「subject」，保存对应数据
            subject=f'【萌语博客】{comment.user.nickname or comment.user.username} 评论了《{article.title}》',
            #: 定义变量「message」，保存对应数据
            message=preview,
            #: 定义变量「from_email」，保存对应数据
            from_email='萌语博客 <noreply@mengyu.blog>',
            #: 定义变量「recipient_list」，保存对应数据（集合/元组）
            recipient_list=[author_email],
            #: 定义变量「html_message」，保存对应数据
            html_message=html,
            #: 定义变量「fail_silently」，保存对应数据
            fail_silently=True,
        #: 该行执行对应逻辑（结合上下文理解）
        )
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.info('评论通知邮件已发送: article=%s', article.pk)
        #: 返回结果并结束当前函数
        return f'已通知作者：{article.title}'
    #: 捕获并处理异常，避免程序中断
    except Exception as exc:
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.error('评论通知邮件发送失败: %s', exc)
        #: 返回结果并结束当前函数
        return f'邮件发送失败: {exc}'

# ============================ 第3轮迭代#4: 批量/缓冲任务 ============================

#: 装饰器：为下一个定义附加「shared_task」行为（权限、缓存、注册信号等）
@shared_task
def send_comment_digest():
    """批量评论通知摘要：把一段时间内多条评论合并为一封邮件发给文章作者。

    与 ``send_comment_notification``（每条评论一封）互补：本任务由 Celery beat
    定时触发，按文章作者聚合"自上次发送以来"的新评论，每封作者只收到一封摘要，
    显著降低邮件数量。全程 try/except，任何异常只记录日志，不影响主流程。

    Returns:
        str: 简要执行结果描述。
    """
    #: 从模块「django.core.cache」导入所需对象
    from django.core.cache import cache
    #: 尝试执行可能出错的代码
    try:
        #: 从模块「.models」导入所需对象
        from .models import Comment, Article
        #: 从模块「django.core.mail」导入所需对象
        from django.core.mail import send_mail
        #: 从模块「django.conf」导入所需对象
        from django.conf import settings
        #: 从模块「django.utils.html」导入所需对象
        from django.utils.html import strip_tags

        # 上次发送截止时间（缓存键），首次运行回退为最近 15 分钟
        #: 定义变量「last_key」，保存对应数据
        last_key = 'digest_last_run'
        #: 读写缓存，减轻数据库压力，注意键与过期时间
        cutoff = cache.get(last_key)
        #: 获取当前时间（时区感知），统一时间口径
        now = timezone.now()
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        qs = (Comment.objects.filter(is_approved=True, parent_comment__isnull=True)
              #: ORM 预加载关联，减少 N+1 查询提升性能
              .select_related('article', 'article__author', 'user'))
        #: 条件判断：条件成立时执行该分支
        if cutoff:
            #: 定义变量「qs」，保存对应数据
            qs = qs.filter(created_at__gt=cutoff)
        #: 以上条件均不成立时的兜底分支
        else:
            #: 定义变量「qs」，保存对应数据
            qs = qs.filter(created_at__gte=now - timedelta(minutes=15))

        # 按文章作者分组（作者本人评论不通知）
        #: 定义变量「groups」，保存对应数据
        groups = {}
        #: 循环遍历，逐个处理元素
        for c in qs:
            #: 定义变量「owner」，保存对应数据
            owner = c.article.author
            #: 条件判断：条件成立时执行该分支
            if owner == c.user or not owner.email:
                #: 跳过本次进入下一次迭代
                continue
            #: 调用「groups.setdefault」执行相应逻辑
            groups.setdefault(owner, []).append(c)

        #: 定义变量「sent」，保存对应数据
        sent = 0
        #: 定义变量「site_name」，保存对应数据
        site_name = getattr(settings, 'SITE_NAME', '本站')
        #: 循环遍历，逐个处理元素
        for owner, comments in groups.items():
            #: 定义变量「lines」，保存对应数据（集合/元组）
            lines = [f'您在 {site_name} 的文章收到 {len(comments)} 条新评论：', '']
            #: 循环遍历，逐个处理元素
            for c in comments:
                #: 定义变量「snippet」，保存对应数据
                snippet = strip_tags(c.content)[:80]
                #: 定义变量「who」，保存对应数据
                who = c.user.nickname or c.user.username if c.user else '访客'
                #: 调用「lines.append」执行相应逻辑
                lines.append(f'- 《{c.article.title}》 {who}: {snippet}')
            #: 尝试执行可能出错的代码
            try:
                #: 调用「send_mail」执行相应逻辑
                send_mail(
                    #: 定义变量「subject」，保存对应数据
                    subject=f'[{site_name}] 您的文章有 {len(comments)} 条新评论',
                    #: 定义变量「message」，保存对应数据
                    message='\n'.join(lines),
                    #: 定义变量「from_email」，保存对应数据
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    #: 定义变量「recipient_list」，保存对应数据（集合/元组）
                    recipient_list=[owner.email],
                    #: 定义变量「fail_silently」，保存对应数据
                    fail_silently=False,
                #: 该行执行对应逻辑（结合上下文理解）
                )
                #: 该行执行对应逻辑（结合上下文理解）
                sent += 1
            #: 捕获并处理异常，避免程序中断
            except Exception as mail_exc:  # noqa: BLE001
                #: 记录日志，便于排查（勿记录密码等敏感信息）
                logger.error('摘要邮件发送失败 %s: %s', owner, mail_exc)

        #: 读写缓存，减轻数据库压力，注意键与过期时间
        cache.set(last_key, now, 86400)
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.info('评论摘要邮件任务完成，发送 %d 封', sent)
        #: 返回结果并结束当前函数
        return f'digest sent={sent}, groups={len(groups)}'
    #: 捕获并处理异常，避免程序中断
    except Exception as exc:  # noqa: BLE001
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.error('评论摘要邮件任务异常: %s', exc)
        #: 返回结果并结束当前函数
        return f'digest error: {exc}'


#: 装饰器：为下一个定义附加「shared_task」行为（权限、缓存、注册信号等）
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
    #: 从模块「django.core.cache」导入所需对象
    from django.core.cache import cache
    #: 从模块「django.db.models」导入所需对象
    from django.db.models import F
    #: 尝试执行可能出错的代码
    try:
        #: 从模块「.models」导入所需对象
        from .models import Article
        #: 定义变量「flushed」，保存对应数据
        flushed = 0
        #: 定义变量「deltas」，保存对应数据
        deltas = {}
        # LocMemCache 内部字典可遍历；其他后端无该属性时安全跳过
        #: 定义变量「internal」，保存对应数据
        internal = getattr(cache, '_cache', None)
        #: 条件判断：条件成立时执行该分支
        if isinstance(internal, dict):
            #: 循环遍历，逐个处理元素
            for key, value in internal.items():
                #: 条件判断：条件成立时执行该分支
                if key.startswith('viewbuf_'):
                    #: 定义变量「pk」，保存对应数据
                    pk = key[len('viewbuf_'):]
                    #: 条件判断：条件成立时执行该分支
                    if str(pk).isdigit() and isinstance(value, int) and value > 0:
                        #: 该行执行对应逻辑（结合上下文理解）
                        deltas[int(pk)] = value
        #: 循环遍历，逐个处理元素
        for pk, delta in deltas.items():
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            Article.objects.filter(pk=pk).update(views=F('views') + delta)
            #: 读写缓存，减轻数据库压力，注意键与过期时间
            cache.delete(f'viewbuf_{pk}')
            #: 该行执行对应逻辑（结合上下文理解）
            flushed += 1
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.info('阅读量缓冲 flush 完成，更新文章 %d 篇', flushed)
        #: 返回结果并结束当前函数
        return f'flushed={flushed}'
    #: 捕获并处理异常，避免程序中断
    except Exception as exc:  # noqa: BLE001
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.error('阅读量 flush 任务异常: %s', exc)
        #: 返回结果并结束当前函数
        return f'flush error: {exc}'


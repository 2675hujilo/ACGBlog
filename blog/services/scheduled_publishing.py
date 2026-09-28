# -*- coding: utf-8 -*-
"""定时投稿状态流转（Bug9-1 / Bug9-2 的统一实现）。

背景（Bug 单原文）
------------------
- 「定时但是未发布的文章只要作者和管理员能看到，而不是 404」；
- 「到时间后文章应该是待审核或者已发布，而不是草稿状态」。

设计
----
本模块把「到点定时文章的状态流转」收敛成**唯一实现**，供三方复用，避免逻辑漂移：

1. ``blog.tasks.check_scheduled_articles`` —— Celery beat 每分钟触发（推荐路径）；
2. ``maybe_sweep_due_articles()`` —— Web 请求侧的**兜底扫描器**：当部署环境没有
   启动 Celery beat（本地开发常见）时，仍能保证到点文章在首个访问请求时被流转，
   不会长期停留在「草稿」状态；
3. ``process_due_articles()`` —— 供管理命令 / 测试直接调用。

流转规则（与 ``ModerationSettings.require_article_review`` 联动）
----------------------------------------------------------------
::

    草稿 + 已到发布时间
        ├─ 开启「普通作者新文章需审核」→ PENDING（待审核，管理员通过后发布）
        └─ 关闭审核                     → PUBLISHED（直接发布）
    管理员（staff）发文                 → 始终 PUBLISHED（与 article_new 角色规则一致）

每次流转都走 ``article.save()``，因此 ``post_save`` 信号（详情页片段缓存失效、
搜索索引、徽章检查等）照常触发；同时写入 ``ModerationLog`` 审核历史
（仅转入待审核时），管理员可在「审核历史」看到「定时发布时间已到…转入待审核」。
"""
#: 导入模块「logging」，供本文件后续使用
import logging

#: 从模块「django.conf」导入所需对象
from django.conf import settings
#: 从模块「django.core.cache」导入所需对象
from django.core.cache import cache
#: 从模块「django.utils」导入所需对象
from django.utils import timezone

#: 定义变量「logger」，保存对应数据
logger = logging.getLogger(__name__)

#: 兜底扫描器的最小间隔（秒）：集中在 settings.SCHEDULED_SWEEP_INTERVAL，
#: 同一进程内两次扫描至少间隔这么久，避免每个请求都查库（高并发下退化）。
SWEEP_INTERVAL = settings.SCHEDULED_SWEEP_INTERVAL
#: 兜底扫描器的分布式锁 key（LocMem 下即进程内，Redis 下为全局，二者语义都正确）
SWEEP_LOCK_KEY = 'scheduled_sweep_lock'
#: 单轮最多处理的文章数：集中在 settings.SCHEDULED_MAX_PER_ROUND，
#: 防止异常堆积（如长时间停机）时一次性处理过多。
MAX_PER_ROUND = settings.SCHEDULED_MAX_PER_ROUND


def process_due_articles(now=None, limit=MAX_PER_ROUND):
    """把所有「已到发布时间」的草稿文章按审核开关流转，并返回统计结果。

    Args:
        now: 参考时间，默认取 ``timezone.now()``（便于测试注入固定时间）。
        limit: 单轮最多处理条数。

    Returns:
        dict: {'published': 直接发布数, 'pending': 转入待审核数, 'pks': 受影响主键列表}
    """
    #: 从模块「..utils.cache_keys」导入所需对象
    from ..utils.cache_keys import invalidate_article, purge_prevnext
    #: 从模块「..models」导入所需对象
    from ..models import Article, ModerationLog, ModerationSettings

    #: 获取当前时间（时区感知），统一时间口径
    now = now or timezone.now()
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    due = list(Article.objects.filter(
        #: 定义变量「status」，保存对应数据
        status=Article.Status.DRAFT,             # 只处理草稿：待审核由管理员处理
        #: 定义变量「is_deleted」，保存对应数据
        is_deleted=False,                        # 回收站内容不参与自动流转
        #: 定义变量「published_at__isnull」，保存对应数据
        published_at__isnull=False,              # 必须设置了定时时间
        #: 定义变量「published_at__lte」，保存对应数据
        published_at__lte=now,                   # 且时间已到
    #: ORM 预加载关联，减少 N+1 查询提升性能
    ).select_related('author').order_by('published_at')[:limit])

    #: 定义变量「result」，保存对应数据
    result = {'published': 0, 'pending': 0, 'pks': []}
    #: 条件判断：条件成立时执行该分支
    if not due:
        #: 返回结果并结束当前函数
        return result

    # 是否开启文章审核：决定「到点」后进入 PENDING 还是直接 PUBLISHED
    #: 定义变量「require_review」，保存对应数据
    require_review = ModerationSettings.load().require_article_review
    #: 循环遍历，逐个处理元素
    for article in due:
        # 管理员发文始终可直接发布（与 article_new 的角色规则保持一致）
        #: 定义变量「target」，保存对应数据（集合/元组）
        target = (Article.Status.PUBLISHED
                  #: 条件判断：条件成立时执行该分支
                  if article.author.is_staff or not require_review
                  #: 以上条件均不成立时的兜底分支
                  else Article.Status.PENDING)
        #: 定义实例/类属性「article.status」，保存对应数据
        article.status = target
        # 逐条 save() 而非 bulk update()：确保 post_save 信号（缓存失效等）照常触发
        #: 调用「article.save」执行相应逻辑
        article.save(update_fields=['status', 'updated_at'])
        #: 该行执行对应逻辑（结合上下文理解）
        result['pks'].append(article.pk)
        #: 条件判断：条件成立时执行该分支
        if target == Article.Status.PENDING:
            #: 该行执行对应逻辑（结合上下文理解）
            result['pending'] += 1
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            ModerationLog.objects.create(
                #: 定义变量「moderator」，保存对应数据
                moderator=None, moderator_name='系统·定时任务',
                #: 定义变量「action」，保存对应数据
                action=ModerationLog.Action.SUBMIT, target_type='article',
                #: 定义变量「article」，保存对应数据
                article=article, target_title=article.title,
                #: 定义变量「reason」，保存对应数据
                reason='定时发布时间已到（%s），因开启文章审核转入待审核'
                       #: 该行执行对应逻辑（结合上下文理解）
                       % article.published_at.strftime('%Y-%m-%d %H:%M'))
        #: 以上条件均不成立时的兜底分支
        else:
            #: 该行执行对应逻辑（结合上下文理解）
            result['published'] += 1

    # 逐条 save() 已触发 post_save 缓存失效；这里再按 pk 精确失效一次，
    # 覆盖详情页片段缓存中的 prev/next 与相关文章等派生数据。
    #: 循环遍历，逐个处理元素
    for pk in result['pks']:
        #: 尝试执行可能出错的代码
        try:
            #: 调用「invalidate_article」执行相应逻辑
            invalidate_article(pk)
        #: 捕获并处理异常，避免程序中断
        except Exception:  # noqa: BLE001 缓存失效失败不影响状态流转结果
            #: 占位语句：此处暂不需要实现
            pass
    #: 尝试执行可能出错的代码
    try:
        #: 调用「purge_prevnext」执行相应逻辑
        purge_prevnext()                      # 新发布文章会改变全站上一篇/下一篇
        #: 读写缓存，减轻数据库压力，注意键与过期时间
        cache.delete('sidebar_data')
        #: 读写缓存，减轻数据库压力，注意键与过期时间
        cache.delete('footer_stats')
        #: 读写缓存，减轻数据库压力，注意键与过期时间
        cache.delete('hot_articles')
    #: 捕获并处理异常，避免程序中断
    except Exception:  # noqa: BLE001
        #: 占位语句：此处暂不需要实现
        pass
    #: 记录日志，便于排查（勿记录密码等敏感信息）
    logger.info('定时投稿流转：直接发布 %s 篇，转入待审核 %s 篇（审核开关=%s）',
                #: 该行执行对应逻辑（结合上下文理解）
                result['published'], result['pending'], require_review)
    #: 返回结果并结束当前函数
    return result


def maybe_sweep_due_articles():
    """请求侧兜底扫描器：限频 + 缓存锁，保证并发下最多一个线程真正扫库。

    使用场景：部署环境未启动 Celery beat 时，定时文章仍能按时流转，
    不会因为「没人跑定时任务」而长期停留在草稿状态（Bug9-2 的直接诱因）。

    Returns:
        dict | None: 真正执行了扫描则返回 ``process_due_articles`` 的结果，
        被限频 / 未抢到锁时返回 None。
    """
    # 缓存锁：add() 原子操作，只有第一个调用者拿到锁；
    # TTL=SWEEP_INTERVAL 秒，天然实现「最小扫描间隔」。
    #: 尝试执行可能出错的代码
    try:
        #: 条件判断：条件成立时执行该分支
        if not cache.add(SWEEP_LOCK_KEY, 1, SWEEP_INTERVAL):
            #: 返回结果并结束当前函数
            return None
    #: 捕获并处理异常，避免程序中断
    except Exception:  # noqa: BLE001 缓存不可用时退化为不做兜底扫描，避免每次请求都扫库
        #: 返回结果并结束当前函数
        return None
    #: 尝试执行可能出错的代码
    try:
        #: 返回结果并结束当前函数
        return process_due_articles()
    #: 捕获并处理异常，避免程序中断
    except Exception as exc:  # noqa: BLE001 兜底扫描失败绝不能影响页面渲染
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.warning('定时投稿兜底扫描失败: %s', exc)
        #: 返回结果并结束当前函数
        return None

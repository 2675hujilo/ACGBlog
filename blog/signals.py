"""
第2轮迭代#41-#50: 模型信号集中注册模块。

把跨模型的 pre_save / post_save / pre_delete / post_delete / m2m_changed
信号从 models.py 中分离到本文件，由 ``blog.apps.BlogConfig.ready()`` 导入，
避免 models.py 尾部过长，并保证 App 启动时信号处理器被正确挂载。

所有信号均做异常兜底：信号内部失败仅记录日志，绝不阻断主请求 / 保存流程。
"""
import logging
import re

from django.core.cache import cache
from django.db.models.signals import (m2m_changed, post_delete, post_save,
                                     pre_delete, pre_save)
from django.dispatch import receiver
from django.contrib.auth.hashers import identify_hasher, make_password

from .cache_keys import invalidate_article, purge_prevnext
from .models import Article, Badge, Comment, Notification, UserBadge

logger = logging.getLogger(__name__)


# 第2轮迭代#41: pre_save 标题截断信号
@receiver(pre_save, sender=Article)
def _truncate_article_title(sender, instance, **kwargs):
    """保存前把超长标题截断到 200 字，规避 MySQL "Data too long" 错误。"""
    if instance.title and len(instance.title) > 200:
        instance.title = instance.title[:200]


# 第2轮迭代#42: pre_save 摘要自动生成信号
@receiver(pre_save, sender=Article)
def _auto_excerpt_on_save(sender, instance, **kwargs):
    """保存前若未手写摘要，则从富文本正文剥离 HTML 后截取前 180 字填入 excerpt_field。"""
    if instance.excerpt_field and instance.excerpt_field.strip():
        return  # 已有手写摘要，不覆盖
    text = re.sub(r'<[^>]+>', '', instance.content or '')
    text = re.sub(r'\s+', ' ', text).strip()
    if text:
        instance.excerpt_field = text[:180]


# 第2轮迭代#43: post_save 评论计数更新信号
@receiver(post_save, sender=Comment)
def _recalc_article_comment_count(sender, instance, created, **kwargs):
    """评论保存后，重算所属文章已通过审核且未软删除的评论数 comment_count。

    与 README 6.2 口径一致：只计「存活评论」（is_approved=True 且 is_deleted=False），
    软删除（撤回 / 审核隐藏）不占位，避免 F±1 / 信号叠加导致计数漂移。
    """
    try:
        cnt = Comment.objects.filter(
            article_id=instance.article_id,
            is_approved=True, is_deleted=False).count()
        Article.objects.filter(pk=instance.article_id).update(comment_count=cnt)
    except Exception as exc:  # 信号失败不得阻断主流程
        logger.warning('评论计数更新失败: %s', exc)


# 第2轮迭代#44: post_save 文章缓存清除信号
@receiver(post_save, sender=Article)
def _invalidate_article_cache(sender, instance, created, **kwargs):
    """文章保存后失效侧边栏 / 页脚统计 / 热门文章缓存，并清详情页片段缓存。

    - 详情页片段（article / comment_tree / related / related_weighted /
      prevnext / missing）由 invalidate_article() 统一失效，覆盖草稿→待审核→
      发布、编辑、软删除、恢复等全部状态变化；
    - 新建文章会使全站「上一篇 / 下一篇」变化，额外 purge_prevnext()。
    """
    try:
        invalidate_article(instance.pk)
        if created:
            purge_prevnext()
        cache.delete('sidebar_data')
        cache.delete('footer_stats')
        cache.delete('hot_articles')
    except Exception as exc:
        logger.debug('文章缓存清除失败: %s', exc)


# 第2轮迭代#45: pre_delete 关联清理信号
@receiver(pre_delete, sender=Article)
def _cleanup_before_article_delete(sender, instance, **kwargs):
    """文章删除前清除其详情页片段缓存与侧边栏缓存（关联行由数据库级联自动清理）。"""
    try:
        invalidate_article(instance.pk)
        purge_prevnext()
        cache.delete('sidebar_data')
    except Exception as exc:
        logger.debug('文章删除前清理失败: %s', exc)


# 第2轮迭代#46: post_delete 缓存清除信号
@receiver(post_delete, sender=Article)
def _invalidate_cache_after_article_delete(sender, instance, **kwargs):
    """文章删除后失效热门文章与页脚统计缓存，并清空全站 prev/next 片段。"""
    try:
        purge_prevnext()
        cache.delete('hot_articles')
        cache.delete('footer_stats')
    except Exception as exc:
        logger.debug('文章删除后缓存清理失败: %s', exc)


# 详情页评论树失效：评论新增 / 撤回（软删）/ 恢复 / 审核隐藏 / 硬删 全部经由此处
@receiver(post_save, sender=Comment)
def _invalidate_detail_on_comment_save(sender, instance, **kwargs):
    """评论保存（含软删除 / 恢复 / 审核变更）后失效所属文章的评论树片段缓存。"""
    if not instance.article_id:
        return
    try:
        invalidate_article(instance.article_id)
    except Exception as exc:
        logger.debug('评论保存缓存清理失败: %s', exc)


@receiver(post_delete, sender=Comment)
def _invalidate_detail_on_comment_delete(sender, instance, **kwargs):
    """评论物理删除后失效所属文章的评论树片段缓存。"""
    if not getattr(instance, 'article_id', None):
        return
    try:
        invalidate_article(instance.article_id)
    except Exception as exc:
        logger.debug('评论删除缓存清理失败: %s', exc)


# 第2轮迭代#47: m2m_changed 标签更新信号
@receiver(m2m_changed, sender=Article.tags.through)
def _on_article_tags_changed(sender, instance, action, **kwargs):
    """文章标签多对多增删/清空后，失效标签云与侧边栏缓存。"""
    if action in ('post_add', 'post_remove', 'post_clear'):
        try:
            cache.delete('tag_cloud')
            cache.delete('sidebar_data')
        except Exception as exc:
            logger.debug('标签变更缓存清理失败: %s', exc)


# 第2轮迭代#48: pre_save 时间戳更新信号
@receiver(pre_save, sender=Article)
def _touch_article_save_count(sender, instance, **kwargs):
    """保存前累加 transient 保存计数（不落库），便于调试追踪保存次数。"""
    instance._save_touch_count = getattr(instance, '_save_touch_count', 0) + 1


# 第2轮迭代#49: post_save 索引更新信号
@receiver(post_save, sender=Article)
def _refresh_search_index(sender, instance, created, **kwargs):
    """文章保存后刷新搜索索引钩子（当前为缓存失效占位，便于后续接入全文检索）。"""
    try:
        cache.delete('search_index_article')
    except Exception as exc:
        logger.debug('搜索索引刷新失败: %s', exc)


# 第2轮迭代#50: pre_save 密码哈希信号
@receiver(pre_save, sender=Article)
def _hash_article_password(sender, instance, **kwargs):
    """保存前若 article.password 为明文则自动哈希；已是哈希串则原样保留（避免双重哈希）。"""
    raw = instance.password or ''
    if not raw:
        return
    try:
        identify_hasher(raw)  # 能识别说明已是 Django 哈希格式
    except (ValueError, TypeError):
        instance.password = make_password(raw)


# ============================ 第5轮 F8/F10: 通知与徽章信号 ============================
from django.utils import timezone as _tz


@receiver(post_save, sender=Comment)
def _notify_on_comment_created(sender, instance, created, **kwargs):
    """评论创建后：给文章作者发回复通知、检测@提及、触发徽章检查。"""
    if not created:
        return
    try:
        article = instance.article
        commenter = instance.user
        # 回复通知：评论作者不是文章作者本人时，通知文章作者
        if commenter.pk != article.author_id:
            Notification.objects.get_or_create(
                user=article.author, type=Notification.Type.REPLY,
                title=f'{commenter} 评论了你的文章《{article.title[:30]}》',
                defaults={
                    'content': re.sub(r'<[^>]+>', '', instance.content or '')[:200],
                    'related_url': article.get_absolute_url() + f'#comment-{instance.pk}',
                },
            )
        # @提及检测：评论正文里 @用户名
        mentioned = re.findall(r'@([A-Za-z0-9_]+)', instance.content or '')
        for uname in set(mentioned):
            from .models import User as _U
            mu = _U.objects.filter(username=uname).first()
            if mu and mu.pk != commenter.pk:
                Notification.objects.get_or_create(
                    user=mu, type=Notification.Type.MENTION,
                    title=f'{commenter} 在评论中提到了你',
                    defaults={
                        'content': re.sub(r'<[^>]+>', '', instance.content or '')[:200],
                        'related_url': article.get_absolute_url(),
                    },
                )
        # 触发评论者徽章检查
        from .views import check_and_award_badges
        check_and_award_badges(commenter)
    except Exception as exc:
        logger.warning('评论通知信号失败: %s', exc)


@receiver(post_save, sender=Article)
def _badge_check_on_article_created(sender, instance, created, **kwargs):
    """文章发布后触发作者徽章检查。"""
    if not created:
        return
    try:
        from .views import check_and_award_badges
        check_and_award_badges(instance.author)
    except Exception as exc:
        logger.warning('文章徽章信号失败: %s', exc)
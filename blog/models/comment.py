# -*- coding: utf-8 -*-
"""
评论领域模型 —— 多级评论、表情反应与评论举报。

本文件从原 ``blog/models.py`` 拆出，含：

- :class:`Comment`：文章评论，支持自关联 ``parent_comment`` 形成楼中楼嵌套，
  含审核开关、配图、长评论折叠、举报标记与软删除；
- :class:`CommentReaction`：评论的表情反应（👍/❤️/😂/😮/😢/🔥）；
- :class:`CommentReport`：评论举报记录。

表名（blog_comment 等）与拆分前一致，不产生数据库结构变更；跨文件外键以字符串
引用。

维护注意点
----------
1. 评论内容在视图层用 bleach 净化为少量安全行内标签，模型只存净化后 HTML；
2. 是否需审核由 :class:`blog.models.ModerationSettings` 的 require_comment_review
   决定，新评论 is_approved 随之取值；评论写操作不可绕过信号（计数重算、缓存
   失效、通知）；
3. 评论删除为软删除（is_deleted/deleted_at），文章 comment_count 由信号按存活
   评论重算；
4. 楼层号 floor_number 仅作兜底，列表场景由视图批量计算注入，避免 N+1。
"""
from django.db import models


class Comment(models.Model):
    """文章评论：楼中楼嵌套 + 审核 + 配图 + 软删除。"""

    article = models.ForeignKey(
        'Article', on_delete=models.CASCADE,
        related_name='comments', verbose_name='文章')
    user = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='comments', verbose_name='评论人')
    content = models.TextField(verbose_name='评论内容')
    # 父评论自关联：空表示顶级评论，删除父评论级联删除其回复
    parent_comment = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.CASCADE,
        related_name='replies', verbose_name='父评论（支持回复嵌套）')
    likes = models.PositiveIntegerField(default=0, verbose_name='点赞数')
    is_approved = models.BooleanField(
        default=True, verbose_name='是否审核通过')
    # 评论配图，上传到 MEDIA_ROOT/comment_images/，可空
    image = models.ImageField(
        upload_to='comment_images/', null=True, blank=True,
        verbose_name='评论图片')
    # 长评论是否折叠（视图按长度标记或后台人工折叠）
    is_folded = models.BooleanField(
        default=False, verbose_name='是否折叠')
    # 是否已被举报，收到举报后置 True 供后台优先审核
    reported = models.BooleanField(default=False, verbose_name='已举报')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='评论时间')
    # 软删除
    is_deleted = models.BooleanField(
        default=False, verbose_name='已软删除')
    deleted_at = models.DateTimeField(
        null=True, blank=True, verbose_name='删除时间')

    class Meta:
        db_table = 'blog_comment'
        verbose_name = '评论'
        verbose_name_plural = '评论'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['article', '-created_at'],
                         name='idx_cmt_article_ct'),
            models.Index(fields=['parent_comment', '-created_at'],
                         name='idx_cmt_parent_ct'),
            models.Index(fields=['user', '-created_at'],
                         name='idx_cmt_user_ct')]

    def __str__(self):
        """可读表示：某人 评论了《文章》: 前20字。"""
        preview = (self.content or '')[:20]
        return f'{self.user} 评论了《{self.article.title}》: {preview}'

    @property
    def floor_number(self):
        """楼层号兜底：同文章下早于本评论的已通过评论数 + 1。

        列表场景由视图批量计算注入模板，此处仅作单点兜底，避免 N+1。
        """
        return (Comment.objects.filter(
            article=self.article, is_approved=True,
            created_at__lt=self.created_at).count()) + 1


class CommentReaction(models.Model):
    """评论表情反应：用户对评论打出一个表情，三者联合唯一。"""

    # 反应类型选项（值 + emoji），模型字段用值，模板展示 emoji
    REACTION_CHOICES = [
        ('like', '👍'), ('love', '❤️'), ('laugh', '😂'),
        ('wow', '😮'), ('sad', '😢'), ('fire', '🔥')]

    user = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='comment_reactions', verbose_name='用户')
    comment = models.ForeignKey(
        Comment, on_delete=models.CASCADE,
        related_name='reactions', verbose_name='评论')
    reaction_type = models.CharField(
        max_length=10, choices=REACTION_CHOICES,
        verbose_name='反应类型')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='时间')

    class Meta:
        db_table = 'blog_comment_reaction'
        unique_together = ('user', 'comment', 'reaction_type')

    def __str__(self):
        """可读表示：用户 反应 评论id。"""
        return f'{self.user} {self.reaction_type} 评论{self.comment_id}'


class CommentReport(models.Model):
    """评论举报记录：举报人与被举报评论，原因必填。"""

    comment = models.ForeignKey(
        Comment, on_delete=models.CASCADE,
        related_name='reports', verbose_name='被举报评论')
    reporter = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='comment_reports', verbose_name='举报人')
    reason = models.TextField(verbose_name='举报原因')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='举报时间')

    class Meta:
        db_table = 'blog_comment_report'
        verbose_name = '评论举报'
        verbose_name_plural = '评论举报'
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：举报人 举报了 评论id。"""
        return f'{self.reporter} 举报了评论#{self.comment_id}'

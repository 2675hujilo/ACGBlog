# -*- coding: utf-8 -*-
"""
社交关系领域模型 —— 关注、扩展资料、活动、屏蔽 / 静音与内容举报。

本文件从原 ``blog/models.py`` 拆出，含：

- :class:`UserFollow`：用户关注关系（粉丝系统）；
- :class:`UserProfile`：用户扩展资料（头像背景色、社交账号、个人网站等）；
- :class:`UserActivity`：用户行为活动流（发布 / 评论 / 点赞 / 收藏 / 关注）；
- :class:`UserBlock`：用户黑名单（屏蔽内容与私信）；
- :class:`UserMute`：用户静音（不收通知但仍可见内容）；
- :class:`CategoryFollow` / :class:`TagFollow`：关注分类 / 标签（新内容通知）；
- :class:`ContentReport`：内容举报（文章 / 评论 / 用户，含处理状态）。

表名与拆分前一致，不产生数据库结构变更；跨文件外键以字符串引用。

维护注意点
----------
1. 关注 / 屏蔽 / 静音均为成对用户的唯一关系，unique_together 兜底，重复提交
   走 get_or_create 幂等；
2. UserProfile 与 User 是 OneToOne（related_name='profile_ext'），与 User 自带的
   avatar / introduction 区分：本表放社交账号与扩展外观；
3. UserActivity 是时间线 / 活跃度数据源，target_id 为泛化目标主键（无外键约束），
   展示前需校验目标是否仍存在；
4. ContentReport 处理状态流转（pending -> resolved/rejected），处理结论与管理员
   备注留痕，注意与 CommentReport（评论举报）区分。
"""
from django.db import models


class UserFollow(models.Model):
    """用户关注关系：关注者 -> 被关注者，联合唯一。"""

    follower = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='following_set', verbose_name='关注者')
    following = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='followers_set', verbose_name='被关注者')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='关注时间')

    class Meta:
        db_table = 'blog_user_follow'
        unique_together = ('follower', 'following')
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：关注者 -> 被关注者。"""
        return f'{self.follower} -> {self.following}'


class UserProfile(models.Model):
    """用户扩展资料：社交账号、个人网站、头像背景色与个性签名。"""

    user = models.OneToOneField(
        'User', on_delete=models.CASCADE,
        related_name='profile_ext', verbose_name='用户')
    bio = models.TextField(
        max_length=500, blank=True, verbose_name='个人简介')
    location = models.CharField(
        max_length=100, blank=True, verbose_name='所在地')
    website = models.URLField(
        max_length=200, blank=True, verbose_name='个人网站')
    twitter = models.CharField(
        max_length=100, blank=True, verbose_name='Twitter')
    github = models.CharField(
        max_length=100, blank=True, verbose_name='GitHub')
    weibo = models.CharField(
        max_length=100, blank=True, verbose_name='微博')
    bilibili = models.CharField(
        max_length=100, blank=True, verbose_name='B站')
    avatar_bg = models.CharField(
        max_length=7, default='#a06cd5', verbose_name='头像背景色')
    signature = models.CharField(
        max_length=200, blank=True, verbose_name='个性签名')

    class Meta:
        db_table = 'blog_user_profile'

    def __str__(self):
        """可读表示：用户 的资料。"""
        return f'{self.user} 的资料'


class UserActivity(models.Model):
    """用户活动记录：行为类型 + 泛化目标（类型 / ID）+ 详情。"""

    user = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='activities', verbose_name='用户')
    action_type = models.CharField(
        max_length=30, verbose_name='行为类型')
    target_type = models.CharField(
        max_length=30, blank=True, verbose_name='目标类型')
    target_id = models.PositiveIntegerField(
        null=True, verbose_name='目标ID')
    detail = models.CharField(
        max_length=200, blank=True, verbose_name='详情')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='时间')

    class Meta:
        db_table = 'blog_user_activity'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action_type'])]

    def __str__(self):
        """可读表示：用户 行为类型。"""
        return f'{self.user} {self.action_type}'


class UserBlock(models.Model):
    """用户黑名单：屏蔽者 -> 被屏蔽者，可记原因。"""

    blocker = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='blocking_set', verbose_name='屏蔽者')
    blocked = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='blocked_set', verbose_name='被屏蔽者')
    reason = models.CharField(
        max_length=200, blank=True, verbose_name='原因')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='时间')

    class Meta:
        db_table = 'blog_user_block'
        unique_together = ('blocker', 'blocked')

    def __str__(self):
        """可读表示：屏蔽者 屏蔽 被屏蔽者。"""
        return f'{self.blocker} 屏蔽 {self.blocked}'


class UserMute(models.Model):
    """用户静音：静音者 -> 被静音者（不收通知、仍可见内容）。"""

    muter = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='muting_set', verbose_name='静音者')
    muted = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='muted_set', verbose_name='被静音者')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='时间')

    class Meta:
        db_table = 'blog_user_mute'
        unique_together = ('muter', 'muted')

    def __str__(self):
        """可读表示：静音者 静音 被静音者。"""
        return f'{self.muter} 静音 {self.muted}'


class CategoryFollow(models.Model):
    """用户关注分类：该分类有新文章时通知。"""

    user = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='category_follows', verbose_name='用户')
    category = models.ForeignKey(
        'Category', on_delete=models.CASCADE,
        related_name='followers', verbose_name='分类')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='时间')

    class Meta:
        db_table = 'blog_category_follow'
        unique_together = ('user', 'category')

    def __str__(self):
        """可读表示：用户 关注分类 分类。"""
        return f'{self.user} 关注分类 {self.category}'


class TagFollow(models.Model):
    """用户关注标签：该标签有新文章时通知。"""

    user = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='tag_follows', verbose_name='用户')
    tag = models.ForeignKey(
        'Tag', on_delete=models.CASCADE,
        related_name='followers', verbose_name='标签')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='时间')

    class Meta:
        db_table = 'blog_tag_follow'
        unique_together = ('user', 'tag')

    def __str__(self):
        """可读表示：用户 关注标签 标签。"""
        return f'{self.user} 关注标签 {self.tag}'


class ContentReport(models.Model):
    """内容举报：文章 / 评论 / 用户，含举报原因与处理状态流转。"""

    # 举报原因选项
    REPORT_TYPE = [
        ('spam', '垃圾广告'), ('inappropriate', '不当内容'),
        ('copyright', '版权侵犯'), ('harassment', '骚扰'),
        ('other', '其他')]
    # 处理状态选项
    STATUS = [
        ('pending', '待处理'), ('resolved', '已处理'),
        ('rejected', '已驳回')]

    reporter = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='reports_made', verbose_name='举报人')
    content_type = models.CharField(
        max_length=20, verbose_name='内容类型')
    content_id = models.PositiveIntegerField(
        verbose_name='内容ID')
    reason = models.CharField(
        max_length=20, choices=REPORT_TYPE, verbose_name='举报原因')
    detail = models.TextField(
        max_length=500, blank=True, verbose_name='详细说明')
    status = models.CharField(
        max_length=20, default='pending', choices=STATUS,
        verbose_name='处理状态')
    admin_note = models.TextField(
        blank=True, verbose_name='管理员备注')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='时间')

    class Meta:
        db_table = 'blog_content_report'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['content_type', 'content_id'])]

    def __str__(self):
        """可读表示：举报 类型#ID (原因)。"""
        return (f'举报 {self.content_type}#{self.content_id} '
                f'({self.reason})')

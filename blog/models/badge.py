# -*- coding: utf-8 -*-
"""
徽章 / 积分 / 成就领域模型。

本文件从原 ``blog/models.py`` 拆出，含：

- :class:`Badge`：成就徽章**定义**（全局共享一套规则），用 condition_type +
  condition_value 描述达成条件（发文数 / 评论数 / 获赞数 / 阅读数 / 注册天数）；
- :class:`UserBadge`：用户已获得徽章的关联（用户 × 徽章唯一）；
- :class:`UserPoint`：用户积分账户（总积分 / 当前积分 / 等级）；
- :class:`PointLog`：积分变动流水；
- :class:`UserAchievement`：用户已解锁成就（与 Badge 互补的成就体系）。

表名与拆分前一致，不产生数据库结构变更；用户 / 徽章外键以字符串引用。

维护注意点
----------
1. Badge 条件由徽章检查函数在用户发文 / 评论 / 获赞等事件触发时比对，达成后
   创建 UserBadge（幂等，唯一约束兜底），并可配套发通知；
2. 积分变动必须同时写 PointLog（含变动后余额），保证可追溯、可对账；
3. UserPoint 为 OneToOne，新用户首次使用时 get_or_create；
4. 新增徽章 / 成就通过 seed 数据或后台录入，condition 字段须与检查逻辑一致。
"""
from django.db import models


class Badge(models.Model):
    """徽章定义：名称 + 图标 + 达成条件（类型 + 阈值）。"""

    class ConditionType(models.TextChoices):
        """达成条件类型枚举。"""

        ARTICLES = 'articles', '发文数'
        COMMENTS = 'comments', '评论数'
        LIKES = 'likes', '获赞数'
        VIEWS = 'views', '阅读数'
        DAYS = 'days', '注册天数'

    name = models.CharField(
        max_length=50, unique=True, verbose_name='徽章名')
    description = models.TextField(
        blank=True, default='', verbose_name='徽章说明')
    icon = models.CharField(
        max_length=20, blank=True, default='🏅',
        verbose_name='图标(emoji)')
    condition_type = models.CharField(
        max_length=15, choices=ConditionType.choices,
        verbose_name='条件类型')
    condition_value = models.IntegerField(
        default=1, verbose_name='条件阈值')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'blog_badge'
        verbose_name = '徽章'
        verbose_name_plural = '徽章'
        ordering = ['condition_type', 'condition_value']

    def __str__(self):
        """可读表示：图标 徽章名。"""
        return f'{self.icon} {self.name}'


class UserBadge(models.Model):
    """用户已获得徽章：用户 × 徽章联合唯一。"""

    user = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='user_badges', verbose_name='用户')
    badge = models.ForeignKey(
        Badge, on_delete=models.CASCADE,
        related_name='user_badges', verbose_name='徽章')
    earned_at = models.DateTimeField(
        auto_now_add=True, verbose_name='获得时间')

    class Meta:
        db_table = 'blog_user_badge'
        verbose_name = '用户徽章'
        verbose_name_plural = '用户徽章'
        unique_together = ('user', 'badge')
        ordering = ['-earned_at']

    def __str__(self):
        """可读表示：用户 获得了 徽章。"""
        return f'{self.user} 获得了 {self.badge}'


class UserPoint(models.Model):
    """用户积分账户：总积分（累计获得）/ 当前积分（可用）/ 等级。"""

    user = models.OneToOneField(
        'User', on_delete=models.CASCADE,
        related_name='points', verbose_name='用户')
    total_points = models.PositiveIntegerField(
        default=0, verbose_name='总积分')
    current_points = models.PositiveIntegerField(
        default=0, verbose_name='当前积分')
    level = models.PositiveIntegerField(
        default=1, verbose_name='等级')

    class Meta:
        db_table = 'blog_user_point'

    def __str__(self):
        """可读表示：用户: 当前积分分 Lv.等级。"""
        return f'{self.user}: {self.current_points}分 Lv.{self.level}'


class PointLog(models.Model):
    """积分变动流水：变动积分（正负）+ 原因 + 变动后余额。"""

    user = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='point_logs', verbose_name='用户')
    points = models.IntegerField(verbose_name='变动积分')
    reason = models.CharField(max_length=100, verbose_name='原因')
    balance_after = models.PositiveIntegerField(
        verbose_name='变动后余额')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='时间')

    class Meta:
        db_table = 'blog_point_log'
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：用户 变动积分 (原因)。"""
        return f'{self.user} {self.points:+d} ({self.reason})'


class UserAchievement(models.Model):
    """用户已解锁成就：成就标识 + 名称 + 描述 + 图标。"""

    user = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='achievements', verbose_name='用户')
    achievement_key = models.CharField(
        max_length=50, verbose_name='成就标识')
    title = models.CharField(max_length=100, verbose_name='成就名称')
    description = models.CharField(
        max_length=300, verbose_name='成就描述')
    icon = models.CharField(
        max_length=20, default='🏆', verbose_name='图标')
    unlocked_at = models.DateTimeField(
        auto_now_add=True, verbose_name='解锁时间')

    class Meta:
        db_table = 'blog_user_achievement'
        unique_together = ('user', 'achievement_key')
        ordering = ['-unlocked_at']

    def __str__(self):
        """可读表示：用户 - 成就名称。"""
        return f'{self.user} - {self.title}'

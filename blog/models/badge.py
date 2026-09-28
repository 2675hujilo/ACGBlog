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
#: 从模块「django.db」导入所需对象
from django.db import models


class Badge(models.Model):
    """徽章定义：名称 + 图标 + 达成条件（类型 + 阈值）。"""

    class ConditionType(models.TextChoices):
        """达成条件类型枚举。"""

        #: 定义变量「ARTICLES」，保存对应数据
        ARTICLES = 'articles', '发文数'
        #: 定义变量「COMMENTS」，保存对应数据
        COMMENTS = 'comments', '评论数'
        #: 定义变量「LIKES」，保存对应数据
        LIKES = 'likes', '获赞数'
        #: 定义变量「VIEWS」，保存对应数据
        VIEWS = 'views', '阅读数'
        #: 定义变量「DAYS」，保存对应数据
        DAYS = 'days', '注册天数'

    #: 定义变量「name」，保存对应数据（Django 模型字段，参与建表）
    name = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=50, unique=True, verbose_name='徽章名')
    #: 定义变量「description」，保存对应数据（Django 模型字段，参与建表）
    description = models.TextField(
        #: 定义变量「blank」，保存对应数据
        blank=True, default='', verbose_name='徽章说明')
    #: 定义变量「icon」，保存对应数据（Django 模型字段，参与建表）
    icon = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=20, blank=True, default='🏅',
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='图标(emoji)')
    #: 定义变量「condition_type」，保存对应数据（Django 模型字段，参与建表）
    condition_type = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=15, choices=ConditionType.choices,
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='条件类型')
    #: 定义变量「condition_value」，保存对应数据（Django 模型字段，参与建表）
    condition_value = models.IntegerField(
        #: 定义变量「default」，保存对应数据
        default=1, verbose_name='条件阈值')
    #: 定义变量「created_at」，保存对应数据（Django 模型字段，参与建表）
    created_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='创建时间')

    class Meta:
        """
        类 Meta：meta。

        字段/类属性：
          - db_table：str
          - verbose_name：str
          - verbose_name_plural：str
          - ordering

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「db_table」，保存对应数据
        db_table = 'blog_badge'
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name = '徽章'
        #: 定义变量「verbose_name_plural」，保存对应数据
        verbose_name_plural = '徽章'
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['condition_type', 'condition_value']

    def __str__(self):
        """可读表示：图标 徽章名。"""
        #: 返回结果并结束当前函数
        return f'{self.icon} {self.name}'


class UserBadge(models.Model):
    """用户已获得徽章：用户 × 徽章联合唯一。"""

    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='user_badges', verbose_name='用户')
    #: 定义变量「badge」，保存对应数据（Django 模型字段，参与建表）
    badge = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        Badge, on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='user_badges', verbose_name='徽章')
    #: 定义变量「earned_at」，保存对应数据（Django 模型字段，参与建表）
    earned_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='获得时间')

    class Meta:
        """
        类 Meta：meta。

        字段/类属性：
          - db_table：str
          - verbose_name：str
          - verbose_name_plural：str
          - unique_together
          - ordering

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「db_table」，保存对应数据
        db_table = 'blog_user_badge'
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name = '用户徽章'
        #: 定义变量「verbose_name_plural」，保存对应数据
        verbose_name_plural = '用户徽章'
        #: 定义变量「unique_together」，保存对应数据（集合/元组）
        unique_together = ('user', 'badge')
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-earned_at']

    def __str__(self):
        """可读表示：用户 获得了 徽章。"""
        #: 返回结果并结束当前函数
        return f'{self.user} 获得了 {self.badge}'


class UserPoint(models.Model):
    """用户积分账户：总积分（累计获得）/ 当前积分（可用）/ 等级。"""

    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.OneToOneField(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='points', verbose_name='用户')
    #: 定义变量「total_points」，保存对应数据（Django 模型字段，参与建表）
    total_points = models.PositiveIntegerField(
        #: 定义变量「default」，保存对应数据
        default=0, verbose_name='总积分')
    #: 定义变量「current_points」，保存对应数据（Django 模型字段，参与建表）
    current_points = models.PositiveIntegerField(
        #: 定义变量「default」，保存对应数据
        default=0, verbose_name='当前积分')
    #: 定义变量「level」，保存对应数据（Django 模型字段，参与建表）
    level = models.PositiveIntegerField(
        #: 定义变量「default」，保存对应数据
        default=1, verbose_name='等级')

    class Meta:
        """
        类 Meta：meta。

        字段/类属性：
          - db_table：str

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「db_table」，保存对应数据
        db_table = 'blog_user_point'

    def __str__(self):
        """可读表示：用户: 当前积分分 Lv.等级。"""
        #: 返回结果并结束当前函数
        return f'{self.user}: {self.current_points}分 Lv.{self.level}'


class PointLog(models.Model):
    """积分变动流水：变动积分（正负）+ 原因 + 变动后余额。"""

    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='point_logs', verbose_name='用户')
    #: 定义变量「points」，保存对应数据（Django 模型字段，参与建表）
    points = models.IntegerField(verbose_name='变动积分')
    #: 定义变量「reason」，保存对应数据（Django 模型字段，参与建表）
    reason = models.CharField(max_length=100, verbose_name='原因')
    #: 定义变量「balance_after」，保存对应数据（Django 模型字段，参与建表）
    balance_after = models.PositiveIntegerField(
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='变动后余额')
    #: 定义变量「created_at」，保存对应数据（Django 模型字段，参与建表）
    created_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='时间')

    class Meta:
        """
        类 Meta：meta。

        字段/类属性：
          - db_table：str
          - ordering

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「db_table」，保存对应数据
        db_table = 'blog_point_log'
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：用户 变动积分 (原因)。"""
        #: 返回结果并结束当前函数
        return f'{self.user} {self.points:+d} ({self.reason})'


class UserAchievement(models.Model):
    """用户已解锁成就：成就标识 + 名称 + 描述 + 图标。"""

    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='achievements', verbose_name='用户')
    #: 定义变量「achievement_key」，保存对应数据（Django 模型字段，参与建表）
    achievement_key = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=50, verbose_name='成就标识')
    #: 定义变量「title」，保存对应数据（Django 模型字段，参与建表）
    title = models.CharField(max_length=100, verbose_name='成就名称')
    #: 定义变量「description」，保存对应数据（Django 模型字段，参与建表）
    description = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=300, verbose_name='成就描述')
    #: 定义变量「icon」，保存对应数据（Django 模型字段，参与建表）
    icon = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=20, default='🏆', verbose_name='图标')
    #: 定义变量「unlocked_at」，保存对应数据（Django 模型字段，参与建表）
    unlocked_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='解锁时间')

    class Meta:
        """
        类 Meta：meta。

        字段/类属性：
          - db_table：str
          - unique_together
          - ordering

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「db_table」，保存对应数据
        db_table = 'blog_user_achievement'
        #: 定义变量「unique_together」，保存对应数据（集合/元组）
        unique_together = ('user', 'achievement_key')
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-unlocked_at']

    def __str__(self):
        """可读表示：用户 - 成就名称。"""
        #: 返回结果并结束当前函数
        return f'{self.user} - {self.title}'

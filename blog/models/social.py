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
#: 从模块「django.db」导入所需对象
from django.db import models


class UserFollow(models.Model):
    """用户关注关系：关注者 -> 被关注者，联合唯一。"""

    #: 定义变量「follower」，保存对应数据（Django 模型字段，参与建表）
    follower = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='following_set', verbose_name='关注者')
    #: 定义变量「following」，保存对应数据（Django 模型字段，参与建表）
    following = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='followers_set', verbose_name='被关注者')
    #: 定义变量「created_at」，保存对应数据（Django 模型字段，参与建表）
    created_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='关注时间')

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
        db_table = 'blog_user_follow'
        #: 定义变量「unique_together」，保存对应数据（集合/元组）
        unique_together = ('follower', 'following')
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：关注者 -> 被关注者。"""
        #: 返回结果并结束当前函数
        return f'{self.follower} -> {self.following}'


class UserProfile(models.Model):
    """用户扩展资料：社交账号、个人网站、头像背景色与个性签名。"""

    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.OneToOneField(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='profile_ext', verbose_name='用户')
    #: 定义变量「bio」，保存对应数据（Django 模型字段，参与建表）
    bio = models.TextField(
        #: 定义变量「max_length」，保存对应数据
        max_length=500, blank=True, verbose_name='个人简介')
    #: 定义变量「location」，保存对应数据（Django 模型字段，参与建表）
    location = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=100, blank=True, verbose_name='所在地')
    #: 定义变量「website」，保存对应数据（Django 模型字段，参与建表）
    website = models.URLField(
        #: 定义变量「max_length」，保存对应数据
        max_length=200, blank=True, verbose_name='个人网站')
    #: 定义变量「twitter」，保存对应数据（Django 模型字段，参与建表）
    twitter = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=100, blank=True, verbose_name='Twitter')
    #: 定义变量「github」，保存对应数据（Django 模型字段，参与建表）
    github = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=100, blank=True, verbose_name='GitHub')
    #: 定义变量「weibo」，保存对应数据（Django 模型字段，参与建表）
    weibo = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=100, blank=True, verbose_name='微博')
    #: 定义变量「bilibili」，保存对应数据（Django 模型字段，参与建表）
    bilibili = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=100, blank=True, verbose_name='B站')
    #: 定义变量「avatar_bg」，保存对应数据（Django 模型字段，参与建表）
    avatar_bg = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=7, default='#a06cd5', verbose_name='头像背景色')
    #: 定义变量「signature」，保存对应数据（Django 模型字段，参与建表）
    signature = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=200, blank=True, verbose_name='个性签名')

    class Meta:
        """
        类 Meta：meta。

        字段/类属性：
          - db_table：str

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「db_table」，保存对应数据
        db_table = 'blog_user_profile'

    def __str__(self):
        """可读表示：用户 的资料。"""
        #: 返回结果并结束当前函数
        return f'{self.user} 的资料'


class UserActivity(models.Model):
    """用户活动记录：行为类型 + 泛化目标（类型 / ID）+ 详情。"""

    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='activities', verbose_name='用户')
    #: 定义变量「action_type」，保存对应数据（Django 模型字段，参与建表）
    action_type = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=30, verbose_name='行为类型')
    #: 定义变量「target_type」，保存对应数据（Django 模型字段，参与建表）
    target_type = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=30, blank=True, verbose_name='目标类型')
    #: 定义变量「target_id」，保存对应数据（Django 模型字段，参与建表）
    target_id = models.PositiveIntegerField(
        #: 定义变量「null」，保存对应数据
        null=True, verbose_name='目标ID')
    #: 定义变量「detail」，保存对应数据（Django 模型字段，参与建表）
    detail = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=200, blank=True, verbose_name='详情')
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
          - indexes

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「db_table」，保存对应数据
        db_table = 'blog_user_activity'
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-created_at']
        #: 定义变量「indexes」，保存对应数据（集合/元组）
        indexes = [
            #: 调用「models.Index」执行相应逻辑
            models.Index(fields=['user', '-created_at']),
            #: 调用「models.Index」执行相应逻辑
            models.Index(fields=['action_type'])]

    def __str__(self):
        """可读表示：用户 行为类型。"""
        #: 返回结果并结束当前函数
        return f'{self.user} {self.action_type}'


class UserBlock(models.Model):
    """用户黑名单：屏蔽者 -> 被屏蔽者，可记原因。"""

    #: 定义变量「blocker」，保存对应数据（Django 模型字段，参与建表）
    blocker = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='blocking_set', verbose_name='屏蔽者')
    #: 定义变量「blocked」，保存对应数据（Django 模型字段，参与建表）
    blocked = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='blocked_set', verbose_name='被屏蔽者')
    #: 定义变量「reason」，保存对应数据（Django 模型字段，参与建表）
    reason = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=200, blank=True, verbose_name='原因')
    #: 定义变量「created_at」，保存对应数据（Django 模型字段，参与建表）
    created_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='时间')

    class Meta:
        """
        类 Meta：meta。

        字段/类属性：
          - db_table：str
          - unique_together

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「db_table」，保存对应数据
        db_table = 'blog_user_block'
        #: 定义变量「unique_together」，保存对应数据（集合/元组）
        unique_together = ('blocker', 'blocked')

    def __str__(self):
        """可读表示：屏蔽者 屏蔽 被屏蔽者。"""
        #: 返回结果并结束当前函数
        return f'{self.blocker} 屏蔽 {self.blocked}'


class UserMute(models.Model):
    """用户静音：静音者 -> 被静音者（不收通知、仍可见内容）。"""

    #: 定义变量「muter」，保存对应数据（Django 模型字段，参与建表）
    muter = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='muting_set', verbose_name='静音者')
    #: 定义变量「muted」，保存对应数据（Django 模型字段，参与建表）
    muted = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='muted_set', verbose_name='被静音者')
    #: 定义变量「created_at」，保存对应数据（Django 模型字段，参与建表）
    created_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='时间')

    class Meta:
        """
        类 Meta：meta。

        字段/类属性：
          - db_table：str
          - unique_together

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「db_table」，保存对应数据
        db_table = 'blog_user_mute'
        #: 定义变量「unique_together」，保存对应数据（集合/元组）
        unique_together = ('muter', 'muted')

    def __str__(self):
        """可读表示：静音者 静音 被静音者。"""
        #: 返回结果并结束当前函数
        return f'{self.muter} 静音 {self.muted}'


class CategoryFollow(models.Model):
    """用户关注分类：该分类有新文章时通知。"""

    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='category_follows', verbose_name='用户')
    #: 定义变量「category」，保存对应数据（Django 模型字段，参与建表）
    category = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'Category', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='followers', verbose_name='分类')
    #: 定义变量「created_at」，保存对应数据（Django 模型字段，参与建表）
    created_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='时间')

    class Meta:
        """
        类 Meta：meta。

        字段/类属性：
          - db_table：str
          - unique_together

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「db_table」，保存对应数据
        db_table = 'blog_category_follow'
        #: 定义变量「unique_together」，保存对应数据（集合/元组）
        unique_together = ('user', 'category')

    def __str__(self):
        """可读表示：用户 关注分类 分类。"""
        #: 返回结果并结束当前函数
        return f'{self.user} 关注分类 {self.category}'


class TagFollow(models.Model):
    """用户关注标签：该标签有新文章时通知。"""

    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='tag_follows', verbose_name='用户')
    #: 定义变量「tag」，保存对应数据（Django 模型字段，参与建表）
    tag = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'Tag', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='followers', verbose_name='标签')
    #: 定义变量「created_at」，保存对应数据（Django 模型字段，参与建表）
    created_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='时间')

    class Meta:
        """
        类 Meta：meta。

        字段/类属性：
          - db_table：str
          - unique_together

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「db_table」，保存对应数据
        db_table = 'blog_tag_follow'
        #: 定义变量「unique_together」，保存对应数据（集合/元组）
        unique_together = ('user', 'tag')

    def __str__(self):
        """可读表示：用户 关注标签 标签。"""
        #: 返回结果并结束当前函数
        return f'{self.user} 关注标签 {self.tag}'


class ContentReport(models.Model):
    """内容举报：文章 / 评论 / 用户，含举报原因与处理状态流转。"""

    # 举报原因选项
    #: 定义变量「REPORT_TYPE」，保存对应数据（集合/元组）
    REPORT_TYPE = [
        #: 该行执行对应逻辑（结合上下文理解）
        ('spam', '垃圾广告'), ('inappropriate', '不当内容'),
        #: 该行执行对应逻辑（结合上下文理解）
        ('copyright', '版权侵犯'), ('harassment', '骚扰'),
        #: 该行执行对应逻辑（结合上下文理解）
        ('other', '其他')]
    # 处理状态选项
    #: 定义变量「STATUS」，保存对应数据（集合/元组）
    STATUS = [
        #: 该行执行对应逻辑（结合上下文理解）
        ('pending', '待处理'), ('resolved', '已处理'),
        #: 该行执行对应逻辑（结合上下文理解）
        ('rejected', '已驳回')]

    #: 定义变量「reporter」，保存对应数据（Django 模型字段，参与建表）
    reporter = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='reports_made', verbose_name='举报人')
    #: 定义变量「content_type」，保存对应数据（Django 模型字段，参与建表）
    content_type = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=20, verbose_name='内容类型')
    #: 定义变量「content_id」，保存对应数据（Django 模型字段，参与建表）
    content_id = models.PositiveIntegerField(
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='内容ID')
    #: 定义变量「reason」，保存对应数据（Django 模型字段，参与建表）
    reason = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=20, choices=REPORT_TYPE, verbose_name='举报原因')
    #: 定义变量「detail」，保存对应数据（Django 模型字段，参与建表）
    detail = models.TextField(
        #: 定义变量「max_length」，保存对应数据
        max_length=500, blank=True, verbose_name='详细说明')
    #: 定义变量「status」，保存对应数据（Django 模型字段，参与建表）
    status = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=20, default='pending', choices=STATUS,
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='处理状态')
    #: 定义变量「admin_note」，保存对应数据（Django 模型字段，参与建表）
    admin_note = models.TextField(
        #: 定义变量「blank」，保存对应数据
        blank=True, verbose_name='管理员备注')
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
          - indexes

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「db_table」，保存对应数据
        db_table = 'blog_content_report'
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-created_at']
        #: 定义变量「indexes」，保存对应数据（集合/元组）
        indexes = [
            #: 调用「models.Index」执行相应逻辑
            models.Index(fields=['status']),
            #: 调用「models.Index」执行相应逻辑
            models.Index(fields=['content_type', 'content_id'])]

    def __str__(self):
        """可读表示：举报 类型#ID (原因)。"""
        #: 返回结果并结束当前函数
        return (f'举报 {self.content_type}#{self.content_id} '
                #: 该行执行对应逻辑（结合上下文理解）
                f'({self.reason})')

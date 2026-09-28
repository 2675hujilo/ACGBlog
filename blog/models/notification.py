# -*- coding: utf-8 -*-
"""
通知领域模型 —— 站内消息通知中心。

本文件从原 ``blog/models.py`` 拆出，仅含 :class:`Notification`。通知由信号 /
视图在「收到回复、被 @、文章被赞、文章审核结果、系统公告」等事件时生成，用户
在通知中心查看；列表按未读优先、时间倒序返回。

表名 ``blog_notification`` 与拆分前一致，不产生数据库结构变更，接收人外键以
字符串引用。

维护注意点
----------
1. 通知标题 ``title`` 必填、正文 ``content`` 可空，跳转走 ``related_url``；
   模板渲染时标题 / 正文做转义，链接须为已校验的相对路径，避免 XSS；
2. 通知类型 ``type`` 用内部枚举 :class:`Notification.Type`（reply/mention/
   like/article/system），新增类型先加枚举；
3. 未读数通过 is_read=False 统计，单条已读 / 全部已读后角标刷新；
4. 通知应在业务事务提交后创建，避免事务回滚后仍发出通知。
"""
#: 从模块「django.db」导入所需对象
from django.db import models


class Notification(models.Model):
    """站内通知：接收人 + 类型 + 标题 + 正文 + 跳转链接 + 已读状态。"""

    class Type(models.TextChoices):
        """通知类型枚举。"""

        #: 定义变量「REPLY」，保存对应数据
        REPLY = 'reply', '回复'
        #: 定义变量「MENTION」，保存对应数据
        MENTION = 'mention', '提及'
        #: 定义变量「LIKE」，保存对应数据
        LIKE = 'like', '点赞'
        #: 定义变量「ARTICLE」，保存对应数据
        ARTICLE = 'article', '文章'
        #: 定义变量「SYSTEM」，保存对应数据
        SYSTEM = 'system', '系统'

    # 通知接收人
    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='notifications', verbose_name='接收人')
    # 通知类型：默认系统
    #: 定义变量「type」，保存对应数据（Django 模型字段，参与建表）
    type = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=10, choices=Type.choices,
        #: 定义变量「default」，保存对应数据
        default=Type.SYSTEM, verbose_name='通知类型')
    # 通知标题：必填，最长 200
    #: 定义变量「title」，保存对应数据（Django 模型字段，参与建表）
    title = models.CharField(max_length=200, verbose_name='标题')
    # 通知正文：可空
    #: 定义变量「content」，保存对应数据（Django 模型字段，参与建表）
    content = models.TextField(
        #: 定义变量「blank」，保存对应数据
        blank=True, default='', verbose_name='正文')
    # 点击跳转的相关 URL：可空
    #: 定义变量「related_url」，保存对应数据（Django 模型字段，参与建表）
    related_url = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=500, blank=True, default='',
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='跳转链接')
    # 是否已读：默认未读
    #: 定义变量「is_read」，保存对应数据（Django 模型字段，参与建表）
    is_read = models.BooleanField(default=False, verbose_name='是否已读')
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
          - indexes

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「db_table」，保存对应数据
        db_table = 'blog_notification'
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name = '通知'
        #: 定义变量「verbose_name_plural」，保存对应数据
        verbose_name_plural = '通知'
        # 未读优先，再按时间倒序
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-is_read', '-created_at']
        #: 定义变量「indexes」，保存对应数据（集合/元组）
        indexes = [
            #: 调用「models.Index」执行相应逻辑
            models.Index(fields=['user', 'is_read'],
                         #: 定义变量「name」，保存对应数据
                         name='idx_notif_user_read')]

    def __str__(self):
        """可读表示：「[类型] 标题」。"""
        #: 返回结果并结束当前函数
        return f'[{self.get_type_display()}] {self.title}'

# -*- coding: utf-8 -*-
"""
分类与标签领域模型 —— 内容的两种「聚合维度」。

本文件从原 ``blog/models.py`` 拆出，包含：

- :class:`Category`：分类，与文章是**一对多**（每篇文章归属至多一个分类）；
- :class:`Tag`：标签，与文章是**多对多**（一篇文章可挂多个标签）。

二者都独立于文章存在，便于：

- 前台导航 / 分类页 / 标签云做聚合统计；
- 按分类或标签筛选文章列表。

表名（``blog_category`` / ``blog_tag``）、字段与排序均与拆分前一致，不产生
数据库结构变更。文章侧对它们的外键 / 多对多关系以字符串形式引用（``'Category'``
/ ``'Tag'``），由 Django 在模型注册后解析。

维护注意点
----------
1. 分类名、标签名都设为唯一，重复创建应由视图用 ``get_or_create`` 消化，
   不要直接 ``create`` 一个可能重名的对象，否则触发 IntegrityError；
2. 删除分类时文章侧外键是 ``SET_NULL``（文章保留、分类置空），删除标签则
   自动解除多对多关系，都不会连带删除文章；
3. ``icon`` 为 emoji 字符，在导航 / 分类页名前展示，更换图标无需改模板。
"""
from django.db import models


class Category(models.Model):
    """文章分类。

    一个分类下可有多篇文章，文章分类可被置空。分类名全局唯一，用于导航与
    归档聚合。
    """

    # 分类名：全局唯一，最长 80 字
    name = models.CharField(max_length=80, unique=True, verbose_name='分类名')
    # 分类介绍：多行文本，可在分类页头部展示，默认空
    description = models.TextField(
        blank=True, default='', verbose_name='分类介绍')
    # 分类图标：emoji 字符，默认文件夹，展示在分类名前
    icon = models.CharField(
        max_length=10, blank=True, default='📁',
        verbose_name='图标(emoji)')
    # 创建时间：auto_now_add 仅在首次创建时写入
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='创建时间')

    class Meta:
        """分类表元信息。"""
        db_table = 'blog_category'
        verbose_name = '分类'
        verbose_name_plural = '分类'
        # 默认按分类名升序，便于后台与导航稳定展示
        ordering = ['name']

    def __str__(self) -> str:
        """返回分类名作为可读表示。"""
        return self.name


class Tag(models.Model):
    """文章标签。

    标签独立于文章存在，与文章多对多关联，便于聚合统计与标签云展示。
    """

    # 标签名：全局唯一，最长 50 字
    name = models.CharField(max_length=50, unique=True, verbose_name='标签名')
    # 创建时间：首次创建自动写入
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='创建时间')

    class Meta:
        """标签表元信息。"""
        db_table = 'blog_tag'
        verbose_name = '标签'
        verbose_name_plural = '标签'
        # 默认按标签名升序
        ordering = ['name']

    def __str__(self) -> str:
        """返回标签名作为可读表示。"""
        return self.name

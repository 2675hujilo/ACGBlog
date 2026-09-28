# -*- coding: utf-8 -*-
"""
系列领域模型 —— 文章合集（Series）。

本文件从原 ``blog/models.py`` 拆出，仅含 :class:`Series`。系列由登录用户创建，
把同一主题的多篇文章组织到一起，文章通过 :class:`blog.models.Article` 的
``series`` 外键归入、并用 ``series_order`` 字段决定在系列内的阅读顺序。

表名 ``blog_series`` 与拆分前一致，不产生数据库结构变更；作者外键以字符串引用。

维护注意点
----------
1. 系列封面可空，模板渲染时对无封面系列用渐变占位；
2. 作者删除时其系列级联删除（文章本身的 series 外键是 SET_NULL，文章不丢）；
3. 系列下文章数在后台 / 卡片展示，统计时注意只计已发布文章。
"""
#: 从模块「django.db」导入所需对象
from django.db import models


class Series(models.Model):
    """文章系列：标题 + 介绍 + 封面 + 作者。"""

    # 系列标题，最长 200
    #: 定义变量「title」，保存对应数据（Django 模型字段，参与建表）
    title = models.CharField(max_length=200, verbose_name='系列标题')
    # 系列介绍，可在系列详情页展示，可空
    #: 定义变量「description」，保存对应数据（Django 模型字段，参与建表）
    description = models.TextField(
        #: 定义变量「blank」，保存对应数据
        blank=True, verbose_name='系列介绍')
    # 系列封面，上传到 MEDIA_ROOT/series/，可空
    #: 定义变量「cover_image」，保存对应数据（Django 模型字段，参与建表）
    cover_image = models.ImageField(
        #: 定义变量「upload_to」，保存对应数据
        upload_to='series/', null=True, blank=True,
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='系列封面')
    # 系列作者，作者删除时级联删除其系列
    #: 定义变量「author」，保存对应数据（Django 模型字段，参与建表）
    author = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='series', verbose_name='作者')
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
        db_table = 'blog_series'
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name = '文章系列'
        #: 定义变量「verbose_name_plural」，保存对应数据
        verbose_name_plural = '文章系列'
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：直接返回系列标题。"""
        #: 返回结果并结束当前函数
        return self.title

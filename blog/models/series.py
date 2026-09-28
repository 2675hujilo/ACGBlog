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
from django.db import models


class Series(models.Model):
    """文章系列：标题 + 介绍 + 封面 + 作者。"""

    # 系列标题，最长 200
    title = models.CharField(max_length=200, verbose_name='系列标题')
    # 系列介绍，可在系列详情页展示，可空
    description = models.TextField(
        blank=True, verbose_name='系列介绍')
    # 系列封面，上传到 MEDIA_ROOT/series/，可空
    cover_image = models.ImageField(
        upload_to='series/', null=True, blank=True,
        verbose_name='系列封面')
    # 系列作者，作者删除时级联删除其系列
    author = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='series', verbose_name='作者')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'blog_series'
        verbose_name = '文章系列'
        verbose_name_plural = '文章系列'
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：直接返回系列标题。"""
        return self.title

# -*- coding: utf-8 -*-
"""
互动领域模型 —— 收藏、评分、书签、阅读清单与读书笔记。

本文件从原 ``blog/models.py`` 拆出，含：

- :class:`FavoriteFolder`：用户收藏夹（收藏的分组容器）；
- :class:`Favorite`：用户收藏文章记录（可归入收藏夹）；
- :class:`Rating`：文章 1~5 星评分；
- :class:`ArticleBookmark`：文章书签（带笔记，可挂收藏夹）；
- :class:`ReadingList`：阅读清单（稍后读 / 在读 / 已读）；
- :class:`UserNote`：文章划线高亮 + 个人笔记。

表名与拆分前一致，不产生数据库结构变更；跨文件外键以字符串引用。

维护注意点
----------
1. Favorite / Rating / Bookmark / ReadingList 都用 unique_together 保证「同一用户
   对同一文章」唯一，重复提交走 get_or_create / update_or_create 幂等处理；
2. Rating 写入后由视图重算 Article.rating_avg / rating_count 冗余字段；
3. 收藏夹删除时其下 Favorite / Bookmark 的 folder 置空（回退默认），记录不丢；
4. 各计数 / 状态变更后失效相关文章缓存，保证聚合数字即时一致。
"""
from django.db import models


class FavoriteFolder(models.Model):
    """用户收藏夹：仅名称 + 所有者，是收藏 / 书签的分组容器。"""

    user = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='favorite_folders', verbose_name='所有者')
    name = models.CharField(max_length=50, verbose_name='收藏夹名称')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'blog_favorite_folder'
        verbose_name = '收藏夹'
        verbose_name_plural = '收藏夹'
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：用户: 收藏夹名。"""
        return f'{self.user}: {self.name}'


class Favorite(models.Model):
    """用户收藏文章：可指定收藏夹，folder 为空表示默认收藏夹。"""

    user = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='favorites', verbose_name='收藏者')
    article = models.ForeignKey(
        'Article', on_delete=models.CASCADE,
        related_name='favorites', verbose_name='文章')
    folder = models.ForeignKey(
        FavoriteFolder, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='favorites', verbose_name='收藏夹')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='收藏时间')

    class Meta:
        db_table = 'blog_favorite'
        verbose_name = '收藏'
        verbose_name_plural = '收藏'
        unique_together = ('user', 'article')
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：用户 收藏了《文章》。"""
        return f'{self.user} 收藏了《{self.article.title}》'


class Rating(models.Model):
    """文章评分：1~5 星，同一用户对同一文章唯一。"""

    class Score(models.IntegerChoices):
        """评分档位枚举（1~5 星）。"""

        ONE = 1, '1星'
        TWO = 2, '2星'
        THREE = 3, '3星'
        FOUR = 4, '4星'
        FIVE = 5, '5星'

    article = models.ForeignKey(
        'Article', on_delete=models.CASCADE,
        related_name='ratings', verbose_name='文章')
    user = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='ratings', verbose_name='用户')
    score = models.PositiveSmallIntegerField(
        choices=Score.choices, verbose_name='评分(1-5)')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='评分时间')

    class Meta:
        db_table = 'blog_rating'
        verbose_name = '评分'
        verbose_name_plural = '评分'
        unique_together = ('article', 'user')
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：用户 给《文章》打了 N 星。"""
        return f'{self.user} 给《{self.article.title}》打了 {self.score} 星'


class ArticleBookmark(models.Model):
    """文章书签：带简短笔记，可挂收藏夹。"""

    user = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='bookmarks', verbose_name='用户')
    article = models.ForeignKey(
        'Article', on_delete=models.CASCADE,
        related_name='bookmarked_by', verbose_name='文章')
    folder = models.ForeignKey(
        FavoriteFolder, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='文件夹')
    note = models.CharField(
        max_length=300, blank=True, verbose_name='笔记')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='时间')

    class Meta:
        db_table = 'blog_article_bookmark'
        unique_together = ('user', 'article')
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：用户 收藏 文章。"""
        return f'{self.user} 收藏 {self.article}'


class ReadingList(models.Model):
    """阅读清单：稍后读 / 在读 / 已读三态，带优先级。"""

    user = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='reading_lists', verbose_name='用户')
    article = models.ForeignKey(
        'Article', on_delete=models.CASCADE,
        related_name='in_reading_lists', verbose_name='文章')
    status = models.CharField(
        max_length=20, default='later',
        choices=[('later', '稍后读'), ('reading', '在读'),
                 ('read', '已读')], verbose_name='状态')
    priority = models.PositiveIntegerField(
        default=0, verbose_name='优先级')
    added_at = models.DateTimeField(
        auto_now_add=True, verbose_name='添加时间')
    read_at = models.DateTimeField(
        null=True, blank=True, verbose_name='读完时间')

    class Meta:
        db_table = 'blog_reading_list'
        unique_together = ('user', 'article')
        ordering = ['-added_at']

    def __str__(self):
        """可读表示：用户 - 文章 (状态)。"""
        return f'{self.user} - {self.article} ({self.status})'


class UserNote(models.Model):
    """用户笔记：文章划线高亮内容 + 个人笔记正文。"""

    user = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='notes', verbose_name='用户')
    article = models.ForeignKey(
        'Article', on_delete=models.CASCADE,
        related_name='user_notes', verbose_name='文章')
    highlight_text = models.TextField(
        blank=True, verbose_name='划线内容')
    note_text = models.TextField(verbose_name='笔记内容')
    color = models.CharField(
        max_length=7, default='#fff3cd', verbose_name='高亮颜色')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='时间')

    class Meta:
        db_table = 'blog_user_note'
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：用户 笔记 @ 文章。"""
        return f'{self.user} 笔记 @ {self.article}'

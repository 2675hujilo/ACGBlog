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
#: 从模块「django.db」导入所需对象
from django.db import models


class FavoriteFolder(models.Model):
    """用户收藏夹：仅名称 + 所有者，是收藏 / 书签的分组容器。"""

    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='favorite_folders', verbose_name='所有者')
    #: 定义变量「name」，保存对应数据（Django 模型字段，参与建表）
    name = models.CharField(max_length=50, verbose_name='收藏夹名称')
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
        db_table = 'blog_favorite_folder'
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name = '收藏夹'
        #: 定义变量「verbose_name_plural」，保存对应数据
        verbose_name_plural = '收藏夹'
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：用户: 收藏夹名。"""
        #: 返回结果并结束当前函数
        return f'{self.user}: {self.name}'


class Favorite(models.Model):
    """用户收藏文章：可指定收藏夹，folder 为空表示默认收藏夹。"""

    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='favorites', verbose_name='收藏者')
    #: 定义变量「article」，保存对应数据（Django 模型字段，参与建表）
    article = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'Article', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='favorites', verbose_name='文章')
    #: 定义变量「folder」，保存对应数据（Django 模型字段，参与建表）
    folder = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        FavoriteFolder, on_delete=models.SET_NULL, null=True, blank=True,
        #: 定义变量「related_name」，保存对应数据
        related_name='favorites', verbose_name='收藏夹')
    #: 定义变量「created_at」，保存对应数据（Django 模型字段，参与建表）
    created_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='收藏时间')

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
        db_table = 'blog_favorite'
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name = '收藏'
        #: 定义变量「verbose_name_plural」，保存对应数据
        verbose_name_plural = '收藏'
        #: 定义变量「unique_together」，保存对应数据（集合/元组）
        unique_together = ('user', 'article')
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：用户 收藏了《文章》。"""
        #: 返回结果并结束当前函数
        return f'{self.user} 收藏了《{self.article.title}》'


class Rating(models.Model):
    """文章评分：1~5 星，同一用户对同一文章唯一。"""

    class Score(models.IntegerChoices):
        """评分档位枚举（1~5 星）。"""

        #: 定义变量「ONE」，保存对应数据
        ONE = 1, '1星'
        #: 定义变量「TWO」，保存对应数据
        TWO = 2, '2星'
        #: 定义变量「THREE」，保存对应数据
        THREE = 3, '3星'
        #: 定义变量「FOUR」，保存对应数据
        FOUR = 4, '4星'
        #: 定义变量「FIVE」，保存对应数据
        FIVE = 5, '5星'

    #: 定义变量「article」，保存对应数据（Django 模型字段，参与建表）
    article = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'Article', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='ratings', verbose_name='文章')
    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='ratings', verbose_name='用户')
    #: 定义变量「score」，保存对应数据（Django 模型字段，参与建表）
    score = models.PositiveSmallIntegerField(
        #: 定义变量「choices」，保存对应数据
        choices=Score.choices, verbose_name='评分(1-5)')
    #: 定义变量「created_at」，保存对应数据（Django 模型字段，参与建表）
    created_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='评分时间')

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
        db_table = 'blog_rating'
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name = '评分'
        #: 定义变量「verbose_name_plural」，保存对应数据
        verbose_name_plural = '评分'
        #: 定义变量「unique_together」，保存对应数据（集合/元组）
        unique_together = ('article', 'user')
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：用户 给《文章》打了 N 星。"""
        #: 返回结果并结束当前函数
        return f'{self.user} 给《{self.article.title}》打了 {self.score} 星'


class ArticleBookmark(models.Model):
    """文章书签：带简短笔记，可挂收藏夹。"""

    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='bookmarks', verbose_name='用户')
    #: 定义变量「article」，保存对应数据（Django 模型字段，参与建表）
    article = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'Article', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='bookmarked_by', verbose_name='文章')
    #: 定义变量「folder」，保存对应数据（Django 模型字段，参与建表）
    folder = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        FavoriteFolder, on_delete=models.SET_NULL, null=True, blank=True,
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='文件夹')
    #: 定义变量「note」，保存对应数据（Django 模型字段，参与建表）
    note = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=300, blank=True, verbose_name='笔记')
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
          - ordering

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「db_table」，保存对应数据
        db_table = 'blog_article_bookmark'
        #: 定义变量「unique_together」，保存对应数据（集合/元组）
        unique_together = ('user', 'article')
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：用户 收藏 文章。"""
        #: 返回结果并结束当前函数
        return f'{self.user} 收藏 {self.article}'


class ReadingList(models.Model):
    """阅读清单：稍后读 / 在读 / 已读三态，带优先级。"""

    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='reading_lists', verbose_name='用户')
    #: 定义变量「article」，保存对应数据（Django 模型字段，参与建表）
    article = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'Article', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='in_reading_lists', verbose_name='文章')
    #: 定义变量「status」，保存对应数据（Django 模型字段，参与建表）
    status = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=20, default='later',
        #: 定义变量「choices」，保存对应数据（集合/元组）
        choices=[('later', '稍后读'), ('reading', '在读'),
                 #: 该行执行对应逻辑（结合上下文理解）
                 ('read', '已读')], verbose_name='状态')
    #: 定义变量「priority」，保存对应数据（Django 模型字段，参与建表）
    priority = models.PositiveIntegerField(
        #: 定义变量「default」，保存对应数据
        default=0, verbose_name='优先级')
    #: 定义变量「added_at」，保存对应数据（Django 模型字段，参与建表）
    added_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='添加时间')
    #: 定义变量「read_at」，保存对应数据（Django 模型字段，参与建表）
    read_at = models.DateTimeField(
        #: 定义变量「null」，保存对应数据
        null=True, blank=True, verbose_name='读完时间')

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
        db_table = 'blog_reading_list'
        #: 定义变量「unique_together」，保存对应数据（集合/元组）
        unique_together = ('user', 'article')
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-added_at']

    def __str__(self):
        """可读表示：用户 - 文章 (状态)。"""
        #: 返回结果并结束当前函数
        return f'{self.user} - {self.article} ({self.status})'


class UserNote(models.Model):
    """用户笔记：文章划线高亮内容 + 个人笔记正文。"""

    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='notes', verbose_name='用户')
    #: 定义变量「article」，保存对应数据（Django 模型字段，参与建表）
    article = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'Article', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='user_notes', verbose_name='文章')
    #: 定义变量「highlight_text」，保存对应数据（Django 模型字段，参与建表）
    highlight_text = models.TextField(
        #: 定义变量「blank」，保存对应数据
        blank=True, verbose_name='划线内容')
    #: 定义变量「note_text」，保存对应数据（Django 模型字段，参与建表）
    note_text = models.TextField(verbose_name='笔记内容')
    #: 定义变量「color」，保存对应数据（Django 模型字段，参与建表）
    color = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=7, default='#fff3cd', verbose_name='高亮颜色')
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
        db_table = 'blog_user_note'
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：用户 笔记 @ 文章。"""
        #: 返回结果并结束当前函数
        return f'{self.user} 笔记 @ {self.article}'

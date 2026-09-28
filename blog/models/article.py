# -*- coding: utf-8 -*-
"""
文章领域模型 —— 全站内容主模型及其周边（历史版本、分享、定时发布、短链）。

本文件从原 ``blog/models.py`` 拆出，含以下模型：

- :class:`ArticleQuerySet`：文章自定义查询集，把常用过滤封装成链式方法；
- :class:`Article`：全站**唯一内容主模型**，文章 / 笔记 / 独立页面以 ``kind``
  区分，草稿 / 待审核 / 已发布以 ``status`` 区分；富文本 HTML 整体存于
  ``content``，不另建表格子表；
- :class:`ArticleHistory`：文章编辑历史版本（修订快照，支持对照）；
- :class:`ArticleShare`：文章分享记录（追踪分享渠道 / IP）；
- :class:`ScheduledPost`：定时发布安排（草稿 + 计划时间）；
- :class:`ShortLink`：6 位短码到原始长 URL 的映射。

表名（blog_article 等）与拆分前完全一致，不产生数据库结构变更；跨文件外键
（作者、分类、系列）一律以字符串引用，由 Django 应用注册表解析，避免循环导入。

维护注意点（极重要）
--------------------
1. 手动摘要字段名是 ``excerpt_field``；``excerpt`` 是 @property（手写优先、否则
   从正文自动截取），切勿把二者混淆；
2. 文章写操作（创建 / 发布 / 编辑 / 删除）必须保留 Django 信号链：内容审核、
   状态流转、缓存失效、搜索索引、计数重算都挂在信号上，不可绕过；
3. ``status`` 新增 PENDING 待审核态：普通作者投稿默认进入，审核通过才公开；
4. 软删除用 is_deleted/deleted_at，前台列表统一叠加 alive()，回收站可恢复；
5. 计数冗余字段（views/likes/comment_count/share_count 等）用 F() 原子更新或
   由信号按存活数据重算，避免并发漂移。
"""
import re
from datetime import timedelta

from django.db import models
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone


# ============================ 自定义查询集 ============================
class ArticleQuerySet(models.QuerySet):
    """文章常用查询集合，通过 ``ArticleQuerySet.as_manager()`` 挂为默认管理器。

    既保留 filter/all/get 等原生能力，又新增语义化链式方法；除 ``popular``
    返回切片列表外，其余方法均返回新 QuerySet 以便继续链式调用。
    """

    def published(self):
        """仅返回已发布文章。"""
        return self.filter(status=self.model.Status.PUBLISHED)

    def draft(self):
        """仅返回草稿文章。"""
        return self.filter(status=self.model.Status.DRAFT)

    def pending(self):
        """仅返回待审核文章（审核队列主数据源）。"""
        return self.filter(status=self.model.Status.PENDING)

    def alive(self):
        """仅返回未软删除内容（前台各列表统一叠加）。"""
        return self.filter(is_deleted=False)

    def dead(self):
        """仅返回已软删除内容（回收站）。"""
        return self.filter(is_deleted=True)

    def scheduled(self):
        """仅返回「草稿 + 未来发布时间」的定时文章。"""
        return self.filter(
            status=self.model.Status.DRAFT,
            published_at__isnull=False,
            published_at__gt=timezone.now())

    def pinned(self):
        """仅返回置顶文章。"""
        return self.filter(is_pinned=True)

    def recent(self, days=30):
        """返回最近 N 天内发布的文章。"""
        return self.filter(
            created_at__gte=timezone.now() - timedelta(days=days))

    def popular(self, limit=10):
        """按阅读量倒序返回热门文章（返回列表切片，不可继续链式）。"""
        return list(
            self.filter(status=self.model.Status.PUBLISHED)
            .order_by('-views')[:limit])

    def by_category(self, category):
        """按分类过滤（接受分类 id 或 Category 对象）。"""
        return self.filter(category=category)

    def by_tag(self, tag):
        """按标签过滤（接受标签 id 或 Tag 对象）。"""
        return self.filter(tags=tag)

    def with_related(self):
        """预加载作者与分类，消除列表 / 详情 N+1 查询。"""
        return self.select_related('author', 'category')

    def optimized(self):
        """列表页优化：预加载作者 / 分类 / 标签，并注解评论数。"""
        return (self.select_related('author', 'category')
                .prefetch_related('tags')
                .annotate(_comment_annot=Count('comments', distinct=True)))


# ============================ 内容主模型 ============================
class Article(models.Model):
    """统一内容主模型：文章 / 笔记 / 独立页面共用。"""

    class Kind(models.TextChoices):
        """内容类型枚举：文章、笔记、独立页面。"""

        ARTICLE = 'article', '文章'
        NOTE = 'note', '笔记'
        PAGE = 'page', '独立页面'

    class Status(models.TextChoices):
        """发布状态枚举：草稿、待审核、已发布。"""

        DRAFT = 'draft', '草稿'
        PENDING = 'pending', '待审核'
        PUBLISHED = 'published', '已发布'

    # ---- 基础内容 ----
    title = models.CharField(max_length=200, verbose_name='标题')
    content = models.TextField(
        blank=True, default='', verbose_name='富文本正文')
    author = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='articles', verbose_name='作者')
    category = models.ForeignKey(
        'Category', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='articles', verbose_name='分类')
    tags = models.ManyToManyField(
        'Tag', blank=True, related_name='articles', verbose_name='标签')

    # ---- 计数冗余 ----
    views = models.PositiveIntegerField(default=0, verbose_name='阅读量')
    likes = models.PositiveIntegerField(default=0, verbose_name='点赞数')
    comment_count = models.PositiveIntegerField(
        default=0, verbose_name='评论数')
    share_count = models.PositiveIntegerField(
        default=0, verbose_name='分享次数')
    dislike_count = models.PositiveIntegerField(
        default=0, verbose_name='踩数')

    # ---- 媒体 / 摘要 ----
    cover_image = models.ImageField(
        upload_to='covers/', null=True, blank=True, verbose_name='封面图')
    # 注意：手动摘要字段是 excerpt_field；excerpt 是下方 property
    excerpt_field = models.TextField(
        blank=True, default='', verbose_name='手动摘要')

    # ---- 状态 / 分类 ----
    status = models.CharField(
        max_length=10, choices=Status.choices,
        default=Status.PUBLISHED, verbose_name='状态')
    kind = models.CharField(
        max_length=10, choices=Kind.choices,
        default=Kind.ARTICLE, verbose_name='内容类型')

    # ---- 时间 ----
    created_at = models.DateTimeField(
        default=timezone.now, verbose_name='发布时间')
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name='更新时间')
    published_at = models.DateTimeField(
        null=True, blank=True, verbose_name='定时发布时间')

    # ---- 运营标记 ----
    is_pinned = models.BooleanField(default=False, verbose_name='是否置顶')
    is_featured = models.BooleanField(
        default=False, verbose_name='是否精华')
    is_hot = models.BooleanField(default=False, verbose_name='是否热门')

    # ---- 访问密码（哈希存储，空表示公开）----
    password = models.CharField(
        max_length=100, blank=True, default='', verbose_name='访问密码')

    # ---- 评分冗余 ----
    rating_avg = models.FloatField(default=0, verbose_name='平均评分')
    rating_count = models.PositiveIntegerField(
        default=0, verbose_name='评分人数')

    # ---- 系列 ----
    series = models.ForeignKey(
        'Series', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='articles', verbose_name='所属系列')
    series_order = models.PositiveIntegerField(
        default=0, verbose_name='系列中序号')

    # ---- 软删除 ----
    is_deleted = models.BooleanField(
        default=False, verbose_name='已软删除')
    deleted_at = models.DateTimeField(
        null=True, blank=True, verbose_name='删除时间')

    # 挂载自定义查询集为默认管理器
    objects = ArticleQuerySet.as_manager()

    class Meta:
        db_table = 'blog_article'
        verbose_name = '文章'
        verbose_name_plural = '文章'
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['status', '-created_at'],
                         name='idx_art_status_ct'),
            models.Index(fields=['is_pinned', '-created_at'],
                         name='idx_art_pinned_ct'),
            models.Index(fields=['is_featured', '-created_at'],
                         name='idx_art_feat_ct'),
            models.Index(fields=['is_hot', '-created_at'],
                         name='idx_art_hot_ct'),
            models.Index(fields=['category', '-created_at'],
                         name='idx_art_cat_ct'),
            models.Index(fields=['title'], name='idx_art_title'),
            models.Index(fields=['kind', 'status', '-created_at'],
                         name='idx_art_kind_st_ct')]
        constraints = [
            models.CheckConstraint(
                condition=Q(rating_avg__gte=0),
                name='ck_art_rating_avg_nn'),
            models.CheckConstraint(
                condition=Q(rating_count__gte=0),
                name='ck_art_rating_cnt_nn')]
        get_latest_by = 'created_at'
        permissions = [
            ('can_review_comment', '可以审核评论')]

    # ---------------- 属性 ----------------
    @property
    def is_scheduled(self):
        """是否为定时发布中的草稿：草稿且有未来发布时间。"""
        return (self.status == Article.Status.DRAFT
                and self.published_at is not None
                and self.published_at > timezone.now())

    @property
    def is_protected(self):
        """是否需要访问密码：password 非空即视为加密文章。"""
        return bool(self.password)

    @property
    def is_scheduled_pending(self):
        """是否为「定时到点、因开启审核而转入待审核」的文章。"""
        return (self.status == Article.Status.PENDING
                and self.published_at is not None
                and self.published_at <= timezone.now())

    @property
    def excerpt(self, length=180):
        """列表摘要：手写 excerpt_field 优先，否则从正文自动截取。

        Args:
            length: 自动摘要最大长度，默认 180。

        Returns:
            str: 纯文本摘要，超长追加省略号。
        """
        # 手写摘要优先（去除残留 HTML）
        if self.excerpt_field and self.excerpt_field.strip():
            manual = re.sub(r'<[^>]+>', '', self.excerpt_field or '')
            manual = re.sub(r'\s+', ' ', manual).strip()
            return manual[:length] + ('…' if len(manual) > length else '')
        # 否则剥离正文 HTML、合并空白后截取
        text = re.sub(r'<[^>]+>', '', self.content or '')
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:length] + ('…' if len(text) > length else '')

    @property
    def plain_text(self):
        """正文纯文本：剥离 HTML 并合并空白。"""
        text = re.sub(r'<[^>]+>', '', self.content or '')
        return re.sub(r'\s+', ' ', text).strip()

    @property
    def word_count(self):
        """字数：CJK 字符每个计 1，连续英文 / 数字序列每个单词计 1。"""
        text = self.plain_text
        chinese = len(re.findall(r'[\u4e00-\u9fff]', text))
        english = len(re.findall(r'[a-zA-Z0-9]+', text))
        return chinese + english

    @property
    def reading_time(self):
        """阅读时长：按 300 字 / 分钟估算，不足 1 分钟按 1 分钟。"""
        minutes = max(1, round(self.word_count / 300))
        return f'约{minutes}分钟'

    @property
    def estimated_reading(self):
        """预估阅读分钟数（整数，最少 1），供数字角标展示。"""
        return max(1, round(self.word_count / 300))

    @property
    def comment_count_display(self):
        """评论数友好显示，如「12条评论」。"""
        return f'{self.comment_count}条评论'

    @property
    def like_count_display(self):
        """点赞数友好显示，如「36赞」。"""
        return f'{self.likes}赞'

    @property
    def view_count_display(self):
        """阅读量友好显示：过万缩写 w，过千缩写 k。"""
        if self.views >= 10000:
            return f'{self.views / 10000:.1f}w'
        if self.views >= 1000:
            return f'{self.views / 1000:.1f}k'
        return str(self.views)

    @property
    def rating_display(self):
        """评分友好显示，如「⭐4.5」，无评分返回「暂无评分」。"""
        if self.rating_count:
            return f'⭐{self.rating_avg:.1f}'
        return '暂无评分'

    @property
    def is_new_24h(self):
        """是否为最近 24 小时内发布的新文章。"""
        return (timezone.now() - self.created_at).total_seconds() < 86400

    @property
    def is_recent_week(self):
        """是否为最近一周内发布的文章。"""
        return (timezone.now() - self.created_at).days <= 7

    @property
    def has_cover(self):
        """是否已上传封面图。"""
        return bool(self.cover_image)

    @property
    def has_excerpt(self):
        """是否手写了摘要（excerpt_field 非空白）。"""
        return bool(self.excerpt_field and self.excerpt_field.strip())

    # ---------------- 方法 ----------------
    def __str__(self):
        """可读表示：返回文章标题。"""
        return self.title

    def get_absolute_url(self):
        """文章详情 URL，形如 /article/<pk>/。"""
        return reverse('article_detail', args=[self.pk])

    def get_related_by_tags(self, limit=5):
        """取共享标签的其他已发布文章，按共享标签数、时间降序。"""
        tag_ids = list(self.tags.values_list('id', flat=True))
        if not tag_ids:
            return []
        return list(
            Article.objects.published()
            .filter(tags__in=tag_ids).exclude(pk=self.pk)
            .annotate(shared=Count('tags', distinct=True))
            .order_by('-shared', '-created_at')[:limit])

    def get_related_by_category(self, limit=5):
        """取同分类下其他已发布文章（时间倒序）。"""
        if not self.category_id:
            return []
        return list(
            Article.objects.published()
            .filter(category_id=self.category_id)
            .exclude(pk=self.pk)
            .order_by('-created_at')[:limit])

    def get_word_count_display(self):
        """友好字数：过千缩写 1.2k字，否则显示整数。"""
        if self.word_count >= 1000:
            return f'约{self.word_count / 1000:.1f}k字'
        return f'{self.word_count}字'

    def get_reading_time_display(self):
        """友好阅读时长（复用 reading_time）。"""
        return self.reading_time

    def get_status_display_cn(self):
        """状态中文：定时发布中 / 草稿 / 待审核 / 已发布。"""
        if self.is_scheduled:
            return '定时发布中'
        return dict(Article.Status.choices).get(self.status, self.status)

    def get_kind_display_cn(self):
        """内容类型中文：文章 / 笔记 / 独立页面。"""
        return dict(Article.Kind.choices).get(self.kind, self.kind)

    def is_editable_by(self, user):
        """是否可被该用户编辑：作者本人或管理员。"""
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        return bool(user.is_staff or user.pk == self.author_id)

    def can_view_by(self, user):
        """是否可被该用户查看：已发布放行；草稿 / 待审核仅作者 / 管理员。"""
        if self.status == Article.Status.PUBLISHED:
            return True
        return bool(user and getattr(user, 'is_authenticated', False)
                    and (user.is_staff or user.pk == self.author_id))

    def get_cover_url(self):
        """封面 URL；无封面或文件缺失返回空串（前端渐变占位）。"""
        if not self.cover_image:
            return ''
        try:
            return self.cover_image.url
        except (ValueError, AttributeError):
            return ''

    def get_excerpt_or_auto(self, length=180, with_more=False):
        """摘要：手写优先、否则自动截取；可选强制追加省略号。"""
        text = self.excerpt
        if with_more and len((self.plain_text or '')) > length \
                and '…' not in text:
            return text.rstrip('…') + '…'
        return text


# ============================ 文章历史版本 ============================
class ArticleHistory(models.Model):
    """文章编辑历史版本（修订快照，支持版本对照）。"""

    article = models.ForeignKey(
        Article, on_delete=models.CASCADE,
        related_name='history_versions', verbose_name='文章')
    editor = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True,
        verbose_name='编辑者')
    title = models.CharField(max_length=200, verbose_name='标题快照')
    content = models.TextField(verbose_name='内容快照')
    excerpt = models.TextField(blank=True, verbose_name='摘要快照')
    version = models.PositiveIntegerField(
        default=1, verbose_name='版本号')
    change_summary = models.CharField(
        max_length=300, blank=True, verbose_name='修改说明')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='时间')

    class Meta:
        db_table = 'blog_article_history'
        ordering = ['-version']
        indexes = [
            models.Index(fields=['article', '-version'])]

    def __str__(self):
        """可读表示：文章 v版本号。"""
        return f'{self.article} v{self.version}'


# ============================ 文章分享记录 ============================
class ArticleShare(models.Model):
    """文章分享记录（追踪分享渠道与来源 IP）。"""

    article = models.ForeignKey(
        Article, on_delete=models.CASCADE,
        related_name='shares', verbose_name='文章')
    user = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='用户')
    platform = models.CharField(max_length=20, verbose_name='平台')
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, verbose_name='IP')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='时间')

    class Meta:
        db_table = 'blog_article_share'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['article', 'platform'])]

    def __str__(self):
        """可读表示：文章 分享到 平台。"""
        return f'{self.article} 分享到 {self.platform}'


# ============================ 定时发布安排 ============================
class ScheduledPost(models.Model):
    """定时发布安排（文章一对一，记录计划时间与实际发布时间）。"""

    article = models.OneToOneField(
        Article, on_delete=models.CASCADE,
        related_name='scheduled', verbose_name='文章')
    scheduled_at = models.DateTimeField(verbose_name='计划发布时间')
    is_published = models.BooleanField(
        default=False, verbose_name='是否已发布')
    published_at = models.DateTimeField(
        null=True, blank=True, verbose_name='实际发布时间')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'blog_scheduled_post'
        ordering = ['scheduled_at']
        indexes = [
            models.Index(fields=['is_published', 'scheduled_at'])]

    def __str__(self):
        """可读表示：文章 计划 时间。"""
        return f'{self.article} 计划 {self.scheduled_at}'


# ============================ 短链接 ============================
class ShortLink(models.Model):
    """短链接映射：6 位短码 -> 原始长 URL，跳转时 clicks+1。"""

    code = models.CharField(
        max_length=10, unique=True, verbose_name='短码')
    original_url = models.URLField(max_length=500, verbose_name='原始链接')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='创建时间')
    clicks = models.PositiveIntegerField(
        default=0, verbose_name='点击次数')

    class Meta:
        db_table = 'blog_short_link'
        verbose_name = '短链接'
        verbose_name_plural = '短链接'
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：短码 -> 原始链接前 40 字。"""
        return f'{self.code} -> {self.original_url[:40]}'

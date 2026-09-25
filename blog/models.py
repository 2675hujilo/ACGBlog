"""
博客数据模型（去维基化重构版）。

本文件定义博客应用的全部 ORM 模型，对应数据库中的数据表：

- Article 为全站唯一内容主模型，文章 / 笔记 / 独立页面以 kind 区分；
- 富文本（含表格 HTML、图片）整体存于 content 字段，表格不另建子表；
- EditLog 仅为轻量修改日志：修改人 + 修改时间，不做 diff、不保存历史副本；
- AccessLog 记录每次 HTTP 请求的访问明细，用于流量分析。
"""
from __future__ import annotations

import logging
import re
from datetime import timedelta
from typing import Any, Optional

from django.contrib.auth.hashers import identify_hasher, make_password
from django.contrib.auth.models import AbstractUser
from django.core.cache import cache
from django.db import models
from django.db.models import Count, Q
from django.db.models.signals import (m2m_changed, post_delete, post_save,
                                     pre_delete, pre_save)
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone

# 第2轮迭代#1 起：模型模块级 logger，供信号处理记录关键事件
logger = logging.getLogger(__name__)


# 迭代#31: User模型类docstring
class User(AbstractUser):
    """站内用户模型（继承 Django 内置 AbstractUser，在其基础上扩展博客字段）。

    该模型通过 ``settings.AUTH_USER_MODEL`` 指定为项目的认证用户表，
    因此所有外键关联（文章作者等）均指向本表。

    扩展字段:
        nickname: 前台展示昵称，为空时回退到 username。
        avatar: 用户头像图片（ImageField）。
        introduction: 个人简介，展示在关于页 / 侧边栏。
    """
    # 昵称：用于前台展示；为空时回退到 username
    nickname = models.CharField(max_length=50, blank=True, verbose_name='昵称')
    # 头像图片，上传到 MEDIA_ROOT/avatars/ 下
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name='头像')
    # 个人简介，显示在关于页 / 侧边栏
    introduction = models.TextField(blank=True, verbose_name='个人介绍')

    # ============================ 第5轮 B/F/H/I: 用户偏好系统 ============================
    # 主题色：purple_pink(默认紫粉)/blue_green(蓝绿)/orange_yellow(橙黄)/custom(自定义HEX)
    theme_color = models.CharField(
        max_length=20, default='purple_pink',
        choices=[('purple_pink', '紫粉'), ('blue_green', '蓝绿'),
                 ('orange_yellow', '橙黄'), ('custom', '自定义')],
        verbose_name='主题色')
    # 自定义主题色 HEX 值（theme_color=custom 时生效）
    custom_theme_color = models.CharField(
        max_length=7, blank=True, default='#a855f7', verbose_name='自定义主题色HEX')
    # 字号档位：small/medium(默认)/large/xlarge
    font_size = models.CharField(
        max_length=10, default='medium',
        choices=[('small', '小'), ('medium', '中'), ('large', '大'), ('xlarge', '超大')],
        verbose_name='字号')
    # 行高：tight(紧凑)/normal(默认)/relaxed(宽松)
    line_height = models.CharField(
        max_length=10, default='normal',
        choices=[('tight', '紧凑'), ('normal', '正常'), ('relaxed', '宽松')],
        verbose_name='行高')
    # 字体族：sans(默认无衬线)/serif(衬线)/mono(等宽)
    font_family = models.CharField(
        max_length=10, default='sans',
        choices=[('sans', '无衬线'), ('serif', '衬线'), ('mono', '等宽')],
        verbose_name='字体')
    # 动效开关（默认开启）
    effects_enabled = models.BooleanField(default=True, verbose_name='动效开关')
    # 音效开关（默认关闭）
    sound_enabled = models.BooleanField(default=False, verbose_name='音效开关')
    # 护眼模式（默认关闭）
    eye_protection = models.BooleanField(default=False, verbose_name='护眼模式')
    # AMOLED 纯黑暗黑模式（默认关闭）
    amoled_dark = models.BooleanField(default=False, verbose_name='纯黑暗黑')
    # 最近活跃时间：由在线状态中间件每 5 分钟刷新一次，用于在线状态展示
    last_active = models.DateTimeField(auto_now=True, verbose_name='最近活跃')
    # 生日（可空，用于生日彩蛋）
    birthday = models.DateField(null=True, blank=True, verbose_name='生日')
    # 个人主页背景图
    background_image = models.ImageField(
        upload_to='user_bg/', null=True, blank=True, verbose_name='个人主页背景')
    # 个性签名（最多 200 字）
    signature = models.CharField(
        max_length=200, blank=True, default='', verbose_name='个性签名')

    # 迭代#32: User.Meta类docstring
    class Meta:
        """模型元信息：自定义数据库表名与中文 verbose_name。

        Attributes:
            db_table: 自定义表名 blog_user，避免默认 auth_user 命名冲突。
            verbose_name: 后台单数显示名。
            verbose_name_plural: 后台复数显示名。
        """
        db_table = 'blog_user'          # 自定义数据库表名，避免默认命名
        verbose_name = '用户'
        verbose_name_plural = '用户'

    # 迭代#33: User.__str__方法docstring
    def __str__(self) -> str:
        """对象的可读表示：优先展示昵称，无昵称时展示登录名。

        Returns:
            str: 用于 admin 列表与外键下拉的显示文本。
        """
        return self.nickname or self.username


# 迭代#34: Category模型类docstring
class Category(models.Model):
    """分类（每篇文章归属一个分类）。

    与 Article 为一对多关系：一个分类下可有多篇文章，文章分类可被置空。
    分类名全局唯一，用于导航与归档聚合。

    Attributes:
        name: 分类名（唯一）。
        description: 分类介绍，可在分类页展示。
        icon: emoji 图标字符，默认 📁。
        created_at: 创建时间（自动填充）。
    """
    # 分类名全局唯一
    name = models.CharField(max_length=80, unique=True, verbose_name='分类名')
    # 分类的简要介绍，可在分类页展示
    description = models.TextField(blank=True, default='', verbose_name='分类介绍')
    # 15. 分类图标（emoji 字符）：在分类页 / 导航栏分类名前展示，默认 📁
    icon = models.CharField(max_length=10, blank=True, default='📁', verbose_name='图标(emoji)')
    # 分类创建时间，自动填充为首次保存时间
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    # 迭代#35: Category.Meta类docstring
    class Meta:
        """模型元信息：表名、中文显示名与默认排序。"""
        db_table = 'blog_category'
        verbose_name = '分类'
        verbose_name_plural = '分类'
        ordering = ['name']   # 默认按分类名升序排列

    # 迭代#36: Category.__str__方法docstring
    def __str__(self) -> str:
        """对象的可读表示：直接返回分类名。

        Returns:
            str: 分类名字符串。
        """
        return self.name


# 迭代#37: Tag模型类docstring
class Tag(models.Model):
    """标签（一篇文章可挂多个标签）。

    与 Article 为多对多关系，标签独立于文章存在，便于聚合统计与标签云展示。
    标签名全局唯一。

    Attributes:
        name: 标签名（唯一）。
        created_at: 创建时间（自动填充）。
    """
    # 标签名全局唯一
    name = models.CharField(max_length=50, unique=True, verbose_name='标签名')
    # 标签创建时间，自动填充为首次保存时间
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    # 迭代#38: Tag.Meta类docstring
    class Meta:
        """模型元信息：表名、中文显示名与默认排序。"""
        db_table = 'blog_tag'
        verbose_name = '标签'
        verbose_name_plural = '标签'
        ordering = ['name']   # 默认按标签名升序排列

    # 迭代#39: Tag.__str__方法docstring
    def __str__(self) -> str:
        """对象的可读表示：直接返回标签名。

        Returns:
            str: 标签名字符串。
        """
        return self.name


# 第2轮迭代#31: 自定义文章查询集 published 方法
class ArticleQuerySet(models.QuerySet):
    """文章自定义 QuerySet：把常用过滤封装为可链式调用的方法。

    通过 ``ArticleQuerySet.as_manager()`` 挂为默认管理器，
    既保留 ``filter/all/get`` 等原生能力，又新增语义化的链式方法。
    所有方法均返回新 QuerySet（``popular`` 例外，返回切片列表）。
    """

    def published(self):
        # 第2轮迭代#31: 仅返回已发布文章
        return self.filter(status=self.model.Status.PUBLISHED)

    def draft(self):
        # 第2轮迭代#32: 仅返回草稿文章
        return self.filter(status=self.model.Status.DRAFT)

    def pending(self):
        # bug8: 仅返回待审核文章（审核队列主数据源）
        return self.filter(status=self.model.Status.PENDING)

    def alive(self):
        # bug8: 仅返回未软删除的内容（前台各列表统一叠加）
        return self.filter(is_deleted=False)

    def dead(self):
        # bug8: 仅返回已软删除的内容（回收站）
        return self.filter(is_deleted=True)

    def scheduled(self):
        # 第2轮迭代#33: 仅返回"草稿且未来发布时间"的定时文章
        return self.filter(
            status=self.model.Status.DRAFT,
            published_at__isnull=False,
            published_at__gt=timezone.now(),
        )

    def pinned(self):
        # 第2轮迭代#34: 仅返回置顶文章
        return self.filter(is_pinned=True)

    def recent(self, days=30):
        # 第2轮迭代#35: 返回最近 N 天内发布的文章
        return self.filter(created_at__gte=timezone.now() - timedelta(days=days))

    def popular(self, limit=10):
        # 第2轮迭代#36: 按阅读量倒序返回热门文章（返回列表切片）
        return list(
            self.filter(status=self.model.Status.PUBLISHED)
            .order_by('-views')[:limit]
        )

    def by_category(self, category):
        # 第2轮迭代#37: 按分类过滤（接受分类 id 或 Category 对象）
        return self.filter(category=category)

    def by_tag(self, tag):
        # 第2轮迭代#38: 按标签过滤（接受标签 id 或 Tag 对象）
        return self.filter(tags=tag)

    def with_related(self):
        # 第2轮迭代#39: 预加载作者与分类，消除列表/详情 N+1 查询
        return self.select_related('author', 'category')

    def optimized(self):
        # 第2轮迭代#40: 列表页优化：预加载关联 + 注解评论数
        return (self.select_related('author', 'category')
                .prefetch_related('tags')
                .annotate(_comment_annot=Count('comments', distinct=True)))


# 迭代#40: Article模型类docstring
class Article(models.Model):
    """统一内容主模型：文章 / 笔记 / 独立页面共用。

    通过 ``kind`` 字段区分内容类型，通过 ``status`` 控制是否对前台可见。
    富文本 HTML 整体存放在 ``content`` 中，不拆分表格为子表。

    核心字段:
        title: 文章标题（必填，最长 200 字）。
        content: 富文本正文 HTML。
        author: 作者外键（CASCADE 删除）。
        category: 分类外键（SET_NULL，可空）。
        tags: 多对多标签。
        status: 草稿 / 已发布。
        kind: 文章 / 笔记 / 独立页面。
    """

    # 迭代#41: Article.Kind枚举docstring
    class Kind(models.TextChoices):
        """内容类型枚举：文章、笔记、独立页面。

        Values:
            ARTICLE: 普通博客文章。
            NOTE: 短笔记。
            PAGE: 独立静态页面（如关于页）。
        """
        ARTICLE = 'article', '文章'
        NOTE = 'note', '笔记'
        PAGE = 'page', '独立页面'

    # 迭代#42: Article.Status枚举docstring
    class Status(models.TextChoices):
        """发布状态枚举：草稿、待审核、已发布。

        Values:
            DRAFT: 草稿状态，仅作者本人可见，前台列表不展示。
            PENDING: 待审核，新文章默认状态；仅作者本人与管理员可见，
                审核通过（转为 PUBLISHED）后其他读者才可见。
            PUBLISHED: 已发布状态，前台对所有人可见。
        """
        DRAFT = 'draft', '草稿'
        PENDING = 'pending', '待审核'
        PUBLISHED = 'published', '已发布'

    # 文章标题
    title = models.CharField(max_length=200, verbose_name='标题')
    # 富文本正文（CKEditor 产出的 HTML），可为空
    content = models.TextField(blank=True, default='', verbose_name='富文本正文')
    # 作者：外键指向 User；删除作者时级联删除其文章
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='articles', verbose_name='作者')
    # 分类：分类被删除时置空（文章仍保留），允许为空
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='articles', verbose_name='分类')
    # 标签：多对多关联，一篇文章可选择多个标签
    tags = models.ManyToManyField(Tag, blank=True, related_name='articles', verbose_name='标签')
    # 阅读量：每访问详情页自增
    views = models.PositiveIntegerField(default=0, verbose_name='阅读量')
    # 点赞数：读者通过详情页点赞按钮累加，用 session 防重复点赞
    likes = models.PositiveIntegerField(default=0, verbose_name='点赞数')
    # 评论数：冗余计数，发表 / 删除评论时原子增减，避免每次 COUNT 评论表
    comment_count = models.PositiveIntegerField(default=0, verbose_name='评论数')
    # 文章封面图：上传到 MEDIA_ROOT/covers/ 下，允许为空（无封面时前端用渐变占位）
    cover_image = models.ImageField(
        upload_to='covers/', null=True, blank=True, verbose_name='封面图')
    # 手动摘要：作者可在编辑页填写；留空时自动从正文截取（见 excerpt property）
    excerpt_field = models.TextField(blank=True, default='', verbose_name='手动摘要')
    # 状态：默认发布，草稿不在前台列表展示
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PUBLISHED, verbose_name='状态')
    # 内容类型：默认为普通文章
    kind = models.CharField(
        max_length=10, choices=Kind.choices, default=Kind.ARTICLE, verbose_name='内容类型')
    # 发布时间：手动指定（默认当前时间），不随修改自动更新
    created_at = models.DateTimeField(default=timezone.now, verbose_name='发布时间')
    # 更新时间：每次保存自动刷新为当前时间
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    # 56. 定时发布时间：为空表示立即发布；设置了未来时间且状态为草稿时，
    #     由 Celery 定时任务在到达该时间后自动转为已发布。
    published_at = models.DateTimeField(
        null=True, blank=True, verbose_name='定时发布时间')
    # 57. 是否置顶：True 时在列表中始终排在最前面（最多允许 3 篇置顶）
    is_pinned = models.BooleanField(default=False, verbose_name='是否置顶')
    # Bug1 是否精华：管理员手动设置，或作者申请、审核通过后置 True
    is_featured = models.BooleanField(default=False, verbose_name='是否精华')
    # Bug1 是否热门：管理员手动设置，或作者申请、审核通过后置 True
    is_hot = models.BooleanField(default=False, verbose_name='是否热门')
    # 58. 访问密码：为空表示公开；非空时访问详情页需先输入密码（哈希存储）
    password = models.CharField(
        max_length=100, blank=True, default='', verbose_name='访问密码')
    # 63. 评分冗余字段：平均评分与评分人数（由 Rating 表聚合后冗余写入，避免每次 COUNT/AVG）
    rating_avg = models.FloatField(default=0, verbose_name='平均评分')
    rating_count = models.PositiveIntegerField(default=0, verbose_name='评分人数')
    # 第4轮 C7: 文章分享计数：读者点击分享按钮时由 share 接口 F() 原子自增
    share_count = models.PositiveIntegerField(default=0, verbose_name='分享次数')
    # 第5轮 C1: 文章踩计数：与点赞对称，session 防重，toggle 语义
    dislike_count = models.PositiveIntegerField(default=0, verbose_name='踩数')
    # 67. 所属系列：系列被删除时置空（文章仍保留），允许为空
    series = models.ForeignKey(
        'Series', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='articles', verbose_name='所属系列')
    # 67. 文章在系列中的序号：同系列文章按该字段升序排列
    series_order = models.PositiveIntegerField(default=0, verbose_name='系列中序号')
    # 软删除（bug8）：删除操作不再物理删除，而是置 is_deleted=True 对前台隐藏；
    # deleted_at 记录删除时间，便于回收站恢复与审计。管理员可在后台彻底删除。
    is_deleted = models.BooleanField(default=False, verbose_name='已软删除')
    deleted_at = models.DateTimeField(
        null=True, blank=True, verbose_name='删除时间')

    # 第2轮迭代#31: 挂载自定义查询集为默认管理器（保留全部原生查询方法）
    objects = ArticleQuerySet.as_manager()

    # 迭代#43: Article.Meta类docstring
    class Meta:
        """模型元信息：表名、中文显示名、排序、索引、约束与自定义权限。"""
        db_table = 'blog_article'
        # 第2轮迭代#24: db_table 确认（显式表名 blog_article，避免默认前缀冲突）
        verbose_name = '文章'
        # 第2轮迭代#23: verbose_name 确认（后台中文单数/复数显示名）
        verbose_name_plural = '文章'
        # 第2轮迭代#22: ordering 确认——按发布时间倒序、再按 id 倒序，保证最新在前
        ordering = ['-created_at', '-id']
        # 第2轮迭代#21: 联合索引优化——覆盖"状态+时间""置顶+时间""分类+时间"三类高频列表查询
        # 第3轮迭代#2: 追加 title 搜索索引与"类型+状态+时间"筛选索引
        indexes = [
            models.Index(fields=['status', '-created_at'], name='idx_art_status_ct'),
            models.Index(fields=['is_pinned', '-created_at'], name='idx_art_pinned_ct'),
            models.Index(fields=['is_featured', '-created_at'], name='idx_art_feat_ct'),
            models.Index(fields=['is_hot', '-created_at'], name='idx_art_hot_ct'),
            models.Index(fields=['category', '-created_at'], name='idx_art_cat_ct'),
            models.Index(fields=['title'], name='idx_art_title'),
            models.Index(fields=['kind', 'status', '-created_at'], name='idx_art_kind_st_ct'),
        ]
        # 第2轮迭代#25: 数据库级约束——平均评分与评分人数不得为负
        constraints = [
            models.CheckConstraint(condition=Q(rating_avg__gte=0), name='ck_art_rating_avg_nn'),
            models.CheckConstraint(condition=Q(rating_count__gte=0), name='ck_art_rating_cnt_nn'),
        ]
        # 第2轮迭代#26: unique_together 确认——收藏(Favorite)与评分(Rating)已在各自 Meta 声明联合唯一
        # 第2轮迭代#27: 不启用 default_related_name——各外键已显式指定 related_name，避免反向访问命名冲突
        # 第2轮迭代#28: get_latest_by——Article.objects.latest() 默认按 created_at 取最新
        get_latest_by = 'created_at'
        # 第2轮迭代#29: order_with_respect_to 不适用——文章为平级内容，无父子层级排序需求
        # 第2轮迭代#30: 自定义权限——评论审核权限（在权限表中注册，供后台细粒度授权）
        permissions = [
            ('can_review_comment', '可以审核评论'),
        ]

    # 迭代#44: is_scheduled属性docstring完善
    # 第2轮迭代#20: is_scheduled 属性复核——草稿且存在未来发布时间即为定时发布中
    @property
    def is_scheduled(self):
        """56. 是否为"定时发布中"的草稿：草稿且设置了未来发布时间。"""
        return (self.status == Article.Status.DRAFT
                and self.published_at is not None
                and self.published_at > timezone.now())

    # 迭代#45: is_protected属性docstring完善
    @property
    def is_protected(self):
        """58. 是否需要访问密码：password 非空即视为加密文章。"""
        return bool(self.password)

    # 迭代#46: Article.__str__方法docstring
    def __str__(self) -> str:
        """对象的可读表示：返回文章标题。

        Returns:
            str: 文章标题。
        """
        return self.title

    # 迭代#47: Article.get_absolute_url方法类型提示
    # 迭代#48: Article.get_absolute_url方法docstring
    def get_absolute_url(self) -> str:
        """返回文章详情页的绝对 URL，供模板 / 重定向使用。

        Returns:
            str: 形如 ``/article/<pk>/`` 的 URL 字符串。
        """
        return reverse('article_detail', args=[self.pk])

    # 迭代#49: Article.excerpt属性类型提示
    # 迭代#50: Article.excerpt属性docstring
    @property
    def excerpt(self, length: int = 180) -> str:
        """列表摘要：优先使用手动填写的 excerpt_field，否则自动截取正文。

        若作者在编辑页填写了 ``excerpt_field``（手动摘要），直接返回其去除 HTML 后的
        纯文本；否则从富文本正文中剥离所有 HTML 标签，合并多余空白，截取前
        ``length`` 个字符，超出则追加省略号。

        Args:
            length: 自动摘要的最大长度，默认 180 字符。

        Returns:
            str: 纯文本摘要。
        """
        # 优先使用作者手写的手动摘要（去除其中可能残留的 HTML 标签）
        if self.excerpt_field and self.excerpt_field.strip():
            manual = re.sub(r'<[^>]+>', '', self.excerpt_field or '')
            manual = re.sub(r'\s+', ' ', manual).strip()
            return manual[:length] + ('…' if len(manual) > length else '')
        # 移除所有 HTML 标签
        text = re.sub(r'<[^>]+>', '', self.content or '')
        # 将连续空白（换行 / 多空格）合并为单个空格并去除首尾空白
        text = re.sub(r'\s+', ' ', text).strip()
        # 截断并按需追加省略号
        return text[:length] + ('…' if len(text) > length else '')

    # 迭代#51: Article.plain_text属性类型提示
    # 迭代#52: Article.plain_text属性docstring
    @property
    def plain_text(self) -> str:
        """正文纯文本：剥离所有 HTML 标签并合并空白，供字数 / 阅读时长统计复用。

        Returns:
            str: 去除标签后的纯文本。
        """
        text = re.sub(r'<[^>]+>', '', self.content or '')
        return re.sub(r'\s+', ' ', text).strip()

    # 迭代#53: Article.word_count属性类型提示
    # 迭代#54: Article.word_count属性docstring
    @property
    def word_count(self) -> int:
        """字数统计：中文字符按 1 字计，英文按空格分词后每个单词计 1 词。

        统计口径：
        - 连续的 CJK 表意字符（\\u4e00-\\u9fff）每个计为 1；
        - 连续的英文字母 / 数字序列按一个英文单词计。

        Returns:
            int: 总字数（中文字符数 + 英文单词数）。
        """
        text = self.plain_text
        # 统计中文字符数量
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        # 统计英文单词（连续字母数字序列）
        english_words = len(re.findall(r'[a-zA-Z0-9]+', text))
        return chinese_chars + english_words

    # 迭代#55: Article.reading_time属性类型提示
    # 迭代#56: Article.reading_time属性docstring
    @property
    def reading_time(self) -> str:
        """阅读时长估算：按 300 字/分钟的中文阅读速度计算，返回友好字符串。

        不足 1 分钟按 1 分钟计；返回形如"约 5 分钟"。

        Returns:
            str: 阅读时长描述。
        """
        minutes = max(1, round(self.word_count / 300))
        return f'约{minutes}分钟'

    # 第2轮迭代#1: 模型方法 get_related_by_tags
    def get_related_by_tags(self, limit: int = 5) -> list:
        """取与本文共享标签的其他已发布文章，按共享标签数降序、时间降序。

        Args:
            limit: 最多返回条数，默认 5。

        Returns:
            list: 相关文章列表（切片后的 QuerySet 转 list）。
        """
        tag_ids = list(self.tags.values_list('id', flat=True))
        if not tag_ids:
            return []
        return list(
            Article.objects.published()
            .filter(tags__in=tag_ids)
            .exclude(pk=self.pk)
            .annotate(shared_tags=Count('tags', distinct=True))
            .order_by('-shared_tags', '-created_at')[:limit]
        )

    # 第2轮迭代#2: 模型方法 get_related_by_category
    def get_related_by_category(self, limit: int = 5) -> list:
        """取同分类下的其他已发布文章（按发布时间倒序）。

        Args:
            limit: 最多返回条数，默认 5。

        Returns:
            list: 同分类相关文章列表。
        """
        if not self.category_id:
            return []
        return list(
            Article.objects.published()
            .filter(category_id=self.category_id)
            .exclude(pk=self.pk)
            .order_by('-created_at')[:limit]
        )

    # 第2轮迭代#3: 模型方法 get_word_count_display
    def get_word_count_display(self) -> str:
        """友好字数显示：过千缩写为 '1.2k字'，否则显示整数字数。"""
        n = self.word_count
        if n >= 1000:
            return f'约{n / 1000:.1f}k字'
        return f'{n}字'

    # 第2轮迭代#4: 模型方法 get_reading_time_display
    def get_reading_time_display(self) -> str:
        """友好阅读时长显示（复用 reading_time，统一对外接口）。"""
        return self.reading_time

    # 第2轮迭代#5: 模型方法 get_status_display_cn
    def get_status_display_cn(self) -> str:
        """状态中文显示：定时中 / 草稿 / 已发布。"""
        if self.is_scheduled:
            return '定时发布中'
        return dict(Article.Status.choices).get(self.status, self.status)

    # 第2轮迭代#6: 模型方法 get_kind_display_cn
    def get_kind_display_cn(self) -> str:
        """内容类型中文显示：文章 / 笔记 / 独立页面。"""
        return dict(Article.Kind.choices).get(self.kind, self.kind)

    # 第2轮迭代#7: 模型方法 is_editable_by
    def is_editable_by(self, user) -> bool:
        """判断用户是否可编辑本文：作者本人或管理员（is_staff）。

        Args:
            user: 当前请求用户（可能为匿名）。

        Returns:
            bool: 可编辑返回 True。
        """
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        return bool(user.is_staff or user.pk == self.author_id)

    # 第2轮迭代#8: 模型方法 can_view_by
    def can_view_by(self, user) -> bool:
        """判断用户是否可查看本文：已发布直接放行；草稿仅作者 / 管理员可见。

        Args:
            user: 当前请求用户。

        Returns:
            bool: 可查看返回 True。
        """
        if self.status == Article.Status.PUBLISHED:
            return True
        return bool(user and getattr(user, 'is_authenticated', False)
                    and (user.is_staff or user.pk == self.author_id))

    # 第2轮迭代#9: 模型方法 get_cover_url
    def get_cover_url(self) -> str:
        """返回封面图访问 URL；无封面或文件缺失时返回空串（前端用渐变占位）。"""
        if not self.cover_image:
            return ''
        try:
            return self.cover_image.url
        except (ValueError, AttributeError):
            return ''

    # 第2轮迭代#10: 模型方法 get_excerpt_or_auto
    def get_excerpt_or_auto(self, length: int = 180, with_more: bool = False) -> str:
        """返回摘要：手写摘要优先，否则自动截取；可选追加"…"阅读更多提示。

        Args:
            length: 自动摘要最大长度。
            with_more: 是否在超长时追加省略号。

        Returns:
            str: 纯文本摘要。
        """
        text = self.excerpt
        if with_more and len((self.plain_text or '')) > length and '…' not in text:
            return text.rstrip('…') + '…'
        return text

    # 第2轮迭代#11: 模型属性 estimated_reading
    @property
    def estimated_reading(self) -> int:
        """预估阅读分钟数（整数，最少 1 分钟），供模板数字角标展示。"""
        return max(1, round(self.word_count / 300))

    # 第2轮迭代#12: 模型属性 comment_count_display
    @property
    def comment_count_display(self) -> str:
        """评论数友好显示：如 '12条评论'。"""
        return f'{self.comment_count}条评论'

    # 第2轮迭代#13: 模型属性 like_count_display
    @property
    def like_count_display(self) -> str:
        """点赞数友好显示：如 '36赞'。"""
        return f'{self.likes}赞'

    # 第2轮迭代#14: 模型属性 view_count_display
    @property
    def view_count_display(self) -> str:
        """阅读量友好显示：过万缩写 '1.2w'，过千缩写 '1.2k'。"""
        v = self.views
        if v >= 10000:
            return f'{v / 10000:.1f}w'
        if v >= 1000:
            return f'{v / 1000:.1f}k'
        return str(v)

    # 第2轮迭代#15: 模型属性 rating_display
    @property
    def rating_display(self) -> str:
        """评分友好显示：如 '⭐4.5'，无评分时返回'暂无评分'。"""
        if self.rating_count:
            return f'⭐{self.rating_avg:.1f}'
        return '暂无评分'

    # 第2轮迭代#16: 模型属性 is_new_24h
    @property
    def is_new_24h(self) -> bool:
        """是否为最近 24 小时内发布的新文章。"""
        return (timezone.now() - self.created_at).total_seconds() < 86400

    # 第2轮迭代#17: 模型属性 is_recent_week
    @property
    def is_recent_week(self) -> bool:
        """是否为最近一周内发布的文章。"""
        return (timezone.now() - self.created_at).days <= 7

    # 第2轮迭代#18: 模型属性 has_cover
    @property
    def has_cover(self) -> bool:
        """是否已上传封面图。"""
        return bool(self.cover_image)

    # 第2轮迭代#19: 模型属性 has_excerpt
    @property
    def has_excerpt(self) -> bool:
        """是否手写了摘要（excerpt_field 非空白）。"""
        return bool(self.excerpt_field and self.excerpt_field.strip())


# 迭代#57: Comment模型类docstring
class Comment(models.Model):
    """文章评论：支持点赞、审核开关与楼中楼嵌套回复（parent_comment 自关联）。

    - 顶级评论 ``parent_comment=None`` 直接挂在文章下；
    - 回复评论 ``parent_comment`` 指向同文章下的某条评论，形成嵌套树；
    - ``is_approved`` 控制是否前台可见（默认自动通过，可在后台关闭）；
    - ``likes`` 为点赞冗余计数，点赞接口用 session 防重复；
    - 文章侧的 ``Article.comment_count`` 为冗余计数，发表 / 删除时原子维护。
    """
    # 所属文章：文章删除时级联删除其全部评论
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name='comments', verbose_name='文章')
    # 评论作者：用户删除时级联删除其评论
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='comments', verbose_name='评论人')
    # 评论内容（已在视图层用 bleach 净化为少量安全行内标签的 HTML）
    content = models.TextField(verbose_name='评论内容')
    # 父评论：自关联，空表示顶级评论；删除父评论时级联删除其全部回复
    parent_comment = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.CASCADE,
        related_name='replies', verbose_name='父评论（支持回复嵌套）')
    # 点赞数：评论点赞接口累加
    likes = models.PositiveIntegerField(default=0, verbose_name='点赞数')
    # 是否审核通过：False 时前台不显示，后台可批量审核
    is_approved = models.BooleanField(default=True, verbose_name='是否审核通过')
    # 第5轮 C5: 评论配图（可选，上传到 MEDIA_ROOT/comment_images/）
    image = models.ImageField(
        upload_to='comment_images/', null=True, blank=True, verbose_name='评论图片')
    # 第5轮 C6: 长评论是否折叠（由视图按长度自动标记或后台人工折叠）
    is_folded = models.BooleanField(default=False, verbose_name='是否折叠')
    # 第5轮 C13: 是否已被举报（收到举报后置 True，供后台优先审核）
    reported = models.BooleanField(default=False, verbose_name='已举报')
    # 评论时间：创建时自动写入
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='评论时间')
    # 软删除（bug8）：评论删除改为置 is_deleted=True 对前台隐藏，
    # deleted_at 记录删除时间；管理员可恢复或彻底删除。
    is_deleted = models.BooleanField(default=False, verbose_name='已软删除')
    deleted_at = models.DateTimeField(
        null=True, blank=True, verbose_name='删除时间')

    class Meta:
        """模型元信息。"""
        db_table = 'blog_comment'
        verbose_name = '评论'
        verbose_name_plural = '评论'
        # 默认按时间倒序（最新在前），详情页展示时再按需翻转为正序
        ordering = ['-created_at']
        # 第3轮迭代#2: 高频评论查询的联合索引——
        # (article, -created_at) 文章评论列表按时间倒序；
        # (parent_comment, -created_at) 楼中楼回复按时间排序；
        # (user, -created_at) 用户评论历史按时间倒序。
        indexes = [
            models.Index(fields=['article', '-created_at'], name='idx_cmt_article_ct'),
            models.Index(fields=['parent_comment', '-created_at'], name='idx_cmt_parent_ct'),
            models.Index(fields=['user', '-created_at'], name='idx_cmt_user_ct'),
        ]

    # 迭代#58: Comment.__str__方法类型提示
    def __str__(self) -> str:
        """对象的可读表示：形如"某人 评论了《某文章》: 前20字…"。"""
        preview = (self.content or '')[:20]
        return f'{self.user} 评论了《{self.article.title}》: {preview}'

    # 迭代#59: floor_number属性docstring完善
    @property
    def floor_number(self):
        """楼层号：同文章下按评论时间正序的序号（从 1 开始）。

        通过统计该文章中"创建时间早于或等于本评论、且 id 不更大"的已通过评论数
        计算。为避免每次渲染都查询，本属性在评论列表上下文中由视图批量计算后
        注入模板（见 views.article_detail 中的 floor 映射）；此处仅作兜底。
        """
        return (Comment.objects.filter(
            article=self.article, is_approved=True,
            created_at__lt=self.created_at).count()) + 1


# 迭代#60: EditLog模型类docstring完善
class EditLog(models.Model):
    """轻量修改日志：仅记录修改人 + 修改时间（无 diff、无历史正文副本）。

    用于在文章详情页下方展示"谁在什么时候修改过"，
    不需要回滚到历史版本。
    """
    # 被修改的文章；文章删除时级联删除其修改日志
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name='edit_logs', verbose_name='文章')
    # 修改人；用户删除时级联删除其产生的日志
    editor = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='edit_logs', verbose_name='修改人')
    # 修改时间，自动填充为日志创建时刻
    edited_at = models.DateTimeField(auto_now_add=True, verbose_name='修改时间')
    # 55. 修改前的正文快照：在 article_edit 保存新内容前写入，
    #     用于详情页"查看快照"做版本对比（只查看不回滚）。
    content_snapshot = models.TextField(
        blank=True, default='', verbose_name='修改前内容快照')

    class Meta:
        """模型元信息。"""
        db_table = 'blog_edit_log'
        verbose_name = '修改日志'
        verbose_name_plural = '修改日志'
        ordering = ['-edited_at']   # 最新修改排在最前

    def __str__(self):
        """对象的可读表示：形如"某人于某时间 修改《某文章》"。"""
        return f'{self.editor} 于 {self.edited_at:%Y-%m-%d %H:%M} 修改《{self.article.title}》'

    @property
    def snapshot_preview(self):
        """55. 快照纯文本预览（前 100 字），供 Admin 列表展示。"""
        text = re.sub(r'<[^>]+>', '', self.content_snapshot or '')
        text = re.sub(r'\s+', ' ', text).strip()
        return (text[:100] + '…') if len(text) > 100 else text

    @property
    def snapshot_plain(self):
        """55. 快照纯文本全文，供快照弹窗对比展示。"""
        text = re.sub(r'<[^>]+>', '', self.content_snapshot or '')
        return re.sub(r'\s+', ' ', text).strip()


class ModerationLog(models.Model):
    """审核操作日志（bug8「审核历史」）。

    记录管理员对文章 / 评论执行的每一次审核动作（提交审核、通过、驳回、
    软删除、恢复等），形成可追溯的审核历史时间线，支持按文章或动作筛选。
    """
    class Action(models.TextChoices):
        """审核动作枚举。"""
        SUBMIT = 'submit', '提交审核'
        APPROVE = 'approve', '审核通过'
        REJECT = 'reject', '审核驳回'
        SOFT_DELETE = 'soft_delete', '删除（隐藏）'
        RESTORE = 'restore', '恢复'
        HARD_DELETE = 'hard_delete', '彻底删除'
        # Bug1：置顶 / 精华 / 热门的设置与取消
        PIN = 'pin', '置顶'
        UNPIN = 'unpin', '取消置顶'
        FEATURE = 'feature', '加精华'
        UNFEATURE = 'unfeature', '取消精华'
        HOT = 'hot', '设热门'
        UNHOT = 'unhot', '取消热门'

    # 执行审核的管理员；管理员账号删除时日志保留、外键置空
    moderator = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='moderation_logs', verbose_name='审核人')
    # 冗余审核人名字符串，账号删除后日志仍可读
    moderator_name = models.CharField(
        max_length=150, blank=True, default='', verbose_name='审核人姓名')
    # 审核动作
    action = models.CharField(
        max_length=15, choices=Action.choices, verbose_name='审核动作')
    # 审核对象类型：article / comment
    target_type = models.CharField(
        max_length=10, default='article', verbose_name='对象类型')
    # 关联文章（评论审核也记录所属文章）；文章被彻底删除时置空
    article = models.ForeignKey(
        Article, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='moderation_logs', verbose_name='所属文章')
    # 关联评论（仅评论审核）
    comment = models.ForeignKey(
        Comment, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='moderation_logs', verbose_name='关联评论')
    # 对象标题 / 摘要快照（防止对象删除后历史不可读）
    target_title = models.CharField(
        max_length=200, blank=True, default='', verbose_name='对象标题快照')
    # 审核理由 / 备注
    reason = models.TextField(blank=True, default='', verbose_name='审核理由')
    # 操作时间
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='操作时间')

    class Meta:
        db_table = 'blog_moderation_log'
        verbose_name = '审核日志'
        verbose_name_plural = '审核日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at'], name='idx_modlog_ct'),
            models.Index(fields=['article', '-created_at'], name='idx_modlog_art_ct'),
            models.Index(fields=['action'], name='idx_modlog_action'),
        ]

    def __str__(self):
        return f'{self.moderator_name} {self.get_action_display()} {self.target_type}「{self.target_title[:20]}」'


# 迭代#61: AccessLog模型类docstring完善
class AccessLog(models.Model):
    """访问日志：记录每次HTTP请求的详细信息。

    由 ``blog.middleware.AccessLogMiddleware`` 自动写入，
    用于在后台分析访问量、来源、浏览器分布等。
    """
    # 访问者 IP，允许为空（如内部测试环境无法获取）
    ip_address = models.GenericIPAddressField(verbose_name='IP地址', null=True, blank=True)
    # 登录用户外键；用户删除时置空，允许未登录访问
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='access_logs', verbose_name='用户')
    # 冗余保存用户名字符串，避免用户删除后日志丢失可读信息
    username = models.CharField(max_length=150, blank=True, default='', verbose_name='用户名')
    # 会话 session_key，便于按会话串联多次访问
    session_key = models.CharField(max_length=64, blank=True, default='', verbose_name='会话ID')
    # 请求路径（不含域名），如 /article/1/
    path = models.CharField(max_length=255, verbose_name='请求路径')
    # 完整 URL（含查询串），用于排查问题
    full_url = models.TextField(blank=True, default='', verbose_name='完整URL')
    # HTTP 方法：GET / POST 等
    method = models.CharField(max_length=10, verbose_name='请求方法')
    # 响应状态码（200/404/500 等），默认 0 表示未记录
    status_code = models.PositiveIntegerField(default=0, verbose_name='响应状态码')
    # 请求处理耗时（毫秒）
    duration_ms = models.FloatField(default=0, verbose_name='耗时(毫秒)')
    # HTTP Referer 来源页
    referer = models.TextField(blank=True, default='', verbose_name='来源页')
    # 浏览器 User-Agent 原始字符串
    user_agent = models.TextField(blank=True, default='', verbose_name='User-Agent')
    # 从 UA 解析出的浏览器名（如 Chrome）
    browser = models.CharField(max_length=100, blank=True, default='', verbose_name='浏览器')
    # 从 UA 解析出的操作系统（如 Windows 10）
    os = models.CharField(max_length=100, blank=True, default='', verbose_name='操作系统')
    # 处理该请求的视图函数路径
    view_func = models.CharField(max_length=200, blank=True, default='', verbose_name='视图函数')
    # 视图位置参数（URL 中捕获的 pk 等），序列化存储
    view_args = models.TextField(blank=True, default='', verbose_name='视图位置参数')
    # 视图关键字参数，序列化存储
    view_kwargs = models.TextField(blank=True, default='', verbose_name='视图关键字参数')
    # 访问时间，自动填充
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='访问时间')

    class Meta:
        """模型元信息。"""
        db_table = 'blog_access_log'
        verbose_name = '访问日志'
        verbose_name_plural = '访问日志'
        ordering = ['-created_at']   # 默认按访问时间倒序
        # 为高频查询字段建立索引，加速按时间 / IP / 路径统计
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['path']),
        ]

    def __str__(self):
        """对象的可读表示：形如"IP [方法] 路径 -> 状态码 (耗时ms)"。"""
        return f'{self.ip_address} [{self.method}] {self.path} -> {self.status_code} ({self.duration_ms:.0f}ms)'


class FriendlyLink(models.Model):
    """友情链接：首页右栏展示，可在后台管理。

    替代原先硬编码在 index.html 中的友情链接，改为从数据库读取，
    支持后台增删改、排序与启用/禁用。
    """
    # 链接名称（前台展示文本）
    name = models.CharField(max_length=80, verbose_name='链接名称')
    # 链接地址（完整 URL，新窗口打开）
    url = models.URLField(verbose_name='链接地址')
    # 链接前的图标（emoji 字符），默认 🔗
    icon = models.CharField(max_length=10, blank=True, default='🔗', verbose_name='图标(emoji)')
    # 排序权重：数值越小排在越前面
    order = models.PositiveIntegerField(default=0, verbose_name='排序(小的在前)')
    # 是否在前台显示：禁用后前台不渲染该链接
    is_active = models.BooleanField(default=True, verbose_name='是否显示')
    # 添加时间，自动填充
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='添加时间')

    class Meta:
        """模型元信息。"""
        db_table = 'blog_friendly_link'
        verbose_name = '友情链接'
        verbose_name_plural = '友情链接'
        # 默认按排序升序、再按添加时间倒序
        ordering = ['order', '-created_at']

    # 迭代#62: FriendlyLink.__str__方法类型提示
    def __str__(self) -> str:
        """对象的可读表示：形如"🔗 链接名"。"""
        return f'{self.icon} {self.name}'


# 迭代#63: Favorite模型类docstring完善
class Favorite(models.Model):
    """用户收藏文章记录：一个用户可收藏多篇文章，一篇文章可被多个用户收藏。

    通过 unique_together=['user', 'article'] 保证同一用户对同一篇文章只收藏一次，
    重复点击"收藏"按钮时由 toggle_favorite 视图做"有则取消、无则添加"切换。
    """
    # 收藏者：用户删除时级联删除其全部收藏记录
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='favorites', verbose_name='收藏者')
    # 被收藏的文章：文章删除时级联删除其全部收藏记录
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name='favorites', verbose_name='文章')
    # 第5轮 C10: 所属收藏夹（可空表示"默认收藏夹"）；收藏夹删除时置空回退默认夹
    folder = models.ForeignKey(
        'FavoriteFolder', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='favorites', verbose_name='收藏夹')
    # 收藏时间：创建时自动写入
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='收藏时间')

    class Meta:
        """模型元信息。"""
        db_table = 'blog_favorite'
        verbose_name = '收藏'
        verbose_name_plural = '收藏'
        # 同一用户对同一篇文章只能收藏一次（数据库层唯一约束兜底）
        unique_together = ('user', 'article')
        # 默认按收藏时间倒序，最新收藏排在最前
        ordering = ['-created_at']

    def __str__(self):
        """对象的可读表示：形如"张三 收藏了《某文章》"。"""
        return f'{self.user} 收藏了《{self.article.title}》'


# ============================ 55-70 新增模型 ============================

# 迭代#64: Rating模型类docstring完善
class Rating(models.Model):
    """63. 文章评分：一个用户对一篇文章只能评一次（unique_together 兜底）。

    重复提交时由视图层 get_or_create 后更新 score，文章侧的
    Article.rating_avg / rating_count 为冗余聚合字段，每次评分后重算。
    """
    # 评分档位：1~5 星（正小整数）
    class Score(models.IntegerChoices):
        """评分档位枚举。"""
        ONE = 1, '1星'
        TWO = 2, '2星'
        THREE = 3, '3星'
        FOUR = 4, '4星'
        FIVE = 5, '5星'

    # 被评分的文章：文章删除时级联删除其全部评分
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name='ratings', verbose_name='文章')
    # 评分人：用户删除时级联删除其全部评分
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='ratings', verbose_name='用户')
    # 评分 1~5
    score = models.PositiveSmallIntegerField(
        choices=Score.choices, verbose_name='评分(1-5)')
    # 评分时间：创建时自动写入
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='评分时间')

    class Meta:
        """模型元信息。"""
        db_table = 'blog_rating'
        verbose_name = '评分'
        verbose_name_plural = '评分'
        # 同一用户对同一篇文章只能评一次（数据库唯一约束兜底）
        unique_together = ('article', 'user')
        ordering = ['-created_at']

    def __str__(self):
        """对象的可读表示：形如"张三 给《某文章》打了 5 星"。"""
        return f'{self.user} 给《{self.article.title}》打了 {self.score} 星'


# 迭代#65: SiteNotice模型类docstring完善
class SiteNotice(models.Model):
    """62. 网站公告：全站导航栏下方滚动展示最新一条激活公告。"""
    # 公告内容（单行，最多 200 字）
    content = models.CharField(max_length=200, verbose_name='公告内容')
    # 是否在前台显示：False 时公告条不渲染
    is_active = models.BooleanField(default=True, verbose_name='是否显示')
    # 公告创建时间：自动填充
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        """模型元信息。"""
        db_table = 'blog_site_notice'
        verbose_name = '网站公告'
        verbose_name_plural = '网站公告'
        ordering = ['-created_at']

    def __str__(self):
        """对象的可读表示：直接返回公告内容前 30 字。"""
        return (self.content or '')[:30]


# 迭代#66: Series模型类docstring完善
class Series(models.Model):
    """67. 文章系列：把多篇文章组织成一个系列，按 series_order 排序阅读。"""
    # 系列标题
    title = models.CharField(max_length=200, verbose_name='系列标题')
    # 系列介绍：可在系列详情页展示
    description = models.TextField(blank=True, verbose_name='系列介绍')
    # 系列封面图，上传到 MEDIA_ROOT/series/ 下，允许为空
    cover_image = models.ImageField(
        upload_to='series/', null=True, blank=True, verbose_name='系列封面')
    # 系列作者：作者删除时级联删除其系列
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='series', verbose_name='作者')
    # 系列创建时间：自动填充
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        """模型元信息。"""
        db_table = 'blog_series'
        verbose_name = '文章系列'
        verbose_name_plural = '文章系列'
        ordering = ['-created_at']

    def __str__(self):
        """对象的可读表示：直接返回系列标题。"""
        return self.title


# ============================ 第5轮新增模型 ============================

# 迭代#R5-C13: CommentReport 评论举报模型
class CommentReport(models.Model):
    """第5轮 C13: 评论举报记录。

    用户举报某条评论后创建一条记录，同时把被举报评论的 ``Comment.reported``
    置为 True，供后台优先审核。

    Attributes:
        comment: 被举报的评论（级联删除）。
        reporter: 举报人（级联删除）。
        reason: 举报原因文本。
        created_at: 举报时间（自动）。
    """
    comment = models.ForeignKey(
        Comment, on_delete=models.CASCADE, related_name='reports', verbose_name='被举报评论')
    reporter = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='comment_reports', verbose_name='举报人')
    reason = models.TextField(verbose_name='举报原因')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='举报时间')

    class Meta:
        """模型元信息。"""
        db_table = 'blog_comment_report'
        verbose_name = '评论举报'
        verbose_name_plural = '评论举报'
        ordering = ['-created_at']

    def __str__(self):
        """对象的可读表示。"""
        return f'{self.reporter} 举报了评论#{self.comment_id}'


# 迭代#R5-C10: FavoriteFolder 收藏夹模型
class FavoriteFolder(models.Model):
    """第5轮 C10: 用户收藏夹分类。

    每个用户可创建多个收藏夹，把文章收藏归入不同分类；
    删除收藏夹时其下收藏记录的 ``folder`` 置空（回退"默认收藏夹"）。

    Attributes:
        user: 收藏夹所有者。
        name: 收藏夹名称（最多 50 字）。
        created_at: 创建时间（自动）。
    """
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='favorite_folders', verbose_name='所有者')
    name = models.CharField(max_length=50, verbose_name='收藏夹名称')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        """模型元信息。"""
        db_table = 'blog_favorite_folder'
        verbose_name = '收藏夹'
        verbose_name_plural = '收藏夹'
        ordering = ['-created_at']

    def __str__(self):
        """对象的可读表示。"""
        return f'{self.user}: {self.name}'


# 迭代#R5-F8: Notification 通知模型
class Notification(models.Model):
    """第5轮 F8: 用户站内通知中心。

    由信号在"收到回复 / 被@ / 文章被赞 / 系统公告"等事件时自动生成，
    列表接口按未读优先、时间倒序返回。

    Attributes:
        user: 通知接收人（related_name='notifications'）。
        type: 通知类型 reply/mention/like/article/system。
        title: 通知标题。
        content: 通知正文（可空）。
        related_url: 点击跳转的相关 URL（可空）。
        is_read: 是否已读。
        created_at: 创建时间（自动）。
    """
    class Type(models.TextChoices):
        """通知类型枚举。"""
        REPLY = 'reply', '回复'
        MENTION = 'mention', '提及'
        LIKE = 'like', '点赞'
        ARTICLE = 'article', '文章'
        SYSTEM = 'system', '系统'

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='notifications', verbose_name='接收人')
    type = models.CharField(
        max_length=10, choices=Type.choices, default=Type.SYSTEM, verbose_name='通知类型')
    title = models.CharField(max_length=200, verbose_name='标题')
    content = models.TextField(blank=True, default='', verbose_name='正文')
    related_url = models.CharField(max_length=500, blank=True, default='', verbose_name='跳转链接')
    is_read = models.BooleanField(default=False, verbose_name='是否已读')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        """模型元信息。"""
        db_table = 'blog_notification'
        verbose_name = '通知'
        verbose_name_plural = '通知'
        # 未读优先（-is_read 在 MySQL 布尔上 True=1 排前），再按时间倒序
        ordering = ['-is_read', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read'], name='idx_notif_user_read'),
        ]

    def __str__(self):
        """对象的可读表示。"""
        return f'[{self.get_type_display()}] {self.title}'


# 迭代#R5-F10: Badge 成就徽章模型
class Badge(models.Model):
    """第5轮 F10: 成就徽章定义（全局，所有用户共享同一套徽章规则）。

    condition_type + condition_value 描述达成条件，由徽章检查函数
    在用户发表文章 / 评论 / 获赞等事件触发时比对。

    Attributes:
        name: 徽章名。
        description: 徽章说明。
        icon: emoji 或图标名。
        condition_type: articles/comments/likes/views/days 之一。
        condition_value: 达成所需的数值阈值。
    """
    class ConditionType(models.TextChoices):
        """达成条件类型枚举。"""
        ARTICLES = 'articles', '发文数'
        COMMENTS = 'comments', '评论数'
        LIKES = 'likes', '获赞数'
        VIEWS = 'views', '阅读数'
        DAYS = 'days', '注册天数'

    name = models.CharField(max_length=50, unique=True, verbose_name='徽章名')
    description = models.TextField(blank=True, default='', verbose_name='徽章说明')
    icon = models.CharField(max_length=20, blank=True, default='🏅', verbose_name='图标(emoji)')
    condition_type = models.CharField(
        max_length=15, choices=ConditionType.choices, verbose_name='条件类型')
    condition_value = models.IntegerField(default=1, verbose_name='条件阈值')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        """模型元信息。"""
        db_table = 'blog_badge'
        verbose_name = '徽章'
        verbose_name_plural = '徽章'
        ordering = ['condition_type', 'condition_value']

    def __str__(self):
        """对象的可读表示。"""
        return f'{self.icon} {self.name}'


# 迭代#R5-F10: UserBadge 用户徽章关联模型
class UserBadge(models.Model):
    """第5轮 F10: 用户已获得的徽章关联（用户×徽章联合唯一）。"""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='user_badges', verbose_name='用户')
    badge = models.ForeignKey(
        Badge, on_delete=models.CASCADE, related_name='user_badges', verbose_name='徽章')
    earned_at = models.DateTimeField(auto_now_add=True, verbose_name='获得时间')

    class Meta:
        """模型元信息。"""
        db_table = 'blog_user_badge'
        verbose_name = '用户徽章'
        verbose_name_plural = '用户徽章'
        # 同一用户同一徽章只能获得一次
        unique_together = ('user', 'badge')
        ordering = ['-earned_at']

    def __str__(self):
        """对象的可读表示。"""
        return f'{self.user} 获得了 {self.badge}'


# 迭代#R5-G7: ShortLink 短链接模型
class ShortLink(models.Model):
    """第5轮 G7: 短链接映射（6 位短码 -> 原始长 URL）。

    短码由 ``string.ascii_letters + string.digits`` 随机生成 6 位，
    跳转视图在 ``/s/<code>/`` 命中后 302 跳转到 original_url 并 clicks+1。

    Attributes:
        code: 短码（唯一，最长 10 位）。
        original_url: 原始长链接。
        created_at: 创建时间（自动）。
        clicks: 跳转次数。
    """
    code = models.CharField(max_length=10, unique=True, verbose_name='短码')
    original_url = models.URLField(max_length=500, verbose_name='原始链接')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    clicks = models.PositiveIntegerField(default=0, verbose_name='点击次数')

    class Meta:
        """模型元信息。"""
        db_table = 'blog_short_link'
        verbose_name = '短链接'
        verbose_name_plural = '短链接'
        ordering = ['-created_at']

    def __str__(self):
        """对象的可读表示。"""
        return f'{self.code} -> {self.original_url[:40]}'

# ============================================================
# 第6轮: 1000功能扩展模型（30个新模型）
# ============================================================

class UserFollow(models.Model):
    """用户关注关系（粉丝系统）。"""
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following_set', verbose_name='关注者')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers_set', verbose_name='被关注者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='关注时间')
    class Meta:
        db_table = 'blog_user_follow'
        unique_together = ('follower', 'following')
        ordering = ['-created_at']
    def __str__(self): return f'{self.follower} -> {self.following}'

class UserProfile(models.Model):
    """用户扩展资料（头像/简介/社交链接/个人网站）。"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile_ext', verbose_name='用户')
    bio = models.TextField(max_length=500, blank=True, verbose_name='个人简介')
    location = models.CharField(max_length=100, blank=True, verbose_name='所在地')
    website = models.URLField(max_length=200, blank=True, verbose_name='个人网站')
    twitter = models.CharField(max_length=100, blank=True, verbose_name='Twitter')
    github = models.CharField(max_length=100, blank=True, verbose_name='GitHub')
    weibo = models.CharField(max_length=100, blank=True, verbose_name='微博')
    bilibili = models.CharField(max_length=100, blank=True, verbose_name='B站')
    avatar_bg = models.CharField(max_length=7, default='#a06cd5', verbose_name='头像背景色')
    signature = models.CharField(max_length=200, blank=True, verbose_name='个性签名')
    class Meta:
        db_table = 'blog_user_profile'
    def __str__(self): return f'{self.user} 的资料'

class UserActivity(models.Model):
    """用户活动记录（发布/评论/点赞/收藏/关注等行为追踪）。"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities', verbose_name='用户')
    action_type = models.CharField(max_length=30, verbose_name='行为类型')
    target_type = models.CharField(max_length=30, blank=True, verbose_name='目标类型')
    target_id = models.PositiveIntegerField(null=True, verbose_name='目标ID')
    detail = models.CharField(max_length=200, blank=True, verbose_name='详情')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='时间')
    class Meta:
        db_table = 'blog_user_activity'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', '-created_at']), models.Index(fields=['action_type'])]
    def __str__(self): return f'{self.user} {self.action_type}'

class UserBlock(models.Model):
    """用户黑名单（屏蔽对方内容和私信）。"""
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocking_set', verbose_name='屏蔽者')
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_set', verbose_name='被屏蔽者')
    reason = models.CharField(max_length=200, blank=True, verbose_name='原因')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='时间')
    class Meta:
        db_table = 'blog_user_block'
        unique_together = ('blocker', 'blocked')
    def __str__(self): return f'{self.blocker} 屏蔽 {self.blocked}'

class UserMute(models.Model):
    """用户静音（不接收对方通知，但仍可见内容）。"""
    muter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='muting_set', verbose_name='静音者')
    muted = models.ForeignKey(User, on_delete=models.CASCADE, related_name='muted_set', verbose_name='被静音者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='时间')
    class Meta:
        db_table = 'blog_user_mute'
        unique_together = ('muter', 'muted')
    def __str__(self): return f'{self.muter} 静音 {self.muted}'

class CategoryFollow(models.Model):
    """用户关注分类（新文章通知）。"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='category_follows', verbose_name='用户')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='followers', verbose_name='分类')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='时间')
    class Meta:
        db_table = 'blog_category_follow'
        unique_together = ('user', 'category')
    def __str__(self): return f'{self.user} 关注分类 {self.category}'

class TagFollow(models.Model):
    """用户关注标签（新文章通知）。"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tag_follows', verbose_name='用户')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='followers', verbose_name='标签')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='时间')
    class Meta:
        db_table = 'blog_tag_follow'
        unique_together = ('user', 'tag')
    def __str__(self): return f'{self.user} 关注标签 {self.tag}'

class ArticleBookmark(models.Model):
    """文章书签（带笔记和自定义文件夹）。"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks', verbose_name='用户')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='bookmarked_by', verbose_name='文章')
    folder = models.ForeignKey(FavoriteFolder, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='文件夹')
    note = models.CharField(max_length=300, blank=True, verbose_name='笔记')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='时间')
    class Meta:
        db_table = 'blog_article_bookmark'
        unique_together = ('user', 'article')
        ordering = ['-created_at']
    def __str__(self): return f'{self.user} 收藏 {self.article}'

class ArticleHistory(models.Model):
    """文章编辑历史版本（修订记录，支持回滚）。"""
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='history_versions', verbose_name='文章')
    editor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='编辑者')
    title = models.CharField(max_length=200, verbose_name='标题快照')
    content = models.TextField(verbose_name='内容快照')
    excerpt = models.TextField(blank=True, verbose_name='摘要快照')
    version = models.PositiveIntegerField(default=1, verbose_name='版本号')
    change_summary = models.CharField(max_length=300, blank=True, verbose_name='修改说明')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='时间')
    class Meta:
        db_table = 'blog_article_history'
        ordering = ['-version']
        indexes = [models.Index(fields=['article', '-version'])]
    def __str__(self): return f'{self.article} v{self.version}'

class CommentReaction(models.Model):
    """评论表情反应（👍/❤️/😂/😮/😢/🔥）。"""
    REACTION_CHOICES = [('like','👍'),('love','❤️'),('laugh','😂'),('wow','😮'),('sad','😢'),('fire','🔥')]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comment_reactions', verbose_name='用户')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='reactions', verbose_name='评论')
    reaction_type = models.CharField(max_length=10, choices=REACTION_CHOICES, verbose_name='反应类型')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='时间')
    class Meta:
        db_table = 'blog_comment_reaction'
        unique_together = ('user', 'comment', 'reaction_type')
    def __str__(self): return f'{self.user} {self.reaction_type} 评论{self.comment_id}'

class SearchHistory(models.Model):
    """搜索历史记录（用户+匿名IP）。"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='search_history', verbose_name='用户')
    query = models.CharField(max_length=200, verbose_name='搜索词')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP')
    result_count = models.PositiveIntegerField(default=0, verbose_name='结果数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='时间')
    class Meta:
        db_table = 'blog_search_history'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['query']), models.Index(fields=['user', '-created_at'])]
    def __str__(self): return f'{self.query} ({self.user or self.ip_address})'

class UserPoint(models.Model):
    """用户积分系统（发文/评论/点赞获得积分）。"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='points', verbose_name='用户')
    total_points = models.PositiveIntegerField(default=0, verbose_name='总积分')
    current_points = models.PositiveIntegerField(default=0, verbose_name='当前积分')
    level = models.PositiveIntegerField(default=1, verbose_name='等级')
    class Meta:
        db_table = 'blog_user_point'
    def __str__(self): return f'{self.user}: {self.current_points}分 Lv.{self.level}'

class PointLog(models.Model):
    """积分变动日志。"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='point_logs', verbose_name='用户')
    points = models.IntegerField(verbose_name='变动积分')
    reason = models.CharField(max_length=100, verbose_name='原因')
    balance_after = models.PositiveIntegerField(verbose_name='变动后余额')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='时间')
    class Meta:
        db_table = 'blog_point_log'
        ordering = ['-created_at']
    def __str__(self): return f'{self.user} {self.points:+d} ({self.reason})'

class UserAchievement(models.Model):
    """用户成就（解锁条件+图标+描述）。"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements', verbose_name='用户')
    achievement_key = models.CharField(max_length=50, verbose_name='成就标识')
    title = models.CharField(max_length=100, verbose_name='成就名称')
    description = models.CharField(max_length=300, verbose_name='成就描述')
    icon = models.CharField(max_length=20, default='🏆', verbose_name='图标')
    unlocked_at = models.DateTimeField(auto_now_add=True, verbose_name='解锁时间')
    class Meta:
        db_table = 'blog_user_achievement'
        unique_together = ('user', 'achievement_key')
        ordering = ['-unlocked_at']
    def __str__(self): return f'{self.user} - {self.title}'

class LoginHistory(models.Model):
    """登录历史记录（安全审计）。"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_history', verbose_name='用户')
    ip_address = models.GenericIPAddressField(verbose_name='IP')
    user_agent = models.CharField(max_length=500, verbose_name='User-Agent')
    device_type = models.CharField(max_length=20, default='desktop', verbose_name='设备类型')
    location = models.CharField(max_length=100, blank=True, verbose_name='地理位置')
    success = models.BooleanField(default=True, verbose_name='是否成功')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='时间')
    class Meta:
        db_table = 'blog_login_history'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', '-created_at'])]
    def __str__(self): return f'{self.user} @ {self.ip_address}'

class UserAPIKey(models.Model):
    """用户API密钥（REST API鉴权）。"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys', verbose_name='用户')
    name = models.CharField(max_length=100, verbose_name='密钥名称')
    key_hash = models.CharField(max_length=128, unique=True, verbose_name='密钥哈希')
    key_prefix = models.CharField(max_length=8, verbose_name='密钥前缀')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name='最后使用时间')
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='过期时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    class Meta:
        db_table = 'blog_user_api_key'
        ordering = ['-created_at']
    def __str__(self): return f'{self.user} - {self.name}'

class Webhook(models.Model):
    """Webhook配置（事件推送）。"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='webhooks', verbose_name='用户')
    url = models.URLField(max_length=500, verbose_name='回调URL')
    events = models.CharField(max_length=500, verbose_name='监听事件（逗号分隔）')
    secret = models.CharField(max_length=100, verbose_name='签名密钥')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    last_triggered_at = models.DateTimeField(null=True, blank=True, verbose_name='最后触发时间')
    failure_count = models.PositiveIntegerField(default=0, verbose_name='失败次数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    class Meta:
        db_table = 'blog_webhook'
        ordering = ['-created_at']
    def __str__(self): return f'{self.user} -> {self.url[:50]}'

class ArticleShare(models.Model):
    """文章分享记录（追踪分享渠道）。"""
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='shares', verbose_name='文章')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='用户')
    platform = models.CharField(max_length=20, verbose_name='平台')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='时间')
    class Meta:
        db_table = 'blog_article_share'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['article', 'platform'])]
    def __str__(self): return f'{self.article} 分享到 {self.platform}'

class ContentReport(models.Model):
    """内容举报（文章/评论/用户）。"""
    REPORT_TYPE = [('spam','垃圾广告'),('inappropriate','不当内容'),('copyright','版权侵犯'),('harassment','骚扰'),('other','其他')]
    STATUS = [('pending','待处理'),('resolved','已处理'),('rejected','已驳回')]
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_made', verbose_name='举报人')
    content_type = models.CharField(max_length=20, verbose_name='内容类型')
    content_id = models.PositiveIntegerField(verbose_name='内容ID')
    reason = models.CharField(max_length=20, choices=REPORT_TYPE, verbose_name='举报原因')
    detail = models.TextField(max_length=500, blank=True, verbose_name='详细说明')
    status = models.CharField(max_length=20, default='pending', choices=STATUS, verbose_name='处理状态')
    admin_note = models.TextField(blank=True, verbose_name='管理员备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='时间')
    class Meta:
        db_table = 'blog_content_report'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status']), models.Index(fields=['content_type', 'content_id'])]
    def __str__(self): return f'举报 {self.content_type}#{self.content_id} ({self.reason})'

class ScheduledPost(models.Model):
    """定时发布文章（草稿+发布时间）。"""
    article = models.OneToOneField(Article, on_delete=models.CASCADE, related_name='scheduled', verbose_name='文章')
    scheduled_at = models.DateTimeField(verbose_name='计划发布时间')
    is_published = models.BooleanField(default=False, verbose_name='是否已发布')
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='实际发布时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    class Meta:
        db_table = 'blog_scheduled_post'
        ordering = ['scheduled_at']
        indexes = [models.Index(fields=['is_published', 'scheduled_at'])]
    def __str__(self): return f'{self.article} 计划 {self.scheduled_at}'

class UserDevice(models.Model):
    """用户设备管理（多端登录管理）。"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices', verbose_name='用户')
    device_name = models.CharField(max_length=100, verbose_name='设备名称')
    device_type = models.CharField(max_length=20, verbose_name='设备类型')
    os = models.CharField(max_length=50, blank=True, verbose_name='操作系统')
    browser = models.CharField(max_length=50, blank=True, verbose_name='浏览器')
    ip_address = models.GenericIPAddressField(verbose_name='IP')
    last_active_at = models.DateTimeField(auto_now=True, verbose_name='最后活跃时间')
    is_current = models.BooleanField(default=False, verbose_name='是否当前设备')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='登录时间')
    class Meta:
        db_table = 'blog_user_device'
        ordering = ['-last_active_at']
    def __str__(self): return f'{self.user} - {self.device_name}'

class ThemePreset(models.Model):
    """主题预设（用户自定义主题配色方案）。"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='theme_presets', verbose_name='用户')
    name = models.CharField(max_length=50, verbose_name='主题名称')
    primary_color = models.CharField(max_length=7, default='#a06cd5', verbose_name='主色')
    accent_color = models.CharField(max_length=7, default='#ff8fb1', verbose_name='强调色')
    bg_color = models.CharField(max_length=7, default='#f4f2fb', verbose_name='背景色')
    text_color = models.CharField(max_length=7, default='#2b2340', verbose_name='文字色')
    is_active = models.BooleanField(default=False, verbose_name='是否当前使用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    class Meta:
        db_table = 'blog_theme_preset'
        ordering = ['-created_at']
    def __str__(self): return f'{self.user} - {self.name}'

class ReadingList(models.Model):
    """阅读清单（稍后读/已读/想读）。"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reading_lists', verbose_name='用户')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='in_reading_lists', verbose_name='文章')
    status = models.CharField(max_length=20, default='later', choices=[('later','稍后读'),('reading','在读'),('read','已读')], verbose_name='状态')
    priority = models.PositiveIntegerField(default=0, verbose_name='优先级')
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='添加时间')
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='读完时间')
    class Meta:
        db_table = 'blog_reading_list'
        unique_together = ('user', 'article')
        ordering = ['-added_at']
    def __str__(self): return f'{self.user} - {self.article} ({self.status})'

class UserNote(models.Model):
    """用户笔记（文章划线+个人笔记）。"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes', verbose_name='用户')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='user_notes', verbose_name='文章')
    highlight_text = models.TextField(blank=True, verbose_name='划线内容')
    note_text = models.TextField(verbose_name='笔记内容')
    color = models.CharField(max_length=7, default='#fff3cd', verbose_name='高亮颜色')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='时间')
    class Meta:
        db_table = 'blog_user_note'
        ordering = ['-created_at']
    def __str__(self): return f'{self.user} 笔记 @ {self.article}'

class ExportJob(models.Model):
    """数据导出任务（异步导出文章/评论/用户数据）。"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='export_jobs', verbose_name='用户')
    export_type = models.CharField(max_length=30, verbose_name='导出类型')
    format = models.CharField(max_length=10, default='json', verbose_name='格式')
    status = models.CharField(max_length=20, default='pending', verbose_name='状态')
    file_path = models.CharField(max_length=500, blank=True, verbose_name='文件路径')
    item_count = models.PositiveIntegerField(default=0, verbose_name='导出条数')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    class Meta:
        db_table = 'blog_export_job'
        ordering = ['-created_at']
    def __str__(self): return f'{self.user} 导出 {self.export_type} ({self.status})'

class UserWidget(models.Model):
    """用户自定义仪表盘组件（可拖拽布局）。"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='widgets', verbose_name='用户')
    widget_type = models.CharField(max_length=50, verbose_name='组件类型')
    title = models.CharField(max_length=100, verbose_name='标题')
    position = models.PositiveIntegerField(default=0, verbose_name='位置')
    is_visible = models.BooleanField(default=True, verbose_name='是否显示')
    config = models.JSONField(default=dict, verbose_name='配置')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    class Meta:
        db_table = 'blog_user_widget'
        ordering = ['position']
    def __str__(self): return f'{self.user} - {self.title}'


# ============================================================
# SiteInfo：站点信息「单例」模型（工单 15）
# ============================================================
class SiteInfo(models.Model):
    """站点信息单例：网站名 / Logo / 副标题 / SEO 描述关键词 / 页脚关于文案等。

    设计目标：把原先硬编码在模板与 settings 中的「网站名、标题、网站介绍」等
    文案变量收敛到数据库，管理员可在「站点设置」页面（或 Django admin）直接修改，
    无需改动代码、无需重新部署。

    - 全站只存在一条记录（id 固定为 1），通过 ``SiteInfo.load()`` 读取，
      结果按缓存键缓存，保存 / 修改时自动失效；
    - 读取侧（SiteInfoMiddleware / 上下文处理器）拿到对象后向模板暴露
      ``site_info`` 及 ``site_name`` 等便捷变量。
    """

    # ---- 品牌区 ----
    site_name = models.CharField(
        max_length=60, default='萌语博客', verbose_name='网站名称',
        help_text='显示在左上角 Logo、版权与浏览器标题后缀')
    logo_emoji = models.CharField(
        max_length=8, default='🌸', verbose_name='Logo 表情',
        help_text='网站名称前的 Emoji，例如 🌸 / 🐱 / 🌟')
    tagline = models.CharField(
        max_length=120,
        default='一个粉紫蓝萌系的二次元小站，记录技术与生活的碎碎念喵~',
        verbose_name='网站副标题 / 一句话介绍')

    # ---- SEO 区 ----
    description = models.TextField(
        default='萌语博客 · 一个粉紫蓝萌系的二次元小站，记录技术与生活的碎碎念喵~',
        verbose_name='网站描述（SEO meta description）')
    keywords = models.CharField(
        max_length=200, default='博客,技术,二次元',
        verbose_name='网站关键词（SEO meta keywords，英文逗号分隔）')

    # ---- 页脚区 ----
    footer_about = models.TextField(
        default='这里是萌语博客，记录技术笔记、生活随笔与各种小确幸。'
                '愿你在这里收获一点点温暖与灵感喵~ (◕ᴗ◕✿)',
        verbose_name='页脚「关于小站」文案')
    footer_icp = models.CharField(
        max_length=80, blank=True, default='',
        verbose_name='备案号（选填，如 浙ICP备xxxxxxxx号）')
    copyright_holder = models.CharField(
        max_length=60, blank=True, default='',
        verbose_name='版权归属名称（留空则用网站名称）')

    # ---- 元信息 ----
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'blog_site_info'
        verbose_name = '站点信息'
        verbose_name_plural = '站点信息'

    def __str__(self):
        return f'站点信息：{self.site_name}'

    # 单例 id 与缓存键（集中定义，避免各处魔法值）
    SINGLETON_ID = 1
    CACHE_KEY = 'site_info_singleton'

    def save(self, *args, **kwargs):
        """保存时强制 pk=1（单例），并清除读取缓存。"""
        self.pk = self.SINGLETON_ID
        super().save(*args, **kwargs)
        try:
            from django.core.cache import cache
            cache.delete(self.CACHE_KEY)
        except Exception:  # noqa: BLE001 缓存失败不影响保存
            pass

    @classmethod
    def load(cls) -> 'SiteInfo':
        """读取全站唯一的 SiteInfo 对象（带缓存）；不存在时用默认值创建。

        Returns:
            SiteInfo: 单例对象，调用方按普通模型使用即可。
        """
        from django.core.cache import cache
        obj = cache.get(cls.CACHE_KEY)
        if obj is not None:
            return obj
        # 字段均有默认值，defaults 留空即可完成首次创建
        obj, _ = cls.objects.get_or_create(pk=cls.SINGLETON_ID, defaults={})
        cache.set(cls.CACHE_KEY, obj, 3600)
        return obj


class PromotionRequest(models.Model):
    """Bug1：作者对已发布文章发起「置顶 / 精华 / 热门」申请，管理员在内容审核页审批。

    - 作者在详情页点对应按钮、弹窗填写理由后生成一条 PENDING 记录；
    - 管理员通过后由审核视图把 Article 对应标记置 True；驳回则置 REJECTED；
    - 处理结果写入 ModerationLog，并向作者发站内通知。
    """

    class Kind(models.TextChoices):
        """申请类型：置顶 / 精华 / 热门。"""
        PIN = 'pin', '置顶'
        FEATURE = 'feature', '精华'
        HOT = 'hot', '热门'

    class Status(models.TextChoices):
        """审批状态：待审核 / 已通过 / 已驳回。"""
        PENDING = 'pending', '待审核'
        APPROVED = 'approved', '已通过'
        REJECTED = 'rejected', '已驳回'

    # 申请对应的文章（文章删除则申请一并删除）
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name='promotion_requests',
        verbose_name='文章')
    # 申请人（账号删除则置空，申请记录保留）
    applicant = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='promotion_requests', verbose_name='申请人')
    # 申请类型（置顶/精华/热门）
    kind = models.CharField(max_length=10, choices=Kind.choices, verbose_name='申请类型')
    # 申请理由
    reason = models.TextField(blank=True, default='', verbose_name='申请理由')
    # 审批状态，默认待审核
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING, verbose_name='状态')
    # 审核人（账号删除置空）
    handled_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='handled_promotion_requests', verbose_name='审核人')
    # 处理时间
    handled_at = models.DateTimeField(null=True, blank=True, verbose_name='处理时间')
    # 申请时间
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='申请时间')

    class Meta:
        db_table = 'blog_promotion_request'
        verbose_name = '推广申请'
        verbose_name_plural = '推广申请'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at'], name='idx_promo_status_ct'),
            models.Index(fields=['kind', 'status'], name='idx_promo_kind_status'),
        ]

    def __str__(self):
        return f'{self.get_kind_display()}申请：文章{self.article_id}（{self.get_status_display()}）'


class ModerationSettings(models.Model):
    """Bug1：内容审核全局设置单例（新文章/新评论是否需审核、评论撤回时限、置顶上限）。

    全站仅一条（pk=1），管理员在内容审核页「全局设置」面板修改；读取侧通过
    ModerationSettings.load() 拿对象（带缓存），保存时自动失效。
    """

    require_article_review = models.BooleanField(
        default=True, verbose_name='普通作者新文章需审核',
        help_text='关闭后普通作者提交即发布；管理员发文始终可直接发布')
    require_comment_review = models.BooleanField(
        default=False, verbose_name='新评论需审核',
        help_text='开启后新评论先待审核，通过后才公开')
    comment_recall_minutes = models.PositiveIntegerField(
        default=10, verbose_name='评论可撤回时长（分钟）',
        help_text='超过该时长不可自行撤回')
    max_pinned = models.PositiveIntegerField(
        default=3, verbose_name='置顶文章数量上限')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'blog_moderation_settings'
        verbose_name = '审核全局设置'
        verbose_name_plural = '审核全局设置'

    def __str__(self):
        return '审核全局设置'

    SINGLETON_ID = 1
    CACHE_KEY = 'moderation_settings_singleton'

    def save(self, *args, **kwargs):
        """保存时强制 pk=1（单例）并清除读取缓存。"""
        self.pk = self.SINGLETON_ID
        super().save(*args, **kwargs)
        try:
            from django.core.cache import cache
            cache.delete(self.CACHE_KEY)
        except Exception:  # noqa: BLE001 缓存失败不影响保存
            pass

    @classmethod
    def load(cls) -> 'ModerationSettings':
        """读取全站唯一的审核设置（带缓存）；不存在时用默认值创建。"""
        from django.core.cache import cache
        obj = cache.get(cls.CACHE_KEY)
        if obj is not None:
            return obj
        obj, _ = cls.objects.get_or_create(pk=cls.SINGLETON_ID, defaults={})
        cache.set(cls.CACHE_KEY, obj, 3600)
        return obj

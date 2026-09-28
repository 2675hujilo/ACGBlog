# -*- coding: utf-8 -*-
"""
站点信息领域模型 —— 站点单例 / 网站公告 / 友情链接。

本文件从原 ``blog/models.py`` 拆出，包含：

- :class:`SiteInfo`：站点信息单例（站名、Logo emoji、副标题、SEO 描述 / 关键词、
  页脚关于文案 / 备案号 / 版权归属），通过 :meth:`SiteInfo.load` 带缓存读取；
- :class:`SiteNotice`：网站公告（导航栏下方滚动展示最新一条激活公告）；
- :class:`FriendlyLink`：友情链接（首页右栏展示，后台可增删、排序、启停）。

设计目标
--------
把原先硬编码在模板与 settings 中的「网站名、标题、介绍、友链」等变量收敛到
数据库，管理员在「站点设置」页或 admin 直接改，无需改代码、无需重新部署。

表名与字段均与拆分前一致，不产生数据库结构变更。

维护注意点
----------
1. SiteInfo 为单例（固定 pk=1），save 强制 pk 并失效缓存，不要 create 第二条；
2. SiteNotice 结构精简（content + is_active），导航下只滚动最新一条激活公告；
3. FriendlyLink 用 ``order`` 排序、``name`` 为链接文本、``icon`` 为 emoji，
   字段名与 admin 配置对应，改动需同步 admin。
"""
from django.db import models


class SiteInfo(models.Model):
    """站点信息单例：网站名 / Logo / 副标题 / SEO / 页脚文案。

    全站只存在一条（id 固定 1），通过 :meth:`load` 读取并缓存，保存 / 修改
    自动失效；读取侧（SiteInfoMiddleware / 上下文处理器）向模板暴露
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
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'blog_site_info'
        verbose_name = '站点信息'
        verbose_name_plural = '站点信息'

    def __str__(self):
        return f'站点信息：{self.site_name}'

    # 单例 id 与缓存键（类常量，避免各处魔法值）
    SINGLETON_ID = 1
    CACHE_KEY = 'site_info_singleton'

    def save(self, *args, **kwargs):
        """保存时强制 pk=1（单例），并清除读取缓存。"""
        self.pk = self.SINGLETON_ID
        super().save(*args, **kwargs)
        try:
            from django.core.cache import cache
            cache.delete(self.CACHE_KEY)
        except Exception:  # noqa: BLE001 - 缓存失败不影响保存
            pass

    @classmethod
    def load(cls):
        """读取全站唯一 SiteInfo（带缓存）；不存在时用默认值创建。

        :return: SiteInfo 单例，调用方按普通模型使用即可。
        """
        from django.core.cache import cache
        obj = cache.get(cls.CACHE_KEY)
        if obj is not None:
            return obj
        # 字段均有默认值，defaults 留空即可完成首次创建
        obj, _ = cls.objects.get_or_create(pk=cls.SINGLETON_ID, defaults={})
        cache.set(cls.CACHE_KEY, obj, 3600)
        return obj


class SiteNotice(models.Model):
    """网站公告：全站导航栏下方滚动展示最新一条激活公告。"""

    # 公告内容（单行，最多 200 字）
    content = models.CharField(max_length=200, verbose_name='公告内容')
    # 是否在前台显示：False 时公告条不渲染
    is_active = models.BooleanField(
        default=True, verbose_name='是否显示')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'blog_site_notice'
        verbose_name = '网站公告'
        verbose_name_plural = '网站公告'
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：公告内容前 30 字。"""
        return (self.content or '')[:30]


class FriendlyLink(models.Model):
    """友情链接：首页右栏展示，可后台管理，支持排序与启停。

    替代原先硬编码在 index.html 中的友链，改为从数据库读取。
    """

    # 链接名称（前台展示文本）
    name = models.CharField(max_length=80, verbose_name='链接名称')
    # 链接地址（完整 URL，新窗口打开）
    url = models.URLField(verbose_name='链接地址')
    # 链接前图标（emoji），默认 🔗
    icon = models.CharField(
        max_length=10, blank=True, default='🔗',
        verbose_name='图标(emoji)')
    # 排序权重：数值越小越靠前
    order = models.PositiveIntegerField(
        default=0, verbose_name='排序(小的在前)')
    # 是否前台显示：禁用后不渲染
    is_active = models.BooleanField(
        default=True, verbose_name='是否显示')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='添加时间')

    class Meta:
        db_table = 'blog_friendly_link'
        verbose_name = '友情链接'
        verbose_name_plural = '友情链接'
        ordering = ['order', '-created_at']

    def __str__(self):
        """可读表示：「图标 链接名」。"""
        return f'{self.icon} {self.name}'

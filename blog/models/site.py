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
#: 从模块「django.db」导入所需对象
from django.db import models


class SiteInfo(models.Model):
    """站点信息单例：网站名 / Logo / 副标题 / SEO / 页脚文案。

    全站只存在一条（id 固定 1），通过 :meth:`load` 读取并缓存，保存 / 修改
    自动失效；读取侧（SiteInfoMiddleware / 上下文处理器）向模板暴露
    ``site_info`` 及 ``site_name`` 等便捷变量。
    """

    # ---- 品牌区 ----
    #: 定义变量「site_name」，保存对应数据（Django 模型字段，参与建表）
    site_name = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=60, default='萌语博客', verbose_name='网站名称',
        #: 定义变量「help_text」，保存对应数据
        help_text='显示在左上角 Logo、版权与浏览器标题后缀')
    #: 定义变量「logo_emoji」，保存对应数据（Django 模型字段，参与建表）
    logo_emoji = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=8, default='🌸', verbose_name='Logo 表情',
        #: 定义变量「help_text」，保存对应数据
        help_text='网站名称前的 Emoji，例如 🌸 / 🐱 / 🌟')
    #: 定义变量「tagline」，保存对应数据（Django 模型字段，参与建表）
    tagline = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=120,
        #: 定义变量「default」，保存对应数据
        default='一个粉紫蓝萌系的二次元小站，记录技术与生活的碎碎念喵~',
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='网站副标题 / 一句话介绍')

    # ---- SEO 区 ----
    #: 定义变量「description」，保存对应数据（Django 模型字段，参与建表）
    description = models.TextField(
        #: 定义变量「default」，保存对应数据
        default='萌语博客 · 一个粉紫蓝萌系的二次元小站，记录技术与生活的碎碎念喵~',
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='网站描述（SEO meta description）')
    #: 定义变量「keywords」，保存对应数据（Django 模型字段，参与建表）
    keywords = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=200, default='博客,技术,二次元',
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='网站关键词（SEO meta keywords，英文逗号分隔）')

    # ---- 页脚区 ----
    #: 定义变量「footer_about」，保存对应数据（Django 模型字段，参与建表）
    footer_about = models.TextField(
        #: 定义变量「default」，保存对应数据
        default='这里是萌语博客，记录技术笔记、生活随笔与各种小确幸。'
                #: 该行执行对应逻辑（结合上下文理解）
                '愿你在这里收获一点点温暖与灵感喵~ (◕ᴗ◕✿)',
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='页脚「关于小站」文案')
    #: 定义变量「footer_icp」，保存对应数据（Django 模型字段，参与建表）
    footer_icp = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=80, blank=True, default='',
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='备案号（选填，如 浙ICP备xxxxxxxx号）')
    #: 定义变量「copyright_holder」，保存对应数据（Django 模型字段，参与建表）
    copyright_holder = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=60, blank=True, default='',
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='版权归属名称（留空则用网站名称）')

    # ---- 元信息 ----
    #: 定义变量「created_at」，保存对应数据（Django 模型字段，参与建表）
    created_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='创建时间')
    #: 定义变量「updated_at」，保存对应数据（Django 模型字段，参与建表）
    updated_at = models.DateTimeField(
        #: 定义变量「auto_now」，保存对应数据
        auto_now=True, verbose_name='更新时间')

    class Meta:
        """
        类 Meta：meta。

        字段/类属性：
          - db_table：str
          - verbose_name：str
          - verbose_name_plural：str

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「db_table」，保存对应数据
        db_table = 'blog_site_info'
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name = '站点信息'
        #: 定义变量「verbose_name_plural」，保存对应数据
        verbose_name_plural = '站点信息'

    def __str__(self):
        """
        功能：处理「str」相关逻辑。

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 返回结果并结束当前函数
        return f'站点信息：{self.site_name}'

    # 单例 id 与缓存键（类常量，避免各处魔法值）
    #: 定义变量「SINGLETON_ID」，保存对应数据
    SINGLETON_ID = 1
    #: 定义变量「CACHE_KEY」，保存对应数据
    CACHE_KEY = 'site_info_singleton'

    def save(self, *args, **kwargs):
        """保存时强制 pk=1（单例），并清除读取缓存。"""
        #: 定义实例/类属性「self.pk」，保存对应数据
        self.pk = self.SINGLETON_ID
        #: 调用「super」执行相应逻辑
        super().save(*args, **kwargs)
        #: 尝试执行可能出错的代码
        try:
            #: 从模块「django.core.cache」导入所需对象
            from django.core.cache import cache
            #: 读写缓存，减轻数据库压力，注意键与过期时间
            cache.delete(self.CACHE_KEY)
        #: 捕获并处理异常，避免程序中断
        except Exception:  # noqa: BLE001 - 缓存失败不影响保存
            #: 占位语句：此处暂不需要实现
            pass

    #: 装饰器：为下一个定义附加「classmethod」行为（权限、缓存、注册信号等）
    @classmethod
    def load(cls):
        """读取全站唯一 SiteInfo（带缓存）；不存在时用默认值创建。

        :return: SiteInfo 单例，调用方按普通模型使用即可。
        """
        #: 从模块「django.core.cache」导入所需对象
        from django.core.cache import cache
        #: 读写缓存，减轻数据库压力，注意键与过期时间
        obj = cache.get(cls.CACHE_KEY)
        #: 条件判断：条件成立时执行该分支
        if obj is not None:
            #: 返回结果并结束当前函数
            return obj
        # 字段均有默认值，defaults 留空即可完成首次创建
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        obj, _ = cls.objects.get_or_create(pk=cls.SINGLETON_ID, defaults={})
        #: 读写缓存，减轻数据库压力，注意键与过期时间
        cache.set(cls.CACHE_KEY, obj, 3600)
        #: 返回结果并结束当前函数
        return obj


class SiteNotice(models.Model):
    """网站公告：全站导航栏下方滚动展示最新一条激活公告。"""

    # 公告内容（单行，最多 200 字）
    #: 定义变量「content」，保存对应数据（Django 模型字段，参与建表）
    content = models.CharField(max_length=200, verbose_name='公告内容')
    # 是否在前台显示：False 时公告条不渲染
    #: 定义变量「is_active」，保存对应数据（Django 模型字段，参与建表）
    is_active = models.BooleanField(
        #: 定义变量「default」，保存对应数据
        default=True, verbose_name='是否显示')
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
        db_table = 'blog_site_notice'
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name = '网站公告'
        #: 定义变量「verbose_name_plural」，保存对应数据
        verbose_name_plural = '网站公告'
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：公告内容前 30 字。"""
        #: 返回结果并结束当前函数
        return (self.content or '')[:30]


class FriendlyLink(models.Model):
    """友情链接：首页右栏展示，可后台管理，支持排序与启停。

    替代原先硬编码在 index.html 中的友链，改为从数据库读取。
    """

    # 链接名称（前台展示文本）
    #: 定义变量「name」，保存对应数据（Django 模型字段，参与建表）
    name = models.CharField(max_length=80, verbose_name='链接名称')
    # 链接地址（完整 URL，新窗口打开）
    #: 定义变量「url」，保存对应数据（Django 模型字段，参与建表）
    url = models.URLField(verbose_name='链接地址')
    # 链接前图标（emoji），默认 🔗
    #: 定义变量「icon」，保存对应数据（Django 模型字段，参与建表）
    icon = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=10, blank=True, default='🔗',
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='图标(emoji)')
    # 排序权重：数值越小越靠前
    #: 定义变量「order」，保存对应数据（Django 模型字段，参与建表）
    order = models.PositiveIntegerField(
        #: 定义变量「default」，保存对应数据
        default=0, verbose_name='排序(小的在前)')
    # 是否前台显示：禁用后不渲染
    #: 定义变量「is_active」，保存对应数据（Django 模型字段，参与建表）
    is_active = models.BooleanField(
        #: 定义变量「default」，保存对应数据
        default=True, verbose_name='是否显示')
    #: 定义变量「created_at」，保存对应数据（Django 模型字段，参与建表）
    created_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='添加时间')

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
        db_table = 'blog_friendly_link'
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name = '友情链接'
        #: 定义变量「verbose_name_plural」，保存对应数据
        verbose_name_plural = '友情链接'
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['order', '-created_at']

    def __str__(self):
        """可读表示：「图标 链接名」。"""
        #: 返回结果并结束当前函数
        return f'{self.icon} {self.name}'

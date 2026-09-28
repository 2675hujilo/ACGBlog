# -*- coding: utf-8 -*-
"""
用户领域模型 —— 站内认证用户与其个性化偏好。

本文件从原 ``blog/models.py`` 拆出，仅含 :class:`User`。该模型继承 Django 内置
:class:`~django.contrib.auth.models.AbstractUser`，并通过 ``settings.
AUTH_USER_MODEL`` 指定为项目认证用户表，因此全站外键（文章作者、评论人等）均指向
本表。表名 ``blog_user`` 与拆分前一致，不产生数据库结构变更。

在 AbstractUser 自带的 username / password / email / is_staff / is_superuser /
is_active / date_joined 等字段之外，本模型扩展了两大类字段：

1. 博客资料：昵称 ``nickname``、头像 ``avatar``、个人介绍 ``introduction``、
   个性签名 ``signature``、生日 ``birthday``、个人主页背景 ``background_image``；
2. 阅读与外观偏好：主题色、字号、行高、字体族、动效 / 音效 / 护眼 / AMOLED 暗黑
   等开关，前端据此调整排版与主题，是二次元萌系个性化体验的数据基础。

维护注意点
----------
1. 昵称可为空，展示时回退 username（见 ``__str__`` 与各视图的 display_name）；
2. 头像 / 背景为 ImageField，上传目录由 ``upload_to`` 指定，删除旧文件由信号或
   存储后端处理，模板用 ``.url`` 取值并做异常兜底；
3. 各偏好字段均给了安全默认值，新增偏好务必带默认值，避免老用户取值为空；
4. ``last_active`` 用 ``auto_now``，由在线状态逻辑周期性刷新，不要手工赋值；
5. 本模型是认证核心表，字段变更会影响登录与全站外键，属核心结构，改动需评审。
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """站内用户：AbstractUser + 博客资料 + 个性化偏好。"""

    # ---------------- 博客资料 ----------------
    # 前台展示昵称，为空时回退到 username
    nickname = models.CharField(
        max_length=50, blank=True, verbose_name='昵称')
    # 用户头像，上传到 MEDIA_ROOT/avatars/
    avatar = models.ImageField(
        upload_to='avatars/', null=True, blank=True, verbose_name='头像')
    # 个人简介，展示在关于页 / 个人主页 / 侧边栏
    introduction = models.TextField(
        blank=True, verbose_name='个人介绍')
    # 个性签名，最长 200 字
    signature = models.CharField(
        max_length=200, blank=True, default='', verbose_name='个性签名')
    # 生日，可空，用于生日彩蛋祝福
    birthday = models.DateField(
        null=True, blank=True, verbose_name='生日')
    # 个人主页顶部背景图，上传到 MEDIA_ROOT/user_bg/
    background_image = models.ImageField(
        upload_to='user_bg/', null=True, blank=True,
        verbose_name='个人主页背景')

    # ---------------- 外观 / 阅读偏好 ----------------
    # 主题色档位：紫粉（默认）/ 蓝绿 / 橙黄 / 自定义 HEX
    theme_color = models.CharField(
        max_length=20, default='purple_pink',
        choices=[('purple_pink', '紫粉'), ('blue_green', '蓝绿'),
                 ('orange_yellow', '橙黄'), ('custom', '自定义')],
        verbose_name='主题色')
    # 自定义主题 HEX，仅 theme_color=custom 时生效
    custom_theme_color = models.CharField(
        max_length=7, blank=True, default='#a855f7',
        verbose_name='自定义主题色HEX')
    # 字号档位：小 / 中（默认）/ 大 / 超大
    font_size = models.CharField(
        max_length=10, default='medium',
        choices=[('small', '小'), ('medium', '中'),
                 ('large', '大'), ('xlarge', '超大')],
        verbose_name='字号')
    # 行高档位：紧凑 / 正常（默认）/ 宽松
    line_height = models.CharField(
        max_length=10, default='normal',
        choices=[('tight', '紧凑'), ('normal', '正常'),
                 ('relaxed', '宽松')],
        verbose_name='行高')
    # 字体族：无衬线（默认）/ 衬线 / 等宽
    font_family = models.CharField(
        max_length=10, default='sans',
        choices=[('sans', '无衬线'), ('serif', '衬线'),
                 ('mono', '等宽')],
        verbose_name='字体')
    # 动效总开关，默认开启（关闭后减少动画，照顾低性能 / 晕动症）
    effects_enabled = models.BooleanField(
        default=True, verbose_name='动效开关')
    # 音效开关，默认关闭（避免未经同意发声）
    sound_enabled = models.BooleanField(
        default=False, verbose_name='音效开关')
    # 护眼模式（降低亮色刺激），默认关闭
    eye_protection = models.BooleanField(
        default=False, verbose_name='护眼模式')
    # AMOLED 纯黑暗黑模式，默认关闭
    amoled_dark = models.BooleanField(
        default=False, verbose_name='纯黑暗黑')
    # 最近活跃时间，auto_now 每次保存刷新，供在线状态展示
    last_active = models.DateTimeField(
        auto_now=True, verbose_name='最近活跃')

    class Meta:
        db_table = 'blog_user'
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        """可读表示：优先昵称，昵称为空用登录名。"""
        return self.nickname or self.username

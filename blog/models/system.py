# -*- coding: utf-8 -*-
"""
系统扩展领域模型 —— API 密钥、Webhook、设备、主题、搜索历史、导出与仪表盘组件。

本文件从原 ``blog/models.py`` 拆出，含：

- :class:`UserAPIKey`：用户 REST API 密钥（仅存哈希 + 前缀，用于 API 鉴权）；
- :class:`Webhook`：用户 Webhook 配置（事件回调 + 签名密钥 + 失败计数）；
- :class:`UserDevice`：用户登录设备 / 多端会话管理；
- :class:`ThemePreset`：用户自定义主题配色预设（主 / 强调 / 背景 / 文字四色）；
- :class:`SearchHistory`：搜索历史（登录用户或匿名 IP）；
- :class:`ExportJob`：异步数据导出任务；
- :class:`UserWidget`：用户自定义仪表盘组件（可拖拽、带配置）。

表名与拆分前一致，不产生数据库结构变更；用户外键以字符串引用。

维护注意点
----------
1. UserAPIKey 只存 key_hash 与 key_prefix，**明文只在创建时展示一次**；鉴权用
   恒定时间比较哈希，过期 / 停用密钥拒绝；
2. Webhook 触发失败累计 failure_count 并更新 last_triggered_at，签名用 secret
   计算 HMAC，密钥不回传前端；
3. ThemePreset 颜色为四个独立 HEX 字段（非 JSON），is_active 标记当前使用，
   切换时同用户其余预设置 False；
4. ExportJob 异步执行，状态 pending -> running -> success/failed，错误写
   error_message，完成后产物路径写 file_path；
5. SearchHistory 泛化记录（user 可空、补 ip_address），注意隐私保留期限。
"""
#: 从模块「django.db」导入所需对象
from django.db import models


class UserAPIKey(models.Model):
    """用户 API 密钥：哈希 + 前缀 + 启用 / 过期 / 最后使用时间。"""

    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='api_keys', verbose_name='用户')
    #: 定义变量「name」，保存对应数据（Django 模型字段，参与建表）
    name = models.CharField(max_length=100, verbose_name='密钥名称')
    #: 定义变量「key_hash」，保存对应数据（Django 模型字段，参与建表）
    key_hash = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=128, unique=True, verbose_name='密钥哈希')
    #: 定义变量「key_prefix」，保存对应数据（Django 模型字段，参与建表）
    key_prefix = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=8, verbose_name='密钥前缀')
    #: 定义变量「is_active」，保存对应数据（Django 模型字段，参与建表）
    is_active = models.BooleanField(
        #: 定义变量「default」，保存对应数据
        default=True, verbose_name='是否启用')
    #: 定义变量「last_used_at」，保存对应数据（Django 模型字段，参与建表）
    last_used_at = models.DateTimeField(
        #: 定义变量「null」，保存对应数据
        null=True, blank=True, verbose_name='最后使用时间')
    #: 定义变量「expires_at」，保存对应数据（Django 模型字段，参与建表）
    expires_at = models.DateTimeField(
        #: 定义变量「null」，保存对应数据
        null=True, blank=True, verbose_name='过期时间')
    #: 定义变量「created_at」，保存对应数据（Django 模型字段，参与建表）
    created_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='创建时间')

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
        db_table = 'blog_user_api_key'
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：用户 - 密钥名。"""
        #: 返回结果并结束当前函数
        return f'{self.user} - {self.name}'


class Webhook(models.Model):
    """Webhook 配置：回调 URL + 监听事件 + 签名密钥 + 失败计数。"""

    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='webhooks', verbose_name='用户')
    #: 定义变量「url」，保存对应数据（Django 模型字段，参与建表）
    url = models.URLField(max_length=500, verbose_name='回调URL')
    #: 定义变量「events」，保存对应数据（Django 模型字段，参与建表）
    events = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=500, verbose_name='监听事件（逗号分隔）')
    #: 定义变量「secret」，保存对应数据（Django 模型字段，参与建表）
    secret = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=100, verbose_name='签名密钥')
    #: 定义变量「is_active」，保存对应数据（Django 模型字段，参与建表）
    is_active = models.BooleanField(
        #: 定义变量「default」，保存对应数据
        default=True, verbose_name='是否启用')
    #: 定义变量「last_triggered_at」，保存对应数据（Django 模型字段，参与建表）
    last_triggered_at = models.DateTimeField(
        #: 定义变量「null」，保存对应数据
        null=True, blank=True, verbose_name='最后触发时间')
    #: 定义变量「failure_count」，保存对应数据（Django 模型字段，参与建表）
    failure_count = models.PositiveIntegerField(
        #: 定义变量「default」，保存对应数据
        default=0, verbose_name='失败次数')
    #: 定义变量「created_at」，保存对应数据（Django 模型字段，参与建表）
    created_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='创建时间')

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
        db_table = 'blog_webhook'
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：用户 -> URL 前50字。"""
        #: 返回结果并结束当前函数
        return f'{self.user} -> {self.url[:50]}'


class UserDevice(models.Model):
    """用户设备 / 会话：设备名、类型、系统、浏览器、IP、最后活跃。"""

    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='devices', verbose_name='用户')
    #: 定义变量「device_name」，保存对应数据（Django 模型字段，参与建表）
    device_name = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=100, verbose_name='设备名称')
    #: 定义变量「device_type」，保存对应数据（Django 模型字段，参与建表）
    device_type = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=20, verbose_name='设备类型')
    #: 定义变量「os」，保存对应数据（Django 模型字段，参与建表）
    os = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=50, blank=True, verbose_name='操作系统')
    #: 定义变量「browser」，保存对应数据（Django 模型字段，参与建表）
    browser = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=50, blank=True, verbose_name='浏览器')
    #: 定义变量「ip_address」，保存对应数据（Django 模型字段，参与建表）
    ip_address = models.GenericIPAddressField(verbose_name='IP')
    #: 定义变量「last_active_at」，保存对应数据（Django 模型字段，参与建表）
    last_active_at = models.DateTimeField(
        #: 定义变量「auto_now」，保存对应数据
        auto_now=True, verbose_name='最后活跃时间')
    #: 定义变量「is_current」，保存对应数据（Django 模型字段，参与建表）
    is_current = models.BooleanField(
        #: 定义变量「default」，保存对应数据
        default=False, verbose_name='是否当前设备')
    #: 定义变量「created_at」，保存对应数据（Django 模型字段，参与建表）
    created_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='登录时间')

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
        db_table = 'blog_user_device'
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-last_active_at']

    def __str__(self):
        """可读表示：用户 - 设备名。"""
        #: 返回结果并结束当前函数
        return f'{self.user} - {self.device_name}'


class ThemePreset(models.Model):
    """主题配色预设：主色 / 强调色 / 背景色 / 文字色四个 HEX。"""

    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='theme_presets', verbose_name='用户')
    #: 定义变量「name」，保存对应数据（Django 模型字段，参与建表）
    name = models.CharField(max_length=50, verbose_name='主题名称')
    #: 定义变量「primary_color」，保存对应数据（Django 模型字段，参与建表）
    primary_color = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=7, default='#a06cd5', verbose_name='主色')
    #: 定义变量「accent_color」，保存对应数据（Django 模型字段，参与建表）
    accent_color = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=7, default='#ff8fb1', verbose_name='强调色')
    #: 定义变量「bg_color」，保存对应数据（Django 模型字段，参与建表）
    bg_color = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=7, default='#f4f2fb', verbose_name='背景色')
    #: 定义变量「text_color」，保存对应数据（Django 模型字段，参与建表）
    text_color = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=7, default='#2b2340', verbose_name='文字色')
    #: 定义变量「is_active」，保存对应数据（Django 模型字段，参与建表）
    is_active = models.BooleanField(
        #: 定义变量「default」，保存对应数据
        default=False, verbose_name='是否当前使用')
    #: 定义变量「created_at」，保存对应数据（Django 模型字段，参与建表）
    created_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='创建时间')

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
        db_table = 'blog_theme_preset'
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：用户 - 主题名。"""
        #: 返回结果并结束当前函数
        return f'{self.user} - {self.name}'


class SearchHistory(models.Model):
    """搜索历史：用户可空（匿名记 IP），含结果数。"""

    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE, null=True, blank=True,
        #: 定义变量「related_name」，保存对应数据
        related_name='search_history', verbose_name='用户')
    #: 定义变量「query」，保存对应数据（Django 模型字段，参与建表）
    query = models.CharField(max_length=200, verbose_name='搜索词')
    #: 定义变量「ip_address」，保存对应数据（Django 模型字段，参与建表）
    ip_address = models.GenericIPAddressField(
        #: 定义变量「null」，保存对应数据
        null=True, blank=True, verbose_name='IP')
    #: 定义变量「result_count」，保存对应数据（Django 模型字段，参与建表）
    result_count = models.PositiveIntegerField(
        #: 定义变量「default」，保存对应数据
        default=0, verbose_name='结果数')
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
          - indexes

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「db_table」，保存对应数据
        db_table = 'blog_search_history'
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-created_at']
        #: 定义变量「indexes」，保存对应数据（集合/元组）
        indexes = [
            #: 调用「models.Index」执行相应逻辑
            models.Index(fields=['query']),
            #: 调用「models.Index」执行相应逻辑
            models.Index(fields=['user', '-created_at'])]

    def __str__(self):
        """可读表示：搜索词 (用户或IP)。"""
        #: 返回结果并结束当前函数
        return f'{self.query} ({self.user or self.ip_address})'


class ExportJob(models.Model):
    """异步数据导出任务：类型 / 格式 / 状态 / 条数 / 产物路径 / 错误。"""

    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='export_jobs', verbose_name='用户')
    #: 定义变量「export_type」，保存对应数据（Django 模型字段，参与建表）
    export_type = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=30, verbose_name='导出类型')
    #: 定义变量「format」，保存对应数据（Django 模型字段，参与建表）
    format = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=10, default='json', verbose_name='格式')
    #: 定义变量「status」，保存对应数据（Django 模型字段，参与建表）
    status = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=20, default='pending', verbose_name='状态')
    #: 定义变量「file_path」，保存对应数据（Django 模型字段，参与建表）
    file_path = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=500, blank=True, verbose_name='文件路径')
    #: 定义变量「item_count」，保存对应数据（Django 模型字段，参与建表）
    item_count = models.PositiveIntegerField(
        #: 定义变量「default」，保存对应数据
        default=0, verbose_name='导出条数')
    #: 定义变量「error_message」，保存对应数据（Django 模型字段，参与建表）
    error_message = models.TextField(
        #: 定义变量「blank」，保存对应数据
        blank=True, verbose_name='错误信息')
    #: 定义变量「created_at」，保存对应数据（Django 模型字段，参与建表）
    created_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='创建时间')
    #: 定义变量「completed_at」，保存对应数据（Django 模型字段，参与建表）
    completed_at = models.DateTimeField(
        #: 定义变量「null」，保存对应数据
        null=True, blank=True, verbose_name='完成时间')

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
        db_table = 'blog_export_job'
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：用户 导出 类型 (状态)。"""
        #: 返回结果并结束当前函数
        return f'{self.user} 导出 {self.export_type} ({self.status})'


class UserWidget(models.Model):
    """用户仪表盘组件：类型 + 标题 + 位置 + 可见性 + JSON 配置。"""

    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='widgets', verbose_name='用户')
    #: 定义变量「widget_type」，保存对应数据（Django 模型字段，参与建表）
    widget_type = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=50, verbose_name='组件类型')
    #: 定义变量「title」，保存对应数据（Django 模型字段，参与建表）
    title = models.CharField(max_length=100, verbose_name='标题')
    #: 定义变量「position」，保存对应数据（Django 模型字段，参与建表）
    position = models.PositiveIntegerField(
        #: 定义变量「default」，保存对应数据
        default=0, verbose_name='位置')
    #: 定义变量「is_visible」，保存对应数据（Django 模型字段，参与建表）
    is_visible = models.BooleanField(
        #: 定义变量「default」，保存对应数据
        default=True, verbose_name='是否显示')
    #: 定义变量「config」，保存对应数据（Django 模型字段，参与建表）
    config = models.JSONField(default=dict, verbose_name='配置')
    #: 定义变量「created_at」，保存对应数据（Django 模型字段，参与建表）
    created_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='创建时间')

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
        db_table = 'blog_user_widget'
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['position']

    def __str__(self):
        """可读表示：用户 - 标题。"""
        #: 返回结果并结束当前函数
        return f'{self.user} - {self.title}'

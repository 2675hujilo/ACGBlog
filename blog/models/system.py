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
from django.db import models


class UserAPIKey(models.Model):
    """用户 API 密钥：哈希 + 前缀 + 启用 / 过期 / 最后使用时间。"""

    user = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='api_keys', verbose_name='用户')
    name = models.CharField(max_length=100, verbose_name='密钥名称')
    key_hash = models.CharField(
        max_length=128, unique=True, verbose_name='密钥哈希')
    key_prefix = models.CharField(
        max_length=8, verbose_name='密钥前缀')
    is_active = models.BooleanField(
        default=True, verbose_name='是否启用')
    last_used_at = models.DateTimeField(
        null=True, blank=True, verbose_name='最后使用时间')
    expires_at = models.DateTimeField(
        null=True, blank=True, verbose_name='过期时间')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'blog_user_api_key'
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：用户 - 密钥名。"""
        return f'{self.user} - {self.name}'


class Webhook(models.Model):
    """Webhook 配置：回调 URL + 监听事件 + 签名密钥 + 失败计数。"""

    user = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='webhooks', verbose_name='用户')
    url = models.URLField(max_length=500, verbose_name='回调URL')
    events = models.CharField(
        max_length=500, verbose_name='监听事件（逗号分隔）')
    secret = models.CharField(
        max_length=100, verbose_name='签名密钥')
    is_active = models.BooleanField(
        default=True, verbose_name='是否启用')
    last_triggered_at = models.DateTimeField(
        null=True, blank=True, verbose_name='最后触发时间')
    failure_count = models.PositiveIntegerField(
        default=0, verbose_name='失败次数')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'blog_webhook'
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：用户 -> URL 前50字。"""
        return f'{self.user} -> {self.url[:50]}'


class UserDevice(models.Model):
    """用户设备 / 会话：设备名、类型、系统、浏览器、IP、最后活跃。"""

    user = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='devices', verbose_name='用户')
    device_name = models.CharField(
        max_length=100, verbose_name='设备名称')
    device_type = models.CharField(
        max_length=20, verbose_name='设备类型')
    os = models.CharField(
        max_length=50, blank=True, verbose_name='操作系统')
    browser = models.CharField(
        max_length=50, blank=True, verbose_name='浏览器')
    ip_address = models.GenericIPAddressField(verbose_name='IP')
    last_active_at = models.DateTimeField(
        auto_now=True, verbose_name='最后活跃时间')
    is_current = models.BooleanField(
        default=False, verbose_name='是否当前设备')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='登录时间')

    class Meta:
        db_table = 'blog_user_device'
        ordering = ['-last_active_at']

    def __str__(self):
        """可读表示：用户 - 设备名。"""
        return f'{self.user} - {self.device_name}'


class ThemePreset(models.Model):
    """主题配色预设：主色 / 强调色 / 背景色 / 文字色四个 HEX。"""

    user = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='theme_presets', verbose_name='用户')
    name = models.CharField(max_length=50, verbose_name='主题名称')
    primary_color = models.CharField(
        max_length=7, default='#a06cd5', verbose_name='主色')
    accent_color = models.CharField(
        max_length=7, default='#ff8fb1', verbose_name='强调色')
    bg_color = models.CharField(
        max_length=7, default='#f4f2fb', verbose_name='背景色')
    text_color = models.CharField(
        max_length=7, default='#2b2340', verbose_name='文字色')
    is_active = models.BooleanField(
        default=False, verbose_name='是否当前使用')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'blog_theme_preset'
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：用户 - 主题名。"""
        return f'{self.user} - {self.name}'


class SearchHistory(models.Model):
    """搜索历史：用户可空（匿名记 IP），含结果数。"""

    user = models.ForeignKey(
        'User', on_delete=models.CASCADE, null=True, blank=True,
        related_name='search_history', verbose_name='用户')
    query = models.CharField(max_length=200, verbose_name='搜索词')
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, verbose_name='IP')
    result_count = models.PositiveIntegerField(
        default=0, verbose_name='结果数')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='时间')

    class Meta:
        db_table = 'blog_search_history'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['query']),
            models.Index(fields=['user', '-created_at'])]

    def __str__(self):
        """可读表示：搜索词 (用户或IP)。"""
        return f'{self.query} ({self.user or self.ip_address})'


class ExportJob(models.Model):
    """异步数据导出任务：类型 / 格式 / 状态 / 条数 / 产物路径 / 错误。"""

    user = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='export_jobs', verbose_name='用户')
    export_type = models.CharField(
        max_length=30, verbose_name='导出类型')
    format = models.CharField(
        max_length=10, default='json', verbose_name='格式')
    status = models.CharField(
        max_length=20, default='pending', verbose_name='状态')
    file_path = models.CharField(
        max_length=500, blank=True, verbose_name='文件路径')
    item_count = models.PositiveIntegerField(
        default=0, verbose_name='导出条数')
    error_message = models.TextField(
        blank=True, verbose_name='错误信息')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='创建时间')
    completed_at = models.DateTimeField(
        null=True, blank=True, verbose_name='完成时间')

    class Meta:
        db_table = 'blog_export_job'
        ordering = ['-created_at']

    def __str__(self):
        """可读表示：用户 导出 类型 (状态)。"""
        return f'{self.user} 导出 {self.export_type} ({self.status})'


class UserWidget(models.Model):
    """用户仪表盘组件：类型 + 标题 + 位置 + 可见性 + JSON 配置。"""

    user = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='widgets', verbose_name='用户')
    widget_type = models.CharField(
        max_length=50, verbose_name='组件类型')
    title = models.CharField(max_length=100, verbose_name='标题')
    position = models.PositiveIntegerField(
        default=0, verbose_name='位置')
    is_visible = models.BooleanField(
        default=True, verbose_name='是否显示')
    config = models.JSONField(default=dict, verbose_name='配置')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'blog_user_widget'
        ordering = ['position']

    def __str__(self):
        """可读表示：用户 - 标题。"""
        return f'{self.user} - {self.title}'

# -*- coding: utf-8 -*-
"""
日志领域模型 —— 访问日志、修改日志与登录历史。

本文件从原 ``blog/models.py`` 拆出，含：

- :class:`AccessLog`：每次 HTTP 请求的访问明细，由访问日志中间件写入，是全站
  流量分析、周 / 月榜热度、安全审计的数据源（全局永久强制模块，不可破坏）；
- :class:`EditLog`：文章轻量修改日志（修改人 + 时间 + 修改前正文快照）；
- :class:`LoginHistory`：登录历史（IP / UA / 设备 / 位置 / 是否成功），安全审计。

表名与拆分前一致，不产生数据库结构变更；用户外键以字符串引用。

维护注意点
----------
1. AccessLog 写入优先走 Celery 异步，Redis Broker 故障时写入 Redis 兜底队列，
   极端情况才同步入库，避免高并发压库（三级降级策略，详见 README 运维章节）；
2. AccessLog 冗余 username，用户删除后日志仍可读；user 外键为 SET_NULL；
3. EditLog 同时保存 content_snapshot 供详情页「查看快照」对照（只看不改）；
4. 日志字段多为排查 / 审计用途，展示时注意敏感信息脱敏与长度截断。
"""
import re

from django.db import models


class AccessLog(models.Model):
    """访问日志：请求 / 响应 / 来源 / 视图 / 耗时等完整明细。"""

    ip_address = models.GenericIPAddressField(
        verbose_name='IP地址', null=True, blank=True)
    user = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='access_logs', verbose_name='用户')
    # 冗余用户名，用户删除后日志仍可读
    username = models.CharField(
        max_length=150, blank=True, default='', verbose_name='用户名')
    session_key = models.CharField(
        max_length=64, blank=True, default='', verbose_name='会话ID')
    path = models.CharField(
        max_length=255, verbose_name='请求路径')
    full_url = models.TextField(
        blank=True, default='', verbose_name='完整URL')
    method = models.CharField(max_length=10, verbose_name='请求方法')
    status_code = models.PositiveIntegerField(
        default=0, verbose_name='响应状态码')
    duration_ms = models.FloatField(
        default=0, verbose_name='耗时(毫秒)')
    referer = models.TextField(
        blank=True, default='', verbose_name='来源页')
    user_agent = models.TextField(
        blank=True, default='', verbose_name='User-Agent')
    browser = models.CharField(
        max_length=100, blank=True, default='', verbose_name='浏览器')
    os = models.CharField(
        max_length=100, blank=True, default='', verbose_name='操作系统')
    view_func = models.CharField(
        max_length=200, blank=True, default='', verbose_name='视图函数')
    view_args = models.TextField(
        blank=True, default='', verbose_name='视图位置参数')
    view_kwargs = models.TextField(
        blank=True, default='', verbose_name='视图关键字参数')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='访问时间')

    class Meta:
        db_table = 'blog_access_log'
        verbose_name = '访问日志'
        verbose_name_plural = '访问日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['path'])]

    def __str__(self):
        """可读表示：IP [方法] 路径 -> 状态码 (耗时ms)。"""
        return (f'{self.ip_address} [{self.method}] {self.path} -> '
                f'{self.status_code} ({self.duration_ms:.0f}ms)')


class EditLog(models.Model):
    """文章修改日志：修改人 + 时间 + 修改前正文快照。"""

    article = models.ForeignKey(
        'Article', on_delete=models.CASCADE,
        related_name='edit_logs', verbose_name='文章')
    editor = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='edit_logs', verbose_name='修改人')
    edited_at = models.DateTimeField(
        auto_now_add=True, verbose_name='修改时间')
    content_snapshot = models.TextField(
        blank=True, default='', verbose_name='修改前内容快照')

    class Meta:
        db_table = 'blog_edit_log'
        verbose_name = '修改日志'
        verbose_name_plural = '修改日志'
        ordering = ['-edited_at']

    def __str__(self):
        """可读表示：某人 于 时间 修改《文章》。"""
        return (f'{self.editor} 于 {self.edited_at:%Y-%m-%d %H:%M} '
                f'修改《{self.article.title}》')

    @property
    def snapshot_preview(self):
        """快照纯文本预览（前 100 字），供后台列表展示。"""
        text = re.sub(r'<[^>]+>', '', self.content_snapshot or '')
        text = re.sub(r'\s+', ' ', text).strip()
        return (text[:100] + '…') if len(text) > 100 else text

    @property
    def snapshot_plain(self):
        """快照纯文本全文，供快照弹窗对照展示。"""
        text = re.sub(r'<[^>]+>', '', self.content_snapshot or '')
        return re.sub(r'\s+', ' ', text).strip()


class LoginHistory(models.Model):
    """登录历史：IP / UA / 设备类型 / 位置 / 是否成功，安全审计用。"""

    user = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='login_history', verbose_name='用户')
    ip_address = models.GenericIPAddressField(verbose_name='IP')
    user_agent = models.CharField(
        max_length=500, verbose_name='User-Agent')
    device_type = models.CharField(
        max_length=20, default='desktop', verbose_name='设备类型')
    location = models.CharField(
        max_length=100, blank=True, verbose_name='地理位置')
    success = models.BooleanField(
        default=True, verbose_name='是否成功')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='时间')

    class Meta:
        db_table = 'blog_login_history'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at'])]

    def __str__(self):
        """可读表示：用户 @ IP。"""
        return f'{self.user} @ {self.ip_address}'

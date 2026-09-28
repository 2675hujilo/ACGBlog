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
#: 导入模块「re」，供本文件后续使用
import re

#: 从模块「django.db」导入所需对象
from django.db import models


class AccessLog(models.Model):
    """访问日志：请求 / 响应 / 来源 / 视图 / 耗时等完整明细。"""

    #: 定义变量「ip_address」，保存对应数据（Django 模型字段，参与建表）
    ip_address = models.GenericIPAddressField(
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='IP地址', null=True, blank=True)
    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        #: 定义变量「related_name」，保存对应数据
        related_name='access_logs', verbose_name='用户')
    # 冗余用户名，用户删除后日志仍可读
    #: 定义变量「username」，保存对应数据（Django 模型字段，参与建表）
    username = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=150, blank=True, default='', verbose_name='用户名')
    #: 定义变量「session_key」，保存对应数据（Django 模型字段，参与建表）
    session_key = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=64, blank=True, default='', verbose_name='会话ID')
    #: 定义变量「path」，保存对应数据（Django 模型字段，参与建表）
    path = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=255, verbose_name='请求路径')
    #: 定义变量「full_url」，保存对应数据（Django 模型字段，参与建表）
    full_url = models.TextField(
        #: 定义变量「blank」，保存对应数据
        blank=True, default='', verbose_name='完整URL')
    #: 定义变量「method」，保存对应数据（Django 模型字段，参与建表）
    method = models.CharField(max_length=10, verbose_name='请求方法')
    #: 定义变量「status_code」，保存对应数据（Django 模型字段，参与建表）
    status_code = models.PositiveIntegerField(
        #: 定义变量「default」，保存对应数据
        default=0, verbose_name='响应状态码')
    #: 定义变量「duration_ms」，保存对应数据（Django 模型字段，参与建表）
    duration_ms = models.FloatField(
        #: 定义变量「default」，保存对应数据
        default=0, verbose_name='耗时(毫秒)')
    #: 定义变量「referer」，保存对应数据（Django 模型字段，参与建表）
    referer = models.TextField(
        #: 定义变量「blank」，保存对应数据
        blank=True, default='', verbose_name='来源页')
    #: 定义变量「user_agent」，保存对应数据（Django 模型字段，参与建表）
    user_agent = models.TextField(
        #: 定义变量「blank」，保存对应数据
        blank=True, default='', verbose_name='User-Agent')
    #: 定义变量「browser」，保存对应数据（Django 模型字段，参与建表）
    browser = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=100, blank=True, default='', verbose_name='浏览器')
    #: 定义变量「os」，保存对应数据（Django 模型字段，参与建表）
    os = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=100, blank=True, default='', verbose_name='操作系统')
    #: 定义变量「view_func」，保存对应数据（Django 模型字段，参与建表）
    view_func = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=200, blank=True, default='', verbose_name='视图函数')
    #: 定义变量「view_args」，保存对应数据（Django 模型字段，参与建表）
    view_args = models.TextField(
        #: 定义变量「blank」，保存对应数据
        blank=True, default='', verbose_name='视图位置参数')
    #: 定义变量「view_kwargs」，保存对应数据（Django 模型字段，参与建表）
    view_kwargs = models.TextField(
        #: 定义变量「blank」，保存对应数据
        blank=True, default='', verbose_name='视图关键字参数')
    #: 定义变量「created_at」，保存对应数据（Django 模型字段，参与建表）
    created_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='访问时间')

    class Meta:
        """
        类 Meta：meta。

        字段/类属性：
          - db_table：str
          - verbose_name：str
          - verbose_name_plural：str
          - ordering
          - indexes

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「db_table」，保存对应数据
        db_table = 'blog_access_log'
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name = '访问日志'
        #: 定义变量「verbose_name_plural」，保存对应数据
        verbose_name_plural = '访问日志'
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-created_at']
        #: 定义变量「indexes」，保存对应数据（集合/元组）
        indexes = [
            #: 调用「models.Index」执行相应逻辑
            models.Index(fields=['created_at']),
            #: 调用「models.Index」执行相应逻辑
            models.Index(fields=['ip_address']),
            #: 调用「models.Index」执行相应逻辑
            models.Index(fields=['path'])]

    def __str__(self):
        """可读表示：IP [方法] 路径 -> 状态码 (耗时ms)。"""
        #: 返回结果并结束当前函数
        return (f'{self.ip_address} [{self.method}] {self.path} -> '
                #: 该行执行对应逻辑（结合上下文理解）
                f'{self.status_code} ({self.duration_ms:.0f}ms)')


class EditLog(models.Model):
    """文章修改日志：修改人 + 时间 + 修改前正文快照。"""

    #: 定义变量「article」，保存对应数据（Django 模型字段，参与建表）
    article = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'Article', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='edit_logs', verbose_name='文章')
    #: 定义变量「editor」，保存对应数据（Django 模型字段，参与建表）
    editor = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='edit_logs', verbose_name='修改人')
    #: 定义变量「edited_at」，保存对应数据（Django 模型字段，参与建表）
    edited_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='修改时间')
    #: 定义变量「content_snapshot」，保存对应数据（Django 模型字段，参与建表）
    content_snapshot = models.TextField(
        #: 定义变量「blank」，保存对应数据
        blank=True, default='', verbose_name='修改前内容快照')

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
        db_table = 'blog_edit_log'
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name = '修改日志'
        #: 定义变量「verbose_name_plural」，保存对应数据
        verbose_name_plural = '修改日志'
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-edited_at']

    def __str__(self):
        """可读表示：某人 于 时间 修改《文章》。"""
        #: 返回结果并结束当前函数
        return (f'{self.editor} 于 {self.edited_at:%Y-%m-%d %H:%M} '
                #: 该行执行对应逻辑（结合上下文理解）
                f'修改《{self.article.title}》')

    #: 装饰器：为下一个定义附加「property」行为（权限、缓存、注册信号等）
    @property
    def snapshot_preview(self):
        """快照纯文本预览（前 100 字），供后台列表展示。"""
        #: 定义变量「text」，保存对应数据
        text = re.sub(r'<[^>]+>', '', self.content_snapshot or '')
        #: 定义变量「text」，保存对应数据
        text = re.sub(r'\s+', ' ', text).strip()
        #: 返回结果并结束当前函数
        return (text[:100] + '…') if len(text) > 100 else text

    #: 装饰器：为下一个定义附加「property」行为（权限、缓存、注册信号等）
    @property
    def snapshot_plain(self):
        """快照纯文本全文，供快照弹窗对照展示。"""
        #: 定义变量「text」，保存对应数据
        text = re.sub(r'<[^>]+>', '', self.content_snapshot or '')
        #: 返回结果并结束当前函数
        return re.sub(r'\s+', ' ', text).strip()


class LoginHistory(models.Model):
    """登录历史：IP / UA / 设备类型 / 位置 / 是否成功，安全审计用。"""

    #: 定义变量「user」，保存对应数据（Django 模型字段，参与建表）
    user = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='login_history', verbose_name='用户')
    #: 定义变量「ip_address」，保存对应数据（Django 模型字段，参与建表）
    ip_address = models.GenericIPAddressField(verbose_name='IP')
    #: 定义变量「user_agent」，保存对应数据（Django 模型字段，参与建表）
    user_agent = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=500, verbose_name='User-Agent')
    #: 定义变量「device_type」，保存对应数据（Django 模型字段，参与建表）
    device_type = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=20, default='desktop', verbose_name='设备类型')
    #: 定义变量「location」，保存对应数据（Django 模型字段，参与建表）
    location = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=100, blank=True, verbose_name='地理位置')
    #: 定义变量「success」，保存对应数据（Django 模型字段，参与建表）
    success = models.BooleanField(
        #: 定义变量「default」，保存对应数据
        default=True, verbose_name='是否成功')
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
        db_table = 'blog_login_history'
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-created_at']
        #: 定义变量「indexes」，保存对应数据（集合/元组）
        indexes = [
            #: 调用「models.Index」执行相应逻辑
            models.Index(fields=['user', '-created_at'])]

    def __str__(self):
        """可读表示：用户 @ IP。"""
        #: 返回结果并结束当前函数
        return f'{self.user} @ {self.ip_address}'

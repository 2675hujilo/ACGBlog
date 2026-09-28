# -*- coding: utf-8 -*-
"""
文案覆盖领域模型 —— 全站文案的数据库可编辑层与弃用归档。

本文件从原 ``blog/models.py`` 拆出，包含：

- :class:`SiteMessage`：全站文案「覆盖项」，让运营在后台改提示词而不用改代码、
  不用重启；只保存被改过的那几条，代码默认值仍是唯一全量登记处；
- :class:`SiteMessageRetired`：被弃用的文案 key（从总表删除、不再渲染统计），
  删除是可逆的（删本表记录即恢复）。

为什么是「覆盖」而不是「全量入库」
----------------------------------
1. **零启动依赖**：进程启动即有全量文案，数据库挂了 / 迁移没跑也不出现满屏
   占位符；
2. **性能几乎无成本**：读取侧把整表合并成一个 dict 缓存，热路径是字典查找、
   零 SQL；
3. **可审计**：表里有什么就是「被改过的文案」清单；
4. **可回滚**：关闭 ``is_enabled`` 或删除记录立刻回代码默认值。

表名与字段均与拆分前一致，不产生数据库结构变更。

维护注意点
----------
1. SiteMessage.key 与文案登记处（services/site_messages.py）中的 key 对应，
   单字段唯一；占位符写法必须与原文一致，否则格式化失败回退原文；
2. 保存 / 删除覆盖项后必须调用 site_messages.invalidate_overrides 使缓存失效；
3. 只应弃用「未接入」的 key；仍被模板 / 视图引用的 key 弃用后会走 ``⟪key⟫``
   兜底并被回归检查发现。
"""
from django.db import models


class SiteMessage(models.Model):
    """全站文案覆盖项：key 定位，text 为自定义内容，is_enabled 控制是否生效。"""

    # 文案键：唯一并加索引，对应 site_messages 登记处的 key
    key = models.CharField(
        max_length=120, unique=True, db_index=True,
        verbose_name='文案键',
        help_text='对应 site_messages 中的 key，例如 auth.login_failed')
    # 文案内容：支持 {} / {name} 占位符，写法须与原文一致
    text = models.TextField(
        verbose_name='文案内容',
        help_text='支持占位符，写法必须与原文案一致，否则格式化失败会回退原文')
    # 用途备注：给自己看的说明
    description = models.CharField(
        max_length=200, blank=True, default='',
        verbose_name='用途备注',
        help_text='例如「登录失败提示，出现在登录页顶部」')
    # 启用覆盖：取消勾选即恢复代码默认文案（无需删除记录）
    is_enabled = models.BooleanField(
        default=True, verbose_name='启用覆盖',
        help_text='取消勾选即恢复代码里的默认文案（无需删除记录）')
    # 最后修改人
    updated_by = models.ForeignKey(
        'User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='site_messages_updated',
        verbose_name='最后修改人')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '文案覆盖'
        verbose_name_plural = '文案覆盖（提示词）'
        ordering = ['key']
        indexes = [
            models.Index(fields=['is_enabled', 'key'],
                         name='idx_msg_enabled_key')]

    def __str__(self):
        """可读表示：「key = 内容前30字」，停用时追加标记。"""
        flag = '' if self.is_enabled else '（已停用）'
        return '%s = %s%s' % (self.key, self.text[:30], flag)

    def save(self, *args, **kwargs):
        """保存后立刻让覆盖层缓存失效，全站下一次取文案即生效。

        site_messages 为业务服务模块（归类后位于 blog/services/）。
        """
        super().save(*args, **kwargs)
        from ..services.site_messages import invalidate_overrides
        invalidate_overrides()

    def delete(self, *args, **kwargs):
        """删除后同样失效缓存，恢复到代码默认值。"""
        result = super().delete(*args, **kwargs)
        from ..services.site_messages import invalidate_overrides
        invalidate_overrides()
        return result


class SiteMessageRetired(models.Model):
    """被弃用的文案 key：从文案总表删除，不再参与渲染与统计。

    有些 key 属「预留登记」：注册了但无任何界面引用，留着只会让运营困惑。
    管理员可在页面删除，本表记录被删 key；site_messages.all_messages() 用
    本表过滤。删除可逆：删本表记录即恢复该文案。
    """

    key = models.CharField(
        '文案 key', max_length=120, unique=True,
        help_text='被弃用的文案标识，如 nav.home')
    reason = models.CharField(
        '弃用原因', max_length=200, blank=True, default='')
    retired_by = models.ForeignKey(
        'blog.User', verbose_name='操作人', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='retired_site_messages')
    created_at = models.DateTimeField(
        '弃用时间', auto_now_add=True)

    class Meta:
        verbose_name = '弃用文案'
        verbose_name_plural = '弃用文案'
        ordering = ('key',)

    def __str__(self):  # pragma: no cover - 仅用于后台显示
        return self.key

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
#: 从模块「django.db」导入所需对象
from django.db import models


class SiteMessage(models.Model):
    """全站文案覆盖项：key 定位，text 为自定义内容，is_enabled 控制是否生效。"""

    # 文案键：唯一并加索引，对应 site_messages 登记处的 key
    #: 定义变量「key」，保存对应数据（Django 模型字段，参与建表）
    key = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=120, unique=True, db_index=True,
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='文案键',
        #: 定义变量「help_text」，保存对应数据
        help_text='对应 site_messages 中的 key，例如 auth.login_failed')
    # 文案内容：支持 {} / {name} 占位符，写法须与原文一致
    #: 定义变量「text」，保存对应数据（Django 模型字段，参与建表）
    text = models.TextField(
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='文案内容',
        #: 定义变量「help_text」，保存对应数据
        help_text='支持占位符，写法必须与原文案一致，否则格式化失败会回退原文')
    # 用途备注：给自己看的说明
    #: 定义变量「description」，保存对应数据（Django 模型字段，参与建表）
    description = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=200, blank=True, default='',
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='用途备注',
        #: 定义变量「help_text」，保存对应数据
        help_text='例如「登录失败提示，出现在登录页顶部」')
    # 启用覆盖：取消勾选即恢复代码默认文案（无需删除记录）
    #: 定义变量「is_enabled」，保存对应数据（Django 模型字段，参与建表）
    is_enabled = models.BooleanField(
        #: 定义变量「default」，保存对应数据
        default=True, verbose_name='启用覆盖',
        #: 定义变量「help_text」，保存对应数据
        help_text='取消勾选即恢复代码里的默认文案（无需删除记录）')
    # 最后修改人
    #: 定义变量「updated_by」，保存对应数据（Django 模型字段，参与建表）
    updated_by = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', null=True, blank=True, on_delete=models.SET_NULL,
        #: 定义变量「related_name」，保存对应数据
        related_name='site_messages_updated',
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='最后修改人')
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
          - verbose_name：str
          - verbose_name_plural：str
          - ordering
          - indexes

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name = '文案覆盖'
        #: 定义变量「verbose_name_plural」，保存对应数据
        verbose_name_plural = '文案覆盖（提示词）'
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['key']
        #: 定义变量「indexes」，保存对应数据（集合/元组）
        indexes = [
            #: 调用「models.Index」执行相应逻辑
            models.Index(fields=['is_enabled', 'key'],
                         #: 定义变量「name」，保存对应数据
                         name='idx_msg_enabled_key')]

    def __str__(self):
        """可读表示：「key = 内容前30字」，停用时追加标记。"""
        #: 定义变量「flag」，保存对应数据
        flag = '' if self.is_enabled else '（已停用）'
        #: 返回结果并结束当前函数
        return '%s = %s%s' % (self.key, self.text[:30], flag)

    def save(self, *args, **kwargs):
        """保存后立刻让覆盖层缓存失效，全站下一次取文案即生效。

        site_messages 为业务服务模块（归类后位于 blog/services/）。
        """
        #: 调用「super」执行相应逻辑
        super().save(*args, **kwargs)
        #: 从模块「..services.site_messages」导入所需对象
        from ..services.site_messages import invalidate_overrides
        #: 调用「invalidate_overrides」执行相应逻辑
        invalidate_overrides()

    def delete(self, *args, **kwargs):
        """删除后同样失效缓存，恢复到代码默认值。"""
        #: 定义变量「result」，保存对应数据
        result = super().delete(*args, **kwargs)
        #: 从模块「..services.site_messages」导入所需对象
        from ..services.site_messages import invalidate_overrides
        #: 调用「invalidate_overrides」执行相应逻辑
        invalidate_overrides()
        #: 返回结果并结束当前函数
        return result


class SiteMessageRetired(models.Model):
    """被弃用的文案 key：从文案总表删除，不再参与渲染与统计。

    有些 key 属「预留登记」：注册了但无任何界面引用，留着只会让运营困惑。
    管理员可在页面删除，本表记录被删 key；site_messages.all_messages() 用
    本表过滤。删除可逆：删本表记录即恢复该文案。
    """

    #: 定义变量「key」，保存对应数据（Django 模型字段，参与建表）
    key = models.CharField(
        #: 该行执行对应逻辑（结合上下文理解）
        '文案 key', max_length=120, unique=True,
        #: 定义变量「help_text」，保存对应数据
        help_text='被弃用的文案标识，如 nav.home')
    #: 定义变量「reason」，保存对应数据（Django 模型字段，参与建表）
    reason = models.CharField(
        #: 该行执行对应逻辑（结合上下文理解）
        '弃用原因', max_length=200, blank=True, default='')
    #: 定义变量「retired_by」，保存对应数据（Django 模型字段，参与建表）
    retired_by = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'blog.User', verbose_name='操作人', null=True, blank=True,
        #: 定义变量「on_delete」，保存对应数据（Django 模型字段，参与建表）
        on_delete=models.SET_NULL,
        #: 定义变量「related_name」，保存对应数据
        related_name='retired_site_messages')
    #: 定义变量「created_at」，保存对应数据（Django 模型字段，参与建表）
    created_at = models.DateTimeField(
        #: 该行执行对应逻辑（结合上下文理解）
        '弃用时间', auto_now_add=True)

    class Meta:
        """
        类 Meta：meta。

        字段/类属性：
          - verbose_name：str
          - verbose_name_plural：str
          - ordering

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name = '弃用文案'
        #: 定义变量「verbose_name_plural」，保存对应数据
        verbose_name_plural = '弃用文案'
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ('key',)

    def __str__(self):  # pragma: no cover - 仅用于后台显示
        """
        功能：处理「str」相关逻辑。

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 返回结果并结束当前函数
        return self.key

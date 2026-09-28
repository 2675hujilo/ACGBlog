# -*- coding: utf-8 -*-
"""
内容审核领域模型 —— 审核日志 / 审核设置 / 推广申请。

本文件从原 ``blog/models.py`` 拆出，包含：

- :class:`ModerationLog`：审核操作流水（谁对文章 / 评论做了什么动作、理由、
  对象标题快照），是「审核历史」时间线的数据源；
- :class:`ModerationSettings`：审核全局设置单例（文章 / 评论是否需审核、评论
  撤回时限、置顶上限），通过 :meth:`ModerationSettings.load` 带缓存读取；
- :class:`PromotionRequest`：作者申请置顶 / 精华 / 热门的工单，含「审批结论」
  与「系统执行状态」两个维度。

与文章状态机的关系
------------------
- 普通作者发文：``require_article_review=True`` 时进入 PENDING，否则直接
  PUBLISHED；管理员发文始终可直接发布；
- 每次审核动作（提交 / 通过 / 驳回 / 删除 / 恢复 / 置顶等）都写 ModerationLog；
- PromotionRequest 审批后由审核视图实际切换 Article 标记，并回写执行状态、
  向申请人发通知。

表名与字段均与拆分前一致，不产生数据库结构变更，外键以字符串引用。

维护注意点
----------
1. ModerationSettings 为单例（pk=1），save 强制 pk 并失效缓存，不要直接
   create 第二条；
2. PromotionRequest 的申请人字段是 ``applicant``、类型字段是 ``kind``，
   ``execution_status`` 单独表达「是否真正落地」，勿与审批 status 混淆；
3. ModerationLog 外键多为 SET_NULL + 冗余名字 / 标题，对象删除后历史仍可读。
"""
#: 从模块「django.db」导入所需对象
from django.db import models


class ModerationLog(models.Model):
    """审核操作日志：记录管理员对文章 / 评论的每次审核动作。

    形成可追溯的审核历史时间线，支持按文章或动作筛选。
    """

    class Action(models.TextChoices):
        """审核动作枚举。"""

        #: 定义变量「SUBMIT」，保存对应数据
        SUBMIT = 'submit', '提交审核'
        #: 定义变量「APPROVE」，保存对应数据
        APPROVE = 'approve', '审核通过'
        #: 定义变量「REJECT」，保存对应数据
        REJECT = 'reject', '审核驳回'
        #: 定义变量「SOFT_DELETE」，保存对应数据
        SOFT_DELETE = 'soft_delete', '删除（隐藏）'
        #: 定义变量「RESTORE」，保存对应数据
        RESTORE = 'restore', '恢复'
        #: 定义变量「HARD_DELETE」，保存对应数据
        HARD_DELETE = 'hard_delete', '彻底删除'
        # 置顶 / 精华 / 热门的设置与取消
        #: 定义变量「PIN」，保存对应数据
        PIN = 'pin', '置顶'
        #: 定义变量「UNPIN」，保存对应数据
        UNPIN = 'unpin', '取消置顶'
        #: 定义变量「FEATURE」，保存对应数据
        FEATURE = 'feature', '加精华'
        #: 定义变量「UNFEATURE」，保存对应数据
        UNFEATURE = 'unfeature', '取消精华'
        #: 定义变量「HOT」，保存对应数据
        HOT = 'hot', '设热门'
        #: 定义变量「UNHOT」，保存对应数据
        UNHOT = 'unhot', '取消热门'

    # 执行审核的管理员；管理员删除时日志保留、外键置空
    #: 定义变量「moderator」，保存对应数据（Django 模型字段，参与建表）
    moderator = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        #: 定义变量「related_name」，保存对应数据
        related_name='moderation_logs', verbose_name='审核人')
    # 冗余审核人名字符串，账号删除后日志仍可读
    #: 定义变量「moderator_name」，保存对应数据（Django 模型字段，参与建表）
    moderator_name = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=150, blank=True, default='',
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='审核人姓名')
    # 审核动作：带 Action choices
    #: 定义变量「action」，保存对应数据（Django 模型字段，参与建表）
    action = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=15, choices=Action.choices,
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='审核动作')
    # 审核对象类型：article / comment
    #: 定义变量「target_type」，保存对应数据（Django 模型字段，参与建表）
    target_type = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=10, default='article', verbose_name='对象类型')
    # 关联文章（评论审核也记录所属文章）；文章彻底删除时置空
    #: 定义变量「article」，保存对应数据（Django 模型字段，参与建表）
    article = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'Article', on_delete=models.SET_NULL, null=True, blank=True,
        #: 定义变量「related_name」，保存对应数据
        related_name='moderation_logs', verbose_name='所属文章')
    # 关联评论（仅评论审核时填写）
    #: 定义变量「comment」，保存对应数据（Django 模型字段，参与建表）
    comment = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'Comment', on_delete=models.SET_NULL, null=True, blank=True,
        #: 定义变量「related_name」，保存对应数据
        related_name='moderation_logs', verbose_name='关联评论')
    # 对象标题 / 摘要快照，防止对象删除后历史不可读
    #: 定义变量「target_title」，保存对应数据（Django 模型字段，参与建表）
    target_title = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=200, blank=True, default='',
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='对象标题快照')
    # 审核理由 / 备注
    #: 定义变量「reason」，保存对应数据（Django 模型字段，参与建表）
    reason = models.TextField(
        #: 定义变量「blank」，保存对应数据
        blank=True, default='', verbose_name='审核理由')
    # 操作时间
    #: 定义变量「created_at」，保存对应数据（Django 模型字段，参与建表）
    created_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='操作时间')

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
        db_table = 'blog_moderation_log'
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name = '审核日志'
        #: 定义变量「verbose_name_plural」，保存对应数据
        verbose_name_plural = '审核日志'
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-created_at']
        #: 定义变量「indexes」，保存对应数据（集合/元组）
        indexes = [
            #: 调用「models.Index」执行相应逻辑
            models.Index(fields=['-created_at'], name='idx_modlog_ct'),
            #: 调用「models.Index」执行相应逻辑
            models.Index(fields=['article', '-created_at'],
                         #: 定义变量「name」，保存对应数据
                         name='idx_modlog_art_ct'),
            #: 调用「models.Index」执行相应逻辑
            models.Index(fields=['action'], name='idx_modlog_action'),
        #: 该行执行对应逻辑（结合上下文理解）
        ]

    def __str__(self):
        """可读表示：「审核人 动作 对象类型「标题前20字」」。"""
        #: 返回结果并结束当前函数
        return (f'{self.moderator_name} {self.get_action_display()} '
                #: 该行执行对应逻辑（结合上下文理解）
                f'{self.target_type}「{self.target_title[:20]}」')


class ModerationSettings(models.Model):
    """内容审核全局设置单例：审核开关 / 评论撤回时限 / 置顶上限。

    全站仅一条（pk=1），管理员在审核页「全局设置」面板修改；读取侧通过
    :meth:`load` 拿对象（带缓存），保存时自动失效。
    """

    #: 定义变量「require_article_review」，保存对应数据（Django 模型字段，参与建表）
    require_article_review = models.BooleanField(
        #: 定义变量「default」，保存对应数据
        default=True, verbose_name='普通作者新文章需审核',
        #: 定义变量「help_text」，保存对应数据
        help_text='关闭后普通作者提交即发布；管理员发文始终可直接发布')
    #: 定义变量「require_comment_review」，保存对应数据（Django 模型字段，参与建表）
    require_comment_review = models.BooleanField(
        #: 定义变量「default」，保存对应数据
        default=False, verbose_name='新评论需审核',
        #: 定义变量「help_text」，保存对应数据
        help_text='开启后新评论先待审核，通过后才公开')
    # 评论可自行撤回的时长（分钟），超时不可撤回
    #: 定义变量「comment_recall_minutes」，保存对应数据（Django 模型字段，参与建表）
    comment_recall_minutes = models.PositiveIntegerField(
        #: 定义变量「default」，保存对应数据
        default=10, verbose_name='评论可撤回时长（分钟）',
        #: 定义变量「help_text」，保存对应数据
        help_text='超过该时长不可自行撤回')
    # 全站置顶文章数量上限
    #: 定义变量「max_pinned」，保存对应数据（Django 模型字段，参与建表）
    max_pinned = models.PositiveIntegerField(
        #: 定义变量「default」，保存对应数据
        default=3, verbose_name='置顶文章数量上限')

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
        db_table = 'blog_moderation_settings'
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name = '审核全局设置'
        #: 定义变量「verbose_name_plural」，保存对应数据
        verbose_name_plural = '审核全局设置'

    def __str__(self):
        """
        功能：处理「str」相关逻辑。

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 返回结果并结束当前函数
        return '审核全局设置'

    # 单例固定主键与缓存键（类常量，便于外部引用）
    #: 定义变量「SINGLETON_ID」，保存对应数据
    SINGLETON_ID = 1
    #: 定义变量「CACHE_KEY」，保存对应数据
    CACHE_KEY = 'moderation_settings_singleton'

    def save(self, *args, **kwargs):
        """保存时强制 pk=1（单例）并清除读取缓存。"""
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
        """读取全站唯一审核设置（带缓存）；不存在时用默认值创建。

        :return: ModerationSettings 实例，调用方一定能拿到。
        """
        #: 从模块「django.core.cache」导入所需对象
        from django.core.cache import cache
        #: 读写缓存，减轻数据库压力，注意键与过期时间
        obj = cache.get(cls.CACHE_KEY)
        #: 条件判断：条件成立时执行该分支
        if obj is not None:
            #: 返回结果并结束当前函数
            return obj
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        obj, _ = cls.objects.get_or_create(pk=cls.SINGLETON_ID, defaults={})
        #: 读写缓存，减轻数据库压力，注意键与过期时间
        cache.set(cls.CACHE_KEY, obj, 3600)
        #: 返回结果并结束当前函数
        return obj


class PromotionRequest(models.Model):
    """推广申请：作者对已发布文章申请置顶 / 精华 / 热门，管理员审批。

    - 作者在详情页点按钮、弹窗填理由后生成一条 PENDING 记录；
    - 管理员通过后由审核视图把 Article 对应标记置 True；驳回置 REJECTED；
    - 处理结果写 ModerationLog，并向申请人发站内通知。
    """

    class Kind(models.TextChoices):
        """申请类型：置顶 / 精华 / 热门。"""

        #: 定义变量「PIN」，保存对应数据
        PIN = 'pin', '置顶'
        #: 定义变量「FEATURE」，保存对应数据
        FEATURE = 'feature', '精华'
        #: 定义变量「HOT」，保存对应数据
        HOT = 'hot', '热门'

    class Status(models.TextChoices):
        """审批状态：待审核 / 已通过 / 已驳回。"""

        #: 定义变量「PENDING」，保存对应数据
        PENDING = 'pending', '待审核'
        #: 定义变量「APPROVED」，保存对应数据
        APPROVED = 'approved', '已通过'
        #: 定义变量「REJECTED」，保存对应数据
        REJECTED = 'rejected', '已驳回'

    class Execution(models.TextChoices):
        """系统执行状态：单独记录「服务端有没有真正执行生效」。

        背景：管理员点「通过置顶」，但全站置顶数已达上限时系统并不会真正
        置顶；此前只显示「已通过」，作者与管理员都看不出实际结果。现在把
        「审批结论」与「系统执行」拆成两个维度。
        """

        #: 定义变量「NOT_RUN」，保存对应数据
        NOT_RUN = 'not_run', '未执行'
        #: 定义变量「SUCCESS」，保存对应数据
        SUCCESS = 'success', '执行成功'
        #: 定义变量「SKIPPED」，保存对应数据
        SKIPPED = 'skipped', '未执行·已达上限'
        #: 定义变量「FAILED」，保存对应数据
        FAILED = 'failed', '执行失败'

    # 申请对应的文章；文章删除则申请一并删除
    #: 定义变量「article」，保存对应数据（Django 模型字段，参与建表）
    article = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'Article', on_delete=models.CASCADE,
        #: 定义变量「related_name」，保存对应数据
        related_name='promotion_requests', verbose_name='文章')
    # 申请人；账号删除则置空、申请保留
    #: 定义变量「applicant」，保存对应数据（Django 模型字段，参与建表）
    applicant = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        #: 定义变量「related_name」，保存对应数据
        related_name='promotion_requests', verbose_name='申请人')
    # 申请类型（置顶 / 精华 / 热门）
    #: 定义变量「kind」，保存对应数据（Django 模型字段，参与建表）
    kind = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=10, choices=Kind.choices,
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='申请类型')
    # 申请理由
    #: 定义变量「reason」，保存对应数据（Django 模型字段，参与建表）
    reason = models.TextField(
        #: 定义变量「blank」，保存对应数据
        blank=True, default='', verbose_name='申请理由')
    # 审批状态，默认待审核
    #: 定义变量「status」，保存对应数据（Django 模型字段，参与建表）
    status = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=10, choices=Status.choices,
        #: 定义变量「default」，保存对应数据
        default=Status.PENDING, verbose_name='状态')
    # ---- 系统执行状态三件套（审批结论之外的真实落地结果）----
    #: 定义变量「execution_status」，保存对应数据（Django 模型字段，参与建表）
    execution_status = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=10, choices=Execution.choices,
        #: 定义变量「default」，保存对应数据
        default=Execution.NOT_RUN, verbose_name='系统执行状态',
        #: 定义变量「help_text」，保存对应数据
        help_text='审批通过后系统实际落地结果：成功 / 已达上限未执行 / 失败')
    # 系统执行说明（如「置顶已达上限 3 篇」）
    #: 定义变量「execution_note」，保存对应数据（Django 模型字段，参与建表）
    execution_note = models.CharField(
        #: 定义变量「max_length」，保存对应数据
        max_length=200, blank=True, default='',
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='系统执行说明')
    # 系统执行时刻
    #: 定义变量「executed_at」，保存对应数据（Django 模型字段，参与建表）
    executed_at = models.DateTimeField(
        #: 定义变量「null」，保存对应数据
        null=True, blank=True, verbose_name='系统执行时间')
    # 审核人；账号删除置空
    #: 定义变量「handled_by」，保存对应数据（Django 模型字段，参与建表）
    handled_by = models.ForeignKey(
        #: 该行执行对应逻辑（结合上下文理解）
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        #: 定义变量「related_name」，保存对应数据
        related_name='handled_promotion_requests',
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name='审核人')
    # 处理时间
    #: 定义变量「handled_at」，保存对应数据（Django 模型字段，参与建表）
    handled_at = models.DateTimeField(
        #: 定义变量「null」，保存对应数据
        null=True, blank=True, verbose_name='处理时间')
    # 申请时间
    #: 定义变量「created_at」，保存对应数据（Django 模型字段，参与建表）
    created_at = models.DateTimeField(
        #: 定义变量「auto_now_add」，保存对应数据
        auto_now_add=True, verbose_name='申请时间')

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
        db_table = 'blog_promotion_request'
        #: 定义变量「verbose_name」，保存对应数据
        verbose_name = '推广申请'
        #: 定义变量「verbose_name_plural」，保存对应数据
        verbose_name_plural = '推广申请'
        #: 定义变量「ordering」，保存对应数据（集合/元组）
        ordering = ['-created_at']
        #: 定义变量「indexes」，保存对应数据（集合/元组）
        indexes = [
            #: 调用「models.Index」执行相应逻辑
            models.Index(fields=['status', '-created_at'],
                         #: 定义变量「name」，保存对应数据
                         name='idx_promo_status_ct'),
            #: 调用「models.Index」执行相应逻辑
            models.Index(fields=['kind', 'status'],
                         #: 定义变量「name」，保存对应数据
                         name='idx_promo_kind_status'),
        #: 该行执行对应逻辑（结合上下文理解）
        ]

    def __str__(self):
        """可读表示：「类型申请：文章ID（状态）」。"""
        #: 返回结果并结束当前函数
        return (f'{self.get_kind_display()}申请：文章{self.article_id}'
                #: 该行执行对应逻辑（结合上下文理解）
                f'（{self.get_status_display()}）')

    #: 装饰器：为下一个定义附加「property」行为（权限、缓存、注册信号等）
    @property
    def is_applied(self) -> bool:
        """审批通过后系统是否真的把标记写进文章（审核页高亮用）。"""
        #: 返回结果并结束当前函数
        return self.execution_status == self.Execution.SUCCESS

    #: 装饰器：为下一个定义附加「property」行为（权限、缓存、注册信号等）
    @property
    def execution_label(self) -> str:
        """系统执行状态的中文短标签（审核页徽章文案）。"""
        #: 返回结果并结束当前函数
        return self.get_execution_status_display()

# -*- coding: utf-8 -*-
"""blog.middleware —— 中间件包（工单 15 重构 + Bug9 扩展）。

原先所有中间件都堆在单个 ``middleware.py`` 中，现按「一个中间件一个文件」拆分为：

- :mod:`~blog.middleware.site_info`      SiteInfoMiddleware：站点信息单例注入；
- :mod:`~blog.middleware.site_messages`  SiteMessagesMiddleware：全站文案注入（Bug9）；
- :mod:`~blog.middleware.access_log`     AccessLogMiddleware：访问日志（三层降级）；
- :mod:`~blog.middleware.online_status`  OnlineStatusMiddleware：在线状态；
- :mod:`~blog.middleware.cute_error_pages` CuteErrorPagesMiddleware：萌系错误页；
- :mod:`~blog.middleware.slow_query`     SlowQueryFilter：慢 SQL 日志过滤器。

为保持向后兼容（settings 中仍以 ``blog.middleware.X`` 形式引用），
本 ``__init__`` 统一再导出全部公开类。
"""
# 再导出全部公开符号，保证 blog.middleware.X 旧引用方式继续可用
#: 从模块「.slow_query」导入所需对象
from .slow_query import SlowQueryFilter
#: 从模块「.access_log」导入所需对象
from .access_log import AccessLogMiddleware
#: 从模块「.online_status」导入所需对象
from .online_status import OnlineStatusMiddleware
#: 从模块「.cute_error_pages」导入所需对象
from .cute_error_pages import CuteErrorPagesMiddleware
#: 从模块「.site_info」导入所需对象
from .site_info import SiteInfoMiddleware
#: 从模块「.site_messages」导入所需对象
from .site_messages import SiteMessagesMiddleware
#: 从模块「.mascot」导入所需对象
from .mascot import MascotToggleMiddleware

#: 定义变量「__all__」，保存对应数据（集合/元组）
__all__ = [
    #: 该行执行对应逻辑（结合上下文理解）
    'SlowQueryFilter',
    #: 该行执行对应逻辑（结合上下文理解）
    'AccessLogMiddleware',
    #: 该行执行对应逻辑（结合上下文理解）
    'OnlineStatusMiddleware',
    #: 该行执行对应逻辑（结合上下文理解）
    'CuteErrorPagesMiddleware',
    #: 该行执行对应逻辑（结合上下文理解）
    'SiteInfoMiddleware',
    #: 该行执行对应逻辑（结合上下文理解）
    'SiteMessagesMiddleware',
    #: 该行执行对应逻辑（结合上下文理解）
    'MascotToggleMiddleware',
#: 该行执行对应逻辑（结合上下文理解）
]

# -*- coding: utf-8 -*-
"""blog.middleware —— 中间件包（工单 15 重构）。

原先所有中间件都堆在单个 ``middleware.py`` 中，现按「一个中间件一个文件」拆分为：

- :mod:`~blog.middleware.site_info`        SiteInfoMiddleware：站点信息单例注入；
- :mod:`~blog.middleware.access_log`       AccessLogMiddleware：访问日志（含同步降级）；
- :mod:`~blog.middleware.online_status`    OnlineStatusMiddleware：在线状态；
- :mod:`~blog.middleware.cute_error_pages` CuteErrorPagesMiddleware：萌系错误页；
- :mod:`~blog.middleware.slow_query`       SlowQueryFilter：慢 SQL 日志过滤器。

为保持向后兼容（settings 中仍以 ``blog.middleware.X`` 形式引用），
本 ``__init__`` 统一再导出全部公开类。
"""
# 再导出全部公开符号，保证 blog.middleware.X 旧引用方式继续可用
from .slow_query import SlowQueryFilter
from .access_log import AccessLogMiddleware
from .online_status import OnlineStatusMiddleware
from .cute_error_pages import CuteErrorPagesMiddleware
from .site_info import SiteInfoMiddleware

__all__ = [
    'SlowQueryFilter',
    'AccessLogMiddleware',
    'OnlineStatusMiddleware',
    'CuteErrorPagesMiddleware',
    'SiteInfoMiddleware',
]

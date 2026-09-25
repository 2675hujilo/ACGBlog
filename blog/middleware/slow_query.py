# -*- coding: utf-8 -*-
"""慢 SQL 日志过滤器（从原 blog/middleware.py 拆出，工单 15）。

供 ``LOGGING.filters`` 引用，仅放行执行耗时超过 0.5 秒的数据库语句，
避免正常 SQL 噪音淹没真正需要关注的慢查询。
"""
import logging
import re


class SlowQueryFilter(logging.Filter):
    """日志过滤器：只放行执行耗时 > 500ms 的慢 SQL。"""

    # 预编译耗时匹配，Django SQL 日志形如 ".... (0.123) ; args=..."
    _DURATION_RE = re.compile(r'\(([\d.]+)\)\s')

    def filter(self, record):
        try:
            msg = record.getMessage()
            match = self._DURATION_RE.search(msg)
            if not match:
                return False
            return float(match.group(1)) > 0.5
        except (ValueError, TypeError):
            return False

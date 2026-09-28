# -*- coding: utf-8 -*-
"""慢 SQL 日志过滤器（从原 blog/middleware.py 拆出，工单 15）。

供 ``LOGGING.filters`` 引用，仅放行执行耗时超过 0.5 秒的数据库语句，
避免正常 SQL 噪音淹没真正需要关注的慢查询。
"""
#: 导入模块「logging」，供本文件后续使用
import logging
#: 导入模块「re」，供本文件后续使用
import re


class SlowQueryFilter(logging.Filter):
    """日志过滤器：只放行执行耗时 > 500ms 的慢 SQL。"""

    # 预编译耗时匹配，Django SQL 日志形如 ".... (0.123) ; args=..."
    #: 定义变量「_DURATION_RE」，保存对应数据
    _DURATION_RE = re.compile(r'\(([\d.]+)\)\s')

    def filter(self, record):
        """
        功能：处理「filter」相关逻辑。

        参数：
          - record：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 尝试执行可能出错的代码
        try:
            #: 定义变量「msg」，保存对应数据
            msg = record.getMessage()
            #: 定义变量「match」，保存对应数据
            match = self._DURATION_RE.search(msg)
            #: 条件判断：条件成立时执行该分支
            if not match:
                #: 返回结果并结束当前函数
                return False
            #: 返回结果并结束当前函数
            return float(match.group(1)) > 0.5
        #: 捕获并处理异常，避免程序中断
        except (ValueError, TypeError):
            #: 返回结果并结束当前函数
            return False

# -*- coding: utf-8 -*-
"""在线状态中间件（从原 blog/middleware.py 拆出，工单 15）。

每 5 分钟最多刷新一次当前登录用户的 ``last_active`` 时间，用于「当前在线」统计，
同时避免每个请求都写库造成的开销。
"""
#: 导入模块「time」，供本文件后续使用
import time

#: 从模块「django.utils」导入所需对象
from django.utils import timezone


class OnlineStatusMiddleware:
    """在线状态中间件：节流刷新登录用户的 last_active。"""

    # 刷新间隔（秒），与「当前在线」判定窗口保持一致量级
    #: 定义变量「UPDATE_INTERVAL」，保存对应数据
    UPDATE_INTERVAL = 300

    def __init__(self, get_response):
        """
        功能：初始化「init」。

        参数：
          - get_response：传入参数，含义结合函数体与调用处

        返回：无显式返回（None），多以副作用为主。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 定义实例/类属性「self.get_response」，保存对应数据
        self.get_response = get_response

    def __call__(self, request):
        """
        功能：处理「call」相关逻辑。

        参数：
          - request：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 定义变量「user」，保存对应数据
        user = getattr(request, 'user', None)
        #: 条件判断：条件成立时执行该分支
        if user is not None and user.is_authenticated and hasattr(request, 'session'):
            #: 定义变量「now_ts」，保存对应数据
            now_ts = time.time()
            #: 定义变量「last_ts」，保存对应数据
            last_ts = request.session.get('last_active_update', 0)
            #: 尝试执行可能出错的代码
            try:
                #: 定义变量「last_ts」，保存对应数据
                last_ts = float(last_ts)
            #: 捕获并处理异常，避免程序中断
            except (TypeError, ValueError):
                #: 定义变量「last_ts」，保存对应数据
                last_ts = 0
            #: 条件判断：条件成立时执行该分支
            if now_ts - last_ts > self.UPDATE_INTERVAL:
                #: 尝试执行可能出错的代码
                try:
                    #: 获取当前时间（时区感知），统一时间口径
                    user.last_active = timezone.now()
                    #: 调用「user.save」执行相应逻辑
                    user.save(update_fields=['last_active'])
                    #: 操作「request」的属性或方法
                    request.session['last_active_update'] = now_ts
                #: 捕获并处理异常，避免程序中断
                except Exception:  # noqa: BLE001 在线状态失败不影响请求
                    #: 占位语句：此处暂不需要实现
                    pass
        #: 返回结果并结束当前函数
        return self.get_response(request)

# -*- coding: utf-8 -*-
"""在线状态中间件（从原 blog/middleware.py 拆出，工单 15）。

每 5 分钟最多刷新一次当前登录用户的 ``last_active`` 时间，用于「当前在线」统计，
同时避免每个请求都写库造成的开销。
"""
import time

from django.utils import timezone


class OnlineStatusMiddleware:
    """在线状态中间件：节流刷新登录用户的 last_active。"""

    # 刷新间隔（秒），与「当前在线」判定窗口保持一致量级
    UPDATE_INTERVAL = 300

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated and hasattr(request, 'session'):
            now_ts = time.time()
            last_ts = request.session.get('last_active_update', 0)
            try:
                last_ts = float(last_ts)
            except (TypeError, ValueError):
                last_ts = 0
            if now_ts - last_ts > self.UPDATE_INTERVAL:
                try:
                    user.last_active = timezone.now()
                    user.save(update_fields=['last_active'])
                    request.session['last_active_update'] = now_ts
                except Exception:  # noqa: BLE001 在线状态失败不影响请求
                    pass
        return self.get_response(request)

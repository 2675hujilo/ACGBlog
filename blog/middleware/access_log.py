# -*- coding: utf-8 -*-
"""访问日志中间件（从原 blog/middleware.py 拆出，工单 15；工单 10 增加同步降级）。

职责：为每个非静态资源请求采集访问元信息（IP / 用户 / 路径 / 状态码 / 耗时 /
UA / 来源等），优先异步投递给 Celery worker 落库；当 Redis broker 不可用、
任务投递失败时，**降级为同步写入**，保证访问数据不因基础设施故障而整天缺失
（此前 broker 宕机期间的访问日志会被直接丢弃，导致看板趋势出现空白天）。
"""
import time

from django.utils.deprecation import MiddlewareMixin

import logging

logger = logging.getLogger(__name__)


class AccessLogMiddleware(MiddlewareMixin):
    """访问日志中间件：记录每次请求的元信息并持久化（异步优先，失败同步兜底）。"""

    def process_request(self, request):
        """请求进入时记录开始时间戳，用于响应时计算耗时。"""
        request._access_log_start_time = time.time()

    def process_response(self, request, response):
        """响应返回前采集日志并投递；静态 / 媒体资源直接跳过。"""
        if self._is_asset(request.path):
            return response
        start_time = getattr(request, '_access_log_start_time', None)
        duration_ms = (time.time() - start_time) * 1000 if start_time else 0

        user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
        username = user.username if user else ''

        session_key = ''
        if hasattr(request, 'session'):
            session_key = request.session.session_key or ''

        ip_address = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        try:
            browser, os_name = self._parse_user_agent(user_agent)
        except (TypeError, AttributeError):
            browser, os_name = '未知', '未知'

        view_func = ''
        if hasattr(request, 'resolver_match') and request.resolver_match:
            view_func = request.resolver_match.view_name or ''

        log_data = {
            'ip_address': ip_address or None,
            'user_id': user.id if user else None,
            'username': username, 'session_key': session_key,
            'path': request.path, 'full_url': request.build_absolute_uri(),
            'method': request.method, 'status_code': response.status_code,
            'duration_ms': round(duration_ms, 2),
            'referer': request.META.get('HTTP_REFERER', ''),
            'user_agent': user_agent, 'browser': browser, 'os': os_name,
            'view_func': view_func, 'view_args': '', 'view_kwargs': '',
        }

        # ---- 访问日志落库 ----
        # Bug12修复：原逻辑 save_access_log.delay() 仅在「broker 连不上」时才同步兜底；
        # 但当 Redis 正常、却没有 Celery worker 消费时，.delay() 不会抛错，任务被静默
        # 丢弃（实测近 3 小时日志全部缺失）。访问日志只是一条廉价的单行 INSERT，
        # 为保证任何环境都能完整记录「用户/时间/路由」，这里直接同步写入，不再依赖 worker。
        try:
            from ..models import AccessLog
            AccessLog.objects.create(**log_data)
        except Exception:  # noqa: BLE001 写入失败时记录明确错误，不影响正常响应
            logger.error('[accesslog] 访问日志写入失败: %s', request.path, exc_info=True)
        return response

    def _is_asset(self, path):
        """静态 / 媒体资源不记入访问日志，避免污染 PV/UV/趋势统计。"""
        return (path.startswith('/static/') or path.startswith('/media/')
                or path.startswith('/favicon') or path == '/robots.txt')

    def _get_client_ip(self, request):
        """获取真实客户端 IP；优先取 X-Forwarded-For 首段（反向代理场景）。"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

    def _parse_user_agent(self, ua):
        """轻量 UA 解析：识别常见浏览器与操作系统，无需第三方库。"""
        browser = '未知'
        os_name = '未知'
        ua_lower = ua.lower()
        if 'edg' in ua_lower:
            browser = 'Edge'
        elif 'chrome' in ua_lower and 'safari' in ua_lower:
            browser = 'Chrome'
        elif 'firefox' in ua_lower:
            browser = 'Firefox'
        elif 'safari' in ua_lower and 'chrome' not in ua_lower:
            browser = 'Safari'
        if 'windows nt 10' in ua_lower:
            os_name = 'Windows 10/11'
        elif 'windows' in ua_lower:
            os_name = 'Windows'
        elif 'mac os x' in ua_lower or 'macintosh' in ua_lower:
            os_name = 'macOS'
        elif 'android' in ua_lower:
            os_name = 'Android'
        elif 'iphone' in ua_lower or 'ipad' in ua_lower:
            os_name = 'iOS'
        elif 'linux' in ua_lower:
            os_name = 'Linux'
        return browser, os_name

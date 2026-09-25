# -*- coding: utf-8 -*-
"""访问日志中间件 —— 「全局永久强制模块」，不可删除、不可破坏。

职责：为每个非静态资源请求采集访问元信息（IP / 用户 / 路径 / 状态码 / 耗时 /
UA / 来源等），并按下面的三层降级策略投递入库，**永不阻塞 Web 请求**：

    ┌ 层 1 · 正常 ────────────────────────────────────────────────┐
    │ save_access_log.delay(payload) → Redis broker → Celery worker│
    │ 异步入库；请求线程只做一次入队，不产生任何数据库写入。        │
    └─────────────────────────────────────────────────────────────┘
                   │ delay() 抛错（broker 连不上）
                   ▼
    ┌ 层 2 · Broker 故障 ────────────────────────────────────────┐
    │ RPUSH acgblog:access_log:fallback（Redis 兜底队列，带短超时）│
    │ 不写库；Broker 恢复后用管理命令批量消费：                    │
    │     python manage.py accesslog_queue --drain                 │
    └─────────────────────────────────────────────────────────────┘
                   │ Redis 也写不进去（完全不可用）
                   ▼
    ┌ 层 3 · 极端降级 ──────────────────────────────────────────┐
    │ 同步 AccessLog.objects.create() 保证日志不丢，并打 ERROR 告警│
    │ 仅此一层允许同步入库；常态严禁全量同步，防止高并发压库。     │
    └─────────────────────────────────────────────────────────────┘

相关实现：``blog/access_log_service.py``（投递通道）、
``blog/tasks.py::save_access_log``（worker 落库）、
``blog/management/commands/accesslog_queue.py``（兜底队列运维命令）。
"""
import logging
import time

from django.utils.deprecation import MiddlewareMixin

from ..access_log_service import (broker_available, enqueue_fallback,
                                  mark_broker_broken)

logger = logging.getLogger(__name__)


class AccessLogMiddleware(MiddlewareMixin):
    """访问日志中间件：异步优先 → Redis 兜底 → 极端同步（三层，见模块 docstring）。"""

    def process_request(self, request):
        """请求进入时记录开始时间戳，用于响应时计算耗时。"""
        request._access_log_start_time = time.time()

    def process_response(self, request, response):
        """响应返回前采集日志并投递；静态 / 媒体资源直接跳过。"""
        from django.conf import settings
        if not getattr(settings, 'ACCESS_LOG_ENABLED', True):
            return response
        if self._is_asset(request.path):
            return response
        start_time = getattr(request, '_access_log_start_time', None)
        duration_ms = (time.time() - start_time) * 1000 if start_time else 0

        user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
        username = user.username if user else ''

        session_key = ''
        if hasattr(request, 'session'):
            try:
                session_key = request.session.session_key or ''
            except Exception:  # noqa: BLE001 会话不可用不影响日志采集
                session_key = ''

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

        self._dispatch(log_data, request.path)
        return response

    # ------------------------------------------------------------------
    # 三层投递
    # ------------------------------------------------------------------
    def _dispatch(self, log_data, path):
        """按「异步 → Redis 兜底 → 同步」顺序投递一条访问日志。

        关键性能约束：任何一层都不得让请求线程长时间等待。
        - 层1 通过 ``broker_available()`` 熔断判断：broker 已知不可用时**直接跳过**，
          不会每次请求都去白白等待连接超时（实测未熔断时单请求要 6.2s）；
        - 层2 Redis 客户端带 0.35s socket 超时 + 20s 熔断；
        - 层3 只有前两层都失败才同步写库。
        """
        # ---- 层 1：Celery 异步（正常路径，不写库、不阻塞）----
        if broker_available():
            try:
                from ..tasks import save_access_log
                save_access_log.delay(log_data)
                return
            except Exception as exc:  # noqa: BLE001 broker 不可用 → 熔断并进入层 2
                mark_broker_broken(exc)

        # ---- 层 2：Redis 兜底队列（仍不写库，等 Broker 恢复后批量消费）----
        if enqueue_fallback(log_data):
            logger.info('[accesslog] 已写入 Redis 兜底队列（Broker 恢复后请执行 '
                        'manage.py accesslog_queue --drain）')
            return

        # ---- 层 3：极端降级，Redis 完全不可用时才同步入库，保证不丢日志 ----
        try:
            from ..models import AccessLog
            AccessLog.objects.create(**log_data)
            logger.error('[accesslog] Redis 与 Broker 均不可用，已同步入库兜底: %s', path)
        except Exception:  # noqa: BLE001 写入失败时记录明确错误，不影响正常响应
            logger.error('[accesslog] 访问日志写入失败: %s', path, exc_info=True)

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
        ua_lower = (ua or '').lower()
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

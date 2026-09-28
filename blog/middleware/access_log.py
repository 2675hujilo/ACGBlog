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

相关实现：``blog/services/access_log_service.py``（投递通道）、
``blog/tasks.py::save_access_log``（worker 落库）、
``blog/management/commands/accesslog_queue.py``（兜底队列运维命令）。
"""
#: 导入模块「logging」，供本文件后续使用
import logging
#: 导入模块「time」，供本文件后续使用
import time

#: 从模块「django.utils.deprecation」导入所需对象
from django.utils.deprecation import MiddlewareMixin

#: 从模块「..services.access_log_service」导入所需对象
from ..services.access_log_service import (broker_available, enqueue_fallback,
                                  #: 该行执行对应逻辑（结合上下文理解）
                                  mark_broker_broken)

#: 定义变量「logger」，保存对应数据
logger = logging.getLogger(__name__)


class AccessLogMiddleware(MiddlewareMixin):
    """访问日志中间件：异步优先 → Redis 兜底 → 极端同步（三层，见模块 docstring）。"""

    def process_request(self, request):
        """请求进入时记录开始时间戳，用于响应时计算耗时。"""
        #: 定义实例/类属性「request._access_log_start_time」，保存对应数据
        request._access_log_start_time = time.time()

    def process_response(self, request, response):
        """响应返回前采集日志并投递；静态 / 媒体资源直接跳过。"""
        #: 从模块「django.conf」导入所需对象
        from django.conf import settings
        #: 条件判断：条件成立时执行该分支
        if not getattr(settings, 'ACCESS_LOG_ENABLED', True):
            #: 返回结果并结束当前函数
            return response
        #: 条件判断：条件成立时执行该分支
        if self._is_asset(request.path):
            #: 返回结果并结束当前函数
            return response
        #: 定义变量「start_time」，保存对应数据
        start_time = getattr(request, '_access_log_start_time', None)
        #: 定义变量「duration_ms」，保存对应数据（集合/元组）
        duration_ms = (time.time() - start_time) * 1000 if start_time else 0

        #: 读取本次请求的 user 数据
        user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
        #: 定义变量「username」，保存对应数据
        username = user.username if user else ''

        #: 定义变量「session_key」，保存对应数据
        session_key = ''
        #: 条件判断：条件成立时执行该分支
        if hasattr(request, 'session'):
            #: 尝试执行可能出错的代码
            try:
                #: 定义变量「session_key」，保存对应数据
                session_key = request.session.session_key or ''
            #: 捕获并处理异常，避免程序中断
            except Exception:  # noqa: BLE001 会话不可用不影响日志采集
                #: 定义变量「session_key」，保存对应数据
                session_key = ''

        #: 定义变量「ip_address」，保存对应数据
        ip_address = self._get_client_ip(request)
        #: 读取本次请求的 META 数据
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        #: 尝试执行可能出错的代码
        try:
            #: 该行执行对应逻辑（结合上下文理解）
            browser, os_name = self._parse_user_agent(user_agent)
        #: 捕获并处理异常，避免程序中断
        except (TypeError, AttributeError):
            #: 该行执行对应逻辑（结合上下文理解）
            browser, os_name = '未知', '未知'

        #: 定义变量「view_func」，保存对应数据
        view_func = ''
        #: 条件判断：条件成立时执行该分支
        if hasattr(request, 'resolver_match') and request.resolver_match:
            #: 定义变量「view_func」，保存对应数据
            view_func = request.resolver_match.view_name or ''

        #: 定义变量「log_data」，保存对应数据
        log_data = {
            #: 配置项「ip_address」：字典/模型的该键设置为对应值
            'ip_address': ip_address or None,
            #: 配置项「user_id」：字典/模型的该键设置为对应值
            'user_id': user.id if user else None,
            #: 配置项「username」：字典/模型的该键设置为对应值
            'username': username, 'session_key': session_key,
            #: 配置项「path」：字典/模型的该键设置为对应值
            'path': request.path, 'full_url': request.build_absolute_uri(),
            #: 读取本次请求的 method 数据
            'method': request.method, 'status_code': response.status_code,
            #: 配置项「duration_ms」：字典/模型的该键设置为对应值
            'duration_ms': round(duration_ms, 2),
            #: 读取本次请求的 META 数据
            'referer': request.META.get('HTTP_REFERER', ''),
            #: 配置项「user_agent」：字典/模型的该键设置为对应值
            'user_agent': user_agent, 'browser': browser, 'os': os_name,
            #: 配置项「view_func」：字典/模型的该键设置为对应值
            'view_func': view_func, 'view_args': '', 'view_kwargs': '',
        #: 该行执行对应逻辑（结合上下文理解）
        }

        #: 调用「self._dispatch」执行相应逻辑
        self._dispatch(log_data, request.path)
        #: 返回结果并结束当前函数
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
        #: 条件判断：条件成立时执行该分支
        if broker_available():
            #: 尝试执行可能出错的代码
            try:
                #: 从模块「..tasks」导入所需对象
                from ..tasks import save_access_log
                #: 把任务异步投递给 Celery Worker 执行，不阻塞请求
                save_access_log.delay(log_data)
                #: 返回结果并结束当前函数
                return
            #: 捕获并处理异常，避免程序中断
            except Exception as exc:  # noqa: BLE001 broker 不可用 → 熔断并进入层 2
                #: 调用「mark_broker_broken」执行相应逻辑
                mark_broker_broken(exc)

        # ---- 层 2：Redis 兜底队列（仍不写库，等 Broker 恢复后批量消费）----
        #: 条件判断：条件成立时执行该分支
        if enqueue_fallback(log_data):
            #: 记录日志，便于排查（勿记录密码等敏感信息）
            logger.info('[accesslog] 已写入 Redis 兜底队列（Broker 恢复后请执行 '
                        #: 该行执行对应逻辑（结合上下文理解）
                        'manage.py accesslog_queue --drain）')
            #: 返回结果并结束当前函数
            return

        # ---- 层 3：极端降级，Redis 完全不可用时才同步入库，保证不丢日志 ----
        #: 尝试执行可能出错的代码
        try:
            #: 从模块「..models」导入所需对象
            from ..models import AccessLog
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            AccessLog.objects.create(**log_data)
            #: 记录日志，便于排查（勿记录密码等敏感信息）
            logger.error('[accesslog] Redis 与 Broker 均不可用，已同步入库兜底: %s', path)
        #: 捕获并处理异常，避免程序中断
        except Exception:  # noqa: BLE001 写入失败时记录明确错误，不影响正常响应
            #: 记录日志，便于排查（勿记录密码等敏感信息）
            logger.error('[accesslog] 访问日志写入失败: %s', path, exc_info=True)

    def _is_asset(self, path):
        """静态 / 媒体资源不记入访问日志，避免污染 PV/UV/趋势统计。"""
        #: 返回结果并结束当前函数
        return (path.startswith('/static/') or path.startswith('/media/')
                #: 该行执行对应逻辑（结合上下文理解）
                or path.startswith('/favicon') or path == '/robots.txt')

    def _get_client_ip(self, request):
        """获取真实客户端 IP；优先取 X-Forwarded-For 首段（反向代理场景）。"""
        #: 读取本次请求的 META 数据
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        #: 条件判断：条件成立时执行该分支
        if x_forwarded_for:
            #: 返回结果并结束当前函数
            return x_forwarded_for.split(',')[0].strip()
        #: 返回结果并结束当前函数
        return request.META.get('REMOTE_ADDR', '')

    def _parse_user_agent(self, ua):
        """轻量 UA 解析：识别常见浏览器与操作系统，无需第三方库。"""
        #: 定义变量「browser」，保存对应数据
        browser = '未知'
        #: 定义变量「os_name」，保存对应数据
        os_name = '未知'
        #: 定义变量「ua_lower」，保存对应数据（集合/元组）
        ua_lower = (ua or '').lower()
        #: 条件判断：条件成立时执行该分支
        if 'edg' in ua_lower:
            #: 定义变量「browser」，保存对应数据
            browser = 'Edge'
        #: 否则若该条件成立则进入此分支
        elif 'chrome' in ua_lower and 'safari' in ua_lower:
            #: 定义变量「browser」，保存对应数据
            browser = 'Chrome'
        #: 否则若该条件成立则进入此分支
        elif 'firefox' in ua_lower:
            #: 定义变量「browser」，保存对应数据
            browser = 'Firefox'
        #: 否则若该条件成立则进入此分支
        elif 'safari' in ua_lower and 'chrome' not in ua_lower:
            #: 定义变量「browser」，保存对应数据
            browser = 'Safari'
        #: 条件判断：条件成立时执行该分支
        if 'windows nt 10' in ua_lower:
            #: 定义变量「os_name」，保存对应数据
            os_name = 'Windows 10/11'
        #: 否则若该条件成立则进入此分支
        elif 'windows' in ua_lower:
            #: 定义变量「os_name」，保存对应数据
            os_name = 'Windows'
        #: 否则若该条件成立则进入此分支
        elif 'mac os x' in ua_lower or 'macintosh' in ua_lower:
            #: 定义变量「os_name」，保存对应数据
            os_name = 'macOS'
        #: 否则若该条件成立则进入此分支
        elif 'android' in ua_lower:
            #: 定义变量「os_name」，保存对应数据
            os_name = 'Android'
        #: 否则若该条件成立则进入此分支
        elif 'iphone' in ua_lower or 'ipad' in ua_lower:
            #: 定义变量「os_name」，保存对应数据
            os_name = 'iOS'
        #: 否则若该条件成立则进入此分支
        elif 'linux' in ua_lower:
            #: 定义变量「os_name」，保存对应数据
            os_name = 'Linux'
        #: 返回结果并结束当前函数
        return browser, os_name

# -*- coding: utf-8 -*-
"""萌系错误页中间件（从原 blog/middleware.py 拆出，工单 15）。

无论 DEBUG 取值如何，对 400 / 403 / 404 / 500 响应统一返回站内自定义的
二次元萌系错误页；``/api/`` 请求则返回 JSON 错误信封。
超级管理员可用 ``?rawdebug=1`` 临时查看原始调试信息。
"""
#: 导入模块「logging」，供本文件后续使用
import logging

#: 定义变量「logger」，保存对应数据
logger = logging.getLogger(__name__)

#: API 错误信封文案键（Bug9 任务2：统一登记在 blog/site_messages.py）
_API_MSG_KEYS = {
    #: 该行执行对应逻辑（结合上下文理解）
    400: 'err.api_400',
    #: 该行执行对应逻辑（结合上下文理解）
    403: 'err.api_403',
    #: 该行执行对应逻辑（结合上下文理解）
    404: 'err.api_404',
    #: 该行执行对应逻辑（结合上下文理解）
    500: 'err.api_500',
#: 该行执行对应逻辑（结合上下文理解）
}

#: 模板渲染失败时的内联兜底页文案键
_INLINE_TEXT_KEYS = {
    #: 该行执行对应逻辑（结合上下文理解）
    400: 'err.400_desc',
    #: 该行执行对应逻辑（结合上下文理解）
    403: 'err.403_desc',
    #: 该行执行对应逻辑（结合上下文理解）
    404: 'err.404_desc',
    #: 该行执行对应逻辑（结合上下文理解）
    500: 'err.500_desc',
#: 该行执行对应逻辑（结合上下文理解）
}


class CuteErrorPagesMiddleware:
    """让全站（含 DEBUG=True）返回自定义萌系错误页（400/403/404/500）。"""

    #: 状态码 → 用于在 HTML 中「探测」是否已被替换成自定义错误页的标记文本
    #: （Bug9：标记文本同样取自文案表，避免这里与错误页模板文案不一致）
    _MARKS = {404: '页面被喵喵吃了', 403: '这里禁止进入',
              #: 该行执行对应逻辑（结合上下文理解）
              400: '请求有点奇怪', 500: '服务器酱宕机'}

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

    def _raw(self, request):
        """超级管理员加 ?rawdebug=1 时放行原始响应，便于排查。"""
        #: 尝试执行可能出错的代码
        try:
            #: 返回结果并结束当前函数
            return (request.GET.get('rawdebug') == '1'
                    #: 读取本次请求的 user 数据
                    and getattr(request.user, 'is_superuser', False))
        #: 捕获并处理异常，避免程序中断
        except Exception:  # noqa: BLE001
            #: 返回结果并结束当前函数
            return False

    def _is_asset(self, request):
        """静态 / 媒体资源不替换错误页。"""
        #: 定义变量「path」，保存对应数据
        path = request.path
        #: 返回结果并结束当前函数
        return (path.startswith('/static/') or path.startswith('/media/')
                #: 该行执行对应逻辑（结合上下文理解）
                or path.startswith('/favicon'))

    def _is_api(self, request):
        """是否为 API 请求（API 错误统一返回 JSON）。"""
        #: 返回结果并结束当前函数
        return request.path.startswith('/api/')

    def _render(self, request, status, template):
        """按状态渲染萌系错误页；API 请求返回 JSON。

        Bug9 任务「2」：本方法内的全部用户可见文案改为从
        :mod:`blog.site_messages` 取词（原先硬编码 12 处中文）。
        ``render(request, ...)`` 会带上请求上下文，因此 404/403/400/500 模板里
        也能直接使用 ``{{ MSG.err.* }}`` 命名空间。
        """
        #: 从模块「django.http」导入所需对象
        from django.http import JsonResponse
        #: 从模块「..services.site_messages」导入所需对象
        from ..services.site_messages import msg
        #: 条件判断：条件成立时执行该分支
        if self._is_api(request):
            # API 错误信封：message 取站点文案表中的 err.api_* 键
            #: 返回结果并结束当前函数
            return JsonResponse(
                #: 该行执行对应逻辑（结合上下文理解）
                {'ok': False, 'code': status,
                 #: 配置项「message」：字典/模型的该键设置为对应值
                 'message': msg(_API_MSG_KEYS.get(status, 'err.api_generic'))},
                #: 定义变量「status」，保存对应数据
                status=status)
        #: 尝试执行可能出错的代码
        try:
            #: 从模块「django.shortcuts」导入所需对象
            from django.shortcuts import render
            #: 渲染模板并返回 HttpResponse（把上下文传给模板生成页面）
            resp = render(request, template, {}, status=status)
            #: 定义实例/类属性「resp._cute_error」，保存对应数据
            resp._cute_error = True
            #: 返回结果并结束当前函数
            return resp
        #: 捕获并处理异常，避免程序中断
        except Exception:  # noqa: BLE001 模板异常时用内联兜底页
            #: 从模块「django.http」导入所需对象
            from django.http import HttpResponse
            #: 返回结果并结束当前函数
            return HttpResponse(
                #: 该行执行对应逻辑（结合上下文理解）
                '<meta charset="utf-8"><div style="font-family:sans-serif;text-align:center;padding:80px;color:#a06cd5">'
                #: 该行执行对应逻辑（结合上下文理解）
                '<div style="font-size:3rem">😿</div><h1>%s</h1><p>%s</p>'
                #: 该行执行对应逻辑（结合上下文理解）
                '<a href="/">%s</a></div>'
                #: 该行执行对应逻辑（结合上下文理解）
                % (msg('err.inline_mark', status), msg(_INLINE_TEXT_KEYS.get(status, 'err.api_generic')),
                   #: 调用「msg」执行相应逻辑
                   msg('btn.back_home')),
                #: 定义变量「status」，保存对应数据
                status=status, content_type='text/html; charset=utf-8')

    def process_exception(self, request, exception):
        """捕获异常并按类型渲染对应错误页。"""
        #: 条件判断：条件成立时执行该分支
        if self._raw(request):
            #: 返回结果并结束当前函数
            return None
        #: 从模块「django.http」导入所需对象
        from django.http import Http404
        #: 从模块「django.core.exceptions」导入所需对象
        from django.core.exceptions import PermissionDenied, SuspiciousOperation
        #: 条件判断：条件成立时执行该分支
        if isinstance(exception, Http404):
            #: 返回结果并结束当前函数
            return self._render(request, 404, '404.html')
        #: 条件判断：条件成立时执行该分支
        if isinstance(exception, PermissionDenied):
            #: 返回结果并结束当前函数
            return self._render(request, 403, '403.html')
        #: 条件判断：条件成立时执行该分支
        if isinstance(exception, SuspiciousOperation):
            #: 记录日志，便于排查（勿记录密码等敏感信息）
            logger.warning('[mw] 400 异常请求 %s: %s', request.path, exception)
            #: 返回结果并结束当前函数
            return self._render(request, 400, '400.html')
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.exception('[mw] 500 未捕获异常: %s %s', request.method, request.path)
        #: 返回结果并结束当前函数
        return self._render(request, 500, '500.html')

    def __call__(self, request):
        """对已生成的错误响应做二次替换（未抛异常但状态码为错误码的情况）。"""
        #: 定义变量「response」，保存对应数据
        response = self.get_response(request)
        #: 条件判断：条件成立时执行该分支
        if self._raw(request) or self._is_asset(request):
            #: 返回结果并结束当前函数
            return response
        #: 条件判断：条件成立时执行该分支
        if getattr(response, '_cute_error', False):
            #: 返回结果并结束当前函数
            return response
        #: 条件判断：条件成立时执行该分支
        if self._is_api(request):
            #: 返回结果并结束当前函数
            return response
        #: 定义变量「ctype」，保存对应数据
        ctype = response.get('Content-Type', '')
        #: 条件判断：条件成立时执行该分支
        if 'text/html' not in ctype:
            #: 返回结果并结束当前函数
            return response
        #: 条件判断：条件成立时执行该分支
        if response.status_code in self._MARKS:
            #: 尝试执行可能出错的代码
            try:
                #: 定义变量「body」，保存对应数据
                body = response.content.decode('utf-8', errors='ignore')
            #: 捕获并处理异常，避免程序中断
            except Exception:  # noqa: BLE001
                #: 返回结果并结束当前函数
                return response
            #: 定义变量「mark」，保存对应数据
            mark = self._MARKS[response.status_code]
            #: 条件判断：条件成立时执行该分支
            if mark not in body:
                #: 定义变量「template」，保存对应数据
                template = {400: '400.html', 403: '403.html',
                            #: 该行执行对应逻辑（结合上下文理解）
                            404: '404.html', 500: '500.html'}[response.status_code]
                #: 返回结果并结束当前函数
                return self._render(request, response.status_code, template)
        #: 返回结果并结束当前函数
        return response

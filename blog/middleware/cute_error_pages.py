# -*- coding: utf-8 -*-
"""萌系错误页中间件（从原 blog/middleware.py 拆出，工单 15）。

无论 DEBUG 取值如何，对 400 / 403 / 404 / 500 响应统一返回站内自定义的
二次元萌系错误页；``/api/`` 请求则返回 JSON 错误信封。
超级管理员可用 ``?rawdebug=1`` 临时查看原始调试信息。
"""
import logging

logger = logging.getLogger(__name__)


class CuteErrorPagesMiddleware:
    """让全站（含 DEBUG=True）返回自定义萌系错误页（400/403/404/500）。"""

    _MARKS = {404: '页面被喵喵吃了', 403: '这里禁止进入',
              400: '请求有点奇怪', 500: '服务器酱宕机'}

    def __init__(self, get_response):
        self.get_response = get_response

    def _raw(self, request):
        """超级管理员加 ?rawdebug=1 时放行原始响应，便于排查。"""
        try:
            return (request.GET.get('rawdebug') == '1'
                    and getattr(request.user, 'is_superuser', False))
        except Exception:  # noqa: BLE001
            return False

    def _is_asset(self, request):
        """静态 / 媒体资源不替换错误页。"""
        path = request.path
        return (path.startswith('/static/') or path.startswith('/media/')
                or path.startswith('/favicon'))

    def _is_api(self, request):
        """是否为 API 请求（API 错误统一返回 JSON）。"""
        return request.path.startswith('/api/')

    def _render(self, request, status, template):
        """按状态渲染萌系错误页；API 请求返回 JSON。"""
        from django.http import JsonResponse
        if self._is_api(request):
            msgs = {400: '请求参数有误喵', 403: '没有权限哦喵',
                    404: '接口不存在喵', 500: '服务器开小差了喵'}
            return JsonResponse(
                {'ok': False, 'code': status,
                 'message': msgs.get(status, '出错了喵')}, status=status)
        try:
            from django.shortcuts import render
            resp = render(request, template, {}, status=status)
            resp._cute_error = True
            return resp
        except Exception:  # noqa: BLE001 模板异常时用内联兜底页
            from django.http import HttpResponse
            return HttpResponse(
                '<meta charset="utf-8"><div style="font-family:sans-serif;text-align:center;padding:80px;color:#a06cd5">'
                '<div style="font-size:3rem">😿</div><h1>%s</h1><p>%s</p>'
                '<a href="/">回到首页喵</a></div>'
                % (self._MARKS.get(status, '出错了喵'),
                   {400: '请求有点奇怪喵', 403: '这里禁止进入喵',
                    404: '页面被喵喵吃了喵~',
                    500: '服务器酱宕机啦…'}.get(status, '')),
                status=status, content_type='text/html; charset=utf-8')

    def process_exception(self, request, exception):
        """捕获异常并按类型渲染对应错误页。"""
        if self._raw(request):
            return None
        from django.http import Http404
        from django.core.exceptions import PermissionDenied, SuspiciousOperation
        if isinstance(exception, Http404):
            return self._render(request, 404, '404.html')
        if isinstance(exception, PermissionDenied):
            return self._render(request, 403, '403.html')
        if isinstance(exception, SuspiciousOperation):
            logger.warning('[mw] 400 异常请求 %s: %s', request.path, exception)
            return self._render(request, 400, '400.html')
        logger.exception('[mw] 500 未捕获异常: %s %s', request.method, request.path)
        return self._render(request, 500, '500.html')

    def __call__(self, request):
        """对已生成的错误响应做二次替换（未抛异常但状态码为错误码的情况）。"""
        response = self.get_response(request)
        if self._raw(request) or self._is_asset(request):
            return response
        if getattr(response, '_cute_error', False):
            return response
        if self._is_api(request):
            return response
        ctype = response.get('Content-Type', '')
        if 'text/html' not in ctype:
            return response
        if response.status_code in self._MARKS:
            try:
                body = response.content.decode('utf-8', errors='ignore')
            except Exception:  # noqa: BLE001
                return response
            mark = self._MARKS[response.status_code]
            if mark not in body:
                template = {400: '400.html', 403: '403.html',
                            404: '404.html', 500: '500.html'}[response.status_code]
                return self._render(request, response.status_code, template)
        return response

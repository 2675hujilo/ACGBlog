# -*- coding: utf-8 -*-
"""站点文案中间件（Bug9 任务「2」：全站提示词后端变量化）。

职责：把 :mod:`blog.site_messages` 中的文案表挂到每个 ``request`` 上，
供视图层直接取用，**无需在每个视图里 import**：

    def some_view(request):
        messages.success(request, request.msg('article.published'))
        messages.error(request, request.msg('promo.limit_reached', 3))

模板侧的同源变量由上下文处理器 ``site_messages_ctx`` 提供（注入 ``MSG`` 命名空间），
二者读取同一份模块级常量，不存在漂移。

与 :class:`~blog.middleware.site_info.SiteInfoMiddleware` 的分工：
- SiteInfoMiddleware 管**可运营编辑**的站点信息（站名 / Logo / 副标题，存数据库）；
- 本中间件管**代码内置**的全站提示词与按钮 / 错误页文案（存 ``site_messages.py``），
  二者互补：前者可后台改，后者随代码版本走。
"""


class SiteMessagesMiddleware:
    """把文案访问器挂到 ``request``：``request.msg(key, *args)``。"""

    def __init__(self, get_response):
        # Django 新式中间件：保存下游调用链
        self.get_response = get_response

    def __call__(self, request):
        """请求进入时挂载访问器，再交下游处理。"""
        # 使用静态方法而非闭包：避免每个请求创建新函数对象，同时便于测试替换
        request.msg = _message_getter
        request.msg_ns = _namespace_getter
        return self.get_response(request)


def _message_getter(key, *args, **kwargs):
    """``request.msg`` 的实现：委托给 :func:`blog.site_messages.msg`。

    之所以做成模块级函数而不是 lambda：便于在测试中断言 ``request.msg`` 可调用、
    也避免中间件里重复书写导入路径。
    """
    from ..services.site_messages import msg
    return msg(key, *args, **kwargs)


def _namespace_getter(prefix):
    """``request.msg_ns`` 的实现：按域取出文案字典（如 ``request.msg_ns('auth')``）。"""
    from ..services.site_messages import namespace
    return namespace(prefix)

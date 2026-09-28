# -*- coding: utf-8 -*-
"""站点信息中间件（工单 15，参考项目 SiteInfoMiddleware）。

在请求进入阶段读取数据库中的 :class:`~blog.models.SiteInfo` 单例（带缓存），
把站点名称 / Logo / 介绍等挂到 ``request`` 上，供视图与后续逻辑使用；
模板侧的同名变量由上下文处理器 ``site_info_ctx`` 提供，二者读取同一份缓存。
"""
from django.utils.deprecation import MiddlewareMixin


class SiteInfoMiddleware(MiddlewareMixin):
    """把站点信息单例注入每个 request。"""

    def process_request(self, request):
        """读取单例并挂载便捷属性；任何异常都不应阻断正常请求。"""
        try:
            from ..models import SiteInfo
            info = SiteInfo.load()
        except Exception:  # noqa: BLE001 站点信息读取失败时降级，不阻断请求
            request.site_info = None
            return
        request.site_info = info
        # 便捷属性，视图中可直接 request.site_name 取用
        request.site_name = info.site_name
        request.site_logo = info.logo_emoji
        request.site_tagline = info.tagline

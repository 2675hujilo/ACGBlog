# -*- coding: utf-8 -*-
"""站点信息中间件（工单 15，参考项目 SiteInfoMiddleware）。

在请求进入阶段读取数据库中的 :class:`~blog.models.SiteInfo` 单例（带缓存），
把站点名称 / Logo / 介绍等挂到 ``request`` 上，供视图与后续逻辑使用；
模板侧的同名变量由上下文处理器 ``site_info_ctx`` 提供，二者读取同一份缓存。
"""
#: 从模块「django.utils.deprecation」导入所需对象
from django.utils.deprecation import MiddlewareMixin


class SiteInfoMiddleware(MiddlewareMixin):
    """把站点信息单例注入每个 request。"""

    def process_request(self, request):
        """读取单例并挂载便捷属性；任何异常都不应阻断正常请求。"""
        #: 尝试执行可能出错的代码
        try:
            #: 从模块「..models」导入所需对象
            from ..models import SiteInfo
            #: 定义变量「info」，保存对应数据
            info = SiteInfo.load()
        #: 捕获并处理异常，避免程序中断
        except Exception:  # noqa: BLE001 站点信息读取失败时降级，不阻断请求
            #: 定义实例/类属性「request.site_info」，保存对应数据
            request.site_info = None
            #: 返回结果并结束当前函数
            return
        #: 定义实例/类属性「request.site_info」，保存对应数据
        request.site_info = info
        # 便捷属性，视图中可直接 request.site_name 取用
        #: 定义实例/类属性「request.site_name」，保存对应数据
        request.site_name = info.site_name
        #: 定义实例/类属性「request.site_logo」，保存对应数据
        request.site_logo = info.logo_emoji
        #: 定义实例/类属性「request.site_tagline」，保存对应数据
        request.site_tagline = info.tagline

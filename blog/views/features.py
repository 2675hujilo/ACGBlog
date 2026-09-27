# -*- coding: utf-8 -*-

"""Round5 功能开关注册表与开关接口。"""

import json
import logging
import os
import re
import uuid
from django.conf import settings
from django.http import (
    FileResponse, Http404, HttpRequest, HttpResponse,
    HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound,
    HttpResponseNotModified, HttpResponsePermanentRedirect,
    HttpResponseRedirect, JsonResponse, StreamingHttpResponse,
)
from django.views.decorators.http import require_POST
from ..site_messages import msg


logger = logging.getLogger('blog.views')

class Round5FeatureRegistry:
    """功能开关注册表（进程内），供「真实功能」声明可运维的启用/停用开关。

    为什么需要它：站点提供了一批可独立开关的功能（阅读增强、彩蛋等），
    需要一个统一的注册与查询入口，让管理员在运行时确认「哪些功能处于开启状态」，
    而不必翻代码。注册表是**真实被装饰器填充**的——使用方式::

        from blog.views import Round5FeatureRegistry

        @Round5FeatureRegistry.register('reading', 'focus_mode', '专注阅读模式')
        def focus_mode_view(request): ...

    未注册任何功能时列表为空（属正常状态），端点仍返回合法 JSON 结构。
    """

    #: 功能领域中文名（用于前端分组展示）
    DOMAINS = {
        'content': '内容创作生产域',
        'reading': '沉浸式阅读域',
        'comment': '评论社区互动域',
        'user': '用户成长与社交域',
        'ui': 'UI装扮个性化域',
        'search': '搜索内容推荐域',
        'operation': '站点运营活动域',
        'analytics': '数据分析监控域',
        'seo': 'SEO与性能扩展域',
        'accessibility': '无障碍增强域',
        'api': 'API与第三方集成域',
        'easter': '彩蛋趣味工具域',
    }

    #: 进程内注册表：feature_id -> 元信息字典
    _registry = {}

    @classmethod
    def register(cls, domain, name, description='', default_enabled=True):
        """功能注册装饰器：把视图登记进注册表，并在调用前检查开关状态。

        Args:
            domain: 领域标识（须在 ``DOMAINS`` 中，否则原样展示）。
            name: 功能短名，与领域拼成 ``feature_id``（``域名_短名``）。
            description: 中文描述，用于管理界面与关闭提示。
            default_enabled: 默认是否启用（可被 settings.ROUND5_FEATURES 覆盖）。

        Returns:
            callable: 装饰器；装饰后的视图在被调用时会先校验开关。
        """
        from functools import wraps

        def decorator(view_func):
            feature_id = '%s_%s' % (domain, name)
            cls._registry[feature_id] = {
                'id': feature_id,
                'domain': domain,
                'domain_name': cls.DOMAINS.get(domain, domain),
                'name': name,
                'description': description,
                'default_enabled': default_enabled,
            }

            @wraps(view_func)
            def wrapper(request, *args, **kwargs):
                # 功能被关闭时返回 403 + 明确文案，而不是静默失败
                if not cls.is_enabled(feature_id):
                    return JsonResponse({
                        'ok': False,
                        'error': 'feature_disabled',
                        'message': '功能「%s」已关闭喵~' % description,
                        'feature_id': feature_id,
                    }, status=403)
                return view_func(request, *args, **kwargs)

            wrapper.feature_id = feature_id
            return wrapper

        return decorator

    @classmethod
    def is_enabled(cls, feature_id):
        """查询功能是否启用：settings 覆盖 > 注册默认值 > 未知功能视为启用。"""
        override = getattr(settings, 'ROUND5_FEATURES', {}) or {}
        if feature_id in override:
            return bool(override[feature_id])
        info = cls._registry.get(feature_id)
        return info['default_enabled'] if info else True

    @classmethod
    def all_features(cls):
        """返回全部已注册功能（按 id 排序的元信息 + 当前启用状态）。"""
        out = []
        for fid, info in sorted(cls._registry.items()):
            item = dict(info)
            item['enabled'] = cls.is_enabled(fid)
            out.append(item)
        return out

    @classmethod
    def stats(cls):
        """按领域统计功能数量与启用数量，供管理页总览。"""
        result = {}
        for domain, domain_name in cls.DOMAINS.items():
            items = [f for f in cls.all_features() if f['domain'] == domain]
            result[domain] = {
                'name': domain_name,
                'total': len(items),
                'enabled': sum(1 for f in items if f['enabled']),
            }
        result['_total'] = len(cls._registry)
        return result

def round5_feature_list(request: HttpRequest) -> JsonResponse:
    """功能开关列表：``GET /api/round5/features/``。

    返回全部已注册功能、领域分组、按领域的启用统计，以及当前生效的覆盖配置。
    只读端点，无需登录（暴露的仅是功能名与开关状态，无敏感信息）。
    """
    features = Round5FeatureRegistry.all_features()
    return JsonResponse({
        'ok': True,
        'total': len(features),
        'domains': Round5FeatureRegistry.DOMAINS,
        'stats': Round5FeatureRegistry.stats(),
        'features': features,
        'overrides': getattr(settings, 'ROUND5_FEATURES', {}) or {},
    })

@require_POST
def round5_feature_toggle(request: HttpRequest, feature_id: str) -> JsonResponse:
    """切换功能开关：``POST /api/round5/features/<feature_id>/toggle/``（仅管理员）。

    请求体可选 ``{"enabled": true/false}``；不传则取反当前值。
    说明：覆盖值写入**进程内 settings**（运行时生效），重启后回到默认值；
    生产环境如需持久化，可改为写入 SiteInfo 或环境变量（README 有说明）。
    """
    if not (request.user.is_authenticated and request.user.is_staff):
        return JsonResponse({'ok': False, 'error': 'permission_denied',
                             'message': msg('err.admin_only')}, status=403)
    if feature_id not in Round5FeatureRegistry._registry:
        return JsonResponse({'ok': False, 'error': 'feature_not_found',
                             'message': msg('err.feature_not_found_short')}, status=404)
    try:
        payload = json.loads(request.body) if request.body else {}
    except (ValueError, TypeError):
        payload = {}
    enabled = payload.get('enabled')
    if enabled is None:
        enabled = not Round5FeatureRegistry.is_enabled(feature_id)
    if not hasattr(settings, 'ROUND5_FEATURES'):
        settings.ROUND5_FEATURES = {}
    settings.ROUND5_FEATURES[feature_id] = bool(enabled)
    return JsonResponse({
        'ok': True,
        'feature_id': feature_id,
        'enabled': bool(enabled),
        'message': '功能「%s」已%s喵~' % (
            Round5FeatureRegistry._registry[feature_id]['description'],
            '开启' if enabled else '关闭'),
    })

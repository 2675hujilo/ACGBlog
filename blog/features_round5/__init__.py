"""
第5轮：10000原子功能核心框架
功能注册、开关控制、模块化管理
"""
from django.conf import settings
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# 全局功能注册表
_FEATURE_REGISTRY = {}

# 功能领域定义
FEATURE_DOMAINS = {
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


def register_feature(domain, name, description='', default_enabled=True):
    """功能注册装饰器：将视图函数注册到功能注册表。"""
    def decorator(view_func):
        feature_id = f"{domain}_{name}"
        _FEATURE_REGISTRY[feature_id] = {
            'id': feature_id,
            'domain': domain,
            'domain_name': FEATURE_DOMAINS.get(domain, domain),
            'name': name,
            'description': description,
            'default_enabled': default_enabled,
            'view': view_func,
        }

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # 检查功能开关
            if not is_feature_enabled(feature_id):
                from django.http import JsonResponse
                return JsonResponse({
                    'ok': False,
                    'error': 'feature_disabled',
                    'message': f'功能「{description}」已关闭喵~',
                    'feature_id': feature_id,
                }, status=403)
            return view_func(request, *args, **kwargs)

        wrapper.feature_id = feature_id
        return wrapper
    return decorator


def is_feature_enabled(feature_id):
    """检查功能是否启用。"""
    # 从settings获取功能配置，默认全部启用
    feature_config = getattr(settings, 'ROUND5_FEATURES', {})
    if feature_id in feature_config:
        return feature_config[feature_id]
    # 默认启用
    feature = _FEATURE_REGISTRY.get(feature_id)
    if feature:
        return feature['default_enabled']
    return True


def get_all_features():
    """获取所有已注册功能。"""
    return _FEATURE_REGISTRY


def get_features_by_domain(domain):
    """按领域获取功能列表。"""
    return {k: v for k, v in _FEATURE_REGISTRY.items() if v['domain'] == domain}


def get_feature_stats():
    """获取功能统计信息。"""
    stats = {}
    for domain in FEATURE_DOMAINS:
        domain_features = get_features_by_domain(domain)
        stats[domain] = {
            'name': FEATURE_DOMAINS[domain],
            'total': len(domain_features),
            'enabled': sum(1 for f in domain_features.values() if is_feature_enabled(f['id'])),
        }
    stats['_total'] = len(_FEATURE_REGISTRY)
    return stats


def feature_list_view(request):
    """功能列表API：返回所有功能及其开关状态。"""
    from django.http import JsonResponse
    features = []
    for fid, finfo in sorted(_FEATURE_REGISTRY.items()):
        features.append({
            'id': fid,
            'domain': finfo['domain'],
            'domain_name': finfo['domain_name'],
            'name': finfo['name'],
            'description': finfo['description'],
            'enabled': is_feature_enabled(fid),
        })
    return JsonResponse({
        'ok': True,
        'total': len(features),
        'domains': FEATURE_DOMAINS,
        'stats': get_feature_stats(),
        'features': features,
    })


def feature_toggle_view(request, feature_id):
    """功能开关切换API（仅管理员）。"""
    from django.http import JsonResponse
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({'ok': False, 'error': 'permission_denied'}, status=403)

    if feature_id not in _FEATURE_REGISTRY:
        return JsonResponse({'ok': False, 'error': 'feature_not_found'}, status=404)

    import json
    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        data = {}

    enabled = data.get('enabled', not is_feature_enabled(feature_id))

    # 保存到settings（运行时）
    if not hasattr(settings, 'ROUND5_FEATURES'):
        settings.ROUND5_FEATURES = {}
    settings.ROUND5_FEATURES[feature_id] = enabled

    return JsonResponse({
        'ok': True,
        'feature_id': feature_id,
        'enabled': enabled,
        'message': f'功能「{_FEATURE_REGISTRY[feature_id]["description"]}」已{"开启" if enabled else "关闭"}喵~',
    })

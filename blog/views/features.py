# -*- coding: utf-8 -*-

"""Round5 功能开关注册表与开关接口。"""

#: 导入模块「json」，供本文件后续使用
import json
#: 导入模块「logging」，供本文件后续使用
import logging
#: 导入模块「os」，供本文件后续使用
import os
#: 导入模块「re」，供本文件后续使用
import re
#: 导入模块「uuid」，供本文件后续使用
import uuid
#: 从模块「django.conf」导入所需对象
from django.conf import settings
#: 从模块「django.http」导入所需对象
from django.http import (
    #: 抛出 404 异常（渲染萌系 404 页）
    FileResponse, Http404, HttpRequest, HttpResponse,
    #: 该行执行对应逻辑（结合上下文理解）
    HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound,
    #: 该行执行对应逻辑（结合上下文理解）
    HttpResponseNotModified, HttpResponsePermanentRedirect,
    #: 构造 HTTP 响应返回给客户端
    HttpResponseRedirect, JsonResponse, StreamingHttpResponse,
#: 该行执行对应逻辑（结合上下文理解）
)
#: 从模块「django.views.decorators.http」导入所需对象
from django.views.decorators.http import require_POST
#: 从模块「..services.site_messages」导入所需对象
from ..services.site_messages import msg


#: 定义变量「logger」，保存对应数据
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
        #: 配置项「content」：字典/模型的该键设置为对应值
        'content': '内容创作生产域',
        #: 配置项「reading」：字典/模型的该键设置为对应值
        'reading': '沉浸式阅读域',
        #: 配置项「comment」：字典/模型的该键设置为对应值
        'comment': '评论社区互动域',
        #: 配置项「user」：字典/模型的该键设置为对应值
        'user': '用户成长与社交域',
        #: 配置项「ui」：字典/模型的该键设置为对应值
        'ui': 'UI装扮个性化域',
        #: 配置项「search」：字典/模型的该键设置为对应值
        'search': '搜索内容推荐域',
        #: 配置项「operation」：字典/模型的该键设置为对应值
        'operation': '站点运营活动域',
        #: 配置项「analytics」：字典/模型的该键设置为对应值
        'analytics': '数据分析监控域',
        #: 配置项「seo」：字典/模型的该键设置为对应值
        'seo': 'SEO与性能扩展域',
        #: 配置项「accessibility」：字典/模型的该键设置为对应值
        'accessibility': '无障碍增强域',
        #: 配置项「api」：字典/模型的该键设置为对应值
        'api': 'API与第三方集成域',
        #: 配置项「easter」：字典/模型的该键设置为对应值
        'easter': '彩蛋趣味工具域',
    #: 该行执行对应逻辑（结合上下文理解）
    }

    #: 进程内注册表：feature_id -> 元信息字典
    _registry = {}

    #: 装饰器：为下一个定义附加「classmethod」行为（权限、缓存、注册信号等）
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
        #: 从模块「functools」导入所需对象
        from functools import wraps

        def decorator(view_func):
            """
            功能：处理「decorator」相关逻辑。

            参数：
              - view_func：传入参数，含义结合函数体与调用处

            返回：对应计算/查询结果。

            注意：保持函数单一职责；修改时确认调用方不受影响。
            """
            #: 定义变量「feature_id」，保存对应数据
            feature_id = '%s_%s' % (domain, name)
            #: 操作「cls」的属性或方法
            cls._registry[feature_id] = {
                #: 配置项「id」：字典/模型的该键设置为对应值
                'id': feature_id,
                #: 配置项「domain」：字典/模型的该键设置为对应值
                'domain': domain,
                #: 配置项「domain_name」：字典/模型的该键设置为对应值
                'domain_name': cls.DOMAINS.get(domain, domain),
                #: 配置项「name」：字典/模型的该键设置为对应值
                'name': name,
                #: 配置项「description」：字典/模型的该键设置为对应值
                'description': description,
                #: 配置项「default_enabled」：字典/模型的该键设置为对应值
                'default_enabled': default_enabled,
            #: 该行执行对应逻辑（结合上下文理解）
            }

            #: 装饰器：为下一个定义附加「wraps(view_func)」行为（权限、缓存、注册信号等）
            @wraps(view_func)
            def wrapper(request, *args, **kwargs):
                # 功能被关闭时返回 403 + 明确文案，而不是静默失败
                """
                功能：处理「wrapper」相关逻辑。

                参数：
                  - request：传入参数，含义结合函数体与调用处

                返回：对应计算/查询结果。

                注意：保持函数单一职责；修改时确认调用方不受影响。
                """
                #: 条件判断：条件成立时执行该分支
                if not cls.is_enabled(feature_id):
                    #: 返回结果并结束当前函数
                    return JsonResponse({
                        #: 配置项「ok」：字典/模型的该键设置为对应值
                        'ok': False,
                        #: 配置项「error」：字典/模型的该键设置为对应值
                        'error': 'feature_disabled',
                        #: 配置项「message」：字典/模型的该键设置为对应值
                        'message': '功能「%s」已关闭喵~' % description,
                        #: 配置项「feature_id」：字典/模型的该键设置为对应值
                        'feature_id': feature_id,
                    #: 该行执行对应逻辑（结合上下文理解）
                    }, status=403)
                #: 返回结果并结束当前函数
                return view_func(request, *args, **kwargs)

            #: 定义实例/类属性「wrapper.feature_id」，保存对应数据
            wrapper.feature_id = feature_id
            #: 返回结果并结束当前函数
            return wrapper

        #: 返回结果并结束当前函数
        return decorator

    #: 装饰器：为下一个定义附加「classmethod」行为（权限、缓存、注册信号等）
    @classmethod
    def is_enabled(cls, feature_id):
        """查询功能是否启用：settings 覆盖 > 注册默认值 > 未知功能视为启用。"""
        #: 定义变量「override」，保存对应数据
        override = settings.ROUND5_FEATURES
        #: 条件判断：条件成立时执行该分支
        if feature_id in override:
            #: 返回结果并结束当前函数
            return bool(override[feature_id])
        #: 定义变量「info」，保存对应数据
        info = cls._registry.get(feature_id)
        #: 返回结果并结束当前函数
        return info['default_enabled'] if info else True

    #: 装饰器：为下一个定义附加「classmethod」行为（权限、缓存、注册信号等）
    @classmethod
    def all_features(cls):
        """返回全部已注册功能（按 id 排序的元信息 + 当前启用状态）。"""
        #: 定义变量「out」，保存对应数据（集合/元组）
        out = []
        #: 循环遍历，逐个处理元素
        for fid, info in sorted(cls._registry.items()):
            #: 定义变量「item」，保存对应数据
            item = dict(info)
            #: 该行执行对应逻辑（结合上下文理解）
            item['enabled'] = cls.is_enabled(fid)
            #: 调用「out.append」执行相应逻辑
            out.append(item)
        #: 返回结果并结束当前函数
        return out

    #: 装饰器：为下一个定义附加「classmethod」行为（权限、缓存、注册信号等）
    @classmethod
    def stats(cls):
        """按领域统计功能数量与启用数量，供管理页总览。"""
        #: 定义变量「result」，保存对应数据
        result = {}
        #: 循环遍历，逐个处理元素
        for domain, domain_name in cls.DOMAINS.items():
            #: 定义变量「items」，保存对应数据（集合/元组）
            items = [f for f in cls.all_features() if f['domain'] == domain]
            #: 该行执行对应逻辑（结合上下文理解）
            result[domain] = {
                #: 配置项「name」：字典/模型的该键设置为对应值
                'name': domain_name,
                #: 配置项「total」：字典/模型的该键设置为对应值
                'total': len(items),
                #: 配置项「enabled」：字典/模型的该键设置为对应值
                'enabled': sum(1 for f in items if f['enabled']),
            #: 该行执行对应逻辑（结合上下文理解）
            }
        #: 该行执行对应逻辑（结合上下文理解）
        result['_total'] = len(cls._registry)
        #: 返回结果并结束当前函数
        return result

def round5_feature_list(request: HttpRequest) -> JsonResponse:
    """功能开关列表：``GET /api/round5/features/``。

    返回全部已注册功能、领域分组、按领域的启用统计，以及当前生效的覆盖配置。
    只读端点，无需登录（暴露的仅是功能名与开关状态，无敏感信息）。
    """
    #: 定义变量「features」，保存对应数据
    features = Round5FeatureRegistry.all_features()
    #: 返回结果并结束当前函数
    return JsonResponse({
        #: 配置项「ok」：字典/模型的该键设置为对应值
        'ok': True,
        #: 配置项「total」：字典/模型的该键设置为对应值
        'total': len(features),
        #: 配置项「domains」：字典/模型的该键设置为对应值
        'domains': Round5FeatureRegistry.DOMAINS,
        #: 配置项「stats」：字典/模型的该键设置为对应值
        'stats': Round5FeatureRegistry.stats(),
        #: 配置项「features」：字典/模型的该键设置为对应值
        'features': features,
        #: 配置项「overrides」：字典/模型的该键设置为对应值
        'overrides': settings.ROUND5_FEATURES,
    #: 该行执行对应逻辑（结合上下文理解）
    })

#: 装饰器：为下一个定义附加「require_POST」行为（权限、缓存、注册信号等）
@require_POST
def round5_feature_toggle(request: HttpRequest, feature_id: str) -> JsonResponse:
    """切换功能开关：``POST /api/round5/features/<feature_id>/toggle/``（仅管理员）。

    请求体可选 ``{"enabled": true/false}``；不传则取反当前值。
    说明：覆盖值写入**进程内 settings**（运行时生效），重启后回到默认值；
    生产环境如需持久化，可改为写入 SiteInfo 或环境变量（README 有说明）。
    """
    #: 条件判断：条件成立时执行该分支
    if not (request.user.is_authenticated and request.user.is_staff):
        #: 返回结果并结束当前函数
        return JsonResponse({'ok': False, 'error': 'permission_denied',
                             #: 配置项「message」：字典/模型的该键设置为对应值
                             'message': msg('err.admin_only')}, status=403)
    #: 条件判断：条件成立时执行该分支
    if feature_id not in Round5FeatureRegistry._registry:
        #: 返回结果并结束当前函数
        return JsonResponse({'ok': False, 'error': 'feature_not_found',
                             #: 配置项「message」：字典/模型的该键设置为对应值
                             'message': msg('err.feature_not_found_short')}, status=404)
    #: 尝试执行可能出错的代码
    try:
        #: 读取本次请求的 body 数据
        payload = json.loads(request.body) if request.body else {}
    #: 捕获并处理异常，避免程序中断
    except (ValueError, TypeError):
        #: 定义变量「payload」，保存对应数据
        payload = {}
    #: 定义变量「enabled」，保存对应数据
    enabled = payload.get('enabled')
    #: 条件判断：条件成立时执行该分支
    if enabled is None:
        #: 定义变量「enabled」，保存对应数据
        enabled = not Round5FeatureRegistry.is_enabled(feature_id)
    # ROUND5_FEATURES 已在 settings 集中定义；直接改其内容即运行时生效（重启还原）。
    #: 操作「settings」的属性或方法
    settings.ROUND5_FEATURES[feature_id] = bool(enabled)
    #: 返回结果并结束当前函数
    return JsonResponse({
        #: 配置项「ok」：字典/模型的该键设置为对应值
        'ok': True,
        #: 配置项「feature_id」：字典/模型的该键设置为对应值
        'feature_id': feature_id,
        #: 配置项「enabled」：字典/模型的该键设置为对应值
        'enabled': bool(enabled),
        #: 配置项「message」：字典/模型的该键设置为对应值
        'message': '功能「%s」已%s喵~' % (
            #: 操作「Round5FeatureRegistry」的属性或方法
            Round5FeatureRegistry._registry[feature_id]['description'],
            #: 该行执行对应逻辑（结合上下文理解）
            '开启' if enabled else '关闭'),
    #: 该行执行对应逻辑（结合上下文理解）
    })

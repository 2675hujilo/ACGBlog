# -*- coding: utf-8 -*-

"""自定义错误页：404 / 500 / 403。"""

#: 导入模块「logging」，供本文件后续使用
import logging
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
#: 从模块「django.shortcuts」导入所需对象
from django.shortcuts import get_object_or_404, redirect, render
#: 从模块「..models」导入所需对象
from ..models import (
    #: 该行执行对应逻辑（结合上下文理解）
    AccessLog, Article, Badge, Category, Comment, CommentReport,
    #: 该行执行对应逻辑（结合上下文理解）
    EditLog, Favorite, FavoriteFolder, ModerationLog, Notification,
    #: 该行执行对应逻辑（结合上下文理解）
    PromotionRequest, ModerationSettings, Rating, Series, ShortLink,
    #: 该行执行对应逻辑（结合上下文理解）
    SiteNotice, Tag, User, UserBadge,
#: 该行执行对应逻辑（结合上下文理解）
)

#: 从模块「.common」导入所需对象
from .common import logger


#: 定义变量「logger」，保存对应数据
logger = logging.getLogger('blog.views')

# 迭代#234: custom_404视图docstring
# 迭代#235: custom_404(request, exception) -> HttpResponse 类型提示
def custom_404(request: HttpRequest, exception: Exception) -> HttpResponse:
    """404 页面：这个页面被喵喵吃掉了~（附带搜索框与热门文章快捷链接）"""
    # 迭代#236: 404错误日志
    #: 记录日志，便于排查（勿记录密码等敏感信息）
    logger.warning('404 Not Found: path=%s', request.path)
    # 6. 传入阅读量最高的 5 篇已发布文章，供 404 页"热门文章"区直接跳转
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    hot = list(Article.objects.filter(status=Article.Status.PUBLISHED)
               #: 对查询结果按字段排序
               .order_by('-views')[:5])
    #: 返回结果并结束当前函数
    return render(request, '404.html', {'hot_articles': hot}, status=404)

def custom_500(request: HttpRequest) -> HttpResponse:
    """500 页面：服务器酱正在罢工中…（注意：500 handler 不需要 exception 参数）"""
    # 迭代#239: 500错误日志
    #: 记录日志，便于排查（勿记录密码等敏感信息）
    logger.error('500 Internal Server Error: path=%s', request.path)
    #: 返回结果并结束当前函数
    return render(request, '500.html', status=500)

# 迭代#240: custom_403视图docstring
# 迭代#241: custom_403(request, exception) -> HttpResponse 类型提示
def custom_403(request: HttpRequest, exception: Exception) -> HttpResponse:
    """403 页面：喵？你没有权限看这个呢~"""
    # 迭代#242: 403错误日志
    #: 记录日志，便于排查（勿记录密码等敏感信息）
    logger.warning('403 Forbidden: path=%s user=%s', request.path,
                   #: 读取本次请求的 user 数据
                   request.user.username if request.user.is_authenticated else 'anonymous')
    #: 返回结果并结束当前函数
    return render(request, '403.html', status=403)

# -*- coding: utf-8 -*-

"""自定义错误页：404 / 500 / 403。"""

import logging
from django.http import (
    FileResponse, Http404, HttpRequest, HttpResponse,
    HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound,
    HttpResponseNotModified, HttpResponsePermanentRedirect,
    HttpResponseRedirect, JsonResponse, StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from ..models import (
    AccessLog, Article, Badge, Category, Comment, CommentReport,
    EditLog, Favorite, FavoriteFolder, ModerationLog, Notification,
    PromotionRequest, ModerationSettings, Rating, Series, ShortLink,
    SiteNotice, Tag, User, UserBadge,
)

from .common import logger


logger = logging.getLogger('blog.views')

# 迭代#234: custom_404视图docstring
# 迭代#235: custom_404(request, exception) -> HttpResponse 类型提示
def custom_404(request: HttpRequest, exception: Exception) -> HttpResponse:
    """404 页面：这个页面被喵喵吃掉了~（附带搜索框与热门文章快捷链接）"""
    # 迭代#236: 404错误日志
    logger.warning('404 Not Found: path=%s', request.path)
    # 6. 传入阅读量最高的 5 篇已发布文章，供 404 页"热门文章"区直接跳转
    hot = list(Article.objects.filter(status=Article.Status.PUBLISHED)
               .order_by('-views')[:5])
    return render(request, '404.html', {'hot_articles': hot}, status=404)

def custom_500(request: HttpRequest) -> HttpResponse:
    """500 页面：服务器酱正在罢工中…（注意：500 handler 不需要 exception 参数）"""
    # 迭代#239: 500错误日志
    logger.error('500 Internal Server Error: path=%s', request.path)
    return render(request, '500.html', status=500)

# 迭代#240: custom_403视图docstring
# 迭代#241: custom_403(request, exception) -> HttpResponse 类型提示
def custom_403(request: HttpRequest, exception: Exception) -> HttpResponse:
    """403 页面：喵？你没有权限看这个呢~"""
    # 迭代#242: 403错误日志
    logger.warning('403 Forbidden: path=%s user=%s', request.path,
                   request.user.username if request.user.is_authenticated else 'anonymous')
    return render(request, '403.html', status=403)

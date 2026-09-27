# -*- coding: utf-8 -*-

"""文章系列：列表、详情与创建。"""

import logging
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, F, Min, Q, Sum
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
from ..site_messages import msg

from .catalog import _sidebar


logger = logging.getLogger('blog.views')

# 迭代#197: series_list视图docstring完善
def series_list(request):
    """67. 系列列表页：展示所有文章系列（封面 + 标题 + 文章数）。"""
    series_qs = Series.objects.annotate(
        n=Count('articles')).order_by('-created_at')
    ctx = {
        'series_list': series_qs,
        'active_nav': 'series',
        'meta_title': f'文章系列 - {settings.SITE_NAME}',
        'meta_description': f'{settings.SITE_NAME} 文章系列合集。',
    }
    ctx.update(_sidebar())
    return render(request, 'blog/series_list.html', ctx)

# 迭代#198: series_detail视图docstring完善
def series_detail(request, pk):
    """67. 系列详情页：展示系列介绍 + 该系列全部文章（按 series_order 排序）。"""
    series = get_object_or_404(Series, pk=pk)
    # 系列下已发布文章，按系列序号升序
    articles = series.articles.filter(
        status=Article.Status.PUBLISHED).order_by('series_order', 'id')
    ctx = {
        'series': series,
        'series_articles': articles,
        'active_nav': 'series',
        'meta_title': f'{series.title} - 文章系列',
        'meta_description': (series.description or series.title)[:150],
    }
    ctx.update(_sidebar())
    return render(request, 'blog/series_detail.html', ctx)

@login_required
def series_create(request: HttpRequest) -> HttpResponse:
    """67扩展：创建文章系列。

    登录用户可创建系列，把同主题文章组织到一起按顺序阅读。
    - GET：渲染萌系创建表单；
    - POST：校验名称后创建系列，可选简介与封面，成功后跳转系列详情页。
    """
    if request.method == 'POST':
        title = (request.POST.get('title') or '').strip()
        description = (request.POST.get('description') or '').strip()[:500]
        if not title:
            ctx = {
                'error': msg('misc.series_name_required'),
                'form_title': title, 'form_desc': description,
                'active_nav': 'series', 'meta_title': '创建系列',
            }
            ctx.update(_sidebar())
            return render(request, 'blog/series_form.html', ctx)
        series = Series(title=title[:80], description=description,
                        author=request.user)
        cover = request.FILES.get('cover_image')
        if cover:
            series.cover_image = cover
        series.save()
        messages.success(request, msg('misc.series_created'))
        return redirect('series_detail', pk=series.pk)
    ctx = {'active_nav': 'series',
           'meta_title': f'创建系列 - {settings.SITE_NAME}'}
    ctx.update(_sidebar())
    return render(request, 'blog/series_form.html', ctx)

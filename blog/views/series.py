# -*- coding: utf-8 -*-

"""文章系列：列表、详情与创建。"""

#: 导入模块「logging」，供本文件后续使用
import logging
#: 从模块「django.conf」导入所需对象
from django.conf import settings
#: 从模块「django.contrib」导入所需对象
from django.contrib import messages
#: 从模块「django.contrib.auth.decorators」导入所需对象
from django.contrib.auth.decorators import login_required
#: 从模块「django.db.models」导入所需对象
from django.db.models import Avg, Count, F, Min, Q, Sum
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
#: 从模块「..services.site_messages」导入所需对象
from ..services.site_messages import msg

#: 从模块「.catalog」导入所需对象
from .catalog import _sidebar


#: 定义变量「logger」，保存对应数据
logger = logging.getLogger('blog.views')

# 迭代#197: series_list视图docstring完善
def series_list(request):
    """67. 系列列表页：展示所有文章系列（封面 + 标题 + 文章数）。"""
    #: 定义变量「series_qs」，保存对应数据
    series_qs = Series.objects.annotate(
        #: 对查询结果按字段排序
        n=Count('articles')).order_by('-created_at')
    #: 定义变量「ctx」，保存对应数据
    ctx = {
        #: 配置项「series_list」：字典/模型的该键设置为对应值
        'series_list': series_qs,
        #: 配置项「active_nav」：字典/模型的该键设置为对应值
        'active_nav': 'series',
        #: 配置项「meta_title」：字典/模型的该键设置为对应值
        'meta_title': f'文章系列 - {settings.SITE_NAME}',
        #: 配置项「meta_description」：字典/模型的该键设置为对应值
        'meta_description': f'{settings.SITE_NAME} 文章系列合集。',
    #: 该行执行对应逻辑（结合上下文理解）
    }
    #: 调用「ctx.update」执行相应逻辑
    ctx.update(_sidebar())
    #: 返回结果并结束当前函数
    return render(request, 'blog/series_list.html', ctx)

# 迭代#198: series_detail视图docstring完善
def series_detail(request, pk):
    """67. 系列详情页：展示系列介绍 + 该系列全部文章（按 series_order 排序）。"""
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    series = get_object_or_404(Series, pk=pk)
    # 系列下已发布文章，按系列序号升序
    #: 定义变量「articles」，保存对应数据
    articles = series.articles.filter(
        #: 对查询结果按字段排序
        status=Article.Status.PUBLISHED).order_by('series_order', 'id')
    #: 定义变量「ctx」，保存对应数据
    ctx = {
        #: 配置项「series」：字典/模型的该键设置为对应值
        'series': series,
        #: 配置项「series_articles」：字典/模型的该键设置为对应值
        'series_articles': articles,
        #: 配置项「active_nav」：字典/模型的该键设置为对应值
        'active_nav': 'series',
        #: 配置项「meta_title」：字典/模型的该键设置为对应值
        'meta_title': f'{series.title} - 文章系列',
        #: 配置项「meta_description」：字典/模型的该键设置为对应值
        'meta_description': (series.description or series.title)[:150],
    #: 该行执行对应逻辑（结合上下文理解）
    }
    #: 调用「ctx.update」执行相应逻辑
    ctx.update(_sidebar())
    #: 返回结果并结束当前函数
    return render(request, 'blog/series_detail.html', ctx)

#: 装饰器：为下一个定义附加「login_required」行为（权限、缓存、注册信号等）
@login_required
def series_create(request: HttpRequest) -> HttpResponse:
    """67扩展：创建文章系列。

    登录用户可创建系列，把同主题文章组织到一起按顺序阅读。
    - GET：渲染萌系创建表单；
    - POST：校验名称后创建系列，可选简介与封面，成功后跳转系列详情页。
    """
    #: 条件判断：条件成立时执行该分支
    if request.method == 'POST':
        #: 读取本次请求的 POST 数据
        title = (request.POST.get('title') or '').strip()
        #: 读取本次请求的 POST 数据
        description = (request.POST.get('description') or '').strip()[:500]
        #: 条件判断：条件成立时执行该分支
        if not title:
            #: 定义变量「ctx」，保存对应数据
            ctx = {
                #: 配置项「error」：字典/模型的该键设置为对应值
                'error': msg('misc.series_name_required'),
                #: 配置项「form_title」：字典/模型的该键设置为对应值
                'form_title': title, 'form_desc': description,
                #: 配置项「active_nav」：字典/模型的该键设置为对应值
                'active_nav': 'series', 'meta_title': '创建系列',
            #: 该行执行对应逻辑（结合上下文理解）
            }
            #: 调用「ctx.update」执行相应逻辑
            ctx.update(_sidebar())
            #: 返回结果并结束当前函数
            return render(request, 'blog/series_form.html', ctx)
        #: 定义变量「series」，保存对应数据
        series = Series(title=title[:80], description=description,
                        #: 读取本次请求的 user 数据
                        author=request.user)
        #: 读取本次请求的 FILES 数据
        cover = request.FILES.get('cover_image')
        #: 条件判断：条件成立时执行该分支
        if cover:
            #: 定义实例/类属性「series.cover_image」，保存对应数据
            series.cover_image = cover
        #: 保存对象（INSERT/UPDATE），可能触发模型信号
        series.save()
        #: 向用户闪现一条提示消息（下次请求展示）
        messages.success(request, msg('misc.series_created'))
        #: 返回结果并结束当前函数
        return redirect('series_detail', pk=series.pk)
    #: 定义变量「ctx」，保存对应数据
    ctx = {'active_nav': 'series',
           #: 配置项「meta_title」：字典/模型的该键设置为对应值
           'meta_title': f'创建系列 - {settings.SITE_NAME}'}
    #: 调用「ctx.update」执行相应逻辑
    ctx.update(_sidebar())
    #: 返回结果并结束当前函数
    return render(request, 'blog/series_form.html', ctx)

# -*- coding: utf-8 -*-

"""文章核心：首页列表、详情、发布、编辑、删除与随机文章。"""

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
#: 从模块「datetime」导入所需对象
from datetime import datetime, timedelta
#: 从模块「typing」导入所需对象
from typing import Any, Optional, Tuple
#: 从模块「django.conf」导入所需对象
from django.conf import settings
#: 从模块「django.contrib」导入所需对象
from django.contrib import messages
#: 从模块「django.contrib.auth.decorators」导入所需对象
from django.contrib.auth.decorators import login_required
#: 从模块「django.contrib.auth.hashers」导入所需对象
from django.contrib.auth.hashers import check_password, make_password
#: 从模块「django.core.cache」导入所需对象
from django.core.cache import cache
#: 从模块「..utils.cache_keys」导入所需对象
from ..utils.cache_keys import (
    #: 该行执行对应逻辑（结合上下文理解）
    DETAIL_TTL, MISSING_TTL, cache_get, cache_get_or_set,
    #: 该行执行对应逻辑（结合上下文理解）
    cache_set, detail_keys, invalidate_article,
#: 该行执行对应逻辑（结合上下文理解）
)
#: 从模块「django.core.paginator」导入所需对象
from django.core.paginator import Paginator
#: 从模块「django.db.models」导入所需对象
from django.db.models import Avg, Count, F, Min, Q, Sum
#: 从模块「django.db」导入所需对象
from django.db import DatabaseError, IntegrityError, OperationalError
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
#: 从模块「django.utils」导入所需对象
from django.utils import timezone
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

#: 从模块「.comments」导入所需对象
from .comments import _build_comment_tree

#: 从模块「.common」导入所需对象
from .common import FOOTER_STATS_KEY, HOT_ARTICLES_KEY, SIDEBAR_CACHE_KEY, SIDEBAR_CACHE_TIMEOUT, TAG_CLOUD_KEY, _base_qs, _filter_articles, _safe_jsonld, logger, sanitize_html

#: 从模块「.interactions」导入所需对象
from .interactions import _hot_articles_for_range

#: 从模块「.moderation」导入所需对象
from .moderation import _promo_block_state

#: 从模块「.seo」导入所需对象
from .seo import _build_website_jsonld


#: 定义变量「logger」，保存对应数据
logger = logging.getLogger('blog.views')

def warm_public_cache():
    """启动预热：预加载侧边栏 / 热门文章 / 标签云 / 页脚统计到缓存。

    在 apps.py 的 ready() 中调用。数据库尚未就绪（如 makemigrations 时）
    会抛异常，整体 try/except 兜底，绝不阻断应用启动。
    """
    #: 尝试执行可能出错的代码
    try:
        #: 调用「_sidebar」执行相应逻辑
        _sidebar()
        #: 读写缓存，减轻数据库压力，注意键与过期时间
        cache.get_or_set(HOT_ARTICLES_KEY, lambda: list(
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            Article.objects.filter(status=Article.Status.PUBLISHED)
            #: 对查询结果按字段排序
            .order_by('-views')[:10]), SIDEBAR_CACHE_TIMEOUT)
        #: 读写缓存，减轻数据库压力，注意键与过期时间
        cache.get_or_set(TAG_CLOUD_KEY, lambda: list(
            #: 使用 Q/F 表达式构造复杂查询或引用字段值
            Tag.objects.annotate(n=Count('articles', filter=Q(
                #: 定义变量「articles__status」，保存对应数据
                articles__status='published', articles__is_deleted=False)))
            #: 对查询结果按字段排序
            .filter(n__gt=0).order_by('-n')[:30]), 600)
        #: 读写缓存，减轻数据库压力，注意键与过期时间
        cache.get_or_set(FOOTER_STATS_KEY, lambda: {
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'article_count': Article.objects.filter(
                #: 定义变量「status」，保存对应数据
                status=Article.Status.PUBLISHED).count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'views_total': Article.objects.filter(
                #: 使用聚合函数做统计查询
                status=Article.Status.PUBLISHED).aggregate(v=Sum('views'))['v'] or 0,
        #: 该行执行对应逻辑（结合上下文理解）
        }, 3600)
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.info('公共缓存预热完成')
    #: 捕获并处理异常，避免程序中断
    except Exception as exc:  # noqa: BLE001 启动期数据库未就绪属正常
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.debug('公共缓存预热跳过（数据库未就绪?）: %s', exc)

# 迭代#122: _get_related_articles函数docstring
# 迭代#123: _get_related_articles(article, request, limit) -> list 类型提示
# 迭代#124: _get_related_articles加权算法注释
def _get_related_articles(article: Article, request: HttpRequest, limit: int = 8) -> list:
    """根据"同分类 + 同标签加权"算法推荐相关文章。

    评分规则：
    - 与当前文章属于同一分类：基础分 +2；
    - 每共享一个标签：再 +1 分；
    - 按总分降序排序，取前 ``limit`` 篇，排除文章自身与不可见的草稿。

    Args:
        article: 当前 Article 对象。
        request: 当前 HttpRequest 对象（用于权限过滤）。
        limit: 最多返回几篇，默认 8。

    Returns:
        list[Article]: 按相关度降序排列的文章列表（可能为空列表）。
    """
    # 仅在权限过滤后的可见文章集合内查找，排除自己
    #: 定义变量「qs」，保存对应数据
    qs = _base_qs(request).exclude(pk=article.pk)
    # 收集当前文章的标签 id，用于加权打分
    #: 定义变量「my_tag_ids」，保存对应数据
    my_tag_ids = list(article.tags.values_list('id', flat=True))
    # 取出候选文章及其标签，在 Python 侧打分（候选数量通常不大，避免复杂 JOIN）
    #: ORM 预加载关联，减少 N+1 查询提升性能
    candidates = list(qs.prefetch_related('tags'))
    #: 定义变量「scored」，保存对应数据（集合/元组）
    scored = []
    #: 循环遍历，逐个处理元素
    for other in candidates:
        #: 定义变量「score」，保存对应数据
        score = 0
        # 同分类加 2 分（需两边分类都存在且相同）
        #: 条件判断：条件成立时执行该分支
        if article.category_id and other.category_id == article.category_id:
            #: 该行执行对应逻辑（结合上下文理解）
            score += 2
        # 每共享一个标签加 1 分
        #: 定义变量「other_tag_ids」，保存对应数据
        other_tag_ids = {t.id for t in other.tags.all()}
        #: 该行执行对应逻辑（结合上下文理解）
        score += len(set(my_tag_ids) & other_tag_ids)
        #: 条件判断：条件成立时执行该分支
        if score > 0:
            #: 调用「scored.append」执行相应逻辑
            scored.append((score, other))
    # 按分数降序，分数相同按发布时间倒序兜底，取前 limit 篇
    #: 调用「scored.sort」执行相应逻辑
    scored.sort(key=lambda x: (-x[0], -x[1].created_at.timestamp()))
    #: 返回结果并结束当前函数
    return [a for _, a in scored[:limit]]

# 迭代#126: index视图docstring
# 迭代#127: index(request) -> HttpResponse 类型提示
def index(request: HttpRequest) -> HttpResponse:
    """首页视图：渲染文章 / 笔记 / 独立页面的统一列表，支持筛选与分页。

    调用 ``_base_qs`` 做权限过滤，再经 ``_filter_articles`` 应用查询条件，
    最后用 Django 内置 ``Paginator`` 分页，模板复用 ``blog/index.html``。

    Args:
        request: 当前 HttpRequest 对象。

    Returns:
        HttpResponse: 渲染后的首页 HTML（含文章列表、分页器、侧边栏数据）。
    """
    # 先权限过滤，再叠加筛选 / 排序
    #: 该行执行对应逻辑（结合上下文理解）
    qs, sort, q = _filter_articles(request, _base_qs(request))
    # 每页条数由 settings.PAGE_SIZE 控制（默认 10）
    #: 定义变量「paginator」，保存对应数据
    paginator = Paginator(qs, settings.PAGE_SIZE)
    # get_page 会自动处理非法页码（如 page=abc 回到第 1 页），比 page() 更宽容
    # 迭代#128: 分页参数验证
    #: 读取本次请求的 GET 数据
    page_obj = paginator.get_page(request.GET.get('page'))
    # ---- SEO meta：首页默认站点信息；带搜索关键词时标题变为"搜索:关键词" ----
    #: 条件判断：条件成立时执行该分支
    if q:
        #: 定义变量「seo_title」，保存对应数据
        seo_title = f'搜索:{q}'
        #: 定义变量「seo_description」，保存对应数据
        seo_description = f'在{settings.SITE_NAME}搜索"{q}"的结果。'
    #: 以上条件均不成立时的兜底分支
    else:
        #: 定义变量「seo_title」，保存对应数据
        seo_title = f'{settings.SITE_NAME} - 首页'
        #: 定义变量「seo_description」，保存对应数据
        seo_description = settings.SITE_DESCRIPTION
    #: 定义变量「ctx」，保存对应数据
    ctx = {
        #: 配置项「page_obj」：字典/模型的该键设置为对应值
        'page_obj': page_obj,
        # page_range 是可迭代对象，模板中 for 循环生成页码按钮时需转 list
        #: 配置项「page_range」：字典/模型的该键设置为对应值
        'page_range': list(paginator.page_range),
        #: 配置项「sort」：字典/模型的该键设置为对应值
        'sort': sort,
        #: 配置项「q」：字典/模型的该键设置为对应值
        'q': q,
        # 以下 active_* 用于模板中高亮当前选中的筛选条件
        #: 读取本次请求的 GET 数据
        'active_kind': request.GET.get('kind', ''),
        #: 读取本次请求的 GET 数据
        'active_category': request.GET.get('category', ''),
        #: 读取本次请求的 GET 数据
        'active_tag': request.GET.get('tag', ''),
        #: 配置项「active_nav」：字典/模型的该键设置为对应值
        'active_nav': 'home',   # 顶栏高亮"首页"
        # ---- SEO / Open Graph ----
        #: 配置项「meta_title」：字典/模型的该键设置为对应值
        'meta_title': seo_title,
        #: 配置项「meta_description」：字典/模型的该键设置为对应值
        'meta_description': seo_description,
        #: 配置项「meta_keywords」：字典/模型的该键设置为对应值
        'meta_keywords': settings.SITE_KEYWORDS,
        #: 配置项「og_type」：字典/模型的该键设置为对应值
        'og_type': 'website',
        #: 配置项「og_url」：字典/模型的该键设置为对应值
        'og_url': request.build_absolute_uri('/'),
    #: 该行执行对应逻辑（结合上下文理解）
    }
    # 首页（非搜索 / 非筛选）输出 Website + SearchAction 结构化数据，
    # 让搜索引擎支持站内搜索框富摘要；筛选 / 搜索页不输出，避免重复。
    #: 条件判断：条件成立时执行该分支
    if not q:
        #: 该行执行对应逻辑（结合上下文理解）
        ctx['site_jsonld'] = _build_website_jsonld(request)
    # 合并侧边栏统计 / 热门 / 标签云 / 分类导航
    # 工单6-5：右栏热门榜默认渲染「本周」，周/月/总切换走片段接口
    #: 该行执行对应逻辑（结合上下文理解）
    ctx['hot_week_items'] = _hot_articles_for_range('week')
    #: 调用「ctx.update」执行相应逻辑
    ctx.update(_sidebar())
    #: 返回结果并结束当前函数
    return render(request, 'blog/index.html', ctx)

# 迭代#129: article_detail视图docstring
# 迭代#130: article_detail(request, pk) -> HttpResponse 类型提示
# 迭代#131: article_detail阅读量自增注释
# 迭代#132: article_detail上一篇/下一篇查询注释
def article_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """文章详情页：展示单篇文章正文、阅读量自增、相关文章与修改记录。

    流程：
    1. 按主键取出文章（受 ``_base_qs`` 权限约束，无权访问的草稿会 404）；
    2. 用 ``F('views') + 1`` 原子自增阅读量，避免并发竞态；
    3. 判断当前用户是否有编辑权限（作者本人或管理员）；
    4. 查询最近 10 条修改日志与同分类下的相关文章；
    5. 合并侧边栏数据后渲染模板。

    Args:
        request: 当前 HttpRequest 对象。
        pk: 文章主键（URL 中捕获的整数）。

    Returns:
        HttpResponse: 渲染后的详情页 HTML。
    """
    # 缓存穿透防护：命中"不存在墓碑"直接 404，避免恶意 id 打穿数据库
    #: 定义变量「keys」，保存对应数据
    keys = detail_keys(pk)
    #: 条件判断：条件成立时执行该分支
    if cache_get(keys['missing']) is not None:
        #: 主动抛出异常交由上层处理
        raise Http404(msg('err.not_found_short'))
    # 文章内容（不含评论/登录态）走缓存；仅"已发布 + 未软删除 + 无访问密码"的
    # 文章跨用户缓存——草稿 / 待审核 / 软删除 / 密码文按用户实时判定，不入缓存
    #: 定义变量「article」，保存对应数据
    article = cache_get(keys['article'])
    #: 定义变量「article_hit」，保存对应数据
    article_hit = article is not None
    #: 条件判断：条件成立时执行该分支
    if article is None:
        #: 尝试执行可能出错的代码
        try:
            #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
            article = get_object_or_404(
                #: ORM 预加载关联，减少 N+1 查询提升性能
                _base_qs(request, own_drafts=True).select_related('author', 'category').prefetch_related('tags'),
                #: 定义变量「pk」，保存对应数据
                pk=pk)
        #: 捕获并处理异常，避免程序中断
        except Http404:
            # 空结果墓碑短 TTL，防止恶意探测穿透到 DB
            #: 调用「cache_set」执行相应逻辑
            cache_set(keys['missing'], 1, MISSING_TTL)
            #: 主动抛出异常交由上层处理
            raise
        # 只缓存"所有用户可见且一致"的文章（含软删除防护，避免回收站预览泄缓存）
        #: 条件判断：条件成立时执行该分支
        if (article.status == Article.Status.PUBLISHED
                #: 该行执行对应逻辑（结合上下文理解）
                and not article.is_deleted and not article.is_protected):
            #: 调用「cache_set」执行相应逻辑
            cache_set(keys['article'], article, DETAIL_TTL)

    # ---- 58. 文章密码保护门：文章设置了密码且本次会话未授权，则要求输入密码 ----
    # 作者本人或管理员不受密码限制（可直接预览编辑）
    #: 读取本次请求的 user 数据
    is_owner = request.user.is_authenticated and (
        #: 读取本次请求的 user 数据
        request.user == article.author or request.user.is_staff)
    #: 条件判断：条件成立时执行该分支
    if article.is_protected and not is_owner:
        #: 定义变量「authorized」，保存对应数据
        authorized = request.session.get('authorized_articles', [])
        #: 条件判断：条件成立时执行该分支
        if pk not in authorized:
            #: 条件判断：条件成立时执行该分支
            if request.method == 'POST':
                # 密码校验：用 Django check_password 比对哈希
                #: 读取本次请求的 POST 数据
                entered = request.POST.get('article_password', '')
                #: 条件判断：条件成立时执行该分支
                if entered and check_password(entered, article.password):
                    #: 调用「authorized.append」执行相应逻辑
                    authorized.append(pk)
                    #: 操作「request」的属性或方法
                    request.session['authorized_articles'] = authorized
                    #: 定义实例/类属性「request.session.modified」，保存对应数据
                    request.session.modified = True
                    # 校验通过后继续正常渲染文章
                #: 以上条件均不成立时的兜底分支
                else:
                    #: 向用户闪现一条提示消息（下次请求展示）
                    messages.error(request, msg('auth.login_failed'))
                    #: 返回结果并结束当前函数
                    return render(request, 'blog/password_gate.html',
                                  #: 该行执行对应逻辑（结合上下文理解）
                                  {'article': article, 'active_nav': 'home'})
            #: 以上条件均不成立时的兜底分支
            else:
                # GET 直接访问密码文章：显示密码输入页（不增加阅读量）
                #: 返回结果并结束当前函数
                return render(request, 'blog/password_gate.html',
                              #: 该行执行对应逻辑（结合上下文理解）
                              {'article': article, 'active_nav': 'home'})

    # F() 表达式在数据库层自增，不读入 Python 再写回，避免并发覆盖丢失计数
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    Article.objects.filter(pk=pk).update(views=F('views') + 1)
    # 自增后从数据库刷新 views 字段，确保模板拿到最新值
    #: 调用「article.refresh_from_db」执行相应逻辑
    article.refresh_from_db(fields=['views'])
    # 编辑权限：必须已登录，且是文章作者本人，或是管理员
    #: 读取本次请求的 user 数据
    can_edit = request.user.is_authenticated and (
        #: 读取本次请求的 user 数据
        request.user == article.author or request.user.is_staff)
    # QA 辅助（仅 DEBUG 生效）：?as_author=1 时即使当前是管理员，也按「普通作者」
    # 视角渲染详情页操作区，便于对作者申请按钮做浏览器视觉验收。
    # 生产环境（DEBUG=False）该参数完全无效，不影响任何真实权限判定。
    #: 读取本次请求的 GET 数据
    qa_as_author = bool(settings.DEBUG and request.GET.get('as_author') == '1' and can_edit)
    # ------------------------------------------------------------------
    # Bug9-1 / Bug9-2：定时投稿预览提示
    # ------------------------------------------------------------------
    # 作者本人或管理员打开「定时未发布 / 待审核」的文章时，页面顶部给出明确状态条，
    # 说明当前状态、预约时间、剩余时间与到点后的去向，避免"以为已发布"的误解。
    #: 定义变量「scheduled_notice」，保存对应数据
    scheduled_notice = None
    #: 条件判断：条件成立时执行该分支
    if can_edit and article.published_at:
        #: 获取当前时间（时区感知），统一时间口径
        now_ts = timezone.now()
        #: 条件判断：条件成立时执行该分支
        if article.published_at > now_ts and article.status in (
                #: 操作「Article.Status」的属性或方法
                Article.Status.DRAFT, Article.Status.PENDING):
            # 未到点：展示倒计时式的「定时投稿」提示
            #: 定义变量「scheduled_notice」，保存对应数据
            scheduled_notice = {
                #: 配置项「kind」：字典/模型的该键设置为对应值
                'kind': 'scheduled',
                #: 配置项「status」：字典/模型的该键设置为对应值
                'status': article.get_status_display(),
                #: 配置项「at」：字典/模型的该键设置为对应值
                'at': article.published_at,
                #: 配置项「left」：字典/模型的该键设置为对应值
                'left': article.published_at - now_ts,
            #: 该行执行对应逻辑（结合上下文理解）
            }
        #: 否则若该条件成立则进入此分支
        elif article.status == Article.Status.DRAFT and article.published_at <= now_ts:
            # 已到点但仍是草稿：兜底扫描器会在 30 秒内流转，这里给出解释避免困惑
            #: 定义变量「scheduled_notice」，保存对应数据
            scheduled_notice = {
                #: 配置项「kind」：字典/模型的该键设置为对应值
                'kind': 'due',
                #: 配置项「status」：字典/模型的该键设置为对应值
                'status': article.get_status_display(),
                #: 配置项「at」：字典/模型的该键设置为对应值
                'at': article.published_at,
                #: 配置项「left」：字典/模型的该键设置为对应值
                'left': None,
            #: 该行执行对应逻辑（结合上下文理解）
            }
    # ---- 点赞状态：从 session 读取该会话已点赞的文章 id 集合 ----
    # session 中以 'liked_article_ids' 列表存储，判断当前文章是否已赞过
    #: 定义变量「liked_ids」，保存对应数据
    liked_ids = request.session.get('liked_article_ids', [])
    #: 定义变量「already_liked」，保存对应数据
    already_liked = pk in liked_ids
    # ---- 踩状态：从 session 读取该会话已踩的文章 id 集合（D2修复） ----
    #: 定义变量「disliked_ids」，保存对应数据
    disliked_ids = request.session.get('disliked_article_ids', [])
    #: 定义变量「already_disliked」，保存对应数据
    already_disliked = pk in disliked_ids
    # ---- 收藏状态：查询当前登录用户是否已收藏本文 ----
    # 未登录用户 always 未收藏；已登录用户查 Favorite 表是否存在对应记录
    #: 定义变量「is_favorited」，保存对应数据
    is_favorited = False
    #: 条件判断：条件成立时执行该分支
    if request.user.is_authenticated:
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        is_favorited = Favorite.objects.filter(user=request.user, article=article).exists()
    # ---- 上一篇 / 下一篇：共享数据（仅已发布未删除文章），按文章缓存 ----
    # 新文章发布 / 删除会使全站 prev/next 变化：信号 purge_prevnext() 整体清空，
    # 或以 TTL 300s 兜底
    def _build_prev_next():
        """
        功能：构建「prev next」。

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 定义变量「prev_article」，保存对应数据
        prev_article = _base_qs(request).filter(
            #: 使用 Q/F 表达式构造复杂查询或引用字段值
            Q(created_at__lt=article.created_at) |
            #: 使用 Q/F 表达式构造复杂查询或引用字段值
            Q(created_at=article.created_at, id__lt=article.id)
        #: 对查询结果按字段排序
        ).order_by('-created_at', '-id').first()
        #: 定义变量「next_article」，保存对应数据
        next_article = _base_qs(request).filter(
            #: 使用 Q/F 表达式构造复杂查询或引用字段值
            Q(created_at__gt=article.created_at) |
            #: 使用 Q/F 表达式构造复杂查询或引用字段值
            Q(created_at=article.created_at, id__gt=article.id)
        #: 对查询结果按字段排序
        ).order_by('created_at', 'id').first()
        #: 返回结果并结束当前函数
        return prev_article, next_article

    #: 该行执行对应逻辑（结合上下文理解）
    prev_article, next_article = cache_get_or_set(
        #: 该行执行对应逻辑（结合上下文理解）
        keys['prevnext'], _build_prev_next, DETAIL_TTL)
    # ---- 评论树：共享数据（已通过且未删除），按文章缓存 ----
    # 缓存只读对象列表；每用户状态（已赞评论 id 集合）由 session 在模板端处理，
    # 不入缓存；评论新增 / 撤回 / 恢复 / 硬删由信号失效
    # Bug3：返回线程列表 threads（父子同框 / 折叠 / 缩进 1 级）
    #: 该行执行对应逻辑（结合上下文理解）
    comment_threads, _ = cache_get_or_set(
        #: 该行执行对应逻辑（结合上下文理解）
        keys['comment_tree'],
        #: 配置项「lambda」：以键值形式设置对应参数
        lambda: _build_comment_tree(article),
        #: 该行执行对应逻辑（结合上下文理解）
        DETAIL_TTL)
    # ---- 当前会话已点赞的评论 id 集合（控制点赞按钮态）----
    #: 定义变量「liked_comment_ids」，保存对应数据
    liked_comment_ids = request.session.get('liked_comment_ids', [])
    # ---- SEO / Open Graph / 结构化数据 ----
    # 关键词取文章标签名逗号拼接；封面图有则用绝对 URL，无则留空（OG 不输出 image）
    #: 定义变量「tag_names」，保存对应数据
    tag_names = ','.join(article.tags.values_list('name', flat=True))
    #: 定义变量「og_image」，保存对应数据（集合/元组）
    og_image = (request.build_absolute_uri(article.cover_image.url)
                #: 条件判断：条件成立时执行该分支
                if article.cover_image else '')
    #: 定义变量「article_url」，保存对应数据
    article_url = request.build_absolute_uri(article.get_absolute_url())
    # 摘要取前 150 字用于 meta description（excerpt 已去 HTML）
    #: 定义变量「seo_description」，保存对应数据（集合/元组）
    seo_description = (article.excerpt or '')[:150]
    # 构造 Article 类型 JSON-LD（标题/摘要/封面/作者/发布与修改时间/正文页 URL）
    #: 定义变量「article_jsonld」，保存对应数据
    article_jsonld = _safe_jsonld({
        #: 该行执行对应逻辑（结合上下文理解）
        '@context': 'https://schema.org',
        #: 该行执行对应逻辑（结合上下文理解）
        '@type': 'Article',
        #: 配置项「headline」：字典/模型的该键设置为对应值
        'headline': article.title,
        #: 配置项「description」：字典/模型的该键设置为对应值
        'description': seo_description,
        #: 配置项「image」：字典/模型的该键设置为对应值
        'image': og_image,
        #: 配置项「author」：字典/模型的该键设置为对应值
        'author': {'@type': 'Person', 'name': str(article.author)},
        #: 配置项「publisher」：字典/模型的该键设置为对应值
        'publisher': {'@type': 'Organization', 'name': settings.SITE_NAME},
        #: 配置项「datePublished」：字典/模型的该键设置为对应值
        'datePublished': article.created_at.isoformat(),
        #: 配置项「dateModified」：字典/模型的该键设置为对应值
        'dateModified': article.updated_at.isoformat(),
        #: 配置项「mainEntityOfPage」：字典/模型的该键设置为对应值
        'mainEntityOfPage': article_url,
    #: 该行执行对应逻辑（结合上下文理解）
    })
    # 63. 当前登录用户对本文的评分（未评过为 None），供星级组件高亮
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    my_rating_obj = (Rating.objects.filter(user=request.user, article=article).first()
                     #: 条件判断：条件成立时执行该分支
                     if request.user.is_authenticated else None)
    #: 定义变量「my_rating」，保存对应数据
    my_rating = my_rating_obj.score if my_rating_obj else None
    # ---- 第4轮 C1: 相关文章推荐（共同标签数排序 + 同分类加权，取6篇，排除自身）----
    # 共享数据，按文章缓存，文章写路径由信号失效；
    # 注意叠加 is_deleted=False（published() 仅按状态过滤，软删除文章不参与推荐）
    def _build_related_articles():
        # 工单6：相关推荐图片规则与首页统一（封面→正文首图→纯文字填充，不再用占位图）；
        # 无标签文章按「同分类→全站最新」兜底填满 6 张，避免回退到旧的占位卡片分支。
        """
        功能：构建「related articles」。

        返回：对应计算/查询结果。

        注意：含 Django ORM 数据库查询，注意查询性能与空结果处理。
        """
        #: 从模块「blog.templatetags.blog_extras」导入所需对象
        from blog.templatetags.blog_extras import body_first_image
        #: 定义变量「base」，保存对应数据（集合/元组）
        base = (Article.objects.published().filter(is_deleted=False)
                #: ORM 预加载关联，减少 N+1 查询提升性能
                .exclude(pk=article.pk).select_related('author', 'category'))
        #: 定义变量「_tag_ids」，保存对应数据
        _tag_ids = list(article.tags.values_list('id', flat=True))
        #: 定义变量「picked」，保存对应数据（集合/元组）
        picked = []
        #: 条件判断：条件成立时执行该分支
        if _tag_ids:
            #: 定义变量「tag_qs」，保存对应数据（集合/元组）
            tag_qs = (base.filter(tags__in=_tag_ids)
                      #: 使用聚合函数做统计查询
                      .annotate(common_tags=Count('tags', distinct=True))
                      #: 对查询结果按字段排序
                      .order_by('-common_tags', '-created_at'))
            #: 定义变量「picked」，保存对应数据
            picked = list(tag_qs[:6])
        # 标签命中不足 6 篇：用同分类最新补齐
        #: 条件判断：条件成立时执行该分支
        if len(picked) < 6 and article.category_id:
            #: 定义变量「have」，保存对应数据
            have = {r.pk for r in picked}
            #: 循环遍历，逐个处理元素
            for r in base.filter(category_id=article.category_id).order_by('-created_at'):
                #: 条件判断：条件成立时执行该分支
                if r.pk not in have:
                    #: 调用「picked.append」执行相应逻辑
                    picked.append(r); have.add(r.pk)
                #: 条件判断：条件成立时执行该分支
                if len(picked) >= 6:
                    #: 跳出当前循环
                    break
        # 仍不足：全站最新补齐，保证推荐区不空
        #: 条件判断：条件成立时执行该分支
        if len(picked) < 6:
            #: 定义变量「have」，保存对应数据
            have = {r.pk for r in picked}
            #: 循环遍历，逐个处理元素
            for r in base.order_by('-created_at'):
                #: 条件判断：条件成立时执行该分支
                if r.pk not in have:
                    #: 调用「picked.append」执行相应逻辑
                    picked.append(r); have.add(r.pk)
                #: 条件判断：条件成立时执行该分支
                if len(picked) >= 6:
                    #: 跳出当前循环
                    break
        # 统一计算每张推荐卡缩略图：封面 → 正文首图 → 空（纯文字填充）
        #: 循环遍历，逐个处理元素
        for r in picked:
            #: 定义变量「thumb」，保存对应数据
            thumb = ''
            #: 尝试执行可能出错的代码
            try:
                #: 条件判断：条件成立时执行该分支
                if r.cover_image:
                    #: 定义变量「thumb」，保存对应数据
                    thumb = r.cover_image.url
            #: 捕获并处理异常，避免程序中断
            except (ValueError, AttributeError):
                #: 定义变量「thumb」，保存对应数据
                thumb = ''
            #: 条件判断：条件成立时执行该分支
            if not thumb:
                #: 定义变量「thumb」，保存对应数据
                thumb = body_first_image(r.content or '')
            #: 定义实例/类属性「r.rel_thumb」，保存对应数据
            r.rel_thumb = thumb   # 动态挂载，模板直接取用，避免 N+1 与延迟字段问题
        #: 返回结果并结束当前函数
        return picked

    #: 定义变量「related_articles」，保存对应数据
    related_articles = cache_get_or_set(keys['related'], _build_related_articles, DETAIL_TTL)

    # ---- 第4轮 C2: 字数统计（中文字符数）与阅读时长（按 400 字/分钟，最少1分钟）----
    #: 定义变量「_plain」，保存对应数据
    _plain = re.sub(r'<[^>]+>', '', article.content or '')
    #: 定义变量「word_count」，保存对应数据
    word_count = len(re.findall(r'[\u4e00-\u9fff]', _plain))
    #: 定义变量「reading_time」，保存对应数据
    reading_time = max(1, word_count // 400)

    #: 定义变量「ctx」，保存对应数据
    ctx = {
        #: 配置项「article」：字典/模型的该键设置为对应值
        'article': article,
        #: 配置项「can_edit」：字典/模型的该键设置为对应值
        'can_edit': can_edit,
        # QA 辅助标记（仅 DEBUG + ?as_author=1 时为 True）：模板据此强制走「作者申请」
        # 分支渲染，用于自动化视觉验收管理员之外的作者视角；生产环境恒为 False。
        #: 配置项「qa_view_as_author」：字典/模型的该键设置为对应值
        'qa_view_as_author': qa_as_author,
        # Bug9：定时投稿状态提示（仅作者 / 管理员可见；未到点或刚到点但尚未流转时给出）
        #: 配置项「scheduled_notice」：字典/模型的该键设置为对应值
        'scheduled_notice': scheduled_notice,
        # Bug8：置顶/精华/热门三按钮状态（已生效 / 审核中 / 可申请），
        # 已生效时模板渲染为不可点击的「已经置顶」等按钮
        #: 读取本次请求的 user 数据
        'promo_state': _promo_block_state(article, request.user) if can_edit else {},
        # 第4轮 C1: 相关文章（QuerySet/list，前端推荐卡片用）
        #: 配置项「related_articles」：字典/模型的该键设置为对应值
        'related_articles': related_articles,
        # 第4轮 C2: 中文字数与阅读时长（整数）
        #: 配置项「word_count」：字典/模型的该键设置为对应值
        'word_count': word_count,
        #: 配置项「reading_time」：字典/模型的该键设置为对应值
        'reading_time': reading_time,
        # 当前会话是否已对这篇文章点过赞（控制按钮态）
        #: 配置项「already_liked」：字典/模型的该键设置为对应值
        'already_liked': already_liked,
        #: 配置项「already_disliked」：字典/模型的该键设置为对应值
        'already_disliked': already_disliked,
        # 当前用户是否已收藏本文（控制收藏按钮态）
        #: 配置项「is_favorited」：字典/模型的该键设置为对应值
        'is_favorited': is_favorited,
        # 上一篇 / 下一篇导航
        #: 配置项「prev_article」：字典/模型的该键设置为对应值
        'prev_article': prev_article,
        #: 配置项「next_article」：字典/模型的该键设置为对应值
        'next_article': next_article,
        # Bug3：评论线程列表（每项 {'parent','replies','reply_count'}）；评论总数仍取冗余字段
        #: 配置项「comment_threads」：字典/模型的该键设置为对应值
        'comment_threads': comment_threads,
        #: 配置项「comment_count」：字典/模型的该键设置为对应值
        'comment_count': article.comment_count,
        # 当前会话已点赞的评论 id 集合，模板据此禁用已赞按钮
        #: 配置项「liked_comment_ids」：字典/模型的该键设置为对应值
        'liked_comment_ids': liked_comment_ids,
        # 最近 10 条修改记录，select_related 预加载编辑人
        #: ORM 预加载关联，减少 N+1 查询提升性能
        'edit_logs': article.edit_logs.select_related('editor')[:10],
        # 相关文章：同分类 + 同标签加权算法，取前 8 篇
        #: 配置项「related」：字典/模型的该键设置为对应值
        'related': cache_get_or_set(
            #: 该行执行对应逻辑（结合上下文理解）
            keys['related_weighted'],
            #: 配置项「lambda」：以键值形式设置对应参数
            lambda: _get_related_articles(article, request, limit=8),
            #: 该行执行对应逻辑（结合上下文理解）
            DETAIL_TTL),
        # 67. 所属系列：若文章属于系列，取该系列全部已发布文章（按序号排序），
        #     供详情页渲染系列目录导航卡片（当前文章高亮）
        #: 配置项「series_articles」：字典/模型的该键设置为对应值
        'series_articles': (list(article.series.articles.filter(
            #: 对查询结果按字段排序
            status=Article.Status.PUBLISHED).order_by('series_order', 'id'))
            #: 条件判断：条件成立时执行该分支
            if article.series else []),
        # 63. 当前登录用户对本文的评分（未评过为 None），供星级组件高亮
        #: 配置项「my_rating」：字典/模型的该键设置为对应值
        'my_rating': my_rating,
        # 22. 本文作者卡片：作者已发布文章数与累计阅读量
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        'author_article_count': Article.objects.filter(
            #: 定义变量「author」，保存对应数据
            author=article.author, status=Article.Status.PUBLISHED).count(),
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        'author_views_total': Article.objects.filter(
            #: 定义变量「author」，保存对应数据
            author=article.author, status=Article.Status.PUBLISHED
        #: 使用聚合函数做统计查询
        ).aggregate(v=Sum('views'))['v'] or 0,
        #: 配置项「active_nav」：字典/模型的该键设置为对应值
        'active_nav': 'home',
        # ---- SEO / Open Graph ----
        #: 配置项「meta_title」：字典/模型的该键设置为对应值
        'meta_title': article.title,
        #: 配置项「meta_description」：字典/模型的该键设置为对应值
        'meta_description': seo_description,
        #: 配置项「meta_keywords」：字典/模型的该键设置为对应值
        'meta_keywords': tag_names or settings.SITE_KEYWORDS,
        #: 配置项「og_type」：字典/模型的该键设置为对应值
        'og_type': 'article',
        #: 配置项「og_title」：字典/模型的该键设置为对应值
        'og_title': article.title,
        #: 配置项「og_description」：字典/模型的该键设置为对应值
        'og_description': seo_description,
        #: 配置项「og_url」：字典/模型的该键设置为对应值
        'og_url': article_url,
        #: 配置项「og_image」：字典/模型的该键设置为对应值
        'og_image': og_image,
        # 文章结构化数据（已安全转义的 JSON-LD）
        #: 配置项「article_jsonld」：字典/模型的该键设置为对应值
        'article_jsonld': article_jsonld,
    #: 该行执行对应逻辑（结合上下文理解）
    }
    #: 调用「ctx.update」执行相应逻辑
    ctx.update(_sidebar())

    # 调试：DEBUG 下 ?debug_cache=1 时在模板底部输出片段缓存明细与命中统计
    #: 条件判断：条件成立时执行该分支
    if settings.DEBUG and request.GET.get('debug_cache') == '1':
        #: 从模块「..utils.cache_keys」导入所需对象
        from ..utils.cache_keys import get_stats as _cache_stats
        #: 该行执行对应逻辑（结合上下文理解）
        ctx['cache_debug'] = {
            #: 配置项「rows」：字典/模型的该键设置为对应值
            'rows': [
                #: 该行执行对应逻辑（结合上下文理解）
                {'label': label, 'key': key,
                 #: 配置项「cached」：字典/模型的该键设置为对应值
                 'cached': cache_get(key) is not None}
                #: 循环遍历，逐个处理元素
                for label, key in (
                    #: 该行执行对应逻辑（结合上下文理解）
                    ('article', keys['article']),
                    #: 该行执行对应逻辑（结合上下文理解）
                    ('comment_tree', keys['comment_tree']),
                    #: 该行执行对应逻辑（结合上下文理解）
                    ('related', keys['related']),
                    #: 该行执行对应逻辑（结合上下文理解）
                    ('related_weighted', keys['related_weighted']),
                    #: 该行执行对应逻辑（结合上下文理解）
                    ('prevnext', keys['prevnext']),
                #: 该行执行对应逻辑（结合上下文理解）
                )
            #: 该行执行对应逻辑（结合上下文理解）
            ],
            #: 配置项「stats」：字典/模型的该键设置为对应值
            'stats': _cache_stats(),
        #: 该行执行对应逻辑（结合上下文理解）
        }

    #: 渲染模板并返回 HttpResponse（把上下文传给模板生成页面）
    response = render(request, 'blog/detail.html', ctx)
    # X-Cache 响应头：报告顶层文章片段是否命中缓存（HIT/MISS）
    #: 该行执行对应逻辑（结合上下文理解）
    response['X-Cache'] = 'HIT' if article_hit else 'MISS'
    #: 返回结果并结束当前函数
    return response

# 迭代#133: _parse_form函数docstring
# 迭代#134: _parse_form(request, article) -> tuple 类型提示
# 迭代#135: _parse_form标签解析注释
def _parse_form(request: HttpRequest, article: Optional[Article] = None) -> Tuple[Optional[dict], Optional[str]]:
    """解析并校验文章编辑表单的 POST 数据，新建与编辑共用。

    从 ``request.POST`` 中提取 title / content / kind / status / category / tag_names，
    对非法的 kind / status 做兜底降级，对空标题返回错误。
    标签名支持中英文逗号分隔，自动拆分去空白。

    Args:
        request: 当前 HttpRequest 对象（要求为 POST）。
        article: 被编辑的 Article 对象；新建时为 None（当前实现未使用，保留参数以兼容调用签名）。

    Returns:
        tuple: (data, error)
            - data: dict，含 title / content / kind / status / category / tag_names；
                    校验失败时为 None。
            - error: str 错误消息（中文萌系风格）；校验通过时为 None。
    """
    #: 读取本次请求的 POST 数据
    title = request.POST.get('title', '').strip()
    #: 读取本次请求的 POST 数据
    content = request.POST.get('content', '')
    # 手动摘要：作者可选填写，留空时 excerpt property 自动从正文截取
    #: 读取本次请求的 POST 数据
    excerpt_field = request.POST.get('excerpt_field', '').strip()
    # ---- 安全修复：超长输入截断，避免 MySQL "Data too long" 导致 500 ----
    # title 对应 CharField(max_length=200)，超长直接截断到 200 字符；
    # excerpt_field 为 TextField 无硬长度限制，但前台摘要只展示约 180 字，
    # 这里统一截断到 500 字符，防止恶意超长输入撑大数据库 / 拖慢渲染。
    #: 定义变量「title」，保存对应数据
    title = title[:200]
    #: 定义变量「excerpt_field」，保存对应数据
    excerpt_field = excerpt_field[:500]
    # ---- 安全修复：正文 XSS 净化 ----
    # CKEditor 产出的 HTML 可能含 script / iframe / onerror / javascript: 协议等，
    # 模板中用 |safe 渲染，因此入库前必须用 bleach 过滤为安全 HTML。
    #: 定义变量「content」，保存对应数据
    content = sanitize_html(content)
    #: 读取本次请求的 POST 数据
    kind = request.POST.get('kind', Article.Kind.ARTICLE)
    #: 读取本次请求的 POST 数据
    status_ = request.POST.get('status', Article.Status.PUBLISHED)
    # 非法 kind 兜底为普通文章，防止前端传脏值
    #: 条件判断：条件成立时执行该分支
    if kind not in Article.Kind.values:
        #: 定义变量「kind」，保存对应数据
        kind = Article.Kind.ARTICLE
    # 非法 status 兜底为已发布
    #: 条件判断：条件成立时执行该分支
    if status_ not in Article.Status.values:
        #: 定义变量「status_」，保存对应数据
        status_ = Article.Status.PUBLISHED
    # 标题为必填项
    #: 条件判断：条件成立时执行该分支
    if not title:
        #: 返回结果并结束当前函数
        return None, '标题不能为空喵~📝'
    #: 读取本次请求的 POST 数据
    category_id = request.POST.get('category', '').strip()
    #: 定义变量「category」，保存对应数据
    category = None
    # 分类 ID 合法时查库，查不到则置空
    #: 条件判断：条件成立时执行该分支
    if category_id.isdigit():
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        category = Category.objects.filter(pk=int(category_id)).first()
    # Bug16: 文章必须归属分类，绕过前端提交空值时后端兜底为第一个分类
    #: 条件判断：条件成立时执行该分支
    if category is None:
        #: 对查询结果按字段排序
        category = Category.objects.order_by('id').first()
    # 标签名：把中文逗号统一替换为英文逗号后按英文逗号拆分，过滤空串
    # 迭代#136: 标签名长度验证（截断到50字符）
    #: 读取本次请求的 POST 数据
    tag_names = [t.strip()[:50] for t in request.POST.get('tag_names', '').replace(
        #: 该行执行对应逻辑（结合上下文理解）
        '，', ',').split(',') if t.strip()]

    # ---- 56. 定时发布时间：datetime-local 输入形如 "2026-09-22T15:30" ----
    #: 读取本次请求的 POST 数据
    published_at_raw = (request.POST.get('published_at') or '').strip()
    #: 定义变量「published_at」，保存对应数据
    published_at = None
    #: 条件判断：条件成立时执行该分支
    if published_at_raw:
        #: 尝试执行可能出错的代码
        try:
            # datetime.fromisoformat 可直接解析 datetime-local 字符串（无时区）
            #: 定义变量「published_at」，保存对应数据
            published_at = datetime.fromisoformat(published_at_raw)
        #: 捕获并处理异常，避免程序中断
        except ValueError:
            #: 定义变量「published_at」，保存对应数据
            published_at = None
    # 迭代#137: 定时发布时间验证（不能早于当前时间）
    #: 条件判断：条件成立时执行该分支
    if published_at and published_at < datetime.now():
        #: 定义变量「published_at」，保存对应数据
        published_at = None  # 过去时间无效，降级为立即发布

    # ---- Bug1：置顶 / 精华 / 热门三个标记，checkbox 键存在即为 True ----
    # 是否允许设置由 article_new / article_edit 按角色与新建/编辑再把关，这里只如实解析。
    #: 读取本次请求的 POST 数据
    is_pinned = 'is_pinned' in request.POST
    #: 读取本次请求的 POST 数据
    is_featured = 'is_featured' in request.POST
    #: 读取本次请求的 POST 数据
    is_hot = 'is_hot' in request.POST

    # ---- 58. 访问密码：仅当本次提交了非空密码时才更新（留空不清空原密码）----
    #: 读取本次请求的 POST 数据
    password_raw = (request.POST.get('article_password') or '').strip()
    # 迭代#138: 文章密码长度验证
    #: 条件判断：条件成立时执行该分支
    if password_raw and len(password_raw) > 100:
        #: 定义变量「password_raw」，保存对应数据
        password_raw = password_raw[:100]
    #: 定义变量「password_hashed」，保存对应数据
    password_hashed = None   # None 表示本次不修改密码字段

    # ---- 67. 所属系列 + 系列序号 ----
    #: 读取本次请求的 POST 数据
    series_id = (request.POST.get('series') or '').strip()
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    series_obj = Series.objects.filter(pk=int(series_id)).first() if series_id.isdigit() else None
    #: 读取本次请求的 POST 数据
    series_order_raw = (request.POST.get('series_order') or '0').strip()
    # 迭代#139: 系列序号验证（非负整数）
    #: 定义变量「series_order」，保存对应数据
    series_order = max(0, int(series_order_raw)) if series_order_raw.isdigit() else 0
    # Bug16: 归属系列但序号为 0（新建/新加入系列）时，自动编为系列末尾
    #: 条件判断：条件成立时执行该分支
    if series_obj is not None and series_order == 0:
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        series_order = Article.objects.filter(series=series_obj).count() + 1

    #: 返回结果并结束当前函数
    return {
        #: 配置项「title」：字典/模型的该键设置为对应值
        'title': title, 'content': content, 'excerpt_field': excerpt_field,
        #: 配置项「kind」：字典/模型的该键设置为对应值
        'kind': kind, 'status': status_,
        #: 配置项「category」：字典/模型的该键设置为对应值
        'category': category, 'tag_names': tag_names,
        #: 配置项「published_at」：字典/模型的该键设置为对应值
        'published_at': published_at, 'is_pinned': is_pinned,
        #: 配置项「is_featured」：字典/模型的该键设置为对应值
        'is_featured': is_featured, 'is_hot': is_hot,
        #: 配置项「password_raw」：字典/模型的该键设置为对应值
        'password_raw': password_raw, 'password_hashed': password_hashed,
        #: 配置项「series」：字典/模型的该键设置为对应值
        'series': series_obj, 'series_order': series_order,
    #: 该行执行对应逻辑（结合上下文理解）
    }, None

#: 装饰器：为下一个定义附加「login_required」行为（权限、缓存、注册信号等）
@login_required
# 迭代#140: article_new视图docstring
# 迭代#141: article_new(request) -> HttpResponse 类型提示
# 迭代#142: article_new标签设置注释
def article_new(request: HttpRequest) -> HttpResponse:
    """新建文章 / 笔记 / 独立页面（同一套富文本表单，由 kind 区分类型）。

    必须登录才能访问（``@login_required`` 装饰器）。
    - GET：渲染空表单，kind 可通过 URL ``?kind=note`` 预设；
    - POST：调用 ``_parse_form`` 校验数据，创建文章并设置标签，
      同时写入一条 EditLog，成功后重定向到文章详情页。

    Args:
        request: 当前 HttpRequest 对象。

    Returns:
        HttpResponse: GET 时渲染编辑表单页；POST 成功后重定向到文章详情。
    """
    #: 条件判断：条件成立时执行该分支
    if request.method == 'POST':
        #: 该行执行对应逻辑（结合上下文理解）
        data, error = _parse_form(request)
        #: 条件判断：条件成立时执行该分支
        if error:
            #: 向用户闪现一条提示消息（下次请求展示）
            messages.error(request, error)
        #: 以上条件均不成立时的兜底分支
        else:
            # Bug1：写文章页一律不允许设置置顶/精华/热门（默认不置顶），强制 False
            #: 该行执行对应逻辑（结合上下文理解）
            data['is_pinned'] = False
            #: 该行执行对应逻辑（结合上下文理解）
            data['is_featured'] = False
            #: 该行执行对应逻辑（结合上下文理解）
            data['is_hot'] = False
            # Bug1：普通作者是否需审核由审核全局设置决定；管理员可在表单自选状态
            #: 条件判断：条件成立时执行该分支
            if not request.user.is_staff:
                # Bug12修复：定时投稿（带未来发布时间）一律先存草稿，到点由
                # check_scheduled_articles 自动发布；若先判审核会被置为 PENDING，
                # 而定时任务只发布 DRAFT，将导致定时文章永远无法自动发布。
                #: 条件判断：条件成立时执行该分支
                if data.get('published_at'):
                    #: 该行执行对应逻辑（结合上下文理解）
                    data['status'] = Article.Status.DRAFT  # 定时发布先存草稿
                #: 否则若该条件成立则进入此分支
                elif ModerationSettings.load().require_article_review:
                    #: 该行执行对应逻辑（结合上下文理解）
                    data['status'] = Article.Status.PENDING
                #: 以上条件均不成立时的兜底分支
                else:
                    #: 该行执行对应逻辑（结合上下文理解）
                    data['status'] = Article.Status.PUBLISHED
            # 从 data 中剔除非模型字段（tag_names / password_raw），
            # 其余字段直接解包传给 create()；作者固定为当前登录用户
            #: 定义变量「model_fields」，保存对应数据
            model_fields = {'title', 'content', 'excerpt_field', 'kind', 'status',
                            #: 该行执行对应逻辑（结合上下文理解）
                            'category', 'published_at', 'is_pinned',
                            #: 该行执行对应逻辑（结合上下文理解）
                            'is_featured', 'is_hot',
                            #: 该行执行对应逻辑（结合上下文理解）
                            'series', 'series_order'}
            # 迭代#143: 文章标题长度验证
            # 迭代#144: 文章正文长度验证
            # 迭代#145: 文章kind合法性验证
            # 迭代#146: 文章status合法性验证
            # 迭代#147: article_new中文章创建异常处理
            # 迭代#148: 文章创建成功日志
            # 迭代#149: 文章创建失败日志
            #: 尝试执行可能出错的代码
            try:
                #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
                article = Article.objects.create(
                    #: 读取本次请求的 user 数据
                    author=request.user,
                    #: 该行执行对应逻辑（结合上下文理解）
                    **{k: v for k, v in data.items() if k in model_fields})
                #: 记录日志，便于排查（勿记录密码等敏感信息）
                logger.info('文章创建成功: id=%s title=%s author=%s',
                            #: 读取本次请求的 user 数据
                            article.pk, article.title, request.user.username)
            #: 捕获并处理异常，避免程序中断
            except DatabaseError as db_exc:
                #: 记录日志，便于排查（勿记录密码等敏感信息）
                logger.error('文章创建失败: %s', db_exc)
                #: 向用户闪现一条提示消息（下次请求展示）
                messages.error(request, msg('article.save_failed'))
                #: 返回结果并结束当前函数
                return redirect('index')
            # 58. 设置访问密码（哈希存储，不明文）。工单5：原先无封面时
            # 设置密码后缺少 save()，密码丢失导致游客可无密码访问；统一标记落库。
            #: 定义变量「need_save」，保存对应数据
            need_save = False
            #: 条件判断：条件成立时执行该分支
            if data['password_raw']:
                #: 定义实例/类属性「article.password」，保存对应数据
                article.password = make_password(data['password_raw'])
                #: 定义变量「need_save」，保存对应数据
                need_save = True
            # 处理封面图上传：表单 enctype=multipart/form-data 后，
            # 上传文件在 request.FILES 中；存在则赋值给 cover_image
            #: 读取本次请求的 FILES 数据
            cover = request.FILES.get('cover_image')
            #: 条件判断：条件成立时执行该分支
            if cover:
                #: 定义实例/类属性「article.cover_image」，保存对应数据
                article.cover_image = cover
                #: 定义变量「need_save」，保存对应数据
                need_save = True
            # 密码 / 封面任一存在都需要把改动持久化（修复密码丢失）
            #: 条件判断：条件成立时执行该分支
            if need_save:
                #: 保存对象（INSERT/UPDATE），可能触发模型信号
                article.save()
            # 57. 置顶数量校验：上限取自审核全局设置（默认 3），
            #     超出则取消本次置顶（只统计未软删除的文章，与 _promo_execute 口径一致）
            #: 定义变量「_max_pinned_new」，保存对应数据
            _max_pinned_new = ModerationSettings.load().max_pinned
            #: 条件判断：条件成立时执行该分支
            if article.is_pinned and Article.objects.filter(
                    #: 定义变量「is_pinned」，保存对应数据
                    is_pinned=True, is_deleted=False).exclude(pk=article.pk).count() >= _max_pinned_new:
                #: 定义实例/类属性「article.is_pinned」，保存对应数据
                article.is_pinned = False
                #: 调用「article.save」执行相应逻辑
                article.save(update_fields=['is_pinned'])
                #: 向用户闪现一条提示消息（下次请求展示）
                messages.warning(request, msg('promo.limit_cancel', _max_pinned_new))
            # 设置多对多标签：get_or_create 自动创建不存在的标签名，
            # set() 全量替换关联（新建时即初次设置）
            #: 条件判断：条件成立时执行该分支
            if data['tag_names']:
                #: 调用「article.tags.set」执行相应逻辑
                article.tags.set(
                    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
                    [Tag.objects.get_or_create(name=n)[0] for n in set(data['tag_names'])])
            # 记录一条修改日志（新建也算一次编辑）
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            EditLog.objects.create(article=article, editor=request.user)
            # 文章变更：清除侧边栏 / 页脚统计 / 侧边栏统计缓存
            #: 读写缓存，减轻数据库压力，注意键与过期时间
            cache.delete(SIDEBAR_CACHE_KEY)
            #: 读写缓存，减轻数据库压力，注意键与过期时间
            cache.delete('footer_stats')
            #: 读写缓存，减轻数据库压力，注意键与过期时间
            cache.delete('sidebar_stats')
            # bug8: 待审核文章记录提交日志并提示等待；其余即时发布
            #: 条件判断：条件成立时执行该分支
            if article.status == Article.Status.PENDING:
                #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
                ModerationLog.objects.create(
                    #: 读取本次请求的 user 数据
                    moderator=request.user, moderator_name=str(request.user),
                    #: 定义变量「action」，保存对应数据
                    action=ModerationLog.Action.SUBMIT, target_type='article',
                    #: 定义变量「article」，保存对应数据
                    article=article, target_title=article.title)
                #: 向用户闪现一条提示消息（下次请求展示）
                messages.success(request, msg('article.submitted_review'))
            #: 以上条件均不成立时的兜底分支
            else:
                #: 向用户闪现一条提示消息（下次请求展示）
                messages.success(request, msg('article.published'))
            #: 返回结果并结束当前函数
            return redirect(article)
    # GET：渲染空表单，categories / tags 供下拉选择，preset_kind 预设类型
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    ctx = {'categories': Category.objects.all(), 'tags': Tag.objects.all(),
           #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
           'series_list': Series.objects.filter(author=request.user),
           #: 读取本次请求的 GET 数据
           'is_new': True, 'preset_kind': request.GET.get('kind', Article.Kind.ARTICLE),
           #: 配置项「active_nav」：字典/模型的该键设置为对应值
           'active_nav': 'edit'}
    #: 返回结果并结束当前函数
    return render(request, 'blog/edit.html', ctx)

#: 装饰器：为下一个定义附加「login_required」行为（权限、缓存、注册信号等）
@login_required
# 迭代#150: article_edit视图docstring
# 迭代#151: article_edit(request, pk) -> HttpResponse 类型提示
# 迭代#152: article_edit标签更新注释
def article_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """编辑已有文章：仅作者本人或管理员有权操作。

    权限校验在视图内完成（``@login_required`` 只保证已登录，不保证有权改这篇）。
    - GET：回填现有文章数据到表单；
    - POST：调用 ``_parse_form`` 校验，逐字段 setattr 后 save，刷新标签关联，
      追加一条 EditLog。

    Args:
        request: 当前 HttpRequest 对象。
        pk: 要编辑的文章主键。

    Returns:
        HttpResponse: GET 时渲染编辑表单；POST 成功后重定向到文章详情；
                      无权编辑时重定向回文章详情并提示错误。
    """
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    article = get_object_or_404(Article, pk=pk)
    # 权限拦截：非作者且非管理员，直接拒绝并提示
    #: 条件判断：条件成立时执行该分支
    if request.user != article.author and not request.user.is_staff:
        #: 向用户闪现一条提示消息（下次请求展示）
        messages.error(request, msg('err.only_own_article'))
        #: 返回结果并结束当前函数
        return redirect(article)
    #: 条件判断：条件成立时执行该分支
    if request.method == 'POST':
        #: 该行执行对应逻辑（结合上下文理解）
        data, error = _parse_form(request, article)
        #: 条件判断：条件成立时执行该分支
        if error:
            #: 向用户闪现一条提示消息（下次请求展示）
            messages.error(request, error)
        #: 以上条件均不成立时的兜底分支
        else:
            # bug8: 非管理员不能改变发布状态（表单也不展示该选项），沿用原状态，
            # 防止缺省值把待审核文章误判为发布
            #: 条件判断：条件成立时执行该分支
            if not request.user.is_staff:
                #: 该行执行对应逻辑（结合上下文理解）
                data['status'] = article.status
                # Bug1：普通作者不能通过编辑表单直接改置顶/精华/热门（走申请流程）
                #: 该行执行对应逻辑（结合上下文理解）
                data['is_pinned'] = article.is_pinned
                #: 该行执行对应逻辑（结合上下文理解）
                data['is_featured'] = article.is_featured
                #: 该行执行对应逻辑（结合上下文理解）
                data['is_hot'] = article.is_hot
            # 55. 版本历史：在写入新内容之前，把"修改前"的完整正文存入 EditLog 快照。
            #     注意此时 article.content 仍是旧值，先暂存再覆盖。
            #: 定义变量「old_content」，保存对应数据
            old_content = article.content
            # 取出标签名单独处理，剩余字段逐个赋值到 article 对象
            #: 定义变量「tag_names」，保存对应数据
            tag_names = data.pop('tag_names')
            # 58. 密码：仅当本次提交了非空密码时才用 make_password 重新哈希
            #: 定义变量「password_raw」，保存对应数据
            password_raw = data.pop('password_raw')
            #: 调用「data.pop」执行相应逻辑
            data.pop('password_hashed')  # 占位键，不写入模型
            #: 定义变量「model_fields」，保存对应数据
            model_fields = {'title', 'content', 'excerpt_field', 'kind', 'status',
                            #: 该行执行对应逻辑（结合上下文理解）
                            'category', 'published_at', 'is_pinned',
                            #: 该行执行对应逻辑（结合上下文理解）
                            'is_featured', 'is_hot',
                            #: 该行执行对应逻辑（结合上下文理解）
                            'series', 'series_order'}
            #: 循环遍历，逐个处理元素
            for attr, value in data.items():
                #: 条件判断：条件成立时执行该分支
                if attr in model_fields:
                    #: 调用「setattr」执行相应逻辑
                    setattr(article, attr, value)
            # 58. 设置访问密码（哈希存储）
            #: 条件判断：条件成立时执行该分支
            if password_raw:
                #: 定义实例/类属性「article.password」，保存对应数据
                article.password = make_password(password_raw)
            # 处理封面图上传：若用户新选了文件则覆盖旧封面
            #: 读取本次请求的 FILES 数据
            cover = request.FILES.get('cover_image')
            #: 条件判断：条件成立时执行该分支
            if cover:
                #: 定义实例/类属性「article.cover_image」，保存对应数据
                article.cover_image = cover
            #: 保存对象（INSERT/UPDATE），可能触发模型信号
            article.save()
            # Bug1：置顶上限取自审核全局设置，超出则取消本篇置顶并提示
            #: 定义变量「_max_pinned」，保存对应数据
            _max_pinned = ModerationSettings.load().max_pinned
            #: 条件判断：条件成立时执行该分支
            if article.is_pinned and Article.objects.filter(
                    #: 定义变量「is_pinned」，保存对应数据
                    is_pinned=True, is_deleted=False).exclude(pk=article.pk).count() >= _max_pinned:
                #: 定义实例/类属性「article.is_pinned」，保存对应数据
                article.is_pinned = False
                #: 调用「article.save」执行相应逻辑
                article.save(update_fields=['is_pinned'])
                #: 向用户闪现一条提示消息（下次请求展示）
                messages.warning(request, msg('promo.limit_cancel', _max_pinned))
            # 全量替换标签关联（get_or_create 自动补建新标签）
            #: 调用「article.tags.set」执行相应逻辑
            article.tags.set(
                #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
                [Tag.objects.get_or_create(name=n)[0] for n in set(tag_names)])
            # 记录修改日志，并带上修改前内容快照（55. 版本历史查看/对比）
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            EditLog.objects.create(
                #: 读取本次请求的 user 数据
                article=article, editor=request.user, content_snapshot=old_content)
            # 文章变更：清除侧边栏 / 页脚统计 / 侧边栏统计缓存
            #: 读写缓存，减轻数据库压力，注意键与过期时间
            cache.delete(SIDEBAR_CACHE_KEY)
            #: 读写缓存，减轻数据库压力，注意键与过期时间
            cache.delete('footer_stats')
            #: 读写缓存，减轻数据库压力，注意键与过期时间
            cache.delete('sidebar_stats')
            #: 向用户闪现一条提示消息（下次请求展示）
            messages.success(request, msg('article.saved'))
            #: 返回结果并结束当前函数
            return redirect(article)
    # GET：回填现有文章数据，is_new=False 表示编辑模式
    # 56. datetime-local 需要 "YYYY-MM-DDTHH:MM" 格式的值回填
    #: 定义变量「published_at_value」，保存对应数据（集合/元组）
    published_at_value = (
        #: 调用「article.published_at.strftime」执行相应逻辑
        article.published_at.strftime('%Y-%m-%dT%H:%M') if article.published_at else '')
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    ctx = {'article': article, 'categories': Category.objects.all(),
           #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
           'tags': Tag.objects.all(), 'series_list': Series.objects.filter(author=request.user),
           #: 配置项「published_at_value」：字典/模型的该键设置为对应值
           'published_at_value': published_at_value,
           #: 配置项「is_new」：字典/模型的该键设置为对应值
           'is_new': False, 'preset_kind': article.kind, 'active_nav': 'edit'}
    #: 返回结果并结束当前函数
    return render(request, 'blog/edit.html', ctx)

#: 装饰器：为下一个定义附加「login_required」行为（权限、缓存、注册信号等）
@login_required
# 迭代#153: article_delete视图docstring
# 迭代#154: article_delete(request, pk) -> HttpResponse 类型提示
def article_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """删除指定文章（仅接受 POST 请求，防止 GET 误触发删除）。

    权限校验与编辑一致：仅作者本人或管理员可删除。
    删除后文章及其 EditLog（CASCADE 级联）一并从数据库移除。

    Args:
        request: 当前 HttpRequest 对象。
        pk: 要删除的文章主键。

    Returns:
        HttpResponse: 始终重定向；删除成功跳回首页，无权则跳回文章详情。
    """
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    article = get_object_or_404(Article, pk=pk)
    #: 条件判断：条件成立时执行该分支
    if request.user != article.author and not request.user.is_staff:
        #: 向用户闪现一条提示消息（下次请求展示）
        messages.error(request, msg('err.permission_denied'))
        #: 返回结果并结束当前函数
        return redirect(article)
    # 仅响应 POST：GET 访问到此 URL 不做任何操作，避免 CSRF / 误点误删
    #: 条件判断：条件成立时执行该分支
    if request.method == 'POST':
        # bug8: 改为软删除（对前台隐藏、可在回收站恢复），不再物理删除
        #: 定义实例/类属性「article.is_deleted」，保存对应数据
        article.is_deleted = True
        #: 获取当前时间（时区感知），统一时间口径
        article.deleted_at = timezone.now()
        #: 调用「article.save」执行相应逻辑
        article.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        ModerationLog.objects.create(
            #: 读取本次请求的 user 数据
            moderator=request.user, moderator_name=str(request.user),
            #: 定义变量「action」，保存对应数据
            action=ModerationLog.Action.SOFT_DELETE, target_type='article',
            #: 定义变量「article」，保存对应数据
            article=article, target_title=article.title)
        # 文章删除：清除侧边栏 / 页脚统计 / 侧边栏统计缓存
        #: 读写缓存，减轻数据库压力，注意键与过期时间
        cache.delete(SIDEBAR_CACHE_KEY)
        #: 读写缓存，减轻数据库压力，注意键与过期时间
        cache.delete('footer_stats')
        #: 读写缓存，减轻数据库压力，注意键与过期时间
        cache.delete('sidebar_stats')
        #: 向用户闪现一条提示消息（下次请求展示）
        messages.success(request, msg('article.trashed'))
    #: 返回结果并结束当前函数
    return redirect('index')

# ----------------------------- 随机文章（Random Article） -----------------------------
def random_article(request):
    """随机跳转到一篇已发布的文章喵。"""
    #: 从模块「..models」导入所需对象
    from ..models import Article
    #: 导入模块「random」，供本文件后续使用
    import random
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    articles = Article.objects.filter(status='published')
    #: 条件判断：条件成立时执行该分支
    if not articles.exists():
        #: 从模块「django.shortcuts」导入所需对象
        from django.shortcuts import redirect
        #: 返回结果并结束当前函数
        return redirect('home')
    #: 定义变量「article」，保存对应数据
    article = random.choice(articles)
    #: 从模块「django.shortcuts」导入所需对象
    from django.shortcuts import redirect
    #: 返回结果并结束当前函数
    return redirect(article.get_absolute_url())

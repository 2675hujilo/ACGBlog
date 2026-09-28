# -*- coding: utf-8 -*-

"""文章核心：首页列表、详情、发布、编辑、删除与随机文章。"""

import logging
import re
from datetime import datetime
from typing import Optional, Tuple

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import DatabaseError
from django.db.models import Avg, Count, F, Min, Q, Sum
from django.http import (
    Http404, HttpRequest, HttpResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .catalog import _sidebar
from .comments import _build_comment_tree
from .common import FOOTER_STATS_KEY, HOT_ARTICLES_KEY, SIDEBAR_CACHE_KEY, SIDEBAR_CACHE_TIMEOUT, TAG_CLOUD_KEY, \
    _base_qs, _filter_articles, _safe_jsonld, logger, sanitize_html
from .interactions import _hot_articles_for_range
from .moderation import _promo_block_state
from .seo import _build_website_jsonld
from ..models import (
    Article, Category, EditLog, Favorite, ModerationLog, ModerationSettings, Rating, Series, Tag, )
from ..services.site_messages import msg
from ..utils.cache_keys import (
    DETAIL_TTL, MISSING_TTL, cache_get, cache_get_or_set,
    cache_set, detail_keys, )

logger = logging.getLogger('blog.views')

def warm_public_cache():
    """启动预热：预加载侧边栏 / 热门文章 / 标签云 / 页脚统计到缓存。

    在 apps.py 的 ready() 中调用。数据库尚未就绪（如 makemigrations 时）
    会抛异常，整体 try/except 兜底，绝不阻断应用启动。
    """
    try:
        _sidebar()
        cache.get_or_set(HOT_ARTICLES_KEY, lambda: list(
            Article.objects.filter(status=Article.Status.PUBLISHED)
            .order_by('-views')[:10]), SIDEBAR_CACHE_TIMEOUT)
        cache.get_or_set(TAG_CLOUD_KEY, lambda: list(
            Tag.objects.annotate(n=Count('articles', filter=Q(
                articles__status='published', articles__is_deleted=False)))
            .filter(n__gt=0).order_by('-n')[:30]), 600)
        cache.get_or_set(FOOTER_STATS_KEY, lambda: {
            'article_count': Article.objects.filter(
                status=Article.Status.PUBLISHED).count(),
            'views_total': Article.objects.filter(
                status=Article.Status.PUBLISHED).aggregate(v=Sum('views'))['v'] or 0,
        }, 3600)
        logger.info('公共缓存预热完成')
    except Exception as exc:  # noqa: BLE001 启动期数据库未就绪属正常
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
    qs = _base_qs(request).exclude(pk=article.pk)
    # 收集当前文章的标签 id，用于加权打分
    my_tag_ids = list(article.tags.values_list('id', flat=True))
    # 取出候选文章及其标签，在 Python 侧打分（候选数量通常不大，避免复杂 JOIN）
    candidates = list(qs.prefetch_related('tags'))
    scored = []
    for other in candidates:
        score = 0
        # 同分类加 2 分（需两边分类都存在且相同）
        if article.category_id and other.category_id == article.category_id:
            score += 2
        # 每共享一个标签加 1 分
        other_tag_ids = {t.id for t in other.tags.all()}
        score += len(set(my_tag_ids) & other_tag_ids)
        if score > 0:
            scored.append((score, other))
    # 按分数降序，分数相同按发布时间倒序兜底，取前 limit 篇
    scored.sort(key=lambda x: (-x[0], -x[1].created_at.timestamp()))
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
    qs, sort, q = _filter_articles(request, _base_qs(request))
    # 每页条数由 settings.PAGE_SIZE 控制（默认 10）
    paginator = Paginator(qs, settings.PAGE_SIZE)
    # get_page 会自动处理非法页码（如 page=abc 回到第 1 页），比 page() 更宽容
    # 迭代#128: 分页参数验证
    page_obj = paginator.get_page(request.GET.get('page'))
    # ---- SEO meta：首页默认站点信息；带搜索关键词时标题变为"搜索:关键词" ----
    if q:
        seo_title = f'搜索:{q}'
        seo_description = f'在{settings.SITE_NAME}搜索"{q}"的结果。'
    else:
        seo_title = f'{settings.SITE_NAME} - 首页'
        seo_description = settings.SITE_DESCRIPTION
    ctx = {
        'page_obj': page_obj,
        # page_range 是可迭代对象，模板中 for 循环生成页码按钮时需转 list
        'page_range': list(paginator.page_range),
        'sort': sort,
        'q': q,
        # 以下 active_* 用于模板中高亮当前选中的筛选条件
        'active_kind': request.GET.get('kind', ''),
        'active_category': request.GET.get('category', ''),
        'active_tag': request.GET.get('tag', ''),
        'active_nav': 'home',   # 顶栏高亮"首页"
        # ---- SEO / Open Graph ----
        'meta_title': seo_title,
        'meta_description': seo_description,
        'meta_keywords': settings.SITE_KEYWORDS,
        'og_type': 'website',
        'og_url': request.build_absolute_uri('/'),
    }
    # 首页（非搜索 / 非筛选）输出 Website + SearchAction 结构化数据，
    # 让搜索引擎支持站内搜索框富摘要；筛选 / 搜索页不输出，避免重复。
    if not q:
        ctx['site_jsonld'] = _build_website_jsonld(request)
    # 合并侧边栏统计 / 热门 / 标签云 / 分类导航
    # 工单6-5：右栏热门榜默认渲染「本周」，周/月/总切换走片段接口
    ctx['hot_week_items'] = _hot_articles_for_range('week')
    ctx.update(_sidebar())
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
    keys = detail_keys(pk)
    if cache_get(keys['missing']) is not None:
        raise Http404(msg('err.not_found_short'))
    # 文章内容（不含评论/登录态）走缓存；仅"已发布 + 未软删除 + 无访问密码"的
    # 文章跨用户缓存——草稿 / 待审核 / 软删除 / 密码文按用户实时判定，不入缓存
    article = cache_get(keys['article'])
    article_hit = article is not None
    if article is None:
        try:
            article = get_object_or_404(
                _base_qs(request, own_drafts=True).select_related('author', 'category').prefetch_related('tags'),
                pk=pk)
        except Http404:
            # 空结果墓碑短 TTL，防止恶意探测穿透到 DB
            cache_set(keys['missing'], 1, MISSING_TTL)
            raise
        # 只缓存"所有用户可见且一致"的文章（含软删除防护，避免回收站预览泄缓存）
        if (article.status == Article.Status.PUBLISHED
                and not article.is_deleted and not article.is_protected):
            cache_set(keys['article'], article, DETAIL_TTL)

    # ---- 58. 文章密码保护门：文章设置了密码且本次会话未授权，则要求输入密码 ----
    # 作者本人或管理员不受密码限制（可直接预览编辑）
    is_owner = request.user.is_authenticated and (
        request.user == article.author or request.user.is_staff)
    if article.is_protected and not is_owner:
        authorized = request.session.get('authorized_articles', [])
        if pk not in authorized:
            if request.method == 'POST':
                # 密码校验：用 Django check_password 比对哈希
                entered = request.POST.get('article_password', '')
                if entered and check_password(entered, article.password):
                    authorized.append(pk)
                    request.session['authorized_articles'] = authorized
                    request.session.modified = True
                    # 校验通过后继续正常渲染文章
                else:
                    messages.error(request, msg('auth.login_failed'))
                    return render(request, 'blog/password_gate.html',
                                  {'article': article, 'active_nav': 'home'})
            else:
                # GET 直接访问密码文章：显示密码输入页（不增加阅读量）
                return render(request, 'blog/password_gate.html',
                              {'article': article, 'active_nav': 'home'})

    # F() 表达式在数据库层自增，不读入 Python 再写回，避免并发覆盖丢失计数
    Article.objects.filter(pk=pk).update(views=F('views') + 1)
    # 自增后从数据库刷新 views 字段，确保模板拿到最新值
    article.refresh_from_db(fields=['views'])
    # 编辑权限：必须已登录，且是文章作者本人，或是管理员
    can_edit = request.user.is_authenticated and (
        request.user == article.author or request.user.is_staff)
    # QA 辅助（仅 DEBUG 生效）：?as_author=1 时即使当前是管理员，也按「普通作者」
    # 视角渲染详情页操作区，便于对作者申请按钮做浏览器视觉验收。
    # 生产环境（DEBUG=False）该参数完全无效，不影响任何真实权限判定。
    qa_as_author = bool(settings.DEBUG and request.GET.get('as_author') == '1' and can_edit)
    # ------------------------------------------------------------------
    # Bug9-1 / Bug9-2：定时投稿预览提示
    # ------------------------------------------------------------------
    # 作者本人或管理员打开「定时未发布 / 待审核」的文章时，页面顶部给出明确状态条，
    # 说明当前状态、预约时间、剩余时间与到点后的去向，避免"以为已发布"的误解。
    scheduled_notice = None
    if can_edit and article.published_at:
        now_ts = timezone.now()
        if article.published_at > now_ts and article.status in (
                Article.Status.DRAFT, Article.Status.PENDING):
            # 未到点：展示倒计时式的「定时投稿」提示
            scheduled_notice = {
                'kind': 'scheduled',
                'status': article.get_status_display(),
                'at': article.published_at,
                'left': article.published_at - now_ts,
            }
        elif article.status == Article.Status.DRAFT and article.published_at <= now_ts:
            # 已到点但仍是草稿：兜底扫描器会在 30 秒内流转，这里给出解释避免困惑
            scheduled_notice = {
                'kind': 'due',
                'status': article.get_status_display(),
                'at': article.published_at,
                'left': None,
            }
    # ---- 点赞状态：从 session 读取该会话已点赞的文章 id 集合 ----
    # session 中以 'liked_article_ids' 列表存储，判断当前文章是否已赞过
    liked_ids = request.session.get('liked_article_ids', [])
    already_liked = pk in liked_ids
    # ---- 踩状态：从 session 读取该会话已踩的文章 id 集合（D2修复） ----
    disliked_ids = request.session.get('disliked_article_ids', [])
    already_disliked = pk in disliked_ids
    # ---- 收藏状态：查询当前登录用户是否已收藏本文 ----
    # 未登录用户 always 未收藏；已登录用户查 Favorite 表是否存在对应记录
    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(user=request.user, article=article).exists()
    # ---- 上一篇 / 下一篇：共享数据（仅已发布未删除文章），按文章缓存 ----
    # 新文章发布 / 删除会使全站 prev/next 变化：信号 purge_prevnext() 整体清空，
    # 或以 TTL 300s 兜底
    def _build_prev_next():
        prev_article = _base_qs(request).filter(
            Q(created_at__lt=article.created_at) |
            Q(created_at=article.created_at, id__lt=article.id)
        ).order_by('-created_at', '-id').first()
        next_article = _base_qs(request).filter(
            Q(created_at__gt=article.created_at) |
            Q(created_at=article.created_at, id__gt=article.id)
        ).order_by('created_at', 'id').first()
        return prev_article, next_article

    prev_article, next_article = cache_get_or_set(
        keys['prevnext'], _build_prev_next, DETAIL_TTL)
    # ---- 评论树：共享数据（已通过且未删除），按文章缓存 ----
    # 缓存只读对象列表；每用户状态（已赞评论 id 集合）由 session 在模板端处理，
    # 不入缓存；评论新增 / 撤回 / 恢复 / 硬删由信号失效
    # Bug3：返回线程列表 threads（父子同框 / 折叠 / 缩进 1 级）
    comment_threads, _ = cache_get_or_set(
        keys['comment_tree'],
        lambda: _build_comment_tree(article),
        DETAIL_TTL)
    # ---- 当前会话已点赞的评论 id 集合（控制点赞按钮态）----
    liked_comment_ids = request.session.get('liked_comment_ids', [])
    # ---- SEO / Open Graph / 结构化数据 ----
    # 关键词取文章标签名逗号拼接；封面图有则用绝对 URL，无则留空（OG 不输出 image）
    tag_names = ','.join(article.tags.values_list('name', flat=True))
    og_image = (request.build_absolute_uri(article.cover_image.url)
                if article.cover_image else '')
    article_url = request.build_absolute_uri(article.get_absolute_url())
    # 摘要取前 150 字用于 meta description（excerpt 已去 HTML）
    seo_description = (article.excerpt or '')[:150]
    # 构造 Article 类型 JSON-LD（标题/摘要/封面/作者/发布与修改时间/正文页 URL）
    article_jsonld = _safe_jsonld({
        '@context': 'https://schema.org',
        '@type': 'Article',
        'headline': article.title,
        'description': seo_description,
        'image': og_image,
        'author': {'@type': 'Person', 'name': str(article.author)},
        'publisher': {'@type': 'Organization', 'name': settings.SITE_NAME},
        'datePublished': article.created_at.isoformat(),
        'dateModified': article.updated_at.isoformat(),
        'mainEntityOfPage': article_url,
    })
    # 63. 当前登录用户对本文的评分（未评过为 None），供星级组件高亮
    my_rating_obj = (Rating.objects.filter(user=request.user, article=article).first()
                     if request.user.is_authenticated else None)
    my_rating = my_rating_obj.score if my_rating_obj else None
    # ---- 第4轮 C1: 相关文章推荐（共同标签数排序 + 同分类加权，取6篇，排除自身）----
    # 共享数据，按文章缓存，文章写路径由信号失效；
    # 注意叠加 is_deleted=False（published() 仅按状态过滤，软删除文章不参与推荐）
    def _build_related_articles():
        # 工单6：相关推荐图片规则与首页统一（封面→正文首图→纯文字填充，不再用占位图）；
        # 无标签文章按「同分类→全站最新」兜底填满 6 张，避免回退到旧的占位卡片分支。
        from blog.templatetags.blog_extras import body_first_image
        base = (Article.objects.published().filter(is_deleted=False)
                .exclude(pk=article.pk).select_related('author', 'category'))
        _tag_ids = list(article.tags.values_list('id', flat=True))
        picked = []
        if _tag_ids:
            tag_qs = (base.filter(tags__in=_tag_ids)
                      .annotate(common_tags=Count('tags', distinct=True))
                      .order_by('-common_tags', '-created_at'))
            picked = list(tag_qs[:6])
        # 标签命中不足 6 篇：用同分类最新补齐
        if len(picked) < 6 and article.category_id:
            have = {r.pk for r in picked}
            for r in base.filter(category_id=article.category_id).order_by('-created_at'):
                if r.pk not in have:
                    picked.append(r); have.add(r.pk)
                if len(picked) >= 6:
                    break
        # 仍不足：全站最新补齐，保证推荐区不空
        if len(picked) < 6:
            have = {r.pk for r in picked}
            for r in base.order_by('-created_at'):
                if r.pk not in have:
                    picked.append(r); have.add(r.pk)
                if len(picked) >= 6:
                    break
        # 统一计算每张推荐卡缩略图：封面 → 正文首图 → 空（纯文字填充）
        for r in picked:
            thumb = ''
            try:
                if r.cover_image:
                    thumb = r.cover_image.url
            except (ValueError, AttributeError):
                thumb = ''
            if not thumb:
                thumb = body_first_image(r.content or '')
            r.rel_thumb = thumb   # 动态挂载，模板直接取用，避免 N+1 与延迟字段问题
        return picked

    related_articles = cache_get_or_set(keys['related'], _build_related_articles, DETAIL_TTL)

    # ---- 第4轮 C2: 字数统计（中文字符数）与阅读时长（按 400 字/分钟，最少1分钟）----
    _plain = re.sub(r'<[^>]+>', '', article.content or '')
    word_count = len(re.findall(r'[\u4e00-\u9fff]', _plain))
    reading_time = max(1, word_count // 400)

    ctx = {
        'article': article,
        'can_edit': can_edit,
        # QA 辅助标记（仅 DEBUG + ?as_author=1 时为 True）：模板据此强制走「作者申请」
        # 分支渲染，用于自动化视觉验收管理员之外的作者视角；生产环境恒为 False。
        'qa_view_as_author': qa_as_author,
        # Bug9：定时投稿状态提示（仅作者 / 管理员可见；未到点或刚到点但尚未流转时给出）
        'scheduled_notice': scheduled_notice,
        # Bug8：置顶/精华/热门三按钮状态（已生效 / 审核中 / 可申请），
        # 已生效时模板渲染为不可点击的「已经置顶」等按钮
        'promo_state': _promo_block_state(article, request.user) if can_edit else {},
        # 第4轮 C1: 相关文章（QuerySet/list，前端推荐卡片用）
        'related_articles': related_articles,
        # 第4轮 C2: 中文字数与阅读时长（整数）
        'word_count': word_count,
        'reading_time': reading_time,
        # 当前会话是否已对这篇文章点过赞（控制按钮态）
        'already_liked': already_liked,
        'already_disliked': already_disliked,
        # 当前用户是否已收藏本文（控制收藏按钮态）
        'is_favorited': is_favorited,
        # 上一篇 / 下一篇导航
        'prev_article': prev_article,
        'next_article': next_article,
        # Bug3：评论线程列表（每项 {'parent','replies','reply_count'}）；评论总数仍取冗余字段
        'comment_threads': comment_threads,
        'comment_count': article.comment_count,
        # 当前会话已点赞的评论 id 集合，模板据此禁用已赞按钮
        'liked_comment_ids': liked_comment_ids,
        # 最近 10 条修改记录，select_related 预加载编辑人
        'edit_logs': article.edit_logs.select_related('editor')[:10],
        # 相关文章：同分类 + 同标签加权算法，取前 8 篇
        'related': cache_get_or_set(
            keys['related_weighted'],
            lambda: _get_related_articles(article, request, limit=8),
            DETAIL_TTL),
        # 67. 所属系列：若文章属于系列，取该系列全部已发布文章（按序号排序），
        #     供详情页渲染系列目录导航卡片（当前文章高亮）
        'series_articles': (list(article.series.articles.filter(
            status=Article.Status.PUBLISHED).order_by('series_order', 'id'))
            if article.series else []),
        # 63. 当前登录用户对本文的评分（未评过为 None），供星级组件高亮
        'my_rating': my_rating,
        # 22. 本文作者卡片：作者已发布文章数与累计阅读量
        'author_article_count': Article.objects.filter(
            author=article.author, status=Article.Status.PUBLISHED).count(),
        'author_views_total': Article.objects.filter(
            author=article.author, status=Article.Status.PUBLISHED
        ).aggregate(v=Sum('views'))['v'] or 0,
        'active_nav': 'home',
        # ---- SEO / Open Graph ----
        'meta_title': article.title,
        'meta_description': seo_description,
        'meta_keywords': tag_names or settings.SITE_KEYWORDS,
        'og_type': 'article',
        'og_title': article.title,
        'og_description': seo_description,
        'og_url': article_url,
        'og_image': og_image,
        # 文章结构化数据（已安全转义的 JSON-LD）
        'article_jsonld': article_jsonld,
    }
    ctx.update(_sidebar())

    # 调试：DEBUG 下 ?debug_cache=1 时在模板底部输出片段缓存明细与命中统计
    if settings.DEBUG and request.GET.get('debug_cache') == '1':
        from ..utils.cache_keys import get_stats as _cache_stats
        ctx['cache_debug'] = {
            'rows': [
                {'label': label, 'key': key,
                 'cached': cache_get(key) is not None}
                for label, key in (
                    ('article', keys['article']),
                    ('comment_tree', keys['comment_tree']),
                    ('related', keys['related']),
                    ('related_weighted', keys['related_weighted']),
                    ('prevnext', keys['prevnext']),
                )
            ],
            'stats': _cache_stats(),
        }

    response = render(request, 'blog/detail.html', ctx)
    # X-Cache 响应头：报告顶层文章片段是否命中缓存（HIT/MISS）
    response['X-Cache'] = 'HIT' if article_hit else 'MISS'
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
    title = request.POST.get('title', '').strip()
    content = request.POST.get('content', '')
    # 手动摘要：作者可选填写，留空时 excerpt property 自动从正文截取
    excerpt_field = request.POST.get('excerpt_field', '').strip()
    # ---- 安全修复：超长输入截断，避免 MySQL "Data too long" 导致 500 ----
    # title 对应 CharField(max_length=200)，超长直接截断到 200 字符；
    # excerpt_field 为 TextField 无硬长度限制，但前台摘要只展示约 180 字，
    # 这里统一截断到 500 字符，防止恶意超长输入撑大数据库 / 拖慢渲染。
    title = title[:200]
    excerpt_field = excerpt_field[:500]
    # ---- 安全修复：正文 XSS 净化 ----
    # CKEditor 产出的 HTML 可能含 script / iframe / onerror / javascript: 协议等，
    # 模板中用 |safe 渲染，因此入库前必须用 bleach 过滤为安全 HTML。
    content = sanitize_html(content)
    kind = request.POST.get('kind', Article.Kind.ARTICLE)
    status_ = request.POST.get('status', Article.Status.PUBLISHED)
    # 非法 kind 兜底为普通文章，防止前端传脏值
    if kind not in Article.Kind.values:
        kind = Article.Kind.ARTICLE
    # 非法 status 兜底为已发布
    if status_ not in Article.Status.values:
        status_ = Article.Status.PUBLISHED
    # 标题为必填项
    if not title:
        return None, '标题不能为空喵~📝'
    category_id = request.POST.get('category', '').strip()
    category = None
    # 分类 ID 合法时查库，查不到则置空
    if category_id.isdigit():
        category = Category.objects.filter(pk=int(category_id)).first()
    # Bug16: 文章必须归属分类，绕过前端提交空值时后端兜底为第一个分类
    if category is None:
        category = Category.objects.order_by('id').first()
    # 标签名：把中文逗号统一替换为英文逗号后按英文逗号拆分，过滤空串
    # 迭代#136: 标签名长度验证（截断到50字符）
    tag_names = [t.strip()[:50] for t in request.POST.get('tag_names', '').replace(
        '，', ',').split(',') if t.strip()]

    # ---- 56. 定时发布时间：datetime-local 输入形如 "2026-09-22T15:30" ----
    published_at_raw = (request.POST.get('published_at') or '').strip()
    published_at = None
    if published_at_raw:
        try:
            # datetime.fromisoformat 可直接解析 datetime-local 字符串（无时区）
            published_at = datetime.fromisoformat(published_at_raw)
        except ValueError:
            published_at = None
    # 迭代#137: 定时发布时间验证（不能早于当前时间）
    if published_at and published_at < datetime.now():
        published_at = None  # 过去时间无效，降级为立即发布

    # ---- Bug1：置顶 / 精华 / 热门三个标记，checkbox 键存在即为 True ----
    # 是否允许设置由 article_new / article_edit 按角色与新建/编辑再把关，这里只如实解析。
    is_pinned = 'is_pinned' in request.POST
    is_featured = 'is_featured' in request.POST
    is_hot = 'is_hot' in request.POST

    # ---- 58. 访问密码：仅当本次提交了非空密码时才更新（留空不清空原密码）----
    password_raw = (request.POST.get('article_password') or '').strip()
    # 迭代#138: 文章密码长度验证
    if password_raw and len(password_raw) > 100:
        password_raw = password_raw[:100]
    password_hashed = None   # None 表示本次不修改密码字段

    # ---- 67. 所属系列 + 系列序号 ----
    series_id = (request.POST.get('series') or '').strip()
    series_obj = Series.objects.filter(pk=int(series_id)).first() if series_id.isdigit() else None
    series_order_raw = (request.POST.get('series_order') or '0').strip()
    # 迭代#139: 系列序号验证（非负整数）
    series_order = max(0, int(series_order_raw)) if series_order_raw.isdigit() else 0
    # Bug16: 归属系列但序号为 0（新建/新加入系列）时，自动编为系列末尾
    if series_obj is not None and series_order == 0:
        series_order = Article.objects.filter(series=series_obj).count() + 1

    return {
        'title': title, 'content': content, 'excerpt_field': excerpt_field,
        'kind': kind, 'status': status_,
        'category': category, 'tag_names': tag_names,
        'published_at': published_at, 'is_pinned': is_pinned,
        'is_featured': is_featured, 'is_hot': is_hot,
        'password_raw': password_raw, 'password_hashed': password_hashed,
        'series': series_obj, 'series_order': series_order,
    }, None

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
    if request.method == 'POST':
        data, error = _parse_form(request)
        if error:
            messages.error(request, error)
        else:
            # Bug1：写文章页一律不允许设置置顶/精华/热门（默认不置顶），强制 False
            data['is_pinned'] = False
            data['is_featured'] = False
            data['is_hot'] = False
            # Bug1：普通作者是否需审核由审核全局设置决定；管理员可在表单自选状态
            if not request.user.is_staff:
                # Bug12修复：定时投稿（带未来发布时间）一律先存草稿，到点由
                # check_scheduled_articles 自动发布；若先判审核会被置为 PENDING，
                # 而定时任务只发布 DRAFT，将导致定时文章永远无法自动发布。
                if data.get('published_at'):
                    data['status'] = Article.Status.DRAFT  # 定时发布先存草稿
                elif ModerationSettings.load().require_article_review:
                    data['status'] = Article.Status.PENDING
                else:
                    data['status'] = Article.Status.PUBLISHED
            # 从 data 中剔除非模型字段（tag_names / password_raw），
            # 其余字段直接解包传给 create()；作者固定为当前登录用户
            model_fields = {'title', 'content', 'excerpt_field', 'kind', 'status',
                            'category', 'published_at', 'is_pinned',
                            'is_featured', 'is_hot',
                            'series', 'series_order'}
            # 迭代#143: 文章标题长度验证
            # 迭代#144: 文章正文长度验证
            # 迭代#145: 文章kind合法性验证
            # 迭代#146: 文章status合法性验证
            # 迭代#147: article_new中文章创建异常处理
            # 迭代#148: 文章创建成功日志
            # 迭代#149: 文章创建失败日志
            try:
                article = Article.objects.create(
                    author=request.user,
                    **{k: v for k, v in data.items() if k in model_fields})
                logger.info('文章创建成功: id=%s title=%s author=%s',
                            article.pk, article.title, request.user.username)
            except DatabaseError as db_exc:
                logger.error('文章创建失败: %s', db_exc)
                messages.error(request, msg('article.save_failed'))
                return redirect('index')
            # 58. 设置访问密码（哈希存储，不明文）。工单5：原先无封面时
            # 设置密码后缺少 save()，密码丢失导致游客可无密码访问；统一标记落库。
            need_save = False
            if data['password_raw']:
                article.password = make_password(data['password_raw'])
                need_save = True
            # 处理封面图上传：表单 enctype=multipart/form-data 后，
            # 上传文件在 request.FILES 中；存在则赋值给 cover_image
            cover = request.FILES.get('cover_image')
            if cover:
                article.cover_image = cover
                need_save = True
            # 密码 / 封面任一存在都需要把改动持久化（修复密码丢失）
            if need_save:
                article.save()
            # 57. 置顶数量校验：上限取自审核全局设置（默认 3），
            #     超出则取消本次置顶（只统计未软删除的文章，与 _promo_execute 口径一致）
            _max_pinned_new = ModerationSettings.load().max_pinned
            if article.is_pinned and Article.objects.filter(
                    is_pinned=True, is_deleted=False).exclude(pk=article.pk).count() >= _max_pinned_new:
                article.is_pinned = False
                article.save(update_fields=['is_pinned'])
                messages.warning(request, msg('promo.limit_cancel', _max_pinned_new))
            # 设置多对多标签：get_or_create 自动创建不存在的标签名，
            # set() 全量替换关联（新建时即初次设置）
            if data['tag_names']:
                article.tags.set(
                    [Tag.objects.get_or_create(name=n)[0] for n in set(data['tag_names'])])
            # 记录一条修改日志（新建也算一次编辑）
            EditLog.objects.create(article=article, editor=request.user)
            # 文章变更：清除侧边栏 / 页脚统计 / 侧边栏统计缓存
            cache.delete(SIDEBAR_CACHE_KEY)
            cache.delete('footer_stats')
            cache.delete('sidebar_stats')
            # bug8: 待审核文章记录提交日志并提示等待；其余即时发布
            if article.status == Article.Status.PENDING:
                ModerationLog.objects.create(
                    moderator=request.user, moderator_name=str(request.user),
                    action=ModerationLog.Action.SUBMIT, target_type='article',
                    article=article, target_title=article.title)
                messages.success(request, msg('article.submitted_review'))
            else:
                messages.success(request, msg('article.published'))
            return redirect(article)
    # GET：渲染空表单，categories / tags 供下拉选择，preset_kind 预设类型
    ctx = {'categories': Category.objects.all(), 'tags': Tag.objects.all(),
           'series_list': Series.objects.filter(author=request.user),
           'is_new': True, 'preset_kind': request.GET.get('kind', Article.Kind.ARTICLE),
           'active_nav': 'edit'}
    return render(request, 'blog/edit.html', ctx)

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
    article = get_object_or_404(Article, pk=pk)
    # 权限拦截：非作者且非管理员，直接拒绝并提示
    if request.user != article.author and not request.user.is_staff:
        messages.error(request, msg('err.only_own_article'))
        return redirect(article)
    if request.method == 'POST':
        data, error = _parse_form(request, article)
        if error:
            messages.error(request, error)
        else:
            # bug8: 非管理员不能改变发布状态（表单也不展示该选项），沿用原状态，
            # 防止缺省值把待审核文章误判为发布
            if not request.user.is_staff:
                data['status'] = article.status
                # Bug1：普通作者不能通过编辑表单直接改置顶/精华/热门（走申请流程）
                data['is_pinned'] = article.is_pinned
                data['is_featured'] = article.is_featured
                data['is_hot'] = article.is_hot
            # 55. 版本历史：在写入新内容之前，把"修改前"的完整正文存入 EditLog 快照。
            #     注意此时 article.content 仍是旧值，先暂存再覆盖。
            old_content = article.content
            # 取出标签名单独处理，剩余字段逐个赋值到 article 对象
            tag_names = data.pop('tag_names')
            # 58. 密码：仅当本次提交了非空密码时才用 make_password 重新哈希
            password_raw = data.pop('password_raw')
            data.pop('password_hashed')  # 占位键，不写入模型
            model_fields = {'title', 'content', 'excerpt_field', 'kind', 'status',
                            'category', 'published_at', 'is_pinned',
                            'is_featured', 'is_hot',
                            'series', 'series_order'}
            for attr, value in data.items():
                if attr in model_fields:
                    setattr(article, attr, value)
            # 58. 设置访问密码（哈希存储）
            if password_raw:
                article.password = make_password(password_raw)
            # 处理封面图上传：若用户新选了文件则覆盖旧封面
            cover = request.FILES.get('cover_image')
            if cover:
                article.cover_image = cover
            article.save()
            # Bug1：置顶上限取自审核全局设置，超出则取消本篇置顶并提示
            _max_pinned = ModerationSettings.load().max_pinned
            if article.is_pinned and Article.objects.filter(
                    is_pinned=True, is_deleted=False).exclude(pk=article.pk).count() >= _max_pinned:
                article.is_pinned = False
                article.save(update_fields=['is_pinned'])
                messages.warning(request, msg('promo.limit_cancel', _max_pinned))
            # 全量替换标签关联（get_or_create 自动补建新标签）
            article.tags.set(
                [Tag.objects.get_or_create(name=n)[0] for n in set(tag_names)])
            # 记录修改日志，并带上修改前内容快照（55. 版本历史查看/对比）
            EditLog.objects.create(
                article=article, editor=request.user, content_snapshot=old_content)
            # 文章变更：清除侧边栏 / 页脚统计 / 侧边栏统计缓存
            cache.delete(SIDEBAR_CACHE_KEY)
            cache.delete('footer_stats')
            cache.delete('sidebar_stats')
            messages.success(request, msg('article.saved'))
            return redirect(article)
    # GET：回填现有文章数据，is_new=False 表示编辑模式
    # 56. datetime-local 需要 "YYYY-MM-DDTHH:MM" 格式的值回填
    published_at_value = (
        article.published_at.strftime('%Y-%m-%dT%H:%M') if article.published_at else '')
    ctx = {'article': article, 'categories': Category.objects.all(),
           'tags': Tag.objects.all(), 'series_list': Series.objects.filter(author=request.user),
           'published_at_value': published_at_value,
           'is_new': False, 'preset_kind': article.kind, 'active_nav': 'edit'}
    return render(request, 'blog/edit.html', ctx)

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
    article = get_object_or_404(Article, pk=pk)
    if request.user != article.author and not request.user.is_staff:
        messages.error(request, msg('err.permission_denied'))
        return redirect(article)
    # 仅响应 POST：GET 访问到此 URL 不做任何操作，避免 CSRF / 误点误删
    if request.method == 'POST':
        # bug8: 改为软删除（对前台隐藏、可在回收站恢复），不再物理删除
        article.is_deleted = True
        article.deleted_at = timezone.now()
        article.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
        ModerationLog.objects.create(
            moderator=request.user, moderator_name=str(request.user),
            action=ModerationLog.Action.SOFT_DELETE, target_type='article',
            article=article, target_title=article.title)
        # 文章删除：清除侧边栏 / 页脚统计 / 侧边栏统计缓存
        cache.delete(SIDEBAR_CACHE_KEY)
        cache.delete('footer_stats')
        cache.delete('sidebar_stats')
        messages.success(request, msg('article.trashed'))
    return redirect('index')

# ----------------------------- 随机文章（Random Article） -----------------------------
def random_article(request):
    """随机跳转到一篇已发布的文章喵。"""
    from ..models import Article
    import random
    articles = Article.objects.filter(status='published')
    if not articles.exists():
        from django.shortcuts import redirect
        return redirect('home')
    article = random.choice(articles)
    from django.shortcuts import redirect
    return redirect(article.get_absolute_url())

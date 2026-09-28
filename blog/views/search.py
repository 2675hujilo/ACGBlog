# -*- coding: utf-8 -*-

"""搜索域：搜索页、自动补全、热词与拼音支持。"""

import logging

from django.core.cache import cache
from django.db.models import Avg, Count, F, Min, Q, Sum
from django.http import (
    HttpRequest, HttpResponse,
    JsonResponse, )

from .articles import index
from .common import SEARCH_Q_MAX_LENGTH, _json_ok
from ..models import (
    Article, )

logger = logging.getLogger('blog.views')

def _search_results_cached(q, timeout=120):
    # 第2轮迭代#69: 搜索结果缓存——关键词结果按 hash 做 key 短 TTL 缓存
    key = f'search_{hash(q) & 0xffffffff}'
    return cache.get_or_set(key, lambda: list(
        Article.objects.filter(status=Article.Status.PUBLISHED)
        .filter(Q(title__icontains=q) | Q(content__icontains=q))[:20]), timeout)

# 迭代#163: search视图docstring
# 迭代#164: search(request) -> HttpResponse 类型提示
def search(request: HttpRequest) -> HttpResponse:
    """全局搜索页：直接复用首页视图（关键词 q 由 ``_filter_articles`` 统一处理）。

    之所以不单独实现，是因为首页的筛选逻辑已经包含了对 ``?q=`` 参数的支持，
    搜索页只需原样转发请求即可，避免重复代码。

    Args:
        request: 当前 HttpRequest 对象。

    Returns:
        HttpResponse: 渲染后的搜索结果列表 HTML。
    """
    return index(request)

# 迭代#165: search_suggest视图docstring
# 迭代#166: search_suggest(request) -> JsonResponse 类型提示
def search_suggest(request: HttpRequest) -> JsonResponse:
    """搜索自动补全接口：GET /api/search/suggest/?q=关键词。

    输入时前端 debounce 300ms 后调用，返回匹配的已发布文章标题（最多 8 条）。
    - 仅匹配已发布文章的标题；
    - 关键词为空 / 过短时返回空列表，避免一次吐出全站标题；
    - 统一返回 ``{"suggestions": [...]}`` JSON。

    Args:
        request: 当前 HttpRequest，读取 GET 参数 ``q``。

    Returns:
        JsonResponse: ``{"suggestions": [标题1, 标题2, ...]}``。
    """
    q = (request.GET.get('q') or '').strip()
    # 迭代#167: 搜索关键词长度验证
    q = q[:SEARCH_Q_MAX_LENGTH]
    # 第5轮 D系列: 拼音搜索建议（limit 10）+ 记录热词
    suggestions = []
    if q:
        suggestions = _enhanced_search_suggest(q)
        _record_search_keyword(q)
    return JsonResponse({'suggestions': suggestions})

SEARCH_HOT_KEY = 'search_history'   # 热门搜索词缓存 key

SEARCH_HOT_TTL = 86400              # 热门搜索词缓存 TTL（秒）

# ----------------------------- 6. 搜索热词（D 系列） -----------------------------
def api_search_hot(request: HttpRequest) -> JsonResponse:
    """热门搜索词：GET /api/search/hot/，返回缓存 TOP10。"""
    history = cache.get(SEARCH_HOT_KEY, {})
    if isinstance(history, dict):
        ranked = sorted(history.items(), key=lambda kv: kv[1], reverse=True)
    else:
        ranked = []
    return _json_ok([{'keyword': k, 'count': v} for k, v in ranked[:10]])

def _record_search_keyword(q: str) -> None:
    """把搜索关键词累加进热门词缓存（失败静默，不影响搜索主流程）。"""
    q = (q or '').strip()
    if not q:
        return
    try:
        history = cache.get(SEARCH_HOT_KEY, {}) or {}
        history[q] = int(history.get(q, 0)) + 1
        cache.set(SEARCH_HOT_KEY, history, SEARCH_HOT_TTL)
    except Exception:  # noqa: BLE001
        pass

def _pinyin_keywords(q: str) -> list:
    """把中文关键词转为拼音（含首字母），用于拼音搜索建议。

    Args:
        q: 原始关键词。

    Returns:
        list: 拼音候选列表（无法导入 pypinyin 时返回空列表）。
    """
    try:
        from pypinyin import lazy_pinyin
    except ImportError:
        return []
    parts = lazy_pinyin(q)
    return [''.join(parts)]

# ----------------------------- 搜索建议增强（拼音 + 热词记录） -----------------------------
def _enhanced_search_suggest(q: str) -> list:
    """带拼音支持的标题搜索建议（limit 10）。

    Args:
        q: 原始关键词。

    Returns:
        list: 标题列表。
    """
    q = (q or '').strip()[:SEARCH_Q_MAX_LENGTH]
    if not q:
        return []
    base = Article.objects.filter(status=Article.Status.PUBLISHED)
    qs = base.filter(Q(title__icontains=q)).order_by('-views')
    # 拼音首字母/全拼补充
    for py in _pinyin_keywords(q):
        if py:
            qs = qs | base.filter(title__icontains=py)
    return list(qs.distinct().order_by('-views').values_list('title', flat=True)[:10])

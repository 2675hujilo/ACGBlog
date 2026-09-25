"""
详情页缓存 key 规范、版本号与失效工具（统一入口）。

- 版本号：文件驱动（``blog/cache_version.txt``，缺失时回退 ``v1``），与
  ``static/assets/.build_token`` 同模式：进程内读一次并缓存；``manage.py
  cache_bump`` 写入新版本后，**重启 runserver / worker** 使新前缀生效，
  旧 key 由 TTL 自动过期清理（不逐条删除）。
- 所有详情页 key 均带 ``{版本}:`` 前缀，bump 版本即整体失效，方便开发调试。
- 命中统计仅进程内累积，供 DEBUG 端点 ``/__debug_cache/`` 与 diag 查看。
- 缓存只放「所有用户可见且一致」的共享数据；每用户态（收藏 / 评分 / 点赞 /
  可编辑）与阅读量自增不入缓存，仍在视图实时处理。
"""
import os

from django.conf import settings
from django.core.cache import cache

# 版本文件：与 .build_token 同样的「文件驱动 + 进程内缓存」模式
CACHE_VERSION_FILE = os.path.join(settings.BASE_DIR, 'blog', 'cache_version.txt')
CACHE_VERSION_FALLBACK = 'v1'

# 详情页片段缓存有效期（与侧边栏一致，5 分钟）
DETAIL_TTL = 300
# 404 墓碑有效期（防恶意 id 穿透）
MISSING_TTL = 60

_version = None
_stats = {}


def get_cache_version():
    """返回当前缓存版本号（进程内只读一次，重启后自动取到文件最新值）。"""
    global _version
    if _version is None:
        try:
            with open(CACHE_VERSION_FILE, 'r', encoding='utf-8') as f:
                _version = f.read().strip() or CACHE_VERSION_FALLBACK
        except OSError:
            _version = CACHE_VERSION_FALLBACK
    return _version


def detail_keys(article_id):
    """返回某篇文章详情页的全部缓存 key（带版本前缀）。"""
    v = get_cache_version()
    return {
        'article': f'{v}:article:{article_id}',
        'comment_tree': f'{v}:comment_tree:{article_id}',
        'related': f'{v}:related:{article_id}',
        'related_weighted': f'{v}:rel_weighted:{article_id}',
        'prevnext': f'{v}:prevnext:{article_id}',
        'missing': f'{v}:missing:{article_id}',
    }


def cache_get(key, default=None):
    """读取缓存并记录命中 / 未命中（进程内统计，供调试端点查看）。"""
    _stats.setdefault(key, {'hits': 0, 'misses': 0})
    value = cache.get(key)
    if value is None:
        _stats[key]['misses'] += 1
        return default
    _stats[key]['hits'] += 1
    return value


def cache_set(key, value, timeout=DETAIL_TTL):
    """写入缓存（默认 5 分钟，与侧边栏一致）。"""
    cache.set(key, value, timeout)


def cache_get_or_set(key, default, timeout=DETAIL_TTL):
    """get_or_set 语义 + 命中统计；default 可为可调用对象。"""
    value = cache_get(key)
    if value is not None:
        return value
    value = default() if callable(default) else default
    cache_set(key, value, timeout)
    return value


def invalidate_article(article_id):
    """文章 / 评论写路径统一失效入口：删除该文章全部详情缓存片段。

    所有文章 / 评论写路径（含信号）都收敛到这里，减少漏删面。
    """
    for key in detail_keys(article_id).values():
        cache.delete(key)


def purge_prevnext():
    """新建 / 删除文章后，全站文章的「上一篇 / 下一篇」都可能变化，整体清空。

    仅支持进程内可遍历的缓存后端（LocMemCache）；Redis / DB 等后端无法按前缀
    枚举时安全跳过，由 TTL 300s 兜底。
    """
    internal = getattr(cache, '_cache', None)
    if not isinstance(internal, dict):
        return
    for key in list(internal.keys()):
        if ':prevnext:' in key:
            cache.delete(key)


def get_stats():
    """返回进程内命中统计快照（供 DEBUG 端点 / diag 使用）。"""
    return dict(_stats)


def reset_stats():
    """清空进程内命中统计。"""
    _stats.clear()

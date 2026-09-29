# -*- coding: utf-8 -*-
"""看板娘形象注册表服务。

职责
----
维护 ``static/assets/live2d/models_registry.json`` 这份「形象总表」，为两处提供数据：

1. **后台管理页**（``/console/live2d-models/``）—— 展示全部形象的缩略图与启用开关；
2. **前台看板娘** —— 通过上下文处理器注入 ``window.LIVE2D_MODELS``，
   只包含 ``enabled=True`` 的形象，前端据此构建切换列表。

为什么用 JSON 文件而不是数据库表
--------------------------------
形象清单是**随静态素材一起分发**的展示配置（与 thumbs/ 缩略图、模型目录同源），
新增一套模型只需投放文件 + 重新生成注册表，无需数据库迁移；
同时它天然可入库随部署走，避免"数据库有配置、磁盘没素材"的错位。

并发与可靠性
------------
- 读：进程内按文件 ``mtime`` 缓存，避免每次请求都读盘；
- 写：**原子写**（临时文件 + ``os.replace``），避免半截 JSON；
- 写后失效缓存，下一次请求即读到新状态；任何异常都降级为「沿用旧值」，
  绝不因注册表问题阻断页面渲染。
"""
import json
import logging
import os
import threading
import time

from django.conf import settings

logger = logging.getLogger(__name__)

# 注册表文件位置（与 live2d 静态素材同级）
REGISTRY_PATH = os.path.join(settings.BASE_DIR, 'static', 'assets', 'live2d',
                             'models_registry.json')

# 进程内缓存：{'stamp': mtime, 'data': dict}
_CACHE = {'stamp': None, 'data': None}
_LOCK = threading.Lock()

# 注入前端时只保留真正需要的字段，控制页面体积
_FRONT_FIELDS = ('id', 'name', 'path', 'skins', 'type')


def _empty():
    return {'version': 1, 'total': 0, 'models': []}


def load(force=False):
    """读取注册表（带 mtime 缓存）。

    Returns:
        dict: ``{'version', 'updated', 'total', 'models': [...]}``；
        文件缺失或损坏时返回空表，绝不抛异常。
    """
    try:
        stamp = os.path.getmtime(REGISTRY_PATH)
    except OSError:
        return _empty()
    if not force and _CACHE['data'] is not None and _CACHE['stamp'] == stamp:
        return _CACHE['data']
    try:
        with open(REGISTRY_PATH, encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict) or 'models' not in data:
            raise ValueError('注册表结构不正确')
        data['models'] = [m for m in data['models'] if isinstance(m, dict) and m.get('id')]
    except Exception as exc:  # noqa: BLE001 注册表异常不得阻断页面
        logger.warning('[live2d] 注册表读取失败，降级为空表: %s', exc)
        return _empty()
    _CACHE['stamp'] = stamp
    _CACHE['data'] = data
    return data


def models(enabled_only=False, group=None):
    """返回形象列表（可按启用状态 / 分组过滤）。"""
    items = load().get('models', [])
    if enabled_only:
        items = [m for m in items if m.get('enabled', True)]
    if group:
        items = [m for m in items if m.get('group') == group]
    return items


def front_payload():
    """返回注入前端的最小字段列表（仅启用项）。

    前端用它构建 ``MODEL_CONFIG``，因此只保留必要字段以控制页面体积。
    """
    out = []
    for m in models(enabled_only=True):
        item = {k: m.get(k) for k in _FRONT_FIELDS if m.get(k) is not None}
        item['skins'] = int(m.get('skins') or 1)
        out.append(item)
    return out


def stats():
    """统计信息，供后台页展示。"""
    items = load().get('models', [])
    enabled = [m for m in items if m.get('enabled', True)]
    return {
        'total': len(items),
        'enabled': len(enabled),
        'disabled': len(items) - len(enabled),
        'builtin': len([m for m in items if m.get('group') == 'builtin']),
        'gfl': len([m for m in items if m.get('group') == 'gfl']),
        'updated': load().get('updated', ''),
    }


def _save(data):
    """原子写入注册表并失效缓存。"""
    data['total'] = len(data.get('models', []))
    data['updated'] = time.strftime('%Y-%m-%d %H:%M:%S')
    tmp = REGISTRY_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, REGISTRY_PATH)
    with _LOCK:
        _CACHE['stamp'] = None
        _CACHE['data'] = None
    load(force=True)


def set_enabled(model_id, enabled):
    """切换单个形象的启用状态。

    Returns:
        tuple(bool, str): ``(是否成功, 说明或错误)``
    """
    data = load(force=True)
    hit = None
    for m in data.get('models', []):
        if m.get('id') == model_id:
            m['enabled'] = bool(enabled)
            hit = m
            break
    if hit is None:
        return False, '形象不存在：%s' % model_id
    _save(data)
    return True, '%s 已%s' % (hit.get('name') or model_id, '开启' if enabled else '关闭')


def set_many(enabled, group=None):
    """批量启用 / 停用（可按分组限定）。

    Returns:
        tuple(int, str): ``(受影响数量, 说明)``
    """
    data = load(force=True)
    n = 0
    for m in data.get('models', []):
        if group and m.get('group') != group:
            continue
        if m.get('enabled', True) != bool(enabled):
            m['enabled'] = bool(enabled)
            n += 1
    if n:
        _save(data)
    scope = {'gfl': '少女前线组', 'builtin': '内置组'}.get(group, '全部形象')
    return n, '%s：%d 款已%s' % (scope, n, '开启' if enabled else '关闭')

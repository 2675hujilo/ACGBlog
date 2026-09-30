# -*- coding: utf-8 -*-
"""Live2D 看板娘 API（原 ``blog/features_live2d.py``，Bug9 任务「3」规范化重命名）。

接口规范参考 fghrsh/live2d_api，提供模型列表 / 取模型 / 切换模型 / 切换皮肤 /
随机切换 / 猜拳小游戏等真实可用端点，供前端 ``waifu-init-new.js`` 调用。

命名说明
--------
原文件名以 ``features_`` 开头，是历史批量生成功能的遗留前缀；本模块是**真实业务
模块**，按「功能域命名」规范改名为 ``blog/live2d.py``。需求要求「最终结果不保留
feature/round 开头的文件」，本模块即整改结果之一。

与 ``blog/site_messages.py`` 的区别
-----------------------------------
本模块内的 ``TALKS`` 是**看板娘角色的台词库**（同一动作多种随机说法，属角色内容），
与全站通用提示词注册表 ``site_messages.MESSAGES`` 用途不同，故保留在本模块内，
仅改名以避免与全局 MESSAGES 混淆。
"""
import json
import os
import random

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# Bug9 任务2：用户可见提示统一取自 blog/site_messages.py
from .services.site_messages import msg

# 模型配置：统一从 models_registry.json 动态读取（与后台管理页 / 前端共享同一数据源）。
# 原 MODELS 硬编码列表已弃用，改为进程内缓存 + 文件 mtime 检测，零数据库依赖。
import threading as _threading
from pathlib import Path as _Path

_REG_PATH = str(_Path(__file__).resolve().parent.parent / 'static' / 'assets' / 'live2d' / 'models_registry.json')
_reg_cache = {'stamp': None, 'models': []}
_reg_lock = _threading.Lock()


def _load_registry():
    """从 models_registry.json 加载 enabled=True 的模型（带 mtime 缓存）。"""
    global _reg_cache
    try:
        stamp = os.path.getmtime(_REG_PATH)
    except OSError:
        return _reg_cache.get('models', [])
    if _reg_cache.get('stamp') == stamp and _reg_cache['models']:
        return _reg_cache['models']
    try:
        with open(_REG_PATH, encoding='utf-8') as f:
            data = json.load(f)
        models_raw = [m for m in data.get('models', [])
                      if isinstance(m, dict) and m.get('enabled', True)]
        with _reg_lock:
            _reg_cache['stamp'] = stamp
            _reg_cache['models'] = models_raw
    except Exception:
        return _reg_cache.get('models', [])
    return _reg_cache['models']


def _registry_as_mode_list():
    """把 registry 的 dict 列表转为兼容旧 API 的模型配置列表。"""
    reg = _load_registry()
    out = []
    for m in reg:
        out.append({
            'id': m.get('id', ''),
            'name': m.get('name', ''),
            'model_path': m.get('path', ''),
            'texture_dir': '',
            'texture_prefix': 'texture_',
            'skin_count': int(m.get('skins', 1) or 1),
            'group': {'builtin': 1, 'gfl': 2}.get(m.get('group', 'builtin'), 1),
            'type': m.get('type', 'cubism2'),
        })
    return out


# 兼容性常量：已注册的模型组（仅用于回退 / 日志，不再作为主数据源）
MODELS = [
    {'id': 'shizuku', 'name': '雫', 'model_path': '/static/assets/live2d/models/shizuku/shizuku.model.json',
     'texture_dir': 'assets/live2d/models/shizuku/moc/shizuku.1024', 'texture_prefix': 'texture_',
     'skin_count': 6, 'group': 1},
    {'id': 'koharu', 'name': '小春', 'model_path': '/static/assets/live2d/models/koharu/koharu.model.json',
     'texture_dir': 'assets/live2d/models/koharu/moc/koharu.2048', 'texture_prefix': 'texture_',
     'skin_count': 1, 'group': 1},
    {'id': 'haru', 'name': '春', 'model_path': '/static/assets/live2d/models/haru/haru01.model.json',
     'texture_dir': 'assets/live2d/models/haru/moc/haru01.1024', 'texture_prefix': 'texture_',
     'skin_count': 3, 'group': 1},
]

# 看板娘台词库：每个动作随机挑选一句，保持角色活泼口语化的二次元语气
TALKS = {
    'switch_model': ['换好新衣服啦~好看吗？', '嘿嘿~新造型怎么样？', '人家换了个样子，还认得出来吗？'],
    'switch_skin': ['新衣服好看吗喵~', '人家换了套衣服呢~', '这个颜色也很可爱吧？'],
    'rand_model': ['随机到了新角色喵~', '猜猜这次是谁？', '惊喜！换了个新朋友~'],
    'rand_skin': ['随机到了新皮肤喵~', '今天穿这套吧~', '惊喜！新衣服~']
}


def get_model_by_id(model_id):
    """根据模型ID获取模型配置（优先 registry，回退到硬编码 MODELS）。"""
    for m in _registry_as_mode_list():
        if m['id'] == model_id:
            return m
    for m in MODELS:
        if m['id'] == model_id:
            return m
    return MODELS[0]


def get_model_index(model_id):
    """获取模型在列表中的索引（优先 registry，回退到硬编码 MODELS）。"""
    active = _registry_as_mode_list()
    for i, m in enumerate(active):
        if m['id'] == model_id:
            return i
    for i, m in enumerate(MODELS):
        if m['id'] == model_id:
            return i
    return 0


@require_http_methods(["GET"])
def model_list(request):
    """获取模型列表（优先从 registry.json 读取，fallback 到硬编码 MODELS）。"""
    active = _registry_as_mode_list() or MODELS
    result = {
        'models': [
            {'id': m['id'], 'name': m['name'], 'skin_count': m['skin_count'],
             'model_path': m['model_path']}
            for m in active
        ],
        'total': len(active)
    }
    return JsonResponse(result)


@require_http_methods(["GET"])
def get_model(request, model=None, skin=None):
    """
    获取指定模型和皮肤的配置
    支持两种调用方式：
    1. /api/live2d/get/?model=xxx&skin=N （查询参数）
    2. /api/live2d/model/xxx/N.json （URL路径）
    返回动态生成的模型JSON（textures字段已替换为指定皮肤）
    """
    model_id = model or request.GET.get('model', 'shizuku')
    skin_idx = skin if skin is not None else request.GET.get('skin', '0')

    try:
        skin_idx = int(skin_idx)
    except (ValueError, TypeError):
        skin_idx = 0

    model = get_model_by_id(model_id)
    skin_idx = max(0, min(skin_idx, model['skin_count'] - 1))

    # 模型所在目录的静态URL前缀（从 model_path 推导，兼容内置/少女前线等多组目录）
    model_dir_url = '/'.join(model['model_path'].split('/')[:-1]) + '/'

    # 读取原始模型JSON
    model_json_path = model['model_path'].replace('/static/', '')
    json_path = os.path.join('static', model_json_path)

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            model_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return JsonResponse({'error': msg('live2d.model_missing')}, status=404)

    # 将所有相对路径转换为绝对路径
    def to_abs(rel_path):
        if rel_path and not rel_path.startswith('/') and not rel_path.startswith('http'):
            return model_dir_url + rel_path
        return rel_path

    if 'model' in model_data:
        model_data['model'] = to_abs(model_data['model'])
    if 'physics' in model_data:
        model_data['physics'] = to_abs(model_data['physics'])
    if 'pose' in model_data:
        model_data['pose'] = to_abs(model_data['pose'])
    if 'expressions' in model_data:
        for exp in model_data['expressions']:
            if 'file' in exp:
                exp['file'] = to_abs(exp['file'])
    if 'motions' in model_data:
        for motion_list in model_data['motions'].values():
            for motion in motion_list:
                if 'file' in motion:
                    motion['file'] = to_abs(motion['file'])
                if 'sound' in motion:
                    motion['sound'] = to_abs(motion['sound'])

    # 替换textures为指定皮肤
    texture_url = f"/static/{model['texture_dir']}/{model['texture_prefix']}{skin_idx:02d}.png"
    model_data['textures'] = [texture_url]

    response = HttpResponse(json.dumps(model_data, ensure_ascii=False), content_type='application/json')
    response['Cache-Control'] = 'no-cache'
    return response


@require_http_methods(["GET"])
def switch_model(request):
    """
    顺序切换模型
    参数：current=当前模型ID
    返回：下一个模型的信息和动态模型JSON URL
    """
    current_id = request.GET.get('current', 'shizuku')
    current_idx = get_model_index(current_id)
    next_idx = (current_idx + 1) % len(MODELS)
    next_model = MODELS[next_idx]

    # 返回动态模型URL（皮肤0）
    model_url = f'/api/live2d/model/{next_model["id"]}/0.json'

    return JsonResponse({
        'model_id': next_model['id'],
        'model_name': next_model['name'],
        'skin': 0,
        'skin_count': next_model['skin_count'],
        'model_url': model_url,
        'message': random.choice(TALKS['switch_model'])
    })


@require_http_methods(["GET"])
def rand_model(request):
    """
    随机切换模型
    参数：current=当前模型ID
    返回：随机模型的信息和动态模型JSON URL
    """
    current_id = request.GET.get('current', 'shizuku')

    # 随机选择一个不同的模型
    available = [m for m in MODELS if m['id'] != current_id]
    if not available:
        available = MODELS
    next_model = random.choice(available)

    model_url = f'/api/live2d/model/{next_model["id"]}/0.json'

    return JsonResponse({
        'model_id': next_model['id'],
        'model_name': next_model['name'],
        'skin': 0,
        'skin_count': next_model['skin_count'],
        'model_url': model_url,
        'message': random.choice(TALKS['rand_model'])
    })


@require_http_methods(["GET"])
def switch_skin(request):
    """
    顺序切换皮肤（在当前模型内）
    参数：model=当前模型ID, current=当前皮肤索引
    返回：下一个皮肤的信息和动态模型JSON URL
    """
    model_id = request.GET.get('model', 'shizuku')
    current_skin = request.GET.get('current', '0')

    try:
        current_skin = int(current_skin)
    except (ValueError, TypeError):
        current_skin = 0

    model = get_model_by_id(model_id)
    next_skin = (current_skin + 1) % model['skin_count']

    model_url = f'/api/live2d/model/{model_id}/{next_skin}.json'

    return JsonResponse({
        'model_id': model_id,
        'model_name': model['name'],
        'skin': next_skin,
        'skin_count': model['skin_count'],
        'model_url': model_url,
        'message': random.choice(TALKS['switch_skin'])
    })


@require_http_methods(["GET"])
def rand_skin(request):
    """
    随机切换皮肤（在当前模型内）
    参数：model=当前模型ID, current=当前皮肤索引
    返回：随机皮肤的信息和动态模型JSON URL
    """
    model_id = request.GET.get('model', 'shizuku')
    current_skin = request.GET.get('current', '0')

    try:
        current_skin = int(current_skin)
    except (ValueError, TypeError):
        current_skin = 0

    model = get_model_by_id(model_id)

    # 随机选择一个不同的皮肤
    available = [i for i in range(model['skin_count']) if i != current_skin]
    if not available:
        available = [current_skin]
    next_skin = random.choice(available)

    model_url = f'/api/live2d/model/{model_id}/{next_skin}.json'

    return JsonResponse({
        'model_id': model_id,
        'model_name': model['name'],
        'skin': next_skin,
        'skin_count': model['skin_count'],
        'model_url': model_url,
        'message': random.choice(TALKS['rand_skin'])
    })


@csrf_exempt
@require_http_methods(["POST"])
def game_play(request):
    """
    看板娘小游戏：猜拳
    参数：choice=石头/剪刀/布
    返回：游戏结果
    """
    try:
        data = json.loads(request.body)
        user_choice = data.get('choice', '').strip()
    except (json.JSONDecodeError, AttributeError):
        user_choice = request.POST.get('choice', '').strip()

    choices = ['石头', '剪刀', '布']
    if user_choice not in choices:
        return JsonResponse({'error': msg('live2d.bad_choice')}, status=400)

    waifu_choice = random.choice(choices)

    # 判断胜负
    if user_choice == waifu_choice:
        result = '平局'
        message = '哎呀，平局了~再来一局喵！'
    elif (user_choice == '石头' and waifu_choice == '剪刀') or \
            (user_choice == '剪刀' and waifu_choice == '布') or \
            (user_choice == '布' and waifu_choice == '石头'):
        result = '胜利'
        message = '你赢了喵~好厉害！'
    else:
        result = '失败'
        message = '嘿嘿，人家赢了~再来一局吗？'

    return JsonResponse({
        'user_choice': user_choice,
        'waifu_choice': waifu_choice,
        'result': result,
        'message': message
    })

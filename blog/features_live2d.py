# -*- coding: utf-8 -*-
"""
Live2D 看板娘 API
参考 fghrsh/live2d_api 接口规范
提供模型切换、皮肤切换、随机切换等功能
"""
import json
import os
import random
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

# 模型配置：分组 -> 模型列表
# 每个模型包含：id, name, model_json路径, 皮肤目录, 皮肤数量
MODELS = [
    {
        'id': 'shizuku',
        'name': '雫',
        'model_path': '/static/assets/live2d/models/shizuku/shizuku.model.json',
        'texture_dir': 'assets/live2d/models/shizuku/moc/shizuku.1024',
        'texture_prefix': 'texture_',
        'skin_count': 6,
        'group': 1
    },
    {
        'id': 'koharu',
        'name': '小春',
        'model_path': '/static/assets/live2d/models/koharu/koharu.model.json',
        'texture_dir': 'assets/live2d/models/koharu/moc/koharu.2048',
        'texture_prefix': 'texture_',
        'skin_count': 1,
        'group': 1
    },
    {
        'id': 'haru',
        'name': '春',
        'model_path': '/static/assets/live2d/models/haru/haru01.model.json',
        'texture_dir': 'assets/live2d/models/haru/moc/haru01.1024',
        'texture_prefix': 'texture_',
        'skin_count': 3,
        'group': 1
    }
]

# 对话文案
MESSAGES = {
    'switch_model': ['换好新衣服啦~好看吗？', '嘿嘿~新造型怎么样？', '人家换了个样子，还认得出来吗？'],
    'switch_skin': ['新衣服好看吗喵~', '人家换了套衣服呢~', '这个颜色也很可爱吧？'],
    'rand_model': ['随机到了新角色喵~', '猜猜这次是谁？', '惊喜！换了个新朋友~'],
    'rand_skin': ['随机到了新皮肤喵~', '今天穿这套吧~', '惊喜！新衣服~']
}


def get_model_by_id(model_id):
    """根据模型ID获取模型配置"""
    for m in MODELS:
        if m['id'] == model_id:
            return m
    return MODELS[0]


def get_model_index(model_id):
    """获取模型在列表中的索引"""
    for i, m in enumerate(MODELS):
        if m['id'] == model_id:
            return i
    return 0


@require_http_methods(["GET"])
def model_list(request):
    """获取模型列表"""
    result = {
        'models': [],
        'total': len(MODELS)
    }
    for m in MODELS:
        result['models'].append({
            'id': m['id'],
            'name': m['name'],
            'skin_count': m['skin_count'],
            'model_path': m['model_path']
        })
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
    
    # 模型所在目录的静态URL前缀
    model_dir_url = '/static/assets/live2d/models/' + model_id + '/'
    
    # 读取原始模型JSON
    model_json_path = model['model_path'].replace('/static/', '')
    json_path = os.path.join('static', model_json_path)
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            model_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return JsonResponse({'error': '模型文件不存在'}, status=404)
    
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
        'message': random.choice(MESSAGES['switch_model'])
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
        'message': random.choice(MESSAGES['rand_model'])
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
        'message': random.choice(MESSAGES['switch_skin'])
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
        'message': random.choice(MESSAGES['rand_skin'])
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
        return JsonResponse({'error': '无效的选择，只能是石头/剪刀/布'}, status=400)
    
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

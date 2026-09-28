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
#: 导入模块「json」，供本文件后续使用
import json
#: 导入模块「os」，供本文件后续使用
import os
#: 导入模块「random」，供本文件后续使用
import random

#: 从模块「django.http」导入所需对象
from django.http import HttpResponse, JsonResponse
#: 从模块「django.views.decorators.csrf」导入所需对象
from django.views.decorators.csrf import csrf_exempt
#: 从模块「django.views.decorators.http」导入所需对象
from django.views.decorators.http import require_http_methods

# Bug9 任务2：用户可见提示统一取自 blog/site_messages.py
#: 从模块「.services.site_messages」导入所需对象
from .services.site_messages import msg

# 模型配置：分组 -> 模型列表
# 每个模型包含：id, name, model_json路径, 皮肤目录, 皮肤数量
#: 定义变量「MODELS」，保存对应数据（集合/元组）
MODELS = [
    #: 该行执行对应逻辑（结合上下文理解）
    {
        #: 配置项「id」：字典/模型的该键设置为对应值
        'id': 'shizuku',
        #: 配置项「name」：字典/模型的该键设置为对应值
        'name': '雫',
        #: 配置项「model_path」：字典/模型的该键设置为对应值
        'model_path': '/static/assets/live2d/models/shizuku/shizuku.model.json',
        #: 配置项「texture_dir」：字典/模型的该键设置为对应值
        'texture_dir': 'assets/live2d/models/shizuku/moc/shizuku.1024',
        #: 配置项「texture_prefix」：字典/模型的该键设置为对应值
        'texture_prefix': 'texture_',
        #: 配置项「skin_count」：字典/模型的该键设置为对应值
        'skin_count': 6,
        #: 配置项「group」：字典/模型的该键设置为对应值
        'group': 1
    #: 该行执行对应逻辑（结合上下文理解）
    },
    #: 该行执行对应逻辑（结合上下文理解）
    {
        #: 配置项「id」：字典/模型的该键设置为对应值
        'id': 'koharu',
        #: 配置项「name」：字典/模型的该键设置为对应值
        'name': '小春',
        #: 配置项「model_path」：字典/模型的该键设置为对应值
        'model_path': '/static/assets/live2d/models/koharu/koharu.model.json',
        #: 配置项「texture_dir」：字典/模型的该键设置为对应值
        'texture_dir': 'assets/live2d/models/koharu/moc/koharu.2048',
        #: 配置项「texture_prefix」：字典/模型的该键设置为对应值
        'texture_prefix': 'texture_',
        #: 配置项「skin_count」：字典/模型的该键设置为对应值
        'skin_count': 1,
        #: 配置项「group」：字典/模型的该键设置为对应值
        'group': 1
    #: 该行执行对应逻辑（结合上下文理解）
    },
    #: 该行执行对应逻辑（结合上下文理解）
    {
        #: 配置项「id」：字典/模型的该键设置为对应值
        'id': 'haru',
        #: 配置项「name」：字典/模型的该键设置为对应值
        'name': '春',
        #: 配置项「model_path」：字典/模型的该键设置为对应值
        'model_path': '/static/assets/live2d/models/haru/haru01.model.json',
        #: 配置项「texture_dir」：字典/模型的该键设置为对应值
        'texture_dir': 'assets/live2d/models/haru/moc/haru01.1024',
        #: 配置项「texture_prefix」：字典/模型的该键设置为对应值
        'texture_prefix': 'texture_',
        #: 配置项「skin_count」：字典/模型的该键设置为对应值
        'skin_count': 3,
        #: 配置项「group」：字典/模型的该键设置为对应值
        'group': 1
    #: 该行执行对应逻辑（结合上下文理解）
    }
#: 该行执行对应逻辑（结合上下文理解）
]

# 看板娘台词库：每个动作随机挑选一句，保持角色活泼口语化的二次元语气
#: 定义变量「TALKS」，保存对应数据
TALKS = {
    #: 配置项「switch_model」：字典/模型的该键设置为对应值
    'switch_model': ['换好新衣服啦~好看吗？', '嘿嘿~新造型怎么样？', '人家换了个样子，还认得出来吗？'],
    #: 配置项「switch_skin」：字典/模型的该键设置为对应值
    'switch_skin': ['新衣服好看吗喵~', '人家换了套衣服呢~', '这个颜色也很可爱吧？'],
    #: 配置项「rand_model」：字典/模型的该键设置为对应值
    'rand_model': ['随机到了新角色喵~', '猜猜这次是谁？', '惊喜！换了个新朋友~'],
    #: 配置项「rand_skin」：字典/模型的该键设置为对应值
    'rand_skin': ['随机到了新皮肤喵~', '今天穿这套吧~', '惊喜！新衣服~']
#: 该行执行对应逻辑（结合上下文理解）
}


def get_model_by_id(model_id):
    """根据模型ID获取模型配置"""
    #: 循环遍历，逐个处理元素
    for m in MODELS:
        #: 条件判断：条件成立时执行该分支
        if m['id'] == model_id:
            #: 返回结果并结束当前函数
            return m
    #: 返回结果并结束当前函数
    return MODELS[0]


def get_model_index(model_id):
    """获取模型在列表中的索引"""
    #: 循环遍历，逐个处理元素
    for i, m in enumerate(MODELS):
        #: 条件判断：条件成立时执行该分支
        if m['id'] == model_id:
            #: 返回结果并结束当前函数
            return i
    #: 返回结果并结束当前函数
    return 0


#: 装饰器：为下一个定义附加「require_http_methods(["GET"])」行为（权限、缓存、注册信号等）
@require_http_methods(["GET"])
def model_list(request):
    """获取模型列表"""
    #: 定义变量「result」，保存对应数据
    result = {
        #: 配置项「models」：字典/模型的该键设置为对应值
        'models': [],
        #: 配置项「total」：字典/模型的该键设置为对应值
        'total': len(MODELS)
    #: 该行执行对应逻辑（结合上下文理解）
    }
    #: 循环遍历，逐个处理元素
    for m in MODELS:
        #: 该行执行对应逻辑（结合上下文理解）
        result['models'].append({
            #: 配置项「id」：字典/模型的该键设置为对应值
            'id': m['id'],
            #: 配置项「name」：字典/模型的该键设置为对应值
            'name': m['name'],
            #: 配置项「skin_count」：字典/模型的该键设置为对应值
            'skin_count': m['skin_count'],
            #: 配置项「model_path」：字典/模型的该键设置为对应值
            'model_path': m['model_path']
        #: 该行执行对应逻辑（结合上下文理解）
        })
    #: 返回结果并结束当前函数
    return JsonResponse(result)


#: 装饰器：为下一个定义附加「require_http_methods(["GET"])」行为（权限、缓存、注册信号等）
@require_http_methods(["GET"])
def get_model(request, model=None, skin=None):
    """
    获取指定模型和皮肤的配置
    支持两种调用方式：
    1. /api/live2d/get/?model=xxx&skin=N （查询参数）
    2. /api/live2d/model/xxx/N.json （URL路径）
    返回动态生成的模型JSON（textures字段已替换为指定皮肤）
    """
    #: 读取本次请求的 GET 数据
    model_id = model or request.GET.get('model', 'shizuku')
    #: 读取本次请求的 GET 数据
    skin_idx = skin if skin is not None else request.GET.get('skin', '0')
    
    #: 尝试执行可能出错的代码
    try:
        #: 定义变量「skin_idx」，保存对应数据
        skin_idx = int(skin_idx)
    #: 捕获并处理异常，避免程序中断
    except (ValueError, TypeError):
        #: 定义变量「skin_idx」，保存对应数据
        skin_idx = 0
    
    #: 定义变量「model」，保存对应数据
    model = get_model_by_id(model_id)
    #: 定义变量「skin_idx」，保存对应数据
    skin_idx = max(0, min(skin_idx, model['skin_count'] - 1))
    
    # 模型所在目录的静态URL前缀
    #: 定义变量「model_dir_url」，保存对应数据
    model_dir_url = '/static/assets/live2d/models/' + model_id + '/'
    
    # 读取原始模型JSON
    #: 定义变量「model_json_path」，保存对应数据
    model_json_path = model['model_path'].replace('/static/', '')
    #: 定义变量「json_path」，保存对应数据
    json_path = os.path.join('static', model_json_path)
    
    #: 尝试执行可能出错的代码
    try:
        #: 上下文管理：进入时获取资源、退出时自动释放
        with open(json_path, 'r', encoding='utf-8') as f:
            #: 定义变量「model_data」，保存对应数据
            model_data = json.load(f)
    #: 捕获并处理异常，避免程序中断
    except (FileNotFoundError, json.JSONDecodeError):
        #: 返回结果并结束当前函数
        return JsonResponse({'error': msg('live2d.model_missing')}, status=404)
    
    # 将所有相对路径转换为绝对路径
    def to_abs(rel_path):
        """
        功能：处理「to abs」相关逻辑。

        参数：
          - rel_path：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 条件判断：条件成立时执行该分支
        if rel_path and not rel_path.startswith('/') and not rel_path.startswith('http'):
            #: 返回结果并结束当前函数
            return model_dir_url + rel_path
        #: 返回结果并结束当前函数
        return rel_path
    
    #: 条件判断：条件成立时执行该分支
    if 'model' in model_data:
        #: 该行执行对应逻辑（结合上下文理解）
        model_data['model'] = to_abs(model_data['model'])
    #: 条件判断：条件成立时执行该分支
    if 'physics' in model_data:
        #: 该行执行对应逻辑（结合上下文理解）
        model_data['physics'] = to_abs(model_data['physics'])
    #: 条件判断：条件成立时执行该分支
    if 'pose' in model_data:
        #: 该行执行对应逻辑（结合上下文理解）
        model_data['pose'] = to_abs(model_data['pose'])
    #: 条件判断：条件成立时执行该分支
    if 'expressions' in model_data:
        #: 循环遍历，逐个处理元素
        for exp in model_data['expressions']:
            #: 条件判断：条件成立时执行该分支
            if 'file' in exp:
                #: 该行执行对应逻辑（结合上下文理解）
                exp['file'] = to_abs(exp['file'])
    #: 条件判断：条件成立时执行该分支
    if 'motions' in model_data:
        #: 循环遍历，逐个处理元素
        for motion_list in model_data['motions'].values():
            #: 循环遍历，逐个处理元素
            for motion in motion_list:
                #: 条件判断：条件成立时执行该分支
                if 'file' in motion:
                    #: 该行执行对应逻辑（结合上下文理解）
                    motion['file'] = to_abs(motion['file'])
                #: 条件判断：条件成立时执行该分支
                if 'sound' in motion:
                    #: 该行执行对应逻辑（结合上下文理解）
                    motion['sound'] = to_abs(motion['sound'])
    
    # 替换textures为指定皮肤
    #: 定义变量「texture_url」，保存对应数据
    texture_url = f"/static/{model['texture_dir']}/{model['texture_prefix']}{skin_idx:02d}.png"
    #: 该行执行对应逻辑（结合上下文理解）
    model_data['textures'] = [texture_url]
    
    #: 构造 HTTP 响应返回给客户端
    response = HttpResponse(json.dumps(model_data, ensure_ascii=False), content_type='application/json')
    #: 该行执行对应逻辑（结合上下文理解）
    response['Cache-Control'] = 'no-cache'
    #: 返回结果并结束当前函数
    return response


#: 装饰器：为下一个定义附加「require_http_methods(["GET"])」行为（权限、缓存、注册信号等）
@require_http_methods(["GET"])
def switch_model(request):
    """
    顺序切换模型
    参数：current=当前模型ID
    返回：下一个模型的信息和动态模型JSON URL
    """
    #: 读取本次请求的 GET 数据
    current_id = request.GET.get('current', 'shizuku')
    #: 定义变量「current_idx」，保存对应数据
    current_idx = get_model_index(current_id)
    #: 定义变量「next_idx」，保存对应数据（集合/元组）
    next_idx = (current_idx + 1) % len(MODELS)
    #: 定义变量「next_model」，保存对应数据
    next_model = MODELS[next_idx]
    
    # 返回动态模型URL（皮肤0）
    #: 定义变量「model_url」，保存对应数据
    model_url = f'/api/live2d/model/{next_model["id"]}/0.json'
    
    #: 返回结果并结束当前函数
    return JsonResponse({
        #: 配置项「model_id」：字典/模型的该键设置为对应值
        'model_id': next_model['id'],
        #: 配置项「model_name」：字典/模型的该键设置为对应值
        'model_name': next_model['name'],
        #: 配置项「skin」：字典/模型的该键设置为对应值
        'skin': 0,
        #: 配置项「skin_count」：字典/模型的该键设置为对应值
        'skin_count': next_model['skin_count'],
        #: 配置项「model_url」：字典/模型的该键设置为对应值
        'model_url': model_url,
        #: 配置项「message」：字典/模型的该键设置为对应值
        'message': random.choice(TALKS['switch_model'])
    #: 该行执行对应逻辑（结合上下文理解）
    })


#: 装饰器：为下一个定义附加「require_http_methods(["GET"])」行为（权限、缓存、注册信号等）
@require_http_methods(["GET"])
def rand_model(request):
    """
    随机切换模型
    参数：current=当前模型ID
    返回：随机模型的信息和动态模型JSON URL
    """
    #: 读取本次请求的 GET 数据
    current_id = request.GET.get('current', 'shizuku')
    
    # 随机选择一个不同的模型
    #: 定义变量「available」，保存对应数据（集合/元组）
    available = [m for m in MODELS if m['id'] != current_id]
    #: 条件判断：条件成立时执行该分支
    if not available:
        #: 定义变量「available」，保存对应数据
        available = MODELS
    #: 定义变量「next_model」，保存对应数据
    next_model = random.choice(available)
    
    #: 定义变量「model_url」，保存对应数据
    model_url = f'/api/live2d/model/{next_model["id"]}/0.json'
    
    #: 返回结果并结束当前函数
    return JsonResponse({
        #: 配置项「model_id」：字典/模型的该键设置为对应值
        'model_id': next_model['id'],
        #: 配置项「model_name」：字典/模型的该键设置为对应值
        'model_name': next_model['name'],
        #: 配置项「skin」：字典/模型的该键设置为对应值
        'skin': 0,
        #: 配置项「skin_count」：字典/模型的该键设置为对应值
        'skin_count': next_model['skin_count'],
        #: 配置项「model_url」：字典/模型的该键设置为对应值
        'model_url': model_url,
        #: 配置项「message」：字典/模型的该键设置为对应值
        'message': random.choice(TALKS['rand_model'])
    #: 该行执行对应逻辑（结合上下文理解）
    })


#: 装饰器：为下一个定义附加「require_http_methods(["GET"])」行为（权限、缓存、注册信号等）
@require_http_methods(["GET"])
def switch_skin(request):
    """
    顺序切换皮肤（在当前模型内）
    参数：model=当前模型ID, current=当前皮肤索引
    返回：下一个皮肤的信息和动态模型JSON URL
    """
    #: 读取本次请求的 GET 数据
    model_id = request.GET.get('model', 'shizuku')
    #: 读取本次请求的 GET 数据
    current_skin = request.GET.get('current', '0')
    
    #: 尝试执行可能出错的代码
    try:
        #: 定义变量「current_skin」，保存对应数据
        current_skin = int(current_skin)
    #: 捕获并处理异常，避免程序中断
    except (ValueError, TypeError):
        #: 定义变量「current_skin」，保存对应数据
        current_skin = 0
    
    #: 定义变量「model」，保存对应数据
    model = get_model_by_id(model_id)
    #: 定义变量「next_skin」，保存对应数据（集合/元组）
    next_skin = (current_skin + 1) % model['skin_count']
    
    #: 定义变量「model_url」，保存对应数据
    model_url = f'/api/live2d/model/{model_id}/{next_skin}.json'
    
    #: 返回结果并结束当前函数
    return JsonResponse({
        #: 配置项「model_id」：字典/模型的该键设置为对应值
        'model_id': model_id,
        #: 配置项「model_name」：字典/模型的该键设置为对应值
        'model_name': model['name'],
        #: 配置项「skin」：字典/模型的该键设置为对应值
        'skin': next_skin,
        #: 配置项「skin_count」：字典/模型的该键设置为对应值
        'skin_count': model['skin_count'],
        #: 配置项「model_url」：字典/模型的该键设置为对应值
        'model_url': model_url,
        #: 配置项「message」：字典/模型的该键设置为对应值
        'message': random.choice(TALKS['switch_skin'])
    #: 该行执行对应逻辑（结合上下文理解）
    })


#: 装饰器：为下一个定义附加「require_http_methods(["GET"])」行为（权限、缓存、注册信号等）
@require_http_methods(["GET"])
def rand_skin(request):
    """
    随机切换皮肤（在当前模型内）
    参数：model=当前模型ID, current=当前皮肤索引
    返回：随机皮肤的信息和动态模型JSON URL
    """
    #: 读取本次请求的 GET 数据
    model_id = request.GET.get('model', 'shizuku')
    #: 读取本次请求的 GET 数据
    current_skin = request.GET.get('current', '0')
    
    #: 尝试执行可能出错的代码
    try:
        #: 定义变量「current_skin」，保存对应数据
        current_skin = int(current_skin)
    #: 捕获并处理异常，避免程序中断
    except (ValueError, TypeError):
        #: 定义变量「current_skin」，保存对应数据
        current_skin = 0
    
    #: 定义变量「model」，保存对应数据
    model = get_model_by_id(model_id)
    
    # 随机选择一个不同的皮肤
    #: 定义变量「available」，保存对应数据（集合/元组）
    available = [i for i in range(model['skin_count']) if i != current_skin]
    #: 条件判断：条件成立时执行该分支
    if not available:
        #: 定义变量「available」，保存对应数据（集合/元组）
        available = [current_skin]
    #: 定义变量「next_skin」，保存对应数据
    next_skin = random.choice(available)
    
    #: 定义变量「model_url」，保存对应数据
    model_url = f'/api/live2d/model/{model_id}/{next_skin}.json'
    
    #: 返回结果并结束当前函数
    return JsonResponse({
        #: 配置项「model_id」：字典/模型的该键设置为对应值
        'model_id': model_id,
        #: 配置项「model_name」：字典/模型的该键设置为对应值
        'model_name': model['name'],
        #: 配置项「skin」：字典/模型的该键设置为对应值
        'skin': next_skin,
        #: 配置项「skin_count」：字典/模型的该键设置为对应值
        'skin_count': model['skin_count'],
        #: 配置项「model_url」：字典/模型的该键设置为对应值
        'model_url': model_url,
        #: 配置项「message」：字典/模型的该键设置为对应值
        'message': random.choice(TALKS['rand_skin'])
    #: 该行执行对应逻辑（结合上下文理解）
    })


#: 装饰器：为下一个定义附加「csrf_exempt」行为（权限、缓存、注册信号等）
@csrf_exempt
#: 装饰器：为下一个定义附加「require_http_methods(["POST"])」行为（权限、缓存、注册信号等）
@require_http_methods(["POST"])
def game_play(request):
    """
    看板娘小游戏：猜拳
    参数：choice=石头/剪刀/布
    返回：游戏结果
    """
    #: 尝试执行可能出错的代码
    try:
        #: 读取本次请求的 body 数据
        data = json.loads(request.body)
        #: 定义变量「user_choice」，保存对应数据
        user_choice = data.get('choice', '').strip()
    #: 捕获并处理异常，避免程序中断
    except (json.JSONDecodeError, AttributeError):
        #: 读取本次请求的 POST 数据
        user_choice = request.POST.get('choice', '').strip()
    
    #: 定义变量「choices」，保存对应数据（集合/元组）
    choices = ['石头', '剪刀', '布']
    #: 条件判断：条件成立时执行该分支
    if user_choice not in choices:
        #: 返回结果并结束当前函数
        return JsonResponse({'error': msg('live2d.bad_choice')}, status=400)
    
    #: 定义变量「waifu_choice」，保存对应数据
    waifu_choice = random.choice(choices)
    
    # 判断胜负
    #: 条件判断：条件成立时执行该分支
    if user_choice == waifu_choice:
        #: 定义变量「result」，保存对应数据
        result = '平局'
        #: 定义变量「message」，保存对应数据
        message = '哎呀，平局了~再来一局喵！'
    #: 否则若该条件成立则进入此分支
    elif (user_choice == '石头' and waifu_choice == '剪刀') or \
         (user_choice == '剪刀' and waifu_choice == '布') or \
         (user_choice == '布' and waifu_choice == '石头'):
        #: 定义变量「result」，保存对应数据
        result = '胜利'
        #: 定义变量「message」，保存对应数据
        message = '你赢了喵~好厉害！'
    #: 以上条件均不成立时的兜底分支
    else:
        #: 定义变量「result」，保存对应数据
        result = '失败'
        #: 定义变量「message」，保存对应数据
        message = '嘿嘿，人家赢了~再来一局吗？'
    
    #: 返回结果并结束当前函数
    return JsonResponse({
        #: 配置项「user_choice」：字典/模型的该键设置为对应值
        'user_choice': user_choice,
        #: 配置项「waifu_choice」：字典/模型的该键设置为对应值
        'waifu_choice': waifu_choice,
        #: 配置项「result」：字典/模型的该键设置为对应值
        'result': result,
        #: 配置项「message」：字典/模型的该键设置为对应值
        'message': message
    #: 该行执行对应逻辑（结合上下文理解）
    })

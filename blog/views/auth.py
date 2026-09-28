# -*- coding: utf-8 -*-

"""认证域：登录、注册、登出。"""

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
#: 从模块「django.contrib」导入所需对象
from django.contrib import messages
#: 从模块「django.contrib.auth」导入所需对象
from django.contrib.auth import authenticate, login, logout
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

#: 从模块「.common」导入所需对象
from .common import logger


#: 定义变量「logger」，保存对应数据
logger = logging.getLogger('blog.views')

# 迭代#178: login_view视图docstring
# 迭代#179: login_view(request) -> HttpResponse 类型提示
def login_view(request: HttpRequest) -> HttpResponse:
    """登录视图：已登录则直接跳首页；否则渲染登录表单并校验凭据。

    - GET：渲染登录表单页 ``blog/login.html``；
    - POST：用 ``authenticate`` 校验用户名密码，成功则 ``login`` 登录并
      跳转（优先跳 ``?next=`` 来源页，否则回首页）；失败则提示错误。

    Args:
        request: 当前 HttpRequest 对象，读取 POST 中的 username / password。

    Returns:
        HttpResponse: 已登录或成功登录后重定向；GET 或校验失败时渲染登录页。
    """
    #: 条件判断：条件成立时执行该分支
    if request.user.is_authenticated:
        #: 返回结果并结束当前函数
        return redirect('index')
    #: 定义变量「login_error」，保存对应数据
    login_error = ''
    #: 条件判断：条件成立时执行该分支
    if request.method == 'POST':
        #: 读取本次请求的 POST 数据
        username = request.POST.get('username', '').strip()
        #: 读取本次请求的 POST 数据
        password = request.POST.get('password', '')
        # authenticate 校验不通过返回 None
        #: 校验用户名密码，返回通过认证的用户或 None
        user = authenticate(request, username=username, password=password)
        #: 条件判断：条件成立时执行该分支
        if user:
            #: 将用户登录状态写入会话
            login(request, user)
            # 迭代#180: 用户登录日志
            #: 记录日志，便于排查（勿记录密码等敏感信息）
            logger.info('用户登录: %s', user.username)
            #: 向用户闪现一条提示消息（下次请求展示）
            messages.success(request, msg('auth.welcome_back', user.username))
            # next 参数为登录前试图访问的页面，登录成功后回跳过去
            #: 返回结果并结束当前函数
            return redirect(request.GET.get('next') or 'index')
        #: 定义变量「login_error」，保存对应数据
        login_error = msg('auth.login_failed')
        #: 向用户闪现一条提示消息（下次请求展示）
        messages.error(request, login_error)
    #: 返回结果并结束当前函数
    return render(request, 'blog/login.html',
                  #: 该行执行对应逻辑（结合上下文理解）
                  {'active_nav': 'login', 'login_error': login_error})

# 迭代#181: register_view视图docstring
# 迭代#182: register_view(request) -> HttpResponse 类型提示
def register_view(request: HttpRequest) -> HttpResponse:
    """注册视图：创建新用户并自动登录。

    - GET：渲染注册表单页；
    - POST：依次校验——用户名/密码非空、两次密码一致、用户名未被占用、
      密码长度≥8；全部通过则 ``create_user`` 创建用户并立即登录。

    Args:
        request: 当前 HttpRequest 对象，读取 POST 中的 username / password /
                 password2 / nickname。

    Returns:
        HttpResponse: 校验通过后重定向首页；否则重新渲染注册页并提示错误。
    """
    #: 条件判断：条件成立时执行该分支
    if request.user.is_authenticated:
        #: 返回结果并结束当前函数
        return redirect('index')
    # Bug8 修复：保留用户本次填写的值（校验失败时不丢输入），并把错误按字段标记，
    # 供模板渲染「输入框下方红色内联提示」——不再依赖整页刷新后的顶部 flash。
    #: 定义变量「form_values」，保存对应数据
    form_values = {'username': '', 'nickname': '', 'email': ''}
    #: 定义变量「field_errors」，保存对应数据（集合/元组）
    field_errors = []
    #: 条件判断：条件成立时执行该分支
    if request.method == 'POST':
        #: 读取本次请求的 POST 数据
        username = request.POST.get('username', '').strip()
        #: 读取本次请求的 POST 数据
        password = request.POST.get('password', '')
        #: 读取本次请求的 POST 数据
        password2 = request.POST.get('password2', '')
        # 迭代#184: 邮箱格式验证（提前读取，纳入统一校验链）
        #: 读取本次请求的 POST 数据
        email = request.POST.get('email', '').strip()
        #: 读取本次请求的 POST 数据
        nickname = request.POST.get('nickname', '').strip()
        #: 定义变量「form_values」，保存对应数据
        form_values = {'username': username, 'nickname': nickname, 'email': email}
        # 逐项校验，任一项不通过即提示并重新渲染表单，绝不创建用户
        # 迭代#183: 用户名长度验证
        # D1修复：所有校验合并为单一 if/elif/else 链，确保密码不一致等
        # 任一校验失败都不会落入 else 执行 create_user
        # Bug8 修复：每条错误带字段名，前端据此渲染内联红字
        #: 条件判断：条件成立时执行该分支
        if not username or not password:
            #: 调用「field_errors.append」执行相应逻辑
            field_errors.append(('username', '用户名和密码都要填喵~📝'))
        #: 否则若该条件成立则进入此分支
        elif len(username) > 150:
            #: 调用「field_errors.append」执行相应逻辑
            field_errors.append(('username', '用户名太长啦~ 最多 150 个字符哦'))
        #: 否则若该条件成立则进入此分支
        elif password != password2:
            #: 调用「field_errors.append」执行相应逻辑
            field_errors.append(('password2', '两次密码不一样呢~再确认一下喵🔍'))
        #: 否则若该条件成立则进入此分支
        elif email and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            #: 调用「field_errors.append」执行相应逻辑
            field_errors.append(('email', '邮箱格式不对呢~再检查一下喵~📧'))
        #: 否则若该条件成立则进入此分支
        elif User.objects.filter(username=username).exists():
            #: 调用「field_errors.append」执行相应逻辑
            field_errors.append(('username', '这个名字已经被别的小伙伴用了呢~换一个吧😢'))
        #: 否则若该条件成立则进入此分支
        elif len(password) < 8:
            #: 调用「field_errors.append」执行相应逻辑
            field_errors.append(('password', '密码至少要 8 位哦~为了安全嘛🔒'))
        #: 以上条件均不成立时的兜底分支
        else:
            # create_user 会自动哈希密码，nickname 为可选昵称
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            user = User.objects.create_user(
                #: 定义变量「username」，保存对应数据
                username=username, password=password,
                #: 定义变量「nickname」，保存对应数据
                nickname=nickname)
            #: 将用户登录状态写入会话
            login(request, user)
            # 迭代#185: 用户注册日志
            #: 记录日志，便于排查（勿记录密码等敏感信息）
            logger.info('用户注册: %s', user.username)
            #: 向用户闪现一条提示消息（下次请求展示）
            messages.success(request, msg('auth.register_success'))
            #: 返回结果并结束当前函数
            return redirect('index')
        # 校验失败：同步写 flash（无 JS 时仍可见）并交给模板渲染内联红字
        #: 循环遍历，逐个处理元素
        for _field, _msg in field_errors:
            #: 向用户闪现一条提示消息（下次请求展示）
            messages.error(request, _msg)
    #: 返回结果并结束当前函数
    return render(request, 'blog/register.html', {
        #: 配置项「active_nav」：字典/模型的该键设置为对应值
        'active_nav': 'register',
        #: 配置项「field_errors」：字典/模型的该键设置为对应值
        'field_errors': field_errors,
        #: 配置项「form_values」：字典/模型的该键设置为对应值
        'form_values': form_values,
    #: 该行执行对应逻辑（结合上下文理解）
    })

# 迭代#186: logout_view视图docstring
# 迭代#187: logout_view(request) -> HttpResponseRedirect 类型提示
def logout_view(request: HttpRequest) -> HttpResponseRedirect:
    """退出登录视图：销毁当前会话并重定向回首页。

    无 GET/POST 区分，访问即登出（实际退出按钮在 base.html 中以 POST 表单提交）。

    Args:
        request: 当前 HttpRequest 对象。

    Returns:
        HttpResponse: 始终重定向回首页。
    """
    # 迭代#188: 用户登出日志
    #: 记录日志，便于排查（勿记录密码等敏感信息）
    logger.info('用户登出: %s', request.user.username if request.user.is_authenticated else 'anonymous')
    #: 清除会话，完成登出
    logout(request)
    #: 向用户闪现一条提示消息（下次请求展示）
    messages.success(request, msg('auth.logout_success'))
    #: 返回结果并结束当前函数
    return redirect('index')

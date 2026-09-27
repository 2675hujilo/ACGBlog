# -*- coding: utf-8 -*-

"""认证域：登录、注册、登出。"""

import json
import logging
import os
import re
import uuid
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import (
    FileResponse, Http404, HttpRequest, HttpResponse,
    HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound,
    HttpResponseNotModified, HttpResponsePermanentRedirect,
    HttpResponseRedirect, JsonResponse, StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from ..models import (
    AccessLog, Article, Badge, Category, Comment, CommentReport,
    EditLog, Favorite, FavoriteFolder, ModerationLog, Notification,
    PromotionRequest, ModerationSettings, Rating, Series, ShortLink,
    SiteNotice, Tag, User, UserBadge,
)
from ..site_messages import msg

from .common import logger


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
    if request.user.is_authenticated:
        return redirect('index')
    login_error = ''
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        # authenticate 校验不通过返回 None
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            # 迭代#180: 用户登录日志
            logger.info('用户登录: %s', user.username)
            messages.success(request, msg('auth.welcome_back', user.username))
            # next 参数为登录前试图访问的页面，登录成功后回跳过去
            return redirect(request.GET.get('next') or 'index')
        login_error = msg('auth.login_failed')
        messages.error(request, login_error)
    return render(request, 'blog/login.html',
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
    if request.user.is_authenticated:
        return redirect('index')
    # Bug8 修复：保留用户本次填写的值（校验失败时不丢输入），并把错误按字段标记，
    # 供模板渲染「输入框下方红色内联提示」——不再依赖整页刷新后的顶部 flash。
    form_values = {'username': '', 'nickname': '', 'email': ''}
    field_errors = []
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        # 迭代#184: 邮箱格式验证（提前读取，纳入统一校验链）
        email = request.POST.get('email', '').strip()
        nickname = request.POST.get('nickname', '').strip()
        form_values = {'username': username, 'nickname': nickname, 'email': email}
        # 逐项校验，任一项不通过即提示并重新渲染表单，绝不创建用户
        # 迭代#183: 用户名长度验证
        # D1修复：所有校验合并为单一 if/elif/else 链，确保密码不一致等
        # 任一校验失败都不会落入 else 执行 create_user
        # Bug8 修复：每条错误带字段名，前端据此渲染内联红字
        if not username or not password:
            field_errors.append(('username', '用户名和密码都要填喵~📝'))
        elif len(username) > 150:
            field_errors.append(('username', '用户名太长啦~ 最多 150 个字符哦'))
        elif password != password2:
            field_errors.append(('password2', '两次密码不一样呢~再确认一下喵🔍'))
        elif email and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            field_errors.append(('email', '邮箱格式不对呢~再检查一下喵~📧'))
        elif User.objects.filter(username=username).exists():
            field_errors.append(('username', '这个名字已经被别的小伙伴用了呢~换一个吧😢'))
        elif len(password) < 8:
            field_errors.append(('password', '密码至少要 8 位哦~为了安全嘛🔒'))
        else:
            # create_user 会自动哈希密码，nickname 为可选昵称
            user = User.objects.create_user(
                username=username, password=password,
                nickname=nickname)
            login(request, user)
            # 迭代#185: 用户注册日志
            logger.info('用户注册: %s', user.username)
            messages.success(request, msg('auth.register_success'))
            return redirect('index')
        # 校验失败：同步写 flash（无 JS 时仍可见）并交给模板渲染内联红字
        for _field, _msg in field_errors:
            messages.error(request, _msg)
    return render(request, 'blog/register.html', {
        'active_nav': 'register',
        'field_errors': field_errors,
        'form_values': form_values,
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
    logger.info('用户登出: %s', request.user.username if request.user.is_authenticated else 'anonymous')
    logout(request)
    messages.success(request, msg('auth.logout_success'))
    return redirect('index')

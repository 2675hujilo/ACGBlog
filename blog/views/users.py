# -*- coding: utf-8 -*-

"""用户域：资料、设置、偏好、徽章、在线状态、通知、收藏夹与个人中心。"""

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
#: 导入模块「bleach」，供本文件后续使用
import bleach
#: 从模块「django.conf」导入所需对象
from django.conf import settings
#: 从模块「django.contrib」导入所需对象
from django.contrib import messages
#: 从模块「django.contrib.auth」导入所需对象
from django.contrib.auth import authenticate, login, logout
#: 从模块「django.contrib.auth.decorators」导入所需对象
from django.contrib.auth.decorators import login_required
#: 从模块「django.core.cache」导入所需对象
from django.core.cache import cache
#: 从模块「django.core.paginator」导入所需对象
from django.core.paginator import Paginator
#: 从模块「django.db.models」导入所需对象
from django.db.models import Avg, Count, F, Min, Q, Sum
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
#: 从模块「PIL」导入所需对象
from PIL import Image
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
from .common import AVATAR_MAX_BYTES, _bad_request, _clamp_page_number, _clean_page_size, _json_ok, _paginate_qs, logger


#: 定义变量「logger」，保存对应数据
logger = logging.getLogger('blog.views')

def _user_profile_cached(username, timeout=600):
    # 第2轮迭代#67: 用户资料缓存——个人主页作者信息短 TTL 缓存
    """
    功能：处理「user profile cached」相关逻辑。

    参数：
      - username：传入参数，含义结合函数体与调用处
      - timeout（可选，有默认值）：传入参数，含义结合函数体与调用处

    返回：对应计算/查询结果。

    注意：含 Django ORM 数据库查询，注意查询性能与空结果处理；读写缓存，注意缓存键口径与失效策略。
    """
    #: 定义变量「key」，保存对应数据
    key = f'user_profile_{username}'
    #: 返回结果并结束当前函数
    return cache.get_or_set(
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        key, lambda: User.objects.filter(username=username).first(), timeout)

# 迭代#189: user_profile视图docstring
# 迭代#190: user_profile(request, username) -> HttpResponse 类型提示
def _build_badge_panel(profile_user, viewer_is_owner: bool) -> dict:
    """Bug9 任务「1」：构造个人中心「徽章 / 成就」可视化面板数据。

    需求原文：站内徽章、成就没有明确的可视化面板，应该在个人中心有自己已经获得的
    成绩和徽章，折叠未获得的徽章和成就，折叠可展开，并说明如何获得。

    实现要点：
    - **已获得**：按获得时间倒序排在前面，每张卡片显示图标 / 名称 / 说明 / 获得时间；
    - **未获得**：默认折叠，展开后每张卡片额外显示「进度条 + 还差多少」，
      让用户明确知道离解锁还有多远（进度按 ``condition_type`` 实时统计）；
    - 进度与 ``check_and_award_badges`` 的统计口径**完全一致**
      （articles=已发布文章数、comments=评论数、likes=文章累计获赞、
      views=文章累计阅读、days=注册天数），避免「进度显示已达标却没发徽章」。

    Args:
        profile_user: 被访问主页的用户。
        viewer_is_owner: 访问者是否为主页主人（决定是否提示「去解锁」引导文案）。

    Returns:
        dict: {
            'obtained': [badge dict...], 'locked': [badge dict...],
            'total', 'obtained_count', 'locked_count', 'rate'(百分比),
            'has_any', 'is_owner'
        }
    """
    # ---- 1. 一次性统计该用户的各项进度（与发徽章口径一致，全部走聚合查询）----
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    pub_articles = Article.objects.filter(
        #: 定义变量「author」，保存对应数据
        author=profile_user, status=Article.Status.PUBLISHED)
    #: 定义变量「stats」，保存对应数据
    stats = {
        #: 配置项「articles」：字典/模型的该键设置为对应值
        'articles': pub_articles.count(),
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        'comments': Comment.objects.filter(user=profile_user).count(),
        #: 使用聚合函数做统计查询
        'likes': pub_articles.aggregate(s=Sum('likes'))['s'] or 0,
        #: 使用聚合函数做统计查询
        'views': pub_articles.aggregate(s=Sum('views'))['s'] or 0,
        #: 获取当前时间（时区感知），统一时间口径
        'days': ((timezone.now() - profile_user.date_joined).days
                 #: 条件判断：条件成立时执行该分支
                 if profile_user.date_joined else 0),
    #: 该行执行对应逻辑（结合上下文理解）
    }
    # ---- 2. 已获得徽章映射：badge_id -> 获得时间 ----
    #: 定义变量「earned」，保存对应数据
    earned = {ub.badge_id: ub.earned_at
              #: 循环遍历，逐个处理元素
              for ub in UserBadge.objects.filter(user=profile_user)}
    #: 该行执行对应逻辑（结合上下文理解）
    obtained, locked = [], []
    #: 循环遍历，逐个处理元素
    for badge in Badge.objects.all().order_by('condition_type', 'condition_value', 'id'):
        #: 定义变量「current」，保存对应数据
        current = stats.get(badge.condition_type, 0) or 0
        #: 定义变量「need」，保存对应数据
        need = badge.condition_value or 1
        # 进度百分比（0~100），已达标固定 100
        #: 定义变量「percent」，保存对应数据
        percent = 100 if current >= need else int(current * 100 / need)
        #: 定义变量「item」，保存对应数据
        item = {
            #: 配置项「id」：字典/模型的该键设置为对应值
            'id': badge.id,
            #: 配置项「name」：字典/模型的该键设置为对应值
            'name': badge.name,
            #: 配置项「icon」：字典/模型的该键设置为对应值
            'icon': badge.icon or '🏅',
            #: 配置项「description」：字典/模型的该键设置为对应值
            'description': badge.description,
            # 获取方式：优先用后台填写的说明，缺失时按条件类型生成兜底文案
            #: 配置项「how_to」：字典/模型的该键设置为对应值
            'how_to': badge.description or _BADGE_HOW_TO.get(badge.condition_type, '继续活跃即可解锁喵~'),
            #: 配置项「current」：字典/模型的该键设置为对应值
            'current': current,
            #: 配置项「need」：字典/模型的该键设置为对应值
            'need': need,
            #: 配置项「percent」：字典/模型的该键设置为对应值
            'percent': percent,
            #: 配置项「remaining」：字典/模型的该键设置为对应值
            'remaining': max(0, need - current),
            #: 配置项「unit」：字典/模型的该键设置为对应值
            'unit': _BADGE_UNITS.get(badge.condition_type, ''),
            #: 配置项「earned_at」：字典/模型的该键设置为对应值
            'earned_at': earned.get(badge.id),
            #: 配置项「obtained」：字典/模型的该键设置为对应值
            'obtained': badge.id in earned,
        #: 该行执行对应逻辑（结合上下文理解）
        }
        #: 该行执行对应逻辑（结合上下文理解）
        (obtained if item['obtained'] else locked).append(item)
    # 已获得：最近获得的排最前；未获得：进度高的排前面（更容易达成的优先展示）
    #: 调用「obtained.sort」执行相应逻辑
    obtained.sort(key=lambda x: (x['earned_at'] is None, -(x['earned_at'].timestamp() if x['earned_at'] else 0)))
    #: 调用「locked.sort」执行相应逻辑
    locked.sort(key=lambda x: (-x['percent'], x['need']))
    #: 定义变量「total」，保存对应数据
    total = len(obtained) + len(locked)
    #: 返回结果并结束当前函数
    return {
        #: 配置项「obtained」：字典/模型的该键设置为对应值
        'obtained': obtained,
        #: 配置项「locked」：字典/模型的该键设置为对应值
        'locked': locked,
        #: 配置项「total」：字典/模型的该键设置为对应值
        'total': total,
        #: 配置项「obtained_count」：字典/模型的该键设置为对应值
        'obtained_count': len(obtained),
        #: 配置项「locked_count」：字典/模型的该键设置为对应值
        'locked_count': len(locked),
        #: 配置项「rate」：字典/模型的该键设置为对应值
        'rate': int(len(obtained) * 100 / total) if total else 0,
        #: 配置项「has_any」：字典/模型的该键设置为对应值
        'has_any': bool(obtained),
        #: 配置项「is_owner」：字典/模型的该键设置为对应值
        'is_owner': viewer_is_owner,
    #: 该行执行对应逻辑（结合上下文理解）
    }

#: 徽章条件类型 → 进度单位（用于面板上的「12/50 篇」这类展示）
_BADGE_UNITS = {
    #: 配置项「articles」：字典/模型的该键设置为对应值
    'articles': '篇',
    #: 配置项「comments」：字典/模型的该键设置为对应值
    'comments': '条',
    #: 配置项「likes」：字典/模型的该键设置为对应值
    'likes': '个赞',
    #: 配置项「views」：字典/模型的该键设置为对应值
    'views': '次阅读',
    #: 配置项「days」：字典/模型的该键设置为对应值
    'days': '天',
#: 该行执行对应逻辑（结合上下文理解）
}

#: 徽章条件类型 → 兜底「如何获得」文案（后台未填写 description 时使用）
_BADGE_HOW_TO = {
    #: 配置项「articles」：字典/模型的该键设置为对应值
    'articles': '发布更多文章即可解锁喵~',
    #: 配置项「comments」：字典/模型的该键设置为对应值
    'comments': '多和大家互动评论即可解锁喵~',
    #: 配置项「likes」：字典/模型的该键设置为对应值
    'likes': '写出让大家喜欢的内容，收获更多点赞即可解锁喵~',
    #: 配置项「views」：字典/模型的该键设置为对应值
    'views': '让更多人读到你的文章即可解锁喵~',
    #: 配置项「days」：字典/模型的该键设置为对应值
    'days': '常回来看看，陪伴站点更久即可解锁喵~',
#: 该行执行对应逻辑（结合上下文理解）
}

def user_profile(request: HttpRequest, username: str) -> HttpResponse:
    """用户个人主页：展示指定用户的资料卡、统计数据与已发布文章列表。

    - 按 username 取用户，不存在则 404；
    - 仅展示该用户的"已发布"文章（草稿不对访客公开）；
    - 统计数据：文章总数、总阅读量、总点赞数、总评论数、收藏数；
    - 同时展示该用户收藏的文章列表（仅收藏公开文章）；
    - 若访问者本人就是主页主人，额外显示"编辑资料"按钮；
    - Bug9 任务「1」：追加「徽章 / 成就」可视化面板（已获得在前，
      未获得默认折叠可展开，并逐条说明获取方式与当前进度）。

    Args:
        request: 当前 HttpRequest 对象。
        username: URL 中捕获的用户名。

    Returns:
        HttpResponse: 渲染后的个人主页 HTML。
    """
    # 按用户名查找用户，不存在则 404
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    profile_user = get_object_or_404(User, username=username)
    # ---- 查询该用户的已发布文章（分页，每页 10 篇）----
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    article_qs = Article.objects.filter(
        #: 定义变量「author」，保存对应数据
        author=profile_user, status=Article.Status.PUBLISHED
    #: ORM 预加载关联，减少 N+1 查询提升性能
    ).select_related('category').prefetch_related('tags').order_by('-created_at', '-id')
    #: 定义变量「paginator」，保存对应数据
    paginator = Paginator(article_qs, 10)
    #: 读取本次请求的 GET 数据
    page_obj = paginator.get_page(request.GET.get('page'))
    # ---- 统计数据：聚合查询，避免循环逐条 count ----
    #: 定义变量「published_articles」，保存对应数据
    published_articles = article_qs
    #: 使用聚合函数做统计查询
    total_views = published_articles.aggregate(v=Sum('views'))['v'] or 0
    #: 使用聚合函数做统计查询
    total_likes = published_articles.aggregate(l=Sum('likes'))['l'] or 0
    #: 使用聚合函数做统计查询
    total_comments = published_articles.aggregate(c=Sum('comment_count'))['c'] or 0
    # 收藏数：该用户收藏的文章总数
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    fav_count = Favorite.objects.filter(user=profile_user).count()
    #: 定义变量「user_stats」，保存对应数据
    user_stats = {
        #: 配置项「article_count」：字典/模型的该键设置为对应值
        'article_count': published_articles.count(),
        #: 配置项「total_views」：字典/模型的该键设置为对应值
        'total_views': total_views,
        #: 配置项「total_likes」：字典/模型的该键设置为对应值
        'total_likes': total_likes,
        #: 配置项「total_comments」：字典/模型的该键设置为对应值
        'total_comments': total_comments,
        #: 配置项「fav_count」：字典/模型的该键设置为对应值
        'fav_count': fav_count,
    #: 该行执行对应逻辑（结合上下文理解）
    }
    # ---- 该用户收藏的文章列表（仅已发布文章）----
    # 通过 Favorite 表关联查询，select_related 预加载文章与作者
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    fav_articles = Article.objects.filter(
        #: 定义变量「favorites__user」，保存对应数据
        favorites__user=profile_user, status=Article.Status.PUBLISHED
    #: ORM 预加载关联，减少 N+1 查询提升性能
    ).select_related('author', 'category').order_by('-favorites__created_at')[:20]
    # ---- 判断是否为本人访问 ----
    #: 读取本次请求的 user 数据
    is_own_profile = request.user.is_authenticated and request.user == profile_user
    #: 定义变量「ctx」，保存对应数据
    ctx = {
        #: 配置项「profile_user」：字典/模型的该键设置为对应值
        'profile_user': profile_user,
        #: 配置项「page_obj」：字典/模型的该键设置为对应值
        'page_obj': page_obj,
        #: 配置项「page_range」：字典/模型的该键设置为对应值
        'page_range': list(paginator.page_range),
        #: 配置项「user_stats」：字典/模型的该键设置为对应值
        'user_stats': user_stats,
        #: 配置项「fav_articles」：字典/模型的该键设置为对应值
        'fav_articles': fav_articles,
        #: 配置项「is_own_profile」：字典/模型的该键设置为对应值
        'is_own_profile': is_own_profile,
        # Bug9 任务1：徽章 / 成就可视化面板（已获得 + 折叠的未获得）
        #: 配置项「badge_panel」：字典/模型的该键设置为对应值
        'badge_panel': _build_badge_panel(profile_user, is_own_profile),
        #: 配置项「active_nav」：字典/模型的该键设置为对应值
        'active_nav': 'home',
    #: 该行执行对应逻辑（结合上下文理解）
    }
    #: 返回结果并结束当前函数
    return render(request, 'blog/user_profile.html', ctx)

#: 装饰器：为下一个定义附加「login_required」行为（权限、缓存、注册信号等）
@login_required
# 迭代#191: user_settings视图docstring
# 迭代#192: user_settings(request) -> HttpResponse 类型提示
# 迭代#193: user_settings分区域处理注释
# 迭代#194: user_settings头像Pillow验证注释
def user_settings(request: HttpRequest) -> HttpResponse:
    """用户设置页：修改基本资料 / 上传头像 / 修改密码。

    GET：渲染设置表单，回填当前用户数据。
    POST：根据提交的区域表单分别处理：
    - ``profile_form``：nickname（截断50字）、introduction（bleach 净化纯文本，截断500字）；
    - ``avatar_form``：avatar 上传（Pillow 验证真实图片，≤2MB，仅 jpg/png/gif/webp）；
    - ``password_form``：旧密码校验、新密码≥8位、两次一致。

    每个区域独立处理，修改成功后通过 messages 提示。

    Args:
        request: 当前 HttpRequest 对象。

    Returns:
        HttpResponse: GET 时渲染设置页；POST 后重定向回设置页并带 flash 消息。
    """
    # 头像上传允许的扩展名白名单
    #: 定义变量「AVATAR_EXTS」，保存对应数据
    AVATAR_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    # 头像大小上限 2MB
    #: 定义变量「AVATAR_MAX_BYTES」，保存对应数据
    AVATAR_MAX_BYTES = 2 * 1024 * 1024

    #: 条件判断：条件成立时执行该分支
    if request.method == 'POST':
        # 通过表单提交的按钮名称区分当前处理哪个区域
        #: 条件判断：条件成立时执行该分支
        if 'profile_form' in request.POST:
            # ---- 区域A：基本资料 ----
            #: 读取本次请求的 POST 数据
            nickname = (request.POST.get('nickname') or '').strip()[:50]
            #: 读取本次请求的 POST 数据
            introduction = request.POST.get('introduction') or ''
            # 用 bleach 净化为纯文本（不允许任何 HTML 标签），防止 XSS
            #: 定义变量「introduction」，保存对应数据
            introduction = bleach.clean(introduction, tags=[], attributes={}, strip=True)
            #: 定义变量「introduction」，保存对应数据
            introduction = introduction[:500]
            #: 读取本次请求的 user 数据
            request.user.nickname = nickname
            #: 读取本次请求的 user 数据
            request.user.introduction = introduction
            #: 读取本次请求的 user 数据
            request.user.save(update_fields=['nickname', 'introduction'])
            #: 向用户闪现一条提示消息（下次请求展示）
            messages.success(request, msg('auth.profile_updated'))
            #: 返回结果并结束当前函数
            return redirect('user_settings')

        #: 否则若该条件成立则进入此分支
        elif 'avatar_form' in request.POST:
            # ---- 区域B：头像上传 ----
            #: 读取本次请求的 FILES 数据
            avatar_file = request.FILES.get('avatar')
            #: 条件判断：条件成立时执行该分支
            if not avatar_file:
                #: 向用户闪现一条提示消息（下次请求展示）
                messages.error(request, msg('auth.avatar_choose'))
            #: 以上条件均不成立时的兜底分支
            else:
                # 验证扩展名白名单
                #: 定义变量「ext」，保存对应数据
                ext = os.path.splitext(avatar_file.name)[1].lower()
                #: 条件判断：条件成立时执行该分支
                if ext not in AVATAR_EXTS:
                    #: 向用户闪现一条提示消息（下次请求展示）
                    messages.error(request, msg('auth.avatar_invalid_type'))
                #: 否则若该条件成立则进入此分支
                elif avatar_file.size > AVATAR_MAX_BYTES:
                    #: 向用户闪现一条提示消息（下次请求展示）
                    messages.error(request, msg('auth.avatar_too_large'))
                #: 以上条件均不成立时的兜底分支
                else:
                    # 用 Pillow 验证是否为真实图片（防止伪装扩展名）
                    #: 尝试执行可能出错的代码
                    try:
                        #: 定义变量「img」，保存对应数据
                        img = Image.open(avatar_file)
                        #: 调用「img.verify」执行相应逻辑
                        img.verify()
                        #: 调用「avatar_file.seek」执行相应逻辑
                        avatar_file.seek(0)
                    #: 捕获并处理异常，避免程序中断
                    except Exception:
                        #: 向用户闪现一条提示消息（下次请求展示）
                        messages.error(request, msg('auth.avatar_not_image'))
                    #: 以上条件均不成立时的兜底分支
                    else:
                        #: 读取本次请求的 user 数据
                        request.user.avatar = avatar_file
                        #: 读取本次请求的 user 数据
                        request.user.save(update_fields=['avatar'])
                        #: 向用户闪现一条提示消息（下次请求展示）
                        messages.success(request, msg('auth.avatar_updated'))
            #: 返回结果并结束当前函数
            return redirect('user_settings')

        #: 否则若该条件成立则进入此分支
        elif 'password_form' in request.POST:
            # ---- 区域C：修改密码 ----
            #: 读取本次请求的 POST 数据
            old_password = request.POST.get('old_password', '')
            #: 读取本次请求的 POST 数据
            new_password = request.POST.get('new_password', '')
            #: 读取本次请求的 POST 数据
            confirm_password = request.POST.get('confirm_password', '')
            # 校验旧密码
            #: 条件判断：条件成立时执行该分支
            if not request.user.check_password(old_password):
                #: 向用户闪现一条提示消息（下次请求展示）
                messages.error(request, msg('auth.old_password_wrong'))
            #: 否则若该条件成立则进入此分支
            elif len(new_password) < 8:
                #: 向用户闪现一条提示消息（下次请求展示）
                messages.error(request, msg('auth.new_password_too_short'))
            #: 否则若该条件成立则进入此分支
            elif new_password != confirm_password:
                #: 向用户闪现一条提示消息（下次请求展示）
                messages.error(request, msg('auth.new_password_mismatch'))
            #: 以上条件均不成立时的兜底分支
            else:
                #: 读取本次请求的 user 数据
                request.user.set_password(new_password)
                #: 保存对象（INSERT/UPDATE），可能触发模型信号
                request.user.save()
                # 修改密码后重新登录，保持会话有效
                #: 将用户登录状态写入会话
                login(request, request.user)
                #: 向用户闪现一条提示消息（下次请求展示）
                messages.success(request, msg('auth.password_changed'))
            #: 返回结果并结束当前函数
            return redirect('user_settings')

    # GET：渲染设置表单，回填当前用户数据
    # Bug9 任务1 补充：个人中心「设置」页此前没有徽章 / 成就入口，
    # 用户看不到自己的战绩。这里把徽章面板数据一并注入（本人视角 → viewer_is_owner=True），
    # 让 /settings/ 直接展示已获得徽章与折叠的未获得徽章（含获取方式与进度条）。
    # badge_panel_flat=True：面板外层已由 .settings-card 提供卡片外观，
    # partial 需去掉自身卡片样式，避免「卡片套卡片」。
    #: 定义变量「ctx」，保存对应数据
    ctx = {
        #: 配置项「active_nav」：字典/模型的该键设置为对应值
        'active_nav': 'settings',
        #: 读取本次请求的 user 数据
        'badge_panel': _build_badge_panel(request.user, True),
        #: 配置项「badge_panel_flat」：字典/模型的该键设置为对应值
        'badge_panel_flat': True,
    #: 该行执行对应逻辑（结合上下文理解）
    }
    #: 返回结果并结束当前函数
    return render(request, 'blog/user_settings.html', ctx)

#: 装饰器：为下一个定义附加「login_required」行为（权限、缓存、注册信号等）
@login_required
# 迭代#195: my_articles视图docstring
# 迭代#196: my_articles(request) -> HttpResponse 类型提示
def my_articles(request: HttpRequest) -> HttpResponse:
    """我的文章管理页：当前用户查看 / 筛选 / 搜索自己的全部文章（含草稿）。

    - 查询当前用户的所有文章（含草稿），按更新时间倒序；
    - 支持筛选：``?status=published|draft``（默认全部）；
    - 支持搜索：``?q=关键词`` 模糊匹配文章标题；
    - 分页每页 15 篇。

    Args:
        request: 当前 HttpRequest 对象。

    Returns:
        HttpResponse: 渲染后的我的文章管理页。
    """
    # 基础查询集：仅当前用户的文章，预加载分类，按更新时间倒序
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    qs = Article.objects.filter(author=request.user).select_related(
        #: 对查询结果按字段排序
        'category').order_by('-updated_at', '-id')
    # ---- 状态筛选 ----
    #: 读取本次请求的 GET 数据
    filter_status = request.GET.get('status', '')
    #: 条件判断：条件成立时执行该分支
    if filter_status in Article.Status.values:
        #: 定义变量「qs」，保存对应数据
        qs = qs.filter(status=filter_status)
    #: 以上条件均不成立时的兜底分支
    else:
        #: 定义变量「filter_status」，保存对应数据
        filter_status = ''   # 非法值回退为"全部"
    # ---- 标题搜索 ----
    #: 读取本次请求的 GET 数据
    search_q = request.GET.get('q', '').strip()
    #: 条件判断：条件成立时执行该分支
    if search_q:
        #: 定义变量「qs」，保存对应数据
        qs = qs.filter(title__icontains=search_q)
    # ---- 分页（每页 15 篇）----
    #: 定义变量「paginator」，保存对应数据
    paginator = Paginator(qs, 15)
    #: 读取本次请求的 GET 数据
    page_obj = paginator.get_page(request.GET.get('page'))
    # ---- 各状态文章计数（用于筛选标签栏显示数量）----
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    all_count = Article.objects.filter(author=request.user).count()
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    published_count = Article.objects.filter(
        #: 读取本次请求的 user 数据
        author=request.user, status=Article.Status.PUBLISHED).count()
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    draft_count = Article.objects.filter(
        #: 读取本次请求的 user 数据
        author=request.user, status=Article.Status.DRAFT).count()
    #: 定义变量「ctx」，保存对应数据
    ctx = {
        #: 配置项「page_obj」：字典/模型的该键设置为对应值
        'page_obj': page_obj,
        #: 配置项「page_range」：字典/模型的该键设置为对应值
        'page_range': list(paginator.page_range),
        #: 配置项「filter_status」：字典/模型的该键设置为对应值
        'filter_status': filter_status,
        #: 配置项「search_q」：字典/模型的该键设置为对应值
        'search_q': search_q,
        #: 配置项「counts」：字典/模型的该键设置为对应值
        'counts': {
            #: 配置项「all」：字典/模型的该键设置为对应值
            'all': all_count,
            #: 配置项「published」：字典/模型的该键设置为对应值
            'published': published_count,
            #: 配置项「draft」：字典/模型的该键设置为对应值
            'draft': draft_count,
        #: 该行执行对应逻辑（结合上下文理解）
        },
        #: 配置项「active_nav」：字典/模型的该键设置为对应值
        'active_nav': 'my_articles',
    #: 该行执行对应逻辑（结合上下文理解）
    }
    #: 返回结果并结束当前函数
    return render(request, 'blog/my_articles.html', ctx)

#: 定义变量「ONLINE_WINDOW」，保存对应数据
ONLINE_WINDOW = timedelta(minutes=5)  # 在线判定窗口

def default_preferences() -> dict:
    """返回匿名用户使用的默认偏好字典（与 User 模型字段一一对应）。

    Returns:
        dict: 前端可直接消费的默认偏好。
    """
    #: 返回结果并结束当前函数
    return {
        #: 配置项「theme_color」：字典/模型的该键设置为对应值
        'theme_color': 'purple_pink',
        #: 配置项「custom_theme_color」：字典/模型的该键设置为对应值
        'custom_theme_color': '#a855f7',
        #: 配置项「font_size」：字典/模型的该键设置为对应值
        'font_size': 'medium',
        #: 配置项「line_height」：字典/模型的该键设置为对应值
        'line_height': 'normal',
        #: 配置项「font_family」：字典/模型的该键设置为对应值
        'font_family': 'sans',
        #: 配置项「effects_enabled」：字典/模型的该键设置为对应值
        'effects_enabled': True,
        #: 配置项「sound_enabled」：字典/模型的该键设置为对应值
        'sound_enabled': False,
        #: 配置项「eye_protection」：字典/模型的该键设置为对应值
        'eye_protection': False,
        #: 配置项「amoled_dark」：字典/模型的该键设置为对应值
        'amoled_dark': False,
        #: 配置项「birthday」：字典/模型的该键设置为对应值
        'birthday': '',
        #: 配置项「background_image」：字典/模型的该键设置为对应值
        'background_image': '',
        #: 配置项「signature」：字典/模型的该键设置为对应值
        'signature': '',
    #: 该行执行对应逻辑（结合上下文理解）
    }

def _preferences_dict(user) -> dict:
    """把当前用户的偏好序列化为 dict；匿名则返回默认值。

    Args:
        user: request.user（可能匿名）。

    Returns:
        dict: 偏好字典。
    """
    #: 条件判断：条件成立时执行该分支
    if not user or not getattr(user, 'is_authenticated', False):
        #: 返回结果并结束当前函数
        return default_preferences()
    #: 返回结果并结束当前函数
    return {
        #: 配置项「theme_color」：字典/模型的该键设置为对应值
        'theme_color': user.theme_color,
        #: 配置项「custom_theme_color」：字典/模型的该键设置为对应值
        'custom_theme_color': user.custom_theme_color,
        #: 配置项「font_size」：字典/模型的该键设置为对应值
        'font_size': user.font_size,
        #: 配置项「line_height」：字典/模型的该键设置为对应值
        'line_height': user.line_height,
        #: 配置项「font_family」：字典/模型的该键设置为对应值
        'font_family': user.font_family,
        #: 配置项「effects_enabled」：字典/模型的该键设置为对应值
        'effects_enabled': bool(user.effects_enabled),
        #: 配置项「sound_enabled」：字典/模型的该键设置为对应值
        'sound_enabled': bool(user.sound_enabled),
        #: 配置项「eye_protection」：字典/模型的该键设置为对应值
        'eye_protection': bool(user.eye_protection),
        #: 配置项「amoled_dark」：字典/模型的该键设置为对应值
        'amoled_dark': bool(user.amoled_dark),
        #: 配置项「birthday」：字典/模型的该键设置为对应值
        'birthday': user.birthday.isoformat() if user.birthday else '',
        #: 配置项「background_image」：字典/模型的该键设置为对应值
        'background_image': user.background_image.url if user.background_image else '',
        #: 配置项「signature」：字典/模型的该键设置为对应值
        'signature': user.signature,
    #: 该行执行对应逻辑（结合上下文理解）
    }

# ----------------------------- 1. 用户偏好 -----------------------------
def api_user_preferences(request: HttpRequest) -> JsonResponse:
    """用户偏好读取(GET)/更新(PUT)。

    - GET：登录用户返回其偏好，匿名返回默认值；
    - PUT：仅登录用户，JSON body 提交部分字段，逐字段校验取值合法性后保存。

    Args:
        request: 当前 HttpRequest。

    Returns:
        JsonResponse: GET 返回 {code:0,data:偏好}；PUT 返回最新偏好。
    """
    #: 条件判断：条件成立时执行该分支
    if request.method == 'GET':
        #: 返回结果并结束当前函数
        return _json_ok(_preferences_dict(request.user))

    #: 条件判断：条件成立时执行该分支
    if request.method == 'PUT':
        # 仅登录用户可写
        #: 条件判断：条件成立时执行该分支
        if not request.user.is_authenticated:
            #: 返回结果并结束当前函数
            return JsonResponse({'code': 401, 'msg': msg('auth.login_required')}, status=401)
        #: 尝试执行可能出错的代码
        try:
            #: 读取本次请求的 body 数据
            body = json.loads(request.body.decode('utf-8') or '{}')
        #: 捕获并处理异常，避免程序中断
        except (ValueError, UnicodeDecodeError):
            #: 返回结果并结束当前函数
            return _bad_request('请求体不是合法 JSON')
        #: 读取本次请求的 user 数据
        user = request.user
        # 允许更新的字段及其合法取值白名单
        #: 定义变量「CHOICE_MAP」，保存对应数据
        CHOICE_MAP = {
            #: 配置项「theme_color」：字典/模型的该键设置为对应值
            'theme_color': {'purple_pink', 'blue_green', 'orange_yellow', 'rose', 'custom'},
            #: 配置项「font_size」：字典/模型的该键设置为对应值
            'font_size': {'small', 'medium', 'large', 'xlarge'},
            #: 配置项「line_height」：字典/模型的该键设置为对应值
            'line_height': {'tight', 'normal', 'relaxed'},
            #: 配置项「font_family」：字典/模型的该键设置为对应值
            'font_family': {'sans', 'serif', 'mono'},
        #: 该行执行对应逻辑（结合上下文理解）
        }
        #: 定义变量「BOOL_FIELDS」，保存对应数据
        BOOL_FIELDS = {'effects_enabled', 'sound_enabled', 'eye_protection', 'amoled_dark'}
        #: 定义变量「update_fields」，保存对应数据（集合/元组）
        update_fields = []
        #: 循环遍历，逐个处理元素
        for field, allowed in CHOICE_MAP.items():
            #: 条件判断：条件成立时执行该分支
            if field in body:
                #: 定义变量「val」，保存对应数据
                val = str(body[field])
                #: 条件判断：条件成立时执行该分支
                if val not in allowed:
                    #: 返回结果并结束当前函数
                    return _bad_request(f'{field} 取值非法')
                #: 调用「setattr」执行相应逻辑
                setattr(user, field, val)
                #: 调用「update_fields.append」执行相应逻辑
                update_fields.append(field)
        #: 循环遍历，逐个处理元素
        for field in BOOL_FIELDS:
            #: 条件判断：条件成立时执行该分支
            if field in body:
                #: 调用「setattr」执行相应逻辑
                setattr(user, field, bool(body[field]))
                #: 调用「update_fields.append」执行相应逻辑
                update_fields.append(field)
        #: 条件判断：条件成立时执行该分支
        if 'custom_theme_color' in body:
            #: 定义变量「val」，保存对应数据
            val = str(body['custom_theme_color']).strip()[:7]
            # 仅允许 # 开头的 HEX 颜色，防止注入
            #: 条件判断：条件成立时执行该分支
            if val and not re.match(r'^#[0-9a-fA-F]{6}$', val):
                #: 返回结果并结束当前函数
                return _bad_request('自定义主题色必须是 #RRGGBB 形式的 HEX 值')
            #: 定义实例/类属性「user.custom_theme_color」，保存对应数据
            user.custom_theme_color = val
            #: 调用「update_fields.append」执行相应逻辑
            update_fields.append('custom_theme_color')
        #: 条件判断：条件成立时执行该分支
        if 'signature' in body:
            #: 定义实例/类属性「user.signature」，保存对应数据
            user.signature = str(body['signature']).strip()[:200]
            #: 调用「update_fields.append」执行相应逻辑
            update_fields.append('signature')
        #: 条件判断：条件成立时执行该分支
        if 'birthday' in body:
            #: 定义变量「val」，保存对应数据
            val = str(body['birthday']).strip()
            #: 条件判断：条件成立时执行该分支
            if val:
                #: 尝试执行可能出错的代码
                try:
                    #: 从模块「datetime」导入所需对象
                    from datetime import date as _date
                    #: 定义实例/类属性「user.birthday」，保存对应数据
                    user.birthday = _date.fromisoformat(val)
                #: 捕获并处理异常，避免程序中断
                except ValueError:
                    #: 返回结果并结束当前函数
                    return _bad_request('birthday 必须是 YYYY-MM-DD 形式')
            #: 以上条件均不成立时的兜底分支
            else:
                #: 定义实例/类属性「user.birthday」，保存对应数据
                user.birthday = None
            #: 调用「update_fields.append」执行相应逻辑
            update_fields.append('birthday')
        #: 条件判断：条件成立时执行该分支
        if update_fields:
            #: 调用「user.save」执行相应逻辑
            user.save(update_fields=update_fields)
        #: 返回结果并结束当前函数
        return _json_ok(_preferences_dict(user))

    #: 返回结果并结束当前函数
    return JsonResponse({'detail': '仅支持 GET / PUT'}, status=405)

# ----------------------------- 4. 收藏夹分类管理（C10） -----------------------------
#: 装饰器：为下一个定义附加「login_required」行为（权限、缓存、注册信号等）
@login_required
def api_favorite_folder_list(request: HttpRequest) -> JsonResponse:
    """收藏夹列表(GET)/创建(POST)。"""
    #: 条件判断：条件成立时执行该分支
    if request.method == 'GET':
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        folders = (FavoriteFolder.objects.filter(user=request.user)
                   #: 使用聚合函数做统计查询
                   .annotate(cnt=Count('favorites'))
                   #: 对查询结果按字段排序
                   .order_by('-created_at'))
        #: 定义变量「data」，保存对应数据（集合/元组）
        data = [{'id': f.id, 'name': f.name, 'count': f.cnt,
                 #: 配置项「created_at」：字典/模型的该键设置为对应值
                 'created_at': f.created_at.isoformat()} for f in folders]
        #: 返回结果并结束当前函数
        return _json_ok(data)
    #: 条件判断：条件成立时执行该分支
    if request.method == 'POST':
        #: 尝试执行可能出错的代码
        try:
            #: 读取本次请求的 body 数据
            body = json.loads(request.body.decode('utf-8') or '{}')
        #: 捕获并处理异常，避免程序中断
        except (ValueError, UnicodeDecodeError):
            #: 读取本次请求的 POST 数据
            body = request.POST
        #: 定义变量「name」，保存对应数据
        name = str(body.get('name', '')).strip()[:50]
        #: 条件判断：条件成立时执行该分支
        if not name:
            #: 返回结果并结束当前函数
            return _bad_request('收藏夹名称不能为空')
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        folder = FavoriteFolder.objects.create(user=request.user, name=name)
        #: 返回结果并结束当前函数
        return _json_ok({'id': folder.id, 'name': folder.name})
    #: 返回结果并结束当前函数
    return JsonResponse({'detail': '仅支持 GET / POST'}, status=405)

#: 装饰器：为下一个定义附加「login_required」行为（权限、缓存、注册信号等）
@login_required
def api_favorite_folder_detail(request: HttpRequest, pk: int) -> JsonResponse:
    """收藏夹重命名(PUT)/删除(DELETE)。删除时其下收藏回退到默认夹(folder=None)。"""
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    folder = get_object_or_404(FavoriteFolder, pk=pk, user=request.user)
    #: 条件判断：条件成立时执行该分支
    if request.method == 'PUT':
        #: 尝试执行可能出错的代码
        try:
            #: 读取本次请求的 body 数据
            body = json.loads(request.body.decode('utf-8') or '{}')
        #: 捕获并处理异常，避免程序中断
        except (ValueError, UnicodeDecodeError):
            #: 读取本次请求的 POST 数据
            body = request.POST
        #: 定义变量「name」，保存对应数据
        name = str(body.get('name', '')).strip()[:50]
        #: 条件判断：条件成立时执行该分支
        if not name:
            #: 返回结果并结束当前函数
            return _bad_request('收藏夹名称不能为空')
        #: 定义实例/类属性「folder.name」，保存对应数据
        folder.name = name
        #: 调用「folder.save」执行相应逻辑
        folder.save(update_fields=['name'])
        #: 返回结果并结束当前函数
        return _json_ok({'id': folder.id, 'name': folder.name})
    #: 条件判断：条件成立时执行该分支
    if request.method == 'DELETE':
        # 其下收藏移到默认文件夹（folder 置空）
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        Favorite.objects.filter(folder=folder).update(folder=None)
        #: 删除对象，注意级联与权限
        folder.delete()
        #: 返回结果并结束当前函数
        return _json_ok({'success': True})
    #: 返回结果并结束当前函数
    return JsonResponse({'detail': '仅支持 PUT / DELETE'}, status=405)

# ----------------------------- 5. 通知中心（F8） -----------------------------
def api_notification_list(request: HttpRequest) -> JsonResponse:
    """通知列表：GET /api/notifications/（分页，未读优先）。"""
    #: 条件判断：条件成立时执行该分支
    if not request.user.is_authenticated:
        #: 返回结果并结束当前函数
        return JsonResponse({'code': 401, 'msg': msg('auth.login_required')}, status=401)
    #: 对查询结果按字段排序
    qs = request.user.notifications.all().order_by('-is_read', '-created_at')
    #: 读取本次请求的 GET 数据
    page_size = _clean_page_size(request.GET.get('page_size')) or settings.PAGE_SIZE
    #: 定义变量「paginator」，保存对应数据
    paginator = Paginator(qs, page_size)
    #: 读取本次请求的 GET 数据
    page_num = _clamp_page_number(request.GET.get('page'), paginator.num_pages)
    #: 定义变量「page」，保存对应数据
    page = paginator.get_page(page_num)
    #: 定义变量「data」，保存对应数据（集合/元组）
    data = [{
        #: 配置项「id」：字典/模型的该键设置为对应值
        'id': n.id, 'type': n.type, 'title': n.title, 'content': n.content,
        #: 配置项「related_url」：字典/模型的该键设置为对应值
        'related_url': n.related_url, 'is_read': n.is_read,
        #: 配置项「created_at」：字典/模型的该键设置为对应值
        'created_at': n.created_at.isoformat(),
    #: 该行执行对应逻辑（结合上下文理解）
    } for n in page.object_list]
    #: 返回结果并结束当前函数
    return _json_ok({
        #: 配置项「results」：字典/模型的该键设置为对应值
        'results': data, 'page': page.number,
        #: 配置项「num_pages」：字典/模型的该键设置为对应值
        'num_pages': paginator.num_pages, 'total': paginator.count,
    #: 该行执行对应逻辑（结合上下文理解）
    })

#: 装饰器：为下一个定义附加「login_required」行为（权限、缓存、注册信号等）
@login_required
def api_notification_read(request: HttpRequest, pk: int) -> JsonResponse:
    """标记单条通知已读。"""
    #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
    note = get_object_or_404(Notification, pk=pk, user=request.user)
    #: 条件判断：条件成立时执行该分支
    if not note.is_read:
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        Notification.objects.filter(pk=note.pk).update(is_read=True)
    #: 返回结果并结束当前函数
    return _json_ok({'success': True})

#: 装饰器：为下一个定义附加「login_required」行为（权限、缓存、注册信号等）
@login_required
def api_notification_read_all(request: HttpRequest) -> JsonResponse:
    """全部标记已读。"""
    #: 读取本次请求的 user 数据
    request.user.notifications.filter(is_read=False).update(is_read=True)
    #: 返回结果并结束当前函数
    return _json_ok({'success': True})

def api_notification_unread_count(request: HttpRequest) -> JsonResponse:
    """未读通知计数。"""
    #: 条件判断：条件成立时执行该分支
    if not request.user.is_authenticated:
        #: 返回结果并结束当前函数
        return _json_ok({'count': 0})
    #: 返回结果并结束当前函数
    return _json_ok({'count': request.user.notifications.filter(is_read=False).count()})

# ----------------------------- 9. 成就徽章（F10） -----------------------------
def check_and_award_badges(user) -> list:
    """检查用户是否达成新徽章，达成则创建 UserBadge 并发放通知。

    统计口径：
    - articles：已发布文章数；
    - comments：评论数；
    - likes：其全部文章累计获赞；
    - days：注册天数（用 date_joined）。

    Args:
        user: 目标用户实例。

    Returns:
        list: 本次新获得的 Badge 对象列表。
    """
    #: 条件判断：条件成立时执行该分支
    if not user or not getattr(user, 'is_authenticated', False):
        #: 返回结果并结束当前函数
        return []
    #: 尝试执行可能出错的代码
    try:
        #: 定义变量「stats」，保存对应数据
        stats = {
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'articles': Article.objects.filter(author=user, status=Article.Status.PUBLISHED).count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'comments': Comment.objects.filter(user=user).count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'likes': Article.objects.filter(author=user).aggregate(s=Sum('likes'))['s'] or 0,
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'views': Article.objects.filter(author=user).aggregate(s=Sum('views'))['s'] or 0,
            #: 获取当前时间（时区感知），统一时间口径
            'days': (timezone.now() - user.date_joined).days if user.date_joined else 0,
        #: 该行执行对应逻辑（结合上下文理解）
        }
        #: 定义变量「newly」，保存对应数据（集合/元组）
        newly = []
        #: 循环遍历，逐个处理元素
        for badge in Badge.objects.all():
            #: 条件判断：条件成立时执行该分支
            if stats.get(badge.condition_type, 0) >= badge.condition_value:
                #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
                _, created = UserBadge.objects.get_or_create(user=user, badge=badge)
                #: 条件判断：条件成立时执行该分支
                if created:
                    #: 调用「newly.append」执行相应逻辑
                    newly.append(badge)
                    # 发放系统通知
                    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
                    Notification.objects.create(
                        #: 定义变量「user」，保存对应数据
                        user=user, type=Notification.Type.SYSTEM,
                        #: 定义变量「title」，保存对应数据
                        title=f'获得新徽章：{badge.name}',
                        #: 定义变量「content」，保存对应数据
                        content=f'恭喜！你达成了「{badge.name}」：{badge.description}',
                    #: 该行执行对应逻辑（结合上下文理解）
                    )
        #: 返回结果并结束当前函数
        return newly
    #: 捕获并处理异常，避免程序中断
    except Exception as exc:  # noqa: BLE001
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.warning('徽章检查失败: %s', exc)
        #: 返回结果并结束当前函数
        return []

#: 装饰器：为下一个定义附加「login_required」行为（权限、缓存、注册信号等）
@login_required
def api_user_badges(request: HttpRequest) -> JsonResponse:
    """当前用户徽章列表：GET /api/user/badges/。"""
    #: ORM 预加载关联，减少 N+1 查询提升性能
    ubs = (request.user.user_badges.select_related('badge')
           #: 对查询结果按字段排序
           .order_by('-earned_at'))
    #: 定义变量「data」，保存对应数据（集合/元组）
    data = [{
        #: 配置项「id」：字典/模型的该键设置为对应值
        'id': ub.badge.id, 'name': ub.badge.name, 'icon': ub.badge.icon,
        #: 配置项「description」：字典/模型的该键设置为对应值
        'description': ub.badge.description, 'earned_at': ub.earned_at.isoformat(),
    #: 该行执行对应逻辑（结合上下文理解）
    } for ub in ubs]
    #: 返回结果并结束当前函数
    return _json_ok(data)

# ----------------------------- 10. 在线状态（F12） -----------------------------
def api_online_users(request: HttpRequest) -> JsonResponse:
    """在线用户：GET /api/online_users/，返回最近 5 分钟活跃用户数与列表。"""
    #: 获取当前时间（时区感知），统一时间口径
    since = timezone.now() - ONLINE_WINDOW
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    qs = User.objects.filter(last_active__gte=since).order_by('-last_active')
    #: 定义变量「count」，保存对应数据
    count = qs.count()
    #: 定义变量「users」，保存对应数据（集合/元组）
    users = [{
        #: 配置项「username」：字典/模型的该键设置为对应值
        'username': u.username,
        #: 配置项「nickname」：字典/模型的该键设置为对应值
        'nickname': u.nickname or u.username,
        #: 配置项「avatar」：字典/模型的该键设置为对应值
        'avatar': u.avatar.url if u.avatar else '',
    #: 该行执行对应逻辑（结合上下文理解）
    } for u in qs[:20]]
    #: 返回结果并结束当前函数
    return _json_ok({'count': count, 'users': users})

#: 装饰器：为下一个定义附加「login_required」行为（权限、缓存、注册信号等）
@login_required
def notifications_page(request: HttpRequest) -> HttpResponse:
    """通知中心实际页面（bug15）：当前用户全部通知，支持只看未读、分页。

    Args:
        request: 当前 HttpRequest，需登录；``?filter=unread`` 只看未读。

    Returns:
        HttpResponse: 渲染 blog/notifications.html。
    """
    #: 对查询结果按字段排序
    qs = request.user.notifications.all().order_by('-is_read', '-created_at')
    #: 读取本次请求的 GET 数据
    show_unread = request.GET.get('filter') == 'unread'
    #: 条件判断：条件成立时执行该分支
    if show_unread:
        #: 定义变量「qs」，保存对应数据
        qs = qs.filter(is_read=False)
    #: 该行执行对应逻辑（结合上下文理解）
    page_obj, _ = _paginate_qs(request, qs, 15)
    #: 定义变量「ctx」，保存对应数据
    ctx = {
        #: 配置项「page_obj」：字典/模型的该键设置为对应值
        'page_obj': page_obj,
        #: 读取本次请求的 user 数据
        'total_count': request.user.notifications.count(),
        #: 读取本次请求的 user 数据
        'unread_count': request.user.notifications.filter(is_read=False).count(),
        #: 配置项「show_unread」：字典/模型的该键设置为对应值
        'show_unread': show_unread,
        #: 配置项「active_nav」：字典/模型的该键设置为对应值
        'active_nav': 'notifications',
    #: 该行执行对应逻辑（结合上下文理解）
    }
    #: 返回结果并结束当前函数
    return render(request, 'blog/notifications.html', ctx)

#: 装饰器：为下一个定义附加「login_required」行为（权限、缓存、注册信号等）
@login_required
def my_favorites(request: HttpRequest) -> HttpResponse:
    """我的收藏（bug14）：当前用户收藏的已发布文章，分页。"""
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    article_ids = Favorite.objects.filter(user=request.user).values_list('article_id', flat=True)
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    qs = (Article.objects.filter(id__in=article_ids, status=Article.Status.PUBLISHED)
          #: ORM 预加载关联，减少 N+1 查询提升性能
          .select_related('category', 'author').order_by('-id'))
    #: 该行执行对应逻辑（结合上下文理解）
    page_obj, _ = _paginate_qs(request, qs, 10)
    #: 返回结果并结束当前函数
    return render(request, 'blog/my_collection.html', {
        #: 配置项「page_obj」：字典/模型的该键设置为对应值
        'page_obj': page_obj, 'kind': 'articles',
        #: 配置项「page_icon」：字典/模型的该键设置为对应值
        'page_icon': '⭐', 'page_title': '我的收藏',
        #: 配置项「empty_text」：字典/模型的该键设置为对应值
        'empty_text': '还没有收藏文章，看到喜欢的点个小星星吧~',
        #: 配置项「active_nav」：字典/模型的该键设置为对应值
        'active_nav': 'favorites'})

#: 装饰器：为下一个定义附加「login_required」行为（权限、缓存、注册信号等）
@login_required
def my_liked(request: HttpRequest) -> HttpResponse:
    """我的点赞（bug14）：当前浏览器会话内点过赞的文章，分页。

    文章点赞记录保存在 session（``liked_article_ids``），故反映当前浏览器；
    换浏览器或结束会话后该列表可能不同。
    """
    #: 定义变量「liked_ids」，保存对应数据
    liked_ids = request.session.get('liked_article_ids', [])
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    qs = (Article.objects.filter(id__in=liked_ids, status=Article.Status.PUBLISHED)
          #: ORM 预加载关联，减少 N+1 查询提升性能
          .select_related('category', 'author').order_by('-id'))
    #: 该行执行对应逻辑（结合上下文理解）
    page_obj, _ = _paginate_qs(request, qs, 10)
    #: 返回结果并结束当前函数
    return render(request, 'blog/my_collection.html', {
        #: 配置项「page_obj」：字典/模型的该键设置为对应值
        'page_obj': page_obj, 'kind': 'articles',
        #: 配置项「page_icon」：字典/模型的该键设置为对应值
        'page_icon': '👍', 'page_title': '我的点赞',
        #: 配置项「empty_text」：字典/模型的该键设置为对应值
        'empty_text': '还没有点过赞，去给喜欢的文章比个心吧~',
        #: 配置项「active_nav」：字典/模型的该键设置为对应值
        'active_nav': 'liked'})

#: 装饰器：为下一个定义附加「login_required」行为（权限、缓存、注册信号等）
@login_required
def my_comments(request: HttpRequest) -> HttpResponse:
    """我的评论（bug14）：当前用户发表过的全部评论（含待审核），分页。"""
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    qs = (Comment.objects.filter(user=request.user).select_related('article')
          #: 对查询结果按字段排序
          .order_by('-created_at'))
    #: 该行执行对应逻辑（结合上下文理解）
    page_obj, _ = _paginate_qs(request, qs, 10)
    #: 返回结果并结束当前函数
    return render(request, 'blog/my_collection.html', {
        #: 配置项「page_obj」：字典/模型的该键设置为对应值
        'page_obj': page_obj, 'kind': 'comments',
        #: 配置项「page_icon」：字典/模型的该键设置为对应值
        'page_icon': '💬', 'page_title': '我的评论',
        #: 配置项「empty_text」：字典/模型的该键设置为对应值
        'empty_text': '还没有发表过评论，来抢沙发吧~',
        #: 配置项「active_nav」：字典/模型的该键设置为对应值
        'active_nav': 'my_comments'})

#: 装饰器：为下一个定义附加「login_required」行为（权限、缓存、注册信号等）
@login_required
def reading_history_page(request: HttpRequest) -> HttpResponse:
    """阅读历史（bug14）：页面外壳，列表由前端 JS 从 localStorage 渲染。"""
    #: 返回结果并结束当前函数
    return render(request, 'blog/reading_history.html', {
        #: 配置项「page_icon」：字典/模型的该键设置为对应值
        'page_icon': '📚', 'page_title': '阅读历史',
        #: 配置项「active_nav」：字典/模型的该键设置为对应值
        'active_nav': 'reading_history'})

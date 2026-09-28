# -*- coding: utf-8 -*-

"""用户域：资料、设置、偏好、徽章、在线状态、通知、收藏夹与个人中心。"""

import json
import logging
import os
import re
import uuid
from datetime import datetime, timedelta
import bleach
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Avg, Count, F, Min, Q, Sum
from django.http import (
    FileResponse, Http404, HttpRequest, HttpResponse,
    HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound,
    HttpResponseNotModified, HttpResponsePermanentRedirect,
    HttpResponseRedirect, JsonResponse, StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from PIL import Image
from ..models import (
    AccessLog, Article, Badge, Category, Comment, CommentReport,
    EditLog, Favorite, FavoriteFolder, ModerationLog, Notification,
    PromotionRequest, ModerationSettings, Rating, Series, ShortLink,
    SiteNotice, Tag, User, UserBadge,
)
from ..services.site_messages import msg

from .common import AVATAR_MAX_BYTES, _bad_request, _clamp_page_number, _clean_page_size, _json_ok, _paginate_qs, logger


logger = logging.getLogger('blog.views')

def _user_profile_cached(username, timeout=600):
    # 第2轮迭代#67: 用户资料缓存——个人主页作者信息短 TTL 缓存
    key = f'user_profile_{username}'
    return cache.get_or_set(
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
    pub_articles = Article.objects.filter(
        author=profile_user, status=Article.Status.PUBLISHED)
    stats = {
        'articles': pub_articles.count(),
        'comments': Comment.objects.filter(user=profile_user).count(),
        'likes': pub_articles.aggregate(s=Sum('likes'))['s'] or 0,
        'views': pub_articles.aggregate(s=Sum('views'))['s'] or 0,
        'days': ((timezone.now() - profile_user.date_joined).days
                 if profile_user.date_joined else 0),
    }
    # ---- 2. 已获得徽章映射：badge_id -> 获得时间 ----
    earned = {ub.badge_id: ub.earned_at
              for ub in UserBadge.objects.filter(user=profile_user)}
    obtained, locked = [], []
    for badge in Badge.objects.all().order_by('condition_type', 'condition_value', 'id'):
        current = stats.get(badge.condition_type, 0) or 0
        need = badge.condition_value or 1
        # 进度百分比（0~100），已达标固定 100
        percent = 100 if current >= need else int(current * 100 / need)
        item = {
            'id': badge.id,
            'name': badge.name,
            'icon': badge.icon or '🏅',
            'description': badge.description,
            # 获取方式：优先用后台填写的说明，缺失时按条件类型生成兜底文案
            'how_to': badge.description or _BADGE_HOW_TO.get(badge.condition_type, '继续活跃即可解锁喵~'),
            'current': current,
            'need': need,
            'percent': percent,
            'remaining': max(0, need - current),
            'unit': _BADGE_UNITS.get(badge.condition_type, ''),
            'earned_at': earned.get(badge.id),
            'obtained': badge.id in earned,
        }
        (obtained if item['obtained'] else locked).append(item)
    # 已获得：最近获得的排最前；未获得：进度高的排前面（更容易达成的优先展示）
    obtained.sort(key=lambda x: (x['earned_at'] is None, -(x['earned_at'].timestamp() if x['earned_at'] else 0)))
    locked.sort(key=lambda x: (-x['percent'], x['need']))
    total = len(obtained) + len(locked)
    return {
        'obtained': obtained,
        'locked': locked,
        'total': total,
        'obtained_count': len(obtained),
        'locked_count': len(locked),
        'rate': int(len(obtained) * 100 / total) if total else 0,
        'has_any': bool(obtained),
        'is_owner': viewer_is_owner,
    }

#: 徽章条件类型 → 进度单位（用于面板上的「12/50 篇」这类展示）
_BADGE_UNITS = {
    'articles': '篇',
    'comments': '条',
    'likes': '个赞',
    'views': '次阅读',
    'days': '天',
}

#: 徽章条件类型 → 兜底「如何获得」文案（后台未填写 description 时使用）
_BADGE_HOW_TO = {
    'articles': '发布更多文章即可解锁喵~',
    'comments': '多和大家互动评论即可解锁喵~',
    'likes': '写出让大家喜欢的内容，收获更多点赞即可解锁喵~',
    'views': '让更多人读到你的文章即可解锁喵~',
    'days': '常回来看看，陪伴站点更久即可解锁喵~',
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
    profile_user = get_object_or_404(User, username=username)
    # ---- 查询该用户的已发布文章（分页，每页 10 篇）----
    article_qs = Article.objects.filter(
        author=profile_user, status=Article.Status.PUBLISHED
    ).select_related('category').prefetch_related('tags').order_by('-created_at', '-id')
    paginator = Paginator(article_qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    # ---- 统计数据：聚合查询，避免循环逐条 count ----
    published_articles = article_qs
    total_views = published_articles.aggregate(v=Sum('views'))['v'] or 0
    total_likes = published_articles.aggregate(l=Sum('likes'))['l'] or 0
    total_comments = published_articles.aggregate(c=Sum('comment_count'))['c'] or 0
    # 收藏数：该用户收藏的文章总数
    fav_count = Favorite.objects.filter(user=profile_user).count()
    user_stats = {
        'article_count': published_articles.count(),
        'total_views': total_views,
        'total_likes': total_likes,
        'total_comments': total_comments,
        'fav_count': fav_count,
    }
    # ---- 该用户收藏的文章列表（仅已发布文章）----
    # 通过 Favorite 表关联查询，select_related 预加载文章与作者
    fav_articles = Article.objects.filter(
        favorites__user=profile_user, status=Article.Status.PUBLISHED
    ).select_related('author', 'category').order_by('-favorites__created_at')[:20]
    # ---- 判断是否为本人访问 ----
    is_own_profile = request.user.is_authenticated and request.user == profile_user
    ctx = {
        'profile_user': profile_user,
        'page_obj': page_obj,
        'page_range': list(paginator.page_range),
        'user_stats': user_stats,
        'fav_articles': fav_articles,
        'is_own_profile': is_own_profile,
        # Bug9 任务1：徽章 / 成就可视化面板（已获得 + 折叠的未获得）
        'badge_panel': _build_badge_panel(profile_user, is_own_profile),
        'active_nav': 'home',
    }
    return render(request, 'blog/user_profile.html', ctx)

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
    AVATAR_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    # 头像大小上限 2MB
    AVATAR_MAX_BYTES = 2 * 1024 * 1024

    if request.method == 'POST':
        # 通过表单提交的按钮名称区分当前处理哪个区域
        if 'profile_form' in request.POST:
            # ---- 区域A：基本资料 ----
            nickname = (request.POST.get('nickname') or '').strip()[:50]
            introduction = request.POST.get('introduction') or ''
            # 用 bleach 净化为纯文本（不允许任何 HTML 标签），防止 XSS
            introduction = bleach.clean(introduction, tags=[], attributes={}, strip=True)
            introduction = introduction[:500]
            request.user.nickname = nickname
            request.user.introduction = introduction
            request.user.save(update_fields=['nickname', 'introduction'])
            messages.success(request, msg('auth.profile_updated'))
            return redirect('user_settings')

        elif 'avatar_form' in request.POST:
            # ---- 区域B：头像上传 ----
            avatar_file = request.FILES.get('avatar')
            if not avatar_file:
                messages.error(request, msg('auth.avatar_choose'))
            else:
                # 验证扩展名白名单
                ext = os.path.splitext(avatar_file.name)[1].lower()
                if ext not in AVATAR_EXTS:
                    messages.error(request, msg('auth.avatar_invalid_type'))
                elif avatar_file.size > AVATAR_MAX_BYTES:
                    messages.error(request, msg('auth.avatar_too_large'))
                else:
                    # 用 Pillow 验证是否为真实图片（防止伪装扩展名）
                    try:
                        img = Image.open(avatar_file)
                        img.verify()
                        avatar_file.seek(0)
                    except Exception:
                        messages.error(request, msg('auth.avatar_not_image'))
                    else:
                        request.user.avatar = avatar_file
                        request.user.save(update_fields=['avatar'])
                        messages.success(request, msg('auth.avatar_updated'))
            return redirect('user_settings')

        elif 'password_form' in request.POST:
            # ---- 区域C：修改密码 ----
            old_password = request.POST.get('old_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')
            # 校验旧密码
            if not request.user.check_password(old_password):
                messages.error(request, msg('auth.old_password_wrong'))
            elif len(new_password) < 8:
                messages.error(request, msg('auth.new_password_too_short'))
            elif new_password != confirm_password:
                messages.error(request, msg('auth.new_password_mismatch'))
            else:
                request.user.set_password(new_password)
                request.user.save()
                # 修改密码后重新登录，保持会话有效
                login(request, request.user)
                messages.success(request, msg('auth.password_changed'))
            return redirect('user_settings')

    # GET：渲染设置表单，回填当前用户数据
    # Bug9 任务1 补充：个人中心「设置」页此前没有徽章 / 成就入口，
    # 用户看不到自己的战绩。这里把徽章面板数据一并注入（本人视角 → viewer_is_owner=True），
    # 让 /settings/ 直接展示已获得徽章与折叠的未获得徽章（含获取方式与进度条）。
    # badge_panel_flat=True：面板外层已由 .settings-card 提供卡片外观，
    # partial 需去掉自身卡片样式，避免「卡片套卡片」。
    ctx = {
        'active_nav': 'settings',
        'badge_panel': _build_badge_panel(request.user, True),
        'badge_panel_flat': True,
    }
    return render(request, 'blog/user_settings.html', ctx)

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
    qs = Article.objects.filter(author=request.user).select_related(
        'category').order_by('-updated_at', '-id')
    # ---- 状态筛选 ----
    filter_status = request.GET.get('status', '')
    if filter_status in Article.Status.values:
        qs = qs.filter(status=filter_status)
    else:
        filter_status = ''   # 非法值回退为"全部"
    # ---- 标题搜索 ----
    search_q = request.GET.get('q', '').strip()
    if search_q:
        qs = qs.filter(title__icontains=search_q)
    # ---- 分页（每页 15 篇）----
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    # ---- 各状态文章计数（用于筛选标签栏显示数量）----
    all_count = Article.objects.filter(author=request.user).count()
    published_count = Article.objects.filter(
        author=request.user, status=Article.Status.PUBLISHED).count()
    draft_count = Article.objects.filter(
        author=request.user, status=Article.Status.DRAFT).count()
    ctx = {
        'page_obj': page_obj,
        'page_range': list(paginator.page_range),
        'filter_status': filter_status,
        'search_q': search_q,
        'counts': {
            'all': all_count,
            'published': published_count,
            'draft': draft_count,
        },
        'active_nav': 'my_articles',
    }
    return render(request, 'blog/my_articles.html', ctx)

ONLINE_WINDOW = timedelta(minutes=5)  # 在线判定窗口

def default_preferences() -> dict:
    """返回匿名用户使用的默认偏好字典（与 User 模型字段一一对应）。

    Returns:
        dict: 前端可直接消费的默认偏好。
    """
    return {
        'theme_color': 'purple_pink',
        'custom_theme_color': '#a855f7',
        'font_size': 'medium',
        'line_height': 'normal',
        'font_family': 'sans',
        'effects_enabled': True,
        'sound_enabled': False,
        'eye_protection': False,
        'amoled_dark': False,
        'birthday': '',
        'background_image': '',
        'signature': '',
    }

def _preferences_dict(user) -> dict:
    """把当前用户的偏好序列化为 dict；匿名则返回默认值。

    Args:
        user: request.user（可能匿名）。

    Returns:
        dict: 偏好字典。
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return default_preferences()
    return {
        'theme_color': user.theme_color,
        'custom_theme_color': user.custom_theme_color,
        'font_size': user.font_size,
        'line_height': user.line_height,
        'font_family': user.font_family,
        'effects_enabled': bool(user.effects_enabled),
        'sound_enabled': bool(user.sound_enabled),
        'eye_protection': bool(user.eye_protection),
        'amoled_dark': bool(user.amoled_dark),
        'birthday': user.birthday.isoformat() if user.birthday else '',
        'background_image': user.background_image.url if user.background_image else '',
        'signature': user.signature,
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
    if request.method == 'GET':
        return _json_ok(_preferences_dict(request.user))

    if request.method == 'PUT':
        # 仅登录用户可写
        if not request.user.is_authenticated:
            return JsonResponse({'code': 401, 'msg': msg('auth.login_required')}, status=401)
        try:
            body = json.loads(request.body.decode('utf-8') or '{}')
        except (ValueError, UnicodeDecodeError):
            return _bad_request('请求体不是合法 JSON')
        user = request.user
        # 允许更新的字段及其合法取值白名单
        CHOICE_MAP = {
            'theme_color': {'purple_pink', 'blue_green', 'orange_yellow', 'rose', 'custom'},
            'font_size': {'small', 'medium', 'large', 'xlarge'},
            'line_height': {'tight', 'normal', 'relaxed'},
            'font_family': {'sans', 'serif', 'mono'},
        }
        BOOL_FIELDS = {'effects_enabled', 'sound_enabled', 'eye_protection', 'amoled_dark'}
        update_fields = []
        for field, allowed in CHOICE_MAP.items():
            if field in body:
                val = str(body[field])
                if val not in allowed:
                    return _bad_request(f'{field} 取值非法')
                setattr(user, field, val)
                update_fields.append(field)
        for field in BOOL_FIELDS:
            if field in body:
                setattr(user, field, bool(body[field]))
                update_fields.append(field)
        if 'custom_theme_color' in body:
            val = str(body['custom_theme_color']).strip()[:7]
            # 仅允许 # 开头的 HEX 颜色，防止注入
            if val and not re.match(r'^#[0-9a-fA-F]{6}$', val):
                return _bad_request('自定义主题色必须是 #RRGGBB 形式的 HEX 值')
            user.custom_theme_color = val
            update_fields.append('custom_theme_color')
        if 'signature' in body:
            user.signature = str(body['signature']).strip()[:200]
            update_fields.append('signature')
        if 'birthday' in body:
            val = str(body['birthday']).strip()
            if val:
                try:
                    from datetime import date as _date
                    user.birthday = _date.fromisoformat(val)
                except ValueError:
                    return _bad_request('birthday 必须是 YYYY-MM-DD 形式')
            else:
                user.birthday = None
            update_fields.append('birthday')
        if update_fields:
            user.save(update_fields=update_fields)
        return _json_ok(_preferences_dict(user))

    return JsonResponse({'detail': '仅支持 GET / PUT'}, status=405)

# ----------------------------- 4. 收藏夹分类管理（C10） -----------------------------
@login_required
def api_favorite_folder_list(request: HttpRequest) -> JsonResponse:
    """收藏夹列表(GET)/创建(POST)。"""
    if request.method == 'GET':
        folders = (FavoriteFolder.objects.filter(user=request.user)
                   .annotate(cnt=Count('favorites'))
                   .order_by('-created_at'))
        data = [{'id': f.id, 'name': f.name, 'count': f.cnt,
                 'created_at': f.created_at.isoformat()} for f in folders]
        return _json_ok(data)
    if request.method == 'POST':
        try:
            body = json.loads(request.body.decode('utf-8') or '{}')
        except (ValueError, UnicodeDecodeError):
            body = request.POST
        name = str(body.get('name', '')).strip()[:50]
        if not name:
            return _bad_request('收藏夹名称不能为空')
        folder = FavoriteFolder.objects.create(user=request.user, name=name)
        return _json_ok({'id': folder.id, 'name': folder.name})
    return JsonResponse({'detail': '仅支持 GET / POST'}, status=405)

@login_required
def api_favorite_folder_detail(request: HttpRequest, pk: int) -> JsonResponse:
    """收藏夹重命名(PUT)/删除(DELETE)。删除时其下收藏回退到默认夹(folder=None)。"""
    folder = get_object_or_404(FavoriteFolder, pk=pk, user=request.user)
    if request.method == 'PUT':
        try:
            body = json.loads(request.body.decode('utf-8') or '{}')
        except (ValueError, UnicodeDecodeError):
            body = request.POST
        name = str(body.get('name', '')).strip()[:50]
        if not name:
            return _bad_request('收藏夹名称不能为空')
        folder.name = name
        folder.save(update_fields=['name'])
        return _json_ok({'id': folder.id, 'name': folder.name})
    if request.method == 'DELETE':
        # 其下收藏移到默认文件夹（folder 置空）
        Favorite.objects.filter(folder=folder).update(folder=None)
        folder.delete()
        return _json_ok({'success': True})
    return JsonResponse({'detail': '仅支持 PUT / DELETE'}, status=405)

# ----------------------------- 5. 通知中心（F8） -----------------------------
def api_notification_list(request: HttpRequest) -> JsonResponse:
    """通知列表：GET /api/notifications/（分页，未读优先）。"""
    if not request.user.is_authenticated:
        return JsonResponse({'code': 401, 'msg': msg('auth.login_required')}, status=401)
    qs = request.user.notifications.all().order_by('-is_read', '-created_at')
    page_size = _clean_page_size(request.GET.get('page_size')) or settings.PAGE_SIZE
    paginator = Paginator(qs, page_size)
    page_num = _clamp_page_number(request.GET.get('page'), paginator.num_pages)
    page = paginator.get_page(page_num)
    data = [{
        'id': n.id, 'type': n.type, 'title': n.title, 'content': n.content,
        'related_url': n.related_url, 'is_read': n.is_read,
        'created_at': n.created_at.isoformat(),
    } for n in page.object_list]
    return _json_ok({
        'results': data, 'page': page.number,
        'num_pages': paginator.num_pages, 'total': paginator.count,
    })

@login_required
def api_notification_read(request: HttpRequest, pk: int) -> JsonResponse:
    """标记单条通知已读。"""
    note = get_object_or_404(Notification, pk=pk, user=request.user)
    if not note.is_read:
        Notification.objects.filter(pk=note.pk).update(is_read=True)
    return _json_ok({'success': True})

@login_required
def api_notification_read_all(request: HttpRequest) -> JsonResponse:
    """全部标记已读。"""
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return _json_ok({'success': True})

def api_notification_unread_count(request: HttpRequest) -> JsonResponse:
    """未读通知计数。"""
    if not request.user.is_authenticated:
        return _json_ok({'count': 0})
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
    if not user or not getattr(user, 'is_authenticated', False):
        return []
    try:
        stats = {
            'articles': Article.objects.filter(author=user, status=Article.Status.PUBLISHED).count(),
            'comments': Comment.objects.filter(user=user).count(),
            'likes': Article.objects.filter(author=user).aggregate(s=Sum('likes'))['s'] or 0,
            'views': Article.objects.filter(author=user).aggregate(s=Sum('views'))['s'] or 0,
            'days': (timezone.now() - user.date_joined).days if user.date_joined else 0,
        }
        newly = []
        for badge in Badge.objects.all():
            if stats.get(badge.condition_type, 0) >= badge.condition_value:
                _, created = UserBadge.objects.get_or_create(user=user, badge=badge)
                if created:
                    newly.append(badge)
                    # 发放系统通知
                    Notification.objects.create(
                        user=user, type=Notification.Type.SYSTEM,
                        title=f'获得新徽章：{badge.name}',
                        content=f'恭喜！你达成了「{badge.name}」：{badge.description}',
                    )
        return newly
    except Exception as exc:  # noqa: BLE001
        logger.warning('徽章检查失败: %s', exc)
        return []

@login_required
def api_user_badges(request: HttpRequest) -> JsonResponse:
    """当前用户徽章列表：GET /api/user/badges/。"""
    ubs = (request.user.user_badges.select_related('badge')
           .order_by('-earned_at'))
    data = [{
        'id': ub.badge.id, 'name': ub.badge.name, 'icon': ub.badge.icon,
        'description': ub.badge.description, 'earned_at': ub.earned_at.isoformat(),
    } for ub in ubs]
    return _json_ok(data)

# ----------------------------- 10. 在线状态（F12） -----------------------------
def api_online_users(request: HttpRequest) -> JsonResponse:
    """在线用户：GET /api/online_users/，返回最近 5 分钟活跃用户数与列表。"""
    since = timezone.now() - ONLINE_WINDOW
    qs = User.objects.filter(last_active__gte=since).order_by('-last_active')
    count = qs.count()
    users = [{
        'username': u.username,
        'nickname': u.nickname or u.username,
        'avatar': u.avatar.url if u.avatar else '',
    } for u in qs[:20]]
    return _json_ok({'count': count, 'users': users})

@login_required
def notifications_page(request: HttpRequest) -> HttpResponse:
    """通知中心实际页面（bug15）：当前用户全部通知，支持只看未读、分页。

    Args:
        request: 当前 HttpRequest，需登录；``?filter=unread`` 只看未读。

    Returns:
        HttpResponse: 渲染 blog/notifications.html。
    """
    qs = request.user.notifications.all().order_by('-is_read', '-created_at')
    show_unread = request.GET.get('filter') == 'unread'
    if show_unread:
        qs = qs.filter(is_read=False)
    page_obj, _ = _paginate_qs(request, qs, 15)
    ctx = {
        'page_obj': page_obj,
        'total_count': request.user.notifications.count(),
        'unread_count': request.user.notifications.filter(is_read=False).count(),
        'show_unread': show_unread,
        'active_nav': 'notifications',
    }
    return render(request, 'blog/notifications.html', ctx)

@login_required
def my_favorites(request: HttpRequest) -> HttpResponse:
    """我的收藏（bug14）：当前用户收藏的已发布文章，分页。"""
    article_ids = Favorite.objects.filter(user=request.user).values_list('article_id', flat=True)
    qs = (Article.objects.filter(id__in=article_ids, status=Article.Status.PUBLISHED)
          .select_related('category', 'author').order_by('-id'))
    page_obj, _ = _paginate_qs(request, qs, 10)
    return render(request, 'blog/my_collection.html', {
        'page_obj': page_obj, 'kind': 'articles',
        'page_icon': '⭐', 'page_title': '我的收藏',
        'empty_text': '还没有收藏文章，看到喜欢的点个小星星吧~',
        'active_nav': 'favorites'})

@login_required
def my_liked(request: HttpRequest) -> HttpResponse:
    """我的点赞（bug14）：当前浏览器会话内点过赞的文章，分页。

    文章点赞记录保存在 session（``liked_article_ids``），故反映当前浏览器；
    换浏览器或结束会话后该列表可能不同。
    """
    liked_ids = request.session.get('liked_article_ids', [])
    qs = (Article.objects.filter(id__in=liked_ids, status=Article.Status.PUBLISHED)
          .select_related('category', 'author').order_by('-id'))
    page_obj, _ = _paginate_qs(request, qs, 10)
    return render(request, 'blog/my_collection.html', {
        'page_obj': page_obj, 'kind': 'articles',
        'page_icon': '👍', 'page_title': '我的点赞',
        'empty_text': '还没有点过赞，去给喜欢的文章比个心吧~',
        'active_nav': 'liked'})

@login_required
def my_comments(request: HttpRequest) -> HttpResponse:
    """我的评论（bug14）：当前用户发表过的全部评论（含待审核），分页。"""
    qs = (Comment.objects.filter(user=request.user).select_related('article')
          .order_by('-created_at'))
    page_obj, _ = _paginate_qs(request, qs, 10)
    return render(request, 'blog/my_collection.html', {
        'page_obj': page_obj, 'kind': 'comments',
        'page_icon': '💬', 'page_title': '我的评论',
        'empty_text': '还没有发表过评论，来抢沙发吧~',
        'active_nav': 'my_comments'})

@login_required
def reading_history_page(request: HttpRequest) -> HttpResponse:
    """阅读历史（bug14）：页面外壳，列表由前端 JS 从 localStorage 渲染。"""
    return render(request, 'blog/reading_history.html', {
        'page_icon': '📚', 'page_title': '阅读历史',
        'active_nav': 'reading_history'})

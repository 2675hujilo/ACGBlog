# -*- coding: utf-8 -*-

"""DRF API：文章、分类、标签、图片上传与 V2 ViewSet。"""

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
#: 从模块「django.conf」导入所需对象
from django.conf import settings
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
#: 从模块「django.utils.decorators」导入所需对象
from django.utils.decorators import method_decorator
#: 从模块「django.views.decorators.csrf」导入所需对象
from django.views.decorators.csrf import csrf_exempt
#: 从模块「PIL」导入所需对象
from PIL import Image
#: 从模块「rest_framework.decorators」导入所需对象
from rest_framework.decorators import action
#: 从模块「rest_framework」导入所需对象
from rest_framework import filters, permissions, status, throttling, viewsets
#: 从模块「rest_framework.authentication」导入所需对象
from rest_framework.authentication import SessionAuthentication
#: 从模块「rest_framework.exceptions」导入所需对象
from rest_framework.exceptions import PermissionDenied
#: 从模块「rest_framework.pagination」导入所需对象
from rest_framework.pagination import PageNumberPagination
#: 从模块「rest_framework.permissions」导入所需对象
from rest_framework.permissions import IsAuthenticated
#: 从模块「rest_framework.response」导入所需对象
from rest_framework.response import Response
#: 从模块「rest_framework.views」导入所需对象
from rest_framework.views import APIView
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
#: 从模块「..serializers」导入所需对象
from ..serializers import (
    #: 该行执行对应逻辑（结合上下文理解）
    ArticleDetailV2Serializer, ArticleListSerializer,
    #: 该行执行对应逻辑（结合上下文理解）
    ArticleSerializer, CategorySerializer, TagSerializer,
#: 该行执行对应逻辑（结合上下文理解）
)

#: 从模块「.common」导入所需对象
from .common import _base_qs, _filter_articles, logger


#: 定义变量「logger」，保存对应数据
logger = logging.getLogger('blog.views')

# 迭代#216: _Pagination类docstring完善
class _Pagination(PageNumberPagination):
    """DRF 接口分页器：默认每页 10 条，支持 ?page_size= 自定义（上限 50）。"""
    #: 定义变量「page_size」，保存对应数据
    page_size = 10                      # 默认每页条数
    #: 定义变量「page_size_query_param」，保存对应数据
    page_size_query_param = 'page_size'  # 允许客户端通过 ?page_size= 调整
    #: 定义变量「max_page_size」，保存对应数据
    max_page_size = 50                  # 单页上限，防止一次拉取过多数据

# 迭代#217: ArticleListCreateView类docstring完善
class ArticleListCreateView(APIView):
    """文章 新增 / 列表查询。GET /api/articles/，POST /api/articles/"""
    #: 定义变量「pagination_class」，保存对应数据
    pagination_class = _Pagination

    def get(self, request):
        """
        功能：获取「get」。

        参数：
          - request：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 该行执行对应逻辑（结合上下文理解）
        qs, _, _ = _filter_articles(request, _base_qs(request))
        #: 定义变量「paginator」，保存对应数据
        paginator = self.pagination_class()
        #: 定义变量「page」，保存对应数据
        page = paginator.paginate_queryset(qs, request, view=self)
        #: 定义变量「serializer」，保存对应数据
        serializer = ArticleListSerializer(page, many=True, context={'request': request})
        #: 返回结果并结束当前函数
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        """
        功能：处理「post」相关逻辑。

        参数：
          - request：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：含 Django ORM 数据库查询，注意查询性能与空结果处理。
        """
        #: 定义变量「serializer」，保存对应数据
        serializer = ArticleSerializer(data=request.data, context={'request': request})
        #: 调用「serializer.is_valid」执行相应逻辑
        serializer.is_valid(raise_exception=True)
        #: 读取本次请求的 user 数据
        article = serializer.save(author=request.user)
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        EditLog.objects.create(article=article, editor=request.user)
        #: 返回结果并结束当前函数
        return Response(ArticleSerializer(article, context={'request': request}).data,
                        #: 定义变量「status」，保存对应数据
                        status=status.HTTP_201_CREATED)

# 迭代#218: ArticleDetailView类docstring完善
class ArticleDetailView(APIView):
    """文章 单篇查询 / 修改 / 删除。/api/articles/<pk>/"""

    def _get_object(self, request, pk):
        """按主键取文章，并校验草稿可见权限。

        已发布文章任何人可见；草稿仅作者本人或管理员可见，否则抛 PermissionDenied。
        """
        #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
        article = get_object_or_404(Article, pk=pk)
        #: 条件判断：条件成立时执行该分支
        if article.status != Article.Status.PUBLISHED and (
                #: 读取本次请求的 user 数据
                not request.user.is_authenticated or
                #: 读取本次请求的 user 数据
                (article.author != request.user and not request.user.is_staff)):
            #: 主动抛出异常交由上层处理
            raise PermissionDenied('无权查看该草稿')
        #: 返回结果并结束当前函数
        return article

    def get(self, request, pk):
        """GET：返回单篇文章完整详情 JSON。"""
        #: 定义变量「article」，保存对应数据
        article = self._get_object(request, pk)
        #: 返回结果并结束当前函数
        return Response(ArticleSerializer(article, context={'request': request}).data)

    def put(self, request, pk):
        """PUT：全量更新文章。"""
        #: 返回结果并结束当前函数
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        """PATCH：部分更新文章。"""
        #: 返回结果并结束当前函数
        return self._update(request, pk, partial=True)

    def _update(self, request, pk, partial):
        """更新文章公共逻辑：校验权限 -> 序列化 -> 保存 -> 记录修改日志。"""
        #: 定义变量「article」，保存对应数据
        article = self._get_object(request, pk)
        #: 条件判断：条件成立时执行该分支
        if article.author != request.user and not request.user.is_staff:
            #: 主动抛出异常交由上层处理
            raise PermissionDenied('只能修改自己的文章')
        #: 定义变量「serializer」，保存对应数据
        serializer = ArticleSerializer(
            #: 该行执行对应逻辑（结合上下文理解）
            article, data=request.data, partial=partial, context={'request': request})
        #: 调用「serializer.is_valid」执行相应逻辑
        serializer.is_valid(raise_exception=True)
        #: 保存对象（INSERT/UPDATE），可能触发模型信号
        article = serializer.save()
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        EditLog.objects.create(article=article, editor=request.user)
        #: 返回结果并结束当前函数
        return Response(ArticleSerializer(article, context={'request': request}).data)

    def delete(self, request, pk):
        """DELETE：删除文章（仅作者本人或管理员）。"""
        #: 定义变量「article」，保存对应数据
        article = self._get_object(request, pk)
        #: 条件判断：条件成立时执行该分支
        if article.author != request.user and not request.user.is_staff:
            #: 主动抛出异常交由上层处理
            raise PermissionDenied('无权删除该文章')
        #: 删除对象，注意级联与权限
        article.delete()
        #: 返回结果并结束当前函数
        return Response(status=status.HTTP_204_NO_CONTENT)

class _CsrfExemptSessionAuthentication(SessionAuthentication):
    """CKEditor 图片对话框以隐藏 iframe 表单提交，无法带 X-CSRFToken，单独豁免。"""
    def enforce_csrf(self, request):
        """
        功能：处理「enforce csrf」相关逻辑。

        参数：
          - request：传入参数，含义结合函数体与调用处

        返回：无显式返回（None），多以副作用为主。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 返回结果并结束当前函数
        return

#: 装饰器：为下一个定义附加「method_decorator(csrf_exempt, name='dispatch')」行为（权限、缓存、注册信号等）
@method_decorator(csrf_exempt, name='dispatch')
# 迭代#219: ImageUploadView类docstring完善
class ImageUploadView(APIView):
    """富文本图片上传，兼容 CKEditor 两种契约：
    - 图片对话框（querystring 带 CKEditorFuncNum）：返回 <script> 回调；
    - 拖拽 / 粘贴上传：返回 {uploaded,fileName,url} JSON。"""
    #: 定义变量「authentication_classes」，保存对应数据（集合/元组）
    authentication_classes = [_CsrfExemptSessionAuthentication]
    #: 定义变量「permission_classes」，保存对应数据（集合/元组）
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        功能：处理「post」相关逻辑。

        参数：
          - request：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：使用 logger 记录运行信息，避免打印敏感数据。
        """
        #: 读取本次请求的 GET 数据
        func_num = request.GET.get('CKEditorFuncNum')

        def respond(ok, url='', message=''):
            """
            功能：处理「respond」相关逻辑。

            参数：
              - ok：传入参数，含义结合函数体与调用处
              - url（可选，有默认值）：传入参数，含义结合函数体与调用处
              - message（可选，有默认值）：传入参数，含义结合函数体与调用处

            返回：对应计算/查询结果。

            注意：保持函数单一职责；修改时确认调用方不受影响。
            """
            #: 条件判断：条件成立时执行该分支
            if func_num is not None:
                #: 定义变量「args」，保存对应数据
                args = json.dumps(
                    #: 该行执行对应逻辑（结合上下文理解）
                    [int(func_num), url, message], ensure_ascii=False)[1:-1]
                #: 返回结果并结束当前函数
                return HttpResponse(
                    #: 该行执行对应逻辑（结合上下文理解）
                    f'<script>window.parent.CKEDITOR.tools.callFunction({args});</script>')
            #: 条件判断：条件成立时执行该分支
            if ok:
                #: 返回结果并结束当前函数
                return JsonResponse(
                    #: 该行执行对应逻辑（结合上下文理解）
                    {'uploaded': 1, 'fileName': os.path.basename(url), 'url': url})
            #: 返回结果并结束当前函数
            return JsonResponse(
                #: 该行执行对应逻辑（结合上下文理解）
                {'uploaded': 0, 'error': {'message': message}}, status=400)

        #: 读取本次请求的 FILES 数据
        upload = request.FILES.get('upload') or request.FILES.get('file')
        #: 条件判断：条件成立时执行该分支
        if not upload:
            #: 返回结果并结束当前函数
            return respond(False, message='未收到图片文件')
        #: 定义变量「ext」，保存对应数据
        ext = os.path.splitext(upload.name)[1].lower()
        #: 条件判断：条件成立时执行该分支
        if ext not in settings.UPLOAD_IMAGE_EXTS:
            #: 返回结果并结束当前函数
            return respond(False, message='不支持的图片格式')
        #: 条件判断：条件成立时执行该分支
        if upload.size > settings.UPLOAD_IMAGE_MAX_BYTES:
            #: 返回结果并结束当前函数
            return respond(False, message='图片不能超过 8MB')
        # Pillow 校验真实图片，防止伪装扩展名
        # 迭代#220: ImageUploadView中图片打开异常处理
        #: 尝试执行可能出错的代码
        try:
            #: 定义变量「image」，保存对应数据
            image = Image.open(upload)
            #: 调用「image.verify」执行相应逻辑
            image.verify()
            #: 调用「upload.seek」执行相应逻辑
            upload.seek(0)
        #: 捕获并处理异常，避免程序中断
        except (Image.UnidentifiedImageError, OSError):
            #: 返回结果并结束当前函数
            return respond(False, message='文件不是有效图片')

        #: 该行执行对应逻辑（结合上下文理解）
        year, month = datetime.now().strftime('%Y'), datetime.now().strftime('%m')
        #: 定义变量「rel_dir」，保存对应数据
        rel_dir = os.path.join('uploads', year, month)
        #: 定义变量「abs_dir」，保存对应数据
        abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
        # 迭代#221: ImageUploadView中目录创建异常处理
        #: 尝试执行可能出错的代码
        try:
            #: 调用「os.makedirs」执行相应逻辑
            os.makedirs(abs_dir, exist_ok=True)
        #: 捕获并处理异常，避免程序中断
        except OSError as os_exc:
            #: 记录日志，便于排查（勿记录密码等敏感信息）
            logger.error('上传目录创建失败: %s', os_exc)
            #: 返回结果并结束当前函数
            return respond(False, message='服务器存储错误')
        #: 定义变量「filename」，保存对应数据
        filename = f'{uuid.uuid4().hex}{ext}'
        # 迭代#222: ImageUploadView中文件写入异常处理
        #: 尝试执行可能出错的代码
        try:
            #: 上下文管理：进入时获取资源、退出时自动释放
            with open(os.path.join(abs_dir, filename), 'wb') as fp:
                #: 循环遍历，逐个处理元素
                for chunk in upload.chunks():
                    #: 调用「fp.write」执行相应逻辑
                    fp.write(chunk)
        #: 捕获并处理异常，避免程序中断
        except OSError as wr_exc:
            #: 记录日志，便于排查（勿记录密码等敏感信息）
            logger.error('上传文件写入失败: %s', wr_exc)
            #: 返回结果并结束当前函数
            return respond(False, message='文件保存失败')
        # 迭代#223: 图片上传日志
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.info('图片上传: %s by %s', upload.name, request.user.username)
        #: 定义变量「url」，保存对应数据
        url = request.build_absolute_uri(f'{settings.MEDIA_URL}uploads/{year}/{month}/{filename}')
        #: 返回结果并结束当前函数
        return respond(True, url=url)

# 迭代#224: CategoryListCreateView类docstring完善
class CategoryListCreateView(APIView):
    """分类 列表 / 新增。"""
    #: 定义变量「pagination_class」，保存对应数据
    pagination_class = _Pagination

    def get(self, request):
        """
        功能：获取「get」。

        参数：
          - request：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：含 Django ORM 数据库查询，注意查询性能与空结果处理。
        """
        #: 对查询结果按字段排序
        qs = Category.objects.annotate(n=Count('articles')).order_by('-n', 'name')
        #: 定义变量「paginator」，保存对应数据
        paginator = self.pagination_class()
        #: 定义变量「page」，保存对应数据
        page = paginator.paginate_queryset(qs, request, view=self)
        #: 返回结果并结束当前函数
        return paginator.get_paginated_response(CategorySerializer(page, many=True).data)

    def post(self, request):
        """
        功能：处理「post」相关逻辑。

        参数：
          - request：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        异常：可能抛出 PermissionDenied，调用方需处理。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 条件判断：条件成立时执行该分支
        if not request.user.is_staff:
            #: 主动抛出异常交由上层处理
            raise PermissionDenied('仅管理员可创建分类')
        #: 定义变量「serializer」，保存对应数据
        serializer = CategorySerializer(data=request.data)
        #: 调用「serializer.is_valid」执行相应逻辑
        serializer.is_valid(raise_exception=True)
        #: 保存对象（INSERT/UPDATE），可能触发模型信号
        serializer.save()
        #: 返回结果并结束当前函数
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class CategoryDetailView(APIView):
    """分类 查询 / 修改 / 删除。"""

    def get(self, request, pk):
        """
        功能：获取「get」。

        参数：
          - request：传入参数，含义结合函数体与调用处
          - pk：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 返回结果并结束当前函数
        return Response(CategorySerializer(get_object_or_404(Category, pk=pk)).data)

    def put(self, request, pk):
        """
        功能：处理「put」相关逻辑。

        参数：
          - request：传入参数，含义结合函数体与调用处
          - pk：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        异常：可能抛出 PermissionDenied，调用方需处理。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 条件判断：条件成立时执行该分支
        if not request.user.is_staff:
            #: 主动抛出异常交由上层处理
            raise PermissionDenied('仅管理员可修改分类')
        #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
        category = get_object_or_404(Category, pk=pk)
        #: 定义变量「serializer」，保存对应数据
        serializer = CategorySerializer(category, data=request.data, partial=True)
        #: 调用「serializer.is_valid」执行相应逻辑
        serializer.is_valid(raise_exception=True)
        #: 保存对象（INSERT/UPDATE），可能触发模型信号
        serializer.save()
        #: 返回结果并结束当前函数
        return Response(serializer.data)

    def delete(self, request, pk):
        """
        功能：删除「delete」。

        参数：
          - request：传入参数，含义结合函数体与调用处
          - pk：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        异常：可能抛出 PermissionDenied，调用方需处理。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 条件判断：条件成立时执行该分支
        if not request.user.is_staff:
            #: 主动抛出异常交由上层处理
            raise PermissionDenied('仅管理员可删除分类')
        #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
        get_object_or_404(Category, pk=pk).delete()
        #: 返回结果并结束当前函数
        return Response(status=status.HTTP_204_NO_CONTENT)

# 迭代#225: TagListCreateView类docstring完善
class TagListCreateView(APIView):
    """标签 列表 / 新增。"""
    #: 定义变量「pagination_class」，保存对应数据
    pagination_class = _Pagination

    def get(self, request):
        """
        功能：获取「get」。

        参数：
          - request：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：含 Django ORM 数据库查询，注意查询性能与空结果处理。
        """
        #: 对查询结果按字段排序
        qs = Tag.objects.annotate(n=Count('articles')).order_by('-n', 'name')
        #: 定义变量「paginator」，保存对应数据
        paginator = self.pagination_class()
        #: 定义变量「page」，保存对应数据
        page = paginator.paginate_queryset(qs, request, view=self)
        #: 返回结果并结束当前函数
        return paginator.get_paginated_response(TagSerializer(page, many=True).data)

    def post(self, request):
        """
        功能：处理「post」相关逻辑。

        参数：
          - request：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 定义变量「serializer」，保存对应数据
        serializer = TagSerializer(data=request.data)
        #: 调用「serializer.is_valid」执行相应逻辑
        serializer.is_valid(raise_exception=True)
        #: 保存对象（INSERT/UPDATE），可能触发模型信号
        serializer.save()
        #: 返回结果并结束当前函数
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class TagDetailView(APIView):
    """标签 查询 / 修改 / 删除。"""

    def get(self, request, pk):
        """
        功能：获取「get」。

        参数：
          - request：传入参数，含义结合函数体与调用处
          - pk：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 返回结果并结束当前函数
        return Response(TagSerializer(get_object_or_404(Tag, pk=pk)).data)

    def put(self, request, pk):
        """
        功能：处理「put」相关逻辑。

        参数：
          - request：传入参数，含义结合函数体与调用处
          - pk：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        异常：可能抛出 PermissionDenied，调用方需处理。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 条件判断：条件成立时执行该分支
        if not request.user.is_staff:
            #: 主动抛出异常交由上层处理
            raise PermissionDenied('仅管理员可修改标签')
        #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
        tag = get_object_or_404(Tag, pk=pk)
        #: 定义变量「serializer」，保存对应数据
        serializer = TagSerializer(tag, data=request.data, partial=True)
        #: 调用「serializer.is_valid」执行相应逻辑
        serializer.is_valid(raise_exception=True)
        #: 保存对象（INSERT/UPDATE），可能触发模型信号
        serializer.save()
        #: 返回结果并结束当前函数
        return Response(serializer.data)

    def delete(self, request, pk):
        """
        功能：删除「delete」。

        参数：
          - request：传入参数，含义结合函数体与调用处
          - pk：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        异常：可能抛出 PermissionDenied，调用方需处理。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 条件判断：条件成立时执行该分支
        if not request.user.is_staff:
            #: 主动抛出异常交由上层处理
            raise PermissionDenied('仅管理员可删除标签')
        #: 按条件取对象，查不到则抛 Http404（渲染 404 页）
        get_object_or_404(Tag, pk=pk).delete()
        #: 返回结果并结束当前函数
        return Response(status=status.HTTP_204_NO_CONTENT)

# 第2轮迭代#174: 自定义限流类——按匿名/登录用户区分访问频率
class _AnonRateThrottle(throttling.ScopedRateThrottle):
    """
    类 _AnonRateThrottle：anon rate throttle。

    继承：ScopedRateThrottle（基类提供相应能力）。

    字段/类属性：
      - scope：str

    注意：
      - 关注实例状态与方法副作用，保持单一职责。
    """
    #: 定义变量「scope」，保存对应数据
    scope = 'anon'

# 第2轮迭代#171-#180: 增强文章视图集（ModelViewSet 风格）
class ArticleV2ViewSet(viewsets.ReadOnlyModelViewSet):
    """文章只读视图集：演示 queryset / serializer / permission / throttle / filter / pagination 全套配置。"""
    # 第2轮迭代#171: 自定义 queryset——仅公开已发布文章并预加载关联
    #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
    queryset = (Article.objects.filter(status=Article.Status.PUBLISHED)
                #: ORM 预加载关联，减少 N+1 查询提升性能
                .select_related('author', 'category')
                #: ORM 预加载关联，减少 N+1 查询提升性能
                .prefetch_related('tags').all())
    # 第2轮迭代#172: 自定义 serializer_class——使用增强版序列化器
    #: 定义变量「serializer_class」，保存对应数据
    serializer_class = ArticleDetailV2Serializer
    # 第2轮迭代#173: 自定义 permission_classes——只读公开
    #: 定义变量「permission_classes」，保存对应数据（集合/元组）
    permission_classes = [permissions.AllowAny]
    # 第2轮迭代#174: 自定义 throttle_classes
    #: 定义变量「throttle_classes」，保存对应数据（集合/元组）
    throttle_classes = [throttling.UserRateThrottle]
    # 第2轮迭代#175: 自定义 filter_backends——搜索 + 排序
    #: 定义变量「filter_backends」，保存对应数据（集合/元组）
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    # 第2轮迭代#176: 自定义 search_fields——标题/正文
    #: 定义变量「search_fields」，保存对应数据（集合/元组）
    search_fields = ['title', 'content']
    # 第2轮迭代#177: 自定义 ordering_fields——按时间/阅读量
    #: 定义变量「ordering_fields」，保存对应数据（集合/元组）
    ordering_fields = ['created_at', 'views', 'likes']
    # 第2轮迭代#178: 自定义 pagination_class——沿用全局分页
    #: 定义变量「pagination_class」，保存对应数据
    pagination_class = PageNumberPagination

    # 第2轮迭代#179: 自定义 action——热门文章子路由
    #: 装饰器：为下一个定义附加「action(detail=False, methods=['get'])」行为（权限、缓存、注册信号等）
    @action(detail=False, methods=['get'])
    def hot(self, request):
        """返回阅读量 TOP10 的文章。"""
        #: 对查询结果按字段排序
        qs = self.get_queryset().order_by('-views')[:10]
        #: 定义变量「page」，保存对应数据
        page = self.paginate_queryset(qs)
        #: 条件判断：条件成立时执行该分支
        if page is not None:
            #: 返回结果并结束当前函数
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        # 第2轮迭代#180: 自定义 response——直接返回序列化数据
        #: 返回结果并结束当前函数
        return Response(self.get_serializer(qs, many=True).data)

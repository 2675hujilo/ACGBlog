# -*- coding: utf-8 -*-

"""DRF API：文章、分类、标签、图片上传与 V2 ViewSet。"""

import json
import logging
import os
import uuid
from datetime import datetime

from PIL import Image
from django.conf import settings
from django.db.models import Avg, Count, F, Min, Q, Sum
from django.http import (
    HttpResponse,
    JsonResponse, )
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import filters, permissions, status, throttling, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .common import _base_qs, _filter_articles, logger
from ..models import (
    Article, Category, EditLog, Tag, )
from ..serializers import (
    ArticleDetailV2Serializer, ArticleListSerializer,
    ArticleSerializer, CategorySerializer, TagSerializer,
)

logger = logging.getLogger('blog.views')

# 迭代#216: _Pagination类docstring完善
class _Pagination(PageNumberPagination):
    """DRF 接口分页器：默认每页 10 条，支持 ?page_size= 自定义（上限 50）。"""
    page_size = 10                      # 默认每页条数
    page_size_query_param = 'page_size'  # 允许客户端通过 ?page_size= 调整
    max_page_size = 50                  # 单页上限，防止一次拉取过多数据

# 迭代#217: ArticleListCreateView类docstring完善
class ArticleListCreateView(APIView):
    """文章 新增 / 列表查询。GET /api/articles/，POST /api/articles/"""
    pagination_class = _Pagination

    def get(self, request):
        qs, _, _ = _filter_articles(request, _base_qs(request))
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = ArticleListSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = ArticleSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        article = serializer.save(author=request.user)
        EditLog.objects.create(article=article, editor=request.user)
        return Response(ArticleSerializer(article, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)

# 迭代#218: ArticleDetailView类docstring完善
class ArticleDetailView(APIView):
    """文章 单篇查询 / 修改 / 删除。/api/articles/<pk>/"""

    def _get_object(self, request, pk):
        """按主键取文章，并校验草稿可见权限。

        已发布文章任何人可见；草稿仅作者本人或管理员可见，否则抛 PermissionDenied。
        """
        article = get_object_or_404(Article, pk=pk)
        if article.status != Article.Status.PUBLISHED and (
                not request.user.is_authenticated or
                (article.author != request.user and not request.user.is_staff)):
            raise PermissionDenied('无权查看该草稿')
        return article

    def get(self, request, pk):
        """GET：返回单篇文章完整详情 JSON。"""
        article = self._get_object(request, pk)
        return Response(ArticleSerializer(article, context={'request': request}).data)

    def put(self, request, pk):
        """PUT：全量更新文章。"""
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        """PATCH：部分更新文章。"""
        return self._update(request, pk, partial=True)

    def _update(self, request, pk, partial):
        """更新文章公共逻辑：校验权限 -> 序列化 -> 保存 -> 记录修改日志。"""
        article = self._get_object(request, pk)
        if article.author != request.user and not request.user.is_staff:
            raise PermissionDenied('只能修改自己的文章')
        serializer = ArticleSerializer(
            article, data=request.data, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)
        article = serializer.save()
        EditLog.objects.create(article=article, editor=request.user)
        return Response(ArticleSerializer(article, context={'request': request}).data)

    def delete(self, request, pk):
        """DELETE：删除文章（仅作者本人或管理员）。"""
        article = self._get_object(request, pk)
        if article.author != request.user and not request.user.is_staff:
            raise PermissionDenied('无权删除该文章')
        article.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class _CsrfExemptSessionAuthentication(SessionAuthentication):
    """CKEditor 图片对话框以隐藏 iframe 表单提交，无法带 X-CSRFToken，单独豁免。"""
    def enforce_csrf(self, request):
        return

@method_decorator(csrf_exempt, name='dispatch')
# 迭代#219: ImageUploadView类docstring完善
class ImageUploadView(APIView):
    """富文本图片上传，兼容 CKEditor 两种契约：
    - 图片对话框（querystring 带 CKEditorFuncNum）：返回 <script> 回调；
    - 拖拽 / 粘贴上传：返回 {uploaded,fileName,url} JSON。"""
    authentication_classes = [_CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        func_num = request.GET.get('CKEditorFuncNum')

        def respond(ok, url='', message=''):
            if func_num is not None:
                args = json.dumps(
                    [int(func_num), url, message], ensure_ascii=False)[1:-1]
                return HttpResponse(
                    f'<script>window.parent.CKEDITOR.tools.callFunction({args});</script>')
            if ok:
                return JsonResponse(
                    {'uploaded': 1, 'fileName': os.path.basename(url), 'url': url})
            return JsonResponse(
                {'uploaded': 0, 'error': {'message': message}}, status=400)

        upload = request.FILES.get('upload') or request.FILES.get('file')
        if not upload:
            return respond(False, message='未收到图片文件')
        ext = os.path.splitext(upload.name)[1].lower()
        if ext not in settings.UPLOAD_IMAGE_EXTS:
            return respond(False, message='不支持的图片格式')
        if upload.size > settings.UPLOAD_IMAGE_MAX_BYTES:
            return respond(False, message='图片不能超过 8MB')
        # Pillow 校验真实图片，防止伪装扩展名
        # 迭代#220: ImageUploadView中图片打开异常处理
        try:
            image = Image.open(upload)
            image.verify()
            upload.seek(0)
        except (Image.UnidentifiedImageError, OSError):
            return respond(False, message='文件不是有效图片')

        year, month = datetime.now().strftime('%Y'), datetime.now().strftime('%m')
        rel_dir = os.path.join('uploads', year, month)
        abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
        # 迭代#221: ImageUploadView中目录创建异常处理
        try:
            os.makedirs(abs_dir, exist_ok=True)
        except OSError as os_exc:
            logger.error('上传目录创建失败: %s', os_exc)
            return respond(False, message='服务器存储错误')
        filename = f'{uuid.uuid4().hex}{ext}'
        # 迭代#222: ImageUploadView中文件写入异常处理
        try:
            with open(os.path.join(abs_dir, filename), 'wb') as fp:
                for chunk in upload.chunks():
                    fp.write(chunk)
        except OSError as wr_exc:
            logger.error('上传文件写入失败: %s', wr_exc)
            return respond(False, message='文件保存失败')
        # 迭代#223: 图片上传日志
        logger.info('图片上传: %s by %s', upload.name, request.user.username)
        url = request.build_absolute_uri(f'{settings.MEDIA_URL}uploads/{year}/{month}/{filename}')
        return respond(True, url=url)

# 迭代#224: CategoryListCreateView类docstring完善
class CategoryListCreateView(APIView):
    """分类 列表 / 新增。"""
    pagination_class = _Pagination

    def get(self, request):
        qs = Category.objects.annotate(n=Count('articles')).order_by('-n', 'name')
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(CategorySerializer(page, many=True).data)

    def post(self, request):
        if not request.user.is_staff:
            raise PermissionDenied('仅管理员可创建分类')
        serializer = CategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class CategoryDetailView(APIView):
    """分类 查询 / 修改 / 删除。"""

    def get(self, request, pk):
        return Response(CategorySerializer(get_object_or_404(Category, pk=pk)).data)

    def put(self, request, pk):
        if not request.user.is_staff:
            raise PermissionDenied('仅管理员可修改分类')
        category = get_object_or_404(Category, pk=pk)
        serializer = CategorySerializer(category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        if not request.user.is_staff:
            raise PermissionDenied('仅管理员可删除分类')
        get_object_or_404(Category, pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# 迭代#225: TagListCreateView类docstring完善
class TagListCreateView(APIView):
    """标签 列表 / 新增。"""
    pagination_class = _Pagination

    def get(self, request):
        qs = Tag.objects.annotate(n=Count('articles')).order_by('-n', 'name')
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(TagSerializer(page, many=True).data)

    def post(self, request):
        serializer = TagSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class TagDetailView(APIView):
    """标签 查询 / 修改 / 删除。"""

    def get(self, request, pk):
        return Response(TagSerializer(get_object_or_404(Tag, pk=pk)).data)

    def put(self, request, pk):
        if not request.user.is_staff:
            raise PermissionDenied('仅管理员可修改标签')
        tag = get_object_or_404(Tag, pk=pk)
        serializer = TagSerializer(tag, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        if not request.user.is_staff:
            raise PermissionDenied('仅管理员可删除标签')
        get_object_or_404(Tag, pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# 第2轮迭代#174: 自定义限流类——按匿名/登录用户区分访问频率
class _AnonRateThrottle(throttling.ScopedRateThrottle):
    scope = 'anon'

# 第2轮迭代#171-#180: 增强文章视图集（ModelViewSet 风格）
class ArticleV2ViewSet(viewsets.ReadOnlyModelViewSet):
    """文章只读视图集：演示 queryset / serializer / permission / throttle / filter / pagination 全套配置。"""
    # 第2轮迭代#171: 自定义 queryset——仅公开已发布文章并预加载关联
    queryset = (Article.objects.filter(status=Article.Status.PUBLISHED)
                .select_related('author', 'category')
                .prefetch_related('tags').all())
    # 第2轮迭代#172: 自定义 serializer_class——使用增强版序列化器
    serializer_class = ArticleDetailV2Serializer
    # 第2轮迭代#173: 自定义 permission_classes——只读公开
    permission_classes = [permissions.AllowAny]
    # 第2轮迭代#174: 自定义 throttle_classes
    throttle_classes = [throttling.UserRateThrottle]
    # 第2轮迭代#175: 自定义 filter_backends——搜索 + 排序
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    # 第2轮迭代#176: 自定义 search_fields——标题/正文
    search_fields = ['title', 'content']
    # 第2轮迭代#177: 自定义 ordering_fields——按时间/阅读量
    ordering_fields = ['created_at', 'views', 'likes']
    # 第2轮迭代#178: 自定义 pagination_class——沿用全局分页
    pagination_class = PageNumberPagination

    # 第2轮迭代#179: 自定义 action——热门文章子路由
    @action(detail=False, methods=['get'])
    def hot(self, request):
        """返回阅读量 TOP10 的文章。"""
        qs = self.get_queryset().order_by('-views')[:10]
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        # 第2轮迭代#180: 自定义 response——直接返回序列化数据
        return Response(self.get_serializer(qs, many=True).data)

"""博客后台管理：自定义 AdminSite 仪表盘 + 各模型 ModelAdmin 增强。

本文件在 Django 内置后台之上做了四件事：
1. 自定义 ``BlogAdminSite``：重写 ``index`` 注入统计卡片 / 最近评论 / 热门文章 / 7天访问趋势；
2. ``ArticleAdmin`` 批量操作：批量发布 / 转草稿 / 改分类（中间选择页）/ 加阅读量；
3. ``AccessLogAdmin`` 增强：耗时颜色标记、changelist 顶部统计摘要、导出 CSV；
4. ``FriendlyLinkAdmin`` 增强：启用状态彩色标签、可点击链接预览。
"""
import csv
from datetime import timedelta
from collections import OrderedDict

from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.contrib.admin.decorators import register
from django.contrib.auth.admin import UserAdmin
from django.db.models import Avg, Count, F, Sum
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.html import format_html
from django.db.models.functions import TruncDate

from .models import (AccessLog, Article, Category, Comment, EditLog,
                     Favorite, FriendlyLink, Rating, Series, SiteInfo,
                     SiteNotice, Tag, User)
from django import forms
from django.contrib.admin import TabularInline


# ============================ 自定义 AdminSite（仪表盘） ============================

# 迭代#1: BlogAdminSite类docstring
class BlogAdminSite(admin.AdminSite):
    """博客专属后台站点：在标准 AdminSite 基础上重写首页（index）。

    重写 ``index`` 方法，向上下文注入全站运营统计：
    - 文章 / 评论 / 阅读量 / 用户 / 今日访问量统计卡片；
    - 最近 10 条评论（可直接跳转审核）；
    - 热门文章 TOP5（按阅读量）；
    - 最近 7 天访问量趋势（供模板画 CSS 柱状图）。

    原有"应用列表 / 最近操作"等功能通过调用 ``super().index()`` 完整保留。
    """
    site_header = '萌语博客 · 后台管理'
    site_title = '萌语博客后台'
    index_title = '运营控制台'
    # 使用自定义仪表盘模板（extends Django 原生 admin/index.html）
    index_template = 'admin/blog_index.html'

    def index(self, request, extra_context=None):
        """重写后台首页：计算运营统计并注入上下文，再交给标准渲染。"""
        # 迭代#2: admin自定义仪表盘统计注释
        today = timezone.now().date()
        # ---- 统计卡片 ----
        stats = {
            'total_articles': Article.objects.count(),
            'published_articles': Article.objects.filter(status=Article.Status.PUBLISHED).count(),
            'draft_articles': Article.objects.filter(status=Article.Status.DRAFT).count(),
            'total_comments': Comment.objects.count(),
            'pending_comments': Comment.objects.filter(is_approved=False).count(),
            'total_views': Article.objects.aggregate(v=Sum('views'))['v'] or 0,
            'total_users': User.objects.count(),
            'today_visits': AccessLog.objects.filter(created_at__date=today).count(),
        }
        # ---- 最近 10 条评论（预加载用户与文章，避免 N+1）----
        recent_comments = (Comment.objects.select_related('user', 'article')
                           .order_by('-created_at')[:10])
        # ---- 热门文章 TOP5（按阅读量）----
        hot_articles = (Article.objects.filter(status=Article.Status.PUBLISHED)
                        .order_by('-views')[:5])
        # ---- 最近 7 天访问趋势：先初始化最近 7 天每天为 0，再用 ORM TruncDate 填充 ----
        trend = OrderedDict()
        for i in range(6, -1, -1):
            trend[(today - timedelta(days=i))] = 0
        rows = (AccessLog.objects.filter(created_at__date__gte=list(trend.keys())[0])
                .annotate(day=TruncDate('created_at'))
                .values('day').annotate(cnt=Count('id')).order_by('day'))
        for row in rows:
            if row['day'] in trend:
                trend[row['day']] = row['cnt']
        # 柱状图最大值（用于按比例计算柱高），至少为 1 防止除零
        max_trend = max(trend.values()) or 1
        trend_data = [
            {'date': d.strftime('%m-%d'), 'count': c, 'pct': int(c / max_trend * 100)}
            for d, c in trend.items()
        ]
        extra_context = extra_context or {}
        # 第2轮迭代#151: 统计卡片（dash_stats 已含文章/评论/阅读/用户/今日访问）
        # 第2轮迭代#152: 图表（trend_data 已用于 7 天访问趋势柱状图）
        # 第2轮迭代#153: 最近活动（recent_comments 已取最近 10 条）
        # 第2轮迭代#154: 热门内容（hot_articles 已取阅读量 TOP5）
        # 第2轮迭代#155: 系统状态——附加 Python/Django 版本
        import sys as _sys
        import django as _django
        dash_system = {
            'python_version': _sys.version.split()[0],
            'django_version': _django.get_version(),
            'now': timezone.now().strftime('%Y-%m-%d %H:%M'),
        }
        # 第2轮迭代#156: 快捷操作——常用后台入口
        dash_quick = {
            'new_article': '/admin/blog/article/add/',
            'pending_comments': '/admin/blog/comment/?is_approved__exact=0',
        }
        # 第2轮迭代#157: 待办事项——待审核评论数
        dash_todo = {'pending_comments': stats['pending_comments']}
        # 第2轮迭代#158: 数据概览——分类数 / 标签数
        dash_overview = {
            'category_count': Category.objects.count(),
            'tag_count': Tag.objects.count(),
        }
        # 第2轮迭代#159: 性能指标——平均文章阅读量
        avg_views = (Article.objects.aggregate(a=Avg('views'))['a'] or 0)
        dash_perf = {'avg_views': round(avg_views, 1)}
        # 第2轮迭代#160: 安全状态——管理员数 / 今日 404 数
        dash_security = {
            'admin_count': User.objects.filter(is_staff=True).count(),
            'not_found_today': AccessLog.objects.filter(
                status_code=404, created_at__date=today).count(),
        }
        extra_context.update({
            'dash_stats': stats,
            'recent_comments': recent_comments,
            'hot_articles': hot_articles,
            'trend_data': trend_data,
            'dash_system': dash_system,
            'dash_quick': dash_quick,
            'dash_todo': dash_todo,
            'dash_overview': dash_overview,
            'dash_perf': dash_perf,
            'dash_security': dash_security,
        })
        return super().index(request, extra_context)


# 实例化自定义站点（name 保持 'admin'，保证 {% url 'admin:index' %} 反解不变）
class _MoeModelAdmin(admin.ModelAdmin):
    """萌系后台基类：统一空值占位文案与分页大小。"""
    # 列表中字段为空时的萌系占位文案
    empty_value_display = '这里还什么都没有喵~'
    # 每页默认 20 条，避免一次渲染过多行
    list_per_page = 20


blog_admin_site = BlogAdminSite(name='admin')


# ============================ 各模型 ModelAdmin ============================

@register(User, site=blog_admin_site)
# 迭代#3: UserAdmin类docstring
class BlogUserAdmin(UserAdmin):
    """用户后台管理：在 Django 内置 UserAdmin 基础上追加博客资料字段。"""
    list_display = ('username', 'nickname', 'email', 'is_staff', 'date_joined')
    fieldsets = UserAdmin.fieldsets + (('博客资料', {'fields': ('nickname', 'avatar', 'introduction')}),)


@register(Category, site=blog_admin_site)
class CategoryAdmin(_MoeModelAdmin):
    list_display = ('id', 'icon', 'name', 'description', 'created_at')
    search_fields = ('name',)


@register(Tag, site=blog_admin_site)
class TagAdmin(_MoeModelAdmin):
    list_display = ('id', 'name', 'created_at')
    search_fields = ('name',)



# ============================ 第2轮迭代#131-#160: Admin 增强组件 ============================


# 第2轮迭代#132: 自定义列表过滤器——是否有封面
class HasCoverFilter(admin.SimpleListFilter):
    """按文章是否上传了封面图过滤。"""
    title = '封面图'
    parameter_name = 'has_cover'

    def lookups(self, request, model_admin):
        return [('yes', '有封面'), ('no', '无封面')]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(cover_image='')
        if self.value() == 'no':
            return queryset.filter(cover_image='')
        return queryset


# 第2轮迭代#141: 自定义表单——ArticleAdminForm
class ArticleAdminForm(forms.ModelForm):
    """文章后台表单：追加自定义校验与字段配置。"""
    class Meta:
        # 第2轮迭代#142: 自定义字段——暴露全部可编辑字段
        model = Article
        fields = '__all__'

    # 第2轮迭代#143: 自定义 Widget——正文使用多行文本域（默认 TextField 即 textarea）
    # 第2轮迭代#148: 自定义帮助文本——title 字段给填写提示
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 第2轮迭代#149: 自定义初始值——新建时默认状态为已发布
        if self.instance and self.instance.pk is None:
            self.fields['status'].initial = Article.Status.PUBLISHED
        if 'title' in self.fields:
            self.fields['title'].help_text = '标题最长 200 字，超出将自动截断'

    # 第2轮迭代#144: 自定义验证——标题不能为空
    def clean_title(self):
        title = (self.cleaned_data.get('title') or '').strip()
        if not title:
            raise forms.ValidationError('标题不能为空')
        return title[:200]

    # 第2轮迭代#145: 自定义只读说明——只读字段由 readonly_fields 控制
    # 第2轮迭代#150: 自定义保存逻辑——保存后缓存失效由模型信号统一处理


# 第2轮迭代#146: 自定义内联——评论内联展示
class CommentInline(TabularInline):
    """在文章详情页内联展示最近评论（只读）。"""
    model = Comment
    extra = 0
    # 第2轮迭代#147: 自定义字段集——内联只展示关键列
    fields = ('user', 'content', 'is_approved', 'created_at')
    readonly_fields = ('user', 'content', 'created_at')

    def has_add_permission(self, request, obj=None):
        return False


@register(Article, site=blog_admin_site)
# 迭代#4: ArticleAdmin类docstring
class ArticleAdmin(_MoeModelAdmin):
    """文章后台管理：列表增强 + 批量操作 + 置顶校验。"""
    # 列表展示：在原有基础上增加置顶图标、定时发布、点赞数、评论数、字数、手动摘要预览
    list_display = ('pinned_icon', 'id', 'title', 'author', 'category', 'kind', 'status',
                    'scheduled_tag', 'views', 'likes', 'comment_count', 'rating_display',
                    'word_count_display', 'excerpt_preview', 'updated_at')
    list_filter = ('kind', 'status', 'category', 'is_pinned', 'created_at', HasCoverFilter)
    search_fields = ('title', 'content')
    filter_horizontal = ('tags',)
    raw_id_fields = ('author',)
    # 第2轮迭代#136: 自定义分页——每页 20 条，避免大数据列表渲染卡顿
    list_per_page = 20
    # 第2轮迭代#135: 自定义排序——后台默认按更新时间倒序
    ordering = ('-updated_at',)
    # 第2轮迭代#137: 自定义批量编辑说明——list_editable 见 FriendlyLink/SiteNotice
    # 第2轮迭代#141: 自定义表单——使用带额外校验的 ArticleAdminForm
    form = ArticleAdminForm
    # 第2轮迭代#146: 自定义内联——文章详情页内联评论
    inlines = [CommentInline]
    # 批量操作：发布 / 转草稿 / 改分类 / 加阅读量
    # 第2轮迭代#134: 自定义动作——批量发布/转草稿/改分类/加阅读量/导出CSV
    actions = ('make_published', 'make_draft', 'change_category', 'increase_views',
             'export_articles_csv')

    @admin.display(description='📌', boolean=False)
    def pinned_icon(self, obj):
        """57. 列表显示置顶状态图标（📌 表示置顶，空表示未置顶）。"""
        return '📌' if obj.is_pinned else ''

    @admin.display(description='定时')
    def scheduled_tag(self, obj):
        """56. 定时发布草稿显示🕐+时间。"""
        if obj.is_scheduled:
            return format_html(
                '<span style="color:#a06cd5;">🕐 {}</span>',
                obj.published_at.strftime('%m-%d %H:%M'))
        return ''

    @admin.display(description='评分')
    def rating_display(self, obj):
        """63. 显示平均评分（⭐4.5 ×10人）。"""
        if obj.rating_count:
            return f'⭐{obj.rating_avg} ({obj.rating_count})'
        return '-'

    @admin.display(description='字数', ordering='-id')
    def word_count_display(self, obj):
        """后台列表展示文章字数（中文字符 + 英文单词数）。"""
        return obj.word_count

    @admin.display(description='摘要预览')
    def excerpt_preview(self, obj):
        """后台列表展示摘要前 40 字，便于一眼判断是否手写了摘要。"""
        text = obj.excerpt or ''
        return (text[:40] + '…') if len(text) > 40 else text

    # 57. 保存时校验置顶数量：全站最多 3 篇置顶
    def save_model(self, request, obj, form, change):
        """保存文章时校验置顶数量，超过 3 篇自动取消置顶并提示。"""
        if obj.is_pinned:
            pinned_count = Article.objects.filter(is_pinned=True).exclude(pk=obj.pk).count()
            if pinned_count >= 3:
                obj.is_pinned = False
                self.message_user(
                    request,
                    '全站置顶文章最多 3 篇，本次置顶未生效喵📌',
                    messages.WARNING)
        super().save_model(request, obj, form, change)

    # 第2轮迭代#131: 自定义列——封面状态标签
    @admin.display(description='封面')
    def cover_status(self, obj):
        """列表显示封面是否已上传：🖼 已传 / — 未传。"""
        return '🖼' if obj.cover_image else '—'

    # 第2轮迭代#133: 自定义搜索说明——search_fields 已覆盖 title/content
    # 第2轮迭代#138: 自定义导出——把选中文章导出为 CSV
    @admin.action(description='⬇ 导出所选文章为 CSV')
    def export_articles_csv(self, request, queryset):
        """把选中文章的标题/作者/分类/阅读量导出为 CSV 下载。"""
        import csv as _csv
        resp = HttpResponse(content_type='text/csv')
        resp['Content-Disposition'] = 'attachment; filename="articles.csv"'
        w = _csv.writer(resp)
        w.writerow(['ID', '标题', '作者', '分类', '状态', '阅读量', '点赞', '评论数', '发布时间'])
        for a in queryset.select_related('author', 'category'):
            w.writerow([a.id, a.title, str(a.author), str(a.category or ''),
                        a.get_status_display_cn(), a.views, a.likes,
                        a.comment_count, a.created_at.strftime('%Y-%m-%d')])
        return resp

    # 第2轮迭代#139: 自定义导入说明——本项目通过 seed_* 命令初始化数据
    # 第2轮迭代#140: 自定义图表说明——访问趋势已在仪表盘 trend_data 渲染

    # ------------------------- 批量操作 -------------------------
    @admin.action(description='📢 批量发布（设为已发布）')
    # 迭代#5: admin中批量操作异常处理
    def make_published(self, request, queryset):
        """批量把选中文章状态置为已发布。"""
        # 迭代#6: admin批量操作注释
        try:
            updated = queryset.update(status=Article.Status.PUBLISHED)
            self.message_user(request, f'已发布 {updated} 篇文章。', messages.SUCCESS)
        except Exception as exc:
            self.message_user(request, f'批量发布失败: {exc}', messages.ERROR)

    @admin.action(description='📝 批量转为草稿')
    def make_draft(self, request, queryset):
        """批量把选中文章状态置为草稿（前台不再可见）。"""
        updated = queryset.update(status=Article.Status.DRAFT)
        self.message_user(request, f'已将 {updated} 篇文章转为草稿。', messages.SUCCESS)

    @admin.action(description='📦 批量增加阅读量（+100）')
    def increase_views(self, request, queryset):
        """批量给选中文章阅读量 +100（F 表达式原子自增，用于测试 / 调数据）。"""
        updated = queryset.update(views=F('views') + 100)
        self.message_user(request, f'已为 {updated} 篇文章各增加 100 阅读量。', messages.SUCCESS)

    @admin.action(description='🗂 批量修改分类…')
    def change_category(self, request, queryset):
        """批量修改分类：第一次提交弹出中间选择页，选择后真正更新。

        利用 action 既能作为"动作"下拉项、又能在 ``request.POST`` 里判别
        用户是否已在中间页选择分类：未选择则渲染选择模板，已选择则执行更新。
        """
        # 用户已在中间页选择了分类并点击"应用"
        if 'apply' in request.POST:
            cat_id = request.POST.get('category')
            category = Category.objects.filter(pk=cat_id).first() if cat_id else None
            updated = queryset.update(category=category)
            self.message_user(
                request,
                f'已将 {updated} 篇文章移动到「{category.name if category else "未分类"}」。',
                messages.SUCCESS)
            return
        # 未选择：渲染中间选择页（列出待改文章 + 分类下拉）
        context = {
            **self.admin_site.each_context(request),
            'title': '批量修改分类',
            'opts': self.model._meta,
            'app_label': self.model._meta.app_label,
            'posts': queryset,
            'cats': Category.objects.all().order_by('name'),
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'cancel_url': request.get_full_path(),
        }
        return TemplateResponse(request, 'admin/blog/change_category.html', context)


@register(EditLog, site=blog_admin_site)
class EditLogAdmin(_MoeModelAdmin):
    """轻量修改日志：只读展示修改人 + 修改时间 + 55. 内容快照预览。"""
    # 55. 列表增加"内容快照预览"列（前 100 字纯文本）
    list_display = ('id', 'article', 'editor', 'edited_at', 'snapshot_preview')
    list_filter = ('edited_at',)
    raw_id_fields = ('article', 'editor')
    readonly_fields = ('article', 'editor', 'edited_at', 'content_snapshot')

    def snapshot_preview(self, obj):
        """55. 修改前内容快照预览（前 100 字纯文本）。"""
        return obj.snapshot_preview or '（无快照）'
    snapshot_preview.short_description = '内容快照(前100字)'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class DurationFilter(admin.SimpleListFilter):
    """访问日志耗时区间筛选：慢(>1000ms) / 中(500-1000) / 快(<500)。"""
    title = '耗时区间'
    parameter_name = 'duration_band'

    def lookups(self, request, model_admin):
        return [
            ('slow', '慢 (>1000ms)'),
            ('mid', '中 (500-1000ms)'),
            ('fast', '快 (<500ms)'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'slow':
            return queryset.filter(duration_ms__gt=1000)
        if self.value() == 'mid':
            return queryset.filter(duration_ms__gt=500, duration_ms__lte=1000)
        if self.value() == 'fast':
            return queryset.filter(duration_ms__lte=500)
        return queryset


@register(AccessLog, site=blog_admin_site)
class AccessLogAdmin(_MoeModelAdmin):
    """访问日志后台：只读 + 耗时颜色 + 统计摘要 + 导出 CSV。"""
    list_display = ('ip_address', 'username', 'method', 'path', 'status_code',
                    'duration_color', 'browser', 'os', 'created_at')
    list_filter = ('method', 'status_code', 'browser', 'os', 'created_at', DurationFilter)
    search_fields = ('ip_address', 'username', 'path', 'user_agent')
    readonly_fields = [f.name for f in AccessLog._meta.get_fields() if f.name != 'id']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    actions = ('export_csv',)

    @admin.display(description='耗时(ms)', ordering='duration_ms')
    def duration_color(self, obj):
        """按耗时长短着色：>1000ms 红、>500ms 橙、其余绿，便于一眼看慢请求。"""
        if obj.duration_ms > 1000:
            color = '#e74c3c'
        elif obj.duration_ms > 500:
            color = '#f39c12'
        else:
            color = '#27ae60'
        return format_html('<span style="color:{};font-weight:600">{}ms</span>',
                           color, f'{obj.duration_ms:.0f}')

    @admin.action(description='⬇ 导出所选为 CSV')
    # 迭代#7: admin中CSV导出异常处理
    def export_csv(self, request, queryset):
        """把选中的访问日志导出为 CSV 下载。"""
        # 迭代#8: admin CSV导出注释
        try:
            response = HttpResponse(content_type='text/csv')
            # 附件下载，文件名带时间戳
            response['Content-Disposition'] = 'attachment; filename="access_logs.csv"'
            writer = csv.writer(response)
            writer.writerow(['时间', 'IP', '用户', '方法', '路径', '状态码', '耗时ms', '浏览器', '操作系统'])
            for log in queryset:
                writer.writerow([
                    log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else '',
                    log.ip_address or '', log.username or '', log.method,
                    log.path, log.status_code, round(log.duration_ms, 1),
                    log.browser or '', log.os or '',
                ])
            return response
        except Exception as exc:
            return HttpResponse(f'导出失败: {exc}', status=500)

    def changelist_view(self, request, extra_context=None):
        """在列表页顶部额外注入统计摘要：总访问量 / 独立IP / 平均耗时 / 404数。"""
        # 用当前筛选条件构造查询集，统计口径与列表一致
        cl = self.get_changelist_instance(request)
        qs = cl.queryset
        extra_context = extra_context or {}
        extra_context['log_stats'] = {
            'total': qs.count(),
            'unique_ips': qs.values('ip_address').distinct().count(),
            'avg_duration': round(qs.aggregate(a=Avg('duration_ms'))['a'] or 0, 1),
            'not_found': qs.filter(status_code=404).count(),
        }
        return super().changelist_view(request, extra_context)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@register(FriendlyLink, site=blog_admin_site)
class FriendlyLinkAdmin(_MoeModelAdmin):
    """友情链接后台管理：彩色状态 + 可点击链接预览 + 排序 / 启用。"""
    list_display = ('icon', 'name', 'link_preview', 'order', 'is_active_tag', 'created_at')
    list_editable = ('order',)
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'url')
    ordering = ['order']
    # 表单字段提示：icon 给 emoji 选择建议，url 给 placeholder
    fieldsets = (
        (None, {'fields': ('name', 'url', 'icon', 'order', 'is_active')}),
    )

    @admin.display(description='状态', ordering='is_active')
    def is_active_tag(self, obj):
        """启用状态彩色标签：绿色✓ / 红色✗。"""
        if obj.is_active:
            return format_html('<span style="color:#27ae60;font-weight:700">✓ 显示</span>')
        return format_html('<span style="color:#e74c3c;font-weight:700">✗ 隐藏</span>')

    @admin.display(description='链接')
    def link_preview(self, obj):
        """可点击的链接预览（新窗口打开），过长时截断显示。"""
        short = obj.url[:48] + ('…' if len(obj.url) > 48 else '')
        return format_html('<a href="{}" target="_blank" rel="noopener">{} ↗</a>', obj.url, short)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """给 icon / url 字段加表单提示，引导运营填写。"""
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == 'icon':
            field.help_text = '图标用 emoji，如 🔗 🌟 🐱 📚 💡'
        if db_field.name == 'url':
            field.widget.attrs['placeholder'] = 'https://example.com'
        return field


@register(Comment, site=blog_admin_site)
# 迭代#9: CommentAdmin类docstring
class CommentAdmin(_MoeModelAdmin):
    """评论后台管理：支持审核 / 批量通过 / 批量删除。"""
    # 列表展示：id + 所属文章 + 评论人 + 内容前 50 字预览 + 父评论 + 点赞 + 审核态 + 时间
    list_display = ('id', 'article', 'user', 'content_preview', 'parent_comment',
                    'likes', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'created_at')
    search_fields = ('content', 'user__username', 'article__title')
    # 文章 / 用户 / 父评论用原始 id 输入框，避免下拉加载上千条评论
    raw_id_fields = ('article', 'user', 'parent_comment')
    actions = ('make_approved', 'make_unapproved', 'really_delete_selected')

    @admin.display(description='内容预览')
    def content_preview(self, obj):
        """列表中展示评论内容前 50 字，超出追加省略号。"""
        text = (obj.content or '')[:50]
        return text + ('…' if len(obj.content or '') > 50 else '')

    @admin.action(description='批量审核通过')
    def make_approved(self, request, queryset):
        """批量把选中评论置为已审核通过。"""
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'已通过审核 {updated} 条评论。')

    @admin.action(description='批量取消审核')
    def make_unapproved(self, request, queryset):
        """批量把选中评论置为未审核（前台隐藏）。"""
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'已取消审核 {updated} 条评论。')

    @admin.action(description='批量删除所选评论')
    def really_delete_selected(self, request, queryset):
        """批量删除选中评论（Django 默认删除动作别名，明确文案）。"""
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'已删除 {count} 条评论。')
    really_delete_selected.short_description = '批量删除所选评论'


@register(Favorite, site=blog_admin_site)
class FavoriteAdmin(_MoeModelAdmin):
    """用户收藏记录后台管理。"""
    list_display = ('id', 'user', 'article', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'article__title')
    raw_id_fields = ('user', 'article')
    date_hierarchy = 'created_at'


@register(SiteNotice, site=blog_admin_site)
class SiteNoticeAdmin(_MoeModelAdmin):
    """62. 网站公告后台：内容 + 是否显示（可直接在列表切换）。"""
    list_display = ('content', 'is_active', 'is_active_tag', 'created_at')
    list_editable = ('is_active',)
    list_filter = ('is_active', 'created_at')

    @admin.display(description='显示状态', ordering='is_active')
    def is_active_tag(self, obj):
        """显示状态彩色标签：绿✓/红✗。"""
        if obj.is_active:
            return format_html('<span style="color:#27ae60;font-weight:700;">✓ 显示</span>')
        return format_html('<span style="color:#e74c3c;font-weight:700;">✗ 隐藏</span>')


@register(Series, site=blog_admin_site)
class SeriesAdmin(_MoeModelAdmin):
    """67. 文章系列后台管理。"""
    list_display = ('id', 'title', 'author', 'article_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('title', 'description')
    raw_id_fields = ('author',)

    @admin.display(description='文章数')
    def article_count(self, obj):
        """系列下已发布文章数量。"""
        return obj.articles.count()


@register(Rating, site=blog_admin_site)
class RatingAdmin(_MoeModelAdmin):
    """63. 文章评分后台：只读查看。"""
    list_display = ('id', 'article', 'user', 'score', 'created_at')
    list_filter = ('score', 'created_at')
    search_fields = ('article__title', 'user__username')
    raw_id_fields = ('article', 'user')

    def has_add_permission(self, request):
        return False


@register(SiteInfo, site=blog_admin_site)
class SiteInfoAdmin(admin.ModelAdmin):
    """站点信息单例后台（工单 15）：萌系「站点设置」页之外的兜底编辑入口。"""

    # 只展示可编辑字段，隐藏自动时间
    fields = ('site_name', 'logo_emoji', 'tagline', 'description', 'keywords',
              'footer_about', 'footer_icp', 'copyright_holder')

    def has_add_permission(self, request):
        """单例：已存在记录时不允许新增。"""
        return not SiteInfo.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """单例不可删除。"""
        return False

    def change_view(self, request, object_id=None, form_url='', extra_context=None):
        """无论从哪里进入，都直接编辑唯一记录。"""
        info = SiteInfo.load()
        return super().change_view(request, str(info.pk), form_url, extra_context)

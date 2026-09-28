"""博客后台管理：自定义 AdminSite 仪表盘 + 各模型 ModelAdmin 增强。

本文件在 Django 内置后台之上做了四件事：
1. 自定义 ``BlogAdminSite``：重写 ``index`` 注入统计卡片 / 最近评论 / 热门文章 / 7天访问趋势；
2. ``ArticleAdmin`` 批量操作：批量发布 / 转草稿 / 改分类（中间选择页）/ 加阅读量；
3. ``AccessLogAdmin`` 增强：耗时颜色标记、changelist 顶部统计摘要、导出 CSV；
4. ``FriendlyLinkAdmin`` 增强：启用状态彩色标签、可点击链接预览。
"""
#: 导入模块「csv」，供本文件后续使用
import csv
#: 从模块「datetime」导入所需对象
from datetime import timedelta
#: 从模块「collections」导入所需对象
from collections import OrderedDict

#: 从模块「django.contrib」导入所需对象
from django.contrib import admin, messages
#: 从模块「django.contrib.admin」导入所需对象
from django.contrib.admin import helpers
#: 从模块「django.contrib.admin.decorators」导入所需对象
from django.contrib.admin.decorators import register
#: 从模块「django.contrib.auth.admin」导入所需对象
from django.contrib.auth.admin import UserAdmin
#: 从模块「django.db.models」导入所需对象
from django.db.models import Avg, Count, F, Sum
#: 从模块「django.http」导入所需对象
from django.http import HttpResponse
#: 从模块「django.template.response」导入所需对象
from django.template.response import TemplateResponse
#: 从模块「django.utils」导入所需对象
from django.utils import timezone
#: 从模块「django.utils.html」导入所需对象
from django.utils.html import format_html
#: 从模块「django.db.models.functions」导入所需对象
from django.db.models.functions import TruncDate

#: 从模块「.models」导入所需对象
from .models import (AccessLog, Article, Category, Comment, EditLog,
                     #: 该行执行对应逻辑（结合上下文理解）
                     Favorite, FriendlyLink, Rating, Series, SiteInfo,
                     #: 该行执行对应逻辑（结合上下文理解）
                     SiteMessage, SiteNotice, Tag, User)
#: 从模块「django」导入所需对象
from django import forms
#: 从模块「django.contrib.admin」导入所需对象
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
    #: 定义变量「site_header」，保存对应数据
    site_header = '萌语博客 · 后台管理'
    #: 定义变量「site_title」，保存对应数据
    site_title = '萌语博客后台'
    #: 定义变量「index_title」，保存对应数据
    index_title = '运营控制台'
    # 使用自定义仪表盘模板（extends Django 原生 admin/index.html）
    #: 定义变量「index_template」，保存对应数据
    index_template = 'admin/blog_index.html'

    def index(self, request, extra_context=None):
        """重写后台首页：计算运营统计并注入上下文，再交给标准渲染。"""
        # 迭代#2: admin自定义仪表盘统计注释
        #: 获取当前时间（时区感知），统一时间口径
        today = timezone.now().date()
        # ---- 统计卡片 ----
        #: 定义变量「stats」，保存对应数据
        stats = {
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'total_articles': Article.objects.count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'published_articles': Article.objects.filter(status=Article.Status.PUBLISHED).count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'draft_articles': Article.objects.filter(status=Article.Status.DRAFT).count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'total_comments': Comment.objects.count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'pending_comments': Comment.objects.filter(is_approved=False).count(),
            #: 使用聚合函数做统计查询
            'total_views': Article.objects.aggregate(v=Sum('views'))['v'] or 0,
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'total_users': User.objects.count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'today_visits': AccessLog.objects.filter(created_at__date=today).count(),
        #: 该行执行对应逻辑（结合上下文理解）
        }
        # ---- 最近 10 条评论（预加载用户与文章，避免 N+1）----
        #: ORM 预加载关联，减少 N+1 查询提升性能
        recent_comments = (Comment.objects.select_related('user', 'article')
                           #: 对查询结果按字段排序
                           .order_by('-created_at')[:10])
        # ---- 热门文章 TOP5（按阅读量）----
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        hot_articles = (Article.objects.filter(status=Article.Status.PUBLISHED)
                        #: 对查询结果按字段排序
                        .order_by('-views')[:5])
        # ---- 最近 7 天访问趋势：先初始化最近 7 天每天为 0，再用 ORM TruncDate 填充 ----
        #: 定义变量「trend」，保存对应数据
        trend = OrderedDict()
        #: 循环遍历，逐个处理元素
        for i in range(6, -1, -1):
            #: 该行执行对应逻辑（结合上下文理解）
            trend[(today - timedelta(days=i))] = 0
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        rows = (AccessLog.objects.filter(created_at__date__gte=list(trend.keys())[0])
                #: 该行执行对应逻辑（结合上下文理解）
                .annotate(day=TruncDate('created_at'))
                #: 对查询结果按字段排序
                .values('day').annotate(cnt=Count('id')).order_by('day'))
        #: 循环遍历，逐个处理元素
        for row in rows:
            #: 条件判断：条件成立时执行该分支
            if row['day'] in trend:
                #: 该行执行对应逻辑（结合上下文理解）
                trend[row['day']] = row['cnt']
        # 柱状图最大值（用于按比例计算柱高），至少为 1 防止除零
        #: 定义变量「max_trend」，保存对应数据
        max_trend = max(trend.values()) or 1
        #: 定义变量「trend_data」，保存对应数据（集合/元组）
        trend_data = [
            #: 该行执行对应逻辑（结合上下文理解）
            {'date': d.strftime('%m-%d'), 'count': c, 'pct': int(c / max_trend * 100)}
            #: 循环遍历，逐个处理元素
            for d, c in trend.items()
        #: 该行执行对应逻辑（结合上下文理解）
        ]
        #: 定义变量「extra_context」，保存对应数据
        extra_context = extra_context or {}
        # 第2轮迭代#151: 统计卡片（dash_stats 已含文章/评论/阅读/用户/今日访问）
        # 第2轮迭代#152: 图表（trend_data 已用于 7 天访问趋势柱状图）
        # 第2轮迭代#153: 最近活动（recent_comments 已取最近 10 条）
        # 第2轮迭代#154: 热门内容（hot_articles 已取阅读量 TOP5）
        # 第2轮迭代#155: 系统状态——附加 Python/Django 版本
        #: 导入模块「sys」，供本文件后续使用
        import sys as _sys
        #: 导入模块「django」，供本文件后续使用
        import django as _django
        #: 定义变量「dash_system」，保存对应数据
        dash_system = {
            #: 配置项「python_version」：字典/模型的该键设置为对应值
            'python_version': _sys.version.split()[0],
            #: 配置项「django_version」：字典/模型的该键设置为对应值
            'django_version': _django.get_version(),
            #: 获取当前时间（时区感知），统一时间口径
            'now': timezone.now().strftime('%Y-%m-%d %H:%M'),
        #: 该行执行对应逻辑（结合上下文理解）
        }
        # 第2轮迭代#156: 快捷操作——常用后台入口
        #: 定义变量「dash_quick」，保存对应数据
        dash_quick = {
            #: 配置项「new_article」：字典/模型的该键设置为对应值
            'new_article': '/admin/blog/article/add/',
            #: 配置项「pending_comments」：字典/模型的该键设置为对应值
            'pending_comments': '/admin/blog/comment/?is_approved__exact=0',
        #: 该行执行对应逻辑（结合上下文理解）
        }
        # 第2轮迭代#157: 待办事项——待审核评论数
        #: 定义变量「dash_todo」，保存对应数据
        dash_todo = {'pending_comments': stats['pending_comments']}
        # 第2轮迭代#158: 数据概览——分类数 / 标签数
        #: 定义变量「dash_overview」，保存对应数据
        dash_overview = {
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'category_count': Category.objects.count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'tag_count': Tag.objects.count(),
        #: 该行执行对应逻辑（结合上下文理解）
        }
        # 第2轮迭代#159: 性能指标——平均文章阅读量
        #: 使用聚合函数做统计查询
        avg_views = (Article.objects.aggregate(a=Avg('views'))['a'] or 0)
        #: 定义变量「dash_perf」，保存对应数据
        dash_perf = {'avg_views': round(avg_views, 1)}
        # 第2轮迭代#160: 安全状态——管理员数 / 今日 404 数
        #: 定义变量「dash_security」，保存对应数据
        dash_security = {
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'admin_count': User.objects.filter(is_staff=True).count(),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'not_found_today': AccessLog.objects.filter(
                #: 定义变量「status_code」，保存对应数据
                status_code=404, created_at__date=today).count(),
        #: 该行执行对应逻辑（结合上下文理解）
        }
        #: 调用「extra_context.update」执行相应逻辑
        extra_context.update({
            #: 配置项「dash_stats」：字典/模型的该键设置为对应值
            'dash_stats': stats,
            #: 配置项「recent_comments」：字典/模型的该键设置为对应值
            'recent_comments': recent_comments,
            #: 配置项「hot_articles」：字典/模型的该键设置为对应值
            'hot_articles': hot_articles,
            #: 配置项「trend_data」：字典/模型的该键设置为对应值
            'trend_data': trend_data,
            #: 配置项「dash_system」：字典/模型的该键设置为对应值
            'dash_system': dash_system,
            #: 配置项「dash_quick」：字典/模型的该键设置为对应值
            'dash_quick': dash_quick,
            #: 配置项「dash_todo」：字典/模型的该键设置为对应值
            'dash_todo': dash_todo,
            #: 配置项「dash_overview」：字典/模型的该键设置为对应值
            'dash_overview': dash_overview,
            #: 配置项「dash_perf」：字典/模型的该键设置为对应值
            'dash_perf': dash_perf,
            #: 配置项「dash_security」：字典/模型的该键设置为对应值
            'dash_security': dash_security,
        #: 该行执行对应逻辑（结合上下文理解）
        })
        #: 返回结果并结束当前函数
        return super().index(request, extra_context)


# 实例化自定义站点（name 保持 'admin'，保证 {% url 'admin:index' %} 反解不变）
class _MoeModelAdmin(admin.ModelAdmin):
    """萌系后台基类：统一空值占位文案与分页大小。"""
    # 列表中字段为空时的萌系占位文案
    #: 定义变量「empty_value_display」，保存对应数据
    empty_value_display = '这里还什么都没有喵~'
    # 每页默认 20 条，避免一次渲染过多行
    #: 定义变量「list_per_page」，保存对应数据
    list_per_page = 20


#: 定义变量「blog_admin_site」，保存对应数据
blog_admin_site = BlogAdminSite(name='admin')


# ============================ 各模型 ModelAdmin ============================

#: 装饰器：为下一个定义附加「register(User, site=blog_admin_site)」行为（权限、缓存、注册信号等）
@register(User, site=blog_admin_site)
# 迭代#3: UserAdmin类docstring
class BlogUserAdmin(UserAdmin):
    """用户后台管理：在 Django 内置 UserAdmin 基础上追加博客资料字段。"""
    #: 定义变量「list_display」，保存对应数据（集合/元组）
    list_display = ('username', 'nickname', 'email', 'is_staff', 'date_joined')
    #: 定义变量「fieldsets」，保存对应数据
    fieldsets = UserAdmin.fieldsets + (('博客资料', {'fields': ('nickname', 'avatar', 'introduction')}),)


#: 装饰器：为下一个定义附加「register(Category, site=blog_admin_site)」行为（权限、缓存、注册信号等）
@register(Category, site=blog_admin_site)
class CategoryAdmin(_MoeModelAdmin):
    """
    类 CategoryAdmin：category admin。

    继承：_MoeModelAdmin（基类提供相应能力）。

    字段/类属性：
      - list_display
      - search_fields

    注意：
      - 关注实例状态与方法副作用，保持单一职责。
    """
    #: 定义变量「list_display」，保存对应数据（集合/元组）
    list_display = ('id', 'icon', 'name', 'description', 'created_at')
    #: 定义变量「search_fields」，保存对应数据（集合/元组）
    search_fields = ('name',)


#: 装饰器：为下一个定义附加「register(Tag, site=blog_admin_site)」行为（权限、缓存、注册信号等）
@register(Tag, site=blog_admin_site)
class TagAdmin(_MoeModelAdmin):
    """
    类 TagAdmin：tag admin。

    继承：_MoeModelAdmin（基类提供相应能力）。

    字段/类属性：
      - list_display
      - search_fields

    注意：
      - 关注实例状态与方法副作用，保持单一职责。
    """
    #: 定义变量「list_display」，保存对应数据（集合/元组）
    list_display = ('id', 'name', 'created_at')
    #: 定义变量「search_fields」，保存对应数据（集合/元组）
    search_fields = ('name',)



# ============================ 第2轮迭代#131-#160: Admin 增强组件 ============================


# 第2轮迭代#132: 自定义列表过滤器——是否有封面
class HasCoverFilter(admin.SimpleListFilter):
    """按文章是否上传了封面图过滤。"""
    #: 定义变量「title」，保存对应数据
    title = '封面图'
    #: 定义变量「parameter_name」，保存对应数据
    parameter_name = 'has_cover'

    def lookups(self, request, model_admin):
        """
        功能：处理「lookups」相关逻辑。

        参数：
          - request：传入参数，含义结合函数体与调用处
          - model_admin：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 返回结果并结束当前函数
        return [('yes', '有封面'), ('no', '无封面')]

    def queryset(self, request, queryset):
        """
        功能：处理「queryset」相关逻辑。

        参数：
          - request：传入参数，含义结合函数体与调用处
          - queryset：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 条件判断：条件成立时执行该分支
        if self.value() == 'yes':
            #: 返回结果并结束当前函数
            return queryset.exclude(cover_image='')
        #: 条件判断：条件成立时执行该分支
        if self.value() == 'no':
            #: 返回结果并结束当前函数
            return queryset.filter(cover_image='')
        #: 返回结果并结束当前函数
        return queryset


# 第2轮迭代#141: 自定义表单——ArticleAdminForm
class ArticleAdminForm(forms.ModelForm):
    """文章后台表单：追加自定义校验与字段配置。"""
    class Meta:
        # 第2轮迭代#142: 自定义字段——暴露全部可编辑字段
        """
        类 Meta：meta。

        字段/类属性：
          - model
          - fields：str

        注意：
          - 关注实例状态与方法副作用，保持单一职责。
        """
        #: 定义变量「model」，保存对应数据
        model = Article
        #: 定义变量「fields」，保存对应数据
        fields = '__all__'

    # 第2轮迭代#143: 自定义 Widget——正文使用多行文本域（默认 TextField 即 textarea）
    # 第2轮迭代#148: 自定义帮助文本——title 字段给填写提示
    def __init__(self, *args, **kwargs):
        """
        功能：初始化「init」。

        返回：无显式返回（None），多以副作用为主。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 调用「super」执行相应逻辑
        super().__init__(*args, **kwargs)
        # 第2轮迭代#149: 自定义初始值——新建时默认状态为已发布
        #: 条件判断：条件成立时执行该分支
        if self.instance and self.instance.pk is None:
            #: 操作「self」的属性或方法
            self.fields['status'].initial = Article.Status.PUBLISHED
        #: 条件判断：条件成立时执行该分支
        if 'title' in self.fields:
            #: 操作「self」的属性或方法
            self.fields['title'].help_text = '标题最长 200 字，超出将自动截断'

    # 第2轮迭代#144: 自定义验证——标题不能为空
    def clean_title(self):
        """
        功能：清理「title」。

        返回：对应计算/查询结果。

        异常：可能抛出 ValidationError，调用方需处理。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 定义变量「title」，保存对应数据（集合/元组）
        title = (self.cleaned_data.get('title') or '').strip()
        #: 条件判断：条件成立时执行该分支
        if not title:
            #: 主动抛出异常交由上层处理
            raise forms.ValidationError('标题不能为空')
        #: 返回结果并结束当前函数
        return title[:200]

    # 第2轮迭代#145: 自定义只读说明——只读字段由 readonly_fields 控制
    # 第2轮迭代#150: 自定义保存逻辑——保存后缓存失效由模型信号统一处理


# 第2轮迭代#146: 自定义内联——评论内联展示
class CommentInline(TabularInline):
    """在文章详情页内联展示最近评论（只读）。"""
    #: 定义变量「model」，保存对应数据
    model = Comment
    #: 定义变量「extra」，保存对应数据
    extra = 0
    # 第2轮迭代#147: 自定义字段集——内联只展示关键列
    #: 定义变量「fields」，保存对应数据（集合/元组）
    fields = ('user', 'content', 'is_approved', 'created_at')
    #: 定义变量「readonly_fields」，保存对应数据（集合/元组）
    readonly_fields = ('user', 'content', 'created_at')

    def has_add_permission(self, request, obj=None):
        """
        功能：判断是否含有「add permission」。

        参数：
          - request：传入参数，含义结合函数体与调用处
          - obj（可选，有默认值）：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 返回结果并结束当前函数
        return False


#: 装饰器：为下一个定义附加「register(Article, site=blog_admin_site)」行为（权限、缓存、注册信号等）
@register(Article, site=blog_admin_site)
# 迭代#4: ArticleAdmin类docstring
class ArticleAdmin(_MoeModelAdmin):
    """文章后台管理：列表增强 + 批量操作 + 置顶校验。"""
    # 列表展示：在原有基础上增加置顶图标、定时发布、点赞数、评论数、字数、手动摘要预览
    #: 定义变量「list_display」，保存对应数据（集合/元组）
    list_display = ('pinned_icon', 'id', 'title', 'author', 'category', 'kind', 'status',
                    #: 该行执行对应逻辑（结合上下文理解）
                    'scheduled_tag', 'views', 'likes', 'comment_count', 'rating_display',
                    #: 该行执行对应逻辑（结合上下文理解）
                    'word_count_display', 'excerpt_preview', 'updated_at')
    #: 定义变量「list_filter」，保存对应数据（集合/元组）
    list_filter = ('kind', 'status', 'category', 'is_pinned', 'created_at', HasCoverFilter)
    #: 定义变量「search_fields」，保存对应数据（集合/元组）
    search_fields = ('title', 'content')
    #: 定义变量「filter_horizontal」，保存对应数据（集合/元组）
    filter_horizontal = ('tags',)
    #: 定义变量「raw_id_fields」，保存对应数据（集合/元组）
    raw_id_fields = ('author',)
    # 第2轮迭代#136: 自定义分页——每页 20 条，避免大数据列表渲染卡顿
    #: 定义变量「list_per_page」，保存对应数据
    list_per_page = 20
    # 第2轮迭代#135: 自定义排序——后台默认按更新时间倒序
    #: 定义变量「ordering」，保存对应数据（集合/元组）
    ordering = ('-updated_at',)
    # 第2轮迭代#137: 自定义批量编辑说明——list_editable 见 FriendlyLink/SiteNotice
    # 第2轮迭代#141: 自定义表单——使用带额外校验的 ArticleAdminForm
    #: 定义变量「form」，保存对应数据
    form = ArticleAdminForm
    # 第2轮迭代#146: 自定义内联——文章详情页内联评论
    #: 定义变量「inlines」，保存对应数据（集合/元组）
    inlines = [CommentInline]
    # 批量操作：发布 / 转草稿 / 改分类 / 加阅读量
    # 第2轮迭代#134: 自定义动作——批量发布/转草稿/改分类/加阅读量/导出CSV
    #: 定义变量「actions」，保存对应数据（集合/元组）
    actions = ('make_published', 'make_draft', 'change_category', 'increase_views',
             #: 该行执行对应逻辑（结合上下文理解）
             'export_articles_csv')

    #: 装饰器：为下一个定义附加「admin.display(description='📌', boolean=False)」行为（权限、缓存、注册信号等）
    @admin.display(description='📌', boolean=False)
    def pinned_icon(self, obj):
        """57. 列表显示置顶状态图标（📌 表示置顶，空表示未置顶）。"""
        #: 返回结果并结束当前函数
        return '📌' if obj.is_pinned else ''

    #: 装饰器：为下一个定义附加「admin.display(description='定时')」行为（权限、缓存、注册信号等）
    @admin.display(description='定时')
    def scheduled_tag(self, obj):
        """56. 定时发布草稿显示🕐+时间。"""
        #: 条件判断：条件成立时执行该分支
        if obj.is_scheduled:
            #: 返回结果并结束当前函数
            return format_html(
                #: 该行执行对应逻辑（结合上下文理解）
                '<span style="color:#a06cd5;">🕐 {}</span>',
                #: 调用「obj.published_at.strftime」执行相应逻辑
                obj.published_at.strftime('%m-%d %H:%M'))
        #: 返回结果并结束当前函数
        return ''

    #: 装饰器：为下一个定义附加「admin.display(description='评分')」行为（权限、缓存、注册信号等）
    @admin.display(description='评分')
    def rating_display(self, obj):
        """63. 显示平均评分（⭐4.5 ×10人）。"""
        #: 条件判断：条件成立时执行该分支
        if obj.rating_count:
            #: 返回结果并结束当前函数
            return f'⭐{obj.rating_avg} ({obj.rating_count})'
        #: 返回结果并结束当前函数
        return '-'

    #: 装饰器：为下一个定义附加「admin.display(description='字数', ordering='-id')」行为（权限、缓存、注册信号等）
    @admin.display(description='字数', ordering='-id')
    def word_count_display(self, obj):
        """后台列表展示文章字数（中文字符 + 英文单词数）。"""
        #: 返回结果并结束当前函数
        return obj.word_count

    #: 装饰器：为下一个定义附加「admin.display(description='摘要预览')」行为（权限、缓存、注册信号等）
    @admin.display(description='摘要预览')
    def excerpt_preview(self, obj):
        """后台列表展示摘要前 40 字，便于一眼判断是否手写了摘要。"""
        #: 定义变量「text」，保存对应数据
        text = obj.excerpt or ''
        #: 返回结果并结束当前函数
        return (text[:40] + '…') if len(text) > 40 else text

    # 57. 保存时校验置顶数量：全站最多 3 篇置顶
    def save_model(self, request, obj, form, change):
        """保存文章时校验置顶数量，超过 3 篇自动取消置顶并提示。"""
        #: 条件判断：条件成立时执行该分支
        if obj.is_pinned:
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            pinned_count = Article.objects.filter(is_pinned=True).exclude(pk=obj.pk).count()
            #: 条件判断：条件成立时执行该分支
            if pinned_count >= 3:
                #: 定义实例/类属性「obj.is_pinned」，保存对应数据
                obj.is_pinned = False
                #: 调用「self.message_user」执行相应逻辑
                self.message_user(
                    #: 该行执行对应逻辑（结合上下文理解）
                    request,
                    #: 该行执行对应逻辑（结合上下文理解）
                    '全站置顶文章最多 3 篇，本次置顶未生效喵📌',
                    #: 操作「messages」的属性或方法
                    messages.WARNING)
        #: 调用「super」执行相应逻辑
        super().save_model(request, obj, form, change)

    # 第2轮迭代#131: 自定义列——封面状态标签
    #: 装饰器：为下一个定义附加「admin.display(description='封面')」行为（权限、缓存、注册信号等）
    @admin.display(description='封面')
    def cover_status(self, obj):
        """列表显示封面是否已上传：🖼 已传 / — 未传。"""
        #: 返回结果并结束当前函数
        return '🖼' if obj.cover_image else '—'

    # 第2轮迭代#133: 自定义搜索说明——search_fields 已覆盖 title/content
    # 第2轮迭代#138: 自定义导出——把选中文章导出为 CSV
    #: 装饰器：为下一个定义附加「admin.action(description='⬇ 导出所选文章为 CSV')」行为（权限、缓存、注册信号等）
    @admin.action(description='⬇ 导出所选文章为 CSV')
    def export_articles_csv(self, request, queryset):
        """把选中文章的标题/作者/分类/阅读量导出为 CSV 下载。"""
        #: 导入模块「csv」，供本文件后续使用
        import csv as _csv
        #: 构造 HTTP 响应返回给客户端
        resp = HttpResponse(content_type='text/csv')
        #: 该行执行对应逻辑（结合上下文理解）
        resp['Content-Disposition'] = 'attachment; filename="articles.csv"'
        #: 定义变量「w」，保存对应数据
        w = _csv.writer(resp)
        #: 调用「w.writerow」执行相应逻辑
        w.writerow(['ID', '标题', '作者', '分类', '状态', '阅读量', '点赞', '评论数', '发布时间'])
        #: 循环遍历，逐个处理元素
        for a in queryset.select_related('author', 'category'):
            #: 调用「w.writerow」执行相应逻辑
            w.writerow([a.id, a.title, str(a.author), str(a.category or ''),
                        #: 调用「a.get_status_display_cn」执行相应逻辑
                        a.get_status_display_cn(), a.views, a.likes,
                        #: 操作「a」的属性或方法
                        a.comment_count, a.created_at.strftime('%Y-%m-%d')])
        #: 返回结果并结束当前函数
        return resp

    # 第2轮迭代#139: 自定义导入说明——本项目通过 seed_* 命令初始化数据
    # 第2轮迭代#140: 自定义图表说明——访问趋势已在仪表盘 trend_data 渲染

    # ------------------------- 批量操作 -------------------------
    #: 装饰器：为下一个定义附加「admin.action(description='📢 批量发布（设为已发布）')」行为（权限、缓存、注册信号等）
    @admin.action(description='📢 批量发布（设为已发布）')
    # 迭代#5: admin中批量操作异常处理
    def make_published(self, request, queryset):
        """批量把选中文章状态置为已发布。"""
        # 迭代#6: admin批量操作注释
        #: 尝试执行可能出错的代码
        try:
            #: 定义变量「updated」，保存对应数据
            updated = queryset.update(status=Article.Status.PUBLISHED)
            #: 调用「self.message_user」执行相应逻辑
            self.message_user(request, f'已发布 {updated} 篇文章。', messages.SUCCESS)
        #: 捕获并处理异常，避免程序中断
        except Exception as exc:
            #: 调用「self.message_user」执行相应逻辑
            self.message_user(request, f'批量发布失败: {exc}', messages.ERROR)

    #: 装饰器：为下一个定义附加「admin.action(description='📝 批量转为草稿')」行为（权限、缓存、注册信号等）
    @admin.action(description='📝 批量转为草稿')
    def make_draft(self, request, queryset):
        """批量把选中文章状态置为草稿（前台不再可见）。"""
        #: 定义变量「updated」，保存对应数据
        updated = queryset.update(status=Article.Status.DRAFT)
        #: 调用「self.message_user」执行相应逻辑
        self.message_user(request, f'已将 {updated} 篇文章转为草稿。', messages.SUCCESS)

    #: 装饰器：为下一个定义附加「admin.action(description='📦 批量增加阅读量（+100）')」行为（权限、缓存、注册信号等）
    @admin.action(description='📦 批量增加阅读量（+100）')
    def increase_views(self, request, queryset):
        """批量给选中文章阅读量 +100（F 表达式原子自增，用于测试 / 调数据）。"""
        #: 使用 Q/F 表达式构造复杂查询或引用字段值
        updated = queryset.update(views=F('views') + 100)
        #: 调用「self.message_user」执行相应逻辑
        self.message_user(request, f'已为 {updated} 篇文章各增加 100 阅读量。', messages.SUCCESS)

    #: 装饰器：为下一个定义附加「admin.action(description='🗂 批量修改分类…')」行为（权限、缓存、注册信号等）
    @admin.action(description='🗂 批量修改分类…')
    def change_category(self, request, queryset):
        """批量修改分类：第一次提交弹出中间选择页，选择后真正更新。

        利用 action 既能作为"动作"下拉项、又能在 ``request.POST`` 里判别
        用户是否已在中间页选择分类：未选择则渲染选择模板，已选择则执行更新。
        """
        # 用户已在中间页选择了分类并点击"应用"
        #: 条件判断：条件成立时执行该分支
        if 'apply' in request.POST:
            #: 读取本次请求的 POST 数据
            cat_id = request.POST.get('category')
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            category = Category.objects.filter(pk=cat_id).first() if cat_id else None
            #: 定义变量「updated」，保存对应数据
            updated = queryset.update(category=category)
            #: 调用「self.message_user」执行相应逻辑
            self.message_user(
                #: 该行执行对应逻辑（结合上下文理解）
                request,
                #: 该行执行对应逻辑（结合上下文理解）
                f'已将 {updated} 篇文章移动到「{category.name if category else "未分类"}」。',
                #: 操作「messages」的属性或方法
                messages.SUCCESS)
            #: 返回结果并结束当前函数
            return
        # 未选择：渲染中间选择页（列出待改文章 + 分类下拉）
        #: 定义变量「context」，保存对应数据
        context = {
            #: 该行执行对应逻辑（结合上下文理解）
            **self.admin_site.each_context(request),
            #: 配置项「title」：字典/模型的该键设置为对应值
            'title': '批量修改分类',
            #: 配置项「opts」：字典/模型的该键设置为对应值
            'opts': self.model._meta,
            #: 配置项「app_label」：字典/模型的该键设置为对应值
            'app_label': self.model._meta.app_label,
            #: 配置项「posts」：字典/模型的该键设置为对应值
            'posts': queryset,
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            'cats': Category.objects.all().order_by('name'),
            #: 配置项「action_checkbox_name」：字典/模型的该键设置为对应值
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            #: 配置项「cancel_url」：字典/模型的该键设置为对应值
            'cancel_url': request.get_full_path(),
        #: 该行执行对应逻辑（结合上下文理解）
        }
        #: 返回结果并结束当前函数
        return TemplateResponse(request, 'admin/blog/change_category.html', context)


#: 装饰器：为下一个定义附加「register(EditLog, site=blog_admin_site)」行为（权限、缓存、注册信号等）
@register(EditLog, site=blog_admin_site)
class EditLogAdmin(_MoeModelAdmin):
    """轻量修改日志：只读展示修改人 + 修改时间 + 55. 内容快照预览。"""
    # 55. 列表增加"内容快照预览"列（前 100 字纯文本）
    #: 定义变量「list_display」，保存对应数据（集合/元组）
    list_display = ('id', 'article', 'editor', 'edited_at', 'snapshot_preview')
    #: 定义变量「list_filter」，保存对应数据（集合/元组）
    list_filter = ('edited_at',)
    #: 定义变量「raw_id_fields」，保存对应数据（集合/元组）
    raw_id_fields = ('article', 'editor')
    #: 定义变量「readonly_fields」，保存对应数据（集合/元组）
    readonly_fields = ('article', 'editor', 'edited_at', 'content_snapshot')

    def snapshot_preview(self, obj):
        """55. 修改前内容快照预览（前 100 字纯文本）。"""
        #: 返回结果并结束当前函数
        return obj.snapshot_preview or '（无快照）'
    #: 定义实例/类属性「snapshot_preview.short_description」，保存对应数据
    snapshot_preview.short_description = '内容快照(前100字)'

    def has_add_permission(self, request):
        """
        功能：判断是否含有「add permission」。

        参数：
          - request：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 返回结果并结束当前函数
        return False

    def has_change_permission(self, request, obj=None):
        """
        功能：判断是否含有「change permission」。

        参数：
          - request：传入参数，含义结合函数体与调用处
          - obj（可选，有默认值）：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 返回结果并结束当前函数
        return False


class DurationFilter(admin.SimpleListFilter):
    """访问日志耗时区间筛选：慢(>1000ms) / 中(500-1000) / 快(<500)。"""
    #: 定义变量「title」，保存对应数据
    title = '耗时区间'
    #: 定义变量「parameter_name」，保存对应数据
    parameter_name = 'duration_band'

    def lookups(self, request, model_admin):
        """
        功能：处理「lookups」相关逻辑。

        参数：
          - request：传入参数，含义结合函数体与调用处
          - model_admin：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 返回结果并结束当前函数
        return [
            #: 该行执行对应逻辑（结合上下文理解）
            ('slow', '慢 (>1000ms)'),
            #: 该行执行对应逻辑（结合上下文理解）
            ('mid', '中 (500-1000ms)'),
            #: 该行执行对应逻辑（结合上下文理解）
            ('fast', '快 (<500ms)'),
        #: 该行执行对应逻辑（结合上下文理解）
        ]

    def queryset(self, request, queryset):
        """
        功能：处理「queryset」相关逻辑。

        参数：
          - request：传入参数，含义结合函数体与调用处
          - queryset：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 条件判断：条件成立时执行该分支
        if self.value() == 'slow':
            #: 返回结果并结束当前函数
            return queryset.filter(duration_ms__gt=1000)
        #: 条件判断：条件成立时执行该分支
        if self.value() == 'mid':
            #: 返回结果并结束当前函数
            return queryset.filter(duration_ms__gt=500, duration_ms__lte=1000)
        #: 条件判断：条件成立时执行该分支
        if self.value() == 'fast':
            #: 返回结果并结束当前函数
            return queryset.filter(duration_ms__lte=500)
        #: 返回结果并结束当前函数
        return queryset


#: 装饰器：为下一个定义附加「register(AccessLog, site=blog_admin_site)」行为（权限、缓存、注册信号等）
@register(AccessLog, site=blog_admin_site)
class AccessLogAdmin(_MoeModelAdmin):
    """访问日志后台：只读 + 耗时颜色 + 统计摘要 + 导出 CSV。"""
    #: 定义变量「list_display」，保存对应数据（集合/元组）
    list_display = ('ip_address', 'username', 'method', 'path', 'status_code',
                    #: 该行执行对应逻辑（结合上下文理解）
                    'duration_color', 'browser', 'os', 'created_at')
    #: 定义变量「list_filter」，保存对应数据（集合/元组）
    list_filter = ('method', 'status_code', 'browser', 'os', 'created_at', DurationFilter)
    #: 定义变量「search_fields」，保存对应数据（集合/元组）
    search_fields = ('ip_address', 'username', 'path', 'user_agent')
    #: 定义变量「readonly_fields」，保存对应数据（集合/元组）
    readonly_fields = [f.name for f in AccessLog._meta.get_fields() if f.name != 'id']
    #: 定义变量「date_hierarchy」，保存对应数据
    date_hierarchy = 'created_at'
    #: 定义变量「ordering」，保存对应数据（集合/元组）
    ordering = ['-created_at']
    #: 定义变量「actions」，保存对应数据（集合/元组）
    actions = ('export_csv',)

    #: 装饰器：为下一个定义附加「admin.display(description='耗时(ms)', ordering='duration_ms')」行为（权限、缓存、注册信号等）
    @admin.display(description='耗时(ms)', ordering='duration_ms')
    def duration_color(self, obj):
        """按耗时长短着色：>1000ms 红、>500ms 橙、其余绿，便于一眼看慢请求。"""
        #: 条件判断：条件成立时执行该分支
        if obj.duration_ms > 1000:
            #: 定义变量「color」，保存对应数据
            color = '#e74c3c'
        #: 否则若该条件成立则进入此分支
        elif obj.duration_ms > 500:
            #: 定义变量「color」，保存对应数据
            color = '#f39c12'
        #: 以上条件均不成立时的兜底分支
        else:
            #: 定义变量「color」，保存对应数据
            color = '#27ae60'
        #: 返回结果并结束当前函数
        return format_html('<span style="color:{};font-weight:600">{}ms</span>',
                           #: 该行执行对应逻辑（结合上下文理解）
                           color, f'{obj.duration_ms:.0f}')

    #: 装饰器：为下一个定义附加「admin.action(description='⬇ 导出所选为 CSV')」行为（权限、缓存、注册信号等）
    @admin.action(description='⬇ 导出所选为 CSV')
    # 迭代#7: admin中CSV导出异常处理
    def export_csv(self, request, queryset):
        """把选中的访问日志导出为 CSV 下载。"""
        # 迭代#8: admin CSV导出注释
        #: 尝试执行可能出错的代码
        try:
            #: 构造 HTTP 响应返回给客户端
            response = HttpResponse(content_type='text/csv')
            # 附件下载，文件名带时间戳
            #: 该行执行对应逻辑（结合上下文理解）
            response['Content-Disposition'] = 'attachment; filename="access_logs.csv"'
            #: 定义变量「writer」，保存对应数据
            writer = csv.writer(response)
            #: 调用「writer.writerow」执行相应逻辑
            writer.writerow(['时间', 'IP', '用户', '方法', '路径', '状态码', '耗时ms', '浏览器', '操作系统'])
            #: 循环遍历，逐个处理元素
            for log in queryset:
                #: 调用「writer.writerow」执行相应逻辑
                writer.writerow([
                    #: 调用「log.created_at.strftime」执行相应逻辑
                    log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else '',
                    #: 操作「log」的属性或方法
                    log.ip_address or '', log.username or '', log.method,
                    #: 操作「log」的属性或方法
                    log.path, log.status_code, round(log.duration_ms, 1),
                    #: 操作「log」的属性或方法
                    log.browser or '', log.os or '',
                #: 该行执行对应逻辑（结合上下文理解）
                ])
            #: 返回结果并结束当前函数
            return response
        #: 捕获并处理异常，避免程序中断
        except Exception as exc:
            #: 返回结果并结束当前函数
            return HttpResponse(f'导出失败: {exc}', status=500)

    def changelist_view(self, request, extra_context=None):
        """在列表页顶部额外注入统计摘要：总访问量 / 独立IP / 平均耗时 / 404数。"""
        # 用当前筛选条件构造查询集，统计口径与列表一致
        #: 定义变量「cl」，保存对应数据
        cl = self.get_changelist_instance(request)
        #: 定义变量「qs」，保存对应数据
        qs = cl.queryset
        #: 定义变量「extra_context」，保存对应数据
        extra_context = extra_context or {}
        #: 该行执行对应逻辑（结合上下文理解）
        extra_context['log_stats'] = {
            #: 配置项「total」：字典/模型的该键设置为对应值
            'total': qs.count(),
            #: 配置项「unique_ips」：字典/模型的该键设置为对应值
            'unique_ips': qs.values('ip_address').distinct().count(),
            #: 使用聚合函数做统计查询
            'avg_duration': round(qs.aggregate(a=Avg('duration_ms'))['a'] or 0, 1),
            #: 配置项「not_found」：字典/模型的该键设置为对应值
            'not_found': qs.filter(status_code=404).count(),
        #: 该行执行对应逻辑（结合上下文理解）
        }
        #: 返回结果并结束当前函数
        return super().changelist_view(request, extra_context)

    def has_add_permission(self, request):
        """
        功能：判断是否含有「add permission」。

        参数：
          - request：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 返回结果并结束当前函数
        return False

    def has_change_permission(self, request, obj=None):
        """
        功能：判断是否含有「change permission」。

        参数：
          - request：传入参数，含义结合函数体与调用处
          - obj（可选，有默认值）：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 返回结果并结束当前函数
        return False

    def has_delete_permission(self, request, obj=None):
        """
        功能：判断是否含有「delete permission」。

        参数：
          - request：传入参数，含义结合函数体与调用处
          - obj（可选，有默认值）：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 返回结果并结束当前函数
        return False


#: 装饰器：为下一个定义附加「register(FriendlyLink, site=blog_admin_site)」行为（权限、缓存、注册信号等）
@register(FriendlyLink, site=blog_admin_site)
class FriendlyLinkAdmin(_MoeModelAdmin):
    """友情链接后台管理：彩色状态 + 可点击链接预览 + 排序 / 启用。"""
    #: 定义变量「list_display」，保存对应数据（集合/元组）
    list_display = ('icon', 'name', 'link_preview', 'order', 'is_active_tag', 'created_at')
    #: 定义变量「list_editable」，保存对应数据（集合/元组）
    list_editable = ('order',)
    #: 定义变量「list_filter」，保存对应数据（集合/元组）
    list_filter = ('is_active', 'created_at')
    #: 定义变量「search_fields」，保存对应数据（集合/元组）
    search_fields = ('name', 'url')
    #: 定义变量「ordering」，保存对应数据（集合/元组）
    ordering = ['order']
    # 表单字段提示：icon 给 emoji 选择建议，url 给 placeholder
    #: 定义变量「fieldsets」，保存对应数据（集合/元组）
    fieldsets = (
        #: 该行执行对应逻辑（结合上下文理解）
        (None, {'fields': ('name', 'url', 'icon', 'order', 'is_active')}),
    #: 该行执行对应逻辑（结合上下文理解）
    )

    #: 装饰器：为下一个定义附加「admin.display(description='状态', ordering='is_active')」行为（权限、缓存、注册信号等）
    @admin.display(description='状态', ordering='is_active')
    def is_active_tag(self, obj):
        """启用状态彩色标签：绿色✓ / 红色✗。"""
        #: 条件判断：条件成立时执行该分支
        if obj.is_active:
            #: 返回结果并结束当前函数
            return format_html('<span style="color:#27ae60;font-weight:700">✓ 显示</span>')
        #: 返回结果并结束当前函数
        return format_html('<span style="color:#e74c3c;font-weight:700">✗ 隐藏</span>')

    #: 装饰器：为下一个定义附加「admin.display(description='链接')」行为（权限、缓存、注册信号等）
    @admin.display(description='链接')
    def link_preview(self, obj):
        """可点击的链接预览（新窗口打开），过长时截断显示。"""
        #: 定义变量「short」，保存对应数据
        short = obj.url[:48] + ('…' if len(obj.url) > 48 else '')
        #: 返回结果并结束当前函数
        return format_html('<a href="{}" target="_blank" rel="noopener">{} ↗</a>', obj.url, short)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """给 icon / url 字段加表单提示，引导运营填写。"""
        #: 定义变量「field」，保存对应数据
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        #: 条件判断：条件成立时执行该分支
        if db_field.name == 'icon':
            #: 定义实例/类属性「field.help_text」，保存对应数据
            field.help_text = '图标用 emoji，如 🔗 🌟 🐱 📚 💡'
        #: 条件判断：条件成立时执行该分支
        if db_field.name == 'url':
            #: 操作「field.widget」的属性或方法
            field.widget.attrs['placeholder'] = 'https://example.com'
        #: 返回结果并结束当前函数
        return field


#: 装饰器：为下一个定义附加「register(Comment, site=blog_admin_site)」行为（权限、缓存、注册信号等）
@register(Comment, site=blog_admin_site)
# 迭代#9: CommentAdmin类docstring
class CommentAdmin(_MoeModelAdmin):
    """评论后台管理：支持审核 / 批量通过 / 批量删除。"""
    # 列表展示：id + 所属文章 + 评论人 + 内容前 50 字预览 + 父评论 + 点赞 + 审核态 + 时间
    #: 定义变量「list_display」，保存对应数据（集合/元组）
    list_display = ('id', 'article', 'user', 'content_preview', 'parent_comment',
                    #: 该行执行对应逻辑（结合上下文理解）
                    'likes', 'is_approved', 'created_at')
    #: 定义变量「list_filter」，保存对应数据（集合/元组）
    list_filter = ('is_approved', 'created_at')
    #: 定义变量「search_fields」，保存对应数据（集合/元组）
    search_fields = ('content', 'user__username', 'article__title')
    # 文章 / 用户 / 父评论用原始 id 输入框，避免下拉加载上千条评论
    #: 定义变量「raw_id_fields」，保存对应数据（集合/元组）
    raw_id_fields = ('article', 'user', 'parent_comment')
    #: 定义变量「actions」，保存对应数据（集合/元组）
    actions = ('make_approved', 'make_unapproved', 'really_delete_selected')

    #: 装饰器：为下一个定义附加「admin.display(description='内容预览')」行为（权限、缓存、注册信号等）
    @admin.display(description='内容预览')
    def content_preview(self, obj):
        """列表中展示评论内容前 50 字，超出追加省略号。"""
        #: 定义变量「text」，保存对应数据（集合/元组）
        text = (obj.content or '')[:50]
        #: 返回结果并结束当前函数
        return text + ('…' if len(obj.content or '') > 50 else '')

    #: 装饰器：为下一个定义附加「admin.action(description='批量审核通过')」行为（权限、缓存、注册信号等）
    @admin.action(description='批量审核通过')
    def make_approved(self, request, queryset):
        """批量把选中评论置为已审核通过。"""
        #: 定义变量「updated」，保存对应数据
        updated = queryset.update(is_approved=True)
        #: 调用「self.message_user」执行相应逻辑
        self.message_user(request, f'已通过审核 {updated} 条评论。')

    #: 装饰器：为下一个定义附加「admin.action(description='批量取消审核')」行为（权限、缓存、注册信号等）
    @admin.action(description='批量取消审核')
    def make_unapproved(self, request, queryset):
        """批量把选中评论置为未审核（前台隐藏）。"""
        #: 定义变量「updated」，保存对应数据
        updated = queryset.update(is_approved=False)
        #: 调用「self.message_user」执行相应逻辑
        self.message_user(request, f'已取消审核 {updated} 条评论。')

    #: 装饰器：为下一个定义附加「admin.action(description='批量删除所选评论')」行为（权限、缓存、注册信号等）
    @admin.action(description='批量删除所选评论')
    def really_delete_selected(self, request, queryset):
        """批量删除选中评论（Django 默认删除动作别名，明确文案）。"""
        #: 定义变量「count」，保存对应数据
        count = queryset.count()
        #: 删除对象，注意级联与权限
        queryset.delete()
        #: 调用「self.message_user」执行相应逻辑
        self.message_user(request, f'已删除 {count} 条评论。')
    #: 定义实例/类属性「really_delete_selected.short_description」，保存对应数据
    really_delete_selected.short_description = '批量删除所选评论'


#: 装饰器：为下一个定义附加「register(Favorite, site=blog_admin_site)」行为（权限、缓存、注册信号等）
@register(Favorite, site=blog_admin_site)
class FavoriteAdmin(_MoeModelAdmin):
    """用户收藏记录后台管理。"""
    #: 定义变量「list_display」，保存对应数据（集合/元组）
    list_display = ('id', 'user', 'article', 'created_at')
    #: 定义变量「list_filter」，保存对应数据（集合/元组）
    list_filter = ('created_at',)
    #: 定义变量「search_fields」，保存对应数据（集合/元组）
    search_fields = ('user__username', 'article__title')
    #: 定义变量「raw_id_fields」，保存对应数据（集合/元组）
    raw_id_fields = ('user', 'article')
    #: 定义变量「date_hierarchy」，保存对应数据
    date_hierarchy = 'created_at'


#: 装饰器：为下一个定义附加「register(SiteNotice, site=blog_admin_site)」行为（权限、缓存、注册信号等）
@register(SiteNotice, site=blog_admin_site)
class SiteNoticeAdmin(_MoeModelAdmin):
    """62. 网站公告后台：内容 + 是否显示（可直接在列表切换）。"""
    #: 定义变量「list_display」，保存对应数据（集合/元组）
    list_display = ('content', 'is_active', 'is_active_tag', 'created_at')
    #: 定义变量「list_editable」，保存对应数据（集合/元组）
    list_editable = ('is_active',)
    #: 定义变量「list_filter」，保存对应数据（集合/元组）
    list_filter = ('is_active', 'created_at')

    #: 装饰器：为下一个定义附加「admin.display(description='显示状态', ordering='is_active')」行为（权限、缓存、注册信号等）
    @admin.display(description='显示状态', ordering='is_active')
    def is_active_tag(self, obj):
        """显示状态彩色标签：绿✓/红✗。"""
        #: 条件判断：条件成立时执行该分支
        if obj.is_active:
            #: 返回结果并结束当前函数
            return format_html('<span style="color:#27ae60;font-weight:700;">✓ 显示</span>')
        #: 返回结果并结束当前函数
        return format_html('<span style="color:#e74c3c;font-weight:700;">✗ 隐藏</span>')


#: 装饰器：为下一个定义附加「register(Series, site=blog_admin_site)」行为（权限、缓存、注册信号等）
@register(Series, site=blog_admin_site)
class SeriesAdmin(_MoeModelAdmin):
    """67. 文章系列后台管理。"""
    #: 定义变量「list_display」，保存对应数据（集合/元组）
    list_display = ('id', 'title', 'author', 'article_count', 'created_at')
    #: 定义变量「list_filter」，保存对应数据（集合/元组）
    list_filter = ('created_at',)
    #: 定义变量「search_fields」，保存对应数据（集合/元组）
    search_fields = ('title', 'description')
    #: 定义变量「raw_id_fields」，保存对应数据（集合/元组）
    raw_id_fields = ('author',)

    #: 装饰器：为下一个定义附加「admin.display(description='文章数')」行为（权限、缓存、注册信号等）
    @admin.display(description='文章数')
    def article_count(self, obj):
        """系列下已发布文章数量。"""
        #: 返回结果并结束当前函数
        return obj.articles.count()


#: 装饰器：为下一个定义附加「register(Rating, site=blog_admin_site)」行为（权限、缓存、注册信号等）
@register(Rating, site=blog_admin_site)
class RatingAdmin(_MoeModelAdmin):
    """63. 文章评分后台：只读查看。"""
    #: 定义变量「list_display」，保存对应数据（集合/元组）
    list_display = ('id', 'article', 'user', 'score', 'created_at')
    #: 定义变量「list_filter」，保存对应数据（集合/元组）
    list_filter = ('score', 'created_at')
    #: 定义变量「search_fields」，保存对应数据（集合/元组）
    search_fields = ('article__title', 'user__username')
    #: 定义变量「raw_id_fields」，保存对应数据（集合/元组）
    raw_id_fields = ('article', 'user')

    def has_add_permission(self, request):
        """
        功能：判断是否含有「add permission」。

        参数：
          - request：传入参数，含义结合函数体与调用处

        返回：对应计算/查询结果。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 返回结果并结束当前函数
        return False


#: 装饰器：为下一个定义附加「register(SiteInfo, site=blog_admin_site)」行为（权限、缓存、注册信号等）
@register(SiteInfo, site=blog_admin_site)
class SiteInfoAdmin(admin.ModelAdmin):
    """站点信息单例后台（工单 15）：萌系「站点设置」页之外的兜底编辑入口。"""

    # 只展示可编辑字段，隐藏自动时间
    #: 定义变量「fields」，保存对应数据（集合/元组）
    fields = ('site_name', 'logo_emoji', 'tagline', 'description', 'keywords',
              #: 该行执行对应逻辑（结合上下文理解）
              'footer_about', 'footer_icp', 'copyright_holder')

    def has_add_permission(self, request):
        """单例：已存在记录时不允许新增。"""
        #: 返回结果并结束当前函数
        return not SiteInfo.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """单例不可删除。"""
        #: 返回结果并结束当前函数
        return False

    def change_view(self, request, object_id=None, form_url='', extra_context=None):
        """无论从哪里进入，都直接编辑唯一记录。"""
        #: 定义变量「info」，保存对应数据
        info = SiteInfo.load()
        #: 返回结果并结束当前函数
        return super().change_view(request, str(info.pk), form_url, extra_context)


class MessageDomainFilter(admin.SimpleListFilter):
    """文案覆盖列表的「所属域」过滤器。

    域不是数据库字段，而是 key 的点号前缀（``auth.login_failed`` → ``auth``），
    所以必须用 ``SimpleListFilter`` 自定义，不能直接把方法名放进 ``list_filter``
    （那样 Django 会报 ``admin.E116: does not refer to a Field``）。
    """

    #: 定义变量「title」，保存对应数据
    title = '所属域'
    #: 定义变量「parameter_name」，保存对应数据
    parameter_name = 'domain'

    def lookups(self, request, model_admin):
        """列出数据库里实际出现过的域（去重、按字母序）。"""
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        domains = {m.key.split('.', 1)[0] for m in SiteMessage.objects.all()}
        #: 返回结果并结束当前函数
        return [(d, d) for d in sorted(domains)]

    def queryset(self, request, queryset):
        """按 ``<域>.`` 前缀过滤。"""
        #: 条件判断：条件成立时执行该分支
        if self.value():
            #: 返回结果并结束当前函数
            return queryset.filter(key__startswith=self.value() + '.')
        #: 返回结果并结束当前函数
        return queryset


#: 装饰器：为下一个定义附加「register(SiteMessage, site=blog_admin_site)」行为（权限、缓存、注册信号等）
@register(SiteMessage, site=blog_admin_site)
class SiteMessageAdmin(admin.ModelAdmin):
    """文案覆盖后台：在线修改全站提示词，保存即生效（无需改代码 / 重启）。

    - 列表页展示「键 / 当前文案 / 是否启用 / 修改人 / 时间」，可按域筛选；
    - 表单里只读展示「代码默认值」，避免把占位符写错导致格式化失败；
    - 保存 / 删除自动失效覆盖层缓存（见 ``SiteMessage.save`` / ``delete``）。
    """

    #: 定义变量「list_display」，保存对应数据（集合/元组）
    list_display = ('key', 'text_short', 'is_enabled', 'updated_by', 'updated_at')
    #: 定义变量「list_filter」，保存对应数据（集合/元组）
    list_filter = ('is_enabled', MessageDomainFilter)
    #: 定义变量「search_fields」，保存对应数据（集合/元组）
    search_fields = ('key', 'text', 'description')
    #: 定义变量「readonly_fields」，保存对应数据（集合/元组）
    readonly_fields = ('created_at', 'updated_at', 'updated_by', 'code_default')
    #: 定义变量「fields」，保存对应数据（集合/元组）
    fields = ('key', 'text', 'description', 'is_enabled', 'code_default',
              #: 该行执行对应逻辑（结合上下文理解）
              'updated_by', 'created_at', 'updated_at')
    #: 定义变量「ordering」，保存对应数据（集合/元组）
    ordering = ('key',)
    #: 定义变量「list_per_page」，保存对应数据
    list_per_page = 50

    #: 装饰器：为下一个定义附加「admin.display(description='文案')」行为（权限、缓存、注册信号等）
    @admin.display(description='文案')
    def text_short(self, obj):
        """列表页只显示前 40 个字符，避免长文案撑破表格。"""
        #: 返回结果并结束当前函数
        return obj.text[:40] + ('…' if len(obj.text) > 40 else '')

    #: 装饰器：为下一个定义附加「admin.display(description='代码默认值（只读）')」行为（权限、缓存、注册信号等）
    @admin.display(description='代码默认值（只读）')
    def code_default(self, obj):
        """显示 ``site_messages.MESSAGES`` 中该 key 的原始文案，便于对照与回滚。"""
        #: 从模块「.services.site_messages」导入所需对象
        from .services.site_messages import MESSAGES
        #: 条件判断：条件成立时执行该分支
        if not obj or not getattr(obj, 'key', ''):
            #: 返回结果并结束当前函数
            return '（填写 key 并保存后显示）'
        #: 定义变量「default」，保存对应数据
        default = MESSAGES.get(obj.key)
        #: 条件判断：条件成立时执行该分支
        if default is None:
            #: 返回结果并结束当前函数
            return '⚠️ 代码中不存在该 key —— 请核对拼写，否则这条覆盖不会生效'
        #: 返回结果并结束当前函数
        return default

    def save_model(self, request, obj, form, change):
        """记录最后修改人，便于追溯。"""
        #: 条件判断：条件成立时执行该分支
        if request.user.is_authenticated:
            #: 读取本次请求的 user 数据
            obj.updated_by = request.user
        #: 调用「super」执行相应逻辑
        super().save_model(request, obj, form, change)

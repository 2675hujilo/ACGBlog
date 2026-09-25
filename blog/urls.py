"""blog 应用路由配置。

本文件统一维护两类路由：
- ``urlpatterns``：前台页面路由（函数视图，返回 HTML 模板）；
- ``api_urlpatterns``：DRF 接口路由（类视图，返回 JSON），
  由项目根 urls.py 挂载到 ``/api/`` 前缀下。
"""
from django.conf import settings
from django.urls import path, include

from . import views
from .features_round5 import urls as round5_urls
from . import features_live2d

# ---------------- 页面路由 ----------------
# 对应 views.py 中的函数视图，name 供模板 {% url %} 与 reverse() 反解
urlpatterns = [
    # 首页：文章列表
    path('', views.index, name='index'),
    # 文章详情页，pk 为文章主键
    path('article/<int:pk>/', views.article_detail, name='article_detail'),
    # 切换文章收藏状态（AJAX，登录用户）
    path('article/<int:pk>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    # 发表评论 / 回复（AJAX 接口，登录用户）
    path('article/<int:article_pk>/comment/', views.comment_create, name='comment_create'),
    # 新建文章
    path('new/', views.article_new, name='article_new'),
    # 编辑指定文章
    path('edit/<int:pk>/', views.article_edit, name='article_edit'),
    # 删除指定文章
    path('delete/<int:pk>/', views.article_delete, name='article_delete'),

    # 全部分类列表页
    path('categories/', views.categories, name='categories'),
    # 单个分类下的文章列表
    path('category/<int:pk>/', views.category_detail, name='category_detail'),
    # 全部标签列表页
    path('tags/', views.tags, name='tags'),
    # 单个标签下的文章列表
    path('tag/<int:pk>/', views.tag_detail, name='tag_detail'),
    # 全文搜索页
    path('search/', views.search, name='search'),
    # 文章归档页（按年月时间轴分组）
    path('archive/', views.archive, name='archive'),

    # 登录 / 注册 / 登出
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    # 用户个人主页
    path('user/<str:username>/', views.user_profile, name='user_profile'),
    # 用户设置页（需登录）
    path('settings/', views.user_settings, name='user_settings'),
    path('console/', views.staff_console, name='staff_console'),
    path('console/site-settings/', views.site_settings_page, name='site_settings'),
    # Round6（bug16）内容审核：待审文章 / 举报审批
    path('console/moderation/', views.moderation_queue, name='moderation_queue'),
    path('console/moderation/article/<int:pk>/', views.moderate_article, name='moderate_article'),
    path('console/moderation/report/<int:pk>/', views.moderate_report, name='moderate_report'),
    # Bug1：推广申请审批 + 审核全局设置保存
    path('console/moderation/promotion/<int:pk>/', views.moderate_promotion, name='moderate_promotion'),
    path('console/moderation/settings/', views.moderation_settings_save, name='moderation_settings_save'),
    # Bug8 回收站：恢复 / 彻底删除（文章 / 评论）
    path('console/moderation/article/<int:pk>/restore/', views.restore_article, name='restore_article'),
    path('console/moderation/article/<int:pk>/purge/', views.hard_delete_article, name='hard_delete_article'),
    path('console/moderation/comment/<int:pk>/restore/', views.restore_comment, name='restore_comment'),
    path('console/moderation/comment/<int:pk>/purge/', views.hard_delete_comment, name='hard_delete_comment'),
    # 我的文章管理页（需登录）
    path('my-articles/', views.my_articles, name='my_articles'),
    # Round6（bug14/15）我的小站系列页面（均需登录）
    path('notifications/', views.notifications_page, name='notifications_page'),
    path('favorites/', views.my_favorites, name='my_favorites'),
    path('reading-history/', views.reading_history_page, name='reading_history_page'),
    path('liked/', views.my_liked, name='my_liked'),
    path('my-comments/', views.my_comments, name='my_comments'),

    # 67. 文章系列：系列列表页 + 系列详情页
    path('series/', views.series_list, name='series_list'),
    path('series/new/', views.series_create, name='series_create'),
    path('series/<int:pk>/', views.series_detail, name='series_detail'),
    # 70. 随机文章：随机跳转到一篇已发布文章
    path('random/', views.random_article, name='random_article'),
    # 工单6 第7项：原第三方登录占位路由 auth/<provider>/ 仅渲染「开发中」页、无真实
    # OAuth，已移除并归档至 docs/archived_feature_stubs/social_login/（登录/注册按钮同步移除）。
    # 69. 网站运行状态页
    path('status/', views.server_status, name='server_status'),

    # ---------------- SEO 输出 ----------------
    # 站点地图（XML）
    path('sitemap.xml', views.sitemap, name='sitemap'),
    # RSS 订阅源（RSS 2.0）
    path('feed/', views.rss_feed, name='rss_feed'),
    # 爬虫抓取规则（纯文本）
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('s/<str:code>/', views.short_link_redirect, name='short_link_redirect'),
]

# ---------------- DRF 接口路由 ----------------
# 对应 views.py 中的 APIView 子类，挂载于 /api/ 前缀
api_urlpatterns = [
    # 搜索自动补全（GET，返回匹配的文章标题建议）
    path('search/suggest/', views.search_suggest, name='api_search_suggest'),
    # 工单6-5：右栏热门文章 周/月/总榜（返回 HTML 片段，首页 AJAX 切换）
    path('hot-articles/', views.api_hot_articles, name='api_hot_articles'),
    # 文章列表（GET）+ 新建文章（POST）
    path('articles/', views.ArticleListCreateView.as_view(), name='api_article_list'),
    # 单篇文章的详情 / 修改 / 删除
    path('articles/<int:pk>/', views.ArticleDetailView.as_view(), name='api_article_detail'),
    # 文章点赞（POST，session 防重复）
    path('articles/<int:pk>/like/', views.like_article, name='api_article_like'),
    # 63. 文章评分（POST，登录用户，1~5 星，幂等更新）
    path('articles/<int:pk>/rate/', views.rate_article, name='api_article_rate'),
    # 70. API 文档页（渲染 HTML 说明文档）
    path('docs/', views.api_docs, name='api_docs'),
    # 评论点赞（POST，session 防重复）
    path('comments/<int:pk>/like/', views.like_comment, name='api_comment_like'),
    # 富文本编辑器图片上传
    path('upload-image/', views.ImageUploadView.as_view(), name='api_image_upload'),
    # 第3轮迭代#8: 文章点赞 / AJAX 评论提交（统一 /api/article/<pk>/ 前缀）
    path('article/<int:pk>/like/', views.like_article, name='api_article_like_v2'),
    path('article/<int:article_pk>/comment/', views.comment_create, name='api_article_comment_v2'),
    # 第4轮 C7: 文章分享计数（登录或匿名均可，F() 原子自增）
    path('article/<int:pk>/share/', views.share_article, name='api_article_share'),
    # Bug1：作者申请置顶/精华/热门；管理员直接切换
    path('article/<int:pk>/promotion-request/', views.api_article_promotion_request, name='api_promotion_request'),
    path('article/<int:pk>/toggle-promotion/', views.api_article_toggle_promotion, name='api_toggle_promotion'),
    # 分类列表（GET）+ 新建分类（POST）
    path('categories/', views.CategoryListCreateView.as_view(), name='api_category_list'),
    # 单个分类的详情 / 修改 / 删除
    path('categories/<int:pk>/', views.CategoryDetailView.as_view(), name='api_category_detail'),
    # 标签列表（GET）+ 新建标签（POST）
    path('tags/', views.TagListCreateView.as_view(), name='api_tag_list'),
    # 单个标签的详情 / 修改 / 删除
    path('tags/<int:pk>/', views.TagDetailView.as_view(), name='api_tag_detail'),
    # ---------------- 第5轮新增 API ----------------
    # 用户偏好
    path('user/preferences/', views.api_user_preferences, name='api_user_preferences'),
    # 文章踩
    path('article/<int:pk>/dislike/', views.api_article_dislike, name='api_article_dislike'),
    # 评论图片上传 / 举报 / 撤回
    path('comment/image/upload/', views.api_comment_image_upload, name='api_comment_image_upload'),
    path('comment/<int:pk>/report/', views.api_comment_report, name='api_comment_report'),
    path('comment/<int:pk>/', views.api_comment_delete, name='api_comment_delete'),
    # 收藏夹管理
    path('favorite_folders/', views.api_favorite_folder_list, name='api_favorite_folder_list'),
    path('favorite_folders/<int:pk>/', views.api_favorite_folder_detail, name='api_favorite_folder_detail'),
    # 通知中心（静态段需排在动态段前）
    path('notifications/read_all/', views.api_notification_read_all, name='api_notification_read_all'),
    path('notifications/unread_count/', views.api_notification_unread_count, name='api_notification_unread_count'),
    path('notifications/', views.api_notification_list, name='api_notification_list'),
    path('notifications/<int:pk>/read/', views.api_notification_read, name='api_notification_read'),
    # 搜索热词
    path('search/hot/', views.api_search_hot, name='api_search_hot'),
    # 文章导出 / 二维码
    path('article/<int:pk>/export/md/', views.api_article_export_md, name='api_article_export_md'),
    path('article/<int:pk>/export/pdf/', views.api_article_export_pdf, name='api_article_export_pdf'),
    path('article/<int:pk>/qrcode/', views.api_article_qrcode, name='api_article_qrcode'),
    # 短链接
    path('short_link/', views.api_short_link, name='api_short_link'),
    # 用户徽章 / 在线用户
    path('user/badges/', views.api_user_badges, name='api_user_badges'),
    path('online_users/', views.api_online_users, name='api_online_users'),
]


# ============================ 第2轮迭代#231-#240: URL 优化 ============================
# 第2轮迭代#231: URL 命名空间说明——/api/ 已用 namespace='api'，前台无命名空间
# 第2轮迭代#232: URL 名称优化——所有 path 均具语义化 name，便于 {% url %} 反解
# 第2轮迭代#233: URL 参数验证——主键统一用 <int:pk>，字符串用 <str:provider>
# 第2轮迭代#234: URL 重定向说明——尾部斜杠差异由 CommonMiddleware 自动补全/重定向
# 第2轮迭代#235: URL 规范化说明——查询串参数在视图层校验，非法值回退默认
# 第2轮迭代#236: URL 性能说明——静态/媒体由 Web 服务器直出，不进 Django 中间件
# 第2轮迭代#237: URL SEO 说明——sitemap.xml / feed/ / robots.txt 独立路由
# 第2轮迭代#238: URL 版本控制说明——/api/ 前缀即版本边界，后续可加 /api/v2/
# 第2轮迭代#239: URL 别名——/home/ 等价于首页
# Live2D 看板娘 API（参考 fghrsh/live2d_api 接口规范）
urlpatterns += [
    path('api/live2d/models/', features_live2d.model_list, name='live2d_model_list'),
    path('api/live2d/get/', features_live2d.get_model, name='live2d_get_model'),
    path('api/live2d/model/<str:model>/<int:skin>.json', features_live2d.get_model, name='live2d_model_json'),
    path('api/live2d/switch_model/', features_live2d.switch_model, name='live2d_switch_model'),
    path('api/live2d/rand_model/', features_live2d.rand_model, name='live2d_rand_model'),
    path('api/live2d/switch_skin/', features_live2d.switch_skin, name='live2d_switch_skin'),
    path('api/live2d/rand_skin/', features_live2d.rand_skin, name='live2d_rand_skin'),
    path('api/live2d/game/', features_live2d.game_play, name='live2d_game'),
]

urlpatterns += [
    path('home/', views.index, name='home_alias'),
    # 第6轮: 404 页面手动测试路由（验证接樱花小游戏/文案/暗黑模式）
    path('test-404/', views.test_404_page, name='test_404'),
    # 工单17：原 /api/features/ 下挂载的 1000 个路由均为自动生成的 csrf_exempt
    # echo 占位桩（仅回显请求体、无真实业务，且前端零调用），已整体移除并归档至
    # docs/archived_feature_stubs/，收敛攻击面、消除重复路由。
    # 第5轮功能框架：仅保留真实的功能开关管理端点（/api/round5/features/）；
    # 原 11,606 个无实现的占位路由已归档清理，详见 features_round5/urls.py。
    path('api/round5/', include(round5_urls)),
    path('api/refresh-assets/', views.api_refresh_assets, name='api_refresh_assets'),
]
# 第2轮迭代#240: URL 反向解析优化说明——统一用 name 反解，避免硬编码路径

# Bug27: 自定义萌系错误页（DEBUG=False 时由 Django 调用；DEBUG=True 时由 CuteErrorPagesMiddleware 接管）
handler400 = 'django.views.defaults.bad_request'      # 渲染根模板 400.html
handler403 = 'django.views.defaults.permission_denied'  # 渲染根模板 403.html
handler404 = 'django.views.defaults.page_not_found'    # 渲染根模板 404.html
handler500 = 'django.views.defaults.server_error'      # 渲染根模板 500.html

# 调试：缓存查看端点（仅 DEBUG 模式挂载，用于开发时在浏览器查看进程内缓存）
if settings.DEBUG:
    urlpatterns += [
        path('__debug_cache/', views.debug_cache_dump, name='debug_cache_dump'),
    ]

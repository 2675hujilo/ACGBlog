"""项目根路由配置。

集中挂载三类入口：
- ``admin/``：Django 内置后台管理；
- ``api/``：博客提供的 RESTful 接口（DRF）；
- ``''``：博客前台页面路由。

此外在 DEBUG 模式下额外挂载媒体文件访问路由，
并注册自定义的 403 / 404 / 500 错误视图。
"""
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from blog.admin import blog_admin_site
from blog.urls import api_urlpatterns

# 路由表：按顺序匹配，命中即停止
urlpatterns = [
    # 自定义后台管理站点（含运营仪表盘 / 统计卡片）
    path('admin/', blog_admin_site.urls),
    # 挂载 DRF 接口，命名空间为 'api'（blog.urls 中的 api_urlpatterns）
    path('api/', include((api_urlpatterns, 'api'), namespace='api')),
    # 挂载博客前台页面路由（blog.urls 中的普通 urlpatterns）
    path('', include('blog.urls')),
]

# 仅在 DEBUG 模式下由 Django 自带服务提供 MEDIA 文件访问；
# 生产环境应由 Nginx 等 Web 服务器直接处理 /media/
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# 自定义错误页面（二次元风格）：在 DEBUG=False 且无对应视图模板时生效
handler404 = 'blog.views.custom_404'  # 页面不存在
handler500 = 'blog.views.custom_500'  # 服务器内部错误
handler403 = 'blog.views.custom_403'  # 禁止访问

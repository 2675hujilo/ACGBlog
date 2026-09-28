"""
DjangoBlog 项目配置（萌系二次元博客版）。

- 数据库：MySQL，库名 Blog_new，字符集 utf8mb4；
- 全站统一 CKEditor 富文本（本地静态资源）；
- Celery + Redis 异步任务队列（访问日志异步写入、定时清理）；
- 自定义 AccessLogMiddleware 全路由访问日志；
- Windows 本地开发直接 runserver，Celery worker 用 --pool=solo 启动。
"""
#: 导入模块「os」，供本文件后续使用
import os
#: 从模块「pathlib」导入所需对象
from pathlib import Path

# Celery 定时任务调度（crontab 表达式用于 CELERY_BEAT_SCHEDULE）
#: 从模块「celery.schedules」导入所需对象
from celery.schedules import crontab

# 项目根目录（manage.py 所在目录），后续路径均基于它拼接
#: 定义变量「BASE_DIR」，保存对应数据
BASE_DIR = Path(__file__).resolve().parent.parent

# 密钥：优先从环境变量读取；本地开发兜底使用内置值（生产环境必须通过环境变量覆盖）
#: 定义变量「SECRET_KEY」，保存对应数据
SECRET_KEY = os.environ.get(
    #: 该行执行对应逻辑（结合上下文理解）
    'DJANGO_SECRET_KEY',
    #: 该行执行对应逻辑（结合上下文理解）
    'django-insecure-m=uppkb@sj^&ohvxi&_b8t_po5_jz3@nxc!dyq7kmmj8=tu710',  # 仅本地开发兜底
#: 该行执行对应逻辑（结合上下文理解）
)
# 调试模式：默认开启（'1'），生产环境务必设为 '0'，否则会泄露敏感信息
#: 定义变量「DEBUG」，保存对应数据
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'
# 允许访问的主机名；'*' 表示开发阶段放行所有域名，生产应改为具体域名
#: 定义变量「ALLOWED_HOSTS」，保存对应数据（集合/元组）
ALLOWED_HOSTS = ['*']

# 已安装的应用：含 Django 内置应用、DRF 以及本项目的 blog 应用
#: 定义变量「INSTALLED_APPS」，保存对应数据（集合/元组）
INSTALLED_APPS = [
    #: 该行执行对应逻辑（结合上下文理解）
    'django.contrib.admin',            # 后台管理站点
    #: 该行执行对应逻辑（结合上下文理解）
    'django.contrib.auth',             # 认证 / 授权框架
    #: 该行执行对应逻辑（结合上下文理解）
    'django.contrib.contenttypes',     # 内容类型框架（与权限系统配合）
    #: 该行执行对应逻辑（结合上下文理解）
    'django.contrib.sessions',         # 会话支持
    #: 该行执行对应逻辑（结合上下文理解）
    'django.contrib.messages',         # 一次性消息提示
    #: 该行执行对应逻辑（结合上下文理解）
    'django.contrib.staticfiles',      # 静态文件管理
    #: 该行执行对应逻辑（结合上下文理解）
    'rest_framework',                  # Django REST framework
    #: 该行执行对应逻辑（结合上下文理解）
    'blog.apps.BlogConfig',            # 本项目博客应用配置
#: 该行执行对应逻辑（结合上下文理解）
]

# 中间件列表：按顺序自上而下处理请求、自下而上处理响应
# AccessLogMiddleware 放在 Security 之后、Session 之前：
# - process_request 阶段只记录开始时间（此时 session/user 尚未就绪，不可访问）；
# - process_response / process_exception 阶段所有内层中间件已执行完毕，
#   session、user 均可用，可捕获完整请求生命周期（含 500 异常与 404 响应）。
#: 定义变量「MIDDLEWARE」，保存对应数据（集合/元组）
MIDDLEWARE = [
    #: 该行执行对应逻辑（结合上下文理解）
    'django.middleware.security.SecurityMiddleware',          # 各类安全相关响应头
    #: 该行执行对应逻辑（结合上下文理解）
    'whitenoise.middleware.WhiteNoiseMiddleware',              # 生产环境静态文件压缩与缓存服务
    #: 该行执行对应逻辑（结合上下文理解）
    'blog.middleware.AccessLogMiddleware',                     # 自定义：记录全路由访问日志
    #: 该行执行对应逻辑（结合上下文理解）
    'django.contrib.sessions.middleware.SessionMiddleware',    # 会话解析
    #: 该行执行对应逻辑（结合上下文理解）
    'django.middleware.common.CommonMiddleware',               # 通用处理（URL 规范化等）
    #: 该行执行对应逻辑（结合上下文理解）
    'django.middleware.csrf.CsrfViewMiddleware',               # CSRF 防护
    #: 读取本次请求的 user 数据
    'django.contrib.auth.middleware.AuthenticationMiddleware', # 绑定 request.user
    #: 该行执行对应逻辑（结合上下文理解）
    'django.contrib.messages.middleware.MessageMiddleware',    # 消息框架
    #: 该行执行对应逻辑（结合上下文理解）
    'django.middleware.clickjacking.XFrameOptionsMiddleware', # 防止点击劫持
    #: 该行执行对应逻辑（结合上下文理解）
    'blog.middleware.OnlineStatusMiddleware',                    # 第5轮: 在线状态更新
    #: 该行执行对应逻辑（结合上下文理解）
    'blog.middleware.SiteInfoMiddleware',                        # 工单15: 站点信息单例注入
    #: 该行执行对应逻辑（结合上下文理解）
    'blog.middleware.SiteMessagesMiddleware',                    # Bug9: 全站文案注入 request.msg
    #: 该行执行对应逻辑（结合上下文理解）
    'blog.middleware.MascotToggleMiddleware',                    # Bug9: 看板娘开关（?waifu=on|off）
    #: 该行执行对应逻辑（结合上下文理解）
    'blog.middleware.CuteErrorPagesMiddleware',                 # Bug27: DEBUG下也显示萌系错误页
#: 该行执行对应逻辑（结合上下文理解）
]

# 根路由模块，即 URL 分发的入口
#: 定义变量「ROOT_URLCONF」，保存对应数据
ROOT_URLCONF = 'DjangoBlog.urls'

# 模板引擎配置
#: 定义变量「TEMPLATES」，保存对应数据（集合/元组）
TEMPLATES = [
    #: 该行执行对应逻辑（结合上下文理解）
    {
        #: 配置项「BACKEND」：字典/模型的该键设置为对应值
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        #: 配置项「DIRS」：字典/模型的该键设置为对应值
        'DIRS': [BASE_DIR / 'templates'],  # 项目级模板目录
        #: 配置项「APP_DIRS」：字典/模型的该键设置为对应值
        'APP_DIRS': True,                  # 自动在各 app 的 templates/ 下查找模板
        #: 配置项「OPTIONS」：字典/模型的该键设置为对应值
        'OPTIONS': {
            # 上下文处理器：向每个模板上下文中注入的额外变量
            #: 配置项「context_processors」：字典/模型的该键设置为对应值
            'context_processors': [
                #: 该行执行对应逻辑（结合上下文理解）
                'django.template.context_processors.debug',
                #: 该行执行对应逻辑（结合上下文理解）
                'django.template.context_processors.request',       # 注入 request 对象
                #: 该行执行对应逻辑（结合上下文理解）
                'django.contrib.auth.context_processors.auth',      # 注入 user / perm
                #: 该行执行对应逻辑（结合上下文理解）
                'django.contrib.messages.context_processors.messages',
                #: 该行执行对应逻辑（结合上下文理解）
                'django.template.context_processors.media',         # 注入 MEDIA_URL
                #: 该行执行对应逻辑（结合上下文理解）
                'blog.context_processors.site_nav',                # 自定义：注入导航数据
                #: 该行执行对应逻辑（结合上下文理解）
                'blog.context_processors.friendly_links',          # 自定义：注入友情链接列表
                #: 该行执行对应逻辑（结合上下文理解）
                'blog.context_processors.site_footer_stats',       # 自定义：注入页脚全站统计
                #: 该行执行对应逻辑（结合上下文理解）
                'blog.context_processors.site_notice',             # 62. 注入最新网站公告
                #: 该行执行对应逻辑（结合上下文理解）
                'blog.context_processors.lazy_public_cache',        # 第4轮 A1: 首个请求一次性懒加载预热公共缓存
                #: 该行执行对应逻辑（结合上下文理解）
                'blog.context_processors.sidebar_stats',            # 第4轮 A4: 侧边栏统计(缓存300s)
                #: 该行执行对应逻辑（结合上下文理解）
                'blog.context_processors.user_preferences',          # 第5轮: 用户偏好
                #: 该行执行对应逻辑（结合上下文理解）
                'blog.context_processors.unread_notification_count', # 第5轮: 未读通知数
                #: 该行执行对应逻辑（结合上下文理解）
                'blog.context_processors.build_token',              # bug20/21: 注入构建版本号
                #: 该行执行对应逻辑（结合上下文理解）
                'blog.context_processors.site_info_ctx',           # 工单15: 注入站点信息(网站名/Logo/介绍/页脚文案)
                #: 该行执行对应逻辑（结合上下文理解）
                'blog.context_processors.site_messages_ctx',       # Bug9: 注入全站文案命名空间 MSG / SITE_MSG_JS
                #: 该行执行对应逻辑（结合上下文理解）
                'blog.middleware.mascot.waifu_enabled',             # Bug9: 注入看板娘开关 waifu_enabled
            #: 该行执行对应逻辑（结合上下文理解）
            ],
            # 全局可用的自定义标签库：`libraries` 让模板**无需 {% load %}** 就能用这些过滤器。
            # 为什么要全局：文案注册表里的文案大量带占位符，模板侧要写成
            #   {{ MSG.a11y.notification_unread|format:count }}
            # 若要求每个模板都先 {% load blog_extras %}，几十个模板逐一补 load 既啰嗦又易漏
            # （漏了就是 TemplateSyntaxError → 整页 500，实测踩过）。注册为内置最稳妥。
            #: 配置项「libraries」：字典/模型的该键设置为对应值
            'libraries': {
                #: 配置项「blog_extras」：字典/模型的该键设置为对应值
                'blog_extras': 'blog.templatetags.blog_extras',
            #: 该行执行对应逻辑（结合上下文理解）
            },
        #: 该行执行对应逻辑（结合上下文理解）
        },
    #: 该行执行对应逻辑（结合上下文理解）
    },
#: 该行执行对应逻辑（结合上下文理解）
]

# WSGI / ASGI 应用入口，供对应服务器加载
#: 定义变量「WSGI_APPLICATION」，保存对应数据
WSGI_APPLICATION = 'DjangoBlog.wsgi.application'
#: 定义变量「ASGI_APPLICATION」，保存对应数据
ASGI_APPLICATION = 'DjangoBlog.asgi.application'

# MySQL：库 Blog_new，utf8mb4（对应 MySQL 的 utf8 超集，支持 emoji / 生僻字）
#: 定义变量「DATABASES」，保存对应数据
DATABASES = {
    #: 配置项「default」：字典/模型的该键设置为对应值
    'default': {
        #: 配置项「ENGINE」：字典/模型的该键设置为对应值
        'ENGINE': 'django.db.backends.mysql',
        # 以下连接参数均可通过环境变量覆盖，便于部署时切换环境
        #: 配置项「NAME」：字典/模型的该键设置为对应值
        'NAME': os.environ.get('DJANGO_MYSQL_DATABASE', 'Blog_new'),
        #: 配置项「USER」：字典/模型的该键设置为对应值
        'USER': os.environ.get('DJANGO_MYSQL_USER', 'root'),
        #: 配置项「PASSWORD」：字典/模型的该键设置为对应值
        'PASSWORD': os.environ.get('DJANGO_MYSQL_PASSWORD', '248617935'),
        #: 配置项「HOST」：字典/模型的该键设置为对应值
        'HOST': os.environ.get('DJANGO_MYSQL_HOST', '127.0.0.1'),
        #: 配置项「PORT」：字典/模型的该键设置为对应值
        'PORT': int(os.environ.get('DJANGO_MYSQL_PORT', 3306)),
        #: 配置项「OPTIONS」：字典/模型的该键设置为对应值
        'OPTIONS': {
            #: 配置项「charset」：字典/模型的该键设置为对应值
            'charset': 'utf8mb4',
            # 严格 SQL 模式，避免静默截断 / 非法插入
            #: 配置项「init_command」：字典/模型的该键设置为对应值
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        #: 该行执行对应逻辑（结合上下文理解）
        },
        # 数据库连接最长保持时间（秒），>0 表示启用长连接复用
        #: 配置项「CONN_MAX_AGE」：字典/模型的该键设置为对应值
        'CONN_MAX_AGE': 60,
    #: 该行执行对应逻辑（结合上下文理解）
    }
#: 该行执行对应逻辑（结合上下文理解）
}

# 自定义用户模型（必须在首次 migrate 前固定，否则后续无法更换）
#: 定义变量「AUTH_USER_MODEL」，保存对应数据
AUTH_USER_MODEL = 'blog.User'
# 未登录访问受限页面时跳转的登录地址
#: 定义变量「LOGIN_URL」，保存对应数据
LOGIN_URL = '/login/'
# 登录成功后默认跳转地址
#: 定义变量「LOGIN_REDIRECT_URL」，保存对应数据
LOGIN_REDIRECT_URL = '/'

# 密码校验器：注册 / 修改密码时按顺序校验强度
#: 定义变量「AUTH_PASSWORD_VALIDATORS」，保存对应数据（集合/元组）
AUTH_PASSWORD_VALIDATORS = [
    #: 该行执行对应逻辑（结合上下文理解）
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    #: 该行执行对应逻辑（结合上下文理解）
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     #: 配置项「OPTIONS」：字典/模型的该键设置为对应值
     'OPTIONS': {'min_length': 8}},  # 密码至少 8 位
    #: 该行执行对应逻辑（结合上下文理解）
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    #: 该行执行对应逻辑（结合上下文理解）
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
#: 该行执行对应逻辑（结合上下文理解）
]

# 国际化与时区
#: 定义变量「LANGUAGE_CODE」，保存对应数据
LANGUAGE_CODE = 'zh-hans'        # 界面语言：简体中文
#: 定义变量「TIME_ZONE」，保存对应数据
TIME_ZONE = 'Asia/Shanghai'     # 时区：中国标准时间
#: 定义变量「USE_I18N」，保存对应数据
USE_I18N = True                 # 启用国际化
#: 定义变量「USE_TZ」，保存对应数据
USE_TZ = False                  # 关闭时区感知，按本地时间存储（项目历史数据兼容）

# 静态文件
#: 定义变量「STATIC_URL」，保存对应数据
STATIC_URL = '/static/'
#: 定义变量「STATICFILES_DIRS」，保存对应数据（集合/元组）
STATICFILES_DIRS = [BASE_DIR / 'static']  # 开发阶段额外静态文件目录
# 生产部署 collectstatic 的目录（本地 runserver 不依赖它）
#: 定义变量「STATIC_ROOT」，保存对应数据
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise：生产环境（DEBUG=False）由 WhiteNoise 直接提供静态文件，
# 自动 gzip/brotli 压缩 + 长期缓存，无需额外配置 nginx
#: 定义变量「STATICFILES_STORAGE」，保存对应数据
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
# manifest 严格模式关闭：CKEditor/DRF 等第三方 CSS 可能引用缺失资源，不阻断 collectstatic 的 gzip 压缩流程
#: 定义变量「WHITENOISE_MANIFEST_STRICT」，保存对应数据
WHITENOISE_MANIFEST_STRICT = False
# 保留原始文件名（同时生成带 hash 的版本），便于模板直接引用
#: 定义变量「WHITENOISE_KEEP_ONLY_HASHED_FILES」，保存对应数据
WHITENOISE_KEEP_ONLY_HASHED_FILES = False

# 媒体上传（富文本图片）：用户上传文件的访问 URL 与磁盘根目录
#: 定义变量「MEDIA_URL」，保存对应数据
MEDIA_URL = '/media/'
#: 定义变量「MEDIA_ROOT」，保存对应数据
MEDIA_ROOT = BASE_DIR / 'media'

# 模型主键默认使用 BigAutoField（64 位自增整数）
#: 定义变量「DEFAULT_AUTO_FIELD」，保存对应数据（Django 模型字段，参与建表）
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 上传文件落盘后的权限掩码（owner 读写、组/其他只读）
#: 定义变量「FILE_UPLOAD_PERMISSIONS」，保存对应数据
FILE_UPLOAD_PERMISSIONS = 0o644
# 超过该大小的上传请求转存磁盘，而不是放在内存（25MB）
#: 定义变量「DATA_UPLOAD_MAX_MEMORY_SIZE」，保存对应数据
DATA_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024
# 单个上传文件超过该大小则写入磁盘而非内存（5MB）
#: 定义变量「FILE_UPLOAD_MAX_MEMORY_SIZE」，保存对应数据
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
# 富文本图片单张上限与扩展名白名单
#: 定义变量「UPLOAD_IMAGE_MAX_BYTES」，保存对应数据
UPLOAD_IMAGE_MAX_BYTES = 8 * 1024 * 1024
#: 定义变量「UPLOAD_IMAGE_EXTS」，保存对应数据（集合/元组）
UPLOAD_IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')

# 列表每页条数（视图层分页使用）
#: 定义变量「PAGE_SIZE」，保存对应数据
PAGE_SIZE = 10

# ============================ SEO 站点常量 ============================
# 站点名称：用于 title / 结构化数据 / Open Graph
#: 定义变量「SITE_NAME」，保存对应数据
SITE_NAME = '萌语博客'
# 站点默认描述：首页 / 无独立描述页面的 meta description
#: 定义变量「SITE_DESCRIPTION」，保存对应数据
SITE_DESCRIPTION = '萌语博客 · 一个粉紫蓝萌系的二次元小站，记录技术与生活的碎碎念喵~'
# 站点默认关键词：首页 meta keywords（逗号分隔）
#: 定义变量「SITE_KEYWORDS」，保存对应数据
SITE_KEYWORDS = '博客,技术,二次元'

# ============================ 缓存配置 ============================
# 使用本地内存缓存（LocMemCache），无需 Redis，适合开发 / 单机部署。
# 用于缓存侧边栏聚合数据、热门文章、页脚统计等只读公共数据，
# 在文章 / 评论变更时由视图主动 cache.delete() 失效。
#: 定义变量「CACHES」，保存对应数据
CACHES = {
    #: 配置项「default」：字典/模型的该键设置为对应值
    'default': {
        #: 配置项「BACKEND」：字典/模型的该键设置为对应值
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        #: 配置项「LOCATION」：字典/模型的该键设置为对应值
        'LOCATION': 'blog-cache',
        #: 配置项「TIMEOUT」：字典/模型的该键设置为对应值
        'TIMEOUT': 300,          # 默认 5 分钟过期
    #: 该行执行对应逻辑（结合上下文理解）
    }
#: 该行执行对应逻辑（结合上下文理解）
}

# Django REST framework 全局配置
#: 定义变量「REST_FRAMEWORK」，保存对应数据
REST_FRAMEWORK = {
    # 统一使用页码分页
    #: 配置项「DEFAULT_PAGINATION_CLASS」：字典/模型的该键设置为对应值
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    #: 配置项「PAGE_SIZE」：字典/模型的该键设置为对应值
    'PAGE_SIZE': 10,
    # 认证方式：浏览器会话 + 基础认证（供调试 / 接口客户端使用）
    #: 配置项「DEFAULT_AUTHENTICATION_CLASSES」：字典/模型的该键设置为对应值
    'DEFAULT_AUTHENTICATION_CLASSES': (
        #: 该行执行对应逻辑（结合上下文理解）
        'rest_framework.authentication.SessionAuthentication',
        #: 该行执行对应逻辑（结合上下文理解）
        'rest_framework.authentication.BasicAuthentication',
    #: 该行执行对应逻辑（结合上下文理解）
    ),
    # 渲染方式：JSON + 可浏览 API（调试页）
    #: 配置项「DEFAULT_RENDERER_CLASSES」：字典/模型的该键设置为对应值
    'DEFAULT_RENDERER_CLASSES': (
        #: 该行执行对应逻辑（结合上下文理解）
        'rest_framework.renderers.JSONRenderer',
        #: 该行执行对应逻辑（结合上下文理解）
        'rest_framework.renderers.BrowsableAPIRenderer',
    #: 该行执行对应逻辑（结合上下文理解）
    ),
    # 接口返回的日期时间统一格式
    #: 配置项「DATETIME_FORMAT」：字典/模型的该键设置为对应值
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    # 默认权限：匿名可读，登录后可写
    #: 配置项「DEFAULT_PERMISSION_CLASSES」：字典/模型的该键设置为对应值
    'DEFAULT_PERMISSION_CLASSES': (
        #: 该行执行对应逻辑（结合上下文理解）
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    #: 该行执行对应逻辑（结合上下文理解）
    ),
#: 该行执行对应逻辑（结合上下文理解）
}

# 会话 / CSRF Cookie 安全设置
#: 定义变量「SESSION_COOKIE_HTTPONLY」，保存对应数据
SESSION_COOKIE_HTTPONLY = True
#: 定义变量「CSRF_COOKIE_HTTPONLY」，保存对应数据
CSRF_COOKIE_HTTPONLY = False  # 模板表单 / 编辑器上传需要读取 CSRF
#: 定义变量「X_FRAME_OPTIONS」，保存对应数据
X_FRAME_OPTIONS = 'SAMEORIGIN'  # 仅允许同源页面 iframe 嵌入

# ============================ Celery 配置 ============================
# Broker 使用 Redis；如 Redis 未启动，Celery worker 无法接收任务，
# 但中间件会降级为同步保存，不影响网站正常运行。
#: 定义变量「CELERY_BROKER_URL」，保存对应数据
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
#: 定义变量「CELERY_RESULT_BACKEND」，保存对应数据
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')
#: 定义变量「CELERY_ACCEPT_CONTENT」，保存对应数据（集合/元组）
CELERY_ACCEPT_CONTENT = ['json']              # 只接受 json 序列化的任务
#: 定义变量「CELERY_TASK_SERIALIZER」，保存对应数据
CELERY_TASK_SERIALIZER = 'json'              # 任务参数序列化方式
#: 定义变量「CELERY_RESULT_SERIALIZER」，保存对应数据
CELERY_RESULT_SERIALIZER = 'json'            # 任务结果序列化方式
#: 定义变量「CELERY_TIMEZONE」，保存对应数据
CELERY_TIMEZONE = 'Asia/Shanghai'            # 任务调度时区
#: 定义变量「CELERY_TASK_ALWAYS_EAGER」，保存对应数据
CELERY_TASK_ALWAYS_EAGER = False  # 设为 True 可同步执行任务（调试用）
# Broker 连接/发布超时收紧：访问日志是「尽力投递」的廉价数据，broker 不可达时
# 必须立刻失败（进入 Redis 兜底队列），绝不能占用请求线程等待重试。
#: 定义变量「CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP」，保存对应数据
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True   # worker 启动期允许重连（不影响请求线程）
#: 定义变量「CELERY_TASK_PUBLISH_RETRY」，保存对应数据
CELERY_TASK_PUBLISH_RETRY = False                  # 发布任务不做重试，快速失败交给兜底队列
#: 定义变量「CELERY_BROKER_TRANSPORT_OPTIONS」，保存对应数据
CELERY_BROKER_TRANSPORT_OPTIONS = {
    #: 配置项「socket_connect_timeout」：字典/模型的该键设置为对应值
    'socket_connect_timeout': 0.4,   # 秒：连接 broker 超时
    #: 配置项「socket_timeout」：字典/模型的该键设置为对应值
    'socket_timeout': 0.4,           # 秒：读写 broker 超时
    #: 配置项「retry_on_timeout」：字典/模型的该键设置为对应值
    'retry_on_timeout': False,       # 超时不重试
    #: 配置项「max_retries」：字典/模型的该键设置为对应值
    'max_retries': 0,                # 发布不做额外重试
#: 该行执行对应逻辑（结合上下文理解）
}
# 访问日志整体开关（全局永久强制模块，默认开启；仅在极端压测时允许临时关闭）
#: 定义变量「ACCESS_LOG_ENABLED」，保存对应数据
ACCESS_LOG_ENABLED = os.environ.get('ACCESS_LOG_ENABLED', '1') == '1'

# ============================ 访问日志投递通道（全局永久强制模块） ============================
# 三层降级策略参数（实现见 blog/middleware/access_log.py 与 blog/services/access_log_service.py）：
#   层1 Celery 异步 → 层2 Redis 兜底队列 → 层3 极端同步入库
# 以下均为短超时设置，确保中间件永不成为请求链路的阻塞点。
#: 定义变量「ACCESS_LOG_FALLBACK_KEY」，保存对应数据
ACCESS_LOG_FALLBACK_KEY = 'acgblog:access_log:fallback'   # 兜底队列键名
# 兜底队列专用 Redis 地址：**必须独立于 Celery broker 配置**。
# 若与 broker 复用同一地址，broker 地址被改动 / 故障时会连带把兜底队列写坏；
# 生产环境建议指向独立的 Redis 实例或不同 db（如 redis://127.0.0.1:6379/1）。
#: 定义变量「ACCESS_LOG_FALLBACK_REDIS_URL」，保存对应数据
ACCESS_LOG_FALLBACK_REDIS_URL = os.environ.get(
    #: 该行执行对应逻辑（结合上下文理解）
    'ACCESS_LOG_FALLBACK_REDIS_URL', 'redis://127.0.0.1:6379/0')
#: 定义变量「ACCESS_LOG_REDIS_TIMEOUT」，保存对应数据
ACCESS_LOG_REDIS_TIMEOUT = 0.35        # 秒：单次 Redis 操作的 socket 超时
#: 定义变量「ACCESS_LOG_REDIS_COOLDOWN」，保存对应数据
ACCESS_LOG_REDIS_COOLDOWN = 20.0       # 秒：Redis 失败后的熔断窗口（避免持续等待）
#: 定义变量「ACCESS_LOG_FALLBACK_MAX_LEN」，保存对应数据
ACCESS_LOG_FALLBACK_MAX_LEN = 20000    # 兜底队列长度上限（LTRIM 保留最新 N 条）
#: 定义变量「ACCESS_LOG_DRAIN_BATCH」，保存对应数据
ACCESS_LOG_DRAIN_BATCH = 500           # 批量消费单批条数
# Broker 熔断窗口（秒）：Celery 投递失败后，这段时间内直接走 Redis 兜底队列，
# 不再尝试连接 broker。原因：broker 宕机时 kombu 的默认连接/重试策略会阻塞数秒
# （实测单请求 6.2s），必须先熔断才能保证「访问日志绝不拖慢网站响应」。
#: 定义变量「ACCESS_LOG_BROKER_COOLDOWN」，保存对应数据
ACCESS_LOG_BROKER_COOLDOWN = 15.0

# Celery Beat 定时任务调度
#: 定义变量「CELERY_BEAT_SCHEDULE」，保存对应数据
CELERY_BEAT_SCHEDULE = {
    # 每天凌晨 3:00 清理 90 天前的访问日志
    #: 该行执行对应逻辑（结合上下文理解）
    'clean-old-logs-daily': {
        #: 配置项「task」：字典/模型的该键设置为对应值
        'task': 'blog.tasks.clean_old_logs',
        #: 配置项「schedule」：字典/模型的该键设置为对应值
        'schedule': crontab(hour=3, minute=0),
        #: 配置项「args」：字典/模型的该键设置为对应值
        'args': (90,),
    #: 该行执行对应逻辑（结合上下文理解）
    },
    # 每小时执行一次文章阅读量统计
    #: 该行执行对应逻辑（结合上下文理解）
    'update-article-views-hourly': {
        #: 配置项「task」：字典/模型的该键设置为对应值
        'task': 'blog.tasks.update_article_views',
        #: 配置项「schedule」：字典/模型的该键设置为对应值
        'schedule': crontab(minute=0),  # 每小时整点
    #: 该行执行对应逻辑（结合上下文理解）
    },
    # 56. 每分钟检查一次定时发布：把到点的草稿自动转为已发布
    #: 该行执行对应逻辑（结合上下文理解）
    'check-scheduled-articles-every-minute': {
        #: 配置项「task」：字典/模型的该键设置为对应值
        'task': 'blog.tasks.check_scheduled_articles',
        #: 配置项「schedule」：字典/模型的该键设置为对应值
        'schedule': crontab(minute='*'),  # 每分钟
    #: 该行执行对应逻辑（结合上下文理解）
    },
    # 第3轮迭代#4: 每 15 分钟批量合并评论通知摘要邮件（每作者一封）
    #: 该行执行对应逻辑（结合上下文理解）
    'send-comment-digest-every-15min': {
        #: 配置项「task」：字典/模型的该键设置为对应值
        'task': 'blog.tasks.send_comment_digest',
        #: 配置项「schedule」：字典/模型的该键设置为对应值
        'schedule': crontab(minute='*/15'),
    #: 该行执行对应逻辑（结合上下文理解）
    },
    # 第3轮迭代#4: 每 5 分钟把阅读量缓冲批量落库
    #: 该行执行对应逻辑（结合上下文理解）
    'flush-buffered-views-every-5min': {
        #: 配置项「task」：字典/模型的该键设置为对应值
        'task': 'blog.tasks.flush_buffered_views',
        #: 配置项「schedule」：字典/模型的该键设置为对应值
        'schedule': crontab(minute='*/5'),
    #: 该行执行对应逻辑（结合上下文理解）
    },
    # 访问日志兜底队列自动补齐：Broker 故障期间的积压日志，恢复后 5 分钟内自动入库
    #: 该行执行对应逻辑（结合上下文理解）
    'flush-access-log-queue-every-5min': {
        #: 配置项「task」：字典/模型的该键设置为对应值
        'task': 'blog.tasks.flush_access_log_queue',
        #: 配置项「schedule」：字典/模型的该键设置为对应值
        'schedule': crontab(minute='*/5'),
    #: 该行执行对应逻辑（结合上下文理解）
    },
#: 该行执行对应逻辑（结合上下文理解）
}

# ============================ 邮件配置（68. 评论通知） ============================
# 开发环境使用 console 后端：邮件只打印到控制台，不真正发送，无需 SMTP 配置。
# 生产环境改为 django.core.mail.backends.smtp.EmailBackend 并配置 SMTP_* 即可。
#: 定义变量「EMAIL_BACKEND」，保存对应数据
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# 发件人默认地址（任务中也会显式指定）
#: 定义变量「DEFAULT_FROM_EMAIL」，保存对应数据
DEFAULT_FROM_EMAIL = '萌语博客 <noreply@mengyu.blog>'
#: 定义变量「SERVER_EMAIL」，保存对应数据
SERVER_EMAIL = '萌语博客 <noreply@mengyu.blog>'

# ============================ 日志配置 ============================
# DEBUG 模式下把每条 SQL 打到控制台，便于核对查询数量；
# 慢查询（>500ms）由 blog.middleware.SlowQueryFilter 过滤后单独标记 WARNING。
#: 定义变量「LOGGING」，保存对应数据
LOGGING = {
    #: 配置项「version」：字典/模型的该键设置为对应值
    'version': 1,
    #: 配置项「disable_existing_loggers」：字典/模型的该键设置为对应值
    'disable_existing_loggers': False,
    #: 配置项「filters」：字典/模型的该键设置为对应值
    'filters': {
        #: 配置项「slow_query」：字典/模型的该键设置为对应值
        'slow_query': {
            #: 该行执行对应逻辑（结合上下文理解）
            '()': 'blog.middleware.SlowQueryFilter',
        #: 该行执行对应逻辑（结合上下文理解）
        },
        # 硬性指标：消除 requests 版本告警（RequestsDependencyWarning）
        #: 配置项「requests_dep_warning」：字典/模型的该键设置为对应值
        'requests_dep_warning': {
            #: 该行执行对应逻辑（结合上下文理解）
            '()': 'blog.utils.deprecation_filters.RequestsDependencyWarningFilter',
        #: 该行执行对应逻辑（结合上下文理解）
        },
    #: 该行执行对应逻辑（结合上下文理解）
    },
    #: 配置项「handlers」：字典/模型的该键设置为对应值
    'handlers': {
        #: 配置项「console」：字典/模型的该键设置为对应值
        'console': {'class': 'logging.StreamHandler'},
    #: 该行执行对应逻辑（结合上下文理解）
    },
    #: 配置项「loggers」：字典/模型的该键设置为对应值
    'loggers': {
        #: 该行执行对应逻辑（结合上下文理解）
        'django.db.backends': {
            #: 配置项「handlers」：字典/模型的该键设置为对应值
            'handlers': ['console'],
            #: 配置项「level」：字典/模型的该键设置为对应值
            'level': 'WARNING',  # 第4轮 A2: 始终 WARNING，不再随 DEBUG 打印每条 SQL
            #: 配置项「propagate」：字典/模型的该键设置为对应值
            'propagate': False,
        #: 该行执行对应逻辑（结合上下文理解）
        },
        #: 该行执行对应逻辑（结合上下文理解）
        'django.db.backends.slow': {
            #: 配置项「handlers」：字典/模型的该键设置为对应值
            'handlers': ['console'],
            #: 配置项「level」：字典/模型的该键设置为对应值
            'level': 'WARNING',
            #: 配置项「filters」：字典/模型的该键设置为对应值
            'filters': ['slow_query'],
            #: 配置项「propagate」：字典/模型的该键设置为对应值
            'propagate': False,
        #: 该行执行对应逻辑（结合上下文理解）
        },
        # requests 自身的 urllib3/chardet 依赖版本告警在此统一静默（已锁版本消除告警源）
        #: 配置项「requests」：字典/模型的该键设置为对应值
        'requests': {
            #: 配置项「handlers」：字典/模型的该键设置为对应值
            'handlers': ['console'],
            #: 配置项「level」：字典/模型的该键设置为对应值
            'level': 'WARNING',
            #: 配置项「filters」：字典/模型的该键设置为对应值
            'filters': ['requests_dep_warning'],
            #: 配置项「propagate」：字典/模型的该键设置为对应值
            'propagate': False,
        #: 该行执行对应逻辑（结合上下文理解）
        },
        #: 配置项「urllib3」：字典/模型的该键设置为对应值
        'urllib3': {
            #: 配置项「handlers」：字典/模型的该键设置为对应值
            'handlers': ['console'],
            #: 配置项「level」：字典/模型的该键设置为对应值
            'level': 'WARNING',
            #: 配置项「filters」：字典/模型的该键设置为对应值
            'filters': ['requests_dep_warning'],
            #: 配置项「propagate」：字典/模型的该键设置为对应值
            'propagate': False,
        #: 该行执行对应逻辑（结合上下文理解）
        },
    #: 该行执行对应逻辑（结合上下文理解）
    },
#: 该行执行对应逻辑（结合上下文理解）
}

# ---- 硬性指标：全局把 RequestsDependencyWarning 降级为「已处理」 ----
# requests 顶层会通过 warnings.warn 输出依赖版本告警；requirements.txt 已锁定
# chardet / urllib3 兼容版本消除告警源，这里再做一层兜底，保证任何环境
# （例如他人机器上装了不同次要版本）都不会把该告警打进控制台 / 验收输出。
#: 定义变量「REQUESTS_DEPENDENCY_WARNING_FILTER」，保存对应数据
REQUESTS_DEPENDENCY_WARNING_FILTER = 'blog.utils.deprecation_filters.install_warning_filters'


# ============================ 第2轮迭代#221-#230: 配置优化补充 ============================

# 第2轮迭代#221: 环境变量配置——按 DJANGO_ENV 区分开发/生产
#: 定义变量「ENVIRONMENT」，保存对应数据
ENVIRONMENT = os.environ.get('DJANGO_ENV', 'development')

# 第2轮迭代#222: 数据库配置优化说明——CONN_MAX_AGE=60 已启用长连接复用，utf8mb4 已配
# 第2轮迭代#223: 缓存配置优化——分级 TTL 常量，便于各视图统一引用
#: 定义变量「CACHE_TTL_SHORT」，保存对应数据
CACHE_TTL_SHORT = 60      # 秒：高频易变数据
#: 定义变量「CACHE_TTL_MEDIUM」，保存对应数据
CACHE_TTL_MEDIUM = 300    # 秒：侧边栏等公共数据
#: 定义变量「CACHE_TTL_LONG」，保存对应数据
CACHE_TTL_LONG = 3600     # 秒：页脚统计等低频数据

# 第2轮迭代#224: 静态文件配置说明——STATIC_URL/STATIC_ROOT/WhiteNoise 已配
# 第2轮迭代#225: 媒体文件配置说明——MEDIA_URL/MEDIA_ROOT 已配，DEBUG 下由 static() 服务

# 第2轮迭代#226: 安全配置补充——浏览器 XSS 过滤与 MIME 嗅探防护
#: 定义变量「SECURE_BROWSER_XSS_FILTER」，保存对应数据
SECURE_BROWSER_XSS_FILTER = True
#: 定义变量「SECURE_CONTENT_TYPE_NOSNIFF」，保存对应数据
SECURE_CONTENT_TYPE_NOSNIFF = True

# 第2轮迭代#227: 日志配置说明——LOGGING 已配慢查询过滤与 SQL 日志级别
# 第2轮迭代#228: 邮件配置说明——开发用 console backend，生产改 smtp 即可
# 第2轮迭代#229: Celery 配置说明——broker/beat 定时任务已配
# 第2轮迭代#230: 国际化配置说明——zh-hans / Asia/Shanghai / USE_TZ=False 已配


# ============================================================================
# 功能开关与运行参数（重构收拢：原散落在各业务文件，现统一在此维护）
# ----------------------------------------------------------------------------
# 约定：每个常量都在注释里注明「引入文件」与「含义」，便于按图索骥调整；
#       仅收拢「可调配置 / 阈值 / 开关 / 默认值」，安全白名单、正则、缓存键
#       模板等业务与实现逻辑仍保留在各自模块，不做机械搬迁。
# ============================================================================

# ---- 全站文案覆盖（引入文件：blog/services/site_messages.py）----
# 文案覆盖项存于 SiteMessage 表；因默认缓存为进程内 LocMemCache、无法跨进程
# 传播失效，模块用「周期性查 MAX(updated_at)」作为跨进程变更信号。本项即该
# 轮询的节流秒数：默认 1.0，做到「保存后刷新立即可见」；设为 0 则每次请求都
# 查库（适合开发 / 极低频站点），调大可进一步降低数据库压力。
#: 定义变量「SITE_MSG_DB_POLL_SECONDS」，保存对应数据
SITE_MSG_DB_POLL_SECONDS = 1.0

# ---- 第 5 轮功能开关（引入文件：blog/views/features.py）----
# 功能特性（Round5Feature）的「settings 层覆盖表」：键为 feature_id、值为
# True/False，优先级高于功能注册默认值。默认为空 {} 表示全部沿用注册默认；
# 在此显式置 False 可关闭某功能，置 True 可强制开启（运行时生效，重启还原）。
#: 定义变量「ROUND5_FEATURES」，保存对应数据
ROUND5_FEATURES = {}

# ---- 定时投稿 Web 兜底扫描（引入文件：blog/services/scheduled_publishing.py）----
# 未启动 Celery beat 时，由 Web 请求侧兜底扫描到点定时文章。本项为同一进程
# 内两次扫描的最小间隔（秒），配合缓存锁避免高并发下每个请求都扫库。
#: 定义变量「SCHEDULED_SWEEP_INTERVAL」，保存对应数据
SCHEDULED_SWEEP_INTERVAL = 30
# 单轮扫描最多流转的文章数：防止长时间停机后定时文章堆积、一次性处理过多。
#: 定义变量「SCHEDULED_MAX_PER_ROUND」，保存对应数据
SCHEDULED_MAX_PER_ROUND = 200

# ---- 详情页缓存（引入文件：blog/utils/cache_keys.py）----
# 缓存版本号文件缺失 / 内容为空时的兜底版本前缀（与文件驱动版本号同模式）。
#: 定义变量「CACHE_VERSION_FALLBACK」，保存对应数据
CACHE_VERSION_FALLBACK = 'v1'
# 说明：详情页片段 TTL 直接复用上方分级 TTL，单一来源、不再另设——
#   · 正文 / 评论树 / 相关文章等共享片段 → CACHE_TTL_MEDIUM（300s）
#   · 「不存在」墓碑（防恶意 id 穿透）   → CACHE_TTL_SHORT（60s）

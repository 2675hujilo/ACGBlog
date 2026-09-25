"""
DjangoBlog 项目配置（萌系二次元博客版）。

- 数据库：MySQL，库名 Blog_new，字符集 utf8mb4；
- 全站统一 CKEditor 富文本（本地静态资源）；
- Celery + Redis 异步任务队列（访问日志异步写入、定时清理）；
- 自定义 AccessLogMiddleware 全路由访问日志；
- Windows 本地开发直接 runserver，Celery worker 用 --pool=solo 启动。
"""
import os
from pathlib import Path

# Celery 定时任务调度（crontab 表达式用于 CELERY_BEAT_SCHEDULE）
from celery.schedules import crontab

# 项目根目录（manage.py 所在目录），后续路径均基于它拼接
BASE_DIR = Path(__file__).resolve().parent.parent

# 密钥：优先从环境变量读取；本地开发兜底使用内置值（生产环境必须通过环境变量覆盖）
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-m=uppkb@sj^&ohvxi&_b8t_po5_jz3@nxc!dyq7kmmj8=tu710',  # 仅本地开发兜底
)
# 调试模式：默认开启（'1'），生产环境务必设为 '0'，否则会泄露敏感信息
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'
# 允许访问的主机名；'*' 表示开发阶段放行所有域名，生产应改为具体域名
ALLOWED_HOSTS = ['*']

# 已安装的应用：含 Django 内置应用、DRF 以及本项目的 blog 应用
INSTALLED_APPS = [
    'django.contrib.admin',            # 后台管理站点
    'django.contrib.auth',             # 认证 / 授权框架
    'django.contrib.contenttypes',     # 内容类型框架（与权限系统配合）
    'django.contrib.sessions',         # 会话支持
    'django.contrib.messages',         # 一次性消息提示
    'django.contrib.staticfiles',      # 静态文件管理
    'rest_framework',                  # Django REST framework
    'blog.apps.BlogConfig',            # 本项目博客应用配置
]

# 中间件列表：按顺序自上而下处理请求、自下而上处理响应
# AccessLogMiddleware 放在 Security 之后、Session 之前：
# - process_request 阶段只记录开始时间（此时 session/user 尚未就绪，不可访问）；
# - process_response / process_exception 阶段所有内层中间件已执行完毕，
#   session、user 均可用，可捕获完整请求生命周期（含 500 异常与 404 响应）。
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',          # 各类安全相关响应头
    'whitenoise.middleware.WhiteNoiseMiddleware',              # 生产环境静态文件压缩与缓存服务
    'blog.middleware.AccessLogMiddleware',                     # 自定义：记录全路由访问日志
    'django.contrib.sessions.middleware.SessionMiddleware',    # 会话解析
    'django.middleware.common.CommonMiddleware',               # 通用处理（URL 规范化等）
    'django.middleware.csrf.CsrfViewMiddleware',               # CSRF 防护
    'django.contrib.auth.middleware.AuthenticationMiddleware', # 绑定 request.user
    'django.contrib.messages.middleware.MessageMiddleware',    # 消息框架
    'django.middleware.clickjacking.XFrameOptionsMiddleware', # 防止点击劫持
    'blog.middleware.OnlineStatusMiddleware',                    # 第5轮: 在线状态更新
    'blog.middleware.SiteInfoMiddleware',                        # 工单15: 站点信息单例注入
    'blog.middleware.CuteErrorPagesMiddleware',                 # Bug27: DEBUG下也显示萌系错误页
]

# 根路由模块，即 URL 分发的入口
ROOT_URLCONF = 'DjangoBlog.urls'

# 模板引擎配置
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # 项目级模板目录
        'APP_DIRS': True,                  # 自动在各 app 的 templates/ 下查找模板
        'OPTIONS': {
            # 上下文处理器：向每个模板上下文中注入的额外变量
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',       # 注入 request 对象
                'django.contrib.auth.context_processors.auth',      # 注入 user / perm
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',         # 注入 MEDIA_URL
                'blog.context_processors.site_nav',                # 自定义：注入导航数据
                'blog.context_processors.friendly_links',          # 自定义：注入友情链接列表
                'blog.context_processors.site_footer_stats',       # 自定义：注入页脚全站统计
                'blog.context_processors.site_notice',             # 62. 注入最新网站公告
                'blog.context_processors.lazy_public_cache',        # 第4轮 A1: 首个请求一次性懒加载预热公共缓存
                'blog.context_processors.sidebar_stats',            # 第4轮 A4: 侧边栏统计(缓存300s)
                'blog.context_processors.user_preferences',          # 第5轮: 用户偏好
                'blog.context_processors.unread_notification_count', # 第5轮: 未读通知数
                'blog.context_processors.build_token',              # bug20/21: 注入构建版本号
                'blog.context_processors.site_info_ctx',           # 工单15: 注入站点信息(网站名/Logo/介绍/页脚文案)
            ],
        },
    },
]

# WSGI / ASGI 应用入口，供对应服务器加载
WSGI_APPLICATION = 'DjangoBlog.wsgi.application'
ASGI_APPLICATION = 'DjangoBlog.asgi.application'

# MySQL：库 Blog_new，utf8mb4（对应 MySQL 的 utf8 超集，支持 emoji / 生僻字）
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        # 以下连接参数均可通过环境变量覆盖，便于部署时切换环境
        'NAME': os.environ.get('DJANGO_MYSQL_DATABASE', 'Blog_new'),
        'USER': os.environ.get('DJANGO_MYSQL_USER', 'root'),
        'PASSWORD': os.environ.get('DJANGO_MYSQL_PASSWORD', '248617935'),
        'HOST': os.environ.get('DJANGO_MYSQL_HOST', '127.0.0.1'),
        'PORT': int(os.environ.get('DJANGO_MYSQL_PORT', 3306)),
        'OPTIONS': {
            'charset': 'utf8mb4',
            # 严格 SQL 模式，避免静默截断 / 非法插入
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        # 数据库连接最长保持时间（秒），>0 表示启用长连接复用
        'CONN_MAX_AGE': 60,
    }
}

# 自定义用户模型（必须在首次 migrate 前固定，否则后续无法更换）
AUTH_USER_MODEL = 'blog.User'
# 未登录访问受限页面时跳转的登录地址
LOGIN_URL = '/login/'
# 登录成功后默认跳转地址
LOGIN_REDIRECT_URL = '/'

# 密码校验器：注册 / 修改密码时按顺序校验强度
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},  # 密码至少 8 位
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# 国际化与时区
LANGUAGE_CODE = 'zh-hans'        # 界面语言：简体中文
TIME_ZONE = 'Asia/Shanghai'     # 时区：中国标准时间
USE_I18N = True                 # 启用国际化
USE_TZ = False                  # 关闭时区感知，按本地时间存储（项目历史数据兼容）

# 静态文件
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']  # 开发阶段额外静态文件目录
# 生产部署 collectstatic 的目录（本地 runserver 不依赖它）
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise：生产环境（DEBUG=False）由 WhiteNoise 直接提供静态文件，
# 自动 gzip/brotli 压缩 + 长期缓存，无需额外配置 nginx
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
# manifest 严格模式关闭：CKEditor/DRF 等第三方 CSS 可能引用缺失资源，不阻断 collectstatic 的 gzip 压缩流程
WHITENOISE_MANIFEST_STRICT = False
# 保留原始文件名（同时生成带 hash 的版本），便于模板直接引用
WHITENOISE_KEEP_ONLY_HASHED_FILES = False

# 媒体上传（富文本图片）：用户上传文件的访问 URL 与磁盘根目录
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# 模型主键默认使用 BigAutoField（64 位自增整数）
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 上传文件落盘后的权限掩码（owner 读写、组/其他只读）
FILE_UPLOAD_PERMISSIONS = 0o644
# 超过该大小的上传请求转存磁盘，而不是放在内存（25MB）
DATA_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024
# 单个上传文件超过该大小则写入磁盘而非内存（5MB）
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
# 富文本图片单张上限与扩展名白名单
UPLOAD_IMAGE_MAX_BYTES = 8 * 1024 * 1024
UPLOAD_IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')

# 列表每页条数（视图层分页使用）
PAGE_SIZE = 10

# ============================ SEO 站点常量 ============================
# 站点名称：用于 title / 结构化数据 / Open Graph
SITE_NAME = '萌语博客'
# 站点默认描述：首页 / 无独立描述页面的 meta description
SITE_DESCRIPTION = '萌语博客 · 一个粉紫蓝萌系的二次元小站，记录技术与生活的碎碎念喵~'
# 站点默认关键词：首页 meta keywords（逗号分隔）
SITE_KEYWORDS = '博客,技术,二次元'

# ============================ 缓存配置 ============================
# 使用本地内存缓存（LocMemCache），无需 Redis，适合开发 / 单机部署。
# 用于缓存侧边栏聚合数据、热门文章、页脚统计等只读公共数据，
# 在文章 / 评论变更时由视图主动 cache.delete() 失效。
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'blog-cache',
        'TIMEOUT': 300,          # 默认 5 分钟过期
    }
}

# Django REST framework 全局配置
REST_FRAMEWORK = {
    # 统一使用页码分页
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    # 认证方式：浏览器会话 + 基础认证（供调试 / 接口客户端使用）
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ),
    # 渲染方式：JSON + 可浏览 API（调试页）
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    # 接口返回的日期时间统一格式
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    # 默认权限：匿名可读，登录后可写
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
}

# 会话 / CSRF Cookie 安全设置
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # 模板表单 / 编辑器上传需要读取 CSRF
X_FRAME_OPTIONS = 'SAMEORIGIN'  # 仅允许同源页面 iframe 嵌入

# ============================ Celery 配置 ============================
# Broker 使用 Redis；如 Redis 未启动，Celery worker 无法接收任务，
# 但中间件会降级为同步保存，不影响网站正常运行。
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')
CELERY_ACCEPT_CONTENT = ['json']              # 只接受 json 序列化的任务
CELERY_TASK_SERIALIZER = 'json'              # 任务参数序列化方式
CELERY_RESULT_SERIALIZER = 'json'            # 任务结果序列化方式
CELERY_TIMEZONE = 'Asia/Shanghai'            # 任务调度时区
CELERY_TASK_ALWAYS_EAGER = False  # 设为 True 可同步执行任务（调试用）

# Celery Beat 定时任务调度
CELERY_BEAT_SCHEDULE = {
    # 每天凌晨 3:00 清理 90 天前的访问日志
    'clean-old-logs-daily': {
        'task': 'blog.tasks.clean_old_logs',
        'schedule': crontab(hour=3, minute=0),
        'args': (90,),
    },
    # 每小时执行一次文章阅读量统计
    'update-article-views-hourly': {
        'task': 'blog.tasks.update_article_views',
        'schedule': crontab(minute=0),  # 每小时整点
    },
    # 56. 每分钟检查一次定时发布：把到点的草稿自动转为已发布
    'check-scheduled-articles-every-minute': {
        'task': 'blog.tasks.check_scheduled_articles',
        'schedule': crontab(minute='*'),  # 每分钟
    },
    # 第3轮迭代#4: 每 15 分钟批量合并评论通知摘要邮件（每作者一封）
    'send-comment-digest-every-15min': {
        'task': 'blog.tasks.send_comment_digest',
        'schedule': crontab(minute='*/15'),
    },
    # 第3轮迭代#4: 每 5 分钟把阅读量缓冲批量落库
    'flush-buffered-views-every-5min': {
        'task': 'blog.tasks.flush_buffered_views',
        'schedule': crontab(minute='*/5'),
    },
}

# ============================ 邮件配置（68. 评论通知） ============================
# 开发环境使用 console 后端：邮件只打印到控制台，不真正发送，无需 SMTP 配置。
# 生产环境改为 django.core.mail.backends.smtp.EmailBackend 并配置 SMTP_* 即可。
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# 发件人默认地址（任务中也会显式指定）
DEFAULT_FROM_EMAIL = '萌语博客 <noreply@mengyu.blog>'
SERVER_EMAIL = '萌语博客 <noreply@mengyu.blog>'

# ============================ 日志配置 ============================
# DEBUG 模式下把每条 SQL 打到控制台，便于核对查询数量；
# 慢查询（>500ms）由 blog.middleware.SlowQueryFilter 过滤后单独标记 WARNING。
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'slow_query': {
            '()': 'blog.middleware.SlowQueryFilter',
        },
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',  # 第4轮 A2: 始终 WARNING，不再随 DEBUG 打印每条 SQL
            'propagate': False,
        },
        'django.db.backends.slow': {
            'handlers': ['console'],
            'level': 'WARNING',
            'filters': ['slow_query'],
            'propagate': False,
        },
    },
}


# ============================ 第2轮迭代#221-#230: 配置优化补充 ============================

# 第2轮迭代#221: 环境变量配置——按 DJANGO_ENV 区分开发/生产
ENVIRONMENT = os.environ.get('DJANGO_ENV', 'development')

# 第2轮迭代#222: 数据库配置优化说明——CONN_MAX_AGE=60 已启用长连接复用，utf8mb4 已配
# 第2轮迭代#223: 缓存配置优化——分级 TTL 常量，便于各视图统一引用
CACHE_TTL_SHORT = 60      # 秒：高频易变数据
CACHE_TTL_MEDIUM = 300    # 秒：侧边栏等公共数据
CACHE_TTL_LONG = 3600     # 秒：页脚统计等低频数据

# 第2轮迭代#224: 静态文件配置说明——STATIC_URL/STATIC_ROOT/WhiteNoise 已配
# 第2轮迭代#225: 媒体文件配置说明——MEDIA_URL/MEDIA_ROOT 已配，DEBUG 下由 static() 服务

# 第2轮迭代#226: 安全配置补充——浏览器 XSS 过滤与 MIME 嗅探防护
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# 第2轮迭代#227: 日志配置说明——LOGGING 已配慢查询过滤与 SQL 日志级别
# 第2轮迭代#228: 邮件配置说明——开发用 console backend，生产改 smtp 即可
# 第2轮迭代#229: Celery 配置说明——broker/beat 定时任务已配
# 第2轮迭代#230: 国际化配置说明——zh-hans / Asia/Shanghai / USE_TZ=False 已配

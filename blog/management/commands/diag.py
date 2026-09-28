"""综合诊断命令：python manage.py diag [选项]

合并了原 10 个 check_* 与 6 个 list_* 管理命令的全部检查项，
通过命令行 flag 选择要执行的诊断块；默认无任何 flag 时给出帮助并提示使用 --all。

用法示例：
    python manage.py diag --all                # 跑全部诊断
    python manage.py diag --db --urls          # 只查数据库与路由
    python manage.py diag --models --views     # 只列模型与视图
    python manage.py diag --security           # 只看安全相关配置项（与独立的 security_test 命令不同）
"""
#: 从模块「importlib」导入所需对象
from importlib import util as importlib_util

#: 从模块「django.apps」导入所需对象
from django.apps import apps
#: 从模块「django.conf」导入所需对象
from django.conf import settings
#: 从模块「django.core.cache」导入所需对象
from django.core.cache import cache
#: 从模块「django.core.management」导入所需对象
from django.core.management import get_commands
#: 从模块「django.core.management.base」导入所需对象
from django.core.management.base import BaseCommand
#: 从模块「django.db」导入所需对象
from django.db import connection
#: 从模块「django.urls」导入所需对象
from django.urls import get_resolver


class Command(BaseCommand):
    """项目综合诊断：配置 / 依赖 / 数据库 / 缓存 / 路由 / 模型 / 视图一览。"""

    #: 定义变量「help」，保存对应数据
    help = '一键诊断项目健康度（合并 check_* / list_* 系列命令）'

    def add_arguments(self, parser):
        """注册所有诊断块的开关。"""
        # 一键开关
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--all', action='store_true', help='执行全部诊断项')

        # 配置与依赖类
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--config', action='store_true', help='输出 DEBUG 等关键配置')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--deps', action='store_true', help='检查第三方依赖是否可导入')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--permissions', action='store_true', help='统计权限表条目数')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--security', action='store_true',
                            #: 定义变量「help」，保存对应数据
                            help='输出安全相关配置项（仅配置项检查，完整渗透测试见独立命令 security_test）')

        # 运行时类
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--db', action='store_true', help='检查数据库连接')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--cache', action='store_true', help='检查缓存后端读写')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--celery', action='store_true', help='检查 Celery 状态')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--static', action='store_true', help='检查静态文件配置')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--templates', action='store_true', help='检查模板配置')

        # 结构盘点类
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--urls', action='store_true', help='输出顶层 URL 路由数量')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--models', action='store_true', help='列出全部已注册模型')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--middleware', action='store_true', help='列出中间件链')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--views', action='store_true', help='列出 blog.views 中所有可调用对象')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--commands', action='store_true', help='列出 Django 已注册的管理命令')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--templatetags', action='store_true', help='列出 blog 应用自定义模板标签')

        # 第3轮迭代#6: 增强诊断项
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--static-size', action='store_true',
                            #: 定义变量「help」，保存对应数据
                            help='输出 static/assets 下 CSS/JS 文件大小并标注预算超限')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--cache-stats', action='store_true',
                            #: 定义变量「help」，保存对应数据
                            help='输出当前缓存 key 数量与占用（LocMemCache 内部统计）')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--cache-keys', nargs='?', const='all', default=None,
                            #: 定义变量「help」，保存对应数据
                            help='列出缓存 key（可带前缀过滤，如 --cache-keys v1:；'
                                 #: 该行执行对应逻辑（结合上下文理解）
                                 'LocMemCache 为进程内缓存，跨进程请用 /__debug_cache/ 端点）')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--slow-queries', action='store_true',
                            #: 定义变量「help」，保存对应数据
                            help='输出最近 >500ms 的慢查询（DEBUG=True 时 connection.queries）')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--db-stats', action='store_true',
                            #: 定义变量「help」，保存对应数据
                            help='输出各核心表记录数（文章/评论/用户/分类/标签）')
        # 第4轮 A5: N+1 检测建议
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--n-plus-one', action='store_true',
                            #: ORM 预加载关联，减少 N+1 查询提升性能
                            help='列出常见 N+1 风险点及应补的 select_related/prefetch_related')

    def handle(self, *args, **options):
        """按 flag 分发到各个诊断方法，任一子项失败不影响其它项。"""
        #: 定义变量「run_all」，保存对应数据
        run_all = options['all']

        # 映射：flag 名 -> (标题, 方法)
        #: 定义变量「blocks」，保存对应数据（集合/元组）
        blocks = [
            #: 该行执行对应逻辑（结合上下文理解）
            ('config', '项目配置', self._check_config),
            #: 该行执行对应逻辑（结合上下文理解）
            ('deps', '第三方依赖', self._check_deps),
            #: 该行执行对应逻辑（结合上下文理解）
            ('db', '数据库连接', self._check_db),
            #: 该行执行对应逻辑（结合上下文理解）
            ('cache', '缓存后端', self._check_cache),
            #: 该行执行对应逻辑（结合上下文理解）
            ('celery', 'Celery 状态', self._check_celery),
            #: 该行执行对应逻辑（结合上下文理解）
            ('security', '安全配置项', self._check_security),
            #: 该行执行对应逻辑（结合上下文理解）
            ('permissions', '权限表', self._check_permissions),
            #: 该行执行对应逻辑（结合上下文理解）
            ('static', '静态文件', self._check_static),
            #: 该行执行对应逻辑（结合上下文理解）
            ('templates', '模板配置', self._check_templates),
            #: 该行执行对应逻辑（结合上下文理解）
            ('urls', 'URL 路由', self._list_urls),
            #: 该行执行对应逻辑（结合上下文理解）
            ('models', '模型清单', self._list_models),
            #: 该行执行对应逻辑（结合上下文理解）
            ('middleware', '中间件链', self._list_middleware),
            #: 该行执行对应逻辑（结合上下文理解）
            ('views', '视图函数', self._list_views),
            #: 该行执行对应逻辑（结合上下文理解）
            ('commands', '管理命令', self._list_commands),
            #: 该行执行对应逻辑（结合上下文理解）
            ('templatetags', '模板标签', self._list_templatetags),
            #: 该行执行对应逻辑（结合上下文理解）
            ('static_size', '静态资源体积', self._check_static_size),
            #: 该行执行对应逻辑（结合上下文理解）
            ('cache_stats', '缓存统计', self._check_cache_stats),
            #: 该行执行对应逻辑（结合上下文理解）
            ('cache_keys', '缓存 key 清单', lambda: self._check_cache_keys(options['cache_keys'])),
            #: 该行执行对应逻辑（结合上下文理解）
            ('slow_queries', '慢查询', self._check_slow_queries),
            #: 该行执行对应逻辑（结合上下文理解）
            ('db_stats', '数据表统计', self._check_db_stats),
            #: 该行执行对应逻辑（结合上下文理解）
            ('n_plus_one', 'N+1 查询检测建议', self._check_n_plus_one),
        #: 该行执行对应逻辑（结合上下文理解）
        ]

        # 没有任何 flag 且未指定 --all 时，打印帮助并退出
        #: 条件判断：条件成立时执行该分支
        if not run_all and not any(options[key] for key, _, _ in blocks):
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.WARNING(
                #: 该行执行对应逻辑（结合上下文理解）
                '未指定任何诊断项。使用 --all 跑全部，或用 --db / --urls / --models 等单项开关。'))
            #: 返回结果并结束当前函数
            return

        #: 定义变量「executed」，保存对应数据
        executed = 0
        #: 循环遍历，逐个处理元素
        for key, title, method in blocks:
            #: 条件判断：条件成立时执行该分支
            if run_all or options[key]:
                #: 该行执行对应逻辑（结合上下文理解）
                executed += 1
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write(self.style.MIGRATE_HEADING(f'\n=== {title} ==='))
                #: 尝试执行可能出错的代码
                try:
                    #: 调用「method」执行相应逻辑
                    method()
                #: 捕获并处理异常，避免程序中断
                except Exception as exc:  # 单项失败不阻断整体诊断
                    #: 调用「self.stderr.write」执行相应逻辑
                    self.stderr.write(self.style.ERROR(f'  执行失败: {exc}'))

        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.SUCCESS(f'\n诊断完成，共执行 {executed} 个模块。'))

    # ============================ check_* 系列 ============================

    def _check_config(self):
        """输出关键运行配置（DEBUG / 数据库 ENGINE 等）。"""
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(f'DEBUG = {settings.DEBUG}')
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(f'USE_TZ = {getattr(settings, "USE_TZ", None)}')
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(f'ALLOWED_HOSTS = {getattr(settings, "ALLOWED_HOSTS", None)}')

    def _check_deps(self):
        """探测常用第三方包是否已安装可导入，并核对 requests 依赖版本组合。"""
        #: 循环遍历，逐个处理元素
        for module in ('django', 'rest_framework', 'bleach', 'PIL', 'celery'):
            #: 定义变量「found」，保存对应数据
            found = importlib_util.find_spec(module) is not None
            #: 定义变量「mark」，保存对应数据
            mark = self.style.SUCCESS('OK') if found else self.style.ERROR('MISSING')
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(f'  {module:<16} {mark}')
        #: 调用「self._check_requests_warning」执行相应逻辑
        self._check_requests_warning()

    def _check_requests_warning(self):
        """硬性指标核验：requests 导入不得产生 RequestsDependencyWarning。

        验收要求「django check 0 错误 0 警告，消除 requests 版本告警」。
        这里在 ``warnings.catch_warnings`` 中强制重载 requests，直接检查：
          1. 是否抛出 RequestsDependencyWarning；
          2. requests 内部解析出的 chardet / charset_normalizer / urllib3 版本组合；
          3. 关键包的实际安装版本。
        """
        #: 导入模块「warnings」，供本文件后续使用
        import warnings
        #: 尝试执行可能出错的代码
        try:
            #: 从模块「requests.exceptions」导入所需对象
            from requests.exceptions import RequestsDependencyWarning
        #: 捕获并处理异常，避免程序中断
        except Exception:  # noqa: BLE001 requests 未安装
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.WARNING('  requests          未安装，跳过版本告警核验'))
            #: 返回结果并结束当前函数
            return
        # 强制重新执行 requests 模块顶层的版本兼容检查
        #: 上下文管理：进入时获取资源、退出时自动释放
        with warnings.catch_warnings(record=True) as caught:
            #: 调用「warnings.simplefilter」执行相应逻辑
            warnings.simplefilter('always')
            #: 尝试执行可能出错的代码
            try:
                #: 导入模块「requests」，供本文件后续使用
                import requests
                #: 定义变量「req_ver」，保存对应数据
                req_ver = requests.__version__
            #: 捕获并处理异常，避免程序中断
            except Exception as exc:  # noqa: BLE001
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write(self.style.ERROR(f'  requests 导入失败: {exc}'))
                #: 返回结果并结束当前函数
                return
        # requests.compat 在不同版本里暴露的符号不同，这里以「实际安装版本」为准
        def _ver(module_name):
            """
            功能：处理「ver」相关逻辑。

            参数：
              - module_name：传入参数，含义结合函数体与调用处

            返回：对应计算/查询结果。

            注意：保持函数单一职责；修改时确认调用方不受影响。
            """
            #: 尝试执行可能出错的代码
            try:
                #: 定义变量「mod」，保存对应数据
                mod = __import__(module_name)
                #: 返回结果并结束当前函数
                return getattr(mod, '__version__', '未知')
            #: 捕获并处理异常，避免程序中断
            except Exception:  # noqa: BLE001
                #: 返回结果并结束当前函数
                return '未安装'

        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(f'  requests          {req_ver}')
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(f'  urllib3           {_ver("urllib3")}')
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(f'  chardet           {_ver("chardet")}')
        # requests 的兼容性检查在模块顶层只跑一次；若此前已被导入，上面的
        # catch_warnings 捕获不到任何东西。这里主动重跑一次检查函数，
        # 确保「有没有告警」的结论不被模块缓存掩盖。
        #: 定义变量「rerun_error」，保存对应数据
        rerun_error = ''
        #: 尝试执行可能出错的代码
        try:
            #: 上下文管理：进入时获取资源、退出时自动释放
            with warnings.catch_warnings(record=True) as caught2:
                #: 调用「warnings.simplefilter」执行相应逻辑
                warnings.simplefilter('always')
                #: 从模块「requests」导入所需对象
                from requests import check_compatibility
                #: 调用「check_compatibility」执行相应逻辑
                check_compatibility(urllib3_version=_ver('urllib3'),
                                    #: 定义变量「chardet_version」，保存对应数据
                                    chardet_version=_ver('chardet'),
                                    #: 定义变量「charset_normalizer_version」，保存对应数据
                                    charset_normalizer_version=_ver('charset_normalizer'))
            #: 调用「caught.extend」执行相应逻辑
            caught.extend(caught2)
        #: 捕获并处理异常，避免程序中断
        except Exception as exc:  # noqa: BLE001 新版本可能没有该函数，按导入结果判定
            #: 定义变量「rerun_error」，保存对应数据
            rerun_error = str(exc)
        #: 定义变量「dep_warnings」，保存对应数据（集合/元组）
        dep_warnings = [w for w in caught if issubclass(w.category, RequestsDependencyWarning)]
        #: 条件判断：条件成立时执行该分支
        if dep_warnings:
            #: 循环遍历，逐个处理元素
            for w in dep_warnings:
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write(self.style.ERROR(f'  RequestsDependencyWarning: {w.message}'))
        #: 以上条件均不成立时的兜底分支
        else:
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.SUCCESS(
                #: 该行执行对应逻辑（结合上下文理解）
                '  requests 版本告警核验   OK（无 RequestsDependencyWarning）'))
        #: 条件判断：条件成立时执行该分支
        if rerun_error:
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(f'  （兼容性检查函数不可直接调用：{rerun_error[:80]}）')

    def _check_db(self):
        """测试数据库连接并显示当前 ENGINE。"""
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(f'数据库: {connection.settings_dict["ENGINE"]}')
        #: 上下文管理：进入时获取资源、退出时自动释放
        with connection.cursor() as cur:
            #: 调用「cur.execute」执行相应逻辑
            cur.execute('SELECT 1')
            #: 调用「cur.fetchone」执行相应逻辑
            cur.fetchone()
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.SUCCESS('数据库连接正常'))

    def _check_cache(self):
        """写入再读出一个 ping 值，验证缓存后端可用。"""
        #: 读写缓存，减轻数据库压力，注意键与过期时间
        cache.set('diag_ping', 1, 1)
        #: 读写缓存，减轻数据库压力，注意键与过期时间
        value = cache.get('diag_ping')
        #: 条件判断：条件成立时执行该分支
        if value == 1:
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.SUCCESS('缓存读写正常'))
        #: 以上条件均不成立时的兜底分支
        else:
            #: 调用「self.stderr.write」执行相应逻辑
            self.stderr.write(self.style.ERROR(f'缓存异常：返回值={value!r}'))

    def _check_celery(self):
        """Celery 状态占位检查（具体 worker 状态需连 broker，这里只做导入探测）。"""
        #: 尝试执行可能出错的代码
        try:
            #: 从模块「celery」导入所需对象
            from celery import Celery  # noqa: F401
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.SUCCESS('celery 包已安装；worker 状态请用 `celery -A DjangoBlog status` 查看'))
        #: 捕获并处理异常，避免程序中断
        except ImportError:
            #: 调用「self.stderr.write」执行相应逻辑
            self.stderr.write(self.style.ERROR('未安装 celery'))

    def _check_security(self):
        """输出与安全相关的关键配置项（仅配置值，不做渗透测试）。"""
        #: 循环遍历，逐个处理元素
        for key in (
            #: 该行执行对应逻辑（结合上下文理解）
            'SESSION_COOKIE_HTTPONLY',
            #: 该行执行对应逻辑（结合上下文理解）
            'CSRF_COOKIE_HTTPONLY',
            #: 该行执行对应逻辑（结合上下文理解）
            'SECURE_CONTENT_TYPE_NOSNIFF',
            #: 该行执行对应逻辑（结合上下文理解）
            'SECURE_BROWSER_XSS_FILTER',
            #: 该行执行对应逻辑（结合上下文理解）
            'X_FRAME_OPTIONS',
        #: 该行执行对应逻辑（结合上下文理解）
        ):
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(f'  {key} = {getattr(settings, key, "<未设置>")}')

    def _check_permissions(self):
        """统计 auth_permission 表条目数。"""
        #: 从模块「django.contrib.auth.models」导入所需对象
        from django.contrib.auth.models import Permission
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        self.stdout.write(f'权限总数: {Permission.objects.count()}')

    def _check_static(self):
        """静态文件相关配置检查。"""
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(f'STATIC_URL = {getattr(settings, "STATIC_URL", None)}')
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(f'STATIC_ROOT = {getattr(settings, "STATIC_ROOT", None)}')
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(f'已安装 staticfiles 应用: '
                          #: 该行执行对应逻辑（结合上下文理解）
                          f'{"django.contrib.staticfiles" in settings.INSTALLED_APPS}')

    def _check_templates(self):
        """模板引擎配置检查。"""
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(f'TEMPLATES 引擎数: {len(getattr(settings, "TEMPLATES", []))}')
        #: 循环遍历，逐个处理元素
        for idx, tpl in enumerate(getattr(settings, 'TEMPLATES', [])):
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(f'  [{idx}] BACKEND = {tpl.get("BACKEND")}')
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(f'      APP_DIRS = {tpl.get("APP_DIRS")}')

    # ============================ list_* 系列 ============================

    def _list_urls(self):
        """统计顶层 URL 路由数量。"""
        #: 定义变量「patterns」，保存对应数据
        patterns = get_resolver().url_patterns
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(f'顶层 URL 路由数: {len(patterns)}')

    def _list_models(self):
        """列出所有已注册到 Django 的模型类名。"""
        #: 循环遍历，逐个处理元素
        for model in apps.get_models():
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(f'  {model._meta.app_label}.{model.__name__}')

    def _list_middleware(self):
        """输出 settings.MIDDLEWARE 链。"""
        #: 循环遍历，逐个处理元素
        for mw in settings.MIDDLEWARE:
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(f'  {mw}')

    def _list_views(self):
        """列出 blog.views 模块中所有可调用对象（含视图函数与 CBV）。"""
        #: 导入模块「blog.views」，供本文件后续使用
        import blog.views as views_module
        #: 循环遍历，逐个处理元素
        for name in sorted(dir(views_module)):
            #: 定义变量「obj」，保存对应数据
            obj = getattr(views_module, name, None)
            #: 条件判断：条件成立时执行该分支
            if callable(obj) and not name.startswith('_'):
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write(f'  {name}')

    def _list_commands(self):
        """列出 Django 已注册的全部管理命令名。"""
        #: 循环遍历，逐个处理元素
        for cmd in sorted(get_commands()):
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(f'  {cmd}')

    def _list_templatetags(self):
        """列出 blog 应用自定义模板标签库中已知标签。"""
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write('  blog_extras: is_new, time_ago, highlight, lazy_images')


    # ============================ 第3轮迭代#6: 增强诊断项 ============================

    # 静态资源体积预算（KB）：超出则在输出中标红
    #: 定义变量「STATIC_BUDGET_KB」，保存对应数据
    STATIC_BUDGET_KB = {
        #: 该行执行对应逻辑（结合上下文理解）
        'ui_polish.css': 60,
        #: 该行执行对应逻辑（结合上下文理解）
        'common.js': 18,
    #: 该行执行对应逻辑（结合上下文理解）
    }

    def _check_static_size(self):
        """遍历 static/assets 下 CSS/JS 文件大小，标注是否超出预算。"""
        #: 导入模块「os」，供本文件后续使用
        import os
        #: 定义变量「base」，保存对应数据
        base = os.path.join(settings.BASE_DIR if hasattr(settings, 'BASE_DIR') else '.', 'static', 'assets')
        #: 条件判断：条件成立时执行该分支
        if not os.path.isdir(base):
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.WARNING(f'未找到目录: {base}'))
            #: 返回结果并结束当前函数
            return
        #: 定义变量「targets」，保存对应数据（集合/元组）
        targets = []
        #: 循环遍历，逐个处理元素
        for root, _dirs, files in os.walk(base):
            #: 循环遍历，逐个处理元素
            for fn in files:
                #: 条件判断：条件成立时执行该分支
                if fn.lower().endswith(('.css', '.js')):
                    #: 定义变量「full」，保存对应数据
                    full = os.path.join(root, fn)
                    #: 定义变量「rel」，保存对应数据
                    rel = os.path.relpath(full, base)
                    #: 调用「targets.append」执行相应逻辑
                    targets.append((rel, os.path.getsize(full)))
        #: 调用「targets.sort」执行相应逻辑
        targets.sort()
        #: 条件判断：条件成立时执行该分支
        if not targets:
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write('  未发现 CSS/JS 文件')
            #: 返回结果并结束当前函数
            return
        #: 循环遍历，逐个处理元素
        for rel, size in targets:
            #: 定义变量「kb」，保存对应数据
            kb = size / 1024
            #: 定义变量「budget」，保存对应数据
            budget = self.STATIC_BUDGET_KB.get(os.path.basename(rel))
            #: 定义变量「flag」，保存对应数据
            flag = ''
            #: 条件判断：条件成立时执行该分支
            if budget is not None:
                #: 条件判断：条件成立时执行该分支
                if kb > budget:
                    #: 定义变量「flag」，保存对应数据
                    flag = self.style.ERROR(f'  超预算(>{budget}KB)')
                #: 以上条件均不成立时的兜底分支
                else:
                    #: 定义变量「flag」，保存对应数据
                    flag = self.style.SUCCESS(f'  OK(≤{budget}KB)')
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(f'  {rel:<40} {kb:8.1f} KB{flag}')

    def _check_cache_stats(self):
        """统计当前缓存后端的 key 数量与占用（LocMemCache 内部字典，其它后端尽力而为）。"""
        #: 定义变量「internal」，保存对应数据
        internal = getattr(cache, '_cache', None)
        #: 条件判断：条件成立时执行该分支
        if isinstance(internal, dict):
            #: 定义变量「total_keys」，保存对应数据
            total_keys = len(internal)
            #: 定义变量「total_bytes」，保存对应数据
            total_bytes = 0
            #: 循环遍历，逐个处理元素
            for value in internal.values():
                #: 尝试执行可能出错的代码
                try:
                    #: 该行执行对应逻辑（结合上下文理解）
                    total_bytes += len(repr(value).encode('utf-8'))
                #: 捕获并处理异常，避免程序中断
                except Exception:  # noqa: BLE001
                    #: 占位语句：此处暂不需要实现
                    pass
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(f'  缓存后端: LocMemCache')
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(f'  当前 key 数量: {total_keys}')
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(f'  估算占用: {total_bytes / 1024:.1f} KB')
            # 命中率需要 hit/miss 计数器，LocMemCache 内部有 _hits/_misses
            #: 定义变量「hits」，保存对应数据
            hits = getattr(cache, '_hits', None)
            #: 定义变量「misses」，保存对应数据
            misses = getattr(cache, '_misses', None)
            #: 条件判断：条件成立时执行该分支
            if hits is not None and misses is not None:
                #: 定义变量「total」，保存对应数据
                total = hits + misses
                #: 定义变量「rate」，保存对应数据（集合/元组）
                rate = (hits / total * 100) if total else 0
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write(f'  命中率: {rate:.1f}% (hits={hits}, misses={misses})')
            #: 以上条件均不成立时的兜底分支
            else:
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write('  命中率: 当前后端未暴露 hit/miss 计数')
            # 详情页片段命中统计（cache_keys 模块进程内累积；diag 独立进程通常为空，
            # 运行中服务的数据请访问 DEBUG 端点 /__debug_cache/）
            #: 从模块「blog.utils.cache_keys」导入所需对象
            from blog.utils.cache_keys import get_stats as _frag_stats
            #: 定义变量「_s」，保存对应数据
            _s = _frag_stats()
            #: 条件判断：条件成立时执行该分支
            if _s:
                #: 定义变量「_tot_h」，保存对应数据
                _tot_h = sum(v['hits'] for v in _s.values())
                #: 定义变量「_tot_m」，保存对应数据
                _tot_m = sum(v['misses'] for v in _s.values())
                #: 定义变量「_rt」，保存对应数据（集合/元组）
                _rt = (_tot_h / (_tot_h + _tot_m) * 100) if (_tot_h + _tot_m) else 0
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write(f'  详情页片段命中率: {_rt:.1f}% '
                                  #: 该行执行对应逻辑（结合上下文理解）
                                  f'(hits={_tot_h}, misses={_tot_m}, 进程内累积，见 /__debug_cache/)')
        #: 以上条件均不成立时的兜底分支
        else:
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.WARNING('  当前缓存后端不支持内部 key 统计'))

    def _check_cache_keys(self, prefix='all'):
        """列出当前缓存进程内的全部 key（可带前缀过滤），并显示详情页片段命中统计。"""
        #: 导入模块「time」，供本文件后续使用
        import time as _time
        #: 从模块「blog.utils.cache_keys」导入所需对象
        from blog.utils.cache_keys import get_stats
        #: 定义变量「internal」，保存对应数据
        internal = getattr(cache, '_cache', None)
        #: 定义变量「expire」，保存对应数据
        expire = getattr(cache, '_expire_info', None)
        #: 条件判断：条件成立时执行该分支
        if isinstance(internal, dict):
            #: 定义变量「now」，保存对应数据
            now = _time.time()
            #: 定义变量「keys」，保存对应数据
            keys = list(internal.keys())
            #: 条件判断：条件成立时执行该分支
            if prefix and prefix != 'all':
                #: 定义变量「keys」，保存对应数据（集合/元组）
                keys = [k for k in keys if k.startswith(prefix)]
            #: 调用「keys.sort」执行相应逻辑
            keys.sort()
            #: 条件判断：条件成立时执行该分支
            if not keys:
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write(self.style.WARNING(
                    #: 该行执行对应逻辑（结合上下文理解）
                    '  无匹配 key（LocMemCache 为进程内缓存，diag 是独立进程，'
                    #: 该行执行对应逻辑（结合上下文理解）
                    '看不到 runserver 进程的缓存；请用 DEBUG 端点 /__debug_cache/ 查看）'))
            #: 循环遍历，逐个处理元素
            for k in keys:
                #: 定义变量「ttl」，保存对应数据
                ttl = None
                #: 条件判断：条件成立时执行该分支
                if expire and k in expire:
                    #: 定义变量「ttl」，保存对应数据
                    ttl = max(0, int(expire[k] - now))
                #: 定义变量「ttl_s」，保存对应数据
                ttl_s = f'{ttl}s' if ttl is not None else '?'
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write(f'  {k}  (剩余TTL {ttl_s})')
        #: 以上条件均不成立时的兜底分支
        else:
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.WARNING(
                #: 该行执行对应逻辑（结合上下文理解）
                '  当前缓存后端不可枚举；生产环境可在 Redis 用 KEYS v*: 查看，'
                #: 该行执行对应逻辑（结合上下文理解）
                '或访问 DEBUG 端点 /__debug_cache/'))
        #: 定义变量「stats」，保存对应数据
        stats = get_stats()
        #: 条件判断：条件成立时执行该分支
        if stats:
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write('  详情页片段命中统计（进程内累积）：')
            #: 循环遍历，逐个处理元素
            for key, s in sorted(stats.items()):
                #: 定义变量「total」，保存对应数据
                total = s['hits'] + s['misses']
                #: 定义变量「rate」，保存对应数据（集合/元组）
                rate = (s['hits'] / total * 100) if total else 0
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write(
                    #: 该行执行对应逻辑（结合上下文理解）
                    f'    {key}  hits={s["hits"]} misses={s["misses"]} rate={rate:.0f}%')

    def _check_slow_queries(self):
        """输出最近 >500ms 的慢查询（依赖 DEBUG=True 时 connection.queries 记录）。"""
        #: 条件判断：条件成立时执行该分支
        if not settings.DEBUG:
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.WARNING('  DEBUG=False，connection.queries 未记录，无法统计慢查询'))
            #: 返回结果并结束当前函数
            return
        #: 定义变量「queries」，保存对应数据
        queries = getattr(connection, 'queries', [])
        #: 定义变量「slow」，保存对应数据（集合/元组）
        slow = [q for q in queries if float(q.get('time', 0)) > 0.5]
        #: 条件判断：条件成立时执行该分支
        if not slow:
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.SUCCESS('  本进程内无 >500ms 的慢查询'))
            #: 返回结果并结束当前函数
            return
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.WARNING(f'  发现 {len(slow)} 条 >500ms 慢查询:'))
        #: 循环遍历，逐个处理元素
        for q in slow[:20]:
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(f"    [{float(q.get('time', 0))*1000:.0f}ms] {q.get('sql', '')[:120]}")

    def _check_db_stats(self):
        """输出各核心表记录数。"""
        #: 从模块「blog.models」导入所需对象
        from blog.models import Article, Category, Comment, Tag, User
        #: 定义变量「rows」，保存对应数据（集合/元组）
        rows = [
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            ('文章 Article', Article.objects.count()),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            ('评论 Comment', Comment.objects.count()),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            ('用户 User', User.objects.count()),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            ('分类 Category', Category.objects.count()),
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            ('标签 Tag', Tag.objects.count()),
        #: 该行执行对应逻辑（结合上下文理解）
        ]
        #: 循环遍历，逐个处理元素
        for name, cnt in rows:
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(f'  {name:<16} {cnt} 条')


    # 第4轮 A5: N+1 查询检测建议
    def _check_n_plus_one(self):
        """列出全站常见 N+1 风险点及应补的 select_related / prefetch_related。

        本方法为静态代码巡检清单，不实际执行查询；用于 code review 与回归自查。
        """
        #: 定义变量「suggestions」，保存对应数据（集合/元组）
        suggestions = [
            #: ORM 预加载关联，减少 N+1 查询提升性能
            ('index 文章列表', '_base_qs 已 select_related(author,category) + prefetch_related(tags)'),
            #: ORM 预加载关联，减少 N+1 查询提升性能
            ('article_detail 文章主体', '已 select_related(author,category) + prefetch_related(tags)'),
            #: ORM 预加载关联，减少 N+1 查询提升性能
            ('article_detail 评论树', '_build_comment_tree：select_related(user) 单次取出全部评论'),
            #: ORM 预加载关联，减少 N+1 查询提升性能
            ('article_detail 相关文章', 'C1：annotate(common_tags) + select_related(author,category) 仅取卡片字段'),
            #: ORM 预加载关联，减少 N+1 查询提升性能
            ('article_detail 上/下一篇', '已走 _base_qs（含 select_related/prefetch）'),
            #: ORM 预加载关联，减少 N+1 查询提升性能
            ('article_detail 修改日志', 'edit_logs.select_related(editor)[:10]'),
            #: 该行执行对应逻辑（结合上下文理解）
            ('侧边栏热门/标签云/导航', '_sidebar() 缓存 300s，命中后无 SQL'),
            #: 该行执行对应逻辑（结合上下文理解）
            ('侧边栏统计 sidebar_stats', 'A4：get_sidebar_stats() 缓存 300s'),
            #: 该行执行对应逻辑（结合上下文理解）
            ('搜索结果', '复用 index 同一 _base_qs，关联已预取'),
            #: ORM 预加载关联，减少 N+1 查询提升性能
            ('用户主页收藏列表', 'fav_articles.select_related(author,category)'),
        #: 该行执行对应逻辑（结合上下文理解）
        ]
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write('  已覆盖的关联预取：')
        #: 循环遍历，逐个处理元素
        for name, ok in suggestions:
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.SUCCESS(f'    [OK] {name:<26} {ok}'))
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write('')
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write('  仍需人工复核的风险点：')
        #: 循环遍历，逐个处理元素
        for risk in (
            #: 该行执行对应逻辑（结合上下文理解）
            '模板循环访问 article.tags.all() 是否触发额外查询（应由 prefetch 覆盖）',
            #: ORM 预加载关联，减少 N+1 查询提升性能
            '模板中 {{ comment.user }} 是否每条评论查 user（应由 select_related 覆盖）',
            #: 该行执行对应逻辑（结合上下文理解）
            'search 关键词高亮在模板侧，确认未在循环内对每条结果重复查库',
            #: 该行执行对应逻辑（结合上下文理解）
            '新增 ORM 查询优先走 _base_qs / .with_related() / .optimized() 链式方法',
        #: 该行执行对应逻辑（结合上下文理解）
        ):
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.WARNING(f'    [检查] {risk}'))

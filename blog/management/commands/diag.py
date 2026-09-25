"""综合诊断命令：python manage.py diag [选项]

合并了原 10 个 check_* 与 6 个 list_* 管理命令的全部检查项，
通过命令行 flag 选择要执行的诊断块；默认无任何 flag 时给出帮助并提示使用 --all。

用法示例：
    python manage.py diag --all                # 跑全部诊断
    python manage.py diag --db --urls          # 只查数据库与路由
    python manage.py diag --models --views     # 只列模型与视图
    python manage.py diag --security           # 只看安全相关配置项（与独立的 security_test 命令不同）
"""
from importlib import util as importlib_util

from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from django.core.management import get_commands
from django.core.management.base import BaseCommand
from django.db import connection
from django.urls import get_resolver


class Command(BaseCommand):
    """项目综合诊断：配置 / 依赖 / 数据库 / 缓存 / 路由 / 模型 / 视图一览。"""

    help = '一键诊断项目健康度（合并 check_* / list_* 系列命令）'

    def add_arguments(self, parser):
        """注册所有诊断块的开关。"""
        # 一键开关
        parser.add_argument('--all', action='store_true', help='执行全部诊断项')

        # 配置与依赖类
        parser.add_argument('--config', action='store_true', help='输出 DEBUG 等关键配置')
        parser.add_argument('--deps', action='store_true', help='检查第三方依赖是否可导入')
        parser.add_argument('--permissions', action='store_true', help='统计权限表条目数')
        parser.add_argument('--security', action='store_true',
                            help='输出安全相关配置项（仅配置项检查，完整渗透测试见独立命令 security_test）')

        # 运行时类
        parser.add_argument('--db', action='store_true', help='检查数据库连接')
        parser.add_argument('--cache', action='store_true', help='检查缓存后端读写')
        parser.add_argument('--celery', action='store_true', help='检查 Celery 状态')
        parser.add_argument('--static', action='store_true', help='检查静态文件配置')
        parser.add_argument('--templates', action='store_true', help='检查模板配置')

        # 结构盘点类
        parser.add_argument('--urls', action='store_true', help='输出顶层 URL 路由数量')
        parser.add_argument('--models', action='store_true', help='列出全部已注册模型')
        parser.add_argument('--middleware', action='store_true', help='列出中间件链')
        parser.add_argument('--views', action='store_true', help='列出 blog.views 中所有可调用对象')
        parser.add_argument('--commands', action='store_true', help='列出 Django 已注册的管理命令')
        parser.add_argument('--templatetags', action='store_true', help='列出 blog 应用自定义模板标签')

        # 第3轮迭代#6: 增强诊断项
        parser.add_argument('--static-size', action='store_true',
                            help='输出 static/assets 下 CSS/JS 文件大小并标注预算超限')
        parser.add_argument('--cache-stats', action='store_true',
                            help='输出当前缓存 key 数量与占用（LocMemCache 内部统计）')
        parser.add_argument('--cache-keys', nargs='?', const='all', default=None,
                            help='列出缓存 key（可带前缀过滤，如 --cache-keys v1:；'
                                 'LocMemCache 为进程内缓存，跨进程请用 /__debug_cache/ 端点）')
        parser.add_argument('--slow-queries', action='store_true',
                            help='输出最近 >500ms 的慢查询（DEBUG=True 时 connection.queries）')
        parser.add_argument('--db-stats', action='store_true',
                            help='输出各核心表记录数（文章/评论/用户/分类/标签）')
        # 第4轮 A5: N+1 检测建议
        parser.add_argument('--n-plus-one', action='store_true',
                            help='列出常见 N+1 风险点及应补的 select_related/prefetch_related')

    def handle(self, *args, **options):
        """按 flag 分发到各个诊断方法，任一子项失败不影响其它项。"""
        run_all = options['all']

        # 映射：flag 名 -> (标题, 方法)
        blocks = [
            ('config', '项目配置', self._check_config),
            ('deps', '第三方依赖', self._check_deps),
            ('db', '数据库连接', self._check_db),
            ('cache', '缓存后端', self._check_cache),
            ('celery', 'Celery 状态', self._check_celery),
            ('security', '安全配置项', self._check_security),
            ('permissions', '权限表', self._check_permissions),
            ('static', '静态文件', self._check_static),
            ('templates', '模板配置', self._check_templates),
            ('urls', 'URL 路由', self._list_urls),
            ('models', '模型清单', self._list_models),
            ('middleware', '中间件链', self._list_middleware),
            ('views', '视图函数', self._list_views),
            ('commands', '管理命令', self._list_commands),
            ('templatetags', '模板标签', self._list_templatetags),
            ('static_size', '静态资源体积', self._check_static_size),
            ('cache_stats', '缓存统计', self._check_cache_stats),
            ('cache_keys', '缓存 key 清单', lambda: self._check_cache_keys(options['cache_keys'])),
            ('slow_queries', '慢查询', self._check_slow_queries),
            ('db_stats', '数据表统计', self._check_db_stats),
            ('n_plus_one', 'N+1 查询检测建议', self._check_n_plus_one),
        ]

        # 没有任何 flag 且未指定 --all 时，打印帮助并退出
        if not run_all and not any(options[key] for key, _, _ in blocks):
            self.stdout.write(self.style.WARNING(
                '未指定任何诊断项。使用 --all 跑全部，或用 --db / --urls / --models 等单项开关。'))
            return

        executed = 0
        for key, title, method in blocks:
            if run_all or options[key]:
                executed += 1
                self.stdout.write(self.style.MIGRATE_HEADING(f'\n=== {title} ==='))
                try:
                    method()
                except Exception as exc:  # 单项失败不阻断整体诊断
                    self.stderr.write(self.style.ERROR(f'  执行失败: {exc}'))

        self.stdout.write(self.style.SUCCESS(f'\n诊断完成，共执行 {executed} 个模块。'))

    # ============================ check_* 系列 ============================

    def _check_config(self):
        """输出关键运行配置（DEBUG / 数据库 ENGINE 等）。"""
        self.stdout.write(f'DEBUG = {settings.DEBUG}')
        self.stdout.write(f'USE_TZ = {getattr(settings, "USE_TZ", None)}')
        self.stdout.write(f'ALLOWED_HOSTS = {getattr(settings, "ALLOWED_HOSTS", None)}')

    def _check_deps(self):
        """探测常用第三方包是否已安装可导入。"""
        for module in ('django', 'rest_framework', 'bleach', 'PIL', 'celery'):
            found = importlib_util.find_spec(module) is not None
            mark = self.style.SUCCESS('OK') if found else self.style.ERROR('MISSING')
            self.stdout.write(f'  {module:<16} {mark}')

    def _check_db(self):
        """测试数据库连接并显示当前 ENGINE。"""
        self.stdout.write(f'数据库: {connection.settings_dict["ENGINE"]}')
        with connection.cursor() as cur:
            cur.execute('SELECT 1')
            cur.fetchone()
        self.stdout.write(self.style.SUCCESS('数据库连接正常'))

    def _check_cache(self):
        """写入再读出一个 ping 值，验证缓存后端可用。"""
        cache.set('diag_ping', 1, 1)
        value = cache.get('diag_ping')
        if value == 1:
            self.stdout.write(self.style.SUCCESS('缓存读写正常'))
        else:
            self.stderr.write(self.style.ERROR(f'缓存异常：返回值={value!r}'))

    def _check_celery(self):
        """Celery 状态占位检查（具体 worker 状态需连 broker，这里只做导入探测）。"""
        try:
            from celery import Celery  # noqa: F401
            self.stdout.write(self.style.SUCCESS('celery 包已安装；worker 状态请用 `celery -A DjangoBlog status` 查看'))
        except ImportError:
            self.stderr.write(self.style.ERROR('未安装 celery'))

    def _check_security(self):
        """输出与安全相关的关键配置项（仅配置值，不做渗透测试）。"""
        for key in (
            'SESSION_COOKIE_HTTPONLY',
            'CSRF_COOKIE_HTTPONLY',
            'SECURE_CONTENT_TYPE_NOSNIFF',
            'SECURE_BROWSER_XSS_FILTER',
            'X_FRAME_OPTIONS',
        ):
            self.stdout.write(f'  {key} = {getattr(settings, key, "<未设置>")}')

    def _check_permissions(self):
        """统计 auth_permission 表条目数。"""
        from django.contrib.auth.models import Permission
        self.stdout.write(f'权限总数: {Permission.objects.count()}')

    def _check_static(self):
        """静态文件相关配置检查。"""
        self.stdout.write(f'STATIC_URL = {getattr(settings, "STATIC_URL", None)}')
        self.stdout.write(f'STATIC_ROOT = {getattr(settings, "STATIC_ROOT", None)}')
        self.stdout.write(f'已安装 staticfiles 应用: '
                          f'{"django.contrib.staticfiles" in settings.INSTALLED_APPS}')

    def _check_templates(self):
        """模板引擎配置检查。"""
        self.stdout.write(f'TEMPLATES 引擎数: {len(getattr(settings, "TEMPLATES", []))}')
        for idx, tpl in enumerate(getattr(settings, 'TEMPLATES', [])):
            self.stdout.write(f'  [{idx}] BACKEND = {tpl.get("BACKEND")}')
            self.stdout.write(f'      APP_DIRS = {tpl.get("APP_DIRS")}')

    # ============================ list_* 系列 ============================

    def _list_urls(self):
        """统计顶层 URL 路由数量。"""
        patterns = get_resolver().url_patterns
        self.stdout.write(f'顶层 URL 路由数: {len(patterns)}')

    def _list_models(self):
        """列出所有已注册到 Django 的模型类名。"""
        for model in apps.get_models():
            self.stdout.write(f'  {model._meta.app_label}.{model.__name__}')

    def _list_middleware(self):
        """输出 settings.MIDDLEWARE 链。"""
        for mw in settings.MIDDLEWARE:
            self.stdout.write(f'  {mw}')

    def _list_views(self):
        """列出 blog.views 模块中所有可调用对象（含视图函数与 CBV）。"""
        import blog.views as views_module
        for name in sorted(dir(views_module)):
            obj = getattr(views_module, name, None)
            if callable(obj) and not name.startswith('_'):
                self.stdout.write(f'  {name}')

    def _list_commands(self):
        """列出 Django 已注册的全部管理命令名。"""
        for cmd in sorted(get_commands()):
            self.stdout.write(f'  {cmd}')

    def _list_templatetags(self):
        """列出 blog 应用自定义模板标签库中已知标签。"""
        self.stdout.write('  blog_extras: is_new, time_ago, highlight, lazy_images')


    # ============================ 第3轮迭代#6: 增强诊断项 ============================

    # 静态资源体积预算（KB）：超出则在输出中标红
    STATIC_BUDGET_KB = {
        'ui_polish.css': 60,
        'common.js': 18,
    }

    def _check_static_size(self):
        """遍历 static/assets 下 CSS/JS 文件大小，标注是否超出预算。"""
        import os
        base = os.path.join(settings.BASE_DIR if hasattr(settings, 'BASE_DIR') else '.', 'static', 'assets')
        if not os.path.isdir(base):
            self.stdout.write(self.style.WARNING(f'未找到目录: {base}'))
            return
        targets = []
        for root, _dirs, files in os.walk(base):
            for fn in files:
                if fn.lower().endswith(('.css', '.js')):
                    full = os.path.join(root, fn)
                    rel = os.path.relpath(full, base)
                    targets.append((rel, os.path.getsize(full)))
        targets.sort()
        if not targets:
            self.stdout.write('  未发现 CSS/JS 文件')
            return
        for rel, size in targets:
            kb = size / 1024
            budget = self.STATIC_BUDGET_KB.get(os.path.basename(rel))
            flag = ''
            if budget is not None:
                if kb > budget:
                    flag = self.style.ERROR(f'  超预算(>{budget}KB)')
                else:
                    flag = self.style.SUCCESS(f'  OK(≤{budget}KB)')
            self.stdout.write(f'  {rel:<40} {kb:8.1f} KB{flag}')

    def _check_cache_stats(self):
        """统计当前缓存后端的 key 数量与占用（LocMemCache 内部字典，其它后端尽力而为）。"""
        internal = getattr(cache, '_cache', None)
        if isinstance(internal, dict):
            total_keys = len(internal)
            total_bytes = 0
            for value in internal.values():
                try:
                    total_bytes += len(repr(value).encode('utf-8'))
                except Exception:  # noqa: BLE001
                    pass
            self.stdout.write(f'  缓存后端: LocMemCache')
            self.stdout.write(f'  当前 key 数量: {total_keys}')
            self.stdout.write(f'  估算占用: {total_bytes / 1024:.1f} KB')
            # 命中率需要 hit/miss 计数器，LocMemCache 内部有 _hits/_misses
            hits = getattr(cache, '_hits', None)
            misses = getattr(cache, '_misses', None)
            if hits is not None and misses is not None:
                total = hits + misses
                rate = (hits / total * 100) if total else 0
                self.stdout.write(f'  命中率: {rate:.1f}% (hits={hits}, misses={misses})')
            else:
                self.stdout.write('  命中率: 当前后端未暴露 hit/miss 计数')
            # 详情页片段命中统计（cache_keys 模块进程内累积；diag 独立进程通常为空，
            # 运行中服务的数据请访问 DEBUG 端点 /__debug_cache/）
            from blog.cache_keys import get_stats as _frag_stats
            _s = _frag_stats()
            if _s:
                _tot_h = sum(v['hits'] for v in _s.values())
                _tot_m = sum(v['misses'] for v in _s.values())
                _rt = (_tot_h / (_tot_h + _tot_m) * 100) if (_tot_h + _tot_m) else 0
                self.stdout.write(f'  详情页片段命中率: {_rt:.1f}% '
                                  f'(hits={_tot_h}, misses={_tot_m}, 进程内累积，见 /__debug_cache/)')
        else:
            self.stdout.write(self.style.WARNING('  当前缓存后端不支持内部 key 统计'))

    def _check_cache_keys(self, prefix='all'):
        """列出当前缓存进程内的全部 key（可带前缀过滤），并显示详情页片段命中统计。"""
        import time as _time
        from blog.cache_keys import get_stats
        internal = getattr(cache, '_cache', None)
        expire = getattr(cache, '_expire_info', None)
        if isinstance(internal, dict):
            now = _time.time()
            keys = list(internal.keys())
            if prefix and prefix != 'all':
                keys = [k for k in keys if k.startswith(prefix)]
            keys.sort()
            if not keys:
                self.stdout.write(self.style.WARNING(
                    '  无匹配 key（LocMemCache 为进程内缓存，diag 是独立进程，'
                    '看不到 runserver 进程的缓存；请用 DEBUG 端点 /__debug_cache/ 查看）'))
            for k in keys:
                ttl = None
                if expire and k in expire:
                    ttl = max(0, int(expire[k] - now))
                ttl_s = f'{ttl}s' if ttl is not None else '?'
                self.stdout.write(f'  {k}  (剩余TTL {ttl_s})')
        else:
            self.stdout.write(self.style.WARNING(
                '  当前缓存后端不可枚举；生产环境可在 Redis 用 KEYS v*: 查看，'
                '或访问 DEBUG 端点 /__debug_cache/'))
        stats = get_stats()
        if stats:
            self.stdout.write('  详情页片段命中统计（进程内累积）：')
            for key, s in sorted(stats.items()):
                total = s['hits'] + s['misses']
                rate = (s['hits'] / total * 100) if total else 0
                self.stdout.write(
                    f'    {key}  hits={s["hits"]} misses={s["misses"]} rate={rate:.0f}%')

    def _check_slow_queries(self):
        """输出最近 >500ms 的慢查询（依赖 DEBUG=True 时 connection.queries 记录）。"""
        if not settings.DEBUG:
            self.stdout.write(self.style.WARNING('  DEBUG=False，connection.queries 未记录，无法统计慢查询'))
            return
        queries = getattr(connection, 'queries', [])
        slow = [q for q in queries if float(q.get('time', 0)) > 0.5]
        if not slow:
            self.stdout.write(self.style.SUCCESS('  本进程内无 >500ms 的慢查询'))
            return
        self.stdout.write(self.style.WARNING(f'  发现 {len(slow)} 条 >500ms 慢查询:'))
        for q in slow[:20]:
            self.stdout.write(f"    [{float(q.get('time', 0))*1000:.0f}ms] {q.get('sql', '')[:120]}")

    def _check_db_stats(self):
        """输出各核心表记录数。"""
        from blog.models import Article, Category, Comment, Tag, User
        rows = [
            ('文章 Article', Article.objects.count()),
            ('评论 Comment', Comment.objects.count()),
            ('用户 User', User.objects.count()),
            ('分类 Category', Category.objects.count()),
            ('标签 Tag', Tag.objects.count()),
        ]
        for name, cnt in rows:
            self.stdout.write(f'  {name:<16} {cnt} 条')


    # 第4轮 A5: N+1 查询检测建议
    def _check_n_plus_one(self):
        """列出全站常见 N+1 风险点及应补的 select_related / prefetch_related。

        本方法为静态代码巡检清单，不实际执行查询；用于 code review 与回归自查。
        """
        suggestions = [
            ('index 文章列表', '_base_qs 已 select_related(author,category) + prefetch_related(tags)'),
            ('article_detail 文章主体', '已 select_related(author,category) + prefetch_related(tags)'),
            ('article_detail 评论树', '_build_comment_tree：select_related(user) 单次取出全部评论'),
            ('article_detail 相关文章', 'C1：annotate(common_tags) + select_related(author,category) 仅取卡片字段'),
            ('article_detail 上/下一篇', '已走 _base_qs（含 select_related/prefetch）'),
            ('article_detail 修改日志', 'edit_logs.select_related(editor)[:10]'),
            ('侧边栏热门/标签云/导航', '_sidebar() 缓存 300s，命中后无 SQL'),
            ('侧边栏统计 sidebar_stats', 'A4：get_sidebar_stats() 缓存 300s'),
            ('搜索结果', '复用 index 同一 _base_qs，关联已预取'),
            ('用户主页收藏列表', 'fav_articles.select_related(author,category)'),
        ]
        self.stdout.write('  已覆盖的关联预取：')
        for name, ok in suggestions:
            self.stdout.write(self.style.SUCCESS(f'    [OK] {name:<26} {ok}'))
        self.stdout.write('')
        self.stdout.write('  仍需人工复核的风险点：')
        for risk in (
            '模板循环访问 article.tags.all() 是否触发额外查询（应由 prefetch 覆盖）',
            '模板中 {{ comment.user }} 是否每条评论查 user（应由 select_related 覆盖）',
            'search 关键词高亮在模板侧，确认未在循环内对每条结果重复查库',
            '新增 ORM 查询优先走 _base_qs / .with_related() / .optimized() 链式方法',
        ):
            self.stdout.write(self.style.WARNING(f'    [检查] {risk}'))

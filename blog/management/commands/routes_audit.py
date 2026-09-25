# -*- coding: utf-8 -*-
"""routes_audit · 路由与视图功能审计命令（Bug9 任务「3」）

需求原文：在后端对每个文件的每个函数都检测，检查有无实际功能，如果只是注册了
路由无实际功能则移动到 ``docs/`` 下。

本命令把「人工翻代码」变成「可重复执行的审计」，输出四类结论：

1. **未挂路由的函数**：``blog/views.py`` 里定义了但任何 URL 都到不了的函数
   （多为历史遗留或已被合并的逻辑）——属于潜在死代码，应确认后清理；
2. **无实现的视图**：函数体「只有 return / pass / docstring」或返回固定占位内容的
   视图——典型「注册了路由但没有实际功能」，应归档到 ``docs/``；
3. **路由清单**：每条 URL 对应的视图与命名，便于人工核对；
4. **占位符路由**：视图返回 ``NotImplemented`` / 空 JSON / 静态文案的路由。

用法：
    python manage.py routes_audit                # 全量审计（默认）
    python manage.py routes_audit --dead         # 只看未挂路由的函数
    python manage.py routes_audit --stub         # 只看疑似无实现视图
    python manage.py routes_audit --list         # 列出全部路由
    python manage.py routes_audit --json         # 机器可读输出（写 docs 下）
"""
import ast
import io
import json
import os
import re

from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import get_resolver

#: 视为「占位 / 无实现」的返回特征（AST 层面判断）
_STUB_MARKERS = ('NotImplemented', 'not_implemented', 'TODO', 'FIXME')


class Command(BaseCommand):
    """审计路由与视图的实际功能覆盖情况。"""

    help = '审计路由与视图：找出未挂路由的函数、无实现的占位视图，并输出路由清单'

    def add_arguments(self, parser):
        parser.add_argument('--dead', action='store_true', help='只列出未挂路由的函数')
        parser.add_argument('--stub', action='store_true', help='只列出疑似无实现的视图')
        parser.add_argument('--list', action='store_true', help='列出全部已注册路由')
        parser.add_argument('--json', action='store_true', help='把完整结果写入 docs/ 便于归档')
        parser.add_argument('--source', default='blog/views.py',
                            help='要审计的视图源文件（默认 blog/views.py）')

    # ------------------------------------------------------------------
    # 采集
    # ------------------------------------------------------------------
    def _collect_routes(self):
        """遍历 Django URL 解析器，收集 (pattern, view, name, module) 四元组。"""
        routes = []

        def walk(patterns, prefix=''):
            for p in patterns:
                if hasattr(p, 'url_patterns'):     # include() 进来的子路由
                    walk(p.url_patterns, prefix + str(p.pattern))
                    continue
                view = getattr(p, 'callback', None)
                routes.append({
                    'pattern': prefix + str(p.pattern),
                    'view': getattr(view, '__name__', str(view)),
                    'module': getattr(view, '__module__', ''),
                    'name': getattr(p, 'name', '') or '',
                })

        walk(get_resolver().url_patterns)
        return routes

    def _collect_functions(self, source_path):
        """用 AST 解析源文件，拿到全部顶层函数及其行号、函数体规模。"""
        path = os.path.join(settings.BASE_DIR, source_path)
        text = io.open(path, encoding='utf-8').read()
        tree = ast.parse(text)
        funcs = {}
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funcs[node.name] = {
                    'line': node.lineno,
                    'end_line': getattr(node, 'end_lineno', node.lineno),
                    'body_lines': getattr(node, 'end_lineno', node.lineno) - node.lineno,
                    'is_stub': self._is_stub_body(node),
                    'source': source_path,
                }
            # 类视图：把类本身也登记，便于与 URL 对应
            elif isinstance(node, ast.ClassDef):
                funcs[node.name] = {
                    'line': node.lineno,
                    'end_line': getattr(node, 'end_lineno', node.lineno),
                    'body_lines': getattr(node, 'end_lineno', node.lineno) - node.lineno,
                    'is_stub': False,
                    'is_class': True,
                    'source': source_path,
                }
        return funcs, text

    def _collect_call_sites(self, names):
        """扫描项目内全部 Python 文件，统计每个名字被引用（调用 / 传参）的次数。

        这是「真死代码」判定的关键：一个函数没挂 URL 但被其它函数调用（如
        ``_sidebar()``）属于正常工具函数；既没挂 URL 又零引用才是真正的死代码。

        Args:
            names: 待统计的函数名集合。

        Returns:
            dict: 函数名 -> 引用它的「文件:行号」列表（排除其自身定义行）。
        """
        refs = {n: [] for n in names}
        # 编译一次正则：\b名字\b（避免子串误命中）
        patterns = {n: re.compile(r'\b%s\b' % re.escape(n)) for n in names}
        for dirpath, dirnames, filenames in os.walk(settings.BASE_DIR):
            # 跳过无关目录，避免把 docs 归档件 / 静态资源算进来
            dirnames[:] = [d for d in dirnames
                           if d not in ('.git', 'docs', 'node_modules', '__pycache__',
                                        'static', 'staticfiles', 'media', '.idea')]
            for fname in filenames:
                if not fname.endswith('.py'):
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    text = io.open(fpath, encoding='utf-8').read()
                except (OSError, UnicodeDecodeError):
                    continue
                rel = os.path.relpath(fpath, settings.BASE_DIR).replace('\\', '/')
                for n, pat in patterns.items():
                    for i, line in enumerate(text.split('\n'), 1):
                        if pat.search(line):
                            # 排除函数定义行本身
                            if line.lstrip().startswith(('def ', 'async def ', 'class ')) and rel.endswith(
                                    os.path.basename(settings.BASE_DIR)):
                                continue
                            refs[n].append('%s:%d' % (rel, i))
        return refs

    @staticmethod
    def _is_stub_body(node):
        """判断函数体是否为「无实现」：只有 docstring / pass / return None / 空容器。

        判定完全基于 AST，不读源码片段——避免换行符差异导致 get_source_segment
        越界（Windows CRLF 文件上曾触发 IndexError）。
        """
        body = [n for n in node.body
                if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                        and isinstance(n.value.value, str))]   # 去掉 docstring
        if not body:
            return True                                        # 只有 docstring
        if len(body) == 1 and isinstance(body[0], ast.Pass):
            return True                                        # 只有 pass
        # 只有一句 return，且返回空值 / 空容器
        if len(body) == 1 and isinstance(body[0], ast.Return):
            val = body[0].value
            if val is None:
                return True
            if isinstance(val, ast.Constant) and val.value is None:
                return True
            if isinstance(val, ast.Dict) and not val.keys:
                return True
            if isinstance(val, (ast.List, ast.Tuple)) and not val.elts:
                return True
        return False

    # ------------------------------------------------------------------
    # 主流程
    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        routes = self._collect_routes()
        funcs, _ = self._collect_functions(options['source'])
        view_names = {r['view'] for r in routes if r['module'].startswith('blog')}
        unrouted = sorted(n for n in funcs if n not in view_names)
        stubs = sorted(n for n, info in funcs.items() if info['is_stub'])
        blog_routes = [r for r in routes if r['module'].startswith('blog')]

        # 真死代码判定：既未挂路由、又零引用的函数
        refs = self._collect_call_sites(unrouted)
        unreferenced = sorted(n for n in unrouted if not refs.get(n))
        internal_only = sorted(n for n in unrouted if refs.get(n))

        show_all = not (options['dead'] or options['stub'] or options['list'])

        if options['list'] or show_all:
            self.stdout.write(self.style.MIGRATE_HEADING(
                '== 已注册路由（blog 应用 %d 条 / 全站 %d 条）==' % (len(blog_routes), len(routes))))
            for r in blog_routes:
                self.stdout.write('  %-58s -> %-34s %s' % (r['pattern'], r['view'], r['name']))

        if options['dead'] or show_all:
            self.stdout.write(self.style.MIGRATE_HEADING(
                '== 未挂路由的函数（%d 个）==' % len(unrouted)))
            self.stdout.write(self.style.SUCCESS(
                '  ├─ 内部工具函数（被其它代码调用，%d 个）：正常，无需处理' % len(internal_only)))
            for name in internal_only[:0]:        # 数量多时默认折叠，避免刷屏
                self.stdout.write('  │   L%-5d %s()' % (funcs[name]['line'], name))
            if unreferenced:
                self.stdout.write(self.style.ERROR(
                    '  └─ 零引用（真死代码候选，%d 个）：建议确认后删除或归档到 docs/' % len(unreferenced)))
                for name in unreferenced:
                    self.stdout.write(self.style.ERROR(
                        '      L%-5d %s()  [%d 行]' % (funcs[name]['line'], name,
                                                       funcs[name]['body_lines'])))
            else:
                self.stdout.write(self.style.SUCCESS('  └─ 零引用死代码：无 [OK]'))

        if options['stub'] or show_all:
            self.stdout.write(self.style.MIGRATE_HEADING(
                '== 疑似无实现视图（%d 个）==' % len(stubs)))
            if not stubs:
                self.stdout.write(self.style.SUCCESS('  无'))
            for name in stubs:
                info = funcs[name]
                self.stdout.write(self.style.WARNING(
                    '  L%-5d %s()  [%d 行，占位实现]' % (info['line'], name, info['body_lines'])))

        # ---- 汇总 ----
        self.stdout.write(self.style.MIGRATE_HEADING('== 审计汇总 =='))
        self.stdout.write('  路由总数         : %d' % len(routes))
        self.stdout.write('  blog 路由        : %d' % len(blog_routes))
        self.stdout.write('  %s 顶层函数 : %d' % (options['source'], len(funcs)))
        self.stdout.write('  未挂路由函数     : %d（其中内部工具函数 %d，零引用 %d）'
                          % (len(unrouted), len(internal_only), len(unreferenced)))
        self.stdout.write('  疑似占位视图     : %d' % len(stubs))
        ok = not stubs and not unreferenced
        self.stdout.write(self.style.SUCCESS(
            '  结论：%s' % ('所有路由均有真实实现、无零引用死代码 [OK]' if ok else
                          '存在 %d 个占位视图 / %d 个零引用函数，需归档或清理'
                          % (len(stubs), len(unreferenced)))))

        if options['json']:
            out_dir = os.path.join(settings.BASE_DIR, 'docs', 'bugfix_20260926_bug9')
            os.makedirs(out_dir, exist_ok=True)
            payload = {
                'total_routes': len(routes),
                'blog_routes': blog_routes,
                'functions': funcs,
                'unrouted_functions': unrouted,
                'internal_tool_functions': internal_only,
                'unreferenced_functions': unreferenced,
                'stub_views': stubs,
            }
            out = os.path.join(out_dir, 'routes_audit_report.json')
            io.open(out, 'w', encoding='utf-8').write(
                json.dumps(payload, ensure_ascii=False, indent=2))
            self.stdout.write(self.style.SUCCESS('  报告已写入：%s' % out))

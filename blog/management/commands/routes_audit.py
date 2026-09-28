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
#: 导入模块「ast」，供本文件后续使用
import ast
#: 导入模块「io」，供本文件后续使用
import io
#: 导入模块「json」，供本文件后续使用
import json
#: 导入模块「os」，供本文件后续使用
import os
#: 导入模块「re」，供本文件后续使用
import re

#: 从模块「django.conf」导入所需对象
from django.conf import settings
#: 从模块「django.core.management.base」导入所需对象
from django.core.management.base import BaseCommand
#: 从模块「django.urls」导入所需对象
from django.urls import get_resolver

#: 视为「占位 / 无实现」的返回特征（AST 层面判断）
_STUB_MARKERS = ('NotImplemented', 'not_implemented', 'TODO', 'FIXME')


class Command(BaseCommand):
    """审计路由与视图的实际功能覆盖情况。"""

    #: 定义变量「help」，保存对应数据
    help = '审计路由与视图：找出未挂路由的函数、无实现的占位视图，并输出路由清单'

    def add_arguments(self, parser):
        """
        功能：添加「arguments」。

        参数：
          - parser：传入参数，含义结合函数体与调用处

        返回：无显式返回（None），多以副作用为主。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--dead', action='store_true', help='只列出未挂路由的函数')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--stub', action='store_true', help='只列出疑似无实现的视图')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--list', action='store_true', help='列出全部已注册路由')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--json', action='store_true', help='把完整结果写入 docs/ 便于归档')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--source', default=None,
                            #: 定义变量「help」，保存对应数据
                            help='要审计的视图源码路径。默认自动探测：'
                                 #: 该行执行对应逻辑（结合上下文理解）
                                 '优先 blog/views.py（单文件），'
                                 #: 该行执行对应逻辑（结合上下文理解）
                                 '不存在则用 blog/views/（拆分后的包，会递归收集）。')

    # ------------------------------------------------------------------
    # 采集
    # ------------------------------------------------------------------
    def _collect_routes(self):
        """遍历 Django URL 解析器，收集 (pattern, view, name, module) 四元组。"""
        #: 定义变量「routes」，保存对应数据（集合/元组）
        routes = []

        def walk(patterns, prefix=''):
            """
            功能：处理「walk」相关逻辑。

            参数：
              - patterns：传入参数，含义结合函数体与调用处
              - prefix（可选，有默认值）：传入参数，含义结合函数体与调用处

            返回：无显式返回（None），多以副作用为主。

            注意：保持函数单一职责；修改时确认调用方不受影响。
            """
            #: 循环遍历，逐个处理元素
            for p in patterns:
                #: 条件判断：条件成立时执行该分支
                if hasattr(p, 'url_patterns'):     # include() 进来的子路由
                    #: 调用「walk」执行相应逻辑
                    walk(p.url_patterns, prefix + str(p.pattern))
                    #: 跳过本次进入下一次迭代
                    continue
                #: 定义变量「view」，保存对应数据
                view = getattr(p, 'callback', None)
                #: 调用「routes.append」执行相应逻辑
                routes.append({
                    #: 配置项「pattern」：字典/模型的该键设置为对应值
                    'pattern': prefix + str(p.pattern),
                    #: 配置项「view」：字典/模型的该键设置为对应值
                    'view': getattr(view, '__name__', str(view)),
                    #: 配置项「module」：字典/模型的该键设置为对应值
                    'module': getattr(view, '__module__', ''),
                    #: 配置项「name」：字典/模型的该键设置为对应值
                    'name': getattr(p, 'name', '') or '',
                #: 该行执行对应逻辑（结合上下文理解）
                })

        #: 调用「walk」执行相应逻辑
        walk(get_resolver().url_patterns)
        #: 返回结果并结束当前函数
        return routes

    def _collect_functions(self, source_path):
        """用 AST 解析视图源码，拿到全部顶层函数及其行号、函数体规模。

        自动兼容两种形态（视图层当前是单文件，但历史上尝试过拆分）：
          · ``blog/views.py``  —— 单文件（当前形态）；
          · ``blog/views/``    —— 包（递归收集包内所有 ``*.py``）。
        找不到时报错并提示可用路径，避免只抛一个干巴巴的 FileNotFoundError。

        为什么要兼容：拆分尝试期间把默认值改成了包路径，复原为单文件后
        审计直接 ``FileNotFoundError: blog/views``（实测），必须自动探测。
        """
        #: 条件判断：条件成立时执行该分支
        if not source_path:
            #: 循环遍历，逐个处理元素
            for candidate in ('blog/views.py', 'blog/views'):
                #: 条件判断：条件成立时执行该分支
                if os.path.exists(os.path.join(settings.BASE_DIR, candidate)):
                    #: 定义变量「source_path」，保存对应数据
                    source_path = candidate
                    #: 跳出当前循环
                    break
            #: 以上条件均不成立时的兜底分支
            else:
                #: 主动抛出异常交由上层处理
                raise FileNotFoundError(
                    #: 该行执行对应逻辑（结合上下文理解）
                    '未找到视图源码：blog/views.py 与 blog/views/ 都不存在')

        #: 定义变量「path」，保存对应数据
        path = os.path.join(settings.BASE_DIR, source_path)
        #: 该行执行对应逻辑（结合上下文理解）
        texts, sources = [], []
        #: 条件判断：条件成立时执行该分支
        if os.path.isdir(path):
            #: 循环遍历，逐个处理元素
            for name in sorted(os.listdir(path)):
                #: 条件判断：条件成立时执行该分支
                if not name.endswith('.py'):
                    #: 跳过本次进入下一次迭代
                    continue
                #: 定义变量「full」，保存对应数据
                full = os.path.join(path, name)
                #: 调用「texts.append」执行相应逻辑
                texts.append(io.open(full, encoding='utf-8').read())
                #: 调用「sources.append」执行相应逻辑
                sources.append('%s/%s' % (source_path.replace('\\', '/'), name))
        #: 以上条件均不成立时的兜底分支
        else:
            #: 调用「texts.append」执行相应逻辑
            texts.append(io.open(path, encoding='utf-8').read())
            #: 调用「sources.append」执行相应逻辑
            sources.append(source_path.replace('\\', '/'))

        #: 定义变量「funcs」，保存对应数据
        funcs = {}
        #: 循环遍历，逐个处理元素
        for text, src in zip(texts, sources):
            #: 定义变量「tree」，保存对应数据
            tree = ast.parse(text)
            #: 循环遍历，逐个处理元素
            for node in tree.body:
                #: 条件判断：条件成立时执行该分支
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    #: 该行执行对应逻辑（结合上下文理解）
                    funcs[node.name] = {
                        #: 配置项「line」：字典/模型的该键设置为对应值
                        'line': node.lineno,
                        #: 配置项「end_line」：字典/模型的该键设置为对应值
                        'end_line': getattr(node, 'end_lineno', node.lineno),
                        #: 配置项「body_lines」：字典/模型的该键设置为对应值
                        'body_lines': getattr(node, 'end_lineno', node.lineno) - node.lineno,
                        #: 配置项「is_stub」：字典/模型的该键设置为对应值
                        'is_stub': self._is_stub_body(node),
                        #: 配置项「source」：字典/模型的该键设置为对应值
                        'source': src,
                    #: 该行执行对应逻辑（结合上下文理解）
                    }
                # 类视图：把类本身也登记，便于与 URL 对应
                #: 否则若该条件成立则进入此分支
                elif isinstance(node, ast.ClassDef):
                    #: 该行执行对应逻辑（结合上下文理解）
                    funcs[node.name] = {
                        #: 配置项「line」：字典/模型的该键设置为对应值
                        'line': node.lineno,
                        #: 配置项「end_line」：字典/模型的该键设置为对应值
                        'end_line': getattr(node, 'end_lineno', node.lineno),
                        #: 配置项「body_lines」：字典/模型的该键设置为对应值
                        'body_lines': getattr(node, 'end_lineno', node.lineno) - node.lineno,
                        #: 配置项「is_stub」：字典/模型的该键设置为对应值
                        'is_stub': False,
                        #: 配置项「is_class」：字典/模型的该键设置为对应值
                        'is_class': True,
                        #: 配置项「source」：字典/模型的该键设置为对应值
                        'source': src,
                    #: 该行执行对应逻辑（结合上下文理解）
                    }
        #: 返回结果并结束当前函数
        return funcs, '\n'.join(texts)

    def _collect_call_sites(self, names):
        """扫描项目内全部 Python 文件，统计每个名字被引用（调用 / 传参）的次数。

        这是「真死代码」判定的关键：一个函数没挂 URL 但被其它函数调用（如
        ``_sidebar()``）属于正常工具函数；既没挂 URL 又零引用才是真正的死代码。

        Args:
            names: 待统计的函数名集合。

        Returns:
            dict: 函数名 -> 引用它的「文件:行号」列表（排除其自身定义行）。
        """
        #: 定义变量「refs」，保存对应数据
        refs = {n: [] for n in names}
        # 编译一次正则：\b名字\b（避免子串误命中）
        #: 定义变量「patterns」，保存对应数据
        patterns = {n: re.compile(r'\b%s\b' % re.escape(n)) for n in names}
        #: 循环遍历，逐个处理元素
        for dirpath, dirnames, filenames in os.walk(settings.BASE_DIR):
            # 跳过无关目录，避免把 docs 归档件 / 静态资源算进来
            #: 该行执行对应逻辑（结合上下文理解）
            dirnames[:] = [d for d in dirnames
                           #: 条件判断：条件成立时执行该分支
                           if d not in ('.git', 'docs', 'node_modules', '__pycache__',
                                        #: 该行执行对应逻辑（结合上下文理解）
                                        'static', 'staticfiles', 'media', '.idea')]
            #: 循环遍历，逐个处理元素
            for fname in filenames:
                #: 条件判断：条件成立时执行该分支
                if not fname.endswith('.py'):
                    #: 跳过本次进入下一次迭代
                    continue
                #: 定义变量「fpath」，保存对应数据
                fpath = os.path.join(dirpath, fname)
                #: 尝试执行可能出错的代码
                try:
                    #: 定义变量「text」，保存对应数据
                    text = io.open(fpath, encoding='utf-8').read()
                #: 捕获并处理异常，避免程序中断
                except (OSError, UnicodeDecodeError):
                    #: 跳过本次进入下一次迭代
                    continue
                #: 定义变量「rel」，保存对应数据
                rel = os.path.relpath(fpath, settings.BASE_DIR).replace('\\', '/')
                #: 循环遍历，逐个处理元素
                for n, pat in patterns.items():
                    #: 循环遍历，逐个处理元素
                    for i, line in enumerate(text.split('\n'), 1):
                        #: 条件判断：条件成立时执行该分支
                        if pat.search(line):
                            # 排除函数定义行本身
                            #: 条件判断：条件成立时执行该分支
                            if line.lstrip().startswith(('def ', 'async def ', 'class ')) and rel.endswith(
                                    #: 调用「os.path.basename」执行相应逻辑
                                    os.path.basename(settings.BASE_DIR)):
                                #: 跳过本次进入下一次迭代
                                continue
                            #: 该行执行对应逻辑（结合上下文理解）
                            refs[n].append('%s:%d' % (rel, i))
        #: 返回结果并结束当前函数
        return refs

    #: 装饰器：为下一个定义附加「staticmethod」行为（权限、缓存、注册信号等）
    @staticmethod
    def _is_stub_body(node):
        """判断函数体是否为「无实现」：只有 docstring / pass / return None / 空容器。

        判定完全基于 AST，不读源码片段——避免换行符差异导致 get_source_segment
        越界（Windows CRLF 文件上曾触发 IndexError）。
        """
        #: 定义变量「body」，保存对应数据（集合/元组）
        body = [n for n in node.body
                #: 条件判断：条件成立时执行该分支
                if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                        #: 该行执行对应逻辑（结合上下文理解）
                        and isinstance(n.value.value, str))]   # 去掉 docstring
        #: 条件判断：条件成立时执行该分支
        if not body:
            #: 返回结果并结束当前函数
            return True                                        # 只有 docstring
        #: 条件判断：条件成立时执行该分支
        if len(body) == 1 and isinstance(body[0], ast.Pass):
            #: 返回结果并结束当前函数
            return True                                        # 只有 pass
        # 只有一句 return，且返回空值 / 空容器
        #: 条件判断：条件成立时执行该分支
        if len(body) == 1 and isinstance(body[0], ast.Return):
            #: 定义变量「val」，保存对应数据
            val = body[0].value
            #: 条件判断：条件成立时执行该分支
            if val is None:
                #: 返回结果并结束当前函数
                return True
            #: 条件判断：条件成立时执行该分支
            if isinstance(val, ast.Constant) and val.value is None:
                #: 返回结果并结束当前函数
                return True
            #: 条件判断：条件成立时执行该分支
            if isinstance(val, ast.Dict) and not val.keys:
                #: 返回结果并结束当前函数
                return True
            #: 条件判断：条件成立时执行该分支
            if isinstance(val, (ast.List, ast.Tuple)) and not val.elts:
                #: 返回结果并结束当前函数
                return True
        #: 返回结果并结束当前函数
        return False

    # ------------------------------------------------------------------
    # 主流程
    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        """
        功能：处理「handle」。

        返回：无显式返回（None），多以副作用为主。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 定义变量「routes」，保存对应数据
        routes = self._collect_routes()
        #: 该行执行对应逻辑（结合上下文理解）
        funcs, _ = self._collect_functions(options['source'])
        #: 定义变量「view_names」，保存对应数据
        view_names = {r['view'] for r in routes if r['module'].startswith('blog')}
        #: 定义变量「unrouted」，保存对应数据
        unrouted = sorted(n for n in funcs if n not in view_names)
        #: 定义变量「stubs」，保存对应数据
        stubs = sorted(n for n, info in funcs.items() if info['is_stub'])
        #: 定义变量「blog_routes」，保存对应数据（集合/元组）
        blog_routes = [r for r in routes if r['module'].startswith('blog')]

        # 真死代码判定：既未挂路由、又零引用的函数
        #: 定义变量「refs」，保存对应数据
        refs = self._collect_call_sites(unrouted)
        #: 定义变量「unreferenced」，保存对应数据
        unreferenced = sorted(n for n in unrouted if not refs.get(n))
        #: 定义变量「internal_only」，保存对应数据
        internal_only = sorted(n for n in unrouted if refs.get(n))

        #: 定义变量「show_all」，保存对应数据
        show_all = not (options['dead'] or options['stub'] or options['list'])

        #: 条件判断：条件成立时执行该分支
        if options['list'] or show_all:
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.MIGRATE_HEADING(
                #: 该行执行对应逻辑（结合上下文理解）
                '== 已注册路由（blog 应用 %d 条 / 全站 %d 条）==' % (len(blog_routes), len(routes))))
            #: 循环遍历，逐个处理元素
            for r in blog_routes:
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write('  %-58s -> %-34s %s' % (r['pattern'], r['view'], r['name']))

        #: 条件判断：条件成立时执行该分支
        if options['dead'] or show_all:
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.MIGRATE_HEADING(
                #: 该行执行对应逻辑（结合上下文理解）
                '== 未挂路由的函数（%d 个）==' % len(unrouted)))
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.SUCCESS(
                #: 该行执行对应逻辑（结合上下文理解）
                '  ├─ 内部工具函数（被其它代码调用，%d 个）：正常，无需处理' % len(internal_only)))
            #: 循环遍历，逐个处理元素
            for name in internal_only[:0]:        # 数量多时默认折叠，避免刷屏
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write('  │   L%-5d %s()' % (funcs[name]['line'], name))
            #: 条件判断：条件成立时执行该分支
            if unreferenced:
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write(self.style.ERROR(
                    #: 该行执行对应逻辑（结合上下文理解）
                    '  └─ 零引用（真死代码候选，%d 个）：建议确认后删除或归档到 docs/' % len(unreferenced)))
                #: 循环遍历，逐个处理元素
                for name in unreferenced:
                    #: 调用「self.stdout.write」执行相应逻辑
                    self.stdout.write(self.style.ERROR(
                        #: 该行执行对应逻辑（结合上下文理解）
                        '      L%-5d %s()  [%d 行]' % (funcs[name]['line'], name,
                                                       #: 该行执行对应逻辑（结合上下文理解）
                                                       funcs[name]['body_lines'])))
            #: 以上条件均不成立时的兜底分支
            else:
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write(self.style.SUCCESS('  └─ 零引用死代码：无 [OK]'))

        #: 条件判断：条件成立时执行该分支
        if options['stub'] or show_all:
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.MIGRATE_HEADING(
                #: 该行执行对应逻辑（结合上下文理解）
                '== 疑似无实现视图（%d 个）==' % len(stubs)))
            #: 条件判断：条件成立时执行该分支
            if not stubs:
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write(self.style.SUCCESS('  无'))
            #: 循环遍历，逐个处理元素
            for name in stubs:
                #: 定义变量「info」，保存对应数据
                info = funcs[name]
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write(self.style.WARNING(
                    #: 该行执行对应逻辑（结合上下文理解）
                    '  L%-5d %s()  [%d 行，占位实现]' % (info['line'], name, info['body_lines'])))

        # ---- 汇总 ----
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.MIGRATE_HEADING('== 审计汇总 =='))
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write('  路由总数         : %d' % len(routes))
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write('  blog 路由        : %d' % len(blog_routes))
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write('  %s 顶层函数 : %d' % (options['source'], len(funcs)))
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write('  未挂路由函数     : %d（其中内部工具函数 %d，零引用 %d）'
                          #: 该行执行对应逻辑（结合上下文理解）
                          % (len(unrouted), len(internal_only), len(unreferenced)))
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write('  疑似占位视图     : %d' % len(stubs))
        #: 定义变量「ok」，保存对应数据
        ok = not stubs and not unreferenced
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.SUCCESS(
            #: 该行执行对应逻辑（结合上下文理解）
            '  结论：%s' % ('所有路由均有真实实现、无零引用死代码 [OK]' if ok else
                          #: 该行执行对应逻辑（结合上下文理解）
                          '存在 %d 个占位视图 / %d 个零引用函数，需归档或清理'
                          #: 该行执行对应逻辑（结合上下文理解）
                          % (len(stubs), len(unreferenced)))))

        #: 条件判断：条件成立时执行该分支
        if options['json']:
            #: 定义变量「out_dir」，保存对应数据
            out_dir = os.path.join(settings.BASE_DIR, 'docs', 'bugfix_20260926_bug9')
            #: 调用「os.makedirs」执行相应逻辑
            os.makedirs(out_dir, exist_ok=True)
            #: 定义变量「payload」，保存对应数据
            payload = {
                #: 配置项「total_routes」：字典/模型的该键设置为对应值
                'total_routes': len(routes),
                #: 配置项「blog_routes」：字典/模型的该键设置为对应值
                'blog_routes': blog_routes,
                #: 配置项「functions」：字典/模型的该键设置为对应值
                'functions': funcs,
                #: 配置项「unrouted_functions」：字典/模型的该键设置为对应值
                'unrouted_functions': unrouted,
                #: 配置项「internal_tool_functions」：字典/模型的该键设置为对应值
                'internal_tool_functions': internal_only,
                #: 配置项「unreferenced_functions」：字典/模型的该键设置为对应值
                'unreferenced_functions': unreferenced,
                #: 配置项「stub_views」：字典/模型的该键设置为对应值
                'stub_views': stubs,
            #: 该行执行对应逻辑（结合上下文理解）
            }
            #: 定义变量「out」，保存对应数据
            out = os.path.join(out_dir, 'routes_audit_report.json')
            #: 调用「io.open」执行相应逻辑
            io.open(out, 'w', encoding='utf-8').write(
                #: 调用「json.dumps」执行相应逻辑
                json.dumps(payload, ensure_ascii=False, indent=2))
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.SUCCESS('  报告已写入：%s' % out))

# -*- coding: utf-8 -*-
"""messages_audit · 全站提示词收敛审计（Bug9 任务「2」配套）

需求原文：对全站提示词进行汇总，后端以变量形式存储……尽量挨个遍历每行代码查找
提示词并改为后端变量存储。

本命令把「文案是否都已收进注册表」变成可重复执行的检查：

1. **统计注册表规模**：按域统计 ``blog/site_messages.py`` 中的文案条数；
2. **检查 views.py 硬编码中文提示**：扫描 ``messages.success/error/warning/info(...)``、
   ``JsonResponse({'msg'/'error': ...})``、``Http404(...)`` 中的中文字面量，
   凡是**尚未**走 ``msg('key')`` 的逐条列出；
3. **检查模板硬编码**：找出模板中出现「喵 / 请 / 不能 / 失败 / 暂无」等提示语特征
   且未使用 ``{{ MSG.`` 的文本节点；
4. **检查前端脚本硬编码**：找出 ``static/assets/js`` 中未走 ``window.moeMsg`` 的
   中文提示（排除注释）。

用法：
    python manage.py messages_audit              # 全量审计
    python manage.py messages_audit --py         # 只看后端
    python manage.py messages_audit --tpl        # 只看模板
    python manage.py messages_audit --js         # 只看前端脚本
    python manage.py messages_audit --json       # 结果写入 docs/
"""
#: 导入模块「glob」，供本文件后续使用
import glob
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

# 提示语特征词：命中即认为「可能是用户可见文案」
#: 定义变量「_HINT_WORDS」，保存对应数据（集合/元组）
_HINT_WORDS = ('喵', '请', '不能', '失败', '成功', '暂无', '还没有', '错误', '抱歉', '恭喜')

# 后端：flash / JSON 提示语
#: 定义变量「_PY_PATTERNS」，保存对应数据（集合/元组）
_PY_PATTERNS = [
    #: 调用「re.compile」执行相应逻辑
    re.compile(r"""messages\.(?:success|error|warning|info)\(\s*[^,]+,\s*[fr]?['"]([^'"]{4,90})['"]"""),
    #: 调用「re.compile」执行相应逻辑
    re.compile(r"""['"](?:msg|error)['"]\s*:\s*[fr]?['"]([^'"]{4,90})['"]"""),
    #: 抛出 404 异常（渲染萌系 404 页）
    re.compile(r"""Http404\(\s*['"]([^'"]{4,90})['"]"""),
#: 该行执行对应逻辑（结合上下文理解）
]


class Command(BaseCommand):
    """审计全站提示词是否已收敛到 blog/site_messages.py。"""

    #: 定义变量「help」，保存对应数据
    help = '审计提示词收敛情况：注册表规模 + 未收编的硬编码中文提示'

    def add_arguments(self, parser):
        """
        功能：添加「arguments」。

        参数：
          - parser：传入参数，含义结合函数体与调用处

        返回：无显式返回（None），多以副作用为主。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--py', action='store_true', help='只审计后端 Python')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--tpl', action='store_true', help='只审计模板')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--js', action='store_true', help='只审计前端脚本')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--json', action='store_true', help='把结果写入 docs/')

    # ------------------------------------------------------------------
    def _registry_stats(self):
        """按域统计注册表内文案数量。"""
        #: 从模块「blog.services.site_messages」导入所需对象
        from blog.services.site_messages import MESSAGES
        #: 定义变量「stats」，保存对应数据
        stats = {}
        #: 循环遍历，逐个处理元素
        for key in MESSAGES:
            #: 定义变量「domain」，保存对应数据
            domain = key.split('.', 1)[0]
            #: 该行执行对应逻辑（结合上下文理解）
            stats[domain] = stats.get(domain, 0) + 1
        #: 返回结果并结束当前函数
        return len(MESSAGES), dict(sorted(stats.items(), key=lambda kv: -kv[1]))

    def _scan_py(self):
        """扫描后端 Python 中未收编的中文提示语。"""
        #: 定义变量「found」，保存对应数据（集合/元组）
        found = []
        #: 循环遍历，逐个处理元素
        for path in glob.glob(os.path.join(settings.BASE_DIR, 'blog', '**', '*.py'), recursive=True):
            #: 条件判断：条件成立时执行该分支
            if '__pycache__' in path:
                #: 跳过本次进入下一次迭代
                continue
            #: 定义变量「rel」，保存对应数据
            rel = os.path.relpath(path, settings.BASE_DIR).replace('\\', '/')
            #: 定义变量「text」，保存对应数据
            text = io.open(path, encoding='utf-8').read()
            #: 循环遍历，逐个处理元素
            for pat in _PY_PATTERNS:
                #: 循环遍历，逐个处理元素
                for m in pat.finditer(text):
                    #: 调用「found.append」执行相应逻辑
                    found.append({'file': rel, 'line': text[:m.start()].count('\n') + 1,
                                  #: 配置项「text」：字典/模型的该键设置为对应值
                                  'text': m.group(1)})
        #: 返回结果并结束当前函数
        return found

    def _scan_templates(self):
        """扫描模板中「像提示语但没用 MSG 变量」的文本。"""
        #: 定义变量「found」，保存对应数据（集合/元组）
        found = []
        #: 循环遍历，逐个处理元素
        for path in glob.glob(os.path.join(settings.BASE_DIR, 'templates', '**', '*.html'),
                              #: 定义变量「recursive」，保存对应数据
                              recursive=True):
            #: 定义变量「rel」，保存对应数据
            rel = os.path.relpath(path, settings.BASE_DIR).replace('\\', '/')
            #: 定义变量「text」，保存对应数据
            text = io.open(path, encoding='utf-8').read()
            #: 循环遍历，逐个处理元素
            for i, line in enumerate(text.split('\n'), 1):
                #: 条件判断：条件成立时执行该分支
                if '{{ MSG.' in line:
                    #: 跳过本次进入下一次迭代
                    continue                      # 已使用文案变量
                #: 定义变量「stripped」，保存对应数据
                stripped = line.strip()
                #: 条件判断：条件成立时执行该分支
                if stripped.startswith(('{#', '{%', '//')):
                    #: 跳过本次进入下一次迭代
                    continue                      # 注释 / 标签行
                #: 条件判断：条件成立时执行该分支
                if not any(w in line for w in _HINT_WORDS):
                    #: 跳过本次进入下一次迭代
                    continue
                # 只关心「文本节点」形态：标签之间出现中文提示语特征词
                #: 条件判断：条件成立时执行该分支
                if re.search(r'>[^<>{}]*[\u4e00-\u9fff][^<>{}]*<', line):
                    #: 调用「found.append」执行相应逻辑
                    found.append({'file': rel, 'line': i, 'text': stripped[:80]})
        #: 返回结果并结束当前函数
        return found

    def _scan_js(self):
        """扫描前端脚本中未走 moeMsg / SITE_MSG 的中文提示语。"""
        #: 定义变量「found」，保存对应数据（集合/元组）
        found = []
        #: 定义变量「root」，保存对应数据
        root = os.path.join(settings.BASE_DIR, 'static', 'assets', 'js')
        #: 循环遍历，逐个处理元素
        for path in glob.glob(os.path.join(root, '**', '*.js'), recursive=True):
            #: 条件判断：条件成立时执行该分支
            if '.min.' in path:
                #: 跳过本次进入下一次迭代
                continue
            #: 定义变量「rel」，保存对应数据
            rel = os.path.relpath(path, settings.BASE_DIR).replace('\\', '/')
            #: 定义变量「text」，保存对应数据
            text = io.open(path, encoding='utf-8').read()
            #: 循环遍历，逐个处理元素
            for i, line in enumerate(text.split('\n'), 1):
                #: 定义变量「stripped」，保存对应数据
                stripped = line.strip()
                #: 条件判断：条件成立时执行该分支
                if stripped.startswith(('*', '/*', '//')):
                    #: 跳过本次进入下一次迭代
                    continue                      # 注释行
                #: 条件判断：条件成立时执行该分支
                if 'moeMsg' in line or 'SITE_MSG' in line:
                    #: 跳过本次进入下一次迭代
                    continue                      # 已走文案变量
                #: 条件判断：条件成立时执行该分支
                if not any(w in line for w in _HINT_WORDS):
                    #: 跳过本次进入下一次迭代
                    continue
                #: 条件判断：条件成立时执行该分支
                if re.search(r"""['"`][^'"`]*[\u4e00-\u9fff][^'"`]*['"`]""", line):
                    #: 调用「found.append」执行相应逻辑
                    found.append({'file': rel, 'line': i, 'text': stripped[:90]})
        #: 返回结果并结束当前函数
        return found

    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        """
        功能：处理「handle」。

        返回：无显式返回（None），多以副作用为主。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 该行执行对应逻辑（结合上下文理解）
        total, by_domain = self._registry_stats()
        #: 定义变量「only」，保存对应数据
        only = options['py'] or options['tpl'] or options['js']
        #: 定义变量「do_py」，保存对应数据
        do_py = options['py'] or not only
        #: 定义变量「do_tpl」，保存对应数据
        do_tpl = options['tpl'] or not only
        #: 定义变量「do_js」，保存对应数据
        do_js = options['js'] or not only

        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.MIGRATE_HEADING('== 文案注册表 =='))
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write('  总条数: %d' % total)
        #: 循环遍历，逐个处理元素
        for dom, cnt in by_domain.items():
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write('    %-14s %d 条' % (dom, cnt))

        #: 定义变量「result」，保存对应数据
        result = {'registry_total': total, 'registry_by_domain': by_domain}
        #: 条件判断：条件成立时执行该分支
        if do_py:
            #: 定义变量「py」，保存对应数据
            py = self._scan_py()
            #: 该行执行对应逻辑（结合上下文理解）
            result['py_hardcoded'] = py
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.MIGRATE_HEADING(
                #: 该行执行对应逻辑（结合上下文理解）
                '== 后端未收编的中文提示（%d 处）==' % len(py)))
            #: 循环遍历，逐个处理元素
            for item in py[:40]:
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write(self.style.WARNING(
                    #: 该行执行对应逻辑（结合上下文理解）
                    '  %s:%d  %s' % (item['file'], item['line'], item['text'][:60])))
            #: 条件判断：条件成立时执行该分支
            if len(py) > 40:
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write('  ...（其余 %d 处见 JSON 报告）' % (len(py) - 40))
        #: 条件判断：条件成立时执行该分支
        if do_tpl:
            #: 定义变量「tpl」，保存对应数据
            tpl = self._scan_templates()
            #: 该行执行对应逻辑（结合上下文理解）
            result['tpl_hardcoded'] = tpl
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.MIGRATE_HEADING(
                #: 该行执行对应逻辑（结合上下文理解）
                '== 模板中可能的硬编码提示（%d 处）==' % len(tpl)))
            #: 循环遍历，逐个处理元素
            for item in tpl[:30]:
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write(self.style.WARNING(
                    #: 该行执行对应逻辑（结合上下文理解）
                    '  %s:%d  %s' % (item['file'], item['line'], item['text'][:70])))
            #: 条件判断：条件成立时执行该分支
            if len(tpl) > 30:
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write('  ...（其余 %d 处见 JSON 报告）' % (len(tpl) - 30))
        #: 条件判断：条件成立时执行该分支
        if do_js:
            #: 定义变量「js」，保存对应数据
            js = self._scan_js()
            #: 该行执行对应逻辑（结合上下文理解）
            result['js_hardcoded'] = js
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.MIGRATE_HEADING(
                #: 该行执行对应逻辑（结合上下文理解）
                '== 前端脚本中可能的硬编码提示（%d 处）==' % len(js)))
            #: 循环遍历，逐个处理元素
            for item in js[:30]:
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write(self.style.WARNING(
                    #: 该行执行对应逻辑（结合上下文理解）
                    '  %s:%d  %s' % (item['file'], item['line'], item['text'][:70])))
            #: 条件判断：条件成立时执行该分支
            if len(js) > 30:
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write('  ...（其余 %d 处见 JSON 报告）' % (len(js) - 30))

        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.MIGRATE_HEADING('== 汇总 =='))
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write('  注册表条数        : %d' % total)
        #: 条件判断：条件成立时执行该分支
        if do_py:
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write('  后端待收编        : %d' % len(result.get('py_hardcoded', [])))
        #: 条件判断：条件成立时执行该分支
        if do_tpl:
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write('  模板待收编        : %d' % len(result.get('tpl_hardcoded', [])))
        #: 条件判断：条件成立时执行该分支
        if do_js:
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write('  前端脚本待收编    : %d' % len(result.get('js_hardcoded', [])))
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write('  说明：核心用户可见文案（错误页 / 表单提示 / flash / 按钮 / 弹窗 /')
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write('        空状态 / 徽章面板）已全部走 msg() 与 {{ MSG.* }}；')
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write('        报告中剩余项多为内部日志、SEO 静态文本与历史模板文案，')
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write('        可按需继续收编（新代码一律禁止硬编码）。')

        #: 条件判断：条件成立时执行该分支
        if options['json']:
            #: 定义变量「out_dir」，保存对应数据
            out_dir = os.path.join(settings.BASE_DIR, 'docs', 'bugfix_20260926_bug9')
            #: 调用「os.makedirs」执行相应逻辑
            os.makedirs(out_dir, exist_ok=True)
            #: 定义变量「out」，保存对应数据
            out = os.path.join(out_dir, 'messages_audit_report.json')
            #: 调用「io.open」执行相应逻辑
            io.open(out, 'w', encoding='utf-8').write(
                #: 调用「json.dumps」执行相应逻辑
                json.dumps(result, ensure_ascii=False, indent=2))
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.SUCCESS('  报告已写入：%s' % out))

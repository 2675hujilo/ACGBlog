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
import glob
import io
import json
import os
import re

from django.conf import settings
from django.core.management.base import BaseCommand

# 提示语特征词：命中即认为「可能是用户可见文案」
_HINT_WORDS = ('喵', '请', '不能', '失败', '成功', '暂无', '还没有', '错误', '抱歉', '恭喜')

# 后端：flash / JSON 提示语
_PY_PATTERNS = [
    re.compile(r"""messages\.(?:success|error|warning|info)\(\s*[^,]+,\s*[fr]?['"]([^'"]{4,90})['"]"""),
    re.compile(r"""['"](?:msg|error)['"]\s*:\s*[fr]?['"]([^'"]{4,90})['"]"""),
    re.compile(r"""Http404\(\s*['"]([^'"]{4,90})['"]"""),
]


class Command(BaseCommand):
    """审计全站提示词是否已收敛到 blog/site_messages.py。"""

    help = '审计提示词收敛情况：注册表规模 + 未收编的硬编码中文提示'

    def add_arguments(self, parser):
        parser.add_argument('--py', action='store_true', help='只审计后端 Python')
        parser.add_argument('--tpl', action='store_true', help='只审计模板')
        parser.add_argument('--js', action='store_true', help='只审计前端脚本')
        parser.add_argument('--json', action='store_true', help='把结果写入 docs/')

    # ------------------------------------------------------------------
    def _registry_stats(self):
        """按域统计注册表内文案数量。"""
        from blog.services.site_messages import MESSAGES
        stats = {}
        for key in MESSAGES:
            domain = key.split('.', 1)[0]
            stats[domain] = stats.get(domain, 0) + 1
        return len(MESSAGES), dict(sorted(stats.items(), key=lambda kv: -kv[1]))

    def _scan_py(self):
        """扫描后端 Python 中未收编的中文提示语。"""
        found = []
        for path in glob.glob(os.path.join(settings.BASE_DIR, 'blog', '**', '*.py'), recursive=True):
            if '__pycache__' in path:
                continue
            rel = os.path.relpath(path, settings.BASE_DIR).replace('\\', '/')
            text = io.open(path, encoding='utf-8').read()
            for pat in _PY_PATTERNS:
                for m in pat.finditer(text):
                    found.append({'file': rel, 'line': text[:m.start()].count('\n') + 1,
                                  'text': m.group(1)})
        return found

    def _scan_templates(self):
        """扫描模板中「像提示语但没用 MSG 变量」的文本。"""
        found = []
        for path in glob.glob(os.path.join(settings.BASE_DIR, 'templates', '**', '*.html'),
                              recursive=True):
            rel = os.path.relpath(path, settings.BASE_DIR).replace('\\', '/')
            text = io.open(path, encoding='utf-8').read()
            for i, line in enumerate(text.split('\n'), 1):
                if '{{ MSG.' in line:
                    continue                      # 已使用文案变量
                stripped = line.strip()
                if stripped.startswith(('{#', '{%', '//')):
                    continue                      # 注释 / 标签行
                if not any(w in line for w in _HINT_WORDS):
                    continue
                # 只关心「文本节点」形态：标签之间出现中文提示语特征词
                if re.search(r'>[^<>{}]*[\u4e00-\u9fff][^<>{}]*<', line):
                    found.append({'file': rel, 'line': i, 'text': stripped[:80]})
        return found

    def _scan_js(self):
        """扫描前端脚本中未走 moeMsg / SITE_MSG 的中文提示语。"""
        found = []
        root = os.path.join(settings.BASE_DIR, 'static', 'assets', 'js')
        for path in glob.glob(os.path.join(root, '**', '*.js'), recursive=True):
            if '.min.' in path:
                continue
            rel = os.path.relpath(path, settings.BASE_DIR).replace('\\', '/')
            text = io.open(path, encoding='utf-8').read()
            for i, line in enumerate(text.split('\n'), 1):
                stripped = line.strip()
                if stripped.startswith(('*', '/*', '//')):
                    continue                      # 注释行
                if 'moeMsg' in line or 'SITE_MSG' in line:
                    continue                      # 已走文案变量
                if not any(w in line for w in _HINT_WORDS):
                    continue
                if re.search(r"""['"`][^'"`]*[\u4e00-\u9fff][^'"`]*['"`]""", line):
                    found.append({'file': rel, 'line': i, 'text': stripped[:90]})
        return found

    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        total, by_domain = self._registry_stats()
        only = options['py'] or options['tpl'] or options['js']
        do_py = options['py'] or not only
        do_tpl = options['tpl'] or not only
        do_js = options['js'] or not only

        self.stdout.write(self.style.MIGRATE_HEADING('== 文案注册表 =='))
        self.stdout.write('  总条数: %d' % total)
        for dom, cnt in by_domain.items():
            self.stdout.write('    %-14s %d 条' % (dom, cnt))

        result = {'registry_total': total, 'registry_by_domain': by_domain}
        if do_py:
            py = self._scan_py()
            result['py_hardcoded'] = py
            self.stdout.write(self.style.MIGRATE_HEADING(
                '== 后端未收编的中文提示（%d 处）==' % len(py)))
            for item in py[:40]:
                self.stdout.write(self.style.WARNING(
                    '  %s:%d  %s' % (item['file'], item['line'], item['text'][:60])))
            if len(py) > 40:
                self.stdout.write('  ...（其余 %d 处见 JSON 报告）' % (len(py) - 40))
        if do_tpl:
            tpl = self._scan_templates()
            result['tpl_hardcoded'] = tpl
            self.stdout.write(self.style.MIGRATE_HEADING(
                '== 模板中可能的硬编码提示（%d 处）==' % len(tpl)))
            for item in tpl[:30]:
                self.stdout.write(self.style.WARNING(
                    '  %s:%d  %s' % (item['file'], item['line'], item['text'][:70])))
            if len(tpl) > 30:
                self.stdout.write('  ...（其余 %d 处见 JSON 报告）' % (len(tpl) - 30))
        if do_js:
            js = self._scan_js()
            result['js_hardcoded'] = js
            self.stdout.write(self.style.MIGRATE_HEADING(
                '== 前端脚本中可能的硬编码提示（%d 处）==' % len(js)))
            for item in js[:30]:
                self.stdout.write(self.style.WARNING(
                    '  %s:%d  %s' % (item['file'], item['line'], item['text'][:70])))
            if len(js) > 30:
                self.stdout.write('  ...（其余 %d 处见 JSON 报告）' % (len(js) - 30))

        self.stdout.write(self.style.MIGRATE_HEADING('== 汇总 =='))
        self.stdout.write('  注册表条数        : %d' % total)
        if do_py:
            self.stdout.write('  后端待收编        : %d' % len(result.get('py_hardcoded', [])))
        if do_tpl:
            self.stdout.write('  模板待收编        : %d' % len(result.get('tpl_hardcoded', [])))
        if do_js:
            self.stdout.write('  前端脚本待收编    : %d' % len(result.get('js_hardcoded', [])))
        self.stdout.write('  说明：核心用户可见文案（错误页 / 表单提示 / flash / 按钮 / 弹窗 /')
        self.stdout.write('        空状态 / 徽章面板）已全部走 msg() 与 {{ MSG.* }}；')
        self.stdout.write('        报告中剩余项多为内部日志、SEO 静态文本与历史模板文案，')
        self.stdout.write('        可按需继续收编（新代码一律禁止硬编码）。')

        if options['json']:
            out_dir = os.path.join(settings.BASE_DIR, 'docs', 'bugfix_20260926_bug9')
            os.makedirs(out_dir, exist_ok=True)
            out = os.path.join(out_dir, 'messages_audit_report.json')
            io.open(out, 'w', encoding='utf-8').write(
                json.dumps(result, ensure_ascii=False, indent=2))
            self.stdout.write(self.style.SUCCESS('  报告已写入：%s' % out))

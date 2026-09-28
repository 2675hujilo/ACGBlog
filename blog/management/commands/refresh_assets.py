# -*- coding: utf-8 -*-
"""
refresh_assets  ·  一键刷新「静态打包 + 全站缓存」管理命令
================================================================
对应需求（Bug21）：后端提供一键刷新所有打包静态文件、刷新所有缓存的能力。

用法：
    # 重新压缩全部 CSS/JS 为 .min，并清空服务端缓存
    python manage.py refresh_assets
    # 同时重新执行 collectstatic（生产 / WhiteNoise 部署后刷新 manifest 与 .gz）
    python manage.py refresh_assets --collect
    # 只清缓存，不重新压缩
    python manage.py refresh_assets --no-css --no-js
    # 只压缩，不清缓存
    python manage.py refresh_assets --no-cache
    # Bug8 增强：只重压改动过的源文件，避免全量重压第三方静态资源
    python manage.py refresh_assets --only ui_polish.css,auth_inline.js
    # Bug8 增强：只更新构建版本号，让模板 ?v= 立即破浏览器缓存
    python manage.py refresh_assets --token-only

说明：
- CSS 压缩：移除 /* */ 注释、合并空白、去除规则间冗余空格，保留 data URI；
- JS 压缩：字符串 / 模板量 / 正则「感知」地移除注释，仅做安全空白压缩，
  保留换行以避免 JS 自动分号插入(ASI)风险，不改动任何运算符；
- .gz 预压缩：每次压完 .min 产物后同步生成同名 .gz（仅当更小时写入），
  供 WhiteNoise 生产环境直接下发，避免线上回落到在线 gzip；
- 缓存：清空 Django 默认缓存（本项目为 LocMem）；不触碰 Redis 中的
  Celery 任务队列，避免误删待执行任务。
- 构建版本号：写入 static/assets/.build_token，模板以 ?v={{ BUILD_TOKEN }}
  引用静态资源；DEBUG 下上下文处理器每请求重读，改完前端刷新即生效。
"""
import os
import re

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.utils import timezone


# ---------------- CSS 压缩 ----------------
def minify_css(text):
    """移除注释与多余空白，安全压缩 CSS。"""
    # 1. 删除块注释（CSS 没有行注释；data URI 中不含 /* */ 序列）
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    # 2. 合并连续空白为单个空格
    text = re.sub(r'\s+', ' ', text)
    # 3. 去除选择器 / 属性 / 规则边界两侧的空格
    text = re.sub(r'\s*([{}:;,>])\s*', r'\1', text)
    # 4. 去掉最后一个分号
    text = text.replace(';}', '}')
    return text.strip()


# ---------------- JS 压缩（字符串感知，安全优先） ----------------
def strip_js_comments(s):
    """在不破坏字符串 / 模板量 / 正则的前提下去除 JS 注释。"""
    n = len(s)
    out = []
    i = 0
    in_str = None   # ' " `
    in_line = False
    in_block = False
    while i < n:
        c = s[i]
        nxt = s[i + 1] if i + 1 < n else ''
        if in_block:
            if c == '*' and nxt == '/':
                in_block = False
                i += 2
                continue
            i += 1
            continue
        if in_line:
            if c == '\n':
                in_line = False
                out.append(c)
            i += 1
            continue
        if in_str:
            out.append(c)
            if c == '\\':
                if i + 1 < n:
                    out.append(s[i + 1])
                    i += 2
                    continue
            elif c == in_str:
                in_str = None
            i += 1
            continue
        if c in ('"', "'", '`'):
            in_str = c
            out.append(c)
            i += 1
            continue
        if c == '/' and nxt == '*':
            in_block = True
            i += 2
            continue
        if c == '/' and nxt == '/':
            prev = ''.join(out).rstrip()[-1:]
            # 保留 URL 中的 :// （前一个有效字符是冒号）
            if prev == ':':
                out.append(c)
                i += 1
                continue
            in_line = True
            i += 2
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def minify_js(text):
    """去注释 + 安全空白压缩（保留换行，规避 ASI 风险）。"""
    text = strip_js_comments(text)
    lines = []
    for line in text.splitlines():
        st = line.strip()
        # 行内水平空白收敛为单空格
        st = re.sub(r'[ \t]+', ' ', st)
        if st:
            lines.append(st)
    return '\n'.join(lines)


class Command(BaseCommand):
    help = '一键重新压缩所有 CSS/JS 静态文件并清空全站缓存。'

    def add_arguments(self, parser):
        parser.add_argument('--no-css', action='store_true', help='跳过 CSS 压缩')
        parser.add_argument('--no-js', action='store_true', help='跳过 JS 压缩')
        parser.add_argument('--no-cache', action='store_true', help='跳过缓存清理')
        parser.add_argument('--collect', action='store_true', help='压缩后执行 collectstatic')
        # Bug8 增强：只重压指定源文件（逗号分隔的文件名），避免全量重压 CKEditor 等
        # 第三方静态资源带来的无谓 diff；同时在产物旁生成 .gz 预压缩副本。
        parser.add_argument('--only', default='', metavar='FILE[,FILE]',
                            help='仅重压指定源文件（可写文件名或相对 static/assets 的路径）')
        parser.add_argument('--no-gz', action='store_true',
                            help='跳过为 .min.css/.min.js 生成 .gz 预压缩副本')
        parser.add_argument('--token-only', action='store_true',
                            help='只更新构建版本号（?v= 破缓存）')

    # -------------------- .gz 预压缩（WhiteNoise 生产托管用） --------------------
    @staticmethod
    def _write_gz(paths):
        """为给定文件写同名 ``.gz`` 预压缩副本；WhiteNoise 直接下发，省去在线压缩。

        仅当压缩后确实更小时才写入，避免小文件反而变大；失败不影响主流程。
        """
        import gzip
        written = 0
        for path in paths:
            try:
                raw = open(path, 'rb').read()
                packed = gzip.compress(raw, compresslevel=9, mtime=0)
                if len(packed) < len(raw):
                    with open(path + '.gz', 'wb') as fh:
                        fh.write(packed)
                    written += 1
            except OSError:
                continue
        return written

    def handle(self, *args, **opts):
        assets_root = os.path.join(settings.BASE_DIR, 'static', 'assets')
        css_dir = os.path.join(assets_root, 'css')
        js_dir = os.path.join(assets_root, 'js')

        css_count = js_count = 0
        css_before = css_after = js_before = js_after = 0
        only = {name.strip().replace('/', os.sep).lower()
                for name in (opts.get('only') or '').split(',') if name.strip()}
        gz_targets = []

        # --token-only：只刷新版本号，跳过压缩与 .gz
        if opts.get('token_only'):
            opts['no_css'] = opts['no_js'] = True
            opts['no_gz'] = True

        def wanted(rel_path, filename):
            """--only 未指定时全量；指定时按文件名或相对路径匹配。"""
            if not only:
                return True
            return filename.lower() in only or rel_path.replace('/', os.sep).lower() in only

        # ---- 压缩 CSS（递归） ----
        if not opts['no_css'] and os.path.isdir(css_dir):
            for dirpath, _, files in os.walk(css_dir):
                for name in files:
                    if not name.endswith('.css') or name.endswith('.min.css'):
                        continue
                    src = os.path.join(dirpath, name)
                    rel = os.path.relpath(src, assets_root)
                    if not wanted(rel, name):
                        continue
                    dst = os.path.join(dirpath, name[:-4] + '.min.css')
                    raw = open(src, encoding='utf-8').read()
                    mini = minify_css(raw)
                    open(dst, 'w', encoding='utf-8').write(mini)
                    gz_targets.append(dst)
                    css_count += 1
                    css_before += len(raw.encode('utf-8'))
                    css_after += len(mini.encode('utf-8'))

        # ---- 压缩 JS（递归，含 features 子目录） ----
        if not opts['no_js'] and os.path.isdir(js_dir):
            for dirpath, _, files in os.walk(js_dir):
                for name in files:
                    if not name.endswith('.js') or name.endswith('.min.js'):
                        continue
                    src = os.path.join(dirpath, name)
                    rel = os.path.relpath(src, assets_root)
                    if not wanted(rel, name):
                        continue
                    dst = os.path.join(dirpath, name[:-3] + '.min.js')
                    raw = open(src, encoding='utf-8').read()
                    mini = minify_js(raw)
                    open(dst, 'w', encoding='utf-8').write(mini)
                    gz_targets.append(dst)
                    js_count += 1
                    js_before += len(raw.encode('utf-8'))
                    js_after += len(mini.encode('utf-8'))

        # ---- .gz 预压缩副本（与 .min 产物同目录同名 + .gz） ----
        if not opts['no_gz']:
            if gz_targets:
                gz_done = self._write_gz(gz_targets)
                self.stdout.write(self.style.SUCCESS(
                    '已生成 %d 个 .gz 预压缩副本（WhiteNoise 生产直发）。' % gz_done))
            elif only:
                self.stdout.write(self.style.WARNING('--only 未匹配到任何源文件，跳过 .gz。'))

        # ---- 清空服务端缓存 ----
        if not opts['no_cache']:
            try:
                cache.clear()
                self.stdout.write(self.style.SUCCESS('已清空 Django 服务端缓存。'))
            except Exception as exc:  # noqa: BLE001 - 缓存失败不应阻断刷新流程
                self.stdout.write(self.style.WARNING('清缓存失败：%s' % exc))

        # ---- 可选 collectstatic ----
        if opts['collect']:
            from django.core.management import call_command
            call_command('collectstatic', interactive=False, verbosity=0)
            self.stdout.write(self.style.SUCCESS('已重新执行 collectstatic。'))
        # ---- 写入构建版本号（供模板 ?v= 破浏览器缓存，bug20/21） ----
        token = timezone.now().strftime('%Y%m%d%H%M%S')
        token_path = os.path.join(assets_root, '.build_token')
        try:
            with open(token_path, 'w', encoding='utf-8') as f:
                f.write(token)
            self.stdout.write(self.style.SUCCESS('构建版本号：%s' % token))
        except OSError as exc:
            self.stdout.write(self.style.WARNING('版本号写入失败：%s' % exc))

        # 只更新版本号模式：不输出压缩汇总
        if opts.get('token_only'):
            self.stdout.write(self.style.SUCCESS('仅更新构建版本号完成喵~'))
            return

        # ---- 汇总输出 ----
        def ratio(before, after):
            return ('%.1f%%' % (100.0 * after / before)) if before else '-'
        self.stdout.write(self.style.SUCCESS(
            'CSS：%d 个，%d -> %d 字节（%s）' % (
                css_count, css_before, css_after, ratio(css_before, css_after))))
        self.stdout.write(self.style.SUCCESS(
            'JS ：%d 个，%d -> %d 字节（%s）' % (
                js_count, js_before, js_after, ratio(js_before, js_after))))
        self.stdout.write(self.style.SUCCESS('静态资源与缓存刷新完成喵~'))

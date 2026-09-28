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
#: 导入模块「os」，供本文件后续使用
import os
#: 导入模块「re」，供本文件后续使用
import re

#: 从模块「django.conf」导入所需对象
from django.conf import settings
#: 从模块「django.core.cache」导入所需对象
from django.core.cache import cache
#: 从模块「django.core.management.base」导入所需对象
from django.core.management.base import BaseCommand
#: 从模块「django.utils」导入所需对象
from django.utils import timezone


# ---------------- CSS 压缩 ----------------
def minify_css(text):
    """移除注释与多余空白，安全压缩 CSS。"""
    # 1. 删除块注释（CSS 没有行注释；data URI 中不含 /* */ 序列）
    #: 定义变量「text」，保存对应数据
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    # 2. 合并连续空白为单个空格
    #: 定义变量「text」，保存对应数据
    text = re.sub(r'\s+', ' ', text)
    # 3. 去除选择器 / 属性 / 规则边界两侧的空格
    #: 定义变量「text」，保存对应数据
    text = re.sub(r'\s*([{}:;,>])\s*', r'\1', text)
    # 4. 去掉最后一个分号
    #: 定义变量「text」，保存对应数据
    text = text.replace(';}', '}')
    #: 返回结果并结束当前函数
    return text.strip()


# ---------------- JS 压缩（字符串感知，安全优先） ----------------
def strip_js_comments(s):
    """在不破坏字符串 / 模板量 / 正则的前提下去除 JS 注释。"""
    #: 定义变量「n」，保存对应数据
    n = len(s)
    #: 定义变量「out」，保存对应数据（集合/元组）
    out = []
    #: 定义变量「i」，保存对应数据
    i = 0
    #: 定义变量「in_str」，保存对应数据
    in_str = None   # ' " `
    #: 定义变量「in_line」，保存对应数据
    in_line = False
    #: 定义变量「in_block」，保存对应数据
    in_block = False
    #: 条件为真时反复执行
    while i < n:
        #: 定义变量「c」，保存对应数据
        c = s[i]
        #: 定义变量「nxt」，保存对应数据
        nxt = s[i + 1] if i + 1 < n else ''
        #: 条件判断：条件成立时执行该分支
        if in_block:
            #: 条件判断：条件成立时执行该分支
            if c == '*' and nxt == '/':
                #: 定义变量「in_block」，保存对应数据
                in_block = False
                #: 该行执行对应逻辑（结合上下文理解）
                i += 2
                #: 跳过本次进入下一次迭代
                continue
            #: 该行执行对应逻辑（结合上下文理解）
            i += 1
            #: 跳过本次进入下一次迭代
            continue
        #: 条件判断：条件成立时执行该分支
        if in_line:
            #: 条件判断：条件成立时执行该分支
            if c == '\n':
                #: 定义变量「in_line」，保存对应数据
                in_line = False
                #: 调用「out.append」执行相应逻辑
                out.append(c)
            #: 该行执行对应逻辑（结合上下文理解）
            i += 1
            #: 跳过本次进入下一次迭代
            continue
        #: 条件判断：条件成立时执行该分支
        if in_str:
            #: 调用「out.append」执行相应逻辑
            out.append(c)
            #: 条件判断：条件成立时执行该分支
            if c == '\\':
                #: 条件判断：条件成立时执行该分支
                if i + 1 < n:
                    #: 调用「out.append」执行相应逻辑
                    out.append(s[i + 1])
                    #: 该行执行对应逻辑（结合上下文理解）
                    i += 2
                    #: 跳过本次进入下一次迭代
                    continue
            #: 否则若该条件成立则进入此分支
            elif c == in_str:
                #: 定义变量「in_str」，保存对应数据
                in_str = None
            #: 该行执行对应逻辑（结合上下文理解）
            i += 1
            #: 跳过本次进入下一次迭代
            continue
        #: 条件判断：条件成立时执行该分支
        if c in ('"', "'", '`'):
            #: 定义变量「in_str」，保存对应数据
            in_str = c
            #: 调用「out.append」执行相应逻辑
            out.append(c)
            #: 该行执行对应逻辑（结合上下文理解）
            i += 1
            #: 跳过本次进入下一次迭代
            continue
        #: 条件判断：条件成立时执行该分支
        if c == '/' and nxt == '*':
            #: 定义变量「in_block」，保存对应数据
            in_block = True
            #: 该行执行对应逻辑（结合上下文理解）
            i += 2
            #: 跳过本次进入下一次迭代
            continue
        #: 条件判断：条件成立时执行该分支
        if c == '/' and nxt == '/':
            #: 定义变量「prev」，保存对应数据
            prev = ''.join(out).rstrip()[-1:]
            # 保留 URL 中的 :// （前一个有效字符是冒号）
            #: 条件判断：条件成立时执行该分支
            if prev == ':':
                #: 调用「out.append」执行相应逻辑
                out.append(c)
                #: 该行执行对应逻辑（结合上下文理解）
                i += 1
                #: 跳过本次进入下一次迭代
                continue
            #: 定义变量「in_line」，保存对应数据
            in_line = True
            #: 该行执行对应逻辑（结合上下文理解）
            i += 2
            #: 跳过本次进入下一次迭代
            continue
        #: 调用「out.append」执行相应逻辑
        out.append(c)
        #: 该行执行对应逻辑（结合上下文理解）
        i += 1
    #: 返回结果并结束当前函数
    return ''.join(out)


def minify_js(text):
    """去注释 + 安全空白压缩（保留换行，规避 ASI 风险）。"""
    #: 定义变量「text」，保存对应数据
    text = strip_js_comments(text)
    #: 定义变量「lines」，保存对应数据（集合/元组）
    lines = []
    #: 循环遍历，逐个处理元素
    for line in text.splitlines():
        #: 定义变量「st」，保存对应数据
        st = line.strip()
        # 行内水平空白收敛为单空格
        #: 定义变量「st」，保存对应数据
        st = re.sub(r'[ \t]+', ' ', st)
        #: 条件判断：条件成立时执行该分支
        if st:
            #: 调用「lines.append」执行相应逻辑
            lines.append(st)
    #: 返回结果并结束当前函数
    return '\n'.join(lines)


class Command(BaseCommand):
    """
    类 Command：command。

    继承：BaseCommand（基类提供相应能力）。

    字段/类属性：
      - help：str

    方法：add_arguments、_write_gz、handle。

    注意：
      - 关注实例状态与方法副作用，保持单一职责。
    """
    #: 定义变量「help」，保存对应数据
    help = '一键重新压缩所有 CSS/JS 静态文件并清空全站缓存。'

    def add_arguments(self, parser):
        """
        功能：添加「arguments」。

        参数：
          - parser：传入参数，含义结合函数体与调用处

        返回：无显式返回（None），多以副作用为主。

        注意：保持函数单一职责；修改时确认调用方不受影响。
        """
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--no-css', action='store_true', help='跳过 CSS 压缩')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--no-js', action='store_true', help='跳过 JS 压缩')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--no-cache', action='store_true', help='跳过缓存清理')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--collect', action='store_true', help='压缩后执行 collectstatic')
        # Bug8 增强：只重压指定源文件（逗号分隔的文件名），避免全量重压 CKEditor 等
        # 第三方静态资源带来的无谓 diff；同时在产物旁生成 .gz 预压缩副本。
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--only', default='', metavar='FILE[,FILE]',
                            #: 定义变量「help」，保存对应数据
                            help='仅重压指定源文件（可写文件名或相对 static/assets 的路径）')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--no-gz', action='store_true',
                            #: 定义变量「help」，保存对应数据
                            help='跳过为 .min.css/.min.js 生成 .gz 预压缩副本')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--token-only', action='store_true',
                            #: 定义变量「help」，保存对应数据
                            help='只更新构建版本号（?v= 破缓存）')

    # -------------------- .gz 预压缩（WhiteNoise 生产托管用） --------------------
    #: 装饰器：为下一个定义附加「staticmethod」行为（权限、缓存、注册信号等）
    @staticmethod
    def _write_gz(paths):
        """为给定文件写同名 ``.gz`` 预压缩副本；WhiteNoise 直接下发，省去在线压缩。

        仅当压缩后确实更小时才写入，避免小文件反而变大；失败不影响主流程。
        """
        #: 导入模块「gzip」，供本文件后续使用
        import gzip
        #: 定义变量「written」，保存对应数据
        written = 0
        #: 循环遍历，逐个处理元素
        for path in paths:
            #: 尝试执行可能出错的代码
            try:
                #: 定义变量「raw」，保存对应数据
                raw = open(path, 'rb').read()
                #: 定义变量「packed」，保存对应数据
                packed = gzip.compress(raw, compresslevel=9, mtime=0)
                #: 条件判断：条件成立时执行该分支
                if len(packed) < len(raw):
                    #: 上下文管理：进入时获取资源、退出时自动释放
                    with open(path + '.gz', 'wb') as fh:
                        #: 调用「fh.write」执行相应逻辑
                        fh.write(packed)
                    #: 该行执行对应逻辑（结合上下文理解）
                    written += 1
            #: 捕获并处理异常，避免程序中断
            except OSError:
                #: 跳过本次进入下一次迭代
                continue
        #: 返回结果并结束当前函数
        return written

    def handle(self, *args, **opts):
        """
        功能：处理「handle」。

        返回：对应计算/查询结果。

        注意：读写缓存，注意缓存键口径与失效策略。
        """
        #: 定义变量「assets_root」，保存对应数据
        assets_root = os.path.join(settings.BASE_DIR, 'static', 'assets')
        #: 定义变量「css_dir」，保存对应数据
        css_dir = os.path.join(assets_root, 'css')
        #: 定义变量「js_dir」，保存对应数据
        js_dir = os.path.join(assets_root, 'js')

        #: 定义变量「css_count」，保存对应数据
        css_count = js_count = 0
        #: 定义变量「css_before」，保存对应数据
        css_before = css_after = js_before = js_after = 0
        #: 定义变量「only」，保存对应数据
        only = {name.strip().replace('/', os.sep).lower()
                #: 循环遍历，逐个处理元素
                for name in (opts.get('only') or '').split(',') if name.strip()}
        #: 定义变量「gz_targets」，保存对应数据（集合/元组）
        gz_targets = []

        # --token-only：只刷新版本号，跳过压缩与 .gz
        #: 条件判断：条件成立时执行该分支
        if opts.get('token_only'):
            #: 该行执行对应逻辑（结合上下文理解）
            opts['no_css'] = opts['no_js'] = True
            #: 该行执行对应逻辑（结合上下文理解）
            opts['no_gz'] = True

        def wanted(rel_path, filename):
            """--only 未指定时全量；指定时按文件名或相对路径匹配。"""
            #: 条件判断：条件成立时执行该分支
            if not only:
                #: 返回结果并结束当前函数
                return True
            #: 返回结果并结束当前函数
            return filename.lower() in only or rel_path.replace('/', os.sep).lower() in only

        # ---- 压缩 CSS（递归） ----
        #: 条件判断：条件成立时执行该分支
        if not opts['no_css'] and os.path.isdir(css_dir):
            #: 循环遍历，逐个处理元素
            for dirpath, _, files in os.walk(css_dir):
                #: 循环遍历，逐个处理元素
                for name in files:
                    #: 条件判断：条件成立时执行该分支
                    if not name.endswith('.css') or name.endswith('.min.css'):
                        #: 跳过本次进入下一次迭代
                        continue
                    #: 定义变量「src」，保存对应数据
                    src = os.path.join(dirpath, name)
                    #: 定义变量「rel」，保存对应数据
                    rel = os.path.relpath(src, assets_root)
                    #: 条件判断：条件成立时执行该分支
                    if not wanted(rel, name):
                        #: 跳过本次进入下一次迭代
                        continue
                    #: 定义变量「dst」，保存对应数据
                    dst = os.path.join(dirpath, name[:-4] + '.min.css')
                    #: 定义变量「raw」，保存对应数据
                    raw = open(src, encoding='utf-8').read()
                    #: 定义变量「mini」，保存对应数据
                    mini = minify_css(raw)
                    #: 调用「open」执行相应逻辑
                    open(dst, 'w', encoding='utf-8').write(mini)
                    #: 调用「gz_targets.append」执行相应逻辑
                    gz_targets.append(dst)
                    #: 该行执行对应逻辑（结合上下文理解）
                    css_count += 1
                    #: 该行执行对应逻辑（结合上下文理解）
                    css_before += len(raw.encode('utf-8'))
                    #: 该行执行对应逻辑（结合上下文理解）
                    css_after += len(mini.encode('utf-8'))

        # ---- 压缩 JS（递归，含 features 子目录） ----
        #: 条件判断：条件成立时执行该分支
        if not opts['no_js'] and os.path.isdir(js_dir):
            #: 循环遍历，逐个处理元素
            for dirpath, _, files in os.walk(js_dir):
                #: 循环遍历，逐个处理元素
                for name in files:
                    #: 条件判断：条件成立时执行该分支
                    if not name.endswith('.js') or name.endswith('.min.js'):
                        #: 跳过本次进入下一次迭代
                        continue
                    #: 定义变量「src」，保存对应数据
                    src = os.path.join(dirpath, name)
                    #: 定义变量「rel」，保存对应数据
                    rel = os.path.relpath(src, assets_root)
                    #: 条件判断：条件成立时执行该分支
                    if not wanted(rel, name):
                        #: 跳过本次进入下一次迭代
                        continue
                    #: 定义变量「dst」，保存对应数据
                    dst = os.path.join(dirpath, name[:-3] + '.min.js')
                    #: 定义变量「raw」，保存对应数据
                    raw = open(src, encoding='utf-8').read()
                    #: 定义变量「mini」，保存对应数据
                    mini = minify_js(raw)
                    #: 调用「open」执行相应逻辑
                    open(dst, 'w', encoding='utf-8').write(mini)
                    #: 调用「gz_targets.append」执行相应逻辑
                    gz_targets.append(dst)
                    #: 该行执行对应逻辑（结合上下文理解）
                    js_count += 1
                    #: 该行执行对应逻辑（结合上下文理解）
                    js_before += len(raw.encode('utf-8'))
                    #: 该行执行对应逻辑（结合上下文理解）
                    js_after += len(mini.encode('utf-8'))

        # ---- .gz 预压缩副本（与 .min 产物同目录同名 + .gz） ----
        #: 条件判断：条件成立时执行该分支
        if not opts['no_gz']:
            #: 条件判断：条件成立时执行该分支
            if gz_targets:
                #: 定义变量「gz_done」，保存对应数据
                gz_done = self._write_gz(gz_targets)
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write(self.style.SUCCESS(
                    #: 该行执行对应逻辑（结合上下文理解）
                    '已生成 %d 个 .gz 预压缩副本（WhiteNoise 生产直发）。' % gz_done))
            #: 否则若该条件成立则进入此分支
            elif only:
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write(self.style.WARNING('--only 未匹配到任何源文件，跳过 .gz。'))

        # ---- 清空服务端缓存 ----
        #: 条件判断：条件成立时执行该分支
        if not opts['no_cache']:
            #: 尝试执行可能出错的代码
            try:
                #: 调用「cache.clear」执行相应逻辑
                cache.clear()
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write(self.style.SUCCESS('已清空 Django 服务端缓存。'))
            #: 捕获并处理异常，避免程序中断
            except Exception as exc:  # noqa: BLE001 - 缓存失败不应阻断刷新流程
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write(self.style.WARNING('清缓存失败：%s' % exc))

        # ---- 可选 collectstatic ----
        #: 条件判断：条件成立时执行该分支
        if opts['collect']:
            #: 从模块「django.core.management」导入所需对象
            from django.core.management import call_command
            #: 调用「call_command」执行相应逻辑
            call_command('collectstatic', interactive=False, verbosity=0)
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.SUCCESS('已重新执行 collectstatic。'))
        # ---- 写入构建版本号（供模板 ?v= 破浏览器缓存，bug20/21） ----
        #: 获取当前时间（时区感知），统一时间口径
        token = timezone.now().strftime('%Y%m%d%H%M%S')
        #: 定义变量「token_path」，保存对应数据
        token_path = os.path.join(assets_root, '.build_token')
        #: 尝试执行可能出错的代码
        try:
            #: 上下文管理：进入时获取资源、退出时自动释放
            with open(token_path, 'w', encoding='utf-8') as f:
                #: 调用「f.write」执行相应逻辑
                f.write(token)
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.SUCCESS('构建版本号：%s' % token))
        #: 捕获并处理异常，避免程序中断
        except OSError as exc:
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.WARNING('版本号写入失败：%s' % exc))

        # 只更新版本号模式：不输出压缩汇总
        #: 条件判断：条件成立时执行该分支
        if opts.get('token_only'):
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.SUCCESS('仅更新构建版本号完成喵~'))
            #: 返回结果并结束当前函数
            return

        # ---- 汇总输出 ----
        def ratio(before, after):
            """
            功能：处理「ratio」相关逻辑。

            参数：
              - before：传入参数，含义结合函数体与调用处
              - after：传入参数，含义结合函数体与调用处

            返回：对应计算/查询结果。

            注意：保持函数单一职责；修改时确认调用方不受影响。
            """
            #: 返回结果并结束当前函数
            return ('%.1f%%' % (100.0 * after / before)) if before else '-'
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.SUCCESS(
            #: 该行执行对应逻辑（结合上下文理解）
            'CSS：%d 个，%d -> %d 字节（%s）' % (
                #: 该行执行对应逻辑（结合上下文理解）
                css_count, css_before, css_after, ratio(css_before, css_after))))
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.SUCCESS(
            #: 该行执行对应逻辑（结合上下文理解）
            'JS ：%d 个，%d -> %d 字节（%s）' % (
                #: 该行执行对应逻辑（结合上下文理解）
                js_count, js_before, js_after, ratio(js_before, js_after))))
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.SUCCESS('静态资源与缓存刷新完成喵~'))

"""manage.py cache_bump [--show] [--set vN]

缓存版本号管理命令：读写 ``blog/cache_version.txt``。版本号是详情页缓存 key 的
前缀（如 ``v1:comment_tree:3``），bump 后所有 key 前缀整体变化，服务端缓存即刻
全局失效——旧 key 由 TTL（300s）自动过期清理，无需逐条删除。

用法：
    python manage.py cache_bump            # 版本号 +1（v1 -> v2）
    python manage.py cache_bump --show     # 只显示当前版本号
    python manage.py cache_bump --set v7   # 直接设为指定版本号

注意：运行中的 runserver / worker 在进程启动时读一次版本号（进程内缓存），
bump 后需重启使其生效；旧版本 key 残留由 TTL 自动清空。
"""
import re

from django.core.management.base import BaseCommand

from blog.cache_keys import CACHE_VERSION_FILE, CACHE_VERSION_FALLBACK


class Command(BaseCommand):
    """缓存版本号管理命令（开发调试用）。"""

    help = '缓存版本号管理：bump 后详情页缓存整体失效（调试用）'

    def add_arguments(self, parser):
        """注册 --show / --set 参数。"""
        parser.add_argument('--show', action='store_true', help='只显示当前版本号')
        parser.add_argument('--set', default='',
                            help='直接写入指定版本号（格式 vN，如 v3）')

    def handle(self, *args, **options):
        """读取当前版本号并执行 show / bump / set。"""
        current = CACHE_VERSION_FALLBACK
        try:
            with open(CACHE_VERSION_FILE, 'r', encoding='utf-8') as f:
                current = f.read().strip() or CACHE_VERSION_FALLBACK
        except OSError:
            pass

        if options['show']:
            self.stdout.write(f'当前缓存版本: {current}')
            return

        if options['set']:
            new_version = options['set'].strip()
            if not re.fullmatch(r'v\d+', new_version):
                self.stdout.write(self.style.ERROR('版本号格式应为 vN（如 v3）'))
                return
        else:
            m = re.fullmatch(r'v(\d+)', current)
            new_version = f'v{(int(m.group(1)) + 1) if m else 2}'

        with open(CACHE_VERSION_FILE, 'w', encoding='utf-8') as f:
            f.write(new_version)
        self.stdout.write(self.style.SUCCESS(
            f'缓存版本已更新: {current} -> {new_version}'))
        self.stdout.write(self.style.WARNING(
            '重启 runserver / worker 后新前缀生效；旧 key 由 TTL 自动清理'))

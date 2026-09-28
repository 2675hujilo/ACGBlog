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
#: 导入模块「re」，供本文件后续使用
import re

#: 从模块「django.core.management.base」导入所需对象
from django.core.management.base import BaseCommand

#: 从模块「blog.utils.cache_keys」导入所需对象
from blog.utils.cache_keys import CACHE_VERSION_FILE, CACHE_VERSION_FALLBACK


class Command(BaseCommand):
    """缓存版本号管理命令（开发调试用）。"""

    #: 定义变量「help」，保存对应数据
    help = '缓存版本号管理：bump 后详情页缓存整体失效（调试用）'

    def add_arguments(self, parser):
        """注册 --show / --set 参数。"""
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--show', action='store_true', help='只显示当前版本号')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--set', default='',
                            #: 定义变量「help」，保存对应数据
                            help='直接写入指定版本号（格式 vN，如 v3）')

    def handle(self, *args, **options):
        """读取当前版本号并执行 show / bump / set。"""
        #: 定义变量「current」，保存对应数据
        current = CACHE_VERSION_FALLBACK
        #: 尝试执行可能出错的代码
        try:
            #: 上下文管理：进入时获取资源、退出时自动释放
            with open(CACHE_VERSION_FILE, 'r', encoding='utf-8') as f:
                #: 定义变量「current」，保存对应数据
                current = f.read().strip() or CACHE_VERSION_FALLBACK
        #: 捕获并处理异常，避免程序中断
        except OSError:
            #: 占位语句：此处暂不需要实现
            pass

        #: 条件判断：条件成立时执行该分支
        if options['show']:
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(f'当前缓存版本: {current}')
            #: 返回结果并结束当前函数
            return

        #: 条件判断：条件成立时执行该分支
        if options['set']:
            #: 定义变量「new_version」，保存对应数据
            new_version = options['set'].strip()
            #: 条件判断：条件成立时执行该分支
            if not re.fullmatch(r'v\d+', new_version):
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write(self.style.ERROR('版本号格式应为 vN（如 v3）'))
                #: 返回结果并结束当前函数
                return
        #: 以上条件均不成立时的兜底分支
        else:
            #: 定义变量「m」，保存对应数据
            m = re.fullmatch(r'v(\d+)', current)
            #: 定义变量「new_version」，保存对应数据
            new_version = f'v{(int(m.group(1)) + 1) if m else 2}'

        #: 上下文管理：进入时获取资源、退出时自动释放
        with open(CACHE_VERSION_FILE, 'w', encoding='utf-8') as f:
            #: 调用「f.write」执行相应逻辑
            f.write(new_version)
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.SUCCESS(
            #: 该行执行对应逻辑（结合上下文理解）
            f'缓存版本已更新: {current} -> {new_version}'))
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.WARNING(
            #: 该行执行对应逻辑（结合上下文理解）
            '重启 runserver / worker 后新前缀生效；旧 key 由 TTL 自动清理'))

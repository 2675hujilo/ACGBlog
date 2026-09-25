"""manage.py seed_demo_stats [--days 14] [--base 80]

演示 / QA 用：为最近 N 天回填“访问日志（AccessLog）”，让运营看板的“近 14 天访问
趋势”在演示环境里呈现自然的连续柱形，而不是只有部署当天有数据。

设计原则（安全 / 不破坏真实数据）：
  * 只回填“当天之前”的日期，**今天**一律不改动，保留真实访问并让其保持峰值；
  * 对每一天先统计已有日志数，已达到目标值就跳过，因此可重复执行、不会翻倍；
  * 目标值按“基础量 × 周末系数 × 临近今日的缓升 + 随机抖动”生成，数值远小于今日
    真实峰值，避免污染整体趋势；
  * 使用 bulk_create 一次性写入，字段取通用 / 匿名的演示值，不关联真实用户。

注意：这是**演示数据**命令，生产环境通常无需运行；站点自然运行满 N 天后趋势图会
自动填满。
"""
import random
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count

from blog.models import AccessLog


class Command(BaseCommand):
    """回填演示访问日志，使近 N 天访问趋势连续自然（仅 QA / 演示用）。"""

    help = '回填最近 N 天的演示访问日志，让看板趋势图连续（QA/演示用）'

    def add_arguments(self, parser):
        """注册 --days / --base 参数。"""
        parser.add_argument('--days', type=int, default=14, help='回填天数（默认 14）')
        parser.add_argument('--base', type=int, default=80,
                            help='每日基础访问量目标（默认 80，会按周末/趋势浮动）')

    def handle(self, *args, **options):
        """按天核对并补足演示访问日志。"""
        days = max(1, min(options['days'], 60))
        base = max(10, options['base'])
        today = datetime.now().date()
        rnd = random.Random(20260924)  # 固定随机种子，保证结果可复现
        # 本次运行的唯一批次令牌（写进演示行 user_agent），避免重复执行时互相串批
        run_token = 'DS%06d' % rnd.randint(0, 999999)

        # 演示用的通用字段池（均为匿名 / 通用值，不涉及真实用户隐私）
        paths = ['/', '/?kind=article', '/categories/', '/tags/', '/archive/',
                 '/category/2/', '/article/76/', '/random/', '/search/?q=python']
        browsers = [('Chrome', 'Windows'), ('Edge', 'Windows'), ('Safari', 'macOS'),
                    ('Chrome', 'Android'), ('Firefox', 'Windows')]
        ips = ['112.10.%d.%d', '223.104.%d.%d', '183.14.%d.%d', '39.144.%d.%d']

        total_created = 0
        # 从最早一天向前回填到“昨天”（今天保留真实数据）
        for back in range(days - 1, 0, -1):
            day = today - timedelta(days=back)
            existing = AccessLog.objects.filter(created_at__date=day).count()

            # 目标量：周末略高 + 越接近今天略高 + 轻微随机抖动
            weekend_k = 1.35 if day.weekday() >= 5 else 1.0
            trend_k = 1.0 + (days - 1 - back) / (days * 4.0)
            target = int(base * weekend_k * trend_k * rnd.uniform(0.8, 1.2))

            if existing >= target:
                self.stdout.write(f'{day} 已有 {existing} 条（目标 {target}），跳过')
                continue

            need = target - existing
            # 按小时把当天的访问分组（8:00-23:00），每小时一个批次；
            # MySQL 的 bulk_create 不回填主键，因此把“批次令牌”写进 user_agent，
            # 插入后立刻按令牌 queryset.update 回写 created_at（update 不走 save，
            # auto_now_add 不会干预），既无需主键又保留一天内的小时分布。
            hour_buckets = {}
            for _ in range(need):
                h = rnd.randint(8, 23)
                br, osname = rnd.choice(browsers)
                ip_tpl = rnd.choice(ips)
                token = f'{run_token}/d{day:%Y%m%d}/h{h:02d}'
                hour_buckets.setdefault(h, []).append(AccessLog(
                    ip_address=ip_tpl % (rnd.randint(1, 254), rnd.randint(1, 254)),
                    path=rnd.choice(paths), method='GET', status_code=200,
                    duration_ms=rnd.randint(8, 320), browser=br, os=osname,
                    user_agent=f'Mozilla/5.0 ({osname}) DemoBrowser/{br} {token}',
                ))
            for h, objs in sorted(hour_buckets.items()):
                token = f'{run_token}/d{day:%Y%m%d}/h{h:02d}'
                AccessLog.objects.bulk_create(objs, batch_size=500)
                # 回写到目标日期 + 该小时，分钟/秒取自然随机值
                AccessLog.objects.filter(user_agent__contains=token).update(
                    created_at=datetime(day.year, day.month, day.day,
                                        h, rnd.randint(0, 59), rnd.randint(0, 59)))
            total_created += need
            self.stdout.write(f'{day} 回填 {need} 条（{existing} -> {target}）')

        self.stdout.write(self.style.SUCCESS(
            f'演示访问日志回填完成，共新增 {total_created} 条；今日真实数据未改动喵~'))

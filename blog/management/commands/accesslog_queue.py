# -*- coding: utf-8 -*-
"""accesslog_queue · 访问日志「Redis 兜底队列」运维命令

背景：访问日志中间件为「全局永久强制模块」，投递走三层降级
（Celery 异步 → Redis 兜底队列 → 极端同步入库）。当 Redis broker 故障时，
日志会堆在 Redis 列表 ``acgblog:access_log:fallback`` 中；broker 恢复后
用本命令批量消费入库，保证一条不丢。

用法：
    # 查看兜底队列积压情况（不消费）
    python manage.py accesslog_queue

    # 批量消费入库（Broker 恢复后执行；可反复执行直到 remaining=0）
    python manage.py accesslog_queue --drain

    # 指定单批条数与最大批数
    python manage.py accesslog_queue --drain --batch 1000 --max-batches 50

    # 只统计不入库（等价于只读，便于核对）
    python manage.py accesslog_queue --dry-run

    # 清空兜底队列（危险：会丢弃尚未入库的日志，需二次确认）
    python manage.py accesslog_queue --purge --yes

自动兜底：Celery beat 定时任务 ``blog.tasks.flush_access_log_queue`` 每 5 分钟
尝试消费一次，即使忘记手动执行也能自动补齐。
"""
from django.core.management.base import BaseCommand

from blog.access_log_service import (FALLBACK_KEY, drain_fallback,
                                     fallback_length, reset_broker_circuit,
                                     reset_circuit)


class Command(BaseCommand):
    """查看 / 消费 / 清空 访问日志 Redis 兜底队列。"""

    help = '访问日志 Redis 兜底队列运维：查看积压、批量消费入库、清空队列'

    def add_arguments(self, parser):
        parser.add_argument('--drain', action='store_true',
                            help='批量消费兜底队列并写入 AccessLog 表')
        parser.add_argument('--dry-run', action='store_true',
                            help='只统计待消费条数，不消费不入库')
        parser.add_argument('--purge', action='store_true',
                            help='清空兜底队列（会丢弃未入库日志，需配合 --yes）')
        parser.add_argument('--yes', action='store_true', help='配合 --purge 的二次确认')
        parser.add_argument('--batch', type=int, default=500, help='单批消费条数（默认 500）')
        parser.add_argument('--max-batches', type=int, default=100,
                            help='单次最多消费批数（默认 100）')
        parser.add_argument('--reset-circuit', action='store_true',
                            help='先清除 Redis / Broker 熔断状态再执行（诊断用）')

    def handle(self, *args, **options):
        if options['reset_circuit']:
            reset_circuit()
            reset_broker_circuit()
            self.stdout.write(self.style.WARNING('已清除 Redis / Broker 熔断窗口。'))

        before = fallback_length()
        if before < 0:
            self.stdout.write(self.style.ERROR(
                'Redis 不可用（或连接超时）。请确认 redis-server 已启动，'
                '再执行本命令；中间件此时会自动走「极端降级」同步入库。'))
            return
        self.stdout.write('兜底队列 %s 当前积压：%s 条' % (FALLBACK_KEY, before))

        if options['purge']:
            if not options['yes']:
                self.stdout.write(self.style.ERROR(
                    '拒绝执行：--purge 会永久丢弃未入库日志，请追加 --yes 二次确认。'))
                return
            from blog.access_log_service import get_redis
            client = get_redis()
            removed = client.delete(FALLBACK_KEY) if client else 0
            self.stdout.write(self.style.WARNING(
                '已清空兜底队列（删除 key=%s，丢弃 %s 条未入库日志）。' % (removed, before)))
            return

        if options['dry_run'] or not options['drain']:
            self.stdout.write(self.style.SUCCESS(
                '待消费 %s 条。执行 `manage.py accesslog_queue --drain` 批量入库。' % before))
            return

        result = drain_fallback(batch=max(1, options['batch']),
                                max_batches=max(1, options['max_batches']))
        if result['error']:
            self.stdout.write(self.style.ERROR('消费失败：%s' % result['error']))
        self.stdout.write(self.style.SUCCESS(
            '消费完成：入库 %s 条，坏数据 %s 条，剩余 %s 条'
            % (result['ok'], result['bad'], result['remaining'])))
        if result['bad']:
            self.stdout.write(self.style.WARNING(
                '存在 %s 条无法解析的坏数据（已丢弃），请检查上游写入。' % result['bad']))

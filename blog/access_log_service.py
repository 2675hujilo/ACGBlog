# -*- coding: utf-8 -*-
"""访问日志投递通道（全局永久强制模块的「投递层」）。

三层降级策略（严格按需求实现，常态禁止全量同步入库）
------------------------------------------------------------------
1. **正常路径（异步优先）**：``save_access_log.delay(payload)`` 把一条单行 INSERT
   交给 Celery worker，经 Redis broker 排队后由 worker 消费入库；
   请求线程只做一次内存级入队，**不碰数据库**，高并发下不会压库。
   判定成功 = broker 接受任务即算成功（worker 稍后消费；即使 worker 未启动，
   任务也安全停留在 broker 队列中，不会丢失）。

2. **Broker 故障（Redis 兜底队列）**：``delay()`` 抛异常（broker 连不上 / 拒绝连接）
   时，把同一条 payload JSON 化后 ``RPUSH`` 到 Redis 列表
   ``acgblog:access_log:fallback``；**绝不**在这一层同步写库。
   待 broker 恢复后，由 Django 管理命令批量消费入库：
   ``python manage.py accesslog_queue --drain``。

3. **极端降级（Redis 也不可用）**：连兜底队列都写不进去（Redis 完全宕机）时，
   才同步 ``AccessLog.objects.create()`` 保证日志不丢失；本层会打 ERROR 日志，
   属于可观测的异常态告警。

设计约束
--------
- 所有 Redis / Celery 操作均带**短超时**（毫秒级），确保中间件永远不会成为
  请求链路的阻塞点；
- 三层各自吞掉自身异常，中间件绝不向上抛错影响响应；
- 兜底队列键名、批量条数、超时均可在 ``settings`` 覆盖（见本模块常量）。
"""
import json
import logging
import time

from django.conf import settings

logger = logging.getLogger(__name__)

# ---- 可配置常量（settings 可覆盖，缺省值面向本地开发） ----
FALLBACK_KEY = getattr(settings, 'ACCESS_LOG_FALLBACK_KEY', 'acgblog:access_log:fallback')
REDIS_URL = getattr(settings, 'ACCESS_LOG_FALLBACK_REDIS_URL', None) or getattr(
    settings, 'CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
# 单次操作超时（秒）：socket 级短超时，避免 Redis 卡住拖慢请求
REDIS_TIMEOUT = float(getattr(settings, 'ACCESS_LOG_REDIS_TIMEOUT', 0.35))
# 兜底队列长度上限：超过则丢弃最老记录并在日志中告警（防止 Redis 内存无限增长）
FALLBACK_MAX_LEN = int(getattr(settings, 'ACCESS_LOG_FALLBACK_MAX_LEN', 20000))
# 批量消费单批条数
DRAIN_BATCH = int(getattr(settings, 'ACCESS_LOG_DRAIN_BATCH', 500))

# 进程内 Redis 连接复用（短超时）；连接失效时下次调用自动重建
_redis_client = None
_redis_broken_until = 0.0   # 熔断窗口：Redis 失败后短时间内不再重试，降低请求延迟
BROKEN_COOLDOWN = float(getattr(settings, 'ACCESS_LOG_REDIS_COOLDOWN', 20.0))

# Broker（Celery）熔断窗口：broker 宕机时 kombu 的连接/发布策略会阻塞数秒，
# 实测单请求 6.2s。为了让访问日志「绝不拖慢网站响应」，投递失败后进入熔断，
# 窗口期内直接走 Redis 兜底队列（不再尝试连接 broker）。
_broker_broken_until = 0.0
BROKER_COOLDOWN = float(getattr(settings, 'ACCESS_LOG_BROKER_COOLDOWN', 15.0))


def broker_available():
    """Broker 是否处于可用（非熔断）状态。"""
    return _broker_broken_until <= time.time()


def mark_broker_broken(exc=None):
    """标记 broker 投递失败并开启熔断窗口；同时丢弃 Celery 连接池中的坏连接。"""
    global _broker_broken_until
    _broker_broken_until = time.time() + BROKER_COOLDOWN
    try:
        from DjangoBlog.celery import app as celery_app
        # 关闭并重建连接池，避免后续请求复用坏连接继续等待超时
        celery_app.close()
    except Exception:  # noqa: BLE001 关闭连接失败不影响熔断语义
        pass
    if exc is not None:
        logger.warning('[accesslog] Celery broker 投递失败（%s），进入 %ss 熔断窗口，'
                       '后续请求直接走 Redis 兜底队列', exc, BROKER_COOLDOWN)


def reset_broker_circuit():
    """清除 broker 熔断状态（管理命令 / 诊断脚本主动重试前调用）。"""
    global _broker_broken_until
    _broker_broken_until = 0.0


def get_redis(timeout=None):
    """获取（并复用）短超时的 Redis 客户端；不可用时返回 None。

    统一使用 ``redis.Redis`` + ``socket_timeout``，并显式 ``decode_responses=True``
    以便直接处理 JSON 字符串。任何构造异常都降级为 None，由调用方走下一层兜底。
    """
    global _redis_client, _redis_broken_until
    # 熔断窗口内直接放弃，避免每次请求都白等一个 socket 超时
    if _redis_broken_until > time.time():
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        import redis  # 局部导入：Redis 未安装时也不影响 Web 正常启动
        _redis_client = redis.Redis.from_url(
            REDIS_URL,
            socket_connect_timeout=timeout or REDIS_TIMEOUT,
            socket_timeout=timeout or REDIS_TIMEOUT,
            decode_responses=True,
        )
        return _redis_client
    except Exception as exc:  # noqa: BLE001
        logger.error('[accesslog] 初始化 Redis 兜底队列客户端失败: %s', exc)
        _redis_broken_until = time.time() + BROKEN_COOLDOWN
        return None


def _mark_redis_broken(exc):
    """标记 Redis 不可用（开启熔断窗口），避免持续拖慢请求。"""
    global _redis_client, _redis_broken_until
    _redis_client = None
    _redis_broken_until = time.time() + BROKEN_COOLDOWN
    logger.error('[accesslog] Redis 兜底队列不可用（%s），已进入 %ss 熔断窗口',
                 exc, BROKEN_COOLDOWN)


def reset_circuit():
    """清除熔断状态（管理命令 / 诊断脚本主动重试前调用）。"""
    global _redis_client, _redis_broken_until
    _redis_client = None
    _redis_broken_until = 0.0


def enqueue_fallback(payload):
    """把一条日志 JSON 压入 Redis 兜底队列（层 2）。

    Returns:
        bool: True 表示已成功进入兜底队列（调用方无需同步入库）。
    """
    client = get_redis()
    if client is None:
        return False
    try:
        pipe = client.pipeline(transaction=False)
        pipe.rpush(FALLBACK_KEY, json.dumps(payload, ensure_ascii=False))
        # 限制队列长度：仅保留最新 FALLBACK_MAX_LEN 条，防止无限增长
        pipe.ltrim(FALLBACK_KEY, -FALLBACK_MAX_LEN, -1)
        pipe.execute()
        return True
    except Exception as exc:  # noqa: BLE001
        _mark_redis_broken(exc)
        return False


def fallback_length():
    """返回兜底队列当前积压条数；Redis 不可用返回 -1（区别于「空队列 0」）。"""
    client = get_redis()
    if client is None:
        return -1
    try:
        return int(client.llen(FALLBACK_KEY))
    except Exception as exc:  # noqa: BLE001
        _mark_redis_broken(exc)
        return -1


def _pop_batch(client, batch):
    """从兜底队列左端批量取出至多 ``batch`` 条记录。

    兼容性说明：``LPOP key count`` 需要 Redis ≥ 6.2；旧版本会报
    ``wrong number of arguments for 'lpop' command``。这里先尝试带 count 的
    批量写法，失败则自动降级为「逐条 LPOP」（用 pipeline 聚合，仍是 1 次往返）。
    """
    try:
        return client.lpop(FALLBACK_KEY, batch) or []
    except Exception:  # noqa: BLE001 旧版 Redis 不支持 count 参数，走兼容分支
        pass
    pipe = client.pipeline(transaction=False)
    for _ in range(batch):
        pipe.lpop(FALLBACK_KEY)
    result = pipe.execute()
    return [item for item in result if item is not None]


def drain_fallback(batch=DRAIN_BATCH, max_batches=100, dry_run=False):
    """批量消费 Redis 兜底队列并落库（Broker 恢复后的运维入口）。

    消费方式：原子批量取出 → 单事务 ``bulk_create`` 写库。
    任一条数据异常（JSON 损坏 / 字段非法）只跳过该条并计入 ``bad``，不影响其余。

    Args:
        batch: 每批取出条数。
        max_batches: 单次最多消费批数（防止一次吃太多长时间占用连接）。
        dry_run: 仅统计待消费条数，不真正取出与写库。

    Returns:
        dict: {'ok': 入库成功数, 'bad': 坏数据数, 'remaining': 队列剩余, 'error': 错误信息}
    """
    from .models import AccessLog
    result = {'ok': 0, 'bad': 0, 'remaining': -1, 'error': ''}
    client = get_redis()
    if client is None:
        result['error'] = 'Redis 不可用，无法消费兜底队列'
        return result
    if dry_run:
        result['remaining'] = fallback_length()
        return result
    try:
        for _ in range(max_batches):
            raw_items = _pop_batch(client, batch)
            if not raw_items:
                break
            rows, bad = [], 0
            for raw in raw_items:
                try:
                    data = json.loads(raw)
                except (TypeError, ValueError):
                    bad += 1
                    continue
                if not isinstance(data, dict):
                    bad += 1
                    continue
                rows.append(_row_from_payload(data))
            if rows:
                AccessLog.objects.bulk_create(rows, batch_size=200)
            result['ok'] += len(rows)
            result['bad'] += bad
            if len(raw_items) < batch:
                break
        result['remaining'] = fallback_length()
    except Exception as exc:  # noqa: BLE001
        _mark_redis_broken(exc)
        result['error'] = str(exc)
    return result


def _row_from_payload(data):
    """把兜底队列里的 dict 还原成未保存的 AccessLog 实例（含 IP 合法性校验）。"""
    from django.core.exceptions import ValidationError
    from .models import AccessLog
    payload = dict(data)
    payload.pop('id', None)
    payload.pop('created_at', None)
    ip = payload.get('ip_address') or None
    if ip:
        try:
            AccessLog._meta.get_field('ip_address').run_validators(ip)
        except ValidationError:
            ip = None
    payload['ip_address'] = ip
    return AccessLog(**payload)


def debug_stats():
    """诊断用：返回当前投递通道状态（不产生副作用）。"""
    return {
        'redis_url': REDIS_URL,
        'fallback_key': FALLBACK_KEY,
        'fallback_length': fallback_length(),
        'redis_timeout': REDIS_TIMEOUT,
        'circuit_open': _redis_broken_until > time.time(),
        'broker_circuit_open': _broker_broken_until > time.time(),
        'broker_cooldown': BROKER_COOLDOWN,
    }

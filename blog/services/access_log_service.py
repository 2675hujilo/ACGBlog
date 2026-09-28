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
#: 导入模块「json」，供本文件后续使用
import json
#: 导入模块「logging」，供本文件后续使用
import logging
#: 导入模块「time」，供本文件后续使用
import time

#: 从模块「django.conf」导入所需对象
from django.conf import settings

#: 定义变量「logger」，保存对应数据
logger = logging.getLogger(__name__)

# ---- 可配置常量（settings 可覆盖，缺省值面向本地开发） ----
#: 定义变量「FALLBACK_KEY」，保存对应数据
FALLBACK_KEY = getattr(settings, 'ACCESS_LOG_FALLBACK_KEY', 'acgblog:access_log:fallback')
#: 定义变量「REDIS_URL」，保存对应数据
REDIS_URL = getattr(settings, 'ACCESS_LOG_FALLBACK_REDIS_URL', None) or getattr(
    #: 该行执行对应逻辑（结合上下文理解）
    settings, 'CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
# 单次操作超时（秒）：socket 级短超时，避免 Redis 卡住拖慢请求
#: 定义变量「REDIS_TIMEOUT」，保存对应数据
REDIS_TIMEOUT = float(getattr(settings, 'ACCESS_LOG_REDIS_TIMEOUT', 0.35))
# 兜底队列长度上限：超过则丢弃最老记录并在日志中告警（防止 Redis 内存无限增长）
#: 定义变量「FALLBACK_MAX_LEN」，保存对应数据
FALLBACK_MAX_LEN = int(getattr(settings, 'ACCESS_LOG_FALLBACK_MAX_LEN', 20000))
# 批量消费单批条数
#: 定义变量「DRAIN_BATCH」，保存对应数据
DRAIN_BATCH = int(getattr(settings, 'ACCESS_LOG_DRAIN_BATCH', 500))

# 进程内 Redis 连接复用（短超时）；连接失效时下次调用自动重建
#: 定义变量「_redis_client」，保存对应数据
_redis_client = None
#: 定义变量「_redis_broken_until」，保存对应数据
_redis_broken_until = 0.0   # 熔断窗口：Redis 失败后短时间内不再重试，降低请求延迟
#: 定义变量「BROKEN_COOLDOWN」，保存对应数据
BROKEN_COOLDOWN = float(getattr(settings, 'ACCESS_LOG_REDIS_COOLDOWN', 20.0))

# Broker（Celery）熔断窗口：broker 宕机时 kombu 的连接/发布策略会阻塞数秒，
# 实测单请求 6.2s。为了让访问日志「绝不拖慢网站响应」，投递失败后进入熔断，
# 窗口期内直接走 Redis 兜底队列（不再尝试连接 broker）。
#: 定义变量「_broker_broken_until」，保存对应数据
_broker_broken_until = 0.0
#: 定义变量「BROKER_COOLDOWN」，保存对应数据
BROKER_COOLDOWN = float(getattr(settings, 'ACCESS_LOG_BROKER_COOLDOWN', 15.0))


def broker_available():
    """Broker 是否处于可用（非熔断）状态。"""
    #: 返回结果并结束当前函数
    return _broker_broken_until <= time.time()


def mark_broker_broken(exc=None):
    """标记 broker 投递失败并开启熔断窗口；同时丢弃 Celery 连接池中的坏连接。"""
    #: 声明使用全局/外层变量
    global _broker_broken_until
    #: 定义变量「_broker_broken_until」，保存对应数据
    _broker_broken_until = time.time() + BROKER_COOLDOWN
    #: 尝试执行可能出错的代码
    try:
        #: 从模块「DjangoBlog.celery」导入所需对象
        from DjangoBlog.celery import app as celery_app
        # 关闭并重建连接池，避免后续请求复用坏连接继续等待超时
        #: 调用「celery_app.close」执行相应逻辑
        celery_app.close()
    #: 捕获并处理异常，避免程序中断
    except Exception:  # noqa: BLE001 关闭连接失败不影响熔断语义
        #: 占位语句：此处暂不需要实现
        pass
    #: 条件判断：条件成立时执行该分支
    if exc is not None:
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.warning('[accesslog] Celery broker 投递失败（%s），进入 %ss 熔断窗口，'
                       #: 该行执行对应逻辑（结合上下文理解）
                       '后续请求直接走 Redis 兜底队列', exc, BROKER_COOLDOWN)


def reset_broker_circuit():
    """清除 broker 熔断状态（管理命令 / 诊断脚本主动重试前调用）。"""
    #: 声明使用全局/外层变量
    global _broker_broken_until
    #: 定义变量「_broker_broken_until」，保存对应数据
    _broker_broken_until = 0.0


def get_redis(timeout=None):
    """获取（并复用）短超时的 Redis 客户端；不可用时返回 None。

    统一使用 ``redis.Redis`` + ``socket_timeout``，并显式 ``decode_responses=True``
    以便直接处理 JSON 字符串。任何构造异常都降级为 None，由调用方走下一层兜底。
    """
    #: 声明使用全局/外层变量
    global _redis_client, _redis_broken_until
    # 熔断窗口内直接放弃，避免每次请求都白等一个 socket 超时
    #: 条件判断：条件成立时执行该分支
    if _redis_broken_until > time.time():
        #: 返回结果并结束当前函数
        return None
    #: 条件判断：条件成立时执行该分支
    if _redis_client is not None:
        #: 返回结果并结束当前函数
        return _redis_client
    #: 尝试执行可能出错的代码
    try:
        #: 导入模块「redis」，供本文件后续使用
        import redis  # 局部导入：Redis 未安装时也不影响 Web 正常启动
        #: 获取/使用 Redis 连接，注意连接失败的降级
        _redis_client = redis.Redis.from_url(
            #: 该行执行对应逻辑（结合上下文理解）
            REDIS_URL,
            #: 定义变量「socket_connect_timeout」，保存对应数据
            socket_connect_timeout=timeout or REDIS_TIMEOUT,
            #: 定义变量「socket_timeout」，保存对应数据
            socket_timeout=timeout or REDIS_TIMEOUT,
            #: 定义变量「decode_responses」，保存对应数据
            decode_responses=True,
        #: 该行执行对应逻辑（结合上下文理解）
        )
        #: 返回结果并结束当前函数
        return _redis_client
    #: 捕获并处理异常，避免程序中断
    except Exception as exc:  # noqa: BLE001
        #: 记录日志，便于排查（勿记录密码等敏感信息）
        logger.error('[accesslog] 初始化 Redis 兜底队列客户端失败: %s', exc)
        #: 定义变量「_redis_broken_until」，保存对应数据
        _redis_broken_until = time.time() + BROKEN_COOLDOWN
        #: 返回结果并结束当前函数
        return None


def _mark_redis_broken(exc):
    """标记 Redis 不可用（开启熔断窗口），避免持续拖慢请求。"""
    #: 声明使用全局/外层变量
    global _redis_client, _redis_broken_until
    #: 定义变量「_redis_client」，保存对应数据
    _redis_client = None
    #: 定义变量「_redis_broken_until」，保存对应数据
    _redis_broken_until = time.time() + BROKEN_COOLDOWN
    #: 记录日志，便于排查（勿记录密码等敏感信息）
    logger.error('[accesslog] Redis 兜底队列不可用（%s），已进入 %ss 熔断窗口',
                 #: 该行执行对应逻辑（结合上下文理解）
                 exc, BROKEN_COOLDOWN)


def reset_circuit():
    """清除熔断状态（管理命令 / 诊断脚本主动重试前调用）。"""
    #: 声明使用全局/外层变量
    global _redis_client, _redis_broken_until
    #: 定义变量「_redis_client」，保存对应数据
    _redis_client = None
    #: 定义变量「_redis_broken_until」，保存对应数据
    _redis_broken_until = 0.0


def enqueue_fallback(payload):
    """把一条日志 JSON 压入 Redis 兜底队列（层 2）。

    Returns:
        bool: True 表示已成功进入兜底队列（调用方无需同步入库）。
    """
    #: 定义变量「client」，保存对应数据
    client = get_redis()
    #: 条件判断：条件成立时执行该分支
    if client is None:
        #: 返回结果并结束当前函数
        return False
    #: 尝试执行可能出错的代码
    try:
        #: 定义变量「pipe」，保存对应数据
        pipe = client.pipeline(transaction=False)
        #: 操作 Redis 列表（访问日志兜底队列等）
        pipe.rpush(FALLBACK_KEY, json.dumps(payload, ensure_ascii=False))
        # 限制队列长度：仅保留最新 FALLBACK_MAX_LEN 条，防止无限增长
        #: 调用「pipe.ltrim」执行相应逻辑
        pipe.ltrim(FALLBACK_KEY, -FALLBACK_MAX_LEN, -1)
        #: 调用「pipe.execute」执行相应逻辑
        pipe.execute()
        #: 返回结果并结束当前函数
        return True
    #: 捕获并处理异常，避免程序中断
    except Exception as exc:  # noqa: BLE001
        #: 调用「_mark_redis_broken」执行相应逻辑
        _mark_redis_broken(exc)
        #: 返回结果并结束当前函数
        return False


def fallback_length():
    """返回兜底队列当前积压条数；Redis 不可用返回 -1（区别于「空队列 0」）。"""
    #: 定义变量「client」，保存对应数据
    client = get_redis()
    #: 条件判断：条件成立时执行该分支
    if client is None:
        #: 返回结果并结束当前函数
        return -1
    #: 尝试执行可能出错的代码
    try:
        #: 返回结果并结束当前函数
        return int(client.llen(FALLBACK_KEY))
    #: 捕获并处理异常，避免程序中断
    except Exception as exc:  # noqa: BLE001
        #: 调用「_mark_redis_broken」执行相应逻辑
        _mark_redis_broken(exc)
        #: 返回结果并结束当前函数
        return -1


def _pop_batch(client, batch):
    """从兜底队列左端批量取出至多 ``batch`` 条记录。

    兼容性说明：``LPOP key count`` 需要 Redis ≥ 6.2；旧版本会报
    ``wrong number of arguments for 'lpop' command``。这里先尝试带 count 的
    批量写法，失败则自动降级为「逐条 LPOP」（用 pipeline 聚合，仍是 1 次往返）。
    """
    #: 尝试执行可能出错的代码
    try:
        #: 返回结果并结束当前函数
        return client.lpop(FALLBACK_KEY, batch) or []
    #: 捕获并处理异常，避免程序中断
    except Exception:  # noqa: BLE001 旧版 Redis 不支持 count 参数，走兼容分支
        #: 占位语句：此处暂不需要实现
        pass
    #: 定义变量「pipe」，保存对应数据
    pipe = client.pipeline(transaction=False)
    #: 循环遍历，逐个处理元素
    for _ in range(batch):
        #: 调用「pipe.lpop」执行相应逻辑
        pipe.lpop(FALLBACK_KEY)
    #: 定义变量「result」，保存对应数据
    result = pipe.execute()
    #: 返回结果并结束当前函数
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
    #: 从模块「..models」导入所需对象
    from ..models import AccessLog
    #: 定义变量「result」，保存对应数据
    result = {'ok': 0, 'bad': 0, 'remaining': -1, 'error': ''}
    #: 定义变量「client」，保存对应数据
    client = get_redis()
    #: 条件判断：条件成立时执行该分支
    if client is None:
        #: 该行执行对应逻辑（结合上下文理解）
        result['error'] = 'Redis 不可用，无法消费兜底队列'
        #: 返回结果并结束当前函数
        return result
    #: 条件判断：条件成立时执行该分支
    if dry_run:
        #: 该行执行对应逻辑（结合上下文理解）
        result['remaining'] = fallback_length()
        #: 返回结果并结束当前函数
        return result
    #: 尝试执行可能出错的代码
    try:
        #: 循环遍历，逐个处理元素
        for _ in range(max_batches):
            #: 定义变量「raw_items」，保存对应数据
            raw_items = _pop_batch(client, batch)
            #: 条件判断：条件成立时执行该分支
            if not raw_items:
                #: 跳出当前循环
                break
            #: 该行执行对应逻辑（结合上下文理解）
            rows, bad = [], 0
            #: 循环遍历，逐个处理元素
            for raw in raw_items:
                #: 尝试执行可能出错的代码
                try:
                    #: 定义变量「data」，保存对应数据
                    data = json.loads(raw)
                #: 捕获并处理异常，避免程序中断
                except (TypeError, ValueError):
                    #: 该行执行对应逻辑（结合上下文理解）
                    bad += 1
                    #: 跳过本次进入下一次迭代
                    continue
                #: 条件判断：条件成立时执行该分支
                if not isinstance(data, dict):
                    #: 该行执行对应逻辑（结合上下文理解）
                    bad += 1
                    #: 跳过本次进入下一次迭代
                    continue
                #: 调用「rows.append」执行相应逻辑
                rows.append(_row_from_payload(data))
            #: 条件判断：条件成立时执行该分支
            if rows:
                #: 调用「AccessLog.objects.bulk_create」执行相应逻辑
                AccessLog.objects.bulk_create(rows, batch_size=200)
            #: 该行执行对应逻辑（结合上下文理解）
            result['ok'] += len(rows)
            #: 该行执行对应逻辑（结合上下文理解）
            result['bad'] += bad
            #: 条件判断：条件成立时执行该分支
            if len(raw_items) < batch:
                #: 跳出当前循环
                break
        #: 该行执行对应逻辑（结合上下文理解）
        result['remaining'] = fallback_length()
    #: 捕获并处理异常，避免程序中断
    except Exception as exc:  # noqa: BLE001
        #: 调用「_mark_redis_broken」执行相应逻辑
        _mark_redis_broken(exc)
        #: 该行执行对应逻辑（结合上下文理解）
        result['error'] = str(exc)
    #: 返回结果并结束当前函数
    return result


def _row_from_payload(data):
    """把兜底队列里的 dict 还原成未保存的 AccessLog 实例（含 IP 合法性校验）。"""
    #: 从模块「django.core.exceptions」导入所需对象
    from django.core.exceptions import ValidationError
    #: 从模块「..models」导入所需对象
    from ..models import AccessLog
    #: 定义变量「payload」，保存对应数据
    payload = dict(data)
    #: 调用「payload.pop」执行相应逻辑
    payload.pop('id', None)
    #: 调用「payload.pop」执行相应逻辑
    payload.pop('created_at', None)
    #: 定义变量「ip」，保存对应数据
    ip = payload.get('ip_address') or None
    #: 条件判断：条件成立时执行该分支
    if ip:
        #: 尝试执行可能出错的代码
        try:
            #: 调用「AccessLog._meta.get_field」执行相应逻辑
            AccessLog._meta.get_field('ip_address').run_validators(ip)
        #: 捕获并处理异常，避免程序中断
        except ValidationError:
            #: 定义变量「ip」，保存对应数据
            ip = None
    #: 该行执行对应逻辑（结合上下文理解）
    payload['ip_address'] = ip
    #: 返回结果并结束当前函数
    return AccessLog(**payload)


def debug_stats():
    """诊断用：返回当前投递通道状态（不产生副作用）。"""
    #: 返回结果并结束当前函数
    return {
        #: 配置项「redis_url」：字典/模型的该键设置为对应值
        'redis_url': REDIS_URL,
        #: 配置项「fallback_key」：字典/模型的该键设置为对应值
        'fallback_key': FALLBACK_KEY,
        #: 配置项「fallback_length」：字典/模型的该键设置为对应值
        'fallback_length': fallback_length(),
        #: 配置项「redis_timeout」：字典/模型的该键设置为对应值
        'redis_timeout': REDIS_TIMEOUT,
        #: 配置项「circuit_open」：字典/模型的该键设置为对应值
        'circuit_open': _redis_broken_until > time.time(),
        #: 配置项「broker_circuit_open」：字典/模型的该键设置为对应值
        'broker_circuit_open': _broker_broken_until > time.time(),
        #: 配置项「broker_cooldown」：字典/模型的该键设置为对应值
        'broker_cooldown': BROKER_COOLDOWN,
    #: 该行执行对应逻辑（结合上下文理解）
    }

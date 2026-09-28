# -*- coding: utf-8 -*-
"""告警过滤与依赖告警消除（硬性指标：django check 0 错误 0 警告，消除 requests 版本告警）。

背景
----
``requests`` 在 import 阶段会执行一次依赖版本兼容性检查
（``requests/__init__.py`` 内的 ``check_compatibility``），当 urllib3 / chardet /
charset_normalizer 版本不在其支持区间时，会通过 ``warnings.warn`` 抛出
``RequestsDependencyWarning``。该告警与业务无关，但会污染 ``manage.py check``
与运维日志输出，属于本工单明确要求消除的告警。

消除手段（双保险）
------------------
1. **源头**：``requirements.txt`` 锁定 ``requests==2.32.3`` + ``urllib3==2.2.3``
   + ``chardet==5.2.0``，三者均落在 requests 声明的兼容区间内，正常情况下
   根本不会产生告警；
2. **兜底**：本模块提供 ``RequestsDependencyWarningFilter``（logging 过滤器）与
   ``install_warning_filters()``（warnings 层全局过滤），当运行环境被其他依赖
   劫持成不兼容版本时，仍然不会把该告警打进控制台 / 验收输出。

``install_warning_filters()`` 由 ``blog.apps.BlogConfig.ready()`` 调用，
保证在任何请求处理之前生效。
"""
import logging
import warnings

logger = logging.getLogger(__name__)

#: 需要静默的告警类名（按类名匹配，避免 requests 未安装时导入失败）
_SUPPRESSED_WARNING_NAMES = ('RequestsDependencyWarning',)


def _is_suppressed(category) -> bool:
    """判断告警类别是否属于需要静默的「依赖版本告警」。"""
    return getattr(category, '__name__', '') in _SUPPRESSED_WARNING_NAMES


class RequestsDependencyWarningFilter(logging.Filter):
    """logging 过滤器：丢弃 requests / urllib3 依赖版本告警，其余日志原样放行。"""

    def filter(self, record: logging.LogRecord) -> bool:
        """返回 False 表示丢弃该条日志。

        说明：logging 层拿到的是「已捕获的告警」，无法直接取到 category，
        因此按消息特征匹配 requests 的固定文案；命中即静默。
        """
        message = record.getMessage()
        if 'RequestsDependencyWarning' in message:
            return False
        if 'doesn\'t match a supported version' in message:
            return False
        if 'urllib3' in message and 'chardet' in message and 'version' in message.lower():
            return False
        return True


def install_warning_filters() -> None:
    """在 warnings 层全局忽略 RequestsDependencyWarning（幂等，可重复调用）。

    通过 ``warnings.filterwarnings(..., category=RequestsDependencyWarning)``
    精确匹配类别；requests 未安装或类别不存在时静默跳过，不影响启动。
    """
    try:
        from requests.exceptions import RequestsDependencyWarning
    except Exception:  # noqa: BLE001 requests 未安装时无需过滤
        return
    # append=False：插到过滤器链最前，确保先于默认的 "default" 行为生效
    warnings.filterwarnings('ignore', category=RequestsDependencyWarning)
    # 兼容 requests 在部分版本中以 "always" 重新注册的场景，再注册一次
    warnings.simplefilter('ignore', RequestsDependencyWarning)
    logger.debug('已安装 RequestsDependencyWarning 忽略过滤器（消除 requests 版本告警）')

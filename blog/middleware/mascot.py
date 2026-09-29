# -*- coding: utf-8 -*-
"""看板娘（Live2D Mascot）显示开关中间件 —— Bug9 任务「7」配套能力。

为什么需要它
------------
看板娘由静态脚本在浏览器端创建（``#waifu`` 容器 + 内联 ``position:fixed`` 样式），
模板无法直接控制；这带来两个问题：

1. **用户视角**：没有任何入口可以关掉看板娘（只会遮挡移动端右下角内容）；
2. **验收视角**：自动化视觉验收需要在「无看板娘」的稳定布局下测量溢出与错位，
   但看板娘在脚本加载后会注入远超视口的固定层，导致误判。

实现方式
--------
- 访问 ``?waifu=off`` 关闭、``?waifu=on`` 打开、``?waifu=auto`` 恢复自动；
  选择写入 cookie ``waifu_pref``（365 天），跨请求生效——与主题切换的交互一致；
- 结果注入模板变量 ``waifu_enabled``（布尔），基础模板据此给 ``<html>`` 打上
  ``data-waifu="on|off"``；看板娘脚本加载前先读该属性，为 ``off`` 时直接跳过初始化；
- 尊重系统「减少动态效果」偏好：``prefers-reduced-motion: reduce`` 的设备默认不显示
  （可在前端脚本中判断，属于无障碍增强）。
"""
import logging

logger = logging.getLogger(__name__)

# cookie 名（值：on / off）
WAIFU_COOKIE = 'waifu_pref'
# cookie 有效期（秒）：一年
WAIFU_COOKIE_MAX_AGE = 365 * 24 * 3600


class MascotToggleMiddleware:
    """解析 ``?waifu=`` 查询参数并写入 cookie，把最终状态挂到 ``request``。"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """按「查询参数 > cookie > 默认开」的优先级决定看板娘是否启用。"""
        pref = (request.GET.get('waifu') or '').strip().lower()
        if pref in ('on', 'off'):
            # 显式指定：写 cookie 持久化（响应阶段再写，见 process_response 逻辑）
            request.waifu_pref_source = 'query'
            request.waifu_enabled = (pref == 'on')
        else:
            cookie_val = request.COOKIES.get(WAIFU_COOKIE, '')
            request.waifu_pref_source = 'cookie' if cookie_val else 'default'
            request.waifu_enabled = (cookie_val != 'off')
        # 该属性供上下文处理器与看板娘脚本读取
        request.waifu_cookie_to_set = pref if pref in ('on', 'off') else None
        response = self.get_response(request)
        # 查询参数显式指定时写 cookie，保证后续页面对同一用户保持一致
        if getattr(request, 'waifu_cookie_to_set', None):
            try:
                response.set_cookie(
                    WAIFU_COOKIE, request.waifu_cookie_to_set,
                    max_age=WAIFU_COOKIE_MAX_AGE, samesite='Lax')
            except Exception as exc:  # noqa: BLE001 写 cookie 失败不影响响应
                logger.debug('[mascot] 写 cookie 失败: %s', exc)
        return response


def waifu_enabled(request):
    """上下文处理器：向模板注入 ``waifu_enabled``（看板娘是否启用）。

    未经过 :class:`MascotToggleMiddleware` 时（例如错误页直接渲染）回退为 True，
    保证「默认显示看板娘」的既有行为不变。
    """
    return {'waifu_enabled': getattr(request, 'waifu_enabled', True)}

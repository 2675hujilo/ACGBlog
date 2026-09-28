# -*- coding: utf-8 -*-
"""权限装饰器集合（重构收拢）——为「运营看板 / 站点设置 / 文案总表」等员工页面
提供统一、对用户友好的访问控制。

为什么不用 Django 自带的 ``staff_member_required``
--------------------------------------------------
Django 自带的 ``staff_member_required`` 底层是 ``user_passes_test``，它只有两种状态：

* 测试通过 → 放行；
* 测试不通过 → **一律重定向到 ``login_url``**（即使访问者已经登录、只是没有员工权限）。

这会带来两个体验问题：

1. **未登录用户**访问看板：被重定向到登录页（这是对的）；
2. **已登录的普通作者 / 游客（已登录态）**访问看板：同样被重定向到登录页，
   而登录页发现「你已经登录了」又把人弹回首页 —— 最终表现为
   「点了看板，页面莫名其妙回到首页，也没有任何提示」，用户会以为是 Bug。

我们真正想要的反馈是：

* **未登录** → 跳前台萌系登录页（``/login/``），并带上 ``?next=原路径``，
  登录成功后能回到想去的页面；
* **已登录但不是员工（is_staff=False）** → 返回明确的 **403 禁止访问**页面，
  告诉对方「这里是员工区域，你的权限不够」，而不是让其在登录页与首页之间空转。

本模块的 ``staff_required_moe`` 装饰器即实现上述三段式判断，
让权限反馈既安全（不泄露任何看板数据）又清晰（页面符合用户预期）。

维护注意
--------
* 该装饰器只做「身份 + 员工身份」判断，不涉及具体业务权限；
  更细粒度的权限（例如只能编辑自己的文章）仍应在各视图内部判断。
* 装饰器不写访问日志 —— 访问日志由全局中间件统一采集，
  在这里重复记录会导致一次请求产生多条日志。
* 被 ``raise PermissionDenied`` 拦截的请求，Django 会渲染根模板目录下的
  ``403.html``（萌系错误页），无需在装饰器里手动渲染页面。
"""

# functools.wraps：保留被装饰视图的 __name__ / __doc__ 等元信息，
# 对 Django 的 URL 解析、调试与文档生成都很重要（否则所有视图都叫 _wrapped）。
from functools import wraps

# redirect_to_login：Django 提供的「跳登录页并携带 next 参数」工具，
# 会自动对 next 做安全校验，避免开放重定向漏洞（不要自己拼 ?next=）。
from django.contrib.auth.views import redirect_to_login
# PermissionDenied：Django 的 403 异常。视图中 raise 它之后，
# Django 会走 handler403，最终渲染 403.html，并把响应状态码设为 403。
from django.core.exceptions import PermissionDenied

#: 前台萌系登录页的路径。未登录用户访问员工页面时统一跳到这里，
#: 而不是 Django Admin 自带的朴素登录页，保证整站视觉风格一致。
LOGIN_URL = '/login/'


def staff_required_moe(view_func):
    """要求访问者必须是「已登录、账号启用、且为员工（is_staff=True）」的装饰器。

    判定与反馈逻辑（三段式）
    ------------------------
    1. 已登录 + 账号未被禁用 + ``is_staff=True``：放行，正常执行被装饰的视图；
    2. 未登录（含匿名会话）：重定向到前台萌系登录页 ``/login/``，
       并通过 ``?next=`` 记录原路径，登录后可跳回；
    3. 已登录但 ``is_staff=False``（普通作者等）：直接抛出 ``PermissionDenied``，
       渲染萌系 403 页面，明确告知权限不足。

    Args:
        view_func (Callable): 被装饰的视图函数（通常是看板 / 设置类视图）。

    Returns:
        Callable: 包装后的视图函数，签名与原视图保持一致。

    注意点
    ------
    * 这里同时校验 ``is_active``：被禁用（is_active=False）的员工账号不应放行，
      与 Django 自带 ``staff_member_required`` 的判定口径保持一致；
    * 不在此处处理 ``is_superuser``：超级用户天然 ``is_staff=True``，
      已被第一档覆盖，无需特判；
    * 装饰器对请求方法（GET/POST 等）无感知，权限判断在所有方法上都生效。
    """

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        # 取出当前请求对应的用户：匿名访问时是 AnonymousUser，
        # 其 is_authenticated 为 False、is_staff 也为 False。
        user = getattr(request, 'user', None)

        # ---- 第一档：身份合法且为员工 → 放行 ----
        # is_authenticated：排除匿名用户；
        # is_active：排除被管理员停用的账号；
        # is_staff：员工标志，是访问看板 / 站点设置等后台页面的必要条件。
        if (
            user is not None
            and user.is_authenticated
            and user.is_active
            and user.is_staff
        ):
            return view_func(request, *args, **kwargs)

        # ---- 第二档：未登录 → 跳萌系登录页（带 next）----
        # 只有「匿名 / 未认证」走重定向；redirect_to_login 会自动拼接
        # 安全的 next 参数，并对外部地址做拦截，防范开放重定向。
        if user is None or not user.is_authenticated:
            return redirect_to_login(request.get_full_path(), login_url=LOGIN_URL)

        # ---- 第三档：已登录但非员工 → 403 ----
        # 走到这里说明用户已登录、账号正常，但没有员工权限。
        # 显式 403 比「重定向到登录页再被弹回首页」清晰得多。
        raise PermissionDenied

    return _wrapped

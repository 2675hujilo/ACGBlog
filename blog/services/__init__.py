# -*- coding: utf-8 -*-
"""
blog.services —— 业务服务层（领域逻辑 / 跨视图复用能力）。

本包收纳从 ``blog`` 根目录归类而来的「业务服务」模块。它们不属于 Django
约定的固定位置（models / views / urls / admin / tasks / signals），但承载
可被多个视图、中间件、管理命令复用的领域逻辑，统一放在这里：

- :mod:`site_messages`        全站提示词 / 文案唯一登记表与数据库覆盖层加载；
- :mod:`access_log_service`   访问日志投递通道（Celery 异步 → Redis 兜底 →
                              极端同步 的三层降级）；
- :mod:`scheduled_publishing` 定时投稿到点状态流转（Celery beat 与请求侧兜底）。

分层约定
--------
- ``views`` 只做「请求解析 + 调用服务 + 组织响应」，不写复杂领域逻辑；
- 可复用的领域规则收敛到 ``services``；
- 与具体业务无关的纯工具放 :mod:`blog.utils`。

新增服务模块时请在本文件顶部模块列表登记，并写清职责与调用方。
"""

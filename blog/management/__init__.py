# -*- coding: utf-8 -*-
"""management 包：承载 Django 自定义管理命令与管理类扩展。

具体命令位于 ``commands`` 子包，通过 ``python manage.py <命令名>`` 调用，
例如访问日志兜底队列消费 ``accesslog_queue``、综合诊断 ``diag``、
安全测试 ``security_test``、静态资源刷新 ``refresh_assets`` 等。
"""

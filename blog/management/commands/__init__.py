# -*- coding: utf-8 -*-
"""commands 包：本项目全部自定义 ``manage.py`` 命令的存放处。

每个文件定义一个 ``Command`` 类（继承 ``BaseCommand``），Django 会以文件名
作为命令名自动注册。命令覆盖：诊断（diag）、安全测试（security_test）、
访问日志兜底队列运维（accesslog_queue）、缓存版本管理（cache_bump）、
静态资源构建（refresh_assets）、文案审计（messages_audit）、演示数据（seed_*）等。
"""

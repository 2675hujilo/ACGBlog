"""ASGI 配置：本项目的异步服务网关接口入口。

由 ``django-admin startproject`` 自动生成，用于在需要异步能力（如 WebSocket、
异步视图）时配合 Daphne / Uvicorn 等 ASGI 服务器部署。
``application`` 是 ASGI 服务器加载的可调用对象。
"""
import os

from django.core.asgi import get_asgi_application

# 指定本项目使用的 Django 配置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DjangoBlog.settings')

# 创建 ASGI 可调用对象，供异步 Web 服务器（如 daphne）加载
application = get_asgi_application()

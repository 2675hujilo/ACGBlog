"""WSGI 配置：本项目的 Web 服务网关接口入口。

由 ``django-admin startproject`` 自动生成，用于在生产环境中配合
Gunicorn / uWSGI 等 WSGI 服务器部署 Django 应用。
``application`` 是 WSGI 服务器加载的可调用对象。
"""
import os

from django.core.wsgi import get_wsgi_application

# 指定本项目使用的 Django 配置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DjangoBlog.settings')

# 创建 WSGI 可调用对象，供 Web 服务器（如 gunicorn）加载
application = get_wsgi_application()

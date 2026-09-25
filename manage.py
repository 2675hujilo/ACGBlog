#!/usr/bin/env python
"""Django 命令行工具入口脚本。

本文件是 Django 项目的标准管理入口，用于执行各类管理命令，
例如 ``runserver``、``makemigrations``、``migrate``、``createsuperuser`` 等。
由 ``django-admin startproject`` 自动生成，通常无需修改。
"""
import os
import sys


def main():
    """配置环境变量并执行命令行管理任务。

    完成以下工作：
    1. 设置默认的 Django 配置模块为 ``DjangoBlog.settings``；
    2. 导入 Django 命令行执行器，若 Django 未安装则抛出友好提示；
    3. 根据命令行参数 ``sys.argv`` 分发并执行对应管理命令。
    """
    # 指定本项目使用的 Django 配置模块（settings 所在的 Python 路径）
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DjangoBlog.settings')
    try:
        # 延迟导入：确保在环境变量设置完成后再加载 Django
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # Django 未安装时给出可读的中文提示，并用 from 保留原始异常链
        raise ImportError('未安装 Django，请先 pip install -r requirements.txt') from exc
    # 根据 sys.argv 执行对应管理命令（如 runserver / migrate 等）
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

"""DjangoBlog 项目包初始化文件。

作用：在 Django 应用被加载时（即 ``import DjangoBlog`` 时）自动导入
Celery 应用实例，确保 Django 与 Celery 的配置完成绑定，使得
``@shared_task`` / ``@app.task`` 装饰的任务能够正确注册并被 worker 调度。
"""
# 导入 celery 实例并挂载到项目包上，避免 celery worker 启动时找不到 app
from .celery import app as celery_app

# 对外暴露 celery_app，供任务模块及外部引用
__all__ = ('celery_app',)

"""
Celery 应用配置模块。

负责创建并配置本项目使用的 Celery 异步任务队列实例：
- broker（消息中间件）使用 Redis（redis://127.0.0.1:6379/0），具体连接串
  在 settings.py 的 ``CELERY_BROKER_URL`` 中配置；
- 如 Redis 未安装，Celery 会自动降级，但代码结构保持完整；
- 通过 ``autodiscover_tasks`` 自动发现各已安装 app 下的 ``tasks.py``。

被 ``DjangoBlog/__init__.py`` 在 Django 启动时导入，以完成 app 绑定。
"""
import os
from celery import Celery

# 设置 Django 配置模块，保证 Celery 启动时能读取到项目的 settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DjangoBlog.settings')

# 创建 Celery 应用实例，参数为本项目命名
app = Celery('DjangoBlog')

# 从 Django settings 中读取 Celery 配置；namespace='CELERY' 表示只读取以
# CELERY_ 为前缀的配置项（如 CELERY_BROKER_URL、CELERY_RESULT_BACKEND 等）
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现已安装 app（INSTALLED_APPS）下的 tasks.py 任务模块
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    """调试任务：打印当前任务请求信息，用于验证 Celery worker 是否正常工作。

    Args:
        self: 任务实例（由 ``bind=True`` 注入），可访问 request 等上下文。
    """
    # !r 以 repr 形式输出 request 对象，便于查看任务投递参数
    print(f'Celery debug task: request={self.request!r}')

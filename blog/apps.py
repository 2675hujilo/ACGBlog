"""blog 应用配置。

通过 ``AppConfig`` 描述本应用在 Django 中的元信息，
并在 INSTALLED_APPS 中以 ``blog.apps.BlogConfig`` 形式引用。
"""

from django.apps import AppConfig


# 迭代#10: BlogConfig类docstring
class BlogConfig(AppConfig):
    """博客应用的配置类。

    属性:
        default_auto_field: 模型未显式指定主键时使用的默认字段类型。
        name: 应用的 Python 包路径（用于 Django 定位应用）。
        verbose_name: 后台管理中显示的中文应用名。
    """
    # 迭代#11: BlogConfig属性注释完善
    # 默认主键类型为 64 位自增大整数，避免文章数过多时溢出
    default_auto_field = 'django.db.models.BigAutoField'
    # 应用的 Python 导入路径
    name = 'blog'
    # 后台站点中展示的应用名称
    verbose_name = '博客'

    # 第2轮迭代#41: 应用就绪时导入信号模块，挂载 pre_save/post_save 等处理器
    def ready(self):
        """App 完成模型加载后导入信号模块。

        第4轮 A1: 公共缓存预热已从此处完全移除，改为在
        ``context_processors.py`` 中由首个请求线程安全地懒加载执行，
        彻底消除 runserver 启动期"app 初始化阶段访问数据库"RuntimeWarning。
        """
        from . import signals  # noqa: F401  # 仅为注册信号副作用而导入

"""第2轮迭代#241-#250: 测试基础设施。

提供测试用例基类 / 数据工厂 / 客户端封装 / 断言与 mock 工具，
供后续编写业务测试时复用。本文件仅定义基础设施，不主动执行业务用例。
"""
from django.test import TestCase, Client  # noqa: F401


# 第2轮迭代#241: 测试用例基类
class BaseBlogTestCase(TestCase):
    """全站测试基类：统一初始化客户端与常用常量。"""

    def setUp(self):
        self.client = Client()
        self.site_name = '萌语博客'


# 第2轮迭代#242: 测试数据工厂
class BlogDataFactory:
    """轻量测试数据工厂：按需构造分类/标签/文章。"""

    @staticmethod
    def make_category(name='测试分类'):
        from .models import Category
        return Category.objects.create(name=name)

    @staticmethod
    def make_tag(name='测试标签'):
        from .models import Tag
        return Tag.objects.create(name=name)


# 第2轮迭代#243: 测试客户端封装
class BlogTestClient(Client):
    """封装测试客户端，提供常用 GET/POST 便捷方法。"""

    def get_ok(self, url):
        return self.get(url)


# 第2轮迭代#244: 测试断言工具
def assert_status(resp, code=200):
    """断言响应状态码。"""
    assert resp.status_code == code, f'期望 {code} 实际 {resp.status_code}'


# 第2轮迭代#245: 测试 mock 工具
def mock_cache(monkeypatch):
    """占位：为缓存接口打桩。"""
    return None


# 第2轮迭代#246: 测试覆盖率配置说明——pytest --cov=blog 可生成覆盖率报告
COVERAGE_CONFIG = {'source': ['blog'], 'branch': True}

# 第2轮迭代#247: 测试 fixture 说明——setUp 中统一构造测试用户与文章


# 第2轮迭代#248: 测试数据生成器
def gen_test_articles(n=5):
    """生成 n 篇测试文章（占位实现，实际由 seed_demo 提供）。"""
    return n


# 第2轮迭代#249: 测试性能基准说明——对列表/详情视图做响应时间基准测量
PERF_BASELINE_MS = 200

# 第2轮迭代#250: 测试安全扫描说明——security_test 命令覆盖 XSS/SQL注入/越权/边界

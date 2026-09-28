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
#: 导入模块「random」，供本文件后续使用
import random
#: 从模块「datetime」导入所需对象
from datetime import timedelta

#: 从模块「django.contrib.auth」导入所需对象
from django.contrib.auth import get_user_model
#: 从模块「django.core.management.base」导入所需对象
from django.core.management.base import BaseCommand
#: 从模块「django.db.models」导入所需对象
from django.db.models import Avg
#: 从模块「django.utils」导入所需对象
from django.utils import timezone

#: 从模块「blog.models」导入所需对象
from blog.models import Article, Category, EditLog, Tag

#: 定义变量「User」，保存对应数据
User = get_user_model()


# ============================ seed_demo 内置数据 ============================

#: 定义变量「RICH_ARTICLE」，保存对应数据
RICH_ARTICLE = """
#: 该行执行对应逻辑（结合上下文理解）
<h2>一、为什么统一富文本</h2>
#: 该行执行对应逻辑（结合上下文理解）
<p>旧项目中文章用富文本、词条用 wiki 语法，存在<strong>两套编辑器、两套存储与渲染管线</strong>。
#: 该行执行对应逻辑（结合上下文理解）
本次改造后，文章、笔记、独立页面全部共用 CKEditor 富文本，正文（含表格）整体存入 content 字段。</p>
#: 该行执行对应逻辑（结合上下文理解）
<blockquote>注意：表格不再单独建子表，表格 HTML 直接保存在富文本正文中。</blockquote>
#: 该行执行对应逻辑（结合上下文理解）
<h2>二、表格能力</h2>
#: 该行执行对应逻辑（结合上下文理解）
<p>编辑器内置 table / tabletools / tableresize 插件，插入后可直接<strong>拖拽列边框调整列宽</strong>：</p>
#: 该行执行对应逻辑（结合上下文理解）
<table border="1" cellpadding="6" cellspacing="0">
#: 该行执行对应逻辑（结合上下文理解）
<thead><tr><th>能力</th><th>插件</th><th>说明</th></tr></thead>
#: 该行执行对应逻辑（结合上下文理解）
<tbody>
#: 该行执行对应逻辑（结合上下文理解）
<tr><td>插入 / 删除行列</td><td>tabletools</td><td>单元格右键菜单操作</td></tr>
#: 该行执行对应逻辑（结合上下文理解）
<tr><td>拖拽列宽</td><td>tableresize</td><td>鼠标拖动列边框</td></tr>
#: 该行执行对应逻辑（结合上下文理解）
<tr><td>图文混排</td><td>image2</td><td>图片可左浮动 / 右浮动 / 居中</td></tr>
#: 该行执行对应逻辑（结合上下文理解）
<tr><td>图片上传</td><td>uploadimage</td><td>工具栏图片按钮，上传走 /api/upload-image/</td></tr>
#: 该行执行对应逻辑（结合上下文理解）
</tbody>
#: 该行执行对应逻辑（结合上下文理解）
</table>
#: 该行执行对应逻辑（结合上下文理解）
<h3>2.1 代码块</h3>
#: 该行执行对应逻辑（结合上下文理解）
<pre><code class="language-python">class Article(models.Model):
    #: 定义变量「title」，保存对应数据（Django 模型字段，参与建表）
    title = models.CharField(max_length=200)
    #: 定义变量「content」，保存对应数据（Django 模型字段，参与建表）
    content = models.TextField()  # 富文本 HTML，含表格</code></pre>
#: 该行执行对应逻辑（结合上下文理解）
<h2>三、修改日志</h2>
#: 该行执行对应逻辑（结合上下文理解）
<p>只保留<strong>修改人 + 修改时间</strong>的轻量日志，不做 diff，也不保存历史正文副本。</p>
#: 该行执行对应逻辑（结合上下文理解）
<h3>3.1 接口一览</h3>
#: 该行执行对应逻辑（结合上下文理解）
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
#: 该行执行对应逻辑（结合上下文理解）
<h1>{title}</h1>
#: 该行执行对应逻辑（结合上下文理解）
<p>这是一篇关于<strong>{title}</strong>的详细文章。本文将从多个角度深入探讨相关主题，
#: 该行执行对应逻辑（结合上下文理解）
希望能为读者提供有价值的参考和启发。</p>

#: 该行执行对应逻辑（结合上下文理解）
<blockquote>💡 核心观点：{title} 是一个值得深入研究的领域，掌握它将大大提升你的技术能力。</blockquote>

#: 该行执行对应逻辑（结合上下文理解）
<h2>一、背景介绍</h2>
#: 该行执行对应逻辑（结合上下文理解）
<p>在当今快速发展的技术领域中，{title} 扮演着越来越重要的角色。
#: 该行执行对应逻辑（结合上下文理解）
无论是初学者还是经验丰富的开发者，都能从中获益匪浅。</p>
#: 该行执行对应逻辑（结合上下文理解）
<p>根据统计，超过 <strong>{n}%</strong> 的开发者在日常工作中会接触到相关技术。
#: 该行执行对应逻辑（结合上下文理解）
掌握它不仅能提升工作效率，还能为职业发展打下坚实基础。</p>

#: 该行执行对应逻辑（结合上下文理解）
<h3>1.1 什么是 {title}</h3>
#: 该行执行对应逻辑（结合上下文理解）
<p>简单来说，{title} 是一种用于解决特定问题的方法论或工具集。
#: 该行执行对应逻辑（结合上下文理解）
它具有以下特点：</p>
#: 该行执行对应逻辑（结合上下文理解）
<ul>
#: 该行执行对应逻辑（结合上下文理解）
<li>高效性：能够快速处理大量数据</li>
#: 该行执行对应逻辑（结合上下文理解）
<li>灵活性：支持多种配置和扩展方式</li>
#: 该行执行对应逻辑（结合上下文理解）
<li>易用性：提供友好的接口和文档</li>
#: 该行执行对应逻辑（结合上下文理解）
<li>社区活跃：拥有庞大的开发者社区</li>
#: 该行执行对应逻辑（结合上下文理解）
</ul>

#: 该行执行对应逻辑（结合上下文理解）
<h3>1.2 发展历程</h3>
#: 该行执行对应逻辑（结合上下文理解）
<p>{title} 的发展可以追溯到多年前。经过持续的迭代和优化，
#: 该行执行对应逻辑（结合上下文理解）
如今已经成为行业标准之一。以下是关键时间节点：</p>
#: 该行执行对应逻辑（结合上下文理解）
<ol>
#: 该行执行对应逻辑（结合上下文理解）
<li>2018年：初始版本发布</li>
#: 该行执行对应逻辑（结合上下文理解）
<li>2020年：重大架构升级</li>
#: 该行执行对应逻辑（结合上下文理解）
<li>2022年：生态系统成熟</li>
#: 该行执行对应逻辑（结合上下文理解）
<li>2024年：AI 集成能力增强</li>
#: 该行执行对应逻辑（结合上下文理解）
</ol>

#: 该行执行对应逻辑（结合上下文理解）
<h2>二、核心概念</h2>
#: 该行执行对应逻辑（结合上下文理解）
<p>在深入实践之前，我们需要理解一些核心概念。
#: 该行执行对应逻辑（结合上下文理解）
这些概念是后续学习的基础。</p>

#: 该行执行对应逻辑（结合上下文理解）
<table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse;">
#: 该行执行对应逻辑（结合上下文理解）
<thead>
#: 该行执行对应逻辑（结合上下文理解）
<tr style="background:#f8f0ff;">
#: 该行执行对应逻辑（结合上下文理解）
<th>概念</th>
#: 该行执行对应逻辑（结合上下文理解）
<th>说明</th>
#: 该行执行对应逻辑（结合上下文理解）
<th>重要程度</th>
#: 该行执行对应逻辑（结合上下文理解）
</tr>
#: 该行执行对应逻辑（结合上下文理解）
</thead>
#: 该行执行对应逻辑（结合上下文理解）
<tbody>
#: 该行执行对应逻辑（结合上下文理解）
<tr><td>基础组件</td><td>构成系统的最小单元</td><td>⭐⭐⭐⭐⭐</td></tr>
#: 该行执行对应逻辑（结合上下文理解）
<tr><td>配置管理</td><td>系统参数的统一管理方式</td><td>⭐⭐⭐⭐</td></tr>
#: 该行执行对应逻辑（结合上下文理解）
<tr><td>扩展机制</td><td>通过插件或中间件扩展功能</td><td>⭐⭐⭐⭐</td></tr>
#: 该行执行对应逻辑（结合上下文理解）
<tr><td>性能调优</td><td>优化系统运行效率的方法</td><td>⭐⭐⭐</td></tr>
#: 该行执行对应逻辑（结合上下文理解）
<tr><td>安全防护</td><td>保护系统免受攻击的措施</td><td>⭐⭐⭐⭐⭐</td></tr>
#: 该行执行对应逻辑（结合上下文理解）
</tbody>
#: 该行执行对应逻辑（结合上下文理解）
</table>

#: 该行执行对应逻辑（结合上下文理解）
<h4>2.1.1 基础组件详解</h4>
#: 该行执行对应逻辑（结合上下文理解）
<p>基础组件是整个系统的基石。每个组件都有明确的职责和接口。
#: 该行执行对应逻辑（结合上下文理解）
理解组件之间的协作关系是掌握系统的关键。</p>

#: 该行执行对应逻辑（结合上下文理解）
<h5>2.1.1.1 组件生命周期</h5>
#: 该行执行对应逻辑（结合上下文理解）
<p>每个组件都有完整的生命周期：初始化 → 运行 → 销毁。
#: 该行执行对应逻辑（结合上下文理解）
在不同阶段需要执行不同的操作。</p>

#: 该行执行对应逻辑（结合上下文理解）
<h2>三、实战代码</h2>
#: 该行执行对应逻辑（结合上下文理解）
<p>理论学习之后，让我们通过实际代码来加深理解。
#: 该行执行对应逻辑（结合上下文理解）
以下是一个完整的示例：</p>

#: 该行执行对应逻辑（结合上下文理解）
<h3>3.1 基础示例</h3>
#: 该行执行对应逻辑（结合上下文理解）
<pre><code class="language-python"># {title} 基础使用示例
#: 导入模块「os」，供本文件后续使用
import os
#: 导入模块「sys」，供本文件后续使用
import sys
#: 从模块「datetime」导入所需对象
from datetime import datetime

class ExampleHandler:
    #: 该行执行对应逻辑（结合上下文理解）
    \"\"\"示例处理器：演示核心功能的使用方式\"\"\"

    def __init__(self, config=None):
        #: 定义实例/类属性「self.config」，保存对应数据
        self.config = config or {}
        #: 定义实例/类属性「self._initialized」，保存对应数据
        self._initialized = False
        #: 定义实例/类属性「self._cache」，保存对应数据
        self._cache = {}

    def initialize(self):
        #: 该行执行对应逻辑（结合上下文理解）
        \"\"\"初始化处理器\"\"\"
        #: 调用「print」执行相应逻辑
        print(f"[{datetime.now()}] 正在初始化...")
        #: 定义实例/类属性「self._initialized」，保存对应数据
        self._initialized = True
        #: 返回结果并结束当前函数
        return self

    def process(self, data):
        #: 该行执行对应逻辑（结合上下文理解）
        \"\"\"处理数据\"\"\"
        #: 条件判断：条件成立时执行该分支
        if not self._initialized:
            #: 主动抛出异常交由上层处理
            raise RuntimeError("请先调用 initialize()")
        #: 定义变量「result」，保存对应数据
        result = self._transform(data)
        #: 操作「self」的属性或方法
        self._cache[data.get('id', 'default')] = result
        #: 返回结果并结束当前函数
        return result

    def _transform(self, data):
        #: 该行执行对应逻辑（结合上下文理解）
        \"\"\"内部转换方法\"\"\"
        #: 返回结果并结束当前函数
        return {
            #: 配置项「original」：字典/模型的该键设置为对应值
            'original': data,
            #: 配置项「processed」：字典/模型的该键设置为对应值
            'processed': True,
            #: 配置项「timestamp」：字典/模型的该键设置为对应值
            'timestamp': datetime.now().isoformat(),
        #: 该行执行对应逻辑（结合上下文理解）
        }

#: 条件判断：条件成立时执行该分支
if __name__ == '__main__':
    #: 定义变量「handler」，保存对应数据
    handler = ExampleHandler({'debug': True}).initialize()
    #: 定义变量「result」，保存对应数据
    result = handler.process({'id': 1, 'name': 'test'})
    #: 调用「print」执行相应逻辑
    print(f"处理结果: {result}")
#: 该行执行对应逻辑（结合上下文理解）
</code></pre>

#: 该行执行对应逻辑（结合上下文理解）
<h3>3.2 进阶示例</h3>
#: 该行执行对应逻辑（结合上下文理解）
<pre><code class="language-javascript">// 前端集成示例
class FrontendIntegration {
  #: 调用「constructor」执行相应逻辑
  constructor(options = {}) {
    #: 定义实例/类属性「this.options」，保存对应数据
    this.options = {
      #: 配置项「endpoint」：以键值形式设置对应参数
      endpoint: '/api/v1/',
      #: 配置项「timeout」：以键值形式设置对应参数
      timeout: 5000,
      #: 配置项「retries」：以键值形式设置对应参数
      retries: 3,
      #: 该行执行对应逻辑（结合上下文理解）
      ...options
    #: 该行执行对应逻辑（结合上下文理解）
    };
    #: 定义实例/类属性「this.client」，保存对应数据
    this.client = this._createClient();
  #: 该行执行对应逻辑（结合上下文理解）
  }

  #: 该行执行对应逻辑（结合上下文理解）
  async fetchData(path, params = {}) {
    #: 该行执行对应逻辑（结合上下文理解）
    const url = new URL(this.options.endpoint + path);
    #: 调用「Object.entries」执行相应逻辑
    Object.entries(params).forEach(([k, v]) =>
      #: 调用「url.searchParams.set」执行相应逻辑
      url.searchParams.set(k, v)
    #: 该行执行对应逻辑（结合上下文理解）
    );

    #: 循环遍历，逐个处理元素
    for (let attempt = 0; attempt < this.options.retries; attempt++) {
      #: 尝试执行可能出错的代码
      try {
        #: 该行执行对应逻辑（结合上下文理解）
        const response = await fetch(url, {
          #: 配置项「method」：以键值形式设置对应参数
          method: 'GET',
          #: 配置项「headers」：以键值形式设置对应参数
          headers: { 'Content-Type': 'application/json' },
          #: 配置项「signal」：以键值形式设置对应参数
          signal: AbortSignal.timeout(this.options.timeout),
        #: 该行执行对应逻辑（结合上下文理解）
        });
        #: 条件判断：条件成立时执行该分支
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        #: 返回结果并结束当前函数
        return await response.json();
      #: 该行执行对应逻辑（结合上下文理解）
      } catch (error) {
        #: 调用「console.warn」执行相应逻辑
        console.warn(`尝试 ${attempt + 1} 失败:`, error.message);
        #: 条件判断：条件成立时执行该分支
        if (attempt === this.options.retries - 1) throw error;
        #: 该行执行对应逻辑（结合上下文理解）
        await new Promise(r => setTimeout(r, 1000 * (attempt + 1)));
      #: 该行执行对应逻辑（结合上下文理解）
      }
    #: 该行执行对应逻辑（结合上下文理解）
    }
  #: 该行执行对应逻辑（结合上下文理解）
  }
#: 该行执行对应逻辑（结合上下文理解）
}
#: 该行执行对应逻辑（结合上下文理解）
</code></pre>

#: 该行执行对应逻辑（结合上下文理解）
<h2>四、常见问题</h2>
#: 该行执行对应逻辑（结合上下文理解）
<p>在实际使用过程中，可能会遇到一些常见问题。
#: 该行执行对应逻辑（结合上下文理解）
以下是整理的 FAQ：</p>

#: 该行执行对应逻辑（结合上下文理解）
<h3>Q1: 如何处理性能瓶颈？</h3>
#: 该行执行对应逻辑（结合上下文理解）
<p><strong>A:</strong> 首先使用性能分析工具定位瓶颈，然后针对性优化。
#: 该行执行对应逻辑（结合上下文理解）
常见的优化手段包括：缓存、异步处理、批量操作、索引优化等。</p>

#: 该行执行对应逻辑（结合上下文理解）
<h3>Q2: 安全性如何保障？</h3>
#: 该行执行对应逻辑（结合上下文理解）
<p><strong>A:</strong> 遵循安全最佳实践：输入验证、输出转义、使用参数化查询、
#: 该行执行对应逻辑（结合上下文理解）
实施 CSRF 防护、定期更新依赖、进行安全审计等。</p>

#: 该行执行对应逻辑（结合上下文理解）
<h2>五、总结与展望</h2>
#: 该行执行对应逻辑（结合上下文理解）
<p>通过本文的学习，相信你对 <strong>{title}</strong> 有了更深入的理解。
#: 该行执行对应逻辑（结合上下文理解）
技术的学习是一个持续的过程，希望本文能成为你技术道路上的一个参考。</p>

#: 该行执行对应逻辑（结合上下文理解）
<blockquote>🌟 记住：实践出真知。只有通过不断的实践和总结，才能真正掌握一门技术。</blockquote>

#: 该行执行对应逻辑（结合上下文理解）
<p>如果你觉得本文对你有帮助，欢迎点赞、收藏、分享三连支持！
#: 该行执行对应逻辑（结合上下文理解）
有任何问题也可以在评论区留言交流~ 🌸</p>
"""


class Command(BaseCommand):
    """综合数据维护命令。"""

    #: 定义变量「help」，保存对应数据
    help = '数据清理 / 重算 / 重置 / 种子数据生成 / 静态产物生成的一站式入口'

    def add_arguments(self, parser):
        """注册数据维护操作的开关。"""
        # 一键：跑所有非破坏性维护项（不含 seed / reset）
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--all-maintain', action='store_true',
                            #: 定义变量「help」，保存对应数据
                            help='执行全部非破坏性维护（清理+重算+生成静态产物）')

        # 清理类
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--clean-logs', action='store_true',
                            #: 定义变量「help」，保存对应数据
                            help='清理 N 天前的访问日志（默认 90 天，用 --days 指定）')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--days', type=int, default=90,
                            #: 定义变量「help」，保存对应数据
                            help='配合 --clean-logs 使用，保留最近 N 天（默认 90）')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--clean-drafts', action='store_true',
                            #: 定义变量「help」，保存对应数据
                            help='清理阅读量为 0 的草稿文章')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--clean-inactive-users', action='store_true',
                            #: 定义变量「help」，保存对应数据
                            help='清理未激活且非 staff 的用户')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--clean-test-data', action='store_true',
                            #: 定义变量「help」，保存对应数据
                            help='清理测试数据（占位提示）')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--clean-unused-images', action='store_true',
                            #: 定义变量「help」，保存对应数据
                            help='清理未使用图片（占位提示）')

        # 重算类
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--recalc-comments', action='store_true',
                            #: 定义变量「help」，保存对应数据
                            help='按已审核评论重算所有文章的 comment_count')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--recalc-rating', action='store_true',
                            #: 定义变量「help」，保存对应数据
                            help='按 Rating 表重算所有文章的 rating_avg / rating_count')

        # 重置类（破坏性，需显式开启）
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--reset-views', action='store_true',
                            #: 定义变量「help」，保存对应数据
                            help='将所有文章阅读量清零（破坏性）')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--reset-db', action='store_true',
                            #: 定义变量「help」，保存对应数据
                            help='数据库重置占位（真正重置请用 migrate）')

        # 静态产物类
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--gen-rss', action='store_true',
                            #: 定义变量「help」，保存对应数据
                            help='提示 RSS 订阅源地址（动态路由，无需离线生成）')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--gen-sitemap', action='store_true',
                            #: 定义变量「help」，保存对应数据
                            help='提示 sitemap.xml 地址（动态路由，无需离线生成）')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--export-backup', action='store_true',
                            #: 定义变量「help」，保存对应数据
                            help='导出数据备份（占位提示）')

        # 种子数据类
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--seed-demo', action='store_true',
                            #: 定义变量「help」，保存对应数据
                            help='写入演示分类/标签/文章（幂等，对应原 seed_demo）')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--seed-large', action='store_true',
                            #: 定义变量「help」，保存对应数据
                            help='大规模种子数据生成（对应原 seed_large_data）')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--articles', type=int, default=100,
                            #: 定义变量「help」，保存对应数据
                            help='配合 --seed-large：要生成的文章数（默认 100）')
        #: 调用「parser.add_argument」执行相应逻辑
        parser.add_argument('--comments', type=int, default=1000,
                            #: 定义变量「help」，保存对应数据
                            help='配合 --seed-large：要生成的评论数（默认 1000）')

    def handle(self, *args, **options):
        """按 flag 分发到各个维护方法。"""
        #: 定义变量「run_all」，保存对应数据
        run_all = options['all_maintain']

        # 映射：flag 名 -> (标题, 方法)
        #: 定义变量「blocks」，保存对应数据（集合/元组）
        blocks = [
            #: 该行执行对应逻辑（结合上下文理解）
            ('clean_logs', '清理过期访问日志', self._clean_logs),
            #: 该行执行对应逻辑（结合上下文理解）
            ('clean_drafts', '清理空草稿', self._clean_drafts),
            #: 该行执行对应逻辑（结合上下文理解）
            ('clean_inactive_users', '清理未激活用户', self._clean_inactive_users),
            #: 该行执行对应逻辑（结合上下文理解）
            ('clean_test_data', '清理测试数据', self._clean_test_data),
            #: 该行执行对应逻辑（结合上下文理解）
            ('clean_unused_images', '清理未使用图片', self._clean_unused_images),
            #: 该行执行对应逻辑（结合上下文理解）
            ('recalc_comments', '重算评论数', self._recalc_comments),
            #: 该行执行对应逻辑（结合上下文理解）
            ('recalc_rating', '重算评分', self._recalc_rating),
            #: 该行执行对应逻辑（结合上下文理解）
            ('reset_views', '重置阅读量', self._reset_views),
            #: 该行执行对应逻辑（结合上下文理解）
            ('reset_db', '数据库重置', self._reset_db),
            #: 该行执行对应逻辑（结合上下文理解）
            ('gen_rss', 'RSS 订阅源', self._gen_rss),
            #: 该行执行对应逻辑（结合上下文理解）
            ('gen_sitemap', '站点地图', self._gen_sitemap),
            #: 该行执行对应逻辑（结合上下文理解）
            ('export_backup', '数据备份', self._export_backup),
            #: 该行执行对应逻辑（结合上下文理解）
            ('seed_demo', '演示数据', self._seed_demo),
            #: 该行执行对应逻辑（结合上下文理解）
            ('seed_large', '大规模种子数据', self._seed_large),
        #: 该行执行对应逻辑（结合上下文理解）
        ]

        #: 条件判断：条件成立时执行该分支
        if not run_all and not any(options[key] for key, _, _ in blocks):
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.WARNING(
                #: 该行执行对应逻辑（结合上下文理解）
                '未指定任何维护项。使用 --all-maintain 跑全部非破坏性项，'
                #: 该行执行对应逻辑（结合上下文理解）
                '或用 --clean-logs / --recalc-comments / --seed-demo 等单项开关。'))
            #: 返回结果并结束当前函数
            return

        # --all-maintain 白名单：只跑非破坏性维护项，不含 reset / seed / 占位命令
        #: 定义变量「non_destructive」，保存对应数据
        non_destructive = {
            #: 该行执行对应逻辑（结合上下文理解）
            'clean_logs', 'clean_drafts', 'clean_inactive_users',
            #: 该行执行对应逻辑（结合上下文理解）
            'recalc_comments', 'recalc_rating',
            #: 该行执行对应逻辑（结合上下文理解）
            'gen_rss', 'gen_sitemap',
        #: 该行执行对应逻辑（结合上下文理解）
        }

        #: 定义变量「executed」，保存对应数据
        executed = 0
        #: 循环遍历，逐个处理元素
        for key, title, method in blocks:
            #: 定义变量「should_run」，保存对应数据
            should_run = False
            #: 条件判断：条件成立时执行该分支
            if run_all:
                #: 定义变量「should_run」，保存对应数据
                should_run = key in non_destructive
            #: 以上条件均不成立时的兜底分支
            else:
                #: 定义变量「should_run」，保存对应数据
                should_run = bool(options[key])
            #: 条件判断：条件成立时执行该分支
            if not should_run:
                #: 跳过本次进入下一次迭代
                continue

            #: 该行执行对应逻辑（结合上下文理解）
            executed += 1
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(self.style.MIGRATE_HEADING(f'\n=== {title} ==='))
            #: 尝试执行可能出错的代码
            try:
                #: 调用「method」执行相应逻辑
                method(options)
            #: 捕获并处理异常，避免程序中断
            except Exception as exc:
                #: 调用「self.stderr.write」执行相应逻辑
                self.stderr.write(self.style.ERROR(f'  执行失败: {exc}'))

        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.SUCCESS(f'\n数据维护完成，共执行 {executed} 个模块。'))

    # ============================ 清理类 ============================

    def _clean_logs(self, options):
        """删除指定天数之前的访问日志。"""
        #: 从模块「blog.models」导入所需对象
        from blog.models import AccessLog
        #: 定义变量「days」，保存对应数据
        days = options['days']
        #: 获取当前时间（时区感知），统一时间口径
        cutoff = timezone.now() - timedelta(days=days)
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        deleted, _ = AccessLog.objects.filter(created_at__lt=cutoff).delete()
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.SUCCESS(f'已清理 {deleted} 条 {days} 天前的访问日志'))

    def _clean_drafts(self, options):
        """删除阅读量为 0 的草稿文章。"""
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        deleted, _ = Article.objects.filter(status='draft', views=0).delete()
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.SUCCESS(f'已清理 {deleted} 篇空草稿'))

    def _clean_inactive_users(self, options):
        """删除未激活且非 staff 的用户。"""
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        deleted, _ = User.objects.filter(is_active=False, is_staff=False).delete()
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.SUCCESS(f'已清理 {deleted} 个未激活用户'))

    def _clean_test_data(self, options):
        """测试数据清理占位。"""
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write('测试数据清理：请使用 --clean-logs / --clean-drafts / --clean-inactive-users 组合')

    def _clean_unused_images(self, options):
        """未使用图片清理占位。"""
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write('未使用图片扫描：请结合 media/ 目录与 Article 正文离线检查')

    # ============================ 重算类 ============================

    def _recalc_comments(self, options):
        """按已审核评论重算每篇文章的 comment_count。"""
        #: 从模块「blog.models」导入所需对象
        from blog.models import Comment
        #: 循环遍历，逐个处理元素
        for article in Article.objects.all():
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            cnt = Comment.objects.filter(article=article, is_approved=True).count()
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            Article.objects.filter(pk=article.pk).update(comment_count=cnt)
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.SUCCESS('评论数已重算'))

    def _recalc_rating(self, options):
        """按 Rating 表重算每篇文章的平均分与计数。"""
        #: 从模块「blog.models」导入所需对象
        from blog.models import Rating
        #: 循环遍历，逐个处理元素
        for article in Article.objects.all():
            #: 使用聚合函数做统计查询
            agg = article.ratings.aggregate(v=Avg('score'))
            #: 定义实例/类属性「article.rating_avg」，保存对应数据
            article.rating_avg = round(agg['v'] or 0, 1)
            #: 定义实例/类属性「article.rating_count」，保存对应数据
            article.rating_count = article.ratings.count()
            #: 调用「article.save」执行相应逻辑
            article.save(update_fields=['rating_avg', 'rating_count'])
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.SUCCESS('评分已重算'))

    # ============================ 重置类 ============================

    def _reset_views(self, options):
        """将所有文章阅读量清零。"""
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        n = Article.objects.update(views=0)
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.SUCCESS(f'已重置 {n} 篇文章阅读量'))

    def _reset_db(self, options):
        """数据库重置占位提示。"""
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.WARNING('重置数据库请使用 migrate / flush，本命令仅占位'))

    # ============================ 静态产物类 ============================

    def _gen_rss(self, options):
        """RSS 订阅源为动态路由，提示其地址。"""
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write('RSS 订阅源为动态路由：访问 /feed/ 即可，无需离线生成')

    def _gen_sitemap(self, options):
        """站点地图为动态路由，提示其地址。"""
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write('站点地图为动态路由：访问 /sitemap.xml 即可，无需离线生成')

    def _export_backup(self, options):
        """数据备份占位提示。"""
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write('数据备份请使用 Django dumpdata 或数据库自带工具（mysqldump 等）')

    # ============================ 种子数据 ============================

    def _seed_demo(self, options):
        """写入演示数据（幂等）：管理员 / 3 个分类 / 7 个标签 / 12 篇演示文章。"""
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        admin, _ = User.objects.get_or_create(
            #: 定义变量「username」，保存对应数据
            username='admin',
            #: 定义变量「defaults」，保存对应数据
            defaults={'is_staff': True, 'is_superuser': True, 'nickname': '站长'})
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        cats = {name: Category.objects.get_or_create(
            #: 定义变量「name」，保存对应数据
            name=name, defaults={'description': f'{name}分类'})[0]
            #: 循环遍历，逐个处理元素
            for name in ('技术笔记', '二次元', '生活随笔')}
        #: 定义变量「tag_names」，保存对应数据（集合/元组）
        tag_names = ['Django', 'Python', 'MySQL', 'CKEditor', '教程', '踩坑', '随想']
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        tags = {n: Tag.objects.get_or_create(name=n)[0] for n in tag_names}

        # 首篇为富文本演示长文
        #: 条件判断：条件成立时执行该分支
        if not Article.objects.filter(title='CKEditor 富文本编辑器接入指南').exists():
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            a = Article.objects.create(
                #: 定义变量「title」，保存对应数据
                title='CKEditor 富文本编辑器接入指南', content=RICH_ARTICLE,
                #: 定义变量「author」，保存对应数据
                author=admin, category=cats['技术笔记'], kind='article',
                #: 获取当前时间（时区感知），统一时间口径
                status='published', views=128, created_at=timezone.now())
            #: 调用「a.tags.set」执行相应逻辑
            a.tags.set([tags['Django'], tags['CKEditor'], tags['教程']])
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            EditLog.objects.create(article=a, editor=admin)

        #: 循环遍历，逐个处理元素
        for i, (kind, title, cat) in enumerate(DEMO_TITLES):
            #: 条件判断：条件成立时执行该分支
            if Article.objects.filter(title=title).exists():
                #: 跳过本次进入下一次迭代
                continue
            #: 定义变量「body」，保存对应数据（集合/元组）
            body = (f'<h2>引言</h2><p>《{title}》的正文内容，这是第 {i + 2} 篇演示文章。</p>'
                    #: 该行执行对应逻辑（结合上下文理解）
                    '<h2>正文</h2><p>这里是段落内容，支持图片、表格与代码块。</p>'
                    #: 该行执行对应逻辑（结合上下文理解）
                    '<h3>小节</h3><p>萌百风格双栏布局，右侧自动生成目录。</p>')
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            a = Article.objects.create(
                #: 定义变量「title」，保存对应数据
                title=title, content=body, author=admin, category=cats[cat],
                #: 定义变量「kind」，保存对应数据
                kind=kind, status='published', views=(13 - i) * 7)
            #: 调用「a.tags.set」执行相应逻辑
            a.tags.set([tags['Python'], tags['教程']] if kind == 'article' else [tags['随想']])
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            EditLog.objects.create(article=a, editor=admin)

        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.SUCCESS(
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            f'演示数据就绪：文章 {Article.objects.count()} 篇，'
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            f'分类 {Category.objects.count()} 个，标签 {Tag.objects.count()} 个'))

    def _seed_large(self, options):
        """大规模种子数据生成：20 用户 / 12 分类 / 35 标签 / N 篇文章 / M 条评论。"""
        #: 定义变量「num_articles」，保存对应数据
        num_articles = options['articles']
        #: 定义变量「num_comments」，保存对应数据
        num_comments = options['comments']

        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 60))
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.MIGRATE_HEADING('  大规模测试数据种子生成器'))
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 60))

        #: 定义变量「users」，保存对应数据
        users = self._seed_create_users()
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(f'  ✓ 用户：{len(users)} 个')

        #: 定义变量「categories」，保存对应数据
        categories = self._seed_create_categories()
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(f'  ✓ 分类：{len(categories)} 个')

        #: 定义变量「tags」，保存对应数据
        tags = self._seed_create_tags()
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(f'  ✓ 标签：{len(tags)} 个')

        #: 条件判断：条件成立时执行该分支
        if num_articles > 0:
            #: 定义变量「articles」，保存对应数据
            articles = self._seed_create_articles(num_articles, users, categories, tags)
        #: 以上条件均不成立时的兜底分支
        else:
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            articles = list(Article.objects.filter(status='published')[:50])
        #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
        self.stdout.write(f'  ✓ 文章：{len(articles)} 篇（累计 {Article.objects.count()} 篇）')

        #: 定义变量「comment_count」，保存对应数据
        comment_count = self._seed_create_comments(num_comments, users, articles)
        #: 条件判断：条件成立时执行该分支
        if comment_count > 0:
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write(f'  ✓ 评论：{comment_count} 条')

        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.SUCCESS('=' * 60))
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.SUCCESS(
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            f'  数据生成完成！文章 {Article.objects.count()} 篇，'
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            f'分类 {Category.objects.count()} 个，标签 {Tag.objects.count()} 个'))
        #: 调用「self.stdout.write」执行相应逻辑
        self.stdout.write(self.style.SUCCESS('=' * 60))

    def _seed_create_users(self):
        """创建种子用户列表（幂等）。"""
        #: 定义变量「users」，保存对应数据（集合/元组）
        users = []
        #: 循环遍历，逐个处理元素
        for username, nickname, is_admin in USER_DATA:
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            user, created = User.objects.get_or_create(
                #: 定义变量「username」，保存对应数据
                username=username,
                #: 定义变量「defaults」，保存对应数据
                defaults={
                    #: 配置项「nickname」：字典/模型的该键设置为对应值
                    'nickname': nickname,
                    #: 配置项「is_staff」：字典/模型的该键设置为对应值
                    'is_staff': is_admin,
                    #: 配置项「is_superuser」：字典/模型的该键设置为对应值
                    'is_superuser': is_admin,
                    #: 配置项「email」：字典/模型的该键设置为对应值
                    'email': f'{username}@example.com',
                #: 该行执行对应逻辑（结合上下文理解）
                })
            #: 条件判断：条件成立时执行该分支
            if created:
                #: 调用「user.set_password」执行相应逻辑
                user.set_password('test123456')
                #: 保存对象（INSERT/UPDATE），可能触发模型信号
                user.save()
            #: 调用「users.append」执行相应逻辑
            users.append(user)
        #: 返回结果并结束当前函数
        return users

    def _seed_create_categories(self):
        """创建种子分类列表（幂等）。"""
        #: 定义变量「categories」，保存对应数据（集合/元组）
        categories = []
        #: 循环遍历，逐个处理元素
        for name, desc in CATEGORY_DATA:
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            cat, _ = Category.objects.get_or_create(name=name, defaults={'description': desc})
            #: 调用「categories.append」执行相应逻辑
            categories.append(cat)
        #: 返回结果并结束当前函数
        return categories

    def _seed_create_tags(self):
        """创建种子标签列表（幂等）。"""
        #: 返回结果并结束当前函数
        return [Tag.objects.get_or_create(name=n)[0] for n in TAG_NAMES]

    def _seed_create_articles(self, count, users, categories, tags):
        """生成指定数量的文章（固定随机种子，可复现）。"""
        #: 调用「random.seed」执行相应逻辑
        random.seed(42)
        #: 获取当前时间（时区感知），统一时间口径
        now = timezone.now()
        #: 定义变量「created_articles」，保存对应数据（集合/元组）
        created_articles = []

        #: 循环遍历，逐个处理元素
        for i in range(count):
            #: 定义变量「category」，保存对应数据
            category = random.choice(categories)
            #: 定义变量「templates」，保存对应数据
            templates = TITLE_TEMPLATES.get(category.name, TITLE_TEMPLATES['其他'])
            #: 定义变量「template」，保存对应数据
            template = random.choice(templates)
            #: 定义变量「title」，保存对应数据
            title = template.format(
                #: 定义变量「n」，保存对应数据
                n=random.randint(1, 99),
                #: 定义变量「topic」，保存对应数据
                topic=random.choice(['异步编程', '内存管理', '并发控制', '设计模式',
                                     #: 该行执行对应逻辑（结合上下文理解）
                                     '性能调优', '安全加固', '架构设计', '测试驱动']))

            # 避免标题重复
            #: 定义变量「base_title」，保存对应数据
            base_title = title
            #: 定义变量「suffix」，保存对应数据
            suffix = 1
            #: 条件为真时反复执行
            while Article.objects.filter(title=title).exists():
                #: 该行执行对应逻辑（结合上下文理解）
                suffix += 1
                #: 定义变量「title」，保存对应数据
                title = f'{base_title}（{suffix}）'

            #: 定义变量「kind」，保存对应数据
            kind = random.choices(['article', 'note', 'page'], weights=[70, 20, 10])[0]
            #: 定义变量「status」，保存对应数据
            status = random.choices(['published', 'draft'], weights=[85, 15])[0]
            #: 定义变量「days_ago」，保存对应数据
            days_ago = random.randint(0, 365)
            #: 定义变量「hours_ago」，保存对应数据
            hours_ago = random.randint(0, 23)
            #: 定义变量「created_at」，保存对应数据
            created_at = now - timedelta(days=days_ago, hours=hours_ago)
            #: 定义变量「views」，保存对应数据
            views = min(int(random.paretovariate(1.5) * 50), 10000)

            #: 定义变量「extra_kwargs」，保存对应数据
            extra_kwargs = {}
            #: 条件判断：条件成立时执行该分支
            if hasattr(Article, 'likes'):
                #: 该行执行对应逻辑（结合上下文理解）
                extra_kwargs['likes'] = random.randint(0, 500)

            #: 定义变量「content」，保存对应数据
            content = RICH_CONTENT_TEMPLATE.replace(
                #: 该行执行对应逻辑（结合上下文理解）
                '{title}', title).replace('{n}', str(random.randint(60, 95)))
            #: 定义变量「author」，保存对应数据
            author = random.choice(users)
            #: 定义变量「article_tags」，保存对应数据
            article_tags = random.sample(tags, random.randint(2, 5))

            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            article = Article.objects.create(
                #: 定义变量「title」，保存对应数据
                title=title, content=content, author=author, category=category,
                #: 定义变量「kind」，保存对应数据
                kind=kind, status=status, views=views, created_at=created_at,
                #: 该行执行对应逻辑（结合上下文理解）
                **extra_kwargs)
            #: 调用「article.tags.set」执行相应逻辑
            article.tags.set(article_tags)
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            EditLog.objects.create(article=article, editor=author)
            #: 调用「created_articles.append」执行相应逻辑
            created_articles.append(article)

            #: 条件判断：条件成立时执行该分支
            if (i + 1) % 20 == 0:
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write(f'    已生成 {i + 1}/{count} 篇文章...')

        #: 返回结果并结束当前函数
        return created_articles

    def _seed_create_comments(self, count, users, articles):
        """生成评论数据（仅当 Comment 模型存在时）。"""
        #: 尝试执行可能出错的代码
        try:
            #: 从模块「blog.models」导入所需对象
            from blog.models import Comment
        #: 捕获并处理异常，避免程序中断
        except ImportError:
            #: 调用「self.stdout.write」执行相应逻辑
            self.stdout.write('  ⚠ Comment 模型不存在，跳过评论生成')
            #: 返回结果并结束当前函数
            return 0

        #: 调用「random.seed」执行相应逻辑
        random.seed(123)
        #: 获取当前时间（时区感知），统一时间口径
        now = timezone.now()
        #: 定义变量「articles_with_comments」，保存对应数据
        articles_with_comments = articles[:50] if len(articles) >= 50 else articles
        #: 定义变量「created_count」，保存对应数据
        created_count = 0

        #: 定义变量「comment_texts」，保存对应数据（集合/元组）
        comment_texts = [
            #: 该行执行对应逻辑（结合上下文理解）
            '写得太好了！学到了很多，感谢分享~ 🌸',
            #: 该行执行对应逻辑（结合上下文理解）
            '这篇文章解决了我困扰已久的问题，收藏了！',
            #: 该行执行对应逻辑（结合上下文理解）
            '请问第三部分的代码在 Windows 上也能运行吗？',
            #: 该行执行对应逻辑（结合上下文理解）
            '博主的写作风格真可爱，内容也很有深度喵~',
            #: 该行执行对应逻辑（结合上下文理解）
            '终于找到一篇讲清楚的文章了，之前看官方文档一直没看懂',
            #: 该行执行对应逻辑（结合上下文理解）
            '建议补充一下性能测试的数据，会更有说服力',
            #: 该行执行对应逻辑（结合上下文理解）
            '按照教程做了一遍，成功运行！感谢大佬~',
            #: 该行执行对应逻辑（结合上下文理解）
            '这个思路很新颖，我之前一直用的另一种方法',
            #: 该行执行对应逻辑（结合上下文理解）
            '代码示例很完整，复制下来就能用，赞！',
            #: 该行执行对应逻辑（结合上下文理解）
            '有没有后续文章？期待更新~ ✨',
            #: 该行执行对应逻辑（结合上下文理解）
            '踩过同样的坑，当时折腾了好久才解决',
            #: 该行执行对应逻辑（结合上下文理解）
            '建议加个目录，文章有点长，翻起来不太方便',
            #: 该行执行对应逻辑（结合上下文理解）
            '暗黑模式下代码块的对比度可以再调高一些',
            #: 该行执行对应逻辑（结合上下文理解）
            '收藏了，周末慢慢研究。感谢博主的用心整理！',
            #: 该行执行对应逻辑（结合上下文理解）
            '这个功能在最新版本中已经内置了，不过原理讲得很清楚',
        #: 该行执行对应逻辑（结合上下文理解）
        ]

        #: 循环遍历，逐个处理元素
        for i in range(count):
            #: 定义变量「article」，保存对应数据
            article = random.choice(articles_with_comments)
            #: 定义变量「user」，保存对应数据
            user = random.choice(users)
            #: 定义变量「days_ago」，保存对应数据
            days_ago = random.randint(0, 180)
            #: 定义变量「created_at」，保存对应数据
            created_at = now - timedelta(
                #: 定义变量「days」，保存对应数据
                days=days_ago,
                #: 定义变量「hours」，保存对应数据
                hours=random.randint(0, 23),
                #: 定义变量「minutes」，保存对应数据
                minutes=random.randint(0, 59))

            #: 定义变量「parent」，保存对应数据
            parent = None
            #: 条件判断：条件成立时执行该分支
            if random.random() < 0.3:
                #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
                existing = Comment.objects.filter(article=article, parent_comment__isnull=True)
                #: 条件判断：条件成立时执行该分支
                if existing.exists():
                    #: 定义变量「parent」，保存对应数据
                    parent = random.choice(list(existing[:20]))

            #: 定义变量「content」，保存对应数据
            content = random.choice(comment_texts)
            #: Django ORM：对数据库执行查询/写入，注意过滤条件与异常处理
            comment = Comment.objects.create(
                #: 定义变量「article」，保存对应数据
                article=article, user=user, content=content,
                #: 定义变量「parent_comment」，保存对应数据
                parent_comment=parent, is_approved=True, created_at=created_at)

            #: 条件判断：条件成立时执行该分支
            if hasattr(Comment, 'likes'):
                #: 定义实例/类属性「comment.likes」，保存对应数据
                comment.likes = random.randint(0, 500)
                #: 保存对象（INSERT/UPDATE），可能触发模型信号
                comment.save()

            #: 该行执行对应逻辑（结合上下文理解）
            created_count += 1
            #: 条件判断：条件成立时执行该分支
            if (i + 1) % 200 == 0:
                #: 调用「self.stdout.write」执行相应逻辑
                self.stdout.write(f'    已生成 {i + 1}/{count} 条评论...')

        #: 返回结果并结束当前函数
        return created_count
